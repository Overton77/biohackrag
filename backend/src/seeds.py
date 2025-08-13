from src.mongo_schemas import init_beanie_with_pymongo,  Person,  Channel, Episode  
import asyncio 


async def seed_from_episode_urls(): 
    async_mongo_client = await init_beanie_with_pymongo()   

    asprey = await Person( 
        name = "Dave Asprey", 
        type = "biohacker", 
    ).insert() 

    channel = await Channel( 
        name = "Human Upgrade Podcast", 
        owner = asprey, 
    ).insert()   

    # Create episodes from the latest episode_urls
    created_count = await create_episodes_from_urls(async_mongo_client, channel, limit=20)
    
    print(f"Inserted {created_count} episodes")
    await async_mongo_client.close() 



async def create_episodes_from_urls(async_mongo_client, channel: Channel, limit: int = 20) -> int:
    """Read top N episode_urls (by episode_number desc) and insert Episode docs."""
    db = async_mongo_client.biohack_agent
    episode_url_collection = db["episode_urls"]

    created = 0
    # Use async cursor to avoid to_list issues
    cursor = episode_url_collection.find().sort("episode_number", -1).limit(limit)
    async for episode_url in cursor:
        await Episode(
            channel=channel,
            episode_page_url=episode_url.get("episode_url"),
            transcript_url=episode_url.get("transcript_url"),
        ).insert()
        created += 1

    return created


if __name__ == "__main__": 
    asyncio.run(seed_from_episode_urls()) 