from pymongo import MongoClient, AsyncMongoClient
from pymongo.errors import ConnectionFailure   
import sys
import logging 
from typing import Union, Dict, Any
from pydantic import BaseModel
from beanie import init_beanie  
from config.settings import get_settings
from src.mongo_schema_overwrite import (  
     Business, Person, Product, Compound, MedicalTreatment, Resource, Transcript, Claim, Episode, BioHack, BioMarker, Protocol, Treatment, CaseStudy, BaseDoc, TimeStamped, SuccessStory, Channel, AttributionQuote)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

def get_mongo_client():
    """
    Creates and returns a MongoDB client connection.
    Handles connection errors and validation.
    """
    # Prefer settings.mongo_db_uri; fallback to legacy env name if present in process
    uri = settings.mongo_db_uri or None
    
    if not uri:
        logger.error("MongoDB connection string not found in settings (mongo_db_uri)")
        sys.exit(1)
        
    try:
        # Create client with reasonable timeouts and pool settings
        client = MongoClient(uri,
                           serverSelectionTimeoutMS=5000,
                           connectTimeoutMS=10000,
                           maxPoolSize=50)
        
        # Verify connection is working
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        return client
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        sys.exit(1) 

async def get_async_mongo_client():
    """
    Creates and returns an asynchronous MongoDB client connection using PyMongo's native async support.
    Handles connection errors and validation.
    """
    uri = settings.mongo_db_uri or None
    
    if not uri:
        logger.error("MongoDB connection string not found in settings (mongo_db_uri)")
        return None
        
    try:
        # Create async client with reasonable timeouts and pool settings
        client = AsyncMongoClient(uri,
                                 serverSelectionTimeoutMS=5000,
                                 connectTimeoutMS=10000,
                                 maxPoolSize=50)
        
        # Verify connection is working  
        await client.admin.command('ping')
        logger.info("Successfully connected to MongoDB (async)")
        return client
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {str(e)}")
        return None

# Create singleton client instance
# client = get_mongo_client()   

async def init_beanie_with_pymongo() -> AsyncMongoClient:
    """Initialize Beanie with all document models"""
    client = await get_async_mongo_client()
    if client is None:
        raise RuntimeError("Async Mongo client not available. Check MONGO_CONNECTION.")
    
    # Initialize Beanie with all document models
    db_name = settings.mongo_db_name or "biohack_agent"
    await init_beanie(
        database=client[db_name], 
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




if __name__ == "__main__": 
    # asyncio.run(get_async_mongo_client())
    logger.info("MongoDB client initialized and ready")