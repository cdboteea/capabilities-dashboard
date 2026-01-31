// Twin-Report KB Frontend - Main JavaScript

// Global variables
let currentTaskId = null;
let processingTasks = new Map();

// Utility functions
const Utils = {
    // Format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // Format time duration
    formatDuration(seconds) {
        if (seconds < 60) return `${seconds.toFixed(1)}s`;
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
    },

    // Show toast notification
    showToast(message, type = 'info') {
        const toast = document.getElementById('liveToast');
        const toastBody = toast.querySelector('.toast-body');
        const toastHeader = toast.querySelector('.toast-header');
        
        // Update content
        toastBody.textContent = message;
        
        // Update icon based on type
        const icon = toastHeader.querySelector('i');
        icon.className = `fas me-2 ${this.getIconForType(type)} text-${type}`;
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    },

    // Get icon for toast type
    getIconForType(type) {
        const icons = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'warning': 'fa-exclamation-triangle',
            'info': 'fa-info-circle'
        };
        return icons[type] || 'fa-info-circle';
    },

    // Validate URL
    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    },

    // Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Format timestamp for display
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    }
};

// API functions
const API = {
    // Base URL for API calls
    baseUrl: '',

    // Generic API call
    async call(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const finalOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, finalOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    },

    // Upload file
    async uploadFile(formData) {
        return await this.call('/upload', {
            method: 'POST',
            body: formData,
            headers: {} // Remove Content-Type to let browser set it with boundary
        });
    },

    // Upload URL
    async uploadUrl(data) {
        return await this.call('/upload/url', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // Upload Google Doc
    async uploadGoogleDoc(data) {
        return await this.call('/upload/google-doc', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // Get task status
    async getTaskStatus(taskId) {
        return await this.call(`/analysis/${taskId}`);
    },

    // Get health status
    async getHealthStatus() {
        return await this.call('/health');
    }
};

// Progress tracking
const ProgressTracker = {
    // Processing steps
    steps: ['pending', 'parsing', 'categorizing', 'quality_check', 'analyzing', 'completed'],

    // Update progress display
    updateProgress(taskId, status) {
        const task = processingTasks.get(taskId);
        if (!task) return;

        // Update task data
        Object.assign(task, status);

        // Update progress bar
        this.updateProgressBar(status.progress || 0);

        // Update step indicators
        this.updateStepIndicators(status.current_step || 'pending');

        // Update current step text
        this.updateCurrentStep(status.current_step || 'pending');

        // Handle completion
        if (status.status === 'completed') {
            this.handleCompletion(taskId);
        } else if (status.status === 'failed') {
            this.handleFailure(taskId, status.error);
        }
    },

    // Update progress bar
    updateProgressBar(progress) {
        const progressBar = document.getElementById('progressBar');
        const progressPercent = document.getElementById('progressPercent');
        
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
        }
        
        if (progressPercent) {
            progressPercent.textContent = `${Math.round(progress)}%`;
        }
    },

    // Update step indicators
    updateStepIndicators(currentStep) {
        const stepItems = document.querySelectorAll('.step-item');
        const currentIndex = this.steps.indexOf(currentStep);

        stepItems.forEach((item, index) => {
            const step = item.getAttribute('data-step');
            const stepIndex = this.steps.indexOf(step);

            // Remove all classes
            item.classList.remove('active', 'completed', 'failed');

            if (stepIndex < currentIndex) {
                item.classList.add('completed');
            } else if (stepIndex === currentIndex) {
                item.classList.add('active');
            }
        });
    },

    // Update current step text
    updateCurrentStep(step) {
        const currentStepElement = document.getElementById('currentStep');
        if (currentStepElement) {
            const stepNames = {
                'pending': 'Initializing...',
                'parsing': 'Parsing document content...',
                'categorizing': 'Categorizing content...',
                'quality_check': 'Assessing quality...',
                'analyzing': 'Analyzing gaps...',
                'completed': 'Analysis complete!',
                'failed': 'Processing failed'
            };
            currentStepElement.textContent = stepNames[step] || 'Processing...';
        }
    },

    // Handle completion
    handleCompletion(taskId) {
        Utils.showToast('Document analysis completed successfully!', 'success');
        
        // Show view results button
        const viewResultsBtn = document.getElementById('viewResults');
        if (viewResultsBtn) {
            viewResultsBtn.style.display = 'block';
            viewResultsBtn.onclick = () => {
                window.location.href = `/results/${taskId}`;
            };
        }

        // Update processing queue
        this.updateProcessingQueue();
    },

    // Handle failure
    handleFailure(taskId, error) {
        Utils.showToast(`Processing failed: ${error}`, 'error');
        
        // Mark all steps as failed
        const stepItems = document.querySelectorAll('.step-item');
        stepItems.forEach(item => {
            item.classList.remove('active', 'completed');
            item.classList.add('failed');
        });

        // Update processing queue
        this.updateProcessingQueue();
    },

    // Start polling for task status
    startPolling(taskId) {
        const pollInterval = setInterval(async () => {
            try {
                const status = await API.getTaskStatus(taskId);
                this.updateProgress(taskId, status);

                // Stop polling if completed or failed
                if (status.status === 'completed' || status.status === 'failed') {
                    clearInterval(pollInterval);
                }
            } catch (error) {
                console.error('Failed to poll task status:', error);
                clearInterval(pollInterval);
                Utils.showToast('Failed to get processing status', 'error');
            }
        }, 2000); // Poll every 2 seconds

        return pollInterval;
    },

    // Update processing queue display
    updateProcessingQueue() {
        const queueElement = document.getElementById('processingQueue');
        if (!queueElement) return;

        const activeTasks = Array.from(processingTasks.values())
            .filter(task => !['completed', 'failed'].includes(task.status));

        if (activeTasks.length === 0) {
            queueElement.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <p>No documents in queue</p>
                </div>
            `;
        } else {
            queueElement.innerHTML = activeTasks.map(task => `
                <div class="queue-item processing">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${task.filename || task.url || 'Document'}</strong>
                            <br>
                            <small class="text-muted">${task.current_step || 'pending'}</small>
                        </div>
                        <div class="text-end">
                            <div class="progress" style="width: 60px; height: 6px;">
                                <div class="progress-bar" style="width: ${task.progress || 0}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
        }
    }
};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Twin-Report KB Frontend initialized');

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-refresh health status every 30 seconds
    setInterval(async () => {
        try {
            const health = await API.getHealthStatus();
            updateHealthIndicators(health);
        } catch (error) {
            console.error('Failed to refresh health status:', error);
        }
    }, 30000);

    // Update processing queue every 5 seconds
    setInterval(() => {
        ProgressTracker.updateProcessingQueue();
    }, 5000);
});

// Update health indicators
function updateHealthIndicators(health) {
    // Update navbar badge if processing queue exists
    const queueBadge = document.querySelector('.navbar .badge');
    if (queueBadge && health.processing_queue !== undefined) {
        if (health.processing_queue > 0) {
            queueBadge.textContent = `${health.processing_queue} processing`;
            queueBadge.style.display = 'inline';
        } else {
            queueBadge.style.display = 'none';
        }
    }
}

// Export to global scope
window.Utils = Utils;
window.API = API;
window.ProgressTracker = ProgressTracker; 