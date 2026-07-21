"""Unit tests for the state routes (in-progress workout persistence)."""
import json
import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    """Create a test client with a fresh temp database."""
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({'TESTING': True, 'DATABASE': db_path})

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_path)


class TestSaveState:
    """Tests for POST /api/state/save endpoint."""

    def test_save_state_returns_success(self, client):
        resp = client.post('/api/state/save',
            data=json.dumps({
                'key': 'in_progress_workout',
                'value': {'week': 1, 'day': 2, 'sets': {}, 'notes': {}}
            }),
            content_type='application/json')
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_save_state_with_full_workout_data(self, client):
        value = {
            'week': 3,
            'day': 1,
            'sets': {
                'Bench Press': {'1': {'weight': '135', 'reps': '8'}, '2': {'weight': '135', 'reps': '7'}},
                'Squat': {'1': {'weight': '225', 'reps': '5'}}
            },
            'notes': {'Bench Press': 'Good form', 'Squat': ''}
        }
        resp = client.post('/api/state/save',
            data=json.dumps({'key': 'in_progress_workout', 'value': value}),
            content_type='application/json')
        assert resp.status_code == 200

    def test_save_null_value_clears_state(self, client):
        # Save some state first
        client.post('/api/state/save',
            data=json.dumps({'key': 'in_progress_workout', 'value': {'week': 1, 'day': 1, 'sets': {}, 'notes': {}}}),
            content_type='application/json')

        # Clear it
        resp = client.post('/api/state/save',
            data=json.dumps({'key': 'in_progress_workout', 'value': None}),
            content_type='application/json')
        assert resp.status_code == 200

        # Verify it's gone
        resp = client.get('/api/state/load')
        assert resp.get_json()['value'] is None

    def test_save_state_overwrites_existing(self, client):
        # Save initial state
        client.post('/api/state/save',
            data=json.dumps({'key': 'in_progress_workout', 'value': {'week': 1, 'day': 1, 'sets': {}, 'notes': {}}}),
            content_type='application/json')

        # Overwrite with new state
        new_value = {'week': 2, 'day': 3, 'sets': {'Ex': {'1': {'weight': '50', 'reps': '10'}}}, 'notes': {}}
        client.post('/api/state/save',
            data=json.dumps({'key': 'in_progress_workout', 'value': new_value}),
            content_type='application/json')

        # Verify latest state is returned
        resp = client.get('/api/state/load')
        data = resp.get_json()
        assert data['value']['week'] == 2
        assert data['value']['day'] == 3

    def test_save_rejects_invalid_json(self, client):
        resp = client.post('/api/state/save',
            data='not json',
            content_type='application/json')
        assert resp.status_code == 400

    def test_save_uses_default_key(self, client):
        """When no key is provided, defaults to 'in_progress_workout'."""
        resp = client.post('/api/state/save',
            data=json.dumps({'value': {'week': 1, 'day': 1, 'sets': {}, 'notes': {}}}),
            content_type='application/json')
        assert resp.status_code == 200

        resp = client.get('/api/state/load')
        assert resp.get_json()['key'] == 'in_progress_workout'
        assert resp.get_json()['value'] is not None


class TestLoadState:
    """Tests for GET /api/state/load endpoint."""

    def test_load_returns_null_when_no_state(self, client):
        resp = client.get('/api/state/load')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['key'] == 'in_progress_workout'
        assert data['value'] is None

    def test_load_returns_saved_state(self, client):
        value = {'week': 1, 'day': 2, 'sets': {'Curl': {'1': {'weight': '25', 'reps': '12'}}}, 'notes': {'Curl': 'Easy'}}
        client.post('/api/state/save',
            data=json.dumps({'key': 'in_progress_workout', 'value': value}),
            content_type='application/json')

        resp = client.get('/api/state/load')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['key'] == 'in_progress_workout'
        assert data['value']['week'] == 1
        assert data['value']['day'] == 2
        assert data['value']['sets']['Curl']['1']['weight'] == '25'
        assert data['value']['notes']['Curl'] == 'Easy'

    def test_load_with_custom_key(self, client):
        """Can load with a specific key query parameter."""
        resp = client.get('/api/state/load?key=nonexistent')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['key'] == 'nonexistent'
        assert data['value'] is None
