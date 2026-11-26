import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

def dashboard_visuals():
    config_path = Path.cwd() / "config" / "config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    # Points utilisation pie chart
    points_allocated = config.get('points_allocated', 0)
    points_utilised = config.get('points_utilised', 0)
    points_available = config.get('points_available', 0)

    pie_fig = go.Figure(data=[go.Pie(
        labels=['Points Utilised', 'Points Available'],
        values=[points_utilised, points_available],
        hole=0.4,
        marker=dict(
            colors=['#2a78d6', '#1baf7a'],
            line=dict(color='#fcfcfb', width=2)
        ),
        textinfo='value+percent',
        hovertemplate='<b>%{label}</b><br>Points: %{value:,}<br>Share: %{percent}<extra></extra>',
        sort=False,
    )])

    pie_fig.update_layout(
        title=dict(text=f"Total Points: {points_allocated}", font=dict(size=14)),
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color='#0b0b0b'),
        legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5),
        margin=dict(t=60, b=60, l=20, r=20),
        paper_bgcolor='#fcfcfb',
        plot_bgcolor='#fcfcfb',
        height=360,
    )

    # Points utilisation on monthly in Bar chart
    order_path = Path(config["order_history"])
    months = ["January","February","March","April","May","June",
              "July","August","September","October","November","December"]
    monthly_totals = {m: 0 for m in months}

    if order_path.exists():
        oh = pd.read_excel(order_path)
        oh["Date"] = pd.to_datetime(oh["Date"], errors="coerce")
        oh["Month"] = oh["Date"].dt.strftime("%B")
        grouped = oh.groupby("Month")["Price"].sum()
        for month, total in grouped.items():
            if month in monthly_totals:
                monthly_totals[month] = total

    bar_fig = go.Figure(data=[go.Bar(
        x=months,
        y=[monthly_totals[m] for m in months],
        marker_color='#2a78d6',
        hovertemplate='<b>%{x}</b><br>Points: %{y:,}<extra></extra>',
    )])
    bar_fig.update_layout(
        title=dict(text="Monthly Points Utilisation", font=dict(size=14)),
        xaxis=dict(title="Month"),
        yaxis=dict(title="Points Spent"),
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color='#0b0b0b'),
        margin=dict(t=60, b=60, l=20, r=20),
        paper_bgcolor='#fcfcfb',
        plot_bgcolor='#fcfcfb',
        height=360,
    )

    pc1, pc2 = st.columns([1, 2])
    with pc1:
        st.subheader("Points Utilisation")
        st.plotly_chart(pie_fig, use_container_width=True)
    with pc2:
        st.subheader("Monthly Spend")
        st.plotly_chart(bar_fig, use_container_width=True)
    st.divider()
