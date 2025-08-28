from llama_index.llms.google_genai import GoogleGenAI  
from langchain_google_genai import ChatGoogleGenerativeAI   
from config.settings import get_settings  


settings = get_settings()
google_api_key = settings.google_free_api_key.get_secret_value() if settings.google_free_api_key else None


llama_index_llm = GoogleGenAI(model="gemini-2.0-flash", api_key=google_api_key) 
langchain_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", api_key=google_api_key) 


if __name__ == "__main__": 
    print("importing llms from llm_setup.py") 