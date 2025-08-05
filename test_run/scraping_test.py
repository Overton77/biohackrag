from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome import webdriver as chrome_webdriver

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome import service as fs

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager 
import re 


# Use webdriver-manager to download the correct ChromeDriver



# Example usage
def launch_browser():
    options = Options()
    options.add_argument("--start-maximized") 
    options.add_argument("--disable-notifications")  # Optional

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    # Example: Go to the podcast interview page
    

    return driver


if __name__ == "__main__":
    driver = launch_browser() 

    def find_view_more_button(driver: webdriver.Chrome, wait: WebDriverWait):
        """
        Find the View More button using multiple fallback strategies.
        Returns the button element or None if not found.
        """
        view_more_btn = None
        
        try:
            # Primary: Wait for the button with specific class combination
            view_more_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.alm-load-more-btn.more"))
            )
            print("🟢 Found button with 'alm-load-more-btn more' classes")
        except:
            try:
                # Fallback to single class
                view_more_btn = wait.until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "alm-load-more-btn"))
                )
                print("🟢 Found button with 'alm-load-more-btn' class")
            except:
                print("❌ No interactable 'View More' button found.")
                
        return view_more_btn

    def calculate_button_distance(driver: webdriver.Chrome, last_element, view_more_btn):
        """
        Calculate the distance from the last element to the View More button.
        Returns the distance in pixels.
        """
        distance_script = """
        var lastElement = arguments[0];
        var button = arguments[1];
        
        var lastRect = lastElement.getBoundingClientRect();
        var btnRect = button.getBoundingClientRect();
        
        // Calculate distance from bottom of last element to button
        var distance = btnRect.top - lastRect.bottom;
        
        return {
            lastBottom: lastRect.bottom,
            buttonTop: btnRect.top,
            distance: distance
        };
        """
        
        result = driver.execute_script(distance_script, last_element, view_more_btn)
        print(f"🔍 Distance from last element to button: {result['distance']}px")
        return result['distance']

    def scroll_to_button_from_last_element(driver: webdriver.Chrome, last_element, distance):
        """
        Scroll to the View More button based on the distance from the last element.
        """
        scroll_script = """
        var lastElement = arguments[0];
        var distance = arguments[1];
        
        var lastRect = lastElement.getBoundingClientRect();
        var scrollY = window.scrollY || window.pageYOffset;
        
        // Calculate target position: last element bottom + distance - small buffer
        var targetY = lastRect.bottom + scrollY + distance - 100;
        
        window.scrollTo({top: targetY, behavior: 'smooth'});
        
        return targetY;
        """
        
        target_y = driver.execute_script(scroll_script, last_element, distance)
        print(f"🟢 Scrolled to position: {target_y}px")
        return target_y

    def collect_episode_data(driver: webdriver.Chrome, h3_pattern):
        """
        Collect episode data from h3 tags and a tags.
        Returns tuple of (episode_numbers_set, h3_text_groups_set, correct_sources_set, last_element)
        """
        # Get all a tags and h3 tags
        a_tags = driver.find_elements(By.CSS_SELECTOR, "a.alm-permalink")
        h3_tags = driver.find_elements(By.CSS_SELECTOR, "div.podcast-excerpt > h3")

        episode_numbers = set()
        h3_text_groups = set()
        correct_sources = set()
        
        # First collect all episode numbers and h3 text from h3 tags
        for h3 in h3_tags:
            h3_text = h3.text
            match = re.search(h3_pattern, h3_text)
            if match:
                episode_numbers.add(match.group(1))
                # Add h3 text and matched group to the set
                h3_text_groups.add((h3_text, match.group(1)))

        # Then check each a tag href against all episode numbers
        for a_tag in a_tags:
            href = a_tag.get_attribute("href")
            for episode_num in episode_numbers:
                if f"/{episode_num}-" in href:
                    correct_sources.add(href)
                    break  # Found a match, move to next a tag

        # Find the last element (either last h3 or last a tag)
        last_element = h3_tags[-1] if h3_tags else (a_tags[-1] if a_tags else None)
        
        return episode_numbers, h3_text_groups, correct_sources, last_element

    def find_a_tag_text_episode_name(driver: webdriver.Chrome, url: str, target_count=48):
        """
        Scrape up to target_count unique episode hrefs by clicking 'View More' and scrolling as needed.
        Args:
            driver: webdriver.Chrome
            url: str
            target_count: int (default 48)
        Returns:
            set of unique hrefs
        """
        import time
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        
        all_correct_sources = set()
        all_h3_text_groups = set()
        h3_pattern = r'(\d+)\.\s+.+'
        button_distance = None  # Will store the calculated distance

        while len(all_correct_sources) < target_count:
            # Wait for episode elements and the load more button
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.alm-permalink")))
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.podcast-excerpt > h3")))
            
            # Wait for the specific load more button with both classes
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.alm-load-more-btn.more")))
            except:
                print("Load more button not found, continuing with available episodes...")

            # Collect episode data
            episode_numbers, h3_text_groups, correct_sources, last_element = collect_episode_data(driver, h3_pattern)
            
            # Add to our master sets
            all_correct_sources.update(correct_sources)
            all_h3_text_groups.update(h3_text_groups)

            print(f"🟢 Collected {len(all_correct_sources)} unique hrefs so far...")
            print(f"🟢 Collected {len(all_h3_text_groups)} h3 text groups so far...")
            
            if len(all_correct_sources) >= target_count:
                break

            # Find the View More button
            view_more_btn = find_view_more_button(driver, wait)
            if view_more_btn is None:
                print("🛑 Stopping early - no View More button found")
                break

            # Calculate distance on first iteration or scroll using stored distance
            if button_distance is None and last_element:
                # First time: calculate the distance from last element to button
                button_distance = calculate_button_distance(driver, last_element, view_more_btn)
                # Scroll to the button normally for the first time
                scroll_script = """
                var btn = arguments[0];
                var rect = btn.getBoundingClientRect();
                var scrollY = window.scrollY || window.pageYOffset;
                window.scrollTo({top: rect.top + scrollY - 100, behavior: 'smooth'});
                return rect.top;
                """
                driver.execute_script(scroll_script, view_more_btn)
            elif button_distance is not None and last_element:
                # Subsequent times: scroll using the calculated distance from the last element
                scroll_to_button_from_last_element(driver, last_element, button_distance)
            
            time.sleep(1)  # Give time for scroll animation

            # Click the button
            try:
                view_more_btn.click()
                print("🟢 Clicked 'View More' button.")
                time.sleep(2)  # Wait for new content to load
            except Exception as e:
                print(f"❌ Failed to click View More button: {e}")
                break

        print(f"🟢 Final collection: {len(all_correct_sources)} unique hrefs and {len(all_h3_text_groups)} h3 text groups")
        return all_correct_sources

    correct_sources = find_a_tag_text_episode_name(driver, "https://daveasprey.com/podcasts", target_count=48)
    print("🟢 Final unique sources (up to 40):\n", correct_sources)

   


    input("🟢 Press Enter to close the browser and end the script...")
    driver.quit()