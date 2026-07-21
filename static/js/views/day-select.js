/* Day Selection View - displays workout days for the current week */

window.views = window.views || {};

window.views['day-select'] = {
    async render(container, params) {
        container.innerHTML = '<div class="loading"><div class="spinner"></div>Loading...</div>';

        try {
            const data = await api.getCurrentWeek();
            const { current_week, days_per_week, total_weeks } = data;

            // Show empty state if no program is loaded
            if (!days_per_week || !total_weeks) {
                this.renderEmptyState(container);
                return;
            }

            // Render the day selection with the current week
            this.renderWeekView(container, current_week, days_per_week, total_weeks);
        } catch (err) {
            container.innerHTML = `
                <div class="error-banner">
                    Cannot connect to server. Please check that the server is running.
                </div>
                <div class="empty-state">
                    <button class="btn btn-primary" onclick="window.views['day-select'].render(document.getElementById('app'), {})">Retry</button>
                </div>
            `;
        }
    },

    renderEmptyState(container) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No program available.</p>
                <a href="#/upload" class="btn btn-primary">Upload a Program</a>
            </div>
        `;
    },

    renderWeekView(container, week, daysPerWeek, totalWeeks) {
        const prevDisabled = week <= 1;
        const nextDisabled = week >= totalWeeks;

        let html = `
            <div class="week-nav">
                <button class="btn btn-secondary" id="prev-week-btn"${prevDisabled ? ' disabled' : ''}>&#9664; Prev</button>
                <span class="week-label">Week ${week} of ${totalWeeks}</span>
                <button class="btn btn-secondary" id="next-week-btn"${nextDisabled ? ' disabled' : ''}>Next &#9654;</button>
            </div>
            <div id="day-cards">
        `;

        for (let d = 1; d <= daysPerWeek; d++) {
            html += `
                <a class="day-card" href="#/workout/${week}/${d}" data-day="${d}">
                    <span class="day-card-label">Day ${d}</span>
                    <span class="day-card-arrow">&#8250;</span>
                </a>
            `;
        }

        html += '</div>';
        container.innerHTML = html;

        // Attach navigation listeners
        const prevBtn = document.getElementById('prev-week-btn');
        const nextBtn = document.getElementById('next-week-btn');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (week > 1) {
                    this.renderWeekView(container, week - 1, daysPerWeek, totalWeeks);
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (week < totalWeeks) {
                    this.renderWeekView(container, week + 1, daysPerWeek, totalWeeks);
                }
            });
        }
    }
};
