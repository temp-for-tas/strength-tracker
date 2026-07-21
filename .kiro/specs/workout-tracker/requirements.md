# Requirements Document

## Introduction

A locally-hosted Android workout tracking application, installable as a Progressive Web App (PWA), that allows the user to follow a pre-loaded multi-day strength training program (1–7 days per week, determined by the uploaded CSV). The app enables workout selection by day, tracks weight, reps, and sets for each exercise, supports per-exercise notes, and maintains a full workout history. Exercise programs are pre-seeded via CSV upload, and the app surfaces previous performance data each time a workout is repeated.

## Glossary

- **App**: The locally-running Android workout tracking application
- **Workout_Day**: A training session identified by week number and day number (1–7), containing a list of exercises (e.g., "Week 1, Day 1"). The number of days per week is determined by the uploaded CSV program and may range from 1 to 7.
- **Exercise**: A specific movement within a Workout_Day, defined by name, target sets, and target reps
- **Set_Entry**: A single recorded set for an exercise, consisting of weight and reps performed
- **Workout_Session**: A completed instance of a Workout_Day, timestamped and stored in history
- **CSV_File**: A comma-separated values file used to seed the exercise program into the App
- **History**: The persistent store of all completed Workout_Sessions
- **Previous_Performance**: The weight and reps recorded for each exercise the last time the same Workout_Day was completed
- **Note**: A free-text annotation attached to an exercise within a Workout_Session

## Requirements

### Requirement 1: Workout Day Selection

**User Story:** As a user, I want to select a workout by day, so that I can quickly start the correct training session.

#### Acceptance Criteria

1. WHEN the App is opened, THE App SHALL display the current week's Workout_Days (Day 1 through Day N, where N is the number of days in the loaded program, ranging from 1 to 7), with each identified by week number and day number
2. WHEN the user selects a Workout_Day, THE App SHALL display the week and day as a heading and all exercises for that specific week/day combination with their exercise name, target sets, and target reps
3. WHEN a Workout_Day is displayed, THE App SHALL provide a navigation action to return to the Workout_Day list
4. IF no Workout_Days are loaded when the App is opened, THEN THE App SHALL display a message indicating that no program is available and prompt the user to upload a CSV_File
5. THE App SHALL allow the user to navigate between weeks to view and select Workout_Days from any week in the program

### Requirement 2: Exercise Data Entry

**User Story:** As a user, I want to record weight and reps for each set of each exercise, so that I can track my performance.

#### Acceptance Criteria

1. WHEN a Workout_Day is active, THE App SHALL display input fields for weight and reps for each set of each exercise
2. THE App SHALL support up to 4 sets per exercise for data entry
3. WHEN the user enters a weight value, THE App SHALL accept numeric values between 0.5 and 9999 with up to one decimal place, representing pounds or kilograms
4. WHEN the user enters a reps value, THE App SHALL accept integer values between 1 and 999
5. THE App SHALL allow the user to leave set fields empty if fewer sets are performed than the target
6. IF the user enters a weight value that is non-numeric, negative, zero, or exceeds 9999, THEN THE App SHALL reject the input and display an error message indicating the acceptable range
7. IF the user enters a reps value that is non-integer, less than 1, or exceeds 999, THEN THE App SHALL reject the input and display an error message indicating the acceptable range

### Requirement 3: Exercise Notes

**User Story:** As a user, I want to enter notes for each exercise, so that I can record observations about form, difficulty, or modifications.

#### Acceptance Criteria

1. WHEN a Workout_Day is active, THE App SHALL display a multi-line notes input field for each exercise
2. THE App SHALL accept free-text input of up to 500 characters per exercise note and SHALL prevent the user from entering more than 500 characters
3. WHEN a Workout_Session is saved, THE App SHALL persist notes along with the set data, including exercises where the note field is left empty
4. WHEN the user opens a Workout_Day for data entry and a prior Workout_Session exists for that Workout_Day, THE App SHALL display the previously saved note for each exercise alongside the Previous_Performance data

### Requirement 4: Save Workout Session

**User Story:** As a user, I want to save my completed workout, so that my data is preserved for future reference.

#### Acceptance Criteria

1. WHILE a Workout_Day is active, THE App SHALL display a save action that the user can trigger at any time
2. WHEN the user triggers the save action, THE App SHALL store the Workout_Session with a timestamp (date and time to the minute), all Set_Entries, and all Notes, and SHALL display a confirmation indicating the session was saved successfully
3. IF the user attempts to save a Workout_Session with no Set_Entries recorded, THEN THE App SHALL display a warning indicating no sets have been recorded and present options to confirm saving or cancel the save action
4. IF the user cancels the save action from the empty-session warning, THEN THE App SHALL return the user to the active Workout_Day with all entered data preserved
5. WHEN a Workout_Session is saved, THE App SHALL add the session to History
6. IF the save operation fails due to a storage error, THEN THE App SHALL display an error message indicating the session was not saved and SHALL preserve the entered data so the user can retry

### Requirement 5: Workout History

**User Story:** As a user, I want to maintain a history of all my workouts, so that I can review past performance over time.

#### Acceptance Criteria

1. THE App SHALL persist all saved Workout_Sessions across application restarts
2. WHEN the user navigates to the history view, THE App SHALL display a list of past Workout_Sessions ordered by date (most recent first), showing the Workout_Day name and the date for each entry
3. WHEN the user selects a past Workout_Session, THE App SHALL display the session timestamp, Workout_Day name, all exercises with their Set_Entries (weight and reps per set), and any Notes recorded
4. IF the user navigates to the history view and no Workout_Sessions have been saved, THEN THE App SHALL display a message indicating that no workout history is available

### Requirement 6: Previous Performance Display

**User Story:** As a user, I want to see how much weight and how many reps I did last time for each exercise, so that I can decide how to progress.

#### Acceptance Criteria

1. WHEN the user opens a Workout_Day for data entry, THE App SHALL display the Previous_Performance for each exercise from the most recent Workout_Session of the same Workout_Day, visually distinct from the current data entry fields
2. WHEN displaying Previous_Performance, THE App SHALL show the previous weight and reps for each set that was recorded in the prior session, aligned to the corresponding set number
3. IF no prior Workout_Session exists for the selected Workout_Day, THEN THE App SHALL display a label for each exercise indicating that no previous data is available
4. IF the prior Workout_Session contains fewer recorded sets than the exercise's target sets, THEN THE App SHALL leave the Previous_Performance display empty for the unrecorded sets

### Requirement 7: CSV Program Upload

**User Story:** As a user, I want to seed my exercise program via CSV upload, so that I can quickly load my training plan without manual entry.

#### Acceptance Criteria

1. THE App SHALL provide a mechanism to upload a CSV_File containing the exercise program, accepting files up to 1 MB in size
2. WHEN a CSV_File is uploaded, THE App SHALL parse the file and create the program structure organized by weeks and days with their associated exercises, target sets, and target reps
3. THE App SHALL support a CSV_File with a header row and columns for: Week (positive integer), Day (integer 1–7), Exercise (text up to 100 characters), Sets (integer 1–10), and Target Reps (text up to 20 characters, supporting formats such as "5–8", "6–8/side", "20–40m", "20–30 sec/side")
4. IF a CSV_File contains invalid or missing required fields, THEN THE App SHALL display error messages identifying each problematic row by row number, field name, and reason for rejection, and SHALL NOT modify the existing program
5. WHEN a CSV_File is uploaded while an existing program is present, THE App SHALL replace the existing program with the new one and SHALL preserve all existing Workout_Sessions in History
6. WHEN a CSV_File is successfully parsed, THE App SHALL display a confirmation message indicating the number of weeks, days per week, and total exercises loaded
7. THE App SHALL determine the number of days per week from the distinct day values in Week 1 of the CSV_File. IF any subsequent week contains a different number of days than Week 1, THEN THE App SHALL reject the CSV_File and display an error message identifying the inconsistent week

### Requirement 8: Local Execution on Android

**User Story:** As a user, I want the app to run entirely on my Android phone, so that I can use it at the gym without internet dependency.

#### Acceptance Criteria

1. THE App SHALL run locally on an Android device running Android 10 or later without requiring an internet connection after initial installation
2. THE App SHALL store all data locally on the device such that data persists across application restarts and device reboots
3. THE App SHALL be accessible via the device's default web browser (Chrome) on the Android device
4. THE App SHALL provide a mechanism to start the local server and open the browser interface with no more than 2 user actions from the device home screen
5. IF the user closes the browser while a Workout_Session has unsaved Set_Entries, THEN THE App SHALL retain the unsaved data in memory until the local server is stopped, allowing the user to resume by reopening the browser

### Requirement 9: Pre-loaded Program Structure

**User Story:** As a user, I want the app to support a structured multi-week training program organized by weeks and days, so that my workouts follow a periodized plan.

#### Acceptance Criteria

1. THE App SHALL support a program consisting of up to 52 weeks, with each week containing up to 7 Workout_Days
2. THE App SHALL identify each Workout_Day by its week number and day number (e.g., "Week 1, Day 1")
3. WHEN displaying an exercise, THE App SHALL show the exercise name, target number of sets (1–10), and target reps as free-text (supporting ranges, per-side notation, distances, and durations)
4. THE App SHALL support exercises varying between weeks — the same day number in different weeks may contain different exercises, sets, or target reps
5. WHEN the user views the Workout_Day list, THE App SHALL indicate the current week of the program and allow navigation to any week
6. THE App SHALL determine the number of Workout_Days per week from the loaded program, supporting 1 to 7 days per week as defined by the CSV upload

### Requirement 10: Progressive Web App Installation

**User Story:** As a user, I want to install the app to my Android home screen like a native app, so that I can launch it with a single tap in full-screen mode without browser chrome.

#### Acceptance Criteria

1. THE App SHALL include a valid web app manifest (`manifest.json`) with: app name, short name, start URL, display mode set to "standalone", theme color, background color, and at least one icon in 192x192 and 512x512 pixel sizes
2. THE App SHALL register a service worker that caches the application shell (HTML, CSS, JS) for offline-capable loading of the UI
3. WHEN the user accesses the App via Chrome on Android, THE App SHALL meet Chrome's installability criteria such that the browser presents an "Add to Home Screen" prompt or allows installation via the browser menu
4. WHEN launched from the home screen, THE App SHALL display in standalone mode (full-screen without browser address bar or navigation controls)
5. THE App SHALL include appropriate meta tags in the HTML for mobile web app capability (viewport, theme-color, apple-mobile-web-app-capable for iOS compatibility)
