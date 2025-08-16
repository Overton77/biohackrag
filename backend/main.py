print('BIOHACKING AGENT') 

from fastapi import FastAPI, HTTPException, Depends, Request, Response  
 
from dotenv import load_dotenv 
import asyncio 


load_dotenv()




app = FastAPI() 




app.post("/ingest_transcript")
async def ingest_transcript(request: Request):  

    print(request) 

    return {"message": "Transcript ingested successfully"}  


if __name__ == "__main__":  
    import uvicorn 
    uvicorn.run(app, host="0.0.0.0", port=8000) 








