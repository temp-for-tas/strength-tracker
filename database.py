"""Database module for SQLite connection management and schema initialization."""
import sqlite3

from flask import current_app, g


def get_db():
    """Get a database connection for the current request.

    Returns the existing connection from Flask's g object,
    or creates a new one if none exists.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(e=None):
    """Close the database connection at the end of a request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database schema if tables don't exist."""
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week INTEGER NOT NULL CHECK(week >= 1 AND week <= 52),
            day INTEGER NOT NULL CHECK(day >= 1 AND day <= 7),
            exercise_name TEXT NOT NULL CHECK(length(exercise_name) <= 100),
            target_sets INTEGER NOT NULL CHECK(target_sets >= 1 AND target_sets <= 10),
            target_reps TEXT NOT NULL CHECK(length(target_reps) <= 20),
            sort_order INTEGER NOT NULL,
            UNIQUE(week, day, exercise_name)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week INTEGER NOT NULL,
            day INTEGER NOT NULL,
            completed_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS set_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            exercise_name TEXT NOT NULL,
            set_number INTEGER NOT NULL CHECK(set_number >= 1 AND set_number <= 10),
            weight REAL CHECK(weight >= 0 AND weight <= 9999),
            reps INTEGER CHECK(reps >= 0 AND reps <= 999),
            UNIQUE(session_id, exercise_name, set_number)
        );

        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            exercise_name TEXT NOT NULL,
            note_text TEXT CHECK(length(note_text) <= 500),
            UNIQUE(session_id, exercise_name)
        );

        CREATE TABLE IF NOT EXISTS app_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    ''')

    # Migrate existing set_entries table if it has the old CHECK constraints
    # (weight >= 0.5 instead of weight >= 0, reps >= 1 instead of reps >= 0)
    _migrate_set_entries(db)


def _migrate_set_entries(db):
    """Migrate set_entries table to allow weight=0 and reps=0.

    SQLite doesn't support ALTER TABLE to change CHECK constraints,
    so we recreate the table if the old constraints are detected.
    """
    # Check the current table schema
    row = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='set_entries'"
    ).fetchone()

    if row is None:
        return  # Table doesn't exist yet (will be created by init_db)

    create_sql = row[0] or ''

    # Detect old constraints (weight >= 0.5 or reps >= 1)
    if 'weight >= 0.5' not in create_sql and 'reps >= 1' not in create_sql:
        return  # Already migrated or fresh schema

    # Recreate table with new constraints
    db.executescript('''
        CREATE TABLE IF NOT EXISTS set_entries_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            exercise_name TEXT NOT NULL,
            set_number INTEGER NOT NULL CHECK(set_number >= 1 AND set_number <= 10),
            weight REAL CHECK(weight >= 0 AND weight <= 9999),
            reps INTEGER CHECK(reps >= 0 AND reps <= 999),
            UNIQUE(session_id, exercise_name, set_number)
        );

        INSERT INTO set_entries_new (id, session_id, exercise_name, set_number, weight, reps)
            SELECT id, session_id, exercise_name, set_number, weight, reps FROM set_entries;

        DROP TABLE set_entries;

        ALTER TABLE set_entries_new RENAME TO set_entries;
    ''')


def init_app(app):
    """Register database functions with the Flask application.

    Call this from the app factory to set up teardown and
    auto-initialization of the database.
    """
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()
