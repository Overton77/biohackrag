from .mongo_schema_overwrite import init_beanie_with_pymongo, Transcript, Episode
import asyncio 
from config.mongo_setup import get_async_mongo_client 
import aiohttp
from bs4 import BeautifulSoup
from charset_normalizer import from_bytes  
from typing import Dict, Any, List

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

async def fetch_transcript_text(url: str, *, timeout: int = 30) -> str:
    """
    Fetch transcript text from a page (<p> tags inside <body>).
    Robust to odd encodings.
    """
    async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()

            # Skip non-HTML (e.g., PDFs)
            ctype = resp.headers.get("Content-Type", "")
            if "html" not in ctype.lower():
                # Return empty so caller can decide what to do
                return ""

            raw = await resp.read()

    # Prefer server-declared charset; otherwise detect
    encoding = resp.charset  # may be None
    if not encoding:
        result = from_bytes(raw).best()
        encoding = (result.encoding if result and result.encoding else "utf-8")

    html = raw.decode(encoding, errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    for br in soup.find_all("br"):
        br.replace_with("\n")

    body = soup.body or soup
    paragraphs = [p.get_text(separator=" ", strip=True) for p in body.find_all("p")]
    return "\n\n".join(p for p in paragraphs if p)

async def update_transcripts_with_full_text():
    await init_beanie_with_pymongo()

    episodes = await Episode.find({"transcript_url": {"$type": "string"}}).to_list(None)

    for ep in episodes:
        url = ep.transcript_url
        if not (isinstance(url, str) and url.startswith("https:")):
            continue

        try:
            text = await fetch_transcript_text(url)
            if not text:
                print(f"Skipped (non-HTML or empty) episode {ep.episode_number}")
                continue
        except Exception as e:
            print(f"Error fetching episode {ep.episode_number}: {e}")
            continue

        if ep.transcript:  
            # transcript is a reference, so update it directly
            transcript = await ep.transcript.fetch()  
            transcript.full_transcript = text
            await transcript.save()
            print(f"Updated transcript for episode {ep.episode_number}")
        else:
            print(f"No transcript linked for episode {ep.episode_number}") 

async def see_stats(limit: int = 50) -> Dict[str, Any]:
    """
    Return IDs of transcripts that have full_transcript and/or timeline,
    along with the episodes linked to those transcripts (episode _id + episode_number).
    """
    client = await get_async_mongo_client()
    db = client["biohack_agent"]
    transcripts = db["transcripts"]

    # Counts
    full_count = await transcripts.count_documents({"full_transcript": {"$ne": None}})
    timeline_count = await transcripts.count_documents({"timeline": {"$ne": None}})

    def lookup_pipeline(match_field: str):
        """
        Match transcripts where `match_field` exists,
        then $lookup episodes that reference this transcript in any of these ways:
          - episodes.transcript == transcript._id
          - episodes.transcript.$id == transcript._id   (DBRef)
          - transcript._id in episodes.transcripts       (array of ObjectIds)
        """
        return [
            {"$match": {match_field: {"$ne": None}}},
            {
                "$lookup": {
                    "from": "episodes",
                    "let": {"tid": "$_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$or": [
                                        {"$eq": ["$transcript", "$$tid"]},
                                        {"$eq": ["$transcript.$id", "$$tid"]},
                                        {"$in": ["$$tid", {"$ifNull": ["$transcripts", []]}]},
                                    ]
                                }
                            }
                        },
                        {"$project": {"_id": 1, "episode_number": 1}},
                    ],
                    "as": "episodes",
                }
            },
            {"$project": {"_id": 1, "episodes": 1}},
            {"$limit": limit},
        ]

    # Aggregate and collect
    full_docs_cursor = await transcripts.aggregate(lookup_pipeline("full_transcript"))
    timeline_docs_cursor = await transcripts.aggregate(lookup_pipeline("timeline"))

    full_docs: List[Dict[str, Any]] = [doc async for doc in full_docs_cursor]
    timeline_docs: List[Dict[str, Any]] = [doc async for doc in timeline_docs_cursor]

    # Optional: quick console summary
    print(f"Total transcripts with full transcripts: {full_count}")
    print(f"Total transcripts with timelines: {timeline_count}")

    print("\nSample (full_transcript):")
    for d in full_docs:
        eps = ", ".join(str(e.get("episode_number")) for e in d.get("episodes", []))
        print(f"  Transcript {d['_id']} -> Episodes [{eps}]")

    print("\nSample (timeline):")
    for d in timeline_docs:
        eps = ", ".join(str(e.get("episode_number")) for e in d.get("episodes", []))
        print(f"  Transcript {d['_id']} -> Episodes [{eps}]")

    return {
        "counts": {"full_transcript": full_count, "timeline": timeline_count},
        "full_transcript": full_docs,
        "timeline": timeline_docs,
    }



if __name__ == "__main__":
    # asyncio.run(update_transcripts_with_full_text())  
    asyncio.run(see_stats())  



