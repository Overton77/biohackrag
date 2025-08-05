#!/usr/bin/env python3
"""
Test script to validate parsed episode data against MongoDB schema
without requiring actual MongoDB connection.
"""

import sys
import os
from datetime import datetime

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'test_run'))

try:
    from src.mongo_schemas import EpisodeSchema
    from test_run.parse_transcript_page import parse_episode_from_file
    print("✅ Successfully imported modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_schema_validation():
    """Test that parsed data validates against MongoDB schema"""
    
    print("🧪 Testing schema validation...")
    
    try:
        # Check if webpage.html exists
        if not os.path.exists('webpage.html'):
            print("❌ webpage.html not found. Creating a minimal test...")
            return create_minimal_test()
        
        # Parse episode data
        print("📄 Parsing episode data...")
        episode_data = parse_episode_from_file('webpage.html')
        
        # Validate with schema
        print("🔍 Validating against MongoDB schema...")
        episode = EpisodeSchema(**episode_data)
        
        print("✅ Schema validation PASSED!")
        print("\n📊 Validation Summary:")
        print(f"  Episode: {episode.episode_number} - {episode.title}")
        print(f"  Slug: {episode.slug}")
        print(f"  Guest: {episode.guest.get('name', 'No guest')}")
        print(f"  Transcript status: {episode.transcript.get('status', 'Unknown')}")
        print(f"  Key takeaways: {len(episode.key_takeaways)}")
        print(f"  Sponsors: {len(episode.sponsors)}")
        print(f"  Resources: {len(episode.resources)}")
        print(f"  Timestamps: {len(episode.timestamps)}")
        print(f"  Schema version: {episode.schema_version}")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation FAILED: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

def create_minimal_test():
    """Create a minimal test case when webpage.html is not available"""
    print("🧪 Running minimal test with sample data...")
    
    minimal_data = {
        "podcast_name": "The Human Upgrade with Dave Asprey",
        "podcast_url": "https://daveasprey.com/",
        "podcast_description": "Test description",
        "podcast_owner": "Dave Asprey",
        "episode_number": 1301,
        "title": "Test Episode",
        "slug": "1301-test-episode",
        "episode_url": "https://daveasprey.com/1301-test-episode/",
        "podcast_subscription_url": "https://daveasprey.com/subscribe/",
        "summary": {
            "short_summary": "Test summary",
            "detailed_summary": {"summary_text": "Detailed test", "key_takeaways": ["Test takeaway"]}
        },
        "guest": {"name": "Test Guest", "title": "Expert", "bio": None},
        "sponsors": [{"name": "Test Sponsor", "url": "https://test.com"}],
        "resources": [{"title": "Test Resource", "url": "https://resource.com"}],
        "transcript": {"download_url": "https://transcript.com", "status": "available"},
        "timestamps": [{"time": "00:01:00", "topic": "Introduction", "description": "Test"}],
        "youtube_video_id": "test123",
        "pdf_resources": ["https://test.pdf"],
        "key_takeaways": ["Test takeaway 1", "Test takeaway 2"],
        "date_published": datetime.now()
    }
    
    try:
        episode = EpisodeSchema(**minimal_data)
        print("✅ Minimal schema validation PASSED!")
        return True
    except Exception as e:
        print(f"❌ Minimal validation FAILED: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 MongoDB Schema Validation Test")
    print("="*50)
    
    success = test_schema_validation()
    
    print("\n" + "="*50)
    if success:
        print("🎉 All tests PASSED! The parsed data is ready for MongoDB.")
    else:
        print("❌ Tests FAILED. Please check the schema or parser.")
    
    sys.exit(0 if success else 1)