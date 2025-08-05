from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

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



test_search = youtube.search().list(
    part="snippet",
    q="Dave Asprey Human Upgrade",
    type="video",
    maxResults=5
).execute() 


print(test_search)


