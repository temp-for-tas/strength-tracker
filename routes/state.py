"""State routes for in-progress workout data persistence."""
import json

from flask import Blueprint, request, jsonify

from database import get_db

state_bp = Blueprint('state', __name__)


@state_bp.route('/api/state/save', methods=['POST'])
def save_state():
    """Store in-progress workout state in the app_state table.

    Expects JSON body: { "key": "in_progress_workout", "value": { week, day, sets, notes } }
    The value can be null to clear the saved state.
    """
    data = request.get_json()

    if data is None:
        return jsonify({'error': 'Request body must be valid JSON'}), 400

    key = data.get('key', 'in_progress_workout')
    value = data.get('value')

    db = get_db()

    try:
        if value is None:
            # Clear the state
            db.execute('DELETE FROM app_state WHERE key = ?', (key,))
        else:
            # Upsert the state
            serialized = json.dumps(value)
            db.execute(
                '''INSERT INTO app_state (key, value) VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value''',
                (key, serialized)
            )
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({'error': 'storage', 'message': str(e)}), 500

    return jsonify({'success': True}), 200


@state_bp.route('/api/state/load', methods=['GET'])
def load_state():
    """Retrieve saved in-progress workout state from the app_state table.

    Returns: { "key": "in_progress_workout", "value": {...} } or
             { "key": "in_progress_workout", "value": null } if no state saved.
    """
    key = request.args.get('key', 'in_progress_workout')

    db = get_db()
    row = db.execute(
        'SELECT value FROM app_state WHERE key = ?', (key,)
    ).fetchone()

    if row is None:
        return jsonify({'key': key, 'value': None}), 200

    try:
        value = json.loads(row['value'])
    except (json.JSONDecodeError, TypeError):
        value = None

    return jsonify({'key': key, 'value': value}), 200
