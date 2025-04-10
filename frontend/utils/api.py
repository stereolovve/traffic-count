# utils/api.py
import httpx
import asyncio
import logging
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from .cache import cache

logging.getLogger(__name__).setLevel(logging.ERROR)

class APICache:
    def __init__(self, cache_dir=".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_duration = timedelta(hours=1)  # Cache válido por 1 hora

    def _get_cache_path(self, key):
        return self.cache_dir / f"{key}.json"

    def get(self, key):
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                cache_time = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - cache_time > self.cache_duration:
                    return None
                return data['value']
        except:
            return None

    def set(self, key, value):
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'value': value
                }, f)
        except:
            pass

# Instância global do cache
cache = APICache()

async def async_api_request(url: str, method: str = "GET", json_data=None, headers: dict = None, use_cache=False, cache_key=None) -> dict | list:
    """
    Faz uma requisição à API com retry automático e cache opcional
    """
    if use_cache and cache_key:
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

    if not isinstance(method, str):
        logging.error(f"[ERROR] Parâmetro 'method' deve ser string, recebido: {method}, Tipo: {type(method)}")
        method = "GET" 

    method = method.upper()
    headers = headers or {}

    max_retries = 3
    base_delay = 1  # segundos

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, json=json_data, headers=headers)
                elif method == "PUT":
                    response = await client.put(url, json=json_data, headers=headers)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    logging.error(f"[API ERROR] Método HTTP '{method}' não suportado.")
                    return {"error": f"Método '{method}' não suportado"}

                response.raise_for_status()
                json_response = response.json()

                if use_cache and cache_key:
                    cache.set(cache_key, json_response)

                logging.debug(f"[API DEBUG] Resposta bem-sucedida para {url}: {json_response}")
                return json_response

        except httpx.HTTPStatusError as ex:
            if attempt == max_retries - 1:
                error_msg = f"HTTP Error {ex.response.status_code}"
                logging.error(f"[API ERROR] {error_msg} - URL: {url}, Body: {ex.response.text}")
                return [] if method == "GET" else {"error": error_msg, "details": ex.response.text}
            delay = base_delay * (2 ** attempt)
            logging.warning(f"Tentativa {attempt + 1} falhou. Tentando novamente em {delay} segundos...")
            await asyncio.sleep(delay)

        except httpx.RequestError as ex:
            if attempt == max_retries - 1:
                error_msg = "Falha na requisição à API"
                logging.error(f"[API ERROR] {error_msg} - URL: {url}, Detalhes: {ex}")
                return [] if method == "GET" else {"error": error_msg, "details": str(ex)}
            delay = base_delay * (2 ** attempt)
            logging.warning(f"Tentativa {attempt + 1} falhou. Tentando novamente em {delay} segundos...")
            await asyncio.sleep(delay)

        except ValueError as ex:
            if attempt == max_retries - 1:
                error_msg = "Resposta inválida da API (não é JSON)"
                logging.error(f"[API ERROR] {error_msg} - URL: {url}, Detalhes: {ex}")
                return [] if method == "GET" else {"error": error_msg, "details": str(ex)}
            delay = base_delay * (2 ** attempt)
            logging.warning(f"Tentativa {attempt + 1} falhou. Tentando novamente em {delay} segundos...")
            await asyncio.sleep(delay)

        except Exception as ex:
            if attempt == max_retries - 1:
                error_msg = "Erro inesperado na requisição"
                logging.error(f"[API ERROR] {error_msg} - URL: {url}, Detalhes: {ex}")
                return [] if method == "GET" else {"error": error_msg, "details": str(ex)}
            delay = base_delay * (2 ** attempt)
            logging.warning(f"Tentativa {attempt + 1} falhou. Tentando novamente em {delay} segundos...")
            await asyncio.sleep(delay)

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