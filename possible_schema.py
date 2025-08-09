from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field
from beanie import Document, Link, BackLink, Indexed

# ---------- Shared Base Models ----------

class TimeStamped(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


class BaseDoc(Document, TimeStamped):
    class Settings:
        use_state_management = True


# ---------- Core Entities ----------

class Company(BaseDoc):
    name: Indexed(str)
    domain: Optional[str] = None
    description: Optional[str] = None

    people: BackLink["Person"]
    products: BackLink["Product"]

    class Settings:
        name = "companies"


class Person(BaseDoc):
    full_name: Indexed(str)
    title: Optional[str] = None
    company: Optional[Link[Company]] = None
    bio: Optional[str] = None

    class Settings:
        name = "people"


class Product(BaseDoc):
    name: Indexed(str)
    company: Optional[Link[Company]] = None
    category: Optional[str] = None
    tags: List[str] = []
    resources: List[Link["Resource"]] = []

    class Settings:
        name = "products"


class MedicalTreatment(BaseDoc):
    name: Indexed(str)
    description: Optional[str] = None
    products: List[Link[Product]] = []

    class Settings:
        name = "medical_treatments"


class Resource(BaseDoc):
    """External references: URLs, PDFs, papers, blog posts, etc."""
    url: Indexed(str)
    title: Optional[str] = None
    kind: Optional[str] = Field(default=None, description="e.g., paper, blog, video, repo")
    meta: Dict[str, Any] = {}

    # NOTE: simplified per request (no backlinks to claims)
    class Settings:
        name = "resources"


class BioMarker(BaseDoc):
    name: Indexed(str)
    units: Optional[str] = None
    description: Optional[str] = None

    class Settings:
        name = "biomarkers"


# ---------- Protocol / BioHack ----------

class Protocol(BaseDoc):
    """
    Simplified protocol; linked to BioHacks & Claims.
    """
    name: Indexed(str)
    description: Optional[str] = None

    # Reverse links (filled automatically)
    biohacks: BackLink["BioHack"]
    claims: BackLink["Claim"]

    class Settings:
        name = "protocols"


class BioHack(BaseDoc):
    """
    Practical regimen connected to a Protocol, Treatments, Biomarkers, and Products.
    """
    name: Indexed(str)
    goal: Optional[str] = None

    protocol: Optional[Link[Protocol]] = None
    treatments: List[Link[MedicalTreatment]] = []
    biomarkers_tracked: List[Link[BioMarker]] = []
    products: List[Link[Product]] = []  # <-- per request

    class Settings:
        name = "biohacks"


# ---------- Episode / Transcript ----------

class Episode(BaseDoc):
    """
    One episode; one transcript (enforced via unique index on Transcript.episode).
    """
    title: Indexed(str)
    published_at: Optional[datetime] = None
    series: Optional[str] = None
    guests: List[Link[Person]] = []
    companies_mentioned: List[Link[Company]] = []

    class Settings:
        name = "episodes"


# ---------- Claims ----------

class ClaimSubject(BaseModel):
    product: Optional[Link[Product]] = None
    treatment: Optional[Link[MedicalTreatment]] = None
    company: Optional[Link[Company]] = None
    person: Optional[Link[Person]] = None
    biomarker: Optional[Link[BioMarker]] = None


class Claim(BaseDoc):
    """
    Kept top-level for easy querying; now can point to a Protocol.
    """
    text: Indexed(str)
    subjects: ClaimSubject = Field(default_factory=ClaimSubject)
    source_transcript: Link["Transcript"]
    source_episode: Optional[Link[Episode]] = None
    resources: List[Link[Resource]] = []
    protocol: Optional[Link[Protocol]] = None  # <-- link to Protocol
    stance: Optional[Literal["for", "against", "neutral"]] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    meta: Dict[str, Any] = {}

    class Settings:
        name = "claims"


# ---------- Transcript (simplified) ----------

class Transcript(BaseDoc):
    """
    Simplified: optional links to entities + simple string summaries.
    One-to-one with Episode is enforced by a unique index on 'episode'.
    """
    episode: Optional[Link[Episode]] = None
    source_url: Optional[str] = None
    language: Optional[str] = "en"

    # Optional links
    companies: List[Link[Company]] = []
    products: List[Link[Product]] = []
    people: List[Link[Person]] = []
    claims: List[Link[Claim]] = []

    # Simple summaries (all optional strings)
    product_summary: Optional[str] = None
    medical_treatment_summary: Optional[str] = None
    business_entities_summary: Optional[str] = None
    claims_made_summary: Optional[str] = None
    high_level_overview: Optional[str] = None
    final_aggregate_summary: Optional[str] = None

    # Raw text (no chunking for simplicity)
    full_text: Optional[str] = None

    meta: Dict[str, Any] = {}

    class Settings:
        name = "transcripts"
        indexes = [
            # Enforce one Transcript per Episode
            {"keys": [("episode", 1)], "unique": True},
        ]
