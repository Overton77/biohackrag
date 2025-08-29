# enhancement_pipeline.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Iterable, Union, Callable
import asyncio
from contextlib import asynccontextmanager

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
from bs4 import BeautifulSoup

from bson import ObjectId

from src.config.mongo_setup import init_beanie_with_pymongo
from src.mongo_schema_overwrite import Episode, Resource, Person
from firecrawl import AsyncFirecrawl
from config.firecrawl_client import firecrawl as shared_firecrawl
from config.settings import get_settings

# --- reuse your sync parsers exactly as-is:
from .episode_summaries import (
    parse_episode_timeline as es_parse_episode_timeline,
    parse_resources as es_parse_resources,
    parse_major_summary as es_parse_major_summary,
    parse_sponsors as es_parse_sponsors,
    extract_episode_number as es_extract_episode_number,
    parse_youtube_embed_url as es_parse_youtube_embed_url,
)
from .store_transcript_links import extract_transcript_url_enhanced

settings = get_settings()

# =========================================================
# A. Session + Helpers
# =========================================================
@asynccontextmanager
async def aiohttp_session(total_timeout_s: int = 30):
    timeout = aiohttp.ClientTimeout(total=total_timeout_s)
    conn = aiohttp.TCPConnector(limit=100, enable_cleanup_closed=True)
    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
        yield session

HEADERS = settings.web_fetch_headers

@retry(
    retry=retry_if_exception_type(aiohttp.ClientError),
    wait=wait_exponential_jitter(initial=0.5, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, headers=HEADERS, allow_redirects=True) as resp:
        resp.raise_for_status()
        return await resp.text()

async def to_thread(fn: Callable, *args, **kwargs):
    """Run a sync parser concurrently without blocking the event loop."""
    return await asyncio.to_thread(fn, *args, **kwargs)

def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")

# =========================================================
# B. Fan-out parsers (run in parallel on one HTML fetch)
# =========================================================
async def fanout_parse_all(html: str) -> Dict[str, Any]:
    # Build soup once and pass the same object to all sync parsers
    soup = _soup(html)

    (
        timeline,
        resources,
        major_summary,
        sponsors,
        episode_number,
        youtube_embed_url,
        transcript_link,
    ) = await asyncio.gather(
        to_thread(es_parse_episode_timeline, soup),
        to_thread(es_parse_resources, soup),
        to_thread(es_parse_major_summary, soup),
        to_thread(es_parse_sponsors, soup),
        to_thread(es_extract_episode_number, soup),
        to_thread(es_parse_youtube_embed_url, soup),
        to_thread(extract_transcript_url_enhanced, html),
    )

    youtube_watch_url = None
    youtube_video_id = None
    if youtube_embed_url:
        try:
            youtube_video_id = youtube_embed_url.rstrip("/").split("/")[-1].split("?")[0]
            youtube_watch_url = f"https://www.youtube.com/watch?v={youtube_video_id}"
        except Exception:
            pass

    return {
        "timeline": timeline or [],
        "resources": resources or [],
        "major_summary": major_summary or {},
        "sponsors": sponsors or [],
        "episode_number": episode_number,
        "youtube_embed_url": youtube_embed_url,
        "youtube_watch_url": youtube_watch_url,
        "youtube_video_id": youtube_video_id,
        "transcript_link": transcript_link,
    }

# =========================================================
# C. Firecrawl guest extraction (async)
# =========================================================
async def get_guest_name(url: str, client: Optional[AsyncFirecrawl]) -> Optional[str]:
    if client is None:
        return None

    from pydantic import BaseModel
    class GuestName(BaseModel):
        guest_name: str

    prompt = (
        "Extract the guest name of the episode. The guest name is the name of the person who is the guest of the episode"
    )
    try:
        res = await client.extract(
            urls=[url],
            prompt=prompt,
            schema=GuestName.model_json_schema(),
        )
        if res.success and isinstance(res.data, dict):
            return res.data.get("guest_name")
    except Exception:
        pass
    return None

# =========================================================
# D. Resources helpers (async upsert)
# =========================================================
def _guess_title(text: Optional[str], url: str) -> Optional[str]:
    """
    If `text` looks like 'Some Title : https://url', use left side; else fallback to hostname.
    """
    if text:
        parts = text.split(" : ", 1)
        if parts and parts[0].strip():
            return parts[0].strip()
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc
        return host or None
    except Exception:
        return None

def _normalize_resource_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Accepts a parser payload and returns a normalized list of items like:
      {"text": "... : https://example.com", "links": ["https://example.com"]}
    """
    if not data:
        return []
    # Our fanout_parse_all returns under "resources"
    lst = data.get("resources")
    return lst if isinstance(lst, list) else []

async def _upsert_resources_from_items(
    items: Iterable[Dict[str, Any]]
) -> List[Resource]:
    """
    Build/return Resource documents by URL (dedup by URL).
    If a Resource already exists, keep it; if new, create it.
    Update missing titles when we can infer one.
    """
    url_to_title: Dict[str, Optional[str]] = {}
    for it in items or []:
        links = it.get("links") or []
        if not links:
            continue
        url = links[0]
        if not url:
            continue
        if url in url_to_title:
            continue
        url_to_title[url] = _guess_title(it.get("text"), url)

    if not url_to_title:
        return []

    urls = list(url_to_title.keys())

    # Prefetch existing
    existing = await Resource.find(Resource.url.in_(urls)).to_list()
    existing_by_url = {r.url: r for r in existing}

    result: List[Resource] = []

    for url in urls:
        title = url_to_title[url]
        if url in existing_by_url:
            res = existing_by_url[url]
            if title and not res.title:
                res.title = title
                await res.save()
            result.append(res)
        else:
            res = Resource(url=url, title=title)
            await res.insert()
            result.append(res)

    return result

# =========================================================
# E. Single episode enhancement
# =========================================================
class Enhancer:
    def __init__(
        self,
        firecrawl_client: Optional[AsyncFirecrawl] = None,
        max_firecrawl_rps: float = 2.0,  # optional: cap QPS per worker
    ):
        self.firecrawl = firecrawl_client or shared_firecrawl
        # simple token-bucket via semaphore if you want a hard cap
        per_second = max(1, int(max_firecrawl_rps))
        self._firecrawl_sem = asyncio.Semaphore(per_second)

    async def enhance_one(self, session: aiohttp.ClientSession, episode: Episode) -> None:
        ep_url = episode.episode_page_url
        if not ep_url:
            return

        # Fetch once (async I/O)
        html = await fetch_html(session, ep_url)

        # Fan-out: HTML parsers + Firecrawl (parallel)
        async with self._firecrawl_sem:
            guest_task = asyncio.create_task(get_guest_name(ep_url, self.firecrawl))
        parse_task = asyncio.create_task(fanout_parse_all(html))

        guest_name, parsed = await asyncio.gather(guest_task, parse_task)

        # Fan-in: aggregate + upsert (one save)
        major = parsed.get("major_summary") or {}
        minor_summary: Optional[str] = major.get("minor_summary")

        sponsors: List[Dict[str, Any]] = parsed.get("sponsors") or []
        timeline: List[Dict[str, Any]] = parsed.get("timeline") or []
        transcript_link: Optional[str] = parsed.get("transcript_link")
        episode_number_str: Optional[str] = parsed.get("episode_number")
        youtube_embed_url: Optional[str] = parsed.get("youtube_embed_url")
        youtube_watch_url: Optional[str] = parsed.get("youtube_watch_url")
        youtube_video_id: Optional[str] = parsed.get("youtube_video_id")

        # NEW: normalize & upsert resources, attach to episode
        resource_items = _normalize_resource_items(parsed)
        resources: List[Resource] = []
        if resource_items:
            resources = await _upsert_resources_from_items(resource_items)

        # upsert/link guest
        if guest_name:
            person = await Person.find(Person.name == guest_name).first_or_none()
            if not person:
                person = Person(name=guest_name)
                await person.insert()
            if episode.guests is None:
                episode.guests = [person]
            else:
                existing_ids = {getattr(p, "id", None) for p in episode.guests}
                if getattr(person, "id", None) not in existing_ids:
                    episode.guests.append(person)  # type: ignore[arg-type]

        # episode fields
        if minor_summary:
            episode.webpage_summary = minor_summary
        if sponsors:
            episode.sponsors = sponsors
        if timeline:
            episode.timeline = timeline
        if transcript_link:
            episode.transcript_url = transcript_link
        if episode_number_str:
            try:
                episode.episode_number = int(episode_number_str)
            except Exception:
                pass
        if youtube_embed_url:
            episode.youtube_embed_url = youtube_embed_url
        if youtube_watch_url:
            episode.youtube_watch_url = youtube_watch_url
        if youtube_video_id:
            episode.youtube_video_id = youtube_video_id
        if resources:
            # Depending on your schema this may be List[Link[Resource]] or List[Resource]
            episode.webpage_resources = resources  # type: ignore[assignment]

        await episode.save()

# =========================================================
# F. Batch runners
# =========================================================
async def enhance_all_episodes(
    *,
    concurrency: int = 10,
    filter_only_missing_youtube: bool = False
) -> None:
    """
    Process a set of episodes discovered by query.
    """
    await init_beanie_with_pymongo()
    enhancer = Enhancer()

    if filter_only_missing_youtube:
        from beanie.odm.operators.find.element import Exists
        from beanie.odm.operators.find.logical import And, Or, Not
        from beanie.odm.operators.find.comparison import NE, Eq
        filter_expr = And(
            Exists(Episode.episode_page_url, True),
            NE(Episode.episode_page_url, None),
            NE(Episode.episode_page_url, ""),
            Or(
                Not(Exists(Episode.youtube_embed_url, True)),
                Eq(Episode.youtube_embed_url, None),
                Eq(Episode.youtube_embed_url, ""),
                Not(Exists(Episode.youtube_watch_url, True)),
                Eq(Episode.youtube_watch_url, None),
                Eq(Episode.youtube_watch_url, ""),
                Not(Exists(Episode.youtube_video_id, True)),
                Eq(Episode.youtube_video_id, None),
                Eq(Episode.youtube_video_id, ""),
            ),
        )
        episodes = await Episode.find(filter_expr, fetch_links=True).to_list()
    else:
        from beanie.odm.operators.find.element import Exists
        episodes = await Episode.find(Exists(Episode.episode_page_url, True), fetch_links=True).to_list()

    await _run_concurrently_over_episodes(episodes, enhancer, concurrency=concurrency)

async def enhance_episodes_by_ids(
    episode_ids: List[Union[str, ObjectId]],
    *,
    concurrency: int = 10,
) -> None:
    """
    Process a specific list of Episode _ids (strings or ObjectIds).
    Only episodes with a non-empty episode_page_url will be enhanced.
    """
    await init_beanie_with_pymongo()
    # Normalize ids to ObjectId
    _ids: List[ObjectId] = []
    for v in episode_ids:
        if isinstance(v, ObjectId):
            _ids.append(v)
        else:
            _ids.append(ObjectId(str(v)))

    # Fetch the episodes (eager list is fine; you control the id list size)
    episodes = await Episode.find(Episode.id.in_(_ids), fetch_links=True).to_list()
    # Filter out those without a target URL early
    episodes = [ep for ep in episodes if getattr(ep, "episode_page_url", None)]

    enhancer = Enhancer()
    await _run_concurrently_over_episodes(episodes, enhancer, concurrency=concurrency)

# Internal concurrent runner
async def _run_concurrently_over_episodes(
    episodes: List[Episode],
    enhancer: Enhancer,
    *,
    concurrency: int = 10,
) -> None:
    sem = asyncio.BoundedSemaphore(concurrency)

    async with aiohttp_session(total_timeout_s=30) as session:
        async def _one(ep: Episode):
            async with sem:
                try:
                    await enhancer.enhance_one(session, ep)
                except Exception as e:
                    print(f"[enhancement] Failed for {getattr(ep,'id',None)}: {e}")

        await asyncio.gather(*[_one(ep) for ep in episodes])

# =========================================================
# G. Convenience single-URL parser (no DB writes)
# =========================================================
async def enhance_one_by_url(url: str) -> Dict[str, Any]:
    async with aiohttp_session() as session:
        html = await fetch_html(session, url)
        guest_task = asyncio.create_task(get_guest_name(url, shared_firecrawl))
        parsed_task = asyncio.create_task(fanout_parse_all(html))
        guest_name, parsed = await asyncio.gather(guest_task, parsed_task)
        parsed["guest_name"] = guest_name
        return parsed 
    

if __name__ == "__main__": 
    print("Importing Episode Enhancement Pipeline")