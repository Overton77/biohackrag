# MongoDB Schema Documentation - mongo_schema_overwrite.py

## Overview

The `mongo_schema_overwrite.py` file defines the complete MongoDB schema for a biohacking/health optimization application using **Beanie**, a modern async ODM (Object Document Mapper) for MongoDB built on top of Pydantic and Motor.

### Key Features
- **Async/await support** through Beanie ODM
- **Type safety** with Pydantic models and Python type hints
- **Automatic validation** and serialization/deserialization
- **Document relationships** using Beanie's Link and BackLink
- **Timestamping** with automatic created_at/updated_at fields
- **Flexible schema** with support for legacy data migration

## Architecture Overview

The schema is organized into several logical groups:
1. **Base Classes & Mixins** - Common functionality shared across documents
2. **Enums** - Controlled vocabularies for finite field values
3. **Document Collections** - Main data models representing MongoDB collections
4. **Utility Functions** - Helpers for data conversion and manipulation

## Base Classes and Mixins

### TimeStamped Mixin
```python
class TimeStamped(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```
Provides automatic timestamping for all documents with UTC timezone support.

### BaseDoc Abstract Base Class
```python
class BaseDoc(Document, TimeStamped):
    class Settings:
        use_state_management = False
    model_config = ConfigDict(extra="ignore")
```
- Inherits from both Beanie's `Document` and `TimeStamped`
- Disables state management for performance
- Ignores unknown fields for backward compatibility with legacy data

## Enumeration Classes

### PersonKind
Defines types of people in the system:
- `host`: Show/podcast host
- `guest`: Show/podcast guest  
- `doctor`: Medical professional
- `other`: Other person type

### ClaimType
Categorizes different types of claims:
- `causal`: Claims about cause and effect relationships
- `quantitative`: Claims with numerical/measurable data
- `experiential`: Claims based on personal experience
- `other`: Other types of claims

### CompoundType
Classifies substances and compounds:
- `supplement`: Dietary/nutritional supplement
- `food`: Food item
- `herb`: Herbal substance
- `other`: Other compound type

### Confidence
Represents confidence levels:
- `high`: High confidence
- `medium`: Medium confidence
- `low`: Low confidence

## Document Collections

### Core People & Content

#### Person Collection (`persons`)
```python
class Person(BaseDoc):
    name: str
    kind: Optional[PersonKind] = None
```
Stores information about people (hosts, guests, doctors, etc.)

**Example Usage:**
```python
# Create a new person
person = Person(name="Dr. Andrew Huberman", kind=PersonKind.host)
await person.save()

# Query persons
hosts = await Person.find(Person.kind == PersonKind.host).to_list()
```

#### Channel Collection (`channels`)
```python
class Channel(BaseDoc):
    name: str
    owner: Optional[Link[Person]] = None
    episodes: List[BackLink["Episode"]] = Field(default_factory=list, original_field="channel")
```
Represents podcast channels or shows with bidirectional relationship to episodes.

#### Episode Collection (`episodes`)
```python
class Episode(BaseDoc):
    channel: Optional[Link[Channel]] = None
    episode_page_url: Optional[str] = None
    transcript_url: Optional[str] = None
    # ... many more fields
    mentions: Optional[EpisodeMentions] = None
```
Comprehensive episode metadata with relationships to all other entities.

#### Transcript Collection (`transcripts`)
```python
class Transcript(BaseDoc):
    product_summary: Optional[str] = None
    compound_summary: Optional[str] = None
    # ... multiple summary fields
    structured: Optional[TranscriptStructured] = None
```
Stores processed transcript content with various summaries and structured data.

### Health & Wellness Entities

#### BioMarker Collection (`biomarkers`)
```python
class BioMarker(BaseDoc):
    name: str
    description: Optional[str] = None
    age_range_optimal: Optional[Dict[str, Any]] = None
    needs_lab: bool = False
```
Represents measurable biological indicators.

#### Protocol Collection (`protocols`)
```python
class Protocol(BaseDoc):
    name: str
    description: Optional[str] = None
    biomarkers: List[Link[BioMarker]] = Field(default_factory=list)
```
Health optimization protocols linked to relevant biomarkers.

#### BioHack Collection (`biohacks`)
```python
class BioHack(BaseDoc):
    description: Optional[str] = None
    effects: List[Link[BioMarker]] = Field(default_factory=list)
```
Specific biohacking techniques and their effects on biomarkers.

### Products & Business

#### Business Collection (`businesses`)
```python
class Business(BaseDoc):
    owner: Optional[Link[Person]] = None
    canonical_name: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    market_cap: Optional[float] = None
    # ... additional business metadata
```

#### Product Collection (`products`)
```python
class Product(BaseDoc):
    name: str
    company: Optional[Link[Business]] = None
    helps_with: List[Link[BioHack]] = Field(default_factory=list)
    cost: Optional[int] = None
    recommended_by: List[Link[Person]] = Field(default_factory=list)
    # ... product details and relationships
```

#### Compound Collection (`compounds`)
```python
class Compound(BaseDoc):
    name: str
    type: CompoundType = CompoundType.other
    benefits_as_stated: List[str] = Field(default_factory=list)
    products: Optional[List[Link[Product]]] = None
```

### Medical & Research

#### Treatment Collection (`treatments`)
```python
class Treatment(BaseDoc):
    name: str
    protocols: Optional[List[Link[Protocol]]] = None
    outcomes_as_reported: List[str] = Field(default_factory=list)
    risks_or_contraindications: List[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.medium
```

#### MedicalTreatment Collection (`medical_treatments`)
```python
class MedicalTreatment(BaseDoc):
    name: str
    cost: Optional[float] = None
    products: List[Link[Product]] = Field(default_factory=list)
    protocols: List[Link[Protocol]] = Field(default_factory=list)
    biomarkers: List[Link[BioMarker]] = Field(default_factory=list)
```

### Research & Evidence

#### Claim Collection (`claims`)
```python
class Claim(BaseDoc):
    text: str
    claim_type: ClaimType = ClaimType.other
    speaker: Optional[str] = None
    evidence_present_in_transcript: Literal["yes", "no"] = "no"
    transcript: Optional[Link[Transcript]] = None
    persons: List[Link[Person]] = Field(default_factory=list)
```

#### Resource Collection (`resources`)
```python
class Resource(BaseDoc):
    url: str
    title: Optional[str] = None
    kind: Optional[str] = None  # "paper", "video", "blog"
    meta: Dict[str, Any] = Field(default_factory=dict)
```

#### CaseStudy Collection (`case_studies`)
```python
class CaseStudy(BaseDoc):
    title: str
    description: Optional[str] = None
    resources: List[Link[Resource]] = Field(default_factory=list)
```

#### SuccessStory Collection (`success_stories`)
```python
class SuccessStory(BaseDoc):
    title: str
    person: Optional[Link[Person]] = None
    resources: Optional[List[Link[Resource]]] = None
    case_study: Optional[Link[CaseStudy]] = None
```

## Beanie ODM Usage Examples

### Initialization
```python
import asyncio
from mongo_schema_overwrite import init_beanie_with_pymongo

async def setup_database():
    """Initialize Beanie with all document models"""
    client = await init_beanie_with_pymongo()
    return client

# Usage
client = asyncio.run(setup_database())
```

### Basic CRUD Operations

#### Creating Documents
```python
# Create a person
person = Person(name="Dr. Rhonda Patrick", kind=PersonKind.doctor)
await person.save()

# Create a channel with owner relationship
channel = Channel(name="FoundMyFitness", owner=person)
await channel.save()

# Create a product with multiple relationships
product = Product(
    name="Vitamin D3",
    cost=25,
    recommended_by=[person],
    benefits_as_stated=["Immune support", "Bone health"]
)
await product.save()
```

#### Reading Documents
```python
# Find all hosts
hosts = await Person.find(Person.kind == PersonKind.host).to_list()

# Find episodes with populated channel data
episodes = await Episode.find().populate(Episode.channel).to_list()

# Complex query with multiple conditions
expensive_supplements = await Product.find(
    Product.cost > 50,
    Product.helps_with.name == "Sleep Optimization"
).to_list()

# Find with sorting and limiting
recent_episodes = await Episode.find().sort(-Episode.release_date).limit(10).to_list()
```

#### Updating Documents
```python
# Update a single field
await person.update({"$set": {"kind": PersonKind.host}})

# Update with Beanie's update methods
await Person.find(Person.name == "Dr. Andrew Huberman").update(
    {"$set": {"kind": PersonKind.host}}
)

# Update using document instance
person.kind = PersonKind.host
await person.save()
```

#### Deleting Documents
```python
# Delete by ID
await Person.get(person_id).delete()

# Delete with conditions
await Product.find(Product.cost == 0).delete()
```

### Working with Relationships

#### Links (One-to-Many, Many-to-One)
```python
# Create linked documents
biomarker = BioMarker(name="Vitamin D", needs_lab=True)
await biomarker.save()

protocol = Protocol(
    name="Vitamin D Optimization",
    biomarkers=[biomarker]  # Link to biomarker
)
await protocol.save()

# Fetch with populated links
protocol_with_biomarkers = await Protocol.find().populate(Protocol.biomarkers).first()
```

#### BackLinks (Reverse Relationships)
```python
# Channel automatically gets episodes via BackLink
channel = await Channel.find().populate(Channel.episodes).first()
print(f"Channel has {len(channel.episodes)} episodes")
```

### Advanced Queries

#### Aggregation Pipeline
```python
# Count episodes per channel
pipeline = [
    {"$group": {"_id": "$channel", "episode_count": {"$sum": 1}}},
    {"$sort": {"episode_count": -1}}
]
results = await Episode.aggregate(pipeline).to_list()
```

#### Text Search
```python
# Find products by text search
products = await Product.find(
    {"$text": {"$search": "vitamin supplement"}}
).to_list()
```

#### Complex Filtering
```python
# Find episodes with specific mentions
episodes_with_products = await Episode.find(
    Episode.mentions.products.exists()
).to_list()

# Find claims with high confidence treatments
high_confidence_claims = await Claim.find().populate([
    Claim.products,
    {"path": "products.treatments", "match": {"confidence": "high"}}
]).to_list()
```

### Bulk Operations
```python
# Bulk insert
people = [
    Person(name="Joe Rogan", kind=PersonKind.host),
    Person(name="Tim Ferriss", kind=PersonKind.host),
    Person(name="Dr. Peter Attia", kind=PersonKind.doctor)
]
await Person.insert_many(people)

# Bulk update
await Person.find(Person.kind == PersonKind.guest).update_many(
    {"$set": {"updated_at": datetime.now(UTC)}}
)
```

## Utility Functions

### Pydantic to Beanie Conversion
```python
def pydantic_to_beanie(
    document_class: type[BaseDoc],
    output: Union[BaseModel, Dict[str, Any]],
    **extra_fields: Any,
) -> BaseDoc:
    """Convert Pydantic model or dict to Beanie document"""
    # Implementation handles field filtering and validation
```

**Usage:**
```python
# Convert from dict
person_data = {"name": "Dr. Example", "kind": "doctor"}
person = pydantic_to_beanie(Person, person_data)

# Convert from Pydantic model
class PersonInput(BaseModel):
    name: str
    kind: str

input_model = PersonInput(name="Dr. Test", kind="doctor")
person = pydantic_to_beanie(Person, input_model, created_at=datetime.now(UTC))
```

### Document Updates
```python
def update_beanie_from_pydantic(
    document: BaseDoc,
    output: Union[BaseModel, Dict[str, Any]],
) -> None:
    """Update existing Beanie document from Pydantic model or dict"""
```

## Best Practices

### 1. Database Initialization
Always initialize Beanie before using any document operations:
```python
async def main():
    client = await init_beanie_with_pymongo()
    try:
        # Your database operations here
        pass
    finally:
        await client.close()
```

### 2. Error Handling
```python
from beanie.exceptions import DocumentNotFound

try:
    person = await Person.get(person_id)
except DocumentNotFound:
    print("Person not found")
```

### 3. Performance Optimization
```python
# Use projection to limit fields
persons = await Person.find().project(PersonProjection).to_list()

# Use pagination for large datasets
page_size = 20
skip = page * page_size
episodes = await Episode.find().skip(skip).limit(page_size).to_list()

# Use indexes for frequently queried fields
# Define in Settings class:
class Settings:
    name = "episodes"
    indexes = ["episode_number", "release_date"]
```

### 4. Transaction Support
```python
from beanie import WriteRules

async with await client.start_session() as session:
    async with session.start_transaction():
        person = Person(name="Test User")
        await person.save(session=session)
        
        episode = Episode(title="Test Episode")
        await episode.save(session=session)
```

## Schema Relationships Overview

The schema creates a rich network of relationships:

- **Episodes** ↔ **Channels** (bidirectional)
- **Episodes** → **Transcripts** (one-to-one)
- **Episodes** → **Persons** (guests, many-to-many)
- **Products** → **Businesses** (many-to-one)
- **Products** → **Persons** (recommended_by, many-to-many)
- **Products** → **BioHacks** (helps_with, many-to-many)
- **Protocols** → **BioMarkers** (many-to-many)
- **Claims** → **Transcripts**, **Persons**, **Products** (many-to-many)
- **Treatments** → **Protocols**, **BioMarkers** (many-to-many)

This interconnected design enables complex queries across the health optimization domain while maintaining data integrity and type safety through Beanie's ODM capabilities.

## Testing

The file includes a basic test function:
```python
async def _test_simple_queries():
    """Basic smoke test: init Beanie, fetch Episodes and Transcripts"""
    client = await init_beanie_with_pymongo()
    # Test operations...
    await client.close()

# Run with: python mongo_schema_overwrite.py
```

This documentation provides a comprehensive guide to understanding and using the MongoDB schema with Beanie ODM for the biohacking application.