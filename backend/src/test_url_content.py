import asyncio
import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import os
from datetime import datetime
from src.config.mongo_setup import get_async_mongo_client


async def fetch_with_aiohttp(url: str) -> str:
    """Fetch content using aiohttp (no JavaScript)"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.text()


async def fetch_with_playwright(url: str) -> str:
    """Fetch content using Playwright (with JavaScript)"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            # Use 'load' instead of 'networkidle' which is more reliable
            await page.goto(url, wait_until='load', timeout=60000)
            
            # Wait a bit for JavaScript to execute
            await page.wait_for_timeout(3000)
            
            # Try to wait for episode title, but don't fail if it's not found
            try:
                await page.wait_for_selector('h1', timeout=10000)
            except:
                print("   ⚠️ H1 selector not found, but continuing...")
            
            content = await page.content()
            return content
        finally:
            await browser.close()


def process_with_beautifulsoup(html_content: str) -> str:
    """Process HTML content with BeautifulSoup"""
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.prettify()


async def get_top_episodes(limit: int = 10):
    """Get top episodes from MongoDB"""
    client = await get_async_mongo_client()
    try:
        db = client["biohack_agent"]
        collection = db["episode_urls"]
        
        # Get top episodes in descending order by episode_number
        cursor = collection.find().sort("episode_number", -1).limit(limit)
        episodes = await cursor.to_list(length=limit)
        
        print(f"📥 Retrieved {len(episodes)} episodes from MongoDB")
        for ep in episodes:
            print(f"   Episode {ep.get('episode_number', 'N/A')}: {ep.get('episode_url', 'N/A')}")
        
        return episodes 
    except Exception as e: 
        print(f"Error getting top episodes: {e}") 
        return []


async def compare_single_episode(episode_data: dict, episode_index: int, timestamp: str):
    """Compare both methods for a single episode and save HTML files"""
    
    episode_number = episode_data.get('episode_number', 'Unknown')
    url = episode_data.get('episode_url', '')
    
    print(f"\n🎯 Episode {episode_index + 1}/10 - Episode #{episode_number}")
    print(f"   URL: {url}")
    print("-" * 80)
    
    if not url:
        print("   ❌ No URL found for this episode")
        return None
    
    results = {
        'episode_number': episode_number,
        'url': url,
        'aiohttp_length': 0,
        'playwright_length': 0,
        'aiohttp_success': False,
        'playwright_success': False,
        'aiohttp_has_title': False,
        'playwright_has_title': False,
        'aiohttp_has_episode': False,
        'playwright_has_episode': False,
        'aiohttp_file': '',
        'playwright_file': ''
    }
    
    # Method 1: aiohttp
    print("   🌐 Testing aiohttp...")
    try:
        aiohttp_content = await fetch_with_aiohttp(url)
        results['aiohttp_length'] = len(aiohttp_content)
        results['aiohttp_success'] = True
        print(f"      ✅ Success! Length: {len(aiohttp_content):,} characters")
        
        # Save aiohttp HTML file
        aiohttp_filename = f"ep{episode_number}_aiohttp_{timestamp}.html"
        aiohttp_filepath = f"output/{aiohttp_filename}"
        with open(aiohttp_filepath, "w", encoding="utf-8") as f:
            f.write(aiohttp_content)
        results['aiohttp_file'] = aiohttp_filename
        print(f"      💾 Saved: {aiohttp_filename}")
        
        # Check for key elements
        soup = BeautifulSoup(aiohttp_content, 'html.parser')
        results['aiohttp_has_title'] = bool(soup.find('h1'))
        results['aiohttp_has_episode'] = bool(soup.find('h2', string=lambda t: t and 'EP' in t))
        
    except Exception as e:
        print(f"      ❌ Failed: {e}")
    
    # Method 2: Playwright
    print("   🎭 Testing Playwright...")
    try:
        playwright_content = await fetch_with_playwright(url)
        results['playwright_length'] = len(playwright_content)
        results['playwright_success'] = True
        print(f"      ✅ Success! Length: {len(playwright_content):,} characters")
        
        # Save playwright HTML file
        playwright_filename = f"ep{episode_number}_playwright_{timestamp}.html"
        playwright_filepath = f"output/{playwright_filename}"
        with open(playwright_filepath, "w", encoding="utf-8") as f:
            f.write(playwright_content)
        results['playwright_file'] = playwright_filename
        print(f"      💾 Saved: {playwright_filename}")
        
        # Check for key elements
        soup = BeautifulSoup(playwright_content, 'html.parser')
        results['playwright_has_title'] = bool(soup.find('h1'))
        results['playwright_has_episode'] = bool(soup.find('h2', string=lambda t: t and 'EP' in t))
        
    except Exception as e:
        print(f"      ❌ Failed: {e}")
    
    # Quick comparison
    if results['aiohttp_success'] and results['playwright_success']:
        diff = results['playwright_length'] - results['aiohttp_length']
        print(f"   📊 Content difference: {diff:,} characters")
        
        if abs(diff) < 1000:
            print("      ✅ Very similar content sizes - aiohttp likely sufficient")
        elif results['playwright_length'] > results['aiohttp_length']:
            print("      ⚠️ Playwright got more content - may need JavaScript")
        else:
            print("      🤔 aiohttp got more content - unexpected")
    
    return results


async def compare_all_episodes():
    """Compare both methods across top 10 episodes"""
    
    print("🚀 EPISODE COMPARISON ANALYSIS")
    print("=" * 80)
    
    # Create output directory
    os.makedirs("output", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Get episodes from MongoDB
    episodes = await get_top_episodes(10)
    
    if not episodes:
        print("❌ No episodes found in MongoDB")
        return
    
    # Compare each episode
    all_results = []
    for i, episode in enumerate(episodes):
        result = await compare_single_episode(episode, i, timestamp)
        if result:
            all_results.append(result)
        
        # Add a small delay to be nice to the server
        await asyncio.sleep(1)
    
    # Generate summary report
    print("\n" + "=" * 80)
    print("📋 SUMMARY REPORT")
    print("=" * 80)
    
    summary_lines = []
    summary_lines.append(f"Total episodes tested: {len(all_results)}")
    summary_lines.append(f"Timestamp: {datetime.now()}")
    summary_lines.append("=" * 80)
    summary_lines.append("")
    
    aiohttp_successes = sum(1 for r in all_results if r['aiohttp_success'])
    playwright_successes = sum(1 for r in all_results if r['playwright_success'])
    
    summary_lines.append(f"🌐 aiohttp success rate: {aiohttp_successes}/{len(all_results)} ({aiohttp_successes/len(all_results)*100:.1f}%)")
    summary_lines.append(f"🎭 Playwright success rate: {playwright_successes}/{len(all_results)} ({playwright_successes/len(all_results)*100:.1f}%)")
    summary_lines.append("")
    
    # Detailed results
    summary_lines.append("📊 DETAILED RESULTS:")
    summary_lines.append("Episode | aiohttp | Playwright | Difference | Title Found | Episode Found")
    summary_lines.append("-" * 80)
    
    for result in all_results:
        ep_num = str(result['episode_number']).ljust(7)
        aio_len = f"{result['aiohttp_length']:,}".rjust(8)
        pw_len = f"{result['playwright_length']:,}".rjust(10)
        diff = result['playwright_length'] - result['aiohttp_length']
        diff_str = f"{diff:+,}".rjust(11)
        
        aio_title = "✅" if result['aiohttp_has_title'] else "❌"
        pw_title = "✅" if result['playwright_has_title'] else "❌"
        title_status = f"{aio_title}/{pw_title}".center(11)
        
        aio_ep = "✅" if result['aiohttp_has_episode'] else "❌"
        pw_ep = "✅" if result['playwright_has_episode'] else "❌"
        episode_status = f"{aio_ep}/{pw_ep}".center(13)
        
        line = f"{ep_num} | {aio_len} | {pw_len} | {diff_str} | {title_status} | {episode_status}"
        summary_lines.append(line)
    
    summary_lines.append("")
    summary_lines.append("Legend: aiohttp/playwright results")
    summary_lines.append("✅ = Found, ❌ = Not found")
    summary_lines.append("")
    
    # Add file listings
    summary_lines.append("📁 SAVED HTML FILES:")
    summary_lines.append("aiohttp files:")
    for result in all_results:
        if result['aiohttp_file']:
            summary_lines.append(f"  - {result['aiohttp_file']}")
    
    summary_lines.append("")
    summary_lines.append("Playwright files:")
    for result in all_results:
        if result['playwright_file']:
            summary_lines.append(f"  - {result['playwright_file']}")
    
    summary_lines.append("")
    summary_lines.append("🔍 INSPECTION GUIDE:")
    summary_lines.append("1. Compare aiohttp vs playwright files for the same episode")
    summary_lines.append("2. Check if your parser selectors work on aiohttp content")
    summary_lines.append("3. Look for structural differences in HTML")
    summary_lines.append("4. Identify if JavaScript is adding missing content")
    
    # Save summary report
    summary_text = "\n".join(summary_lines)
    with open(f"output/episodes_comparison_{timestamp}.txt", "w", encoding="utf-8") as f:
        f.write(summary_text)
    
    # Print summary
    print(summary_text)
    
    print(f"\n📁 Summary saved to: output/episodes_comparison_{timestamp}.txt")
    print(f"📁 HTML files saved in output/ directory - ready for inspection!")
    print("🎉 Episode comparison complete!")


async def main():
    """Main function to run the episode comparison"""
    await compare_all_episodes()


if __name__ == "__main__":
    asyncio.run(main())
