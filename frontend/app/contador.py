# app/contador.py
import flet as ft
import logging
import asyncio
import json
from database.models import Session, Categoria, Sessao, Contagem, Historico, init_db
from sqlalchemy.exc import SQLAlchemyError
from app import aba_contagem, listener, sessao
from utils.initializer import inicializar_variaveis, configurar_numpad_mappings
from openpyxl import Workbook
from utils.config import API_URL, EXCEL_BASE_DIR, DESKTOP_DIR
from loginregister.login import LoginPage
from utils.period import format_period
from app.ui.aba_ajuda import AbaAjuda
from app.ui.aba_relatorio import AbaRelatorio
from app.ui.aba_config import AbaConfig
from app.ui.aba_historico import AbaHistorico
from loginregister.register import RegisterPage
from pynput import keyboard
from time import sleep
import pandas as pd
from datetime import datetime, timedelta, time
import threading, os, re, httpx, openpyxl
from utils.change_binds import abrir_configuracao_binds, BindManager
from openpyxl.utils.dataframe import dataframe_to_rows
from utils.api import async_api_request

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
        inicializar_variaveis(self)
        configurar_numpad_mappings(self)
        self.session_lock = threading.Lock() 
        self.session = Session()  
    
        self.setup_ui()
        self.page.update()
        asyncio.create_task(self.load_active_session()) 
        self.binds = {}  
        self.labels = {}  
        self.contagens = {}  
        self.categorias = []  
        self.details = {"Movimentos": []}

    def validar_texto(self, texto):
        """ Permite apenas letras e números, remove espaços e caracteres especiais """
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
        self.tabs = ft.Tabs(
            selected_index=0,  
            tabs=[
                ft.Tab(
                    text="Início", content=ft.Column(expand=True)),
                ft.Tab(
                    text="Contador", content=ft.Column(expand=True)),
                ft.Tab(
                    text="Histórico", content=AbaHistorico(self)),
                ft.Tab(
                    text="",
                    icon=ft.icons.SETTINGS, content=AbaConfig(self)),
                ft.Tab(
                    text="",
                    icon=ft.icons.HELP, content=AbaAjuda(self)),
                ft.Tab(
                    text="Relatório",
                    icon=ft.icons.TABLE_CHART, content=AbaRelatorio(self)),
            ],
            expand=1, 
        )
        self.controls.clear()
        self.controls.append(self.tabs)
        self.page.window.scroll = ft.ScrollMode.AUTO 
        self.page.window.width = 800
        self.page.window.height = 700
        self.page.update()

        self.setup_aba_inicio()
        self.setup_aba_contagem()
        

        if hasattr(self, "sessao") and self.sessao:
            self.tabs.selected_index = 1 
            self.tabs.tabs[1].content.visible = True
        else:
            self.tabs.tabs[1].content.visible = False 
    
    # ------------------------ ABA INICIO ------------------------
    def setup_aba_inicio(self):
        tab = self.tabs.tabs[0].content
        tab.controls.clear()

        hoje_str = datetime.now().strftime("%d-%m-%Y")
        user_label = ft.Text(f"Usuário logado: {self.username}", size=16, weight=ft.FontWeight.BOLD, color="BLUE")
        tab.controls.append(user_label)
        self.codigo_ponto_input = ft.TextField(
            label="Código do Ponto",
            hint_text="Ex: ER2403",
            icon=ft.icons.CODE,
            expand=True,
            border_radius=8
        )

        self.nome_ponto_input = ft.TextField(
            label="Nome do Ponto",
            hint_text="Ex: P10; P15",
            icon=ft.icons.LOCATION_PIN,
            expand=True,
            border_radius=8
        )

        self.data_ponto_input = ft.TextField(
            label="Data",
            hint_text="dd-mm-aaaa",
            value=hoje_str,
            icon=ft.icons.CALENDAR_MONTH,
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            border_radius=8
        )

        self.selected_time = "00:00"

        def picker_changed(e):
            selected_seconds = e.control.value
            hours, remainder = divmod(selected_seconds, 3600)
            minutes = (remainder // 60)
            adjusted_minutes = (minutes // 15) * 15
            self.selected_time = f"{hours:02}:{adjusted_minutes:02}"
            self.time_picker_button.text = f"{self.selected_time}"
            self.time_picker_button.update()

        self.time_picker = ft.CupertinoTimerPicker(
            mode=ft.CupertinoTimerPickerMode.HOUR_MINUTE,
            value=0,
            minute_interval=15,
            on_change=picker_changed
        )

        self.time_picker_button = ft.ElevatedButton(
            text=f"{self.selected_time}",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            width=float('inf'),
            height=50,
            icon=ft.icons.ACCESS_ALARM,
            on_click=lambda _: self.page.open(ft.AlertDialog(content=self.time_picker))
        )

        self.padrao_dropdown = ft.Dropdown(
            label="Selecione o Padrão",
            options=[],
            on_change=self.carregar_padroes_selecionados,
            expand=True,
        )

        input_container = ft.Container(
            content=ft.Column(
                controls=[
                    self.codigo_ponto_input,
                    self.nome_ponto_input,
                    self.data_ponto_input,
                    self.time_picker_button,
                    self.padrao_dropdown,
                ],
                spacing=10
            ),
            padding=ft.padding.all(16),
            border_radius=10,
            bgcolor=ft.colors.SURFACE_VARIANT
        )

        self.movimentos_container = ft.Column()

        def adicionar_campo_movimento(e):
            movimento_input = ft.TextField(
                label="Movimento",
                hint_text="Exemplo: A",
                border_radius=8,
                expand=True
            )
            remover_button = ft.IconButton(
                icon=ft.icons.REMOVE,
                on_click=lambda _: remover_campo(movimento_input, remover_button)
            )
            movimento_row = ft.Row(controls=[movimento_input, remover_button], spacing=10)
            self.movimentos_container.controls.append(movimento_row)
            self.page.update()

        def remover_campo(movimento_input, remover_button):
            movimento_row = next(
                (row for row in self.movimentos_container.controls if movimento_input in row.controls),
                None
            )
            if movimento_row:
                self.movimentos_container.controls.remove(movimento_row)
                self.page.update()

        adicionar_movimento_button = ft.ElevatedButton(
            text="Adicionar Movimento",
            icon=ft.icons.ADD,
            width=float('inf'),
            height=45,
            on_click=adicionar_campo_movimento
        )

        criar_sessao_button = ft.ElevatedButton(
            text="Criar Sessão",
            on_click=self.criar_sessao,
            width=float('inf'),
            height=50,
            icon=ft.icons.SEND
        )

        self.api_padroes_container = ft.Column()

        tab.controls.extend([
            input_container,
            ft.Divider(),
            adicionar_movimento_button,
            self.movimentos_container,
            ft.Divider(),
            criar_sessao_button,
            self.api_padroes_container,
        ])

        self.page.update()

        async def load_padroes_wrapper():
            await self.load_padroes()

        self.page.run_task(load_padroes_wrapper)
        
    async def load_padroes(self):
        try:
            headers = {"Authorization": f"Bearer {self.tokens['access']}"} if self.tokens and 'access' in self.tokens else {}

            url = f"{API_URL}/padroes/tipos-de-padrao/"
            response = await async_api_request(url, method="GET", headers=headers)
            tipos = response

            if isinstance(tipos, dict):
                tipos_list = list(tipos.values()) if tipos else list(tipos.keys())
            elif isinstance(tipos, list):
                tipos_list = tipos
            else:
                tipos_list = [str(tipos)] 

            self.padrao_dropdown.options = [ft.dropdown.Option(str(t)) for t in tipos_list]

            if tipos_list and not self.padrao_dropdown.value:
                self.padrao_dropdown.value = str(tipos_list[0])

            self.page.update()
        except Exception as ex:
            logging.error(f"Erro ao carregar tipos de padrões: {ex}")
            self.padrao_dropdown.options = [ft.dropdown.Option("Erro na API")]
            self.page.update()

    def validar_campos(self):
        campos_obrigatorios = [
            (self.codigo_ponto_input, "Código"),
            (self.nome_ponto_input, "Ponto"),
            (self.time_picker_button, "Horário de Início"),
            (self.data_ponto_input, "Data do Ponto")
        ]

        for campo, nome in campos_obrigatorios:
            if isinstance(campo, ft.TextField) and not campo.value:
                snackbar = ft.SnackBar(ft.Text(f"{nome} é obrigatório!"), bgcolor="ORANGE")
                self.page.overlay.append(snackbar)
                snackbar.open = True
                self.page.update()
                return False
            elif isinstance(campo, ft.ElevatedButton) and campo.text == "Selecionar Horário":
                snackbar = ft.SnackBar(ft.Text(f"{nome} é obrigatório!"), bgcolor="ORANGE")
                self.page.overlay.append(snackbar)
                snackbar.open = True
                self.page.update()
                return False

        for mov_row in self.movimentos_container.controls:
            if isinstance(mov_row, ft.Row) and mov_row.controls:
                movimento_input = mov_row.controls[0]
                if isinstance(movimento_input, ft.TextField) and not movimento_input.value.strip():
                    snackbar = ft.SnackBar(ft.Text("Movimentos não podem estar vazios!"), bgcolor="RED")
                    self.page.overlay.append(snackbar)
                    snackbar.open = True
                    self.page.update()
                    return False

        return True

    # ------------------------ SESSÃO ------------------------
    def criar_sessao(self, e):
        async def _carregar_sessao():
            sessao.criar_sessao(self, e)

            await self.carregar_padroes_selecionados()
            await self.load_categories_api(self.padrao_dropdown.value)
            await self.update_binds()

            self.load_local_categories() 
            self.setup_aba_contagem() 
            self.page.update() 
            await self.send_session_to_django()
        self.page.run_task(_carregar_sessao)

    async def send_session_to_django(self):
        try:
            headers = {
                "Authorization": f"Bearer {self.tokens['access']}" if self.tokens and 'access' in self.tokens else "",
                "Content-Type": "application/json"
            }

            payload = {
                "sessao": self.sessao,
                "codigo": self.details.get("Código"),
                "ponto": self.details.get("Ponto"),
                "data": self.details.get("Data do Ponto"),
                "horario_inicio": self.details.get("HorarioInicio"),
                "usuario": self.username,
                "ativa": self.session.query(Sessao).filter_by(sessao=self.sessao).first().ativa if self.sessao else True,
                "movimentos": self.details.get("Movimentos", [])  # <-- ESSENCIAL!
            }


            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{API_URL}/contagens/registrar-sessao/", json=payload, headers=headers)

            if response.status_code in [200, 201]:
                logging.info("✅ Detalhes da sessão enviados ao Django com sucesso!")
            else:
                logging.error(f"❌ Falha ao enviar detalhes da sessão: {response.text}")

        except Exception as ex:
            logging.error(f"[ERROR] ao enviar detalhes da sessão: {ex}")

    async def send_count_to_django(self):
        try:
            headers = {
                "Authorization": f"Bearer {self.tokens['access']}" if self.tokens and 'access' in self.tokens else "",
                "Content-Type": "application/json"
            }

            contagens_list = [
                {"veiculo": veiculo, "movimento": movimento, "count": self.contagens.get((veiculo, movimento), 0)}
                for (veiculo, movimento) in self.contagens
            ]

            # Obter o período atual
            periodo_atual = None
            if hasattr(self, "current_timeslot") and self.current_timeslot:
                periodo_atual = self.current_timeslot.strftime("%H:%M")

            payload = {
                "sessao": self.sessao,
                "usuario": self.username,
                "contagens": contagens_list,
                "current_timeslot": periodo_atual  # Incluir o período atual no payload
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{API_URL}/contagens/get/", json=payload, headers=headers)

            if response.status_code == 201:
                logging.info("✅ Contagens enviadas com sucesso para Django!")
            else:
                logging.error(f"❌ Erro ao enviar contagens: {response.text}")

        except Exception as ex:
            logging.error(f"❌ Erro ao enviar contagens para Django: {ex}")

    async def notificar_finalizacao_django(self):
        try:
            headers = {
                "Authorization": f"Bearer {self.tokens['access']}" if self.tokens and 'access' in self.tokens else "",
                "Content-Type": "application/json"
            }

            payload = {
                "sessao": self.sessao,
                "ativa": False
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(f"{API_URL}/contagens/finalizar-sessao/", headers=headers, json=payload)

            if response.status_code == 200:
                logging.info("Sessão finalizada no Django com sucesso!")
            else:
                logging.error(f"Erro ao finalizar sessão no Django: {response.status_code} - {response.text}")

        except Exception as e:
            logging.error(f"Exceção ao notificar Django: {e}")
    

    def load_local_categories(self, padrao=None):
        padrao_atual = padrao or self.padrao_dropdown.value

        if not padrao_atual:
            logging.warning("[WARNING] Nenhum padrão selecionado")
            return []

        logging.debug(f"[DEBUG] Buscando categorias no banco para o padrão: {padrao_atual}")

        with self.session_lock:
            try:
                self.categorias = (
                    self.session.query(Categoria)
                    .filter(Categoria.padrao == padrao_atual)
                    .order_by(Categoria.id)
                    .all()
                )
                self.session.commit()

                logging.debug(f"[DEBUG] Categorias carregadas do banco: {[(c.veiculo, c.movimento) for c in self.categorias]}")

                self.setup_aba_contagem()
                self.page.update()

            except Exception as ex:
                logging.error(f"[ERROR] Erro ao carregar categorias locais: {ex}")
                self.session.rollback()
                self.categorias = []

        return self.categorias

    def atualizar_binds_na_ui(self):
        for veiculo, bind in self.binds.items():
            for movimento in self.details.get("Movimentos", []):
                key = (veiculo, movimento)
                if key in self.labels:  
                    if isinstance(self.labels[key], list) and len(self.labels[key]) >= 2:
                        label_bind = self.labels[key][1]  
                        label_bind.value = f"({bind})"
                        label_bind.update()

        self.page.update()

    async def update_binds(self):
        try:
            bind_manager = BindManager()
            headers = await bind_manager.get_authenticated_headers()

            if not headers:
                logging.error("[ERROR] Falha ao obter headers autenticados")
                return

            padrao_atual = self.padrao_dropdown.value
            if not padrao_atual:
                logging.warning("[WARNING] Nenhum padrão selecionado")
                return

            padrao_atual_str = str(padrao_atual)
            response = await async_api_request(f"{API_URL}/padroes/merged-binds/?pattern_type={padrao_atual_str}", headers=headers)

            if "error" in response:
                logging.error(f"[ERROR] Erro na API ao carregar binds: {response['error']}")
                return

            self.binds.clear()
            for cat in response:
                veiculo = cat["veiculo"]
                bind = cat["bind"]
                self.binds[veiculo] = bind

            self.setup_aba_contagem()
            self.page.update()

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao carregar binds do usuário: {ex}")

    def _inicializar_arquivo_excel(self):
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

    def show_dialog_end_session(self, e):
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        async def end_and_close(e):
            try:
                dialog.open = False
                self.page.update()
                await self.end_session()
            except Exception as ex:
                logging.error(f"Erro ao finalizar sessão: {ex}")

        dialog = ft.AlertDialog(
            title=ft.Text("Finalizar Sessão"),
            content=ft.Text("Você tem certeza que deseja finalizar a sessão?"),
            actions=[
                ft.TextButton("Sim", on_click=end_and_close),
                ft.TextButton("Cancelar", on_click=close_dialog),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    async def end_session(self):
        try:
            await self.notificar_finalizacao_django()
            # Atualiza status da sessão local
            sessao_concluida = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
            if sessao_concluida:
                sessao_concluida.ativa = False 
                self.session.commit()

            # Zera contagens
            for veiculo, movimento in list(self.contagens.keys()):
                self.contagens[(veiculo, movimento)] = 0
                self.update_labels(veiculo, movimento)
                self.save_to_db(veiculo, movimento)

            # Limpa variáveis de sessão
            self.sessao = None
            self.details = {"Movimentos": []}
            self.contagens = {}
            self.binds = {}
            self.labels = {}

            # Feedback visual
            self.page.overlay.append(ft.SnackBar(ft.Text("Sessão finalizada com sucesso!"), bgcolor="BLUE"))
            self.page.update()

            self.restart_app()

        except Exception as ex:
            logging.error(f"Erro ao encerrar sessão: {ex}")
            self.page.overlay.append(ft.SnackBar(ft.Text(f"Erro ao encerrar sessão: {ex}"), bgcolor="RED"))
            self.page.update()

    def restart_app(self):
        self.stop_listener()
        self.sessao = None
        self.details = {"Movimentos": []}
        self.contagens = {}
        self.binds = {}
        self.labels = {}
        self.setup_ui()
        self.page.update()
        self.start_listener()

    def save_to_db(self, veiculo, movimento):
        try:
            with self.session_lock:
                if self.session.in_transaction():
                    self.session.commit()  

                contagem_periodo = self.contagens.get((veiculo, movimento), 0)
                
                with self.session.begin():
                    contagem = self.session.query(Contagem).filter_by(
                        sessao=self.sessao,
                        veiculo=veiculo,
                        movimento=movimento
                    ).first()

                    if contagem:
                        contagem.count = contagem_periodo
                        contagem.contagem_total += contagem_periodo
                    else:
                        nova_contagem = Contagem(
                            sessao=self.sessao,
                            veiculo=veiculo,
                            movimento=movimento,
                            count=contagem_periodo,
                            contagem_total=contagem_periodo
                        )
                        self.session.add(nova_contagem)
                
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao salvar contagem no DB: {ex}")
            with self.session_lock:
                self.session.rollback()

    def recover_active_countings(self):
        try:
            contagens_db = self.session.query(Contagem).filter_by(sessao=self.sessao).all()
            self.contagens.clear()

            for contagem in contagens_db:
                key = (contagem.veiculo, contagem.movimento)
                
                if contagem.count == 0:
                    logging.info(f"[INFO] Contagem zerada detectada para {contagem.veiculo} - {contagem.movimento}, ignorando.")
                    continue

                self.contagens[key] = contagem.count

                if key in self.labels:
                    label_count, label_bind = self.labels[key]
                    label_count.value = str(self.contagens[key])
                    label_count.update()
                else:
                    logging.warning(f"[WARNING] Label não encontrada para {key}. Aguardando criação.")

            logging.info(f"✅ Contagens recuperadas: {self.contagens}")
        
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao recuperar contagens: {ex}")

    def atualizar_binds(self):
        for veiculo, bind in self.binds.items():
            if veiculo in self.labels:
                self.labels[veiculo].value = bind
                self.labels[veiculo].update()
        
        self.page.update()

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

            self.session.commit()
            self.update_binds()
            self.update_ui()

            logging.info(f"Bind atualizado para todos os movimentos do veículo: {veiculo}")
            snackbar = ft.SnackBar(ft.Text(f"Bind atualizado para {veiculo}"), bgcolor="GREEN")
            self.page.overlay.append(snackbar)
            snackbar.open = True

        except SQLAlchemyError as ex:
            logging.error(f"Erro ao atualizar bind no banco: {ex}")
            self.session.rollback()

    def update_ui(self):
        self.setup_aba_contagem()
        self.page.update()

    # ------------------- ABA CONTADOR ------------------------
    def setup_aba_contagem(self):
        aba_contagem.setup_aba_contagem(self)
    def toggle_listener(self, e):
        if self.listener_switch.value:
            self.start_listener()
            self.listener_switch.label = "🎧 Listener Ativado"
            logging.info("✅ Listener ativado")
        else:
            self.stop_listener()
            self.listener_switch.label = "🚫 Listener Desativado"
            logging.info("❌ Listener desativado")

        self.listener_switch.update()
        self.page.update()

    def reset_all_countings(self, e):
        aba_contagem.reset_all_countings(self, e)

    def confirm_reset_all_countings(self, e):
        aba_contagem.confirm_reset_all_countings(self, e)

    def create_moviment_content(self, movimento):
        logging.debug(f"[DEBUG] Criando conteúdo para o movimento: {movimento}")

        content = ft.Column()
        
        categorias = [c for c in self.categorias if movimento.strip().upper() == c.movimento.strip().upper()]
        
        logging.debug(f"[DEBUG] Categorias encontradas para {movimento}: {[(c.veiculo, c.movimento) for c in categorias]}")

        if not categorias:
            logging.warning(f"[WARNING] Nenhuma categoria encontrada para {movimento}")
            content.controls.append(ft.Text(f"🙈 Carregando categorias para {movimento}.", color="RED"))
        else:
            for categoria in categorias:
                veiculo = categoria.veiculo
                bind = self.binds.get(veiculo, "N/A")
                if bind == "N/A":
                    logging.warning(f"[WARNING] Bind não encontrado para veículo {veiculo}, usando padrão")
                control = self.create_category_control(veiculo, bind, movimento)
                content.controls.append(control)

        self.page.update()
        return content

    def create_category_control(self, veiculo, bind, movimento):

        if bind == "N/A":
            bind = self.binds.get(veiculo, "Carregando...")

        label_veiculo = ft.Text(f"{veiculo}", size=15, width=100)
        label_bind = ft.Text(f"({bind})", color="cyan" if bind != "N/A" else "red", size=15, width=50)
        label_count = ft.Text(f"{self.contagens.get((veiculo, movimento), 0)}", size=15, width=50)

        row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=5,
            controls=[
                ft.Container(content=label_veiculo, alignment=ft.alignment.center_left),
                ft.Container(content=label_bind, alignment=ft.alignment.center),
                ft.Container(content=label_count, alignment=ft.alignment.center_right),
                ft.PopupMenuButton(
                    icon_color="teal",
                    items=[
                        ft.PopupMenuItem(text="Adicionar", icon=ft.icons.ADD, on_click=lambda e: self.increment(veiculo, movimento)),
                        ft.PopupMenuItem(text="Remover", icon=ft.icons.REMOVE, on_click=lambda e: self.decrement(veiculo, movimento)),
                        ft.PopupMenuItem(text="Editar Contagem", icon=ft.icons.EDIT, on_click=lambda e: self.abrir_edicao_contagem(veiculo, movimento))
                    ]
                )
            ]
        )

        self.labels[(veiculo, movimento)] = [label_count, label_bind]

        self.page.update()
        return row

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

    def check_categories_in_db(self):
        try:
            categorias = self.session.query(Categoria).all()
            return categorias
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao buscar categorias do banco: {ex}")
    def update_session_info_color(self):
        if self.contagem_ativa:
            self.session_info.bgcolor = "GREEN"
        else:
            self.session_info.bgcolor = "RED"
        self.session_info.update()
        self.page.update()

    def update_status_container_color(self):
        if self.contagem_ativa:
            self.status_container.bgcolor = "GREEN"
        else:
            self.status_container.bgcolor = "RED"
        self.status_container.update()
        self.page.update()

    def toggle_contagem(self, e):
        if not hasattr(self, "toggle_button"):
            logging.error("[ERROR] toggle_button não foi inicializado.")
            return

        self.contagem_ativa = self.toggle_button.value 

        if self.contagem_ativa:
            logging.info("✅ Contagem ativada!")  
            self.start_listener()
        else:
            logging.info("❌ Contagem desativada!")  
            self.stop_listener()

        self.update_session_info_color()
        self.update_status_container_color()
        self.toggle_button.update()
        self.page.update()

    def increment(self, veiculo, movimento):
        try:
            categoria = self.session.query(Categoria).filter_by(
                padrao=self.padrao_dropdown.value,
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
                padrao=self.padrao_dropdown.value,
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
                self.salvar_historico(veiculo, movimento, "edição manual")
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
                categoria_id=categoria_id,
                movimento=movimento,
                acao=acao
            )
            with self.session_lock:
                self.session.add(novo_historico)
                self.session.commit()
            logging.info(f"[INFO] Histórico salvo com sucesso para categoria_id={categoria_id}")
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao salvar histórico: {ex}")
            with self.session_lock:
                self.session.rollback()

    def update_current_tab(self):
        current_tab = self.movimento_tabs.tabs[self.movimento_tabs.selected_index]
        current_tab.content.update()
        self.page.update()

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

                            if key in self.labels:
                                label_count, _ = self.labels[key]
                                nova_linha[veiculo] = label_count.value
                            else:
                                nova_linha[veiculo] = 0

                        df_novo = pd.DataFrame([nova_linha])
                        df_resultante = pd.concat([df_existente, df_novo], ignore_index=True)
                        df_resultante.to_excel(writer, sheet_name=movimento, index=False)

                self.last_save_time = now
                self.details["last_save_time"] = self.last_save_time.strftime("%H:%M:%S")
                self.update_last_save_label(self.last_save_time)

                self.current_timeslot += timedelta(minutes=15)
                self.details["current_timeslot"] = self.current_timeslot.strftime("%H:%M")
                self.update_period_status()

                self.save_session()

                logging.info(f"Salvamento realizado com sucesso: {arquivo_sessao}")

                with self.session_lock:
                    self.session.query(Contagem).filter_by(sessao=self.sessao).delete()
                    self.session.commit()

                for key in self.contagens:
                    self.contagens[key] = 0
                    if key in self.labels:
                        label_count, _ = self.labels[key]
                        label_count.value = "0"
                        label_count.update()

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

    async def load_active_session(self):
        try:
            sessao_ativa = self.session.query(Sessao).filter_by(ativa=True).first()
            if not sessao_ativa:
                logging.info("[INFO] Nenhuma sessão ativa encontrada, iniciando sem sessão")
                self.setup_ui()
                return False

            self.sessao = sessao_ativa.sessao  
            self.details = json.loads(sessao_ativa.details) 

            if "current_timeslot" in self.details:
                self.current_timeslot = datetime.strptime(self.details["current_timeslot"], "%H:%M")
            elif "HorarioInicio" in self.details:
                self.current_timeslot = datetime.strptime(self.details["HorarioInicio"], "%H:%M")
            else:
                self.current_timeslot = datetime.now().replace(second=0, microsecond=0)

            if "last_save_time" in self.details:
                self.last_save_time = datetime.strptime(self.details["last_save_time"], "%H:%M:%S")
            else:
                self.last_save_time = None

            self.setup_ui()  
            await asyncio.sleep(0.5)

            self.update_last_save_label(self.last_save_time)  
            self.update_period_status()  

            self.padrao_dropdown.value = sessao_ativa.padrao

            await self.load_padroes()
            await self.carregar_padroes_selecionados()
            await self.load_categories_api(self.padrao_dropdown.value)
            self.load_local_categories()

            self.recover_active_countings()
            self.setup_aba_contagem()

            self.tabs.selected_index = 1
            self.tabs.tabs[1].content.visible = True
            self.page.window.scroll = ft.ScrollMode.AUTO
            self.page.update()

            return True

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao carregar sessão ativa: {ex}")
            self.setup_ui()
            self.page.update()
            return False


    def save_session(self):
        try:
            details_json = json.dumps(self.details)
            sessao_existente = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
            if sessao_existente:
                sessao_existente.details = details_json
                sessao_existente.ativa = True
            else:
                nova_sessao = Sessao(
                    sessao=self.sessao,
                    details=details_json,
                    ativa=True
                )
                self.session.add(nova_sessao)
            self.session.commit()
            logging.info(f"✅ Sessão {self.sessao} salva e marcada como ativa!")
            
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao salvar sessão: {ex}")
            self.session.rollback()


    async def load_categories_api(self, pattern_type):
        try:
            movimentos = self.details.get("Movimentos", [])
            if not movimentos:
                logging.warning("[WARNING] Nenhum movimento definido")
                return

            movimentos = [str(mov).strip().upper() for mov in movimentos if str(mov).strip()]
            self.details["Movimentos"] = movimentos
            movimento_atual = self.details.get("Movimentos", ["A"])[0]  # Pegar o primeiro movimento
            url = f"{API_URL}/padroes/padroes-api/?pattern_type={pattern_type}"  # Remover filtro de movimento
            response = await self.api_get(url)

            if not response:
                logging.warning(f"[WARNING] Nenhuma categoria retornada pela API para {pattern_type}")
                return

            categorias_a_salvar = []
            for cat in response:
                # Criar uma categoria para cada movimento
                for movimento in movimentos:
                    nova_categoria = Categoria(
                        padrao=cat["pattern_type"],
                        veiculo=cat["veiculo"],
                        movimento=movimento,
                        bind=cat.get("bind", "N/A")
                    )
                    categorias_a_salvar.append(nova_categoria)

            self.save_categories_in_local(categorias_a_salvar)
            self.setup_aba_contagem()
            self.page.update() 
        except Exception as ex:
            logging.error(f"[ERROR] Erro em load_categories_api: {ex}")

    def save_categories_in_local(self, categorias):
        try:
            with self.session_lock:
                for categoria in categorias:
                    logging.debug(f"[DEBUG] Tipo de categoria.movimento: {type(categoria.movimento)} - Valor: {categoria.movimento}")

                    movimentos = categoria.movimento if isinstance(categoria.movimento, list) else categoria.movimento.split(", ")

                    for movimento in movimentos:
                        logging.debug(f"[DEBUG] Salvando no banco: {categoria.veiculo} - {movimento}")

                        existe = self.session.query(Categoria).filter_by(
                            padrao=categoria.padrao, veiculo=categoria.veiculo, movimento=movimento
                        ).first()

                        if not existe:
                            nova_categoria = Categoria(
                                padrao=categoria.padrao,
                                veiculo=categoria.veiculo,
                                movimento=movimento,
                                bind=categoria.bind
                            )
                            self.session.add(nova_categoria)
                        else:
                            logging.debug(f"[DEBUG] Categoria já existente no banco: {categoria.veiculo} - {movimento}")

                self.session.commit()
                logging.debug("[DEBUG] Commit realizado! Verificando banco de dados...")
                self.check_categories_in_db()

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao salvar categorias no banco: {ex}")
            self.session.rollback()

    async def carregar_padroes_selecionados(self, e=None):
        try:
            padrao_selecionado = self.padrao_dropdown.value

            if not padrao_selecionado:
                logging.warning("[WARNING] Nenhum padrão selecionado! Usando padrão default se disponível.")
                if self.padrao_dropdown.options:
                    default_option = self.padrao_dropdown.options[0]
                    padrao_selecionado = default_option.key if hasattr(default_option, 'key') else str(default_option)
                    self.padrao_dropdown.value = padrao_selecionado

            padrao_selecionado_str = str(padrao_selecionado)
            api_url = f"{API_URL}/padroes/merged-binds/?pattern_type={padrao_selecionado_str}"
            
            bind_manager = BindManager()
            headers = await bind_manager.get_authenticated_headers()
            response = await async_api_request(api_url, method="GET", headers=headers)

            self.binds = {item["veiculo"]: item["bind"] for item in response}
            
            self.setup_aba_contagem()
            self.page.update() 

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao carregar padrões do usuário: {ex}")
            
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