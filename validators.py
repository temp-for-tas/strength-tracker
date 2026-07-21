"""Input validation functions for weight, reps, notes, and session data."""

import math


def validate_weight(value):
    """Validate a weight value.

    Accepts numeric values between 0.5 and 9999 with up to one decimal place.
    Rejects non-numeric, negative, zero, or exceeding 9999, or values with
    more than one decimal place.

    Args:
        value: The weight value to validate (string or numeric).

    Returns:
        tuple: (is_valid: bool, parsed_value_or_None: float|None, error_message_or_None: str|None)
    """
    # Try to convert to float
    try:
        weight = float(value)
    except (TypeError, ValueError):
        return (False, None, "Weight must be a numeric value between 0.5 and 9999")

    # Reject NaN and infinity
    if math.isnan(weight) or math.isinf(weight):
        return (False, None, "Weight must be a numeric value between 0.5 and 9999")

    # Check range
    if weight < 0.5 or weight > 9999:
        return (False, None, "Weight must be between 0.5 and 9999")

    # Check decimal places (at most one)
    # Multiply by 10 and check if it's an integer
    if round(weight * 10, 5) != round(round(weight * 10, 5)):
        return (False, None, "Weight must have at most one decimal place")

    # More reliable decimal place check using string representation
    str_value = str(value).strip()
    if '.' in str_value:
        decimal_part = str_value.split('.')[-1]
        if len(decimal_part) > 1:
            return (False, None, "Weight must have at most one decimal place")

    return (True, weight, None)


def validate_reps(value):
    """Validate a reps value.

    Accepts integer values between 1 and 999.
    Rejects non-integer, less than 1, or exceeding 999.

    Args:
        value: The reps value to validate (string or numeric).

    Returns:
        tuple: (is_valid: bool, parsed_value_or_None: int|None, error_message_or_None: str|None)
    """
    # Try to convert to a number first
    try:
        num = float(value)
    except (TypeError, ValueError):
        return (False, None, "Reps must be an integer between 1 and 999")

    # Reject NaN and infinity
    if math.isnan(num) or math.isinf(num):
        return (False, None, "Reps must be an integer between 1 and 999")

    # Check if it's an integer (no decimal part)
    if num != int(num):
        return (False, None, "Reps must be a whole number (integer)")

    reps = int(num)

    # Check range
    if reps < 1 or reps > 999:
        return (False, None, "Reps must be between 1 and 999")

    return (True, reps, None)


def validate_note(value):
    """Validate a note value.

    Accepts strings up to 500 characters. Rejects strings exceeding 500 characters.

    Args:
        value: The note string to validate.

    Returns:
        tuple: (is_valid: bool, parsed_value_or_None: str|None, error_message_or_None: str|None)
    """
    if value is None:
        return (True, "", None)

    if not isinstance(value, str):
        return (False, None, "Note must be a string")

    if len(value) > 500:
        return (False, None, "Note must be 500 characters or fewer")

    return (True, value, None)


def validate_session(data):
    """Validate the full session payload structure.

    Expected structure:
    {
        "week": int (1-52),
        "day": int (1-7),
        "sets": [
            {"exercise_name": str, "set_number": int, "weight": float, "reps": int}
        ],
        "notes": [
            {"exercise_name": str, "note": str}
        ]
    }

    Args:
        data: The session payload dictionary.

    Returns:
        tuple: (is_valid: bool, errors: list[str])
    """
    errors = []

    if not isinstance(data, dict):
        return (False, ["Session data must be a JSON object"])

    # Validate week
    week = data.get("week")
    if week is None:
        errors.append("'week' is required")
    elif not isinstance(week, int) or isinstance(week, bool):
        errors.append("'week' must be an integer")
    elif week < 1 or week > 52:
        errors.append("'week' must be between 1 and 52")

    # Validate day
    day = data.get("day")
    if day is None:
        errors.append("'day' is required")
    elif not isinstance(day, int) or isinstance(day, bool):
        errors.append("'day' must be an integer")
    elif day < 1 or day > 7:
        errors.append("'day' must be between 1 and 7")

    # Validate sets
    sets = data.get("sets")
    if sets is None:
        errors.append("'sets' is required")
    elif not isinstance(sets, list):
        errors.append("'sets' must be a list")
    else:
        for i, set_entry in enumerate(sets):
            if not isinstance(set_entry, dict):
                errors.append(f"sets[{i}]: must be an object")
                continue

            # Validate exercise_name
            exercise_name = set_entry.get("exercise_name")
            if not exercise_name or not isinstance(exercise_name, str):
                errors.append(f"sets[{i}]: 'exercise_name' is required and must be a string")

            # Validate set_number
            set_number = set_entry.get("set_number")
            if set_number is None:
                errors.append(f"sets[{i}]: 'set_number' is required")
            elif not isinstance(set_number, int) or isinstance(set_number, bool):
                errors.append(f"sets[{i}]: 'set_number' must be an integer")
            elif set_number < 1 or set_number > 10:
                errors.append(f"sets[{i}]: 'set_number' must be between 1 and 10")

            # Validate weight
            weight = set_entry.get("weight")
            if weight is None:
                errors.append(f"sets[{i}]: 'weight' is required")
            else:
                is_valid, _, err = validate_weight(weight)
                if not is_valid:
                    errors.append(f"sets[{i}]: {err}")

            # Validate reps
            reps = set_entry.get("reps")
            if reps is None:
                errors.append(f"sets[{i}]: 'reps' is required")
            else:
                is_valid, _, err = validate_reps(reps)
                if not is_valid:
                    errors.append(f"sets[{i}]: {err}")

    # Validate notes
    notes = data.get("notes")
    if notes is None:
        errors.append("'notes' is required")
    elif not isinstance(notes, list):
        errors.append("'notes' must be a list")
    else:
        for i, note_entry in enumerate(notes):
            if not isinstance(note_entry, dict):
                errors.append(f"notes[{i}]: must be an object")
                continue

            # Validate exercise_name
            exercise_name = note_entry.get("exercise_name")
            if not exercise_name or not isinstance(exercise_name, str):
                errors.append(f"notes[{i}]: 'exercise_name' is required and must be a string")

            # Validate note text
            note_text = note_entry.get("note")
            if note_text is None:
                # note can be omitted (treated as empty)
                pass
            else:
                is_valid, _, err = validate_note(note_text)
                if not is_valid:
                    errors.append(f"notes[{i}]: {err}")

    return (len(errors) == 0, errors)
