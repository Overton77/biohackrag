from pydantic import BaseModel, Field 
from typing import List, Optional, Dict, Any, Literal, Union, TYPE_CHECKING
from datetime import datetime, UTC
from beanie import Document, Link, init_beanie, BackLink
from src.config.mongo_setup import get_async_mongo_client   
import asyncio 
from pymongo import AsyncMongoClient
class TimeStamped(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BaseDoc(Document, TimeStamped): 
    class Settings:
        use_state_management = True 




# -------------------------
# People (Pydantic output)
# -------------------------

class PersonOutput(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None


# -------------------------
# People (Beanie)
# -------------------------

class Person(BaseDoc):
    
    name: str
    type: Optional[str] = None  # e.g., "host", "guest", "doctor", etc.

    class Settings:
        name = "persons"

# LLM settings next to the document



# -------------------------
# Core domain docs
# -------------------------

# Pydantic: Transcript
class TranscriptOutput(BaseModel):
    product_summary: Optional[str] = None
    business_summary: Optional[str] = None
    medical_treatment_summary: Optional[str] = None
    claims_made_summary: Optional[str] = None
    high_level_overview_summary: Optional[str] = None
    master_aggregate_summary: Optional[str] = None

    structured_product_information: Optional[Dict[str, Any]] = None
    structured_medical_treatment: Optional[Dict[str, Any]] = None
    structured_high_level_overview: Optional[Dict[str, Any]] = None
    structured_claims_made: Optional[Dict[str, Any]] = None
    structured_businesses_entities: Optional[Dict[str, Any]] = None


class Transcript(BaseDoc):
    # BackLink from Episode.transcript (Episode -> Link[Transcript])
    episode: BackLink["Episode"] = Field(default=None, original_field="transcript")

    # Summaries
    product_summary: Optional[str] = None
    business_summary: Optional[str] = None
    medical_treatment_summary: Optional[str] = None
    claims_made_summary: Optional[str] = None
    high_level_overview_summary: Optional[str] = None
    master_aggregate_summary: Optional[str] = None

    # Structured output from FunctionAgents
    structured_product_information: Optional[Dict[str, Any]] = None
    structured_medical_treatment: Optional[Dict[str, Any]] = None
    structured_high_level_overview: Optional[Dict[str, Any]] = None
    structured_claims_made: Optional[Dict[str, Any]] = None
    structured_businesses_entities: Optional[Dict[str, Any]] = None

    class Settings:
        name = "transcripts"

# LLM settings next to the document



# Pydantic: Resource
class ResourceOutput(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    kind: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class Resource(BaseDoc):

    url: str
    title: Optional[str] = None
    kind: Optional[str] = None  # e.g., "paper", "video", "blog"
    meta: Dict[str, Any] = Field(default_factory=dict)

    # Reverse: Episodes that reference this Resource
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="webpage_resources")

    class Settings:
        name = "resources"

# LLM settings next to the document



# Pydantic: BioMarker
class BioMarkerOutput(BaseModel):
    name: Optional[str] = None
    age_range_optimal: Optional[Dict[str, Any]] = None
    needs_lab: Optional[bool] = None


class BioMarker(BaseDoc):

    name: str
    age_range_optimal: Optional[Dict[str, Any]] = None  # e.g., {"min": 20, "max": 40}
    needs_lab: bool = False
    affected_by: Optional[List[Link["Product"]]] = None  # products that affect this biomarker

    class Settings:
        name = "biomarkers"

# LLM settings next to the document



# Pydantic: Protocol
class ProtocolOutput(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Protocol(BaseDoc):

    name: str
    description: Optional[str] = None

    # Reverse relations:
    biohacks: BackLink["BioHack"] = Field(default_factory=list, original_field="involved_in")
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="protocols")

    class Settings:
        name = "protocols"

# LLM settings next to the document



# Pydantic: BioHack
class BioHackOutput(BaseModel):
    description: Optional[str] = None


class BioHack(BaseDoc):

    description: Optional[str] = None
    effects: Optional[List[Link[BioMarker]]] = None                 # biomarkers affected by this biohack
    involved_in: Optional[List[Link[Protocol]]] = None              # protocols this biohack is involved in
    products: Optional[List[Link["Product"]]] = None
    recommended_by: Optional[List[Link[Person]]] = None

    # Reverse:
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="biohacks")

    class Settings:
        name = "biohacks"

# LLM settings next to the document



# Pydantic: Business
class BusinessOutput(BaseModel):
    biography: Optional[str] = None
    market_cap: Optional[float] = None
    canonical_name: Optional[str] = None
    aliases: Optional[List[str]] = None
    role_or_relevance: Optional[str] = None
    first_timestamp: Optional[str] = None
    attribution_quotes: Optional[List[Dict[str, Any]]] = None


class Business(BaseDoc):

    owner: Optional[Link[Person]] = None
    products: Optional[List[Link["Product"]]] = None
    biography: Optional[str] = None
    market_cap: Optional[float] = None
    mentioned_in: Optional[List[Link[Transcript]]] = None  # transcripts referencing this business

    # Structured output fields from CompanyItem
    canonical_name: Optional[str] = None
    aliases: Optional[List[str]] = None
    role_or_relevance: Optional[str] = None
    first_timestamp: Optional[str] = None
    attribution_quotes: Optional[List[Dict[str, Any]]] = None  # AttributionQuote data

    # Reverse:
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="businesses")
    product_backlinks: BackLink["Product"] = Field(default_factory=list, original_field="company")

    class Settings:
        name = "businesses"

# LLM settings next to the document



# Pydantic: Product
class ProductOutput(BaseModel):
    name: Optional[str] = None
    cost: Optional[int] = None
    buy_links: Optional[List[str]] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None
    protocols: Optional[List[str]] = None
    benefits_as_stated: Optional[List[str]] = None
    attribution_quotes: Optional[List[Dict[str, Any]]] = None


class Product(BaseDoc):

    name: str
    company: Optional[Link[Business]] = None            # (Business.products is the BackLink)
    helps_with: Optional[List[Link[BioHack]]] = None    # biohacks this product helps with
    cost: Optional[int] = None
    buy_links: Optional[List[str]] = None
    description: Optional[str] = None
    recommended_by: Optional[List[Link[Person]]] = None

    # Structured output fields from ProductItem
    features: Optional[List[str]] = None
    protocols: Optional[List[str]] = None
    benefits_as_stated: Optional[List[str]] = None
    attribution_quotes: Optional[List[Dict[str, Any]]] = None  # AttributionQuote data

    # Reverse:
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="products")

    class Settings:
        name = "products" 

# LLM settings next to the document






# Pydantic: Treatment
class TreatmentOutput(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    procedure_or_protocol: Optional[List[str]] = None
    outcomes_as_reported: Optional[List[str]] = None
    risks_or_contraindications: Optional[List[str]] = None
    confidence: Optional[Literal["high", "medium", "low"]] = None
    attribution_quotes: Optional[List[Dict[str, Any]]] = None


class Treatment(BaseDoc):

    name: str
    description: Optional[str] = None
    products: Optional[List[Link[Product]]] = None
    protocols: Optional[List[Link[Protocol]]] = None
    biomarkers: Optional[List[Link[BioMarker]]] = None

    # Structured output fields from TreatmentItem
    procedure_or_protocol: Optional[List[str]] = None
    outcomes_as_reported: Optional[List[str]] = None
    risks_or_contraindications: Optional[List[str]] = None
    confidence: Optional[Literal["high", "medium", "low"]] = "medium"
    attribution_quotes: Optional[List[Dict[str, Any]]] = None  # AttributionQuote data

    # Reverse:
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="treatments")

    class Settings:
        name = "treatments"

# LLM settings next to the document



# Pydantic: CaseStudy
class CaseStudyOutput(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class CaseStudy(BaseDoc):

    title: str
    description: Optional[str] = None
    resources: Optional[List[Link[Resource]]] = None
    products: Optional[List[Link[Product]]] = None
    businesses: Optional[List[Link[Business]]] = None
    treatments: Optional[List[Link[Treatment]]] = None

    # Note: Removed invalid BackLink to Episode (no corresponding Link on Episode)

    class Settings:
        name = "case_studies"

# LLM settings next to the document



# Pydantic: SuccessStory
class SuccessStoryOutput(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None


class SuccessStory(BaseDoc):

    title: str
    summary: Optional[str] = None
    person: Optional[Link[Person]] = None
    product: Optional[Link[Product]] = None
    business: Optional[Link[Business]] = None
    resources: Optional[List[Link[Resource]]] = None
    case_study: Optional[Link[CaseStudy]] = None

    # Reverse:
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="success_stories")

    class Settings:
        name = "success_stories"

# LLM settings next to the document


# Pydantic: Claim
class ClaimOutput(BaseModel):
    text: Optional[str] = None
    description: Optional[str] = None
    claim_type: Optional[Literal["causal", "quantitative", "experiential", "other"]] = None
    speaker: Optional[str] = None
    evidence_present_in_transcript: Optional[Literal["yes", "no"]] = None
    attribution_quotes: Optional[List[Dict[str, Any]]] = None


class Claim(BaseDoc):

    text: str
    description: Optional[str] = None 
    claim_type: Optional[Literal["causal", "quantitative", "experiential", "other"]] = "other"

    # Structured output fields from ClaimItem
    speaker: Optional[str] = None
    evidence_present_in_transcript: Optional[Literal["yes", "no"]] = "no"
    attribution_quotes: Optional[List[Dict[str, Any]]] = None  # AttributionQuote data

    # Optional typed relations (attach what you have)
    persons: Optional[List[Link[Person]]] = None
    products: Optional[List[Link[Product]]] = None
    treatments: Optional[List[Link[Treatment]]] = None
    biomarkers: Optional[List[Link[BioMarker]]] = None
    businesses: Optional[List[Link[Business]]] = None
    protocols: Optional[List[Link[Protocol]]] = None
    transcript: Optional[Link[Transcript]] = None
    resources: Optional[List[Link[Resource]]] = None 
    compounds: Optional[List[Link["Compound"]]] = None

    # Reverse:
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="claims")

    class Settings:
        name = "claims"

# LLM settings next to the document


# Pydantic: Compound
class CompoundOutput(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[Literal["supplement", "food", "herb", "other"]] = None 


class Compound(BaseDoc): 

    name: str   
    description: Optional[str] = None
    products: Optional[List[Link[Product]]] = None 
    protocols: Optional[List[Link[Protocol]]] = None  
    claims: Optional[List[Link[Claim]]] = None
    type: Optional[Literal["supplement", "food", "herb", "other"]] = "other" 
    benefits_as_stated: Optional[List[str]] = None 
    class Settings: 
        name = "compounds"

# LLM settings next to the document

# -------------------------
# Media hierarchy
# -------------------------

# Pydantic: Episode
class EpisodeOutput(BaseModel):
    episode_page_url: Optional[str] = None
    transcript_url: Optional[str] = None
    webpage_summary: Optional[str] = None
    internal_summary: Optional[str] = None
    release_date: Optional[datetime] = None
    webpage_claims: Optional[Dict[str, str]] = None
    purpose: Optional[str] = None
    participants: Optional[List[str]] = None
    main_sections: Optional[List[Dict[str, Any]]] = None
    key_takeaways: Optional[List[str]] = None
    overview_attribution_quotes: Optional[List[Dict[str, Any]]] = None


class Episode(BaseDoc):

    # Channel that this episode belongs to
    channel: Link["Channel"]

    episode_page_url: Optional[str] = None
    transcript_url: Optional[str] = None
    webpage_summary: Optional[str] = None
    internal_summary: Optional[str] = None
    release_date: Optional[datetime] = None

    # One transcript per episode (Link on Episode, BackLink on Transcript)
    transcript: Optional[Link[Transcript]] = None

    guests: Optional[List[Link[Person]]] = None

    # Webpage-level extraction
    webpage_claims: Optional[Dict[str, str]] = None  # {claim: description}
    webpage_resources: Optional[List[Link[Resource]]] = None

    # Structured output fields from HighLevelOverview
    purpose: Optional[str] = None
    participants: Optional[List[str]] = None
    main_sections: Optional[List[Dict[str, Any]]] = None  # SectionItem data
    key_takeaways: Optional[List[str]] = None
    overview_attribution_quotes: Optional[List[Dict[str, Any]]] = None  # AttributionQuote data

    # Optional link-to-lists
    products: Optional[List[Link[Product]]] = None
    protocols: Optional[List[Link[Protocol]]] = None
    biohacks: Optional[List[Link[BioHack]]] = None
    businesses: Optional[List[Link[Business]]] = None
    claims: Optional[List[Link[Claim]]] = None
    treatments: Optional[List[Link[Treatment]]] = None
    success_stories: Optional[List[Link[SuccessStory]]] = None

    class Settings:
        name = "episodes"

# LLM settings next to the document


# Pydantic: Channel
class ChannelOutput(BaseModel):
    name: Optional[str] = None


class Channel(BaseDoc):

    name: str
    owner: Optional[Link[Person]] = None
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="channel")

    class Settings:
        name = "channels" 

# LLM settings next to the document


class AttributionQuoteOutput(BaseModel):  
    quote: Optional[str] = None
    timestamp: Optional[str] = None    


class AttributionQuote(BaseDoc):  
    
    quote: Optional[str] = None 
    timestamp: Optional[str] = None  
    person: Optional[Link[Person]] = None   
    transcript: Optional[Link[Transcript]] = None 
    class Settings: 
        name = "attribution_quotes"  

# LLM settings next to the document




class MedicalTreatmentOutput(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cost: Optional[float] = None


class MedicalTreatment(BaseDoc):

    name: str
    description: Optional[str] = None
    cost: Optional[float] = None

    # Relationships
    persons: Optional[List[Link[Person]]] = None          # linked people
    businesses: Optional[List[Link[Business]]] = None     # linked businesses
    products: Optional[List[Link[Product]]] = None
    protocols: Optional[List[Link[Protocol]]] = None
    biomarkers: Optional[List[Link[BioMarker]]] = None
    success_stories: Optional[List[Link[SuccessStory]]] = None

    # Note: Removed invalid BackLink to Episode (Episode does not link to MedicalTreatment)

    class Settings:
        name = "medical_treatments"

# LLM settings next to the document



async def init_beanie_with_pymongo() -> AsyncMongoClient:
    """Initialize Beanie with all document models"""
    client = await get_async_mongo_client()
    if client is None:
        raise RuntimeError("Async Mongo client not available. Check MONGO_CONNECTION.")
    
    # Initialize Beanie with all document models
    await init_beanie(
        database=client.biohack_agent, 
        document_models=[
            Business,
            Person, 
            Product, 
            Compound, 
            MedicalTreatment,
            Resource,
            Transcript,
            Claim,
            Episode,  
            BioHack, 
            BioMarker,  
            Protocol, 
            Treatment,
            CaseStudy,
            SuccessStory,
            Channel,
        ]
    )
    return client




def pydantic_to_beanie(
    document_class: type[BaseDoc],
    output: Union[BaseModel, Dict[str, Any]],
    /,
    **extra_fields: Any,
) -> BaseDoc:
    """Create a Beanie document instance from a Pydantic model or dict.

    - Only fields that exist on the Beanie document are copied.
    - Relation fields (e.g., links) are naturally ignored if not provided.
    - extra_fields can override or set additional fields that exist on the document.
    """
    if isinstance(output, BaseModel):
        payload: Dict[str, Any] = output.model_dump(exclude_none=True)
    else:
        payload = {**output}

    allowed_keys = set(getattr(document_class, "model_fields").keys())
    filtered = {key: value for key, value in payload.items() if key in allowed_keys}

    for key, value in extra_fields.items():
        if key in allowed_keys:
            filtered[key] = value

    return document_class(**filtered)


def update_beanie_from_pydantic(
    document: BaseDoc,
    output: Union[BaseModel, Dict[str, Any]],
) -> None:
    """Update an existing Beanie document from a Pydantic model or dict."""
    if isinstance(output, BaseModel):
        payload: Dict[str, Any] = output.model_dump(exclude_none=True)
    else:
        payload = {**output}

    allowed_keys = set(document.__class__.model_fields.keys())
    for key, value in payload.items():
        if key in allowed_keys:
            setattr(document, key, value)



    

if __name__ == "__main__":  
    print("Importing mongo schemas")