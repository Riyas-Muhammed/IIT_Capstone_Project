import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from fastmcp import Client
import streamlit as st


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

# Forces to prioritize the Current Working Directory (CWD) when looking for modules or packages to import
sys.path.insert(0, str(Path.cwd()))
from modules.llm import get_llm
from prompts.chat_prompt import system_prompt

config_path = Path.cwd() / "config" / "config.json"
with open(config_path, "r") as f:
    config = json.load(f)

def load_memmory():
    try:
        memory_path = config["chat_history"]
        with open(memory_path, "r") as f:
            memmory = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        memmory = []
    return memmory

def load_chat_history():
    memmory = load_memmory()
    if "messages" not in st.session_state:
        st.session_state.messages = list(memmory)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
def update_chat_memmory(conversation: dict):
    memmory = load_memmory()
    memmory.append(conversation)
    with open(config["chat_history"], "w") as f:
        json.dump(memmory, f, indent=4)
    
def clear_chat_hisrory():
    with open(config["chat_history"], "w") as f:
        json.dump([], f, indent=4)
    


async def mcp_tools(mcp_client: Client) -> list:
    """List tools from an already-open MCP client."""
    discovered = await mcp_client.list_tools()
    tools = []
    for tool in discovered:
        schema = getattr(tool, "input_schema", None)
        if schema is None:
            schema = tool.inputSchema
        tools.append({"type": "function", "function": {
            "name": tool.name,
            "description": tool.description or tool.name,
            "parameters": schema,
            "strict": False,
        }})
    return tools


async def get_response(query: str) -> str:
    from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

    provider = config["provider"]
    llm = get_llm(provider)

    async with Client("http://localhost:8000/mcp") as mcp:
        tools = await mcp_tools(mcp)
        llm_with_tools = llm.bind_tools(tools)

        messages = [SystemMessage(system_prompt), HumanMessage(query)]

        while True:
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            if not response.tool_calls:
                break

            for tool_call in response.tool_calls:
                result = await mcp.call_tool(tool_call["name"], tool_call["args"])
                content = result.content if hasattr(result, "content") else str(result)
                if isinstance(content, list):
                    content = " ".join(
                        part.text if hasattr(part, "text") else str(part)
                        for part in content
                    )
                messages.append(ToolMessage(
                    content=str(content),
                    tool_call_id=tool_call["id"],
                ))
                print(f"[Tool called] : {tool_call['name']}")
        print(response.content)
    return response.content

