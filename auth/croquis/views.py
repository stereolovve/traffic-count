#croquis/views.py
from django.shortcuts import render
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
from trabalhos.models import Ponto
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
    form_class = CroquisForm
    template_name = 'croquis/croquis_form.html'
    success_url = reverse_lazy('croquis_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.status = 'P'  # Garante que o status seja 'P'
        response = super().form_valid(form)
        messages.success(self.request, 'Croqui criado com sucesso!')
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
    form_class = CroquisForm
    template_name = 'croquis/croquis_form.html'
    success_url = reverse_lazy('croquis_list')

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
