/**
 * Sessões de Contagem - JavaScript específico da página
 * Funcionalidades: Filtros, ordenação, ações de sessão, UI interativa
 */

$(document).ready(function() {
    // Initialize Select2 with enhanced styling
    $('.select2').each(function() {
        let placeholder = $(this).attr('name');
        placeholder = placeholder.charAt(0).toUpperCase() + placeholder.slice(1);
        $(this).select2({
            placeholder: `Selecione um ${placeholder}`,
            allowClear: true,
            width: '100%',
            language: {
                noResults: function() {
                    return "Nenhum resultado encontrado";
                },
                searching: function() {
                    return "Pesquisando...";
                }
            },
            theme: "default"
        });
    });

    // Dynamic filter for Ponto based on Codigo selection
    $('#codigo-select').on('change', function() {
        const codigoSelecionado = $(this).val();
        const pontoSelect = $('#ponto-select');
        const pontoSelectContainer = pontoSelect.parent();
        
        // Show loading state
        pontoSelectContainer.addClass('loading-select');
        pontoSelect.addClass('select-disabled');
        
        // Reset ponto selection
        pontoSelect.val('').trigger('change');
        
        if (codigoSelecionado) {
            // Fetch pontos for selected codigo
            $.ajax({
                url: '/trabalhos/pontos-por-codigo/',
                method: 'GET',
                data: {
                    'codigo': codigoSelecionado
                },
                success: function(data) {
                    // Clear existing options except the first one
                    pontoSelect.find('option:not(:first)').remove();
                    
                    // Add new options
                    if (data.pontos && data.pontos.length > 0) {
                        data.pontos.forEach(function(ponto) {
                            const isSelected = window.filtrosAtivos && window.filtrosAtivos.ponto === ponto ? 'selected' : '';
                            pontoSelect.append(`<option value="${ponto}" ${isSelected}>${ponto}</option>`);
                        });
                        
                        // Update label to show filtered state
                        const label = pontoSelect.closest('.filter-group').find('label');
                        label.find('.text-gray-500').text(`(${data.pontos.length} pontos encontrados)`);
                    } else {
                        // Update label to show no results
                        const label = pontoSelect.closest('.filter-group').find('label');
                        label.find('.text-gray-500').text('(Nenhum ponto encontrado)');
                    }
                    
                    // Refresh Select2
                    pontoSelect.trigger('change');
                },
                error: function(xhr, status, error) {
                    console.error('Erro ao buscar pontos:', error);
                    showNotification('Erro ao buscar pontos para o código selecionado', 'error');
                    
                    // Reset label
                    const label = pontoSelect.closest('.filter-group').find('label');
                    label.find('.text-gray-500').text('(Erro ao carregar)');
                },
                complete: function() {
                    // Remove loading state
                    pontoSelectContainer.removeClass('loading-select');
                    pontoSelect.removeClass('select-disabled');
                }
            });
        } else {
            // Reset to original pontos list when no codigo is selected
            pontoSelect.find('option:not(:first)').remove();
            // Add original pontos back
            if (window.originalPontos) {
                window.originalPontos.forEach(function(ponto) {
                    pontoSelect.append(`<option value="${ponto}">${ponto}</option>`);
                });
            }
            
            // Reset label
            const label = pontoSelect.closest('.filter-group').find('label');
            label.find('.text-gray-500').text('(Filtre por código primeiro)');
            
            // Remove loading state
            pontoSelectContainer.removeClass('loading-select');
            pontoSelect.removeClass('select-disabled');
        }
    });

    // Trigger change event on page load if there's a pre-selected codigo
    const codigoInicial = $('#codigo-select').val();
    if (codigoInicial) {
        $('#codigo-select').trigger('change');
    }

    // Enhanced menu handling
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.action-menu').length) {
            $('.action-dropdown').hide().removeClass('dropdown-up arrow-left');
        }
    });
    
    // Hide dropdowns on scroll or resize
    $(window).on('scroll resize', function() {
        $('.action-dropdown').hide().removeClass('dropdown-up arrow-left');
    });

    // Toggle action menu with smart positioning for viewport and table position
    $('.js-toggle-menu').on('click', function(e) {
        e.stopPropagation();
        const button = $(this);
        const menu = button.siblings('.action-dropdown');
        
        // Hide other menus
        $('.action-dropdown').not(menu).hide().removeClass('dropdown-up arrow-left');
        
        if (menu.is(':visible')) {
            menu.hide();
        } else {
            // Get table and row information
            const row = button.closest('tr');
            const table = button.closest('table');
            const allRows = table.find('tbody tr');
            const rowIndex = allRows.index(row);
            const totalRows = allRows.length;
            
            // Check viewport constraints
            const buttonRect = this.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            const menuHeight = 150; // Approximate dropdown height
            
            // Determine if we should open upward based on:
            // 1. Row position in table (last 3 rows)
            // 2. Viewport constraints
            const isInLastRows = rowIndex >= totalRows - 3;
            const wouldGoOutOfViewport = buttonRect.bottom + menuHeight > viewportHeight;
            
            if (isInLastRows || wouldGoOutOfViewport) {
                // Open upward
                menu.addClass('dropdown-up');
                menu.css({
                    'top': 'auto',
                    'bottom': '100%',
                    'margin-bottom': '5px',
                    'margin-top': '0'
                });
            } else {
                // Open downward (default)
                menu.removeClass('dropdown-up');
                menu.css({
                    'top': '100%',
                    'bottom': 'auto',
                    'margin-top': '5px',
                    'margin-bottom': '0'
                });
            }
            
            menu.show();
        }
    });

    // Action handlers with enhanced UX
    $('.js-finalizar').on('click', function() {
        const sessaoId = $(this).data('sessao-id');
        finalizarSessao(sessaoId);
    });

    $('.js-exportar').on('click', function() {
        const sessaoId = $(this).data('sessao-id');
        exportarCSV(sessaoId);
    });

    // Add loading states and animations
    $('form').on('submit', function() {
        const submitBtn = $(this).find('button[type="submit"]');
        submitBtn.prop('disabled', true);
        submitBtn.html('<i class="fas fa-spinner fa-spin mr-2"></i>Carregando...');
    });

    // Auto-collapse filter if no filters are active and screen is small
    if (window.innerWidth < 768 && !hasActiveFilters()) {
        // Keep collapsed on mobile by default
    } else if (hasActiveFilters()) {
        // Auto-expand if there are active filters
        const filterContent = document.getElementById('filter-content');
        const toggleIcon = document.querySelector('.filter-toggle-icon');
        if (filterContent && toggleIcon) {
            filterContent.classList.add('expanded');
            toggleIcon.classList.add('rotated');
        }
    }
});

function hasActiveFilters() {
    const urlParams = new URLSearchParams(window.location.search);
    const filterParams = ['status', 'usuario', 'codigo', 'ponto', 'data', 'padrao'];
    return filterParams.some(param => urlParams.get(param));
}

function toggleFilters() {
    const filterContent = document.getElementById('filter-content');
    const toggleIcon = document.querySelector('.filter-toggle-icon');
    
    if (filterContent.classList.contains('expanded')) {
        filterContent.classList.remove('expanded');
        toggleIcon.classList.remove('rotated');
    } else {
        filterContent.classList.add('expanded');
        toggleIcon.classList.add('rotated');
        
        // Re-initialize Select2 after expansion to ensure proper rendering
        setTimeout(() => {
            $('.select2').trigger('change');
        }, 300);
    }
}

function removeFilter(filterName) {
    const input = document.querySelector(`[name="${filterName}"]`);
    if (input) {
        input.value = '';
        if ($(input).hasClass('select2')) {
            $(input).val(null).trigger('change');
        }
        
        // Special handling for codigo filter removal
        if (filterName === 'codigo') {
            // Also clear ponto filter since it's dependent
            const pontoInput = document.querySelector('[name="ponto"]');
            if (pontoInput) {
                pontoInput.value = '';
                if ($(pontoInput).hasClass('select2')) {
                    $(pontoInput).val(null).trigger('change');
                }
            }
        }
        
        showLoadingState();
        document.getElementById('filter-form').submit();
    }
}

function resetFilters() {
    const inputs = document.querySelectorAll('#filter-form input:not(#sort-field), #filter-form select');
    inputs.forEach(input => {
        input.value = '';
    });
    $('.select2').val(null).trigger('change');
    
    showLoadingState();
    document.getElementById('filter-form').submit();
}

function sortTable(field) {
    const sortField = document.getElementById('sort-field');
    let currentSort = sortField.value;
    
    if (currentSort === field) {
        sortField.value = '-' + field;
    } else if (currentSort === '-' + field) {
        sortField.value = field;
    } else {
        sortField.value = field;
    }
    
    // Add visual feedback
    showLoadingState();
    document.getElementById('filter-form').submit();
}

function finalizarSessao(sessaoId) {
    showConfirmDialog(
        'Finalizar Sessão',
        'Tem certeza que deseja finalizar esta sessão? Esta ação não pode ser desfeita.',
        'warning'
    ).then((confirmed) => {
        if (!confirmed) return;

        showLoadingNotification('Finalizando sessão...');

        fetch('/contagens/finalizar-sessao/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
                sessao_id: sessaoId
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro na resposta do servidor');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                showNotification('Sessão finalizada com sucesso!', 'success');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                throw new Error(data.message || 'Erro ao finalizar sessão');
            }
        })
        .catch(error => {
            showNotification('Erro ao finalizar sessão: ' + error.message, 'error');
        });
    });
}

function exportarCSV(sessaoId) {
    showLoadingNotification('Preparando exportação...');
    
    // Create temporary notification for download
    const notification = showNotification('Download iniciado!', 'info', 3000);
    
    window.location.href = `/contagens/exportar-csv/${sessaoId}`;
}

function showLoadingState() {
    const overlay = document.createElement('div');
    overlay.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    overlay.innerHTML = `
        <div class="bg-white rounded-lg p-6 flex items-center gap-3">
            <i class="fas fa-spinner fa-spin text-blue-600 text-xl"></i>
            <span class="text-gray-700 font-medium">Carregando...</span>
        </div>
    `;
    document.body.appendChild(overlay);
}

function showNotification(message, type = 'info', duration = 3000) {
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        warning: 'bg-yellow-500',
        info: 'bg-blue-500'
    };

    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };

    const notification = document.createElement('div');
    notification.className = `fixed bottom-4 right-4 ${colors[type]} text-white px-6 py-4 rounded-lg shadow-lg z-50 flex items-center gap-3 transform transition-all duration-300 translate-x-full`;
    notification.innerHTML = `
        <i class="${icons[type]}"></i>
        <span class="font-medium">${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 100);
    
    // Animate out and remove
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => notification.remove(), 300);
    }, duration);
    
    return notification;
}

function showLoadingNotification(message) {
    return showNotification(`<i class="fas fa-spinner fa-spin mr-2"></i>${message}`, 'info', 2000);
}

function showConfirmDialog(title, message, type = 'warning') {
    return new Promise((resolve) => {
        const colors = {
            warning: 'text-yellow-600 bg-yellow-100',
            danger: 'text-red-600 bg-red-100',
            info: 'text-blue-600 bg-blue-100'
        };

        const icons = {
            warning: 'fas fa-exclamation-triangle',
            danger: 'fas fa-exclamation-circle',
            info: 'fas fa-info-circle'
        };

        const overlay = document.createElement('div');
        overlay.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        overlay.innerHTML = `
            <div class="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4 transform transition-all duration-300 scale-95">
                <div class="flex items-center gap-4 mb-4">
                    <div class="w-12 h-12 rounded-full ${colors[type]} flex items-center justify-center">
                        <i class="${icons[type]} text-xl"></i>
                    </div>
                    <div>
                        <h3 class="text-lg font-bold text-gray-900">${title}</h3>
                    </div>
                </div>
                <p class="text-gray-600 mb-6">${message}</p>
                <div class="flex gap-3 justify-end">
                    <button class="cancel-btn px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-medium transition-colors">
                        Cancelar
                    </button>
                    <button class="confirm-btn px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors">
                        Confirmar
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        
        // Animate in
        setTimeout(() => {
            overlay.querySelector('.bg-white').classList.add('scale-100');
            overlay.querySelector('.bg-white').classList.remove('scale-95');
        }, 100);

        overlay.querySelector('.cancel-btn').onclick = () => {
            overlay.remove();
            resolve(false);
        };

        overlay.querySelector('.confirm-btn').onclick = () => {
            overlay.remove();
            resolve(true);
        };

        overlay.onclick = (e) => {
            if (e.target === overlay) {
                overlay.remove();
                resolve(false);
            }
        };
    });
}