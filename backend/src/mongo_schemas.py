from pydantic import BaseModel, Field 
from typing import List, Optional, Dict, Any, Literal, Union, TYPE_CHECKING
from datetime import datetime, UTC
from beanie import Document, Link, init_beanie, BackLink
from config.mongo_setup import get_async_mongo_client   
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
    """Person document stored in 'persons' collection
    
    Fields:
        name (str): Name of the person
        type (Optional[str]): Type of person e.g. "host", "guest", "doctor"
    """
    
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
    """Transcript document stored in 'transcripts' collection
    
    Fields:
        episode (BackLink[Episode]): Back reference to Episode
        product_summary (Optional[str]): Summary of products mentioned
        business_summary (Optional[str]): Summary of businesses mentioned  
        medical_treatment_summary (Optional[str]): Summary of medical treatments
        claims_made_summary (Optional[str]): Summary of claims made
        high_level_overview_summary (Optional[str]): High level overview
        master_aggregate_summary (Optional[str]): Master summary
        structured_product_information (Optional[Dict]): Structured product data
        structured_medical_treatment (Optional[Dict]): Structured medical data
        structured_high_level_overview (Optional[Dict]): Structured overview
        structured_claims_made (Optional[Dict]): Structured claims
        structured_businesses_entities (Optional[Dict]): Structured business data
    """

    # BackLink from Episode.transcript (Episode -> Link[Transcript])
    episode: BackLink["Episode"] = Field(default=None, original_field="transcript")

    # Summaries
    product_summary: Optional[str] = None
    business_summary: Optional[str] = None
    medical_treatment_summary: Optional[str] = None
    claims_made_summary: Optional[str] = None
    high_level_overview_summary: Optional[str] = None
    master_aggregate_summary: Optional[str] = None 
    timeline: Optional[List[Dict[str, Any]]] = None  

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
    """Resource document stored in 'resources' collection
    
    Fields:
        url (str): URL of the resource
        title (Optional[str]): Title of the resource
        kind (Optional[str]): Type of resource e.g. "paper", "video", "blog"
        meta (Dict): Additional metadata
        episodes (BackLink[Episode]): Episodes referencing this resource
    """

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
    """BioMarker document stored in 'biomarkers' collection
    
    Fields:
        name (str): Name of the biomarker
        age_range_optimal (Optional[Dict]): Optimal age range e.g. {"min": 20, "max": 40}
        needs_lab (bool): Whether lab testing is required
        affected_by (Optional[List[Link[Product]]]): Products affecting this biomarker
    """

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
    """Protocol document stored in 'protocols' collection
    
    Fields:
        name (str): Name of the protocol
        description (Optional[str]): Description of the protocol
        biohacks (BackLink[BioHack]): BioHacks involved in this protocol
        episodes (BackLink[Episode]): Episodes mentioning this protocol
    """

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
    """BioHack document stored in 'biohacks' collection
    
    Fields:
        description (Optional[str]): Description of the biohack
        effects (Optional[List[Link[BioMarker]]]): Biomarkers affected
        involved_in (Optional[List[Link[Protocol]]]): Related protocols
        products (Optional[List[Link[Product]]]): Related products
        recommended_by (Optional[List[Link[Person]]]): People recommending this
        episodes (BackLink[Episode]): Episodes mentioning this biohack
    """

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
    """Business document stored in 'businesses' collection
    
    Fields:
        owner (Optional[Link[Person]]): Business owner
        products (Optional[List[Link[Product]]]): Products by this business
        biography (Optional[str]): Business biography
        market_cap (Optional[float]): Market capitalization
        mentioned_in (Optional[List[Link[Transcript]]]): Transcript mentions
        canonical_name (Optional[str]): Official business name
        aliases (Optional[List[str]]): Alternative names
        role_or_relevance (Optional[str]): Business role/relevance
        first_timestamp (Optional[str]): First mention timestamp
        attribution_quotes (Optional[List[Dict]]): Attribution quotes
        episodes (BackLink[Episode]): Episodes mentioning this business
        product_backlinks (BackLink[Product]): Products linked to this business
    """

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
    """Product document stored in 'products' collection
    
    Fields:
        name (str): Product name
        company (Optional[Link[Business]]): Company making the product
        helps_with (Optional[List[Link[BioHack]]]): Related biohacks
        cost (Optional[int]): Product cost
        buy_links (Optional[List[str]]): Purchase links
        description (Optional[str]): Product description
        recommended_by (Optional[List[Link[Person]]]): People recommending
        features (Optional[List[str]]): Product features
        protocols (Optional[List[str]]): Related protocols
        benefits_as_stated (Optional[List[str]]): Claimed benefits
        attribution_quotes (Optional[List[Dict]]): Attribution quotes
        episodes (BackLink[Episode]): Episodes mentioning this product
    """

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
    """Treatment document stored in 'treatments' collection
    
    Fields:
        name (str): Treatment name
        description (Optional[str]): Treatment description
        products (Optional[List[Link[Product]]]): Related products
        protocols (Optional[List[Link[Protocol]]]): Related protocols
        biomarkers (Optional[List[Link[BioMarker]]]): Affected biomarkers
        procedure_or_protocol (Optional[List[str]]): Treatment steps
        outcomes_as_reported (Optional[List[str]]): Reported outcomes
        risks_or_contraindications (Optional[List[str]]): Risks/contraindications
        confidence (Optional[Literal]): Confidence level
        attribution_quotes (Optional[List[Dict]]): Attribution quotes
        episodes (BackLink[Episode]): Episodes mentioning this treatment
    """

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
    """CaseStudy document stored in 'case_studies' collection
    
    Fields:
        title (str): Case study title
        description (Optional[str]): Case study description
        resources (Optional[List[Link[Resource]]]): Related resources
        products (Optional[List[Link[Product]]]): Related products
        businesses (Optional[List[Link[Business]]]): Related businesses
        treatments (Optional[List[Link[Treatment]]]): Related treatments
    """

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
    """SuccessStory document stored in 'success_stories' collection
    
    Fields:
        title (str): Success story title
        summary (Optional[str]): Success story summary
        person (Optional[Link[Person]]): Person involved
        product (Optional[Link[Product]]): Related product
        business (Optional[Link[Business]]): Related business
        resources (Optional[List[Link[Resource]]]): Related resources
        case_study (Optional[Link[CaseStudy]]): Related case study
        episodes (BackLink[Episode]): Episodes mentioning this story
    """

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
    """Claim document stored in 'claims' collection
    
    Fields:
        text (str): Claim text
        description (Optional[str]): Claim description
        claim_type (Optional[Literal]): Type of claim
        speaker (Optional[str]): Who made the claim
        evidence_present_in_transcript (Optional[Literal]): Evidence presence
        attribution_quotes (Optional[List[Dict]]): Attribution quotes
        persons (Optional[List[Link[Person]]]): Related people
        products (Optional[List[Link[Product]]]): Related products
        treatments (Optional[List[Link[Treatment]]]): Related treatments
        biomarkers (Optional[List[Link[BioMarker]]]): Related biomarkers
        businesses (Optional[List[Link[Business]]]): Related businesses
        protocols (Optional[List[Link[Protocol]]]): Related protocols
        transcript (Optional[Link[Transcript]]): Source transcript
        resources (Optional[List[Link[Resource]]]): Supporting resources
        compounds (Optional[List[Link[Compound]]]): Related compounds
        episodes (BackLink[Episode]): Episodes containing this claim
    """

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
    """Compound document stored in 'compounds' collection
    
    Fields:
        name (str): Compound name
        description (Optional[str]): Compound description
        products (Optional[List[Link[Product]]]): Related products
        protocols (Optional[List[Link[Protocol]]]): Related protocols
        claims (Optional[List[Link[Claim]]]): Related claims
        type (Optional[Literal]): Compound type
        benefits_as_stated (Optional[List[str]]): Stated benefits
    """

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
    """Episode document stored in 'episodes' collection
    
    Fields:
        channel (Link[Channel]): Parent channel
        episode_page_url (Optional[str]): Episode webpage URL
        transcript_url (Optional[str]): Transcript URL
        webpage_summary (Optional[str]): Webpage summary
        internal_summary (Optional[str]): Internal summary
        release_date (Optional[datetime]): Release date
        transcript (Optional[Link[Transcript]]): Episode transcript
        guests (Optional[List[Link[Person]]]): Episode guests
        webpage_resources (Optional[List[Link[Resource]]]): Resources
        sponsors (Optional[List[Dict]]): Episode sponsors
        learning_claims (Optional[List[str]]): Learning claims
        purpose (Optional[str]): Episode purpose
        participants (Optional[List[str]]): Participants
        main_sections (Optional[List[Dict]]): Main sections
        key_takeaways (Optional[List[str]]): Key takeaways
        overview_attribution_quotes (Optional[List[Dict]]): Attribution quotes
        products (Optional[List[Link[Product]]]): Related products
        protocols (Optional[List[Link[Protocol]]]): Related protocols
        biohacks (Optional[List[Link[BioHack]]]): Related biohacks
        businesses (Optional[List[Link[Business]]]): Related businesses
        claims (Optional[List[Link[Claim]]]): Related claims
        treatments (Optional[List[Link[Treatment]]]): Related treatments
        success_stories (Optional[List[Link[SuccessStory]]]): Success stories
    """

    # Channel that this episode belongs to
    channel: Link["Channel"]

    episode_page_url: Optional[str] = None
    transcript_url: Optional[str] = None
    webpage_summary: Optional[str] = None
    internal_summary: Optional[str] = None
    release_date: Optional[datetime] = None 
    episode_number: Optional[int] = None 

    # One transcript per episode (Link on Episode, BackLink on Transcript)
    transcript: Optional[Link[Transcript]] = None

    guests: Optional[List[Link[Person]]] = None

    # Webpage-level extraction
    webpage_resources: Optional[List[Link[Resource]]] = None 
    sponsors: Optional[List[Dict[str, Any]]] = None  
    learning_claims: Optional[List[str]] = None 

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
    """Channel document stored in 'channels' collection
    
    Fields:
        name (str): Channel name
        owner (Optional[Link[Person]]): Channel owner
        episodes (BackLink[Episode]): Channel episodes
    """

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
    """AttributionQuote document stored in 'attribution_quotes' collection
    
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

# LLM settings next to the document




class MedicalTreatmentOutput(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cost: Optional[float] = None


class MedicalTreatment(BaseDoc):
    """MedicalTreatment document stored in 'medical_treatments' collection
    
    Fields:
        name (str): Treatment name
        description (Optional[str]): Treatment description
        cost (Optional[float]): Treatment cost
        persons (Optional[List[Link[Person]]]): Related people
        businesses (Optional[List[Link[Business]]]): Related businesses
        products (Optional[List[Link[Product]]]): Related products
        protocols (Optional[List[Link[Protocol]]]): Related protocols
        biomarkers (Optional[List[Link[BioMarker]]]): Related biomarkers
        success_stories (Optional[List[Link[SuccessStory]]]): Success stories
    """

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