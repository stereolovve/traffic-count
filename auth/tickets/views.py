from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, fields
from django.views.decorators.http import require_POST
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Ticket
from .forms import TicketForm, TicketFilterForm
from .serializers import TicketSerializer
from trabalhos.models import Codigo
from padroes.models import PadraoContagem
from autenticacao.models import User
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta

User = get_user_model()

@login_required
def ticket_list(request):
    """Lista todos os tickets com filtros e paginação"""
    # Obter parâmetros de filtro
    status = request.GET.get('status', '')
    prioridade = request.GET.get('prioridade', '')
    turno = request.GET.get('turno', '')
    data = request.GET.get('data', '')
    coordenador = request.GET.get('coordenador', '')
    pesquisador = request.GET.get('pesquisador', '')
    search = request.GET.get('search', '')
    
    # Filtrar tickets
    tickets = Ticket.objects.select_related(
        'coordenador', 'pesquisador', 'codigo', 'codigo__cliente', 'padrao'
    ).order_by('-data', '-criado_em')
    
    if status:
        tickets = tickets.filter(status=status)
    if prioridade:
        tickets = tickets.filter(prioridade=prioridade)
    if turno:
        tickets = tickets.filter(turno=turno)
    if data:
        tickets = tickets.filter(data=data)
    if coordenador:
        tickets = tickets.filter(coordenador_id=coordenador)
    if pesquisador:
        tickets = tickets.filter(pesquisador_id=pesquisador)
    if search:
        tickets = tickets.filter(
            Q(codigo__codigo__icontains=search) |
            Q(codigo__descricao__icontains=search) |
            Q(cam__icontains=search) |
            Q(mov__icontains=search) |
            Q(observacao__icontains=search) |
            Q(coordenador__username__icontains=search) |
            Q(pesquisador__username__icontains=search)
        )
    
    # Paginação
    paginator = Paginator(tickets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Contexto para filtros
    coordenadores = User.objects.filter(setor='SUPER').order_by('username')
    pesquisadores = User.objects.all().order_by('username')
    
    context = {
        'page_obj': page_obj,
        'tickets': page_obj,
        'status_choices': Ticket.STATUS_CHOICES,
        'prioridade_choices': Ticket.PRIORIDADE_CHOICES,
        'turno_choices': Ticket.TURNO_CHOICES,
        'coordenadores': coordenadores,
        'pesquisadores': pesquisadores,
        'filters': {
            'status': status,
            'prioridade': prioridade,
            'turno': turno,
            'data': data,
            'coordenador': coordenador,
            'pesquisador': pesquisador,
            'search': search,
        }
    }
    
    return render(request, 'tickets/ticket_list.html', context)

@login_required
def ticket_create(request):
    """Cria um novo ticket"""
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            if not ticket.coordenador:
                ticket.coordenador = request.user
            ticket.save()
            messages.success(request, 'Ticket criado com sucesso!')
            return redirect('ticket_list')
    else:
        form = TicketForm()
    
    context = {
        'form': form,
        'title': 'Criar Novo Ticket'
    }
    return render(request, 'tickets/ticket_form.html', context)

@login_required
def ticket_edit(request, pk):
    """Edita um ticket existente"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ticket atualizado com sucesso!')
            return redirect('ticket_list')
    else:
        form = TicketForm(instance=ticket)
    
    context = {
        'form': form,
        'ticket': ticket,
        'title': 'Editar Ticket'
    }
    return render(request, 'tickets/ticket_form.html', context)

@login_required
def ticket_detail(request, pk):
    """Exibe detalhes de um ticket"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    context = {
        'ticket': ticket
    }
    return render(request, 'tickets/ticket_detail.html', context)

@login_required
@require_POST
def ticket_delete(request, pk):
    """Deleta um ticket"""
    ticket = get_object_or_404(Ticket, pk=pk)
    ticket.delete()
    messages.success(request, 'Ticket excluído com sucesso!')
    return redirect('ticket_list')

@login_required
@require_POST
def ticket_change_status(request, pk):
    """Muda o status de um ticket"""
    ticket = get_object_or_404(Ticket, pk=pk)
    new_status = request.POST.get('status')
    from_list = request.POST.get('from_list', '0')
    
    if new_status in dict(Ticket.STATUS_CHOICES):
        ticket.status = new_status
        ticket.save()
        messages.success(request, f'Status do ticket #{ticket.id} alterado para {ticket.get_status_display()}')
    else:
        messages.error(request, 'Status inválido')
    
    # Redirecionar baseado no parâmetro from_list
    if from_list == '1':
        return redirect('ticket_list')
    else:
        return redirect('ticket_detail', pk=ticket.pk)

@login_required
@require_POST
def ticket_assign_researcher(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    pesquisador_id = request.POST.get('pesquisador_id')
    
    try:
        pesquisador = User.objects.get(id=pesquisador_id)
        ticket.pesquisador = pesquisador
        ticket.save()
        messages.success(request, f'Pesquisador {pesquisador.username} atribuído ao ticket')
    except User.DoesNotExist:
        messages.error(request, 'Pesquisador não encontrado')
    
    return redirect('ticket_list')

# APIs para autocomplete
def api_codigos(request):
    """API para buscar códigos"""
    search = request.GET.get('search', '')
    codigos = Codigo.objects.filter(
        Q(codigo__icontains=search) | Q(descricao__icontains=search)
    )[:10]
    
    data = [{'id': c.id, 'text': f"{c.codigo} - {c.descricao}"} for c in codigos]
    return JsonResponse({'results': data})

def api_padroes(request):
    """API para buscar padrões"""
    search = request.GET.get('search', '')
    padroes = PadraoContagem.objects.filter(
        Q(pattern_type__icontains=search) | Q(veiculo__icontains=search)
    )[:10]
    
    data = [{'id': p.id, 'text': f"{p.pattern_type} - {p.veiculo}"} for p in padroes]
    return JsonResponse({'results': data})

def api_pesquisadores(request):
    """API para buscar pesquisadores"""
    search = request.GET.get('search', '')
    usuarios = User.objects.filter(
        Q(username__icontains=search) | Q(name__icontains=search) | Q(last_name__icontains=search)
    )[:10]
    
    data = [{'id': u.id, 'text': f"{u.username} - {u.name} {u.last_name}"} for u in usuarios]
    return JsonResponse({'results': data})

# ViewSet para API REST
class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Ticket.objects.select_related(
            'coordenador', 'pesquisador', 'codigo', 'codigo__cliente', 'padrao'
        )
        
        # Filtros
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        prioridade = self.request.query_params.get('prioridade', None)
        if prioridade:
            queryset = queryset.filter(prioridade=prioridade)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def atribuir_pesquisador(self, request, pk=None):
        """Atribui um pesquisador ao ticket"""
        ticket = self.get_object()
        pesquisador_id = request.data.get('pesquisador_id')
        
        try:
            pesquisador = User.objects.get(id=pesquisador_id)
            ticket.pesquisador = pesquisador
            ticket.save()
            return Response({'status': 'success'})
        except User.DoesNotExist:
            return Response(
                {'error': 'Pesquisador não encontrado'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def mudar_status(self, request, pk=None):
        """Muda o status do ticket"""
        ticket = self.get_object()
        novo_status = request.data.get('status')
        
        if novo_status in dict(Ticket.STATUS_CHOICES):
            ticket.status = novo_status
            ticket.save()
            return Response({'status': 'success'})
        else:
            return Response(
                {'error': 'Status inválido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

@login_required
def dashboard(request):
    """Dashboard com métricas e estatísticas dos tickets"""
    
    # Período para análise (últimos 30 dias por padrão)
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Estatísticas gerais
    total_tickets = Ticket.objects.filter(data__range=[start_date, end_date]).count()
    tickets_aguardando = Ticket.objects.filter(status='AGUARDANDO', data__range=[start_date, end_date]).count()
    tickets_em_andamento = Ticket.objects.filter(status__in=['INICIADO', 'CONTANDO'], data__range=[start_date, end_date]).count()
    tickets_finalizados = Ticket.objects.filter(status='FINALIZADO', data__range=[start_date, end_date]).count()
    
    # Distribuição por status
    status_distribution = Ticket.objects.filter(data__range=[start_date, end_date]).values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Distribuição por prioridade
    priority_distribution = Ticket.objects.filter(data__range=[start_date, end_date]).values('prioridade').annotate(
        count=Count('id')
    ).order_by('prioridade')
    
    # Distribuição por turno
    turno_distribution = Ticket.objects.filter(data__range=[start_date, end_date]).values('turno').annotate(
        count=Count('id')
    ).order_by('turno')
    
    # Top pesquisadores (por tickets finalizados)
    top_pesquisadores = User.objects.filter(
        tickets_pesquisados__status='FINALIZADO',
        tickets_pesquisados__data__range=[start_date, end_date]
    ).annotate(
        tickets_finalizados=Count('tickets_pesquisados')
    ).order_by('-tickets_finalizados')[:5]
    
    # Top coordenadores
    top_coordenadores = User.objects.filter(
        setor='SUPER',
        tickets_coordenados__data__range=[start_date, end_date]
    ).annotate(
        total_tickets_coordenados=Count('tickets_coordenados')
    ).order_by('-total_tickets_coordenados')[:5]
    
    # Evolução diária (últimos 7 dias)
    daily_evolution = []
    for i in range(7):
        date = end_date - timedelta(days=i)
        daily_tickets = Ticket.objects.filter(data=date).count()
        daily_finalizados = Ticket.objects.filter(data=date, status='FINALIZADO').count()
        daily_evolution.append({
            'date': date.strftime('%d/%m'),
            'total': daily_tickets,
            'finalizados': daily_finalizados
        })
    daily_evolution.reverse()
    
    # Tickets por período (manhã vs noite)
    manha_tickets = Ticket.objects.filter(turno='MANHA', data__range=[start_date, end_date]).count()
    noite_tickets = Ticket.objects.filter(turno='NOITE', data__range=[start_date, end_date]).count()
    
    # Tempo médio de finalização (em horas)
    avg_completion_time = Ticket.objects.filter(
        status='FINALIZADO',
        data_atribuicao__isnull=False,
        data_finalizacao__isnull=False,
        data__range=[start_date, end_date]
    ).annotate(
        completion_duration=ExpressionWrapper(
            F('data_finalizacao') - F('data_atribuicao'),
            output_field=fields.DurationField()
        )
    ).aggregate(
        avg_time=Avg('completion_duration')
    )['avg_time']
    
    # Converter para horas se não for None
    if avg_completion_time:
        avg_hours = avg_completion_time.total_seconds() / 3600
    else:
        avg_hours = 0
    
    # Tickets urgentes
    tickets_urgentes = Ticket.objects.filter(
        prioridade='URGENTE',
        status__in=['AGUARDANDO', 'INICIADO', 'CONTANDO'],
        data__range=[start_date, end_date]
    ).count()
    
    context = {
        'total_tickets': total_tickets,
        'tickets_aguardando': tickets_aguardando,
        'tickets_em_andamento': tickets_em_andamento,
        'tickets_finalizados': tickets_finalizados,
        'status_distribution': list(status_distribution),
        'priority_distribution': list(priority_distribution),
        'turno_distribution': list(turno_distribution),
        'top_pesquisadores': top_pesquisadores,
        'top_coordenadores': top_coordenadores,
        'daily_evolution': daily_evolution,
        'manha_tickets': manha_tickets,
        'noite_tickets': noite_tickets,
        'avg_completion_hours': round(avg_hours, 1),
        'tickets_urgentes': tickets_urgentes,
        'start_date': start_date,
        'end_date': end_date,
        'days': days,
    }
    
    return render(request, 'tickets/dashboard.html', context)
