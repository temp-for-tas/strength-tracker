"""Property-based tests for program operations.

# Feature: workout-tracker, Property 10: Program re-upload preserving history

Validates: Requirements 7.5, 9.6
"""

import tempfile
import os
import io
import json

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app import create_app
from database import get_db


# --- Helper to create a fresh app and client per test iteration ---


def make_app_and_client():
    """Create a fresh Flask app with a temporary database.

    Returns (app, client, cleanup_func).
    Call cleanup_func() when done to remove the temp db.
    """
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(test_config={'DATABASE': db_path, 'TESTING': True})
    client = app.test_client()

    def cleanup():
        os.close(db_fd)
        os.unlink(db_path)

    return app, client, cleanup


# --- Strategies ---

# Valid exercise name for CSV: non-empty, printable, no commas or newlines or quotes
exercise_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters=',\n\r"',
    ),
    min_size=1,
    max_size=50,
).map(str.strip).filter(lambda s: 1 <= len(s) <= 100)

# Valid target reps for CSV: non-empty text up to 20 chars, no commas/newlines/quotes
target_reps_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters=',\n\r"',
    ),
    min_size=1,
    max_size=20,
).map(str.strip).filter(lambda s: 1 <= len(s) <= 20)

# Valid weight: 0.5 to 9999, one decimal place
valid_weight_strategy = st.one_of(
    st.integers(min_value=1, max_value=9999).map(float),
    st.integers(min_value=5, max_value=99990).map(lambda x: x / 10.0),
).filter(lambda w: 0.5 <= w <= 9999)

# Valid reps: integers 1 to 999
valid_reps_strategy = st.integers(min_value=1, max_value=999)

# Valid note: up to 500 chars, simple text
valid_note_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S", "Z")),
    min_size=0,
    max_size=200,
)


@st.composite
def program_reupload_scenario_strategy(draw):
    """Generate a full scenario: first program, sessions, second program.

    Returns (csv1, csv2, sessions_data, days_per_week_2, exercise_data_2) where
    sessions_data is a list of session payloads valid against csv1's exercises.
    """
    # First program - ensure unique exercise names per (week, day)
    num_weeks_1 = draw(st.integers(min_value=1, max_value=2))
    days_per_week_1 = draw(st.integers(min_value=1, max_value=3))
    exercises_per_day_1 = draw(st.integers(min_value=1, max_value=2))

    lines_1 = ["Week,Day,Exercise,Sets,Target Reps"]
    exercises_by_day = {}

    for week in range(1, num_weeks_1 + 1):
        for day in range(1, days_per_week_1 + 1):
            # Generate unique exercise names for this day
            day_exercise_names = draw(
                st.lists(
                    exercise_name_strategy,
                    min_size=exercises_per_day_1,
                    max_size=exercises_per_day_1,
                    unique=True,
                )
            )
            day_exercises = []
            for name in day_exercise_names:
                sets = draw(st.integers(min_value=1, max_value=10))
                reps = draw(target_reps_strategy)
                lines_1.append(f"{week},{day},{name},{sets},{reps}")
                day_exercises.append(name)
            exercises_by_day[(week, day)] = day_exercises

    csv1 = "\n".join(lines_1)

    # Generate sessions (1-3 sessions for a random week/day from program 1)
    available_days = list(exercises_by_day.keys())
    chosen_day = draw(st.sampled_from(available_days))
    chosen_week, chosen_day_num = chosen_day
    available_exercises = exercises_by_day[chosen_day]

    num_sessions = draw(st.integers(min_value=1, max_value=3))
    sessions_data = []
    for _ in range(num_sessions):
        # Each session uses the unique exercises from the chosen day
        sets = []
        notes = []
        for ex_name in available_exercises:
            num_sets = draw(st.integers(min_value=1, max_value=4))
            for set_num in range(1, num_sets + 1):
                weight = draw(valid_weight_strategy)
                reps = draw(valid_reps_strategy)
                sets.append({
                    'exercise_name': ex_name,
                    'set_number': set_num,
                    'weight': weight,
                    'reps': reps,
                })
            note_text = draw(valid_note_strategy)
            notes.append({
                'exercise_name': ex_name,
                'note': note_text,
            })

        sessions_data.append({
            'week': chosen_week,
            'day': chosen_day_num,
            'sets': sets,
            'notes': notes,
        })

    # Second program (different from first) - ensure unique names per (week, day)
    num_weeks_2 = draw(st.integers(min_value=1, max_value=2))
    days_per_week_2 = draw(st.integers(min_value=1, max_value=3))
    exercises_per_day_2 = draw(st.integers(min_value=1, max_value=2))

    lines_2 = ["Week,Day,Exercise,Sets,Target Reps"]
    exercise_data_2 = []
    for week in range(1, num_weeks_2 + 1):
        for day in range(1, days_per_week_2 + 1):
            day_exercise_names = draw(
                st.lists(
                    exercise_name_strategy,
                    min_size=exercises_per_day_2,
                    max_size=exercises_per_day_2,
                    unique=True,
                )
            )
            for name in day_exercise_names:
                sets = draw(st.integers(min_value=1, max_value=10))
                reps = draw(target_reps_strategy)
                lines_2.append(f"{week},{day},{name},{sets},{reps}")
                exercise_data_2.append((week, day, name, sets, reps))

    csv2 = "\n".join(lines_2)

    return csv1, csv2, sessions_data, days_per_week_2, exercise_data_2


# ============================================================================
# Feature: workout-tracker, Property 10: Program re-upload preserving history
# Validates: Requirements 7.5, 9.6
# ============================================================================


@settings(max_examples=100)
@given(scenario=program_reupload_scenario_strategy())
def test_program_reupload_preserves_history(scenario):
    """Upload a program, create sessions, upload a different program, verify all
    previous session data (sets, notes) is still intact and retrievable, and
    verify the new program's exercises are accessible.

    **Validates: Requirements 7.5, 9.6**
    """
    csv1, csv2, sessions_data, days_per_week_2, exercise_data_2 = scenario

    app, client, cleanup = make_app_and_client()
    try:
        with app.app_context():
            # Step 1: Upload the first program
            response = client.post(
                '/api/program/upload',
                data={'file': (io.BytesIO(csv1.encode('utf-8')), 'program1.csv')},
                content_type='multipart/form-data',
            )
            assert response.status_code == 200, (
                f"First upload failed: {response.get_json()}"
            )

            # Step 2: Create sessions via POST /api/sessions
            saved_session_ids = []
            for session_payload in sessions_data:
                response = client.post(
                    '/api/sessions',
                    data=json.dumps(session_payload),
                    content_type='application/json',
                )
                assert response.status_code == 201, (
                    f"Session save failed: {response.get_json()}"
                )
                result = response.get_json()
                saved_session_ids.append(result['session_id'])

            # Step 3: Upload a DIFFERENT program (replaces the first)
            response = client.post(
                '/api/program/upload',
                data={'file': (io.BytesIO(csv2.encode('utf-8')), 'program2.csv')},
                content_type='multipart/form-data',
            )
            assert response.status_code == 200, (
                f"Second upload failed: {response.get_json()}"
            )

            # Step 4: Verify all sessions from step 2 are still retrievable
            # Check via GET /api/sessions (history list)
            response = client.get('/api/sessions')
            assert response.status_code == 200
            history = response.get_json()
            history_ids = [s['id'] for s in history['sessions']]

            for session_id in saved_session_ids:
                assert session_id in history_ids, (
                    f"Session {session_id} not found in history after re-upload. "
                    f"Available IDs: {history_ids}"
                )

            # Verify each session's data via GET /api/sessions/<id>
            for idx, session_id in enumerate(saved_session_ids):
                response = client.get(f'/api/sessions/{session_id}')
                assert response.status_code == 200, (
                    f"Failed to retrieve session {session_id}"
                )
                retrieved = response.get_json()

                original = sessions_data[idx]

                # Verify week and day
                assert retrieved['week'] == original['week'], (
                    f"Session {session_id} week mismatch: "
                    f"expected {original['week']}, got {retrieved['week']}"
                )
                assert retrieved['day'] == original['day'], (
                    f"Session {session_id} day mismatch: "
                    f"expected {original['day']}, got {retrieved['day']}"
                )

                # Verify all sets are intact
                for submitted_set in original['sets']:
                    exercise_name = submitted_set['exercise_name']
                    assert exercise_name in retrieved['exercises'], (
                        f"Exercise '{exercise_name}' not found in session "
                        f"{session_id} after re-upload"
                    )
                    exercise_data = retrieved['exercises'][exercise_name]
                    matching_sets = [
                        s for s in exercise_data['sets']
                        if s['set_number'] == submitted_set['set_number']
                    ]
                    assert len(matching_sets) == 1, (
                        f"Expected 1 set with set_number="
                        f"{submitted_set['set_number']} for '{exercise_name}' "
                        f"in session {session_id}, found {len(matching_sets)}"
                    )
                    retrieved_set = matching_sets[0]
                    assert retrieved_set['weight'] == pytest.approx(
                        submitted_set['weight'], abs=0.01
                    ), (
                        f"Weight mismatch in session {session_id} for "
                        f"'{exercise_name}' set {submitted_set['set_number']}"
                    )
                    assert retrieved_set['reps'] == submitted_set['reps'], (
                        f"Reps mismatch in session {session_id} for "
                        f"'{exercise_name}' set {submitted_set['set_number']}"
                    )

                # Verify notes are intact
                for submitted_note in original['notes']:
                    exercise_name = submitted_note['exercise_name']
                    assert exercise_name in retrieved['exercises'], (
                        f"Exercise '{exercise_name}' not found for note "
                        f"verification in session {session_id}"
                    )
                    retrieved_note = retrieved['exercises'][exercise_name]['note']
                    assert retrieved_note == submitted_note['note'], (
                        f"Note mismatch in session {session_id} for "
                        f"'{exercise_name}': expected '{submitted_note['note']}', "
                        f"got '{retrieved_note}'"
                    )

            # Step 5: Verify the new program's exercises are accessible
            for week, day, name, sets, reps in exercise_data_2:
                response = client.get(
                    f'/api/program/weeks/{week}/days/{day}'
                )
                assert response.status_code == 200
                result = response.get_json()
                assert result['week'] == week
                assert result['day'] == day

                # Find the exercise in the returned list
                matching_exercises = [
                    ex for ex in result['exercises']
                    if ex['exercise_name'] == name
                ]
                assert len(matching_exercises) >= 1, (
                    f"Exercise '{name}' not found in week {week} day {day} "
                    f"after re-upload. Available: "
                    f"{[ex['exercise_name'] for ex in result['exercises']]}"
                )
                matched_ex = matching_exercises[0]
                assert matched_ex['target_sets'] == sets, (
                    f"Target sets mismatch for '{name}' in week {week} "
                    f"day {day}: expected {sets}, got {matched_ex['target_sets']}"
                )
                assert matched_ex['target_reps'] == reps, (
                    f"Target reps mismatch for '{name}' in week {week} "
                    f"day {day}: expected '{reps}', got '{matched_ex['target_reps']}'"
                )
    finally:
        cleanup()
