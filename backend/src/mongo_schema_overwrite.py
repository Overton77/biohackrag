from pydantic import BaseModel, Field, ConfigDict 
from typing import List, Optional, Dict, Any, Literal, Union, TYPE_CHECKING
from datetime import datetime, UTC
from beanie import Document, Link, init_beanie, BackLink
from config.mongo_setup import get_async_mongo_client   
import asyncio 
from pymongo import AsyncMongoClient
from enum import Enum 

# ========= Common mixins =========

class TimeStamped(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BaseDoc(Document, TimeStamped):
    class Settings:
        # Keep this off by default for less overhead; enable per-model if needed.
        use_state_management = False
    # Ignore unknown/legacy fields from existing documents in the DB
    model_config = ConfigDict(extra="ignore")


# ========= Enums (finite fields kept tidy) =========

class PersonKind(str, Enum):
    """Person type enumeration.
    
    Values:
        host: Show/podcast host
        guest: Show/podcast guest
        doctor: Medical professional
        other: Other person type
    """
    host = "host"
    guest = "guest"
    doctor = "doctor"
    other = "other"

class ClaimType(str, Enum):
    """Type of claim made in transcript.
    
    Values:
        causal: Claims about cause and effect
        quantitative: Claims with numerical/measurable data
        experiential: Claims based on personal experience
        other: Other types of claims
    """
    causal = "causal"
    quantitative = "quantitative"
    experiential = "experiential"
    other = "other"

class CompoundType(str, Enum):
    """Type of compound/substance.
    
    Values:
        supplement: Dietary/nutritional supplement
        food: Food item
        herb: Herbal substance
        other: Other compound type
    """
    supplement = "supplement"
    food = "food"
    herb = "herb"
    other = "other"

class Confidence(str, Enum):
    """Confidence level enumeration.
    
    Values:
        high: High confidence
        medium: Medium confidence
        low: Low confidence
    """
    high = "high"
    medium = "medium"
    low = "low"


# ==================================================
# People
# ==================================================

class Person(BaseDoc):
    """Person document stored in 'persons' collection.
    
    Fields:
        name (str): Person's name
        kind (Optional[PersonKind]): Type of person (host, guest, doctor, etc)
    """
    name: str
    kind: Optional[PersonKind] = None  # e.g., host, guest, doctor 
    bio: Optional[str] = None    
    website: Optional[str] = None  
    social_links: Optional[List[Dict[str, Any]]] = None   
    episode_appearances: Optional[List[BackLink["Episode"]]] = Field(default_factory=list, original_field="guests") 




    class Settings:
        name = "persons"


class TranscriptStructured(BaseModel): 
    """Structured block of transcript data produced by LLM.
    
    Fields:
        product (Optional[Dict]): Product-related structured data
        medical_treatment (Optional[Dict]): Medical treatment structured data
        high_level_overview (Optional[Dict]): High-level overview structured data
        claims_made (Optional[Dict]): Claims structured data
        businesses (Optional[Dict]): Business-related structured data
    """
    product: Optional[Dict[str, Any]] = None
    medical_treatment: Optional[Dict[str, Any]] = None
    high_level_overview: Optional[Dict[str, Any]] = None
    claims_made: Optional[Dict[str, Any]] = None
    businesses: Optional[Dict[str, Any]] = None


class Transcript(BaseDoc):
    """Transcript document stored in 'transcripts' collection.
    
    Fields:
        product_summary (Optional[str]): Summary of products discussed
        compound_summary (Optional[str]): Summary of compounds discussed
        business_summary (Optional[str]): Summary of businesses discussed
        medical_treatment_summary (Optional[str]): Summary of medical treatments
        claims_made_summary (Optional[str]): Summary of claims made
        high_level_overview_summary (Optional[str]): High-level overview
        master_aggregate_summary (Optional[str]): Aggregate summary
        timeline (List[Dict]): Timeline of transcript events
        structured (Optional[TranscriptStructured]): Structured data block
    """
    product_summary: Optional[str] = None 
    compound_summary: Optional[str] = None 
    business_summary: Optional[str] = None
    medical_treatment_summary: Optional[str] = None
    claims_made_summary: Optional[str] = None
    high_level_overview_summary: Optional[str] = None
    master_aggregate_summary: Optional[str] = None
    timeline: Optional[List[Dict[str, Any]]] = None 
    full_transcript: Optional[str] = None 

    structured: Optional[TranscriptStructured] = None

    class Settings:
        name = "transcripts"



# ==================================================
# Resources
# ==================================================

class Resource(BaseDoc):
    """Resource document stored in 'resources' collection.
    
    Fields:
        url (str): Resource URL
        title (Optional[str]): Resource title
        kind (Optional[str]): Resource type (paper, video, blog, etc)
        meta (Dict): Additional metadata
    """
    url: str
    title: Optional[str] = None
    kind: Optional[str] = None  # e.g., "paper", "video", "blog"
    meta: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "resources"




class BioMarker(BaseDoc):
    """BioMarker document stored in 'biomarkers' collection.
    
    Fields:
        name (str): Biomarker name
        description (Optional[str]): Biomarker description
        age_range_optimal (Optional[Dict]): Optimal age range
        needs_lab (bool): Whether lab testing is required
    """
    name: str 
    description: Optional[str] = None  
    age_range_optimal: Optional[Dict[str, Any]] = None  # e.g., {"min": 20, "max": 40}
    needs_lab: bool = False

    class Settings:
        name = "biomarkers"


class Protocol(BaseDoc):
    """Protocol document stored in 'protocols' collection.
    
    Fields:
        name (str): Protocol name
        description (Optional[str]): Protocol description
        biomarkers (List[Link[BioMarker]]): Linked biomarkers
    """
    name: str
    description: Optional[str] = None 
    biomarkers: List[Link[BioMarker]] = Field(default_factory=list) 

    class Settings:
        name = "protocols"



class BioHack(BaseDoc):
    """BioHack document stored in 'biohacks' collection.
    
    Fields:
        description (Optional[str]): BioHack description
        effects (List[Link[BioMarker]]): Linked biomarker effects
    """
    description: Optional[str] = None
    effects: List[Link[BioMarker]] = Field(default_factory=list)

    class Settings:
        name = "biohacks"



class Business(BaseDoc):
    """Business document stored in 'businesses' collection.
    
    Fields:
        owner (Optional[Link[Person]]): Business owner
        biography (Optional[str]): Business biography
        market_cap (Optional[float]): Market capitalization
        canonical_name (Optional[str]): Official business name
        aliases (List[str]): Alternative names
        role_or_relevance (Optional[str]): Business role/relevance
        first_timestamp (Optional[str]): First mention timestamp
        business_documents (Optional[List[str]]): Related documents
    """
    owner: Optional[Link[Person]] = None
    biography: Optional[str] = None
    market_cap: Optional[float] = None

    canonical_name: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    role_or_relevance: Optional[str] = None
    first_timestamp: Optional[str] = None 
    business_documents: Optional[List[str]] = None   

    class Settings:
        name = "businesses"



class Product(BaseDoc):
    """Product document stored in 'products' collection.
    
    Fields:
        name (str): Product name
        company (Optional[Link[Business]]): Associated company
        helps_with (List[Link[BioHack]]): Related biohacks
        cost (Optional[int]): Product cost
        buy_links (List[str]): Purchase links
        sponsor_links (Optional[List[Link[Resource]]]): Sponsor resources
        description (Optional[str]): Product description
        recommended_by (List[Link[Person]]): Recommenders
        features (List[str]): Product features
        protocols (List[str]): Related protocols
        benefits_as_stated (List[str]): Claimed benefits
    """
    name: str
    company: Optional[Link[Business]] = None            
    helps_with: List[Link[BioHack]] = Field(default_factory=list)
    cost: Optional[int] = None
    buy_links: List[str] = Field(default_factory=list)  
    sponsor_links: Optional[List[Link[Resource]]] = None 
    description: Optional[str] = None
    recommended_by: List[Link[Person]] = Field(default_factory=list)

    features: List[str] = Field(default_factory=list)
    protocols: List[str] = Field(default_factory=list)  
    benefits_as_stated: List[str] = Field(default_factory=list)

    class Settings:
        name = "products"




class Treatment(BaseDoc):
    """Treatment document stored in 'treatments' collection.
    
    Fields:
        name (str): Treatment name
        description (Optional[str]): Treatment description
        protocols (Optional[List[Link[Protocol]]]): Related protocols
        procedure_or_protocol (List[str]): Procedure steps
        outcomes_as_reported (List[str]): Reported outcomes
        risks_or_contraindications (List[str]): Risks/contraindications
        confidence (Confidence): Confidence level
        biomarkers (Optional[List[Link[BioMarker]]]): Related biomarkers
    """
    name: str
    description: Optional[str] = None

    protocols: Optional[List[Link[Protocol]]] = None 
    procedure_or_protocol: List[str] = Field(default_factory=list)
    outcomes_as_reported: List[str] = Field(default_factory=list)
    risks_or_contraindications: List[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.medium 
    biomarkers: Optional[List[Link[BioMarker]]] = None 

    class Settings:
        name = "treatments"



class CaseStudy(BaseDoc):
    """CaseStudy document stored in 'case_studies' collection.
    
    Fields:
        title (str): Case study title
        description (Optional[str]): Case study description
        resources_unlinked (Optional[List[str]]): Unlinked resources
        resources (List[Link[Resource]]): Linked resources
    """
    title: str
    description: Optional[str] = None 
    resources_unlinked: Optional[List[str]] = None  
    resources: List[Link[Resource]] = Field(default_factory=list)
    
    class Settings:
        name = "case_studies"



class SuccessStory(BaseDoc):
    """SuccessStory document stored in 'success_stories' collection.
    
    Fields:
        title (str): Story title
        summary (Optional[str]): Story summary
        person (Optional[Link[Person]]): Related person
        resources (Optional[List[Link[Resource]]]): Related resources
        case_study (Optional[Link[CaseStudy]]): Related case study
    """
    title: str
    summary: Optional[str] = None

    person: Optional[Link[Person]] = None
    resources: Optional[List[Link[Resource]]] = None 
    case_study: Optional[Link[CaseStudy]] = None

    class Settings:
        name = "success_stories"


class Claim(BaseDoc):
    """Claim document stored in 'claims' collection.
    
    Fields:
        text (str): Claim text
        description (Optional[str]): Claim description
        claim_type (ClaimType): Type of claim
        speaker (Optional[str]): Who made the claim
        evidence_present_in_transcript (Literal["yes","no"]): Evidence presence
        transcript (Optional[Link[Transcript]]): Related transcript
        persons (List[Link[Person]]): Related persons
        products (List[Link[Product]]): Related products
    """
    text: str
    description: Optional[str] = None
    claim_type: ClaimType = ClaimType.other
    speaker: Optional[str] = None
    evidence_present_in_transcript: Literal["yes", "no"] = "no"

    transcript: Optional[Link[Transcript]] = None
    persons: List[Link[Person]] = Field(default_factory=list)
    products: List[Link[Product]] = Field(default_factory=list)

    class Settings:
        name = "claims"



class Compound(BaseDoc):
    """Compound document stored in 'compounds' collection.
    
    Fields:
        name (str): Compound name
        description (Optional[str]): Compound description
        type (CompoundType): Type of compound
        benefits_as_stated (List[str]): Stated benefits
        products (Optional[List[Link[Product]]]): Related products
        claims (Optional[List[Link[Claim]]]): Related claims
    """
    name: str
    description: Optional[str] = None
    type: CompoundType = CompoundType.other
    benefits_as_stated: List[str] = Field(default_factory=list)

    products: Optional[List[Link[Product]]] = None 
    claims: Optional[List[Link[Claim]]] = None 

    class Settings:
        name = "compounds"




class Channel(BaseDoc):
    """Channel document stored in 'channels' collection.
    
    Fields:
        name (str): Channel name
        owner (Optional[Link[Person]]): Channel owner
        episodes (List[BackLink["Episode"]]): Related episodes
    """
    name: str
    owner: Optional[Link[Person]] = None

    episodes: List[BackLink["Episode"]] = Field(default_factory=list, original_field="channel")

    class Settings:
        name = "channels"


class EpisodeMentions(BaseModel):
    """Group all episode-linked lists in one spot.
    
    Fields:
        products (List[Link[Product]]): Product mentions
        protocols (List[Link[Protocol]]): Protocol mentions
        biohacks (List[Link[BioHack]]): BioHack mentions
        businesses (List[Link[Business]]): Business mentions
        claims (List[Link[Claim]]): Claim mentions
        treatments (List[Link[Treatment]]): Treatment mentions
        success_stories (List[Link[SuccessStory]]): Success story mentions
        resources (List[Link[Resource]]): Resource mentions
    """
    products: List[Link[Product]] = Field(default_factory=list)
    protocols: List[Link[Protocol]] = Field(default_factory=list)
    biohacks: List[Link[BioHack]] = Field(default_factory=list)
    businesses: List[Link[Business]] = Field(default_factory=list)
    claims: List[Link[Claim]] = Field(default_factory=list)
    treatments: List[Link[Treatment]] = Field(default_factory=list)
    success_stories: List[Link[SuccessStory]] = Field(default_factory=list)
    resources: List[Link[Resource]] = Field(default_factory=list)


class Episode(BaseDoc):
    """Episode document stored in 'episodes' collection.
    
    Fields:
        channel (Link[Channel]): Parent channel
        episode_page_url (Optional[str]): Episode page URL
        transcript_url (Optional[str]): Transcript URL
        webpage_summary (Optional[str]): Webpage summary
        internal_summary (Optional[str]): Internal summary
        release_date (Optional[datetime]): Release date
        episode_number (Optional[int]): Episode number
        transcript (Optional[Link[Transcript]]): Episode transcript
        guests (List[Link[Person]]): Episode guests
        sponsors (List[Dict]): Episode sponsors
        learning_claims (List[str]): Learning claims
        purpose (Optional[str]): Episode purpose
        participants (List[str]): Episode participants
        main_sections (List[Dict]): Main sections
        key_takeaways (List[str]): Key takeaways
        overview_attribution_quotes (List[Dict]): Attribution quotes
        mentions (Optional[EpisodeMentions]): All mentions
    """
    channel: Optional[Link[Channel]] = None  # allow missing legacy data

    episode_page_url: Optional[str] = None
    transcript_url: Optional[str] = None
    webpage_summary: Optional[str] = None
    internal_summary: Optional[str] = None
    release_date: Optional[datetime] = None
    episode_number: Optional[int] = None

    transcript: Optional[Link[Transcript]] = None
    guests: Optional[List[Link[Person]]] = None

    sponsors: Optional[List[Dict[str, Any]]] = None
    # Accept legacy string URLs or proper Link[Resource]
    webpage_resources: Optional[List[Union[Link[Resource], str]]] = None
    learning_claims: Optional[List[str]] = None 
    timeline: Optional[List[Dict[str, Any]]] = None    
    master_summary: Optional[str] = None   
    # Use this to produce vector store embeddings 

    purpose: Optional[str] = None
    participants: Optional[List[str]] = None
    main_sections: Optional[List[Dict[str, Any]]] = None
    key_takeaways: Optional[List[str]] = None
    overview_attribution_quotes: Optional[List[Dict[str, Any]]] = None

    mentions: Optional[EpisodeMentions] = None 

    class Settings:
        name = "episodes"




class AttributionQuote(BaseDoc):
    """AttributionQuote document stored in 'attribution_quotes' collection.
    
    Fields:
        quote (Optional[str]): Quote text
        timestamp (Optional[str]): Quote timestamp
        person (Optional[Link[Person]]): Person quoted
        transcript (Optional[Link[Transcript]]): Source transcript
    """
    quote: Optional[str] = None
    timestamp: Optional[str] = None
    person: Optional[Link[Person]] = None
    transcript: Optional[Link[Transcript]] = None

    class Settings:
        name = "attribution_quotes"



class MedicalTreatment(BaseDoc):
    """MedicalTreatment document stored in 'medical_treatments' collection.
    
    Fields:
        name (str): Treatment name
        description (Optional[str]): Treatment description
        cost (Optional[float]): Treatment cost
        products (List[Link[Product]]): Related products
        protocols (List[Link[Protocol]]): Related protocols
        biomarkers (List[Link[BioMarker]]): Related biomarkers
    """
    name: str
    description: Optional[str] = None
    cost: Optional[float] = None

    products: List[Link[Product]] = Field(default_factory=list)
    protocols: List[Link[Protocol]] = Field(default_factory=list)
    biomarkers: List[Link[BioMarker]] = Field(default_factory=list)

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
            AttributionQuote,
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



    

async def _test_simple_queries() -> None:
    """Basic smoke test: init Beanie, fetch Episodes and Transcripts."""
    client = await init_beanie_with_pymongo()

    episodes = await Episode.find().sort("-episode_number").limit(10).to_list()
    print(f"Episodes fetched: {len(episodes)}")
    for ep in episodes:
        print({
            "_id": str(getattr(ep, "id", "")),
            "episode_number": ep.episode_number,
            "has_channel": ep.channel is not None,
        })

    transcripts = await Transcript.find().limit(10).to_list()
    print(f"Transcripts fetched: {len(transcripts)}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(_test_simple_queries())