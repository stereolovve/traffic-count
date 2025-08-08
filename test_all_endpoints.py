#!/usr/bin/env python3
"""
Script completo para testar todos os endpoints da API
"""
import requests
import json
from datetime import datetime
import time

# Configurações
BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, endpoint, data=None, params=None):
    """Testa um endpoint genérico"""
    url = BASE_URL + endpoint
    print(f"\n{'='*60}")
    print(f"[TESTE] {name}")
    print(f"[URL] {method} {url}")
    
    if data:
        print(f"[DATA] {json.dumps(data, indent=2, ensure_ascii=False)}")
    if params:
        print(f"[PARAMS] {params}")
    
    try:
        if method == 'GET':
            response = requests.get(url, params=params, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'}, timeout=10)
        
        print(f"[STATUS] {response.status_code}")
        
        try:
            response_json = response.json()
            print(f"[RESPONSE] {json.dumps(response_json, indent=2, ensure_ascii=False)}")
            return response_json
        except:
            print(f"[RESPONSE] {response.text[:500]}...")
            return response.text
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Erro na requisicao: {e}")
        return None

def run_complete_test():
    """Executa uma bateria completa de testes"""
    timestamp = int(time.time())
    session_name = f"Teste_Completo_{timestamp}"
    
    print("Iniciando testes completos da API...")
    print(f"Session Name: {session_name}")
    
    # 1. Criar uma sessão
    session_data = {
        "sessao": session_name,
        "codigo": "TEST789",
        "ponto": "Ponto Teste Completo",
        "data": datetime.now().strftime("%Y-%m-%d"),
        "horario_inicio": "09:00",
        "horario_fim": "17:00",
        "usuario": "lucas.melo",
        "status": "Em andamento",
        "movimentos": ["N-S", "S-N", "E-O", "O-E"],
        "padrao": "Teste Completo"
    }
    
    session_response = test_endpoint(
        "1. Registrar Sessao", 
        "POST", 
        "/contagens/registrar-sessao/", 
        session_data
    )
    
    if not session_response or 'id' not in session_response:
        print("[ERROR] Falha ao criar sessao, interrompendo testes")
        return
    
    session_id = session_response['id']
    print(f"[INFO] Sessao criada com ID: {session_id}")
    
    # 2. Buscar sessão por nome
    test_endpoint(
        "2. Buscar Sessao por Nome",
        "GET",
        "/contagens/buscar-sessao/",
        params={"nome": session_name}
    )
    
    # 3. Enviar contagens
    contagens_data = {
        "sessao": session_name,
        "usuario": "lucas.melo",
        "contagens": [
            {"veiculo": "Carro", "movimento": "N-S", "count": 25, "periodo": "09:00"},
            {"veiculo": "Caminhao", "movimento": "N-S", "count": 5, "periodo": "09:00"},
            {"veiculo": "Moto", "movimento": "S-N", "count": 12, "periodo": "09:00"},
            {"veiculo": "Carro", "movimento": "E-O", "count": 18, "periodo": "09:15"},
            {"veiculo": "Onibus", "movimento": "O-E", "count": 3, "periodo": "09:15"}
        ]
    }
    
    test_endpoint(
        "3. Enviar Contagens",
        "POST",
        "/contagens/get/",
        contagens_data
    )
    
    # 4. Atualizar contagens
    update_data = {
        "sessao": session_name,
        "usuario": "lucas.melo",
        "contagens": [
            {"veiculo": "Carro", "movimento": "N-S", "count": 30, "periodo": "09:00"},  # Atualizado
            {"veiculo": "Caminhao", "movimento": "N-S", "count": 7, "periodo": "09:00"},  # Atualizado
            {"veiculo": "Bicicleta", "movimento": "S-N", "count": 8, "periodo": "09:30"}  # Novo
        ]
    }
    
    test_endpoint(
        "4. Atualizar Contagens",
        "POST",
        "/contagens/atualizar-contagens/",
        update_data
    )
    
    # 5. Finalizar sessão por ID
    test_endpoint(
        "5. Finalizar Sessao por ID",
        "POST",
        "/contagens/finalizar-sessao/",
        {"sessao_id": session_id}
    )
    
    # 6. Verificar se foi finalizada
    test_endpoint(
        "6. Verificar Status Final",
        "GET",
        "/contagens/buscar-sessao/",
        params={"nome": session_name}
    )
    
    print(f"\n{'='*60}")
    print("[SUCESSO] Todos os testes concluidos!")
    print(f"[INFO] Session ID criada: {session_id}")
    print(f"[INFO] Session Name: {session_name}")

if __name__ == "__main__":
    run_complete_test()