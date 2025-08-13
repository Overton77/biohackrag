from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from langchain_core.tools import tool

# Import Pydantic output models and their LLM settings
from src.mongo_schemas import (
    ProductOutput,
    
    TreatmentOutput,
  
    ClaimOutput,
  
    BusinessOutput,
 
    CompoundOutput,
   
)


def _to_dict(model: BaseModel) -> Dict[str, Any]:
    # pydantic v2 / v1 compatibility
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


# -------------------------
# Tools
# -------------------------

@tool(
    "submit_product_information",
    args_schema=ProductOutput,
    return_direct=True,
    parse_docstring=True,
    description="Submit structured product information for a single product",
)
def submit_product_information(
    name: Optional[str] = None,
    cost: Optional[int] = None,
    buy_links: Optional[List[str]] = None,
    description: Optional[str] = None,
    features: Optional[List[str]] = None,
    protocols: Optional[List[str]] = None,
    benefits_as_stated: Optional[List[str]] = None,
    attribution_quotes: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Provide structured product information for a single product.

    Args follow ProductOutput. All fields are optional to allow partial submission.
    """
    payload = ProductOutput(
        name=name,
        cost=cost,
        buy_links=buy_links,
        description=description,
        features=features,
        protocols=protocols,
        benefits_as_stated=benefits_as_stated,
        attribution_quotes=attribution_quotes,
    )
    return _to_dict(payload)


@tool(
    "submit_medical_treatment",
    args_schema=TreatmentOutput,
    return_direct=True,
    parse_docstring=True,
    description="Submit structured medical treatment information for a single treatment",
)
def submit_medical_treatment(
    name: Optional[str] = None,
    description: Optional[str] = None,
    procedure_or_protocol: Optional[List[str]] = None,
    outcomes_as_reported: Optional[List[str]] = None,
    risks_or_contraindications: Optional[List[str]] = None,
    confidence: Optional[str] = None,
    attribution_quotes: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Provide structured medical treatment information.

    Args follow TreatmentOutput. All fields are optional to allow partial submission.
    """
    payload = TreatmentOutput(
        name=name,
        description=description,
        procedure_or_protocol=procedure_or_protocol,
        outcomes_as_reported=outcomes_as_reported,
        risks_or_contraindications=risks_or_contraindications,
        confidence=confidence,  # expects one of ["high", "medium", "low"] or None
        attribution_quotes=attribution_quotes,
    )
    return _to_dict(payload)


@tool(
    "submit_claims_made",
    args_schema=ClaimOutput,
    return_direct=True,
    parse_docstring=True,
    description="Submit a single explicit claim",
)
def submit_claims_made(
    text: Optional[str] = None,
    description: Optional[str] = None,
    claim_type: Optional[str] = None,  # causal | quantitative | experiential | other
    speaker: Optional[str] = None,
    evidence_present_in_transcript: Optional[str] = None,  # yes | no
    attribution_quotes: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Provide a single explicit claim.

    Args follow ClaimOutput.
    """
    payload = ClaimOutput(
        text=text,
        description=description,
        claim_type=claim_type,
        speaker=speaker,
        evidence_present_in_transcript=evidence_present_in_transcript,
        attribution_quotes=attribution_quotes,
    )
    return _to_dict(payload)


@tool(
    "submit_businesses_entities",
    args_schema=BusinessOutput,
    return_direct=True,
    parse_docstring=True,
    description="Submit a single business/entity",
)
def submit_businesses_entities(
    biography: Optional[str] = None,
    market_cap: Optional[float] = None,
    canonical_name: Optional[str] = None,
    aliases: Optional[List[str]] = None,
    role_or_relevance: Optional[str] = None,
    first_timestamp: Optional[str] = None,
    attribution_quotes: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Provide a single business/entity definition.

    Args follow BusinessOutput.
    """
    payload = BusinessOutput(
        biography=biography,
        market_cap=market_cap,
        canonical_name=canonical_name,
        aliases=aliases,
        role_or_relevance=role_or_relevance,
        first_timestamp=first_timestamp,
        attribution_quotes=attribution_quotes,
    )
    return _to_dict(payload)


@tool(
    "submit_compound",
    args_schema=CompoundOutput,
    return_direct=True,
    parse_docstring=True,
    description="Submit a single compound",
)
def submit_compound(
    name: Optional[str] = None,
    description: Optional[str] = None,
    type: Optional[str] = None,  # supplement | food | herb | other
) -> Dict[str, Any]:
    """
    Provide a single compound definition.

    Args follow CompoundOutput.
    """
    payload = CompoundOutput(
        name=name,
        description=description,
        type=type,
    )
    return _to_dict(payload)


TOOLS = [
    submit_product_information,
    submit_medical_treatment,
    submit_claims_made,
    submit_businesses_entities,
    submit_compound,
]
