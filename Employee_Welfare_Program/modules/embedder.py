"""
modules/embedder.py
-------------------
Purpose:
    Handles text embeddings and local vector store management.
"""
import os
from typing import List, Optional
# from langchain_community.vectorstores import FAISS, Chroma, Pinecone as LC_Pinecone

from langchain_community.vectorstores import FAISS, Chroma

from langchain_core.documents import Document
from modules.llm import get_embedding_model


def build_or_update_vectorstore(docs: List[Document], config: dict, persist_dir: Optional[str] = None):
    """
    Create or update a vectorstore based on the provider in config.

    Args:
        docs: List of LangChain Document chunks
        config: Dictionary loaded from config.json
        persist_dir: Optional local directory to store FAISS/Chroma data

    Returns:
        A LangChain VectorStore object (FAISS, Chroma, or Pinecone)
    """
    provider = config.get("provider").lower()
    store_config = config.get("vector_store", {})
    store_type = store_config.get("type").lower()

    print(f"🔹 Embedding Provider: {provider}")
    print(f"🔹 Vector Store Type: {store_type}")

    # --- Load Embedding Model ---
    embedding_model = get_embedding_model(provider)
    print("✅ Embedding model loaded successfully.")

    # =============================================================
    # 🧠 LOCAL VECTOR STORES (FAISS / Chroma)
    # =============================================================
    
    if store_type == "faiss":
        if not persist_dir:
            persist_dir = os.path.join(os.getcwd(), "vectorstores", f"{provider}_{store_type}_index")
        os.makedirs(persist_dir, exist_ok=True)

        index_path = os.path.join(persist_dir, "index.faiss")
        metadata_path = os.path.join(persist_dir, "index.pkl")

        if os.path.exists(index_path):
            print("♻️ Updating existing FAISS index...")
            vectorstore = FAISS.load_local(
                persist_dir,
                embeddings=embedding_model,
                allow_dangerous_deserialization=True
            )
            if docs:
                vectorstore.add_documents(docs)
            else:
                print("⚪ No new documents provided — loaded existing index only.")
        else:
            if not docs:
                raise ValueError("❌ No documents provided and FAISS index not found.")
            print("🆕 Creating new FAISS index...")
            vectorstore = FAISS.from_documents(docs, embedding_model)

        vectorstore.save_local(persist_dir)
        print(f"✅ FAISS vectorstore saved at: {persist_dir}")
        return vectorstore

    else:
        print("Store_type not supported ❌")