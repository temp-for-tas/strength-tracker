"""Property-based tests for the validators module.

Uses Hypothesis to test universal properties of weight, reps, and note validators.
Each property test runs at least 100 iterations.
"""

import string

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from validators import validate_weight, validate_reps, validate_note


# ============================================================================
# Feature: workout-tracker, Property 2: Weight validation accepts valid and rejects invalid
# Validates: Requirements 2.3, 2.6
# ============================================================================


@settings(max_examples=200)
@given(
    integer_part=st.integers(min_value=1, max_value=9999),
)
def test_weight_valid_integers_accepted(integer_part):
    """Valid integer weights between 1 and 9999 are accepted."""
    is_valid, parsed, err = validate_weight(str(integer_part))
    assert is_valid is True
    assert parsed == float(integer_part)
    assert err is None


@settings(max_examples=200)
@given(
    integer_part=st.integers(min_value=0, max_value=9998),
    decimal_digit=st.integers(min_value=0, max_value=9),
)
def test_weight_valid_one_decimal_accepted(integer_part, decimal_digit):
    """Valid weights with one decimal place between 0.5 and 9999 are accepted."""
    weight_str = f"{integer_part}.{decimal_digit}"
    weight_float = float(weight_str)
    assume(0.5 <= weight_float <= 9999)

    is_valid, parsed, err = validate_weight(weight_str)
    assert is_valid is True
    assert parsed == weight_float
    assert err is None


@settings(max_examples=200)
@given(
    value=st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False),
)
def test_weight_below_minimum_rejected(value):
    """Negative weights are rejected (minimum is 0)."""
    is_valid, parsed, err = validate_weight(value)
    assert is_valid is False
    assert parsed is None
    assert err is not None


@settings(max_examples=200)
@given(
    value=st.floats(min_value=9999.1, max_value=1e10, allow_nan=False, allow_infinity=False),
)
def test_weight_above_maximum_rejected(value):
    """Weights above 9999 are rejected."""
    is_valid, parsed, err = validate_weight(value)
    assert is_valid is False
    assert parsed is None
    assert err is not None


@settings(max_examples=200)
@given(
    text=st.text(
        alphabet=st.sampled_from(string.ascii_letters + "!@#$%^&*()_+-=[]{}|;:',<>?/~`"),
        min_size=1,
        max_size=20,
    )
)
def test_weight_non_numeric_strings_rejected(text):
    """Non-numeric strings are rejected as weights."""
    # Ensure it can't be parsed as a float
    try:
        float(text)
        assume(False)  # Skip if it accidentally parses as a float
    except (ValueError, TypeError):
        pass

    is_valid, parsed, err = validate_weight(text)
    assert is_valid is False
    assert parsed is None
    assert err is not None


@settings(max_examples=200)
@given(
    integer_part=st.integers(min_value=0, max_value=9998),
    decimal_digits=st.text(alphabet="0123456789", min_size=2, max_size=5),
)
def test_weight_more_than_one_decimal_rejected(integer_part, decimal_digits):
    """Weights with more than one decimal place are rejected."""
    # Ensure last digit is non-zero so trailing zeros don't reduce decimal places
    assume(decimal_digits[-1] != '0')
    weight_str = f"{integer_part}.{decimal_digits}"
    weight_float = float(weight_str)
    assume(0.5 <= weight_float <= 9999)

    is_valid, parsed, err = validate_weight(weight_str)
    assert is_valid is False
    assert parsed is None
    assert err is not None


# ============================================================================
# Feature: workout-tracker, Property 3: Reps validation accepts valid and rejects invalid
# Validates: Requirements 2.4, 2.7
# ============================================================================


@settings(max_examples=200)
@given(
    reps=st.integers(min_value=1, max_value=999),
)
def test_reps_valid_integers_accepted(reps):
    """Valid integer reps between 1 and 999 are accepted."""
    is_valid, parsed, err = validate_reps(reps)
    assert is_valid is True
    assert parsed == reps
    assert err is None


@settings(max_examples=200)
@given(
    reps=st.integers(min_value=1, max_value=999),
)
def test_reps_valid_string_integers_accepted(reps):
    """Valid integer reps passed as strings are accepted."""
    is_valid, parsed, err = validate_reps(str(reps))
    assert is_valid is True
    assert parsed == reps
    assert err is None


@settings(max_examples=200)
@given(
    value=st.integers(max_value=-1),
)
def test_reps_below_minimum_rejected(value):
    """Negative reps are rejected (minimum is 0)."""
    is_valid, parsed, err = validate_reps(value)
    assert is_valid is False
    assert parsed is None
    assert err is not None


@settings(max_examples=200)
@given(
    value=st.integers(min_value=1000, max_value=100000),
)
def test_reps_above_maximum_rejected(value):
    """Reps above 999 are rejected."""
    is_valid, parsed, err = validate_reps(value)
    assert is_valid is False
    assert parsed is None
    assert err is not None


@settings(max_examples=200)
@given(
    integer_part=st.integers(min_value=1, max_value=998),
    fractional_part=st.integers(min_value=1, max_value=99),
)
def test_reps_floats_rejected(integer_part, fractional_part):
    """Non-integer float values are rejected as reps."""
    float_str = f"{integer_part}.{fractional_part}"
    # Make sure it's actually non-integer
    assume(float(float_str) != int(float(float_str)))

    is_valid, parsed, err = validate_reps(float_str)
    assert is_valid is False
    assert parsed is None
    assert err is not None


@settings(max_examples=200)
@given(
    text=st.text(
        alphabet=st.sampled_from(string.ascii_letters + "!@#$%^&*()_+-=[]{}|;:',<>?/~`"),
        min_size=1,
        max_size=20,
    )
)
def test_reps_non_numeric_strings_rejected(text):
    """Non-numeric strings are rejected as reps."""
    try:
        float(text)
        assume(False)
    except (ValueError, TypeError):
        pass

    is_valid, parsed, err = validate_reps(text)
    assert is_valid is False
    assert parsed is None
    assert err is not None


# ============================================================================
# Feature: workout-tracker, Property 4: Note length enforcement
# Validates: Requirements 3.2
# ============================================================================


@settings(max_examples=200)
@given(
    note=st.text(min_size=0, max_size=500),
)
def test_note_within_limit_accepted(note):
    """Notes of 500 characters or fewer are accepted."""
    is_valid, parsed, err = validate_note(note)
    assert is_valid is True
    assert parsed == note
    assert err is None


@settings(max_examples=200)
@given(
    length=st.integers(min_value=501, max_value=2000),
)
def test_note_exceeding_limit_rejected(length):
    """Notes exceeding 500 characters are rejected."""
    note = "a" * length
    is_valid, parsed, err = validate_note(note)
    assert is_valid is False
    assert parsed is None
    assert err is not None


@settings(max_examples=100)
@given(
    note=st.text(min_size=501, max_size=1000),
)
def test_note_over_500_any_content_rejected(note):
    """Any string content over 500 characters is rejected regardless of content."""
    is_valid, parsed, err = validate_note(note)
    assert is_valid is False
    assert parsed is None
    assert err is not None


def test_note_none_accepted():
    """None is treated as an empty string and accepted."""
    is_valid, parsed, err = validate_note(None)
    assert is_valid is True
    assert parsed == ""
    assert err is None
