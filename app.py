import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from backend import DataManager
from datetime import timedelta
import time

# --- Configuration & Styles ---
st.set_page_config(
    page_title="Geoguessr Duels Analytics",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .main { background: #0e1117; }
    h1, h2, h3 { font-family: 'Inter', sans-serif; color: #f0f2f6; }
    .stMetric {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #262730;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- Helpers ---
def apply_timezone(df, hours=5, minutes=30):
    if df.empty: return df
    df['Date'] = pd.to_datetime(df['Date'])
    df['Local Date'] = df['Date'] + timedelta(hours=hours, minutes=minutes)
    return df

# --- UI Components ---
def render_header(nick):
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"Duels Analyzer")
        if nick:
            st.markdown(f"### Welcome back, *{nick}*")
    with col2:
        st.image("https://www.geoguessr.com/_next/static/images/logo-19d26db60a87754dfdb4b786c526485d.svg", width=150)

def render_metrics(df):
    if df.empty: return
    
    # Calculate stats
    games_df = df.groupby('Game Id').agg({
        'Win Percentage': 'first',
        'Your Rating': 'first',
        'Your Score': 'sum',
    }).reset_index()

    total_games = len(games_df)
    win_rate = df['Win Percentage'].mean()
    current_rating = games_df.sort_values('Game Id').iloc[-1]['Your Rating'] if not games_df.empty else 0
    avg_score = df['Your Score'].mean()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Games", f"{total_games}")
    col2.metric("Current Rating", f"{current_rating}")
    col3.metric("Round Win Rate", f"{win_rate:.1f}%")
    col4.metric("Avg Score/Round", f"{int(avg_score)}")

def render_charts(df):
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🗺️ Geography", "📈 Deep Dive", "📄 Raw Data"])
    
    with tab1:
        st.markdown("#### Performance Over Time")
        df_sorted = df.sort_values('Date')
        df_sorted['Rolling Score'] = df_sorted['Your Score'].rolling(window=50).mean()
        
        fig = px.line(df_sorted, x='Date', y='Rolling Score', title="Average Score (50-Round Moving Avg)")
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### Rating History")
        games_sorted = df.sort_values('Date').groupby('Game Id').first().reset_index()
        fig2 = px.line(games_sorted, x='Date', y='Your Rating', title="Rating Progression")
        fig2.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("#### Country Mastery")
            country_stats = df.groupby('Country').agg({
                'Your Score': 'mean',
                'Game Id': 'count'
            }).rename(columns={'Game Id': 'Rounds'}).reset_index()
            
            country_stats = country_stats[country_stats['Rounds'] > 2]
            
            fig_map = px.choropleth(
                country_stats,
                locations="Country",
                locationmode="country names",
                color="Your Score",
                hover_name="Country",
                color_continuous_scale="Viridis",
                title="Average Score by Country"
            )
            fig_map.update_layout(template="plotly_dark", geo=dict(bgcolor='#0e1117'), height=600)
            st.plotly_chart(fig_map, use_container_width=True)
            
        with col2:
            st.markdown("#### Top Countries")
            top_countries = country_stats.sort_values('Your Score', ascending=False).head(10)
            st.dataframe(top_countries[['Country', 'Your Score', 'Rounds']].style.format({"Your Score": "{:.0f}"}), 
                         hide_index=True, use_container_width=True)
            
            st.markdown("#### Weakest Countries")
            low_countries = country_stats.sort_values('Your Score', ascending=True).head(10)
            st.dataframe(low_countries[['Country', 'Your Score', 'Rounds']].style.format({"Your Score": "{:.0f}"}), 
                         hide_index=True, use_container_width=True)

    with tab3:
        st.markdown("#### Score Distribution")
        fig_hist = px.histogram(df, x="Your Score", nbins=50, title="Distribution of Round Scores")
        fig_hist.update_layout(template="plotly_dark", bargap=0.1)
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.markdown("#### Distance vs Score")
        sample_df = df.sample(n=min(len(df), 2000)) if len(df) > 2000 else df
        fig_scatter = px.scatter(
            sample_df, 
            x="Your Distance", 
            y="Your Score", 
            color="Game Mode", 
            hover_data=['Country', 'Map Name'],
            title="Distance vs Score Correlation"
        )
        fig_scatter.update_layout(template="plotly_dark")
        st.plotly_chart(fig_scatter, use_container_width=True)

    with tab4:
        st.dataframe(df.sort_values('Date', ascending=False))

# --- Main Logic ---

def main():
    # Session State Init
    if 'ncfa_token' not in st.session_state:
        st.session_state['ncfa_token'] = ''
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None
    if 'user_nick' not in st.session_state:
        st.session_state['user_nick'] = None
    if 'new_tokens' not in st.session_state:
        st.session_state['new_tokens'] = []

    # --- Sidebar ---
    with st.sidebar:
        st.subheader("Settings")
        
        if not st.session_state['user_id']:
            token_input = st.text_input("Geoguessr _ncfa Cookie", type="password", help="Found in website cookies.")
            if st.button("Connect"):
                if token_input:
                    with st.spinner("Verifying Token..."):
                        user_info = DataManager.get_user_info(token_input)
                        if user_info:
                            st.session_state['ncfa_token'] = token_input
                            st.session_state['user_id'] = user_info['id']
                            st.session_state['user_nick'] = user_info['nick']
                            st.rerun()
                        else:
                            st.error("Invalid Token or Connection Failed")
        else:
            st.success(f"Connected as: {st.session_state['user_nick']}")
            
            # Sync Logic
            st.divider()
            st.subheader("Data Sync")

            if st.button("Check for New Games"):
                with st.spinner("Checking server..."):
                    new_tokens, total_remote, total_local = DataManager.check_for_new_games(
                        st.session_state['ncfa_token'],
                        st.session_state['user_id']
                    )
                    st.session_state['new_tokens'] = new_tokens
                    st.toast(f"Found {len(new_tokens)} new games!", icon="🎉")

            new_count = len(st.session_state['new_tokens'])
            if new_count > 0:
                st.info(f"{new_count} new games available.")

                import_count = st.slider("Import Limit", 1, new_count, new_count)

                if st.button(f"Import {import_count} Games", type="primary"):
                    tokens_to_fetch = st.session_state['new_tokens'][:import_count]

                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    try:
                        DataManager.fetch_and_save_games(
                            st.session_state['ncfa_token'],
                            st.session_state['user_id'],
                            tokens_to_fetch,
                            progress_callback=progress_bar.progress
                        )
                        st.success(f"Successfully imported {import_count} games!")
                        st.session_state['new_tokens'] = [] # Clear queue
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Import failed: {str(e)}")
            elif st.session_state.get('user_id'):
                st.caption("No new games detected.")

            if st.button("Logout"):
                st.session_state.clear()
                st.rerun()

    # --- Main Content ---
    
    # Load Data (User Specific)
    df = pd.DataFrame()
    if st.session_state['user_id']:
        df = DataManager.load_cache(st.session_state['user_id'])
        
    render_header(st.session_state['user_nick'])

    if st.session_state['user_id']:
        if not df.empty:
            df = apply_timezone(df)

            # Filters
            with st.expander("Filters", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    modes = st.multiselect("Game Mode", df['Game Mode'].unique(), default=df['Game Mode'].unique())
                with col2:
                    maps = st.multiselect("Map", df['Map Name'].unique())
            
            # Apply Filters
            filtered_df = df[df['Game Mode'].isin(modes)]
            if maps:
                filtered_df = filtered_df[filtered_df['Map Name'].isin(maps)]

            render_metrics(filtered_df)
            render_charts(filtered_df)
        else:
            st.info("No games found in cache. Use the sidebar to 'Check for New Games' and import your data.")
    else:
        st.write("👋 Welcome! Please enter your `_ncfa` token in the sidebar to get started.")

if __name__ == "__main__":
    main()
