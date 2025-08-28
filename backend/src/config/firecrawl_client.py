from config.settings import get_settings   
from firecrawl import AsyncFirecrawl, AsyncFirecrawlApp   



settings = get_settings()  


api_key = None
if settings.firecrawl_api_key is not None:
    try:
        # SecretStr -> str
        api_key = settings.firecrawl_api_key.get_secret_value()
    except Exception:
        api_key = str(settings.firecrawl_api_key)

firecrawl = AsyncFirecrawl(api_key=api_key)  
firecrawl_app = AsyncFirecrawlApp(api_key=api_key)  


if __name__ == "__main__":    
    print("Firecrawl api key present:", bool(api_key)) 
    print("importing firecrawl client from firecrawl_client.py")  

