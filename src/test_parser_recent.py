from src.transcript_parser import EpisodeParser 
from src.config.mongo_setup import get_async_mongo_client  
from src.async_playwright_scraper import get_episode_html_playwright
import aiohttp 
import asyncio 


async def get_episode_html_aiohttp(episode_url: str): 
    """Get HTML using aiohttp (no JavaScript) - for comparison"""
    async with aiohttp.ClientSession() as session: 
        async with session.get(episode_url) as response:  
            response_text = await response.text()  
            print(f"aiohttp HTML length: {len(response_text)}")
            return response_text

async def get_episode_html(episode_url: str):
    """Get HTML using Playwright (with JavaScript) - recommended"""
    html_content = await get_episode_html_playwright(episode_url)
    print(f"Playwright HTML length: {len(html_content)}")
    return html_content 

async def test_parser_recent(): 
    client = await get_async_mongo_client() 
    db = client["biohack_agent"] 
    collection = db["episode_urls"]  


    # Motor cursors don't need await on the find() itself, but on iteration
    cursor = collection.find().sort("episode_number", -1).limit(10)
    
    # Iterate directly over the cursor (async iteration)
    async for episode in cursor:  

        if episode["episode_number"] == 1333: 
           

            html_content = await get_episode_html(episode["episode_url"]) 
            episode_parser = EpisodeParser(html_content) 
            episode_data = episode_parser.parse_full_episode() 
            print("Episode data\n\n") 
            print("Inspect carefully")  
            print(episode_data)

        

    
    
    


if __name__ == "__main__": 
    asyncio.run(test_parser_recent()) 





