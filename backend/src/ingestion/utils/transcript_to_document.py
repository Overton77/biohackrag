import aiohttp as aio  
from config.mongo_setup import get_async_mongo_client  
import re   
from bs4 import BeautifulSoup    
import asyncio   
from typing import Optional


DEFAULT_HEADERS = {
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

async def fetch_url_async(url: str, headers: Optional[dict] = None, timeout_s: int = 30) -> str:
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    timeout = aio.ClientTimeout(total=timeout_s)
    async with aio.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=merged_headers, allow_redirects=True) as response:
            text = await response.text()
            if response.status in (403, 406) and "Forbidden" in text:
                raise PermissionError(f"Blocked with status {response.status}")
            return text
        


async def get_transcript_url(episode_number: int) -> str: 
    client = await get_async_mongo_client() 
    if not client: 
        raise Exception("Failed to connect to MongoDB") 
    
    db = client["biohack_agent"] 
    collection = db["episode_urls"]  


    episode = await collection.find_one({"episode_number": episode_number})  
    if not episode: 
        raise Exception(f"Episode {episode_number} not found")  
    
    print(episode["transcript_url"])
    
    return episode["transcript_url"] 



async def clean_transcript(transcript_url: str) -> str:
    try:
        html_content = await fetch_url_async(transcript_url)
    except PermissionError:
        try:
            from async_playwright_scraper import get_episode_html_playwright
        except Exception:
            raise
        html_content = await get_episode_html_playwright(transcript_url)
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text()
    text = re.sub(r"\s+", " ", text)
    return text.strip()  


async def get_transcript_document(episode_number: int) -> str: 
    transcript_url = await get_transcript_url(episode_number) 
    transcript_text = await clean_transcript(transcript_url) 
    return transcript_text   

async def retrieve_transcript_documents(episode_numbers: list[int]) -> list[str]: 
    tasks = [get_transcript_document(episode_number) for episode_number in episode_numbers] 
    return await asyncio.gather(*tasks) 


async def main(): 
    transcript_text = await get_transcript_document(1333) 
    print(transcript_text) 
    
if __name__ == "__main__":  
    print("Importing transcript_to_document.py")
    # asyncio.run(main()) 
    
    





