/**
 * Modal Manager - Traffic Count
 * Handles modal functionality
 */

class ModalManager {
    constructor() {
        this.modals = new Map();
        this.init();
    }

    init() {
        // Find all modals and register them
        const modalElements = document.querySelectorAll('[id$="Modal"]');
        modalElements.forEach(modal => {
            this.registerModal(modal.id);
        });
        
        // Global escape key handler
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeTopModal();
            }
        });
    }

    registerModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        this.modals.set(modalId, {
            element: modal,
            isOpen: false
        });

        // Set up backdrop click to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.close(modalId);
            }
        });

        // Set up close buttons
        const closeButtons = modal.querySelectorAll('[data-modal-close]');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.close(modalId));
        });
    }

    open(modalId) {
        const modalData = this.modals.get(modalId);
        if (!modalData) {
            console.error(`Modal ${modalId} not found`);
            return;
        }

        const modal = modalData.element;
        modal.classList.remove('hidden');
        modalData.isOpen = true;
        
        // Focus management
        const firstFocusable = modal.querySelector('input, select, textarea, button');
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 100);
        }

        // Prevent body scroll
        document.body.style.overflow = 'hidden';
        
        // Add fade-in animation
        modal.style.opacity = '0';
        setTimeout(() => {
            modal.style.transition = 'opacity 0.3s ease';
            modal.style.opacity = '1';
        }, 10);
    }

    close(modalId) {
        const modalData = this.modals.get(modalId);
        if (!modalData) return;

        const modal = modalData.element;
        
        // Fade out animation
        modal.style.opacity = '0';
        setTimeout(() => {
            modal.classList.add('hidden');
            modal.style.opacity = '';
            modal.style.transition = '';
            modalData.isOpen = false;
            
            // Restore body scroll if no other modals are open
            const hasOpenModals = Array.from(this.modals.values()).some(m => m.isOpen);
            if (!hasOpenModals) {
                document.body.style.overflow = '';
            }
        }, 300);

        // Clear form if exists
        const form = modal.querySelector('form');
        if (form) {
            form.reset();
            // Clear validation states
            const inputs = form.querySelectorAll('.form-input');
            inputs.forEach(input => {
                input.classList.remove('error', 'success');
            });
        }
    }

    closeTopModal() {
        // Close the most recently opened modal
        const openModals = Array.from(this.modals.entries())
            .filter(([_, data]) => data.isOpen);
        
        if (openModals.length > 0) {
            const [modalId] = openModals[openModals.length - 1];
            this.close(modalId);
        }
    }

    isOpen(modalId) {
        const modalData = this.modals.get(modalId);
        return modalData ? modalData.isOpen : false;
    }
}

// Global modal manager instance
window.modalManager = new ModalManager();

// Utility functions for backward compatibility
window.showModal = function(modalId) {
    window.modalManager.open(modalId);
};

window.hideModal = function(modalId) {
    window.modalManager.close(modalId);
};