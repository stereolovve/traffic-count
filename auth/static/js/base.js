/**
 * Base JavaScript - Traffic Count
 * Core functionality and utilities
 */

// Global utilities
window.TrafficCount = {
    // CSRF Token utility
    getCsrfToken: function() {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith('csrftoken=')) {
                return decodeURIComponent(cookie.substring(10));
            }
        }
        return null;
    },

    // Toast notifications
    showToast: function(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-xl shadow-xl transition-all duration-300 z-50 ${
            type === 'success' ? 'alert alert-success' : 'alert alert-error'
        }`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} mr-2"></i>
            ${message}
        `;
        document.body.appendChild(toast);
        
        // Auto remove
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, type === 'success' ? 2000 : 3000);
    },

    // API request utility
    apiRequest: async function(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            }
        };

        const finalOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, finalOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Check if response has content to parse as JSON
            const contentType = response.headers.get('content-type');
            const contentLength = response.headers.get('content-length');
            
            // If it's a 204 No Content or empty response, return null
            if (response.status === 204 || contentLength === '0') {
                return null;
            }
            
            // If response has JSON content, parse it
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            // For other content types or if no content-type header, try to parse as JSON
            // but handle the case where it might be empty
            const text = await response.text();
            if (!text.trim()) {
                return null;
            }
            
            try {
                return JSON.parse(text);
            } catch (jsonError) {
                // If JSON parsing fails, return the raw text
                return text;
            }
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
};

// Sidebar functionality
class SidebarManager {
    constructor() {
        this.sidebar = document.getElementById('sidebar');
        this.mainContent = document.getElementById('main-content');
        this.toggle = document.getElementById('sidebar-toggle');
        this.overlay = document.getElementById('mobile-overlay');
        
        this.init();
    }

    init() {
        if (!this.sidebar || !this.mainContent) return;

        // Load saved state
        const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        if (isCollapsed) {
            this.collapse();
        }

        // Bind events
        this.bindEvents();
        this.updateTooltips();
    }

    bindEvents() {
        // Toggle button
        if (this.toggle) {
            this.toggle.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    this.toggleMobile();
                } else {
                    this.toggleDesktop();
                }
            });
        }

        // Mobile overlay
        if (this.overlay) {
            this.overlay.addEventListener('click', () => this.toggleMobile());
        }

        // Window resize
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                this.sidebar.classList.remove('mobile-open');
                this.overlay.classList.add('hidden');
                document.body.style.overflow = '';
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + B to toggle sidebar
            if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                e.preventDefault();
                this.toggle?.click();
            }
            
            // Esc to close mobile sidebar
            if (e.key === 'Escape' && this.sidebar.classList.contains('mobile-open')) {
                this.toggleMobile();
            }
        });
    }

    toggleDesktop() {
        this.sidebar.classList.toggle('collapsed');
        this.mainContent.classList.toggle('expanded');
        
        // Save state
        const isCollapsed = this.sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
        
        // Update tooltips
        setTimeout(() => this.updateTooltips(), 300);
    }

    toggleMobile() {
        this.sidebar.classList.toggle('mobile-open');
        this.overlay.classList.toggle('hidden');
        
        // Prevent body scroll when mobile menu is open
        document.body.style.overflow = this.sidebar.classList.contains('mobile-open') ? 'hidden' : '';
    }

    collapse() {
        this.sidebar.classList.add('collapsed');
        this.mainContent.classList.add('expanded');
        this.updateTooltips();
    }

    expand() {
        this.sidebar.classList.remove('collapsed');
        this.mainContent.classList.remove('expanded');
        this.updateTooltips();
    }

    updateTooltips() {
        if (!this.sidebar) return;
        
        const sidebarItems = this.sidebar.querySelectorAll('.sidebar-item');
        const isCollapsed = this.sidebar.classList.contains('collapsed');
        
        sidebarItems.forEach(item => {
            if (isCollapsed) {
                const text = item.querySelector('.sidebar-item-text')?.textContent;
                if (text) {
                    item.classList.add('tooltip');
                    item.setAttribute('data-tooltip', text);
                }
            } else {
                item.classList.remove('tooltip');
                item.removeAttribute('data-tooltip');
            }
        });
    }
}

// Form enhancements
class FormEnhancer {
    constructor() {
        this.init();
    }

    init() {
        this.enhanceInputs();
        this.addLoadingStates();
    }

    enhanceInputs() {
        const formInputs = document.querySelectorAll('.form-input');
        formInputs.forEach(input => {
            const label = input.previousElementSibling;
            if (label && label.classList.contains('form-label')) {
                input.addEventListener('focus', () => {
                    label.style.transform = 'translateY(-8px) scale(0.9)';
                    label.style.color = 'var(--primary-color)';
                });
                
                input.addEventListener('blur', () => {
                    if (!input.value) {
                        label.style.transform = '';
                        label.style.color = '';
                    }
                });
            }
        });
    }

    addLoadingStates() {
        const buttons = document.querySelectorAll('.btn[type="submit"]');
        buttons.forEach(btn => {
            // Skip auth forms
            const form = btn.closest('form');
            if (form && (form.action.includes('/login/') || form.action.includes('/register/') || form.action.includes('/logout/'))) {
                return;
            }
            
            btn.addEventListener('click', function(e) {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Carregando...';
                this.disabled = true;
                this.classList.add('loading');
                
                // Re-enable after timeout if still on same page
                setTimeout(() => {
                    if (this.innerHTML.includes('Carregando...')) {
                        this.innerHTML = originalText;
                        this.disabled = false;
                        this.classList.remove('loading');
                    }
                }, 3000);
            });
        });
    }
}

// Alert manager
class AlertManager {
    constructor() {
        this.init();
    }

    init() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => this.enhanceAlert(alert));
    }

    enhanceAlert(alert) {
        // Auto-hide after 5 seconds
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100%)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
        
        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.className = 'absolute top-2 right-2 text-slate-400 hover:text-slate-300 transition-colors';
        closeBtn.style.cssText = 'position: absolute; top: 0.5rem; right: 0.5rem; background: none; border: none; cursor: pointer;';
        closeBtn.onclick = () => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100%)';
            setTimeout(() => alert.remove(), 300);
        };
        
        alert.style.position = 'relative';
        alert.appendChild(closeBtn);
    }
}

// Smooth scrolling for internal links
function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Fade-in animation for content
function initFadeInAnimation() {
    const content = document.querySelector('.fade-in');
    if (content) {
        content.style.opacity = '0';
        content.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            content.style.transition = 'all 0.5s ease-out';
            content.style.opacity = '1';
            content.style.transform = 'translateY(0)';
        }, 100);
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize managers
    new SidebarManager();
    new FormEnhancer();
    new AlertManager();
    
    // Initialize utilities
    initSmoothScrolling();
    initFadeInAnimation();
    
    console.log('Traffic Count base.js initialized');
});