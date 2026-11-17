"""
Phase 2: Parameterized SQL Query Engine for the Steam Video Game Dashboard.
Uses read-only SQLite connections and parameterized queries (?) for security,
and generates formatted SQL previews for the portfolio "View Live SQL Query" panel.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQLITE_DB_PATH = PROJECT_ROOT / "data" / "steam_games.db"

SORT_COLUMNS: dict[str, str] = {
    "Best Rated (Wilson Score)": "g.wilson_score DESC, g.total_reviews DESC",
    "Most Popular (Total Reviews)": "g.total_reviews DESC, g.wilson_score DESC",
    "Peak Active Players (CCU)": "g.peak_ccu DESC, g.total_reviews DESC",
    "Highest User Score (%)": "g.review_score_pct DESC, g.total_reviews DESC",
    "Highest Metacritic Score": "COALESCE(g.metacritic_score, -1) DESC, g.wilson_score DESC",
    "Longest Playtime (Hours)": "g.avg_playtime_hours DESC, g.wilson_score DESC",
    "Best Value (Hours per $)": "COALESCE(g.hours_per_dollar, -1) DESC, g.wilson_score DESC",
    "Newest Releases": "g.release_year DESC, g.release_date DESC, g.wilson_score DESC",
    "Price: Low to High": "g.price ASC, g.wilson_score DESC",
}


@dataclass
class GameFilterParams:
    """Filter state passed from the dashboard UI to the SQL query builder."""

    studio_tiers: list[str] = field(default_factory=list)  # e.g. ['Indie'], ['AA', 'AAA']
    indie_mode: str = "All Games"  # 'All Games', 'Indie Only', 'Studio (AA & AAA)'
    genres: list[str] = field(default_factory=list)
    player_modes: list[str] = field(default_factory=list)
    max_price: float | None = None
    free_only: bool = False
    min_playtime_hours: float = 0.0
    max_playtime_hours: float | None = None
    playtime_tiers: list[str] = field(default_factory=list)
    min_review_score_pct: float = 0.0
    min_total_reviews: int = 50
    min_metacritic: int = 0
    release_year_range: tuple[int, int] = (1995, 2026)
    search_query: str = ""


def get_readonly_connection(db_path: Path = SQLITE_DB_PATH) -> sqlite3.Connection:
    """Open SQLite database in strict read-only URI mode (?mode=ro)."""
    uri = f"file:{db_path.resolve()}?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def format_sql_for_display(sql: str, params: list[Any]) -> str:
    """
    Create a human-readable SQL string with bound parameter values substituted ONLY for UI display.
    Actual execution always uses parameterized `cursor.execute(sql, params)`.
    """
    display_sql = sql.strip()
    for p in params:
        if p is None:
            val_str = "NULL"
        elif isinstance(p, str):
            escaped = p.replace("'", "''")
            val_str = f"'{escaped}'"
        else:
            val_str = str(p)
        display_sql = display_sql.replace("?", val_str, 1)
    return display_sql


def build_where_clause(filters: GameFilterParams) -> tuple[str, list[Any]]:
    """Construct a parameterized SQL WHERE clause and parameter list from GameFilterParams."""
    clauses: list[str] = ["1 = 1"]
    params: list[Any] = []

    # 1. Dedicated Indie / Studio Tier filters
    if filters.indie_mode == "Indie Only":
        clauses.append("g.is_indie = ?")
        params.append(1)
    elif filters.indie_mode == "Studio (AA & AAA)":
        clauses.append("g.is_indie = ?")
        params.append(0)

    if filters.studio_tiers:
        placeholders = ", ".join(["?"] * len(filters.studio_tiers))
        clauses.append(f"g.studio_tier IN ({placeholders})")
        params.extend(filters.studio_tiers)

    # 2. Gameplay Genres filter via normalized bridge table game_genres
    if filters.genres:
        placeholders = ", ".join(["?"] * len(filters.genres))
        clauses.append(
            f"""EXISTS (
        SELECT 1 FROM game_genres gg
        WHERE gg.app_id = g.app_id AND gg.genre IN ({placeholders})
    )"""
        )
        params.extend(filters.genres)

    # 3. Player Modes filter via normalized bridge table game_modes
    if filters.player_modes:
        placeholders = ", ".join(["?"] * len(filters.player_modes))
        clauses.append(
            f"""EXISTS (
        SELECT 1 FROM game_modes gm
        WHERE gm.app_id = g.app_id AND gm.mode IN ({placeholders})
    )"""
        )
        params.extend(filters.player_modes)

    # 4. Price & Free-to-Play filters
    if filters.free_only:
        clauses.append("g.is_free = ?")
        params.append(1)
    elif filters.max_price is not None:
        clauses.append("g.price <= ?")
        params.append(float(filters.max_price))

    # 5. Playtime hours & Playtime Tier filters
    if filters.min_playtime_hours > 0:
        clauses.append("g.avg_playtime_hours >= ?")
        params.append(float(filters.min_playtime_hours))
    if filters.max_playtime_hours is not None:
        clauses.append("g.avg_playtime_hours <= ?")
        params.append(float(filters.max_playtime_hours))
    if filters.playtime_tiers:
        placeholders = ", ".join(["?"] * len(filters.playtime_tiers))
        clauses.append(f"g.playtime_tier IN ({placeholders})")
        params.extend(filters.playtime_tiers)

    # 6. Review & Critic score filters
    if filters.min_review_score_pct > 0:
        clauses.append("g.review_score_pct >= ?")
        params.append(float(filters.min_review_score_pct))
    if filters.min_total_reviews > 50:
        clauses.append("g.total_reviews >= ?")
        params.append(int(filters.min_total_reviews))
    if filters.min_metacritic > 0:
        clauses.append("g.metacritic_score >= ?")
        params.append(int(filters.min_metacritic))

    # 7. Release Year range
    start_yr, end_yr = filters.release_year_range
    if start_yr > 1995 or end_yr < 2026:
        clauses.append("g.release_year BETWEEN ? AND ?")
        params.extend([int(start_yr), int(end_yr)])

    # 8. Text search (Game title or Developer)
    if filters.search_query and filters.search_query.strip():
        q = f"%{filters.search_query.strip()}%"
        clauses.append("(g.name LIKE ? OR g.developers LIKE ?)")
        params.extend([q, q])

    where_sql = " AND ".join(clauses)
    return where_sql, params


def get_filter_metadata(db_path: Path = SQLITE_DB_PATH) -> dict[str, Any]:
    """Fetch distinct genres, modes, studio tiers, and numeric bounds for UI controls."""
    with get_readonly_connection(db_path) as conn:
        genres_df = pd.read_sql_query(
            """
            SELECT genre, COUNT(*) AS game_count
            FROM game_genres
            GROUP BY genre
            ORDER BY game_count DESC
            """,
            conn,
        )
        modes_df = pd.read_sql_query(
            """
            SELECT mode, COUNT(*) AS game_count
            FROM game_modes
            GROUP BY mode
            ORDER BY game_count DESC
            """,
            conn,
        )
        tiers_df = pd.read_sql_query(
            """
            SELECT studio_tier, COUNT(*) AS game_count
            FROM games
            GROUP BY studio_tier
            ORDER BY game_count DESC
            """,
            conn,
        )
        bounds_df = pd.read_sql_query(
            """
            SELECT
                MIN(release_year) AS min_year,
                MAX(release_year) AS max_year,
                MAX(price) AS max_price,
                COUNT(*) AS total_games
            FROM games
            """,
            conn,
        )

    return {
        "genres": genres_df["genre"].tolist(),
        "genre_counts": dict(zip(genres_df["genre"], genres_df["game_count"])),
        "player_modes": modes_df["mode"].tolist(),
        "studio_tiers": ["Indie", "AA", "AAA"],
        "studio_tier_counts": dict(zip(tiers_df["studio_tier"], tiers_df["game_count"])),
        "playtime_tiers": ["Quick (<5h)", "Medium (5-20h)", "Long (20-50h)", "Endless (50h+)"],
        "min_year": int(bounds_df["min_year"].iloc[0]),
        "max_year": int(bounds_df["max_year"].iloc[0]),
        "total_games": int(bounds_df["total_games"].iloc[0]),
    }


def query_kpi_summary(
    filters: GameFilterParams,
    db_path: Path = SQLITE_DB_PATH,
) -> tuple[dict[str, Any], str]:
    """Execute SQL aggregation for top-level dashboard KPI cards."""
    where_sql, params = build_where_clause(filters)
    sql = f"""
SELECT
    COUNT(*) AS matching_games,
    ROUND(AVG(g.is_indie) * 100.0, 1) AS indie_share_pct,
    ROUND(AVG(g.review_score_pct), 1) AS avg_review_score_pct,
    ROUND(AVG(g.metacritic_score), 1) AS avg_metacritic_score,
    ROUND(AVG(g.price), 2) AS avg_price,
    ROUND(AVG(g.avg_playtime_hours), 1) AS avg_playtime_hours,
    ROUND(AVG(g.hours_per_dollar), 2) AS avg_hours_per_dollar
FROM games g
WHERE {where_sql};
""".strip()

    with get_readonly_connection(db_path) as conn:
        df = pd.read_sql_query(sql, conn, params=params)

    row = df.iloc[0].to_dict() if not df.empty else {}
    return row, format_sql_for_display(sql, params)


def query_games_explorer(
    filters: GameFilterParams,
    sort_by: str = "Best Rated (Wilson Score)",
    limit: int = 60,
    db_path: Path = SQLITE_DB_PATH,
) -> tuple[pd.DataFrame, str]:
    """
    Execute SQL query for Feature 1 ('Find My Next Game' Visual Explorer)
    and Feature 2 (Value vs. Reception Scatter Plot).
    """
    where_sql, params = build_where_clause(filters)
    order_clause = SORT_COLUMNS.get(sort_by, SORT_COLUMNS["Best Rated (Wilson Score)"])
    query_params = [*params, int(limit)]

    sql = f"""
SELECT
    g.app_id,
    g.name,
    g.release_year,
    g.studio_tier,
    g.is_indie,
    g.price,
    g.is_free,
    g.total_reviews,
    g.review_score_pct,
    g.wilson_score,
    g.steam_rating_tier,
    g.metacritic_score,
    g.avg_playtime_hours,
    g.median_playtime_hours,
    g.playtime_tier,
    g.hours_per_dollar,
    g.estimated_owners_label,
    g.estimated_owners_mid,
    g.peak_ccu,
    g.primary_genre,
    g.genres_str,
    g.player_modes_str,
    g.developers,
    g.publishers,
    g.short_description,
    g.header_image
FROM games g
WHERE {where_sql}
ORDER BY {order_clause}
LIMIT ?;
""".strip()

    with get_readonly_connection(db_path) as conn:
        df = pd.read_sql_query(sql, conn, params=query_params)

    return df, format_sql_for_display(sql, query_params)


def query_genre_landscape(
    filters: GameFilterParams,
    db_path: Path = SQLITE_DB_PATH,
) -> tuple[pd.DataFrame, str]:
    """
    Execute SQL JOIN + GROUP BY query for Feature 3 (Genre & Studio Market Landscape).
    Aggregates game count, review scores, playtime, value, and Indie % across gameplay genres.
    """
    where_sql, params = build_where_clause(filters)
    sql = f"""
SELECT
    gg.genre AS genre,
    COUNT(DISTINCT g.app_id) AS game_count,
    ROUND(AVG(g.review_score_pct), 1) AS avg_review_score_pct,
    ROUND(AVG(g.wilson_score), 1) AS avg_wilson_score,
    ROUND(AVG(g.metacritic_score), 1) AS avg_metacritic_score,
    ROUND(AVG(g.avg_playtime_hours), 1) AS avg_playtime_hours,
    ROUND(AVG(g.price), 2) AS avg_price,
    ROUND(AVG(g.hours_per_dollar), 2) AS avg_hours_per_dollar,
    ROUND(AVG(g.is_indie) * 100.0, 1) AS indie_share_pct,
    SUM(g.peak_ccu) AS total_peak_ccu
FROM games g
INNER JOIN game_genres gg ON g.app_id = gg.app_id
WHERE {where_sql}
GROUP BY gg.genre
HAVING COUNT(DISTINCT g.app_id) >= 5
ORDER BY game_count DESC;
""".strip()

    with get_readonly_connection(db_path) as conn:
        df = pd.read_sql_query(sql, conn, params=params)

    return df, format_sql_for_display(sql, params)


def query_studio_tier_comparison(
    filters: GameFilterParams,
    db_path: Path = SQLITE_DB_PATH,
) -> tuple[pd.DataFrame, str]:
    """
    Execute SQL GROUP BY studio_tier ('Indie', 'AA', 'AAA') to compare
    pricing, player reception, playtime, and value across Indie vs AA vs AAA games.
    """
    where_sql, params = build_where_clause(filters)
    sql = f"""
SELECT
    g.studio_tier,
    COUNT(*) AS game_count,
    ROUND(AVG(g.price), 2) AS avg_price,
    ROUND(AVG(g.review_score_pct), 1) AS avg_review_score_pct,
    ROUND(AVG(g.metacritic_score), 1) AS avg_metacritic_score,
    ROUND(AVG(g.avg_playtime_hours), 1) AS avg_playtime_hours,
    ROUND(AVG(g.hours_per_dollar), 2) AS avg_hours_per_dollar,
    SUM(g.peak_ccu) AS total_peak_ccu
FROM games g
WHERE {where_sql}
GROUP BY g.studio_tier
ORDER BY
    CASE g.studio_tier
        WHEN 'Indie' THEN 1
        WHEN 'AA' THEN 2
        WHEN 'AAA' THEN 3
        ELSE 4
    END;
""".strip()

    with get_readonly_connection(db_path) as conn:
        df = pd.read_sql_query(sql, conn, params=params)

    return df, format_sql_for_display(sql, params)
