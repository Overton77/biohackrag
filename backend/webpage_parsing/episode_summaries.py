from bs4 import BeautifulSoup  
import json
import re
from typing import Any, Dict, List, Optional  
import asyncio 
from src.config.mongo_setup import get_async_mongo_client
import aiohttp


def _extract_time_and_title_from_li(li_tag) -> Dict[str, Optional[str]]:
    """Extract a time stamp and title from a single <li> element.

    This function is resilient to different internal structures, including
    <b><span>time</span></b><span>title</span> or plain text.
    """
    li_text = " ".join(list(li_tag.stripped_strings))

    # Matches mm:ss or hh:mm:ss at the beginning of the line
    time_match = re.match(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s*(.*)$", li_text)
    if time_match:
        time_text = time_match.group(1)
        title_text = time_match.group(2).strip() if time_match.group(2) else None
        return {"time": time_text, "title": title_text or None}

    # Fallback: look inside <b> for a time-like string
    bold_tag = li_tag.find("b")
    if bold_tag is not None:
        bold_text = " ".join(list(bold_tag.stripped_strings))
        time_match = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?)", bold_text)
        if time_match:
            time_text = time_match.group(1)
            # Remove bold content from the full text to approximate the title
            remainder = li_text.replace(bold_text, "").strip()
            remainder = remainder.lstrip("-: ") or None
            return {"time": time_text, "title": remainder}

    return {"time": None, "title": li_text or None}


def parse_episode_timeline(soup: BeautifulSoup) -> List[Dict[str, Any]]:   
    """Parse timeline entries from the podcast timestamp section.

    Returns a list of objects: {"time": str|None, "title": str|None, "description": str|None}
    The description is taken from the first <p> following the corresponding <ul>.
    Parsing stops assigning descriptions once the "Resources:" section begins.
    """
    timeline_container = soup.find("div", class_="podcast-timestap-wrap")
    if timeline_container is None:
        return []

    entries: List[Dict[str, Any]] = []
    last_index_with_entry: Optional[int] = None
    reached_resources = False

    for child in timeline_container.children:
        if getattr(child, "name", None) is None:
            continue

        if child.name == "p":
            text = child.get_text(" ", strip=True)
            if not text:
                continue
            if text.lower().startswith("resources:"):
                reached_resources = True
                continue
            if not reached_resources and last_index_with_entry is not None:
                if not entries[last_index_with_entry].get("description"):
                    entries[last_index_with_entry]["description"] = text
            continue

        if child.name == "ul":
            # In most pages, there is one <li> per <ul> for timeline, but handle multiple conservatively
            for li_tag in child.find_all("li", recursive=False):
                extracted = _extract_time_and_title_from_li(li_tag)
                entry: Dict[str, Any] = {
                    "time": extracted.get("time"),
                    "title": extracted.get("title"),
                    "description": None,
                }
                entries.append(entry)
                last_index_with_entry = len(entries) - 1

    return entries


def parse_resources(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Parse the Resources list within the timestamp container.

    Returns a list of objects: {"text": str, "links": [str, ...]}
    """
    timeline_container = soup.find("div", class_="podcast-timestap-wrap")
    if timeline_container is None:
        return []

    # Locate the "Resources:" label paragraph
    resources_label = None
    for p in timeline_container.find_all("p"):
        label_text = p.get_text(" ", strip=True).lower()
        if label_text.startswith("resources:"):
            resources_label = p
            break

    if resources_label is None:
        return []

    # The first <ul> after the label contains the resources list
    ul = resources_label.find_next_sibling("ul")
    if ul is None:
        return []

    items: List[Dict[str, Any]] = []
    for li in ul.find_all("li", recursive=False):
        text = li.get_text(" ", strip=True)
        links = [a.get("href") for a in li.find_all("a", href=True)]
        items.append({"text": text, "links": links})

    return items


def parse_html_content(html_content: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html_content, "html.parser")
    return {
        "timeline": parse_episode_timeline(soup),
        "resources": parse_resources(soup),
        "major_summary": parse_major_summary(soup),
        "sponsors": parse_sponsors(soup),
    }


# def main() -> None:
#     html_path = r"C:\Users\Pinda\Proyectos\BioHackAgent\output\ep1332_aiohttp_20250805_144953.html"
#     with open(html_path, "r", encoding="utf-8") as file:
#         html_content = file.read()

#     result = parse_html_content(html_content)  
#     print(json.dumps(result, ensure_ascii=False, indent=2))
#     return result 
    
async def save_to_mongo(result: Dict[str, Any]) -> None:  
    episode_number = 1333 
    client = await get_async_mongo_client()
    if client is None:
        print("Failed to connect to MongoDB")
        return

    db = client["biohack_agent"] 

    collection = db["episode_urls"]   

    episode_entry = await collection.find_one({"episode_number": episode_number})
    
    episode_id = episode_entry["_id"]  

    all_timeline_entries = []  
    for key, value in result.items(): 
        if key == "timeline": 
            for item in value: 
                if item.get("time") and item.get("title"): 
                    all_timeline_entries.append({
                        "time": item["time"],
                        "title": item["title"],
                        "description": item.get("description"),
                    })

            await collection.update_one(
                {"_id": episode_id},
                {"$set": {"timeline": all_timeline_entries}}
            )




async def _fetch_html(episode_url: str, timeout_s: int = 30) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://daveasprey.com/",
    }
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(episode_url, headers=headers, allow_redirects=True) as response:
            return await response.text()


async def parse_and_update_timeline_for_episode_url(episode_url: str) -> Optional[str]:
    """Fetch an episode by episode_url, parse its timeline from the webpage, and update MongoDB.

    Only saves entries that include both time and title. Returns the episode document _id as a string.
    """
    client = await get_async_mongo_client()
    if client is None:
        print("Failed to connect to MongoDB")
        return None

    try:
        db = client["biohack_agent"]
        collection = db["episode_urls"]

        episode_entry = await collection.find_one({"episode_url": episode_url})
        if not episode_entry:
            print("Episode not found for provided episode_url")
            return None

        html_content = await _fetch_html(episode_url)
        parsed = parse_html_content(html_content)

        timeline_entries: List[Dict[str, str]] = []
        for item in parsed.get("timeline", []):
            time_text = item.get("time")
            title_text = item.get("title")
            if time_text and title_text:
                timeline_entries.append({"time": time_text, "title": title_text})

        await collection.update_one(
            {"_id": episode_entry["_id"]},
            {"$set": {"timeline": timeline_entries}},
        )

        return str(episode_entry["_id"])
    finally:
        await client.close()

def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_major_summary(soup: BeautifulSoup) -> Dict[str, Any]:
    """Parse the main episode overview that starts with the heading
    "In this Episode of The Human Upgrade" and ends before the "SPONSORS:" section.

    Returns: {
      heading: str|None,
      paragraphs: [str],
      bullets: [str],
      links: [str],
      free_resources: [str]
    }
    """
    heading_tag = None
    for h_tag in soup.find_all(["h2", "h3"]):
        if re.search(r"In\s+this\s+Episode\s+of\s+The\s+Human\s+Upgrade", h_tag.get_text(" ", strip=True), re.I):
            heading_tag = h_tag
            break

    result: Dict[str, Any] = {
        "heading": heading_tag.get_text(" ", strip=True) if heading_tag else None,
        "paragraphs": [],
        "bullets": [],
        "links": [],
        "free_resources": [],
    }

    if heading_tag is None:
        return result

    for el in heading_tag.next_elements:
        if getattr(el, "name", None) is None:
            continue
        if el.name == "p":
            text = _normalize_text(el.get_text(" ", strip=True))
            if not text:
                continue
            if text.lower().startswith("sponsors:"):
                break
            result["paragraphs"].append(text)
            for a in el.find_all("a", href=True):
                href = a.get("href")
                if href:
                    result["links"].append(href)
                    if "cdn.shopify.com" in href:
                        result["free_resources"].append(href)
        elif el.name == "ul":
            for li in el.find_all("li"):
                li_text = _normalize_text(li.get_text(" ", strip=True))
                if li_text:
                    result["bullets"].append(li_text)
                for a in li.find_all("a", href=True):
                    href = a.get("href")
                    if href:
                        result["links"].append(href)
                        if "cdn.shopify.com" in href:
                            result["free_resources"].append(href)

    return result


def parse_sponsors(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Parse sponsors section after a paragraph whose text starts with "SPONSORS:".

    Returns a list of items: {
      text: str,
      links: [str],
      has_code_dave: bool,
      code: str|None,
      brand: str|None,
      discount_percent: int|None,
    }
    """
    sponsors_p = None
    for p in soup.find_all("p"):
        if p.get_text(" ", strip=True).lower().startswith("sponsors:"):
            sponsors_p = p
            break

    if sponsors_p is None:
        return []

    sponsors: List[Dict[str, Any]] = []
    node = sponsors_p
    for _ in range(10):
        node = node.find_next_sibling()
        if node is None:
            break
        if getattr(node, "name", None) != "ul":
            continue
        for li in node.find_all("li", recursive=False):
            text = _normalize_text(li.get_text(" ", strip=True))
            links = [a.get("href") for a in li.find_all("a", href=True)]
            brand = None
            bold = li.find("b")
            if bold is not None:
                brand = _normalize_text(bold.get_text(" ", strip=True))
            has_code = bool(re.search(r"\bcode\s*DAVE\b", text, re.I) or any("/DAVE" in (href or "").upper() or "CODE=DAVE" in (href or "").upper() for href in links))
            discount = None
            m = re.search(r"(\d{1,2})%", text)
            if m:
                try:
                    discount = int(m.group(1))
                except Exception:
                    discount = None
            sponsors.append({
                "text": text,
                "links": links,
                "has_code_dave": has_code,
                "code": "DAVE" if has_code else None,
                "brand": brand,
                "discount_percent": discount,
            })

    return sponsors


if __name__ == "__main__":  
    # episode_url = "https://daveasprey.com/1301-ewot/" 
    # asyncio.run(parse_and_update_timeline_for_episode_url(episode_url))  
    soup = BeautifulSoup(open("C:/Users/Pinda/Proyectos/BioHackAgent/output/ep1333_aiohttp_20250805_144953.html", "r", encoding="utf-8").read(), "html.parser") 
    major_summary = parse_major_summary(soup)
    print(json.dumps(major_summary, ensure_ascii=False, indent=2)) 

     

    heading = major_summary["heading"] 
    paragraphs = major_summary["paragraphs"] 
    bullets = major_summary["bullets"] 
    links = major_summary["links"] 
    free_resources = major_summary["free_resources"]  


    async def run_quick_mongo_update(episode_number: int): 
        client = await get_async_mongo_client()  
        if client is None: 
            print("Failed to connect to MongoDB") 
            return 

        db = client["biohack_agent"] 
        collection = db["episode_urls"]  

        episode_entry = await collection.find_one({"episode_number": episode_number}) 
        if not episode_entry: 
            print(f"Episode {episode_number} not found in MongoDB") 
            return 

        episode_id = episode_entry["_id"]  

        major_summary = heading + "\n" + "\n".join(paragraphs) + "\n" + "\n".join(bullets) + "\n" + "\n".join(links) + "\n" + "\n".join(free_resources)  

        resource_link = free_resources[0]  

        await collection.update_one(
            {"_id": episode_id},
            {"$set": {
                "major_summary": major_summary,
                "resource_link": resource_link
            }}
        ) 

        print(f"Updated episode {episode_number} in MongoDB")  

    asyncio.run(run_quick_mongo_update(1333)) 


    
    


