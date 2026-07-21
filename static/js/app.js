/* Page router - hash-based client-side navigation */

const router = {
    routes: [
        { pattern: /^#\/workout\/(\d+)\/(\d+)$/, view: 'workout', params: ['week', 'day'] },
        { pattern: /^#\/history\/(\d+)$/, view: 'history-detail', params: ['id'] },
        { pattern: /^#\/history$/, view: 'history', params: [] },
        { pattern: /^#\/upload$/, view: 'upload', params: [] },
        { pattern: /^#\/$/, view: 'day-select', params: [] }
    ],

    appContainer: null,

    init() {
        this.appContainer = document.getElementById('app');
        window.addEventListener('hashchange', () => this.navigate());
        // Set default hash if none present
        if (!window.location.hash || window.location.hash === '#') {
            window.location.hash = '#/';
        } else {
            this.navigate();
        }
    },

    navigate() {
        const hash = window.location.hash || '#/';
        let matched = false;

        for (const route of this.routes) {
            const match = hash.match(route.pattern);
            if (match) {
                const params = {};
                route.params.forEach((name, i) => {
                    params[name] = match[i + 1];
                });
                this.render(route.view, params);
                matched = true;
                break;
            }
        }

        if (!matched) {
            // Default to day selection for unknown routes
            window.location.hash = '#/';
            return;
        }

        this.updateActiveNav(hash);
    },

    updateActiveNav(hash) {
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => link.classList.remove('active'));

        let activeNav = 'home';
        if (hash.startsWith('#/history')) {
            activeNav = 'history';
        } else if (hash.startsWith('#/upload')) {
            activeNav = 'upload';
        } else if (hash.startsWith('#/workout')) {
            activeNav = 'home';
        }

        const activeLink = document.querySelector(`.nav-link[data-nav="${activeNav}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
    },

    async render(viewName, params) {
        // View modules are loaded from static/js/views/
        const viewModules = {
            'day-select': '/static/js/views/day-select.js',
            'workout': '/static/js/views/workout.js',
            'history': '/static/js/views/history.js',
            'history-detail': '/static/js/views/history.js',
            'upload': '/static/js/views/upload.js'
        };

        // Check if view module is already loaded
        const view = window.views && window.views[viewName];
        if (view && typeof view.render === 'function') {
            view.render(this.appContainer, params);
            return;
        }

        // Show loading state while view loads
        this.appContainer.innerHTML = '<div class="loading"><div class="spinner"></div>Loading...</div>';

        // Try to load the view module dynamically
        const modulePath = viewModules[viewName];
        if (modulePath) {
            try {
                await this.loadScript(modulePath);
                const loadedView = window.views && window.views[viewName];
                if (loadedView && typeof loadedView.render === 'function') {
                    loadedView.render(this.appContainer, params);
                } else {
                    this.appContainer.innerHTML = '<div class="empty-state"><p>View not available yet.</p></div>';
                }
            } catch (e) {
                this.appContainer.innerHTML = '<div class="empty-state"><p>View not available yet.</p></div>';
            }
        } else {
            this.appContainer.innerHTML = '<div class="empty-state"><p>Page not found.</p></div>';
        }
    },

    loadScript(src) {
        return new Promise((resolve, reject) => {
            // Check if already loaded
            const existing = document.querySelector(`script[src="${src}"]`);
            if (existing) {
                resolve();
                return;
            }
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.body.appendChild(script);
        });
    }
};

// Initialize views namespace
window.views = window.views || {};

// Start the router when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    router.init();
});
