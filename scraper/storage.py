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
    url TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    display_name TEXT,
    content TEXT NOT NULL,
    topic TEXT,
    timestamp TEXT,
    likes INTEGER DEFAULT 0,
    retweets INTEGER DEFAULT 0,
    quotes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    engagement_score INTEGER DEFAULT 0,
    images TEXT DEFAULT '[]',
    scraped_at TEXT NOT NULL,
    bookmarked INTEGER DEFAULT 0
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
    """Initialize the database schema."""
    with _get_db() as conn:
        conn.executescript(_SCHEMA)
    logger.info("Database initialized at %s", config.DB_PATH)


def save_posts(posts: list[dict]) -> int:
    """Save posts to the database. Returns count of new posts inserted."""
    inserted = 0
    with _get_db() as conn:
        for post in posts:
            try:
                conn.execute(
                    """
                    INSERT INTO posts (url, username, display_name, content, topic,
                                       timestamp, likes, retweets, quotes, comments,
                                       engagement_score, images, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        likes = excluded.likes,
                        retweets = excluded.retweets,
                        quotes = excluded.quotes,
                        comments = excluded.comments,
                        engagement_score = excluded.engagement_score,
                        scraped_at = excluded.scraped_at
                    """,
                    (
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
    allowed_sort = {"engagement_score", "likes", "retweets", "comments", "timestamp", "scraped_at"}
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
        return dict(row) if row else {}


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
