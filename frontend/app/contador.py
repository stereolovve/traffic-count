# app/contador.py
import flet as ft
import logging
import asyncio
import json
from database.models import Session, Categoria, Sessao, Historico, init_db
from sqlalchemy.exc import SQLAlchemyError
from app import listener
from utils.initializer import inicializar_variaveis, configurar_numpad_mappings
from openpyxl import Workbook
from utils.config import API_URL, EXCEL_BASE_DIR, DESKTOP_DIR
from loginregister.login import LoginPage
from app.ui.aba_config import AbaConfig
from app.ui.aba_contagem import AbaContagem
from app.ui.aba_historico import AbaHistorico
from app.ui.aba_inicio import AbaInicio
from app.ui.aba_edicao_periodos import AbaEdicaoPeriodos
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

# Configurar logging para este módulo
contador_logger = logging.getLogger('contador')
contador_logger.setLevel(logging.INFO)

# Initialize database with error handling
try:
    if not init_db():
        contador_logger.error("Database initialization failed in contador.py")
except Exception as e:
    contador_logger.error(f"Critical database error in contador.py: {e}")
    raise

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
        
        # Inicializar variáveis essenciais primeiro
        self.session = Session()
        self.session_lock = threading.Lock()
        self.ui_components = {}
        self.binds = {}  
        self.labels = {}  
        self.contagens = {}  
        self.categorias = []  
        self.details = {"Movimentos": []}
        self.period_observacoes = {}
        
        self.session_manager = SessionManager(self)
        self.history_manager = HistoryManager(self)
        self.api_manager = ApiManager(self)
        self.excel_manager = ExcelManager(self)
        self.ui_manager = UIManager(self)
        
        inicializar_variaveis(self)
        configurar_numpad_mappings(self)
        
        # Configurar UI
        self.setup_ui()
        self.page.update()
        
        asyncio.create_task(self._check_active_session())

    def validar_texto(self, texto):
        return re.sub(r'[^a-zA-Z0-9]', '', texto)

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def setup_ui(self):
        aba_inicio = AbaInicio(self)
        aba_contagem = AbaContagem(self)
        aba_edicao_periodos = AbaEdicaoPeriodos(self)
        
        self.ui_components['inicio'] = aba_inicio
        self.ui_components['contagem'] = aba_contagem
        self.ui_components['edicao_periodos'] = aba_edicao_periodos
        
        self.tabs = ft.Tabs(
            selected_index=0,  
            tabs=[
                ft.Tab(text="Início", content=aba_inicio),
                ft.Tab(text="Contador", content=aba_contagem),
                ft.Tab(text="", icon=ft.Icons.EDIT_DOCUMENT, content=aba_edicao_periodos),
                ft.Tab(text="Histórico", content=AbaHistorico(self)),
                ft.Tab(text="", icon=ft.Icons.SETTINGS, content=AbaConfig(self)),
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
        
    async def _check_active_session(self):
        """Verifica se existe uma sessão ativa ao inicializar o aplicativo"""
        try:
            await self.session_manager.load_active_session()
        except Exception as ex:
            logging.error(f"Erro ao verificar sessão ativa: {ex}")

    async def load_active_session(self):
        """Método público para carregar sessão ativa (mantido para compatibilidade)"""
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

    def test_save_counting(self):
        return self.session_manager.test_save_counting()

    def test_increment_and_save(self):
        try:
            
            self.increment("Leves", "a")
            self.check_database_countings()
            
            return True
        except Exception as ex:
            print(f"[TEST] Erro no teste: {ex}")
            return False

    def check_database_countings(self):
        return self.session_manager.check_database_countings()

    def save_to_db(self, veiculo, movimento):
        self.session_manager.save_to_db(veiculo, movimento)

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

    def reload_binds_from_api(self, pattern_type):
        """Recarrega binds da API e atualiza a UI imediatamente"""
        try:
            print(f"🔧 DEBUG: reload_binds_from_api chamado para pattern_type: {pattern_type}")
            
            # Usar o BindManager para recarregar
            bind_manager = BindManager(self.page, self)
            
            # Executar de forma síncrona usando asyncio.run em thread
            def run_reload():
                try:
                    import asyncio
                    new_binds_list = asyncio.run(bind_manager.carregar_categorias(pattern_type))
                    
                    if new_binds_list:
                        # Converter para dict
                        new_binds = {}
                        for categoria in new_binds_list:
                            if isinstance(categoria, dict):
                                veiculo = categoria.get('veiculo')
                                bind = categoria.get('bind')
                                if veiculo and bind:
                                    new_binds[veiculo] = bind
                        
                        print(f"🔧 DEBUG: Novos binds: {new_binds}")
                        
                        # Atualizar no thread principal
                        old_binds = self.binds.copy()
                        self.binds = new_binds
                        
                        print(f"🔧 DEBUG: Binds atualizados de {old_binds} para {self.binds}")
                        
                        # Atualizar UI usando método existente
                        self.page.run_task(self.atualizar_binds)
                        
                        logging.info("Binds recarregados da API e UI atualizada")
                    else:
                        print("🔧 DEBUG: Nenhum bind retornado da API")
                        
                except Exception as ex:
                    print(f"🔧 DEBUG: Erro em run_reload: {ex}")
            
            # Executar em thread separado
            threading.Thread(target=run_reload, daemon=True).start()
            
        except Exception as ex:
            print(f"🔧 DEBUG: Erro em reload_binds_from_api: {ex}")
            logging.error(f"Erro ao recarregar binds da API: {ex}")

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
            categorias = novos_binds  # Fix: assign categorias from argument
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
        """Incremento otimizado - evita operações custosas desnecessárias"""
        key = (veiculo, movimento)
        valor_anterior = self.contagens.get(key, 0)
        self.contagens[key] = valor_anterior + 1
        
        # ✅ Atualização otimizada - apenas o label específico
        self.update_labels(veiculo, movimento)
        
        # ✅ Salvar no banco de forma assíncrona para não bloquear UI
        try:
            self.save_to_db(veiculo, movimento)
            
            # ✅ Buscar categoria de forma mais eficiente (cache se necessário)
            categoria = self.session.query(Categoria).filter_by(
                padrao=self.ui_components['inicio'].padrao_dropdown.value,
                veiculo=veiculo,
                movimento=movimento
            ).first()
            
            if categoria:
                self.history_manager.salvar_historico(categoria.id, movimento, "increment")
            
            # ✅ Log apenas debug para reduzir overhead
            logging.debug(f"✅ Incremento: {veiculo}-{movimento} = {self.contagens[key]}")
            
        except Exception as ex:
            logging.error(f"Erro no incremento de {veiculo}-{movimento}: {ex}")
            # ✅ Rollback do incremento em caso de erro
            self.contagens[key] = valor_anterior

    def decrement(self, veiculo, movimento):
        """Decremento otimizado - evita operações custosas desnecessárias"""
        try:
            key = (veiculo, movimento)
            valor_anterior = self.contagens.get(key, 0)
            
            # ✅ Não decrementar se já for 0
            if valor_anterior <= 0:
                logging.debug(f"Decremento ignorado: {veiculo}-{movimento} já é 0")
                return
            
            # ✅ Atualizar valor
            self.contagens[key] = valor_anterior - 1
            
            # ✅ Atualização otimizada - apenas o label específico
            self.update_labels(veiculo, movimento)
            
            # ✅ Buscar categoria de forma mais eficiente
            categoria = self.session.query(Categoria).filter_by(
                padrao=self.ui_components['inicio'].padrao_dropdown.value,
                veiculo=veiculo,
                movimento=movimento
            ).first()
            
            if not categoria:
                logging.warning(f"Categoria não encontrada para {veiculo}-{movimento}")
                # ✅ Rollback em caso de categoria não encontrada
                self.contagens[key] = valor_anterior
                return

            # ✅ Salvar no banco
            self.save_to_db(veiculo, movimento)
            self.history_manager.salvar_historico(categoria.id, movimento, "decrement")
            
            # ✅ Log apenas debug para reduzir overhead
            logging.debug(f"✅ Decremento: {veiculo}-{movimento} = {self.contagens[key]}")

        except Exception as ex:
            logging.error(f"Erro ao decrementar {veiculo}-{movimento}: {ex}")
            # ✅ Rollback em caso de erro
            if 'valor_anterior' in locals():
                self.contagens[key] = valor_anterior

    def update_labels(self, veiculo, movimento):
        """Atualização otimizada de labels - evita redundância e page.update() custoso"""
        key = (veiculo, movimento)
        new_value = str(self.contagens.get(key, 0))
        
        if key in self.labels:
            label_count, label_bind = self.labels[key]
            # ✅ Só atualizar se o valor realmente mudou
            if label_count.value != new_value:
                label_count.value = new_value
                label_count.update()
            # ✅ REMOVIDO: page.update() custoso após cada incremento
        else:
            logging.debug(f"Label não encontrada para {key}. Será criado no próximo setup_ui.")
        
        # ✅ Delegar para o componente de contagem fazer sua própria atualização
        if 'contagem' in self.ui_components:
            self.ui_components['contagem'].update_labels(veiculo, movimento)

    def save_contagens(self, e):
        try:
            now = datetime.now()
            
            # ✅ NOVA VALIDAÇÃO: Verificar se pode salvar considerando horário fim
            pode_salvar, motivo, slots_restantes = self.session_manager.can_save_session()
            
            if not pode_salvar:
                # Mostrar diálogo informativo sobre limite atingido
                def on_close_dialog(e):
                    dialog.open = False
                    self.page.update()
                
                def on_force_save(e):
                    dialog.open = False
                    self.page.update()
                    # Forçar salvamento mesmo fora do horário
                    self.page.run_task(self.api_manager.send_count_to_django)
                    self._perform_save(now)
                
                dialog = ft.AlertDialog(
                    title=ft.Text("⏰ Limite de Horário Atingido", color=ft.Colors.ORANGE_700),
                    content=ft.Column([
                        ft.Text(motivo, size=16),
                        ft.Divider(),
                        ft.Text("Informações da sessão:", weight=ft.FontWeight.BOLD),
                        ft.Text(f"• Início: {self.details.get('HorarioInicio', 'N/A')}"),
                        ft.Text(f"• Fim: {self.details.get('HorarioFim', 'N/A')}"),
                        ft.Text(f"• Período atual: {self.current_timeslot.strftime('%H:%M')}"),
                        ft.Text(f"• Próximo período seria: {(self.current_timeslot + timedelta(minutes=15)).strftime('%H:%M')}"),
                        ft.Divider(),
                        ft.Text("⚠️ O salvamento avançaria além do horário de fim da sessão.", 
                               color=ft.Colors.ORANGE_700),
                        ft.Text("Deseja mesmo salvar e finalizar a sessão automaticamente?")
                    ], tight=True, spacing=5),
                    actions=[
                        ft.TextButton("Salvar e Finalizar", 
                                     on_click=on_force_save,
                                     style=ft.ButtonStyle(color=ft.Colors.ORANGE_700)),
                        ft.TextButton("Cancelar", on_click=on_close_dialog),
                    ],
                )
                self.page.overlay.append(dialog)
                dialog.open = True
                self.page.update()
                return
            
            # Mostrar informação sobre slots restantes se aplicável
            if slots_restantes > 0 and slots_restantes <= 3:
                # Aviso quando restam poucos slots
                info_msg = f"⚠️ Atenção: Restam apenas {slots_restantes} período(s) até o fim da sessão ({self.details.get('HorarioFim', 'N/A')})"
                snackbar = ft.SnackBar(
                    content=ft.Text(info_msg),
                    bgcolor=ft.Colors.ORANGE_600,
                    duration=3000
                )
                self.page.overlay.append(snackbar)
                snackbar.open = True
                self.page.update()
            
            # Verificar salvamento recente (lógica existente)
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

            # Prosseguir com salvamento normal
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

                try:
                    await self.api_manager.send_count_to_django()
                except Exception as api_ex:
                    logging.error(f"Erro ao enviar para o Django: {api_ex}")

                if not self.excel_manager.save_contagens(self.current_timeslot):
                    raise Exception("Falha ao salvar no Excel")

                self.last_save_time = now
                self.details["last_save_time"] = self.last_save_time.strftime("%H:%M:%S")
                
                self.current_timeslot += timedelta(minutes=15)
                self.details["current_timeslot"] = self.current_timeslot.strftime("%H:%M")
                
                self.save_session()

                if 'contagem' in self.ui_components:
                    aba_contagem = self.ui_components['contagem']
                    aba_contagem.update_last_save_label(self.last_save_time)
                    aba_contagem.update_period_status()

                # Limpar dados atuais (memória + sessão)
                for key in self.contagens:
                    self.contagens[key] = 0
                    if key in self.labels:
                        label_count, _ = self.labels[key]
                        label_count.value = "0"
                        label_count.update()

                # Limpar contagens salvas na sessão também
                try:
                    with self.session_lock:
                        sessao_obj = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
                        if sessao_obj:
                            sessao_obj.contagens_atuais = None  # Limpar contagens salvas
                            self.session.commit()
                except Exception as clear_ex:
                    logging.error(f"Erro ao limpar contagens da sessão: {clear_ex}")

                self.history_manager.salvar_historico(None, "TODOS", "salvamento")

                # ✅ VALIDAÇÃO: Verificar status da sessão após salvamento (SEM finalização automática)
                pode_salvar_proximo, motivo, slots_restantes = self.session_manager.can_save_session()
                
                if not pode_salvar_proximo:
                    # Sessão atingiu o limite - apenas avisar (NÃO finalizar automaticamente)
                    logging.info(f"Sessão atingiu limite de horário: {motivo}")
                    
                    snackbar = ft.SnackBar(
                        content=ft.Text("⚠️ Último período salvo! Para continuar além do horário, edite a sessão."), 
                        bgcolor=ft.Colors.ORANGE_700,
                        duration=4000
                    )
                    self.page.overlay.append(snackbar)
                    snackbar.open = True
                    self.page.update()
                    
                elif slots_restantes == 1:
                    # Último período disponível - avisar usuário
                    snackbar = ft.SnackBar(
                        content=ft.Text("⚠️ ATENÇÃO: Próximo salvamento será o último do período configurado!"), 
                        bgcolor=ft.Colors.ORANGE_600,
                        duration=4000
                    )
                    self.page.overlay.append(snackbar)
                    snackbar.open = True
                    self.page.update()
                else:
                    # Salvamento normal
                    snackbar = ft.SnackBar(ft.Text("Contagens salvas e enviadas com sucesso!"), bgcolor="GREEN")
                    self.page.overlay.append(snackbar)
                    snackbar.open = True
                    self.page.update()

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
                self.ui_components['contagem'].force_ui_update()
            self.page.update()

    async def load_binds(self, pattern_type=None):
        if pattern_type is None:
            pattern_type = self.ui_components['inicio'].padrao_dropdown.value
        
        binds = await self.api_manager.load_binds(pattern_type)
        if binds:
            self.binds = binds
            await self.atualizar_binds()
            if 'contagem' in self.ui_components:
                self.ui_components['contagem'].force_ui_update()
            self.page.update()