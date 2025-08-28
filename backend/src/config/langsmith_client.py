from langsmith import Client 
from config.settings import get_settings  

settings = get_settings()   

api_key = None
if settings.langsmith_api_key is not None:
    try:
        api_key = settings.langsmith_api_key.get_secret_value()
    except Exception:
        api_key = str(settings.langsmith_api_key)

langsmith_client = Client(api_key=api_key) 



if __name__ == "__main__": 
    print("importing langsmith client from langsmith_client.py") 

