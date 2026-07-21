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

## Running on Android (Termux)

This app is designed to run locally on your Android phone via Termux, with Chrome as the front-end.

### 1. Install Termux

Install **Termux** from the Google Play Store.

### 2. Set up the environment

Open Termux and run:

```bash
pkg update && pkg upgrade
pkg install python git
```

### 3. Clone the repo

```bash
cd ~
git clone https://github.com/temp-for-tas/strength-tracker.git
cd strength-tracker
```

### 4. Create the Python environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install Flask==3.1.1
```

### 5. Set up the `gym` alias

Add an alias to your shell profile so you can start the app with a single command:

```bash
echo "alias gym='cd ~/strength-tracker && source .venv/bin/activate && python app.py'" >> ~/.bashrc
source ~/.bashrc
```

From now on, just open Termux and type:

```bash
gym
```

The server starts at `http://localhost:5000`.

### 6. Open in Chrome and install as a home screen app

1. Open **Chrome** on your phone and navigate to `http://localhost:5000`
2. Tap the three-dot menu → **Add to Home Screen** (or "Install app" if prompted)
3. Chrome adds a Strength Tracker icon to your home screen that launches the app in full-screen standalone mode, just like a native app

> The server must be running in Termux for the app to work. Open Termux and run `gym` first, then tap the home screen icon to open the app.

### Backing up and restoring your workout data

Your workout history lives in a SQLite database inside the Termux home directory. If you reinstall Termux or switch devices, back it up first.

**Back up:**
```bash
cp ~/strength-tracker/instance/workout_tracker.db /sdcard/workout_backup.db
```

**Restore after reinstalling:**
```bash
mkdir -p ~/strength-tracker/instance
cp /sdcard/workout_backup.db ~/strength-tracker/instance/workout_tracker.db
```

`/sdcard/` is Android's shared storage and survives app uninstalls.

## CSV Format

... (rest of existing content unchanged)
