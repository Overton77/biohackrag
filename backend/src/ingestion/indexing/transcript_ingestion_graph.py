from langchain_core.prompts import PromptTemplate 
from langchain_core.documents import Document    
from langchain_core.tools import Tool    
from langchain_core.output_parsers import StrOutputParser  
import os   
from langgraph.graph import StateGraph, START, END 
from langchain_core.prompts import PromptTemplate    
from langchain_core.runnables import Runnable     
import asyncio 
from typing import TypedDict, Dict, Any, Optional, List, Literal 
from langchain_google_vertexai.model_garden import ChatAnthropicVertex 
from langchain_google_genai import ChatGoogleGenerativeAI 
from langchain_core.tools import Tool 
from langchain_core.output_parsers import StrOutputParser 
from langchain_core.prompts import PromptTemplate 
from langchain_core.runnables import Runnable 
import json  
from dotenv import load_dotenv   
from pydantic import BaseModel, Field   
from langchain_core.tools import tool   
from ingestion.indexing.prompts.transcript_prompts import (
    product_information_structured_prompt,
    medical_treatment_structured_prompt,
    claims_made_structured_prompt,
    businesses_entities_structured_prompt,
    product_information_summary_prompt,
    medical_treatment_summary_prompt,
    high_level_overview_summary_prompt,
    claims_made_summary_prompt,
    businesses_entities_summary_prompt,
    compounds_summary_prompt,
) 
from ingestion.indexing.tools.transcript_ingestion_tools import (
    submit_product_information,
    submit_medical_treatment,
    submit_claims_made,
    submit_businesses_entities,
    submit_compound,
)  
from mongo_schemas import (
    ProductOutput,
    
    TreatmentOutput,
  
    ClaimOutput,
  
    BusinessOutput,
 
    CompoundOutput,
    Product, 
    init_beanie_with_pymongo, 
   
) 



import re 
import nest_asyncio 
load_dotenv()   

nest_asyncio.apply()    


anthropic_vertex = ChatAnthropicVertex(model="claude-3-5-sonnet-20240620")   
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", api_key=os.getenv("GOOGLE_FREE_API_KEY")) 



def extract_attributions(summary_text: str) -> str:
    matches = re.findall(r"<attribution>(.*?)</attribution>", summary_text, re.DOTALL | re.IGNORECASE)
    return "\n\n".join(m.strip() for m in matches) if matches else ""



MODEL_MAP = {
    "product_information": ProductOutput,
    "medical_treatment": TreatmentOutput,
    "claims_made": ClaimOutput,
    "businesses_entities": BusinessOutput,
    "compounds": CompoundOutput,
} 


TOOL_MAP = { 
    "product_information": submit_product_information,
    "medical_treatment": submit_medical_treatment,
    "claims_made": submit_claims_made,
    "businesses_entities": submit_businesses_entities,
    "compounds": submit_compound,
}



# ---------------------------
# Summarization prompts
# ---------------------------
SUMMARY_PROMPTS: Dict[str, str] = {
    "product_information": (
        product_information_summary_prompt.template
    ), 
    "medical_treatment": (
        medical_treatment_summary_prompt.template
    ),
    "high_level_overview": (
        high_level_overview_summary_prompt.template
    ),
    "claims_made": (
        claims_made_summary_prompt.template
    ),
    "businesses_entities": (
        businesses_entities_summary_prompt.template
    ), 
    "compounds": ( 
        compounds_summary_prompt.template 
    )
}


# ---------------------------
# Structured extraction prompts
# ---------------------------
STRUCTURED_EXTRACTOR_PROMPTS: Dict[str, str] = {
    "product_information": (
        product_information_structured_prompt.template
    ),
    "medical_treatment": (
        medical_treatment_structured_prompt.template
    ),
   
    "claims_made": (
      claims_made_structured_prompt.template
    ),
    "businesses_entities": (
        businesses_entities_structured_prompt.template
    ),
} 




class TranscriptIngestionState(TypedDict, total=False):
    input: str
    aggregate_summary: str
    final_summary: str   
    summary_prompts_dict: Dict[str, str]
    full_transcript: Document  
    product_information: str
    medical_treatment: str 
    structured_tool_call_dict: Dict[str, Any] 
    high_level_overview: str
    claims_made: str
    businesses_entities: str 
    structured_output_prompts_dict: Dict[str, str]
    structured_output_dict: Dict[str, Any] 
    structured_output_tool_dict: Dict[str, Tool]   
    anthropic_vertex_llm: ChatAnthropicVertex   
    google_llm: ChatGoogleGenerativeAI   
    structured_output_models: Dict[str, Any] 



def parse_tool_call_or_json(message, tool_map: Dict[str, Tool]):
    """Robustly extract a tool call and arguments from a model message.

    Preference order:
    1) message.tool_calls (LangChain-normalized)
    2) message.additional_kwargs["function_call"] (OpenAI-style)
    3) JSON in message.content (strip code fences)
    Returns: (callable_tool, args_dict) or (None, None)
    """
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        call = tool_calls[0]
        name = call.get("name")
        args = call.get("args", {})
        return tool_map.get(name), args

    additional_kwargs = getattr(message, "additional_kwargs", {}) or {}
    function_call = additional_kwargs.get("function_call")
    if isinstance(function_call, dict):
        name = function_call.get("name")
        raw_args = function_call.get("arguments")
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
        except Exception:
            args = {}
        return tool_map.get(name), args

    content = getattr(message, "content", None)
    if isinstance(content, str) and content:
        text = content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else ""
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
        text = text.strip()
        try:
            args = json.loads(text)
            return None, args
        except Exception:
            return None, None
    return None, None


async def return_tool_call_dict(tool_response, tool_map): 
    tool_to_call, arguments_loaded = parse_tool_call_or_json(tool_response, tool_map)
    print(arguments_loaded)
    if tool_to_call and arguments_loaded is not None:
        return tool_to_call(**arguments_loaded)
    return arguments_loaded 


def return_tool_call_dict_sync(tool_response, tool_map): 
    tool_to_call, arguments_loaded = parse_tool_call_or_json(tool_response, tool_map)
    print(arguments_loaded)
    return (tool_to_call, arguments_loaded)





initial_state: TranscriptIngestionState = {  
    "input": "Begin the Transcript Chain",   
    "aggregate_summary": "",
    "final_summary": "",
    "summary_prompts_dict": SUMMARY_PROMPTS, 
    "structured_output_prompts_dict": STRUCTURED_EXTRACTOR_PROMPTS,
    "full_transcript": "",
    "product_information": "",
    "medical_treatment": "",
    "high_level_overview": "",
    "claims_made": "",
    "businesses_entities": "", 
    "structured_tool_call_dict": {},
    "structured_output_tool_dict": TOOL_MAP,
    "anthropic_vertex_llm": anthropic_vertex,
    "google_llm": llm,
    "structured_output_models": {   
        "product_information": llm.bind_tools([submit_product_information]),
        "medical_treatment": llm.bind_tools([submit_medical_treatment]),
        "claims_made": anthropic_vertex.bind_tools([submit_claims_made]),
        "businesses_entities": anthropic_vertex.bind_tools([submit_businesses_entities]),
        "compounds": anthropic_vertex.bind_tools([submit_compound]),
    },
}




async def generate_summaries(state: TranscriptIngestionState) -> TranscriptIngestionState:  

    full_transcript = state.get("full_transcript", "")   

    summary_prompts_dict = state.get("summary_prompts_dict", {})    


    for summary_key, summary_prompt in summary_prompts_dict.items():   

        prompt_template = PromptTemplate.from_template(summary_prompt)   
        
        chain = prompt_template | state.get("google_llm") | StrOutputParser()   
        response = await chain.ainvoke({"transcript": full_transcript.page_content})   
        state[summary_key] = response   
        state["aggregate_summary"] += f"\n{summary_key}. {response}"   
        
    return {**state}     

async def structured_extraction(state: TranscriptIngestionState) -> TranscriptIngestionState:   

    structured_output_tools = state.get("structured_output_tool_dict", {})    

    structured_output_models = state.get("structured_output_models", {})   

    structured_extractor_prompts_dict = state.get("structured_output_prompts_dict", {})    

    for key, tool in structured_output_tools.items(): 
        structured_model = structured_output_models.get(key, None)    
        prompt = structured_extractor_prompts_dict.get(key, "")    


        if structured_model is None or prompt is None:  
            return None    
        
        prompt_template = PromptTemplate.from_template(prompt) 
        if state.get(key, "") == "": continue  

        specific_summary = state.get(key, "")    
        chain = prompt_template | structured_model     
        response = await chain.ainvoke({"summary": specific_summary})    

        tool_to_call, arguments_loaded = await return_tool_call_dict(response, structured_output_tools)  

        state["structured_tool_call_dict"][key] = arguments_loaded  





        return {**state} 




graph = StateGraph(TranscriptIngestionState)
graph.add_node("generate_summaries", generate_summaries)
graph.add_node("structured_extraction", structured_extraction)

graph.add_edge(START, "generate_summaries")
graph.add_edge("generate_summaries", "structured_extraction")
graph.add_edge("structured_extraction", END)

app = graph.compile()





async def run_graph(transcript: Document):
    # Stream steps
    async for step in app.astream({"full_transcript": transcript.page_content}, **initial_state ): 
        print("STEP KEYS:", list(step.keys()))

    # Get final state
    final_state = await app.ainvoke(initial_state)

    # Print full state
    print("\n=== Full State ===")
    for key, value in final_state.items():
        print(f"\n[{key}]")
        print(value)

    # Print structured output
    print("\n=== Structured Output ===")
    if "structured_tool_call_dict" in final_state:
        for key, value in final_state["structured_tool_call_dict"].items():
            print(f"\n[{key}]")
            print(value)

    # Print summaries
    print("\n=== Individual Summaries ===")
    summary_keys = ["product_information", "medical_treatment", "high_level_overview", 
                   "claims_made", "businesses_entities"]
    for key in summary_keys:
        print(f"\n## {key}")
        print(final_state.get(key, '')[:2000])  # Trim if too long

    # Print aggregate summary
    print("\n=== Aggregate Summary ===")
    print(final_state.get("aggregate_summary", '')[:4000])  # Show first 4000 chars


# asyncio.run(run_graph())  



if __name__ == "__main__":  


    # Doing a test run here in the file. 

    with open(r"C:\Users\Pinda\Proyectos\BioHackAgent\src\ingestion\indexing\transcript_test.txt", "r") as f:  
        transcript = f.read()  

    transcript_document = Document(page_content=transcript) 

    product_summary = product_information_summary_prompt 

    


    test_chain = product_summary | llm | StrOutputParser() 


    response = test_chain.invoke({"transcript": transcript_document.page_content}) 

    print(response) 



    llm_with_tools = llm.bind_tools([submit_product_information])  

    next_chain = product_information_structured_prompt | llm_with_tools  

    next_response = next_chain.invoke({"summary": response})  

    print(next_response)   

    py_model = return_tool_call_dict_sync(next_response, TOOL_MAP)  


    async def store_product_information(py_model: ProductOutput): 
        await init_beanie_with_pymongo() 

        product = Product(
            name=py_model.name,
            description=py_model.description,
            features=py_model.features,
            protocols=py_model.protocols,
            benefits_as_stated=py_model.benefits_as_stated,
            attribution_quotes=py_model.attribution_quotes,
        )   

        await product.save() 

    asyncio.run(store_product_information(py_model)) 







