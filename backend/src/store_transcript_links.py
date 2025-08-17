import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from config.mongo_setup import get_async_mongo_client
from pymongo import AsyncMongoClient 


async def fetch_episode_html(url: str) -> str:
    """Fetch HTML content using aiohttp"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.text()


def extract_transcript_url_enhanced(html_content: str) -> str:
    """
    Enhanced transcript URL extraction with fallback mechanism
    
    Method 1: Text-based search for "Download a transcript of this show"
    Method 2: Regex pattern matching as fallback
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Method 1: Text-based extraction (PRIMARY)
    print("      🎯 Trying text-based method...")
    try:
        # Look for exact text match (case insensitive)
        span_element = soup.find('span', string=re.compile(r'Download a transcript of this show', re.IGNORECASE))
        
        if span_element:
            print("      ✅ Found target span element")
            
            # Look for the parent <a> tag
            a_tag = span_element.find_parent('a')
            if a_tag and a_tag.get('href'):
                transcript_url = a_tag['href']
                print(f"      ✅ SUCCESS (Text Method): {transcript_url}")
                return transcript_url
            
            # If no direct parent <a>, look in the containing element
            parent = span_element.parent
            if parent:
                a_tag = parent.find('a', href=True)
                if a_tag:
                    transcript_url = a_tag['href']
                    print(f"      ✅ SUCCESS (Text Method - Sibling): {transcript_url}")
                    return transcript_url
        
        # Alternative text search with broader pattern
        elements_with_text = soup.find_all(string=re.compile(r'Download.*transcript.*show', re.IGNORECASE))
        for element in elements_with_text:
            parent = element.parent
            while parent and parent.name != 'html':
                if parent.name == 'a' and parent.get('href'):
                    transcript_url = parent['href']
                    print(f"      ✅ SUCCESS (Text Method - Broad Search): {transcript_url}")
                    return transcript_url
                parent = parent.parent
        
        print("      ⚠️ Text method found no results, trying fallback...")
        
    except Exception as e:
        print(f"      ⚠️ Text method error: {e}, trying fallback...")
    
    # Method 2: Regex pattern fallback (FALLBACK)
    print("      🔄 Trying regex fallback method...")
    try:
        transcript_pattern = re.compile(r'https://daveasprey\.com/wp-content/uploads/.*[Tt]ranscript.*\.html')
        links = soup.find_all('a', href=transcript_pattern)
        
        if links:
            transcript_url = links[0]['href']
            print(f"      ✅ SUCCESS (Regex Fallback): {transcript_url}")
            return transcript_url
        else:
            print("      ❌ Regex fallback found no results")
            
    except Exception as e:
        print(f"      ❌ Regex fallback error: {e}")
    
    print("      ❌ All methods failed - no transcript URL found")
    return None


async def get_episodes_missing_transcripts(async_mongo_client: AsyncMongoClient, limit: int = None):
    """
    Get all episodes where transcript_url is null or missing
    
    Args:
        limit: Optional limit for number of episodes (if None, gets ALL episodes)
    """
    
    
    try:
        db = async_mongo_client.biohack_agent
        collection = db.episodes 
        
        # Find episodes where transcript_url is null, empty, or doesn't exist
        query = {
            "$or": [
                {"transcript_url": None},
                {"transcript_url": {"$exists": False}},
                {"transcript_url": ""},
                {"transcript_url": {"$in": [None, "", " "]}}
            ]
        }
        
        cursor = collection.find(query).sort("episode_number", -1)
        
        if limit:
            cursor = cursor.limit(limit)
            episodes = await cursor.to_list(length=limit)
        else:
            episodes = await cursor.to_list(length=None)
        
        print(f"📥 Found {len(episodes)} episodes missing transcript URLs")
        if limit:
            print(f"   (Limited to {limit} episodes)")
        else:
            print(f"   (ALL episodes in collection)")
        
        return episodes
    
    except Exception as e:
        print(f"❌ Error finding episodes with missing transcripts: {e}")
        return []



async def update_episode_transcript(async_mongo_client: AsyncMongoClient, episode_doc: dict, transcript_url: str):
    """Update episode document with transcript URL"""
    episode_id = episode_doc.get('_id')
    episode_number = episode_doc.get('episode_number', 'Unknown')
    
        
    try:
        db = async_mongo_client.biohack_agent
        collection = db.episodes 
    
        
        # Update the specific episode document with the transcript URL
        result = await collection.update_one(
            {"_id": episode_id},
            {"$set": {"transcript_url": transcript_url}}
        )
        
        if result.modified_count > 0:
            print(f"      💾 ✅ Successfully updated episode {episode_number}")
            return True
        elif result.matched_count > 0:
            print(f"      ⚠️ Document found but transcript_url was already the same")
            return True
        else:
            print(f"      ❌ No document found with _id: {episode_id}")
            return False
            
    except Exception as e:
        print(f"      ❌ Error updating episode {episode_number}: {e}")
        return False
        

async def process_single_episode(async_mongo_client: AsyncMongoClient, episode_data: dict, episode_index: int, total_count: int):
    """Process a single episode to extract and store transcript URL"""
    
    episode_number = episode_data.get('episode_number', 'Unknown')
    episode_url = episode_data.get('episode_page_url', '')
    
    print(f"\n🎯 Episode {episode_index + 1}/{total_count} - Episode #{episode_number}")
    print(f"   URL: {episode_url}")
    print("-" * 80)
    
    if not episode_url:
        print("   ❌ No episode URL found")
        return False
    
    try:
        # Fetch HTML content
        print("   📄 Fetching episode HTML...")
        html_content = await fetch_episode_html(episode_url)
        print(f"   ✅ Got HTML content ({len(html_content):,} characters)")
        
        # Extract transcript URL using enhanced method with fallback
        print("   🔍 Extracting transcript URL (with fallback)...")
        transcript_url = extract_transcript_url_enhanced(html_content)
        
        if transcript_url:
            # Update MongoDB document
            print("   💾 Updating MongoDB...")
            success = await update_episode_transcript(async_mongo_client, episode_data, transcript_url)
            return success
        else:
            print("   ❌ No transcript URL found with any method")
            return False
            
    except Exception as e:
        print(f"   ❌ Error processing episode {episode_number}: {e}")
        return False


async def process_all_missing_transcripts(async_mongo_client: AsyncMongoClient, limit: int = None):
    """
    Process ALL episodes with missing transcript URLs using enhanced extraction
    
    Args:
        limit: Optional limit for number of episodes to process (if None, processes ALL)
    """
    
    print("🚀 COMPREHENSIVE TRANSCRIPT URL EXTRACTION")
    print("=" * 80)
    print("🎯 Target: Episodes with missing transcript URLs")
    print("🔧 Method: Enhanced extraction with text + regex fallback")
    print("=" * 80)
    
    # Get all episodes with missing transcript URLs
    episodes = await get_episodes_missing_transcripts(async_mongo_client, limit)
    
    if not episodes:
        print("✅ No episodes with missing transcript URLs found!")
        print("   All episodes already have transcript URLs.")
        return
    
    # Process each episode
    success_count = 0
    total_count = len(episodes)
    
    print(f"\n📋 Processing {total_count} episodes...")
    
    for i, episode in enumerate(episodes):
        success = await process_single_episode(async_mongo_client, episode, i, total_count)
        if success:
            success_count += 1
        
        # Add a small delay to be nice to the server
        await asyncio.sleep(0.5)
    
    # Final summary
    print("\n" + "=" * 80)
    print("📋 FINAL SUMMARY")
    print("=" * 80)
    print(f"Total episodes processed: {total_count}")
    print(f"Transcript URLs found and stored: {success_count}")
    print(f"Success rate: {success_count/total_count*100:.1f}%")
    print(f"Failed to find transcripts: {total_count - success_count}")
    
    if success_count > 0:
        print(f"\n✅ Successfully found {success_count} transcript URLs!")
        print("   Enhanced method with fallback was effective.")
    
    if total_count - success_count > 0:
        print(f"\n⚠️ {total_count - success_count} episodes still missing transcripts.")
        print("   These episodes may not have transcript downloads available.")


async def verify_transcript_coverage():
    """Verify how many episodes now have transcript URLs"""
    
    print("\n🔍 VERIFYING TRANSCRIPT COVERAGE")
    print("=" * 50)
    
    client = await get_async_mongo_client()
    if client is None:
        print("❌ Failed to get MongoDB client for verification")
        return
        
    try:
        db = client["biohack_agent"]
        collection = db["episode_urls"]
        
        # Count total episodes
        total_episodes = await collection.count_documents({})
        
        # Count episodes with transcript URLs
        episodes_with_transcripts = await collection.count_documents({
            "transcript_url": {"$exists": True, "$ne": None, "$ne": ""}
        })
        
        # Count episodes still missing transcripts
        episodes_missing = await collection.count_documents({
            "$or": [
                {"transcript_url": None},
                {"transcript_url": {"$exists": False}},
                {"transcript_url": ""}
            ]
        })
        
        print(f"Total episodes in collection: {total_episodes}")
        print(f"Episodes with transcript URLs: {episodes_with_transcripts}")
        print(f"Episodes missing transcript URLs: {episodes_missing}")
        print(f"Coverage: {episodes_with_transcripts/total_episodes*100:.1f}%")
        
    finally:
        if client:
            await client.close()


async def main():
    """Main function - Process all episodes missing transcript URLs"""
    # Process ALL episodes with missing transcript URLs (no limit)
    await process_all_missing_transcripts()
    
    # Verify final coverage
    # await verify_transcript_coverage()


if __name__ == "__main__":
    print("Importing store_transcript_links")