# Duels Analyzer 🌍

A modern Streamlit dashboard for analyzing Geoguessr Duels history — tracking win rate, country mastery, score distributions, rating progression, streaks, and more.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the dashboard:
   ```bash
   streamlit run app.py
   ```
3. Enter your `_ncfa` token in the sidebar to authorize and sync games.

## Features

- **Game & Round Win Rates** — true game-level outcomes via HP tracking
- **Rating Progression** — per-game rating delta chart
- **Win/Loss Streaks** — current and longest
- **Country Mastery** — choropleth maps, top/weakest countries
- **Opponent Analysis** — performance vs opponent nationality
- **Deep Dive** — per-round stats, binned histograms, Moving vs NMPZ comparison
- **Head-to-Head** — repeat opponent tracking
- **Data Export** — CSV download of all round-level data
- **Local Cache** — games stored in `games_cache.json`, only new games are fetched on sync
