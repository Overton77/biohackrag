import os
import asyncio
import logging
from typing import Optional, List

from beanie import Document, Link, init_beanie
from pydantic import BaseModel
from pymongo import AsyncMongoClient

from src.config.mongo_setup import get_async_mongo_client 
from dotenv import load_dotenv 

load_dotenv() 


logger = logging.getLogger(__name__)


class AttributionQuote(BaseModel):
    text: Optional[str] = None
    timestamp: Optional[str] = None
    speaker: Optional[str] = None
    chunk_id: Optional[str] = None


class Company(Document):
    canonical_name: Optional[str] = None
    aliases: List[str] = []
    category: Optional[str] = None
    website: Optional[str] = None
    role_or_relevance: Optional[str] = None
    first_timestamp: Optional[str] = None


class Product(Document):
    name: Optional[str] = None
    description: Optional[str] = None
    features: List[str] = []
    protocols: List[str] = []
    benefits_as_stated: List[str] = []
    attribution: List[AttributionQuote] = []
    company: Optional[Link[Company]] = None


class Person(Document):
    canonical_name: Optional[str] = None
    aliases: List[str] = []
    role_or_relevance: Optional[str] = None
    first_timestamp: Optional[str] = None
    social_links: List[str] = []
    description: Optional[str] = None
    attribution: List[AttributionQuote] = []
    companies: List[Link[Company]] = []


class Transcript(Document):
    content: Optional[str] = None
    episode_url: Optional[str] = None


class Claim(Document):
    speaker: Optional[str] = None
    claim_text: Optional[str] = None
    claim_type: Optional[str] = None  # causal | quantitative | experiential | other
    evidence_present_in_transcript: Optional[str] = None  # yes | no
    attribution: List[AttributionQuote] = []
    transcript: Optional[Link[Transcript]] = None
    speaker_person: Optional[Link[Person]] = None


async def init_beanie_with_pymongo() -> AsyncMongoClient:
    client = await get_async_mongo_client()
    if client is None:
        raise RuntimeError("Async Mongo client not available. Check MONGO_CONNECTION.")
    await init_beanie(database=client.biohack_agent, document_models=[Company, Product, Person, Transcript, Claim])
    return client


async def demo_relationships():
    client = await init_beanie_with_pymongo()
    try:
        # 1) Create a company
        acme = await Company(canonical_name="Acme Health", category="Biohacking").insert()
        logger.info("Inserted company _id=%s", acme.id)

        # 2) Create a product linked to company
        product = await Product(name="Acme Red Light", description="660nm panel", company=acme).insert()
        logger.info("Inserted product _id=%s (company_id=%s)", product.id, acme.id)

        # 3) Create a person linked to the company
        person = await Person(canonical_name="Jane Biohacker", companies=[acme]).insert()
        logger.info("Inserted person _id=%s", person.id)

        # 4) Create a transcript
        transcript = await Transcript(content="...transcript text...", episode_url="https://example/ep1").insert()
        logger.info("Inserted transcript _id=%s", transcript.id)

        # 5) Create a claim linked to transcript and speaker
        claim = await Claim(
            speaker="Jane Biohacker",
            claim_text="Red light therapy improves sleep quality",
            claim_type="causal",
            evidence_present_in_transcript="yes",
            transcript=transcript,
            speaker_person=person,
        ).insert()
        logger.info("Inserted claim _id=%s", claim.id)

        # Queries using relationships
        products_for_company = await Product.find(Product.company.id == acme.id, fetch_links=True).to_list()
        logger.info("Products for company %s: %d", acme.id, len(products_for_company))

        person_with_links = await Person.find_one(Person.id == person.id, fetch_links=True)
        num_companies = len(person_with_links.companies) if person_with_links and person_with_links.companies else 0
        logger.info("Companies for person %s: %d", person.id, num_companies)

        claims_for_transcript = await Claim.find(Claim.transcript.id == transcript.id).to_list()
        logger.info("Claims for transcript %s: %d", transcript.id, len(claims_for_transcript))

    finally:
        try:
            await client.close()
        except Exception:
            pass


async def main():
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    await demo_relationships()


if __name__ == "__main__":
    # Run with: uv run python -m src.mongo_schemas_test
    # asyncio.run(main())
