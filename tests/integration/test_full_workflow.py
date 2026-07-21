"""Integration tests for full workout tracker workflow.

Tests exercise the complete user journey through the API endpoints,
verifying that components work correctly together end-to-end.
"""
import io
import json
import os
import tempfile

import pytest

from app import create_app


# --- Fixtures ---

SAMPLE_CSV = """\
Week,Day,Exercise,Sets,Target Reps
1,1,Bench Press,4,5-8
1,1,Incline DB Press,3,8-10
1,2,Squat,4,5-8
1,2,Leg Press,3,10-12
2,1,Bench Press,4,4-6
2,1,Incline DB Press,3,6-8
2,2,Squat,4,4-6
2,2,Leg Press,3,8-10
"""

SAMPLE_CSV_B = """\
Week,Day,Exercise,Sets,Target Reps
1,1,Overhead Press,3,5-8
1,2,Deadlift,4,3-5
2,1,Overhead Press,3,4-6
2,2,Deadlift,4,2-4
"""


@pytest.fixture
def app():
    """Create a Flask app with a temporary database for testing."""
    db_fd, db_path = tempfile.mkstemp()
    application = create_app({
        'TESTING': True,
        'DATABASE': db_path,
    })

    yield application

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client for the Flask app."""
    return app.test_client()


# --- Helper functions ---

def upload_csv(client, csv_content):
    """Upload a CSV string via the API and return the response."""
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'program.csv')
    }
    return client.post('/api/program/upload', data=data, content_type='multipart/form-data')


def save_session(client, week, day, sets, notes=None):
    """Save a workout session and return the response."""
    payload = {
        'week': week,
        'day': day,
        'sets': sets,
        'notes': notes or []
    }
    return client.post('/api/sessions', json=payload)


# --- Test 1: Full Workout Journey ---

class TestFullWorkoutJourney:
    """Test complete user journey: upload CSV → browse days → enter workout → save → view history."""

    def test_full_journey(self, client):
        """End-to-end test of the primary user workflow."""
        # Step 1: Upload CSV
        resp = upload_csv(client, SAMPLE_CSV)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['weeks'] == 2
        assert data['days_per_week'] == 2
        assert data['total_exercises'] == 8

        # Step 2: Get current week info (verify program loaded)
        resp = client.get('/api/program/current-week')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['current_week'] == 1
        assert data['days_per_week'] == 2
        assert data['total_weeks'] == 2

        # Step 3: Get exercises for week 1, day 1 (verify exercises returned)
        resp = client.get('/api/program/weeks/1/days/1')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['week'] == 1
        assert data['day'] == 1
        exercises = data['exercises']
        assert len(exercises) == 2
        assert exercises[0]['exercise_name'] == 'Bench Press'
        assert exercises[0]['target_sets'] == 4
        assert exercises[0]['target_reps'] == '5-8'
        assert exercises[1]['exercise_name'] == 'Incline DB Press'

        # Step 4: Check previous performance (should be empty initially)
        resp = client.get('/api/sessions/previous/1/1')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['session_id'] is None
        assert data['exercises'] == {}

        # Step 5: Save a workout session
        sets = [
            {'exercise_name': 'Bench Press', 'set_number': 1, 'weight': 135.0, 'reps': 8},
            {'exercise_name': 'Bench Press', 'set_number': 2, 'weight': 135.0, 'reps': 7},
            {'exercise_name': 'Bench Press', 'set_number': 3, 'weight': 130.0, 'reps': 6},
            {'exercise_name': 'Bench Press', 'set_number': 4, 'weight': 130.0, 'reps': 5},
            {'exercise_name': 'Incline DB Press', 'set_number': 1, 'weight': 50.0, 'reps': 10},
            {'exercise_name': 'Incline DB Press', 'set_number': 2, 'weight': 50.0, 'reps': 9},
            {'exercise_name': 'Incline DB Press', 'set_number': 3, 'weight': 47.5, 'reps': 8},
        ]
        notes = [
            {'exercise_name': 'Bench Press', 'note': 'Felt strong today'},
            {'exercise_name': 'Incline DB Press', 'note': 'Good pump'},
        ]
        resp = save_session(client, week=1, day=1, sets=sets, notes=notes)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        session_id = data['session_id']
        assert session_id is not None

        # Step 6: Verify session appears in history
        resp = client.get('/api/sessions')
        assert resp.status_code == 200
        data = resp.get_json()
        sessions = data['sessions']
        assert len(sessions) == 1
        assert sessions[0]['id'] == session_id
        assert sessions[0]['week'] == 1
        assert sessions[0]['day'] == 1

        # Step 7: Verify session detail
        resp = client.get(f'/api/sessions/{session_id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['id'] == session_id
        assert data['week'] == 1
        assert data['day'] == 1
        assert 'Bench Press' in data['exercises']
        assert len(data['exercises']['Bench Press']['sets']) == 4
        assert data['exercises']['Bench Press']['note'] == 'Felt strong today'
        assert 'Incline DB Press' in data['exercises']
        assert len(data['exercises']['Incline DB Press']['sets']) == 3
        assert data['exercises']['Incline DB Press']['note'] == 'Good pump'

        # Step 8: Verify previous performance now returns the saved session
        resp = client.get('/api/sessions/previous/1/1')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['session_id'] == session_id
        assert 'Bench Press' in data['exercises']
        bench_sets = data['exercises']['Bench Press']['sets']
        assert len(bench_sets) == 4
        assert bench_sets[0]['weight'] == 135.0
        assert bench_sets[0]['reps'] == 8


# --- Test 2: Program Re-upload Preserves History ---

class TestProgramReuploadPreservesHistory:
    """Test that re-uploading a new program preserves existing session history."""

    def test_reupload_preserves_sessions(self, client):
        """Upload program A, save sessions, upload program B, verify sessions from A still accessible."""
        # Upload program A
        resp = upload_csv(client, SAMPLE_CSV)
        assert resp.status_code == 200

        # Save a session for program A (week 1, day 1)
        sets_a = [
            {'exercise_name': 'Bench Press', 'set_number': 1, 'weight': 100.0, 'reps': 5},
            {'exercise_name': 'Bench Press', 'set_number': 2, 'weight': 100.0, 'reps': 5},
        ]
        notes_a = [
            {'exercise_name': 'Bench Press', 'note': 'Program A session'}
        ]
        resp = save_session(client, week=1, day=1, sets=sets_a, notes=notes_a)
        assert resp.status_code == 201
        session_id_a = resp.get_json()['session_id']

        # Save another session for program A (week 1, day 2)
        sets_a2 = [
            {'exercise_name': 'Squat', 'set_number': 1, 'weight': 185.0, 'reps': 5},
        ]
        resp = save_session(client, week=1, day=2, sets=sets_a2)
        assert resp.status_code == 201
        session_id_a2 = resp.get_json()['session_id']

        # Upload program B (completely different exercises)
        resp = upload_csv(client, SAMPLE_CSV_B)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

        # Verify the program has changed
        resp = client.get('/api/program/weeks/1/days/1')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['exercises'][0]['exercise_name'] == 'Overhead Press'

        # Verify sessions from program A are still accessible
        resp = client.get('/api/sessions')
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['sessions']) == 2

        # Verify session detail is intact
        resp = client.get(f'/api/sessions/{session_id_a}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['week'] == 1
        assert data['day'] == 1
        assert 'Bench Press' in data['exercises']
        assert data['exercises']['Bench Press']['sets'][0]['weight'] == 100.0
        assert data['exercises']['Bench Press']['note'] == 'Program A session'

        # Verify second session is also intact
        resp = client.get(f'/api/sessions/{session_id_a2}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'Squat' in data['exercises']
        assert data['exercises']['Squat']['sets'][0]['weight'] == 185.0


# --- Test 3: In-Progress State Cycle ---

class TestInProgressStateCycle:
    """Test in-progress state save/restore cycle."""

    def test_state_save_load_clear_cycle(self, client):
        """Save in-progress workout → load → save session → clear → verify cleared."""
        # Upload a program first
        resp = upload_csv(client, SAMPLE_CSV)
        assert resp.status_code == 200

        # Step 1: Save in-progress workout state
        in_progress_data = {
            'week': 1,
            'day': 1,
            'sets': [
                {'exercise_name': 'Bench Press', 'set_number': 1, 'weight': 135.0, 'reps': 8},
                {'exercise_name': 'Bench Press', 'set_number': 2, 'weight': 135.0, 'reps': 7},
            ],
            'notes': [
                {'exercise_name': 'Bench Press', 'note': 'In progress...'}
            ]
        }
        resp = client.post('/api/state/save', json={
            'key': 'in_progress_workout',
            'value': in_progress_data
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

        # Step 2: Load state (verify it matches what was saved)
        resp = client.get('/api/state/load?key=in_progress_workout')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['key'] == 'in_progress_workout'
        assert data['value'] is not None
        assert data['value']['week'] == 1
        assert data['value']['day'] == 1
        assert len(data['value']['sets']) == 2
        assert data['value']['sets'][0]['weight'] == 135.0
        assert data['value']['notes'][0]['note'] == 'In progress...'

        # Step 3: Complete and save the actual session
        full_sets = [
            {'exercise_name': 'Bench Press', 'set_number': 1, 'weight': 135.0, 'reps': 8},
            {'exercise_name': 'Bench Press', 'set_number': 2, 'weight': 135.0, 'reps': 7},
            {'exercise_name': 'Bench Press', 'set_number': 3, 'weight': 130.0, 'reps': 6},
        ]
        resp = save_session(client, week=1, day=1, sets=full_sets)
        assert resp.status_code == 201

        # Step 4: Clear in-progress state (save with null value)
        resp = client.post('/api/state/save', json={
            'key': 'in_progress_workout',
            'value': None
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

        # Step 5: Verify state is cleared
        resp = client.get('/api/state/load?key=in_progress_workout')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['key'] == 'in_progress_workout'
        assert data['value'] is None


# --- Test 4: Previous Performance with Multiple Sessions ---

class TestPreviousPerformanceMultipleSessions:
    """Test that previous performance returns the most recent session."""

    def test_returns_most_recent_session(self, client):
        """Save multiple sessions for same week/day, verify most recent is returned."""
        # Upload program
        resp = upload_csv(client, SAMPLE_CSV)
        assert resp.status_code == 200

        # Save first session for week 1, day 1
        sets_first = [
            {'exercise_name': 'Bench Press', 'set_number': 1, 'weight': 100.0, 'reps': 5},
            {'exercise_name': 'Bench Press', 'set_number': 2, 'weight': 100.0, 'reps': 5},
        ]
        notes_first = [
            {'exercise_name': 'Bench Press', 'note': 'First session'}
        ]
        resp = save_session(client, week=1, day=1, sets=sets_first, notes=notes_first)
        assert resp.status_code == 201
        first_session_id = resp.get_json()['session_id']

        # Save second session for week 1, day 1 (more recent)
        sets_second = [
            {'exercise_name': 'Bench Press', 'set_number': 1, 'weight': 110.0, 'reps': 6},
            {'exercise_name': 'Bench Press', 'set_number': 2, 'weight': 110.0, 'reps': 5},
            {'exercise_name': 'Bench Press', 'set_number': 3, 'weight': 105.0, 'reps': 5},
        ]
        notes_second = [
            {'exercise_name': 'Bench Press', 'note': 'Second session - stronger'}
        ]
        resp = save_session(client, week=1, day=1, sets=sets_second, notes=notes_second)
        assert resp.status_code == 201
        second_session_id = resp.get_json()['session_id']

        # Verify previous performance returns the most recent (second) session
        resp = client.get('/api/sessions/previous/1/1')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['session_id'] == second_session_id
        assert 'Bench Press' in data['exercises']
        bench = data['exercises']['Bench Press']
        assert len(bench['sets']) == 3
        assert bench['sets'][0]['weight'] == 110.0
        assert bench['sets'][0]['reps'] == 6
        assert bench['note'] == 'Second session - stronger'

    def test_different_day_does_not_interfere(self, client):
        """Sessions for different days don't affect each other's previous performance."""
        # Upload program
        resp = upload_csv(client, SAMPLE_CSV)
        assert resp.status_code == 200

        # Save session for week 1, day 1
        sets_day1 = [
            {'exercise_name': 'Bench Press', 'set_number': 1, 'weight': 135.0, 'reps': 8},
        ]
        resp = save_session(client, week=1, day=1, sets=sets_day1)
        assert resp.status_code == 201

        # Save session for week 1, day 2
        sets_day2 = [
            {'exercise_name': 'Squat', 'set_number': 1, 'weight': 225.0, 'reps': 5},
        ]
        resp = save_session(client, week=1, day=2, sets=sets_day2)
        assert resp.status_code == 201

        # Previous for day 1 should only show bench press data
        resp = client.get('/api/sessions/previous/1/1')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'Bench Press' in data['exercises']
        assert 'Squat' not in data['exercises']

        # Previous for day 2 should only show squat data
        resp = client.get('/api/sessions/previous/1/2')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'Squat' in data['exercises']
        assert 'Bench Press' not in data['exercises']
