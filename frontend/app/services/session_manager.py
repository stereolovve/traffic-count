import logging
import json
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from database.models import Sessao, Categoria
import threading
import asyncio
import flet as ft
import re
import logging
import httpx
import time


class SessionManager:
    def __init__(self, contador):
        self.contador = contador
        self.session_lock = threading.Lock()
        
        # Referências diretas
        self.session = contador.session
        self.ui_components = contador.ui_components
        self.contagens = contador.contagens
        self.labels = contador.labels
        self.categorias = contador.categorias

    async def create_session(self, session_data):
        banner = None
        try:
            banner = self.contador.show_loading("Criando sessão e carregando padrões...")

            # 1. Validar dados da sessão
            if not all(session_data.get(key) for key in ["codigo", "ponto", "horario_inicio", "data_ponto", "padrao"]):
                raise ValueError("Dados da sessão incompletos")

            if not session_data.get("movimentos"):
                raise ValueError("É necessário definir pelo menos um movimento")

            # 2. Configurar detalhes da sessão (em memória)
            self.contador.details = {
                "Pesquisador": session_data["pesquisador"],
                "Código": session_data["codigo"],
                "Ponto": session_data["ponto"],
                "HorarioInicio": session_data["horario_inicio"],
                "HorarioFim": session_data.get("horario_fim", ""),
                "Data do Ponto": session_data["data_ponto"],
                "Movimentos": session_data["movimentos"]
            }

            # 3. Configurar horário inicial
            hoje = datetime.now().date()
            horario_inicial = datetime.strptime(session_data["horario_inicio"], "%H:%M").time()
            self.contador.current_timeslot = datetime.combine(hoje, horario_inicial)
            self.contador.details["current_timeslot"] = self.contador.current_timeslot.strftime("%H:%M")
            
            # 4. Gerar nome da sessão
            horario_inicial_file_safe = session_data["horario_inicio"].replace(":", "h")
            formated_date = datetime.strptime(
                session_data["data_ponto"], 
                "%d-%m-%Y"
            ).strftime("%d-%m-%Y")
            movimentos_str = "-".join(session_data["movimentos"])
            movimentos_str = re.sub(r'[<>:"/\\|?*]', '', movimentos_str)
            base_sessao = (
                f"{session_data['ponto']}_{formated_date}_"
                f"{movimentos_str}_{horario_inicial_file_safe}"
            )

            self.contador.sessao = base_sessao
            counter = 1
            while self.contador.session.query(Sessao).filter_by(sessao=self.contador.sessao).first():
                self.contador.sessao = f"{base_sessao}_{counter}"
                counter += 1

            # 5. ✅ Limpeza robusta para evitar duplicação
            logging.info("Limpando dados da sessão anterior...")
            
            # Limpar categorias
            self.categorias.clear()
            self.contador.categorias.clear()
            
            # ✅ Limpar labels e contagens de sessão anterior
            self.labels.clear()
            self.contador.labels.clear()
            
            # ✅ Limpar contagens da sessão anterior (apenas se for nova sessão)
            if not hasattr(self.contador, '_current_session') or self.contador._current_session != base_sessao:
                self.contador.contagens.clear()
                self.contador._current_session = base_sessao
                logging.info("Nova sessão detectada - contagens zeradas")
            
            # ✅ Marcar UI components para reconstrução
            if 'contagem' in self.contador.ui_components:
                self.contador.ui_components['contagem']._session_loaded = False
            
            # 6. Carregar binds e categorias em paralelo (otimização)
            logging.info("Iniciando carregamento paralelo de binds e categorias...")
            
            import asyncio
            tasks = [
                self.contador.api_manager.load_binds(session_data["padrao"]),
                self.contador.api_manager.load_categories(session_data["padrao"])
            ]
            
            # Executar em paralelo para reduzir tempo de carregamento
            results = await asyncio.gather(*tasks, return_exceptions=True)
            binds_result, categorias_result = results
            
            # Processar resultados
            if not isinstance(binds_result, Exception) and binds_result:
                self.contador.binds = binds_result
                logging.info(f"Binds carregados: {len(binds_result)} itens")
            else:
                logging.warning("Falha ao carregar binds, usando fallback local")
                
            if not isinstance(categorias_result, Exception) and categorias_result:
                logging.info(f"Categorias carregadas do servidor: {len(categorias_result)} itens")
                self.save_categories_in_local(categorias_result)
            else:
                logging.warning("Falha ao carregar categorias do servidor")

            # Carregar categorias locais (já limpo anteriormente)
            self.carregar_categorias_locais(session_data["padrao"])

            # 7. Criar sessão no banco local
            nova_sessao = Sessao(
                sessao=self.contador.sessao,
                padrao=session_data["padrao"],
                codigo=session_data["codigo"],
                ponto=session_data["ponto"],
                data=session_data["data_ponto"],
                horario_inicio=session_data["horario_inicio"],
                horario_fim=session_data.get("horario_fim", ""),
                criada_em=datetime.now(),
                status="Em andamento",
                movimentos=json.dumps(session_data["movimentos"])  # Salvar movimentos como JSON
            )
            with self.contador.session_lock:
                self.contador.session.add(nova_sessao)
                self.contador.session.commit()

            # 8. Inicializar arquivo Excel
            try:
                success_excel = self.contador.excel_manager.initialize_excel_file()
                if not success_excel:
                    raise Exception("Falha ao criar arquivo Excel")
            except Exception as ex:
                logging.error(f"Erro ao criar arquivo Excel: {ex}")
                raise

            # 9. Registrar sessão no Django
            success_django = await self.contador.api_manager.send_session_to_django()
            if not success_django:
                logging.warning("Sessão criada localmente, mas não registrada no servidor.")

            # 10. Configurar UI
            if 'contagem' in self.contador.ui_components:
                self.contador.ui_components['contagem'].force_ui_update()

            self.contador.tabs.selected_index = 1
            self.contador.tabs.tabs[1].content.visible = True

            # 11. Mostrar feedback
            self.contador.page.overlay.append(
                ft.SnackBar(
                    content=ft.Text(
                        "Sessão criada com sucesso!" +
                        (" e registrada no servidor." if success_django else "")
                    ),
                    bgcolor="green"
                )
            )
            self.contador.page.update()

        except Exception as ex:
            logging.error(f"Erro ao criar sessão: {ex}")
            # Tentar limpar estado em caso de erro
            self.contador.sessao = None
            self.contador.details = {"Movimentos": []}
            
            self.contador.page.overlay.append(
                ft.SnackBar(
                    content=ft.Text(f"Erro ao criar sessão: {str(ex)}"),
                    bgcolor="red"
                )
            )
            self.contador.page.update()
            raise

        finally:
            if banner:
                self.contador.hide_loading(banner)

    def save_session(self):
        try:
            start_time = time.time()
            
            with self.session_lock:
                if self.session.in_transaction():
                    self.session.commit()
                
                # Salvar contagens
                for (veiculo, movimento), count in self.contagens.items():
                    self.save_to_db(veiculo, movimento)
                
                # Atualizar detalhes da sessão com o período atual
                sessao = self.session.query(Sessao).filter_by(sessao=self.contador.sessao).first()
                if sessao:
                    self.contador.details["current_timeslot"] = self.contador.current_timeslot.strftime("%H:%M")
                    # Não salvar details mais - usar campos próprios
                    self.session.commit()
                
                self.last_save_time = datetime.now()
                
            end_time = time.time()
            elapsed_time = (end_time - start_time) * 1000  # Convertendo para milissegundos
            logging.info(f"Tempo total para salvar sessão: {elapsed_time:.2f}ms")
                
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao salvar sessão no DB: {ex}")
            with self.contador.session_lock:
                self.session.rollback()

    async def load_active_session(self):
        try:
            sessao_ativa = self.session.query(Sessao).filter_by(status="Em andamento").first()
            
            if not sessao_ativa:
                logging.info("Nenhuma sessão ativa encontrada")
                return False

            # Mostrar diálogo para o usuário escolher
            return await self._show_session_choice_dialog(sessao_ativa)

        except Exception as ex:
            logging.error(f"Erro ao verificar sessão ativa: {ex}")
            return False

    async def _show_session_choice_dialog(self, sessao_ativa):
        """Mostra diálogo para o usuário escolher o que fazer com a sessão ativa"""
        try:
            def continuar_sessao(e):
                dialog.open = False
                self.contador.page.update()
                self.contador.page.run_task(self._resume_session, sessao_ativa)

            def finalizar_e_nova(e):
                dialog.open = False
                self.contador.page.update()
                self.contador.page.run_task(self._end_and_start_new)

            # Coletar informações detalhadas da sessão
            session_details = self._get_session_details(sessao_ativa)

            dialog = ft.AlertDialog(
                title=ft.Text("Sessão ativa detectada", size=18, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("DETALHES DA SESSÃO", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                        ft.Divider(height=1, color=ft.Colors.BLUE_300),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.FINGERPRINT, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"ID: {session_details['sessao']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.CATEGORY, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"Padrão: {session_details['padrao']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.CODE, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"Código: {session_details['codigo']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.LOCATION_ON, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"Ponto: {session_details['ponto']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.CALENDAR_TODAY, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"Data: {session_details['data']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.ACCESS_TIME, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"Início: {session_details['horario_inicio']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.ACCESS_TIME_FILLED, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"Fim: {session_details['horario_fim']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.INFO, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"Status: {session_details['status']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Divider(height=1, color=ft.Colors.GREY_300),
                        
                        ft.Text("ESTATÍSTICAS", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.MOVING, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"Movimentos: {session_details['total_movimentos']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.NUMBERS, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"Total de contagens: {session_details['total_contagens']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.SCHEDULE, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"Último período: {session_details['ultimo_periodo']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Row([
                            ft.Icon(ft.Icons.UPDATE, size=16, color=ft.Colors.GREY_600),
                            ft.Text(f"Criada em: {session_details['criada_em']}", weight=ft.FontWeight.W_500)
                        ], spacing=8),
                        
                        ft.Divider(height=1, color=ft.Colors.ORANGE_300),
                        ft.Text("Deseja continuar esta sessão ou iniciar uma nova?", 
                               text_align=ft.TextAlign.CENTER, 
                               weight=ft.FontWeight.BOLD,
                               color=ft.Colors.ORANGE_700)
                    ], spacing=4, scroll=ft.ScrollMode.AUTO),
                    width=400,
                    height=500,
                    padding=10
                ),
                actions=[
                    ft.TextButton("Continuar sessão", 
                                 on_click=continuar_sessao,
                                 style=ft.ButtonStyle(color=ft.Colors.GREEN_700)),
                    ft.TextButton("Iniciar nova sessão", 
                                 on_click=finalizar_e_nova,
                                 style=ft.ButtonStyle(color=ft.Colors.ORANGE_700)),
                ],
            )
            
            self.contador.page.overlay.append(dialog)
            dialog.open = True
            self.contador.page.update()
            return True

        except Exception as ex:
            logging.error(f"Erro ao mostrar diálogo de escolha: {ex}")
            return False

    def _get_session_details(self, sessao_ativa):
        """Coleta informações detalhadas da sessão para exibir no diálogo"""
        try:
            # Informações básicas da sessão
            details = {
                'sessao': sessao_ativa.sessao or "N/A",
                'padrao': sessao_ativa.padrao or "N/A",
                'codigo': sessao_ativa.codigo or "N/A",
                'ponto': sessao_ativa.ponto or "N/A",
                'data': sessao_ativa.data or "N/A",
                'horario_inicio': sessao_ativa.horario_inicio or "N/A",
                'horario_fim': sessao_ativa.horario_fim or "Não definido",
                'status': sessao_ativa.status or "N/A"
            }
            
            # Formattar data de criação
            if hasattr(sessao_ativa, 'criada_em') and sessao_ativa.criada_em:
                details['criada_em'] = sessao_ativa.criada_em.strftime("%d/%m/%Y %H:%M")
            else:
                details['criada_em'] = "N/A"
            
            # Contar movimentos da sessão
            movimentos_count = 0
            if hasattr(sessao_ativa, 'movimentos') and sessao_ativa.movimentos:
                try:
                    import json
                    movimentos = json.loads(sessao_ativa.movimentos)
                    movimentos_count = len(movimentos) if isinstance(movimentos, list) else 0
                except:
                    movimentos_count = 0
            details['total_movimentos'] = str(movimentos_count)
            
            # Sistema otimizado - sem estatísticas de contagens do banco
            details['total_contagens'] = "0 (otimizado)"
            details['ultimo_periodo'] = "Sistema simplificado"
            
            logging.info(f"Detalhes da sessão coletados: {details}")
            return details
            
        except Exception as ex:
            logging.error(f"Erro ao coletar detalhes da sessão: {ex}")
            # Retornar detalhes básicos em caso de erro
            return {
                'sessao': getattr(sessao_ativa, 'sessao', 'N/A'),
                'padrao': getattr(sessao_ativa, 'padrao', 'N/A'),
                'codigo': getattr(sessao_ativa, 'codigo', 'N/A'),
                'ponto': getattr(sessao_ativa, 'ponto', 'N/A'),
                'data': getattr(sessao_ativa, 'data', 'N/A'),
                'horario_inicio': getattr(sessao_ativa, 'horario_inicio', 'N/A'),
                'horario_fim': getattr(sessao_ativa, 'horario_fim', 'Não definido'),
                'status': getattr(sessao_ativa, 'status', 'N/A'),
                'criada_em': 'N/A',
                'total_movimentos': '0',
                'total_contagens': '0',
                'ultimo_periodo': 'Nenhum'
            }

    async def _resume_session(self, sessao_ativa):
        """Resume uma sessão ativa existente"""
        banner = None
        try:
            banner = self.contador.show_loading("Carregando sessão ativa...")
            logging.info(f"Resumindo sessão: {sessao_ativa.sessao}")

            # 1. Configurar dados básicos da sessão
            self._setup_session_basic_data(sessao_ativa)
            
            # 2. Configurar horários
            self._setup_session_timing(sessao_ativa)
            
            # 3. Configurar UI
            self._setup_session_ui(sessao_ativa)
            
            # 4. Carregar dados da sessão
            await self._load_session_data(sessao_ativa)
            
            # 5. Recuperar contagens
            self._recover_session_countings()
            
            # 6. Configurar interface final
            self._setup_final_interface()
            
            logging.info("Sessão resumida com sucesso")

        except Exception as ex:
            logging.error(f"Erro ao resumir sessão: {ex}")
            self._handle_session_resume_error(ex)
        finally:
            if banner:
                self.contador.hide_loading(banner)

    def _setup_session_basic_data(self, sessao_ativa):
        """Configura os dados básicos da sessão"""
        self.contador.sessao = sessao_ativa.sessao
        
        # Carregar movimentos da sessão se existirem
        movimentos = []
        if hasattr(sessao_ativa, 'movimentos') and sessao_ativa.movimentos:
            try:
                import json
                movimentos = json.loads(sessao_ativa.movimentos)
                logging.info(f"[DEBUG] Movimentos carregados da sessão: {movimentos}")
            except Exception as ex:
                logging.warning(f"[WARNING] Erro ao carregar movimentos da sessão: {ex}")
                movimentos = []
        else:
            logging.warning(f"[WARNING] Sessão não possui movimentos salvos")
        
        # Configurar detalhes da sessão
        self.contador.details = {
            "Pesquisador": self.contador.username,
            "Código": sessao_ativa.codigo,
            "Ponto": sessao_ativa.ponto,
            "HorarioInicio": sessao_ativa.horario_inicio,
            "HorarioFim": getattr(sessao_ativa, "horario_fim", ""),
            "Data do Ponto": sessao_ativa.data,
            "Movimentos": movimentos
        }
        
        logging.info(f"Dados básicos configurados para sessão: {self.contador.sessao}")

    def _setup_session_timing(self, sessao_ativa):
        """Configura os horários da sessão - recupera último período salvo"""
        hoje = datetime.now().date()
        
        # Tentar recuperar último período salvo no Excel
        ultimo_periodo = self._get_ultimo_periodo_salvo()
        
        if ultimo_periodo:
            # Usar próximo período após o último salvo
            try:
                ultimo_datetime = datetime.strptime(ultimo_periodo, "%H:%M").time()
                ultimo_slot = datetime.combine(hoje, ultimo_datetime)
                # Próximo período seria 15 minutos depois
                self.contador.current_timeslot = ultimo_slot + timedelta(minutes=15)
                logging.info(f"Recuperado último período: {ultimo_periodo}, próximo: {self.contador.current_timeslot.strftime('%H:%M')}")
            except Exception as ex:
                logging.warning(f"Erro ao processar último período {ultimo_periodo}: {ex}")
                # Fallback para horário de início
                horario = datetime.strptime(sessao_ativa.horario_inicio, "%H:%M").time()
                self.contador.current_timeslot = datetime.combine(hoje, horario)
        else:
            # Usar horário de início da sessão
            horario = datetime.strptime(sessao_ativa.horario_inicio, "%H:%M").time()
            self.contador.current_timeslot = datetime.combine(hoje, horario)
            logging.info(f"Nenhum período salvo encontrado, usando horário de início: {horario}")
        
        self.contador.details["current_timeslot"] = self.contador.current_timeslot.strftime("%H:%M")
        logging.info(f"Horário configurado: {self.contador.current_timeslot.strftime('%H:%M')}")

    def _get_ultimo_periodo_salvo(self):
        """Recupera o último período salvo no Excel"""
        try:
            from utils.config import get_excel_dir
            import pandas as pd
            import os
            import re
            
            if not self.contador.sessao or not self.contador.details:
                return None
            
            # Construir caminho do Excel
            nome_pesquisador = re.sub(r'[<>:"/\\|?*]', '', self.contador.username)
            codigo = re.sub(r'[<>:"/\\|?*]', '', self.contador.details['Código'])
            excel_dir = get_excel_dir()
            diretorio_pesquisador_codigo = os.path.join(excel_dir, nome_pesquisador, codigo)
            excel_path = os.path.join(diretorio_pesquisador_codigo, f'{self.contador.sessao}.xlsx')
            
            if not os.path.exists(excel_path):
                logging.info("Arquivo Excel não encontrado - primeira execução da sessão")
                return None
            
            # Verificar último período em todas as abas
            ultimo_periodo = None
            movimentos = self.contador.details.get("Movimentos", [])
            
            for movimento in movimentos:
                try:
                    df = pd.read_excel(excel_path, sheet_name=movimento)
                    if not df.empty and 'das' in df.columns:
                        # Pegar último período da coluna 'das'
                        ultimos_das = df['das'].dropna().astype(str)
                        if not ultimos_das.empty:
                            periodo_movimento = ultimos_das.iloc[-1]
                            # Comparar períodos para pegar o mais recente
                            if not ultimo_periodo or periodo_movimento > ultimo_periodo:
                                ultimo_periodo = periodo_movimento
                except Exception as ex:
                    logging.warning(f"Erro ao verificar movimento {movimento}: {ex}")
            
            if ultimo_periodo:
                logging.info(f"Último período salvo encontrado: {ultimo_periodo}")
                return ultimo_periodo
            else:
                logging.info("Nenhum período salvo encontrado no Excel")
                return None
                
        except Exception as ex:
            logging.warning(f"Erro ao recuperar último período do Excel: {ex}")
            return None

    def _setup_session_ui(self, sessao_ativa):
        """Configura a interface da sessão"""
        self.contador.setup_ui()
        
        # Configurar padrão selecionado
        if 'inicio' in self.contador.ui_components:
            self.contador.ui_components['inicio'].padrao_dropdown.value = sessao_ativa.padrao
        
        logging.info("Interface configurada")

    async def _load_session_data(self, sessao_ativa):
        """Carrega os dados da sessão (binds e categorias)"""
        padrao_atual = sessao_ativa.padrao
        logging.info(f"Carregando dados para padrão: {padrao_atual}")
        
        # Limpar categorias anteriores para evitar duplicação
        logging.info("Limpando categorias anteriores para evitar duplicação...")
        self.categorias.clear()
        self.contador.categorias.clear()
        
        # Carregar binds
        try:
            binds = await self.contador.api_manager.load_binds(padrao_atual)
            if binds:
                self.contador.binds = binds
                logging.info(f"Binds carregados: {len(binds)} itens")
        except Exception as ex:
            logging.error(f"Erro ao carregar binds: {ex}")
            # Fallback para binds locais
            self.contador.binds = self._carregar_binds_locais(padrao_atual)
        
        # Carregar categorias
        try:
            categorias = await self.contador.api_manager.load_categories(padrao_atual)
            if categorias:
                self.save_categories_in_local(categorias)
                logging.info(f"Categorias carregadas do servidor: {len(categorias)} itens")
        except Exception as ex:
            logging.error(f"Erro ao carregar categorias: {ex}")
        
        # Carregar categorias locais (já limpo anteriormente)
        self.carregar_categorias_locais(padrao_atual)
        
        # Atualizar a UI de contagem após carregar os dados
        if 'contagem' in self.contador.ui_components:
            logging.info("Atualizando UI de contagem após carregamento de dados...")
            self.contador.ui_components['contagem'].force_ui_update()

    def _recover_session_countings(self):
        """Recupera as contagens ativas da sessão"""
        try:
            self.recover_active_countings()
        except Exception as ex:
            logging.error(f"Erro ao recuperar contagens: {ex}")

    def _setup_final_interface(self):
        if 'contagem' in self.contador.ui_components and self.contador.categorias:
            logging.info("Configurando UI de contagem com categorias carregadas...")
            self.contador.ui_components['contagem'].force_ui_update()
        else:
            logging.warning("Categorias não carregadas ou componente de contagem não disponível")
        
        self.contador.tabs.selected_index = 1
        self.contador.tabs.tabs[1].content.visible = True
        self.contador.page.window.scroll = ft.ScrollMode.AUTO
        self.contador.page.update()
        
        logging.info("Interface final configurada")

    def _handle_session_resume_error(self, ex):
        """Trata erros ao resumir sessão"""
        logging.error(f"Erro crítico ao resumir sessão: {ex}")
        self.contador.page.overlay.append(
            ft.SnackBar(
                content=ft.Text(f"Erro ao carregar sessão: {str(ex)}"),
                bgcolor="red"
            )
        )
        self.contador.page.update()
        self.contador.setup_ui()

    async def _end_and_start_new(self):
        try:
            # Force end any active session regardless of state
            await self.force_end_current_session()
            self.contador.setup_ui()
        except Exception as ex:
            logging.error(f"Erro ao finalizar e iniciar nova sessão: {ex}")

    async def force_end_current_session(self):
        """Force end current session without validation"""
        try:
            # Find any active session in database and end it
            with self.contador.session_lock:
                sessao_ativa = self.session.query(Sessao).filter_by(status="Em andamento").first()
                if sessao_ativa:
                    # Update session to completed
                    sessao_ativa.status = "Concluída"
                    self.session.commit()
                    logging.info(f"Sessão forçadamente finalizada: {sessao_ativa.sessao}")
                    
                    # Try to sync with Django if possible
                    try:
                        if hasattr(self.contador, 'api_manager'):
                            await self.contador.api_manager.end_session_django(sessao_ativa.sessao)
                    except Exception as sync_ex:
                        logging.warning(f"Não foi possível sincronizar com Django: {sync_ex}")
                
                # Clear all session data regardless
                self.contador.sessao = None
                self.contador.details = {"Movimentos": []}
                self.contagens.clear()
                self.contador.binds.clear()
                self.contador.labels.clear()
                self.categorias.clear()
                self.contador.categorias.clear()
                
                logging.info("Dados da sessão limpos forçadamente")
                
        except Exception as ex:
            logging.error(f"Erro ao forçar finalização da sessão: {ex}")
            # Even if database update fails, clear memory state
            self.contador.sessao = None
            self.contador.details = {"Movimentos": []}
            self.contagens.clear()
            self.contador.binds.clear()
            self.contador.labels.clear()
            self.categorias.clear()
            self.contador.categorias.clear()

    def save_to_db(self, veiculo, movimento):
        movimento = movimento.upper()
        
        key = (veiculo, movimento)
        
        try:
            import json
            with self.contador.session_lock:
                sessao_obj = self.session.query(Sessao).filter_by(sessao=self.contador.sessao).first()
                if sessao_obj:
                    contagens_json = json.dumps({f"{k[0]}_{k[1]}": v for k, v in self.contador.contagens.items()})
                    sessao_obj.contagens_atuais = contagens_json
                    self.session.commit()
                    
            logging.debug(f"Contagem salva: {veiculo} - {movimento} = {self.contador.contagens.get(key, 0)}")
        except Exception as ex:
            logging.error(f"Erro ao salvar contagem na sessão: {ex}")

    def recover_active_countings(self):
        try:
            logging.info("Recuperando contagens da sessão...")
            
            with self.contador.session_lock:
                sessao_obj = self.session.query(Sessao).filter_by(sessao=self.contador.sessao).first()
                
                if sessao_obj and sessao_obj.contagens_atuais:
                    import json
                    try:
                        contagens_salvas = json.loads(sessao_obj.contagens_atuais)
                        
                        for key_str, valor in contagens_salvas.items():
                            if '_' in key_str:
                                veiculo, movimento = key_str.rsplit('_', 1)
                                key = (veiculo, movimento)
                                self.contador.contagens[key] = valor
                                
                                if key in self.contador.labels:
                                    label_count, _ = self.contador.labels[key]
                                    label_count.value = str(valor)
                                    label_count.update()
                        
                        total_recuperado = sum(contagens_salvas.values())
                        logging.info(f"Contagens recuperadas: {total_recuperado} itens")
                        
                        if hasattr(self.contador, 'page') and self.contador.page:
                            self.contador.page.update()
                            
                    except Exception as json_ex:
                        logging.error(f"Erro ao decodificar contagens salvas: {json_ex}")
                        self._clear_countings()
                else:
                    logging.info("Nenhuma contagem salva encontrada - iniciando do zero")
                    self._clear_countings()
                    
        except Exception as ex:
            logging.error(f"Erro ao recuperar contagens: {ex}")
            self._clear_countings()
    
    def _clear_countings(self):
        self.contador.contagens.clear()
        
        for key in self.contador.labels:
            if key in self.contador.labels:
                label_count, _ = self.contador.labels[key]
                label_count.value = "0"
                label_count.update()

    def save_categories_in_local(self, categorias):
        try:
            with self.contador.session_lock:
                # Lista para armazenar novas categorias em lote
                novas_categorias = []
                
                for categoria_dict in categorias:
                    movimento = categoria_dict['movimento']

                    existe = self.session.query(Categoria).filter_by(
                        padrao=categoria_dict['pattern_type'],
                        veiculo=categoria_dict['veiculo'],
                        movimento=movimento
                    ).first()

                    if not existe:
                        nova_categoria = Categoria(
                            padrao=categoria_dict['pattern_type'],
                            veiculo=categoria_dict['veiculo'],
                            movimento=movimento,
                            bind=categoria_dict.get('bind', 'N/A')
                        )
                        novas_categorias.append(nova_categoria)
                    else:
                        logging.debug(f"[DEBUG] Categoria já existente no banco: {categoria_dict['veiculo']} - {movimento}")

                # Inserção em lote para melhor performance
                if novas_categorias:
                    self.session.bulk_save_objects(novas_categorias)
                
                self.session.commit()

        except Exception as ex:
            self.session.rollback()

    def _carregar_binds_locais(self, padrao=None):
        try:
            if not padrao:
                return {}
            
            categorias = self.session.query(Categoria).filter_by(padrao=padrao).all()
            binds_locais = {}
            
            for cat in categorias:
                if cat.veiculo not in binds_locais and cat.bind != "N/A":
                    binds_locais[cat.veiculo] = cat.bind
                
            return binds_locais
        except Exception as ex:
            logging.error(f"❌ Erro ao carregar binds locais: {ex}")
            return {}

    def carregar_categorias_locais(self, padrao=None):
        if not self.ui_components or 'inicio' not in self.ui_components:
            logging.warning("[WARNING] UI components não inicializados corretamente")
            return []
            
        padrao_atual = padrao or self.ui_components['inicio'].padrao_dropdown.value

        if not padrao_atual:
            logging.warning("[WARNING] Nenhum padrão selecionado")
            return []

        logging.info(f"Carregando categorias locais para padrão: {padrao_atual}")

        with self.contador.session_lock:
            try:
                # NÃO limpar categorias aqui - já foram limpas antes da chamada
                # self.categorias.clear()
                # self.contador.categorias.clear()
                
                categorias_db = (
                    self.session.query(Categoria)
                    .filter(Categoria.padrao == padrao_atual)
                    .order_by(Categoria.id)
                    .all()
                )
                self.session.commit()

                # Atualizar as listas de categorias (extend mantém referências)
                self.categorias.extend(categorias_db)
                self.contador.categorias.extend(categorias_db)

                logging.info(f"Categorias locais carregadas: {len(self.categorias)} itens")
                
                if self.categorias:
                    logging.info(f"[DEBUG] Primeiras 5 categorias carregadas: {[(c.veiculo, c.movimento, c.padrao) for c in self.categorias[:5]]}")
                    
                    movimentos_unicos = set(c.movimento for c in self.categorias)
                    logging.info(f"[DEBUG] Movimentos únicos nas categorias: {sorted(movimentos_unicos)}")
                    
                    movimentos_sessao = self.contador.details.get("Movimentos", [])
                    logging.info(f"[DEBUG] Movimentos da sessão: {movimentos_sessao}")
                    
                    for movimento_sessao in movimentos_sessao:
                        categorias_movimento = [c for c in self.categorias if movimento_sessao.strip().upper() == c.movimento.strip().upper()]
                        logging.info(f"[DEBUG] Movimento '{movimento_sessao}': {len(categorias_movimento)} categorias encontradas")
                else:
                    logging.warning(f"[WARNING] Nenhuma categoria encontrada para o padrão: {padrao_atual}")

                # Garantir sincronização das referências
                self.contador.categorias = self.categorias

            except Exception as ex:
                logging.error(f"[ERROR] Erro ao carregar categorias locais: {ex}")
                self.session.rollback()
                self.categorias = []

        return self.categorias

    async def end_session(self):
        try:
            
            if not self.contador.sessao:
                raise ValueError("Não há sessão ativa para finalizar")
            
            await self.contador.api_manager.send_session_to_django()
            
            success = await self.contador.api_manager.end_session_django(self.contador.sessao)
            
            if success:
                logging.info("Sessão finalizada no Django com sucesso!")
            else:
                logging.warning("Não foi possível finalizar a sessão no Django, mas continuaremos com a finalização local.")
            
            with self.contador.session_lock:
                sessao_concluida = self.session.query(Sessao).filter_by(sessao=self.contador.sessao).first()
                if sessao_concluida:
                    sessao_concluida.status = "Concluída"
                    self.session.commit()
                else:
                    logging.warning("Sessão não encontrada no banco local")

            sessao_finalizada = self.contador.sessao
            self.contador.sessao = None
            self.contador.details = {"Movimentos": []}
            self.contagens.clear()
            self.contador.binds.clear()
            self.contador.labels.clear()
            
            # Limpar categorias para evitar duplicação na próxima sessão
            self.categorias.clear()
            self.contador.categorias.clear()
            logging.info("Dados da sessão limpos (contagens, binds, labels, categorias)")

            snackbar = ft.SnackBar(
                content=ft.Text(f"Sessão {sessao_finalizada} finalizada com sucesso!"),
                bgcolor="blue"
            )
            self.contador.page.overlay.append(snackbar)
            snackbar.open = True

            self.contador.restart_app_after_end_session()
            
            self.contador.tabs.selected_index = 0
            self.contador.page.update()

        except ValueError as ex:
            logging.error(f"Erro de validação ao encerrar sessão: {ex}")
            snackbar = ft.SnackBar(
                content=ft.Text(str(ex)),
                bgcolor="red"
            )
            self.contador.page.overlay.append(snackbar)
            snackbar.open = True
            self.contador.page.update()
        except Exception as ex:
            logging.error(f"Erro ao encerrar sessão: {ex}")
            snackbar = ft.SnackBar(
                content=ft.Text(f"Erro ao encerrar sessão: {str(ex)}"),
                bgcolor="red"
            )
            self.contador.page.overlay.append(snackbar)
            snackbar.open = True
            self.contador.page.update()

    def show_dialog_end_session(self, e):
        def close_dialog(e):
            dialog.open = False
            self.contador.page.update()

        async def run_end_session():
            try:
                dialog.open = False
                self.contador.page.update()
                await self.end_session()
            except Exception as ex:
                logging.error(f"Erro ao finalizar sessão via diálogo: {ex}")

        dialog = ft.AlertDialog(
            title=ft.Text("Finalizar Sessão"),
            content=ft.Text("Você tem certeza que deseja finalizar a sessão?"),
            actions=[
                ft.TextButton("Sim", on_click=lambda e: self.contador.page.run_task(run_end_session)),
                ft.TextButton("Cancelar", on_click=close_dialog),
            ],
        )
        self.contador.page.overlay.append(dialog)
        dialog.open = True
        self.contador.page.update()

    def clear_current_session_data(self):
        self.contador.contagens.clear()
        logging.info("Dados da sessão limpos da memória (otimizado)")

    def update_session_time(self, current_timeslot, last_save_time):
        self.contador.last_save_time = last_save_time
        self.contador.details["last_save_time"] = last_save_time.strftime("%H:%M:%S")
        self.contador.current_timeslot = current_timeslot + timedelta(minutes=15)
        self.contador.details["current_timeslot"] = self.contador.current_timeslot.strftime("%H:%M")

    def check_database_countings(self):
        try:
            
            if not self.contador.sessao:
                print(f"[CHECK] Nenhuma sessão ativa")
                return
            
            total_memoria = sum(self.contagens.values())
            
        except Exception as ex:
            print(f"[CHECK] Erro ao verificar contagens: {ex}")

    def test_save_counting(self):
        try:
            if not self.contador.sessao:
                return False
            
            if not self.contagens:
                return False
            
            # Verificar se há contagens em memória
            total_contagens = sum(self.contagens.values())
            print(f"[TEST] Total de contagens em memória: {total_contagens}")
            
            for (veiculo, movimento), count in self.contagens.items():
                print(f"[TEST]  - {veiculo} - {movimento} = {count}")
            
            return total_contagens > 0
            
        except Exception as ex:
            print(f"[TEST] Erro no teste: {ex}")
            return False

    def can_save_session(self):
        """
        Verifica se é possível salvar a sessão considerando o horário de fim.
        
        Returns:
            tuple: (pode_salvar: bool, motivo: str, proximos_slots: int)
        """
        try:
            if not self.contador.sessao or not hasattr(self.contador, 'details'):
                return False, "Sessão não inicializada", 0
            
            # Verificar se há horário de fim definido
            horario_fim_str = self.contador.details.get("HorarioFim", "").strip()
            if not horario_fim_str:
                # Se não há horário fim, permite salvar indefinidamente
                return True, "Sem limite de horário", -1
            
            # Calcular horários
            hoje = datetime.now().date()
            horario_inicio = datetime.strptime(self.contador.details["HorarioInicio"], "%H:%M").time()
            horario_fim = datetime.strptime(horario_fim_str, "%H:%M").time()
            
            inicio_datetime = datetime.combine(hoje, horario_inicio)
            fim_datetime = datetime.combine(hoje, horario_fim)
            
            # Se fim é menor que início, assumir que é no dia seguinte
            if fim_datetime <= inicio_datetime:
                fim_datetime += timedelta(days=1)
            
            # Próximo slot após salvamento seria current_timeslot + 15 min
            proximo_slot = self.contador.current_timeslot + timedelta(minutes=15)
            
            # Verificar se próximo slot ultrapassa horário fim
            if proximo_slot > fim_datetime:
                # Calcular quantos slots ainda são possíveis
                diferenca_minutos = (fim_datetime - self.contador.current_timeslot).total_seconds() / 60
                slots_restantes = int(diferenca_minutos // 15)
                
                if slots_restantes <= 0:
                    return False, f"Período da sessão finalizado. Horário fim: {horario_fim_str}", 0
                else:
                    return True, f"Último salvamento possível (fim: {horario_fim_str})", slots_restantes
            
            # Calcular quantos slots ainda são possíveis
            diferenca_total = (fim_datetime - self.contador.current_timeslot).total_seconds() / 60
            slots_restantes = int(diferenca_total // 15)
            
            return True, f"Dentro do período (fim: {horario_fim_str})", slots_restantes
            
        except Exception as ex:
            logging.error(f"Erro ao verificar se pode salvar sessão: {ex}")
            return True, "Erro na validação - permitindo salvar", -1

    def get_session_time_info(self):
        """
        Retorna informações detalhadas sobre o tempo da sessão.
        
        Returns:
            dict: Informações sobre tempo atual, limites e status
        """
        try:
            if not self.contador.sessao or not hasattr(self.contador, 'details'):
                return {"erro": "Sessão não inicializada"}
            
            pode_salvar, motivo, slots_restantes = self.can_save_session()
            
            info = {
                "sessao_id": self.contador.sessao,
                "horario_inicio": self.contador.details.get("HorarioInicio", "N/A"),
                "horario_fim": self.contador.details.get("HorarioFim", "Sem limite"),
                "periodo_atual": self.contador.current_timeslot.strftime("%H:%M"),
                "pode_salvar": pode_salvar,
                "motivo": motivo,
                "slots_restantes": slots_restantes,
                "proximo_slot": (self.contador.current_timeslot + timedelta(minutes=15)).strftime("%H:%M")
            }
            
            return info
            
        except Exception as ex:
            logging.error(f"Erro ao obter informações de tempo da sessão: {ex}")
            return {"erro": str(ex)}
            return False
