from typing import Any, Dict, List, Optional, Iterable, Union
import aiohttp
from bs4 import BeautifulSoup  
from urllib.parse import urlparse   
from pydantic import BaseModel  

from config.settings import get_settings   
from src.mongo_schema_overwrite import Episode, Transcript, Resource, Person  
from src.store_transcript_links import extract_transcript_url_enhanced 
from firecrawl import AsyncFirecrawl  
from config.firecrawl_client import firecrawl  
from config.mongo_setup import init_beanie_with_pymongo 

# Reuse the robust parsers implemented elsewhere
from .episode_summaries import (
    parse_episode_timeline as es_parse_episode_timeline,
    parse_resources as es_parse_resources,
    parse_major_summary as es_parse_major_summary,
    parse_sponsors as es_parse_sponsors, 
    extract_episode_number as es_extract_episode_number,
    parse_youtube_embed_url as es_parse_youtube_embed_url,
)  
import asyncio  
from beanie.odm.operators.find.element import Exists 

settings = get_settings()   


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

    def __init__(self, session: Optional[aiohttp.ClientSession] = None, timeout_s: int = 30, firecrawl_client: Optional[AsyncFirecrawl] = None) -> None:
        self._session = session
        self._timeout_s = timeout_s 
        # Default to the shared client if none provided
        self._firecrawl_client = firecrawl_client or firecrawl

    async def _fetch_html(self, url: str) -> str:
        headers = settings.web_fetch_headers
        if self._session is not None:
            async with self._session.get(url, headers=headers, allow_redirects=True) as response:
                return await response.text()
        timeout = aiohttp.ClientTimeout(total=self._timeout_s)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, allow_redirects=True) as response:
                return await response.text() 
            
    async def _get_guest_name(self, url: str) -> Optional[str]:   
        class GuestName(BaseModel): 
            guest_name: str  

        if self._firecrawl_client is None:
            return None

        prompt = "Extract the guest name of the episode. The guest name is the name of the person who is the guest of the episode"
        try:
            res = await self._firecrawl_client.extract( 
                urls=[url], 
                prompt=prompt, 
                schema=GuestName.model_json_schema(),   
            ) 
            if res.success: 
                data = res.data 
                if isinstance(data, dict):
                    return data.get("guest_name") 
            else: 
                print(f"Error getting guest name: {res.error}")
                return None 
        except Exception as e:
            print(f"Error getting guest name: {e}")
            return None

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
    
    def parse_episode_number(self, html: str) -> Optional[str]: 
        soup = self._soup(html) 
        return es_extract_episode_number(soup) 

    def parse_youtube(self, html: str) -> Dict[str, Optional[str]]:
        """Return embed URL, watch URL, and video id if present."""
        soup = self._soup(html)
        embed_url = es_parse_youtube_embed_url(soup)
        video_id: Optional[str] = None
        watch_url: Optional[str] = None
        if embed_url:
            # Typical format: https://www.youtube.com/embed/<video_id>
            try:
                video_id = embed_url.rstrip("/").split("/")[-1].split("?")[0]
                watch_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None
            except Exception:
                video_id = None
                watch_url = None
        return {
            "youtube_embed_url": embed_url,
            "youtube_watch_url": watch_url,
            "youtube_video_id": video_id,
        }

    async def parse_all_except_transcript(self, url: str) -> Dict[str, Any]:
        """Fetch HTML and return all parsed parts as a dictionary."""
        html = await self._fetch_html(url)
        youtube = self.parse_youtube(html)
        return {
            "timeline": self.parse_timeline(html),
            "resources": self.parse_resources(html), 
            "major_summary": self.parse_major_summary(html), 
            "sponsors": self.parse_sponsors(html), 
            "episode_number": self.parse_episode_number(html), 
            **youtube,
        }   
    
    async def parse_all(self, url: str) -> Dict[str, Any]:
        """Fetch HTML once and return all parsed parts as a dictionary."""
        html = await self._fetch_html(url)
        youtube = self.parse_youtube(html)
        major = self.parse_major_summary(html)
        return {
            "transcript_link": self.parse_transcript_link(html), 
            "guest_name": await self._get_guest_name(url), 
            "timeline": self.parse_timeline(html),
            "resources": self.parse_resources(html), 
            "major_summary": major, 
            "sponsors": self.parse_sponsors(html), 
            "episode_number": self.parse_episode_number(html), 
            **youtube,
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





async def update_episodes_guest_and_youtube() -> None:
    """
    Streams episodes that have an episode_page_url.
    For each episode:
      - parse page for guest_name and youtube fields only
      - upsert/link Person docs from guest_name
      - update Episode youtube fields (youtube_embed_url, youtube_watch_url, youtube_video_id)
    """  

    await init_beanie_with_pymongo()  
    parser = WebpageEpisodeParse()

    # Stream instead of materializing the whole list.
    # fetch_links=True so `episode.transcript` is the populated Transcript doc (if present)
    async for episode in Episode.find(Exists(Episode.episode_page_url, True), fetch_links=True):
        try:
            ep_url = episode.episode_page_url
            if not ep_url:
                continue

            data = await parser.parse_all(ep_url)
            if not data:
                continue

            # ---- extract parsed fields safely
            guest_name: Optional[str] = data.get("guest_name")    
            youtube_embed_url: Optional[str] = data.get("youtube_embed_url")
            youtube_watch_url: Optional[str] = data.get("youtube_watch_url")
            youtube_video_id: Optional[str] = data.get("youtube_video_id")

            # ---- upsert guest and attach to episode.guests
            if guest_name:
                person = await Person.find(Person.name == guest_name).first_or_none()
                if not person:
                    person = Person(name=guest_name)
                    await person.insert()
                if episode.guests is None:
                    episode.guests = [person]
                else:
                    # Avoid duplicates by id
                    existing_ids = {getattr(p, "id", None) for p in episode.guests}
                    if getattr(person, "id", None) not in existing_ids:
                        episode.guests.append(person)  # type: ignore[arg-type]

            # ---- update Episode youtube fields (single save at end)
            if youtube_embed_url:
                episode.youtube_embed_url = youtube_embed_url
            if youtube_watch_url:
                episode.youtube_watch_url = youtube_watch_url
            if youtube_video_id:
                episode.youtube_video_id = youtube_video_id

            await episode.save()

        except Exception as e:
            # Keep the loop going; you might also want to log this or push to an "errors" array on the episode
            print(f"[update_episodes_guest_and_youtube] Failed for episode {getattr(episode, 'id', None)}: {e}")
            continue


async def update_all_episodes(episodes_to_update: Union[List[Episode], None] = None) -> None:
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
    if episodes_to_update is None:  
        episodes = await Episode.find(Exists(Episode.episode_page_url, True), fetch_links=True).to_list()  
    else: 
        episodes = episodes_to_update  

    for episode in episodes:  
        try:
            ep_url = episode.episode_page_url
            if not ep_url:
                continue

            data = await parser.parse_all(ep_url)
            if not data:
                continue

            # ---- extract parsed fields safely
            major = data.get("major_summary") or {}
            minor_summary: Optional[str] = major.get("minor_summary") 
            guest_name: Optional[str] = data.get("guest_name")    
            episode_number_str: Optional[str] = data.get("episode_number")   
            sponsors: List[Dict[str, Any]] = data.get("sponsors") or []
            timeline: List[Dict[str, Any]] = data.get("timeline") or []
            transcript_link: Optional[str] = data.get("transcript_link")
            youtube_embed_url: Optional[str] = data.get("youtube_embed_url")
            youtube_watch_url: Optional[str] = data.get("youtube_watch_url")
            youtube_video_id: Optional[str] = data.get("youtube_video_id")
            resource_items = _normalize_resource_items(data)
            resources = await _upsert_resources_from_items(resource_items)

            # ---- upsert guest and attach to episode.guests
            if guest_name:
                person = await Person.find(Person.name == guest_name).first_or_none()
                if not person:
                    person = Person(name=guest_name)
                    await person.insert()
                if episode.guests is None:
                    episode.guests = [person]
                else:
                    # Avoid duplicates by id
                    existing_ids = {getattr(p, "id", None) for p in episode.guests}
                    if getattr(person, "id", None) not in existing_ids:
                        episode.guests.append(person)  # type: ignore[arg-type]

            # ---- update Episode fields (single save at end)
            if minor_summary:
                episode.webpage_summary = minor_summary
            if sponsors:
                episode.sponsors = sponsors 
            if timeline:
                episode.timeline = timeline
            if resources:
                episode.webpage_resources = resources  # type: ignore[assignment]
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

            await episode.save()

          

        except Exception as e:
            # Keep the loop going; you might also want to log this or push to an "errors" array on the episode
            print(f"[update_all_episodes] Failed for episode {getattr(episode, 'id', None)}: {e}")
            continue




async def run_one(episode_page_url: str): 

    parser = WebpageEpisodeParse() 
    data = await parser.parse_all(episode_page_url) 
    print(data) 





if __name__ == "__main__": 
    print("Importing webpage_ep_parsing.py")   

    # asyncio.run(run_one("https://daveasprey.com/1303-nayan-patel/"))
    asyncio.run(update_episodes_guest_and_youtube())

