"""Property-based tests for in-progress session state persistence.

# Feature: workout-tracker, Property 12: In-progress state persistence

Validates: Requirements 10.1, 10.2, 10.3, 10.4
"""

import tempfile
import os
import json

import pytest
from hypothesis import given, settings
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
).map(str.strip).filter(lambda s: len(s) >= 1)

# Valid weight as a string (what the in-progress form would store)
weight_str_strategy = st.one_of(
    st.integers(min_value=1, max_value=9999).map(str),
    st.integers(min_value=5, max_value=99990).map(lambda x: str(x / 10.0)),
    st.just(""),  # empty fields are valid for in-progress state
)

# Valid reps as a string
reps_str_strategy = st.one_of(
    st.integers(min_value=1, max_value=999).map(str),
    st.just(""),  # empty fields are valid for in-progress state
)

# Note text: up to 500 chars
note_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S", "Z")),
    min_size=0,
    max_size=500,
)


@st.composite
def in_progress_state_strategy(draw):
    """Generate random workout state data simulating in-progress form data.

    Produces state with:
    - week: 1-52
    - day: 1-7
    - sets: dict of exercise_name -> { set_number (str) -> { weight: str, reps: str } }
    - notes: dict of exercise_name -> note text string
    """
    week = draw(st.integers(min_value=1, max_value=52))
    day = draw(st.integers(min_value=1, max_value=7))

    # Generate 1-4 unique exercise names
    num_exercises = draw(st.integers(min_value=1, max_value=4))
    exercise_names = draw(
        st.lists(
            exercise_name_strategy,
            min_size=num_exercises,
            max_size=num_exercises,
            unique=True,
        )
    )

    # Generate sets: dict of exercise_name -> { set_number_str -> { weight, reps } }
    sets = {}
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
        exercise_sets = {}
        for set_num in set_numbers:
            weight = draw(weight_str_strategy)
            reps = draw(reps_str_strategy)
            exercise_sets[str(set_num)] = {
                'weight': weight,
                'reps': reps,
            }
        sets[name] = exercise_sets

    # Generate notes: dict of exercise_name -> note text
    notes = {}
    for name in exercise_names:
        note_text = draw(note_strategy)
        notes[name] = note_text

    return {
        'week': week,
        'day': day,
        'sets': sets,
        'notes': notes,
    }


# ============================================================================
# Feature: workout-tracker, Property 12: In-progress state persistence
# Validates: Requirements 10.1, 10.2, 10.3, 10.4
# ============================================================================


@settings(max_examples=100)
@given(state_data=in_progress_state_strategy())
def test_in_progress_state_round_trip(state_data):
    """For any random workout state data (week, day, sets with various
    weights/reps, notes), saving via POST /api/state/save and retrieving
    via GET /api/state/load should produce an exactly equivalent value.

    This validates that in-progress session state survives a browser close
    scenario — the state is synced to the backend, and on reload it can be
    retrieved intact.

    **Validates: Requirements 10.1, 10.2, 10.3, 10.4**
    """
    app, client, cleanup = make_app_and_client()
    try:
        with app.app_context():
            # Save the in-progress state
            save_payload = {
                'key': 'in_progress_workout',
                'value': state_data,
            }
            response = client.post(
                '/api/state/save',
                data=json.dumps(save_payload),
                content_type='application/json',
            )
            assert response.status_code == 200, (
                f"Save state failed: {response.get_json()}"
            )
            result = response.get_json()
            assert result['success'] is True

            # Retrieve the in-progress state (simulating browser reopen)
            response = client.get('/api/state/load')
            assert response.status_code == 200
            loaded = response.get_json()

            # Verify the key matches
            assert loaded['key'] == 'in_progress_workout'

            # Verify the loaded value exactly matches what was saved
            assert loaded['value'] is not None, (
                "Expected saved state to be present, got None"
            )
            assert loaded['value'] == state_data, (
                f"State round-trip mismatch.\n"
                f"Saved: {json.dumps(state_data, indent=2)}\n"
                f"Loaded: {json.dumps(loaded['value'], indent=2)}"
            )
    finally:
        cleanup()
