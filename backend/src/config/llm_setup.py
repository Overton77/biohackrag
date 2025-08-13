from llama_index.llms.google_genai import GoogleGenAI 
from dotenv import load_dotenv  
from llama_index.core.tools import FunctionTool  
from llama_index.core.llms import ChatMessage    
from llama_index.core.prompts import RichPromptTemplate 


import asyncio 
import os  

load_dotenv()


free_tier_model = GoogleGenAI(model="gemini-2.0-flash",api_key=os.getenv("GOOGLE_FREE_API_KEY")) 




