import logging
import httpx
from utils.api import async_api_request
from utils.config import API_URL
from datetime import datetime
import json

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
            logging.error(f"[ERRO] Requisição GET para {url}: {ex}")
            return None

    async def send_session_to_django(self):
        """Envia os dados da sessão para o Django"""
        try:
            if not self.contador.sessao:
                logging.error("[ERRO] Nenhuma sessão ativa para enviar ao Django")
                return False

            # Preparar dados da sessão
            codigo = self.contador.details.get("Código", "") or f"AUTO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            ponto = self.contador.details.get("Ponto", "") or f"PONTO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            data_ponto = self.contador.details.get("Data do Ponto", "") or datetime.now().strftime("%d/%m/%Y")
            horario_inicio = self.contador.details.get("HorarioInicio", "") or datetime.now().strftime("%H:%M")
            padrao = self.contador.details.get("padrao_usado", "")
            
            # Tratar movimentos
            movimentos = self.contador.details.get("Movimentos", [])
            if isinstance(movimentos, set):
                movimentos = list(movimentos)
            if not movimentos:
                movimentos = ["A"]

            data = {
                "sessao": self.contador.sessao,
                "codigo": codigo,
                "ponto": ponto,
                "data": data_ponto,
                "horario_inicio": horario_inicio,
                "usuario": self.username,
                "ativa": True,
                "movimentos": movimentos,
                "padrao": padrao
            }

            logging.info(f"[INFO] Enviando sessão para o Django com padrão: {padrao}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_URL}/contagens/registrar-sessao/",
                    json=data,
                    headers=self._get_auth_headers()
                )

            if response.status_code in [200, 201]:
                try:
                    # Tentar obter o ID da sessão da resposta
                    response_data = response.json()
                    if 'id' in response_data:
                        session_id = response_data['id']
                        self.contador.details['session_id'] = session_id
                        logging.info(f"[OK] Sessão ID {session_id} salvo nos detalhes")
                    else:
                        # Se não vier na resposta, fazer uma consulta para buscar
                        await self.obter_id_sessao(self.contador.sessao)
                except Exception as ex:
                    logging.warning(f"[AVISO] Não foi possível extrair ID da sessão: {ex}")
                
                logging.info("[OK] Sessão enviada com sucesso para o Django")
                return True
            else:
                logging.error(f"[ERRO] Falha ao enviar sessão para o Django: {response.status_code} - {response.text}")
                return False

        except Exception as ex:
            logging.error(f"[ERRO] Exceção ao enviar sessão para o Django: {ex}")
            return False
            
    async def obter_id_sessao(self, nome_sessao):
        """Obtém o ID numérico de uma sessão pelo nome"""
        try:
            if not nome_sessao:
                logging.error("[ERRO] Nome da sessão não especificado")
                return None
                
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_URL}/contagens/buscar-sessao/?nome={nome_sessao}",
                    headers=self._get_auth_headers()
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if 'id' in response_data:
                        session_id = response_data['id']
                        self.contador.details['session_id'] = session_id
                        logging.info(f"[OK] ID da sessão obtido: {session_id}")
                        # Salvar na sessão
                        self.contador.save_session()
                        return session_id
                    else:
                        logging.warning("[AVISO] Resposta não contém ID da sessão")
                else:
                    logging.error(f"[ERRO] Falha ao obter ID da sessão: {response.status_code} - {response.text}")
                    
            return None
        except Exception as ex:
            logging.error(f"[ERRO] Exceção ao obter ID da sessão: {ex}")
            return None

    async def send_count_to_django(self):
        """Envia as contagens para o Django de forma otimizada"""
        try:
            if not self.contador.sessao:
                return False
            
            # Preparar dados para envio
            if not hasattr(self.contador, "current_timeslot"):
                raise ValueError("current_timeslot não está definido")
                
            current_timeslot = self.contador.current_timeslot.strftime("%H:%M")
            
            # Preparar payload otimizado
            data = {
                "sessao": self.contador.sessao,
                "usuario": self.username,
                "contagens": []
            }
            
            # Verificar movimentos
            movimentos = self.contador.details.get("Movimentos", [])
            if not movimentos:
                movimentos = ["A"]
                
            # Obter todos os veículos possíveis
            all_veiculos = set()
            # Primeiro verifica nos binds
            all_veiculos.update(self.contador.binds.keys())
            
            # Depois verifica nas contagens existentes
            for key in self.contador.contagens.keys():
                all_veiculos.add(key[0])  # key[0] é o veículo
            
            # Preparar contagens para todos os veículos e movimentos
            for veiculo in all_veiculos:
                for movimento in movimentos:
                    key = (veiculo, movimento)
                    count = self.contador.contagens.get(key, 0)
                    # Envia todas as contagens, mesmo as zeradas
                    data["contagens"].append({
                        "veiculo": veiculo,
                        "movimento": movimento,
                        "count": count,
                        "periodo": current_timeslot
                    })

            # Fazer a requisição
            response = await async_api_request(
                "POST",
                "/contagens/get/",
                data=data,
                headers={"Authorization": f"Bearer {self.contador.tokens['access']}"}
            )

            if "erro" in response:
                logging.error(f"Erro ao enviar contagens para o Django: {response['erro']}")
                return False

            return True

        except Exception as ex:
            logging.error(f"Erro ao enviar contagens para o Django: {ex}")
            return False

    async def load_categories(self, pattern_type):
        """Carrega as categorias do Django"""
        try:
            if not pattern_type:
                logging.error("[ERRO] Tipo de padrão não especificado")
                return None

            # Verificar se temos movimentos definidos
            movimentos = self.contador.details.get("Movimentos", [])
            if isinstance(movimentos, set):
                movimentos = list(movimentos)
            if not movimentos:
                logging.warning("[AVISO] Nenhum movimento definido, usando movimento padrão 'A'")
                movimentos = ["A"]

            logging.info(f"[INFO] Carregando categorias para padrão {pattern_type} com movimentos: {movimentos}")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_URL}/padroes/padroes-api/?pattern_type={pattern_type}",
                    headers=self._get_auth_headers()
                )

            if response.status_code == 200:
                api_data = response.json()
                logging.info(f"[INFO] Dados recebidos da API: {len(api_data)} itens")
                
                # Log detalhado dos veículos recebidos
                veiculos_recebidos = sorted([item.get("veiculo") for item in api_data if "veiculo" in item])
                logging.info(f"[INFO] Veículos recebidos da API para padrão '{pattern_type}': {veiculos_recebidos}")

                # Criar lista de categorias expandida com todos os movimentos
                categorias = []
                for item in api_data:
                    for movimento in movimentos:
                        categoria = {
                            "pattern_type": pattern_type,
                            "veiculo": item["veiculo"],
                            "movimento": movimento,
                            "bind": item.get("bind", "N/A")
                        }
                        categorias.append(categoria)

                # Salvar o tipo de padrão usado para referência futura
                self.contador.details["padrao_usado"] = pattern_type
                logging.info(f"[INFO] Padrão '{pattern_type}' salvo nos detalhes para referência")

                logging.info(f"[OK] {len(categorias)} categorias processadas com sucesso")
                return categorias
            else:
                logging.error(f"[ERRO] Falha ao carregar categorias do Django: {response.status_code} - {response.text}")
                return None

        except Exception as ex:
            logging.error(f"[ERRO] Exceção ao carregar categorias do Django: {ex}")
            return None

    async def load_binds(self, pattern_type):
        """Carrega os binds do Django"""
        try:
            if not pattern_type:
                logging.error("[ERRO] Tipo de padrão não especificado para carregar binds")
                return None
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_URL}/padroes/merged-binds/?pattern_type={pattern_type}",
                    headers=self._get_auth_headers()
                )

            if response.status_code == 200:
                binds_list = response.json()
                # Converter a lista em um dicionário {veiculo: bind}
                binds_dict = {}
                for item in binds_list:
                    if isinstance(item, dict) and "veiculo" in item and "bind" in item:
                        binds_dict[item["veiculo"]] = item["bind"]
                    else:
                        logging.warning(f"[AVISO] Item de bind ignorado por formato inválido: {item}")

                logging.info(f"[OK] {len(binds_dict)} binds carregados e convertidos para dicionário")
                return binds_dict
            else:
                logging.error(f"[ERRO] Falha ao carregar binds do Django: {response.status_code} - {response.text}")
                return {}

        except Exception as ex:
            logging.error(f"[ERRO] Exceção ao carregar binds do Django: {ex}")
            return {}

    async def end_session_django(self, sessao_id):
        """Finaliza a sessão no Django"""
        try:
            if not sessao_id:
                logging.error("[ERRO] ID da sessão não especificado")
                return False
                
            # Verificar se sessao_id é numérico
            session_numeric_id = None
            if str(sessao_id).isdigit():
                session_numeric_id = int(sessao_id)
            else:
                # Se não for numérico, é o nome da sessão - precisamos fazer uma busca pelo ID numérico
                logging.info(f"[INFO] Buscando ID numérico para a sessão '{sessao_id}'")
                try:
                    # Primeiro verificamos se temos o ID numérico salvo nos detalhes
                    if hasattr(self.contador, 'details') and 'session_id' in self.contador.details:
                        session_numeric_id = self.contador.details['session_id']
                        logging.info(f"[INFO] ID numérico encontrado nos detalhes: {session_numeric_id}")
                    else:
                        # Precisamos fazer uma busca na API
                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                f"{API_URL}/contagens/buscar-sessao/?nome={sessao_id}",
                                headers=self._get_auth_headers()
                            )
                            
                            if response.status_code == 200:
                                response_data = response.json()
                                if 'id' in response_data:
                                    session_numeric_id = response_data['id']
                                    # Salvar o ID para uso futuro
                                    if hasattr(self.contador, 'details'):
                                        self.contador.details['session_id'] = session_numeric_id
                                    logging.info(f"[INFO] ID numérico encontrado via API: {session_numeric_id}")
                except Exception as ex:
                    logging.error(f"[ERRO] Falha ao buscar ID numérico da sessão: {ex}")
            
            if not session_numeric_id:
                # Alternativa: Usar uma abordagem simplificada - assumir que é apenas o nome da sessão
                # e tentar finalizar diretamente usando um endpoint diferente
                data = {"sessao_nome": sessao_id}
                async with httpx.AsyncClient(follow_redirects=False) as client:
                    try:
                        response = await client.post(
                            f"{API_URL}/contagens/finalizar-por-nome/",
                            json=data,
                            headers=self._get_auth_headers(),
                            timeout=30.0
                        )
                        
                        if response.status_code in [200, 201]:
                            logging.info(f"[OK] Sessão finalizada com sucesso pelo nome")
                            return True
                    except Exception as e:
                        logging.error(f"[ERRO] Falha ao finalizar por nome: {e}")
                
                logging.error(f"[ERRO] Não foi possível obter o ID numérico da sessão '{sessao_id}'")
                return False

            data = {"sessao_id": session_numeric_id}
            
            logging.info(f"[INFO] Tentando finalizar sessão com ID {session_numeric_id}")
            
            # Configurar as requisições para não seguir redirecionamentos
            async with httpx.AsyncClient(follow_redirects=False) as client:
                try:
                    response = await client.post(
                        f"{API_URL}/contagens/finalizar-sessao/",
                        json=data,
                        headers=self._get_auth_headers(),
                        timeout=30.0
                    )

                    if response.status_code in [200, 201]:
                        try:
                            response_data = response.json()
                            mensagem = response_data.get('message', 'Sessão finalizada com sucesso')
                        except:
                            mensagem = 'Sessão finalizada com sucesso'
                        
                        logging.info(f"[OK] {mensagem}")
                        return True
                    else:
                        logging.error(f"[ERRO] Falha ao finalizar sessão no Django: {response.status_code}")
                        if response.text:
                            logging.error(f"[ERRO] Resposta do servidor: {response.text}")
                        return False

                except httpx.TimeoutException:
                    logging.error("[ERRO] Timeout ao tentar finalizar sessão")
                    return False
                except httpx.RequestError as e:
                    logging.error(f"[ERRO] Erro na requisição ao finalizar sessão: {e}")
                    return False

        except Exception as ex:
            logging.error(f"[ERRO] Exceção ao finalizar sessão no Django: {ex}")
            return False

    async def load_codigos(self):
        """Carrega os códigos do Django"""
        try:
            response = await async_api_request(
                url=f"{API_URL}/trabalhos/api/codigos/",
                method="GET",
                headers=self._get_auth_headers()
            )
            
            if response:
                return [item["codigo"] for item in response]
            return []
        except Exception as ex:
            logging.error(f"[ERRO] Falha ao carregar códigos: {ex}")
            return []

    async def load_padroes(self):
        """Carrega os tipos de padrões do Django"""
        try:
            response = await async_api_request(
                url=f"{API_URL}/padroes/tipos-padroes/",
                method="GET",
                headers=self._get_auth_headers()
            )
            
            if response:
                return [item["nome"] for item in response]
            return []
        except Exception as ex:
            logging.error(f"[ERRO] Falha ao carregar tipos de padrões: {ex}")
            return []

    async def load_pontos(self, codigo):
        """Carrega os pontos do Django para um código específico"""
        try:
            response = await async_api_request(
                url=f"{API_URL}/trabalhos/api/pontos/{codigo}/",
                method="GET",
                headers=self._get_auth_headers()
            )
            
            if response:
                return [item["nome"] for item in response]
            return []
        except Exception as ex:
            logging.error(f"[ERRO] Falha ao carregar pontos: {ex}")
            return []
