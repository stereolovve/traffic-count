#auth/contagens/views.py
from django.shortcuts import render, get_object_or_404
from .models import Session, Counting
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from collections import defaultdict
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta

User = get_user_model()

def listar_sessoes(request):
    status = request.GET.get("status")
    pesquisador = request.GET.get("usuario")

    sessoes = Session.objects.all().select_related('criado_por')

    if status == "ativas":
        sessoes = sessoes.filter(ativa=True)
    elif status == "finalizadas":
        sessoes = sessoes.filter(ativa=False)

    if pesquisador:
        sessoes = sessoes.filter(criado_por__username__icontains=pesquisador)

    sessoes_com_movimentos = []
    for sessao in sessoes:
        movimentos = sessao.movimentos if sessao.movimentos else []
        sessoes_com_movimentos.append({
            "sessao": sessao,
            "movimentos": list(movimentos),
            "sessao_id": sessao.id
        })

    return render(request, 'contagens/sessoes.html', {"sessoes": sessoes_com_movimentos})


def detalhes_sessao(request, sessao_id):
    sessao = get_object_or_404(Session, id=sessao_id)
    contagens = Counting.objects.filter(sessao=sessao).order_by("id")

    if not contagens.exists():
        return render(request, 'contagens/detalhes_sessao.html', {
            "sessao": sessao,
            "dados_sessao": {},
            "veiculos": [],
            "erro": "Nenhuma contagem registrada para esta sessão."
        })

    try:
        movimentos = sorted(set(contagem.movimento for contagem in contagens))
        
        # Obtenha também movimentos da sessão que ainda não têm contagens
        if sessao.movimentos:
            movimentos = sorted(set(movimentos) | set(sessao.movimentos))
            
        veiculos = sorted(set(contagem.veiculo for contagem in contagens))

        if not movimentos:
            return render(request, 'contagens/detalhes_sessao.html', {
                "sessao": sessao,
                "dados_sessao": {},
                "veiculos": [],
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
                for veiculo in veiculos:
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
                
                # Se não há contagens com período explícito, usar a lógica antiga
                if not contagens_periodo.exists():
                    contagens_movimento = {veiculo: 0 for veiculo in veiculos}
                else:
                    contagens_movimento = {
                        contagem.veiculo: contagem.contagem 
                        for contagem in contagens_periodo
                    }
                    
                    # Garantir que todos os veículos estejam representados
                    for veiculo in veiculos:
                        if veiculo not in contagens_movimento:
                            contagens_movimento[veiculo] = 0
                
                dados_sessao[movimento].append({
                    "das": periodo,
                    "as": periodo_fim,
                    "observacao": "Nenhuma",
                    "contagens": contagens_movimento
                })
        
        return render(request, 'contagens/detalhes_sessao.html', {
            "sessao": sessao,
            "dados_sessao": dict(dados_sessao),
            "veiculos": veiculos
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

def finalizar_sessao(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            nome_sessao = data.get("sessao")
            ativa = data.get("ativa")

            if nome_sessao is None or ativa is None:
                return JsonResponse({"erro": "Campos obrigatórios ausentes"}, status=400)

            sessao = Session.objects.filter(sessao=nome_sessao).first()
            if not sessao:
                return JsonResponse({"erro": "Sessão não encontrada"}, status=404)

            sessao.ativa = bool(ativa)
            sessao.save()

            return JsonResponse({"mensagem": "Sessão atualizada com sucesso"})

        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=500)
    else:
        return JsonResponse({"erro": "Método não permitido"}, status=405)

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
