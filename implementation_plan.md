# Implementation Plan - Duels Analyzer UI Overhaul

This plan outlines the steps to modernize the user interface, implement data persistence, and refactor the code for better maintainability while preserving existing functionality.

## 1. Architecture Restructuring

Split the monolithic `main.py` into modular components to separate concerns (UI vs. Logic).

- **`backend.py`**: Handles API interaction, data processing, and persistence logic.
- **`app.py`**: The main entry point containing the UI code (Streamlit).
- **`utils.py`**: Shared helper functions (dates, formatting).
- **`assets/style.css`**: Custom CSS for a premium look.

## 2. Data Persistence (Caching Strategy)

Implement a robust caching mechanism to avoid re-scraping existing games.

- **Storage**: Use a local JSON file (`games_cache.json`) as the primary storage.
- **Logic**:
  1.  **Load**: On startup, load existing games from `games_cache.json` into a Pandas DataFrame.
  2.  **Sync**: logic to fetch *new* game tokens from the Geoguessr API.
  3.  **Update**: Compare fetched tokens with cached Game IDs. Only fetch details for the *missing* (new) games.
  4.  **Save**: Append new game details to the cache file and save.
- **Streamlit Compatibility**: This works perfectly for local deployments. For Streamlit Cloud, it acts as a session-to-session cache (until the container restarts), which is still an improvement over the current "scrape everything every refresh" model.

## 3. UI Overhaul (Visual Excellence)

Transform the interface from a linear script into a modern dashboard.

- **Theme**: Dark mode optimized with vibrant accent colors (Teal/Purple).
- **Layout**:
  - **Sidebar**: Configuration, Token Input, Filters (Date, Game Mode).
  - **Main Area**:
    - **Hero Section**: High-level metrics (Win Rate, Current Rating, Total Games) displayed as prominent cards.
    - **Tabs**: Organize content to reduce scrolling.
      - **Dashboard**: aggregated trends and recent performance.
      - **Geography**: Maps and country-specific performance (Heatmaps).
      - **Analysis**: Detailed charts (Score distribution, Round analysis).
      - **Raw Data**: Data table and export options.
- **Components**:
  - Custom CSS for "glassmorphism" cards.
  - Interactive Plotly charts with consistent theming (removing default backgrounds, using custom color palettes).

## 4. Implementation Steps

### Step 1: Backend Refactor (`backend.py`)
- Extract scraping logic from `main.py`.
- Implement `JobManager` or `DataManager` class to handle the sync logic described above.
- Ensure `requests.Session` is managed correctly.

### Step 2: Frontend Setup (`app.py`)
- Initialize `st.set_page_config`.
- specific custom CSS injection.
- Create the authentication/onboarding state (keeping the current cookie method).

### Step 3: Dashboard Construction
- Re-implement the visualizations using the cleaned data from `backend.py`.
- Apply "Premium" styling directives (Plotly template updates).
- Verify all original metrics (Win Rate, Score Diff, etc.) are present.

### Step 4: Verification
- Test user flow: Enter Token -> Load Cache -> Fetch New -> Display.
- Verify filtering works on the cached dataset.

