from src.mongo_schemas import EpisodeSchema, EpisodeTranscriptSchema
import asyncio 
import sys
import os
from datetime import datetime 
from src.config.mongo_setup import get_async_mongo_client  
import pandas as pd 
from src.transcript_parser import EpisodeParser  





async def insert_episode_from_parser():
    """Insert episode using data from the webpage parser"""
    # Get Async Mongo Client
    client = await get_async_mongo_client()
    db = client["biohack_agent"]
    collection = db["episodes"]

    try:
        # Parse episode data from HTML file
        print("📄 Parsing episode data from webpage.html...")
        episode_data = parse_episode_from_file('webpage.html')
        
        print("✅ Episode data parsed successfully!")
        print(f"Episode: {episode_data.get('episode_number')} - {episode_data.get('title')}")
        
        # ✅ Validate with Pydantic
        print("🔍 Validating data with MongoDB schema...")
        episode = EpisodeSchema(**episode_data)
        print("✅ Schema validation passed!")

        # Convert Pydantic model to dict
        mongo_doc = episode.model_dump()
        
        # ✅ Insert into MongoDB
        print("💾 Inserting into MongoDB...")
        insert_result = await collection.insert_one(mongo_doc)  
        print(f"✅ Inserted episode ID: {insert_result.inserted_id}")

        # ✅ Fetch and print inserted document summary
        inserted_doc = await collection.find_one({"_id": insert_result.inserted_id})
        print("\n📄 Inserted Document Summary:")
        print(f"  Episode: {inserted_doc.get('episode_number')} - {inserted_doc.get('title')}")
        print(f"  Slug: {inserted_doc.get('slug')}")
        print(f"  Guest: {inserted_doc.get('guest', {}).get('name', 'No guest')}")
        print(f"  Transcript: {inserted_doc.get('transcript', {}).get('status')}")
        print(f"  Key takeaways: {len(inserted_doc.get('key_takeaways', []))}")
        print(f"  Sponsors: {len(inserted_doc.get('sponsors', []))}")
        print(f"  Resources: {len(inserted_doc.get('resources', []))}")
        print(f"  Timestamps: {len(inserted_doc.get('timestamps', []))}")

        # ✅ Delete the inserted document
        delete_result = await collection.delete_one({"_id": insert_result.inserted_id})
        print(f"\n🗑 Deleted {delete_result.deleted_count} document(s)")

    except FileNotFoundError:
        print("❌ Error: webpage.html file not found. Please make sure it exists in the current directory.")
    except Exception as e:
        print(f"❌ Error during insertion: {str(e)}")
    finally:
        # Close the client
        await client.close()
    

async def main():
    await insert_episode_from_parser() 


async def insert_episode_urls_only(episode_urls): 
    for i, episode_url in episode_urls: 
        print(f"Inserting episode {i + 1} - of episode: {episode_url} into episodes ")  


async def insert_episode_urls_only(csv_file_path): 
    client = await get_async_mongo_client()
    db = client["biohack_agent"]
    collection = db["episode_urls"]  

    await collection.delete_many({})  


    
    # Read episode URLs from CSV
    episode_urls = []  

    try:  
        episode_urls = pd.read_csv(csv_file_path)  

        only_urls = episode_urls["episode_url"].tolist()   
        episode_numbers = episode_urls["episode_number"].tolist()  

        for url, episode_number in zip(only_urls, episode_numbers): 
            print(f"Inserting episode {url} into episode_urls") 
            episode_transcript_schema = EpisodeTranscriptSchema(episode_url=url, episode_number=episode_number) 
            insert_result = await collection.insert_one(episode_transcript_schema.model_dump()) 
            print(f"Inserted episode {url} into episode_urls") 
            
            
            



    except Exception as e:  
        print(f"Error inserting episode URLs: {e}") 
    


        

if __name__ == "__main__": 
    asyncio.run(insert_episode_urls_only("sorted_episodes.csv")) 
    # asyncio.run(main()) 