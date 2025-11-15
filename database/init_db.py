import argparse
import os
import sqlite3
from datetime import datetime, timezone
from typing import Iterable, Tuple

DEFAULT_DB_PATH = os.path.join("database", "topics.db")


def ensure_db_dir(db_path: str = DEFAULT_DB_PATH) -> None:
    parent = os.path.dirname(db_path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


def _connect(db_path: str):
    ensure_db_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Create tables and indices if they do not already exist. Idempotent."""
    with _connect(db_path) as conn:
        cur = conn.cursor()
        # Tables
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS previous_topics (
                id INTEGER PRIMARY KEY,
                topic_name TEXT NOT NULL,
                date_posted TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS potential_topics (
                id INTEGER PRIMARY KEY,
                topic_name TEXT NOT NULL UNIQUE,
                field TEXT NOT NULL
            );
            """
        )
        # Indices
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_previous_topics_date_posted
            ON previous_topics(date_posted DESC);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_potential_topics_field
            ON potential_topics(field, topic_name);
            """
        )
        conn.commit()


def seed_potential_topics(
    rows: Iterable[Tuple[str, str]], db_path: str = DEFAULT_DB_PATH
) -> int:
    """Seed potential_topics with (topic_name, field) rows using INSERT OR IGNORE.

    Returns the number of rows actually inserted (ignored duplicates excluded).
    """
    with _connect(db_path) as conn:
        cur = conn.cursor()
        cur.executemany(
            "INSERT OR IGNORE INTO potential_topics(topic_name, field) VALUES (?, ?);",
            list(rows),
        )
        conn.commit()
        return cur.rowcount


DEFAULT_FIELD_DS = "Data Science (Optimizations & Time-Series Analysis)"
DEFAULT_FIELD_GAI = "Generative AI & AI Agents"

DEFAULT_SEED_ROWS = [
    # Data Science
    ("How to detect data leakage in time-series pipelines", DEFAULT_FIELD_DS),
    ("Feature engineering for irregular time-series", DEFAULT_FIELD_DS),
    ("Optimizing inference latency with ONNX Runtime", DEFAULT_FIELD_DS),
    ("Segmented ARIMA vs. Prophet: where each wins", DEFAULT_FIELD_DS),
    ("Causal impact vs. A/B: choosing the right test", DEFAULT_FIELD_DS),
    ("Hyperparameter search budgets: Bayesian vs. early-stopping", DEFAULT_FIELD_DS),
    ("Forecast error decomposition your CFO understands", DEFAULT_FIELD_DS),
    ("Building robust backtests for demand forecasting", DEFAULT_FIELD_DS),
    # GenAI
    ("RAG pitfalls: when retrieval silently fails", DEFAULT_FIELD_GAI),
    ("Agent routing strategies that actually converge", DEFAULT_FIELD_GAI),
    ("Guardrails: regex, CFGs, or vector policies?", DEFAULT_FIELD_GAI),
    ("Evaluating LLM tools with function-calling traces", DEFAULT_FIELD_GAI),
    ("Latency-aware chunking for streaming RAG", DEFAULT_FIELD_GAI),
    ("LLM evals that predict business outcomes", DEFAULT_FIELD_GAI),
    ("Stateful multi-agent memory designs", DEFAULT_FIELD_GAI),
    ("From prompts to protocols: MCP in production", DEFAULT_FIELD_GAI),
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize and optionally seed topics DB"
    )
    parser.add_argument(
        "--db", dest="db", default=DEFAULT_DB_PATH, help="Path to topics.db"
    )
    parser.add_argument(
        "--seed", dest="seed", action="store_true", help="Seed potential topics"
    )
    args = parser.parse_args()

    init_db(args.db)
    if args.seed:
        inserted = seed_potential_topics(DEFAULT_SEED_ROWS, args.db)
        print(f"Seeded potential_topics (inserted={inserted}) at {args.db}")
    else:
        print(f"Initialized database at {args.db}")


if __name__ == "__main__":
    main()
