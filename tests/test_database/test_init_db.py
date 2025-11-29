import os
import sqlite3

import pytest

from database.init_db import (
    init_db,
    ensure_db_dir,
    seed_potential_topics,
    DEFAULT_SEED_ROWS,
)


def test_init_creates_tables(tmp_path):
    db_path = os.path.join(tmp_path, "topics.db")
    ensure_db_dir(db_path)
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(previous_topics);")
        prev_cols = {row[1] for row in cur.fetchall()}
        assert {"id", "topic_name", "date_posted"}.issubset(prev_cols)

        cur.execute("PRAGMA table_info(potential_topics);")
        pot_cols = {row[1] for row in cur.fetchall()}
        assert {"id", "topic_name", "field"}.issubset(pot_cols)
    finally:
        conn.close()


essential_fields = [
    "Data Science (Optimizations & Time-Series Analysis)",
    "Generative AI & AI Agents",
]


def test_seed_data_contains_all_essential_fields(tmp_path):
    db_path = os.path.join(tmp_path, "topics.db")
    init_db(db_path)
    seed_potential_topics(DEFAULT_SEED_ROWS, db_path)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT field FROM potential_topics;")
        present_fields = {row[0] for row in cur.fetchall()}
        for field in essential_fields:
            assert field in present_fields, f"Missing field in seed data: {field}"
    finally:
        conn.close()


def test_uniqueness_constraint_on_topic_name(tmp_path):
    db_path = os.path.join(tmp_path, "topics.db")
    init_db(db_path)

    # Seed once
    inserted = seed_potential_topics(DEFAULT_SEED_ROWS, db_path)
    assert inserted >= 1

    # Try duplicate insert without OR IGNORE to assert uniqueness enforcement
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        topic_name, field = DEFAULT_SEED_ROWS[0]
        try:
            cur.execute(
                "INSERT INTO potential_topics(topic_name, field) VALUES (?, ?);",
                (topic_name, field),
            )
            conn.commit()
            pytest.fail("Expected IntegrityError for duplicate topic_name")
        except sqlite3.IntegrityError:
            pass
    finally:
        conn.close()
