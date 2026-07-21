# Strength Tracker

A mobile-first workout tracking web app built with Flask and vanilla JavaScript. Designed for use on Android phones at the gym with large touch targets and a clean interface.

## Features

- **CSV Program Upload** — Upload your training program as a CSV file (weeks, days, exercises, sets, target reps)
- **Workout Logging** — Record weight and reps for each set with inline validation
- **Previous Performance** — View your last session's data while logging the current one
- **Session History** — Browse past workouts with full detail
- **Auto-Save** — In-progress workouts sync to the server automatically (survives browser close)
- **Program Flexibility** — Supports 1–7 day programs up to 52 weeks; re-uploading a program preserves history

## Tech Stack

- **Backend**: Python 3.9+, Flask, SQLite
- **Frontend**: Vanilla HTML/CSS/JS (no framework, no build step)
- **Testing**: pytest, Hypothesis (property-based testing)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/temp-for-tas/strength-tracker.git
cd strength-tracker

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the app
./run.sh
# or: python app.py
```

The app runs at http://localhost:5000. Upload a CSV program to get started (a sample is included in `sample_program/`).

## CSV Format

```
Week,Day,Exercise,Sets,Target Reps
1,1,Bench Press,4,5-8
1,1,Incline DB Press,3,8-10
1,2,Squat,4,6-8
1,2,Bulgarian Split Squat,3,6-8/side
2,1,Bench Press,4,5-8
...
```

- **Week**: 1–52
- **Day**: 1–7
- **Exercise**: Name (up to 100 characters)
- **Sets**: 1–10
- **Target Reps**: Free text up to 20 characters (e.g., "5-8", "6-8/side", "20-30 sec")

## Running Tests

```bash
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run property-based tests
pytest tests/property/ -v

# Run integration tests
pytest tests/integration/ -v
```

## Project Structure

```
├── app.py              # Flask app factory and entry point
├── database.py         # SQLite connection management and schema
├── csv_parser.py       # CSV program file parser with validation
├── validators.py       # Input validation (weight, reps, notes, sessions)
├── routes/
│   ├── program.py      # Program upload and retrieval endpoints
│   ├── sessions.py     # Workout session save and history endpoints
│   └── state.py        # In-progress state persistence endpoints
├── static/
│   ├── css/style.css   # Mobile-first responsive styles
│   └── js/
│       ├── api.js      # Fetch wrappers for all backend endpoints
│       ├── app.js      # Hash-based client-side router
│       └── views/      # View modules (day-select, workout, history, upload)
├── templates/
│   └── index.html      # HTML shell with navigation
├── tests/
│   ├── unit/           # Unit tests (175 tests)
│   ├── property/       # Property-based tests with Hypothesis (27 tests)
│   └── integration/    # End-to-end workflow tests (5 tests)
├── sample_program/     # Example 12-week 4-day strength program CSV
├── requirements.txt    # Python dependencies
└── run.sh              # Startup script
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/program/upload` | Upload CSV program (multipart, ≤1MB) |
| GET | `/api/program/weeks` | List all weeks with day counts |
| GET | `/api/program/weeks/<week>/days` | List days for a week |
| GET | `/api/program/weeks/<week>/days/<day>` | Get exercises for a day |
| GET | `/api/program/current-week` | Get current week info |
| POST | `/api/sessions` | Save a workout session |
| GET | `/api/sessions` | List all sessions (newest first) |
| GET | `/api/sessions/<id>` | Get session detail |
| GET | `/api/sessions/previous/<week>/<day>` | Get most recent session for a day |
| POST | `/api/state/save` | Save in-progress workout state |
| GET | `/api/state/load` | Load in-progress workout state |

## License

Private project.
