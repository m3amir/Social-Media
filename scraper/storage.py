"""SQLite storage for scraped posts."""

import json
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime

import config

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    username TEXT NOT NULL,
    display_name TEXT,
    content TEXT NOT NULL,
    topic TEXT,
    timestamp TEXT,
    likes INTEGER DEFAULT 0,
    retweets INTEGER DEFAULT 0,
    quotes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    reply_opportunity INTEGER DEFAULT 0,
    engagement_score INTEGER DEFAULT 0,
    images TEXT DEFAULT '[]',
    scraped_at TEXT NOT NULL,
    bookmarked INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS scrape_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS credit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    api_calls INTEGER DEFAULT 0,
    tweets_read INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_posts_engagement ON posts(engagement_score DESC);
CREATE INDEX IF NOT EXISTS idx_posts_topic ON posts(topic);
CREATE INDEX IF NOT EXISTS idx_posts_scraped_at ON posts(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_bookmarked ON posts(bookmarked);
"""


@contextmanager
def _get_db():
    """Get a database connection."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialize the database schema and run migrations."""
    with _get_db() as conn:
        conn.executescript(_SCHEMA)
        # Migration: add columns if missing (upgrading from older versions)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(posts)").fetchall()}
        if "impressions" not in cols:
            conn.execute("ALTER TABLE posts ADD COLUMN impressions INTEGER DEFAULT 0")
        if "tweet_id" not in cols:
            conn.execute("ALTER TABLE posts ADD COLUMN tweet_id TEXT DEFAULT ''")
        if "reply_opportunity" not in cols:
            conn.execute("ALTER TABLE posts ADD COLUMN reply_opportunity INTEGER DEFAULT 0")
    logger.info("Database initialized at %s", config.DB_PATH)


def get_since_id(batch_name: str) -> str | None:
    """Get the newest tweet ID we've seen for a batch, for incremental fetching."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT value FROM scrape_state WHERE key = ?",
            (f"since_id:{batch_name}",),
        ).fetchone()
        return row["value"] if row else None


def set_since_id(batch_name: str, tweet_id: str):
    """Store the newest tweet ID for a batch."""
    with _get_db() as conn:
        conn.execute(
            "INSERT INTO scrape_state (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (f"since_id:{batch_name}", tweet_id),
        )


def log_credit_usage(api_calls: int, tweets_read: int):
    """Log API credit usage for tracking spend."""
    with _get_db() as conn:
        conn.execute(
            "INSERT INTO credit_log (timestamp, api_calls, tweets_read) VALUES (?, ?, ?)",
            (datetime.utcnow().isoformat(), api_calls, tweets_read),
        )


def get_credit_usage() -> dict:
    """Get credit usage summary."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(api_calls), 0) as total_calls, "
            "COALESCE(SUM(tweets_read), 0) as total_tweets, "
            "MIN(timestamp) as first_call, "
            "MAX(timestamp) as last_call "
            "FROM credit_log"
        ).fetchone()
        return dict(row) if row else {}


def save_posts(posts: list[dict]) -> int:
    """Save posts to the database. Returns count of new posts inserted."""
    inserted = 0
    with _get_db() as conn:
        for post in posts:
            try:
                conn.execute(
                    """
                    INSERT INTO posts (tweet_id, url, username, display_name, content,
                                       topic, timestamp, likes, retweets, quotes,
                                       comments, impressions, reply_opportunity,
                                       engagement_score, images, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(tweet_id) DO UPDATE SET
                        likes = excluded.likes,
                        retweets = excluded.retweets,
                        quotes = excluded.quotes,
                        comments = excluded.comments,
                        impressions = excluded.impressions,
                        reply_opportunity = excluded.reply_opportunity,
                        engagement_score = excluded.engagement_score,
                        scraped_at = excluded.scraped_at
                    """,
                    (
                        post.get("tweet_id", ""),
                        post["url"],
                        post["username"],
                        post["display_name"],
                        post["content"],
                        post.get("topic", ""),
                        post["timestamp"],
                        post["likes"],
                        post["retweets"],
                        post["quotes"],
                        post["comments"],
                        post.get("impressions", 0),
                        post.get("reply_opportunity", 0),
                        post["engagement_score"],
                        json.dumps(post.get("images", [])),
                        datetime.utcnow().isoformat(),
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                pass
    logger.info("Saved %d posts (%d new/updated)", len(posts), inserted)
    return inserted


def get_posts(
    topic: str | None = None,
    sort_by: str = "engagement_score",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    bookmarked_only: bool = False,
    search: str | None = None,
) -> list[dict]:
    """Retrieve posts with filtering and sorting."""
    allowed_sort = {"engagement_score", "likes", "retweets", "comments", "impressions", "reply_opportunity", "timestamp", "scraped_at"}
    if sort_by not in allowed_sort:
        sort_by = "engagement_score"
    order = "ASC" if order.lower() == "asc" else "DESC"

    conditions = []
    params = []

    if topic:
        conditions.append("topic = ?")
        params.append(topic)
    if bookmarked_only:
        conditions.append("bookmarked = 1")
    if search:
        conditions.append("(content LIKE ? OR username LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"SELECT * FROM posts {where} ORDER BY {sort_by} {order} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with _get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(row) for row in rows]


def get_topics() -> list[dict]:
    """Get all topics with post counts."""
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT topic, COUNT(*) as count, MAX(engagement_score) as top_score "
            "FROM posts GROUP BY topic ORDER BY count DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_stats() -> dict:
    """Get overall statistics."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as total, "
            "AVG(engagement_score) as avg_engagement, "
            "MAX(engagement_score) as max_engagement, "
            "MIN(scraped_at) as first_scraped, "
            "MAX(scraped_at) as last_scraped "
            "FROM posts"
        ).fetchone()
        stats = dict(row) if row else {}

        # Add credit usage
        credits = get_credit_usage()
        stats["api_calls"] = credits.get("total_calls", 0)
        stats["tweets_read"] = credits.get("total_tweets", 0)
        return stats


def toggle_bookmark(post_id: int) -> bool:
    """Toggle bookmark status. Returns new bookmark state."""
    with _get_db() as conn:
        row = conn.execute("SELECT bookmarked FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return False
        new_state = 0 if row["bookmarked"] else 1
        conn.execute("UPDATE posts SET bookmarked = ? WHERE id = ?", (new_state, post_id))
        return bool(new_state)


def _row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to a dict with parsed JSON fields."""
    d = dict(row)
    if "images" in d and isinstance(d["images"], str):
        d["images"] = json.loads(d["images"])
    return d
