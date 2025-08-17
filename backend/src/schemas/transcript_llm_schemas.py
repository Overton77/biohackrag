from pydantic import BaseModel, Field 
from typing import List, Optional, Dict, Any, Literal, Union, TYPE_CHECKING
from datetime import datetime, UTC

# ========= Common mixins =========




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



class PersonOutput(BaseModel):
    """Pydantic output model for Person document.
    
    Fields:
        name (str): Person's name
        kind (Optional[PersonKind]): Type of person
    """
    name: str = None
    kind: Optional[PersonKind] = None


# ==================================================
# Transcript (consolidated structured block)
# ==================================================

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



class TranscriptOutput(BaseModel):
    """Pydantic output model for Transcript document.
    
    Fields:
        product_summary (Optional[str]): Summary of products
        business_summary (Optional[str]): Summary of businesses
        medical_treatment_summary (Optional[str]): Summary of medical treatments
        claims_made_summary (Optional[str]): Summary of claims
        high_level_overview_summary (Optional[str]): High-level overview
        master_aggregate_summary (Optional[str]): Aggregate summary
        structured (Optional[TranscriptStructured]): Structured data
    """
    product_summary: Optional[str] = None
    business_summary: Optional[str] = None
    medical_treatment_summary: Optional[str] = None
    claims_made_summary: Optional[str] = None
    high_level_overview_summary: Optional[str] = None
    master_aggregate_summary: Optional[str] = None
    structured: Optional[TranscriptStructured] = None




class BioMarkerOutput(BaseModel):
    """Pydantic output model for BioMarker document.
    
    Fields:
        name (Optional[str]): Biomarker name
        description (Optional[str]): Description
        age_range_optimal (Optional[Dict]): Optimal age range
        needs_lab (Optional[bool]): Lab testing requirement
    """
    name: Optional[str] = None  
    description: Optional[str] = None  
    age_range_optimal: Optional[Dict[str, Any]] = None
    needs_lab: Optional[bool] = None




class ProtocolOutput(BaseModel):
    """Pydantic output model for Protocol document.
    
    Fields:
        name (Optional[str]): Protocol name
        description (Optional[str]): Description
    """
    name: Optional[str] = None
    description: Optional[str] = None




class BioHackOutput(BaseModel):
    """Pydantic output model for BioHack document.
    
    Fields:
        name (Optional[str]): BioHack name
        description (Optional[str]): Description
    """
    name: Optional[str] = None 
    description: Optional[str] = None





class BusinessOutput(BaseModel):
    """Pydantic output model for Business document.
    
    Fields:
        biography (Optional[str]): Business biography
        market_cap (Optional[float]): Market capitalization
        canonical_name (Optional[str]): Official name
        aliases (List[str]): Alternative names
        role_or_relevance (Optional[str]): Role/relevance
        first_timestamp (Optional[str]): First mention
    """
    biography: Optional[str] = None
    market_cap: Optional[float] = None
    canonical_name: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    role_or_relevance: Optional[str] = None
    first_timestamp: Optional[str] = None



class ProductOutput(BaseModel):
    """Pydantic output model for Product document.
    
    Fields:
        name (Optional[str]): Product name
        cost (Optional[int]): Cost
        buy_links (List[str]): Purchase links
        description (Optional[str]): Description
        features (List[str]): Features
        protocols (List[str]): Protocols
        benefits_as_stated (List[str]): Benefits
    """
    name: Optional[str] = None
    cost: Optional[int] = None
    buy_links: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    protocols: List[str] = Field(default_factory=list)
    benefits_as_stated: List[str] = Field(default_factory=list)



class TreatmentOutput(BaseModel):
    """Pydantic output model for Treatment document.
    
    Fields:
        name (Optional[str]): Treatment name
        description (Optional[str]): Description
        procedure_or_protocol (List[str]): Procedure
        outcomes_as_reported (List[str]): Outcomes
        risks_or_contraindications (List[str]): Risks
        confidence (Optional[Confidence]): Confidence
    """
    name: Optional[str] = None
    description: Optional[str] = None
    procedure_or_protocol: List[str] = Field(default_factory=list)
    outcomes_as_reported: List[str] = Field(default_factory=list)
    risks_or_contraindications: List[str] = Field(default_factory=list)
    confidence: Optional[Confidence] = None



class CaseStudyOutput(BaseModel):
    """Pydantic output model for CaseStudy document.
    
    Fields:
        title (Optional[str]): Case study title
        description (Optional[str]): Description
        resources_unlinked (Optional[List[str]]): Resources
        url (Optional[str]): URL
    """
    title: Optional[str] = None
    description: Optional[str] = None  
    resources_unlinked: Optional[List[str]] = None   
    url: Optional[str] = None  




class SuccessStoryOutput(BaseModel):
    """Pydantic output model for SuccessStory document.
    
    Fields:
        title (Optional[str]): Story title
        summary (Optional[str]): Summary
        url (Optional[str]): URL
    """
    title: Optional[str] = None
    summary: Optional[str] = None 
    url: Optional[str] = None  



class ClaimOutput(BaseModel):
    """Pydantic output model for Claim document.
    
    Fields:
        text (Optional[str]): Claim text
        description (Optional[str]): Description
        claim_type (Optional[ClaimType]): Type
        speaker (Optional[str]): Speaker
        evidence_present_in_transcript (Optional[Literal]): Evidence
    """
    text: Optional[str] = None
    description: Optional[str] = None
    claim_type: Optional[ClaimType] = None
    speaker: Optional[str] = None
    evidence_present_in_transcript: Optional[Literal["yes", "no"]] = None



class CompoundOutput(BaseModel):
    """Pydantic output model for Compound document.
    
    Fields:
        name (Optional[str]): Compound name
        description (Optional[str]): Description
        type (Optional[CompoundType]): Type
        benefits_as_stated (List[str]): Benefits
    """
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[CompoundType] = None
    benefits_as_stated: List[str] = Field(default_factory=list)





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





class EpisodeOutput(BaseModel):
    """Pydantic output model for Episode document.
    
    Fields:
        episode_page_url (Optional[str]): Page URL
        transcript_url (Optional[str]): Transcript URL
        webpage_summary (Optional[str]): Webpage summary
        internal_summary (Optional[str]): Internal summary
        release_date (Optional[datetime]): Release date
        episode_number (Optional[int]): Episode number
        sponsors (List[Dict]): Sponsors
        learning_claims (List[str]): Learning claims
        purpose (Optional[str]): Purpose
        participants (List[str]): Participants
        main_sections (List[Dict]): Sections
        key_takeaways (List[str]): Takeaways
        overview_attribution_quotes (List[Dict]): Quotes
    """
    episode_page_url: Optional[str] = None
    transcript_url: Optional[str] = None
    webpage_summary: Optional[str] = None
    internal_summary: Optional[str] = None
    release_date: Optional[datetime] = None
    episode_number: Optional[int] = None
    sponsors: List[Dict[str, Any]] = Field(default_factory=list)
    learning_claims: List[str] = Field(default_factory=list)
    purpose: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    main_sections: List[Dict[str, Any]] = Field(default_factory=list)
    key_takeaways: List[str] = Field(default_factory=list)
    overview_attribution_quotes: List[Dict[str, Any]] = Field(default_factory=list)



class AttributionQuoteOutput(BaseModel):
    """Pydantic output model for AttributionQuote document.
    
    Fields:
        quote (Optional[str]): Quote text
        timestamp (Optional[str]): Timestamp
        person (Optional[str]): Person
        reference (Optional[str]): Reference
    """
    quote: Optional[str] = None
    timestamp: Optional[str] = None 
    person: Optional[str] = None   
    reference: Optional[str] = None 






class MedicalTreatmentOutput(BaseModel):
    """Pydantic output model for MedicalTreatment document.
    
    Fields:
        name (Optional[str]): Treatment name
        description (Optional[str]): Description
        cost (Optional[float]): Cost
    """
    name: Optional[str] = None
    description: Optional[str] = None
    cost: Optional[float] = None






    

if __name__ == "__main__":  
    print("Importing llm transcript output schemas")