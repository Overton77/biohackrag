from src.mongo_schemas import EpisodeSchema 
import asyncio 
from datetime import datetime 
from src.config.mongo_setup import get_async_mongo_client 
import urllib  
import os  
import pandas as pd 


async def insert_episode():
    # Get Async Mongo Client
    client = await get_async_mongo_client()
    db = client["biohack_agent"]
    collection = db["episodes"]

    # Prepare complete episode data (with podcast fields)
    episode_data = {
        "podcast_name": "The Human Upgrade with Dave Asprey",
        "podcast_url": "https://daveasprey.com/",
        "podcast_description": "Biohacking tips, expert interviews, and science-backed methods for better performance and health.",
        "podcast_owner": "Dave Asprey",
        "episode_number": 1301,
        "title": "E.W.O.T: Exercise With Oxygen Therapy",
        "slug": "1301-ewot",
        "summary": {
            "short_summary": "Learn about oxygen therapy for performance",
            "detailed_summary": "In-depth discussion on EWOT and its benefits."
        },
        "guest": {"name": "Guest Name", "title": "Biohacker", "bio": None},
        "sponsors": [{"name": "Upgrade Labs", "url": "https://upgradelabs.com"}],
        "resources": [{"title": "EWOT Device", "url": "https://resource-link.com"}],
        "transcript": {"download_url": "https://transcript-link.com", "status": "pending"},
        "timestamps": [{"time": "00:01:00", "topic": "Introduction"}],
        "date_published": datetime.now(),
        "episode_url": "https://daveasprey.com/1301-ewot/",
        "podcast_subscription_url": "https://daveasprey.com/subscribe/"
    }

    # ✅ Validate with Pydantic
    episode = EpisodeSchema(**episode_data)

    # Convert Pydantic model to dict and ensure URLs are strings
    mongo_doc = episode.model_dump()
    # Convert HttpUrl fields to strings
    mongo_doc["podcast_url"] = str(mongo_doc["podcast_url"])
    mongo_doc["episode_url"] = str(mongo_doc["episode_url"])
    mongo_doc["podcast_subscription_url"] = str(mongo_doc["podcast_subscription_url"])

    # ✅ Insert into MongoDB
    insert_result = await collection.insert_one(mongo_doc)  
    print("Insert result:", insert_result)
    print(f"✅ Inserted episode ID: {insert_result.inserted_id}")

    # ✅ Fetch and print inserted document
    inserted_doc = await collection.find_one({"_id": insert_result.inserted_id})
    print("\n📄 Inserted Document:")
    print(inserted_doc)

    # ✅ Delete the inserted document
    delete_result = await collection.delete_one({"_id": insert_result.inserted_id})
    print(f"\n🗑 Deleted {delete_result.deleted_count} document(s)")

async def main():
    await insert_episode() 


async def insert_episode_urls_only(episode_urls): 
    for i, episode_url in episode_urls: 
        print(f"Inserting episode {i + 1} - of episode: {episode_url} into episodes ") 

        

if __name__ == "__main__":
    