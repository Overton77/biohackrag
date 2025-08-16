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
    
    




async def main(): 
    import json  
    parser = WebpageEpisodeParse()
    data = await parser.parse_all("https://daveasprey.com/1303-nayan-patel/") 
    print("\n\n")
    
    print("=== FULL DATA ===")
    print(json.dumps(data, indent=4))
    
    print("\n=== TIMELINE ===")
    print(json.dumps(data.get("timeline"), indent=4))
    
    print("\n=== RESOURCES ===")
    print(json.dumps(data.get("resources"), indent=4))
    
    print("\n=== MAJOR SUMMARY ===")
    print(json.dumps(data.get("major_summary"), indent=4))
    
    print("\n=== SPONSORS ===")
    print(json.dumps(data.get("sponsors"), indent=4))
    
    print("\n=== TRANSCRIPT LINK ===")
    print(json.dumps(data.get("transcript_link"), indent=4))  

    print("\n=== MINOR SUMMARY ===")
    print(data.get("major_summary").get("minor_summary"))


   
async def _normalize_episode_webpage_resources(ep_coll, res_coll, episode_id: ObjectId) -> None:
    """Fix episodes where `webpage_resources` mistakenly stores URLs instead of ObjectIds.

    - For each string URL, create/find a Resource doc and replace with its ObjectId
    - Leaves existing ObjectIds intact
    """
    doc = await ep_coll.find_one({"_id": episode_id})
    if not doc:
        return
    wr = doc.get("webpage_resources")
    if not isinstance(wr, list):
        return

    new_ids: List[ObjectId] = []
    for item in wr:
        if isinstance(item, ObjectId):
            new_ids.append(item)
        elif isinstance(item, str):
            url = item
            if not url:
                continue
            existing = await res_coll.find_one({"url": url})
            if existing:
                new_ids.append(existing["_id"])
            else:
                ins = await res_coll.insert_one({"url": url})
                new_ids.append(ins.inserted_id)
        elif isinstance(item, dict):
            url = item.get("url")
            if not url:
                continue
            existing = await res_coll.find_one({"url": url})
            if existing:
                new_ids.append(existing["_id"])
            else:
                ins = await res_coll.insert_one({"url": url})
                new_ids.append(ins.inserted_id)

    await ep_coll.update_one({"_id": episode_id}, {"$set": {"webpage_resources": new_ids}})



async def upsert_ingestion() -> None:
    # Initialize ODM and raw collections (for data normalization)
    client = await init_beanie_with_pymongo()  


     




if __name__ == "__main__":
    asyncio.run(main()) 

    # asyncio.run(ingest_every_episode()) 