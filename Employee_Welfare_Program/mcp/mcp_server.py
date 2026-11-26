import json
import sys
import pandas as pd
from pathlib import Path

# Corporate proxy fix: must run before any import that triggers a network call (e.g. tiktoken).
# Tries truststore first (uses Windows cert store properly); falls back to disabling verification.
import ssl
import urllib3
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    ssl._create_default_https_context = ssl._create_unverified_context
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, str(Path.cwd()))

from modules.loader import load_document
from modules.splitter import split_documents
from modules.embedder import build_or_update_vectorstore
from modules.retriever import get_retriever


from fastmcp import FastMCP
mcp = FastMCP(name="EWP_MCP_Server")

config_path = Path.cwd() / "config" / "config.json"
with open(config_path, "r") as f:
    config = json.load(f)

@mcp.tool
def policy_context(user_prompt: str, config=config) -> str:
    """
    Retrieve the user prompt related contents from policy document
    """
    doc_path = config["policy_path"]
    docs = load_document(doc_path)
    chunks = split_documents(docs)
    vectorstore = build_or_update_vectorstore(chunks, config)
    retriever = get_retriever(vectorstore, config)
    retrieved_docs = retriever.invoke(user_prompt)
    context = "\n\n".join([doc.page_content for doc in retrieved_docs])
    return context
    
@mcp.tool
def chat_history() -> list[dict] | None:
    """
    Retrive the previous chat or conversations
    """
    try:
        memory_path = config["order_history"]
        with open(memory_path, "r") as f:
            memmory = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        memmory = []
    return memmory

@mcp.tool
def order_history() -> pd.DataFrame:
    """
    Retrive the order history of Items/Prodects and its details. 
    """
    order_history = pd.read_excel(config["order_history"])
    return order_history

@mcp.tool
def products_info() -> pd.DataFrame:
    """
    Retrive all the products and its details which are available to the employees as per the Employee Welfare Programe
    """
    product_info = pd.read_excel(config["products_DB"])
    return product_info

@mcp.tool
def cart_info() -> list[dict] | None:
    """
    Retrive the list of items/products are added in the cart
    """
    try:
        cart_path = config["cart_path"]
        with open(cart_path, "r") as f:
            cart = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cart = []
    return cart

@mcp.tool
def points_info() -> dict:
    """
    Retrive the points details such as total points, utilised points and balance points
    """
    points = {
        "Total points allocated for each employees during the year": config["points_allocated"],
        "Points utilised by this employee during the year": config["points_utilised"],
        "Balance points available for this employee for this year": config["points_available"]
    }
    return points


if __name__=="__main__":
    mcp.run(transport="http", port=8000)