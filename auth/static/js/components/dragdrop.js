/**
 * Drag and Drop Manager - Traffic Count
 * Handles sortable list functionality
 */

class DragDropManager {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            itemSelector: '.pattern-item',
            handleSelector: '.drag-handle',
            dropIndicatorClass: 'drop-indicator',
            draggingClass: 'dragging',
            onReorder: null,
            ...options
        };
        
        this.draggedItem = null;
        this.init();
    }

    init() {
        if (!this.container) return;
        
        this.setupItems();
    }

    setupItems() {
        const items = this.container.querySelectorAll(this.options.itemSelector);
        const indicators = this.container.querySelectorAll(`.${this.options.dropIndicatorClass}`);
        
        items.forEach(item => {
            const handle = item.querySelector(this.options.handleSelector);
            if (handle) {
                this.setupDragHandle(handle, item);
            }
        });
    }

    setupDragHandle(handle, item) {
        handle.addEventListener('mousedown', (e) => {
            e.preventDefault();
            this.startDrag(item, e);
        });
    }

    startDrag(item, e) {
        this.draggedItem = item;
        item.classList.add(this.options.draggingClass);
        
        const startY = e.clientY;
        const startTop = item.offsetTop;
        
        const onMouseMove = (e) => {
            const newY = e.clientY - startY;
            
            // Constrain movement to container
            const containerRect = this.container.getBoundingClientRect();
            let constrainedY = newY;
            
            if (e.clientY < containerRect.top) {
                constrainedY = containerRect.top - startY;
            } else if (e.clientY > containerRect.bottom) {
                constrainedY = containerRect.bottom - startY;
            }
            
            // Update visual position
            item.style.transform = `translateY(${constrainedY}px)`;
            
            // Update drop indicators
            this.updateDropIndicators(e.clientY);
        };
        
        const onMouseUp = () => {
            item.classList.remove(this.options.draggingClass);
            item.style.transform = '';
            
            // Hide all indicators
            const indicators = this.container.querySelectorAll(`.${this.options.dropIndicatorClass}`);
            indicators.forEach(indicator => {
                indicator.style.display = 'none';
            });
            
            // Reorder items
            this.reorderItems();
            
            // Callback
            if (this.options.onReorder) {
                this.options.onReorder(this.getNewOrder());
            }
            
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            
            this.draggedItem = null;
        };
        
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }

    updateDropIndicators(mouseY) {
        const indicators = this.container.querySelectorAll(`.${this.options.dropIndicatorClass}`);
        let closestIndicator = null;
        let closestDistance = Infinity;
        
        indicators.forEach(indicator => {
            const rect = indicator.getBoundingClientRect();
            const distance = Math.abs(rect.top - mouseY);
            
            if (distance < closestDistance) {
                closestDistance = distance;
                closestIndicator = indicator;
            }
            
            indicator.style.display = 'none';
        });
        
        if (closestIndicator) {
            closestIndicator.style.display = 'block';
        }
    }

    reorderItems() {
        const items = Array.from(this.container.querySelectorAll(this.options.itemSelector));
        
        // Sort items by vertical position
        items.sort((a, b) => {
            return a.getBoundingClientRect().top - b.getBoundingClientRect().top;
        });
        
        // Reorganize DOM
        items.forEach(item => {
            const indicator = item.nextElementSibling;
            this.container.appendChild(item);
            if (indicator && indicator.classList.contains(this.options.dropIndicatorClass)) {
                this.container.appendChild(indicator);
            }
        });
    }

    getNewOrder() {
        const items = this.container.querySelectorAll(this.options.itemSelector);
        return Array.from(items).map((item, index) => ({
            id: parseInt(item.dataset.id),
            order: (index + 1) * 10
        }));
    }

    destroy() {
        // Clean up event listeners and references
        this.container = null;
        this.draggedItem = null;
    }
}

// Export for use in other modules
window.DragDropManager = DragDropManager;