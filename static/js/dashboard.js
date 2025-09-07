document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Enable Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });
    
    // Handle sidebar collapse on mobile
    const sidebar = document.getElementById('sidebar');
    const sidebarToggler = document.querySelector('[data-bs-target="#sidebar"]');
    
    if (sidebar && sidebarToggler) {
        sidebarToggler.addEventListener('click', function() {
            sidebar.classList.toggle('collapse');
        });
    }
    
    // Auto-resize textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
        
        // Trigger initial resize
        textarea.dispatchEvent(new Event('input'));
    });
    
    // File upload preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const previewId = this.getAttribute('data-preview');
            if (!previewId) return;
            
            const preview = document.getElementById(previewId);
            if (!preview) return;
            
            const file = this.files[0];
            if (file) {
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        preview.innerHTML = `<img src="${e.target.result}" class="img-fluid rounded" alt="Preview">`;
                    };
                    reader.readAsDataURL(file);
                } else {
                    preview.innerHTML = `<div class="alert alert-info p-2">
                        <i class="fas fa-file me-2"></i>${file.name}
                    </div>`;
                }
            } else {
                preview.innerHTML = '';
            }
        });
    });
    
    // Due date validation
    const dueDateInputs = document.querySelectorAll('input[type="datetime-local"]');
    dueDateInputs.forEach(input => {
        input.addEventListener('change', function() {
            const selectedDate = new Date(this.value);
            const now = new Date();
            
            if (selectedDate < now) {
                this.setCustomValidity('Due date must be in the future');
            } else {
                this.setCustomValidity('');
            }
        });
    });
    
    // AJAX form submissions
    const ajaxForms = document.querySelectorAll('form[data-ajax="true"]');
    ajaxForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            
            // Show loading state
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
            submitBtn.disabled = true;
            
            const formData = new FormData(this);
            const url = this.getAttribute('action');
            const method = this.getAttribute('method') || 'POST';
            
            fetch(url, {
                method: method,
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success message
                    showAlert('success', data.message);
                    
                    // Reset form if needed
                    if (this.hasAttribute('data-reset')) {
                        this.reset();
                    }
                    
                    // Redirect if needed
                    if (data.redirect) {
                        setTimeout(() => {
                            window.location.href = data.redirect;
                        }, 1500);
                    }
                } else {
                    showAlert('danger', data.message || 'An error occurred');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('danger', 'An error occurred. Please try again.');
            })
            .finally(() => {
                // Restore button state
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            });
        });
    });
    
    // Helper function to show alerts
    function showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Prepend to the main content area
        const mainContent = document.querySelector('main');
        if (mainContent) {
            mainContent.insertBefore(alertDiv, mainContent.firstChild);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alertDiv);
                bsAlert.close();
            }, 5000);
        }
    }
});