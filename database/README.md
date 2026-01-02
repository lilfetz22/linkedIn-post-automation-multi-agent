# Database

## Overview

This directory contains SQLite database management for the LinkedIn post automation system.

## Files

- `init_db.py` - Database initialization and seeding script
- `operations.py` - Database query and update operations
- `topics.db` - **Not in version control** - Runtime database file

## Database Schema

```sql
CREATE TABLE previous_topics (
    id INTEGER PRIMARY KEY,
    topic_name TEXT NOT NULL,
    date_posted TEXT NOT NULL
);

CREATE TABLE potential_topics (
    id INTEGER PRIMARY KEY,
    topic_name TEXT NOT NULL UNIQUE,
    field TEXT NOT NULL,
    used BOOLEAN DEFAULT FALSE
);
```

## Setup

### First-time initialization

```powershell
# Initialize database with schema only
python database/init_db.py

# Initialize and seed with default topics
python database/init_db.py --seed
```

### Custom database path

```powershell
python database/init_db.py --db path/to/custom.db --seed
```

## Why `topics.db` is Not in Version Control

The `topics.db` file is **excluded from version control** because:

1. **Runtime State**: Contains operational data that changes with each workflow run
2. **User-Specific**: Different users/environments will have different topic histories
3. **Merge Conflicts**: Versioning would cause conflicts in collaborative environments
4. **Idempotent Setup**: `init_db.py` can recreate the schema on any machine

## Seed Data

Default seed topics are defined in `init_db.py` and cover:
- Data Science (Optimizations & Time-Series Analysis)
- Generative AI & AI Agents

Users can customize by:
1. Modifying `DEFAULT_SEED_ROWS` in `init_db.py` before first run
2. Manually adding topics via `database/operations.py` functions
3. Running the workflow, which populates topics from user's field in `config.json`

## Usage in Workflow

The orchestrator automatically:
1. Checks if `topics.db` exists
2. Initializes schema if missing (via `init_db()`)
3. Seeds if database is empty (optional)
4. Updates `previous_topics` after each successful post
5. Marks topics as used in `potential_topics`
