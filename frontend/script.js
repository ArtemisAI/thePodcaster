// script.js
const App = {
    API_BASE_URL: '/api',
    ALLOWED_AUDIO_TYPES: ['audio/mpeg', 'audio/wav', 'audio/mp3', 'audio/x-wav'], // Common audio types

    // DOM Elements
    elements: {
        views: null,
        uploadForm: null,
        mainTrackInput: null,
        introTrackInput: null,
        outroTrackInput: null,
        uploadResponseDiv: null,
        jobsList: null,
        libraryList: null,
        vizFileSelect: null,
        processVizBtn: null,
        vizResponseDiv: null,
        jobIdInput: null, // Will be added in HTML
        submitButton: null, // Will be added in HTML
        // Spinners will be handled dynamically
    },

    init: function() {
        // Cache DOM elements
        this.elements.views = document.querySelectorAll('.view');
        this.elements.uploadForm = document.getElementById('uploadForm');
        this.elements.mainTrackInput = document.getElementById('mainTrack');
        this.elements.introTrackInput = document.getElementById('introTrack');
        this.elements.outroTrackInput = document.getElementById('outroTrack');
        this.elements.uploadResponseDiv = document.getElementById('uploadResponse');
        this.elements.jobsList = document.getElementById('jobsList');
        this.elements.libraryList = document.getElementById('libraryList');
        this.elements.vizFileSelect = document.getElementById('vizFileSelect');
        this.elements.processVizBtn = document.getElementById('processVizBtn');
        this.elements.vizResponseDiv = document.getElementById('vizResponse');
        this.elements.jobIdInput = document.getElementById('jobIdInput'); // Assuming this will be added
        this.elements.submitButton = this.elements.uploadForm ? this.elements.uploadForm.querySelector('button[type="submit"]') : null;


        // Event Listeners
        document.querySelectorAll('nav button[data-view]').forEach(button => {
            button.addEventListener('click', () => this.showView(button.dataset.view));
        });
        
        if (this.elements.uploadForm) {
            this.elements.uploadForm.addEventListener('submit', this.handleUploadAndProcess.bind(this));
            // Add input event listeners for validation
            [this.elements.mainTrackInput, this.elements.introTrackInput, this.elements.outroTrackInput].forEach(input => {
                if (input) input.addEventListener('change', this.validateFileInput.bind(this, input));
            });
            this.updateSubmitButtonState(); // Initial state
        }

        // Add listeners for refresh buttons if they exist
        const refreshJobsBtn = document.getElementById('refreshJobsBtn');
        if (refreshJobsBtn) refreshJobsBtn.addEventListener('click', this.fetchJobs.bind(this));
        
        const refreshLibraryBtn = document.getElementById('refreshLibraryBtn');
        if (refreshLibraryBtn) refreshLibraryBtn.addEventListener('click', this.fetchLibrary.bind(this));
        if (this.elements.processVizBtn) this.elements.processVizBtn.addEventListener('click', this.handleVisualizationProcess.bind(this));


        // Tooltip setup (delegated event listener on a parent)
        document.body.addEventListener('mouseover', this.handleTooltipMouseOver.bind(this));
        document.body.addEventListener('mouseout', this.hideAllTooltips.bind(this));


        this.showView('uploadView'); // Default view
    },

    showView: function(viewId) {
        this.elements.views.forEach(view => {
            view.style.display = 'none';
            view.setAttribute('aria-hidden', 'true');
        });
        const targetView = document.getElementById(viewId);
        if (targetView) {
            targetView.style.display = 'block';
            targetView.setAttribute('aria-hidden', 'false');

            // Focus management: Set focus to the view or its first focusable element
            // This helps screen reader users understand the context has changed.
            targetView.focus(); // Set focus to the section itself
            // Or, find the first heading or interactive element if more appropriate
            // const firstFocusable = targetView.querySelector('h2, button, input, a');
            // if (firstFocusable) firstFocusable.focus();


            // Specific actions when a view is shown
            if (viewId === 'jobsView' && this.elements.jobsList.children.length === 0) {
                // this.fetchJobs(); // Optionally auto-fetch
            } else if (viewId === 'libraryView' && this.elements.libraryList.children.length === 0) {
                this.fetchLibrary();
            } else if (viewId === 'visualizationView') {
                this.fetchLibraryForViz();
            }
        } else {
            console.error(`View with ID ${viewId} not found.`);
        }
    },

    displayMessage: function(element, message, type) {
        if (!element) return;
        // Ensure element has an ID for aria-describedby if needed elsewhere, though for alerts aria-live is primary
        // element.id = element.id || `alert-msg-${Date.now()}`; 
        element.className = `alert alert-${type}`;
        element.textContent = message;
        element.style.display = 'block'; 
        // For screen readers, the change in content of an aria-live region is announced.
        // If it was previously hidden and now shown, that change also gets announced.
    },

    clearMessage: function(element) {
        if (!element) return;
        element.textContent = '';
        element.className = ''; // Clear classes to remove styling
        element.style.display = 'none'; 
    },
    
    showSpinner: function(parentElement, clearContent = true) {
        if (!parentElement) return;
        if (clearContent) parentElement.innerHTML = ''; // Clear previous content
        const spinner = document.createElement('div');
        spinner.className = 'spinner';
        spinner.setAttribute('role', 'status'); // Announce as a status region
        
        const spinnerText = document.createElement('span');
        spinnerText.className = 'sr-only'; // Visually hidden text for screen readers
        spinnerText.textContent = 'Loading...';
        spinner.appendChild(spinnerText);

        parentElement.appendChild(spinner);
    },

    hideSpinner: function(parentElement) {
        if (!parentElement) return;
        const spinner = parentElement.querySelector('.spinner');
        if (spinner) spinner.remove();
    },

    validateFileInput: function(inputElement) {
        if (!inputElement || !inputElement.files || inputElement.files.length === 0) {
            this.clearValidationFeedback(inputElement);
            this.updateSubmitButtonState();
            // For optional fields, empty is valid. For required (mainTrack), this will be caught by updateSubmitButtonState.
            return inputElement.id !== 'mainTrack'; 
        }

        const file = inputElement.files[0];
        const feedbackElement = document.getElementById(inputElement.id + 'Feedback'); // Already has aria-live
        let isValid = true;
        let message = '';

        // File Type Check
        if (!this.ALLOWED_AUDIO_TYPES.includes(file.type)) {
            message = `Invalid file type for ${file.name}. Allowed: ${this.ALLOWED_AUDIO_TYPES.join(', ')}.`;
            isValid = false;
        }
        // File Size Check removed (no client-side size limit)

        if (!isValid && feedbackElement) {
            feedbackElement.textContent = message;
            inputElement.classList.add('is-invalid');
            inputElement.setAttribute('aria-invalid', 'true');
        } else if (feedbackElement) {
            this.clearValidationFeedback(inputElement);
        }
        
        this.updateSubmitButtonState();
        return isValid;
    },
    
    clearValidationFeedback: function(inputElement) {
        const feedbackElement = document.getElementById(inputElement.id + 'Feedback');
        if (feedbackElement) {
            feedbackElement.textContent = ''; // Content removal will be announced by aria-live
        }
        inputElement.classList.remove('is-invalid');
        inputElement.removeAttribute('aria-invalid');
    },

    updateSubmitButtonState: function() {
        if (!this.elements.submitButton || !this.elements.mainTrackInput) return;

        let allValid = true;
        // Main track is required and must be valid
        const mainTrackFile = this.elements.mainTrackInput.files[0];
        if (!mainTrackFile) {
            allValid = false;
            // Optionally provide feedback if main track is empty when trying to enable button
            // but relying on `required` attribute and initial check is often enough.
        } else {
            // Re-validate, or trust prior validation state if input hasn't changed
            // For simplicity, let's assume prior validation through 'change' event is sufficient
            // or we can call validateFileInput again.
            // To be robust:
            if (this.elements.mainTrackInput.classList.contains('is-invalid')) allValid = false;
        }

        // Optional tracks, if present, must be valid (no 'is-invalid' class)
        if (this.elements.introTrackInput.files && this.elements.introTrackInput.files.length > 0 && this.elements.introTrackInput.classList.contains('is-invalid')) {
            allValid = false;
        }
        if (this.elements.outroTrackInput.files && this.elements.outroTrackInput.files.length > 0 && this.elements.outroTrackInput.classList.contains('is-invalid')) {
            allValid = false;
        }
        
        this.elements.submitButton.disabled = !allValid;
        if (allValid) {
            this.elements.submitButton.removeAttribute('aria-disabled');
        } else {
            this.elements.submitButton.setAttribute('aria-disabled', 'true');
        }
    },

    handleUploadAndProcess: async function(event) {
        event.preventDefault();
        if (this.elements.submitButton.disabled) {
             this.displayMessage(this.elements.uploadResponseDiv, 'Please correct the errors in the form before submitting.', 'error');
            return;
        }

        const form = event.target;
        const formData = new FormData();
        const mainTrack = this.elements.mainTrackInput.files[0];
        const introTrack = this.elements.introTrackInput.files[0];
        const outroTrack = this.elements.outroTrackInput.files[0];

        // This check should be redundant due to button state, but as a safeguard:
        if (!mainTrack || this.elements.mainTrackInput.classList.contains('is-invalid') ||
            (introTrack && this.elements.introTrackInput.classList.contains('is-invalid')) ||
            (outroTrack && this.elements.outroTrackInput.classList.contains('is-invalid'))) {
            this.displayMessage(this.elements.uploadResponseDiv, 'Please ensure all files are valid.', 'error');
            return;
        }

        formData.append('main_track', mainTrack, mainTrack.name);
        if (introTrack) formData.append('intro', introTrack, introTrack.name);
        if (outroTrack) formData.append('outro', outroTrack, outroTrack.name);

        this.clearMessage(this.elements.uploadResponseDiv);
        // The uploadResponseDiv has aria-live="polite"
        this.displayMessage(this.elements.uploadResponseDiv, 'Uploading audio files...', 'processing');
        this.showSpinner(this.elements.uploadResponseDiv, false); // Add spinner next to text
        
        this.elements.submitButton.disabled = true;
        this.elements.submitButton.setAttribute('aria-disabled', 'true');


        try {
            const uploadRes = await fetch(`${this.API_BASE_URL}/audio/upload`, {
                method: 'POST',
                body: formData,
            });
            const uploadData = await uploadRes.json();

            if (!uploadRes.ok) {
                throw new Error(uploadData.detail || `Upload failed: ${uploadRes.statusText}`);
            }
            
            // Update message, spinner still there
            this.displayMessage(this.elements.uploadResponseDiv, `Upload successful! Session ID: ${uploadData.upload_session_id}. Starting processing...`, 'processing');

            const processRes = await fetch(`${this.API_BASE_URL}/audio/process/${uploadData.upload_session_id}`, {
                method: 'POST',
            });
            const processData = await processRes.json();

            if (!processRes.ok) {
                throw new Error(processData.detail || `Processing failed: ${processRes.statusText}`);
            }
            
            this.hideSpinner(this.elements.uploadResponseDiv);
            this.displayMessage(this.elements.uploadResponseDiv, `Processing started! Job ID: ${processData.job_id}. Check status in 'View Jobs'.`, 'success');
            form.reset();
            [this.elements.mainTrackInput, this.elements.introTrackInput, this.elements.outroTrackInput].forEach(input => {
                if(input) this.clearValidationFeedback(input);
            });

        } catch (error) {
            console.error('Error during upload/process:', error);
            this.hideSpinner(this.elements.uploadResponseDiv);
            this.displayMessage(this.elements.uploadResponseDiv, `Error: ${error.message}`, 'error');
        } finally {
            // Re-enable submit button regardless of outcome, if form is in a submittable state
            this.updateSubmitButtonState(); 
        }
    },

    fetchJobs: async function() {
        if (!this.elements.jobsList) return;
        // Announce loading state for screen readers via an sr-only div or by changing button text
        const jobsListStatus = document.getElementById('jobsListStatus');
        if (jobsListStatus) jobsListStatus.textContent = 'Loading jobs...';
        
        this.showSpinner(this.elements.jobsList, true); // true to clear previous items before loading

        try {
            const jobIdToFetch = this.elements.jobIdInput ? this.elements.jobIdInput.value.trim() : '';
            let endpoint = `${this.API_BASE_URL}/jobs`;
            if (jobIdToFetch) {
                endpoint = `${endpoint}/${jobIdToFetch}`;
            }
            const response = await fetch(endpoint);
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || response.statusText);

            const jobs = Array.isArray(data) ? data : [data];

            this.hideSpinner(this.elements.jobsList);
            if (!jobs || jobs.length === 0) {
                this.elements.jobsList.innerHTML = '<li>No jobs found.</li>';
                if (jobsListStatus) jobsListStatus.textContent = 'No jobs found.';
                return;
            }

            this.elements.jobsList.innerHTML = ''; // Clear spinner
            jobs.forEach(job => {
                const li = document.createElement('li');
                li.setAttribute('role', 'listitem'); // Explicit role, though often inferred
                li.setAttribute('aria-labelledby', `job-id-${job.id}`); // For more complex items
                
                let tooltipText = `Status: ${job.status}. `;
                if (job.status === 'FAILED' && job.error_message) tooltipText += `Error: ${job.error_message}`;
                else if (job.status === 'COMPLETED') tooltipText += 'Ready for download.';
                else if (job.status === 'PROCESSING') tooltipText += 'Currently processing.';

                // Using textContent for security and spans for structure
                const idSpan = document.createElement('span');
                idSpan.id = `job-id-${job.id}`;
                idSpan.className = 'job-field job-id';
                idSpan.innerHTML = `<strong>ID:</strong> ${job.id}`;

                const statusSpan = document.createElement('span');
                statusSpan.className = 'job-field job-status';
                statusSpan.innerHTML = `<strong>Status:</strong> ${job.status} <span class="tooltip-trigger" data-tooltip="${tooltipText}" aria-label="Job status details"><span aria-hidden="true">&#❓</span></span>`;
                
                const typeSpan = document.createElement('span');
                typeSpan.className = 'job-field job-type';
                typeSpan.innerHTML = `<strong>Type:</strong> ${job.type}`;

                const createdSpan = document.createElement('span');
                createdSpan.className = 'job-field job-created';
                createdSpan.innerHTML = `<strong>Created:</strong> ${new Date(job.created_at).toLocaleString()}`;
                
                li.appendChild(idSpan);
                li.appendChild(statusSpan);
                li.appendChild(typeSpan);
                li.appendChild(createdSpan);

                if (job.status === 'COMPLETED' && job.output_file_path) {
                    const outputSpan = document.createElement('span');
                    outputSpan.className = 'job-field job-output';
                    const downloadLink = document.createElement('a');
                    downloadLink.href = `${this.API_BASE_URL}/audio/download/${job.id}`;
                    downloadLink.target = '_blank';
                    downloadLink.textContent = `Download ${job.output_file_path}`;
                    downloadLink.setAttribute('aria-label', `Download processed file for job ${job.id}`);
                    outputSpan.innerHTML = `<strong>Output:</strong> `;
                    outputSpan.appendChild(downloadLink);
                    li.appendChild(outputSpan);
                } else if (job.status === 'FAILED') {
                    const errorSpan = document.createElement('span');
                    errorSpan.className = 'job-field job-error';
                    errorSpan.innerHTML = `<strong>Error:</strong> ${job.error_message || 'Unknown error'}`;
                    li.appendChild(errorSpan);
                } else {
                     const outputSpan = document.createElement('span');
                     outputSpan.className = 'job-field job-output';
                     outputSpan.innerHTML = `<strong>Output:</strong> N/A`;
                     li.appendChild(outputSpan);
                }
                this.elements.jobsList.appendChild(li);
            });
            if (jobsListStatus) jobsListStatus.textContent = `Job list updated. ${jobs.length} items shown.`;

        } catch (error) {
            console.error('Error fetching jobs:', error);
            this.hideSpinner(this.elements.jobsList);
            this.elements.jobsList.innerHTML = `<li>Error fetching jobs: ${error.message}</li>`;
            if (jobsListStatus) jobsListStatus.textContent = `Error fetching jobs.`;
        }
    },
    // Fetch media library items from backend
    fetchLibrary: async function() {
        if (!this.elements.libraryList) return;
        const libraryListStatus = document.getElementById('libraryListStatus');
        if (libraryListStatus) libraryListStatus.textContent = 'Loading library items...';
        this.showSpinner(this.elements.libraryList, true);
        try {
            const response = await fetch(`${this.API_BASE_URL}/library`);
            const items = await response.json();
            if (!response.ok) throw new Error(items.detail || response.statusText);
            this.hideSpinner(this.elements.libraryList);
            if (!items || items.length === 0) {
                this.elements.libraryList.innerHTML = '<li>No media found in the library.</li>';
                if (libraryListStatus) libraryListStatus.textContent = 'No media found in the library.';
                return;
            }
            this.elements.libraryList.innerHTML = '';
            items.forEach(item => {
                const li = document.createElement('li');
                li.setAttribute('role', 'listitem');
                const idSpan = document.createElement('span');
                idSpan.className = 'lib-field lib-id';
                idSpan.innerHTML = `<strong>ID:</strong> ${item.job_id}`;
                const typeSpan = document.createElement('span');
                typeSpan.className = 'lib-field lib-type';
                typeSpan.innerHTML = `<strong>Type:</strong> ${item.job_type}`;
                const pathSpan = document.createElement('span');
                pathSpan.className = 'lib-field lib-path';
                pathSpan.innerHTML = `<strong>Path:</strong> ${item.output_file_path}`;
                const actionsSpan = document.createElement('span');
                actionsSpan.className = 'lib-field lib-actions';
                actionsSpan.innerHTML = `<strong>Actions:</strong> `;
                const downloadLink = document.createElement('a');
                downloadLink.href = item.download_url;
                downloadLink.target = '_blank';
                downloadLink.textContent = 'Download';
                actionsSpan.appendChild(downloadLink);
                li.appendChild(idSpan);
                li.appendChild(typeSpan);
                li.appendChild(pathSpan);
                li.appendChild(actionsSpan);
                this.elements.libraryList.appendChild(li);
            });
            if (libraryListStatus) libraryListStatus.textContent = `Library list updated. ${items.length} items shown.`;
        } catch (error) {
            console.error('Error fetching library:', error);
            this.hideSpinner(this.elements.libraryList);
            this.elements.libraryList.innerHTML = `<li>Error fetching library: ${error.message}</li>`;
            if (libraryListStatus) libraryListStatus.textContent = 'Error fetching library.';
        }
    },

    fetchLibraryForViz: async function() {
        if (!this.elements.vizFileSelect) return;
        this.elements.vizFileSelect.innerHTML = '<option value="">Loading files...</option>';
        try {
            const response = await fetch(`${this.API_BASE_URL}/library`);
            const items = await response.json();
            if (!response.ok) throw new Error(items.detail || response.statusText);
            this.elements.vizFileSelect.innerHTML = '<option value="">-- Select a file --</option>';
            items.forEach(item => {
                const option = document.createElement('option');
                option.value = item.job_id;
                option.textContent = `${item.job_type} - ${item.output_file_path}`;
                this.elements.vizFileSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error fetching library for visualization:', error);
            this.elements.vizFileSelect.innerHTML = '<option value="">Error loading items</option>';
        }
    },
    handleVisualizationProcess: async function() {
        if (!this.elements.vizResponseDiv) return;
        const jobId = this.elements.vizFileSelect ? this.elements.vizFileSelect.value : null;
        const vizWaveform = document.getElementById('vizWaveform')?.checked;
        this.clearMessage(this.elements.vizResponseDiv);
        if (!jobId) {
            this.displayMessage(this.elements.vizResponseDiv, 'Please select a file to visualize.', 'error');
            return;
        }
        if (!vizWaveform) {
            this.displayMessage(this.elements.vizResponseDiv, 'Please select at least one visualization type.', 'error');
            return;
        }
        this.displayMessage(this.elements.vizResponseDiv, 'Starting visualization...', 'processing');
        try {
            const res = await fetch(`${this.API_BASE_URL}/video/process/${jobId}`, { method: 'POST' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || res.statusText);
            this.displayMessage(this.elements.vizResponseDiv, `Visualization started! Job ID: ${data.job_id}.`, 'success');
        } catch (error) {
            console.error('Error starting visualization:', error);
            this.displayMessage(this.elements.vizResponseDiv, `Error: ${error.message}`, 'error');
        }
    },

    // Tooltip Handling
    handleTooltipMouseOver: function(event) {
        const target = event.target.closest('.tooltip-trigger');
        if (target) {
            const tooltipText = target.dataset.tooltip;
            if (tooltipText) {
                this.showTooltip(target, tooltipText);
            }
        }
    },

    showTooltip: function(triggerElement, text) {
        this.hideAllTooltips(); // Hide any existing tooltips

        const tooltipId = `tooltip-${Date.now()}`;
        const tooltip = document.createElement('div');
        tooltip.id = tooltipId;
        tooltip.className = 'tooltip-active';
        tooltip.textContent = text;
        tooltip.setAttribute('role', 'tooltip'); // ARIA role for tooltip
        document.body.appendChild(tooltip);

        triggerElement.setAttribute('aria-describedby', tooltipId); // Associate tooltip with trigger

        const triggerRect = triggerElement.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();

        let top = triggerRect.bottom + window.scrollY + 5; // Below the trigger
        let left = triggerRect.left + window.scrollX + (triggerRect.width / 2) - (tooltipRect.width / 2); // Centered

        // Adjust if tooltip goes off screen
        if (left < 0) left = 5;
        if (left + tooltipRect.width > window.innerWidth) left = window.innerWidth - tooltipRect.width - 5;
        if (top + tooltipRect.height > window.innerHeight && (triggerRect.top - tooltipRect.height - 5) > 0) {
            // If no space below and space above, position above
            top = triggerRect.top + window.scrollY - tooltipRect.height - 5;
        } else if (top + tooltipRect.height > window.innerHeight) {
            // Default to below if no space above either (rare for small tooltips)
            // Or adjust to fit viewport if it's too tall
            top = window.innerHeight - tooltipRect.height - 5 - window.scrollY;
        }
        
        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
    },

    hideAllTooltips: function() {
        document.querySelectorAll('.tooltip-active').forEach(tooltip => {
            const trigger = document.querySelector(`[aria-describedby="${tooltip.id}"]`);
            if (trigger) {
                trigger.removeAttribute('aria-describedby');
            }
            tooltip.remove();
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// Expose to global scope if HTML onclick attributes are still used for some parts,
// or if direct console access is needed for debugging.
// Otherwise, with data-view attributes and proper event listeners, this might not be strictly necessary.
window.App = App;
