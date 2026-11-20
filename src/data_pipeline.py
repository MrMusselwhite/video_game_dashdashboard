"""
Phase 1: Steam Games Data Cleaning & Anti-Shovelware Pipeline
Transforms raw Steam parquet metadata into a normalized SQLite database (data/steam_games.db).
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_PARQUET_PATH = PROJECT_ROOT / "data" / "raw_steam_games.parquet"
SQLITE_DB_PATH = PROJECT_ROOT / "data" / "steam_games.db"

# Non-game software genres on Steam to exclude from core video game genres
NON_GAME_GENRES = {
    "Utilities",
    "Design & Illustration",
    "Animation & Modeling",
    "Video Production",
    "Audio Production",
    "Software Training",
    "Photo Editing",
    "Web Publishing",
    "Accounting",
    "Game Development",
    "Movie",
    "Documentary",
    "Short",
    "Tutorial",
    "360 Video",
}

# Genres that describe studio type, pricing/release state, or content descriptors rather than gameplay genre
NON_GAMEPLAY_GENRE_TAGS = {
    "Indie",
    "Free To Play",
    "Early Access",
    "Violent",
    "Gore",
    "Nudity",
    "Sexual Content",
}

# Curated player modes / features from Steam categories
KEY_PLAYER_MODES = [
    "Single-player",
    "Multi-player",
    "Co-op",
    "Online Co-op",
    "LAN Co-op",
    "Shared/Split Screen Co-op",
    "PvP",
    "Online PvP",
    "Shared/Split Screen PvP",
    "Shared/Split Screen",
    "Cross-Platform Multiplayer",
    "Full controller support",
    "Steam Workshop",
    "Steam Achievements",
    "Steam Cloud",
]

# Major AAA Publishers & First-Party Studios
AAA_PUBLISHER_PATTERN = re.compile(
    r"electronic arts|ubisoft|square enix|sega|2k|rockstar games|activision|blizzard|"
    r"bethesda|bandai namco|xbox game studios|microsoft studios|playstation publishing|sony interactive|"
    r"capcom|konami|valve|warner bros|wb games|cd projekt|larian|fromsoftware|bungie|"
    r"take-two|lucasarts|bioware|koei tecmo|krafton|tencent|netease|hoyoverse|mihoyo|"
    r"nexon|ncsoft|amazon games|ea sports|2k sports|disney|game science|embark studios|riot games|epic games",
    re.IGNORECASE,
)

# Mid-Tier (AA) Publishers & Studios
AA_PUBLISHER_PATTERN = re.compile(
    r"thq nordic|focus entertainment|focus home|paradox interactive|deep silver|nacon|"
    r"505 games|kalypso|nis america|spike chunsoft|slitherine|milestone|arc system works|"
    r"rebellion|funcom|starbreeze|dontnod|frogwares|marvelous|xseed|atlus|idea factory|"
    r"falcom|compile heart|aquaplus|aksys|daedalic|microids|tripwire|saber interactive|"
    r"techland|ci games|bohemia interactive|astragon|aerosoft|giants software|"
    r"frontier developments|codemasters|snk|behaviour interactive|gaijin|digital extremes|"
    r"coffee stain|team17|devolver digital|annapurna interactive|hooded horse|tinybuild",
    re.IGNORECASE,
)

# Anti-shovelware threshold constants
MIN_TOTAL_REVIEWS = 50
MIN_AVG_PLAYTIME_MINUTES = 10


def compute_wilson_score(positive: pd.Series, total: pd.Series, z: float = 1.96) -> pd.Series:
    """
    Calculate the lower bound of Wilson score confidence interval for a Bernoulli parameter.
    Used by SteamDB to rank games fairly by balancing positive ratio with review volume.
    """
    n = total.astype(float)
    p_hat = np.where(n > 0, positive.astype(float) / n, 0.0)
    z2 = z * z
    numerator = (
        p_hat
        + (z2 / (2.0 * n))
        - z * np.sqrt((p_hat * (1.0 - p_hat) + z2 / (4.0 * n)) / n)
    )
    denominator = 1.0 + (z2 / n)
    return np.round((numerator / denominator) * 100.0, 2)


def classify_steam_rating_tier(total_reviews: int, review_score_pct: float) -> str:
    """Assign official Steam store review tier labels."""
    if total_reviews >= 500 and review_score_pct >= 95.0:
        return "Overwhelmingly Positive"
    if total_reviews >= 50 and review_score_pct >= 80.0:
        return "Very Positive"
    if review_score_pct >= 70.0:
        return "Mostly Positive"
    if review_score_pct >= 40.0:
        return "Mixed"
    if total_reviews >= 500 and review_score_pct < 20.0:
        return "Overwhelmingly Negative"
    if review_score_pct < 40.0:
        return "Mostly Negative"
    return "Mixed"


def classify_playtime_tier(hours: float) -> str:
    """Group average playtime into intuitive discovery buckets."""
    if hours < 5.0:
        return "Quick (<5h)"
    if hours < 20.0:
        return "Medium (5-20h)"
    if hours < 50.0:
        return "Long (20-50h)"
    return "Endless (50h+)"


def parse_owners_midpoint(owners_str: str) -> int:
    """Convert SteamSpy owner range string (e.g., '200000 - 500000') to integer midpoint."""
    if not isinstance(owners_str, str) or "-" not in owners_str:
        return 0
    parts = [p.strip().replace(",", "") for p in owners_str.split("-")]
    try:
        low, high = int(parts[0]), int(parts[1])
        return (low + high) // 2
    except (ValueError, IndexError):
        return 0


def extract_gameplay_genres(raw_genres: Iterable[str] | None) -> list[str]:
    """
    Filter out non-game software categories and non-gameplay tags ('Indie', 'Free To Play', etc.)
    so the genre filter contains pure gameplay genres (Action, RPG, Strategy, etc.).
    """
    if raw_genres is None or not hasattr(raw_genres, "__iter__"):
        return []
    raw_list = [str(g).strip() for g in raw_genres if str(g).strip()]
    # If all genres are non-game software genres, return empty list so the row is excluded
    game_candidates = [g for g in raw_list if g not in NON_GAME_GENRES]
    if not game_candidates:
        return []
    gameplay_only = [g for g in game_candidates if g not in NON_GAMEPLAY_GENRE_TAGS]
    if gameplay_only:
        return gameplay_only
    # Fallback if a game was only tagged 'Indie' or 'Free To Play' with no other genre
    return ["Casual"]


def classify_studio_tier(
    has_indie_tag: bool,
    developers_str: str,
    publishers_str: str,
    price: float,
    total_reviews: int,
) -> str:
    """
    Classify a game into 'Indie', 'AA', or 'AAA' based on Steam's Indie tag,
    publisher/developer pedigree, pricing, and commercial scale.
    """
    pub_dev_text = f"{publishers_str} | {developers_str}"
    is_aaa_studio = bool(AAA_PUBLISHER_PATTERN.search(pub_dev_text))
    is_aa_studio = bool(AA_PUBLISHER_PATTERN.search(publishers_str))

    # 1. AAA: Major publisher/studio (without Indie tag, or premium price >= $39.99),
    # or full-price ($49.99+) non-indie release, or massive non-indie blockbuster
    if (is_aaa_studio and not has_indie_tag) or (is_aaa_studio and price >= 39.99):
        return "AAA"
    if not has_indie_tag and price >= 49.99:
        return "AAA"
    if not has_indie_tag and total_reviews >= 30000 and price >= 29.99:
        return "AAA"

    # 2. AA: Mid-tier publisher, or non-Indie tagged studio game
    if is_aa_studio and not has_indie_tag:
        return "AA"
    if not has_indie_tag:
        # Self-published lower-priced games that simply omitted the 'Indie' tag (e.g. Among Us, Bloons TD 6)
        if (
            developers_str != "Unknown"
            and developers_str.lower() == publishers_str.lower()
            and price < 25.0
            and not is_aa_studio
            and not is_aaa_studio
        ):
            return "Indie"
        return "AA"

    # 3. Games with 'Indie' tag that are priced in the AA tier ($39.99+)
    if has_indie_tag and price >= 39.99:
        return "AA"

    return "Indie"


def resolve_price_and_free_flag(
    raw_price: float,
    raw_genres: Iterable[str] | None,
    raw_packages: str | None,
) -> tuple[float | None, int]:
    """
    Distinguish genuinely Free-to-Play games from delisted/replaced paid games whose
    Steam API price defaulted to 0.0 during scraping.

    Returns (cleaned_price_or_None, is_free_flag):
      - Paid games (> $0): (price, 0)
      - Tagged 'Free To Play': (0.0, 1)
      - $0.00 without 'Free To Play' tag:
          1) Recover lowest paid price from packages JSON if available.
          2) If a package explicitly says 'Free' (e.g. Artifact), mark (0.0, 1).
          3) Otherwise treat as delisted/unavailable: (None, 0) so SQL AVG(price)
             and 'Free-to-Play Only' filters stay accurate.
    """
    price_val = float(raw_price) if pd.notna(raw_price) else 0.0
    if price_val > 0.0:
        return round(price_val, 2), 0

    has_f2p_genre = (
        any(str(g).strip() == "Free To Play" for g in raw_genres)
        if raw_genres is not None and hasattr(raw_genres, "__iter__")
        else False
    )
    if has_f2p_genre:
        return 0.0, 1

    if isinstance(raw_packages, str) and len(raw_packages) > 2:
        try:
            pkgs = json.loads(raw_packages)
            paid_prices: list[float] = []
            has_explicit_free_sub = False
            for pkg in pkgs:
                for sub in pkg.get("subs", []):
                    sub_price = sub.get("price")
                    sub_text = str(sub.get("text", ""))
                    if isinstance(sub_price, (int, float)) and sub_price > 0:
                        paid_prices.append(float(sub_price))
                    elif (
                        "free" in sub_text.lower()
                        and not any(
                            excl in sub_text.lower()
                            for excl in ("ea play", "ubisoft+", "subscription", "trial", "demo", "episode 1")
                        )
                        and (sub_price == 0 or sub_price == 0.0)
                    ):
                        has_explicit_free_sub = True
            if paid_prices:
                return round(min(paid_prices), 2), 0
            if has_explicit_free_sub:
                return 0.0, 1
        except (ValueError, TypeError):
            pass

    return None, 0


def join_array_field(val: Iterable[str] | None, max_items: int = 3) -> str:
    """Convert numpy array / list of strings into a comma-separated string."""
    if val is None or not hasattr(val, "__iter__"):
        return "Unknown"
    items = [str(x).strip() for x in val if str(x).strip()]
    if not items:
        return "Unknown"
    return ", ".join(items[:max_items])


def run_pipeline(
    parquet_path: Path = RAW_PARQUET_PATH,
    db_path: Path = SQLITE_DB_PATH,
) -> dict[str, int]:
    """Execute the full ETL pipeline and build the SQLite database."""
    print(f"Loading raw dataset from {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    raw_count = len(df)

    # 1. Calculate total reviews and basic validity flags
    df["total_reviews"] = df["positive"].fillna(0).astype(int) + df["negative"].fillna(0).astype(int)
    df["name"] = df["name"].fillna("").astype(str).str.strip()
    df["header_image"] = df["header_image"].fillna("").astype(str).str.strip()

    # 2. Anti-Shovelware & Portfolio-Safe Quality Gate
    # Exclude playtests, demos, soundtracks, dedicated servers, SDKs, benchmarks, and desktop utilities
    non_game_title_mask = df["name"].str.contains(
        r"\b(?:Playtest|Demo|Soundtrack|OST|Dedicated Server|SDK|Benchmark|Artbook|Beta Test|"
        r"Wallpaper Engine|Soundpad|Lossless Scaling|Crosshair X|VTube Studio|3DMark|"
        r"Borderless Gaming|OVR Toolkit|Virtual Desktop|RPG Maker|Aseprite|Blender|Source Filmmaker)\b",
        case=False,
        regex=True,
        na=True,
    )

    # Exclude rows that have ANY non-game utility genre (like Wallpaper Engine or video editors tagged 'Indie' + 'Utilities')
    has_utility_genre_mask = df["genres"].apply(
        lambda g: any(str(x).strip() in NON_GAME_GENRES for x in g)
        if hasattr(g, "__iter__")
        else False
    )

    # Exclude explicit NSFW / adult-only shovelware while keeping mainstream mature games
    explicit_nsfw_mask = (
        df["genres"].apply(
            lambda g: any(x in ("Sexual Content", "Nudity") for x in g)
            if hasattr(g, "__iter__")
            else False
        )
        | df["name"].str.contains(
            r"hentai|\bsex\b|waifu|nsfw|erotic|brothel|succubus|milf|lewd|ecchi|boobs",
            case=False,
            regex=True,
            na=False,
        )
        | df["notes"]
        .fillna("")
        .str.contains(
            r"hentai|explicit sexual|sexual acts|porn|nsfw|erotic|nudity and sexual content|adult only",
            case=False,
            regex=True,
            na=False,
        )
    )

    # Extract pure gameplay genres
    df["clean_genres"] = df["genres"].apply(extract_gameplay_genres)
    has_valid_genre = df["clean_genres"].apply(lambda g: len(g) > 0)

    # Apply quality gate filters
    filtered = df[
        (df["name"] != "")
        & df["header_image"].str.startswith("http")
        & (~non_game_title_mask)
        & (~has_utility_genre_mask)
        & (~explicit_nsfw_mask)
        & has_valid_genre
        & (df["total_reviews"] >= MIN_TOTAL_REVIEWS)
        & (df["average_playtime_forever"] >= MIN_AVG_PLAYTIME_MINUTES)
    ].copy()

    # Deduplicate by appID
    filtered["app_id"] = pd.to_numeric(filtered["appID"], errors="coerce")
    filtered = filtered.dropna(subset=["app_id"]).copy()
    filtered["app_id"] = filtered["app_id"].astype(int)
    filtered = filtered.sort_values("total_reviews", ascending=False).drop_duplicates(subset=["app_id"])

    # 3. Feature Engineering & Cleaning
    parsed_dates = pd.to_datetime(filtered["release_date"], format="mixed", errors="coerce")
    filtered["release_date_iso"] = parsed_dates.dt.strftime("%Y-%m-%d").fillna("Unknown")
    filtered["release_year"] = parsed_dates.dt.year.fillna(0).astype(int)
    filtered = filtered[(filtered["release_year"] >= 1995) & (filtered["release_year"] <= 2026)].copy()

    resolved_prices = [
        resolve_price_and_free_flag(p, g, pkg)
        for p, g, pkg in zip(filtered["price"], filtered["genres"], filtered["packages"])
    ]
    filtered["price"] = [rp[0] for rp in resolved_prices]
    filtered["is_free"] = [rp[1] for rp in resolved_prices]

    filtered["review_score_pct"] = (
        (filtered["positive"] / filtered["total_reviews"]) * 100.0
    ).round(1)
    filtered["wilson_score"] = compute_wilson_score(filtered["positive"], filtered["total_reviews"])
    filtered["steam_rating_tier"] = [
        classify_steam_rating_tier(tot, pct)
        for tot, pct in zip(filtered["total_reviews"], filtered["review_score_pct"])
    ]

    # Convert 0 Metacritic score to NULL (None) so SQL AVG() is accurate
    filtered["metacritic_score_clean"] = filtered["metacritic_score"].apply(
        lambda x: int(x) if pd.notna(x) and int(x) > 0 else None
    )

    # Playtime in hours
    filtered["avg_playtime_hours"] = (filtered["average_playtime_forever"] / 60.0).round(1)
    filtered["median_playtime_hours"] = (
        np.where(
            filtered["median_playtime_forever"] > 0,
            filtered["median_playtime_forever"],
            filtered["average_playtime_forever"],
        )
        / 60.0
    ).round(1)
    filtered["playtime_tier"] = filtered["avg_playtime_hours"].apply(classify_playtime_tier)

    # Value metric: hours of average playtime per dollar (for paid games >= $1 with known price)
    filtered["hours_per_dollar"] = [
        round(hrs / prc, 2) if (prc is not None and pd.notna(prc) and prc >= 1.0) else None
        for hrs, prc in zip(filtered["avg_playtime_hours"], filtered["price"])
    ]

    # Owners & Popularity
    filtered["estimated_owners_label"] = filtered["estimated_owners"].fillna("Unknown").astype(str)
    filtered["estimated_owners_mid"] = filtered["estimated_owners_label"].apply(parse_owners_midpoint)
    filtered["peak_ccu"] = filtered["peak_ccu"].fillna(0).astype(int)

    # Developers, Publishers & Studio Tier (Indie / AA / AAA)
    filtered["developers_str"] = filtered["developers"].apply(join_array_field)
    filtered["publishers_str"] = filtered["publishers"].apply(join_array_field)
    filtered["has_raw_indie_tag"] = filtered["genres"].apply(
        lambda g: "Indie" in g if hasattr(g, "__iter__") else False
    )
    filtered["studio_tier"] = [
        classify_studio_tier(indie_tag, dev, pub, float(prc) if (prc is not None and pd.notna(prc)) else 0.0, rev)
        for indie_tag, dev, pub, prc, rev in zip(
            filtered["has_raw_indie_tag"],
            filtered["developers_str"],
            filtered["publishers_str"],
            filtered["price"],
            filtered["total_reviews"],
        )
    ]
    filtered["is_indie"] = (filtered["studio_tier"] == "Indie").astype(int)

    # Gameplay Genres & Categories
    filtered["primary_genre"] = filtered["clean_genres"].apply(lambda g: g[0] if g else "Action")
    filtered["genres_str"] = filtered["clean_genres"].apply(lambda g: ", ".join(g[:4]))

    def extract_modes(cats: Iterable[str] | None) -> list[str]:
        if cats is None or not hasattr(cats, "__iter__"):
            return []
        cat_set = {str(c).strip() for c in cats}
        return [m for m in KEY_PLAYER_MODES if m in cat_set]

    filtered["clean_modes"] = filtered["categories"].apply(extract_modes)
    filtered["player_modes_str"] = filtered["clean_modes"].apply(
        lambda m: ", ".join(m[:3]) if m else "Single-player"
    )

    filtered["is_singleplayer"] = filtered["clean_modes"].apply(lambda m: int("Single-player" in m))
    filtered["is_multiplayer"] = filtered["clean_modes"].apply(
        lambda m: int("Multi-player" in m or "PvP" in m or "Online PvP" in m)
    )
    filtered["is_coop"] = filtered["clean_modes"].apply(
        lambda m: int("Co-op" in m or "Online Co-op" in m or "Shared/Split Screen Co-op" in m)
    )
    filtered["has_controller_support"] = filtered["clean_modes"].apply(
        lambda m: int("Full controller support" in m)
    )

    filtered["short_description_clean"] = (
        filtered["short_description"]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.slice(0, 240)
    )

    # 4. Prepare Normalized DataFrames for SQLite
    games_columns = [
        "app_id",
        "name",
        "release_date_iso",
        "release_year",
        "studio_tier",
        "is_indie",
        "price",
        "is_free",
        "positive",
        "negative",
        "total_reviews",
        "review_score_pct",
        "wilson_score",
        "steam_rating_tier",
        "metacritic_score_clean",
        "avg_playtime_hours",
        "median_playtime_hours",
        "playtime_tier",
        "hours_per_dollar",
        "estimated_owners_label",
        "estimated_owners_mid",
        "peak_ccu",
        "primary_genre",
        "genres_str",
        "player_modes_str",
        "is_singleplayer",
        "is_multiplayer",
        "is_coop",
        "has_controller_support",
        "developers_str",
        "publishers_str",
        "short_description_clean",
        "header_image",
        "windows",
        "mac",
        "linux",
    ]

    games_df = filtered[games_columns].rename(
        columns={
            "release_date_iso": "release_date",
            "metacritic_score_clean": "metacritic_score",
            "developers_str": "developers",
            "publishers_str": "publishers",
            "short_description_clean": "short_description",
        }
    )
    games_df["windows"] = games_df["windows"].astype(int)
    games_df["mac"] = games_df["mac"].astype(int)
    games_df["linux"] = games_df["linux"].astype(int)

    # Bridge table 1: game_genres (app_id, genre)
    genre_rows = []
    for app_id, g_list in zip(filtered["app_id"], filtered["clean_genres"]):
        for g in dict.fromkeys(g_list):
            genre_rows.append((int(app_id), g))
    game_genres_df = pd.DataFrame(genre_rows, columns=["app_id", "genre"])

    # Bridge table 2: game_modes (app_id, mode)
    mode_rows = []
    for app_id, m_list in zip(filtered["app_id"], filtered["clean_modes"]):
        for m in dict.fromkeys(m_list):
            mode_rows.append((int(app_id), m))
    game_modes_df = pd.DataFrame(mode_rows, columns=["app_id", "mode"])

    # 5. Write to SQLite with explicit schema & indexes
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE games (
                app_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                release_date TEXT,
                release_year INTEGER,
                studio_tier TEXT NOT NULL,
                is_indie INTEGER NOT NULL,
                price REAL,
                is_free INTEGER NOT NULL,
                positive INTEGER NOT NULL,
                negative INTEGER NOT NULL,
                total_reviews INTEGER NOT NULL,
                review_score_pct REAL NOT NULL,
                wilson_score REAL NOT NULL,
                steam_rating_tier TEXT NOT NULL,
                metacritic_score INTEGER,
                avg_playtime_hours REAL NOT NULL,
                median_playtime_hours REAL NOT NULL,
                playtime_tier TEXT NOT NULL,
                hours_per_dollar REAL,
                estimated_owners_label TEXT,
                estimated_owners_mid INTEGER NOT NULL,
                peak_ccu INTEGER NOT NULL,
                primary_genre TEXT NOT NULL,
                genres_str TEXT NOT NULL,
                player_modes_str TEXT NOT NULL,
                is_singleplayer INTEGER NOT NULL,
                is_multiplayer INTEGER NOT NULL,
                is_coop INTEGER NOT NULL,
                has_controller_support INTEGER NOT NULL,
                developers TEXT,
                publishers TEXT,
                short_description TEXT,
                header_image TEXT NOT NULL,
                windows INTEGER NOT NULL,
                mac INTEGER NOT NULL,
                linux INTEGER NOT NULL
            );

            CREATE TABLE game_genres (
                app_id INTEGER NOT NULL,
                genre TEXT NOT NULL,
                PRIMARY KEY (app_id, genre),
                FOREIGN KEY (app_id) REFERENCES games(app_id)
            );

            CREATE TABLE game_modes (
                app_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                PRIMARY KEY (app_id, mode),
                FOREIGN KEY (app_id) REFERENCES games(app_id)
            );
            """
        )

        games_df.to_sql("games", conn, if_exists="append", index=False)
        game_genres_df.to_sql("game_genres", conn, if_exists="append", index=False)
        game_modes_df.to_sql("game_modes", conn, if_exists="append", index=False)

        conn.executescript(
            """
            CREATE INDEX idx_games_studio_tier ON games(studio_tier);
            CREATE INDEX idx_games_is_indie ON games(is_indie);
            CREATE INDEX idx_games_review_score ON games(review_score_pct DESC);
            CREATE INDEX idx_games_wilson_score ON games(wilson_score DESC);
            CREATE INDEX idx_games_total_reviews ON games(total_reviews DESC);
            CREATE INDEX idx_games_price ON games(price);
            CREATE INDEX idx_games_playtime ON games(avg_playtime_hours);
            CREATE INDEX idx_games_release_year ON games(release_year);
            CREATE INDEX idx_games_primary_genre ON games(primary_genre);
            CREATE INDEX idx_game_genres_genre ON game_genres(genre, app_id);
            CREATE INDEX idx_game_modes_mode ON game_modes(mode, app_id);
            ANALYZE;
            VACUUM;
            """
        )

    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"Raw rows:          {raw_count:,}")
    print(f"Cleaned games:     {len(games_df):,}")
    print(f"Studio Tiers:      {games_df['studio_tier'].value_counts().to_dict()}")
    print(f"Genre mappings:    {len(game_genres_df):,}")
    print(f"Mode mappings:     {len(game_modes_df):,}")
    print(f"SQLite DB size:    {db_size_mb:.2f} MB ({db_path})")

    return {
        "raw_count": raw_count,
        "clean_games": len(games_df),
        "genre_rows": len(game_genres_df),
        "mode_rows": len(game_modes_df),
    }


if __name__ == "__main__":
    run_pipeline()
