# app/contador.py
import flet as ft
import logging
import asyncio
import json
from database.models import Session, Categoria, Sessao, Contagem, Historico, init_db
from sqlalchemy.exc import SQLAlchemyError
from app import listener
from utils.initializer import inicializar_variaveis, configurar_numpad_mappings
from openpyxl import Workbook
from utils.config import API_URL, EXCEL_BASE_DIR, DESKTOP_DIR
from loginregister.login import LoginPage
from utils.period import format_period
from app.ui.aba_ajuda import AbaAjuda
from app.ui.aba_relatorio import AbaRelatorio
from app.ui.aba_config import AbaConfig
from app.ui.aba_contagem import AbaContagem
from app.ui.aba_historico import AbaHistorico
from app.ui.aba_inicio import AbaInicio
from loginregister.register import RegisterPage
from pynput import keyboard
from time import sleep
import pandas as pd
from datetime import datetime, timedelta, time
import threading, os, re, httpx, openpyxl
from utils.change_binds import abrir_configuracao_binds, BindManager
from openpyxl.utils.dataframe import dataframe_to_rows
from utils.api import async_api_request
from app.services.session_manager import SessionManager
from app.services.history_manager import HistoryManager
from app.services.api_manager import ApiManager
from app.services.excel_manager import ExcelManager
from app.services.ui_manager import UIManager
from sqlalchemy.sql import text

logging.getLogger(__name__).setLevel(logging.ERROR)

class ContadorPerplan(ft.Column):
    def __init__(self, page, username, app):
        super().__init__()
        self.tokens = app.tokens 
        self.page = page
        self.username = username
        self.period_status_label = ft.Text("")
        self.app = app
        self.pressed_keys = set()
        self.user_preferences = app.user_preferences
        self.last_save_time = None
        self.period_observacao = ""
        self.listener = None  
        self.ultima_contagem = {}
        self.movimento_tabs = {}
        
        # Inicializar banco de dados
        try:
            init_db()
            logging.info("Banco de dados inicializado com sucesso")
        except Exception as e:
            error_msg = f"Erro ao inicializar banco de dados: {str(e)}"
            logging.error(error_msg)
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("Erro ao conectar ao banco de dados. Verifique as configurações."),
                    bgcolor=ft.colors.RED
                )
            )
            # Voltar para a tela de login
            self.app.show_login_page()
            return
        
        # Inicializar variáveis essenciais primeiro
        try:
            self.session = Session()
            self.session_lock = threading.Lock()
            self.ui_components = {}
            self.binds = {}  
            self.labels = {}  
            self.contagens = {}  
            self.categorias = []  
            self.details = {"Movimentos": []}
            self.period_observacoes = {}
            
            # Inicializar serviços
            self.session_manager = SessionManager(self)
            self.history_manager = HistoryManager(self)
            self.api_manager = ApiManager(self)
            self.excel_manager = ExcelManager(self)
            self.ui_manager = UIManager(self)
            
            # Inicializar outras configurações
            inicializar_variaveis(self)
            configurar_numpad_mappings(self)
            
            # Configurar UI
            self.setup_ui()
            self.page.update()
            
            # Carregar sessão ativa
            asyncio.create_task(self.load_active_session())
        except Exception as e:
            error_msg = f"Erro ao inicializar contador: {str(e)}"
            logging.error(error_msg)
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("Erro ao inicializar o contador. Tente novamente."),
                    bgcolor=ft.colors.RED
                )
            )
            self.app.show_login_page()

    def validar_texto(self, texto):
        return re.sub(r'[^a-zA-Z0-9]', '', texto)

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def setup_ui(self):
        aba_inicio = AbaInicio(self)
        aba_contagem = AbaContagem(self)
        
        self.ui_components['inicio'] = aba_inicio
        self.ui_components['contagem'] = aba_contagem
        
        self.tabs = ft.Tabs(
            selected_index=0,  
            tabs=[
                ft.Tab(text="Início", content=aba_inicio),
                ft.Tab(text="Contador", content=aba_contagem),
                ft.Tab(text="Histórico", content=AbaHistorico(self)),
                ft.Tab(text="", icon=ft.icons.SETTINGS, content=AbaConfig(self)),
                ft.Tab(text="", icon=ft.icons.HELP, content=AbaAjuda(self)),
                ft.Tab(text="Relatório", icon=ft.icons.TABLE_CHART, content=AbaRelatorio(self)),
            ],
            expand=1
        )
        self.controls.clear()
        self.controls.append(self.tabs)
        self.page.window.scroll = ft.ScrollMode.AUTO 
        self.page.window.width = 800
        self.page.window.height = 700
        self.page.update()

        if hasattr(self, "sessao") and self.sessao:
            self.tabs.selected_index = 1 
            self.tabs.tabs[1].content.visible = True
        else:
            self.tabs.tabs[1].content.visible = False 
    
    def show_loading(self, message="Carregando..."):
        progress = ft.ProgressRing()
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(message),
            content=progress,
            actions=[]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        return dialog

    def hide_loading(self, banner):
        dialog = banner
        dialog.open = False
        self.page.update()
        self.page.dialog = None

    async def create_session(self, session_data):
        await self.session_manager.create_session(session_data)
        await self.api_manager.send_session_to_django()
        
    async def load_active_session(self):
        await self.session_manager.load_active_session()

    async def end_session(self):
        await self.session_manager.end_session()

    def save_session(self):
        self.session_manager.save_session()

    def restart_app_after_end_session(self):
        try:
            logging.info("Iniciando restart da aplicação...")
            
            if hasattr(self, 'listener') and self.listener:
                self.stop_listener()
                logging.info("Listener parado com sucesso")

            self.sessao = None
            self.details = {"Movimentos": []}
            self.contagens = {}
            self.binds = {}
            self.labels = {}
                
            self.setup_ui()
            
            if len(self.tabs.tabs) > 1:
                self.tabs.tabs[1].content.visible = False
            
            self.tabs.selected_index = 0
            
            logging.info("Aplicação reiniciada com sucesso")
        except Exception as ex:
            logging.error(f"Erro ao reiniciar aplicação: {ex}")

    def save_to_db(self, veiculo, movimento):
        try:
            with self.session_lock:
                # Criar uma nova sessão para esta operação
                session = Session()
                try:
                    # Definir timeout para esta transação
                    session.execute(text("SET LOCAL statement_timeout = '10s'"))
                    session.execute(text("SET LOCAL lock_timeout = '10s'"))
                    
                    # Buscar ou criar contagem com lock
                    contagem = session.query(Contagem).filter_by(
                        sessao=self.sessao,
                        veiculo=veiculo,
                        movimento=movimento
                    ).with_for_update(skip_locked=True).first()

                    if not contagem:
                        contagem = Contagem(
                            sessao=self.sessao,
                            veiculo=veiculo,
                            movimento=movimento,
                            count=0,
                            periodo=self.details.get("current_timeslot", "00:00")
                        )
                        session.add(contagem)

                    # Atualizar contagem
                    contagem.count = self.contagens.get((veiculo, movimento), 0)
                    session.commit()
                    
                    logging.info(f"✅ Contagem salva no banco para {veiculo} - {movimento}")
                    
                except Exception as e:
                    session.rollback()
                    raise
                finally:
                    session.close()
                
        except Exception as ex:
            logging.error(f"Erro ao salvar no banco: {ex}")
            # Não propaga o erro para não travar a interface

    def recover_active_countings(self):
        self.session_manager.recover_active_countings()

    async def atualizar_binds(self):
        try:
            for veiculo, bind in self.binds.items():
                for movimento in self.details.get("Movimentos", []):
                    key = (veiculo, movimento)
                    if key in self.labels:  
                        if isinstance(self.labels[key], list) and len(self.labels[key]) >= 2:
                            label_bind = self.labels[key][1]  
                            label_bind.value = f"({bind})"
                            label_bind.update()
        
            self.page.update()
            
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao atualizar binds: {ex}")

    def atualizar_bind_todos_movimentos(self, veiculo, novo_bind):
        if not novo_bind:
            logging.error("Bind inválido. Não foi possível atualizar.")
            return
        try:
            categorias = self.session.query(Categoria).filter_by(veiculo=veiculo).all()
            if not categorias:
                logging.warning(f"Nenhuma categoria encontrada para o veículo: {veiculo}")
                return

            for categoria in categorias:
                categoria.bind = novo_bind
            
            # Atualizar o dicionário de binds
            self.binds[veiculo] = novo_bind
            
            self.session.commit()
            
            # Atualizar os labels na UI
            for key in self.labels:
                if key[0] == veiculo:  # Se o veículo corresponde
                    label_count, label_bind = self.labels[key]
                    label_bind.value = f"({novo_bind})"
                    label_bind.update()

            # Atualizar a UI completa
            self.page.update()

            logging.info(f"Bind atualizado para todos os movimentos do veículo: {veiculo}")
            snackbar = ft.SnackBar(
                content=ft.Text(f"Bind atualizado para {veiculo}: {novo_bind}"),
                bgcolor="green"
            )
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

        except SQLAlchemyError as ex:
            logging.error(f"Erro ao atualizar bind no banco: {ex}")
            self.session.rollback()

    def save_new_binds(self, novos_binds):
        try:
            with self.session_lock:
                for cat in categorias:

                    nova_categoria = Categoria(
                        padrao=cat["pattern_type"],
                        veiculo=cat["veiculo"],
                        movimento=cat["movimento"],
                        bind=cat.get("bind", "N/A")
                    )
                    self.session.add(nova_categoria)

                self.session.commit()
                logging.info("[INFO] Categorias salvas no banco com sucesso!")

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao salvar categorias no banco: {ex}")
            self.session.rollback()

    def increment(self, veiculo, movimento):
        try:
            # Incrementar contagem na memória primeiro
            key = (veiculo, movimento)
            self.contagens[key] = self.contagens.get(key, 0) + 1
            
            # Atualizar UI imediatamente
            self.update_labels(veiculo, movimento)
            
            # Criar uma nova sessão para esta operação
            session = Session()
            try:
                # Buscar categoria
                categoria = session.query(Categoria).filter_by(
                    padrao=self.ui_components['inicio'].padrao_dropdown.value,
                    veiculo=veiculo,
                    movimento=movimento
                ).first()
                
                if not categoria:
                    logging.warning(f"[WARNING] Categoria não encontrada para veiculo={veiculo}, movimento={movimento}")
                    return

                # Registrar no histórico
                self.history_manager.salvar_historico(categoria.id, movimento, "increment")
                
                # Salvar no banco em uma transação separada
                try:
                    contagem = session.query(Contagem).filter_by(
                        sessao=self.sessao,
                        veiculo=veiculo,
                        movimento=movimento
                    ).first()

                    if not contagem:
                        contagem = Contagem(
                            sessao=self.sessao,
                            veiculo=veiculo,
                            movimento=movimento,
                            count=0,
                            periodo=self.details.get("current_timeslot", "00:00")
                        )
                        session.add(contagem)

                    contagem.count = self.contagens[key]
                    session.commit()
                    logging.info(f"✅ Contagem incrementada para {veiculo} - {movimento}")
                except Exception as db_error:
                    session.rollback()
                    logging.error(f"Erro ao salvar no banco: {db_error}")
                    # Não propaga o erro para não travar a interface
                
            except Exception as e:
                session.rollback()
                raise
            finally:
                session.close()

        except Exception as ex:
            logging.error(f"Erro ao incrementar: {ex}")
            # Não propaga o erro para não travar a interface

    def decrement(self, veiculo, movimento):
        try:
            # Decrementar contagem na memória primeiro
            key = (veiculo, movimento)
            current_count = self.contagens.get(key, 0)
            if current_count > 0:
                self.contagens[key] = current_count - 1
                
                # Atualizar UI imediatamente
                self.update_labels(veiculo, movimento)
                
                # Criar uma nova sessão para esta operação
                session = Session()
                try:
                    # Buscar categoria
                    categoria = session.query(Categoria).filter_by(
                        padrao=self.ui_components['inicio'].padrao_dropdown.value,
                        veiculo=veiculo,
                        movimento=movimento
                    ).first()
                    
                    if not categoria:
                        logging.warning(f"[WARNING] Categoria não encontrada para veiculo={veiculo}, movimento={movimento}")
                        return

                    # Registrar no histórico
                    self.history_manager.salvar_historico(categoria.id, movimento, "decrement")
                    
                    # Salvar no banco em uma transação separada
                    try:
                        contagem = session.query(Contagem).filter_by(
                            sessao=self.sessao,
                            veiculo=veiculo,
                            movimento=movimento
                        ).first()

                        if not contagem:
                            contagem = Contagem(
                                sessao=self.sessao,
                                veiculo=veiculo,
                                movimento=movimento,
                                count=0,
                                periodo=self.details.get("current_timeslot", "00:00")
                            )
                            session.add(contagem)

                        contagem.count = self.contagens[key]
                        session.commit()
                        logging.info(f"✅ Contagem decrementada para {veiculo} - {movimento}")
                    except Exception as db_error:
                        session.rollback()
                        logging.error(f"Erro ao salvar no banco: {db_error}")
                        # Não propaga o erro para não travar a interface
                
                except Exception as e:
                    session.rollback()
                    raise
                finally:
                    session.close()

        except Exception as ex:
            logging.error(f"Erro ao decrementar: {ex}")
            # Não propaga o erro para não travar a interface

    def update_labels(self, veiculo, movimento):
        key = (veiculo, movimento)
        if key in self.labels:
            label_count, label_bind = self.labels[key]
            label_count.value = str(self.contagens.get(key, 0))
            label_count.update()
        else:
            logging.warning(f"[WARNING] Label não encontrada para {key}. Aguardando criação.")

    def save_contagens(self, e):
        try:
            now = datetime.now()
            
            if hasattr(self, "last_save_time") and self.last_save_time is not None:
                time_since_last_save = now - self.last_save_time
                if time_since_last_save < timedelta(minutes=5):
                    def on_confirm_save(e):
                        dialog.open = False
                        self.page.update()
                        self.page.run_task(self.api_manager.send_count_to_django)
                        self._perform_save(now)  

                    def on_cancel_save(e):
                        dialog.open = False
                        self.page.update()

                    dialog = ft.AlertDialog(
                        title=ft.Text("Confirmar Salvamento"),
                        content=ft.Text("Você salvou recentemente. Deseja salvar novamente?"),
                        actions=[
                            ft.TextButton("Sim", on_click=on_confirm_save),
                            ft.TextButton("Cancelar", on_click=on_cancel_save),
                        ],
                    )
                    self.page.overlay.append(dialog)
                    dialog.open = True
                    self.page.update()
                    return 

            self.page.run_task(self.api_manager.send_count_to_django)
            self._perform_save(now)

        except Exception as ex:
            logging.error(f"Erro ao salvar contagens: {ex}")
            snackbar = ft.SnackBar(ft.Text("Erro ao salvar contagens."), bgcolor="RED")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

    def _perform_save(self, now):
        banner = self.show_loading("Salvando contagens...")
        async def salvar():
            try:
                # 1. Configurar timeslot
                if not hasattr(self, "current_timeslot") or self.current_timeslot is None:
                    if "current_timeslot" in self.details:
                        hoje = datetime.now().date()
                        horario = datetime.strptime(self.details["current_timeslot"], "%H:%M").time()
                        self.current_timeslot = datetime.combine(hoje, horario)
                    elif "HorarioInicio" in self.details:
                        hoje = datetime.now().date()
                        horario = datetime.strptime(self.details["HorarioInicio"], "%H:%M").time()
                        self.current_timeslot = datetime.combine(hoje, horario)
                    else:
                        self.current_timeslot = datetime.now().replace(second=0, microsecond=0)

                # 2. Enviar para o Django (não falhar se der erro)
                try:
                    await self.api_manager.send_count_to_django()
                except Exception as api_ex:
                    logging.error(f"Erro ao enviar para o Django: {api_ex}")

                # 3. Salvar no Excel
                if not self.excel_manager.save_contagens(self.current_timeslot):
                    raise Exception("Falha ao salvar no Excel")

                # 4. Atualizar estado da sessão
                self.last_save_time = now
                self.details["last_save_time"] = self.last_save_time.strftime("%H:%M:%S")
                
                # Atualizar o período para o próximo
                self.current_timeslot += timedelta(minutes=15)
                self.details["current_timeslot"] = self.current_timeslot.strftime("%H:%M")
                
                # Salvar a sessão com os novos dados
                self.save_session()

                # 5. Atualizar UI
                if 'contagem' in self.ui_components:
                    aba_contagem = self.ui_components['contagem']
                    aba_contagem.update_last_save_label(self.last_save_time)
                    aba_contagem.update_period_status()

                # 6. Limpar dados atuais
                with self.session_lock:
                    self.session.query(Contagem).filter_by(sessao=self.sessao).delete()
                    self.session.commit()

                for key in self.contagens:
                    self.contagens[key] = 0
                    if key in self.labels:
                        label_count, _ = self.labels[key]
                        label_count.value = "0"
                        label_count.update()

                # 7. Registrar no histórico
                self.history_manager.salvar_historico(None, "TODOS", "salvamento")

                # 8. Mostrar feedback
                snackbar = ft.SnackBar(ft.Text("Contagens salvas e enviadas com sucesso!"), bgcolor="GREEN")
                self.page.overlay.append(snackbar)
                snackbar.open = True
                self.page.update()

                # Limpar observações após salvamento
                self.period_observacoes.clear()

            except ValueError as ve:
                logging.error(f"Erro de validação: {ve}")
                self.ui_manager.show_error_message(str(ve))
            except Exception as ex:
                logging.error(f"Erro ao salvar contagens: {ex}")
                self.ui_manager.show_error_message(f"Erro ao salvar contagens: {str(ex)}")
            finally:
                self.hide_loading(banner)
        self.page.run_task(salvar)

    def on_key_press(self, key):
        listener.on_key_press(self, key)

    def on_key_release(self, key):
        try:
            if hasattr(self, "pressed_keys"):
                self.pressed_keys.discard(key)
            else:
                logging.warning("[WARNING] pressed_keys não estava inicializado! Criando novamente.")
                self.pressed_keys = set()
        except Exception as ex:
            logging.error(f"Erro no on_key_release: {ex}")

    def start_listener(self):
        if not hasattr(self, "pressed_keys"):
            self.pressed_keys = set()

        if self.listener is None:
            self.listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
            self.listener.start()

    def stop_listener(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
            self.pressed_keys.clear()

    def save_categories_in_local(self, categorias):
        self.session_manager.save_categories_in_local(categorias)

    def _carregar_binds_locais(self, padrao=None):
        self.session_manager._carregar_binds_locais(padrao)
            
    def logout_user(self, e):
        try:
            # Parar o listener se estiver ativo
            if hasattr(self, 'listener') and self.listener:
                self.stop_listener()
                logging.info("Listener parado durante logout")
                
            # Chamar reset_app do app principal para voltar à tela de login
            if hasattr(self, 'app') and self.app:
                self.app.reset_app()  # Este método cuidará de todo o processo
                logging.info("Processo de logout iniciado")
            else:
                logging.error("Referência ao app principal não encontrada")
                # Fallback: mostra mensagem de erro
                self.ui_manager.show_error_message("Erro no logout: referência ao app principal não encontrada")

        except Exception as ex:
            logging.error(f"Erro ao deslogar: {ex}")
            self.ui_manager.show_error_message(f"Erro ao deslogar: {str(ex)}")

    def show_dialog_end_session(self, e):
        self.session_manager.show_dialog_end_session(e)

    def carregar_categorias_locais(self, padrao=None):
        self.session_manager.carregar_categorias_locais(padrao)

    def inicializar_arquivo_excel(self):
        return self.excel_manager.initialize_excel_file()

    async def load_categories(self, pattern_type):
        categorias = await self.api_manager.load_categories(pattern_type)
        if categorias:
            self.save_categories_in_local(categorias)
            if 'contagem' in self.ui_components:
                self.ui_components['contagem'].setup_ui()
            self.page.update()

    async def load_binds(self, pattern_type=None):
        if pattern_type is None:
            pattern_type = self.ui_components['inicio'].padrao_dropdown.value
        
        binds = await self.api_manager.load_binds(pattern_type)
        if binds:
            self.binds = binds
            await self.atualizar_binds()
            if 'contagem' in self.ui_components:
                self.ui_components['contagem'].setup_ui()
            self.page.update()