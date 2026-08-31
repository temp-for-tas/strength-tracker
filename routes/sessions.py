"""Session routes for workout session recording and history."""
import csv
import io
from datetime import datetime

from flask import Blueprint, request, jsonify, Response

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


@sessions_bp.route('/api/sessions/exact/<int:week>/<int:day>', methods=['GET'])
def get_exact_session(week, day):
    """Return the most recent session for an exact week+day combination.

    Unlike the 'previous' endpoint which searches across all weeks for a day,
    this returns only a session that matches both the specific week AND day.
    Used to pre-fill inputs when revisiting a completed workout.

    Returns sets grouped by exercise_name and notes included.
    Returns empty response if no session exists for this exact week/day.
    """
    db = get_db()

    session = db.execute(
        '''SELECT id, completed_at
           FROM sessions
           WHERE week = ? AND day = ?
           ORDER BY completed_at DESC, id DESC
           LIMIT 1''',
        (week, day)
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


@sessions_bp.route('/api/sessions/previous-by-exercise', methods=['GET'])
def get_previous_by_exercise():
    """Return the most recent performance for each requested exercise.

    Each exercise is looked up independently — it finds the most recent
    session containing that exercise, regardless of week/day. This supports
    programs where exercises appear on different days across weeks.

    Query params:
        exercises: comma-separated list of exercise names

    Returns a dict keyed by exercise_name, each with sets, note,
    completed_at, week, and day from the session it came from.
    """
    exercises_param = request.args.get('exercises', '')
    if not exercises_param:
        return jsonify({'exercises': {}}), 200

    exercise_names = [name.strip() for name in exercises_param.split(',') if name.strip()]
    if not exercise_names:
        return jsonify({'exercises': {}}), 200

    db = get_db()
    result = {}

    for exercise_name in exercise_names:
        # Find the most recent session that contains this exercise
        # by looking at set_entries for this exercise_name
        session_row = db.execute(
            '''SELECT s.id, s.week, s.day, s.completed_at
               FROM sessions s
               INNER JOIN set_entries se ON se.session_id = s.id
               WHERE se.exercise_name = ?
               ORDER BY s.completed_at DESC, s.id DESC
               LIMIT 1''',
            (exercise_name,)
        ).fetchone()

        if session_row is None:
            # No previous data for this exercise
            continue

        session_id = session_row['id']

        # Get sets for this exercise from that session
        set_rows = db.execute(
            '''SELECT set_number, weight, reps
               FROM set_entries
               WHERE session_id = ? AND exercise_name = ?
               ORDER BY set_number''',
            (session_id, exercise_name)
        ).fetchall()

        # Get note for this exercise from that session
        note_row = db.execute(
            '''SELECT note_text
               FROM notes
               WHERE session_id = ? AND exercise_name = ?''',
            (session_id, exercise_name)
        ).fetchone()

        result[exercise_name] = {
            'sets': [
                {'set_number': r['set_number'], 'weight': r['weight'], 'reps': r['reps']}
                for r in set_rows
            ],
            'note': note_row['note_text'] if note_row else '',
            'completed_at': session_row['completed_at'],
            'week': session_row['week'],
            'day': session_row['day']
        }

    return jsonify({'exercises': result}), 200


@sessions_bp.route('/api/sessions/export', methods=['GET'])
def export_sessions():
    """Export the full workout history as a flat CSV file.

    Produces one row per recorded set, joined with its session metadata
    (week, day, completed_at) and the exercise's note. Exercises that have
    a note but no recorded sets appear as a single row with blank set fields.

    Rows are ordered by completed_at, then by the program's exercise sort
    order for that session's week/day, then by set number.

    Returns a text/csv response with a Content-Disposition attachment so
    browsers download it as a file.
    """
    db = get_db()

    sessions = db.execute(
        '''SELECT id, week, day, completed_at
           FROM sessions
           ORDER BY completed_at ASC, id ASC'''
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'session_id', 'completed_at', 'week', 'day',
        'exercise_name', 'set_number', 'weight', 'reps', 'note'
    ])

    for session in sessions:
        session_id = session['id']
        week = session['week']
        day = session['day']
        completed_at = session['completed_at']

        # Program exercise order for this week/day (for stable, meaningful ordering)
        order_rows = db.execute(
            '''SELECT exercise_name FROM exercises
               WHERE week = ? AND day = ?
               ORDER BY sort_order''',
            (week, day)
        ).fetchall()
        program_order = [row['exercise_name'] for row in order_rows]

        # Sets for this session
        set_rows = db.execute(
            '''SELECT exercise_name, set_number, weight, reps
               FROM set_entries
               WHERE session_id = ?''',
            (session_id,)
        ).fetchall()

        # Notes for this session
        note_rows = db.execute(
            '''SELECT exercise_name, note_text
               FROM notes
               WHERE session_id = ?''',
            (session_id,)
        ).fetchall()
        notes_map = {row['exercise_name']: (row['note_text'] or '') for row in note_rows}

        # Group sets by exercise
        sets_by_exercise = {}
        for row in set_rows:
            sets_by_exercise.setdefault(row['exercise_name'], []).append(row)

        # Build the ordered list of exercises: program order first,
        # then any exercises present in the data but not in the program.
        exercise_names = list(program_order)
        for name in sets_by_exercise:
            if name not in exercise_names:
                exercise_names.append(name)
        for name in notes_map:
            if name not in exercise_names:
                exercise_names.append(name)

        for exercise_name in exercise_names:
            exercise_sets = sorted(
                sets_by_exercise.get(exercise_name, []),
                key=lambda r: r['set_number']
            )
            note = notes_map.get(exercise_name, '')

            if exercise_sets:
                for s in exercise_sets:
                    writer.writerow([
                        session_id, completed_at, week, day,
                        exercise_name, s['set_number'], s['weight'], s['reps'], note
                    ])
            elif note:
                # Exercise has a note but no recorded sets
                writer.writerow([
                    session_id, completed_at, week, day,
                    exercise_name, '', '', '', note
                ])

    csv_text = output.getvalue()
    output.close()

    filename = 'workout_history_' + datetime.now().strftime('%Y%m%d') + '.csv'
    return Response(
        csv_text,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
