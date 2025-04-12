# utils/api.py
import httpx
import asyncio
import logging
import json
from functools import lru_cache
from typing import Optional, Dict, Any
import aiohttp
from datetime import datetime
from .config import API_URL

# Configurar logging apenas para erros críticos
logging.getLogger(__name__).setLevel(logging.ERROR)

# Cache apenas para token de autenticação
@lru_cache(maxsize=1)
def get_auth_token() -> Optional[str]:
    try:
        with open("tokens.json", "r") as f:
            tokens = json.load(f)
            return tokens.get("access")
    except:
        return None

async def async_api_request(method, endpoint, data=None, headers=None):
    """Faz uma requisição assíncrona para a API."""
    if headers is None:
        headers = {}
    
    # Adiciona headers padrão
    headers.update({
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=f"{API_URL}{endpoint}",
                json=data,
                headers=headers
            ) as response:
                # Trata diferentes códigos de status
                if response.status in [200, 201]:  # Sucesso
                    return await response.json()
                elif response.status == 400:  # Bad Request
                    error_text = await response.text()
                    logging.error(f"Erro na requisição (400): {error_text}")
                    return {"erro": f"Erro na requisição: {error_text}"}
                elif response.status == 401:  # Unauthorized
                    logging.error("Erro de autenticação (401)")
                    return {"erro": "Erro de autenticação"}
                elif response.status == 404:  # Not Found
                    logging.error("Recurso não encontrado (404)")
                    return {"erro": "Recurso não encontrado"}
                else:  # Outros erros
                    error_text = await response.text()
                    logging.error(f"Erro na requisição ({response.status}): {error_text}")
                    return {"erro": f"Erro na requisição: {error_text}"}
    except Exception as e:
        logging.error(f"Erro na requisição: {str(e)}")
        return {"erro": str(e)}

async def parallel_requests(urls, headers=None):
    """
    Faz múltiplas requisições em paralelo
    """
    async with httpx.AsyncClient() as client:
        tasks = []
        for url in urls:
            tasks.append(client.get(url, headers=headers))
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]