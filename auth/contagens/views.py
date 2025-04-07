#auth/contagens/views.py
from django.shortcuts import render, get_object_or_404
from .models import Session, Counting
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
import json
from collections import defaultdict
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from padroes.models import PadraoContagem
import csv
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

User = get_user_model()

def listar_sessoes(request):
    # Get filter parameters
    status = request.GET.get("status")
    pesquisador = request.GET.get("usuario")
    codigo = request.GET.get("codigo")
    ponto = request.GET.get("ponto")
    data = request.GET.get("data")
    sort_field = request.GET.get("sort", "-id")

    # Get list of researchers (users who have created sessions)
    pesquisadores = User.objects.filter(
        id__in=Session.objects.values_list('criado_por', flat=True).distinct()
    ).order_by('username')

    # Get unique codes and points
    codigos = Session.objects.values_list('codigo', flat=True).distinct().order_by('codigo')
    pontos = Session.objects.values_list('ponto', flat=True).distinct().order_by('ponto')
    datas = Session.objects.values_list('data', flat=True).distinct().order_by('data')

    # Start with base queryset
    sessoes = Session.objects.all().select_related('criado_por')

    # Apply filters
    if status == "ativas":
        sessoes = sessoes.filter(ativa=True)
    elif status == "finalizadas":
        sessoes = sessoes.filter(ativa=False)

    if pesquisador:
        sessoes = sessoes.filter(criado_por__username__icontains=pesquisador)

    if codigo:
        sessoes = sessoes.filter(codigo__icontains=codigo)

    if ponto:
        sessoes = sessoes.filter(ponto__icontains=ponto)

    if data:
        sessoes = sessoes.filter(data__icontains=data)

    # Apply sorting
    if sort_field:
        # Handle special cases for sorting
        if sort_field == 'criado_por':
            sessoes = sessoes.order_by(f'criado_por__username{"" if sort_field[0] != "-" else ""}')
        else:
            sessoes = sessoes.order_by(sort_field)

    # Prepare the data for the template
    sessoes_com_movimentos = []
    for sessao in sessoes:
        movimentos = sessao.movimentos if sessao.movimentos else []
        sessoes_com_movimentos.append({
            "sessao": sessao,
            "movimentos": list(movimentos),
            "sessao_id": sessao.id
        })

    return render(request, 'contagens/sessoes.html', {
        "sessoes": sessoes_com_movimentos,
        "current_sort": sort_field,
        "pesquisadores": pesquisadores,
        "codigos": codigos,  # Add list of unique codes
        "pontos": pontos,    # Add list of unique points
        "datas": datas,
        "filtros_ativos": {
            "status": status,
            "pesquisador": pesquisador,
            "codigo": codigo,
            "ponto": ponto,
            "data": data
        }
    })


def detalhes_sessao(request, sessao_id):
    try:
        sessao = Session.objects.get(id=sessao_id)
    except Session.DoesNotExist:
        return render(request, 'contagens/detalhes_sessao.html', {'erro': 'Sessão não encontrada.'})
    
    try:
        # Obter apenas os padrões do tipo correto, na ordem correta
        padroes_ordenados = PadraoContagem.objects.filter(
            pattern_type="padrao_perplan"
        ).order_by('order')
        
        # Lista de veículos na ordem correta - será nossa única fonte de veículos
        veiculos_ordenados = [padrao.veiculo for padrao in padroes_ordenados]
        
        # Obter os dados da sessão
        contagens = Counting.objects.filter(sessao=sessao).order_by("id")
        
        if not contagens.exists():
            return render(request, 'contagens/detalhes_sessao.html', {
                "sessao": sessao,
                "dados_sessao": {},
                "veiculos": veiculos_ordenados,
                "erro": "Nenhuma contagem registrada para esta sessão."
            })

        try:
            movimentos = sorted(set(contagem.movimento for contagem in contagens))
            
            # Obtenha também movimentos da sessão que ainda não têm contagens
            if sessao.movimentos:
                movimentos = sorted(set(movimentos) | set(sessao.movimentos))

            if not movimentos:
                return render(request, 'contagens/detalhes_sessao.html', {
                    "sessao": sessao,
                    "dados_sessao": {},
                    "veiculos": veiculos_ordenados,
                    "erro": "Nenhum movimento registrado para esta sessão."
                })

            horario_inicio = datetime.strptime(sessao.horario_inicio, "%H:%M") if sessao.horario_inicio else datetime.strptime("00:00", "%H:%M")

            # Agrupar contagens por período explícito
            periodos_registrados = set()
            for contagem in contagens:
                if contagem.periodo:
                    periodos_registrados.add(contagem.periodo)
            
            # Se não houver períodos registrados, criar períodos a partir do horário de início
            if not periodos_registrados:
                # Determinar número de períodos baseado no número de contagens por movimento/veículo
                max_contagens_por_mov_veiculo = {}
                for mov in movimentos:
                    for veiculo in veiculos_ordenados:
                        count = Counting.objects.filter(
                            sessao=sessao, 
                            movimento=mov, 
                            veiculo=veiculo
                        ).count()
                        max_contagens_por_mov_veiculo[(mov, veiculo)] = count
                
                num_periodos = max(max_contagens_por_mov_veiculo.values(), default=1)
                
                for i in range(num_periodos):
                    periodo = (horario_inicio + timedelta(minutes=15 * i)).strftime("%H:%M")
                    periodos_registrados.add(periodo)
            
            # Organizar períodos em ordem cronológica
            periodos = sorted(periodos_registrados)
            
            # Organizar dados por movimento e período
            dados_sessao = defaultdict(list)
            
            for periodo in periodos:
                periodo_datetime = datetime.strptime(periodo, "%H:%M")
                periodo_fim = (periodo_datetime + timedelta(minutes=15)).strftime("%H:%M")
                
                for movimento in movimentos:
                    # Obter contagens para este movimento e período
                    contagens_periodo = Counting.objects.filter(
                        sessao=sessao,
                        movimento=movimento,
                        periodo=periodo
                    )
                    
                    # Inicializar contagens com 0 para todos os veículos dos padrões
                    contagens_movimento = {veiculo: 0 for veiculo in veiculos_ordenados}
                    
                    # Atualizar apenas os veículos que existem nos padrões
                    for contagem in contagens_periodo:
                        if contagem.veiculo in veiculos_ordenados:
                            contagens_movimento[contagem.veiculo] = contagem.contagem
                    
                    dados_sessao[movimento].append({
                        "das": periodo,
                        "as": periodo_fim,
                        "observacao": "Nenhuma",
                        "contagens": contagens_movimento
                    })

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return render(request, 'contagens/detalhes_sessao.html', {
                "sessao": sessao,
                "dados_sessao": {},
                "veiculos": veiculos_ordenados,
                "erro": f"Erro ao carregar os dados da sessão: {str(e)}"
            })

        return render(request, 'contagens/detalhes_sessao.html', {
            "sessao": sessao,
            "dados_sessao": dict(dados_sessao),
            "veiculos": veiculos_ordenados  # Usar sempre a lista original de veículos dos padrões
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return render(request, 'contagens/detalhes_sessao.html', {
            "sessao": sessao,
            "dados_sessao": {},
            "veiculos": [],
            "erro": f"Erro ao carregar os dados da sessão: {str(e)}"
        })

def get_countings(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            sessao_nome = data.get("sessao")
            username = data.get("usuario")
            contagens = data.get("contagens")
            periodo_atual = data.get("current_timeslot", None)  # Recupera o período atual se fornecido

            if not sessao_nome or not username or not contagens:
                return JsonResponse({"erro": "Dados obrigatórios ausentes"}, status=400)

            usuario = User.objects.filter(username=username).first()
            if not usuario:
                print("❌ Usuário não encontrado!")
                return JsonResponse({"erro": "Usuário não encontrado"}, status=404)

            # Recuperar sessão
            sessao = Session.objects.filter(sessao=sessao_nome).first()
            if not sessao:
                # Criar sessão se não existir (faltam campos, mas podemos criar uma básica)
                sessao = Session.objects.create(
                    sessao=sessao_nome,
                    criado_por=usuario,
                    ativa=True
                )

            if "ativa" in data:
                sessao.ativa = bool(data["ativa"])
                sessao.save()

            # IMPORTANTE: Não excluir contagens anteriores!
            # Verificar se já existem contagens para este período e sessão
            if periodo_atual:
                # Se um período foi especificado, podemos excluir apenas aquele período
                # para permitir correções no período atual
                Counting.objects.filter(
                    sessao=sessao, 
                    periodo=periodo_atual
                ).delete()
            
            # Agrupar contagens por movimento
            contagens_por_movimento = defaultdict(list)
            for item in contagens:
                contagens_por_movimento[item["movimento"]].append(item)
            
            # Processar contagens movimento por movimento
            for movimento, itens in contagens_por_movimento.items():
                for item in itens:
                    Counting.objects.create(
                        sessao=sessao,
                        veiculo=item["veiculo"],
                        movimento=movimento,
                        contagem=item["count"],
                        periodo=periodo_atual  # Salvar o período atual
                    )

            return JsonResponse({"mensagem": "Contagens salvas com sucesso!"}, status=201)

        except json.JSONDecodeError:
            print("❌ JSON inválido recebido!")
            return JsonResponse({"erro": "JSON inválido"}, status=400)
        except Exception as e:
            print(f"❌ Erro ao processar contagens: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return JsonResponse({"erro": f"Erro ao processar contagens: {str(e)}"}, status=500)

    return JsonResponse({"erro": "Método não permitido"}, status=405)

@csrf_exempt
@login_required
def finalizar_sessao(request):
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Método não permitido'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        sessao_id = data.get('sessao_id')
        
        if not sessao_id:
            return JsonResponse({
                'status': 'error',
                'message': 'ID da sessão não fornecido'
            }, status=400)
        
        sessao = get_object_or_404(Session, id=sessao_id)
        
        # Verificar se o usuário tem permissão para finalizar a sessão
        if sessao.criado_por != request.user and not request.user.is_staff:
            return JsonResponse({
                'status': 'error',
                'message': 'Você não tem permissão para finalizar esta sessão'
            }, status=403)
        
        if not sessao.ativa:
            return JsonResponse({
                'status': 'error',
                'message': 'Esta sessão já está finalizada'
            }, status=400)
        
        sessao.ativa = False
        sessao.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Sessão finalizada com sucesso'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Dados inválidos'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def exportar_csv(request, sessao_id):
    try:
        sessao = get_object_or_404(Session, id=sessao_id)
        
        # Verificar se o usuário tem permissão para exportar a sessão
        if sessao.criado_por != request.user and not request.user.is_staff:
            return HttpResponse('Você não tem permissão para exportar esta sessão', status=403)
        
        # Criar um novo workbook
        wb = openpyxl.Workbook()
        
        # Configurar estilos
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color='CCE5FF', end_color='CCE5FF', fill_type='solid')
        
        # Primeira aba - Detalhes da Sessão
        ws_info = wb.active
        ws_info.title = 'Detalhes da Sessão'
        
        # Adicionar informações da sessão
        info_headers = [
            ['ID da Sessão', sessao.id],
            ['Nome da Sessão', sessao.sessao],
            ['Código', sessao.codigo],
            ['Ponto', sessao.ponto],
            ['Data', sessao.data],
            ['Horário', sessao.horario_inicio],
            ['Status', 'Finalizada' if not sessao.ativa else 'Ativa'],
            ['Criado Por', sessao.criado_por.username],
            ['Email do Pesquisador', sessao.criado_por.email]
        ]
        
        for row_idx, (header, value) in enumerate(info_headers, 1):
            ws_info.cell(row=row_idx, column=1, value=header).font = header_font
            ws_info.cell(row=row_idx, column=2, value=value)
        
        # Ajustar largura das colunas
        ws_info.column_dimensions['A'].width = 20
        ws_info.column_dimensions['B'].width = 30
        
        # Obter contagens agrupadas por movimento
        contagens = Counting.objects.filter(sessao=sessao).order_by('periodo', 'movimento', 'veiculo')
        movimentos = sorted(set(c.movimento for c in contagens))
        
        # Para cada movimento, criar uma aba separada
        for movimento in movimentos:
            ws_mov = wb.create_sheet(f'Contagens - {movimento}')
            
            # Obter veículos únicos para este movimento
            veiculos = sorted(set(c.veiculo for c in contagens if c.movimento == movimento))
            
            # Escrever cabeçalho
            headers = ['Período'] + veiculos
            for col_idx, header in enumerate(headers, 1):
                cell = ws_mov.cell(row=1, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
            
            # Agrupar contagens por período
            periodos = defaultdict(lambda: defaultdict(int))
            for contagem in contagens:
                if contagem.movimento == movimento:
                    periodos[contagem.periodo][contagem.veiculo] = contagem.contagem
            
            # Escrever dados
            for row_idx, (periodo, contagens_periodo) in enumerate(sorted(periodos.items()), 2):
                ws_mov.cell(row=row_idx, column=1, value=periodo)
                for col_idx, veiculo in enumerate(veiculos, 2):
                    ws_mov.cell(row=row_idx, column=col_idx, value=contagens_periodo[veiculo])
            
            # Ajustar largura das colunas
            for col_idx, header in enumerate(headers, 1):
                ws_mov.column_dimensions[get_column_letter(col_idx)].width = max(15, len(header) + 2)
        
        # Criar resposta HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="sessao_{sessao_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        # Salvar o arquivo
        wb.save(response)
        return response
        
    except Exception as e:
        return HttpResponse(f'Erro ao exportar sessão: {str(e)}', status=500)

def registrar_sessao(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            sessao_nome = data.get("sessao")
            codigo = data.get("codigo")
            ponto = data.get("ponto")
            data_sessao = data.get("data")
            horario_inicio = data.get("horario_inicio")
            username = data.get("usuario")
            ativa = data.get("ativa", True) 
            movimentos = data.get("movimentos")

            if not all([sessao_nome, codigo, ponto, data_sessao, horario_inicio, username]):
                return JsonResponse({"erro": "Dados obrigatórios ausentes"}, status=400)

            usuario = User.objects.filter(username=username).first()
            if not usuario:
                return JsonResponse({"erro": "Usuário não encontrado"}, status=404)

            sessao, created = Session.objects.get_or_create(
                sessao=sessao_nome,
                defaults={
                    "codigo": codigo,
                    "ponto": ponto,
                    "data": data_sessao,
                    "horario_inicio": horario_inicio,
                    "criado_por": usuario,
                    "ativa": ativa,
                    "movimentos": movimentos,
                }
            )

            if not created:
                # Atualiza se já existe
                sessao.codigo = codigo
                sessao.ponto = ponto
                sessao.data = data_sessao
                sessao.horario_inicio = horario_inicio
                sessao.ativa = ativa
                sessao.movimentos = movimentos
                sessao.save()

            return JsonResponse({"mensagem": "Sessão registrada com sucesso"}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)
        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=500)
    else:
        return JsonResponse({"erro": "Método não permitido"}, status=405)
