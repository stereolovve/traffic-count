/**
 * Trabalhos Page JavaScript - Traffic Count
 * Handles client/code/point management functionality
 */

class TrabalhosManager {
    constructor() {
        this.clienteId = this.getClienteId();
        this.codigoId = this.getCodigoId();
        this.init();
    }

    init() {
        this.bindModalTriggers();
        this.bindEditButtons();
        this.bindDeleteButtons();
        this.bindBulkOperations();
        this.bindFormSubmissions();
    }

    getClienteId() {
        const element = document.getElementById('cliente_id');
        return element ? element.value : null;
    }

    getCodigoId() {
        const element = document.getElementById('codigo_id');
        return element ? element.value : null;
    }

    bindModalTriggers() {
        // Cliente modal triggers
        const newClienteBtns = document.querySelectorAll('#newClienteBtn, #newClienteBtn2');
        newClienteBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                window.modalManager.open('newClienteModal');
            });
        });

        // Codigo modal triggers  
        const newCodigoBtns = document.querySelectorAll('#newCodigoBtn, #newCodigoBtn2');
        newCodigoBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                window.modalManager.open('newCodigoModal');
            });
        });

        // Ponto modal triggers
        const newPontoBtns = document.querySelectorAll('#newPontoBtn, #newPontoBtn2');
        newPontoBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                window.modalManager.open('newPontoModal');
            });
        });

        // Bulk create pontos modal trigger
        const bulkCreateBtn = document.getElementById('bulkCreatePontosBtn');
        if (bulkCreateBtn) {
            bulkCreateBtn.addEventListener('click', () => {
                window.modalManager.open('bulkCreatePontosModal');
            });
        }
    }

    bindEditButtons() {
        // Edit cliente buttons
        const editClienteBtns = document.querySelectorAll('.edit-cliente-btn');
        editClienteBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.dataset.id;
                const nome = btn.dataset.nome;
                this.openEditClienteModal(id, nome);
            });
        });

        // Edit codigo buttons
        const editCodigoBtns = document.querySelectorAll('.edit-codigo-btn');
        editCodigoBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.dataset.id;
                const codigo = btn.dataset.codigo;
                const descricao = btn.dataset.descricao;
                this.openEditCodigoModal(id, codigo, descricao);
            });
        });

        // Edit ponto buttons
        const editPontoBtns = document.querySelectorAll('.edit-ponto-btn');
        editPontoBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.dataset.id;
                const nome = btn.dataset.nome;
                const localizacao = btn.dataset.localizacao;
                this.openEditPontoModal(id, nome, localizacao);
            });
        });
    }

    bindDeleteButtons() {
        // Delete cliente buttons
        const deleteClienteBtns = document.querySelectorAll('.delete-cliente-btn');
        deleteClienteBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.dataset.id;
                const nome = btn.dataset.nome;
                this.confirmDeleteCliente(id, nome);
            });
        });

        // Delete codigo buttons
        const deleteCodigoBtns = document.querySelectorAll('.delete-codigo-btn');
        deleteCodigoBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.dataset.id;
                const codigo = btn.dataset.codigo;
                this.confirmDeleteCodigo(id, codigo);
            });
        });

        // Delete ponto buttons
        const deletePontoBtns = document.querySelectorAll('.delete-ponto-btn');
        deletePontoBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.dataset.id;
                this.confirmDeletePonto(id);
            });
        });
    }

    bindBulkOperations() {
        const selectAll = document.getElementById('select-all');
        const checkboxes = document.querySelectorAll('.select-checkbox');
        const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
        
        if (!selectAll || !bulkDeleteBtn) return;

        // Update button state based on selection
        const updateBulkDeleteButton = () => {
            const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            
            bulkDeleteBtn.disabled = !anyChecked;
            
            selectAll.checked = allChecked && checkboxes.length > 0;
            selectAll.indeterminate = anyChecked && !allChecked;
            
            // Update button text
            const selectedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
            if (selectedCount > 0) {
                bulkDeleteBtn.innerHTML = `<i class="fas fa-trash-alt mr-2"></i>Excluir ${selectedCount} Selecionado${selectedCount > 1 ? 's' : ''}`;
            } else {
                bulkDeleteBtn.innerHTML = `<i class="fas fa-trash-alt mr-2"></i>Excluir Selecionados`;
            }
        };
        
        // Select all functionality
        selectAll.addEventListener('change', () => {
            checkboxes.forEach(cb => cb.checked = selectAll.checked);
            updateBulkDeleteButton();
        });
        
        // Individual checkbox functionality
        checkboxes.forEach(cb => cb.addEventListener('change', updateBulkDeleteButton));
        
        // Initial state
        updateBulkDeleteButton();
    }

    openEditClienteModal(id, nome) {
        // Populate edit form
        const modal = document.getElementById('editClienteModal');
        if (modal) {
            const form = modal.querySelector('form');
            const nameInput = form.querySelector('[name="nome"]');
            const idInput = form.querySelector('[name="cliente_id"]');
            
            if (nameInput) nameInput.value = nome;
            if (idInput) idInput.value = id;
            
            window.modalManager.open('editClienteModal');
        }
    }

    openEditCodigoModal(id, codigo, descricao) {
        const modal = document.getElementById('editCodigoModal');
        if (modal) {
            const form = modal.querySelector('form');
            const codigoInput = form.querySelector('[name="codigo"]');
            const descricaoInput = form.querySelector('[name="descricao"]');
            const idInput = form.querySelector('[name="codigo_id"]');
            
            if (codigoInput) codigoInput.value = codigo;
            if (descricaoInput) descricaoInput.value = descricao || '';
            if (idInput) idInput.value = id;
            
            window.modalManager.open('editCodigoModal');
        }
    }

    openEditPontoModal(id, nome, localizacao) {
        const modal = document.getElementById('editPontoModal');
        if (modal) {
            const form = modal.querySelector('form');
            const nomeInput = form.querySelector('[name="nome"]');
            const localizacaoInput = form.querySelector('[name="localizacao"]');
            const idInput = form.querySelector('[name="ponto_id"]');
            
            if (nomeInput) nomeInput.value = nome;
            if (localizacaoInput) localizacaoInput.value = localizacao || '';
            if (idInput) idInput.value = id;
            
            window.modalManager.open('editPontoModal');
        }
    }

    confirmDeleteCliente(id, nome) {
        if (confirm(`Tem certeza que deseja excluir o cliente "${nome}"?\\n\\nEsta ação não pode ser desfeita.`)) {
            this.deleteCliente(id);
        }
    }

    confirmDeleteCodigo(id, codigo) {
        if (confirm(`Tem certeza que deseja excluir o código "${codigo}"?\\n\\nEsta ação não pode ser desfeita.`)) {
            this.deleteCodigo(id);
        }
    }

    confirmDeletePonto(id) {
        if (confirm('Tem certeza que deseja excluir este ponto?\\n\\nEsta ação não pode ser desfeita.')) {
            this.deletePonto(id);
        }
    }

    async deleteCliente(id) {
        try {
            await window.TrafficCount.apiRequest(`/trabalhos/api/clientes/${id}/`, {
                method: 'DELETE'
            });
            
            window.TrafficCount.showToast('Cliente excluído com sucesso!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } catch (error) {
            console.error('Erro ao excluir cliente:', error);
            window.TrafficCount.showToast('Erro ao excluir cliente', 'error');
        }
    }

    async deleteCodigo(id) {
        try {
            await window.TrafficCount.apiRequest(`/trabalhos/api/codigos/${id}/`, {
                method: 'DELETE'
            });
            
            window.TrafficCount.showToast('Código excluído com sucesso!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } catch (error) {
            console.error('Erro ao excluir código:', error);
            window.TrafficCount.showToast('Erro ao excluir código', 'error');
        }
    }

    async deletePonto(id) {
        try {
            await window.TrafficCount.apiRequest(`/trabalhos/api/pontos/${id}/`, {
                method: 'DELETE'
            });
            
            window.TrafficCount.showToast('Ponto excluído com sucesso!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } catch (error) {
            console.error('Erro ao excluir ponto:', error);
            window.TrafficCount.showToast('Erro ao excluir ponto', 'error');
        }
    }

    async bulkCreatePontos(data) {
        try {
            const result = await window.TrafficCount.apiRequest('/trabalhos/api/pontos/bulk-create/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            
            window.TrafficCount.showToast('Pontos criados com sucesso!', 'success');
            return result;
        } catch (error) {
            console.error('Erro na criação em massa:', error);
            window.TrafficCount.showToast('Erro ao criar pontos', 'error');
            throw error;
        }
    }

    bindFormSubmissions() {
        // Edit cliente form
        const editClienteForm = document.getElementById('editClienteForm');
        if (editClienteForm) {
            editClienteForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const formData = new FormData(editClienteForm);
                const clienteId = formData.get('cliente_id');
                
                if (clienteId) {
                    editClienteForm.action = `/trabalhos/cliente/${clienteId}/update/`;
                    editClienteForm.submit();
                }
            });
        }

        // Edit codigo form
        const editCodigoForm = document.getElementById('editCodigoForm');
        if (editCodigoForm) {
            editCodigoForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const formData = new FormData(editCodigoForm);
                const codigoId = formData.get('codigo_id');
                
                if (codigoId) {
                    editCodigoForm.action = `/trabalhos/codigo/${codigoId}/update/`;
                    editCodigoForm.submit();
                }
            });
        }

        // Edit ponto form
        const editPontoForm = document.getElementById('editPontoForm');
        if (editPontoForm) {
            editPontoForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const formData = new FormData(editPontoForm);
                const pontoId = formData.get('ponto_id');
                
                if (pontoId) {
                    editPontoForm.action = `/trabalhos/ponto/${pontoId}/update/`;
                    editPontoForm.submit();
                }
            });
        }

        // Bulk create pontos form
        const bulkCreateForm = document.getElementById('bulkCreatePontosForm');
        if (bulkCreateForm) {
            bulkCreateForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(bulkCreateForm);
                const data = {
                    codigo_id: formData.get('codigo_id'),
                    quantity: parseInt(formData.get('quantity')),
                    prefix: formData.get('prefix'),
                    suffix: formData.get('suffix'),
                    startNumber: parseInt(formData.get('startNumber')),
                    digits: parseInt(formData.get('digits'))
                };

                try {
                    await this.bulkCreatePontos(data);
                    window.modalManager.close('bulkCreatePontosModal');
                    setTimeout(() => window.location.reload(), 1000);
                } catch (error) {
                    console.error('Bulk create error:', error);
                }
            });
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.trabalhosManager = new TrabalhosManager();
    console.log('Trabalhos page initialized');
});