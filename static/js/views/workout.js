/* Workout View - exercise data entry with validation and previous performance display */

window.views = window.views || {};

window.views['workout'] = {
    // Local state for entered data (accessible by save functionality in task 7.2)
    state: {
        week: null,
        day: null,
        exercises: [],
        sets: {},      // { "exerciseName": { 1: { weight: "", reps: "" }, 2: {...}, ... } }
        notes: {},     // { "exerciseName": "note text" }
        dirty: false
    },

    // Auto-save debounce timer
    _autoSaveTimer: null,
    _autoSaveDelay: 2000, // 2 seconds of inactivity

    async render(container, params) {
        const { week, day } = params;
        this.state.week = week;
        this.state.day = day;

        container.innerHTML = '<div class="loading"><div class="spinner"></div>Loading...</div>';

        try {
            const [exerciseData, previousData, savedState] = await Promise.all([
                api.getExercises(week, day),
                api.getPreviousSession(week, day),
                api.loadState()
            ]);

            // Persist the current week so the Days tab returns here
            api.setCurrentWeek(week);

            this.state.exercises = exerciseData.exercises || [];
            this.initState(this.state.exercises);

            // Restore saved in-progress state if it matches current week/day
            if (savedState && savedState.value &&
                savedState.value.week == week && savedState.value.day == day) {
                this.restoreSavedState(savedState.value);
            }

            this.renderWorkout(container, exerciseData, previousData);
        } catch (err) {
            container.innerHTML = `
                <div class="error-banner">
                    Cannot connect to server. Please check that the server is running.
                </div>
                <div class="empty-state">
                    <button class="btn btn-primary" onclick="window.views['workout'].render(document.getElementById('app'), { week: '${week}', day: '${day}' })">Retry</button>
                </div>
            `;
        }
    },

    initState(exercises) {
        // Initialize sets and notes for each exercise if not already set
        exercises.forEach(ex => {
            const name = ex.exercise_name;
            const targetSets = ex.target_sets || 4;
            if (!this.state.sets[name]) {
                this.state.sets[name] = {};
                for (let i = 1; i <= targetSets; i++) {
                    this.state.sets[name][i] = { weight: '', reps: '' };
                }
            }
            if (this.state.notes[name] === undefined) {
                this.state.notes[name] = '';
            }
        });

        // Expose state globally for save functionality (task 7.2)
        window.workoutState = this.state;
    },

    renderWorkout(container, exerciseData, previousData) {
        const { week, day } = this.state;
        const exercises = exerciseData.exercises || [];
        const prevExercises = previousData.exercises || {};
        const hasPrevious = previousData.session_id !== null && previousData.session_id !== undefined;

        let html = `
            <a href="#/" class="btn btn-secondary mb-16">&larr; Back to Days</a>
            <h1>Week ${week}, Day ${day}</h1>
            <div id="workout-error-banner" class="error-banner hidden"></div>
        `;

        if (exercises.length === 0) {
            html += '<div class="empty-state"><p>No exercises found for this day.</p></div>';
            container.innerHTML = html;
            return;
        }

        exercises.forEach((ex, idx) => {
            const name = ex.exercise_name;
            const prevEx = prevExercises[name];
            const prevNote = prevEx ? prevEx.note : null;

            html += `<div class="exercise-card" data-exercise="${this.escapeAttr(name)}">`;
            html += `<div class="exercise-name">${this.escapeHtml(name)}</div>`;
            html += `<div class="exercise-target">${ex.target_sets} sets &times; ${this.escapeHtml(ex.target_reps)} reps</div>`;

            // Previous performance
            html += this.renderPreviousPerformance(prevEx, hasPrevious, prevNote, ex.target_sets);

            // Set input rows based on target_sets (1-10)
            const targetSets = ex.target_sets || 4;
            html += '<div class="sets-container">';
            for (let s = 1; s <= targetSets; s++) {
                const prevSet = prevEx && prevEx.sets ? prevEx.sets.find(ps => ps.set_number === s) : null;
                const currentWeight = this.state.sets[name] && this.state.sets[name][s] ? this.state.sets[name][s].weight : '';
                const currentReps = this.state.sets[name] && this.state.sets[name][s] ? this.state.sets[name][s].reps : '';

                html += `<div class="set-row">`;
                html += `<span class="set-label">${s}</span>`;
                html += `<div class="input-group">`;
                html += `<label for="weight-${idx}-${s}">Weight</label>`;
                html += `<input type="number" id="weight-${idx}-${s}" step="0.5" min="0" max="9999" 
                    placeholder="${prevSet ? prevSet.weight : ''}" 
                    value="${this.escapeAttr(currentWeight)}"
                    data-exercise="${this.escapeAttr(name)}" data-set="${s}" data-field="weight"
                    aria-label="Weight for set ${s}">`;
                html += `<div class="error-message" id="error-weight-${idx}-${s}"></div>`;
                html += `</div>`;
                html += `<div class="input-group">`;
                html += `<label for="reps-${idx}-${s}">Reps</label>`;
                html += `<input type="number" id="reps-${idx}-${s}" step="1" min="0" max="999" 
                    placeholder="${prevSet ? prevSet.reps : ''}" 
                    value="${this.escapeAttr(currentReps)}"
                    data-exercise="${this.escapeAttr(name)}" data-set="${s}" data-field="reps"
                    aria-label="Reps for set ${s}">`;
                html += `<div class="error-message" id="error-reps-${idx}-${s}"></div>`;
                html += `</div>`;
                html += `</div>`;
            }
            html += '</div>';

            // Notes section
            const currentNote = this.state.notes[name] || '';
            const charCount = currentNote.length;
            html += `<div class="notes-section">`;
            html += `<label class="notes-label" for="note-${idx}">Notes</label>`;
            if (hasPrevious && prevNote) {
                html += `<div class="text-small text-muted mb-8">Previous: ${this.escapeHtml(prevNote)}</div>`;
            }
            html += `<textarea id="note-${idx}" maxlength="500" 
                data-exercise="${this.escapeAttr(name)}" 
                placeholder="Add notes about form, difficulty, etc."
                aria-label="Notes for ${this.escapeAttr(name)}">${this.escapeHtml(currentNote)}</textarea>`;
            html += `<div class="notes-char-count${charCount >= 450 ? (charCount >= 500 ? ' at-limit' : ' near-limit') : ''}" id="charcount-${idx}">${charCount}/500</div>`;
            html += `</div>`;

            html += `</div>`;
        });

        container.innerHTML = html;
        this.attachEventListeners(container, exercises);
        this.renderSaveButton();
    },

    renderSaveButton() {
        // Remove existing save button container if present
        const existing = document.querySelector('.save-btn-container');
        if (existing) existing.remove();

        const saveContainer = document.createElement('div');
        saveContainer.className = 'save-btn-container';
        saveContainer.innerHTML = `
            <button class="btn btn-primary btn-block" id="save-workout-btn" aria-label="Save Workout">
                Save Workout
            </button>
        `;
        document.body.appendChild(saveContainer);

        document.getElementById('save-workout-btn').addEventListener('click', () => this.handleSave());
    },

    removeSaveButton() {
        const existing = document.querySelector('.save-btn-container');
        if (existing) existing.remove();
    },

    async handleSave() {
        // Check for validation errors on filled fields
        if (this.hasValidationErrors()) {
            this.showErrorBanner('Fix validation errors before saving');
            return;
        }

        const sets = this.getEnteredSets();

        // If no sets recorded, show warning modal
        if (sets.length === 0) {
            this.showModal(
                'No sets recorded',
                'You haven\'t recorded any sets. Are you sure you want to save this workout?',
                'Save Anyway',
                'Cancel',
                () => this.submitSave(sets),
                null
            );
            return;
        }

        // Show confirmation modal
        this.showModal(
            'Save this workout session?',
            `You have recorded ${sets.length} set${sets.length !== 1 ? 's' : ''}. Save this workout?`,
            'Save',
            'Cancel',
            () => this.submitSave(sets),
            null
        );
    },

    async submitSave(sets) {
        this.dismissModal();

        const saveBtn = document.getElementById('save-workout-btn');
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
        }

        const payload = {
            week: parseInt(this.state.week),
            day: parseInt(this.state.day),
            sets: sets,
            notes: this.getEnteredNotes()
        };

        try {
            const result = await api.saveSession(payload);

            if (result._status === 201) {
                // Success
                this.hideErrorBanner();
                this.showToast('Workout saved!', 'success');
                this.resetState();
                this.clearSavedState();
                this.removeSaveButton();
                setTimeout(() => {
                    window.location.hash = '#/';
                }, 1500);
            } else if (result._status === 400) {
                // Validation errors from server
                const details = result.details || [result.message || 'Validation failed'];
                this.showErrorBanner(details.join('. '));
                if (saveBtn) {
                    saveBtn.disabled = false;
                    saveBtn.textContent = 'Save Workout';
                }
            } else {
                // Other server errors
                this.showToast('Failed to save. Please try again.', 'error');
                if (saveBtn) {
                    saveBtn.disabled = false;
                    saveBtn.textContent = 'Save Workout';
                }
            }
        } catch (err) {
            // Network error
            this.showToast('Failed to save. Please try again.', 'error');
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save Workout';
            }
        }
    },

    showModal(title, body, confirmText, cancelText, onConfirm, onCancel) {
        // Remove existing modal if any
        this.dismissModal();

        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.id = 'workout-modal';
        overlay.innerHTML = `
            <div class="modal" role="dialog" aria-labelledby="modal-title" aria-modal="true">
                <div class="modal-title" id="modal-title">${this.escapeHtml(title)}</div>
                <div class="modal-body">${this.escapeHtml(body)}</div>
                <div class="modal-actions">
                    <button class="btn btn-secondary" id="modal-cancel">${this.escapeHtml(cancelText)}</button>
                    <button class="btn btn-primary" id="modal-confirm">${this.escapeHtml(confirmText)}</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        document.getElementById('modal-cancel').addEventListener('click', () => {
            this.dismissModal();
            if (onCancel) onCancel();
        });

        document.getElementById('modal-confirm').addEventListener('click', () => {
            if (onConfirm) onConfirm();
        });

        // Close modal on overlay click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.dismissModal();
                if (onCancel) onCancel();
            }
        });
    },

    dismissModal() {
        const modal = document.getElementById('workout-modal');
        if (modal) modal.remove();
    },

    showToast(message, type) {
        // Remove existing toast
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = `toast ${type || ''}`;
        toast.textContent = message;
        toast.setAttribute('role', 'alert');
        document.body.appendChild(toast);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (toast.parentNode) toast.remove();
        }, 3000);
    },

    showErrorBanner(message) {
        const banner = document.getElementById('workout-error-banner');
        if (banner) {
            banner.textContent = message;
            banner.classList.remove('hidden');
        }
    },

    hideErrorBanner() {
        const banner = document.getElementById('workout-error-banner');
        if (banner) {
            banner.textContent = '';
            banner.classList.add('hidden');
        }
    },

    renderPreviousPerformance(prevEx, hasPrevious, prevNote, targetSets) {
        if (!hasPrevious) {
            return '<div class="no-previous">No previous data</div>';
        }

        if (!prevEx || !prevEx.sets || prevEx.sets.length === 0) {
            return '<div class="no-previous">No previous data for this exercise</div>';
        }

        const numSets = targetSets || 4;
        let html = '<div class="previous-perf">';
        html += '<div class="previous-perf-title">Previous Performance</div>';
        for (let s = 1; s <= numSets; s++) {
            const prevSet = prevEx.sets.find(ps => ps.set_number === s);
            if (prevSet) {
                html += `<div class="previous-perf-set">`;
                html += `<span>Set ${s}:</span>`;
                html += `<span>${prevSet.weight} lb &times; ${prevSet.reps}</span>`;
                html += `</div>`;
            }
        }
        html += '</div>';
        return html;
    },

    attachEventListeners(container, exercises) {
        // Weight and reps inputs - validation on blur/change
        const inputs = container.querySelectorAll('input[type="number"]');
        inputs.forEach(input => {
            input.addEventListener('blur', (e) => this.handleInputChange(e));
            input.addEventListener('change', (e) => this.handleInputChange(e));
            input.addEventListener('input', (e) => this.handleInputUpdate(e));
        });

        // Notes textarea
        const textareas = container.querySelectorAll('textarea');
        textareas.forEach(textarea => {
            textarea.addEventListener('input', (e) => this.handleNoteInput(e));
        });
    },

    handleInputChange(e) {
        const input = e.target;
        const exerciseName = input.dataset.exercise;
        const setNumber = parseInt(input.dataset.set);
        const field = input.dataset.field;
        const value = input.value.trim();

        // Update local state
        if (!this.state.sets[exerciseName]) {
            this.state.sets[exerciseName] = {};
        }
        if (!this.state.sets[exerciseName][setNumber]) {
            this.state.sets[exerciseName][setNumber] = { weight: '', reps: '' };
        }
        this.state.sets[exerciseName][setNumber][field] = value;
        this.state.dirty = true;

        // Validate
        this.validateField(input, field, value);
    },

    handleInputUpdate(e) {
        // Update state on each keystroke (for live state tracking)
        const input = e.target;
        const exerciseName = input.dataset.exercise;
        const setNumber = parseInt(input.dataset.set);
        const field = input.dataset.field;
        const value = input.value.trim();

        if (!this.state.sets[exerciseName]) {
            this.state.sets[exerciseName] = {};
        }
        if (!this.state.sets[exerciseName][setNumber]) {
            this.state.sets[exerciseName][setNumber] = { weight: '', reps: '' };
        }
        this.state.sets[exerciseName][setNumber][field] = value;
        this.state.dirty = true;

        // Schedule auto-save after 2 seconds of inactivity
        this.scheduleAutoSave();
    },

    handleNoteInput(e) {
        const textarea = e.target;
        const exerciseName = textarea.dataset.exercise;
        const value = textarea.value;

        // Enforce max length (maxlength attribute handles this, but also update state)
        this.state.notes[exerciseName] = value.substring(0, 500);
        this.state.dirty = true;

        // Schedule auto-save after 2 seconds of inactivity
        this.scheduleAutoSave();

        // Update character count
        const charCountEl = textarea.parentElement.querySelector('.notes-char-count');
        if (charCountEl) {
            const count = value.length;
            charCountEl.textContent = `${count}/500`;
            charCountEl.classList.remove('near-limit', 'at-limit');
            if (count >= 500) {
                charCountEl.classList.add('at-limit');
            } else if (count >= 450) {
                charCountEl.classList.add('near-limit');
            }
        }
    },

    validateField(input, field, value) {
        const errorEl = input.parentElement.querySelector('.error-message');

        // Allow empty fields
        if (value === '') {
            input.classList.remove('error');
            if (errorEl) errorEl.textContent = '';
            return true;
        }

        if (field === 'weight') {
            return this.validateWeight(input, value, errorEl);
        } else if (field === 'reps') {
            return this.validateReps(input, value, errorEl);
        }
        return true;
    },

    validateWeight(input, value, errorEl) {
        const num = parseFloat(value);

        // Check if it's a valid number
        if (isNaN(num) || value === '') {
            input.classList.add('error');
            if (errorEl) errorEl.textContent = 'Weight must be a number between 0 and 9999';
            return false;
        }

        // Check range (0 is allowed for bodyweight exercises)
        if (num < 0 || num > 9999) {
            input.classList.add('error');
            if (errorEl) errorEl.textContent = 'Weight must be between 0 and 9999';
            return false;
        }

        // Check one decimal place max
        const parts = value.split('.');
        if (parts.length > 1 && parts[1].length > 1) {
            input.classList.add('error');
            if (errorEl) errorEl.textContent = 'Weight allows up to one decimal place';
            return false;
        }

        input.classList.remove('error');
        if (errorEl) errorEl.textContent = '';
        return true;
    },

    validateReps(input, value, errorEl) {
        const num = parseInt(value);

        // Check if it's a valid integer
        if (isNaN(num) || value.includes('.') || value.includes(',')) {
            input.classList.add('error');
            if (errorEl) errorEl.textContent = 'Reps must be a whole number between 0 and 999';
            return false;
        }

        // Check it matches integer pattern
        if (num.toString() !== value) {
            input.classList.add('error');
            if (errorEl) errorEl.textContent = 'Reps must be a whole number between 0 and 999';
            return false;
        }

        // Check range (0 is allowed — means skipped set)
        if (num < 0 || num > 999) {
            input.classList.add('error');
            if (errorEl) errorEl.textContent = 'Reps must be between 0 and 999';
            return false;
        }

        input.classList.remove('error');
        if (errorEl) errorEl.textContent = '';
        return true;
    },

    // Utility: check if there are any validation errors currently displayed
    hasValidationErrors() {
        const errors = document.querySelectorAll('.exercise-card .error-message');
        for (const el of errors) {
            if (el.textContent.trim() !== '') return true;
        }
        return false;
    },

    // Utility: get all entered sets as array for save
    // A set is "entered" if reps is filled in. Weight is optional (blank → 0).
    getEnteredSets() {
        const sets = [];
        for (const [exerciseName, setData] of Object.entries(this.state.sets)) {
            for (const [setNum, values] of Object.entries(setData)) {
                if (values.reps !== '') {
                    sets.push({
                        exercise_name: exerciseName,
                        set_number: parseInt(setNum),
                        weight: values.weight !== '' ? parseFloat(values.weight) : 0,
                        reps: parseInt(values.reps)
                    });
                }
            }
        }
        return sets;
    },

    // Utility: get all notes as array for save (used by task 7.2)
    getEnteredNotes() {
        const notes = [];
        for (const [exerciseName, noteText] of Object.entries(this.state.notes)) {
            notes.push({
                exercise_name: exerciseName,
                note: noteText
            });
        }
        return notes;
    },

    // Utility: reset state (used after successful save)
    resetState() {
        this.state.sets = {};
        this.state.notes = {};
        this.state.dirty = false;
    },

    // Restore saved in-progress state from backend
    restoreSavedState(savedValue) {
        if (savedValue.sets && typeof savedValue.sets === 'object') {
            // Merge saved sets into current state
            for (const [exerciseName, setData] of Object.entries(savedValue.sets)) {
                if (this.state.sets[exerciseName]) {
                    for (const [setNum, values] of Object.entries(setData)) {
                        if (this.state.sets[exerciseName][setNum]) {
                            this.state.sets[exerciseName][setNum] = {
                                weight: values.weight || '',
                                reps: values.reps || ''
                            };
                        }
                    }
                }
            }
        }
        if (savedValue.notes && typeof savedValue.notes === 'object') {
            for (const [exerciseName, noteText] of Object.entries(savedValue.notes)) {
                if (this.state.notes.hasOwnProperty(exerciseName)) {
                    this.state.notes[exerciseName] = noteText || '';
                }
            }
        }
    },

    // Schedule an auto-save after 2 seconds of inactivity
    scheduleAutoSave() {
        if (this._autoSaveTimer) {
            clearTimeout(this._autoSaveTimer);
        }
        this._autoSaveTimer = setTimeout(() => {
            this.autoSave();
        }, this._autoSaveDelay);
    },

    // Perform the auto-save to backend
    async autoSave() {
        if (!this.state.week || !this.state.day) return;

        const payload = {
            key: 'in_progress_workout',
            value: {
                week: parseInt(this.state.week),
                day: parseInt(this.state.day),
                sets: this.state.sets,
                notes: this.state.notes
            }
        };

        try {
            await api.saveState(payload);
        } catch (err) {
            // Auto-save failures are silent - don't disrupt user workflow
        }
    },

    // Clear saved in-progress state (called after successful session save)
    async clearSavedState() {
        try {
            await api.saveState({ key: 'in_progress_workout', value: null });
        } catch (err) {
            // Clearing failures are non-critical
        }
    },

    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    escapeAttr(str) {
        if (str === null || str === undefined) return '';
        return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
};
