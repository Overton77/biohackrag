"""
Async web scraper using Selenium for JavaScript-rendered pages
"""
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import aiohttp
from typing import Dict
from src.transcript_parser import EpisodeParser


class AsyncSeleniumScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
    
    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Auto-install ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        return self.driver
    
    async def get_rendered_html(self, url: str, wait_for_element: str = None, timeout: int = 10) -> str:
        """
        Get fully rendered HTML after JavaScript execution
        
        Args:
            url: The URL to scrape
            wait_for_element: CSS selector to wait for before getting HTML
            timeout: Maximum time to wait for page load
        """
        if not self.driver:
            self.setup_driver()
        
        try:
            # Load the page
            print(f"Loading page: {url}")
            self.driver.get(url)
            
            # Wait for specific element if provided
            if wait_for_element:
                print(f"Waiting for element: {wait_for_element}")
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
                )
            else:
                # Wait a bit for JavaScript to load
                await asyncio.sleep(3)
            
            # Get the fully rendered HTML
            html_content = self.driver.page_source
            print(f"Got HTML content, length: {len(html_content)}")
            return html_content
            
        except Exception as e:
            print(f"Error getting rendered HTML: {e}")
            return ""
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None


async def compare_scraping_methods(episode_url: str):
    """Compare aiohttp vs Selenium scraping results"""
    
    print("=" * 60)
    print("COMPARING SCRAPING METHODS")
    print("=" * 60)
    
    # Method 1: aiohttp (no JavaScript)
    print("\n1. Testing aiohttp (no JavaScript)...")
    async with aiohttp.ClientSession() as session:
        async with session.get(episode_url) as response:
            aiohttp_html = await response.text()
    
    print(f"aiohttp HTML length: {len(aiohttp_html)}")
    
    # Parse with aiohttp content
    parser_aiohttp = EpisodeParser(aiohttp_html)
    aiohttp_data = parser_aiohttp.parse_full_episode()
    
    print("aiohttp results:")
    print(f"  Episode number: {aiohttp_data.get('episode_number')}")
    print(f"  Title: {aiohttp_data.get('title')}")
    print(f"  Guest: {aiohttp_data.get('guest', {}).get('name')}")
    print(f"  Sponsors count: {len(aiohttp_data.get('sponsors', []))}")
    
    # Method 2: Selenium (with JavaScript)
    print("\n2. Testing Selenium (with JavaScript)...")
    scraper = AsyncSeleniumScraper(headless=True)
    
    try:
        # Wait for the main episode title to load
        selenium_html = await scraper.get_rendered_html(
            episode_url, 
            wait_for_element="h1.elementor-heading-title",
            timeout=15
        )
        
        print(f"Selenium HTML length: {len(selenium_html)}")
        
        # Parse with Selenium content
        parser_selenium = EpisodeParser(selenium_html)
        selenium_data = parser_selenium.parse_full_episode()
        
        print("Selenium results:")
        print(f"  Episode number: {selenium_data.get('episode_number')}")
        print(f"  Title: {selenium_data.get('title')}")
        print(f"  Guest: {selenium_data.get('guest', {}).get('name')}")
        print(f"  Sponsors count: {len(selenium_data.get('sponsors', []))}")
        
        # Compare content differences
        print("\n" + "=" * 60)
        print("CONTENT COMPARISON")
        print("=" * 60)
        
        if len(selenium_html) > len(aiohttp_html) * 1.5:
            print("✅ Selenium returned significantly more content!")
            print("   → This confirms JavaScript rendering is needed")
        else:
            print("🤔 Similar content lengths, investigating differences...")
        
        # Check for specific missing elements
        if not aiohttp_data.get('episode_number') and selenium_data.get('episode_number'):
            print("✅ Selenium found episode number, aiohttp didn't")
        
        if not aiohttp_data.get('title') and selenium_data.get('title'):
            print("✅ Selenium found title, aiohttp didn't")
            
        return selenium_data
        
    finally:
        scraper.close()


async def get_episode_html_with_js(episode_url: str) -> str:
    """
    Production function to get episode HTML with JavaScript rendering
    Use this instead of plain aiohttp for Dave Asprey's site
    """
    scraper = AsyncSeleniumScraper(headless=True)
    try:
        html = await scraper.get_rendered_html(
            episode_url,
            wait_for_element="h1.elementor-heading-title",  # Wait for episode title
            timeout=15
        )
        return html
    finally:
        scraper.close()


if __name__ == "__main__": 
    pass 
    # Test with a specific episode
    # test_url = "https://daveasprey.com/1333-quantum-health/"
    # asyncio.run(compare_scraping_methods(test_url))