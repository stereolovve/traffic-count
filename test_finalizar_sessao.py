#!/usr/bin/env python3
"""
Script para testar o endpoint de finalizar sessão
"""
import requests
import json

# Configurações
BASE_URL = "http://localhost:8000"
ENDPOINT = "/contagens/finalizar-sessao/"

# Dados de teste para finalizar uma sessão (substitua pelo ID real)
test_data = {
    "sessao_id": 1  # Substitua pelo ID de uma sessão existente
}

def test_finalizar_sessao():
    """Testa o endpoint de finalizar sessão"""
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
    test_finalizar_sessao()