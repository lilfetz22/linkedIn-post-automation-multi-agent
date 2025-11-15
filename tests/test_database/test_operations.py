import os
import sys
from pathlib import Path

# Add project root to sys.path for imports
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sqlite3
from time import sleep

from database.init_db import init_db, seed_potential_topics, DEFAULT_SEED_ROWS, DEFAULT_FIELD_DS, DEFAULT_FIELD_GAI
from database.operations import get_recent_topics, record_posted_topic, select_new_topic


def _all_previous_topics(db_path):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT topic_name, date_posted FROM previous_topics ORDER BY id ASC;")
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
    ds_topic = next(name for name, field in DEFAULT_SEED_ROWS if field == DEFAULT_FIELD_DS)
    record_posted_topic(ds_topic, db_path=db_path)

    # Should select a DS topic that is not the recently posted one
    sel = select_new_topic(DEFAULT_FIELD_DS, recent_limit=10, db_path=db_path)
    assert sel is not None
    assert sel["topic"] != ds_topic

    # For GAI field, should select the smallest id among GAI topics (deterministic)
    sel_gai = select_new_topic(DEFAULT_FIELD_GAI, recent_limit=10, db_path=db_path)
    assert sel_gai is not None
    # Ensure it comes from GAI set
    gai_topics = [name for name, field in DEFAULT_SEED_ROWS if field == DEFAULT_FIELD_GAI]
    assert sel_gai["topic"] in gai_topics
