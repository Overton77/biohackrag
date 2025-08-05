import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime 
from typing import Dict, List, Optional   




def save_webpage_html(url, output_filename):
    # Add headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Send GET request to the URL
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Save the HTML content to a file
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))
        
        print(f"Successfully saved HTML content to {output_filename}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

class EpisodeParser:
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
    
    def extract_episode_number(self) -> Optional[int]:
        """Extract episode number from EP XXXX pattern"""
        try:
            # Look for h2 with "EP" followed by numbers
            ep_element = self.soup.find('h2', class_='elementor-heading-title')
            if ep_element and ep_element.text.strip().startswith('EP'):
                ep_text = ep_element.text.strip()
                match = re.search(r'EP\s*(\d+)', ep_text)
                if match:
                    return int(match.group(1))
        except Exception as e:
            print(f"Error extracting episode number: {e}")
        return None
    
    def extract_title(self) -> Optional[str]:
        """Extract episode title from h1 element"""
        try:
            # Look for h1 with the full episode title
            title_element = self.soup.find('h1', class_='elementor-heading-title')
            if title_element:
                title_text = title_element.get_text(strip=True)
                # Remove episode number prefix if present
                title_text = re.sub(r'^\d+\.\s*', '', title_text)
                return title_text
        except Exception as e:
            print(f"Error extracting title: {e}")
        return None
    
    def extract_short_summary(self) -> Optional[str]:
        """Extract the short summary from the first paragraph after episode title"""
        try:
            # Find the first detailed paragraph after the title
            # Look for the widget with text-editor class that contains the episode summary
            text_editor = self.soup.find('div', {'data-widget_type': 'text-editor.default'})
            if text_editor:
                p_tag = text_editor.find('p')
                if p_tag:
                    # Extract text and clean it up
                    summary = p_tag.get_text(strip=True)
                    # Clean up spacing issues
                    summary = ' '.join(summary.split())
                    # Limit to first sentence or reasonable length
                    sentences = summary.split('. ')
                    if len(sentences) > 1:
                        return sentences[0] + '.'
                    return summary[:200] + '...' if len(summary) > 200 else summary
        except Exception as e:
            print(f"Error extracting short summary: {e}")
        return None
    
    def extract_detailed_summary(self) -> Optional[Dict[str, str]]:
        """Extract the detailed summary section starting from 'In this Episode...' 
        and include the bullet points after 'You’ll learn:', excluding Dave Asprey bio and sponsor sections.

        Returns:
            dict with:
                - 'summary_text': main descriptive paragraphs
                - 'key_takeaways': list of bullet points
            """
        try:
            # Locate the header
            header = self.soup.find("h2", string=lambda t: t and "In this Episode of The Human Upgrade" in t)
            if not header:
                return None

            # Find the main text container after header
            detailed_div = header.find_next("div", class_="elementor-widget-text-editor")
            if not detailed_div:
                return None

            summary_parts = []
            key_takeaways: List[str] = []
            stop = False

            # Collect all paragraphs until the PDF link or SPONSORS section
            for p in detailed_div.find_all("p"):
                text = p.get_text(" ", strip=True)
                if not text:
                    continue

                # Stop collecting if PDF link or sponsor section is detected
                if "SPONSORS" in text or "https://cdn.shopify.com" in text:
                    break

                # Identify "You’ll learn:" marker
                if text.replace(" ", "") == "You’lllearn:":
                    # Get the <ul> that follows this <p>
                    ul = p.find_next("ul")
                    if ul:
                        for li in ul.find_all("li"):
                            li_text = li.get_text(" ", strip=True)
                            if li_text:
                                key_takeaways.append(li_text)
                    # Skip adding "You’ll learn:" itself to summary_parts
                    continue

                summary_parts.append(text)

            if not summary_parts and not key_takeaways:
                return None

            # Combine main summary
            summary_text = " ".join(summary_parts)

            # Remove trailing section starting with "Dave Asprey is"
            summary_text = re.split(r"(Dave Asprey is a)", summary_text)[0].strip()

            # Normalize whitespace
            summary_text = re.sub(r"\s+", " ", summary_text)

            return {
                "summary_text": summary_text,
                "key_takeaways": key_takeaways
            }

        except Exception as e:
            print(f"Error extracting detailed summary: {e}")
            return None
    
    def extract_guest_info(self) -> Dict[str, Optional[str]]:
        """Extract guest name and info"""
        try:
            guest_info = {"name": None, "title": None, "bio": None}
            
            # Look for guest name in the summary text or quote attribution
            # First try to find it in a quote attribution
            h4_elements = self.soup.find_all('h4', class_='elementor-heading-title')
            for h4 in h4_elements:
                text = h4.get_text(strip=True)
                # Skip common names like "Dave Asprey"
                if text and text != "Dave Asprey" and len(text.split()) <= 3:
                    guest_info["name"] = text
                    break
            
            # If not found, try to extract from summary text
            if not guest_info["name"]:
                text_divs = self.soup.find_all('div', class_='elementor-widget-container')
                for div in text_divs:
                    text = div.get_text()
                    # Look for patterns like "Joined by" or "Guest [Name]"
                    patterns = [
                        r'Joined by[^.]*?([A-Z][a-z]+ [A-Z][a-z]+)',
                        r'Guest ([A-Z][a-z]+ [A-Z][a-z]+)',
                        r'with ([A-Z][a-z]+ [A-Z][a-z]+)',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, text)
                        if match:
                            guest_info["name"] = match.group(1)
                            break
                    
                    if guest_info["name"]:
                        break
            
            return guest_info
        except Exception as e:
            print(f"Error extracting guest info: {e}")
            return {"name": None, "title": None, "bio": None}
    
    def extract_sponsors(self) -> List[Dict[str, str]]:
        """Extract sponsors information"""
        try:
            sponsors = []
            
            # Find the sponsors section
            all_divs = self.soup.find_all('div', class_='elementor-widget-container')
            for div in all_divs:
                text = div.get_text()
                if "SPONSORS:" in text and "Resources:" not in text:  # Make sure we're in sponsors section only
                    # Look for list items in this section
                    list_items = div.find_all('li')
                    for li in list_items:
                        link = li.find('a', href=True)
                        if link:
                            href = link['href']
                            
                            # Skip PDF links (these should be in resources)
                            if '.pdf' in href:
                                continue
                                
                            # Extract sponsor name from the li text before the link
                            li_text = li.get_text()
                            # Pattern: "SPONSOR_NAME | Go to URL for discount"
                            if '|' in li_text:
                                sponsor_name = li_text.split('|')[0].strip()
                                # Clean up common patterns
                                sponsor_name = re.sub(r'\s+Head to\s*$', '', sponsor_name)
                                sponsor_name = re.sub(r'\s+Go to\s*$', '', sponsor_name)
                            else:
                                sponsor_name = link.get_text(strip=True)
                            
                            sponsors.append({
                                "name": sponsor_name,
                                "url": href
                            })
            
            return sponsors
        except Exception as e:
            print(f"Error extracting sponsors: {e}")
            return []
    
    def extract_resources(self) -> List[Dict[str, str]]:
        """Extract resources links"""
        try:
            resources = []
            
            # Find the resources section
            all_divs = self.soup.find_all('div', class_='elementor-widget-container')
            for div in all_divs:
                text = div.get_text()
                if "Resources:" in text:
                    # Extract all links in this section
                    links = div.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        text = link.get_text(strip=True)
                        
                        # Get the title from the preceding bold text
                        li_parent = link.find_parent('li')
                        if li_parent:
                            bold_text = li_parent.find('b')
                            title = bold_text.get_text(strip=True) if bold_text else text
                            # Clean up title (remove trailing colons)
                            title = re.sub(r':$', '', title)
                        else:
                            title = text
                        
                        resources.append({
                            "title": title,
                            "url": href
                        })
            
            return resources
        except Exception as e:
            print(f"Error extracting resources: {e}")
            return []
    
    def extract_transcript_url(self) -> Optional[str]:
        """Extract transcript download URL"""
        try:
            # Look for download transcript button
            download_links = self.soup.find_all('a', href=True)
            for link in download_links:
                href = link['href']
                link_text = link.get_text(strip=True).lower()
                
                # Check if this is a transcript download link
                if ('transcript' in link_text and 'download' in link_text) or 'Transcript.html' in href:
                    return href
        except Exception as e:
            print(f"Error extracting transcript URL: {e}")
        return None
    
    def extract_timestamps(self) -> List[Dict[str, str]]:
        """Extract podcast timestamps"""
        try:
            timestamps = []
            
            # Look for the podcast timestamp section
            timestamp_div = self.soup.find('div', class_='podcast-timestap-wrap')
            if timestamp_div:
                list_items = timestamp_div.find_all('li')
                
                # Get descriptions that follow each timestamp
                all_content = timestamp_div.get_text()
                sections = []
                
                for li in list_items:
                    # Extract time and topic
                    bold_element = li.find('b')
                    if bold_element:
                        time_text = bold_element.get_text(strip=True)
                        # Get the remaining text after the bold time
                        topic_text = li.get_text(strip=True)
                        topic_text = topic_text.replace(time_text, '', 1).strip()
                        
                        # Only add if it's a proper time format (HH:MM)
                        if re.match(r'\d{1,2}:\d{2}', time_text):
                            timestamps.append({
                                "time": time_text,
                                "topic": topic_text
                            })
                
                # Match descriptions to timestamps
                paragraphs = timestamp_div.find_all('p')
                description_texts = []
                for p in paragraphs:
                    desc_text = p.get_text(strip=True)
                    if desc_text and not desc_text.startswith('Resources:'):
                        description_texts.append(desc_text)
                
                # Pair descriptions with timestamps
                for i, timestamp in enumerate(timestamps):
                    if i < len(description_texts):
                        timestamp["description"] = description_texts[i]
            
            return timestamps
        except Exception as e:
            print(f"Error extracting timestamps: {e}")
            return []
    
    def extract_youtube_video_id(self) -> Optional[str]:
        """Extract YouTube video ID"""
        try:
            # Look for YouTube embed
            youtube_div = self.soup.find('div', class_='rll-youtube-player')
            if youtube_div and 'data-id' in youtube_div.attrs:
                return youtube_div['data-id']
            
            # Alternative: look for YouTube iframe
            iframe = self.soup.find('iframe', src=True)
            if iframe:
                src = iframe['src']
                youtube_match = re.search(r'youtube\.com/embed/([^/?]+)', src)
                if youtube_match:
                    return youtube_match.group(1)
        except Exception as e:
            print(f"Error extracting YouTube video ID: {e}")
        return None
    
    def extract_pdf_resources(self) -> List[str]:
        """Extract PDF resource links"""
        try:
            pdf_links = []
            
            # Look for Shopify CDN links (usually PDFs)
            all_links = self.soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                if 'cdn.shopify.com' in href and '.pdf' in href:
                    pdf_links.append(href)
            
            return pdf_links
        except Exception as e:
            print(f"Error extracting PDF resources: {e}")
            return []
    
    def parse_full_episode(self) -> Dict:
        """Parse all episode data and return structured dict compatible with MongoDB schema"""
        
        # Get core data
        episode_number = self.extract_episode_number()
        title = self.extract_title()
        detailed_summary_data = self.extract_detailed_summary()
        
        # Generate slug from episode number and title
        title_slug = title.lower() if title else ""
        title_slug = re.sub(r'[^a-z0-9\s-]', '', title_slug)
        title_slug = re.sub(r'\s+', '-', title_slug).strip('-')
        slug = f"{episode_number}-{title_slug}" if episode_number and title_slug else ""
        
        # Extract key takeaways from detailed summary
        key_takeaways = []
        if detailed_summary_data and detailed_summary_data.get("key_takeaways"):
            key_takeaways = detailed_summary_data["key_takeaways"]
        
        return {
            # Podcast metadata
            "podcast_name": "The Human Upgrade with Dave Asprey",
            "podcast_url": "https://daveasprey.com/",
            "podcast_description": "Biohacking tips, expert interviews, and science-backed methods for better performance and health.",
            "podcast_owner": "Dave Asprey",
            
            # Episode core data
            "episode_number": episode_number,
            "title": title,
            "slug": slug,
            "episode_url": f"https://daveasprey.com/{slug}/" if slug else "",
            "podcast_subscription_url": "https://daveasprey.com/subscribe/",
            
            # Rich summary structure
            "summary": {
                "short_summary": self.extract_short_summary(),
                "detailed_summary": detailed_summary_data  # Keep the full structure
            },
            
            # Episode content
            "guest": self.extract_guest_info(),
            "sponsors": self.extract_sponsors(),
            "resources": self.extract_resources(),
            "transcript": {
                "download_url": self.extract_transcript_url(),
                "status": "available" if self.extract_transcript_url() else "pending"
            },
            "timestamps": self.extract_timestamps(),  # Includes description field
            
            # Additional rich data
            "youtube_video_id": self.extract_youtube_video_id(),
            "pdf_resources": self.extract_pdf_resources(),
            "key_takeaways": key_takeaways,
            
            # Metadata
            "date_published": datetime.now()  # You might want to extract this from the page
        }

# Example usage
def parse_episode_from_file(file_path: str) -> Dict:
    """Parse episode data from HTML file"""
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    parser = EpisodeParser(html_content)
    return parser.parse_full_episode()



if __name__ == "__main__": 
    print('Importing Transcript Parser')
    # Test with the webpage.html file
    # episode_data = parse_episode_from_file('webpage.html') 
    # print("=== PARSED EPISODE DATA (MongoDB Ready) ===")
    # for key, value in episode_data.items():
    #     print(f"{key}: {value}")
    
    # print("\n" + "="*50)
    # print("Summary of key fields:")
    # print(f"Episode: {episode_data.get('episode_number')} - {episode_data.get('title')}")
    # print(f"Slug: {episode_data.get('slug')}")
    # print(f"Guest: {episode_data.get('guest', {}).get('name', 'No guest')}")
    # print(f"Transcript available: {episode_data.get('transcript', {}).get('status')}")
    # print(f"Key takeaways count: {len(episode_data.get('key_takeaways', []))}")
    # print(f"Sponsors count: {len(episode_data.get('sponsors', []))}")
    # print(f"Resources count: {len(episode_data.get('resources', []))}")
    # print(f"Timestamps count: {len(episode_data.get('timestamps', []))}")   
    # print("-------------------------------------------------------")

    # print(f"Transcript URL: {episode_data.get('transcript', {}).get('download_url')}")





