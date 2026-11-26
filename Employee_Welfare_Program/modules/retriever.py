from langchain_classic.retrievers import MultiQueryRetriever
from modules.llm import get_embedding_model
from langchain_openai import ChatOpenAI

def get_retriever(vectorstore, config):

    provider = config["provider"]
    retriever_type = config.get("retriever").get("type")

    if retriever_type == "base":
        print("Using base retriever(simple similarity search)")
        return vectorstore.as_retriever(search_kwargs = {"k": config["retriever"]["top_k"]})
    else:
        raise ValueError(f"Unsupported retriever_type: {retriever_type}")