// Twin-Report KB Frontend - Upload JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeUploadPage();
});

function initializeUploadPage() {
    setupDropZone();
    setupFileInput();
    setupUploadForm();
    setupAlternativeUploads();
}

// Drop zone functionality
function setupDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    if (!dropZone || !fileInput) return;

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', handleDrop, false);

    // Handle click to browse
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        dropZone.classList.add('drag-over');
    }

    function unhighlight() {
        dropZone.classList.remove('drag-over');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    }
}

// File input functionality
function setupFileInput() {
    const fileInput = document.getElementById('fileInput');
    
    if (!fileInput) return;

    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });
}

// Handle file selection
function handleFileSelection(file) {
    const maxSize = 100 * 1024 * 1024; // 100MB
    const allowedTypes = ['.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.html', '.md'];
    
    // Validate file size
    if (file.size > maxSize) {
        Utils.showToast('File is too large. Maximum size is 100MB.', 'error');
        return;
    }

    // Validate file type
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedTypes.includes(fileExt)) {
        Utils.showToast('File type not supported. Please use PDF, DOCX, XLSX, PPTX, TXT, HTML, or MD files.', 'error');
        return;
    }

    // Update UI
    displayFileInfo(file);
    enableSubmitButton();
}

// Display file information
function displayFileInfo(file) {
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');

    if (fileInfo && fileName && fileSize) {
        fileName.textContent = file.name;
        fileSize.textContent = Utils.formatFileSize(file.size);
        fileInfo.classList.remove('d-none');
    }
}

// Clear file selection
function clearFile() {
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    const submitBtn = document.getElementById('submitBtn');

    if (fileInput) fileInput.value = '';
    if (fileInfo) fileInfo.classList.add('d-none');
    if (submitBtn) submitBtn.disabled = true;
}

// Enable submit button
function enableSubmitButton() {
    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) {
        submitBtn.disabled = false;
    }
}

// Setup main upload form
function setupUploadForm() {
    const uploadForm = document.getElementById('uploadForm');
    
    if (!uploadForm) return;

    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const fileInput = document.getElementById('fileInput');
        const analysisDepth = document.getElementById('analysisDepth');
        const categories = document.getElementById('categories');

        if (!fileInput.files.length) {
            Utils.showToast('Please select a file to upload.', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('analysis_depth', analysisDepth.value);
        
        if (categories.value.trim()) {
            formData.append('categories', categories.value.trim());
        }

        try {
            // Show progress modal
            showProgressModal();

            // Upload file
            const response = await API.uploadFile(formData);
            
            if (response.success) {
                currentTaskId = response.task_id;
                
                // Store task info
                processingTasks.set(currentTaskId, {
                    task_id: currentTaskId,
                    filename: fileInput.files[0].name,
                    status: 'pending',
                    progress: 0
                });

                Utils.showToast('File uploaded successfully! Processing started.', 'success');
                
                // Start polling for progress
                ProgressTracker.startPolling(currentTaskId);
                
                // Reset form
                uploadForm.reset();
                clearFile();
                
            } else {
                throw new Error(response.error || 'Upload failed');
            }

        } catch (error) {
            console.error('Upload error:', error);
            Utils.showToast(`Upload failed: ${error.message}`, 'error');
            hideProgressModal();
        }
    });
}

// Setup alternative upload methods
function setupAlternativeUploads() {
    setupUrlUpload();
    setupGoogleDocUpload();
}

// URL upload functionality
function setupUrlUpload() {
    const urlForm = document.getElementById('urlUploadForm');
    
    if (!urlForm) return;

    urlForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const urlInput = document.getElementById('urlInput');
        const url = urlInput.value.trim();

        if (!url) {
            Utils.showToast('Please enter a URL.', 'warning');
            return;
        }

        if (!Utils.isValidUrl(url)) {
            Utils.showToast('Please enter a valid URL.', 'error');
            return;
        }

        try {
            showProgressModal();

            const response = await API.uploadUrl({
                url: url,
                analysis_depth: 'comprehensive'
            });

            if (response.success) {
                currentTaskId = response.task_id;
                
                // Store task info
                processingTasks.set(currentTaskId, {
                    task_id: currentTaskId,
                    url: url,
                    status: 'pending',
                    progress: 0
                });

                Utils.showToast('URL submitted successfully! Processing started.', 'success');
                
                // Start polling for progress
                ProgressTracker.startPolling(currentTaskId);
                
                // Reset form
                urlForm.reset();
                
            } else {
                throw new Error(response.error || 'URL processing failed');
            }

        } catch (error) {
            console.error('URL upload error:', error);
            Utils.showToast(`URL processing failed: ${error.message}`, 'error');
            hideProgressModal();
        }
    });
}

// Google Doc upload functionality
function setupGoogleDocUpload() {
    const googleDocForm = document.getElementById('googleDocUploadForm');
    
    if (!googleDocForm) return;

    googleDocForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const docInput = document.getElementById('googleDocInput');
        const docId = docInput.value.trim();

        if (!docId) {
            Utils.showToast('Please enter a Google Doc URL or ID.', 'warning');
            return;
        }

        try {
            showProgressModal();

            const response = await API.uploadGoogleDoc({
                doc_id: docId,
                analysis_depth: 'comprehensive'
            });

            if (response.success) {
                currentTaskId = response.task_id;
                
                // Store task info
                processingTasks.set(currentTaskId, {
                    task_id: currentTaskId,
                    google_doc_id: docId,
                    status: 'pending',
                    progress: 0
                });

                Utils.showToast('Google Doc submitted successfully! Processing started.', 'success');
                
                // Start polling for progress
                ProgressTracker.startPolling(currentTaskId);
                
                // Reset form
                googleDocForm.reset();
                
            } else {
                throw new Error(response.error || 'Google Doc processing failed');
            }

        } catch (error) {
            console.error('Google Doc upload error:', error);
            Utils.showToast(`Google Doc processing failed: ${error.message}`, 'error');
            hideProgressModal();
        }
    });
}

// Progress modal functions
function showProgressModal() {
    const progressModal = document.getElementById('progressModal');
    if (progressModal) {
        const modal = new bootstrap.Modal(progressModal);
        modal.show();
        
        // Reset progress display
        ProgressTracker.updateProgressBar(0);
        ProgressTracker.updateCurrentStep('pending');
        ProgressTracker.updateStepIndicators('pending');
        
        // Hide view results button
        const viewResultsBtn = document.getElementById('viewResults');
        if (viewResultsBtn) {
            viewResultsBtn.style.display = 'none';
        }
    }
}

function hideProgressModal() {
    const progressModal = document.getElementById('progressModal');
    if (progressModal) {
        const modal = bootstrap.Modal.getInstance(progressModal);
        if (modal) {
            modal.hide();
        }
    }
}

// Cancel processing
document.addEventListener('DOMContentLoaded', function() {
    const cancelBtn = document.getElementById('cancelProcessing');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            hideProgressModal();
            Utils.showToast('Processing cancelled', 'info');
        });
    }
});

// Export functions to global scope
window.clearFile = clearFile;
window.showProgressModal = showProgressModal;
window.hideProgressModal = hideProgressModal; 