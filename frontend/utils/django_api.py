import httpx
import logging
from utils.config import API_URL

async def send_session_to_django(session_name, details, username, is_active, token):
    try:
        headers = {
            "Authorization": f"Bearer {token}" if token else "",
            "Content-Type": "application/json"
        }

        payload = {
            "sessao": session_name,
            "codigo": details.get("Código"),
            "ponto": details.get("Ponto"),
            "data": details.get("Data do Ponto"),
            "horario_inicio": details.get("HorarioInicio"),
            "usuario": username,
            "ativa": is_active
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{API_URL}/contagens/get/", json=payload, headers=headers)

        if response.status_code in [200, 201]:
            logging.info("✅ Sessão criada ou atualizada no Django com sucesso.")
        else:
            logging.error(f"❌ Erro ao enviar detalhes da sessão: {response.text}")

    except Exception as ex:
        logging.error(f"❌ Erro ao enviar metadados da sessão para Django: {ex}")


async def send_count_to_django(session_name, contagens, username, is_active, details, token):
    try:
        headers = {
            "Authorization": f"Bearer {token}" if token else "",
            "Content-Type": "application/json"
        }

        payload = {
            "sessao": session_name,
            "codigo": details.get("Código"),
            "ponto": details.get("Ponto"),
            "data": details.get("Data do Ponto"),
            "horario_inicio": details.get("HorarioInicio"),
            "usuario": username,
            "ativa": is_active,
            "contagens": contagens
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{API_URL}/contagens/get/", json=payload, headers=headers)

        if response.status_code == 201:
            logging.info("✅ Contagens enviadas com sucesso!")
        else:
            logging.error(f"❌ Erro ao enviar contagens: {response.text}")

    except Exception as ex:
        logging.error(f"❌ Erro ao enviar contagens para o Django: {ex}")


async def send_status_to_django(session_name, token):
    try:
        headers = {
            "Authorization": f"Bearer {token}" if token else "",
            "Content-Type": "application/json"
        }

        payload = {
            "sessao": session_name,
            "ativa": False
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{API_URL}/contagens/finalizar-sessao/", json=payload, headers=headers)

        if response.status_code == 200:
            logging.info("✅ Sessão finalizada no Django.")
        else:
            logging.error(f"❌ Erro ao finalizar sessão no Django: {response.text}")

    except Exception as ex:
        logging.error(f"❌ Exceção ao finalizar sessão: {ex}")
