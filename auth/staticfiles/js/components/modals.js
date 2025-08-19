// Simple Modal System - Traffic Count
// Based on the clean pattern provided by the user

// Elements DOM state
let items = [];

// Modal open/close functions - defined globally
window.openModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('hidden');
  }
};

window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('hidden');
    const form = modal.querySelector('form');
    if (form) {
      form.reset();
    }
  }
};

// Initialize modal functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  // Bind close buttons
  const cancelButtons = [
    'cancelClienteBtn',
    'cancelEditClienteBtn', 
    'cancelCodigoBtn',
    'cancelEditCodigoBtn',
    'cancelPontoBtn',
    'cancelEditPontoBtn',
    'cancelBulkBtn'
  ];

  cancelButtons.forEach(btnId => {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.addEventListener('click', () => {
        // Simple mapping of cancel buttons to modals
        const modalMap = {
          'cancelClienteBtn': 'newClienteModal',
          'cancelEditClienteBtn': 'editClienteModal',
          'cancelCodigoBtn': 'newCodigoModal',
          'cancelEditCodigoBtn': 'editCodigoModal',
          'cancelPontoBtn': 'newPontoModal',
          'cancelEditPontoBtn': 'editPontoModal',
          'cancelBulkBtn': 'bulkCreatePontosModal'
        };
        
        const modalId = modalMap[btnId];
        if (modalId) {
          window.closeModal(modalId);
        }
      });
    }
  });

  // Close modal when clicking on backdrop
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('bg-black') && e.target.classList.contains('bg-opacity-50')) {
      const modalId = e.target.id;
      window.closeModal(modalId);
    }
  });

  // Close modal on ESC key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const openModals = document.querySelectorAll('[id$="Modal"]:not(.hidden)');
      openModals.forEach(modal => modal.classList.add('hidden'));
    }
  });

  // Bulk create pontos preview functionality
  const bulkModal = document.getElementById('bulkCreatePontosModal');
  if (bulkModal) {
    const quantityInput = bulkModal.querySelector('#quantity');
    const prefixInput = bulkModal.querySelector('#prefix');
    const suffixInput = bulkModal.querySelector('#suffix');
    const startNumberInput = bulkModal.querySelector('#startNumber');
    const digitsSelect = bulkModal.querySelector('#digits');
    const previewList = bulkModal.querySelector('#previewList');
    
    function updatePreview() {
      const quantity = parseInt(quantityInput.value) || 10;
      const prefix = prefixInput.value || '';
      const suffix = suffixInput.value || '';
      const startNumber = parseInt(startNumberInput.value) || 1;
      const digits = parseInt(digitsSelect.value) || 3;
      
      const previews = [];
      const maxPreview = Math.min(quantity, 5);
      
      for (let i = 0; i < maxPreview; i++) {
        const number = (startNumber + i).toString().padStart(digits, '0');
        const name = `${prefix}${number}${suffix}`;
        previews.push(name);
      }
      
      let previewText = previews.join(', ');
      if (quantity > 5) {
        previewText += '...';
      }
      
      if (previewList) {
        previewList.textContent = previewText;
      }
    }
    
    // Update preview on input change
    [quantityInput, prefixInput, suffixInput, startNumberInput, digitsSelect].forEach(input => {
      if (input) {
        input.addEventListener('input', updatePreview);
        input.addEventListener('change', updatePreview);
      }
    });
    
    // Initialize preview
    updatePreview();
  }
});

// Functions are already defined globally above