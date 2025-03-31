import logging
import httpx
from utils.config import API_URL

class DjangoService:
    def __init__(self, tokens):
        self.tokens = tokens
    
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.tokens['access']}" if self.tokens and 'access' in self.tokens else "",
            "Content-Type": "application/json"
        }

    async def send_session(self, session, details, username, is_active):
        """Envia os detalhes da sessão para o Django"""
        try:
            headers = self._get_headers()
            payload = {
                "sessao": session,
                "codigo": details.get("Código", ""),
                "ponto": details.get("Ponto", ""),
                "data": details.get("Data do Ponto", ""),
                "horario_inicio": details.get("HorarioInicio", ""),
                "usuario": username,
                "ativa": is_active,
                "movimentos": details.get("Movimentos", [])
            }

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{API_URL}/contagens/registrar-sessao/", 
                        json=payload, 
                        headers=headers
                    )

                if response.status_code in [200, 201]:
                    logging.info("✅ Detalhes da sessão enviados ao Django com sucesso!")
                    return True
                else:
                    logging.error(f"❌ Falha ao enviar detalhes da sessão: {response.text}")
                    return False
            except httpx.TimeoutException:
                logging.error("⏱️ Timeout ao comunicar com o Django. Continuando localmente.")
                return False

        except Exception as ex:
            logging.error(f"[ERROR] ao enviar detalhes da sessão: {ex}")
            return False

    async def send_counts(self, session, username, counts, current_time):
        """Envia as contagens para o Django"""
        try:
            headers = self._get_headers()
            counts_list = [
                {"veiculo": veiculo, "movimento": movimento, "count": count}
                for (veiculo, movimento), count in counts.items()
            ]

            payload = {
                "sessao": session,
                "usuario": username,
                "contagens": counts_list,
                "current_timeslot": current_time
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{API_URL}/contagens/get/", json=payload, headers=headers)
                return response.status_code == 201

        except Exception as ex:
            logging.error(f"❌ Erro ao enviar contagens para Django: {ex}")
            return False

    async def end_session(self, session):
        """Finaliza a sessão no Django"""
        try:
            if not session:
                logging.error("Não é possível finalizar sessão: ID da sessão está vazio")
                return False
            
            headers = self._get_headers()
            payload = {"sessao": session, "ativa": False}
            
            logging.info(f"Tentando finalizar sessão {session} no Django...")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{API_URL}/contagens/finalizar-sessao/",
                    headers=headers,
                    json=payload
                )
            
            if response.status_code == 404:
                logging.warning(f"A sessão {session} não foi encontrada no Django. A finalização local ainda será realizada.")
                return False
            elif response.status_code == 200:
                logging.info(f"Sessão {session} finalizada no Django com sucesso!")
                return True
            else:
                logging.error(f"Falha ao finalizar sessão no Django: {response.status_code} - {response.text}")
                return False

        except Exception as ex:
            logging.error(f"Erro ao finalizar sessão no Django: {ex}")
            return False 