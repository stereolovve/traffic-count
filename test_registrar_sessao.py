#!/usr/bin/env python3
"""
Script para testar o endpoint de registrar sessão
"""
import requests
import json
from datetime import datetime

# Configurações
BASE_URL = "http://localhost:8000"
ENDPOINT = "/contagens/registrar-sessao/"

# Dados de teste para registrar uma nova sessão
test_data = {
    "sessao": f"Teste_Sessao_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    "codigo": "COD123",
    "ponto": "Ponto Teste A",
    "data": datetime.now().strftime("%Y-%m-%d"),
    "horario_inicio": "08:00",
    "horario_fim": "12:00",
    "usuario": "lucas.melo",  # Usuario existente no sistema
    "status": "Em andamento",
    "movimentos": ["N-S", "S-N", "E-O", "O-E"],
    "padrao": "Padrão Teste"
}

def test_registrar_sessao():
    """Testa o endpoint de registrar sessão"""
    url = BASE_URL + ENDPOINT
    
    print(f"[TEST] Testando: {url}")
    print(f"[DATA] Dados enviados:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    print("-" * 50)
    
    try:
        response = requests.post(
            url,
            json=test_data,
            headers={
                'Content-Type': 'application/json'
            },
            timeout=10
        )
        
        print(f"[STATUS] Status Code: {response.status_code}")
        print(f"[HEADERS] Response Headers: {dict(response.headers)}")
        print(f"[RESPONSE] Response Body:")
        
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2, ensure_ascii=False))
        except:
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Erro na requisicao: {e}")
    except Exception as e:
        print(f"[ERROR] Erro inesperado: {e}")

if __name__ == "__main__":
    test_registrar_sessao()