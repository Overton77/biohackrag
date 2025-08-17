print('BIOHACKING AGENT') 

from fastapi import FastAPI, HTTPException, Depends, Request, Response  
 
from dotenv import load_dotenv  
from scraping_ops.find_episodes_selenium import update_episodes_url_selenium   
from contextlib import asynccontextmanager   
from src.mongo_schema_overwrite import init_beanie_with_pymongo 
from src.store_transcript_links import process_all_missing_transcripts  
from pydantic import BaseModel  
from typing import Optional   
from webpage_parsing.webpage_ep_parsing import update_all_episodes   
import asyncio 


load_dotenv()


async def lifespan(app: FastAPI): 
    app.state.mongo_client = await init_beanie_with_pymongo() 
    yield 
    await app.state.mongo_client.close() 


app = FastAPI(title="Biohack Agent", lifespan=lifespan)  


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

app.post("/ingest_transcript")
async def ingest_transcript(request: Request):  

    print(request) 

    return {"message": "Transcript ingested successfully"}   

# Test this on one tomorrow  



@app.post("/update_episodes_webpage") 
async def update_episodes_transcripts(request: Request): 
    await update_all_episodes(request.app.state.mongo_client) 
    return {"message": "Episodes transcripts updated successfully"} 






if __name__ == "__main__":  
    import uvicorn 
    uvicorn.run(app, host="0.0.0.0", port=8000) 








