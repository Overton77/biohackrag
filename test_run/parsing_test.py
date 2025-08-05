from bs4 import BeautifulSoup  

with open("webpage.html", "r", encoding="utf-8") as file:
    html_content = file.read()
    soup = BeautifulSoup(html_content, "html.parser", from_encoding="utf-8")







def parse_episode_page(html):
    soup = BeautifulSoup(html, "html.parser")

    # Episode number & title
    episode_number_tag = soup.find("h2", class_="elementor-heading-title")
    episode_number = int(episode_number_tag.get_text(strip=True).replace("EP ", "")) if episode_number_tag else None

    title_tag = soup.find("h1", class_="elementor-heading-title")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Mini summary
    mini_summary_p = soup.find(string=lambda text: "Episode_number-mini-summary_p__start" in text)
    mini_summary = None
    if mini_summary_p:
        parent_div = mini_summary_p.find_parent("div", class_="elementor-widget-container")
        mini_summary = parent_div.get_text(" ", strip=True)

    # Detailed summary & "You'll learn"
    detailed_section_header = soup.find("h2", string=lambda t: "In this Episode of The Human Upgrade" in t)
    detailed_summary = None
    you_will_learn = []
    if detailed_section_header:
        container = detailed_section_header.find_parent("div", class_="elementor-widget-container")
        paragraphs = container.find_all("p")
        detailed_summary = " ".join(p.get_text(" ", strip=True) for p in paragraphs if "You’ll learn:" not in p.get_text())

        # Extract bullet points for "You'll learn"
        ul_tags = container.find_all("ul")
        for ul in ul_tags:
            for li in ul.find_all("li"):
                text = li.get_text(" ", strip=True)
                if text:
                    you_will_learn.append(text)

    # Podcast subscription links
    podcast_links = [a["href"] for a in soup.select("a[href*='itunes'], a[href*='spotify'], a[href*='amazon'], a[href*='youtube']")]

    # Sponsors
    sponsors = []
    sponsor_list = container.find_all("ul")
    for ul in sponsor_list:
        for li in ul.find_all("li"):
            link = li.find("a")
            if link:
                sponsors.append({"name": li.get_text(" ", strip=True).split("|")[0], "url": link["href"]})

    # Resources
    resources = []
    resources_section = soup.find("b", string=lambda t: "Resources" in t)
    if resources_section:
        resource_ul = resources_section.find_parent().find_next_sibling("ul")
        while resource_ul:
            for li in resource_ul.find_all("li"):
                link = li.find("a")
                if link:
                    title = li.get_text(" ", strip=True)
                    resources.append({"title": title, "url": link["href"]})
            resource_ul = resource_ul.find_next_sibling("ul")

    # Transcript
    transcript_link = soup.select_one("a[href*='Transcript.html']")
    transcript_url = transcript_link["href"] if transcript_link else None

    # YouTube video
    youtube_div = soup.select_one(".rll-youtube-player")
    youtube_video_id = youtube_div.get("data-id") if youtube_div else None

    # Timestamps
    timestamps = []
    timestamp_wrap = soup.select_one(".podcast-timestap-wrap")
    if timestamp_wrap:
        lis = timestamp_wrap.find_all("li")
        ps = timestamp_wrap.find_all("p")
        for i, li in enumerate(lis):
            time_text = li.find("b").get_text(strip=True)
            topic_text = li.get_text(strip=True).replace(time_text, "").strip()
            desc = ps[i].get_text(strip=True) if i < len(ps) else ""
            timestamps.append({"time": time_text, "topic": topic_text, "description": desc})

    return {
        "podcast_name": "The Human Upgrade",
        "podcast_subscription_urls": podcast_links,
        "episode_number": episode_number,
        "title": title,
        "mini_summary": mini_summary,
        "detailed_summary": detailed_summary,
        "you_will_learn": you_will_learn,
        "sponsors": sponsors,
        "resources": resources,
        "timestamps": timestamps,
        "transcript_url": transcript_url,
        "youtube_video_id": youtube_video_id
    } 


if __name__ == "__main__":  
    print(parse_episode_page(html_content)) 