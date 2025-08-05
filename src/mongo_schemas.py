from pydantic import BaseModel, Field 
from typing import List, Optional, Dict, Any
from datetime import datetime 

class EpisodeSchema(BaseModel):
    # Podcast metadata
    podcast_name: str
    podcast_url: str
    podcast_description: str
    podcast_owner: str

    # Episode core data
    episode_number: int
    title: str
    slug: str
    episode_url: str
    podcast_subscription_url: str

    # Rich summary structure that matches parser output
    summary: Dict[str, Any]  # Contains short_summary and detailed_summary dict
    
    # Guest information
    guest: Dict[str, Optional[str]]  # {"name": "...", "title": "...", "bio": "..."}

    # Episode content
    sponsors: List[Dict[str, str]]  # [{"name": "...", "url": "..."}]
    resources: List[Dict[str, str]]  # [{"title": "...", "url": "..."}]
    transcript: Dict[str, str]  # {"download_url": "...", "status": "available"}
    
    # Timestamps with description support
    timestamps: List[Dict[str, str]]  # [{"time": "...", "topic": "...", "description": "..."}]

    # Additional rich data
    youtube_video_id: Optional[str] = None
    pdf_resources: Optional[List[str]] = Field(default_factory=list)
    key_takeaways: Optional[List[str]] = Field(default_factory=list)

    # Metadata
    date_published: Optional[datetime] = None
    schema_version: int = Field(default=3, description="Schema version for tracking upgrades") 



class EpisodeTranscriptSchema(BaseModel):
    episode_url: str
    transcript_url: Optional[str] = None 
    episode_number: Optional[int] = None  



if __name__ == "__main__":
    print("Importing mongo schemas")
    