"""
Async web scraper using Playwright (more modern alternative to Selenium)
Playwright is built for async and generally faster/more reliable
"""
import asyncio
from playwright.async_api import async_playwright
from typing import Dict
from src.transcript_parser import EpisodeParser


class PlaywrightScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def get_rendered_html(self, url: str, wait_for_selector: str = None, timeout: int = 30000) -> str:
        """
        Get fully rendered HTML after JavaScript execution
        
        Args:
            url: The URL to scrape
            wait_for_selector: CSS selector to wait for before getting HTML
            timeout: Maximum time to wait (in milliseconds)
        """
        page = await self.context.new_page()
        
        try:
            print(f"Loading page: {url}")
            await page.goto(url, wait_until='networkidle', timeout=timeout)
            
            # Wait for specific element if provided
            if wait_for_selector:
                print(f"Waiting for selector: {wait_for_selector}")
                await page.wait_for_selector(wait_for_selector, timeout=timeout)
            
            # Get the fully rendered HTML
            html_content = await page.content()
            print(f"Got HTML content, length: {len(html_content)}")
            return html_content
            
        except Exception as e:
            print(f"Error getting rendered HTML: {e}")
            return ""
        finally:
            await page.close()


async def get_episode_html_playwright(episode_url: str) -> str:
    """
    Get episode HTML using Playwright (recommended approach)
    """
    async with PlaywrightScraper(headless=True) as scraper:
        html = await scraper.get_rendered_html(
            episode_url,
            wait_for_selector="h1.elementor-heading-title",  # Wait for episode title
            timeout=30000  # 30 seconds
        )
        return html


async def test_playwright_vs_aiohttp(episode_url: str):
    """Test Playwright vs aiohttp for episode parsing"""
    
    print("🧪 Testing Playwright vs aiohttp...")
    
    # Test with Playwright
    print("\n📄 Getting HTML with Playwright...")
    html_content = await get_episode_html_playwright(episode_url)
    
    if html_content:
        parser = EpisodeParser(html_content)
        episode_data = parser.parse_full_episode()
        
        print("✅ Playwright results:")
        print(f"  Episode number: {episode_data.get('episode_number')}")
        print(f"  Title: {episode_data.get('title')}")
        print(f"  Guest: {episode_data.get('guest', {}).get('name', 'No guest')}")
        print(f"  Sponsors: {len(episode_data.get('sponsors', []))}")
        print(f"  Resources: {len(episode_data.get('resources', []))}")
        print(f"  Timestamps: {len(episode_data.get('timestamps', []))}")
        print(f"  Key takeaways: {len(episode_data.get('key_takeaways', []))}")
        
        return episode_data
    else:
        print("❌ Failed to get HTML content")
        return None


if __name__ == "__main__": 
    pass 
    # Test with episode 1333
    # test_url = "https://daveasprey.com/1301-ewot/"
    # result = asyncio.run(test_playwright_vs_aiohttp(test_url))
    
    # if result:
    #     print(f"\n🎉 Successfully parsed episode: {result.get('title')}")
    # else:
    #     print("\n❌ Failed to parse episode")