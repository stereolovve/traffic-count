# utils/api.py
import httpx
import asyncio
import logging

logging.getLogger(__name__).setLevel(logging.ERROR)

async def async_api_request(url: str, method: str = "GET", json_data=None, headers: dict = None) -> dict | list:

    if not isinstance(method, str):
        logging.error(f"[ERROR] Parâmetro 'method' deve ser string, recebido: {method}, Tipo: {type(method)}")
        method = "GET" 

    method = method.upper()
    headers = headers or {}

    async with httpx.AsyncClient() as client:
        try:
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
            logging.debug(f"[API DEBUG] Resposta bem-sucedida para {url}: {json_response}")
            return json_response

        except httpx.HTTPStatusError as ex:
            error_msg = f"HTTP Error {ex.response.status_code}"
            logging.error(f"[API ERROR] {error_msg} - URL: {url}, Body: {ex.response.text}")
            return [] if method == "GET" else {"error": error_msg, "details": ex.response.text}

        except httpx.RequestError as ex:
            error_msg = "Falha na requisição à API"
            logging.error(f"[API ERROR] {error_msg} - URL: {url}, Detalhes: {ex}")
            return [] if method == "GET" else {"error": error_msg, "details": str(ex)}

        except ValueError as ex:
            error_msg = "Resposta inválida da API (não é JSON)"
            logging.error(f"[API ERROR] {error_msg} - URL: {url}, Detalhes: {ex}")
            return [] if method == "GET" else {"error": error_msg, "details": str(ex)}

        except Exception as ex:
            error_msg = "Erro inesperado na requisição"
            logging.error(f"[API ERROR] {error_msg} - URL: {url}, Detalhes: {ex}")
            return [] if method == "GET" else {"error": error_msg, "details": str(ex)}