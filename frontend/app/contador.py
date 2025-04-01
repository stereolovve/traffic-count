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
from app.services.django_service import DjangoService
from app.services.session_manager import SessionManager
logging.getLogger(__name__).setLevel(logging.ERROR)

init_db()

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
        
        # Inicializar serviços
        self.session_manager = SessionManager(self)
        self.django_service = DjangoService(app.tokens)
        
        # Inicializar outras configurações
        inicializar_variaveis(self)
        configurar_numpad_mappings(self)
        
        # Configurar UI
        self.setup_ui()
        self.page.update()
        
        # Carregar sessão ativa
        asyncio.create_task(self.load_active_session())

    def validar_texto(self, texto):
        return re.sub(r'[^a-zA-Z0-9]', '', texto)

    async def api_get(self, url):
        headers = {}
        if self.tokens and 'access' in self.tokens:
            headers["Authorization"] = f"Bearer {self.tokens['access']}"
        return await async_api_request(url=url, method="GET", headers=headers)

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    # ------------------------ SETUP UI ------------------------
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
        banner = ft.Banner(
            content=ft.Text(message),
            leading=progress,
            bgcolor=ft.colors.BLUE_100,
            actions=[
                ft.TextButton("Aguarde...", disabled=True)
            ] 
        )
        self.page.overlay.append(banner)
        self.page.update()
        return banner

    def hide_loading(self, banner):
        if banner in self.page.overlay:
            self.page.overlay.remove(banner)
            self.page.update()

    async def criar_sessao(self, session_data):
        await self.session_manager.create_session(session_data)

    async def load_active_session(self):
        await self.session_manager.load_active_session()

    async def end_session(self):
        await self.session_manager.end_session()

    def save_session(self):
        self.session_manager.save_session()
        

    async def send_session_to_django(self):
        try:
            logging.info(f"Enviando dados da sessão {self.sessao} para o Django...")
            
            if not self.sessao:
                logging.error("❌ Não foi possível enviar sessão ao Django: self.sessao está vazio!")
                return False

            logging.info(f"Details disponíveis: {self.details}")
            
            headers = {
                "Authorization": f"Bearer {self.tokens['access']}" if self.tokens and 'access' in self.tokens else "",
                "Content-Type": "application/json"
            }

            codigo = self.details.get("Código", "")
            if not codigo:
                codigo = f"AUTO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            ponto = self.details.get("Ponto", "")
            if not ponto:
                ponto = f"PONTO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            data_ponto = self.details.get("Data do Ponto", "")
            if not data_ponto:
                data_ponto = datetime.now().strftime("%d/%m/%Y")
            
            horario_inicio = self.details.get("HorarioInicio", "")
            if not horario_inicio:
                horario_inicio = datetime.now().strftime("%H:%M")

            movimentos = self.details.get("Movimentos", [])
            if isinstance(movimentos, set):
                movimentos = list(movimentos)
            if not movimentos:
                movimentos = ["A"]

            payload = {
                "sessao": self.sessao,
                "codigo": codigo,
                "ponto": ponto,
                "data": data_ponto,
                "horario_inicio": horario_inicio,
                "usuario": self.username,
                "ativa": True,
                "movimentos": movimentos
            }

            logging.info(f"Payload completo: {payload}")

            url = f"{API_URL}/contagens/registrar-sessao/"
            logging.info(f"Enviando para URL: {url}")
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                logging.info(f"Resposta do server: {response.status_code} - {response.text}")

            if response.status_code in [200, 201]:
                logging.info(f"✅ Detalhes da sessão {self.sessao} enviados ao Django com sucesso!")
                return True
            else:
                logging.error(f"❌ Falha ao enviar detalhes da sessão: {response.status_code} - {response.text}")
                return False

        except Exception as ex:
            logging.error(f"[ERROR] ao enviar detalhes da sessão: {ex}")
            return False

    async def send_count_to_django(self):
        try:
            logging.info(f"Enviando contagens da sessão {self.sessao} para o Django...")
            
            headers = {
                "Authorization": f"Bearer {self.tokens['access']}" if self.tokens and 'access' in self.tokens else "",
                "Content-Type": "application/json"
            }

            contagens_list = []
            for categoria in self.categorias:
                contagens_list.append({
                    "veiculo": categoria.veiculo,
                    "movimento": categoria.movimento,
                    "count": self.contagens.get((categoria.veiculo, categoria.movimento), 0)
                })

            periodo_atual = None
            if hasattr(self, "current_timeslot") and self.current_timeslot:
                periodo_atual = self.current_timeslot.strftime("%H:%M")

            payload = {
                "sessao": self.sessao,
                "usuario": self.username,
                "contagens": contagens_list,
                "current_timeslot": periodo_atual
            }
            
            logging.info(f"Payload das contagens: {payload}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{API_URL}/contagens/get/", json=payload, headers=headers)

            if response.status_code == 201:
                logging.info(f"✅ Contagens da sessão {self.sessao} enviadas com sucesso para Django!")
            else:
                logging.error(f"❌ Erro ao enviar contagens: {response.status_code} - {response.text}")

        except Exception as ex:
            logging.error(f"❌ Erro ao enviar contagens para Django: {ex}")

    def restart_app(self):
        try:
            logging.info("Iniciando restart da aplicação...")
            
            # 1. Parar o listener
            if hasattr(self, 'listener') and self.listener:
                self.stop_listener()
                logging.info("Listener parado com sucesso")

            # 2. Limpar estado
            self.sessao = None
            self.details = {"Movimentos": []}
            self.contagens = {}
            self.binds = {}
            self.labels = {}
                
            # 3. Reconfigurar UI
            self.setup_ui()
            
            # 4. Garantir que a aba de contagem está invisível
            if len(self.tabs.tabs) > 1:
                self.tabs.tabs[1].content.visible = False
            
            # 5. Voltar para a primeira aba
            self.tabs.selected_index = 0
            
            logging.info("Aplicação reiniciada com sucesso")
        except Exception as ex:
            logging.error(f"Erro ao reiniciar aplicação: {ex}")

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

    """def check_categories_in_db(self):
        try:
            categorias = self.session.query(Categoria).all()
            return categorias
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao buscar categorias do banco: {ex}")"""

    def increment(self, veiculo, movimento):
        try:
            categoria = self.session.query(Categoria).filter_by(
                padrao=self.ui_components['inicio'].padrao_dropdown.value,
                veiculo=veiculo,
                movimento=movimento
            ).first()
            if not categoria:
                logging.warning(f"[WARNING] Categoria não encontrada para veiculo={veiculo}, movimento={movimento}")
                return

            key = (veiculo, movimento)
            self.contagens[key] = self.contagens.get(key, 0) + 1
            self.update_labels(veiculo, movimento)
            self.save_to_db(veiculo, movimento)
            self.salvar_historico(categoria.id, movimento, "increment")  
            logging.info(f"✅ Contagem salva para {veiculo} - {movimento}")

        except Exception as ex:
            logging.error(f"Erro ao incrementar: {ex}")

    def decrement(self, veiculo, movimento):
        try:
            categoria = self.session.query(Categoria).filter_by(
                padrao=self.ui_components['inicio'].padrao_dropdown.value,
                veiculo=veiculo,
                movimento=movimento
            ).first()
            if not categoria:
                logging.warning(f"[WARNING] Categoria não encontrada para veiculo={veiculo}, movimento={movimento}")
                return

            key = (veiculo, movimento)
            self.contagens[key] = max(self.contagens.get(key, 0) - 1, 0)
            self.update_labels(veiculo, movimento)
            self.save_to_db(veiculo, movimento)
            self.salvar_historico(categoria.id, movimento, "decrement") 
            logging.info(f"✅ Contagem salva para {veiculo} - {movimento}")

        except Exception as ex:
            logging.error(f"Erro ao decrementar: {ex}")

    def abrir_edicao_contagem(self, veiculo, movimento):
        self.contagem_ativa = False
        self.page.update()

        def on_submit(e):
            try:
                nova_contagem = int(input_contagem.value)
                self.contagens[(veiculo, movimento)] = nova_contagem
                self.update_labels(veiculo, movimento)
                self.save_to_db(veiculo, movimento)
                
                # Encontrar a categoria para ter o ID
                categoria = self.session.query(Categoria).filter_by(
                    padrao=self.ui_components['inicio'].padrao_dropdown.value,
                    veiculo=veiculo,
                    movimento=movimento
                ).first()
                
                # Salvar no histórico com o ID correto da categoria
                self.salvar_historico(categoria.id if categoria else None, movimento, "edicao manual")
                
                snackbar = ft.SnackBar(
                    ft.Text(f"Contagem de '{veiculo}' no movimento '{movimento}' foi atualizada para {nova_contagem}."),
                    bgcolor="BLUE"
                )
                self.page.overlay.append(snackbar)
                snackbar.open = True
                dialog.open = False
                self.contagem_ativa = True
                self.page.update()

            except ValueError:
                logging.error("[ERROR] Valor de contagem inválido.")

        input_contagem = ft.TextField(
            label="Nova Contagem",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=on_submit
        )
        dialog = ft.AlertDialog(
            title=ft.Text(f"Editar Contagem: {veiculo}"),
            content=input_contagem,
            actions=[ft.TextButton("Salvar", on_click=on_submit)],
            on_dismiss=lambda e: None,
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def salvar_historico(self, categoria_id, movimento, acao):
        try:
            novo_historico = Historico(
                sessao=self.sessao,
                categoria_id=categoria_id,  # Pode ser None para ações gerais
                movimento=movimento,
                acao=acao
            )
            with self.session_lock:
                self.session.add(novo_historico)
                self.session.commit()
            logging.info(f"[INFO] Histórico salvo com sucesso para ação: {acao}")
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao salvar histórico: {ex}")
            with self.session_lock:
                self.session.rollback()

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
                        self.page.run_task(self.send_count_to_django)
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

            self.page.run_task(self.send_count_to_django)
            self._perform_save(now)

        except Exception as ex:
            logging.error(f"Erro ao salvar contagens: {ex}")
            snackbar = ft.SnackBar(ft.Text("Erro ao salvar contagens."), bgcolor="RED")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

    def _perform_save(self, now):
        async def salvar():
            try:
                # Garantir que estamos usando o horário correto da sessão
                if not hasattr(self, "current_timeslot") or self.current_timeslot is None:
                    if "HorarioInicio" in self.details:
                        # Converter a string do horário inicial para datetime
                        hoje = datetime.now().date()
                        horario = datetime.strptime(self.details["HorarioInicio"], "%H:%M").time()
                        self.current_timeslot = datetime.combine(hoje, horario)
                    else:
                        # Fallback apenas em caso de erro
                        logging.error("Horário inicial não encontrado nos detalhes da sessão!")
                        self.current_timeslot = datetime.now().replace(second=0, microsecond=0)

                horario_atual = self.current_timeslot
                nome_pesquisador = re.sub(r'[<>:"/\\|?*]', '', self.username)
                codigo = re.sub(r'[<>:"/\\|?*]', '', self.details['Código'])
                diretorio_base = EXCEL_BASE_DIR 
                diretorio_pesquisador_codigo = os.path.join(diretorio_base, nome_pesquisador, codigo)
                arquivo_sessao = os.path.join(diretorio_pesquisador_codigo, f'{self.sessao}.xlsx')

                if not os.path.exists(diretorio_base):
                    os.makedirs(diretorio_base, exist_ok=True)
                if not os.path.exists(diretorio_pesquisador_codigo):
                    os.makedirs(diretorio_pesquisador_codigo, exist_ok=True)

                with pd.ExcelWriter(arquivo_sessao, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                    for movimento in self.details["Movimentos"]:
                        df_existente = pd.read_excel(arquivo_sessao, sheet_name=movimento)

                        nova_linha = {
                            "das": horario_atual.strftime("%H:%M"),
                            "às": (horario_atual + timedelta(minutes=15)).strftime("%H:%M"),
                            "observacao": self.period_observacao
                        }

                        for categoria in [c for c in self.categorias if c.movimento == movimento]:
                            veiculo = categoria.veiculo
                            key = (veiculo, movimento)
                            nova_linha[veiculo] = self.contagens.get(key, 0)

                        df_novo = pd.DataFrame([nova_linha])
                        df_resultante = pd.concat([df_existente, df_novo], ignore_index=True)
                        df_resultante.to_excel(writer, sheet_name=movimento, index=False)

                self.last_save_time = now
                self.details["last_save_time"] = self.last_save_time.strftime("%H:%M:%S")
                
                # Atualizar a UI através do componente de contagem
                if 'contagem' in self.ui_components:
                    aba_contagem = self.ui_components['contagem']
                    if hasattr(aba_contagem, 'last_save_label'):
                        aba_contagem.last_save_label.value = f"⏳ Último salvamento: {self.last_save_time.strftime('%H:%M:%S')}"
                        aba_contagem.last_save_label.update()

                self.current_timeslot += timedelta(minutes=15)
                self.details["current_timeslot"] = self.current_timeslot.strftime("%H:%M")
                
                # Atualizar o período na UI
                if 'contagem' in self.ui_components:
                    aba_contagem = self.ui_components['contagem']
                    if hasattr(aba_contagem, 'period_label'):
                        periodo_inicio = self.current_timeslot.strftime("%H:%M")
                        periodo_fim = (self.current_timeslot + timedelta(minutes=15)).strftime("%H:%M")
                        aba_contagem.period_label.value = f"🕒 Período: {periodo_inicio} - {periodo_fim}"
                        aba_contagem.period_label.update()

                self.save_session()

                # Limpar contagens
                with self.session_lock:
                    self.session.query(Contagem).filter_by(sessao=self.sessao).delete()
                    self.session.commit()

                for key in self.contagens:
                    self.contagens[key] = 0
                    if key in self.labels:
                        label_count, _ = self.labels[key]
                        label_count.value = "0"
                        label_count.update()

                # Adicionar registro no histórico para o salvamento
                self.salvar_historico(None, "TODOS", "salvamento")  # None porque é uma ação geral

                snackbar = ft.SnackBar(ft.Text("Contagens salvas e enviadas com sucesso!"), bgcolor="GREEN")
                self.page.overlay.append(snackbar)
                snackbar.open = True
                self.page.update()

            except Exception as ex:
                logging.error(f"Erro ao salvar contagens: {ex}")
                snackbar = ft.SnackBar(ft.Text("Erro ao salvar contagens."), bgcolor="RED")
                self.page.overlay.append(snackbar)
                snackbar.open = True
                self.page.update()

        self.page.run_task(salvar)

    def abrir_dialogo_observacao(self, e):
        def on_confirm(ev):
            self.period_observacao = textfield.value
            dialog.open = False
            self.page.update()

            snackbar = ft.SnackBar(ft.Text("✅ Observação salva!"), bgcolor="PURPLE")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

        textfield = ft.TextField(label="Observação do período", multiline=True, width=300)
        dialog = ft.AlertDialog(
            title=ft.Text("Inserir Observação"),
            content=textfield,
            actions=[
                ft.TextButton("Confirmar", on_click=on_confirm),
                ft.TextButton("Cancelar", on_click=lambda _: self.close_dialog(dialog)),
            ],
            on_dismiss=lambda _: self.close_dialog(dialog),
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()


    def update_last_save_label(self, now=None):
        if not hasattr(self, "last_save_label"):
            self.last_save_label = ft.Text(
                value="Último salvamento: --:--:--",
                size=15,
                weight=ft.FontWeight.W_400
            )
            self.tabs.tabs[1].content.controls.insert(0, self.last_save_label)
        
        timestamp = now if now else (self.last_save_time if hasattr(self, "last_save_time") else datetime.now())
        self.last_save_label.value = f"Último salvamento: {timestamp.strftime('%H:%M:%S')}"
        self.last_save_label.update()

    def update_period_status(self):
        if not hasattr(self, "period_label"):
            self.period_label = ft.Text(
                value="Período atual: --:-- - --:--",
                size=16,
                weight=ft.FontWeight.W_400
            )
            if self.tabs.tabs[1].content.controls:
                labels_row = self.tabs.tabs[1].content.controls[1].content
                if isinstance(labels_row, ft.Row) and self.period_label not in labels_row.controls:
                    labels_row.controls.append(self.period_label)

        if not hasattr(self, "current_timeslot") or self.current_timeslot is None:
            if "current_timeslot" in self.details:
                self.current_timeslot = datetime.strptime(self.details["current_timeslot"], "%H:%M")
            elif "HorarioInicio" in self.details:
                self.current_timeslot = datetime.strptime(self.details["HorarioInicio"], "%H:%M")
            else:
                self.current_timeslot = datetime.now().replace(second=0, microsecond=0)

        periodo_inicio = self.current_timeslot.strftime("%H:%M")
        periodo_fim = (self.current_timeslot + timedelta(minutes=15)).strftime("%H:%M")
        self.period_label.value = f"Período atual: {periodo_inicio} - {periodo_fim}"
        self.period_label.update()

    # ------------------- LISTENER -----------------------------
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

    async def load_categories_api(self, pattern_type):
        try:
            logging.info(f"[INFO] Iniciando carregamento de categorias para padrão {pattern_type}")
            movimentos = self.details.get("Movimentos", [])
            if not movimentos:
                logging.warning("[WARNING] Nenhum movimento definido")
                return

            movimentos = [str(mov).strip().upper() for mov in movimentos if str(mov).strip()]
            self.details["Movimentos"] = movimentos
            movimento_atual = self.details.get("Movimentos", ["A"])[0]
            url = f"{API_URL}/padroes/padroes-api/?pattern_type={pattern_type}"
            response = await self.api_get(url)

            if not response:
                logging.warning(f"[WARNING] Nenhuma categoria retornada pela API para {pattern_type}")
                return

            categorias_a_salvar = []
            for cat in response:
                for movimento in movimentos:
                    nova_categoria = Categoria(
                        padrao=cat["pattern_type"],
                        veiculo=cat["veiculo"],
                        movimento=movimento,
                        bind=cat.get("bind", "N/A")
                    )
                    categorias_a_salvar.append(nova_categoria)

            self.save_categories_in_local(categorias_a_salvar)
            logging.info(f"[INFO] Categorias salvas: {len(categorias_a_salvar)}")
            
            if 'contagem' in self.ui_components:
                logging.info("[INFO] Atualizando UI da aba contagem")
                self.ui_components['contagem'].setup_ui()
            
            self.page.update() 
        except Exception as ex:
            logging.error(f"[ERROR] Erro em load_categories_api: {ex}")

    def save_categories_in_local(self, categorias):
        self.session_manager.save_categories_in_local(categorias)

    async def carregar_padroes_selecionados(self, e=None):
        try:
            padrao_selecionado = self.ui_components['inicio'].padrao_dropdown.value

            if not padrao_selecionado:
                logging.warning("[WARNING] Nenhum padrão selecionado!")
                return

            logging.info(f"Carregando binds para o padrão: {padrao_selecionado}")

            padrao_selecionado_str = str(padrao_selecionado)
            api_url = f"{API_URL}/padroes/merged-binds/?pattern_type={padrao_selecionado_str}"
            
            headers = {"Authorization": f"Bearer {self.tokens['access']}"} if self.tokens and 'access' in self.tokens else {}
            
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(api_url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    self.binds = {item["veiculo"]: item["bind"] for item in data}
                    logging.info(f"✅ {len(self.binds)} binds carregados com sucesso")
                else:
                    logging.error(f"❌ Erro ao carregar binds: {response.status_code}")
        
            if 'contagem' in self.ui_components:
                self.ui_components['contagem'].setup_ui()
        
            self.page.update() 

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao carregar padrões: {ex}")

    def _carregar_binds_locais(self, padrao=None):
        self.session_manager._carregar_binds_locais(padrao)
            
    def logout_user(self, e):
        try:
            tokens_path = DESKTOP_DIR / "auth_tokens.json"
            if tokens_path.exists():
                tokens_path.unlink()
                logging.info("[✅] Tokens apagados no logout.")

            self.tokens = None
            self.username = None
            self.app.reset_app()

        except Exception as ex:
            logging.error(f"Erro ao deslogar: {ex}")

    def show_dialog_end_session(self, e):
        self.session_manager.show_dialog_end_session(e)

    def carregar_categorias_locais(self, padrao=None):
        self.session_manager.carregar_categorias_locais(padrao)

    def inicializar_arquivo_excel(self):
        try:
            nome_pesquisador = re.sub(r'[<>:"/\\|?*]', '', self.username)
            codigo = re.sub(r'[<>:"/\\|?*]', '', self.details['Código'])
            diretorio_base = EXCEL_BASE_DIR

            if not os.path.exists(diretorio_base):
                os.makedirs(diretorio_base, exist_ok=True)

            diretorio_pesquisador_codigo = os.path.join(diretorio_base, nome_pesquisador, codigo)
            if not os.path.exists(diretorio_pesquisador_codigo):
                os.makedirs(diretorio_pesquisador_codigo, exist_ok=True)

            arquivo_sessao = os.path.join(diretorio_pesquisador_codigo, f'{self.sessao}.xlsx')

            if os.path.exists(arquivo_sessao):
                os.remove(arquivo_sessao)

            wb = Workbook()

            if not self.details["Movimentos"]:
                ws = wb.active
                ws.title = "Placeholder"
                ws.append(["Aviso", "Nenhum movimento foi definido."])
                logging.warning("Nenhum movimento definido. Placeholder criado.")
            else:
                wb.remove(wb.active)
                for movimento in self.details["Movimentos"]:
                    wb.create_sheet(title=movimento)

            ws_details = wb.create_sheet(title="Detalhes")
            details_df = pd.DataFrame([self.details])

            for coluna in details_df.columns:
                details_df[coluna] = details_df[coluna].apply(
                    lambda x: ', '.join(x) if isinstance(x, list) else x
                )

            for row in dataframe_to_rows(details_df, index=False, header=True):
                ws_details.append(row)

            wb.active = 0
            wb.save(arquivo_sessao)
            logging.info(f"Arquivo Excel inicializado com sucesso: {arquivo_sessao}")

        except Exception as ex:
            logging.error(f"Erro ao inicializar arquivo Excel: {ex}")
            raise