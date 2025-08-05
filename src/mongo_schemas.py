from pydantic import BaseModel, Field 
from typing import List, Optional, Dict 
from datetime import datetime 

class EpisodeSchema(BaseModel):
    podcast_name: str
    podcast_url: str  # Changed from HttpUrl to str for Mongo compatibility
    podcast_description: str
    podcast_owner: str

    episode_number: int
    title: str
    slug: str

    # Updated summary to be structured
    summary: Dict[str, Optional[str]]  # e.g., {"short_summary": "...", "summary_text": "..."}
    
    guest: Dict[str, Optional[str]]  # e.g., {"name": "...", "title": "...", "bio": "..."}

    sponsors: List[Dict[str, str]]  # [{"name": "...", "url": "..."}]
    resources: List[Dict[str, str]]  # [{"title": "...", "url": "..."}]
    
    transcript: Dict[str, str]  # {"download_url": "...", "status": "available"}

    timestamps: List[Dict[str, str]]  # [{"time": "...", "topic": "...", "description": "..."}]

    date_published: Optional[datetime] = None
    episode_url: str  # Changed from HttpUrl
    podcast_subscription_url: str  # Changed from HttpUrl

    key_takeaways: List[str]  # New field for bullet points

    schema_version: int = Field(default=2, description="Schema version for tracking upgrades")


if __name__ == "__main__":
    print("Importing mongo schemas")
    