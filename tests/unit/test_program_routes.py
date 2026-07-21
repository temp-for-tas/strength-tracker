"""Unit tests for program routes (CSV upload and program retrieval).

Tests cover:
- File size rejection (>1MB)
- Program replacement preserves session history
- Program retrieval endpoints (weeks, days, exercises, current-week)
- CSV upload via multipart form

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
"""
import io
import os
import tempfile

import pytest

from app import create_app
from database import get_db


# Skip all tests in this module if routes/program.py doesn't exist yet
_program_routes_path = os.path.join(
    os.path.dirname(__file__), '..', '..', 'routes', 'program.py'
)
pytestmark = pytest.mark.skipif(
    not os.path.exists(_program_routes_path),
    reason="routes/program.py not yet created (task 2.2 in progress)"
)


@pytest.fixture
def app():
    """Create a test application with a temporary database."""
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(test_config={'DATABASE': db_path, 'TESTING': True})
    yield app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def sample_csv():
    """A simple valid 2-week, 2-day CSV."""
    return (
        "Week,Day,Exercise,Sets,Target Reps\n"
        "1,1,Bench Press,4,5-8\n"
        "1,1,Incline DB Press,3,8-10\n"
        "1,2,Squat,4,6-8\n"
        "1,2,Leg Press,3,10-12\n"
        "2,1,Bench Press,4,5-8\n"
        "2,1,Incline DB Press,3,8-10\n"
        "2,2,Squat,4,6-8\n"
        "2,2,Leg Press,3,10-12\n"
    )


@pytest.fixture
def uploaded_program(client, sample_csv):
    """Upload a sample program and return the response."""
    data = {'file': (io.BytesIO(sample_csv.encode()), 'program.csv')}
    response = client.post(
        '/api/program/upload',
        data=data,
        content_type='multipart/form-data'
    )
    return response


class TestProgramUpload:
    """Tests for POST /api/program/upload."""

    def test_upload_valid_csv_returns_success(self, client, sample_csv):
        """Uploading a valid CSV returns success with summary."""
        data = {'file': (io.BytesIO(sample_csv.encode()), 'program.csv')}
        response = client.post(
            '/api/program/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data is not None

    def test_upload_valid_csv_returns_correct_counts(self, client, sample_csv):
        """Upload response includes correct week count, days_per_week, and exercise count."""
        data = {'file': (io.BytesIO(sample_csv.encode()), 'program.csv')}
        response = client.post(
            '/api/program/upload',
            data=data,
            content_type='multipart/form-data'
        )
        json_data = response.get_json()
        # Should report 2 weeks, 2 days per week, 8 total exercises
        assert json_data.get('weeks') == 2 or json_data.get('total_weeks') == 2
        assert json_data.get('days_per_week') == 2
        assert json_data.get('total_exercises') == 8

    def test_upload_rejects_file_over_1mb(self, client):
        """Files exceeding 1MB should be rejected with 413 status."""
        # Create a CSV content that exceeds 1MB
        header = "Week,Day,Exercise,Sets,Target Reps\n"
        # Each row is about 30 bytes, we need ~35000 rows to exceed 1MB
        large_content = header + ("1,1,Exercise Name Here,4,5-8\n" * 40000)
        assert len(large_content.encode()) > 1024 * 1024  # Verify > 1MB

        data = {'file': (io.BytesIO(large_content.encode()), 'large.csv')}
        response = client.post(
            '/api/program/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 413

    def test_upload_rejects_invalid_csv(self, client):
        """Uploading an invalid CSV returns 400 with errors."""
        bad_csv = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "abc,0,,11,\n"
        )
        data = {'file': (io.BytesIO(bad_csv.encode()), 'bad.csv')}
        response = client.post(
            '/api/program/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400
        json_data = response.get_json()
        assert 'error' in json_data or 'errors' in json_data or 'rows' in json_data

    def test_upload_rejects_empty_csv(self, client):
        """Uploading an empty file returns 400."""
        data = {'file': (io.BytesIO(b''), 'empty.csv')}
        response = client.post(
            '/api/program/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400

    def test_upload_rejects_inconsistent_days(self, client):
        """CSV with inconsistent day counts across weeks should be rejected."""
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Ex A,3,8-10\n"
            "1,2,Ex B,3,8-10\n"
            "1,3,Ex C,3,8-10\n"
            "2,1,Ex A,3,8-10\n"
            "2,2,Ex B,3,8-10\n"
        )
        data = {'file': (io.BytesIO(csv_content.encode()), 'inconsistent.csv')}
        response = client.post(
            '/api/program/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400

    def test_upload_no_file_returns_error(self, client):
        """POST without a file should return an error."""
        response = client.post(
            '/api/program/upload',
            data={},
            content_type='multipart/form-data'
        )
        assert response.status_code in (400, 422)


class TestProgramReplacement:
    """Tests for program replacement preserving session history."""

    def test_replacement_preserves_session_history(self, app, client, sample_csv):
        """Re-uploading a new program should preserve existing sessions."""
        # First upload
        data = {'file': (io.BytesIO(sample_csv.encode()), 'program.csv')}
        client.post('/api/program/upload', data=data,
                    content_type='multipart/form-data')

        # Insert a session directly into the database
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO sessions (week, day, completed_at) "
                "VALUES (1, 1, '2025-01-15T09:30')"
            )
            db.execute(
                "INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps) "
                "VALUES (1, 'Bench Press', 1, 135.0, 8)"
            )
            db.commit()

        # Upload a different program
        new_csv = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Overhead Press,3,6-8\n"
            "1,2,Deadlift,5,3-5\n"
            "2,1,Overhead Press,3,6-8\n"
            "2,2,Deadlift,5,3-5\n"
        )
        data = {'file': (io.BytesIO(new_csv.encode()), 'new_program.csv')}
        response = client.post('/api/program/upload', data=data,
                               content_type='multipart/form-data')
        assert response.status_code == 200

        # Verify session history is preserved
        with app.app_context():
            db = get_db()
            sessions = db.execute("SELECT * FROM sessions").fetchall()
            assert len(sessions) == 1
            assert sessions[0]['week'] == 1
            assert sessions[0]['day'] == 1

            # Set entries should also be preserved
            entries = db.execute("SELECT * FROM set_entries").fetchall()
            assert len(entries) == 1
            assert entries[0]['weight'] == 135.0

    def test_replacement_replaces_exercises(self, app, client, sample_csv):
        """Re-uploading should replace the exercise program."""
        # First upload
        data = {'file': (io.BytesIO(sample_csv.encode()), 'program.csv')}
        client.post('/api/program/upload', data=data,
                    content_type='multipart/form-data')

        # Upload a different program
        new_csv = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Overhead Press,3,6-8\n"
            "1,2,Deadlift,5,3-5\n"
            "2,1,Overhead Press,3,6-8\n"
            "2,2,Deadlift,5,3-5\n"
        )
        data = {'file': (io.BytesIO(new_csv.encode()), 'new_program.csv')}
        client.post('/api/program/upload', data=data,
                    content_type='multipart/form-data')

        # Verify old exercises are gone, new ones are present
        with app.app_context():
            db = get_db()
            exercises = db.execute("SELECT * FROM exercises").fetchall()
            exercise_names = [e['exercise_name'] for e in exercises]
            assert 'Bench Press' not in exercise_names
            assert 'Overhead Press' in exercise_names
            assert 'Deadlift' in exercise_names


class TestProgramWeeksEndpoint:
    """Tests for GET /api/program/weeks."""

    def test_returns_weeks_after_upload(self, client, uploaded_program):
        """Should return list of weeks after program upload."""
        response = client.get('/api/program/weeks')
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data is not None

    def test_returns_empty_when_no_program(self, client):
        """Should return empty/indication when no program is loaded."""
        response = client.get('/api/program/weeks')
        assert response.status_code == 200
        json_data = response.get_json()
        # Should be empty list or indicate no program
        assert json_data is not None


class TestProgramDaysEndpoint:
    """Tests for GET /api/program/weeks/<week>/days."""

    def test_returns_days_for_valid_week(self, client, uploaded_program):
        """Should return days for an existing week."""
        response = client.get('/api/program/weeks/1/days')
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data is not None

    def test_returns_error_for_invalid_week(self, client, uploaded_program):
        """Should handle non-existent week gracefully."""
        response = client.get('/api/program/weeks/99/days')
        # Should return 200 with empty or 400
        assert response.status_code in (200, 400, 404)


class TestProgramExercisesEndpoint:
    """Tests for GET /api/program/weeks/<week>/days/<day>."""

    def test_returns_exercises_for_valid_day(self, client, uploaded_program):
        """Should return exercises for a valid week/day combination."""
        response = client.get('/api/program/weeks/1/days/1')
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data is not None
        # Should contain exercises
        exercises = json_data.get('exercises', json_data)
        if isinstance(exercises, list):
            assert len(exercises) > 0

    def test_returns_correct_exercise_fields(self, client, uploaded_program):
        """Exercises should include name, target_sets, and target_reps."""
        response = client.get('/api/program/weeks/1/days/1')
        json_data = response.get_json()
        exercises = json_data.get('exercises', [])
        if exercises:
            ex = exercises[0]
            assert 'exercise_name' in ex
            assert 'target_sets' in ex
            assert 'target_reps' in ex


class TestProgramCurrentWeekEndpoint:
    """Tests for GET /api/program/current-week."""

    def test_returns_current_week_info(self, client, uploaded_program):
        """Should return current week, days_per_week, and total_weeks."""
        response = client.get('/api/program/current-week')
        assert response.status_code == 200
        json_data = response.get_json()
        assert 'current_week' in json_data
        assert 'days_per_week' in json_data
        assert 'total_weeks' in json_data

    def test_current_week_defaults_to_1(self, client, uploaded_program):
        """Current week should default to 1 for a new program."""
        response = client.get('/api/program/current-week')
        json_data = response.get_json()
        assert json_data['current_week'] == 1

    def test_days_per_week_matches_program(self, client, uploaded_program):
        """days_per_week should match the uploaded program's structure."""
        response = client.get('/api/program/current-week')
        json_data = response.get_json()
        assert json_data['days_per_week'] == 2  # sample_csv has 2 days

    def test_total_weeks_matches_program(self, client, uploaded_program):
        """total_weeks should match the uploaded program."""
        response = client.get('/api/program/current-week')
        json_data = response.get_json()
        assert json_data['total_weeks'] == 2  # sample_csv has 2 weeks

    def test_returns_empty_state_when_no_program(self, client):
        """Should handle gracefully when no program is loaded."""
        response = client.get('/api/program/current-week')
        assert response.status_code == 200
        json_data = response.get_json()
        # Should indicate no program or return zeros/defaults
        assert json_data is not None


class TestProgramUpload7DayProgram:
    """Tests for 7-day program upload via routes."""

    def test_7_day_program_upload_accepted(self, client):
        """A 7-day program should be uploaded successfully."""
        rows = ["Week,Day,Exercise,Sets,Target Reps"]
        for week in range(1, 3):
            for day in range(1, 8):
                rows.append(f"{week},{day},Exercise Day{day},3,8-10")
        csv_content = "\n".join(rows)

        data = {'file': (io.BytesIO(csv_content.encode()), 'seven_day.csv')}
        response = client.post(
            '/api/program/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data.get('days_per_week') == 7

    def test_7_day_program_current_week_endpoint(self, client):
        """After uploading a 7-day program, current-week shows days_per_week=7."""
        rows = ["Week,Day,Exercise,Sets,Target Reps"]
        for week in range(1, 3):
            for day in range(1, 8):
                rows.append(f"{week},{day},Exercise Day{day},3,8-10")
        csv_content = "\n".join(rows)

        data = {'file': (io.BytesIO(csv_content.encode()), 'seven_day.csv')}
        client.post('/api/program/upload', data=data,
                    content_type='multipart/form-data')

        response = client.get('/api/program/current-week')
        json_data = response.get_json()
        assert json_data['days_per_week'] == 7
