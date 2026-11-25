"""Unit tests for either-or exercises, the optional Notes (cue) column, and
the dropdown options returned with a day's exercises."""
import io
import os
import sqlite3
import tempfile

import pytest

from app import create_app
from csv_parser import parse_csv
from database import get_db, init_db
from exercise_variants import build_options, split_variants


# --- split_variants / build_options -----------------------------------------

class TestSplitVariants:
    def test_splits_on_or(self):
        assert split_variants("Hack Squats or Bulgarian Split Squat") == [
            "Hack Squats", "Bulgarian Split Squat"
        ]

    def test_is_case_insensitive(self):
        assert split_variants("Hack Squats OR Leg Press") == ["Hack Squats", "Leg Press"]

    def test_three_way(self):
        assert split_variants("A or B or C") == ["A", "B", "C"]

    def test_plain_name_is_not_split(self):
        assert split_variants("Chest Press") == []

    def test_slash_is_not_a_separator(self):
        assert split_variants("Chin-ups / Ring Chins") == []

    def test_or_inside_a_word_is_not_a_separator(self):
        assert split_variants("Hip Thrust Floor Press") == []
        assert split_variants("Doorway Row") == []

    def test_or_inside_parentheses_is_not_a_separator(self):
        assert split_variants("Ring Chins (pause or slow)") == []

    def test_parenthetical_suffix_is_kept_on_its_part(self):
        assert split_variants("Chin-ups or Ring Chins (w/ rotation)") == [
            "Chin-ups", "Ring Chins (w/ rotation)"
        ]


class TestBuildOptions:
    def test_includes_names_as_written_and_their_parts_sorted_without_duplicates(self):
        options = build_options([
            "Row Machine",
            "Hack Squats or Bulgarian Split Squat",
            "Row Machine",
            "Bulgarian Split Squat",
        ])
        assert options == [
            "Bulgarian Split Squat",
            "Hack Squats",
            "Hack Squats or Bulgarian Split Squat",
            "Row Machine",
        ]


# --- CSV Notes column --------------------------------------------------------

HEADER = "Week,Day,Exercise,Sets,Target Reps"


class TestCsvNotesColumn:
    def test_notes_column_is_read_as_cue(self):
        result = parse_csv(f"{HEADER},Notes\n1,1,Chest Press,3,5-8,Control the lowering\n")
        assert result.success
        assert result.exercises[0].cue == "Control the lowering"

    def test_notes_column_is_optional(self):
        result = parse_csv(f"{HEADER}\n1,1,Chest Press,3,5-8\n")
        assert result.success
        assert result.exercises[0].cue == ""

    def test_blank_or_missing_notes_cell_means_no_cue(self):
        result = parse_csv(f"{HEADER},Notes\n1,1,Chest Press,3,5-8,\n1,1,Row,3,8-12\n")
        assert result.success
        assert [e.cue for e in result.exercises] == ["", ""]

    def test_notes_column_can_be_anywhere_and_commas_can_be_quoted(self):
        result = parse_csv('Notes,Week,Day,Exercise,Sets,Target Reps\n"Pause, then press",1,1,Chest Press,3,5-8\n')
        assert result.success
        assert result.exercises[0].cue == "Pause, then press"

    def test_notes_over_500_characters_is_rejected_with_row_number(self):
        result = parse_csv(f"{HEADER},Notes\n1,1,Chest Press,3,5-8,{'x' * 501}\n")
        assert not result.success
        assert any("Row 2" in e and "Notes" in e for e in result.errors)

    def test_notes_of_exactly_500_characters_is_accepted(self):
        result = parse_csv(f"{HEADER},Notes\n1,1,Chest Press,3,5-8,{'x' * 500}\n")
        assert result.success


# --- Routes and migration ----------------------------------------------------

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(test_config={'DATABASE': db_path, 'TESTING': True})
    yield app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


PROGRAM = (
    f"{HEADER},Notes\n"
    "1,1,Chest Press,3,5-8,Heavy and controlled\n"
    "1,1,Hack Squats or Bulgarian Split Squat,3,6-10,Pick one and note which\n"
    "1,2,Row Machine,3,8-12,\n"
    "2,1,Chest Press,3,5-8,Heavy and controlled\n"
    "2,2,Row Machine,3,8-12,\n"
)


def upload(client, content):
    return client.post(
        '/api/program/upload',
        data={'file': (io.BytesIO(content.encode('utf-8')), 'program.csv')},
        content_type='multipart/form-data',
    )


class TestDayExercisesResponse:
    def test_returns_cue_and_variants_per_exercise(self, client):
        assert upload(client, PROGRAM).status_code == 200
        data = client.get('/api/program/weeks/1/days/1').get_json()
        chest, either_or = data['exercises']
        assert chest['cue'] == "Heavy and controlled"
        assert chest['variants'] == []
        assert either_or['exercise_name'] == "Hack Squats or Bulgarian Split Squat"
        assert either_or['variants'] == ["Hack Squats", "Bulgarian Split Squat"]
        assert either_or['cue'] == "Pick one and note which"

    def test_options_cover_the_whole_program_not_just_the_day(self, client):
        upload(client, PROGRAM)
        data = client.get('/api/program/weeks/1/days/1').get_json()
        assert data['options'] == [
            "Bulgarian Split Squat",
            "Chest Press",
            "Hack Squats",
            "Hack Squats or Bulgarian Split Squat",
            "Row Machine",
        ]

    def test_cues_map_only_has_exercises_with_a_cue(self, client):
        upload(client, PROGRAM)
        cues = client.get('/api/program/weeks/1/days/1').get_json()['cues']
        assert cues["Chest Press"] == "Heavy and controlled"
        assert "Row Machine" not in cues

    def test_program_without_notes_column_still_works(self, client):
        upload(client, f"{HEADER}\n1,1,Chest Press,3,5-8\n")
        data = client.get('/api/program/weeks/1/days/1').get_json()
        assert data['exercises'][0]['cue'] == ""


class TestHistoryFollowsTheChosenExercise:
    def test_session_saved_under_a_variant_feeds_that_exercises_history(self, client):
        upload(client, PROGRAM)
        resp = client.post('/api/sessions', json={
            'week': 1, 'day': 1,
            'sets': [{'exercise_name': 'Hack Squats', 'set_number': 1, 'weight': 200, 'reps': 8}],
            'notes': [{'exercise_name': 'Hack Squats', 'note': 'felt good'}],
        })
        assert resp.status_code == 201

        prev = client.get('/api/sessions/previous-by-exercise?exercises=Hack Squats,Bulgarian Split Squat').get_json()
        assert prev['exercises']['Hack Squats']['sets'][0]['weight'] == 200
        assert prev['exercises']['Hack Squats']['note'] == 'felt good'
        assert 'Bulgarian Split Squat' not in prev['exercises']


class TestCueMigration:
    def test_existing_database_gains_cue_column_and_keeps_its_rows(self, tmp_path):
        db_path = str(tmp_path / 'old.db')
        old = sqlite3.connect(db_path)
        old.executescript('''
            CREATE TABLE exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week INTEGER NOT NULL, day INTEGER NOT NULL,
                exercise_name TEXT NOT NULL, target_sets INTEGER NOT NULL,
                target_reps TEXT NOT NULL, sort_order INTEGER NOT NULL,
                UNIQUE(week, day, exercise_name)
            );
            INSERT INTO exercises (week, day, exercise_name, target_sets, target_reps, sort_order)
                VALUES (1, 1, 'Chest Press', 3, '5-8', 1);
        ''')
        old.commit()
        old.close()

        app = create_app(test_config={'DATABASE': db_path, 'TESTING': True})
        with app.app_context():
            db = get_db()
            row = db.execute('SELECT exercise_name, cue FROM exercises').fetchone()
            assert row['exercise_name'] == 'Chest Press'
            assert row['cue'] == ''
            init_db()  # running again must be harmless
            assert db.execute('SELECT COUNT(*) FROM exercises').fetchone()[0] == 1


# --- Exercises typed in as "other" -------------------------------------------

def save_session(client, name, note='', week=1, day=1):
    return client.post('/api/sessions', json={
        'week': week, 'day': day,
        'sets': [{'exercise_name': name, 'set_number': 1, 'weight': 20, 'reps': 10}],
        'notes': [{'exercise_name': name, 'note': note}],
    })


class TestCustomExercisesJoinTheOptions:
    def test_saved_custom_exercise_is_offered_on_every_day(self, client):
        upload(client, PROGRAM)
        assert 'Cable Fly' not in client.get('/api/program/weeks/1/days/1').get_json()['options']

        assert save_session(client, 'Cable Fly').status_code == 201

        for week, day in [(1, 1), (1, 2), (2, 2)]:
            options = client.get(f'/api/program/weeks/{week}/days/{day}').get_json()['options']
            assert 'Cable Fly' in options

    def test_options_stay_sorted_and_without_duplicates(self, client):
        upload(client, PROGRAM)
        save_session(client, 'Chest Press')  # already in the program
        save_session(client, 'Cable Fly', week=1, day=2)
        options = client.get('/api/program/weeks/1/days/1').get_json()['options']
        assert options.count('Chest Press') == 1
        assert options == sorted(options, key=lambda n: (n.lower(), n))

    def test_either_or_name_saved_in_history_also_offers_its_parts(self, client):
        upload(client, f"{HEADER}\n1,1,Row Machine,3,8-12\n")
        save_session(client, 'Leg Press or Hack Squats')
        options = client.get('/api/program/weeks/1/days/1').get_json()['options']
        assert {'Leg Press or Hack Squats', 'Leg Press', 'Hack Squats'} <= set(options)

    def test_blank_note_alone_does_not_add_an_option(self, client):
        upload(client, PROGRAM)
        # Notes with no sets and no text are written for every slot on save
        client.post('/api/sessions', json={
            'week': 1, 'day': 1, 'sets': [],
            'notes': [{'exercise_name': 'Ghost Exercise', 'note': ''}],
        })
        options = client.get('/api/program/weeks/1/days/1').get_json()['options']
        assert 'Ghost Exercise' not in options

    def test_note_with_text_and_no_sets_does_add_an_option(self, client):
        upload(client, PROGRAM)
        client.post('/api/sessions', json={
            'week': 1, 'day': 1, 'sets': [],
            'notes': [{'exercise_name': 'Stretching', 'note': '10 minutes'}],
        })
        options = client.get('/api/program/weeks/1/days/1').get_json()['options']
        assert 'Stretching' in options

    def test_options_survive_uploading_a_new_program(self, client):
        upload(client, PROGRAM)
        save_session(client, 'Cable Fly')
        upload(client, f"{HEADER}\n1,1,Squat,3,5\n")
        options = client.get('/api/program/weeks/1/days/1').get_json()['options']
        assert 'Cable Fly' in options and 'Squat' in options


class TestHistoryLookupParameters:
    def test_name_with_a_comma_is_looked_up_as_one_exercise(self, client):
        upload(client, PROGRAM)
        save_session(client, 'Dips, weighted', note='chest forward')
        resp = client.get('/api/sessions/previous-by-exercise', query_string={'name': 'Dips, weighted'})
        exercises = resp.get_json()['exercises']
        assert list(exercises) == ['Dips, weighted']
        assert exercises['Dips, weighted']['note'] == 'chest forward'

    def test_repeated_name_parameters_look_up_each_exercise(self, client):
        upload(client, PROGRAM)
        save_session(client, 'Cable Fly')
        save_session(client, 'Chest Press', week=1, day=2)
        resp = client.get('/api/sessions/previous-by-exercise?name=Cable Fly&name=Chest Press&name=Unknown')
        assert set(resp.get_json()['exercises']) == {'Cable Fly', 'Chest Press'}

    def test_legacy_comma_separated_parameter_still_works(self, client):
        upload(client, PROGRAM)
        save_session(client, 'Cable Fly')
        resp = client.get('/api/sessions/previous-by-exercise?exercises=Cable Fly,Unknown')
        assert set(resp.get_json()['exercises']) == {'Cable Fly'}
