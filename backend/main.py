print("BIOHACKING AGENT")

import os
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Optional, List 

from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv

from src.mongo_schema_overwrite import init_beanie_with_pymongo, Episode, Transcript 
from scraping_ops.find_episodes_selenium import update_episodes_url_selenium
from src.store_transcript_links import process_all_missing_transcripts
from webpage_parsing.webpage_ep_parsing import update_all_episodes

# MCP server & client pieces
from mcp_server import mcp  # FastMCP(name="BiohackAgent", streamable_http_path="/")
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession 
from langchain_google_genai import ChatGoogleGenerativeAI   
from langchain_mcp_adapters.tools import load_mcp_tools  
from langchain_core.prompts import PromptTemplate 
from langchain_core.output_parsers import StrOutputParser  
from src.store_full_transcripts import fetch_transcript_text 




load_dotenv()

# Build the MCP ASGI sub-app (its internal base path is "/")
mcp_app = mcp.streamable_http_app()

@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        # Start the MCP sub-app lifespan so the StreamableHTTP session manager runs
        await stack.enter_async_context(mcp_app.router.lifespan_context(mcp_app))

        # Your app startup (DB, caches, etc.)
        app.state.mongo_client = await init_beanie_with_pymongo() 
        app.state.google_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", api_key=os.getenv("GOOGLE_FREE_API_KEY"))

        # Do NOT self-connect an MCP client during startup
        yield
        # ExitStack will gracefully close all contexts

app = FastAPI(title="Biohack Agent", lifespan=combined_lifespan)

# Mount MCP at "/mcp" so external endpoints are:
#   /mcp           (meta)
#   /mcp/sse
#   /mcp/messages
app.mount("/mcp", mcp_app)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class UpdateRequest(BaseModel):
    update: bool

class UpdateTranscriptLinksRequest(BaseModel):
    limit: Optional[int] = None

class SummarizeEpisodeDumpRequest(BaseModel):
    timeline_string: str
    full_transcript_string: str
    high_level_overview_string: str

# ---------------------------------------------------------------------------
# Helper: return an async context manager (NOT async def)
# ---------------------------------------------------------------------------
MCP_BASE = os.getenv("MCP_BASE_URL", "http://localhost:8000/mcp")

def open_mcp_session():
    """
    Return the streamable HTTP async context manager for the mounted MCP server.
    This function is intentionally NOT 'async def' so it can be used as:
        async with open_mcp_session() as (read, write, _):
            ...
    """
    return streamablehttp_client(MCP_BASE)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/add_episodes_selenium")
async def update_episodes(request: Request, update_data: UpdateRequest):
    if update_data.update:
        updated = await update_episodes_url_selenium(request.app.state.mongo_client)
        return {"message": "Episodes updated successfully", "updated_episodes": updated}
    return {"message": "Update not requested"}

@app.post("/update_transcript_links")
async def update_transcript_links(request: Request, update_data: UpdateTranscriptLinksRequest):
    await process_all_missing_transcripts(request.app.state.mongo_client, update_data.limit)
    return {"message": "Transcript links updated successfully"}

@app.post("/ingest_transcript")
async def ingest_transcript(request: Request):
    # Hook your ingestion pipeline here
    return {"message": "Transcript ingested successfully"}

@app.post("/summarize_episode_dump")
async def summarize_episode_dump(request: Request, body: SummarizeEpisodeDumpRequest):
    # Open a transient MCP client session to call prompts/tools
    async with open_mcp_session() as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Example: list available prompts
            prompts = await session.list_prompts()

            # Example (commented): call your tool with structured args
            # result = await session.call_tool("get_product_information", {
            #     "name": "...",
            #     "cost": "...",
            #     "buy_links": "...",
            #     "description": "...",
            #     "features": ["..."],
            #     "protocols": ["..."],
            #     "benefits_as_stated": ["..."]
            # })
            # return result

            return {"message": "Ready", "available_prompts": [p.name for p in prompts.prompts]}


async def find_episodes_with_full_transcript_and_timeline() -> List[Episode]:
    # 1) Get qualifying transcript ids 
    await init_beanie_with_pymongo() 
    transcripts = await Transcript.find({
        "full_transcript": {"$exists": True, "$ne": None},
        "timeline": {"$exists": True, "$ne": None},
    }).to_list()
    transcript_ids = [t.id for t in transcripts if getattr(t, "id", None) is not None]
    if not transcript_ids:
        return []

    # 2) Query Episodes by the Link's id (DBRef-like): transcript.$id IN transcript_ids
    episodes = await Episode.find({
        "transcript.$id": {"$in": transcript_ids}
    }).to_list()

    return episodes 


class EpisodeSummary(BaseModel): 
    episode_id: Optional[str] = None   

@app.get("episode_summaries") 
async def episode_summaries(request: Request, episode_request: EpisodeSummary):   

    if episode_request.episode_id: 
        episode = await Episode.get(episode_request.episode_id)  
        return { 
            "episode_id": episode.id,
            "episode_number": episode.episode_number,
            "master_summary": episode.master_summary,
        } 
    else: 
        episodes = await Episode.find({"master_summary": {"$exists": True, "$ne": None}}).to_list()
        return { 
            "message": "Episodes that are summarized successfully. Ready for vector store",   
            "status": "ok",

            "episodes": [
                {
                    "episode_id": episode.id,
                    "episode_number": episode.episode_number,
                    "master_summary": episode.master_summary,
                }
                for episode in episodes
            ]
        }
  

@app.post("/summarize_transcripts")
async def summarize_transcripts(request: Request):
    async with open_mcp_session() as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session: 
            await session.initialize()

            # Find recent eligible episodes
            episodes = await Episode.find({
                "transcript": {"$exists": True, "$ne": None},
                "timeline": {"$exists": True, "$ne": None},
                "webpage_summary": {"$exists": True, "$ne": None},
            }).sort("-episode_number").limit(30).to_list()

            if not episodes:
                return {"message": "No eligible episodes found to summarize."}

            results = []

            for episode in episodes:  
                try:
                    timeline = episode.timeline or []
                    timeline_string = "\n".join([
                        f"{(t.get('time') or t.get('timestamp') or '')}: {(t.get('description') or t.get('text') or '')}"
                        for t in timeline
                    ])

                    print('Timeline string', timeline_string)

                    transcript_text = ""
                    transcript_url = getattr(episode, "transcript_url", None)
                    if transcript_url:
                        try:
                            transcript_text = await fetch_transcript_text(transcript_url)
                        except Exception as e:
                            print(f"Error fetching transcript URL for episode {episode.episode_number}: {e}")

                    # Fallback to linked transcript document
                    if not transcript_text and episode.transcript is not None:
                        try:
                            linked_transcript = await episode.transcript.fetch()
                            transcript_text = linked_transcript.full_transcript or ""
                        except Exception as e:
                            print(f"Error fetching linked transcript for episode {episode.episode_number}: {e}")

                    if not transcript_text:
                        print(f"No transcript text for episode {episode.episode_number}; skipping")
                        continue

                    print("Fetched transcript text", transcript_text[:200])
                    print("\n---------------")

                    full_transcript = transcript_text
                    high_level_overview = episode.webpage_summary or ""

                    transcript_prompt = await session.get_prompt(
                        "transcript_summary",
                        {
                            "full_transcript": full_transcript,
                            "timeline": timeline_string,
                            "high_level_overview": high_level_overview,
                        },
                    )

                    # Rendered prompt text to feed to LLM
                    prompt_text = transcript_prompt.messages[0].content.text

                    # Simple passthrough template to feed full prompt string
                    transcript_prompt_template = PromptTemplate.from_template(prompt_text)
                    google_llm = request.app.state.google_llm
                    chain = transcript_prompt_template | google_llm | StrOutputParser()

                    result = await chain.ainvoke({"input": "Start summarization process"}) 

                    episode.master_summary = result
                    await episode.save()
                    print('Episode saved with new master_summary')
                    results.append({
                        "episode_id": str(getattr(episode, 'id', '')),
                        "episode_number": episode.episode_number,
                        "status": "ok",
                    })
                except Exception as e:
                    print(f"Error summarizing episode {episode.episode_number}: {e}")
                    results.append({
                        "episode_id": str(getattr(episode, 'id', '')),
                        "episode_number": episode.episode_number,
                        "status": "error",
                        "error": str(e),
                    })

            return {"message": "Summarization run complete", "results": results}




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)