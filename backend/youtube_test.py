from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
import re

# ----- Your setup (unchanged) -----
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

# Update this path if your client secret filename/path differs
CLIENT_SECRET_FILE = "client_secret_490654219742-i9ea6bruh70731fgpi810hsf7hb1g47p.apps.googleusercontent.com.json"

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
credentials = flow.run_local_server(port=0)

youtube = build("youtube", "v3", credentials=credentials)
# ----------------------------------


def extract_video_id(value: str) -> str:
    """Return a YouTube video ID from a URL or raw ID."""
    # Raw 11-char ID
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", value):
        return value

    # youtu.be short links
    if value.startswith(("https://youtu.be/", "http://youtu.be/")):
        return value.rstrip("/").split("/")[-1].split("?")[0]

    # youtube.com links
    parsed = urlparse(value)
    if parsed.netloc.endswith("youtube.com"):
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                return qs["v"][0]
        if parsed.path.startswith("/embed/"):
            return parsed.path.split("/embed/")[-1].split("?")[0]

    raise ValueError(f"Could not extract a valid YouTube video ID from: {value}")


# The video you provided
video_input = "https://www.youtube.com/watch?v=pQWfxAuFe1o"

# 1) Run a SEARCH first (as requested)
print("\n=== SEARCH (matching your request) ===")
search_resp = youtube.search().list(
    part="snippet",
    q=video_input,   # you can also use the raw ID from extract_video_id(video_input)
    type="video",
    maxResults=5
).execute()

for i, item in enumerate(search_resp.get("items", []), start=1):
    s = item["snippet"]
    print(f"{i}. {s.get('title')}  |  Channel: {s.get('channelTitle')}  |  Published: {s.get('publishedAt')}")
    print(f"   Video ID: {item['id'].get('videoId')}")
    print()

# 2) Get FULL details for the exact video (title, LONG description, stats)
print("\n=== VIDEO DETAILS (precise) ===")
video_id = extract_video_id(video_input)

video_resp = youtube.videos().list(
    part="snippet,contentDetails,statistics,status",
    id=video_id,
    maxResults=1
).execute()

items = video_resp.get("items", [])
if not items:
    print(f"No video found for ID: {video_id}")
else:
    v = items[0]
    snip = v.get("snippet", {})
    stats = v.get("statistics", {})

    title = snip.get("title", "(no title)")
    channel = snip.get("channelTitle", "(unknown channel)")
    published = snip.get("publishedAt", "(unknown date)")
    description = snip.get("description", "")
    views = stats.get("viewCount", "0")
    likes = stats.get("likeCount", "0")
    comments = stats.get("commentCount", "0")

    print(f"Title: {title}")
    print(f"Channel: {channel}")
    print(f"Published: {published}")
    print(f"Views: {views}  Likes: {likes}  Comments: {comments}")
    print("-" * 80)
    print(description)
    print("-" * 80)
