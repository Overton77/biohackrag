print('BIOHACKING AGENT') 

from fastapi import FastAPI, HTTPException, Depends, Request, Response  
 
from dotenv import load_dotenv  
from scraping_ops.find_episodes_selenium import update_episodes_url_selenium   
from contextlib import asynccontextmanager   
import contextlib  
from src.mongo_schema_overwrite import init_beanie_with_pymongo 
from src.store_transcript_links import process_all_missing_transcripts  
from pydantic import BaseModel  
from typing import Optional, List, Iterable, Dict, Any  
from webpage_parsing.webpage_ep_parsing import update_all_episodes   
import asyncio  
from mcp_server import mcp  
from mcp.client.streamable_http import streamablehttp_client  
from mcp import ClientSession 





load_dotenv()


async def lifespan(app: FastAPI):   
    app.state.session = None  
    app.state.mcp_transport_cm = None  
    app.state.mcp_session_cm = None  

    async with mcp.session_manager.run():
        app.state.mongo_client = await init_beanie_with_pymongo() 
        try:
            yield 
        finally:
            # Close MCP client session/transport if they were opened lazily
            try:
                if app.state.mcp_session_cm is not None:
                    await app.state.mcp_session_cm.__aexit__(None, None, None)
            finally:
                if app.state.mcp_transport_cm is not None:
                    await app.state.mcp_transport_cm.__aexit__(None, None, None)
            await app.state.mongo_client.close()  
    


app = FastAPI(title="Biohack Agent", lifespan=lifespan)  


async def get_mcp_session(app: FastAPI) -> ClientSession:
    if getattr(app.state, "session", None) is not None:
        return app.state.session

    # Lazily create a persistent streamable HTTP client connection to the mounted server
    transport_cm = streamablehttp_client("http://localhost:8000/mcp")
    read_stream, write_stream, _ = await transport_cm.__aenter__()
    session_cm = ClientSession(read_stream, write_stream)
    session = await session_cm.__aenter__()
    await session.initialize()

    app.state.mcp_transport_cm = transport_cm
    app.state.mcp_session_cm = session_cm
    app.state.session = session
    return session

class UpdateRequest(BaseModel):
    update: bool

@app.post("/add_episodes_selenium")
async def update_episodes(request: Request,update_data: UpdateRequest):
    if update_data.update:
        updated_episodes = await update_episodes_url_selenium(request.app.state.mongo_client)
        return {"message": "Episodes updated successfully", "updated_episodes": updated_episodes}
    else:
        return {"message": "Update not requested"}  

class UpdateTranscriptLinksRequest(BaseModel): 
    limit: Optional[int] = None  

@app.post("/update_transcript_links") 
async def update_transcript_links(request: Request, update_data: UpdateTranscriptLinksRequest): 
    await process_all_missing_transcripts(request.app.state.mongo_client, update_data.limit) 
    return {"message": "Transcript links updated successfully"} 

@app.post("/ingest_transcript")
async def ingest_transcript(request: Request):  

    print(request) 

    return {"message": "Transcript ingested successfully"}   

# Test this on one tomorrow  

class SummarizeEpisodeDumpRequest(BaseModel):  
    timeline_string: str  
    full_transcript_string: str    
    high_level_overview_string: str   

@app.post("/summarize_episode_dump") 
async def summarize_episode_dump(request: Request, summarize_episode_dump_request: SummarizeEpisodeDumpRequest): 
    pass 



@app.post("/update_episodes_webpage") 
async def update_episodes_transcripts(request: Request): 
    await update_all_episodes(request.app.state.mongo_client) 
    return {"message": "Episodes transcripts updated successfully"} 




app.mount("/mcp", mcp.streamable_http_app())


@app.get("/check_mcp_connection") 
@app.post("/check_mcp_connection") 
async def check_mcp_connection(request: Request):   
    session = await get_mcp_session(request.app)  
    print(session)  
    if session is None: 
        raise HTTPException(status_code=500, detail="MCP connection not established") 
    return {"message": "MCP connection established"} 




if __name__ == "__main__":  
    import uvicorn 
    uvicorn.run(app, host="0.0.0.0", port=8000) 








