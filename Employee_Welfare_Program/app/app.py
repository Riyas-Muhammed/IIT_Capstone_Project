import sys
import json
import asyncio
import nest_asyncio
nest_asyncio.apply()
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta
from dashboard import dashboard_visuals
from marketplace import marketplace_items


sys.path.insert(0, str(Path.cwd()))
from agents.chat import load_chat_history, get_response, update_chat_memmory, clear_chat_hisrory


config_path = Path.cwd() / "config" / "config.json"
with open(config_path, "r") as f:
    config = json.load(f)

cart_path = Path(config["cart_path"])
user_name = config.get('employee')
points = config.get('points_available')


def dashboard():
    st.header("📊 Dashboard")
    st.success(f"Hello, {user_name}! Let's visualize some data.")
    # Visualization Section
    dashboard_visuals()
 
def marketplace():
    # market place window
    st.header("🛒 Marketplace")
    st.success(f"Hello, {user_name}! Below are the products available for you.")
    marketplace_items()

def reimburse():
    # Reimbursement window
    st.header("💲 Reimbursement")
    st.success(f"Hello, {user_name}! Claim your expense by submitting the invoice.")

def chat_bot():
    left, right = st.columns([8,2])
    with left:    
        # Chat assistant window
        st.header("💬 Chat Assistant")
    with right:
        if st.button("🧹 Clear Chat", width="stretch"):
            clear_chat_hisrory()
            st.session_state.messages = []
            st.rerun()
    st.success(f"Hello, {user_name}! Chat with AI assistant for your queries.")
    
    # Scrollable container for chat messages
    chat_container = st.container(height=500, border=True)

    # Store messages across app reruns
    with chat_container:
        load_chat_history()
    # Accept a new message
    if prompt := st.chat_input("Type your question here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.write(prompt)
        update_chat_memmory({"role": "user", "content": prompt, "datetime": datetime.now().isoformat()})
        reply = asyncio.run(get_response(prompt))
        st.session_state.messages.append({"role": "assistant", "content": reply})
        with chat_container:
            with st.chat_message("assistant"):
                st.write(reply)
        update_chat_memmory({"role": "assistant", "content": reply, "datetime": datetime.now().isoformat()})
        

# 1. Page Configuration & Header
st.set_page_config(page_title="Employee Welfare Program", layout="wide")
left, right = st.columns([8,2])
with left:
    st.title("👩‍💻Employee Welfare Program")
    st.write("Better workdays start with better support.")
with right:
    if st.button("🧑‍💼Acount", use_container_width=True):
        st.session_state["page"] = "Account"
    
    if cart_path.exists() and cart_path.stat().st_size > 0:
        with open(cart_path, "r") as f:
            cart = json.load(f)
        cart_count = len(cart)
    else:
        cart_count = 0
    
    if st.button(f"🛒 Cart ({cart_count})", use_container_width=True):
        st.session_state["page"] = "Cart"
st.divider()
# 2. Sidebar Layout for Inputs
st.sidebar.header(f"Welcome {user_name}!")
st.sidebar.success(f"**Points: {points}**")


if "page" not in st.session_state:
    st.session_state.page = "Home"

if st.sidebar.button("🏠 Home", type="primary" if st.session_state.page == "Home" else "secondary"):
    st.session_state.page = "Home"
    st.rerun()
if st.sidebar.button("🎁 Marketplace", type="primary" if st.session_state.page == "Marketplace" else "secondary"):
    st.session_state.page = "Marketplace"
    st.rerun()
if st.sidebar.button("🔁 Reimburse", type="primary" if st.session_state.page == "Reimburse" else "secondary"):
    st.session_state.page = "Reimburse"
    st.rerun()
if st.sidebar.button("💬 Chat Bot", type="primary" if st.session_state.page == "ChatBot" else "secondary"):
    st.session_state.page = "ChatBot"
    st.rerun()
if st.sidebar.button("🗃️ Order History", type="primary" if st.session_state.page == "Orders" else "secondary"):
    st.session_state.page = "Orders"
    st.rerun()


if st.session_state.page == "Home":
    dashboard()
elif st.session_state.page == "Marketplace":
    marketplace()
elif st.session_state.page == "Reimburse":
    reimburse()
elif st.session_state.page == "ChatBot":
    chat_bot()
elif st.session_state.page == "Account":
    dashboard()
elif st.session_state.page == "Cart":
    dashboard()