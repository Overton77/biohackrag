# Beanie ODM Reference Guide

## Overview

Beanie is an asynchronous Object Document Mapper (ODM) for MongoDB built on top of PyMongo and Pydantic. This guide covers the key concepts and patterns for working with Beanie in your project.

## Table of Contents

1. [Setup and Initialization](#setup-and-initialization)
2. [Document Models](#document-models)
3. [Relationships](#relationships)
4. [CRUD Operations](#crud-operations)
5. [Querying](#querying)
6. [Best Practices](#best-practices)

---

## Setup and Initialization

### 1. Dependencies

```toml
# pyproject.toml
dependencies = [
  "pydantic>=2.11,<3",
  "pymongo>=4.11,<5",
  "beanie>=2,<3",
  "python-dotenv>=1.0.0",
]
```

### 2. Database Connection Setup

```python
from pymongo import AsyncMongoClient
from beanie import init_beanie
import os
from dotenv import load_dotenv

load_dotenv()

async def get_async_mongo_client():
    """Create async MongoDB client"""
    uri = os.getenv("MONGO_CONNECTION")
    client = AsyncMongoClient(
        uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        maxPoolSize=50
    )
    # Verify connection
    await client.admin.command('ping')
    return client
```

### 3. Initialize Beanie

```python
async def init_beanie_with_pymongo():
    """Initialize Beanie with document models"""
    client = await get_async_mongo_client()

    # Initialize Beanie with your document models
    await init_beanie(
        database=client.db_name,  # Your database name
        document_models=[Company, Product, Person, Transcript, Claim]
    )
    return client
```

---

## Document Models

### 1. Basic Document Structure

```python
from beanie import Document
from pydantic import BaseModel
from typing import Optional, List

class Company(Document):
    """Basic document with simple fields"""
    canonical_name: Optional[str] = None
    aliases: List[str] = []
    category: Optional[str] = None
    website: Optional[str] = None
    role_or_relevance: Optional[str] = None
    first_timestamp: Optional[str] = None

    class Settings:
        # Optional: customize collection name
        name = "companies"
```

### 2. Embedded Documents (Sub-documents)

```python
class AttributionQuote(BaseModel):
    """Embedded document - not stored in separate collection"""
    text: Optional[str] = None
    timestamp: Optional[str] = None
    speaker: Optional[str] = None
    chunk_id: Optional[str] = None

class Product(Document):
    name: Optional[str] = None
    description: Optional[str] = None
    features: List[str] = []
    protocols: List[str] = []
    benefits_as_stated: List[str] = []
    # Embedded documents as list
    attribution: List[AttributionQuote] = []
```

---

## Relationships

### 1. One-to-Many Relationships

```python
from beanie import Link

class Product(Document):
    name: Optional[str] = None
    # Reference to Company document
    company: Optional[Link[Company]] = None

class Person(Document):
    canonical_name: Optional[str] = None
    # List of references to Company documents
    companies: List[Link[Company]] = []
```

### 2. Creating Relationships

```python
# Create parent document first
company = await Company(
    canonical_name="Acme Health",
    category="Biohacking"
).insert()

# Create child document with reference
product = await Product(
    name="Acme Red Light",
    description="660nm panel",
    company=company  # Direct reference
).insert()

# Multiple references
person = await Person(
    canonical_name="Jane Biohacker",
    companies=[company]  # List of references
).insert()
```

---

## CRUD Operations

### 1. Create (Insert)

```python
# Single document
company = await Company(
    canonical_name="Example Corp",
    category="Technology"
).insert()

# Multiple documents
companies = await Company.insert_many([
    Company(canonical_name="Corp A"),
    Company(canonical_name="Corp B")
])
```

### 2. Read (Find)

```python
# Find one document
company = await Company.find_one(Company.canonical_name == "Acme Health")

# Find multiple documents
companies = await Company.find(Company.category == "Biohacking").to_list()

# Find all documents
all_companies = await Company.find_all().to_list()

# Find by ID
company = await Company.get(company_id)
```

### 3. Update

```python
# Update single document
await company.set({Company.category: "Updated Category"})

# Update multiple documents
await Company.find(Company.category == "Old Category").update(
    {"$set": {Company.category: "New Category"}}
)

# Replace document
company.category = "New Category"
await company.replace()
```

### 4. Delete

```python
# Delete single document
await company.delete()

# Delete multiple documents
await Company.find(Company.category == "Obsolete").delete()
```

---

## Querying

### 1. Basic Queries

```python
# Equality
companies = await Company.find(Company.category == "Biohacking").to_list()

# Multiple conditions
products = await Product.find(
    Product.name == "Red Light",
    Product.company.id == company_id
).to_list()
```

### 2. Relationship Queries

```python
# Query by referenced document ID
products = await Product.find(Product.company.id == company.id).to_list()

# Fetch with linked documents populated
products = await Product.find(
    Product.company.id == company.id,
    fetch_links=True  # Populates company data
).to_list()

# Query person with populated company links
person = await Person.find_one(
    Person.id == person_id,
    fetch_links=True
)
```

### 3. Complex Queries

```python
# Claims for specific transcript
claims = await Claim.find(Claim.transcript.id == transcript.id).to_list()

# Claims by speaker and transcript
claims = await Claim.find(
    Claim.speaker == "Jane Biohacker",
    Claim.transcript.id == transcript.id
).to_list()

# Using regex
companies = await Company.find(
    {"canonical_name": {"$regex": "Health", "$options": "i"}}
).to_list()
```

### 4. Aggregation

```python
# Count documents
count = await Company.find(Company.category == "Biohacking").count()

# Aggregation pipeline
pipeline = [
    {"$match": {"category": "Biohacking"}},
    {"$group": {"_id": "$category", "count": {"$sum": 1}}}
]
result = await Company.aggregate(pipeline).to_list()
```

---

## Best Practices

### 1. Document Design

- Use embedded documents for data that belongs together and won't be queried independently
- Use references (Links) for data that will be queried separately or shared across documents
- Keep embedded documents small to avoid document size limits

### 2. Relationship Patterns

```python
# Good: One-to-many with Link
class Order(Document):
    customer: Link[Customer]  # Reference to customer
    items: List[OrderItem]    # Embedded order items

# Good: Many-to-many with Links
class Person(Document):
    companies: List[Link[Company]]  # Person can work for multiple companies
```

### 3. Query Optimization

```python
# Use fetch_links=True when you need referenced data
products = await Product.find(
    Product.category == "Electronics",
    fetch_links=True  # Populates company data
).to_list()

# Don't fetch links if you only need IDs
product_ids = await Product.find(
    Product.category == "Electronics"
).project(Product.id).to_list()
```

### 4. Error Handling

```python
async def safe_insert_company(name: str):
    try:
        company = await Company(canonical_name=name).insert()
        return company
    except Exception as e:
        logger.error(f"Failed to insert company {name}: {e}")
        return None
```

### 5. Connection Management

```python
async def demo_with_cleanup():
    client = await init_beanie_with_pymongo()
    try:
        # Your database operations here
        companies = await Company.find_all().to_list()
        return companies
    finally:
        # Always close the client
        await client.close()
```

### 6. Environment Configuration

```bash
# .env file
MONGO_CONNECTION=mongodb://localhost:27017/your_database
LOG_LEVEL=INFO
```

---

## Example Complete Workflow

```python
import asyncio
import logging
from your_models import Company, Product, Person, Transcript, Claim
from your_config import init_beanie_with_pymongo

async def complete_example():
    # Initialize Beanie
    client = await init_beanie_with_pymongo()

    try:
        # 1. Create a company
        company = await Company(
            canonical_name="Acme Health",
            category="Biohacking",
            website="https://acmehealth.com"
        ).insert()

        # 2. Create a product linked to the company
        product = await Product(
            name="Red Light Panel",
            description="660nm therapeutic light",
            features=["660nm wavelength", "LED technology"],
            company=company
        ).insert()

        # 3. Create a person associated with the company
        person = await Person(
            canonical_name="Dr. Jane Smith",
            role_or_relevance="Founder",
            companies=[company]
        ).insert()

        # 4. Query relationships
        # Find all products for this company
        company_products = await Product.find(
            Product.company.id == company.id,
            fetch_links=True
        ).to_list()

        # Find all people associated with this company
        company_people = await Person.find(
            Person.companies.id == company.id,
            fetch_links=True
        ).to_list()

        logging.info(f"Company {company.canonical_name} has:")
        logging.info(f"- {len(company_products)} products")
        logging.info(f"- {len(company_people)} people")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(complete_example())
```

---

## Running Your Code

Based on your project structure, run your Beanie code with:

```bash
# For modules with __init__.py
uv run python -m src.mongo_schemas_test

# For standalone scripts
uv run python your_script.py
```

This guide covers the essential patterns used in your working code. Beanie provides a clean, async-first approach to working with MongoDB while leveraging Pydantic's validation and type safety.
