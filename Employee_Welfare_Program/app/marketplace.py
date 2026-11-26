import json
import openpyxl
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta

def marketplace_items():
    config_path = Path.cwd() / "config" / "config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    user_name = config.get('employee')
    points = config.get('points_available')
    data_path = Path(config["products_DB"])
    cart_path = Path(config["cart_path"])

    def get_cart():
        if cart_path.exists() and cart_path.stat().st_size > 0:
            with open(cart_path, "r") as f:
                return json.load(f)
        return []
    
    def add_to_cart(product: dict):
        cart = get_cart()
        cart.append(product)
        with open(cart_path, "w") as f:
            json.dump(cart, f, indent=2)

    def update_point(spend: int):
        """spend= used points"""
        # 1. Change the value (including nested keys or list items)
        allocated = int(config["points_allocated"])
        utilised = spend + int(config["points_utilised"])
        balance = allocated - utilised
        config["points_utilised"] = utilised
        config["points_available"] = balance
        
        # 2. Write the updated dictionary back to the file
        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)

    def update_order_history(product, order_type):
        wb_path = config["order_history"]
        wb = openpyxl.load_workbook(wb_path)
        ws = wb.active

        new_row = [datetime.now().isoformat(), 
                product["Product Name"],product["Description"], 
                product["Product Type"], product["Category"], 
                product["Sub Category"], product["Price in INR"], 
                product["Expiry"], 
                (datetime.now() + timedelta(days=product["Delivery in Days"])).isoformat(),
                    order_type]
        ws.append(new_row)
        wb.save(wb_path)

    @st.dialog("Order Confirmation")
    def show_product_dialog(product):
        img_path = Path(str(product["Image path"]).strip())
        if img_path.exists():
            st.image(str(img_path), width=250)

        st.markdown(f"### {product['Product Name']}")
        st.markdown(f"**Category:** {product['Category']}")
        st.markdown(f"**Sub Category:** {product['Sub Category']}")
        st.markdown(f"**Type:** {product['Product Type']}")
        st.markdown(f"**Price:** ₹ {int(product['Price in INR']):,}")
        st.markdown(f"**Details:** {product['Description']}")
        st.divider()

        st.markdown(f"**Points available:** {points}")
        if int(points) > int(product['Price in INR']):
            st.warning("Please confirm your purchase below.")
            if st.button("Confirm Purchase", type="primary", use_container_width=True):
                update_point(int(product['Price in INR']))
                update_order_history(product, "Marketplace")
                st.success("Order placed successfully!")
                st.session_state.buy_product = None
                st.rerun()
        else:
            st.warning("You dont have enough points to purchase this product.")
            return

    @st.dialog("Cart Confirmation")
    def show_cart_dialog(product):
        img_path = Path(str(product["Image path"]).strip())
        if img_path.exists():
            st.image(str(img_path), width=250)

        st.markdown(f"### {product['Product Name']}")
        st.markdown(f"**Category:** {product['Category']}")
        st.markdown(f"**Sub Category:** {product['Sub Category']}")
        st.markdown(f"**Type:** {product['Product Type']}")
        st.markdown(f"**Price:** ₹ {int(product['Price in INR']):,}")
        st.markdown(f"**Details:** {product['Description']}")
        st.divider()

        st.markdown(f"**Points available:** {points}")
        st.warning("Please proceed to add the item to cart.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Proceed", type="primary", use_container_width=True):
                add_to_cart(product)
                st.session_state.cart_product = None
                st.toast("Item added to your Cart!", icon="✅")
                st.rerun()
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.cart_product = None
                st.rerun()

    try:
        df = pd.read_excel(data_path)
        df.columns = df.columns.str.strip()

        if "buy_product" not in st.session_state:
            st.session_state.buy_product = None

        if "cart_product" not in st.session_state:
                    st.session_state.cart_product = None

        COLS_PER_ROW = 3
        rows = [df.iloc[i:i+COLS_PER_ROW] for i in range(0, len(df), COLS_PER_ROW)]

        for row in rows:
            cols = st.columns(COLS_PER_ROW)
            for col, (_, product) in zip(cols, row.iterrows()):
                with col:
                    img_path = Path(str(product["Image path"]).strip())
                    if img_path.exists():
                        st.image(str(img_path), use_container_width=False)
                    else:
                        st.image("https://via.placeholder.com/300x200?text=No+Image", use_container_width=False)

                    st.markdown(f"**{product['Product Name']}**")
                    st.markdown(f"{product['Category']}  -  {product['Product Type']}")
                    st.markdown(f"Price: ₹ {int(product['Price in INR']):,}")
                    btn1, btn2 = st.columns(2)
                    with btn1:
                        if st.button("Add to Cart", key=f"cart_{product['Product Name']}"):
                            st.session_state.cart_product = product.to_dict()
                    with btn2:
                        if st.button("Buy Now", key=f"buy_{product['Product Name']}", type="primary"):
                            st.session_state.buy_product = product.to_dict()
                    st.markdown("---")

        if st.session_state.buy_product:
            show_product_dialog(st.session_state.buy_product)
            
        if st.session_state.cart_product:
            show_cart_dialog(st.session_state.cart_product)
            
        
    except FileNotFoundError:
        st.error("Products database not found. Please ensure `data/Products_DB.xlsx` exists.")
