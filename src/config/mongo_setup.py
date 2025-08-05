from pymongo import MongoClient
from pymongo.errors import ConnectionFailure  
from motor.motor_asyncio import AsyncIOMotorClient 
from dotenv import load_dotenv
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_mongo_client():
    """
    Creates and returns a MongoDB client connection.
    Handles connection errors and validation.
    """
    uri = os.getenv("MONGO_CONNECTION")
    
    if not uri:
        logger.error("MongoDB connection string not found in environment variables")
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
    Creates and returns an asynchronous MongoDB client connection.
    Handles connection errors and validation.
    """
    uri = os.getenv("MONGO_CONNECTION")
    
    if not uri:
        logger.error("MongoDB connection string not found in environment variables")
        sys.exit(1)
        
    try:
        # Create client with reasonable timeouts and pool settings
        client = AsyncIOMotorClient(uri,
                                   serverSelectionTimeoutMS=5000,
                                   connectTimeoutMS=10000,
                                   maxPoolSize=50)
        
        # Verify connection is working  
        await client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        return client
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
# Create singleton client instance
# client = get_mongo_client() 


if __name__ == "__main__":
    logger.info("MongoDB client initialized and ready")