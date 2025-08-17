from typing import Any, Dict, List, Optional
import aiohttp
from bs4 import BeautifulSoup  
from bson import ObjectId 
from src.mongo_schema_overwrite import init_beanie_with_pymongo, Episode, Transcript, Resource

# Reuse the robust parsers implemented elsewhere
from .episode_summaries import (
    parse_episode_timeline as es_parse_episode_timeline,
    parse_resources as es_parse_resources,
    parse_major_summary as es_parse_major_summary,
    parse_sponsors as es_parse_sponsors,
)
from src.store_transcript_links import extract_transcript_url_enhanced 
import asyncio  
from pymongo import AsyncMongoClient  
import json 


class WebpageEpisodeParse:
    """Async webpage parser for episode pages.

    Provides dedicated methods to parse:
    - transcript_link
    - timeline
    - resources
    - sponsors
    - major_summary

    Plus a master method to fetch HTML and return all parts together.
    """

    def __init__(self, session: Optional[aiohttp.ClientSession] = None, timeout_s: int = 30) -> None:
        self._session = session
        self._timeout_s = timeout_s

    async def _fetch_html(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://daveasprey.com/",
        }
        if self._session is not None:
            async with self._session.get(url, headers=headers, allow_redirects=True) as response:
                return await response.text()
        timeout = aiohttp.ClientTimeout(total=self._timeout_s)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, allow_redirects=True) as response:
                return await response.text()

    @staticmethod
    def _soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def parse_transcript_link(self, html: str) -> Optional[str]:
        return extract_transcript_url_enhanced(html)

    def parse_timeline(self, html: str) -> List[Dict[str, Any]]:
        soup = self._soup(html)
        return es_parse_episode_timeline(soup)

    def parse_resources(self, html: str) -> List[Dict[str, Any]]:
        soup = self._soup(html)
        return es_parse_resources(soup)

    def parse_sponsors(self, html: str) -> List[Dict[str, Any]]:
        soup = self._soup(html)
        return es_parse_sponsors(soup)

    def parse_major_summary(self, html: str) -> Dict[str, Any]:
        soup = self._soup(html)
        return es_parse_major_summary(soup)

    async def parse_all_except_transcript(self, url: str) -> Dict[str, Any]:
        """Fetch HTML and return all parsed parts as a dictionary."""
        html = await self._fetch_html(url)
        return {
            
            #url on Transcript there is also episode_number 
            "timeline": self.parse_timeline(html),
            "resources": self.parse_resources(html), 
            #Resource connected to webpage_resources Resource field url 
            "major_summary": self.parse_major_summary(html), 
            #webpage_summary 
            "sponsors": self.parse_sponsors(html), 
            #sponsors Will become Business later on if deemed. 
        }   
    
    async def parse_all(self, url: str) -> Dict[str, Any]:
        """Fetch HTML and return all parsed parts as a dictionary."""
        html = await self._fetch_html(url)
        return {
            "transcript_link": self.parse_transcript_link(html), 
            **(await self.parse_all_except_transcript(url))
        }
    
    



def _guess_title(text: Optional[str], url: str) -> Optional[str]:
    """
    Heuristic: if `text` is in the form 'Some Title : https://url', use the left side.
    Fallback to hostname when title can't be inferred.
    """
    if text:
        parts = text.split(" : ", 1)
        if parts and parts[0].strip():
            return parts[0].strip()
    try:
        host = urlparse(url).netloc
        return host or None
    except Exception:
        return None


def _normalize_resource_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Accepts a parser payload and returns a normalized list of items like:
      {"text": "... : https://example.com", "links": ["https://example.com"]}

    Adjust the keys if your parser uses a different one (e.g., "webpage_resources").
    """
    if not data:
        return []
    maybe_lists = [
        data.get("resources"),
        data.get("webpage_resources"),
        data.get("references"),
    ]
    for lst in maybe_lists:
        if isinstance(lst, list):
            return lst
    return []


async def _upsert_resources_from_items(
    items: Iterable[Dict[str, Any]]
) -> List["Resource"]:
    """
    Build/return Resource documents by URL (dedup by URL).
    If a Resource already exists, keep it; if new, create it.
    Update missing titles when we can infer one.
    """
    # Collect candidate URLs with titles
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

    # Prefetch existing in one query
    existing = await Resource.find(Resource.url.in_(urls)).to_list()
    existing_by_url = {r.url: r for r in existing}

    result: List[Resource] = []

    # Create new or update missing title
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





async def update_all_episodes(_: Any) -> None:
    """
    Streams episodes that have an episode_page_url.
    For each episode:
      - parse page
      - update Episode.webpage_summary (from minor_summary)
      - update Episode.sponsors (array of objects)
      - upsert/link Resource docs from parsed resource items
      - update Transcript.timeline (array of objects)
    """
    parser = WebpageEpisodeParse()

    # Stream instead of materializing the whole list.
    # fetch_links=True so `episode.transcript` is the populated Transcript doc (if present)
    async for episode in Episode.find(Episode.episode_page_url.exists(True), fetch_links=True):
        try:
            # Require a transcript link/doc to update its timeline
            if not episode.transcript:
                continue

            ep_url = episode.episode_page_url
            if not ep_url:
                continue

            data = await parser.parse_all(ep_url)
            if not data:
                continue

            # ---- extract parsed fields safely
            major = data.get("major_summary") or {}
            minor_summary: Optional[str] = major.get("minor_summary")

            sponsors: List[Dict[str, Any]] = data.get("sponsors") or []
            timeline: List[Dict[str, Any]] = data.get("timeline") or []

            resource_items = _normalize_resource_items(data)
            resources = await _upsert_resources_from_items(resource_items)

            # ---- update Episode
            if minor_summary:
                # per your note: put minor_summary into webpage_summary (you'll rewire later)
                episode.webpage_summary = minor_summary

            # sponsors is an array of objects
            if sponsors:
                episode.sponsors = sponsors

            # link Resource docs (your field allows Link[Resource] or legacy str)
            if resources:
                episode.webpage_resources = resources  # type: ignore[assignment]

            await episode.save()

            # ---- update Transcript timeline
            tr: Optional[Transcript] = episode.transcript  # already populated via fetch_links=True
            if tr and timeline:
                tr.timeline = timeline
                await tr.save()

        except Exception as e:
            # Keep the loop going; you might also want to log this or push to an "errors" array on the episode
            print(f"[update_all_episodes] Failed for episode {getattr(episode, 'id', None)}: {e}")
            continue




if __name__ == "__main__": 
    print("Importing webpage_ep_parsing.py")
    # asyncio.run(main()) 

    # asyncio.run(ingest_every_episode()) 