// Trabalhos.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM carregado - Inicializando trabalhos.js');
    
    // Função para obter o token CSRF
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Helper functions
    function showToast(message, isSuccess = true) {
        console.log('Mostrando toast:', message, isSuccess);
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg text-white ${
            isSuccess ? 'bg-green-500' : 'bg-red-500'
        }`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    function showModal(modalId) {
        console.log('Tentando mostrar modal:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            console.log('Modal encontrado, removendo classe hidden');
            modal.classList.remove('hidden');
        } else {
            console.error('Modal não encontrado:', modalId);
        }
    }

    function hideModal(modalId) {
        console.log('Tentando esconder modal:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            console.log('Modal encontrado, adicionando classe hidden');
            modal.classList.add('hidden');
        } else {
            console.error('Modal não encontrado:', modalId);
        }
    }

    // Bulk create points function
    async function bulkCreatePontos(data) {
        console.log('Iniciando criação em massa de pontos:', data);
        try {
            const response = await fetch('/api/pontos/bulk-create/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                const result = await response.json();
                showToast('Pontos criados com sucesso!', true);
                console.log('Pontos criados:', result);
                return result;
            } else {
                const error = await response.json();
                showToast(error.message || 'Erro ao criar pontos', false);
                console.error('Erro na criação em massa:', error);
                throw new Error(error.message || 'Erro ao criar pontos');
            }
        } catch (error) {
            console.error('Erro na requisição:', error);
            showToast('Erro ao criar pontos', false);
            throw error;
        }
    }

    // Create buttons
    const newClienteBtn = document.getElementById('newClienteBtn');
    console.log('Botão de novo cliente:', newClienteBtn);
    if (newClienteBtn) {
        newClienteBtn.addEventListener('click', () => {
            console.log('Clique no botão de novo cliente');
            showModal('newClienteModal');
        });
    } else {
        console.error('Botão de novo cliente não encontrado!');
    }

    const newCodigoBtn = document.getElementById('newCodigoBtn');
    console.log('Botão de novo código:', newCodigoBtn);
    if (newCodigoBtn) {
        newCodigoBtn.addEventListener('click', () => {
            console.log('Clique no botão de novo código');
            showModal('newCodigoModal');
        });
    } else {
        console.error('Botão de novo código não encontrado!');
    }

    const newPontoBtn = document.getElementById('newPontoBtn');
    console.log('Botão de novo ponto:', newPontoBtn);
    if (newPontoBtn) {
        newPontoBtn.addEventListener('click', () => {
            console.log('Clique no botão de novo ponto');
            showModal('newPontoModal');
        });
    } else {
        console.error('Botão de novo ponto não encontrado!');
    }

    // Edit buttons
    document.querySelectorAll('.edit-cliente-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            const nome = btn.dataset.nome;
            const form = document.getElementById('editClienteForm');
            form.dataset.id = id;
            form.action = `/trabalhos/cliente/${id}/update/`;
            document.getElementById('editClienteNome').value = nome;
            showModal('editClienteModal');
        });
    });

    document.querySelectorAll('.edit-codigo-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            const codigo = btn.dataset.codigo;
            const form = document.getElementById('editCodigoForm');
            form.dataset.id = id;
            form.action = `/trabalhos/codigo/${id}/update/`;
            document.getElementById('editCodigoNome').value = codigo;
            showModal('editCodigoModal');
        });
    });

    document.querySelectorAll('.edit-ponto-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            const nome = btn.dataset.nome;
            const form = document.getElementById('editPontoForm');
            form.dataset.id = id;
            form.action = `/trabalhos/ponto/${id}/update/`;
            document.getElementById('editPontoNome').value = nome;
            showModal('editPontoModal');
        });
    });

    // Delete buttons
    document.querySelectorAll('.delete-cliente-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            const form = document.getElementById('deleteClienteForm');
            form.dataset.id = id;
            form.action = `/trabalhos/cliente/${id}/delete/`;
            showModal('deleteClienteModal');
        });
    });

    document.querySelectorAll('.delete-codigo-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            const form = document.getElementById('deleteCodigoForm');
            form.dataset.id = id;
            form.action = `/trabalhos/codigo/${id}/delete/`;
            showModal('deleteCodigoModal');
        });
    });

    document.querySelectorAll('.delete-ponto-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            const form = document.getElementById('deletePontoForm');
            form.dataset.id = id;
            form.action = `/trabalhos/ponto/${id}/delete/`;
            showModal('deletePontoModal');
        });
    });

    // Setup create forms
    const clienteForm = document.getElementById('clienteForm');
    const codigoForm = document.getElementById('codigoForm');
    const pontoForm = document.getElementById('pontoForm');

    console.log('Formulário de cliente:', clienteForm);
    console.log('Formulário de código:', codigoForm);
    console.log('Formulário de ponto:', pontoForm);

    if (clienteForm) {
        clienteForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('Enviando formulário de cliente');
            const formData = new FormData(clienteForm);
            try {
                const response = await fetch('/trabalhos/api/clientes/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        nome: formData.get('nome'),
                        descricao: formData.get('descricao')
                    })
                });
                if (response.ok) {
                    showToast('Cliente criado com sucesso!', true);
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    const data = await response.json();
                    showToast(data.message || 'Erro ao criar cliente', false);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('Erro ao criar cliente', false);
            }
        });
    }

    if (codigoForm) {
        codigoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('Enviando formulário de código');
            const formData = new FormData(codigoForm);
            console.log('Dados do formulário:', {
                codigo: formData.get('codigo'),
                descricao: formData.get('descricao'),
                cliente: formData.get('cliente')
            });
            try {
                const response = await fetch('/trabalhos/api/codigos/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        codigo: formData.get('codigo'),
                        descricao: formData.get('descricao'),
                        cliente: formData.get('cliente')
                    })
                });
                console.log('Resposta do servidor:', response);
                if (response.ok) {
                    showToast('Código criado com sucesso!', true);
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    const data = await response.json();
                    console.error('Erro do servidor:', data);
                    showToast(data.message || 'Erro ao criar código', false);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('Erro ao criar código', false);
            }
        });
    } else {
        console.error('Formulário de código não encontrado!');
    }

    if (pontoForm) {
        pontoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(pontoForm);
            try {
                const response = await fetch('/trabalhos/api/pontos/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        nome: formData.get('nome'),
                        descricao: formData.get('descricao'),
                        codigo: formData.get('codigo')
                    })
                });
                if (response.ok) {
                    showToast('Ponto criado com sucesso!', true);
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    const data = await response.json();
                    showToast(data.message || 'Erro ao criar ponto', false);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('Erro ao criar ponto', false);
            }
        });
    }

    // Edit form submissions
    document.getElementById('editClienteForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const id = form.dataset.id;
        const formData = new FormData(form);

        try {
            const response = await fetch(`/trabalhos/cliente/${id}/update/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: formData
            });

            if (response.ok) {
                showToast('Cliente atualizado com sucesso!');
                window.location.reload();
            } else {
                showToast('Erro ao atualizar cliente', false);
            }
        } catch (error) {
            showToast('Erro ao atualizar cliente', false);
        }
    });

    document.getElementById('editCodigoForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const id = form.dataset.id;
        const formData = new FormData(form);

        try {
            const response = await fetch(`/trabalhos/codigo/${id}/update/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: formData
            });

            if (response.ok) {
                showToast('Código atualizado com sucesso!');
                window.location.reload();
            } else {
                showToast('Erro ao atualizar código', false);
            }
        } catch (error) {
            showToast('Erro ao atualizar código', false);
        }
    });

    document.getElementById('editPontoForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const id = form.dataset.id;
        const formData = new FormData(form);

        try {
            const response = await fetch(`/trabalhos/ponto/${id}/update/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: formData
            });

            if (response.ok) {
                showToast('Ponto atualizado com sucesso!');
                window.location.reload();
            } else {
                showToast('Erro ao atualizar ponto', false);
            }
        } catch (error) {
            showToast('Erro ao atualizar ponto', false);
        }
    });

    // Delete form submissions
    document.getElementById('deleteClienteForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const id = form.dataset.id;
        const formData = new FormData(form);

        try {
            const response = await fetch(`/trabalhos/cliente/${id}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: formData
            });

            if (response.ok) {
                showToast('Cliente excluído com sucesso!');
                window.location.reload();
            } else {
                showToast('Erro ao excluir cliente', false);
            }
        } catch (error) {
            showToast('Erro ao excluir cliente', false);
        }
    });

    document.getElementById('deleteCodigoForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const id = form.dataset.id;
        const formData = new FormData(form);

        try {
            const response = await fetch(`/trabalhos/codigo/${id}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: formData
            });

            if (response.ok) {
                showToast('Código excluído com sucesso!');
                window.location.reload();
            } else {
                showToast('Erro ao excluir código', false);
            }
        } catch (error) {
            showToast('Erro ao excluir código', false);
        }
    });

    document.getElementById('deletePontoForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const id = form.dataset.id;
        const formData = new FormData(form);

        try {
            const response = await fetch(`/trabalhos/ponto/${id}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: formData
            });

            if (response.ok) {
                showToast('Ponto excluído com sucesso!');
                window.location.reload();
            } else {
                showToast('Erro ao excluir ponto', false);
            }
        } catch (error) {
            showToast('Erro ao excluir ponto', false);
        }
    });

    // Modal close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            console.log('Clique no botão de fechar modal');
            const modal = btn.closest('.modal');
            if (modal) {
                console.log('Modal encontrado para fechar:', modal.id);
                hideModal(modal.id);
            } else {
                console.error('Modal não encontrado para fechar');
            }
        });
    });

    // Bulk create points
    document.getElementById('bulkCreatePontosBtn')?.addEventListener('click', () => {
        showModal('bulkCreatePontosModal');
    });

    const bulkCreatePontosForm = document.getElementById('bulkCreatePontosForm');
    if (bulkCreatePontosForm) {
        bulkCreatePontosForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                quantity: parseInt(document.getElementById('quantity').value),
                prefix: document.getElementById('prefix').value,
                suffix: document.getElementById('suffix').value,
                startNumber: parseInt(document.getElementById('startNumber').value),
                digits: parseInt(document.getElementById('digits').value),
                codigo_id: document.getElementById('codigo_id').value
            };

            try {
                console.log('Enviando dados:', formData);
                const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                const response = await fetch('/trabalhos/api/pontos/bulk-create/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'include',
                    body: JSON.stringify(formData)
                });

                const data = await response.json();
                console.log('Resposta:', data);

                if (response.ok) {
                    showToast('Pontos criados com sucesso!', true);
                    hideModal('bulkCreatePontosModal');
                    location.reload();
                } else {
                    console.error('Erro do servidor:', data);
                    showToast(data.message || data.detail || 'Erro ao criar pontos', false);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('Erro ao criar pontos', false);
            }
        });
    }
});
