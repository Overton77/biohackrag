 # --- imports ---
from typing import Any, Dict, List, Optional, Literal, TypedDict
from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph import StateGraph, START, END
import re
import asyncio

# -------------------------------------------------------------
# 0) Load transcript
# -------------------------------------------------------------
docs: List[Document] = TextLoader(file_path="./transcript.txt").load()  # one Document
full_transcript: str = docs[0].page_content

# -------------------------------------------------------------
# 1) Split
# -------------------------------------------------------------
text_splitter = CharacterTextSplitter(chunk_size=1200, chunk_overlap=300)
doc_splits: List[Document] = text_splitter.split_documents(docs)
print("num splits:", len(doc_splits))

# -------------------------------------------------------------
# 2) Vector store & retriever
# -------------------------------------------------------------
# NOTE: provide your own `embedder` (e.g., NVIDIAEmbeddings(...))
transcript_store = FAISS.from_documents(doc_splits, embedder)
transcript_retriever = transcript_store.as_retriever(search_kwargs={"k": 5})

# -------------------------------------------------------------
# 3) Free‑form summary prompts (with <attribution>)
# -------------------------------------------------------------
summary_prompts: Dict[str, str] = {
    "product_information": (
        "The intention is to parse the following transcript and extract information about products. "
        "Extract and summarize all information related to products, including product names, descriptions, "
        "features, and any discussions about product performance or use. Present the summary as a list of key "
        "product details. For each product, include an <attribution> section containing short quotes and timestamps "
        "directly from the transcript.\n\nTranscript:\n{transcript}"
    ),
    "medical_treatment": (
        "The intention is to parse the following transcript and extract information about medical treatments or services. "
        "Extract and summarize all content related to medical treatments or services, including treatment names, procedures, "
        "protocols, patient experiences, and any relevant outcomes. Present this summary as a concise, organized overview. "
        "For each treatment or service, include an <attribution> section with short quotes and timestamps from the transcript.\n\n"
        "Transcript:\n{transcript}"
    ),
    "high_level_overview": (
        "The intention is to parse the following transcript and provide a high-level summary. "
        "Highlight the main topics discussed, key participants, and the general flow of the conversation. "
        "The summary should capture the most important points and the overall purpose of the transcript. "
        "At the end, add an <attribution> section with 3–5 quotes and timestamps that support your summary.\n\n"
        "Transcript:\n{transcript}"
    ),
    "claims_made": (
        "The intention is to parse the following transcript and identify explicit claims. "
        "Identify and summarize all explicit claims made in the transcript. For each claim, note who made it (if possible) "
        "and briefly describe the supporting evidence or reasoning provided. Include an <attribution> section with short quotes "
        "and timestamps for each claim.\n\nTranscript:\n{transcript}"
    ),
    "businesses_entities": (
        "The intention is to parse the following transcript and extract information about businesses and entities. "
        "List all businesses, organizations, or notable entities mentioned in the transcript. For each entity, provide a brief "
        "description of their role or relevance to the discussion, as stated or implied. Include an <attribution> section with "
        "a short quote and timestamp for each entity.\n\nTranscript:\n{transcript}"
    ),
}

# -------------------------------------------------------------
# 4) Structured extractor prompts (summary -> schema)
# -------------------------------------------------------------
structured_extractor_prompts = {
    "product_information": (
        "You will extract structured product data from a targeted summary.\n"
        "Use ONLY the content in the provided summary—do not add outside facts.\n"
        "Populate the ProductSummary schema fields faithfully. If data is missing, leave fields empty.\n"
        "If the summary includes quotes/timestamps (e.g., inside <attribution>), map them into the structured 'attribution' list.\n\n"
        "TARGETED SUMMARY:\n{summary}\n"
    ),
    "medical_treatment": (
        "You will extract structured medical treatment/service data from a targeted summary.\n"
        "Use ONLY the content in the provided summary—no outside facts.\n"
        "Populate the MedicalSummary schema, set 'confidence' (high/medium/low) based on how explicit the summary is, "
        "and map quotes/timestamps into the 'attribution' list.\n\n"
        "TARGETED SUMMARY:\n{summary}\n"
    ),
    "high_level_overview": (
        "You will extract a high-level overview from a targeted summary.\n"
        "Use ONLY the content in the provided summary. Populate the HighLevelOverview schema: purpose, participants, main_sections "
        "(with approx time ranges if present), and 5–7 key_takeaways when available. Map quotes/timestamps into 'attribution'.\n\n"
        "TARGETED SUMMARY:\n{summary}\n"
    ),
    "claims_made": (
        "You will extract explicit claims from a targeted summary.\n"
        "Use ONLY the summary—no outside facts. Populate the ClaimsSummary schema. For each claim, set speaker (if given), "
        "claim_text (≤20 words if possible), claim_type (causal/quantitative/experiential/other), "
        "evidence_present_in_transcript ('yes' or 'no'), and add quotes/timestamps to 'attribution'.\n\n"
        "TARGETED SUMMARY:\n{summary}\n"
    ),
    "businesses_entities": (
        "You will extract businesses/organizations/entities from a targeted summary.\n"
        "Use ONLY the summary—no outside facts. Populate the EntitiesSummary schema with canonical_name, aliases (if any), "
        "role_or_relevance (≤12 words), first_timestamp if present, and quotes/timestamps in 'attribution'.\n\n"
        "TARGETED SUMMARY:\n{summary}\n"
    ),
}

# -------------------------------------------------------------
# 5) Pydantic models
# -------------------------------------------------------------
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

class EntityItem(BaseModel):
    canonical_name: str
    aliases: List[str] = Field(default_factory=list)
    role_or_relevance: Optional[str] = None
    first_timestamp: Optional[str] = None
    attribution: List[AttributionQuote] = Field(default_factory=list)

class EntitiesSummary(BaseModel):
    entities: List[EntityItem] = Field(default_factory=list)

model_map = {
    "product_information": ProductSummary,
    "medical_treatment": MedicalSummary,
    "high_level_overview": HighLevelOverview,
    "claims_made": ClaimsSummary,
    "businesses_entities": EntitiesSummary,
}

# -------------------------------------------------------------
# 6) LangGraph state
# -------------------------------------------------------------
class TranscriptState(TypedDict, total=False):
    input: str
    aggregate_summary: str
    final_summary: str
    prompts_dict: Dict[str, str]
    full_transcript: str
    documents: List[Document]
    transcript_retriever: Any

    # Summaries (strings)
    product_information: str
    medical_treatment: str
    high_level_overview: str
    claims_made: str
    businesses_entities: str

    # Attributions parsed from <attribution> tags (strings)
    attribution_product_information: str
    attribution_medical_treatment: str
    attribution_high_level_overview: str
    attribution_claims_made: str
    attribution_businesses_entities: str

    # Structured outputs (validated Pydantic objects or dicts)
    structured_output_dict: Dict[str, Any]
    structured_extractor_prompts: Dict[str, str]

# -------------------------------------------------------------
# 7) Helpers
# -------------------------------------------------------------
def extract_attributions(summary_text: str) -> str:
    """Return ALL <attribution>...</attribution> contents joined with double newlines."""
    matches = re.findall(r"<attribution>(.*?)</attribution>", summary_text, re.DOTALL | re.IGNORECASE)
    return "\n\n".join(m.strip() for m in matches) if matches else ""

def build_summary_chain(prompt_text: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a careful, concise summarizer. Use only the transcript. Include <attribution> blocks."),
        ("user", prompt_text),  # contains {transcript}
    ])
    return prompt | large_llm | StrOutputParser()

def build_structured_from_summary_chain(prompt_text: str, model_cls):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract ONLY from the provided summary. Output MUST conform to the schema."),
        ("user", prompt_text),  # contains {summary}
    ])
    return prompt | large_llm.with_structured_output(model_cls)

# -------------------------------------------------------------
# 8) Node: generate_summaries (runs in parallel for speed)
# -------------------------------------------------------------
async def generate_summaries(state: TranscriptState) -> TranscriptState:
    transcript = state.get("full_transcript", "")
    prompts = state.get("prompts_dict", {})
    if not transcript:
        raise ValueError("full_transcript missing from state.")
    if not prompts:
        return state

    # Build one runnable per summary type
    summary_runnables = {k: build_summary_chain(v) for k, v in prompts.items()}
    parallel = RunnableParallel(**summary_runnables)

    # Invoke all in parallel
    results: Dict[str, str] = await parallel.ainvoke({"transcript": transcript})

    # Write summaries + attributions + aggregate
    aggregate = state.get("aggregate_summary", "")
    for key, resp in results.items():
        state[key] = resp
        state[f"attribution_{key}"] = extract_attributions(resp)
        aggregate += f"\n\n## {key}\n{resp}"
    state["aggregate_summary"] = aggregate
    return state

# -------------------------------------------------------------
# 9) After summaries: run structured extraction from summaries
# -------------------------------------------------------------
async def run_structured_from_summaries(state: TranscriptState) -> TranscriptState:
    structured_prompts = state["structured_extractor_prompts"]
    out: Dict[str, Any] = {}

    # Build structured chains
    chains = {
        key: build_structured_from_summary_chain(structured_prompts[key], model_map[key])
        for key in model_map.keys()
    }

    # Prepare inputs (summary text per key)
    inputs = {k: {"summary": state.get(k, "")} for k in model_map.keys()}

    # Run each structured chain sequentially (can parallelize if desired)
    for k, chain in chains.items():
        obj = await chain.ainvoke(inputs[k])   # returns Pydantic model instance
        # store both the object and a serializable dict version
        out[k] = {"object": obj, "dict": obj.dict()}

    state["structured_output_dict"] = out
    return state

# -------------------------------------------------------------
# 10) Graph
# -------------------------------------------------------------
graph = StateGraph(TranscriptState)
graph.add_node("generate_summaries", generate_summaries)
graph.add_node("structured_extraction", run_structured_from_summaries)

graph.add_edge(START, "generate_summaries")
graph.add_edge("generate_summaries", "structured_extraction")
graph.add_edge("structured_extraction", END)

app = graph.compile()

# -------------------------------------------------------------
# 11) Initial state
# -------------------------------------------------------------
initial_state: TranscriptState = {
    "input": "Begin the summary chain",
    "aggregate_summary": "",
    "final_summary": "",
    "prompts_dict": summary_prompts,
    "full_transcript": full_transcript,
    "documents": doc_splits,
    "transcript_retriever": transcript_retriever,

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
    "structured_extractor_prompts": structured_extractor_prompts,
}

# -------------------------------------------------------------
# 12) Run and print requested outputs
# -------------------------------------------------------------
async def main():
    # Stream steps (optional)
    async for step in app.astream(initial_state):
        print("STEP KEYS:", list(step.keys()))

    # Final state
    final_state = await app.ainvoke(initial_state)

    # ---- PRINT REQUESTED ITEMS ----
    print("\n=== Pydantic Model Output (dicts) ===")
    for k, v in final_state["structured_output_dict"].items():
        print(f"\n[{k}]")
        print(v["dict"])

    print("\n=== Each Summary ===")
    for key in ["product_information", "medical_treatment", "high_level_overview", "claims_made", "businesses_entities"]:
        print(f"\n## {key}\n{final_state.get(key, '')[:2000]}")  # trim if huge

    print("\n=== Each Attribution (parsed from <attribution>) ===")
    for key in ["product_information", "medical_treatment", "high_level_overview", "claims_made", "businesses_entities"]:
        akey = f"attribution_{key}"
        print(f"\n## {akey}\n{final_state.get(akey, '')[:2000]}")

    print("\n=== High-Level Overview Summary ===")
    print(final_state.get("high_level_overview", "")[:4000])

# If you're in an async-capable environment:
# await main()
# Otherwise:
asyncio.run(main())

 
 