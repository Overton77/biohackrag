from config.mongo_setup import get_async_mongo_client  
import re   
import asyncio  


def extract_episode_number(url: str) -> str: 
    match = re.search(r"/(\d+)-", url)
    if match:
        return match.group(1)  # -> 1297
    return None 

async def update_episode_numbers(): 
    client = await get_async_mongo_client()  

    db = client.biohack_agent  

    episodes = db.episodes 

    all_episodes = await episodes.find({"episode_number": {"$exists": True}}).to_list(length=None)   


    for episode in all_episodes:  
        episode_url = episode.get("episode_page_url") 

        if episode_url is None:  
            continue  
        
        episode_number = extract_episode_number(episode_url) 
        
        if episode_number is None: 
            continue  

        if episode_number == episode.get("episode_number"): 
            continue 
        
        await episodes.update_one({"_id": episode.get("_id")}, {"$set": {"episode_number": episode_number}})  

async def main(): 
    await update_episode_numbers() 


if __name__ == "__main__": 
    print("Fast update file")




