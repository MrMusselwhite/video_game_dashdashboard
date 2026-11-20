# Steam Video Game Explorer — Interactive Portfolio Dashboard

An interactive data analytics dashboard built with **Python**, **SQL (`sqlite3`)**, **Plotly**, and **Streamlit** to help players and analysts explore **20,316 curated Steam video games** by studio tier (`Indie`, `AA`, `AAA`), gameplay genre, player mode, playtime engagement, pricing value, and player vs. critic reception.

> **Status:** Active development — Phases 1–3 complete (Data Pipeline, SQL Query Engine, & Interactive Game Explorer). Phases 4–6 (Scatter Plot Analytics, Genre & Studio Landscape, and Streamlit Community Cloud Deployment) are queued next.

---

## Project Goals & Architecture

This project is designed as a public, link-ready portfolio piece (built to be shared via **Streamlit Community Cloud**) that demonstrates end-to-end data skills:
1. **Python Data Engineering & Cleaning (`pandas`):** Transforming 124,146 raw Steam store records into a clean, relational SQLite database with strict anti-shovelware and pricing data-quality rules.
2. **Parameterized SQL Analytics (`sqlite3`):** Every filter, KPI metric, and table view runs read-only (`?mode=ro`), parameterized SQL queries (`?` placeholders to prevent SQL injection) — with a live **"🔍 View Live SQL Query"** drawer in the UI so visitors and technical reviewers can inspect the exact SQL behind their filter clicks.
3. **Cohesive Portfolio UI:** Styled using the exact WCAG-verified color tokens (`#ffffff` background, `#f7f7f5` warm surfaces, `#e4e4e0` borders, `#16624f` deep teal accent, `#17181a` ink) and typography (`Space Grotesk` + `JetBrains Mono`) from my [Personal Website](https://github.com/MrMusselwhite/Personal-Website).

---

## What Has Been Built So Far (Phases 1–3)

### Phase 1: Data Cleaning & Anti-Shovelware Pipeline (`src/data_pipeline.py`)
Source dataset: Public Steam Games Dataset (`FronkonGames/steam-games-dataset`, **124,146** raw rows).

Key cleaning and feature-engineering decisions:
- **Anti-Shovelware & Portfolio-Safe Quality Gate:**
  - Requires at least **50 user reviews** (`positive + negative >= 50`), at least **10 minutes** of recorded average playtime, a valid Steam cover art URL (`header_image`), and at least one valid gameplay genre.
  - Excludes Playtests, Demos, Soundtracks/OSTs, Dedicated Servers, SDKs, Benchmarks, desktop software utilities (*Wallpaper Engine*, *Soundpad*, *Lossless Scaling*, *3DMark*, *Source Filmmaker*, etc.), and explicit NSFW shovelware.
  - Result: **20,316** community-vetted video games.
- **Dedicated Studio Tier Classification (`Indie`, `AA`, `AAA`):**
  - Separated `'Indie'` out of the gameplay genre list into its own dedicated studio classifier (`studio_tier` and `is_indie`), keeping gameplay genres clean (`Action`, `Adventure`, `RPG`, `Strategy`, `Simulation`, `Casual`, `Sports`, `Racing`, `Massively Multiplayer`, `Education`).
  - Breakdown: **15,577 Indie** · **3,439 AA (Mid-Tier)** · **1,300 AAA (Major Studio)**.
- **Fixing Delisted & Subscription `$0.00` Price Bugs:**
  - In raw Steam API scrapes, delisted/replaced paid editions (e.g., *Grand Theft Auto V Legacy*, *FIFA 21–23*, *Yakuza 0*, *Rocket League*) and subscription-only entries (e.g., `"EA Play - Free"`) default to `price = 0.0`.
  - The pipeline recovers real non-zero prices from Steam's `packages` JSON where available (e.g., *Horizon Zero Dawn™ Complete Edition* → `$49.99`), excludes subscription-only `"Free"` tags, and stores unpurchasable/delisted editions as SQL **`NULL`** (`is_free = 0`) so `AVG(price)` and `"Free-to-Play Only"` stay accurate.
- **Derived Analytical Metrics:**
  - `wilson_score`: Lower bound of the 95% Wilson score confidence interval (SteamDB-style ranking that balances review ratio with review volume).
  - `metacritic_score`: Converted `0` values to SQL `NULL` so critic averages aren't artificially dragged down.
  - `avg_playtime_hours`, `median_playtime_hours`, `playtime_tier`, `hours_per_dollar`, and `estimated_owners_mid`.

### Phase 2: Relational SQLite Schema & Query Engine (`src/sql_queries.py`)
Normalized 3-table SQLite database (`data/steam_games.db`, ~22.4 MB, indexed for sub-second filtering):
- **`games`** (`20,316` rows) — primary game metrics, studio tier, pricing, ratings, playtime, and cover art URL.
- **`game_genres`** (`41,114` rows) — normalized `(app_id, genre)` bridge table queried via `EXISTS` / `INNER JOIN`.
- **`game_modes`** (`75,018` rows) — normalized `(app_id, mode)` bridge table (`Single-player`, `Online Co-op`, `PvP`, `Full controller support`, `Steam Workshop`, etc.).

Implemented read-only parameterized SQL functions:
- `get_filter_metadata()` — populates dynamic filter controls and counts.
- `query_kpi_summary()` — computes live filtered KPI metrics (`Matching Games`, `Indie Share %`, `Avg User Score`, `Avg Metacritic`, `Avg Playtime`, `Avg Price`).
- `query_games_explorer()` — powers the full scrollable explorer table and live SQL preview.
- `query_genre_landscape()` & `query_studio_tier_comparison()` — SQL `JOIN` + `GROUP BY` aggregations ready for Phase 5.

### Phase 3: Dashboard Shell & Tab 1 — Game Explorer (`app.py`, `.streamlit/config.toml`)
- **Focused 6-Filter Sidebar + Reset Button:** Search by Title/Developer, Studio Tier (`Indie` / `AA` / `AAA`), Gameplay Genre, Player Mode & Features, Max Price / Free-to-Play, Average Playtime, Minimum User Score, and Sort Order.
- **Top KPI Bar + Live SQL Drawer:** Updates dynamically on every filter change.
- **Tab 1 ("🎮 Game Explorer"):**
  - Virtualized `st.dataframe` displaying **all matching games** with clickable column-header sorting, mini Steam cover art thumbnails (`ImageColumn`), User Score progress bars, Metacritic, Playtime, Price (`$XX.XX`, `$0.00` for Free, `—` for Delisted), and direct Steam Store links.
  - **Clean Row-Click Modal (`@st.dialog`):** Nothing pops up on initial page load; clicking any row opens a centered **Game Details** modal with full cover art, developer/publisher, description, 6-metric stats grid (including `Value: hrs/$`), and `"Open on Steam Store ↗"` link — plus a contextual **`🔍 View more details`** button above the table.

---

## Upcoming Roadmap (Phases 4–6)

- [ ] **Phase 4 — Tab 2 (`📈 Value vs. Reception Scatter`):**
  - Interactive Plotly scatter plot with **1-click Preset Story Buttons**:
    1. *Playtime vs. Score* (engagement vs. player praise)
    2. *Price vs. Score* (budget gems vs. premium titles)
    3. *Critic vs. Player Score* (Metacritic vs. Steam user consensus)
  - Optional collapsed **"Customize Axes"** toggle for visitors who want to explore custom X/Y/Size/Color dimensions.
- [ ] **Phase 5 — Tab 3 (`🗺️ Genre & Studio Landscape`):**
  - **Horizontal Genre Ranking Bar Chart** by user-chosen metric (`Avg Playtime`, `User Score %`, `Avg Price`, `Value hrs/$`, or `Game Count`).
  - **Genre Bubble Matrix** (`Avg Playtime` vs. `Avg User Score`, sized by `Number of Games`).
  - **Indie vs. AA vs. AAA Studio Comparison** panel powered by `query_studio_tier_comparison()`.
- [ ] **Phase 6 — Final Polish & Deployment:**
  - Connect `MrMusselwhite/video_game_dashdashboard` to **Streamlit Community Cloud** (`https://<app>.streamlit.app`) for instant zero-login access from LinkedIn and my Personal Website.
  - Final accessibility, contrast, and responsive layout review.

---

## Repository Structure

```text
video_game_dashdashboard/
├── .streamlit/
│   └── config.toml          # Light theme tokens matching Personal-Website (#16624f teal)
├── data/
│   └── steam_games.db       # Cleaned, indexed SQLite database (20,316 games)
├── src/
│   ├── data_pipeline.py     # Phase 1: Python ETL, anti-shovelware gate, studio tiers & price cleaning
│   └── sql_queries.py       # Phase 2: Read-only parameterized SQL query engine & SQL formatter
├── app.py                   # Phase 3+: Streamlit web application
├── requirements.txt         # Python dependencies
└── README.md
```

---

## Running Locally

1. **Create and activate a virtual environment** (first time only):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start the dashboard locally:**
   ```bash
   source .venv/bin/activate
   streamlit run app.py
   ```
   Open **http://localhost:8501** in your browser. Press **`Ctrl + C`** in the terminal to stop the server.

3. *(Optional)* **Re-run the data pipeline** (requires downloading `raw_steam_games.parquet` into `data/`):
   ```bash
   .venv/bin/python src/data_pipeline.py
   ```
