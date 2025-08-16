from src.mongo_schemas import init_beanie_with_pymongo, Episode, Channel    
from src.config.mongo_setup import get_async_mongo_client 
import asyncio 
from bson import ObjectId 






async def main(): 
    client = await init_beanie_with_pymongo()  

    # Get the Human Upgrade Podcast channel
    channel = await Channel.find_one({"name": "Human Upgrade Podcast"})
    if channel is None:
        # Try by ObjectId if name doesn't work
        channel = await Channel.get(ObjectId("689653f27af011efb67d982f"))
    
    if channel is None:
        print("Could not find Human Upgrade Podcast channel")
        return

    db = client.biohack_agent 
    existing_collection = db.episode_urls 

    existing_episodes = await existing_collection.find().to_list(length=None)  

    for episode in existing_episodes:    
        episode_number = episode.get("episode_number")   
        episode_url = episode.get("episode_url")
        transcript_url = episode.get("transcript_url")

        if episode_number is None or episode_url is None: 
            continue 

        # Check if episode already exists
        existing_episode = await Episode.find_one({"episode_page_url": episode_url})

        if existing_episode is None:
            # Create new Episode using Beanie
            new_episode = Episode(
                channel=channel,
                episode_page_url=episode_url,
                transcript_url=transcript_url,
                episode_number=episode_number
            )
            await new_episode.insert()
            print(f"Created new episode {episode_number}")
        else:
            # Update existing episode
            existing_episode.transcript_url = transcript_url
            existing_episode.episode_number = episode_number
            existing_episode.channel = channel
            await existing_episode.save()
            print(f"Updated existing episode {episode_number}")


async def migrate_episode_ids_to_objectid() -> None:
    """Migrate all documents in the episodes collection to have BSON ObjectId _id.

    For any document whose _id is not an ObjectId (e.g., int or str), this will:
    - Create a new document with the same fields and a fresh ObjectId (or reuse the string if it's a valid 24-char hex ObjectId)
    - Insert the new document
    - Delete the original document

    Note: This does not update references in other collections.
    """
    client = await init_beanie_with_pymongo()

    db = client.biohack_agent
    episodes = db["episodes"]

    all_docs = await episodes.find({}).to_list(length=None)

    migrated = 0
    skipped = 0
    mappings = []  # list of tuples (old_id, new_id)

    for doc in all_docs:
        old_id = doc.get("_id")
        # Skip if already a proper ObjectId
        if isinstance(old_id, ObjectId):
            skipped += 1
            continue

        # Choose a new ObjectId
        try:
            if isinstance(old_id, str):
                # Reuse if convertible to ObjectId; else generate
                new_oid = ObjectId(old_id)
            else:
                new_oid = ObjectId()
        except Exception:
            new_oid = ObjectId()

        # Clone doc without _id
        payload = {k: v for k, v in doc.items() if k != "_id"}

        try:
            await episodes.insert_one({"_id": new_oid, **payload})
            await episodes.delete_one({"_id": old_id})
            migrated += 1
            mappings.append((old_id, new_oid))
        except Exception as e:
            print(f"❌ Failed to migrate episode _id={old_id}: {e}")

    print(f"✅ Episodes already ObjectId (skipped): {skipped}")
    print(f"🛠️ Episodes migrated to ObjectId: {migrated}")
    if mappings:
        print("🔁 Old -> New _id mappings:")
        for old_id, new_id in mappings:
            print(f"  {old_id} -> {new_id}")

    try:
        await client.close()
    except Exception:
        pass 


async def fix_missing_episode_numbers():
    """Fix episodes that are missing episode_number by matching URLs."""
    client = await get_async_mongo_client()
    db = client.biohack_agent
    episodes_coll = db["episodes"]
    episode_urls_coll = db["episode_urls"]

    # Find episodes without episode_number
    episodes_without_number = await episodes_coll.find({
        "$or": [
            {"episode_number": {"$exists": False}},
            {"episode_number": None}
        ]
    }).to_list(length=None)

    print(f"Found {len(episodes_without_number)} episodes missing episode_number")

    # Get all episode_urls for mapping
    all_episode_urls = await episode_urls_coll.find({}).to_list(length=None)
    
    # Create mapping from episode_url to episode_number
    url_to_number = {}
    for url_doc in all_episode_urls:
        episode_url = url_doc.get("episode_url")
        episode_number = url_doc.get("episode_number")
        if episode_url and episode_number is not None:
            url_to_number[episode_url] = episode_number

    print(f"Found {len(url_to_number)} episode URLs with numbers")

    updated = 0
    not_found = 0

    for episode in episodes_without_number:
        episode_page_url = episode.get("episode_page_url")
        episode_id = episode.get("_id")
        
        if not episode_page_url:
            print(f"❌ Episode {episode_id} has no episode_page_url")
            not_found += 1
            continue

        # Find matching episode_number
        episode_number = url_to_number.get(episode_page_url)
        
        if episode_number is not None:
            try:
                await episodes_coll.update_one(
                    {"_id": episode_id},
                    {"$set": {"episode_number": episode_number}}
                )
                print(f"✅ Updated episode {episode_id} with episode_number {episode_number}")
                updated += 1
            except Exception as e:
                print(f"❌ Failed to update episode {episode_id}: {e}")
                not_found += 1
        else:
            print(f"❌ No matching episode_number found for URL: {episode_page_url}")
            not_found += 1

    print(f"✅ Successfully updated {updated} episodes with episode_numbers")
    print(f"❌ Could not find episode_numbers for {not_found} episodes")

    try:
        await client.close()
    except Exception:
        pass


if __name__ == "__main__": 
    # asyncio.run(migrate_episode_ids_to_objectid()) 

    # asyncio.run(fix_missing_episode_numbers()) 

    pass 
