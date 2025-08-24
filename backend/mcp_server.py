# mcp_server.py
from mcp.server.fastmcp import FastMCP 
from src.ingestion.indexing.prompts.transcript_prompts import master_summary_prompt   
from src.schemas.transcript_llm_schemas import ProductOutput, BusinessOutput 
from typing import List 



mcp = FastMCP(name="BiohackAgent")   


@mcp.prompt(title="Transcript Summary") 
def transcript_summary(timeline: str, full_transcript: str, high_level_overview: str) -> str:  
    return master_summary_prompt.format(timeline=timeline, full_transcript=full_transcript, high_level_overview=high_level_overview)  



@mcp.tool() 
def get_product_information(name: str, cost: str, buy_links: str, description: str, features: List[str], protocols: List[str], benefits_as_stated: List[str]) -> ProductOutput:  
    """ 
    This tool is used to extract product information from a summary of a biohacking podcast transcript. 
    If any of the arguments are not found in the summary, return the string "unknown" for that argument. 
    """  

    
    return ProductOutput(name=name, cost=cost, buy_links=buy_links, description=description, features=features, protocols=protocols, benefits_as_stated=benefits_as_stated) 


    







