#croquis/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Croquis
from .forms import CroquisForm, CroquisReviewForm, CroquisFilterForm
from django.utils import timezone
from django.http import JsonResponse
from trabalhos.models import Ponto, Cliente, Codigo
from padroes.models import PadraoContagem
from django.db.models import Q

@login_required
def ajax_load_pontos(request):
    """
    Retorna em JSON os pontos de um código específico.
    URL: /croquis/ajax/load-pontos/?codigo_id=123
    """
    codigo_id = request.GET.get('codigo_id')
    pontos = (
        Ponto.objects.filter(codigo_id=codigo_id)
                     .order_by('nome')
                     .values('id', 'nome')
    )
    return JsonResponse(list(pontos), safe=False)

class CroquisListView(LoginRequiredMixin, ListView):
    model = Croquis
    template_name = 'croquis/croquis_list.html'
    context_object_name = 'croquis'
    paginate_by = 10

    def get_queryset(self):
        queryset = Croquis.objects.all()
        form = CroquisFilterForm(self.request.GET)

        if form.is_valid():
            # Filtro por código
            if form.cleaned_data['codigo']:
                queryset = queryset.filter(codigo=form.cleaned_data['codigo'])
            
            # Filtro por ponto
            if form.cleaned_data['ponto']:
                queryset = queryset.filter(ponto=form.cleaned_data['ponto'])
            
            # Filtro por lote
            if form.cleaned_data['lote']:
                queryset = queryset.filter(lote__icontains=form.cleaned_data['lote'])
            
            # Filtro por status
            if form.cleaned_data['status']:
                queryset = queryset.filter(status=form.cleaned_data['status'])
            
            # Filtro por data
            if form.cleaned_data['data_croqui']:
                queryset = queryset.filter(data_croqui=form.cleaned_data['data_croqui'])
            
            # Filtro por criador
            if form.cleaned_data['created_by']:
                queryset = queryset.filter(created_by=form.cleaned_data['created_by'])

        return queryset.select_related('codigo', 'ponto', 'created_by', 'aprovado_por').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = CroquisFilterForm(self.request.GET)
        return context

@login_required
def croquis_list(request):
    cliente_id = request.GET.get('cliente_id')
    codigo_id = request.GET.get('codigo_id')
    ponto_id = request.GET.get('ponto_id')
    context = {}
    if not cliente_id:
        clientes = Cliente.objects.order_by('nome')
        context['clientes'] = clientes
    elif cliente_id and not codigo_id:
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        codigos = Codigo.objects.filter(cliente=cliente).order_by('codigo')
        context['cliente'] = cliente
        context['codigos'] = codigos
    elif codigo_id and not ponto_id:
        codigo = get_object_or_404(Codigo, pk=codigo_id)
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        pontos = Ponto.objects.filter(codigo=codigo).order_by('nome')
        context['cliente'] = cliente
        context['codigo'] = codigo
        context['pontos'] = pontos
    else:
        ponto = get_object_or_404(Ponto, pk=ponto_id)
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        codigo = get_object_or_404(Codigo, pk=codigo_id)
        croquis_list = Croquis.objects.filter(ponto=ponto).order_by('-created_at')
        context['cliente'] = cliente
        context['codigo'] = codigo
        context['ponto'] = ponto
        context['croquis_list'] = croquis_list
    return render(request, 'croquis/croquis_list.html', context)

class CroquisDetailView(LoginRequiredMixin, DetailView):
    model = Croquis
    template_name = 'croquis/croquis_detail.html'
    context_object_name = 'croqui'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Croqui {self.object.codigo}'
        return context

class CroquisCreateView(LoginRequiredMixin, CreateView):
    model = Croquis
    template_name = 'croquis/croquis_upload.html'  # Nova template simplificada
    fields = ['imagem']  # Apenas o campo de imagem
    
    def get_success_url(self):
        # Retornar para a lista de croquis do ponto
        ponto_id = self.request.GET.get('ponto_id')
        ponto = get_object_or_404(Ponto, pk=ponto_id)
        return f"{reverse_lazy('croquis_list')}?cliente_id={ponto.codigo.cliente.id}&codigo_id={ponto.codigo.id}&ponto_id={ponto.id}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adicionar informações do ponto ao contexto
        ponto_id = self.request.GET.get('ponto_id')
        if ponto_id:
            ponto = get_object_or_404(Ponto, pk=ponto_id)
            context['ponto'] = ponto
            context['codigo'] = ponto.codigo
            context['cliente'] = ponto.codigo.cliente
        return context

    def form_valid(self, form):
        # Preencher automaticamente os campos não exibidos no formulário
        ponto_id = self.request.GET.get('ponto_id')
        if not ponto_id:
            messages.error(self.request, "É necessário especificar um ponto para criar um croqui.")
            return self.form_invalid(form)
            
        ponto = get_object_or_404(Ponto, pk=ponto_id)
        
        # Definir os campos obrigatórios
        form.instance.ponto = ponto
        form.instance.codigo = ponto.codigo
        form.instance.created_by = self.request.user
        form.instance.status = 'P'
        
        # Definir data atual para o croqui
        from django.utils import timezone
        form.instance.data_croqui = timezone.now().date()
        
        # Gerar um lote baseado na data e ponto
        form.instance.lote = f"LOTE-{ponto.id}-{timezone.now().strftime('%Y%m%d')}"
        
        # Definir valores padrão para campos não exibidos
        form.instance.movimento = 'Padrão'
            
        # Usar o primeiro padrão disponível
        padrao = PadraoContagem.objects.first()
        if padrao:
            form.instance.padrao = padrao
                
        # Definir horários padrão
        form.instance.hora_inicio = '08:00'
        form.instance.hora_fim = '18:00'
            
        response = super().form_valid(form)
        messages.success(self.request, 'Croqui enviado com sucesso!')
        return response

    def form_invalid(self, form):
        error_messages = []
        for field, errors in form.errors.items():
            if field != '__all__':  # Erros específicos de campo
                error_messages.append(f"{field}: {', '.join(errors)}")
            else:  # Erros gerais do formulário
                error_messages.extend(errors)
        
        messages.error(self.request, f"Erro ao criar o croqui: {' | '.join(error_messages)}")
        return super().form_invalid(form)

class CroquisUpdateView(LoginRequiredMixin, UpdateView):
    model = Croquis
    fields = ['imagem']
    template_name = 'croquis/croquis_upload.html'
    
    def get_success_url(self):
        # Retornar para a lista de croquis do ponto
        ponto = self.object.ponto
        return f"{reverse_lazy('croquis_list')}?cliente_id={ponto.codigo.cliente.id}&codigo_id={ponto.codigo.id}&ponto_id={ponto.id}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adicionar informações do ponto ao contexto
        context['ponto'] = self.object.ponto
        context['codigo'] = self.object.codigo
        context['cliente'] = self.object.codigo.cliente
        context['is_edit'] = True
        return context

class CroquisDeleteView(LoginRequiredMixin, DeleteView):
    model = Croquis
    template_name = 'croquis/croquis_confirm_delete.html'
    success_url = reverse_lazy('croquis_list')

class CroquisReviewView(LoginRequiredMixin, UpdateView):
    model = Croquis
    form_class = CroquisReviewForm
    template_name = 'croquis/croquis_review.html'
    success_url = reverse_lazy('croquis_list')
    context_object_name = 'croqui'

    def form_valid(self, form):
        form.instance.aprovado_por = self.request.user
        form.instance.aprovado_em = timezone.now()
        response = super().form_valid(form)
        status = form.cleaned_data['status']
        messages.success(
            self.request, 
            'Croqui aprovado com sucesso!' if status == 'A' else 'Croqui reprovado com sucesso!'
        )
        return response
