from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config.settings import get_settings 

# ----- Your setup (unchanged) -----
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

# Update this path if your client secret filename/path differs
CLIENT_SECRET_FILE = get_settings().google_oauth_client_credentials_path

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
credentials = flow.run_local_server(port=0)

youtube = build("youtube", "v3", credentials=credentials) 

if __name__ == "__main__": 
    print("importing youtube client from youtube_client.py") 