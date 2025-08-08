#!/usr/bin/env python3
"""
Script para testar o endpoint de enviar contagens
"""
import requests
import json
from datetime import datetime

# Configurações
BASE_URL = "http://localhost:8000"
ENDPOINT = "/contagens/get/"

# Dados de teste para enviar contagens
test_data = {
    "sessao": "Teste_Sessao_20250107_143000",  # Nome da sessão existente
    "usuario": "admin",
    "contagens": [
        {
            "veiculo": "Carro",
            "movimento": "N-S",
            "count": 15,
            "periodo": "08:00"
        },
        {
            "veiculo": "Caminhao",
            "movimento": "N-S", 
            "count": 3,
            "periodo": "08:00"
        },
        {
            "veiculo": "Moto",
            "movimento": "S-N",
            "count": 8,
            "periodo": "08:00"
        },
        {
            "veiculo": "Carro",
            "movimento": "E-O",
            "count": 12,
            "periodo": "08:15"
        }
    ]
}

def test_contagens():
    """Testa o endpoint de contagens"""
    url = BASE_URL + ENDPOINT
    
    print(f"🚀 Testando: {url}")
    print(f"📝 Dados enviados:")
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
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        print(f"💬 Response Body:")
        
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2, ensure_ascii=False))
        except:
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    test_contagens()