"""Unit tests for session save, history, and previous performance endpoints."""
import tempfile
import os
import pytest

from app import create_app
from database import get_db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(test_config={'DATABASE': db_path, 'TESTING': True})
    yield app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


def _valid_session_payload(week=1, day=1, sets=None, notes=None):
    """Helper to build a valid session payload."""
    if sets is None:
        sets = [
            {"exercise_name": "Bench Press", "set_number": 1, "weight": 100.0, "reps": 8},
            {"exercise_name": "Bench Press", "set_number": 2, "weight": 100.0, "reps": 7},
            {"exercise_name": "Squat", "set_number": 1, "weight": 140.0, "reps": 5},
        ]
    if notes is None:
        notes = [
            {"exercise_name": "Bench Press", "note": "Felt strong today"},
        ]
    return {"week": week, "day": day, "sets": sets, "notes": notes}


class TestSaveSession:
    """Tests for POST /api/sessions."""

    def test_save_valid_session_returns_201(self, client):
        """Save with valid data returns 201 and confirmation."""
        payload = _valid_session_payload()
        resp = client.post('/api/sessions', json=payload)

        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        assert 'session_id' in data
        assert isinstance(data['session_id'], int)
        assert data['message'] == 'Session saved successfully'

    def test_save_with_no_set_entries_accepted(self, client):
        """Save with no set entries is accepted (returns 201).

        The current implementation does not produce a special warning for
        empty sets — it accepts and saves them normally.
        """
        payload = _valid_session_payload(sets=[], notes=[])
        resp = client.post('/api/sessions', json=payload)

        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        assert 'session_id' in data

    def test_save_with_invalid_weight_returns_400(self, client):
        """Save with invalid weight returns 400 with field-level errors."""
        payload = _valid_session_payload(sets=[
            {"exercise_name": "Bench Press", "set_number": 1, "weight": -5, "reps": 8},
        ])
        resp = client.post('/api/sessions', json=payload)

        assert resp.status_code == 400
        data = resp.get_json()
        assert data['error'] == 'validation'
        assert any('Weight' in err or 'weight' in err.lower() for err in data['details'])

    def test_save_with_invalid_reps_returns_400(self, client):
        """Save with invalid reps returns 400 with field-level errors."""
        payload = _valid_session_payload(sets=[
            {"exercise_name": "Bench Press", "set_number": 1, "weight": 100.0, "reps": 0},
        ])
        resp = client.post('/api/sessions', json=payload)

        assert resp.status_code == 400
        data = resp.get_json()
        assert data['error'] == 'validation'
        assert any('Reps' in err or 'reps' in err.lower() for err in data['details'])

    def test_save_with_invalid_weight_and_reps_returns_multiple_errors(self, client):
        """Save with multiple invalid fields returns 400 with all field-level errors."""
        payload = _valid_session_payload(sets=[
            {"exercise_name": "Bench Press", "set_number": 1, "weight": 99999, "reps": 1000},
        ])
        resp = client.post('/api/sessions', json=payload)

        assert resp.status_code == 400
        data = resp.get_json()
        assert data['error'] == 'validation'
        assert len(data['details']) >= 2

    def test_save_partial_sets_saved_correctly(self, client):
        """Partial sets (fewer than target) are saved correctly."""
        # Only recording 2 sets for an exercise that has target of 4
        payload = _valid_session_payload(sets=[
            {"exercise_name": "Bench Press", "set_number": 1, "weight": 100.0, "reps": 8},
            {"exercise_name": "Bench Press", "set_number": 2, "weight": 95.0, "reps": 7},
        ], notes=[])
        resp = client.post('/api/sessions', json=payload)

        assert resp.status_code == 201
        data = resp.get_json()
        session_id = data['session_id']

        # Retrieve and verify only the submitted sets are stored
        resp2 = client.get(f'/api/sessions/{session_id}')
        assert resp2.status_code == 200
        session_data = resp2.get_json()
        bench_sets = session_data['exercises']['Bench Press']['sets']
        assert len(bench_sets) == 2
        assert bench_sets[0]['weight'] == 100.0
        assert bench_sets[0]['reps'] == 8
        assert bench_sets[1]['weight'] == 95.0
        assert bench_sets[1]['reps'] == 7

    def test_save_empty_notes_preserved(self, client):
        """Empty notes are preserved when saved."""
        payload = _valid_session_payload(
            sets=[
                {"exercise_name": "Bench Press", "set_number": 1, "weight": 100.0, "reps": 8},
            ],
            notes=[
                {"exercise_name": "Bench Press", "note": ""},
            ]
        )
        resp = client.post('/api/sessions', json=payload)

        assert resp.status_code == 201
        session_id = resp.get_json()['session_id']

        # Retrieve session and verify empty note is stored
        resp2 = client.get(f'/api/sessions/{session_id}')
        assert resp2.status_code == 200
        session_data = resp2.get_json()
        assert session_data['exercises']['Bench Press']['note'] == ''


class TestGetSessions:
    """Tests for GET /api/sessions (history)."""

    def test_history_returns_sessions_in_descending_date_order(self, client, app):
        """History returns sessions in descending date order."""
        # Insert sessions with specific timestamps to control order
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (?, ?, ?)",
                (1, 1, '2025-01-10T08:00')
            )
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (?, ?, ?)",
                (1, 2, '2025-01-12T09:00')
            )
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (?, ?, ?)",
                (2, 1, '2025-01-11T10:00')
            )
            db.commit()

        resp = client.get('/api/sessions')
        assert resp.status_code == 200
        data = resp.get_json()
        sessions = data['sessions']
        assert len(sessions) == 3

        # Verify descending order by completed_at
        assert sessions[0]['completed_at'] == '2025-01-12T09:00'
        assert sessions[1]['completed_at'] == '2025-01-11T10:00'
        assert sessions[2]['completed_at'] == '2025-01-10T08:00'

    def test_history_empty_returns_empty_list(self, client):
        """History with no sessions returns empty list."""
        resp = client.get('/api/sessions')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['sessions'] == []


class TestPreviousPerformance:
    """Tests for GET /api/sessions/previous/<week>/<day>."""

    def test_previous_returns_correct_session_when_multiple_exist(self, client, app):
        """Previous performance returns the most recent session when multiple exist."""
        with app.app_context():
            db = get_db()
            # Insert two sessions for week 1 day 1 with different timestamps
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (?, ?, ?)",
                (1, 1, '2025-01-05T08:00')
            )
            older_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (?, ?, ?)",
                (1, 1, '2025-01-12T09:00')
            )
            newer_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Add sets to both sessions
            db.execute(
                "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) VALUES (?, ?, ?, ?, ?)",
                (older_id, 'Bench Press', 1, 90.0, 8)
            )
            db.execute(
                "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) VALUES (?, ?, ?, ?, ?)",
                (newer_id, 'Bench Press', 1, 100.0, 8)
            )
            db.commit()

        resp = client.get('/api/sessions/previous/1/1')
        assert resp.status_code == 200
        data = resp.get_json()

        # Should return the more recent session
        assert data['session_id'] == newer_id
        assert data['completed_at'] == '2025-01-12T09:00'
        assert data['exercises']['Bench Press']['sets'][0]['weight'] == 100.0

    def test_previous_returns_empty_when_no_prior_session(self, client):
        """Previous performance returns empty when no prior session exists."""
        resp = client.get('/api/sessions/previous/1/1')
        assert resp.status_code == 200
        data = resp.get_json()

        assert data['session_id'] is None
        assert data['exercises'] == {}

    def test_previous_includes_notes(self, client, app):
        """Previous performance includes notes for exercises."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) VALUES (?, ?, ?)",
                (2, 3, '2025-01-15T10:00')
            )
            session_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.execute(
                "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) VALUES (?, ?, ?, ?, ?)",
                (session_id, 'Squat', 1, 140.0, 5)
            )
            db.execute(
                "INSERT INTO notes (session_id, exercise_name, note_text) VALUES (?, ?, ?)",
                (session_id, 'Squat', 'Depth was good')
            )
            db.commit()

        resp = client.get('/api/sessions/previous/2/3')
        assert resp.status_code == 200
        data = resp.get_json()

        assert data['exercises']['Squat']['note'] == 'Depth was good'
        assert data['exercises']['Squat']['sets'][0]['weight'] == 140.0
