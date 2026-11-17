"""
Steam Video Game Explorer — Portfolio Dashboard
Built with Python, SQLite (parameterized SQL), Plotly, and Streamlit.
Visual identity aligned with Alexander's Personal Website (white + warm surface + deep teal #16624f).
"""

from __future__ import annotations

import html
import streamlit as st

from src.sql_queries import (
    SORT_COLUMNS,
    GameFilterParams,
    get_filter_metadata,
    query_games_explorer,
    query_kpi_summary,
)

# st.set_page_config must be the very first Streamlit command called in the script.
# layout="wide" lets the dashboard use the full browser width for tables and charts
# rather than capping the page to a narrow center column.
st.set_page_config(
    page_title="Steam Game Explorer | Portfolio Dashboard",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_design_system_css() -> None:
    """
    Apply custom CSS using the exact design tokens (:root variables) from
    Alexander's Personal-Website repository.
    All text/background combinations meet WCAG AA/AAA contrast (>= 5.80:1).
    """
    st.markdown(
        """
        <style>
        :root {
            --color-bg: #ffffff;
            --color-surface: #f7f7f5;
            --color-media: #e9e9e5;
            --color-text: #17181a;
            --color-text-soft: #34363a;
            --color-text-muted: #5e6165;
            --color-border: #e4e4e0;
            --color-accent: #16624f;
            --color-accent-strong: #0f4a3b;
            --color-accent-ink: #ffffff;
            --radius-sm: 8px;
            --radius-card: 20px;
            --font-body: "Space Grotesk", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
            --font-mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
        }

        /* Tighten top padding so the header sits comfortably near the top of the viewport */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 78rem !important;
        }

        h1, h2, h3, h4 {
            font-family: var(--font-body) !important;
            letter-spacing: -0.03em !important;
            color: var(--color-text) !important;
        }

        /* Header bar with title and portfolio links */
        .portfolio-header {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: flex-end;
            gap: 1rem;
            padding-bottom: 1.25rem;
            margin-bottom: 1.25rem;
            border-bottom: 1px solid var(--color-border);
        }

        .portfolio-header__title {
            font-size: clamp(1.75rem, 3.5vw, 2.4rem);
            font-weight: 700;
            letter-spacing: -0.03em;
            color: var(--color-text);
            margin: 0 0 0.35rem 0;
            line-height: 1.15;
        }

        .portfolio-header__subtitle {
            font-size: 1rem;
            color: var(--color-text-muted);
            margin: 0;
            max-width: 46rem;
        }

        .portfolio-header__links {
            display: flex;
            gap: 0.6rem;
            flex-wrap: wrap;
        }

        .portfolio-btn {
            display: inline-block;
            padding: 0.45rem 0.9rem;
            border-radius: var(--radius-sm);
            font-size: 0.875rem;
            font-weight: 500;
            text-decoration: none !important;
            transition: background-color 120ms ease, border-color 120ms ease;
        }

        .portfolio-btn--primary {
            background-color: var(--color-accent);
            color: var(--color-accent-ink) !important;
            border: 1px solid var(--color-accent);
        }

        .portfolio-btn--primary:hover {
            background-color: var(--color-accent-strong);
            border-color: var(--color-accent-strong);
        }

        .portfolio-btn--secondary {
            background-color: var(--color-surface);
            color: var(--color-text) !important;
            border: 1px solid var(--color-border);
        }

        .portfolio-btn--secondary:hover {
            border-color: var(--color-accent);
            color: var(--color-accent) !important;
        }

        /* KPI Summary Cards */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
            gap: 0.85rem;
            margin-bottom: 1rem;
        }

        .kpi-card {
            background-color: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-sm);
            padding: 0.9rem 1.1rem;
        }

        .kpi-card__label {
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--color-text-muted);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.25rem;
        }

        .kpi-card__value {
            font-family: var(--font-mono);
            font-size: 1.45rem;
            font-weight: 700;
            color: var(--color-text);
            line-height: 1.2;
        }

        .kpi-card__sub {
            font-size: 0.8rem;
            color: var(--color-text-muted);
            margin-top: 0.2rem;
        }

        /* Game Spotlight Card (shown above the interactive table) */
        .spotlight-card {
            display: grid;
            grid-template-columns: minmax(240px, 340px) 1fr;
            gap: 1.5rem;
            background-color: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-card);
            padding: 1.25rem;
            margin-bottom: 1.25rem;
            align-items: start;
        }

        @media (max-width: 768px) {
            .spotlight-card {
                grid-template-columns: 1fr;
            }
        }

        /* Reserve aspect-ratio on the cover image wrapper so the page layout never
           jumps while the Steam CDN cover image downloads. */
        .spotlight-card__media {
            width: 100%;
            aspect-ratio: 460 / 215;
            background-color: var(--color-media);
            border-radius: calc(var(--radius-card) - 6px);
            overflow: hidden;
            border: 1px solid var(--color-border);
        }

        .spotlight-card__media img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        .spotlight-card__header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.75rem;
            flex-wrap: wrap;
            margin-bottom: 0.4rem;
        }

        .spotlight-card__title {
            font-size: 1.35rem;
            font-weight: 700;
            color: var(--color-text);
            margin: 0;
            letter-spacing: -0.02em;
        }

        .spotlight-card__meta {
            font-size: 0.9rem;
            color: var(--color-text-muted);
            margin-bottom: 0.65rem;
        }

        .spotlight-card__desc {
            font-size: 0.95rem;
            color: var(--color-text-soft);
            line-height: 1.5;
            margin-bottom: 0.9rem;
        }

        .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-bottom: 0.85rem;
        }

        .badge {
            font-family: var(--font-mono);
            font-size: 0.78rem;
            padding: 0.2rem 0.6rem;
            border-radius: var(--radius-sm);
            border: 1px solid var(--color-border);
            background-color: var(--color-bg);
            color: var(--color-text-soft);
        }

        .badge--accent {
            background-color: var(--color-accent);
            color: var(--color-accent-ink);
            border-color: var(--color-accent);
            font-weight: 500;
        }

        .spotlight-stats {
            display: flex;
            flex-wrap: wrap;
            gap: 1.25rem;
            padding-top: 0.75rem;
            border-top: 1px solid var(--color-border);
            font-family: var(--font-mono);
            font-size: 0.85rem;
            color: var(--color-text-soft);
        }

        .spotlight-stats strong {
            color: var(--color-text);
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                transition-duration: 0.01ms !important;
                animation-duration: 0.01ms !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_metadata() -> dict:
    """
    Cache filter metadata (distinct genres, studio tiers, modes, year bounds) in memory
    so we don't re-query static dropdown options on every user click.
    """
    return get_filter_metadata()


def reset_all_filters() -> None:
    """Callback for the 'Reset Filters' button to restore default session state."""
    st.session_state["f_search"] = ""
    st.session_state["f_studio_tiers"] = ["Indie", "AA", "AAA"]
    st.session_state["f_genres"] = []
    st.session_state["f_modes"] = []
    st.session_state["f_free_only"] = False
    st.session_state["f_max_price"] = 70.0
    st.session_state["f_playtime"] = (0.0, 200.0)
    st.session_state["f_min_score"] = 70
    st.session_state["f_sort_by"] = "Best Rated (Wilson Score)"


def render_sidebar(meta: dict) -> tuple[GameFilterParams, str]:
    """
    Render the 6 focused sidebar filter controls and return the structured
    GameFilterParams dataclass + selected sort order.
    """
    st.sidebar.markdown("### 🎯 Filter Games")
    st.sidebar.caption(
        f"Filtering **{meta['total_games']:,}** community-vetted Steam games "
        "(minimum 50 user reviews; shovelware & utilities excluded)."
    )

    st.sidebar.button(
        "↺ Reset All Filters",
        on_click=reset_all_filters,
        use_container_width=True,
    )

    # 1. Search by Game Title or Developer
    search_query = st.sidebar.text_input(
        "1. Search Title or Developer",
        value=st.session_state.get("f_search", ""),
        placeholder="e.g. Stardew Valley, Hades, Valve...",
        key="f_search",
    )

    # 2. Studio Tier classifier (Indie / AA / AAA)
    studio_tiers = st.sidebar.multiselect(
        "2. Studio Tier (Indie / AA / AAA)",
        options=meta["studio_tiers"],
        default=st.session_state.get("f_studio_tiers", ["Indie", "AA", "AAA"]),
        key="f_studio_tiers",
        help="Filter by Indie studios, AA (mid-tier publishers), or AAA (major publishers/blockbusters).",
    )

    # 3. Gameplay Genre
    genres = st.sidebar.multiselect(
        "3. Gameplay Genre",
        options=meta["genres"],
        default=st.session_state.get("f_genres", []),
        placeholder="All gameplay genres",
        key="f_genres",
    )

    # 4. Player Mode (Single-player, Co-op, PvP, Controller support, etc.)
    priority_modes = [
        "Single-player",
        "Multi-player",
        "Co-op",
        "Online Co-op",
        "Shared/Split Screen Co-op",
        "PvP",
        "Online PvP",
        "Full controller support",
        "Steam Workshop",
    ]
    available_modes = [m for m in priority_modes if m in meta["player_modes"]]
    player_modes = st.sidebar.multiselect(
        "4. Player Mode & Features",
        options=available_modes,
        default=st.session_state.get("f_modes", []),
        placeholder="Any player mode",
        key="f_modes",
    )

    # 5. Price & Free-to-Play
    st.sidebar.markdown("---")
    free_only = st.sidebar.checkbox(
        "Free-to-Play Games Only ($0)",
        value=st.session_state.get("f_free_only", False),
        key="f_free_only",
    )
    max_price_slider = st.sidebar.slider(
        "5. Max Price ($ USD)",
        min_value=0.0,
        max_value=70.0,
        value=float(st.session_state.get("f_max_price", 70.0)),
        step=5.0,
        disabled=free_only,
        key="f_max_price",
        help="Slide to 70 to include all price points, or lower to find budget gems.",
    )
    # If slider is at max (70.0), don't cap rare collector's editions priced > $70
    effective_max_price = None if max_price_slider >= 70.0 else max_price_slider

    # 6. Playtime & Minimum Review Score
    playtime_range = st.sidebar.slider(
        "6a. Average Playtime (Hours)",
        min_value=0.0,
        max_value=200.0,
        value=st.session_state.get("f_playtime", (0.0, 200.0)),
        step=5.0,
        key="f_playtime",
        help="Filter by how long players spend in the game on average (200+ includes endless games).",
    )
    min_playtime = playtime_range[0]
    max_playtime = None if playtime_range[1] >= 200.0 else playtime_range[1]

    min_score = st.sidebar.slider(
        "6b. Minimum User Score (%)",
        min_value=0,
        max_value=95,
        value=int(st.session_state.get("f_min_score", 70)),
        step=5,
        key="f_min_score",
        help="70%+ = Mostly Positive, 80%+ = Very Positive, 95%+ = Overwhelmingly Positive.",
    )

    sort_by = st.sidebar.selectbox(
        "Sort Results By",
        options=list(SORT_COLUMNS.keys()),
        index=0,
        key="f_sort_by",
    )

    filters = GameFilterParams(
        studio_tiers=studio_tiers if len(studio_tiers) < 3 else [],
        genres=genres,
        player_modes=player_modes,
        max_price=effective_max_price,
        free_only=free_only,
        min_playtime_hours=min_playtime,
        max_playtime_hours=max_playtime,
        min_review_score_pct=float(min_score),
        search_query=search_query,
    )

    # Edge case: if the user explicitly deselects all 3 studio tiers, treat as no studio tier match
    if len(studio_tiers) == 0:
        filters.studio_tiers = ["__NONE__"]

    return filters, sort_by


def render_header_and_kpis(kpi: dict, total_catalog: int, executed_sql: str) -> None:
    """Render the portfolio header, 5 KPI summary cards, and the Live SQL Query drawer."""
    st.markdown(
        """
        <header class="portfolio-header">
            <div>
                <h1 class="portfolio-header__title">Steam Video Game Explorer</h1>
                <p class="portfolio-header__subtitle">
                    Interactive SQL &amp; Python analytics dashboard exploring player reception,
                    playtime engagement, pricing value, and Indie vs. AA/AAA studio trends.
                </p>
            </div>
            <div class="portfolio-header__links">
                <a class="portfolio-btn portfolio-btn--primary"
                   href="https://github.com/MrMusselwhite/video_game_dashdashboard"
                   target="_blank" rel="noopener noreferrer">
                   GitHub Repository ↗
                </a>
                <a class="portfolio-btn portfolio-btn--secondary"
                   href="https://github.com/MrMusselwhite"
                   target="_blank" rel="noopener noreferrer">
                   Portfolio Profile ↗
                </a>
            </div>
        </header>
        """,
        unsafe_allow_html=True,
    )

    matching = int(kpi.get("matching_games") or 0)
    pct_of_catalog = (matching / total_catalog * 100.0) if total_catalog else 0.0
    indie_share = kpi.get("indie_share_pct")
    avg_score = kpi.get("avg_review_score_pct")
    avg_playtime = kpi.get("avg_playtime_hours")
    avg_price = kpi.get("avg_price")
    avg_meta = kpi.get("avg_metacritic_score")

    st.markdown(
        f"""
        <section class="kpi-grid" aria-label="Filtered Summary Metrics">
            <div class="kpi-card">
                <div class="kpi-card__label">Matching Games</div>
                <div class="kpi-card__value">{matching:,}</div>
                <div class="kpi-card__sub">{pct_of_catalog:.1f}% of curated catalog</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-card__label">Indie Share</div>
                <div class="kpi-card__value">{f"{indie_share:.1f}%" if indie_share is not None else "—"}</div>
                <div class="kpi-card__sub">Self-published &amp; Indie studios</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-card__label">Avg User Score</div>
                <div class="kpi-card__value">{f"{avg_score:.1f}%" if avg_score is not None else "—"}</div>
                <div class="kpi-card__sub">Metacritic Avg: {f"{avg_meta:.0f}" if avg_meta is not None else "N/A"}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-card__label">Avg Playtime</div>
                <div class="kpi-card__value">{f"{avg_playtime:.1f}h" if avg_playtime is not None else "—"}</div>
                <div class="kpi-card__sub">Recorded Steam average</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-card__label">Avg Price</div>
                <div class="kpi-card__value">{f"${avg_price:.2f}" if avg_price is not None else "—"}</div>
                <div class="kpi-card__sub">USD store price</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🔍 View Live SQL Query (Generated by Current Filters)", expanded=False):
        st.caption(
            "Every filter change executes a parameterized read-only SQLite query (`?mode=ro`). "
            "Below is the formatted SQL query powering the current view:"
        )
        st.code(executed_sql, language="sql")


def render_spotlight_card(game_row: dict) -> None:
    """
    Render the 'Game Spotlight' preview card for the currently selected row in the table
    (or the #1 top-ranked game when no row is clicked yet).
    """
    # Escape text fields so game titles or descriptions containing '<' or '&' never break HTML markup
    title = html.escape(str(game_row["name"]))
    dev = html.escape(str(game_row["developers"] or "Unknown"))
    pub = html.escape(str(game_row["publishers"] or "Unknown"))
    desc = html.escape(
        str(game_row["short_description"] or "No description provided on Steam.")
    )
    studio_tier = html.escape(str(game_row["studio_tier"]))
    genres_str = html.escape(str(game_row["genres_str"]))
    modes_str = html.escape(str(game_row["player_modes_str"]))
    rating_tier = html.escape(str(game_row["steam_rating_tier"]))
    img_url = html.escape(str(game_row["header_image"]))
    app_id = int(game_row["app_id"])
    year = int(game_row["release_year"])

    price_val = float(game_row["price"])
    price_display = "Free to Play" if price_val == 0.0 else f"${price_val:.2f}"
    score_pct = float(game_row["review_score_pct"])
    total_rev = int(game_row["total_reviews"])
    playtime_hrs = float(game_row["avg_playtime_hours"])
    peak_ccu = int(game_row["peak_ccu"])
    meta_val = game_row["metacritic_score"]
    meta_str = (
        f"Metacritic: {int(meta_val)}/100"
        if meta_val is not None and str(meta_val) != "nan"
        else "Metacritic: —"
    )

    st.markdown(
        f"""
        <article class="spotlight-card" aria-label="Selected Game Spotlight">
            <div class="spotlight-card__media">
                <img src="{img_url}" alt="Cover art for {title}" loading="lazy" width="460" height="215" />
            </div>
            <div>
                <div class="spotlight-card__header">
                    <h3 class="spotlight-card__title">{title} ({year})</h3>
                    <a class="portfolio-btn portfolio-btn--primary"
                       href="https://store.steampowered.com/app/{app_id}"
                       target="_blank" rel="noopener noreferrer">
                       View on Steam ↗
                    </a>
                </div>
                <div class="spotlight-card__meta">
                    Developer: <strong>{dev}</strong> &nbsp;|&nbsp; Publisher: <strong>{pub}</strong>
                </div>
                <div class="badge-row">
                    <span class="badge badge--accent">Studio: {studio_tier}</span>
                    <span class="badge">{rating_tier} ({score_pct:.1f}%)</span>
                    <span class="badge">{genres_str}</span>
                    <span class="badge">{modes_str}</span>
                </div>
                <p class="spotlight-card__desc">{desc}</p>
                <div class="spotlight-stats">
                    <span>Price: <strong>{price_display}</strong></span>
                    <span>User Reviews: <strong>{total_rev:,}</strong></span>
                    <span>Avg Playtime: <strong>{playtime_hrs:.1f} hrs</strong></span>
                    <span>Peak Players: <strong>{peak_ccu:,}</strong></span>
                    <span><strong>{meta_str}</strong></span>
                </div>
            </div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_game_explorer_tab(filters: GameFilterParams, sort_by: str) -> None:
    """
    Render Tab 1: 'Game Explorer' featuring:
    1. A 'Game Spotlight' preview card (defaults to #1 result; updates when a user clicks any table row).
    2. An interactive, sortable table with a mini cover image column (`ImageColumn`).
    """
    col_info, col_limit = st.columns([3, 1])
    with col_limit:
        result_limit = st.selectbox(
            "Rows to display",
            options=[50, 100, 250, 500],
            index=1,
            label_visibility="collapsed",
        )

    games_df, _ = query_games_explorer(filters, sort_by=sort_by, limit=result_limit)

    if games_df.empty:
        st.warning(
            "No games matched your current filter combination. "
            "Try broadening your price, playtime, or genre filters in the sidebar."
        )
        return

    # Read which row is currently selected in the interactive dataframe below.
    # On initial load (before any row is clicked), we default to index 0 (the #1 top match).
    selected_idx = 0
    table_state = st.session_state.get("explorer_table_selection")
    if table_state and "selection" in table_state:
        rows = table_state["selection"].get("rows", [])
        if rows and 0 <= rows[0] < len(games_df):
            selected_idx = rows[0]

    selected_game = games_df.iloc[selected_idx].to_dict()

    with col_info:
        st.markdown(
            f"**Game Spotlight** — Showing **#{selected_idx + 1}** of top **{len(games_df)}** displayed matches "
            "*(click any row in the table below to inspect that game)*"
        )

    render_spotlight_card(selected_game)

    # Prepare clean table columns for st.dataframe
    display_df = games_df[
        [
            "header_image",
            "name",
            "studio_tier",
            "primary_genre",
            "review_score_pct",
            "metacritic_score",
            "avg_playtime_hours",
            "price",
            "total_reviews",
            "peak_ccu",
            "release_year",
        ]
    ].copy()

    st.dataframe(
        display_df,
        key="explorer_table_selection",
        on_select="rerun",
        selection_mode="single-row",
        use_container_width=True,
        hide_index=True,
        height=560,
        column_config={
            "header_image": st.column_config.ImageColumn(
                "Cover",
                help="Official Steam store header image",
                width="small",
            ),
            "name": st.column_config.TextColumn(
                "Game Title",
                width="medium",
            ),
            "studio_tier": st.column_config.TextColumn(
                "Studio",
                help="Indie, AA (Mid-Tier), or AAA (Major Studio)",
                width="small",
            ),
            "primary_genre": st.column_config.TextColumn(
                "Genre",
                width="small",
            ),
            "review_score_pct": st.column_config.ProgressColumn(
                "User Score",
                help="Percentage of positive user reviews on Steam",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "metacritic_score": st.column_config.NumberColumn(
                "Metacritic",
                help="Critic score out of 100 (blank if not reviewed on Metacritic)",
                format="%d",
            ),
            "avg_playtime_hours": st.column_config.NumberColumn(
                "Avg Playtime",
                help="Average recorded Steam playtime in hours",
                format="%.1f hrs",
            ),
            "price": st.column_config.NumberColumn(
                "Price",
                format="$%.2f",
            ),
            "total_reviews": st.column_config.NumberColumn(
                "Total Reviews",
                format="%d",
            ),
            "peak_ccu": st.column_config.NumberColumn(
                "Peak Players",
                help="Peak concurrent players (CCU)",
                format="%d",
            ),
            "release_year": st.column_config.NumberColumn(
                "Year",
                format="%d",
            ),
        },
    )


def main() -> None:
    inject_design_system_css()
    meta = load_metadata()
    filters, sort_by = render_sidebar(meta)

    kpi, _ = query_kpi_summary(filters)
    _, explorer_sql = query_games_explorer(filters, sort_by=sort_by, limit=100)
    render_header_and_kpis(kpi, meta["total_games"], explorer_sql)

    tab_explorer, tab_scatter, tab_landscape = st.tabs(
        [
            "🎮 Game Explorer",
            "📈 Value vs. Reception Scatter",
            "🗺️ Genre & Studio Landscape",
        ]
    )

    with tab_explorer:
        render_game_explorer_tab(filters, sort_by)

    with tab_scatter:
        st.info(
            "Phase 4 (Next Step): Preset Story Buttons ('Playtime vs. Score', 'Price vs. Score', "
            "'Critic vs. Player Score') + Custom Axes Scatter Plot."
        )

    with tab_landscape:
        st.info(
            "Phase 5 (Upcoming): Horizontal Genre Ranking Bar Chart + Genre Bubble Matrix + "
            "Indie vs. AA vs. AAA Studio Comparison."
        )


if __name__ == "__main__":
    main()
