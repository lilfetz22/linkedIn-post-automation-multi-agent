import os
import sys
from pathlib import Path

# Add project root to sys.path for imports
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sqlite3
from time import sleep

from database.init_db import (
    init_db,
    seed_potential_topics,
    DEFAULT_SEED_ROWS,
    DEFAULT_FIELD_DS,
    DEFAULT_FIELD_GAI,
)
from database.operations import get_recent_topics, record_posted_topic, select_new_topic


def _all_previous_topics(db_path):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT topic_name, date_posted FROM previous_topics ORDER BY id ASC;"
        )
        return cur.fetchall()
    finally:
        conn.close()


def test_record_and_get_recent_ordering(tmp_path):
    db_path = os.path.join(tmp_path, "topics.db")
    init_db(db_path)

    record_posted_topic("A", db_path=db_path)
    sleep(0.01)
    record_posted_topic("B", db_path=db_path)
    sleep(0.01)
    record_posted_topic("C", db_path=db_path)

    recent = get_recent_topics(limit=2, db_path=db_path)
    assert recent == ["C", "B"]

    all_rows = _all_previous_topics(db_path)
    assert len(all_rows) == 3
    assert all_rows[0][0] == "A"


def test_select_new_topic_excludes_recent_and_filters_by_field(tmp_path):
    db_path = os.path.join(tmp_path, "topics.db")
    init_db(db_path)

    # Seed topics for both fields
    seed_potential_topics(DEFAULT_SEED_ROWS, db_path)

    # Pick one DS topic as recently posted
    ds_topic = next(
        name for name, field in DEFAULT_SEED_ROWS if field == DEFAULT_FIELD_DS
    )
    record_posted_topic(ds_topic, db_path=db_path)

    # Should select a DS topic that is not the recently posted one
    sel = select_new_topic(DEFAULT_FIELD_DS, recent_limit=10, db_path=db_path)
    assert sel is not None
    assert sel["topic"] != ds_topic

    # For GAI field, should select the smallest id among GAI topics (deterministic)
    sel_gai = select_new_topic(DEFAULT_FIELD_GAI, recent_limit=10, db_path=db_path)
    assert sel_gai is not None
    # Ensure it comes from GAI set
    gai_topics = [
        name for name, field in DEFAULT_SEED_ROWS if field == DEFAULT_FIELD_GAI
    ]
    assert sel_gai["topic"] in gai_topics


def test_record_posted_topic_iso_date_format(tmp_path):
    """Verify record_posted_topic writes ISO8601 formatted dates."""
    db_path = os.path.join(tmp_path, "topics.db")
    init_db(db_path)

    # Record without explicit date (should use ISO8601 UTC)
    record_posted_topic("Test Topic", db_path=db_path)

    all_rows = _all_previous_topics(db_path)
    assert len(all_rows) == 1
    topic_name, date_posted = all_rows[0]
    assert topic_name == "Test Topic"
    # Check ISO8601 format: YYYY-MM-DDTHH:MM:SSZ
    assert "T" in date_posted
    assert date_posted.endswith("Z")

    # Record with explicit date
    custom_date = "2024-01-15T12:30:45Z"
    record_posted_topic("Another Topic", date_posted=custom_date, db_path=db_path)

    all_rows = _all_previous_topics(db_path)
    assert len(all_rows) == 2
    assert all_rows[1][1] == custom_date


def test_all_functions_accept_db_path_override(tmp_path):
    """Verify all database operations accept db_path parameter for test isolation."""
    db_path1 = os.path.join(tmp_path, "db1.db")
    db_path2 = os.path.join(tmp_path, "db2.db")

    # Initialize two separate databases
    init_db(db_path1)
    init_db(db_path2)

    # Seed only db1
    seed_potential_topics(DEFAULT_SEED_ROWS, db_path1)

    # Record topic in db1
    record_posted_topic("Topic in DB1", db_path=db_path1)

    # Verify db1 has data
    recent1 = get_recent_topics(limit=10, db_path=db_path1)
    assert len(recent1) == 1
    assert recent1[0] == "Topic in DB1"

    # Verify db2 is empty
    recent2 = get_recent_topics(limit=10, db_path=db_path2)
    assert len(recent2) == 0

    # Verify select_new_topic works with both
    sel1 = select_new_topic(DEFAULT_FIELD_DS, recent_limit=10, db_path=db_path1)
    assert sel1 is not None  # Has seeded topics

    sel2 = select_new_topic(DEFAULT_FIELD_DS, recent_limit=10, db_path=db_path2)
    assert sel2 is None  # No seeded topics
