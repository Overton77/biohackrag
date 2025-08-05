from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build 
from youtube_transcript_api import YouTubeTranscriptApi  
import json 

# Define YouTube Data API v3 scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

# Load your credentials
flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret_490654219742-i9ea6bruh70731fgpi810hsf7hb1g47p.apps.googleusercontent.com.json", SCOPES
)

# Launch the local OAuth login
credentials = flow.run_local_server(port=0)

# Build YouTube API client
youtube = build("youtube", "v3", credentials=credentials)

# Example request: get your own channel info (if authenticated YouTube user)



def get_videos(youtube, channel_id, max_results=5): 
    response = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        type="video",
        maxResults=max_results
    ).execute()   

    videos = []

    for item in response["items"]: 
        video_id = item["id"]["videoId"] 
        title = item["snippet"]["title"] 
        description = item["snippet"]["description"] 
        published_at = item["snippet"]["publishedAt"] 
        print(f"Video ID: {video_id}") 
        print(f"Title: {title}") 
        print(f"Description: {description}") 
        print(f"Published At: {published_at}")  

        videos.append({
            "video_id": video_id,
            "title": title,
            "description": description,
            "published_at": published_at
        })   

         
    return videos 


def filter_for_human_upgrade(videos): 
    return [ 
        v for v in videos if "The Human Upgrade" in v["description"] or "Human Upgrade Podcast" in v["description"]
    ] 



def get_transcript(video_id): 
    try:  
        transcript = YouTubeTranscriptApi.get_transcript(video_id)   

        print("Full transcript from youtube transcript api: \n\n", transcript)
        return "\n".join([t["text"] for t in transcript]) 

    except Exception as e: 
        print(f"Error getting transcript for video {video_id}: {e}") 

if __name__ == "__main__":  
    channel_id = "UC0RhatS1pyxInC00YKjjBqQ" 

    videos = get_videos(youtube, channel_id)  

    human_upgrade_videos = filter_for_human_upgrade(videos)   

    print("Number of human upgrade videos\n\n", len(human_upgrade_videos)) 

    print("\n") 

    print("Transcripts: \n\n") 

    for video in human_upgrade_videos: 
        transcript = get_transcript(video["video_id"]) 
        print(json.dumps(transcript))  

        with open("transcripts.json", "w") as f: 
            f.write(json.dumps(transcript)) 


