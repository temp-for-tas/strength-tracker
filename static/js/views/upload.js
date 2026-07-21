/* Upload View - CSV file upload with drag-and-drop support */

window.views = window.views || {};

window.views['upload'] = {
    async render(container, params) {
        this.container = container;
        this.renderUploadForm();
    },

    renderUploadForm() {
        this.container.innerHTML = `
            <h1>Upload Program</h1>
            <div class="upload-area" id="upload-drop-area">
                <p>Select a CSV file to upload your program</p>
                <label class="file-input-label" for="csv-file-input">Choose File</label>
                <input type="file" id="csv-file-input" accept=".csv">
            </div>
        `;

        this.attachListeners();
    },

    attachListeners() {
        const dropArea = document.getElementById('upload-drop-area');
        const fileInput = document.getElementById('csv-file-input');

        // Drag-and-drop events
        dropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropArea.classList.add('drag-over');
        });

        dropArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropArea.classList.remove('drag-over');
        });

        dropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            dropArea.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFile(files[0]);
            }
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFile(e.target.files[0]);
            }
        });
    },

    async handleFile(file) {
        this.showLoading();

        try {
            const result = await api.uploadCSV(file);

            if (result.error) {
                this.showError(result);
            } else if (result.success) {
                this.showSuccess(result);
            } else {
                this.showError({ error: 'unknown', message: 'Unexpected response from server.' });
            }
        } catch (err) {
            this.showError({ error: 'network', message: 'Cannot connect to server. Please check that the server is running.' });
        }
    },

    showLoading() {
        this.container.innerHTML = `
            <h1>Upload Program</h1>
            <div class="loading"><div class="spinner"></div>Uploading...</div>
        `;
    },

    showSuccess(result) {
        const { weeks, days_per_week, total_exercises } = result;
        this.container.innerHTML = `
            <h1>Upload Program</h1>
            <div class="success-banner">
                Program uploaded! ${weeks} weeks, ${days_per_week} days/week, ${total_exercises} exercises.
            </div>
            <a href="#/" class="btn btn-primary btn-block">Go to Day Selection</a>
            <button class="btn btn-secondary btn-block mt-16" id="upload-another-btn">Upload Another</button>
        `;

        document.getElementById('upload-another-btn').addEventListener('click', () => {
            this.renderUploadForm();
        });
    },

    showError(result) {
        let errorContent = '';

        if (result.error === 'file_too_large') {
            errorContent = `
                <div class="error-banner">
                    File is too large. Maximum file size is ${result.max_size || '1MB'}.
                </div>
            `;
        } else if (result.error === 'csv_parse' && result.rows && result.rows.length > 0) {
            errorContent = `
                <div class="error-banner">CSV contains errors. Please fix the following issues and try again.</div>
                <table class="error-table">
                    <thead>
                        <tr><th>Error</th></tr>
                    </thead>
                    <tbody>
                        ${result.rows.map(row => `<tr><td>${this.escapeHtml(row)}</td></tr>`).join('')}
                    </tbody>
                </table>
            `;
        } else if (result.error === 'network') {
            errorContent = `
                <div class="error-banner">${this.escapeHtml(result.message)}</div>
            `;
        } else {
            const message = result.message || result.error || 'An unexpected error occurred.';
            errorContent = `
                <div class="error-banner">${this.escapeHtml(message)}</div>
            `;
        }

        this.container.innerHTML = `
            <h1>Upload Program</h1>
            ${errorContent}
            <button class="btn btn-primary btn-block mt-16" id="retry-upload-btn">Try Again</button>
        `;

        document.getElementById('retry-upload-btn').addEventListener('click', () => {
            this.renderUploadForm();
        });
    },

    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
