# utils/api.py
import httpx
import asyncio
import logging

logging.getLogger(__name__).setLevel(logging.ERROR)

async def async_api_request(url: str, method: str = "GET", json_data=None, headers: dict = None) -> dict:

    if not isinstance(method, str):
        logging.error(f"[ERROR] Parâmetro 'method' deve ser string, recebido: {method}, Tipo: {type(method)}")
        method = "GET"  

    method = method.upper()
    headers = headers or {}

    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method in ["POST", "PUT"]:
                response = await client.request(method, url, json=json_data, headers=headers)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                logging.error(f"[API ERROR] Método HTTP '{method}' não suportado.")
                return {"error": f"Método '{method}' não suportado"}

            response.raise_for_status()
            return response.json()  

        except httpx.HTTPStatusError as ex:
            logging.error(f"[API ERROR] HTTP Error - Status: {ex.response.status_code}, Body: {ex.response.text}")
            return {"error": f"HTTP Error {ex.response.status_code}", "details": ex.response.text}
        except httpx.RequestError as ex:
            logging.error(f"[API ERROR] Request Error: {ex}")
            return {"error": "Request Error", "details": str(ex)}
        except Exception as ex:
            logging.error(f"[API ERROR] Unexpected Error: {ex}")
            return {"error": "Unexpected Error", "details": str(ex)}
