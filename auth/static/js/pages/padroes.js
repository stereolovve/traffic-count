/**
 * Padrões Page JavaScript - Traffic Count
 * Handles pattern list functionality including drag and drop reordering
 */

class PadroesManager {
    constructor() {
        this.selectedType = this.getSelectedType();
        this.dragDropManager = null;
        this.init();
    }

    init() {
        // Only initialize drag and drop if we have patterns and a selected type
        if (this.selectedType && document.getElementById('pattern-container')) {
            this.initDragDrop();
        }
    }

    getSelectedType() {
        // Get selected type from template variable or URL
        const patternContainer = document.getElementById('pattern-container');
        if (patternContainer) {
            // Extract from page context - this would be set by the template
            return window.selectedPatternType || null;
        }
        return null;
    }

    initDragDrop() {
        this.dragDropManager = new DragDropManager('pattern-container', {
            itemSelector: '.pattern-item',
            handleSelector: '.drag-handle',
            dropIndicatorClass: 'drop-indicator',
            draggingClass: 'dragging',
            onReorder: (orderData) => this.saveNewOrder(orderData)
        });
    }

    async saveNewOrder(orderData) {
        try {
            const response = await window.TrafficCount.apiRequest('/api/padroes/reorder/', {
                method: 'POST',
                body: JSON.stringify({
                    patterns: orderData,
                    pattern_type: this.selectedType
                })
            });

            if (response.status === 'success') {
                this.showFeedback('Ordem salva com sucesso!', 'success');
            } else {
                throw new Error(response.message || 'Erro ao salvar ordem');
            }
        } catch (error) {
            console.error('Erro ao salvar ordem:', error);
            this.showFeedback('Erro ao salvar ordem: ' + error.message, 'error');
        }
    }

    showFeedback(message, type) {
        // Remove any existing feedback
        const existingFeedback = document.querySelector('.feedback-message');
        if (existingFeedback) {
            existingFeedback.remove();
        }

        // Create new feedback element
        const feedback = document.createElement('div');
        feedback.className = `fixed bottom-4 right-4 px-6 py-3 rounded-xl shadow-xl feedback-message transition-all duration-300 ${
            type === 'success' ? 'alert alert-success' : 'alert alert-error'
        }`;
        feedback.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} mr-2"></i>
            ${message}
        `;
        document.body.appendChild(feedback);
        
        // Remove after delay
        setTimeout(() => {
            feedback.style.transform = 'translateX(100%)';
            setTimeout(() => feedback.remove(), 300);
        }, type === 'success' ? 2000 : 3000);
    }

    destroy() {
        if (this.dragDropManager) {
            this.dragDropManager.destroy();
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Set selected pattern type from template
    const selectedTypeElement = document.querySelector('[data-selected-type]');
    if (selectedTypeElement) {
        window.selectedPatternType = selectedTypeElement.dataset.selectedType;
    }
    
    // Initialize patterns manager
    window.padroesManager = new PadroesManager();
    
    console.log('Padrões page initialized');
});