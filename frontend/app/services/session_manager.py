import logging
import json
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from database.models import Sessao, Categoria, Contagem
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

            # 2. Configurar detalhes da sessão
            self.contador.details = {
                "Pesquisador": session_data["pesquisador"],
                "Código": session_data["codigo"],
                "Ponto": session_data["ponto"],
                "HorarioInicio": session_data["horario_inicio"],
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


            # 5. Carregar binds e categorias
            binds = await self.contador.api_manager.load_binds(session_data["padrao"])
            if binds:
                self.contador.binds = binds

            categorias = await self.contador.api_manager.load_categories(session_data["padrao"])
            if categorias:
                self.save_categories_in_local(categorias)

            self.carregar_categorias_locais()

            # 6. Criar sessão no banco local
            nova_sessao = Sessao(
                sessao=self.contador.sessao,
                details=json.dumps(self.contador.details),
                padrao=session_data["padrao"],
                ativa=True
            )
            with self.contador.session_lock:
                self.contador.session.add(nova_sessao)
                self.contador.session.commit()

            # 7. Inicializar arquivo Excel
            try:
                success_excel = self.contador.excel_manager.initialize_excel_file()
                if not success_excel:
                    raise Exception("Falha ao criar arquivo Excel")
            except Exception as ex:
                logging.error(f"Erro ao criar arquivo Excel: {ex}")
                raise

            # 8. Registrar sessão no Django
            success_django = await self.contador.api_manager.send_session_to_django()
            if not success_django:
                logging.warning("Sessão criada localmente, mas não registrada no servidor.")

            # 9. Configurar UI
            if 'contagem' in self.contador.ui_components:
                self.contador.ui_components['contagem'].setup_ui()

            self.contador.tabs.selected_index = 1
            self.contador.tabs.tabs[1].content.visible = True

            # 10. Mostrar feedback
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
                    sessao.details = json.dumps(self.contador.details)
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
            sessao_ativa = self.contador.session.query(Sessao).filter_by(ativa=True).first()
            if not sessao_ativa:
                self.contador.setup_ui()
                return False

            self.contador.sessao = sessao_ativa.sessao  
            self.contador.details = json.loads(sessao_ativa.details) 

            # Configurar o timeslot atual
            hoje = datetime.now().date()
            
            # Primeiro tenta carregar o último período das contagens
            ultima_contagem = self.contador.session.query(Contagem)\
                .filter_by(sessao=self.contador.sessao)\
                .order_by(Contagem.periodo.desc())\
                .first()
                
            if ultima_contagem and ultima_contagem.periodo:
                # Se encontrou uma contagem com período, usa ela como base
                horario = datetime.strptime(ultima_contagem.periodo, "%H:%M").time()
                self.contador.current_timeslot = datetime.combine(hoje, horario) + timedelta(minutes=15)
                self.contador.details["current_timeslot"] = self.contador.current_timeslot.strftime("%H:%M")
            # Se não encontrou contagem com período, tenta usar o último período salvo nos detalhes
            elif "current_timeslot" in self.contador.details:
                horario = datetime.strptime(self.contador.details["current_timeslot"], "%H:%M").time()
                self.contador.current_timeslot = datetime.combine(hoje, horario)
            # Se não tem período salvo, usa o horário inicial
            elif "HorarioInicio" in self.contador.details:
                horario = datetime.strptime(self.contador.details["HorarioInicio"], "%H:%M").time()
                self.contador.current_timeslot = datetime.combine(hoje, horario)
            # Se não tem nada, usa o horário atual
            else:
                horario = datetime.now().time()
                self.contador.current_timeslot = datetime.combine(hoje, horario)
                self.contador.details["current_timeslot"] = self.contador.current_timeslot.strftime("%H:%M")
                logging.warning("Nenhum horário encontrado, usando horário atual")

            # Carregar último horário de salvamento
            if "last_save_time" in self.contador.details:
                self.contador.last_save_time = datetime.strptime(self.contador.details["last_save_time"], "%H:%M:%S")
            else:
                self.contador.last_save_time = None

            self.contador.setup_ui()  
            await asyncio.sleep(0.5)

            if sessao_ativa:
                self.contador.ui_components['inicio'].padrao_dropdown.value = sessao_ativa.padrao

            padrao_atual = self.contador.ui_components['inicio'].padrao_dropdown.value
            
            binds = await self.contador.api_manager.load_binds(padrao_atual)
            if binds:
                self.contador.binds = binds
            
            categorias = await self.contador.api_manager.load_categories(padrao_atual)
            if categorias:
                self.save_categories_in_local(categorias)
            
            self.carregar_categorias_locais()
            self.recover_active_countings()
            
            if 'contagem' in self.contador.ui_components:
                self.contador.ui_components['contagem'].setup_ui()

            self.contador.tabs.selected_index = 1
            self.contador.tabs.tabs[1].content.visible = True
            self.contador.page.window.scroll = ft.ScrollMode.AUTO
            self.contador.page.update()

            return True

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao carregar sessão ativa: {ex}")
            self.contador.setup_ui()
            self.contador.page.update()
            return False

    def save_to_db(self, veiculo, movimento):
        try:
            start_time = time.time()
            
            with self.session_lock:
                contagem_periodo = self.contagens.get((veiculo, movimento), 0)
                if contagem_periodo == 0:
                    return

                # Iniciar uma nova transação
                self.session.begin()
                
                try:
                    contagem = self.session.query(Contagem).filter_by(
                        sessao=self.contador.sessao,
                        veiculo=veiculo,
                        movimento=movimento
                    ).first()

                    # Obter o período atual
                    periodo_atual = self.contador.current_timeslot.strftime("%H:%M")

                    if contagem:
                        contagem.count = contagem_periodo
                        contagem.contagem_total += contagem_periodo
                        contagem.periodo = periodo_atual
                    else:
                        nova_contagem = Contagem(
                            sessao=self.contador.sessao,
                            veiculo=veiculo,
                            movimento=movimento,
                            count=contagem_periodo,
                            contagem_total=contagem_periodo,
                            periodo=periodo_atual
                        )
                        self.session.add(nova_contagem)
                    
                    # Commit da transação
                    self.session.commit()
                    
                except Exception as ex:
                    # Rollback em caso de erro
                    self.session.rollback()
                    raise
                
            end_time = time.time()
            elapsed_time = (end_time - start_time) * 1000  # Convertendo para milissegundos
            logging.info(f"Tempo para salvar contagem de {veiculo} - {movimento}: {elapsed_time:.2f}ms")
                
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao salvar contagem no DB: {ex}")
            with self.contador.session_lock:
                self.session.rollback()

    def recover_active_countings(self):
        try:
            contagens_db = self.session.query(Contagem).filter_by(sessao=self.contador.sessao).all()
            self.contagens.clear()

            for contagem in contagens_db:
                key = (contagem.veiculo, contagem.movimento)
                
                if contagem.count == 0:
                    continue

                self.contagens[key] = contagem.count

                if key in self.labels:
                    label_count, label_bind = self.labels[key]
                    label_count.value = str(self.contagens[key])
                    label_count.update()
                else:
                    logging.warning(f"[WARNING] Label não encontrada para {key}. Aguardando criação.")

        
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao recuperar contagens: {ex}")

    def save_categories_in_local(self, categorias):
        try:
            with self.contador.session_lock:
                for categoria_dict in categorias:

                    movimento = categoria_dict['movimento']

                    # Verificar se já existe
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
                        self.session.add(nova_categoria)
                    else:
                        logging.debug(f"[DEBUG] Categoria já existente no banco: {categoria_dict['veiculo']} - {movimento}")

                self.session.commit()
                logging.debug("[DEBUG] Commit realizado!")

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao salvar categorias no banco: {ex}")
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
        # Verificar se ui_components existe e tem o componente 'inicio'
        if not self.ui_components or 'inicio' not in self.ui_components:
            logging.warning("[WARNING] UI components não inicializados corretamente")
            return []
            
        padrao_atual = padrao or self.ui_components['inicio'].padrao_dropdown.value

        if not padrao_atual:
            logging.warning("[WARNING] Nenhum padrão selecionado")
            return []

        logging.debug(f"[DEBUG] Buscando categorias no banco para o padrão: {padrao_atual}")

        with self.contador.session_lock:
            try:
                self.categorias = (
                    self.session.query(Categoria)
                    .filter(Categoria.padrao == padrao_atual)
                    .order_by(Categoria.id)
                    .all()
                )
                self.session.commit()


                # Atualizar as categorias no contador também
                self.contador.categorias = self.categorias

                if 'contagem' in self.ui_components:
                    self.ui_components['contagem'].setup_ui()
                self.contador.page.update()

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
            
            # Atualizar status da sessão local
            with self.contador.session_lock:
                sessao_concluida = self.session.query(Sessao).filter_by(sessao=self.contador.sessao).first()
                if sessao_concluida:
                    sessao_concluida.ativa = False 
                    self.session.commit()
                else:
                    logging.warning("Sessão não encontrada no banco local")

            # Limpar o estado atual
            sessao_finalizada = self.contador.sessao  # Guardar para logging
            self.contador.sessao = None
            self.contador.details = {"Movimentos": []}
            self.contagens.clear()
            self.contador.binds.clear()
            self.contador.labels.clear()

            # Feedback visual
            snackbar = ft.SnackBar(
                content=ft.Text(f"Sessão {sessao_finalizada} finalizada com sucesso!"),
                bgcolor="blue"
            )
            self.contador.page.overlay.append(snackbar)
            snackbar.open = True

            # Reiniciar a aplicação
            self.contador.restart_app_after_end_session()
            
            # Voltar para a aba inicial
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
        with self.session_lock:
            self.session.query(Contagem).filter_by(sessao=self.contador.sessao).delete()
            self.session.commit()
        
        self.contador.contagens.clear()

    def update_session_time(self, current_timeslot, last_save_time):
        self.contador.last_save_time = last_save_time
        self.contador.details["last_save_time"] = last_save_time.strftime("%H:%M:%S")
        self.contador.current_timeslot = current_timeslot + timedelta(minutes=15)
        self.contador.details["current_timeslot"] = self.contador.current_timeslot.strftime("%H:%M")
