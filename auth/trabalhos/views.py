#trabalhos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from .models import Cliente, Codigo, Ponto, PontoDetail, PontoDetailImage
from .serializers import ClienteSerializer, CodigoSerializer, PontoSerializer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated
from .forms import PontoDetailForm

def trabalho_list(request):
    cliente_id = request.GET.get('cliente_id')
    codigo_id = request.GET.get('codigo_id')
    
    clientes = Cliente.objects.filter().order_by('nome')
    cliente = None
    codigo = None
    codigos = []
    pontos = []
    
    if cliente_id:
        cliente = get_object_or_404(Cliente, id=cliente_id)
        codigos = Codigo.objects.filter(cliente=cliente).order_by('codigo')
        
        if codigo_id:
            codigo = get_object_or_404(Codigo, id=codigo_id)
            pontos = Ponto.objects.filter(codigo=codigo).order_by('nome')
    
    context = {
        'clientes': clientes,
        'cliente': cliente,
        'codigo': codigo,
        'codigos': codigos,
        'pontos': pontos,
    }
    
    return render(request, 'trabalhos/trabalho_list.html', context)

def cliente_create(request):
    if request.method == 'POST':
        print("Recebendo requisição POST para criar cliente")
        print("Dados recebidos:", request.POST)
        nome = request.POST.get('nome')
        print("Nome do cliente:", nome)
        if nome:
            Cliente.objects.create(nome=nome)
            messages.success(request, 'Cliente criado com sucesso!')
            print("Cliente criado com sucesso")
        else:
            messages.error(request, 'Nome do cliente é obrigatório!')
            print("Erro: Nome do cliente é obrigatório")
    return redirect('trabalho_list')

def cliente_edit(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    return JsonResponse({
        'id': cliente.id,
        'nome': cliente.nome
    })

def cliente_update(request, pk):
    if request.method == 'POST':
        cliente = get_object_or_404(Cliente, pk=pk)
        nome = request.POST.get('nome')
        if nome:
            cliente.nome = nome
            cliente.save()
            messages.success(request, 'Cliente atualizado com sucesso!')
        else:
            messages.error(request, 'Nome do cliente é obrigatório!')
    return redirect('trabalho_list')

def cliente_delete(request, pk):
    if request.method == 'POST':
        cliente = get_object_or_404(Cliente, pk=pk)
        cliente.delete()
        messages.success(request, 'Cliente excluído com sucesso!')
    return redirect('trabalho_list')

def codigo_create(request):
    if request.method == 'POST':
        codigo = request.POST.get('codigo')
        cliente_id = request.POST.get('cliente_id')
        descricao = request.POST.get('descricao')
        
        if codigo and cliente_id:
            cliente = get_object_or_404(Cliente, id=cliente_id)
            Codigo.objects.create(
                codigo=codigo,
                cliente=cliente,
                descricao=descricao
            )
            messages.success(request, 'Código criado com sucesso!')
        else:
            messages.error(request, 'Código e cliente são obrigatórios!')
    return redirect('trabalho_list')

def codigo_edit(request, pk):
    codigo = get_object_or_404(Codigo, pk=pk)
    return JsonResponse({
        'id': codigo.id,
        'codigo': codigo.codigo,
        'descricao': codigo.descricao
    })

def codigo_update(request, pk):
    if request.method == 'POST':
        codigo_obj = get_object_or_404(Codigo, pk=pk)
        codigo = request.POST.get('codigo')
        descricao = request.POST.get('descricao')
        
        if codigo:
            codigo_obj.codigo = codigo
            codigo_obj.descricao = descricao
            codigo_obj.save()
            messages.success(request, 'Código atualizado com sucesso!')
        else:
            messages.error(request, 'Código é obrigatório!')
    return redirect('trabalho_list')

def codigo_delete(request, pk):
    if request.method == 'POST':
        codigo = get_object_or_404(Codigo, pk=pk)
        codigo.delete()
        messages.success(request, 'Código excluído com sucesso!')
    return redirect('trabalho_list')

@login_required
def ponto_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        codigo_id = request.POST.get('codigo_id')
        localizacao = request.POST.get('localizacao')
        
        if nome and codigo_id:
            codigo = get_object_or_404(Codigo, id=codigo_id)
            Ponto.objects.create(
                nome=nome,
                codigo=codigo,
                localizacao=localizacao
            )
            messages.success(request, 'Ponto criado com sucesso!')
        else:
            messages.error(request, 'Nome e código são obrigatórios!')
    return redirect('trabalho_list')

def ponto_edit(request, pk):
    ponto = get_object_or_404(Ponto, pk=pk)
    return JsonResponse({
        'id': ponto.id,
        'nome': ponto.nome,
        'localizacao': ponto.localizacao
    })

def ponto_update(request, pk):
    if request.method == 'POST':
        ponto = get_object_or_404(Ponto, pk=pk)
        nome = request.POST.get('nome')
        localizacao = request.POST.get('localizacao')
        
        if nome:
            ponto.nome = nome
            ponto.localizacao = localizacao
            ponto.save()
            messages.success(request, 'Ponto atualizado com sucesso!')
        else:
            messages.error(request, 'Nome do ponto é obrigatório!')
    return redirect('trabalho_list')

def ponto_delete(request, pk):
    if request.method == 'POST':
        ponto = get_object_or_404(Ponto, pk=pk)
        ponto.delete()
        messages.success(request, 'Ponto excluído com sucesso!')
    return redirect('trabalho_list')

def ponto_detail(request, pk):
    ponto = get_object_or_404(Ponto, pk=pk)
    if request.method == 'POST':
        form_type = request.POST.get('form_type', '')
        
        if form_type == 'movimento':
            # Processar formulário de movimento
            movimento = request.POST.get('movimento', '')
            if movimento:
                detail = PontoDetail.objects.create(ponto=ponto, movimento=movimento)
                messages.success(request, "Movimento salvo com sucesso!")
            else:
                messages.error(request, "Por favor, informe a descrição do movimento.")
        
        elif form_type == 'observacao':
            # Processar formulário de observação
            observacao = request.POST.get('observacao', '')
            if observacao:
                detail = PontoDetail.objects.create(ponto=ponto, observacao=observacao)
                messages.success(request, "Observação salva com sucesso!")
            else:
                messages.error(request, "Por favor, informe a observação.")
        
        elif form_type == 'croqui':
            # Processar formulário de croqui
            if 'imagens' in request.FILES:
                detail = PontoDetail.objects.create(ponto=ponto)
                for f in request.FILES.getlist('imagens'):
                    PontoDetailImage.objects.create(detail=detail, image=f)
                messages.success(request, "Croquis salvos com sucesso!")
            else:
                messages.error(request, "Por favor, selecione pelo menos um arquivo.")
        
        else:
            # Processar formulário padrão (compatibilidade com versão anterior)
            form = PontoDetailForm(request.POST, request.FILES)
            if form.is_valid():
                movimento = form.cleaned_data['movimento']
                observacao = form.cleaned_data['observacao']
                detail = PontoDetail.objects.create(ponto=ponto, movimento=movimento, observacao=observacao)
                for f in request.FILES.getlist('imagens'):
                    PontoDetailImage.objects.create(detail=detail, image=f)
                messages.success(request, "Detalhe salvo com sucesso!")
        
        return redirect('ponto_detail', pk=pk)
    else:
        form = PontoDetailForm()
    
    # prefetch images to display thumbnails
    details = ponto.details.prefetch_related('images').all().order_by('-created_at')
    return render(request, 'trabalhos/ponto_detail.html', {
        'ponto': ponto,
        'form': form,
        'details': details,
    })

@login_required
def ponto_detail_add_images(request, pk, detail_id):
    ponto = get_object_or_404(Ponto, pk=pk)
    detail = get_object_or_404(PontoDetail, pk=detail_id, ponto=ponto)
    if request.method == 'POST':
        for f in request.FILES.getlist('imagens'):
            PontoDetailImage.objects.create(detail=detail, image=f)
        messages.success(request, "Imagens adicionadas ao detalhe com sucesso!")
    return redirect('ponto_detail', pk=pk)

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

class CodigoViewSet(viewsets.ModelViewSet):
    queryset = Codigo.objects.all()
    serializer_class = CodigoSerializer

class PontoViewSet(viewsets.ModelViewSet):
    queryset = Ponto.objects.all()
    serializer_class = PontoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['codigo']

@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def bulk_create_pontos(request):
    try:
        data = request.data
        quantity = int(data.get('quantity', 1))
        prefix = data.get('prefix', '')
        suffix = data.get('suffix', '')
        start_number = int(data.get('startNumber', 1))
        digits = int(data.get('digits', 3))
        codigo_id = data.get('codigo_id')

        if not codigo_id:
            return Response({'message': 'Código é obrigatório'}, status=400)

        try:
            codigo = Codigo.objects.get(id=codigo_id)
        except Codigo.DoesNotExist:
            return Response({'message': 'Código não encontrado'}, status=404)

        pontos = []
        for i in range(quantity):
            number = start_number + i
            formatted_number = str(number).zfill(digits)
            nome = f"{prefix}{formatted_number}{suffix}"
            
            # Verifica se já existe um ponto com este nome
            if Ponto.objects.filter(nome=nome, codigo=codigo).exists():
                return Response({
                    'message': f'Já existe um ponto com o nome {nome}'
                }, status=400)
            
            ponto = Ponto(
                nome=nome,
                codigo=codigo
            )
            pontos.append(ponto)

        # Criar todos os pontos de uma vez
        Ponto.objects.bulk_create(pontos)
        
        return Response({
            'message': f'{quantity} pontos criados com sucesso'
        }, status=201)

    except ValueError as e:
        return Response({'message': f'Erro de validação: {str(e)}'}, status=400)
    except Exception as e:
        return Response({'message': f'Erro ao criar pontos: {str(e)}'}, status=400)
