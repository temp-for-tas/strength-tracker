"""Flask application entry point with app factory pattern."""
import os
from flask import Flask, send_from_directory, render_template


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder='static',
        template_folder='templates'
    )

    # Default configuration
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, 'workout_tracker.db'),
    )

    if test_config is not None:
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize the database module
    from database import init_app as init_db_app
    init_db_app(app)

    # Register blueprints
    from routes.program import program_bp
    app.register_blueprint(program_bp)

    from routes.sessions import sessions_bp
    app.register_blueprint(sessions_bp)

    from routes.state import state_bp
    app.register_blueprint(state_bp)

    # Index route - serve the main HTML page
    @app.route('/')
    def index():
        return render_template('index.html')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
