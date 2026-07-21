/* History View - displays past workout sessions and session details */

window.views = window.views || {};

window.views['history'] = {
    async render(container, params) {
        container.innerHTML = '<div class="loading"><div class="spinner"></div>Loading...</div>';

        try {
            const data = await api.getHistory();
            const sessions = data.sessions || [];

            if (sessions.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>No workout history available.</p>
                        <a href="#/" class="btn btn-secondary">Go to Workouts</a>
                    </div>
                `;
                return;
            }

            this.renderSessionList(container, sessions);
        } catch (err) {
            container.innerHTML = `
                <div class="error-banner">
                    Cannot connect to server. Please check that the server is running.
                </div>
                <div class="empty-state">
                    <button class="btn btn-primary" onclick="window.views['history'].render(document.getElementById('app'), {})">Retry</button>
                </div>
            `;
        }
    },

    renderSessionList(container, sessions) {
        let html = '<h1>Workout History</h1>';

        sessions.forEach(session => {
            const dateStr = this.formatDate(session.completed_at);
            html += `
                <a class="history-item" href="#/history/${session.id}">
                    <div class="history-item-info">
                        <div class="history-item-title">Week ${session.week}, Day ${session.day}</div>
                        <div class="history-item-date">${this.escapeHtml(dateStr)}</div>
                    </div>
                    <span class="history-item-arrow">&#8250;</span>
                </a>
            `;
        });

        container.innerHTML = html;
    },

    formatDate(isoStr) {
        if (!isoStr) return '';
        try {
            const date = new Date(isoStr);
            if (isNaN(date.getTime())) return isoStr;
            return date.toLocaleDateString(undefined, {
                weekday: 'short',
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            return isoStr;
        }
    },

    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};

window.views['history-detail'] = {
    async render(container, params) {
        const { id } = params;
        container.innerHTML = '<div class="loading"><div class="spinner"></div>Loading...</div>';

        try {
            const session = await api.getSession(id);

            if (session.error === 'not_found') {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>Session not found.</p>
                        <a href="#/history" class="btn btn-secondary">Back to History</a>
                    </div>
                `;
                return;
            }

            this.renderSessionDetail(container, session);
        } catch (err) {
            container.innerHTML = `
                <div class="error-banner">
                    Cannot connect to server. Please check that the server is running.
                </div>
                <div class="empty-state">
                    <button class="btn btn-primary" onclick="window.views['history-detail'].render(document.getElementById('app'), { id: '${id}' })">Retry</button>
                </div>
            `;
        }
    },

    renderSessionDetail(container, session) {
        const dateStr = this.formatDate(session.completed_at);
        const exercises = session.exercises || {};

        let html = `
            <a href="#/history" class="btn btn-secondary mb-16">&larr; Back to History</a>
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Week ${session.week}, Day ${session.day}</div>
                        <div class="card-subtitle">${this.escapeHtml(dateStr)}</div>
                    </div>
                </div>
            </div>
        `;

        const exerciseNames = Object.keys(exercises);

        if (exerciseNames.length === 0) {
            html += '<div class="empty-state"><p>No exercises recorded in this session.</p></div>';
        } else {
            exerciseNames.forEach(name => {
                const exercise = exercises[name];
                const sets = exercise.sets || [];
                const note = exercise.note || '';

                html += `<div class="exercise-card">`;
                html += `<div class="exercise-name">${this.escapeHtml(name)}</div>`;

                if (sets.length > 0) {
                    html += '<div class="sets-container">';
                    sets.forEach(set => {
                        html += `
                            <div class="set-row">
                                <span class="set-label">${set.set_number}</span>
                                <div class="input-group">
                                    <span>${set.weight} kg</span>
                                </div>
                                <div class="input-group">
                                    <span>${set.reps} reps</span>
                                </div>
                            </div>
                        `;
                    });
                    html += '</div>';
                } else {
                    html += '<p class="text-muted text-small">No sets recorded</p>';
                }

                if (note) {
                    html += `<div class="notes-section">`;
                    html += `<span class="notes-label">Notes</span>`;
                    html += `<p class="text-small mt-8">${this.escapeHtml(note)}</p>`;
                    html += `</div>`;
                }

                html += `</div>`;
            });
        }

        container.innerHTML = html;
    },

    formatDate(isoStr) {
        if (!isoStr) return '';
        try {
            const date = new Date(isoStr);
            if (isNaN(date.getTime())) return isoStr;
            return date.toLocaleDateString(undefined, {
                weekday: 'short',
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            return isoStr;
        }
    },

    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
