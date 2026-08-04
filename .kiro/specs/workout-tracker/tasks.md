# Implementation Plan: Workout Tracker

## Overview

Build a locally-hosted workout tracking web app using Python (Flask), SQLite, and vanilla HTML/CSS/JS. The app allows loading a multi-week strength program from CSV, selecting workout days, recording weight/reps/notes per exercise, viewing previous performance, and browsing workout history. It runs entirely on an Android device via Termux/Chrome.

## Tasks

- [x] 1. Set up project structure and core infrastructure
  - [x] 1.1 Create project directory structure and Python virtual environment
    - Create directories: `static/`, `static/js/`, `static/js/views/`, `static/css/`, `templates/`, `routes/`, `tests/`, `tests/unit/`, `tests/property/`, `tests/integration/`
    - Create Python virtual environment at `.venv`
    - Create `requirements.txt` with: Flask, pytest, hypothesis
    - Install dependencies into `.venv`
    - Create `app.py` entry point with Flask app factory, static file serving, and index route
    - _Requirements: 8.1, 8.3_

  - [x] 1.2 Create the database module and schema initialization
    - Create `database.py` with `get_db()`, `init_db()`, `close_db()` functions
    - Implement full SQLite schema: `exercises`, `sessions`, `set_entries`, `notes`, `app_state` tables
    - Include all CHECK constraints and UNIQUE constraints from the design (note: `day` CHECK constraint is `day >= 1 AND day <= 7` to support 1–7 day programs)
    - Enable foreign keys with `PRAGMA foreign_keys = ON`
    - Register `close_db` on Flask teardown
    - Auto-initialize database on first request if tables don't exist
    - _Requirements: 8.2, 9.1, 9.6_

  - [x] 1.3 Create input validators module
    - Create `validators.py` with `validate_weight(value)`, `validate_reps(value)`, `validate_note(value)`, and `validate_session(data)` functions
    - Weight: accept numeric 0.5–9999, up to one decimal place; reject otherwise
    - Reps: accept integers 1–999; reject otherwise
    - Note: accept strings up to 500 characters; reject longer
    - Session: validate the full session payload structure (week, day, sets list, notes list)
    - Each validator returns `(is_valid, parsed_value_or_None, error_message_or_None)`
    - _Requirements: 2.3, 2.4, 2.6, 2.7, 3.2_

- [x] 2. Implement CSV parsing and program upload
  - [x] 2.1 Create the CSV parser module
    - Create `csv_parser.py` with `ParsedExercise` and `ParseResult` dataclasses
    - Implement `parse_csv(file_content: str) -> ParseResult`
    - Validate header row contains: Week, Day, Exercise, Sets, Target Reps
    - Validate each row: Week is positive int (1–52), Day is int (1–7), Exercise is non-empty text (≤100 chars), Sets is int (1–10), Target Reps is non-empty text (≤20 chars)
    - Determine `days_per_week` from the distinct day values in Week 1
    - Validate all subsequent weeks have the same number of distinct days as Week 1; if inconsistent, return error identifying the bad week (e.g., "Week 3 has 5 days but Week 1 defines 4 days per week")
    - Include `days_per_week` in `ParseResult` on success
    - Collect per-row errors with row number, field name, and reason
    - If any errors, return `success=False` with error list and empty exercises
    - If valid, return `success=True` with parsed exercises and maintain sort order
    - _Requirements: 7.2, 7.3, 7.4, 7.7_

  - [x] 2.2 Create program routes for upload and retrieval
    - Create `routes/program.py` Flask blueprint
    - `POST /api/program/upload`: Accept multipart file upload (≤1MB), parse CSV, replace existing program atomically (in transaction), preserve workout history, return summary (weeks count, days per week, total exercises)
    - `GET /api/program/weeks`: Return list of all weeks with day counts
    - `GET /api/program/weeks/<week>/days`: Return days available for a given week
    - `GET /api/program/weeks/<week>/days/<day>`: Return exercises for a specific week/day with name, target_sets, target_reps
    - `GET /api/program/current-week`: Return current program week (stored in app_state, defaults to 1), `days_per_week` (determined from the loaded program), and `total_weeks`
    - Register blueprint in `app.py`
    - _Requirements: 1.1, 1.2, 1.5, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 2.3 Write property tests for CSV parsing (Properties 8, 9, 11)
    - **Property 8: CSV parsing round-trip** — Generate random valid program structures (1–7 days per week, consistent day counts across all weeks), serialize to CSV, parse, verify equivalence and correct `days_per_week` value
    - **Property 9: CSV error reporting identifies invalid rows** — Generate CSVs with injected errors and CSVs with inconsistent day counts across weeks, verify error reports identify correct rows/fields/weeks
    - **Property 11: CSV parse summary accuracy** — Generate valid CSVs, parse, verify reported counts match actual data
    - **Validates: Requirements 7.2, 7.3, 7.4, 7.6, 7.7**

  - [x] 2.4 Write unit tests for CSV parser and program routes
    - Test known-good CSV produces expected structure
    - Test boundary values: 52 weeks, 10 sets, 100-char exercise names, 20-char target reps
    - Test invalid rows produce correct error messages with row numbers
    - Test empty file, headers-only file, duplicate exercise rows
    - Test file size rejection (>1MB)
    - Test program replacement preserves session history
    - Test inconsistent day counts across weeks are rejected with correct error identifying the bad week
    - Test 7-day programs are accepted and `days_per_week` is set to 7
    - Test varying day counts (1, 2, 3, 4, 5, 6, 7 days per week) all parse correctly when consistent across weeks
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

- [x] 3. Checkpoint - Core data layer verified
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement workout session recording and history
  - [x] 4.1 Create session routes for save and retrieval
    - Create `routes/sessions.py` Flask blueprint
    - `POST /api/sessions`: Validate session data (using validators), save session with timestamp, set_entries, and notes in a single transaction; return 201 with session id and confirmation; return 400 with validation errors if invalid
    - `GET /api/sessions`: Return all sessions ordered by `completed_at` descending (most recent first), each with id, week, day, completed_at
    - `GET /api/sessions/<id>`: Return full session details including all set_entries and notes
    - `GET /api/sessions/previous/<week>/<day>`: Return the most recent session for a given week/day, with sets grouped by exercise_name and notes included; return 404-style empty response if no prior session exists
    - Register blueprint in `app.py`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4_

  - [x] 4.2 Write property tests for validators (Properties 2, 3, 4)
    - **Property 2: Weight validation accepts valid and rejects invalid** — Generate random floats/strings, verify accept/reject against spec rules
    - **Property 3: Reps validation accepts valid and rejects invalid** — Generate random ints/strings, verify accept/reject against spec rules
    - **Property 4: Note length enforcement** — Generate random strings of varying lengths, verify 500-char boundary
    - **Validates: Requirements 2.3, 2.4, 2.6, 2.7, 3.2**

  - [x] 4.3 Write property tests for sessions (Properties 5, 6, 7)
    - **Property 5: Session data round-trip** — Generate random valid sessions, save via API, retrieve, verify equivalence
    - **Property 6: History ordering** — Generate sessions with random timestamps, save, retrieve history, verify descending order
    - **Property 7: Previous performance returns most recent session** — Generate multiple sessions for same week/day, verify most recent returned
    - **Validates: Requirements 4.2, 3.3, 4.5, 5.2, 6.1**

  - [x] 4.4 Write unit tests for session save, history, and previous performance
    - Test save with valid data returns 201 and confirmation
    - Test save with no set entries triggers warning-level response
    - Test save with invalid weight/reps returns 400 with field-level errors
    - Test history returns sessions in descending date order
    - Test previous performance returns correct session when multiple exist
    - Test previous performance returns empty when no prior session exists
    - Test partial sets (fewer than target) saved correctly
    - Test empty notes preserved
    - _Requirements: 4.2, 4.3, 4.5, 4.6, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4_

- [x] 5. Checkpoint - Backend API complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement frontend - navigation and day selection
  - [x] 6.1 Create the HTML shell and CSS styles
    - Create `templates/index.html` with mobile-responsive meta tags, viewport settings, and app container
    - Create `static/css/style.css` with responsive layout, large touch targets for gym use, clear visual hierarchy for exercises/sets
    - Link the JS modules from index.html
    - _Requirements: 8.3_

  - [x] 6.2 Create the API client and page router
    - Create `static/js/api.js` with fetch wrappers for all backend endpoints (getWeeks, getDays, getExercises, getPreviousSession, saveSession, getHistory, getSession, uploadCSV)
    - Create `static/js/app.js` with hash-based router (`#/`, `#/workout/{week}/{day}`, `#/history`, `#/history/{id}`, `#/upload`)
    - Router renders the appropriate view into the app container
    - _Requirements: 1.3_

  - [x] 6.3 Create the day selection view
    - Create `static/js/views/day-select.js`
    - Fetch `days_per_week` from `GET /api/program/current-week` and display current week's Workout Days (Day 1 through Day N, where N is `days_per_week` from the program API response)
    - Week navigation (prev/next buttons) to browse all weeks in the program
    - Indicate current week of program
    - Show "no program available" message with link to upload when no program is loaded
    - Each day is a tappable card that navigates to the workout view
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 9.2, 9.5, 9.6_

- [x] 7. Implement frontend - workout data entry
  - [x] 7.1 Create the workout view with exercise data entry
    - Create `static/js/views/workout.js`
    - Display week/day heading and all exercises with name, target sets, target reps
    - For each exercise: render input fields (weight + reps) for up to 4 sets
    - Display previous performance data (visually distinct) aligned to set numbers
    - Show "no previous data" label when no prior session exists
    - Multi-line notes textarea per exercise (max 500 characters, enforced in UI)
    - Client-side input validation: weight (0.5–9999, one decimal), reps (1–999, integer)
    - Display inline error messages for invalid inputs
    - Allow empty set fields (fewer sets performed than target)
    - _Requirements: 1.2, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.4, 6.1, 6.2, 6.3, 6.4_

  - [x] 7.2 Implement save functionality and confirmation flow
    - Add save button (always visible) in workout view
    - On save: if no sets recorded, display warning with confirm/cancel options
    - On cancel: return to active workout with data preserved
    - On confirm (or if sets exist): POST session to API
    - On success: display confirmation message, navigate back to day selection
    - On failure: display error message, preserve all entered data for retry
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6_

- [x] 8. Implement frontend - history and upload views
  - [x] 8.1 Create the history view
    - Create `static/js/views/history.js`
    - Display list of past sessions ordered by date (most recent first), showing week/day label and date
    - Tapping a session navigates to detail view showing: timestamp, week/day, all exercises with set entries (weight/reps per set), and notes
    - Show "no workout history" message when history is empty
    - Back navigation to day selection
    - _Requirements: 5.2, 5.3, 5.4_

  - [x] 8.2 Create the upload view
    - Create `static/js/views/upload.js`
    - File picker for CSV upload (accepts .csv files up to 1MB)
    - On successful upload: display confirmation with counts (weeks, days, total exercises)
    - On parse errors: display error table with row number, field, and reason per error
    - On file too large: display size limit message
    - After successful upload, navigate to day selection
    - _Requirements: 7.1, 7.2, 7.4, 7.5, 7.6_

- [x] 9. Implement in-progress session state persistence
  - [x] 9.1 Add auto-sync of in-progress workout data to backend
    - Add `POST /api/state/save` and `GET /api/state/load` endpoints (in a new `routes/state.py` blueprint or added to sessions routes) that store/retrieve serialized in-progress session data in the `app_state` table
    - In the workout view JS, periodically sync (on each field change or every 30s) the current form state to the backend
    - On workout view load, check for saved in-progress state and restore if present
    - Clear in-progress state when a session is successfully saved
    - _Requirements: 8.5_

  - [x] 9.2 Write property test for in-progress state persistence (Property 12)
    - **Property 12: In-progress session state survives browser close** — Generate random in-progress state, sync to backend, clear, retrieve, verify equivalence
    - **Validates: Requirements 8.5**

- [x] 10. Implement exercise retrieval property test and program re-upload test
  - [x] 10.1 Write property test for exercise retrieval (Property 1)
    - **Property 1: Exercise retrieval correctness** — Generate random programs, load via database functions, query each week/day, verify correct exercises returned
    - **Validates: Requirements 1.2, 9.3, 9.4**

  - [x] 10.2 Write property test for program re-upload preserving history (Property 10)
    - **Property 10: Program re-upload preserves workout history** — Generate sessions, save, upload new CSV, verify all prior sessions retrievable
    - **Validates: Requirements 7.5**

- [x] 11. Final integration and wiring
  - [x] 11.1 Wire everything together and add startup script
    - Ensure all Flask blueprints are registered and routes work end-to-end
    - Create a `run.sh` startup script that activates the venv and starts Flask on `0.0.0.0:5000` (accessible on device)
    - Verify the sample CSV at `sample_program/updated_4_day_strength_tracker.csv` can be uploaded and parsed correctly
    - Verify full workflow: upload CSV → select day → enter data → save → appears in history → previous performance shows on next visit
    - _Requirements: 8.1, 8.3, 8.4_

  - [x] 11.2 Write integration tests for full workflow
    - Test server startup and database initialization
    - Test full flow: upload CSV → select day → record sets/notes → save → retrieve in history → verify previous performance
    - Test data persistence across simulated server restart
    - _Requirements: 4.2, 5.1, 6.1, 7.2, 8.2_

- [x] 13. Implement Progressive Web App support
  - [x] 13.1 Create web app manifest and app icons
    - Create `static/manifest.json` with: name "Strength Tracker", short_name "Strength", start_url "/", display "standalone", theme_color and background_color (dark gym theme), icons array with 192x192 and 512x512 PNG icons
    - Create or source simple app icons at both sizes (can be generated programmatically or use a simple design)
    - _Requirements: 10.1_

  - [x] 13.2 Create and register service worker
    - Create `static/sw.js` implementing cache-first strategy for the application shell
    - On install event: pre-cache all static assets (HTML, CSS, JS, manifest, icons)
    - On fetch event: serve static assets from cache first; pass all `/api/*` requests through to network (never cache API calls)
    - Implement cache versioning (cache name includes a version string to bust stale caches on updates)
    - _Requirements: 10.2_

  - [x] 13.3 Update HTML shell for PWA support
    - Add `<link rel="manifest" href="/static/manifest.json">` to `templates/index.html`
    - Add `<meta name="theme-color" content="...">` tag
    - Add `<meta name="apple-mobile-web-app-capable" content="yes">` for iOS compatibility
    - Add service worker registration script: `if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/static/sw.js'); }`
    - Verify Chrome installability criteria are met (HTTPS not required for localhost)
    - _Requirements: 10.1, 10.3, 10.4, 10.5_

- [x] 14. Final checkpoint - All tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases using pytest
- The virtual environment MUST be created before any package installation
- The sample CSV is located at `sample_program/updated_4_day_strength_tracker.csv` and serves as the primary test fixture
- All frontend code uses vanilla JS (no framework, no build step)
- The app binds to `0.0.0.0:5000` for local Android access via Chrome

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["2.1", "6.1"] },
    { "id": 3, "tasks": ["2.2", "2.3", "2.4", "4.2", "6.2"] },
    { "id": 4, "tasks": ["4.1", "6.3"] },
    { "id": 5, "tasks": ["4.3", "4.4", "7.1"] },
    { "id": 6, "tasks": ["7.2", "8.1", "8.2", "13.1"] },
    { "id": 7, "tasks": ["9.1", "13.2"] },
    { "id": 8, "tasks": ["9.2", "10.1", "10.2", "13.3"] },
    { "id": 9, "tasks": ["11.1"] },
    { "id": 10, "tasks": ["11.2"] }
  ]
}
```
