from src.config.mongo_setup import get_async_mongo_client 


async def get_recent_data(): 
    client = await get_async_mongo_client()   
    db = client.biohack_agent   
    episodes_collection = db.episodes
    transcripts_collection = db.transcripts
    
    sorted_episodes = await episodes_collection.find().sort("episode_number", -1).limit(200).to_list(length=None) 
    
    count = 0
    for episode in sorted_episodes: 
        transcript_id = episode.get("transcript")
        if transcript_id:  # Only process if transcript exists
            # Fetch the transcript document using the ObjectId
            transcript = await transcripts_collection.find_one({"_id": transcript_id})
            if transcript:
                timeline = transcript.get("timeline")
                if timeline:  # Only print if timeline exists and is not empty
                    count += 1
                    episode_number = episode.get("episode_number", "Unknown")
                    print(f"\n{'='*60}")
                    print(f"Episode {episode_number} - Timeline:")
                    print(f"{'='*60}")
                    
                    # Print timeline items
                    for item in timeline:
                        timestamp = item.get("time", "Unknown")
                        description = item.get("description", "")
                        print(f"[{timestamp}] {description}")
                    
                    print(f"{'='*60}")
    
    print(f"\nTotal episodes with timelines: {count} out of {len(sorted_episodes)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(get_recent_data())
