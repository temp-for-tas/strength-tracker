"""Unit tests for the validators module."""
import pytest
from validators import validate_weight, validate_reps, validate_note, validate_session


class TestValidateWeight:
    """Tests for validate_weight function."""

    def test_accepts_minimum_weight(self):
        is_valid, value, err = validate_weight(0.5)
        assert is_valid is True
        assert value == 0.5
        assert err is None

    def test_accepts_maximum_weight(self):
        is_valid, value, err = validate_weight(9999)
        assert is_valid is True
        assert value == 9999.0
        assert err is None

    def test_accepts_integer_weight(self):
        is_valid, value, err = validate_weight(100)
        assert is_valid is True
        assert value == 100.0
        assert err is None

    def test_accepts_one_decimal_place(self):
        is_valid, value, err = validate_weight("35.5")
        assert is_valid is True
        assert value == 35.5
        assert err is None

    def test_accepts_string_numeric(self):
        is_valid, value, err = validate_weight("225")
        assert is_valid is True
        assert value == 225.0
        assert err is None

    def test_rejects_two_decimal_places(self):
        is_valid, value, err = validate_weight("35.55")
        assert is_valid is False
        assert value is None
        assert err is not None

    def test_accepts_zero(self):
        """Zero is now valid — used for bodyweight exercises."""
        is_valid, value, err = validate_weight(0)
        assert is_valid is True
        assert value == 0.0
        assert err is None

    def test_rejects_negative(self):
        is_valid, value, err = validate_weight(-5)
        assert is_valid is False
        assert value is None
        assert err is not None

    def test_accepts_below_old_minimum(self):
        """Values like 0.4 are now valid (new minimum is 0)."""
        is_valid, value, err = validate_weight(0.4)
        assert is_valid is True
        assert value == 0.4
        assert err is None

    def test_rejects_above_maximum(self):
        is_valid, value, err = validate_weight(10000)
        assert is_valid is False
        assert value is None
        assert err is not None

    def test_rejects_non_numeric_string(self):
        is_valid, value, err = validate_weight("abc")
        assert is_valid is False
        assert value is None
        assert err is not None

    def test_accepts_empty_string_as_zero(self):
        """Empty string is valid — defaults to 0 (weight is optional)."""
        is_valid, value, err = validate_weight("")
        assert is_valid is True
        assert value == 0.0
        assert err is None

    def test_accepts_none_as_zero(self):
        """None is valid — defaults to 0 (weight is optional)."""
        is_valid, value, err = validate_weight(None)
        assert is_valid is True
        assert value == 0.0
        assert err is None

    def test_accepts_whole_number_as_string(self):
        is_valid, value, err = validate_weight("1")
        assert is_valid is True
        assert value == 1.0
        assert err is None

    def test_rejects_three_decimal_places(self):
        is_valid, value, err = validate_weight("10.123")
        assert is_valid is False
        assert value is None
        assert err is not None


class TestValidateReps:
    """Tests for validate_reps function."""

    def test_accepts_minimum_reps(self):
        is_valid, value, err = validate_reps(1)
        assert is_valid is True
        assert value == 1
        assert err is None

    def test_accepts_maximum_reps(self):
        is_valid, value, err = validate_reps(999)
        assert is_valid is True
        assert value == 999
        assert err is None

    def test_accepts_typical_reps(self):
        is_valid, value, err = validate_reps(8)
        assert is_valid is True
        assert value == 8
        assert err is None

    def test_accepts_string_integer(self):
        is_valid, value, err = validate_reps("12")
        assert is_valid is True
        assert value == 12
        assert err is None

    def test_accepts_zero(self):
        """Zero reps is valid — indicates a skipped set."""
        is_valid, value, err = validate_reps(0)
        assert is_valid is True
        assert value == 0
        assert err is None

    def test_rejects_negative(self):
        is_valid, value, err = validate_reps(-1)
        assert is_valid is False
        assert value is None
        assert err is not None

    def test_rejects_above_maximum(self):
        is_valid, value, err = validate_reps(1000)
        assert is_valid is False
        assert value is None
        assert err is not None

    def test_rejects_float(self):
        is_valid, value, err = validate_reps(8.5)
        assert is_valid is False
        assert value is None
        assert err is not None

    def test_rejects_non_numeric_string(self):
        is_valid, value, err = validate_reps("abc")
        assert is_valid is False
        assert value is None
        assert err is not None

    def test_rejects_empty_string(self):
        is_valid, value, err = validate_reps("")
        assert is_valid is False
        assert value is None
        assert err is not None

    def test_rejects_none(self):
        is_valid, value, err = validate_reps(None)
        assert is_valid is False
        assert value is None
        assert err is not None

    def test_accepts_float_that_is_whole_number(self):
        """A float like 8.0 represents integer 8."""
        is_valid, value, err = validate_reps("8.0")
        assert is_valid is True
        assert value == 8
        assert err is None


class TestValidateNote:
    """Tests for validate_note function."""

    def test_accepts_empty_string(self):
        is_valid, value, err = validate_note("")
        assert is_valid is True
        assert value == ""
        assert err is None

    def test_accepts_none_as_empty(self):
        is_valid, value, err = validate_note(None)
        assert is_valid is True
        assert value == ""
        assert err is None

    def test_accepts_short_note(self):
        is_valid, value, err = validate_note("Felt good today")
        assert is_valid is True
        assert value == "Felt good today"
        assert err is None

    def test_accepts_500_characters(self):
        note = "a" * 500
        is_valid, value, err = validate_note(note)
        assert is_valid is True
        assert value == note
        assert err is None

    def test_rejects_501_characters(self):
        note = "a" * 501
        is_valid, value, err = validate_note(note)
        assert is_valid is False
        assert value is None
        assert err is not None

    def test_rejects_non_string(self):
        is_valid, value, err = validate_note(123)
        assert is_valid is False
        assert value is None
        assert err is not None


class TestValidateSession:
    """Tests for validate_session function."""

    def test_accepts_valid_session(self):
        data = {
            "week": 1,
            "day": 1,
            "sets": [
                {"exercise_name": "Bench Press", "set_number": 1, "weight": 135.0, "reps": 8}
            ],
            "notes": [
                {"exercise_name": "Bench Press", "note": "Felt strong"}
            ]
        }
        is_valid, errors = validate_session(data)
        assert is_valid is True
        assert errors == []

    def test_accepts_session_with_empty_sets_and_notes(self):
        data = {
            "week": 1,
            "day": 1,
            "sets": [],
            "notes": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is True
        assert errors == []

    def test_rejects_missing_week(self):
        data = {
            "day": 1,
            "sets": [],
            "notes": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is False
        assert any("week" in e for e in errors)

    def test_rejects_missing_day(self):
        data = {
            "week": 1,
            "sets": [],
            "notes": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is False
        assert any("day" in e for e in errors)

    def test_rejects_missing_sets(self):
        data = {
            "week": 1,
            "day": 1,
            "notes": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is False
        assert any("sets" in e for e in errors)

    def test_rejects_missing_notes(self):
        data = {
            "week": 1,
            "day": 1,
            "sets": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is False
        assert any("notes" in e for e in errors)

    def test_rejects_invalid_week_type(self):
        data = {
            "week": "one",
            "day": 1,
            "sets": [],
            "notes": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is False
        assert any("week" in e and "integer" in e for e in errors)

    def test_rejects_week_out_of_range(self):
        data = {
            "week": 53,
            "day": 1,
            "sets": [],
            "notes": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is False
        assert any("week" in e for e in errors)

    def test_rejects_day_out_of_range(self):
        data = {
            "week": 1,
            "day": 8,
            "sets": [],
            "notes": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is False
        assert any("day" in e for e in errors)

    def test_rejects_invalid_set_entry(self):
        data = {
            "week": 1,
            "day": 1,
            "sets": [
                {"exercise_name": "Squat", "set_number": 1, "weight": -5, "reps": 8}
            ],
            "notes": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is False
        assert any("sets[0]" in e for e in errors)

    def test_accepts_zero_reps_in_set(self):
        """Zero reps is valid — means user explicitly skipped the set."""
        data = {
            "week": 1,
            "day": 1,
            "sets": [
                {"exercise_name": "Squat", "set_number": 1, "weight": 100, "reps": 0}
            ],
            "notes": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is True
        assert errors == []

    def test_rejects_note_too_long(self):
        data = {
            "week": 1,
            "day": 1,
            "sets": [],
            "notes": [
                {"exercise_name": "Squat", "note": "a" * 501}
            ]
        }
        is_valid, errors = validate_session(data)
        assert is_valid is False
        assert any("notes[0]" in e for e in errors)

    def test_rejects_non_dict_input(self):
        is_valid, errors = validate_session("not a dict")
        assert is_valid is False
        assert any("JSON object" in e for e in errors)

    def test_rejects_boolean_as_week(self):
        """Booleans should not be accepted as integers."""
        data = {
            "week": True,
            "day": 1,
            "sets": [],
            "notes": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is False
        assert any("week" in e for e in errors)

    def test_accepts_multiple_sets(self):
        data = {
            "week": 1,
            "day": 1,
            "sets": [
                {"exercise_name": "Bench Press", "set_number": 1, "weight": 135.0, "reps": 8},
                {"exercise_name": "Bench Press", "set_number": 2, "weight": 135.0, "reps": 7},
                {"exercise_name": "Bench Press", "set_number": 3, "weight": 130.0, "reps": 6},
            ],
            "notes": [
                {"exercise_name": "Bench Press", "note": "Good session"}
            ]
        }
        is_valid, errors = validate_session(data)
        assert is_valid is True
        assert errors == []

    def test_rejects_set_number_out_of_range(self):
        data = {
            "week": 1,
            "day": 1,
            "sets": [
                {"exercise_name": "Squat", "set_number": 11, "weight": 100, "reps": 5}
            ],
            "notes": []
        }
        is_valid, errors = validate_session(data)
        assert is_valid is False
        assert any("set_number" in e for e in errors)
