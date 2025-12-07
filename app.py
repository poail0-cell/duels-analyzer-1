import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from backend import DataManager
from datetime import timedelta

# --- Configuration & Styles ---
st.set_page_config(
    page_title="Geoguessr Duels Analytics",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Premium" feel
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .main {
        background: #0e1117;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        color: #f0f2f6;
    }
    .stMetric {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
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
    # Ensure Date is datetime
    df['Date'] = pd.to_datetime(df['Date'])
    # Add offset (assuming original data is UTC or equivalent base)
    # The API returns UTC usually.
    df['Local Date'] = df['Date'] + timedelta(hours=hours, minutes=minutes)
    return df

# --- UI Components ---
def render_header(player_data):
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"Duels Analyzer")
        if player_data:
            st.markdown(f"### Welcome back, *{player_data.get('nick')}*")
    with col2:
        st.image("https://www.geoguessr.com/_next/static/images/logo-19d26db60a87754dfdb4b786c526485d.svg", width=150)

def render_metrics(df):
    if df.empty: return
    
    # Calculate stats
    last_game = df.iloc[-1]
    
    # Win Rate
    # Since df is round-level, we need to aggregate by Game Id first for game-level stats
    games_df = df.groupby('Game Id').agg({
        'Win Percentage': 'first', # It's 100 or 0 per round? No, wait. 
                                  # The backend calculates Win Percentage per round based on score? 
                                  # Wait, the backend row['Win Percentage'] is 100 if Your Score > Opp Score.
                                  # That's round win percentage. To get Game Win Percentage, we need game result.
                                  # The backend doesn't explicitly store "Game Won". 
                                  # Usually defined by HP provided in other endpoints, or total score?
                                  # Duels is HP based. We don't have HP in rounds.
                                  # However, the original code used `df['Win Percentage'].mean()` which is ROUND win percentage.
                                  # I will stick to Round Win Percentage for now as that's what was available, 
                                  # but I'll label it "Round Win Rate".
        'Your Rating': 'first', # Rating is usually same for all rounds in a game or at least stored repeatedly
        'Score Difference': 'sum',
        'Your Score': 'sum',
        'Your Distance': 'mean' # Avg distance per round
    }).reset_index()

    total_games = len(games_df)
    win_rate = df['Win Percentage'].mean() # Round win rate
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
        # Moving Average of Score
        df_sorted = df.sort_values('Date')
        df_sorted['Rolling Score'] = df_sorted['Your Score'].rolling(window=50).mean()
        
        fig = px.line(df_sorted, x='Date', y='Rolling Score', title="Average Score (50-Round Moving Avg)")
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### Rating History")
        # Group by Game to get rating history
        games_sorted = df.sort_values('Date').groupby('Game Id').first().reset_index()
        fig2 = px.line(games_sorted, x='Date', y='Your Rating', title="Rating Progression")
        fig2.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("#### Country Mastery")
            # Map
            country_stats = df.groupby('Country').agg({
                'Your Score': 'mean',
                'Game Id': 'count'
            }).rename(columns={'Game Id': 'Rounds'}).reset_index()
            
            # Filter for meaningful data
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
        # Scatter plot sample to avoid lag if many points
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


# --- Main Application Logic ---

def main():
    # Sidebar: Onboarding & Sync
    with st.sidebar:
        st.subheader("Settings")
        token_input = st.text_input("Geoguessr _ncfa Cookie", type="password", help="Found in website cookies. Required for fetching data.")
        
        if 'ncfa_token' not in st.session_state and token_input:
            st.session_state['ncfa_token'] = token_input
            
        sync_btn = st.button("Sync Data", type="primary")
        
        st.divider()
        st.info("Data is cached locally in `games_cache.json`. Syncing only fetches new games.")

    # Main Content
    
    # 1. Load Data (Always load cache if available)
    df = DataManager.load_cache()
    
    # 2. Sync if requested or logic implies
    player_data = {}
    if sync_btn and st.session_state.get('ncfa_token'):
        with st.status("Syncing with Geoguessr...", expanded=True) as status:
            try:
                st.write("Checking for new games...")
                updated_df, new_count, p_data = DataManager.sync_data(
                    st.session_state['ncfa_token'], 
                    progress_callback=lambda p: st.progress(p)
                )
                df = updated_df
                player_data = p_data
                status.update(label=f"Sync Complete! Added {new_count} new games.", state="complete", expanded=False)
                st.rerun() # Refresh to show new data
            except Exception as e:
                status.update(label="Sync Failed", state="error")
                st.error(f"Error: {str(e)}")
    
    # 3. Process Data for View
    if not df.empty:
        df = apply_timezone(df)
        
        # Determine player nick if not just synced
        # We can store player nick in cache or just defaults. 
        # For now, if we have player_data from sync use it, else generic.
        
        render_header(player_data)
        
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
        st.title("Duels Analyzer")
        st.write("👋 Welcome! Please enter your `_ncfa` token in the sidebar and click **Sync Data** to get started.")
        st.warning("No data found in cache.")

if __name__ == "__main__":
    main()
