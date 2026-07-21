"""Program routes for CSV upload and exercise program retrieval."""
from flask import Blueprint, request, jsonify

from database import get_db
from csv_parser import parse_csv

program_bp = Blueprint('program', __name__)

MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB


@program_bp.route('/api/program/upload', methods=['POST'])
def upload_program():
    """Upload a CSV file to replace the current exercise program.

    Accepts multipart file upload, validates size and content,
    replaces the existing program atomically while preserving
    workout session history.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'no_file', 'message': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'no_file', 'message': 'No file selected'}), 400

    # Check file size
    file_content = file.read()
    if len(file_content) > MAX_FILE_SIZE:
        return jsonify({'error': 'file_too_large', 'max_size': '1MB'}), 413

    # Decode and parse CSV
    try:
        content_str = file_content.decode('utf-8')
    except UnicodeDecodeError:
        return jsonify({'error': 'csv_parse', 'rows': ['File is not valid UTF-8 text']}), 400

    result = parse_csv(content_str)

    if not result.success:
        return jsonify({'error': 'csv_parse', 'rows': result.errors}), 400

    # Replace existing program atomically in a transaction
    db = get_db()
    try:
        # Delete existing exercises only (preserve sessions/history)
        db.execute('DELETE FROM exercises')

        # Insert new exercises with sort_order
        for sort_order, exercise in enumerate(result.exercises, start=1):
            db.execute(
                '''INSERT INTO exercises (week, day, exercise_name, target_sets, target_reps, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (exercise.week, exercise.day, exercise.exercise_name,
                 exercise.sets, exercise.target_reps, sort_order)
            )

        # Update days_per_week in app_state
        db.execute(
            '''INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)''',
            ('days_per_week', str(result.days_per_week))
        )

        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({'error': 'storage', 'message': str(e)}), 500

    # Calculate summary
    total_weeks = len(set(ex.week for ex in result.exercises))
    total_exercises = len(result.exercises)

    return jsonify({
        'success': True,
        'weeks': total_weeks,
        'days_per_week': result.days_per_week,
        'total_exercises': total_exercises,
    }), 200


@program_bp.route('/api/program/weeks', methods=['GET'])
def get_weeks():
    """Return list of all weeks with day counts."""
    db = get_db()
    rows = db.execute(
        '''SELECT week, COUNT(DISTINCT day) as day_count
           FROM exercises
           GROUP BY week
           ORDER BY week'''
    ).fetchall()

    weeks = [{'week': row['week'], 'day_count': row['day_count']} for row in rows]
    return jsonify({'weeks': weeks}), 200


@program_bp.route('/api/program/weeks/<int:week>/days', methods=['GET'])
def get_days(week):
    """Return days available for a given week."""
    db = get_db()
    rows = db.execute(
        '''SELECT DISTINCT day FROM exercises
           WHERE week = ?
           ORDER BY day''',
        (week,)
    ).fetchall()

    days = [row['day'] for row in rows]
    return jsonify({'week': week, 'days': days}), 200


@program_bp.route('/api/program/weeks/<int:week>/days/<int:day>', methods=['GET'])
def get_exercises(week, day):
    """Return exercises for a specific week/day with name, target_sets, target_reps."""
    db = get_db()
    rows = db.execute(
        '''SELECT exercise_name, target_sets, target_reps
           FROM exercises
           WHERE week = ? AND day = ?
           ORDER BY sort_order''',
        (week, day)
    ).fetchall()

    exercises = [
        {
            'exercise_name': row['exercise_name'],
            'target_sets': row['target_sets'],
            'target_reps': row['target_reps'],
        }
        for row in rows
    ]

    return jsonify({'week': week, 'day': day, 'exercises': exercises}), 200


@program_bp.route('/api/program/current-week', methods=['GET'])
def get_current_week():
    """Return current program week, days per week, and total weeks.

    Current week is stored in app_state (defaults to 1).
    days_per_week is determined from the loaded program.
    total_weeks is the count of distinct weeks in the exercises table.
    """
    db = get_db()

    # Get current_week from app_state (default to 1)
    row = db.execute(
        "SELECT value FROM app_state WHERE key = 'current_week'"
    ).fetchone()
    current_week = int(row['value']) if row else 1

    # Get days_per_week from app_state (set during upload)
    row = db.execute(
        "SELECT value FROM app_state WHERE key = 'days_per_week'"
    ).fetchone()
    if row:
        days_per_week = int(row['value'])
    else:
        # Fallback: determine from exercises in week 1
        result = db.execute(
            'SELECT COUNT(DISTINCT day) as cnt FROM exercises WHERE week = 1'
        ).fetchone()
        days_per_week = result['cnt'] if result['cnt'] else 0

    # Get total_weeks
    result = db.execute(
        'SELECT COUNT(DISTINCT week) as cnt FROM exercises'
    ).fetchone()
    total_weeks = result['cnt'] if result['cnt'] else 0

    return jsonify({
        'current_week': current_week,
        'days_per_week': days_per_week,
        'total_weeks': total_weeks,
    }), 200
