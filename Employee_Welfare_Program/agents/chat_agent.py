"""
Chat module for interacting with LLM providers.
"""
import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime


import ssl
import urllib3
# Corporate proxy fix: must run before any import that triggers a network call (e.g. tiktoken).
# Tries truststore first (uses Windows cert store properly); falls back to disabling verification.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    ssl._create_default_https_context = ssl._create_unverified_context
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Forces to prioritize the Current Working Directory (CWD) when looking for modules or packages to import
sys.path.insert(0, str(Path.cwd()))

from langchain_core.prompts import PromptTemplate
from prompts.prompts import cat_prompt, chat_system_prompt
from modules.loader import load_document
from modules.splitter import split_documents
from modules.embedder import build_or_update_vectorstore
from modules.retriever import get_retriever
from modules.llm import get_llm

config_path = Path.cwd() / "config" / "config.json"
with open(config_path, "r") as f:
    config = json.load(f)

try:
    memory_path = Path.cwd() / "data" / "chat_history.json"
    with open(memory_path, "r") as f:
        memmory = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    memmory = []

def load_chat_history():
    import streamlit as st
    if "messages" not in st.session_state:
        st.session_state.messages = memmory
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    # st.chat_input("Type your question here...")
    # if prompt := st.chat_input("Type your question here..."):
    #     st.session_state.messages.append(
    #         {"role": "user", "content": prompt}
    #     )
    #     with st.chat_message("user"):
    #         st.write(prompt)

def get_category(messages: list[dict], provider: str) -> str:
    """Get the category of user query"""
    client = get_llm(provider)
    chat_history = messages

    prompt_template = PromptTemplate(
        input_variables=["chat_history"],
        template=cat_prompt
    )
    prompt = prompt_template.format(chat_history=chat_history)
    response = client.invoke(prompt)
    print(f"User query category is {response.content}")
    return response.content

def get_response(
        query: str, 
        messages: list[dict] = None, 
        context: str = None, 
        order_history: pd.DataFrame = None,
        products: pd.DataFrame = None, 
        provider: str = None) -> str:
    """Send a list of messages to the LLM and return the assistant reply."""

    provider = provider or config["provider"]
    client = get_llm(provider)
    
    prompt_template = PromptTemplate(
        input_variables=["question","chat_history","context", "order_history", "products"],
        template=chat_system_prompt
    )
    prompt = prompt_template.format(question=query, chat_history=messages, context=context, order_history=order_history, products=products)
    response = client.invoke(prompt)
    return response.content

def run_chat():
    """Run an interactive chat session."""
    provider = config["provider"]
    model = config[provider]["llm_model"]
    conversation: dict = {}

    # if system_prompt:
    #     conversation.append({"role": "system", "content": system_prompt})
    #print(f"Chat started (provider: {provider}, model: {model})")
    #print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        conversation = {"role": "user", "content": user_input, "datetime": datetime.now().isoformat()}
        memmory.append(conversation)
        category = get_category(memmory, provider)

        if category == "Policy":
            docs = load_document(config["policy_path"])
            chunks = split_documents(docs)
            vectorstore = build_or_update_vectorstore(chunks, config)
            retriever = get_retriever(vectorstore, config)
            retrieved_docs = retriever.invoke(user_input)
            context = "\n\n".join([doc.page_content for doc in retrieved_docs])
            order_history = None
            products = None
        elif category == "Order History":
            order_history = pd.read_excel(config["order_history"])
            context = None
            products = None
        elif category == "Products":
            products = pd.read_excel(config["products_DB"])
            context = None
            order_history = None
        else:
            context = None
            order_history = None
            products = None
        
        try:
            reply = get_response(user_input, memmory, context, order_history, products, provider)
            conversation = {"role": "assistant", "content": reply, "datetime": datetime.now().isoformat()}
            print(f"\nAssistant: {reply}\n")
            memmory.append(conversation)
            with open(memory_path, "w") as f:
                json.dump(memmory, f, indent=4)

        except Exception as e:
            print(f"Error: {e}")
            # conversation.pop()


if __name__ == "__main__":
    run_chat()
