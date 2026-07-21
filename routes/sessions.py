"""Session routes for workout session recording and history."""
from datetime import datetime

from flask import Blueprint, request, jsonify

from database import get_db
from validators import validate_session

sessions_bp = Blueprint('sessions', __name__)


@sessions_bp.route('/api/sessions', methods=['POST'])
def save_session():
    """Save a new workout session.

    Validates session data, saves session with timestamp, set_entries,
    and notes in a single transaction.

    Returns 201 with session id and confirmation on success.
    Returns 400 with validation errors if invalid.
    """
    data = request.get_json()

    if data is None:
        return jsonify({'error': 'validation', 'details': ['Request body must be valid JSON']}), 400

    is_valid, errors = validate_session(data)
    if not is_valid:
        return jsonify({'error': 'validation', 'details': errors}), 400

    week = data['week']
    day = data['day']
    sets = data['sets']
    notes = data['notes']

    # Generate server-side timestamp
    completed_at = datetime.now().strftime('%Y-%m-%dT%H:%M')

    db = get_db()
    try:
        # Insert session
        cursor = db.execute(
            'INSERT INTO sessions (week, day, completed_at) VALUES (?, ?, ?)',
            (week, day, completed_at)
        )
        session_id = cursor.lastrowid

        # Insert set entries
        for set_entry in sets:
            weight = set_entry.get('weight')
            # Default None/missing weight to 0
            if weight is None:
                weight = 0
            else:
                weight = float(weight)
            db.execute(
                '''INSERT INTO set_entries (session_id, exercise_name, set_number, weight, reps)
                   VALUES (?, ?, ?, ?, ?)''',
                (session_id, set_entry['exercise_name'], set_entry['set_number'],
                 weight, set_entry['reps'])
            )

        # Insert notes
        for note_entry in notes:
            note_text = note_entry.get('note', '')
            db.execute(
                '''INSERT INTO notes (session_id, exercise_name, note_text)
                   VALUES (?, ?, ?)''',
                (session_id, note_entry['exercise_name'], note_text)
            )

        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({'error': 'storage', 'message': str(e)}), 500

    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': 'Session saved successfully'
    }), 201


@sessions_bp.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Return all sessions ordered by completed_at descending.

    Each session includes id, week, day, and completed_at timestamp.
    """
    db = get_db()
    rows = db.execute(
        '''SELECT id, week, day, completed_at
           FROM sessions
           ORDER BY completed_at DESC'''
    ).fetchall()

    sessions = [
        {
            'id': row['id'],
            'week': row['week'],
            'day': row['day'],
            'completed_at': row['completed_at']
        }
        for row in rows
    ]

    return jsonify({'sessions': sessions}), 200


@sessions_bp.route('/api/sessions/<int:session_id>', methods=['GET'])
def get_session(session_id):
    """Return full session details including set_entries and notes.

    Returns the session with exercises grouped by exercise_name,
    each containing their sets and note. Includes exercise_order
    to match the program's sort order for that day.
    """
    db = get_db()

    # Get session metadata
    session = db.execute(
        'SELECT id, week, day, completed_at FROM sessions WHERE id = ?',
        (session_id,)
    ).fetchone()

    if session is None:
        return jsonify({'error': 'not_found'}), 404

    # Get the program's exercise order for this week/day
    order_rows = db.execute(
        '''SELECT exercise_name FROM exercises
           WHERE week = ? AND day = ?
           ORDER BY sort_order''',
        (session['week'], session['day'])
    ).fetchall()
    program_order = [row['exercise_name'] for row in order_rows]

    # Get set entries for this session
    set_rows = db.execute(
        '''SELECT exercise_name, set_number, weight, reps
           FROM set_entries
           WHERE session_id = ?
           ORDER BY exercise_name, set_number''',
        (session_id,)
    ).fetchall()

    # Get notes for this session
    note_rows = db.execute(
        '''SELECT exercise_name, note_text
           FROM notes
           WHERE session_id = ?''',
        (session_id,)
    ).fetchall()

    # Build notes lookup
    notes_map = {row['exercise_name']: row['note_text'] for row in note_rows}

    # Group sets by exercise_name
    exercises = {}
    for row in set_rows:
        exercise_name = row['exercise_name']
        if exercise_name not in exercises:
            exercises[exercise_name] = {
                'sets': [],
                'note': notes_map.get(exercise_name, '')
            }
        exercises[exercise_name]['sets'].append({
            'set_number': row['set_number'],
            'weight': row['weight'],
            'reps': row['reps']
        })

    # Include exercises that only have notes but no sets
    for exercise_name, note_text in notes_map.items():
        if exercise_name not in exercises:
            exercises[exercise_name] = {
                'sets': [],
                'note': note_text
            }

    # Build ordered exercise list: program order first, then any extras not in program
    exercise_order = list(program_order)
    for name in exercises:
        if name not in exercise_order:
            exercise_order.append(name)

    return jsonify({
        'id': session['id'],
        'week': session['week'],
        'day': session['day'],
        'completed_at': session['completed_at'],
        'exercises': exercises,
        'exercise_order': exercise_order
    }), 200


@sessions_bp.route('/api/sessions/previous/<int:week>/<int:day>', methods=['GET'])
def get_previous_session(week, day):
    """Return the most recent session for a given day number.

    Searches across all weeks to find the most recent session for this day,
    so that if a user skips weeks, they still see their last performance.
    The week parameter is kept for URL compatibility but not used in the query.

    Returns sets grouped by exercise_name and notes included.
    Returns empty response if no prior session exists.
    """
    db = get_db()

    # Find the most recent session for this day number across all weeks
    # Use id DESC as tiebreaker when timestamps match (same minute)
    session = db.execute(
        '''SELECT id, completed_at
           FROM sessions
           WHERE day = ?
           ORDER BY completed_at DESC, id DESC
           LIMIT 1''',
        (day,)
    ).fetchone()

    if session is None:
        return jsonify({'session_id': None, 'exercises': {}}), 200

    session_id = session['id']

    # Get set entries for this session
    set_rows = db.execute(
        '''SELECT exercise_name, set_number, weight, reps
           FROM set_entries
           WHERE session_id = ?
           ORDER BY exercise_name, set_number''',
        (session_id,)
    ).fetchall()

    # Get notes for this session
    note_rows = db.execute(
        '''SELECT exercise_name, note_text
           FROM notes
           WHERE session_id = ?''',
        (session_id,)
    ).fetchall()

    # Build notes lookup
    notes_map = {row['exercise_name']: row['note_text'] for row in note_rows}

    # Group sets by exercise_name
    exercises = {}
    for row in set_rows:
        exercise_name = row['exercise_name']
        if exercise_name not in exercises:
            exercises[exercise_name] = {
                'sets': [],
                'note': notes_map.get(exercise_name, '')
            }
        exercises[exercise_name]['sets'].append({
            'set_number': row['set_number'],
            'weight': row['weight'],
            'reps': row['reps']
        })

    # Include exercises that only have notes but no sets
    for exercise_name, note_text in notes_map.items():
        if exercise_name not in exercises:
            exercises[exercise_name] = {
                'sets': [],
                'note': note_text
            }

    return jsonify({
        'session_id': session_id,
        'completed_at': session['completed_at'],
        'exercises': exercises
    }), 200
