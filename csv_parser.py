"""CSV parser for workout program files.

Parses CSV files containing exercise programs organized by weeks and days.
Validates structure, data types, ranges, and consistency of day counts across weeks.
"""

import csv
import io
from dataclasses import dataclass, field


@dataclass
class ParsedExercise:
    """A single exercise parsed from a CSV row."""
    week: int
    day: int
    exercise_name: str
    sets: int
    target_reps: str


@dataclass
class ParseResult:
    """Result of parsing a CSV file."""
    success: bool
    exercises: list[ParsedExercise] = field(default_factory=list)
    days_per_week: int = 0  # Determined by distinct days in Week 1
    errors: list[str] = field(default_factory=list)


REQUIRED_HEADERS = ["Week", "Day", "Exercise", "Sets", "Target Reps"]


def parse_csv(file_content: str) -> ParseResult:
    """Parse a CSV file containing an exercise program.

    Validates the header row, each data row's fields, and consistency of day
    counts across weeks. Row numbers in error messages are 1-based (header is
    row 1, first data row is row 2).

    Args:
        file_content: The full text content of the CSV file.

    Returns:
        ParseResult with success status, parsed exercises (if valid),
        days_per_week (from Week 1), and any errors found.
    """
    errors = []
    exercises = []

    reader = csv.reader(io.StringIO(file_content))

    # Read and validate header row
    try:
        header = next(reader)
    except StopIteration:
        return ParseResult(
            success=False,
            errors=["CSV file is empty"],
        )

    # Normalize header (strip whitespace)
    header = [h.strip() for h in header]

    # Check required headers
    missing_headers = [h for h in REQUIRED_HEADERS if h not in header]
    if missing_headers:
        return ParseResult(
            success=False,
            errors=[f"Missing required columns: {', '.join(missing_headers)}"],
        )

    # Get column indices
    week_idx = header.index("Week")
    day_idx = header.index("Day")
    exercise_idx = header.index("Exercise")
    sets_idx = header.index("Sets")
    reps_idx = header.index("Target Reps")

    # Parse data rows
    for row_num, row in enumerate(reader, start=2):  # Header is row 1
        # Skip empty rows
        if not row or all(cell.strip() == "" for cell in row):
            continue

        # Ensure row has enough columns
        if len(row) <= max(week_idx, day_idx, exercise_idx, sets_idx, reps_idx):
            errors.append(f"Row {row_num}: row has insufficient columns")
            continue

        week_str = row[week_idx].strip()
        day_str = row[day_idx].strip()
        exercise_str = row[exercise_idx].strip()
        sets_str = row[sets_idx].strip()
        reps_str = row[reps_idx].strip()

        row_has_error = False

        # Validate Week: positive integer 1-52
        week = None
        if not week_str:
            errors.append(f"Row {row_num}: 'Week' is required")
            row_has_error = True
        else:
            try:
                week = int(week_str)
                if week < 1 or week > 52:
                    errors.append(
                        f"Row {row_num}: 'Week' must be a positive integer between 1 and 52"
                    )
                    row_has_error = True
            except ValueError:
                errors.append(
                    f"Row {row_num}: 'Week' must be a positive integer between 1 and 52"
                )
                row_has_error = True

        # Validate Day: integer 1-7
        day = None
        if not day_str:
            errors.append(f"Row {row_num}: 'Day' is required")
            row_has_error = True
        else:
            try:
                day = int(day_str)
                if day < 1 or day > 7:
                    errors.append(
                        f"Row {row_num}: 'Day' must be an integer between 1 and 7"
                    )
                    row_has_error = True
            except ValueError:
                errors.append(
                    f"Row {row_num}: 'Day' must be an integer between 1 and 7"
                )
                row_has_error = True

        # Validate Exercise: non-empty text, max 100 chars
        if not exercise_str:
            errors.append(f"Row {row_num}: 'Exercise' is required")
            row_has_error = True
        elif len(exercise_str) > 100:
            errors.append(
                f"Row {row_num}: 'Exercise' must be 100 characters or fewer"
            )
            row_has_error = True

        # Validate Sets: integer 1-10
        sets = None
        if not sets_str:
            errors.append(f"Row {row_num}: 'Sets' is required")
            row_has_error = True
        else:
            try:
                sets = int(sets_str)
                if sets < 1 or sets > 10:
                    errors.append(
                        f"Row {row_num}: 'Sets' must be an integer between 1 and 10"
                    )
                    row_has_error = True
            except ValueError:
                errors.append(
                    f"Row {row_num}: 'Sets' must be an integer between 1 and 10"
                )
                row_has_error = True

        # Validate Target Reps: non-empty text, max 20 chars
        if not reps_str:
            errors.append(f"Row {row_num}: 'Target Reps' is required")
            row_has_error = True
        elif len(reps_str) > 20:
            errors.append(
                f"Row {row_num}: 'Target Reps' must be 20 characters or fewer"
            )
            row_has_error = True

        # If row is valid, add to exercises list
        if not row_has_error:
            exercises.append(ParsedExercise(
                week=week,
                day=day,
                exercise_name=exercise_str,
                sets=sets,
                target_reps=reps_str,
            ))

    # If there are row-level errors, return failure
    if errors:
        return ParseResult(
            success=False,
            errors=errors,
        )

    # If no data rows parsed
    if not exercises:
        return ParseResult(
            success=False,
            errors=["CSV file contains no data rows"],
        )

    # Determine days_per_week from distinct day values in Week 1
    week1_days = set()
    for ex in exercises:
        if ex.week == 1:
            week1_days.add(ex.day)

    if not week1_days:
        return ParseResult(
            success=False,
            errors=["CSV file contains no exercises for Week 1"],
        )

    days_per_week = len(week1_days)

    # Validate all subsequent weeks have the same number of distinct days as Week 1
    weeks = set(ex.week for ex in exercises)
    for week_num in sorted(weeks):
        if week_num == 1:
            continue
        week_days = set(ex.day for ex in exercises if ex.week == week_num)
        if len(week_days) != days_per_week:
            errors.append(
                f"Week {week_num} has {len(week_days)} days but "
                f"Week 1 defines {days_per_week} days per week"
            )

    if errors:
        return ParseResult(
            success=False,
            errors=errors,
        )

    return ParseResult(
        success=True,
        exercises=exercises,
        days_per_week=days_per_week,
    )
