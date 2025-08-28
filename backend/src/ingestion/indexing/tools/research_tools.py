from config.firecrawl_client import firecrawl_app, firecrawl   
from typing import Dict, List, Optional, Any, Union, Literal    
from firecrawl import AsyncFirecrawl  
from pydantic import BaseModel
import asyncio 
import json


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
    name: Optional[str] 
    cost: Optional[int] 
    buy_links: List[str] 
    description: Optional[str] 
    features: List[str] 
    protocols: List[str] 
    benefits_as_stated: List[str]  


class ProductOutputs(BaseModel): 
    products: List[ProductOutput] 


def _to_plain_dict(obj: Any) -> Dict[str, Any]:
    """Convert Firecrawl result objects (Pydantic v2 models or others) to plain dicts."""
    if obj is None:
        return {}
    # Pydantic v2
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        return obj.model_dump()
    # Pydantic v1 fallback
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    # Fallback to attribute dict
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {"value": obj}


async def run_search_tool(query: str, sources: List[str], limit: int = 10) -> Dict[str, List[Dict[str, Any]]]: 
    """Run Firecrawl search and return a dict mapping source -> list of items.

    Example shape: {"web": [{...}], "news": [{...}], "images": [{...}]}.
    Only sources with results are included.
    """
    res = await firecrawl_app.search(query=query, limit=limit, sources=sources)   

    source_keys = ["web", "news", "images"]
    result: Dict[str, List[Dict[str, Any]]] = {}
    for key in source_keys:
        items = getattr(res, key, None) or []
        if items:
            result[key] = [_to_plain_dict(item) for item in items]

    return result  


async def find_links(firecrawl: AsyncFirecrawl, url: str, limit: int = 20) -> List[str]: 
    """Find a certain number of links from a given url"""  


    res = await firecrawl.map(url=url, limit=limit, sitemap="skip")   


    print(res)  

    link_results: List[str] = [] 

    if hasattr(res, "links"): 
        link_results = [link.url for link in res.links]    

    print(link_results) 

    return link_results   


async def find_products(firecrawl: AsyncFirecrawl, urls: List[str]) -> List[str]:   

    res = await firecrawl.extract(urls=urls, prompt="Extract all of the products from the urls to which you navigate. Return the results as a list of ProductOutputs", schema=ProductOutput.model_json_schema()) 

    print(res) 

    if hasattr(res, "data"): 
        print(res.data)  

    return res 







if __name__ == "__main__": 
    # Example usage   
    # result = asyncio.run(
    #     run_search_tool(query="artificial intelligence", sources=["web", "news"], limit=3)
    # )
    # print(json.dumps(result, indent=2, default=str))   
    # asyncio.run(find_links(firecrawl, "https://aurowellness.com/"))   

    product_urls = [ 'https://aurowellness.com',  'https://aurowellness.com/blog', 'https://aurowellness.com/blog/tocotrienols', 'https://aurowellness.com/blog/prevent-forehead-wrinkles', 'https://aurowellness.com/blog/glutathione-lotion', 'https://aurowellness.com/blog/glutathione-supplements', 'https://aurowellness.com/blog/glutathione-for-skin-2', 'https://aurowellness.com/blog/glutathione-vitamin-c', 'https://aurowellness.com/blog/glutathione-shots', 'https://aurowellness.com/blog/oxidized-glutathione', 'https://aurowellness.com/blog/best-clean-skincare-for-rosacea', 'https://aurowellness.com/blog/nano-glutathione', 'https://aurowellness.com/blog/glutathione-for-skin', 'https://aurowellness.com/blog/glutathione-cosmetics', 'https://aurowellness.com/blog/glutathione-cream'] 


    asyncio.run(find_products(firecrawl, product_urls)) 
    print("Importing research tools")




