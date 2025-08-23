import os
import re
import time
import logging
import asyncio
from typing import Optional, Set

from pymongo import AsyncMongoClient  

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# ---------- Logging ----------
def setup_logger() -> logging.Logger:
    logger = logging.getLogger("podcast_scraper")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    logger.handlers.clear()

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(sh)

    log_path = os.getenv("LOG_PATH")
    if log_path:
        fh = logging.FileHandler(log_path)
        fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(fh)

    return logger

logger = setup_logger()

# ---------- Config ----------
START_URL = os.getenv("START_URL", "https://www.daveasprey.com/podcast/")
MONGODB_URI = os.getenv("MONGODB_URI")  
DB_NAME = os.getenv("DB_NAME", "biohack_agent")
COLLECTION = os.getenv("COLLECTION", "episodes")

# ---------- Helpers ----------
EP_NUM_RE = re.compile(r"/(\d{2,5})(?:[_\-\/]|$)")

def extract_episode_number(url: str) -> Optional[int]:
    if not url:
        return None
    m = EP_NUM_RE.search(url)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None

def launch_browser() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=opts)  # Selenium Manager handles driver

async def get_most_recent_in_db(col) -> tuple[Optional[int], Optional[str]]:
    """Return (max_episode_number, latest_episode_url_fallback)."""
    with_num = await col.find({"episode_number": {"$type": "int"}})\
                        .sort("episode_number", -1)\
                        .limit(1)\
                        .to_list(length=1)
    max_num = with_num[0]["episode_number"] if with_num else None

    latest = await col.find({}).sort("_id", -1).limit(1).to_list(length=1)
    latest_url = latest[0].get("episode_page_url") if latest else None
    return max_num, latest_url

async def update_episodes_url_selenium(async_mongo_client: AsyncMongoClient):
    logger.info("Launching headless Chrome…")
    driver = launch_browser()
    try:
        driver.get(START_URL)
        logger.info("✅ Navigated to podcast page: %s", START_URL)

        time.sleep(5)
        driver.execute_script("window.scrollBy(0, 1880);")
        time.sleep(5)

        db = async_mongo_client[DB_NAME]
        col = db[COLLECTION]

        max_ep_in_db, latest_url_fallback = await get_most_recent_in_db(col)
        logger.info("Most recent in DB -> episode_number: %s, url: %s",
                    max_ep_in_db, latest_url_fallback)

        seen_links: Set[str] = set()
        inserted = 0

        while True:
            links = driver.find_elements(By.CSS_SELECTOR, "h3.elementor-post__title a")
            new_this_cycle = 0
            for el in links:
                href = el.get_attribute("href")
                if not href or href in seen_links:
                    continue

                seen_links.add(href)
                ep_num = extract_episode_number(href)

                if max_ep_in_db is not None and ep_num is not None and ep_num <= max_ep_in_db:
                    logger.info("✅ Reached existing episode number %s (<= %s). Stopping.",
                                ep_num, max_ep_in_db)
                    logger.info("Inserted %d new episodes this run.", inserted)
                    return

                if max_ep_in_db is None and latest_url_fallback and href == latest_url_fallback:
                    logger.info("✅ Reached most recent episode URL already in DB. Stopping.")
                    logger.info("Inserted %d new episodes this run.", inserted)
                    return

                doc = {"episode_page_url": href}
                if ep_num is not None:
                    doc["episode_number"] = ep_num

                await col.insert_one(doc)
                inserted += 1
                new_this_cycle += 1

            if new_this_cycle:
                logger.info("✅ Collected %d new links this cycle (total inserted: %d)",
                            new_this_cycle, inserted)
            else:
                logger.info("No new links detected on this batch.")

            if any("/1-" in url for url in seen_links):
                logger.info("✅ Episode 1 pattern found. Ending.")
                return

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
                    logger.info("✅ Clicked View More")
                else:
                    logger.info("❌ No View More button found. Ending.")
                    return

            except Exception as e:
                logger.exception("❌ Error clicking View More: %s", e)
                return

            driver.execute_script("window.scrollBy(0, 1880);")
            time.sleep(6)

    finally:
        driver.quit()
        logger.info("Chrome quit. Done.")

async def main():
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI env var is required")
    client = AsyncMongoClient(MONGODB_URI)
    # No explicit client.close(); process exit will clean up.

if __name__ == "__main__":
    asyncio.run(update_episodes_url_selenium(AsyncMongoClient(MONGODB_URI)))