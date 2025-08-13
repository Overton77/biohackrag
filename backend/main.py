print('BIOHACKING AGENT') 

from fastapi import FastAPI, HTTPException, Depends, Request, Response  
from src.ingestion.indexing.transcript_ingestion_graph import run_graph 
from langchain_core.documents import Document  
from src.mongo_schemas import init_beanie_with_pymongo  




app = FastAPI() 




app.post("/ingest_transcript")
async def ingest_transcript(request: Request): 
    transcript = await request.json() 
    transcript_document = Document(page_content=transcript) 
    await run_graph(transcript_document) 
    return {"message": "Transcript ingested successfully"} 








