from config.mongo_setup import get_async_mongo_client 
import asyncio 



async def get_mongo_schema_output():  

    client = await get_async_mongo_client()  
    db = client.biohack_agent  
    episodes = db.episodes 
    transcripts = db.transcripts 
    resources = db.resources  

    # Get collection schemas
    episode_schema = await episodes.find_one()
    transcript_schema = await transcripts.find_one()
    resource_schema = await resources.find_one()

    # Print schemas
    print("\nEpisode Schema:")
    for field, value in episode_schema.items():
        print(f"{field}: {type(value)}")

    print("\nTranscript Schema:") 
    for field, value in transcript_schema.items():
        print(f"{field}: {type(value)}")

    print("\nResource Schema:")
    for field, value in resource_schema.items():
        print(f"{field}: {type(value)}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(get_mongo_schema_output())