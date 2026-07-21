/* API client - fetch wrappers for backend endpoints */

const api = {
    getWeeks: () => fetch('/api/program/weeks').then(r => r.json()),

    getDays: (week) => fetch(`/api/program/weeks/${week}/days`).then(r => r.json()),

    getExercises: (week, day) => fetch(`/api/program/weeks/${week}/days/${day}`).then(r => r.json()),

    getCurrentWeek: () => fetch('/api/program/current-week').then(r => r.json()),

    setCurrentWeek: (week) => fetch('/api/program/current-week', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ week: parseInt(week) })
    }).then(r => r.json()),

    getPreviousSession: (week, day) => fetch(`/api/sessions/previous/${week}/${day}`).then(r => r.json()),

    saveSession: (data) => fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(async r => {
        const json = await r.json();
        json._status = r.status;
        return json;
    }),

    getHistory: () => fetch('/api/sessions').then(r => r.json()),

    getSession: (id) => fetch(`/api/sessions/${id}`).then(r => r.json()),

    uploadCSV: (file) => {
        const fd = new FormData();
        fd.append('file', file);
        return fetch('/api/program/upload', { method: 'POST', body: fd }).then(r => r.json());
    },

    saveState: (data) => fetch('/api/state/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(r => r.json()),

    loadState: () => fetch('/api/state/load').then(r => r.json())
};
