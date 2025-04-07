import logging
import httpx
from utils.api import async_api_request
from utils.config import API_URL
from datetime import datetime

class ApiManager:
    def __init__(self, contador):
        self.contador = contador
        self.tokens = contador.tokens
        self.username = contador.username
        
    def _get_auth_headers(self):
        """Retorna os headers de autenticação padrão"""
        headers = {
            "Content-Type": "application/json"
        }
        if self.tokens and 'access' in self.tokens:
            headers["Authorization"] = f"Bearer {self.tokens['access']}"
        return headers

    async def api_get(self, url):
        """Método genérico para requisições GET"""
        try:
            return await async_api_request(
                url=url, 
                method="GET", 
                headers=self._get_auth_headers()
            )
        except Exception as ex:
            logging.error(f"Erro na requisição GET para {url}: {ex}")
            return None

    async def send_session_to_django(self):
        """Envia os detalhes da sessão para o Django"""
        try:
            if not self.contador.sessao:
                logging.error("❌ Não foi possível enviar sessão ao Django: sessão está vazia!")
                return False

            logging.info(f"Enviando dados da sessão {self.contador.sessao} para o Django...")
            
            # Preparar dados da sessão
            codigo = self.contador.details.get("Código", "") or f"AUTO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            ponto = self.contador.details.get("Ponto", "") or f"PONTO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            data_ponto = self.contador.details.get("Data do Ponto", "") or datetime.now().strftime("%d/%m/%Y")
            horario_inicio = self.contador.details.get("HorarioInicio", "") or datetime.now().strftime("%H:%M")
            
            # Tratar movimentos
            movimentos = self.contador.details.get("Movimentos", [])
            if isinstance(movimentos, set):
                movimentos = list(movimentos)
            if not movimentos:
                movimentos = ["A"]

            payload = {
                "sessao": self.contador.sessao,
                "codigo": codigo,
                "ponto": ponto,
                "data": data_ponto,
                "horario_inicio": horario_inicio,
                "usuario": self.username,
                "ativa": True,
                "movimentos": movimentos
            }

            url = f"{API_URL}/contagens/registrar-sessao/"
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url, 
                    json=payload, 
                    headers=self._get_auth_headers()
                )

            if response.status_code in [200, 201]:
                logging.info(f"✅ Detalhes da sessão {self.contador.sessao} enviados com sucesso!")
                return True
            else:
                logging.error(f"❌ Falha ao enviar detalhes: {response.status_code} - {response.text}")
                return False

        except Exception as ex:
            logging.error(f"[ERROR] ao enviar detalhes da sessão: {ex}")
            return False

    async def send_count_to_django(self):
        """Envia as contagens para o Django"""
        try:
            logging.info(f"Enviando contagens da sessão {self.contador.sessao} para o Django...")
            
            # Preparar lista de contagens
            contagens_list = [
                {
                    "veiculo": categoria.veiculo,
                    "movimento": categoria.movimento,
                    "count": self.contador.contagens.get((categoria.veiculo, categoria.movimento), 0)
                }
                for categoria in self.contador.categorias
            ]

            # Obter período atual
            periodo_atual = None
            if hasattr(self.contador, "current_timeslot") and self.contador.current_timeslot:
                periodo_atual = self.contador.current_timeslot.strftime("%H:%M")

            payload = {
                "sessao": self.contador.sessao,
                "usuario": self.username,
                "contagens": contagens_list,
                "current_timeslot": periodo_atual
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{API_URL}/contagens/get/",
                    json=payload,
                    headers=self._get_auth_headers()
                )

            if response.status_code == 201:
                logging.info("Contagens enviadas com sucesso!")
                return True
            else:
                logging.error(f"Erro ao enviar contagens: {response.status_code} - {response.text}")
                return False

        except Exception as ex:
            logging.error(f"Erro ao enviar contagens para Django: {ex}")
            return False

    async def load_categories(self, pattern_type):
        """Carrega categorias da API para um determinado padrão"""
        try:
            logging.info(f"[INFO] Carregando categorias para padrão {pattern_type}")
            
            # Preparar movimentos
            movimentos = self.contador.details.get("Movimentos", [])
            if not movimentos:
                logging.warning("[WARNING] Nenhum movimento definido")
                return []

            movimentos = [str(mov).strip().upper() for mov in movimentos if str(mov).strip()]
            self.contador.details["Movimentos"] = movimentos
            print(f"[INFO] Movimentos definidos: {movimentos}")

            # Fazer requisição à API
            url = f"{API_URL}/padroes/padroes-api/?pattern_type={pattern_type}"
            print(f"[INFO] Fazendo requisição para {url}")
            response = await self.api_get(url)

            if not response:
                logging.warning(f"[WARNING] Nenhuma categoria retornada para {pattern_type}")
                return []

            print(f"[INFO] Resposta recebida: {response}")

            # Usar um dicionário para garantir unicidade das categorias
            categorias_dict = {}
            
            # Para cada veículo retornado da API, criar uma categoria para cada movimento
            for cat in response:
                for movimento in movimentos:
                    key = (cat["pattern_type"], cat["veiculo"], movimento)
                    if key not in categorias_dict:
                        categorias_dict[key] = {
                            "pattern_type": cat["pattern_type"],
                            "veiculo": cat["veiculo"],
                            "movimento": movimento,
                            "bind": cat.get("bind", "N/A")
                        }

            # Converter o dicionário de volta para lista
            categorias = list(categorias_dict.values())
            print(f"[INFO] Categorias processadas: {categorias}")
            return categorias

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao carregar categorias: {ex}")
            return []

    async def load_binds(self, pattern_type):
        """Carrega os binds da API para um determinado padrão"""
        try:
            if not pattern_type:
                logging.warning("[WARNING] Nenhum padrão selecionado!")
                return {}

            print(f"Carregando binds para o padrão: {pattern_type}")
            
            url = f"{API_URL}/padroes/merged-binds/?pattern_type={pattern_type}"
            
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(url, headers=self._get_auth_headers())
                
                if response.status_code == 200:
                    data = response.json()
                    binds = {item["veiculo"]: item["bind"] for item in data}
                    print(f"✅ {len(binds)} binds carregados com sucesso")
                    return binds
                else:
                    logging.error(f"❌ Erro ao carregar binds: {response.status_code}")
                    return {}

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao carregar binds: {ex}")
            return {}

    async def end_session_django(self, session_id):
        """Finaliza uma sessão no Django"""
        try:
            url = f"{API_URL}/contagens/finalizar-sessao/"
            
            # Adicionar payload com o ID da sessão
            payload = {
                "sessao": session_id,
                "ativa": False
            }
            
            logging.info(f"Finalizando sessão {session_id} no Django...")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json=payload,  # Adicionar o payload na requisição
                    headers=self._get_auth_headers()
                )
            
            if response.status_code in [200, 201]:
                logging.info(f"✅ Sessão {session_id} finalizada no Django com sucesso!")
                return True
            else:
                logging.error(f"❌ Erro ao finalizar sessão no Django: {response.status_code} - {response.text}")
                return False
            
        except Exception as ex:
            logging.error(f"❌ Erro ao finalizar sessão no Django: {ex}")
            return False
