"""UI components and visual templates configuration."""

import streamlit as st

# Premium styling
PRIMARY_COLOR = "#00c6ff"
SECONDARY_COLOR = "#0072ff"
BACKGROUND_COLOR = "#0b101e"
CARD_COLOR = "#151b2c"
TEXT_COLOR = "#f0f2f6"

def inject_styles():
    st.markdown(f"""
    <style>
        /* Base typography & backgrounds */
        h1, h2, h3, h4, h5, h6 {{
            font-family: 'Inter', sans-serif;
            color: {TEXT_COLOR};
        }}
        .stApp {{
            background-color: {BACKGROUND_COLOR};
            color: {TEXT_COLOR};
        }}
        
        /* Metric Cards */
        [data-testid="stMetricValue"] {{
            color: {PRIMARY_COLOR};
            font-weight: 700;
        }}
        [data-testid="metric-container"] {{
            background-color: {CARD_COLOR};
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        [data-testid="metric-container"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0,198,255,0.15);
        }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 15px;
            background-color: transparent;
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            background-color: {CARD_COLOR};
            border-radius: 8px 8px 0 0;
            padding: 10px 24px;
            border: 1px solid rgba(255,255,255,0.05);
            border-bottom: none;
            color: #8c92a4;
            transition: all 0.3s ease;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {PRIMARY_COLOR};
            background-image: linear-gradient(135deg, {PRIMARY_COLOR} 0%, {SECONDARY_COLOR} 100%);
            color: white;
            font-weight: 600;
        }}
        
        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: {CARD_COLOR} !important;
            border-right: 1px solid rgba(255,255,255,0.05);
        }}
        
        /* Tables */
        .stDataFrame {{
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.05);
        }}
    </style>
    """, unsafe_allow_html=True)

PLOTLY_THEME = dict(
    layout=dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_COLOR, family="Inter, sans-serif"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.1)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.1)"),
        colorway=[PRIMARY_COLOR, '#c84b31', '#2d4263', '#ecdbba']
    )
)
