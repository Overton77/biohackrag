from typing import Dict, Any, List, Optional, Literal
import os
import re
import asyncio
import logging

from pydantic import BaseModel, Field

from llama_index.core.prompts import RichPromptTemplate 
from llama_index.llms.google_genai import GoogleGenAI 
from src.config.llm_setup import free_tier_model   
from llama_index.core.agent.workflow import FunctionAgent  
from llama_index.core import SimpleDirectoryReader    
from src.mongo_schemas import init_beanie_with_pymongo, Transcript, Business, Product, Person, Claim, Treatment, CaseStudy, SuccessStory, Channel, Episode, BioMarker, Protocol, BioHack  



logger = logging.getLogger(__name__)








def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_attributions(summary_text: str) -> str:
    matches = re.findall(r"<attribution>(.*?)</attribution>", summary_text, re.DOTALL | re.IGNORECASE)
    return "\n\n".join(m.strip() for m in matches) if matches else ""


class AttributionQuote(BaseModel):
    text: str = Field(..., description="Short quote from summary/transcript")
    timestamp: Optional[str] = None
    speaker: Optional[str] = None
    chunk_id: Optional[str] = None


class ProductItem(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    protocols: List[str] = Field(default_factory=list)
    benefits_as_stated: List[str] = Field(default_factory=list)
    attribution: List[AttributionQuote] = Field(default_factory=list)


class ProductSummary(BaseModel):
    products: List[ProductItem] = Field(default_factory=list)


class TreatmentItem(BaseModel):
    name: Optional[str] = None
    procedure_or_protocol: List[str] = Field(default_factory=list)
    outcomes_as_reported: List[str] = Field(default_factory=list)
    risks_or_contraindications: List[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    attribution: List[AttributionQuote] = Field(default_factory=list)


class MedicalSummary(BaseModel):
    treatments: List[TreatmentItem] = Field(default_factory=list)


class SectionItem(BaseModel):
    title_or_topic: Optional[str] = None
    approx_time_range: Optional[str] = Field(None, description="e.g., 00:00–05:30")


class HighLevelOverview(BaseModel):
    purpose: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    main_sections: List[SectionItem] = Field(default_factory=list)
    key_takeaways: List[str] = Field(default_factory=list)
    attribution: List[AttributionQuote] = Field(default_factory=list)


class ClaimItem(BaseModel):
    speaker: Optional[str] = None
    claim_text: str
    claim_type: Literal["causal", "quantitative", "experiential", "other"] = "other"
    evidence_present_in_transcript: Literal["yes", "no"] = "no"
    attribution: List[AttributionQuote] = Field(default_factory=list)


class ClaimsSummary(BaseModel):
    claims: List[ClaimItem] = Field(default_factory=list)


class CompanyItem(BaseModel):
    canonical_name: str
    aliases: List[str] = Field(default_factory=list)
    role_or_relevance: Optional[str] = None
    first_timestamp: Optional[str] = None
    attribution: List[AttributionQuote] = Field(default_factory=list)


class CompaniesSummary(BaseModel):
    entities: List[CompanyItem] = Field(default_factory=list)


MODEL_MAP = {
    "product_information": ProductSummary,
    "medical_treatment": MedicalSummary,
    "high_level_overview": HighLevelOverview,
    "claims_made": ClaimsSummary,
    "businesses_entities": CompaniesSummary,
}


# ---------------------------
# Summarization prompts
# ---------------------------
SUMMARY_PROMPTS: Dict[str, str] = {
    "product_information": (
        "The intention is to parse the following transcript and extract information about products. "
        "Extract and summarize all information related to products, including product names, descriptions, "
        "features, and any discussions about product performance or use. Present the summary as a list of key "
        "product details. For each product, include an <attribution> section containing short quotes and timestamps "
        "directly from the transcript.\n\nTranscript:\n{{ transcript }}"
    ),
    "medical_treatment": (
        "The intention is to parse the following transcript and extract information about medical treatments or services. "
        "Extract and summarize all content related to medical treatments or services, including treatment names, procedures, "
        "protocols, patient experiences, and any relevant outcomes. Present this summary as a concise, organized overview. "
        "For each treatment or service, include an <attribution> section with short quotes and timestamps from the transcript.\n\n"
        "Transcript:\n{{ transcript }}"
    ),
    "high_level_overview": (
        "The intention is to parse the following transcript and provide a high-level summary. "
        "Highlight the main topics discussed, key participants, and the general flow of the conversation. "
        "The summary should capture the most important points and the overall purpose of the transcript. "
        "At the end, add an <attribution> section with 3–5 quotes and timestamps that support your summary.\n\n"
        "Transcript:\n{{ transcript }}"
    ),
    "claims_made": (
        "The intention is to parse the following transcript and identify explicit claims. "
        "Identify and summarize all explicit claims made in the transcript. For each claim, note who made it (if possible) "
        "and briefly describe the supporting evidence or reasoning provided. Include an <attribution> section with short quotes "
        "and timestamps for each claim.\n\nTranscript:\n{{ transcript }}"
    ),
    "businesses_entities": (
        "The intention is to parse the following transcript and extract information about businesses and entities. "
        "List all businesses, organizations, or notable entities mentioned in the transcript. For each entity, provide a brief "
        "description of their role or relevance to the discussion, as stated or implied. Include an <attribution> section with "
        "a short quote and timestamp for each entity.\n\nTranscript:\n{{ transcript }}"
    ),
}


# ---------------------------
# Structured extraction prompts
# ---------------------------
STRUCTURED_EXTRACTOR_PROMPTS: Dict[str, str] = {
    "product_information": (
        "You will extract structured product data from a targeted summary.\n"
        "Use ONLY the content in the provided summary—do not add outside facts.\n"
        "Populate the ProductSummary schema fields faithfully. If data is missing, leave fields empty.\n"
        "If the summary includes quotes/timestamps (e.g., inside <attribution>), map them into the structured 'attribution' list.\n\n"
        "TARGETED SUMMARY:\n{{ summary }}\n"
    ),
    "medical_treatment": (
        "You will extract structured medical treatment/service data from a targeted summary.\n"
        "Use ONLY the content in the provided summary—no outside facts.\n"
        "Populate the MedicalSummary schema, set 'confidence' (high/medium/low) based on how explicit the summary is, "
        "and map quotes/timestamps into the 'attribution' list.\n\n"
        "TARGETED SUMMARY:\n{{ summary }}\n"
    ),
    "high_level_overview": (
        "You will extract a high-level overview from a targeted summary.\n"
        "Use ONLY the content in the provided summary. Populate the HighLevelOverview schema: purpose, participants, main_sections "
        "(with approx time ranges if present), and 5–7 key_takeaways when available. Map quotes/timestamps into 'attribution'.\n\n"
        "TARGETED SUMMARY:\n{{ summary }}\n"
    ),
    "claims_made": (
        "You will extract explicit claims from a targeted summary.\n"
        "Use ONLY the summary—no outside facts. Populate the ClaimsSummary schema. For each claim, set speaker (if given), "
        "claim_text (≤20 words if possible), claim_type (causal/quantitative/experiential/other), "
        "evidence_present_in_transcript ('yes' or 'no'), and add quotes/timestamps to 'attribution'.\n\n"
        "TARGETED SUMMARY:\n{{ summary }}\n"
    ),
    "businesses_entities": (
        "You will extract businesses/organizations/entities from a targeted summary.\n"
        "Use ONLY the summary—no outside facts. Populate the CompaniesSummary schema with canonical_name, aliases (if any), "
        "role_or_relevance (≤12 words), first_timestamp if present, and quotes/timestamps in 'attribution'.\n\n"
        "TARGETED SUMMARY:\n{{ summary }}\n"
    ),
} 



product_agent = FunctionAgent( 
    name="product_extractor", 
    system_prompt="You are a helpful assistant that extracts product information from a transcript.",  
    tools=[], 
    output_cls=ProductSummary,  
    llm=free_tier_model,  
) 


medical_treatment_agent = FunctionAgent( 
    name="medical_treatment_extractor", 
    system_prompt="You are a helpful assistant that extracts medical treatment information from a transcript.",  
    tools=[], 
    output_cls=MedicalSummary,  
    llm=free_tier_model,  
) 


high_level_overview_agent = FunctionAgent(   
    name="high_level_overview_extractor", 
    system_prompt="You are a helpful assistant that extracts a high-level overview from a transcript.",  
    tools=[], 
    output_cls=HighLevelOverview,  
    llm=free_tier_model,  
)  


business_entities_agent = FunctionAgent( 
    name="business_entities_extractor", 
    system_prompt="You are a helpful assistant that extracts business entities from a transcript.",  
    tools=[], 
    output_cls=CompaniesSummary,  
    llm=free_tier_model,  
)  


claims_made_agent = FunctionAgent( 
    name="claims_made_extractor", 
    system_prompt="You are a helpful assistant that extracts claims made from a transcript.",  
    tools=[], 
    output_cls=ClaimsSummary,  
    llm=free_tier_model,  
)   


agent_dict = { 
    "product_information": product_agent, 
    "medical_treatment": medical_treatment_agent, 
    "high_level_overview": high_level_overview_agent, 
    "businesses_entities": business_entities_agent, 
    "claims_made": claims_made_agent, 
}





async def generate_summaries(llm: GoogleGenAI, transcript: str, prompts: Dict[str, str]) -> Dict[str, str]:
    async def _one(key: str, tmpl: str) -> tuple[str, str]:
        template = RichPromptTemplate(tmpl)
        prompt_str = template.format(transcript=transcript)
        logger.debug("Generating summary for key='%s' with prompt length=%d", key, len(prompt_str))
        resp = await llm.acomplete(prompt_str) 
        logger.debug("Received summary for key='%s' with text length=%d", key, len(resp.text) if hasattr(resp, "text") and resp.text else 0)
        return key, resp.text

    tasks = [_one(k, v) for k, v in prompts.items()]
    results = await asyncio.gather(*tasks)
    return {k: v for k, v in results}


async def run_structured_extraction(agent_dict: Dict[str, FunctionAgent], summaries: Dict[str, str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, model_cls  in MODEL_MAP.items():
        tmpl = STRUCTURED_EXTRACTOR_PROMPTS[key]
        template = RichPromptTemplate(tmpl)
        prompt_str = template.format(summary=summaries.get(key, ""))
        logger.debug("Structured extraction for key='%s' using agent and model='%s'", key, model_cls.__name__)
        agent = agent_dict[key]
        response = await agent.run(prompt_str)   # returns Pydantic object 
        pydantic_model = response.get_pydantic_model(model_cls) 
        out[key] = pydantic_model  
        logger.debug("Structured extraction complete for key='%s'", key)
    return out


async def main() -> None:
    # 1) Load transcript  

    async_mongo_client = await init_beanie_with_pymongo()  



    episode_number = 1333 

    episode_url = "https://daveasprey.com/1301-ewot/" 

    transcript_url = "https://daveasprey.com/wp-content/uploads/2025/07/EP_1301_BRAD_PITZELE_Transcript.html"
    repo_root = os.getcwd()
    transcript_path = os.path.join(repo_root, "transcript_test.txt") 

    documents = await SimpleDirectoryReader(input_files=[transcript_path]).aload_data()

    full_transcript = clean_whitespace(documents[0].text)

    logger.info("Loaded transcript from '%s' (characters=%d)", transcript_path, len(full_transcript))

    # 3) LLM (requires OPENAI_API_KEY in environment)
    llm = free_tier_model 

    # 4) Build state and generate summaries
    state: Dict[str, Any] = {
        "input": "Begin the summary chain",
        "aggregate_summary": "",
        "final_summary": "",
        "prompts_dict": SUMMARY_PROMPTS,
        "full_transcript": full_transcript,
        "documents": documents,
        "transcript_retriever": None,
        # placeholders for outputs
        "product_information": "",
        "medical_treatment": "",
        "high_level_overview": "",
        "claims_made": "",
        "businesses_entities": "",
        "attribution_product_information": "",
        "attribution_medical_treatment": "",
        "attribution_high_level_overview": "",
        "attribution_claims_made": "",
        "attribution_businesses_entities": "",
        "structured_output_dict": {},
        "structured_extractor_prompts": STRUCTURED_EXTRACTOR_PROMPTS,
    }

    summaries = await generate_summaries(llm, state["full_transcript"], state["prompts_dict"])
    aggregate = state["aggregate_summary"]
    for key, text in summaries.items():
        state[key] = text
        state[f"attribution_{key}"] = extract_attributions(text)
        aggregate += f"\n\n## {key}\n{text}"
    state["aggregate_summary"] = aggregate  

    episode = await Episode( 
        
    )


    transcript_update = await Transcript( 

     )

    # 5) Structured extraction
    state["structured_output_dict"] = await run_structured_extraction(agent_dict, summaries)

    # 6) Print outputs
    logger.info("=== Pydantic Model Output (dicts) ===")
    for k, v in state["structured_output_dict"].items():
        logger.info("\n[%s]", k)
        logger.info("%s", v["dict"])  # already a dict

    logger.info("\n=== Each Summary ===")
    for key in [
        "product_information",
        "medical_treatment",
        "high_level_overview",
        "claims_made",
        "businesses_entities",
    ]:
        logger.info("\n## %s\n%s", key, state.get(key, '')[:2000])

    logger.info("\n=== Each Attribution (parsed from <attribution>) ===")
    for key in [
        "product_information",
        "medical_treatment",
        "high_level_overview",
        "claims_made",
        "businesses_entities",
    ]:
        akey = f"attribution_{key}"
        logger.info("\n## %s\n%s", akey, state.get(akey, '')[:2000])

    logger.info("\n=== High-Level Overview Summary ===")
    logger.info("%s", state.get("high_level_overview", "")[:4000])


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(main())

 
