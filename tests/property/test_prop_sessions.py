"""Property-based tests for session recording, history, and previous performance.

# Feature: workout-tracker, Property 5: Session data round-trip
# Feature: workout-tracker, Property 6: History ordering
# Feature: workout-tracker, Property 7: Previous performance returns most recent session

Validates: Requirements 4.2, 3.3, 4.5, 5.2, 6.1
"""

import tempfile
import os
import json
from datetime import datetime, timedelta

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

# Valid exercise names (non-empty, printable, up to 50 chars)
exercise_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters='\x00',
    ),
    min_size=1,
    max_size=50,
).map(str.strip).filter(lambda s: 1 <= len(s) <= 100)

# Valid weight: 0.5 to 9999, one decimal place
valid_weight_strategy = st.one_of(
    st.integers(min_value=1, max_value=9999).map(float),
    st.integers(min_value=5, max_value=99990).map(lambda x: x / 10.0),
).filter(lambda w: 0.5 <= w <= 9999)

# Valid reps: integers 1 to 999
valid_reps_strategy = st.integers(min_value=1, max_value=999)

# Valid note: up to 500 chars
valid_note_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S", "Z")),
    min_size=0,
    max_size=500,
)


@st.composite
def valid_session_strategy(draw):
    """Generate a valid session payload with random exercises, sets, and notes."""
    week = draw(st.integers(min_value=1, max_value=52))
    day = draw(st.integers(min_value=1, max_value=7))

    # Generate 1-3 unique exercise names
    num_exercises = draw(st.integers(min_value=1, max_value=3))
    exercise_names = draw(
        st.lists(
            exercise_name_strategy,
            min_size=num_exercises,
            max_size=num_exercises,
            unique=True,
        )
    )

    # Generate sets: each exercise has 1-4 sets with unique set_numbers
    sets = []
    for name in exercise_names:
        num_sets = draw(st.integers(min_value=1, max_value=4))
        set_numbers = draw(
            st.lists(
                st.integers(min_value=1, max_value=4),
                min_size=num_sets,
                max_size=num_sets,
                unique=True,
            )
        )
        for set_num in set_numbers:
            weight = draw(valid_weight_strategy)
            reps = draw(valid_reps_strategy)
            sets.append({
                'exercise_name': name,
                'set_number': set_num,
                'weight': weight,
                'reps': reps,
            })

    # Generate notes: each exercise gets a note
    notes = []
    for name in exercise_names:
        note_text = draw(valid_note_strategy)
        notes.append({
            'exercise_name': name,
            'note': note_text,
        })

    return {
        'week': week,
        'day': day,
        'sets': sets,
        'notes': notes,
    }


# ============================================================================
# Feature: workout-tracker, Property 5: Session data round-trip
# Validates: Requirements 4.2, 3.3, 4.5
# ============================================================================


@settings(max_examples=100)
@given(session_data=valid_session_strategy())
def test_session_data_round_trip(session_data):
    """For any valid workout session, saving via the API and then retrieving
    it should produce data equivalent to what was submitted — all set entries
    with matching exercise names, set numbers, weights, and reps, plus all
    notes with matching text.

    **Validates: Requirements 4.2, 3.3, 4.5**
    """
    app, client, cleanup = make_app_and_client()
    try:
        with app.app_context():
            # Save the session
            response = client.post(
                '/api/sessions',
                data=json.dumps(session_data),
                content_type='application/json',
            )
            assert response.status_code == 201, (
                f"Save failed: {response.get_json()}"
            )
            result = response.get_json()
            assert result['success'] is True
            session_id = result['session_id']

            # Retrieve the session
            response = client.get(f'/api/sessions/{session_id}')
            assert response.status_code == 200
            retrieved = response.get_json()

            # Verify week and day match
            assert retrieved['week'] == session_data['week']
            assert retrieved['day'] == session_data['day']

            # Verify sets match
            submitted_sets = session_data['sets']
            retrieved_exercises = retrieved['exercises']

            for submitted_set in submitted_sets:
                exercise_name = submitted_set['exercise_name']
                assert exercise_name in retrieved_exercises, (
                    f"Exercise '{exercise_name}' not found in retrieved data. "
                    f"Available: {list(retrieved_exercises.keys())}"
                )

                exercise_data = retrieved_exercises[exercise_name]
                # Find the matching set by set_number
                matching_sets = [
                    s for s in exercise_data['sets']
                    if s['set_number'] == submitted_set['set_number']
                ]
                assert len(matching_sets) == 1, (
                    f"Expected 1 set with set_number={submitted_set['set_number']} "
                    f"for '{exercise_name}', found {len(matching_sets)}"
                )

                retrieved_set = matching_sets[0]
                assert retrieved_set['weight'] == pytest.approx(
                    submitted_set['weight'], abs=0.01
                ), (
                    f"Weight mismatch for {exercise_name} set "
                    f"{submitted_set['set_number']}: "
                    f"submitted={submitted_set['weight']}, "
                    f"retrieved={retrieved_set['weight']}"
                )
                assert retrieved_set['reps'] == submitted_set['reps'], (
                    f"Reps mismatch for {exercise_name} set "
                    f"{submitted_set['set_number']}: "
                    f"submitted={submitted_set['reps']}, "
                    f"retrieved={retrieved_set['reps']}"
                )

            # Verify total set count matches
            total_retrieved_sets = sum(
                len(ex['sets']) for ex in retrieved_exercises.values()
            )
            assert total_retrieved_sets == len(submitted_sets), (
                f"Total set count mismatch: submitted {len(submitted_sets)}, "
                f"retrieved {total_retrieved_sets}"
            )

            # Verify notes match
            for submitted_note in session_data['notes']:
                exercise_name = submitted_note['exercise_name']
                assert exercise_name in retrieved_exercises, (
                    f"Exercise '{exercise_name}' not found for note verification"
                )
                retrieved_note = retrieved_exercises[exercise_name]['note']
                assert retrieved_note == submitted_note['note'], (
                    f"Note mismatch for '{exercise_name}': "
                    f"submitted='{submitted_note['note']}', "
                    f"retrieved='{retrieved_note}'"
                )
    finally:
        cleanup()


# ============================================================================
# Feature: workout-tracker, Property 6: History ordering
# Validates: Requirements 5.2
# ============================================================================


@st.composite
def sessions_with_timestamps_strategy(draw):
    """Generate multiple sessions with distinct timestamps for direct DB insertion."""
    num_sessions = draw(st.integers(min_value=2, max_value=10))

    # Generate distinct timestamps by using a base time and random offsets
    base_time = datetime(2025, 1, 1, 8, 0)
    offsets = draw(
        st.lists(
            st.integers(min_value=0, max_value=525600),  # up to 1 year in minutes
            min_size=num_sessions,
            max_size=num_sessions,
            unique=True,
        )
    )

    sessions = []
    for offset in offsets:
        timestamp = base_time + timedelta(minutes=offset)
        week = draw(st.integers(min_value=1, max_value=52))
        day = draw(st.integers(min_value=1, max_value=7))
        sessions.append({
            'week': week,
            'day': day,
            'completed_at': timestamp.strftime('%Y-%m-%dT%H:%M'),
        })

    return sessions


@settings(max_examples=100)
@given(sessions=sessions_with_timestamps_strategy())
def test_history_ordering_descending(sessions):
    """For any collection of saved workout sessions with distinct timestamps,
    retrieving the history list should return sessions ordered by date
    descending (most recent first).

    **Validates: Requirements 5.2**
    """
    app, client, cleanup = make_app_and_client()
    try:
        with app.app_context():
            db = get_db()

            # Insert sessions directly into DB with controlled timestamps
            for session_data in sessions:
                db.execute(
                    'INSERT INTO sessions (week, day, completed_at) VALUES (?, ?, ?)',
                    (session_data['week'], session_data['day'],
                     session_data['completed_at'])
                )
            db.commit()

            # Retrieve history via API
            response = client.get('/api/sessions')
            assert response.status_code == 200
            result = response.get_json()

            retrieved_sessions = result['sessions']
            assert len(retrieved_sessions) == len(sessions)

            # Verify descending order by completed_at
            timestamps = [s['completed_at'] for s in retrieved_sessions]
            for i in range(len(timestamps) - 1):
                assert timestamps[i] >= timestamps[i + 1], (
                    f"History not in descending order: "
                    f"'{timestamps[i]}' should be >= '{timestamps[i + 1]}' "
                    f"at positions {i} and {i + 1}"
                )
    finally:
        cleanup()


# ============================================================================
# Feature: workout-tracker, Property 7: Previous performance returns most recent session
# Validates: Requirements 6.1
# ============================================================================


@st.composite
def multiple_sessions_same_day_strategy(draw):
    """Generate multiple sessions for the same week/day with distinct timestamps."""
    week = draw(st.integers(min_value=1, max_value=52))
    day = draw(st.integers(min_value=1, max_value=7))
    num_sessions = draw(st.integers(min_value=2, max_value=6))

    # Generate distinct timestamps
    base_time = datetime(2025, 1, 1, 8, 0)
    offsets = draw(
        st.lists(
            st.integers(min_value=0, max_value=525600),
            min_size=num_sessions,
            max_size=num_sessions,
            unique=True,
        )
    )

    # Determine which offset is the most recent (largest)
    most_recent_offset = max(offsets)

    # Generate a unique exercise name for identification
    exercise_name = draw(exercise_name_strategy)

    sessions = []
    for offset in offsets:
        timestamp = base_time + timedelta(minutes=offset)
        # Use different reps for each session to identify which one is returned
        reps = draw(st.integers(min_value=1, max_value=999))
        weight = draw(valid_weight_strategy)

        sessions.append({
            'week': week,
            'day': day,
            'completed_at': timestamp.strftime('%Y-%m-%dT%H:%M'),
            'exercise_name': exercise_name,
            'weight': weight,
            'reps': reps,
            'is_most_recent': (offset == most_recent_offset),
        })

    return week, day, sessions


@settings(max_examples=100)
@given(data=multiple_sessions_same_day_strategy())
def test_previous_performance_returns_most_recent(data):
    """For any workout day completed multiple times, querying previous
    performance should return data from the most recently completed session
    (by timestamp), not any earlier session.

    **Validates: Requirements 6.1**
    """
    week, day, sessions = data

    app, client, cleanup = make_app_and_client()
    try:
        with app.app_context():
            db = get_db()

            # Insert all sessions directly into DB
            most_recent_session_id = None
            for session_data in sessions:
                cursor = db.execute(
                    'INSERT INTO sessions (week, day, completed_at) VALUES (?, ?, ?)',
                    (session_data['week'], session_data['day'],
                     session_data['completed_at'])
                )
                session_id = cursor.lastrowid

                # Insert a set entry for this session
                db.execute(
                    '''INSERT INTO set_entries
                       (session_id, exercise_name, set_number, weight, reps)
                       VALUES (?, ?, ?, ?, ?)''',
                    (session_id, session_data['exercise_name'], 1,
                     session_data['weight'], session_data['reps'])
                )

                if session_data['is_most_recent']:
                    most_recent_session_id = session_id

            db.commit()

            # Query previous performance
            response = client.get(f'/api/sessions/previous/{week}/{day}')
            assert response.status_code == 200
            result = response.get_json()

            # Should return the most recent session
            assert result['session_id'] == most_recent_session_id, (
                f"Expected session_id={most_recent_session_id}, "
                f"got {result['session_id']}"
            )

            # Verify the returned session has the correct timestamp
            most_recent_data = next(
                s for s in sessions if s['is_most_recent']
            )
            assert result['completed_at'] == most_recent_data['completed_at'], (
                f"Timestamp mismatch: expected '{most_recent_data['completed_at']}', "
                f"got '{result['completed_at']}'"
            )

            # Verify the exercise data matches the most recent session
            exercise_name = most_recent_data['exercise_name']
            assert exercise_name in result['exercises'], (
                f"Exercise '{exercise_name}' not in returned exercises"
            )
            returned_sets = result['exercises'][exercise_name]['sets']
            assert len(returned_sets) >= 1
            assert returned_sets[0]['weight'] == pytest.approx(
                most_recent_data['weight'], abs=0.01
            )
            assert returned_sets[0]['reps'] == most_recent_data['reps']
    finally:
        cleanup()
