from pydantic import BaseModel, Field 
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, UTC
from beanie import Document, Link, init_beanie, BackLink
from src.config.mongo_setup import get_async_mongo_client  
from pymongo import AsyncMongoClient
class TimeStamped(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BaseDoc(Document, TimeStamped):
    class Settings:
        use_state_management = True


# -------------------------
# People
# -------------------------

class Person(BaseDoc):
    name: str
    type: Optional[str] = None  # e.g., "host", "guest", "doctor", etc.

    class Settings:
        name = "persons"


# -------------------------
# Core domain docs
# -------------------------

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


class Resource(BaseDoc):
    url: str
    title: Optional[str] = None
    kind: Optional[str] = None  # e.g., "paper", "video", "blog"
    meta: Dict[str, Any] = Field(default_factory=dict)

    # Reverse: Episodes that reference this Resource
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="webpage_resources")

    class Settings:
        name = "resources"


class BioMarker(BaseDoc):
    name: str
    age_range_optimal: Optional[Dict[str, Any]] = None  # e.g., {"min": 20, "max": 40}
    needs_lab: bool = False
    affected_by: Optional[List[Link["Product"]]] = None  # products that affect this biomarker

    class Settings:
        name = "biomarkers"


class Protocol(BaseDoc):
    name: str
    description: Optional[str] = None

    # Reverse relations:
    biohacks: BackLink["BioHack"] = Field(default_factory=list, original_field="involved_in")
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="protocols")

    class Settings:
        name = "protocols"


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

    # Reverse:
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="claims")

    class Settings:
        name = "claims"


# -------------------------
# Media hierarchy
# -------------------------

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


class Channel(BaseDoc):
    name: str
    owner: Optional[Link[Person]] = None
    episodes: BackLink["Episode"] = Field(default_factory=list, original_field="channel")

    class Settings:
        name = "channels" 

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


if __name__ == "__main__":
    print("Importing mongo schemas")
    