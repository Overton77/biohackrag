import os
import time
import logging
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Logging setup
logging.basicConfig(
    filename='podcast_scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CSV path
CSV_PATH = "episodes.csv"

def launch_browser():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_experimental_option("detach", True)  # Keep browser open
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def save_to_csv(data, path=CSV_PATH):
    df = pd.DataFrame(data, columns=["episode_url"])
    if os.path.exists(path):
        existing = pd.read_csv(path)
        combined = pd.concat([existing, df]).drop_duplicates().reset_index(drop=True)
        combined.to_csv(path, index=False)
    else:
        df.to_csv(path, index=False)
    logger.info(f"✅ Saved {len(data)} new episodes to {path}")

def get_existing_links(path=CSV_PATH):
    if os.path.exists(path):
        return set(pd.read_csv(path)["episode_url"].tolist())
    return set()

if __name__ == "__main__":
    driver = launch_browser()
    driver.get("https://www.daveasprey.com/podcast/")
    logger.info("✅ Navigated to Dave Asprey podcast page")

    time.sleep(5)  # Allow initial load
    driver.execute_script("window.scrollBy(0, 1880);")
    time.sleep(10)

    seen_links = get_existing_links()
    logger.info(f"Loaded {len(seen_links)} existing episode links")

    while True:
        # Collect all current episode links
        episode_links = driver.find_elements(By.CSS_SELECTOR, "h3.elementor-post__title a")
        new_links = []
        for link in episode_links:
            href = link.get_attribute("href")
            if href and href not in seen_links:
                seen_links.add(href)
                new_links.append([href])

        if new_links:
            save_to_csv(new_links)
            print(f"✅ Collected {len(new_links)} new links this cycle")
            logger.info(f"Collected {len(new_links)} new links this cycle")

        # Check if Episode 1 is found
        if any("/1-" in url for url in seen_links):
            print("✅ Episode 1 found! Exiting loop.")
            logger.info("✅ Episode 1 found! Ending scrape.")
            break

        # Locate View More button
        try:
            wrappers = driver.find_elements(By.CSS_SELECTOR, "div.elementor-button-wrapper")
            view_more_btn = None
            for wrapper in wrappers:
                a_tag = wrapper.find_element(By.CSS_SELECTOR, "a.elementor-button-link")
                text_span = a_tag.find_element(By.CSS_SELECTOR, "span.elementor-button-text")
                if text_span.text.strip().lower() == "view more":
                    view_more_btn = a_tag
                    break

            if view_more_btn:
                driver.execute_script("arguments[0].click();", view_more_btn)
                logger.info("✅ Clicked View More button")
                print("Clicked View More button")
            else:
                print("❌ No View More button found. Ending loop.")
                logger.info("❌ No View More button found. Ending loop.")
                break

        except Exception as e:
            logger.error(f"❌ Error clicking View More: {str(e)}")
            break

        # Scroll down and wait for new content
        driver.execute_script("window.scrollBy(0, 1880);")
        time.sleep(8)  # Adjust if needed for slow load

    print("✅ Done scraping. Check episodes.csv for results.")
