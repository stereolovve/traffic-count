# utils/api.py
import httpx
import asyncio
import logging

# Configura o nível de log
logging.getLogger(__name__).setLevel(logging.ERROR)

async def async_api_request(url: str, method: str = "GET", json_data=None, headers: dict = None) -> dict | list:
    """
    Realiza uma requisição assíncrona à API e retorna o resultado em JSON.
    Em caso de erro, retorna um dicionário com detalhes do erro ou uma lista vazia para métodos GET.

    Args:
        url (str): URL da API.
        method (str): Método HTTP (GET, POST, PUT, DELETE).
        json_data (dict, optional): Dados a serem enviados no corpo da requisição.
        headers (dict, optional): Cabeçalhos HTTP.

    Returns:
        dict | list: Resposta JSON da API ou valor padrão em caso de erro.
    """
    if not isinstance(method, str):
        logging.error(f"[ERROR] Parâmetro 'method' deve ser string, recebido: {method}, Tipo: {type(method)}")
        method = "GET"  # Força o método para GET se inválido

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

            # Levanta uma exceção se o status não for 2xx
            response.raise_for_status()

            # Retorna a resposta JSON
            json_response = response.json()
            logging.debug(f"[API DEBUG] Resposta bem-sucedida para {url}: {json_response}")
            return json_response

        except httpx.HTTPStatusError as ex:
            error_msg = f"HTTP Error {ex.response.status_code}"
            logging.error(f"[API ERROR] {error_msg} - URL: {url}, Body: {ex.response.text}")
            # Para GET, retorna lista vazia; para outros métodos, retorna dict com erro
            return [] if method == "GET" else {"error": error_msg, "details": ex.response.text}

        except httpx.RequestError as ex:
            error_msg = "Falha na requisição à API"
            logging.error(f"[API ERROR] {error_msg} - URL: {url}, Detalhes: {ex}")
            return [] if method == "GET" else {"error": error_msg, "details": str(ex)}

        except ValueError as ex:
            # Caso o response.json() falhe (ex.: resposta não é JSON)
            error_msg = "Resposta inválida da API (não é JSON)"
            logging.error(f"[API ERROR] {error_msg} - URL: {url}, Detalhes: {ex}")
            return [] if method == "GET" else {"error": error_msg, "details": str(ex)}

        except Exception as ex:
            error_msg = "Erro inesperado na requisição"
            logging.error(f"[API ERROR] {error_msg} - URL: {url}, Detalhes: {ex}")
            return [] if method == "GET" else {"error": error_msg, "details": str(ex)}