"""Property-based tests for CSV parsing.

# Feature: workout-tracker, Property 8: CSV parsing round-trip
# Feature: workout-tracker, Property 9: CSV error reporting identifies invalid rows
# Feature: workout-tracker, Property 11: CSV parse summary accuracy

Validates: Requirements 7.2, 7.3, 7.4, 7.6, 7.7
"""

import string

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from csv_parser import parse_csv, ParsedExercise, ParseResult


# --- Strategies ---

# Valid exercise name: non-empty, up to 100 chars, printable, no commas or newlines
# (commas/newlines would break CSV serialization)
exercise_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S", "Z"),
        blacklist_characters=",\n\r\"",
    ),
    min_size=1,
    max_size=100,
).map(str.strip).filter(lambda s: len(s) >= 1 and len(s) <= 100)

# Valid target reps: non-empty text up to 20 chars, no commas or newlines
target_reps_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters=",\n\r\"",
    ),
    min_size=1,
    max_size=20,
).map(str.strip).filter(lambda s: len(s) >= 1 and len(s) <= 20)


@st.composite
def valid_program_strategy(draw):
    """Generate a valid program structure with consistent day counts across weeks."""
    num_weeks = draw(st.integers(min_value=1, max_value=5))
    days_per_week = draw(st.integers(min_value=1, max_value=7))
    # Each week/day has 1-3 exercises to keep test fast
    exercises_per_day = draw(st.integers(min_value=1, max_value=3))

    exercises = []
    for week in range(1, num_weeks + 1):
        for day in range(1, days_per_week + 1):
            for ex_idx in range(exercises_per_day):
                name = draw(exercise_name_strategy)
                sets = draw(st.integers(min_value=1, max_value=10))
                reps = draw(target_reps_strategy)
                exercises.append(ParsedExercise(
                    week=week,
                    day=day,
                    exercise_name=name,
                    sets=sets,
                    target_reps=reps,
                ))

    return exercises, days_per_week


def serialize_to_csv(exercises: list[ParsedExercise]) -> str:
    """Serialize a list of ParsedExercise to a CSV string."""
    lines = ["Week,Day,Exercise,Sets,Target Reps"]
    for ex in exercises:
        # Escape fields that might contain special chars
        name = ex.exercise_name.replace('"', '""')
        reps = ex.target_reps.replace('"', '""')
        # Quote fields if they contain quotes
        if '"' in name:
            name = f'"{name}"'
        if '"' in reps:
            reps = f'"{reps}"'
        lines.append(f"{ex.week},{ex.day},{name},{ex.sets},{reps}")
    return "\n".join(lines)


# --- Property 8: CSV parsing round-trip ---

# Feature: workout-tracker, Property 8: CSV parsing round-trip
# **Validates: Requirements 7.2, 7.3, 7.7**
@given(data=valid_program_strategy())
@settings(max_examples=100)
def test_csv_round_trip(data):
    """For any valid program structure with consistent day counts, serializing
    to CSV and parsing back should produce an equivalent program with correct
    days_per_week."""
    exercises, expected_days_per_week = data

    # Serialize to CSV
    csv_content = serialize_to_csv(exercises)

    # Parse it back
    result = parse_csv(csv_content)

    # Should succeed
    assert result.success, f"Parse failed with errors: {result.errors}"

    # days_per_week should match
    assert result.days_per_week == expected_days_per_week, (
        f"Expected days_per_week={expected_days_per_week}, "
        f"got {result.days_per_week}"
    )

    # Number of exercises should match
    assert len(result.exercises) == len(exercises), (
        f"Expected {len(exercises)} exercises, got {len(result.exercises)}"
    )

    # Each exercise should match (in order since we maintain sort order)
    for orig, parsed in zip(exercises, result.exercises):
        assert parsed.week == orig.week
        assert parsed.day == orig.day
        assert parsed.exercise_name == orig.exercise_name
        assert parsed.sets == orig.sets
        assert parsed.target_reps == orig.target_reps


# --- Property 9: CSV error reporting identifies invalid rows ---

# Feature: workout-tracker, Property 9: CSV error reporting identifies invalid rows
# **Validates: Requirements 7.4, 7.7**

@st.composite
def csv_with_invalid_week(draw):
    """Generate a CSV with an invalid week value in one row."""
    # Generate a valid base exercise
    day = draw(st.integers(min_value=1, max_value=7))
    name = draw(exercise_name_strategy)
    sets = draw(st.integers(min_value=1, max_value=10))
    reps = draw(target_reps_strategy)

    # Generate an invalid week value
    invalid_week = draw(st.one_of(
        st.integers(max_value=0),      # Zero or negative
        st.integers(min_value=53),     # Too large
        st.text(
            alphabet=string.ascii_letters,
            min_size=1,
            max_size=5,
        ),  # Non-numeric
    ))

    # Build CSV with the invalid row
    csv_lines = [
        "Week,Day,Exercise,Sets,Target Reps",
        f"{invalid_week},{day},{name},{sets},{reps}",
    ]
    # Row number of invalid row is 2 (header is 1)
    return "\n".join(csv_lines), 2, "Week"


@st.composite
def csv_with_empty_exercise(draw):
    """Generate a CSV with an empty exercise name in one row."""
    week = draw(st.integers(min_value=1, max_value=52))
    day = draw(st.integers(min_value=1, max_value=7))
    sets = draw(st.integers(min_value=1, max_value=10))
    reps = draw(target_reps_strategy)

    csv_lines = [
        "Week,Day,Exercise,Sets,Target Reps",
        f"{week},{day},,{sets},{reps}",
    ]
    return "\n".join(csv_lines), 2, "Exercise"


@st.composite
def csv_with_invalid_sets(draw):
    """Generate a CSV with an out-of-range sets value."""
    week = draw(st.integers(min_value=1, max_value=52))
    day = draw(st.integers(min_value=1, max_value=7))
    name = draw(exercise_name_strategy)
    reps = draw(target_reps_strategy)

    # Invalid sets: 0, negative, > 10, or non-numeric
    invalid_sets = draw(st.one_of(
        st.integers(max_value=0),
        st.integers(min_value=11),
        st.text(alphabet=string.ascii_letters, min_size=1, max_size=5),
    ))

    csv_lines = [
        "Week,Day,Exercise,Sets,Target Reps",
        f"{week},{day},{name},{invalid_sets},{reps}",
    ]
    return "\n".join(csv_lines), 2, "Sets"


@given(data=csv_with_invalid_week())
@settings(max_examples=100)
def test_csv_error_identifies_invalid_week_rows(data):
    """CSV with invalid week values should be rejected with errors identifying
    the row and field."""
    csv_content, expected_row, expected_field = data

    result = parse_csv(csv_content)

    assert not result.success
    assert len(result.errors) >= 1

    # At least one error should mention the row number
    row_mentioned = any(f"Row {expected_row}" in err for err in result.errors)
    assert row_mentioned, (
        f"Expected error referencing Row {expected_row}, "
        f"got: {result.errors}"
    )

    # Error should mention 'Week'
    field_mentioned = any(expected_field in err for err in result.errors)
    assert field_mentioned, (
        f"Expected error mentioning '{expected_field}', "
        f"got: {result.errors}"
    )


@given(data=csv_with_empty_exercise())
@settings(max_examples=100)
def test_csv_error_identifies_empty_exercise(data):
    """CSV with empty exercise names should be rejected with errors identifying
    the row and field."""
    csv_content, expected_row, expected_field = data

    result = parse_csv(csv_content)

    assert not result.success
    assert len(result.errors) >= 1

    row_mentioned = any(f"Row {expected_row}" in err for err in result.errors)
    assert row_mentioned, (
        f"Expected error referencing Row {expected_row}, "
        f"got: {result.errors}"
    )

    field_mentioned = any(expected_field in err for err in result.errors)
    assert field_mentioned, (
        f"Expected error mentioning '{expected_field}', "
        f"got: {result.errors}"
    )


@given(data=csv_with_invalid_sets())
@settings(max_examples=100)
def test_csv_error_identifies_invalid_sets(data):
    """CSV with invalid sets values should be rejected with errors identifying
    the row and field."""
    csv_content, expected_row, expected_field = data

    result = parse_csv(csv_content)

    assert not result.success
    assert len(result.errors) >= 1

    row_mentioned = any(f"Row {expected_row}" in err for err in result.errors)
    assert row_mentioned, (
        f"Expected error referencing Row {expected_row}, "
        f"got: {result.errors}"
    )

    field_mentioned = any(expected_field in err for err in result.errors)
    assert field_mentioned, (
        f"Expected error mentioning '{expected_field}', "
        f"got: {result.errors}"
    )


@st.composite
def csv_with_inconsistent_days(draw):
    """Generate a CSV where Week 2 has a different number of days than Week 1."""
    days_week1 = draw(st.integers(min_value=1, max_value=6))
    # Week 2 has a different number of days
    days_week2 = draw(
        st.integers(min_value=1, max_value=7).filter(lambda d: d != days_week1)
    )

    name = draw(exercise_name_strategy)
    sets = draw(st.integers(min_value=1, max_value=10))
    reps = draw(target_reps_strategy)

    lines = ["Week,Day,Exercise,Sets,Target Reps"]

    # Week 1: days_week1 days
    for day in range(1, days_week1 + 1):
        lines.append(f"1,{day},{name},{sets},{reps}")

    # Week 2: days_week2 days (different count)
    for day in range(1, days_week2 + 1):
        lines.append(f"2,{day},{name},{sets},{reps}")

    return "\n".join(lines), days_week1, days_week2


@given(data=csv_with_inconsistent_days())
@settings(max_examples=100)
def test_csv_error_identifies_inconsistent_week_days(data):
    """CSV with inconsistent day counts across weeks should be rejected with an
    error identifying the inconsistent week."""
    csv_content, days_week1, days_week2 = data

    result = parse_csv(csv_content)

    assert not result.success
    assert len(result.errors) >= 1

    # Error should mention "Week 2"
    week_mentioned = any("Week 2" in err for err in result.errors)
    assert week_mentioned, (
        f"Expected error mentioning 'Week 2', got: {result.errors}"
    )

    # Error should reference the expected vs actual day counts
    count_mentioned = any(
        str(days_week2) in err and str(days_week1) in err
        for err in result.errors
    )
    assert count_mentioned, (
        f"Expected error mentioning {days_week2} and {days_week1} days, "
        f"got: {result.errors}"
    )


# --- Property 11: CSV parse summary accuracy ---

# Feature: workout-tracker, Property 11: CSV parse summary accuracy
# **Validates: Requirements 7.6**

@given(data=valid_program_strategy())
@settings(max_examples=100)
def test_csv_parse_summary_accuracy(data):
    """For any successfully parsed CSV, the reported counts (days_per_week,
    distinct weeks, total exercises) should exactly match the actual parsed data."""
    exercises, expected_days_per_week = data

    csv_content = serialize_to_csv(exercises)
    result = parse_csv(csv_content)

    assert result.success, f"Parse failed: {result.errors}"

    # days_per_week matches distinct days in Week 1
    week1_days = set(ex.day for ex in result.exercises if ex.week == 1)
    assert result.days_per_week == len(week1_days), (
        f"days_per_week={result.days_per_week} but Week 1 has "
        f"{len(week1_days)} distinct days"
    )

    # Total exercise count matches
    assert len(result.exercises) == len(exercises), (
        f"Expected {len(exercises)} exercises, got {len(result.exercises)}"
    )

    # Distinct weeks count matches
    expected_weeks = set(ex.week for ex in exercises)
    actual_weeks = set(ex.week for ex in result.exercises)
    assert actual_weeks == expected_weeks, (
        f"Expected weeks {expected_weeks}, got {actual_weeks}"
    )

    # Verify days_per_week matches for all weeks (consistency)
    for week_num in actual_weeks:
        week_days = set(ex.day for ex in result.exercises if ex.week == week_num)
        assert len(week_days) == result.days_per_week, (
            f"Week {week_num} has {len(week_days)} days but "
            f"days_per_week is {result.days_per_week}"
        )
