"""Helpers for either-or exercise names such as "Hack Squats or Bulgarian Split Squat"."""


def split_variants(name):
    """Split an either-or exercise name into its individual exercises.

    Splits on the word "or" (case-insensitive) surrounded by spaces, but only
    outside parentheses, so "Ring Chins (w/ rotation or pause)" is not split.
    Returns an empty list when the name is not an either-or name.

    >>> split_variants("Hack Squats or Bulgarian Split Squat")
    ['Hack Squats', 'Bulgarian Split Squat']
    >>> split_variants("Chest Press")
    []
    """
    parts = []
    current = []
    depth = 0
    lowered = name.lower()
    i = 0
    while i < len(name):
        ch = name[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth = max(0, depth - 1)
        if depth == 0 and lowered.startswith(' or ', i):
            parts.append(''.join(current).strip())
            current = []
            i += 4
            continue
        current.append(ch)
        i += 1
    parts.append(''.join(current).strip())

    parts = [p for p in parts if p]
    return parts if len(parts) > 1 else []


def build_options(exercise_names):
    """Return the sorted, de-duplicated dropdown options for a program.

    Includes every exercise name as written plus the individual exercises
    from any either-or names.
    """
    options = set()
    for name in exercise_names:
        options.add(name)
        options.update(split_variants(name))
    return sorted(options, key=lambda n: (n.lower(), n))
