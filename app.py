"""
Steam Video Game Explorer — Portfolio Dashboard
Built with Python, SQLite (parameterized SQL), Plotly, and Streamlit.
Visual identity aligned with Alexander's Personal Website (white + warm surface + deep teal #16624f).
"""

from __future__ import annotations

import html
import math
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

        /* Explorer Table Header & Row Styling */
        .table-header-label {
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--color-text-muted);
            padding: 0.35rem 0;
        }

        .row-thumb {
            width: 100%;
            max-width: 120px;
            aspect-ratio: 460 / 215;
            object-fit: cover;
            border-radius: 6px;
            background-color: var(--color-media);
            border: 1px solid var(--color-border);
            display: block;
        }

        .row-title {
            font-weight: 600;
            font-size: 0.95rem;
            color: var(--color-text);
            line-height: 1.25;
            margin-bottom: 0.15rem;
        }

        .row-sub {
            font-size: 0.78rem;
            color: var(--color-text-muted);
            font-family: var(--font-mono);
        }

        .row-mono {
            font-family: var(--font-mono);
            font-size: 0.86rem;
            color: var(--color-text-soft);
        }

        .row-score-high {
            font-family: var(--font-mono);
            font-size: 0.86rem;
            font-weight: 700;
            color: var(--color-accent);
        }

        .row-divider {
            border: 0;
            border-top: 1px solid var(--color-border);
            margin: 0.35rem 0 0.45rem 0;
        }

        .pill {
            display: inline-block;
            font-family: var(--font-mono);
            font-size: 0.74rem;
            padding: 0.14rem 0.5rem;
            border-radius: var(--radius-sm);
            border: 1px solid var(--color-border);
            background-color: var(--color-surface);
            color: var(--color-text-soft);
            white-space: nowrap;
        }

        .pill--accent {
            background-color: var(--color-accent);
            color: var(--color-accent-ink);
            border-color: var(--color-accent);
            font-weight: 500;
        }

        .pill--muted {
            color: var(--color-text-muted);
            background-color: var(--color-bg);
        }

        /* Modal detail card media & stats */
        .modal-cover {
            width: 100%;
            aspect-ratio: 460 / 215;
            background-color: var(--color-media);
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid var(--color-border);
            margin-bottom: 1rem;
        }

        .modal-cover img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        .modal-meta {
            font-size: 0.9rem;
            color: var(--color-text-muted);
            margin-bottom: 0.75rem;
        }

        .modal-desc {
            font-size: 0.96rem;
            color: var(--color-text-soft);
            line-height: 1.55;
            margin: 0.75rem 0 1rem 0;
        }

        .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-bottom: 0.5rem;
        }

        .modal-stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(8.5rem, 1fr));
            gap: 0.65rem;
            margin: 1rem 0 1.25rem 0;
        }

        .modal-stat-box {
            background-color: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-sm);
            padding: 0.65rem 0.8rem;
        }

        .modal-stat-box__label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--color-text-muted);
            margin-bottom: 0.15rem;
        }

        .modal-stat-box__val {
            font-family: var(--font-mono);
            font-size: 1rem;
            font-weight: 700;
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


def format_price_display(price_val: object, is_free: int) -> tuple[str, str]:
    """
    Format a game's price into (display_text, status_kind):
      - ('Free', 'free') for confirmed Free-to-Play titles
      - ('$19.99', 'paid') for active paid titles
      - ('N/A', 'delisted') for delisted/replaced editions with NULL price
    """
    if int(is_free or 0) == 1:
        return "Free", "free"
    if price_val is None or (isinstance(price_val, float) and math.isnan(price_val)):
        return "N/A", "delisted"
    return f"${float(price_val):.2f}", "paid"


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
    st.session_state["last_modal_app_id"] = None


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
        help="Slide to 70 to include all games (including delisted editions with N/A price), or lower to set a strict budget.",
    )
    # If slider is at max (70.0), don't cap rare collector's editions or hide N/A delisted games
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

    # Edge case: if the user explicitly deselects all 3 studio tiers, return 0 matches
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
                <div class="kpi-card__sub">Active USD store prices</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🔍 View Live SQL Query (Generated by Current Filters)", expanded=False):
        st.caption(
            "Every filter change executes a parameterized read-only SQLite query (`?mode=ro`). "
            "Below is the formatted SQL query powering the current page:"
        )
        st.code(executed_sql, language="sql")


@st.dialog("Game Details", width="large")
def open_game_detail_modal(game_row: dict) -> None:
    """
    Modal popup triggered ONLY when a visitor clicks 'View more' on a specific game row.
    Keeping this inside @st.dialog ensures nothing pops up on initial page load and
    visitors never lose their scroll position when inspecting games further down the list.
    """
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

    price_text, price_kind = format_price_display(game_row["price"], game_row["is_free"])
    if price_kind == "delisted":
        price_display = "N/A (Delisted)"
    elif price_kind == "free":
        price_display = "Free to Play"
    else:
        price_display = price_text

    score_pct = float(game_row["review_score_pct"])
    total_rev = int(game_row["total_reviews"])
    playtime_hrs = float(game_row["avg_playtime_hours"])
    peak_ccu = int(game_row["peak_ccu"])
    meta_val = game_row["metacritic_score"]
    meta_str = (
        f"{int(meta_val)} / 100"
        if meta_val is not None and not (isinstance(meta_val, float) and math.isnan(meta_val))
        else "—"
    )
    hpd_val = game_row["hours_per_dollar"]
    hpd_str = (
        f"{float(hpd_val):.1f} hrs/$"
        if hpd_val is not None and not (isinstance(hpd_val, float) and math.isnan(hpd_val))
        else "—"
    )

    st.markdown(
        f"""
        <div class="modal-cover">
            <img src="{img_url}" alt="Cover art for {title}" width="460" height="215" />
        </div>
        <h2 style="margin: 0 0 0.25rem 0;">{title} ({year})</h2>
        <div class="modal-meta">
            Developer: <strong>{dev}</strong> &nbsp;|&nbsp; Publisher: <strong>{pub}</strong>
        </div>
        <div class="badge-row">
            <span class="pill pill--accent">Studio: {studio_tier}</span>
            <span class="pill">{rating_tier} ({score_pct:.1f}%)</span>
            <span class="pill">{genres_str}</span>
            <span class="pill">{modes_str}</span>
        </div>
        <p class="modal-desc">{desc}</p>
        <div class="modal-stats-grid">
            <div class="modal-stat-box">
                <div class="modal-stat-box__label">Price</div>
                <div class="modal-stat-box__val">{price_display}</div>
            </div>
            <div class="modal-stat-box">
                <div class="modal-stat-box__label">User Reviews</div>
                <div class="modal-stat-box__val">{total_rev:,}</div>
            </div>
            <div class="modal-stat-box">
                <div class="modal-stat-box__label">Avg Playtime</div>
                <div class="modal-stat-box__val">{playtime_hrs:.1f} hrs</div>
            </div>
            <div class="modal-stat-box">
                <div class="modal-stat-box__label">Peak Players</div>
                <div class="modal-stat-box__val">{peak_ccu:,}</div>
            </div>
            <div class="modal-stat-box">
                <div class="modal-stat-box__label">Metacritic</div>
                <div class="modal-stat-box__val">{meta_str}</div>
            </div>
            <div class="modal-stat-box">
                <div class="modal-stat-box__label">Value</div>
                <div class="modal-stat-box__val">{hpd_str}</div>
            </div>
        </div>
        <a class="portfolio-btn portfolio-btn--primary"
           href="https://store.steampowered.com/app/{app_id}"
           target="_blank" rel="noopener noreferrer">
           Open on Steam Store ↗
        </a>
        """,
        unsafe_allow_html=True,
    )


def render_game_explorer_tab(
    games_df,
) -> None:
    """
    Render Tab 1: 'Game Explorer' using Streamlit's virtualized st.dataframe so:
      - ALL matching games are smoothly scrollable (no 50-row cap)
      - Every column header is clickable to sort ascending/descending
      - Mini Steam cover thumbnails appear in the first column
      - Nothing pops up on initial load; selecting any row immediately opens
        the 'Game Details' modal (@st.dialog), and a 'View more' button appears
        above the table to re-open the selected game anytime.
    """
    if games_df.empty:
        st.warning(
            "No games matched your current filter combination. "
            "Try broadening your price, playtime, or genre filters in the sidebar."
        )
        return

    # Check if the user has selected a row in the table
    selected_idx: int | None = None
    table_state = st.session_state.get("explorer_table")
    if table_state and "selection" in table_state:
        rows = table_state["selection"].get("rows", [])
        if rows and 0 <= rows[0] < len(games_df):
            selected_idx = rows[0]

    # Top bar: row count + contextual 'View more' button when a row is selected
    bar_left, bar_right = st.columns([3, 1.3], vertical_alignment="center")
    if selected_idx is not None:
        selected_game = games_df.iloc[selected_idx].to_dict()
        selected_app_id = int(selected_game["app_id"])
        selected_title = str(selected_game["name"])

        with bar_left:
            st.caption(
                f"Showing all **{len(games_df):,}** matching games · "
                f"Selected: **{selected_title}**"
            )
        with bar_right:
            reopen_clicked = st.button(
                "🔍 View more details",
                key="reopen_selected_game_modal",
                type="primary",
                use_container_width=True,
            )

        # Open the modal automatically when a NEW row is selected, or when 'View more details' is clicked.
        # Storing last_modal_app_id prevents the modal from re-opening unexpectedly after the user closes it.
        if reopen_clicked or st.session_state.get("last_modal_app_id") != selected_app_id:
            st.session_state["last_modal_app_id"] = selected_app_id
            open_game_detail_modal(selected_game)
    else:
        st.session_state["last_modal_app_id"] = None
        with bar_left:
            st.caption(
                f"Showing all **{len(games_df):,}** matching games · "
                "Click any column header to sort · Select any row to open full game details."
            )

    # Build table DataFrame with numeric types preserved so column-header sorting works accurately
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
    display_df["steam_url"] = (
        "https://store.steampowered.com/app/" + games_df["app_id"].astype(str)
    )

    st.dataframe(
        display_df,
        key="explorer_table",
        on_select="rerun",
        selection_mode="single-row",
        use_container_width=True,
        hide_index=True,
        height=620,
        row_height=54,
        placeholder="—",
        column_config={
            "header_image": st.column_config.ImageColumn(
                "Cover",
                help="Official Steam store cover image",
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
                help="Percentage of positive Steam user reviews",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "metacritic_score": st.column_config.NumberColumn(
                "Metacritic",
                help="Critic score out of 100 (— if no Metacritic score)",
                format="%d",
            ),
            "avg_playtime_hours": st.column_config.NumberColumn(
                "Avg Playtime",
                help="Average recorded Steam playtime in hours",
                format="%.1f hrs",
            ),
            "price": st.column_config.NumberColumn(
                "Price",
                help="$0.00 = Free to Play · — = Delisted / Unavailable on Steam",
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
            "steam_url": st.column_config.LinkColumn(
                "Steam",
                display_text="Store ↗",
                width="small",
            ),
        },
    )


def main() -> None:
    inject_design_system_css()
    meta = load_metadata()
    filters, sort_by = render_sidebar(meta)

    kpi, _ = query_kpi_summary(filters)
    games_df, executed_sql = query_games_explorer(filters, sort_by=sort_by, limit=None)

    render_header_and_kpis(kpi, meta["total_games"], executed_sql)

    tab_explorer, tab_scatter, tab_landscape = st.tabs(
        [
            "🎮 Game Explorer",
            "📈 Value vs. Reception Scatter",
            "🗺️ Genre & Studio Landscape",
        ]
    )

    with tab_explorer:
        render_game_explorer_tab(games_df)

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
