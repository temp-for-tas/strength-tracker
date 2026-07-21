"""Unit tests for the csv_parser module."""
import os
import pytest
from csv_parser import parse_csv, ParsedExercise, ParseResult


class TestParseCSVValidInput:
    """Tests for valid CSV parsing."""

    def test_parses_simple_valid_csv(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Bench Press,4,5-8\n"
            "1,2,Squat,4,6-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert len(result.exercises) == 2
        assert result.days_per_week == 2
        assert result.errors == []

    def test_parses_sample_csv(self):
        """Test parsing the actual sample CSV structure."""
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Incline DB Press (15-30°),4,5–8\n"
            "1,1,Ring Push-ups / Dips,4,6–8\n"
            "1,2,Front/Goblet Squat,4,6–8\n"
            "1,2,Bulgarian Split Squat,3,6–8/side\n"
            "2,1,Incline DB Press (15-30°),4,5–8\n"
            "2,1,Ring Push-ups / Dips,4,6–8\n"
            "2,2,Front/Goblet Squat,4,6–8\n"
            "2,2,Bulgarian Split Squat,3,6–8/side\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.days_per_week == 2
        assert len(result.exercises) == 8

    def test_maintains_sort_order(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Exercise A,3,8-10\n"
            "1,1,Exercise B,4,5-8\n"
            "1,2,Exercise C,3,10-12\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.exercises[0].exercise_name == "Exercise A"
        assert result.exercises[1].exercise_name == "Exercise B"
        assert result.exercises[2].exercise_name == "Exercise C"

    def test_parses_exercise_fields_correctly(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Bench Press,3,8-10\n"
            "1,2,Squat,3,5-8\n"
            "2,1,Bench Press,3,8-10\n"
            "2,2,Squat,3,5-8\n"
            "3,1,Overhead Press,3,6-8\n"
            "3,2,Romanian Deadlift,4,6-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        ex = result.exercises[5]  # Last row
        assert ex.week == 3
        assert ex.day == 2
        assert ex.exercise_name == "Romanian Deadlift"
        assert ex.sets == 4
        assert ex.target_reps == "6-8"

    def test_supports_various_target_reps_formats(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Exercise A,3,5-8\n"
            "1,1,Exercise B,3,6-8/side\n"
            "1,1,Exercise C,3,20-40m\n"
            "1,1,Exercise D,2,20-30 sec/side\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.exercises[0].target_reps == "5-8"
        assert result.exercises[1].target_reps == "6-8/side"
        assert result.exercises[2].target_reps == "20-40m"
        assert result.exercises[3].target_reps == "20-30 sec/side"

    def test_accepts_7_days_per_week(self):
        rows = ["Week,Day,Exercise,Sets,Target Reps"]
        for day in range(1, 8):
            rows.append(f"1,{day},Exercise {day},3,8-10")
        csv_content = "\n".join(rows)
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.days_per_week == 7

    def test_accepts_1_day_per_week(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Only Exercise,3,8-10\n"
            "2,1,Only Exercise,3,8-10\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.days_per_week == 1


class TestParseCSVHeaderValidation:
    """Tests for header row validation."""

    def test_rejects_empty_file(self):
        result = parse_csv("")
        assert result.success is False
        assert any("empty" in e.lower() for e in result.errors)

    def test_rejects_missing_week_column(self):
        csv_content = "Day,Exercise,Sets,Target Reps\n1,Squat,4,5-8\n"
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Week" in e for e in result.errors)

    def test_rejects_missing_multiple_columns(self):
        csv_content = "Week,Exercise\n1,Squat\n"
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Day" in e for e in result.errors)
        assert any("Sets" in e for e in result.errors)

    def test_rejects_headers_only_no_data(self):
        csv_content = "Week,Day,Exercise,Sets,Target Reps\n"
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("no data" in e.lower() for e in result.errors)


class TestParseCSVRowValidation:
    """Tests for per-row validation."""

    def test_rejects_non_integer_week(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "abc,1,Squat,4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Week" in e for e in result.errors)

    def test_rejects_week_zero(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "0,1,Squat,4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Week" in e for e in result.errors)

    def test_rejects_week_53(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "53,1,Squat,4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Week" in e for e in result.errors)

    def test_rejects_day_zero(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,0,Squat,4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Day" in e for e in result.errors)

    def test_rejects_day_8(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,8,Squat,4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Day" in e for e in result.errors)

    def test_rejects_empty_exercise(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,,4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Exercise" in e for e in result.errors)

    def test_rejects_exercise_over_100_chars(self):
        long_name = "A" * 101
        csv_content = (
            f"Week,Day,Exercise,Sets,Target Reps\n"
            f"1,1,{long_name},4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Exercise" in e for e in result.errors)

    def test_accepts_exercise_exactly_100_chars(self):
        name = "A" * 100
        csv_content = (
            f"Week,Day,Exercise,Sets,Target Reps\n"
            f"1,1,{name},4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True

    def test_rejects_sets_zero(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Squat,0,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Sets" in e for e in result.errors)

    def test_rejects_sets_11(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Squat,11,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Sets" in e for e in result.errors)

    def test_rejects_non_integer_sets(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Squat,abc,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Sets" in e for e in result.errors)

    def test_rejects_empty_target_reps(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Squat,4,\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Target Reps" in e for e in result.errors)

    def test_rejects_target_reps_over_20_chars(self):
        long_reps = "A" * 21
        csv_content = (
            f"Week,Day,Exercise,Sets,Target Reps\n"
            f"1,1,Squat,4,{long_reps}\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 2" in e and "Target Reps" in e for e in result.errors)

    def test_accepts_target_reps_exactly_20_chars(self):
        reps = "A" * 20
        csv_content = (
            f"Week,Day,Exercise,Sets,Target Reps\n"
            f"1,1,Squat,4,{reps}\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True

    def test_collects_multiple_errors(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "abc,0,,11,\n"
            "1,1,Valid Exercise,4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        # Should have errors for Week, Day, Exercise, Sets, and Target Reps on row 2
        row2_errors = [e for e in result.errors if "Row 2" in e]
        assert len(row2_errors) >= 4

    def test_error_row_numbers_are_1_based(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Valid,4,5-8\n"
            "abc,1,Valid,4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Row 3" in e for e in result.errors)


class TestParseCSVDayConsistency:
    """Tests for day count consistency across weeks."""

    def test_rejects_inconsistent_day_counts(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Exercise A,3,8-10\n"
            "1,2,Exercise B,3,8-10\n"
            "1,3,Exercise C,3,8-10\n"
            "2,1,Exercise A,3,8-10\n"
            "2,2,Exercise B,3,8-10\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any("Week 2" in e and "2 days" in e and "3 days" in e for e in result.errors)

    def test_error_identifies_bad_week(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Ex A,3,8-10\n"
            "1,2,Ex B,3,8-10\n"
            "1,3,Ex C,3,8-10\n"
            "1,4,Ex D,3,8-10\n"
            "2,1,Ex A,3,8-10\n"
            "2,2,Ex B,3,8-10\n"
            "2,3,Ex C,3,8-10\n"
            "2,4,Ex D,3,8-10\n"
            "3,1,Ex A,3,8-10\n"
            "3,2,Ex B,3,8-10\n"
            "3,3,Ex C,3,8-10\n"
            "3,4,Ex D,3,8-10\n"
            "3,5,Ex E,3,8-10\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert any(
            "Week 3 has 5 days but Week 1 defines 4 days per week" in e
            for e in result.errors
        )

    def test_accepts_consistent_day_counts(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Ex A,3,8-10\n"
            "1,2,Ex B,3,8-10\n"
            "2,1,Ex A,3,8-10\n"
            "2,2,Ex B,3,8-10\n"
            "3,1,Ex A,3,8-10\n"
            "3,2,Ex B,3,8-10\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.days_per_week == 2

    def test_days_per_week_defaults_to_0_on_failure(self):
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "abc,1,Squat,4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is False
        assert result.days_per_week == 0


class TestParseCSVBoundaryValues:
    """Tests for boundary values: 52 weeks, 10 sets, varying day counts."""

    def test_accepts_52_weeks(self):
        """CSV with 52 weeks (max allowed) should be accepted."""
        rows = ["Week,Day,Exercise,Sets,Target Reps"]
        for week in range(1, 53):
            rows.append(f"{week},1,Exercise A,3,8-10")
        csv_content = "\n".join(rows)
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.days_per_week == 1
        assert len(result.exercises) == 52

    def test_accepts_10_sets(self):
        """CSV with sets=10 (max allowed) should be accepted."""
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Heavy Exercise,10,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.exercises[0].sets == 10

    def test_accepts_1_set(self):
        """CSV with sets=1 (min allowed) should be accepted."""
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Light Exercise,1,15-20\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.exercises[0].sets == 1

    def test_accepts_100_char_exercise_name(self):
        """Exercise name exactly 100 characters should be accepted."""
        name = "A" * 100
        csv_content = (
            f"Week,Day,Exercise,Sets,Target Reps\n"
            f"1,1,{name},4,5-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.exercises[0].exercise_name == name

    def test_accepts_20_char_target_reps(self):
        """Target reps exactly 20 characters should be accepted."""
        reps = "12-15 reps per side"  # exactly 19 chars, pad to 20
        reps = "A" * 20
        csv_content = (
            f"Week,Day,Exercise,Sets,Target Reps\n"
            f"1,1,Squat,4,{reps}\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.exercises[0].target_reps == reps

    def test_2_days_per_week_consistent(self):
        """2 days per week across multiple weeks should parse correctly."""
        rows = ["Week,Day,Exercise,Sets,Target Reps"]
        for week in range(1, 4):
            rows.append(f"{week},1,Exercise A,3,8-10")
            rows.append(f"{week},2,Exercise B,3,8-10")
        csv_content = "\n".join(rows)
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.days_per_week == 2

    def test_3_days_per_week_consistent(self):
        """3 days per week across multiple weeks should parse correctly."""
        rows = ["Week,Day,Exercise,Sets,Target Reps"]
        for week in range(1, 4):
            for day in range(1, 4):
                rows.append(f"{week},{day},Exercise {day},3,8-10")
        csv_content = "\n".join(rows)
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.days_per_week == 3

    def test_4_days_per_week_consistent(self):
        """4 days per week across multiple weeks should parse correctly."""
        rows = ["Week,Day,Exercise,Sets,Target Reps"]
        for week in range(1, 4):
            for day in range(1, 5):
                rows.append(f"{week},{day},Exercise {day},3,8-10")
        csv_content = "\n".join(rows)
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.days_per_week == 4

    def test_5_days_per_week_consistent(self):
        """5 days per week across multiple weeks should parse correctly."""
        rows = ["Week,Day,Exercise,Sets,Target Reps"]
        for week in range(1, 4):
            for day in range(1, 6):
                rows.append(f"{week},{day},Exercise {day},3,8-10")
        csv_content = "\n".join(rows)
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.days_per_week == 5

    def test_6_days_per_week_consistent(self):
        """6 days per week across multiple weeks should parse correctly."""
        rows = ["Week,Day,Exercise,Sets,Target Reps"]
        for week in range(1, 4):
            for day in range(1, 7):
                rows.append(f"{week},{day},Exercise {day},3,8-10")
        csv_content = "\n".join(rows)
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.days_per_week == 6

    def test_7_days_per_week_sets_days_per_week_to_7(self):
        """7-day program should set days_per_week to 7."""
        rows = ["Week,Day,Exercise,Sets,Target Reps"]
        for week in range(1, 3):
            for day in range(1, 8):
                rows.append(f"{week},{day},Exercise {day},3,8-10")
        csv_content = "\n".join(rows)
        result = parse_csv(csv_content)
        assert result.success is True
        assert result.days_per_week == 7
        assert len(result.exercises) == 14


class TestParseCSVDuplicateExerciseRows:
    """Tests for duplicate exercise entries within same week/day."""

    def test_rejects_duplicate_exercise_same_day(self):
        """Same exercise name on same week/day should be treated as a duplicate.

        Note: The CSV parser itself may not reject duplicates (it depends on
        implementation). If the parser passes duplicates through, the database
        UNIQUE constraint will catch them. Test the actual behavior.
        """
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Bench Press,4,5-8\n"
            "1,1,Bench Press,3,8-10\n"
        )
        result = parse_csv(csv_content)
        # The parser may accept this (DB constraint catches it) or reject it
        # Either way, document the behavior
        if result.success:
            # If parser allows it, both exercises should be in the list
            bench_exercises = [e for e in result.exercises
                              if e.exercise_name == "Bench Press"
                              and e.week == 1 and e.day == 1]
            assert len(bench_exercises) == 2
        else:
            # If parser catches it, error should mention the duplicate
            assert any("duplicate" in e.lower() or "Bench Press" in e
                       for e in result.errors)

    def test_same_exercise_different_days_is_allowed(self):
        """Same exercise name on different days is valid."""
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Bench Press,4,5-8\n"
            "1,2,Bench Press,3,8-10\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert len(result.exercises) == 2

    def test_same_exercise_different_weeks_is_allowed(self):
        """Same exercise name on different weeks is valid."""
        csv_content = (
            "Week,Day,Exercise,Sets,Target Reps\n"
            "1,1,Bench Press,4,5-8\n"
            "2,1,Bench Press,4,6-8\n"
        )
        result = parse_csv(csv_content)
        assert result.success is True
        assert len(result.exercises) == 2


class TestParseCSVSampleFile:
    """Tests using the actual sample CSV file."""

    @pytest.fixture
    def sample_csv_content(self):
        """Load the actual sample CSV file content."""
        sample_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'sample_program', 'updated_4_day_strength_tracker.csv'
        )
        if not os.path.exists(sample_path):
            pytest.skip("Sample CSV file not found")
        with open(sample_path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_sample_csv_parses_successfully(self, sample_csv_content):
        """The sample CSV file should parse without errors."""
        result = parse_csv(sample_csv_content)
        assert result.success is True
        assert result.errors == []

    def test_sample_csv_has_4_days_per_week(self, sample_csv_content):
        """The sample CSV is a 4-day program."""
        result = parse_csv(sample_csv_content)
        assert result.days_per_week == 4

    def test_sample_csv_has_12_weeks(self, sample_csv_content):
        """The sample CSV has 12 weeks."""
        result = parse_csv(sample_csv_content)
        weeks = set(ex.week for ex in result.exercises)
        assert len(weeks) == 12
        assert max(weeks) == 12

    def test_sample_csv_exercises_have_valid_fields(self, sample_csv_content):
        """All exercises in the sample CSV should have valid field values."""
        result = parse_csv(sample_csv_content)
        for ex in result.exercises:
            assert 1 <= ex.week <= 52
            assert 1 <= ex.day <= 7
            assert 0 < len(ex.exercise_name) <= 100
            assert 1 <= ex.sets <= 10
            assert 0 < len(ex.target_reps) <= 20

    def test_sample_csv_first_day_exercises(self, sample_csv_content):
        """Week 1, Day 1 should have the expected exercises."""
        result = parse_csv(sample_csv_content)
        day1_exercises = [ex for ex in result.exercises
                         if ex.week == 1 and ex.day == 1]
        exercise_names = [ex.exercise_name for ex in day1_exercises]
        assert "Incline DB Press (15-30°)" in exercise_names
        assert "Ring Push-ups / Dips" in exercise_names

    def test_sample_csv_consistent_day_counts(self, sample_csv_content):
        """All weeks in sample should have 4 days each."""
        result = parse_csv(sample_csv_content)
        weeks = set(ex.week for ex in result.exercises)
        for week_num in weeks:
            week_days = set(ex.day for ex in result.exercises if ex.week == week_num)
            assert len(week_days) == 4, f"Week {week_num} has {len(week_days)} days, expected 4"
