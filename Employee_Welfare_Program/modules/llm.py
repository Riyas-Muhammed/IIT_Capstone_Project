"""
This module setup the llm based on the llm provider
"""
import os
import json
import ollama
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path 
from langchain_openai import ChatOpenAI,OpenAIEmbeddings
from langchain_ollama import ChatOllama


load_dotenv(Path.cwd()/"config"/".env")

config_path = Path.cwd() / "config" / "config.json"
with open(config_path, "r") as f:
    config = json.load(f)

def get_llm(provider: str):
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL")
    
    if provider == "openai":
        if not api_key:
            raise ValueError("API_KEY not found in .env")
        # print("Loading llm model...")
        client = ChatOpenAI(api_key=api_key, base_url=base_url,model=config[provider]["llm_model"])
        #client = OpenAI(api_key=api_key, base_url=base_url)
        return client
    
    elif provider == "ollama":
        # print("Loading llm model...")
        client = ChatOllama(model=config[provider]["model"])
        return client
        #return config["ollama"]["llm_model"]
    else:
        raise ValueError(f"Unsupported llm provider: {provider}")

    
def get_embedding_model(provider: str):
    provider = provider.lower()

    if provider == "openai":
        api_key = os.getenv("API_KEY")
        base_url = os.getenv("BASE_URL")
        if not api_key:
            raise ValueError("API_KEY not found in .env")
        print("Loading OpenAI embedding model...")
        return OpenAIEmbeddings(model=config["openai"]["embed_model"], api_key=api_key, base_url=base_url)
     
    elif provider == "ollama":
        print("Ollama ebedding code is missing")
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")
