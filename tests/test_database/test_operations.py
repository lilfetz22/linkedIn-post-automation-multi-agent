import os
import sqlite3
from time import sleep

from database.init_db import (
    init_db,
    seed_potential_topics,
    DEFAULT_SEED_ROWS,
    DEFAULT_FIELD_DS,
    DEFAULT_FIELD_GAI,
)
from database.operations import (
    get_recent_topics,
    record_posted_topic,
    select_new_topic,
    get_all_used_topics,
    bulk_insert_topics,
)


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


def test_get_all_used_topics(tmp_path):
    """Test get_all_used_topics returns only used topics for a field."""
    db_path = os.path.join(tmp_path, "topics.db")
    init_db(db_path)
    seed_potential_topics(DEFAULT_SEED_ROWS, db_path)

    # Get all used topics for DS field
    used = get_all_used_topics(DEFAULT_FIELD_DS, db_path=db_path)

    # Initially all should be unused, so empty list
    assert used == []

    # Select a topic (marks it as used)
    sel = select_new_topic(DEFAULT_FIELD_DS, db_path=db_path)
    assert sel is not None

    # Now get_all_used_topics should return the selected topic
    used = get_all_used_topics(DEFAULT_FIELD_DS, db_path=db_path)
    assert len(used) == 1
    assert used[0] == sel["topic"]

    # Select another
    sel2 = select_new_topic(DEFAULT_FIELD_DS, db_path=db_path)
    assert sel2 is not None
    assert sel2["topic"] != sel["topic"]

    # Should have 2 used topics
    used = get_all_used_topics(DEFAULT_FIELD_DS, db_path=db_path)
    assert len(used) == 2


def test_get_all_used_topics_filters_by_field(tmp_path):
    """Test get_all_used_topics only returns topics for requested field."""
    db_path = os.path.join(tmp_path, "topics.db")
    init_db(db_path)
    seed_potential_topics(DEFAULT_SEED_ROWS, db_path)

    # Use a DS topic
    select_new_topic(DEFAULT_FIELD_DS, db_path=db_path)

    # Use a GAI topic
    select_new_topic(DEFAULT_FIELD_GAI, db_path=db_path)

    # Get used topics for each field
    ds_used = get_all_used_topics(DEFAULT_FIELD_DS, db_path=db_path)
    gai_used = get_all_used_topics(DEFAULT_FIELD_GAI, db_path=db_path)

    # Each should have exactly 1 used topic
    assert len(ds_used) == 1
    assert len(gai_used) == 1

    # Should be different topics
    assert ds_used[0] != gai_used[0]


def test_bulk_insert_topics(tmp_path):
    """Test bulk_insert_topics inserts multiple topics as unused."""
    db_path = os.path.join(tmp_path, "topics.db")
    init_db(db_path)

    new_topics = [
        "Topic A",
        "Topic B",
        "Topic C",
    ]

    # Insert new topics
    bulk_insert_topics(new_topics, DEFAULT_FIELD_DS, db_path=db_path)

    # Verify all are in database as unused
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT topic_name, used FROM potential_topics WHERE field = ? ORDER BY id ASC;",
            (DEFAULT_FIELD_DS,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    assert len(rows) == 3
    for i, (topic_name, used) in enumerate(rows):
        assert topic_name == new_topics[i]
        # SQLite stores FALSE as 0
        assert used == 0


def test_bulk_insert_topics_preserves_field(tmp_path):
    """Test bulk_insert_topics preserves the field."""
    db_path = os.path.join(tmp_path, "topics.db")
    init_db(db_path)

    new_topics = ["New Topic 1", "New Topic 2"]

    # Insert for DS field
    bulk_insert_topics(new_topics, DEFAULT_FIELD_DS, db_path=db_path)

    # Verify field is correct
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT field FROM potential_topics WHERE topic_name = ?;",
            ("New Topic 1",),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == DEFAULT_FIELD_DS


def test_bulk_insert_then_select_workflow(tmp_path):
    """Test the complete workflow: exhaust topics, generate and insert new ones, select from new pool."""
    db_path = os.path.join(tmp_path, "topics.db")
    init_db(db_path)

    # Create a minimal set of topics
    initial_topics = [
        ("Topic 1", DEFAULT_FIELD_DS),
        ("Topic 2", DEFAULT_FIELD_DS),
    ]
    seed_potential_topics(initial_topics, db_path)

    # Select all initial topics
    sel1 = select_new_topic(DEFAULT_FIELD_DS, db_path=db_path)
    assert sel1 is not None
    assert sel1["topic"] == "Topic 1"

    sel2 = select_new_topic(DEFAULT_FIELD_DS, db_path=db_path)
    assert sel2 is not None
    assert sel2["topic"] == "Topic 2"

    # Try to select again - now that all are exhausted, the fallback kicks in
    # and select_new_topic will try to find a used topic that's not in recent history.
    # Since we haven't recorded any topics in previous_topics, it will return
    # the first used topic (Topic 1) again
    sel3 = select_new_topic(DEFAULT_FIELD_DS, recent_limit=10, db_path=db_path)
    # With fallback behavior, it returns the first used topic since no unused ones exist
    # and there's no recent history to filter it out
    assert sel3 is not None
    assert sel3["topic"] in ["Topic 1", "Topic 2"]

    # Get all used topics
    used = get_all_used_topics(DEFAULT_FIELD_DS, db_path=db_path)
    assert len(used) == 2

    # Generate and insert new topics
    new_topics = ["Topic 3", "Topic 4", "Topic 5"]
    bulk_insert_topics(new_topics, DEFAULT_FIELD_DS, db_path=db_path)

    # Now should be able to select a new unused topic
    sel4 = select_new_topic(DEFAULT_FIELD_DS, db_path=db_path)
    assert sel4 is not None
    assert sel4["topic"] == "Topic 3"

    sel5 = select_new_topic(DEFAULT_FIELD_DS, db_path=db_path)
    assert sel5 is not None
    assert sel5["topic"] == "Topic 4"
