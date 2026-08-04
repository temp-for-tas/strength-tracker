"""Unit tests for the database module."""
import os
import sqlite3
import tempfile

import pytest

from app import create_app
from database import get_db, init_db, close_db


@pytest.fixture
def app():
    """Create a test application with a temporary database."""
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(test_config={
        'DATABASE': db_path,
        'TESTING': True,
    })

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestGetDb:
    """Tests for the get_db function."""

    def test_returns_connection(self, app):
        """get_db returns a sqlite3 connection within app context."""
        with app.app_context():
            db = get_db()
            assert db is not None
            assert isinstance(db, sqlite3.Connection)

    def test_returns_same_connection_in_same_context(self, app):
        """get_db returns the same connection within a single request context."""
        with app.app_context():
            db1 = get_db()
            db2 = get_db()
            assert db1 is db2

    def test_foreign_keys_enabled(self, app):
        """Foreign keys pragma is enabled on the connection."""
        with app.app_context():
            db = get_db()
            result = db.execute('PRAGMA foreign_keys').fetchone()
            assert result[0] == 1

    def test_row_factory_set(self, app):
        """Row factory is set to sqlite3.Row for dict-like access."""
        with app.app_context():
            db = get_db()
            assert db.row_factory == sqlite3.Row


class TestInitDb:
    """Tests for schema initialization."""

    def test_exercises_table_exists(self, app):
        """The exercises table is created on init."""
        with app.app_context():
            db = get_db()
            result = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='exercises'"
            ).fetchone()
            assert result is not None

    def test_sessions_table_exists(self, app):
        """The sessions table is created on init."""
        with app.app_context():
            db = get_db()
            result = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
            ).fetchone()
            assert result is not None

    def test_set_entries_table_exists(self, app):
        """The set_entries table is created on init."""
        with app.app_context():
            db = get_db()
            result = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='set_entries'"
            ).fetchone()
            assert result is not None

    def test_notes_table_exists(self, app):
        """The notes table is created on init."""
        with app.app_context():
            db = get_db()
            result = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='notes'"
            ).fetchone()
            assert result is not None

    def test_app_state_table_exists(self, app):
        """The app_state table is created on init."""
        with app.app_context():
            db = get_db()
            result = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='app_state'"
            ).fetchone()
            assert result is not None

    def test_init_db_idempotent(self, app):
        """Calling init_db multiple times doesn't raise errors."""
        with app.app_context():
            # init_db was already called by init_app, call again
            init_db()
            db = get_db()
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = [t['name'] for t in tables]
            assert 'exercises' in table_names
            assert 'sessions' in table_names
            assert 'set_entries' in table_names
            assert 'notes' in table_names
            assert 'app_state' in table_names


class TestConstraints:
    """Tests for CHECK and UNIQUE constraints."""

    def test_exercises_week_check_lower(self, app):
        """Exercises table rejects week < 1."""
        with app.app_context():
            db = get_db()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO exercises (week, day, exercise_name, target_sets, target_reps, sort_order) "
                    "VALUES (0, 1, 'Bench Press', 4, '5-8', 1)"
                )

    def test_exercises_week_check_upper(self, app):
        """Exercises table rejects week > 52."""
        with app.app_context():
            db = get_db()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO exercises (week, day, exercise_name, target_sets, target_reps, sort_order) "
                    "VALUES (53, 1, 'Bench Press', 4, '5-8', 1)"
                )

    def test_exercises_day_check_lower(self, app):
        """Exercises table rejects day < 1."""
        with app.app_context():
            db = get_db()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO exercises (week, day, exercise_name, target_sets, target_reps, sort_order) "
                    "VALUES (1, 0, 'Bench Press', 4, '5-8', 1)"
                )

    def test_exercises_day_check_upper(self, app):
        """Exercises table rejects day > 7."""
        with app.app_context():
            db = get_db()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO exercises (week, day, exercise_name, target_sets, target_reps, sort_order) "
                    "VALUES (1, 8, 'Bench Press', 4, '5-8', 1)"
                )

    def test_exercises_day_7_accepted(self, app):
        """Exercises table accepts day = 7 (supports 7-day programs)."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO exercises (week, day, exercise_name, target_sets, target_reps, sort_order) "
                "VALUES (1, 7, 'Sunday Run', 1, '20-30 min', 1)"
            )
            db.commit()
            result = db.execute(
                "SELECT * FROM exercises WHERE week=1 AND day=7"
            ).fetchone()
            assert result is not None
            assert result['exercise_name'] == 'Sunday Run'

    def test_exercises_target_sets_check_lower(self, app):
        """Exercises table rejects target_sets < 1."""
        with app.app_context():
            db = get_db()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO exercises (week, day, exercise_name, target_sets, target_reps, sort_order) "
                    "VALUES (1, 1, 'Bench Press', 0, '5-8', 1)"
                )

    def test_exercises_target_sets_check_upper(self, app):
        """Exercises table rejects target_sets > 10."""
        with app.app_context():
            db = get_db()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO exercises (week, day, exercise_name, target_sets, target_reps, sort_order) "
                    "VALUES (1, 1, 'Bench Press', 11, '5-8', 1)"
                )

    def test_exercises_unique_constraint(self, app):
        """Exercises table enforces UNIQUE(week, day, exercise_name)."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO exercises (week, day, exercise_name, target_sets, target_reps, sort_order) "
                "VALUES (1, 1, 'Bench Press', 4, '5-8', 1)"
            )
            db.commit()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO exercises (week, day, exercise_name, target_sets, target_reps, sort_order) "
                    "VALUES (1, 1, 'Bench Press', 3, '8-10', 2)"
                )

    def test_set_entries_set_number_check_lower(self, app):
        """set_entries table rejects set_number < 1."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.commit()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) "
                    "VALUES (1, 'Bench Press', 0, 50.0, 8)"
                )

    def test_set_entries_set_number_check_upper(self, app):
        """set_entries table rejects set_number > 10."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.commit()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) "
                    "VALUES (1, 'Bench Press', 11, 50.0, 8)"
                )

    def test_set_entries_weight_check_lower(self, app):
        """set_entries table rejects weight < 0 (negative)."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.commit()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) "
                    "VALUES (1, 'Bench Press', 1, -1, 8)"
                )

    def test_set_entries_weight_check_upper(self, app):
        """set_entries table rejects weight > 9999."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.commit()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) "
                    "VALUES (1, 'Bench Press', 1, 10000, 8)"
                )

    def test_set_entries_reps_check_lower(self, app):
        """set_entries table rejects reps < 0 (negative)."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.commit()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) "
                    "VALUES (1, 'Bench Press', 1, 50.0, -1)"
                )

    def test_set_entries_reps_check_upper(self, app):
        """set_entries table rejects reps > 999."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.commit()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) "
                    "VALUES (1, 'Bench Press', 1, 50.0, 1000)"
                )

    def test_set_entries_unique_constraint(self, app):
        """set_entries enforces UNIQUE(session_id, exercise_name, set_number)."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.execute(
                "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) "
                "VALUES (1, 'Bench Press', 1, 50.0, 8)"
            )
            db.commit()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) "
                    "VALUES (1, 'Bench Press', 1, 55.0, 6)"
                )

    def test_notes_length_check(self, app):
        """Notes table rejects note_text > 500 chars."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.commit()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO notes (session_id, exercise_name, note_text) "
                    "VALUES (1, 'Bench Press', ?)",
                    ('x' * 501,)
                )

    def test_notes_unique_constraint(self, app):
        """Notes enforces UNIQUE(session_id, exercise_name)."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.execute(
                "INSERT INTO notes (session_id, exercise_name, note_text) "
                "VALUES (1, 'Bench Press', 'Good form')"
            )
            db.commit()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO notes (session_id, exercise_name, note_text) "
                    "VALUES (1, 'Bench Press', 'Different note')"
                )

    def test_cascade_delete_set_entries(self, app):
        """Deleting a session cascades to set_entries."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.execute(
                "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) "
                "VALUES (1, 'Bench Press', 1, 50.0, 8)"
            )
            db.commit()
            db.execute("DELETE FROM sessions WHERE id = 1")
            db.commit()
            result = db.execute("SELECT * FROM set_entries WHERE session_id = 1").fetchall()
            assert len(result) == 0

    def test_cascade_delete_notes(self, app):
        """Deleting a session cascades to notes."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.execute(
                "INSERT INTO notes (session_id, exercise_name, note_text) "
                "VALUES (1, 'Bench Press', 'Good form')"
            )
            db.commit()
            db.execute("DELETE FROM sessions WHERE id = 1")
            db.commit()
            result = db.execute("SELECT * FROM notes WHERE session_id = 1").fetchall()
            assert len(result) == 0


class TestAppState:
    """Tests for the app_state table."""

    def test_insert_and_retrieve(self, app):
        """Can insert and retrieve key-value pairs."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO app_state (key, value) VALUES ('current_week', '3')"
            )
            db.commit()
            result = db.execute(
                "SELECT value FROM app_state WHERE key = 'current_week'"
            ).fetchone()
            assert result['value'] == '3'

    def test_primary_key_enforced(self, app):
        """app_state enforces primary key on 'key' column."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO app_state (key, value) VALUES ('current_week', '1')"
            )
            db.commit()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO app_state (key, value) VALUES ('current_week', '2')"
                )


class TestCloseDb:
    """Tests for database connection teardown."""

    def test_connection_closed_after_context(self, app):
        """Database connection is closed after app context ends."""
        with app.app_context():
            db = get_db()
            # Connection should be usable within context
            db.execute("SELECT 1")

        # After context, connection should be closed
        # Attempting to use it should raise an error
        with pytest.raises(Exception):
            db.execute("SELECT 1")
