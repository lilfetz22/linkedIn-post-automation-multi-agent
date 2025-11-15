import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

DEFAULT_DB_PATH = os.path.join("database", "topics.db")


@contextmanager
def get_connection(db_path: str = DEFAULT_DB_PATH):
    parent = os.path.dirname(db_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
    finally:
        conn.close()


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_recent_topics(limit: int = 10, db_path: str = DEFAULT_DB_PATH) -> List[str]:
    """Return the most recent topic names, newest-first."""
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT topic_name FROM previous_topics ORDER BY date_posted DESC, id DESC LIMIT ?;",
            (limit,),
        )
        rows = cur.fetchall()
        return [r[0] for r in rows]


def record_posted_topic(
    topic_name: str, date_posted: Optional[str] = None, db_path: str = DEFAULT_DB_PATH
) -> None:
    """Insert a row into previous_topics with ISO8601 timestamp if not provided."""
    ts = date_posted or _iso_now()
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO previous_topics(topic_name, date_posted) VALUES (?, ?);",
            (topic_name, ts),
        )
        conn.commit()


def select_new_topic(
    field: str, recent_limit: int = 10, db_path: str = DEFAULT_DB_PATH
) -> Optional[dict]:
    """Select a topic from potential_topics for the given field avoiding recent topics.

    Deterministic: pick the smallest id among candidates not in the recent set.
    Returns {"topic": str} or None if none available.
    """
    recent = set(get_recent_topics(limit=recent_limit, db_path=db_path))

    with get_connection(db_path) as conn:
        cur = conn.cursor()
        if recent:
            placeholders = ",".join(["?"] * len(recent))
            query = (
                f"SELECT id, topic_name FROM potential_topics "
                f"WHERE field = ? AND topic_name NOT IN ({placeholders}) "
                f"ORDER BY id ASC LIMIT 1;"
            )
            params = (field, *sorted(recent))
        else:
            query = "SELECT id, topic_name FROM potential_topics WHERE field = ? ORDER BY id ASC LIMIT 1;"
            params = (field,)
        cur.execute(query, params)
        row = cur.fetchone()
        if not row:
            return None
        return {"topic": row[1]}
