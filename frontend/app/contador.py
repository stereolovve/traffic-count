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
        inicializar_variaveis(self)
        configurar_numpad_mappings(self)
        self.session_lock = threading.Lock() 
        self.session = Session()  
    
        self.ui_components = {}  # Adicionar este dicionário para armazenar referências
        self.setup_ui()
        self.page.update()
        asyncio.create_task(self.load_active_session()) 
        self.binds = {}  
        self.labels = {}  
        self.contagens = {}  
        self.categorias = []  
        self.details = {"Movimentos": []}
        self.django_service = DjangoService(app.tokens)

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
        """Mostra um indicador de carregamento com uma mensagem personalizada"""
        progress = ft.ProgressRing()
        banner = ft.Banner(
            content=ft.Text(message),
            leading=progress,
            bgcolor=ft.colors.BLUE_100,
            actions=[
                ft.TextButton("Aguarde...", disabled=True)
            ]  # Banner requer pelo menos uma action
        )
        self.page.overlay.append(banner)
        self.page.update()
        return banner

    def hide_loading(self, banner):
        """Remove o indicador de carregamento"""
        if banner in self.page.overlay:
            self.page.overlay.remove(banner)
            self.page.update()

    async def criar_sessao(self, session_data):
        """
        Cria uma nova sessão com os dados fornecidos.
        """
        banner = None
        try:
            # 1. Mostrar loading
            banner = self.show_loading("Criando sessão e carregando padrões...")

            # 2. Validar dados recebidos
            if not all(session_data.get(key) for key in ["codigo", "ponto", "horario_inicio", "data_ponto", "padrao"]):
                raise ValueError("Dados da sessão incompletos")

            if not session_data.get("movimentos"):
                raise ValueError("É necessário definir pelo menos um movimento")

            # 3. Criar a sessão localmente
            self.details = {
                "Pesquisador": session_data["pesquisador"],
                "Código": session_data["codigo"],
                "Ponto": session_data["ponto"],
                "HorarioInicio": session_data["horario_inicio"],
                "Data do Ponto": session_data["data_ponto"],
                "Movimentos": session_data["movimentos"]
            }

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

            # 5. Verificar duplicidade
            self.sessao = base_sessao
            counter = 1
            while self.session.query(Sessao).filter_by(sessao=self.sessao).first():
                self.sessao = f"{base_sessao}_{counter}"
                counter += 1

            # 6. Carregar dados necessários
            await self.carregar_padroes_selecionados()
            await self.load_categories_api(session_data["padrao"])
            self.carregar_categorias_locais()

            # 7. Salvar sessão no banco local
            nova_sessao = Sessao(
                sessao=self.sessao,
                details=json.dumps(self.details),
                padrao=session_data["padrao"],
                ativa=True
            )
            with self.session_lock:
                self.session.add(nova_sessao)
                self.session.commit()

            # 8. Inicializar arquivo Excel
            self.inicializar_arquivo_excel()

            # 9. Enviar sessão para o Django
            success = await self.send_session_to_django()
            if not success:
                logging.warning("⚠️ Sessão criada localmente, mas não registrada no servidor.")

            # 10. Configurar interface
            if 'contagem' in self.ui_components:
                self.ui_components['contagem'].setup_ui()

            # 11. Mudar para a aba de contagem
            self.tabs.selected_index = 1
            self.tabs.tabs[1].content.visible = True

            # 12. Mostrar mensagem de sucesso
            self.page.overlay.append(
                ft.SnackBar(
                    content=ft.Text(
                        "Sessão criada com sucesso!" +
                        (" e registrada no servidor." if success else "")
                    ),
                    bgcolor="green"
                )
            )
            self.page.update()

            # Inicializar o current_timeslot com o horário de início selecionado
            self.current_timeslot = datetime.strptime(session_data["horario_inicio"], "%H:%M")
            self.details["current_timeslot"] = self.current_timeslot.strftime("%H:%M")

        except Exception as ex:
            logging.error(f"Erro ao criar sessão: {ex}")
            self.page.overlay.append(
                ft.SnackBar(
                    content=ft.Text(f"Erro ao criar sessão: {str(ex)}"),
                    bgcolor="red"
                )
            )
            self.page.update()
            raise

        finally:
            if banner:
                self.hide_loading(banner)

    async def send_session_to_django(self):
        try:
            logging.info(f"Enviando dados da sessão {self.sessao} para o Django...")
            
            if not self.sessao:
                logging.error("❌ Não foi possível enviar sessão ao Django: self.sessao está vazio!")
                return False

            # MUITO IMPORTANTE: Adicionar logging para verificar o payload
            logging.info(f"Details disponíveis: {self.details}")
            
            headers = {
                "Authorization": f"Bearer {self.tokens['access']}" if self.tokens and 'access' in self.tokens else "",
                "Content-Type": "application/json"
            }

            # Garantir que todos os campos estão presentes e com valores válidos
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

            # Garantir que movimentos é uma lista
            movimentos = self.details.get("Movimentos", [])
            if isinstance(movimentos, set):
                movimentos = list(movimentos)
            if not movimentos:
                movimentos = ["A"]  # Valor padrão em caso de erro

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

            # Adicionar log do payload para depuração
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

            # Criar lista de todas as combinações possíveis de veículo e movimento
            contagens_list = []
            for categoria in self.categorias:
                contagens_list.append({
                    "veiculo": categoria.veiculo,
                    "movimento": categoria.movimento,
                    "count": self.contagens.get((categoria.veiculo, categoria.movimento), 0)
                })

            # Obter o período atual
            periodo_atual = None
            if hasattr(self, "current_timeslot") and self.current_timeslot:
                periodo_atual = self.current_timeslot.strftime("%H:%M")

            payload = {
                "sessao": self.sessao,
                "usuario": self.username,
                "contagens": contagens_list,
                "current_timeslot": periodo_atual
            }
            
            logging.info(f"Payload das contagens: {payload}")  # Log para debug
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{API_URL}/contagens/get/", json=payload, headers=headers)

            if response.status_code == 201:
                logging.info(f"✅ Contagens da sessão {self.sessao} enviadas com sucesso para Django!")
            else:
                logging.error(f"❌ Erro ao enviar contagens: {response.status_code} - {response.text}")

        except Exception as ex:
            logging.error(f"❌ Erro ao enviar contagens para Django: {ex}")

    async def end_session(self):
        try:
            logging.info("Iniciando processo de finalização da sessão...")
            
            # Tentar registrar a sessão no Django caso ainda não tenha sido feito
            await self.send_session_to_django()
            
            # 1. Notificar o Django para finalizar a sessão
            success = await self.django_service.end_session(self.sessao)
            
            if success:
                logging.info("Sessão finalizada no Django com sucesso!")
            else:
                logging.warning("Não foi possível finalizar a sessão no Django, mas continuaremos com a finalização local.")
            
            # 2. Atualizar status da sessão local
            with self.session_lock:
                sessao_concluida = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
                if sessao_concluida:
                    sessao_concluida.ativa = False 
                    self.session.commit()
                    logging.info(f"Sessão {self.sessao} marcada como inativa no banco local")

            # 3. Limpar o estado atual
            self.sessao = None
            self.details = {"Movimentos": []}
            self.contagens = {}
            self.binds = {}
            self.labels = {}

            # 4. Feedback visual
            snackbar = ft.SnackBar(
                content=ft.Text("Sessão finalizada com sucesso!"),
                bgcolor="blue"
            )
            self.page.overlay.append(snackbar)
            snackbar.open = True

            # 5. Reiniciar a aplicação
            logging.info("Reiniciando aplicação após finalização da sessão...")
            self.restart_app()
            
            # 6. Voltar para a aba inicial
            self.tabs.selected_index = 0
            self.page.update()

        except Exception as ex:
            logging.error(f"Erro ao encerrar sessão: {ex}")
            snackbar = ft.SnackBar(
                content=ft.Text(f"Erro ao encerrar sessão: {str(ex)}"),
                bgcolor="red"
            )
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

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

    def update_ui(self):
        self.setup_aba_contagem()
        self.page.update()


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

            # Configurar o current_timeslot corretamente
            hoje = datetime.now().date()
            if "current_timeslot" in self.details:
                horario = datetime.strptime(self.details["current_timeslot"], "%H:%M").time()
            elif "HorarioInicio" in self.details:
                horario = datetime.strptime(self.details["HorarioInicio"], "%H:%M").time()
            else:
                horario = datetime.now().time()
            
            self.current_timeslot = datetime.combine(hoje, horario)
            
            if "last_save_time" in self.details:
                self.last_save_time = datetime.strptime(self.details["last_save_time"], "%H:%M:%S")
            else:
                self.last_save_time = None

            self.setup_ui()  
            await asyncio.sleep(0.5)

            if sessao_ativa:
                self.ui_components['inicio'].padrao_dropdown.value = sessao_ativa.padrao

            await self.ui_components['inicio'].load_padroes()
            await self.carregar_padroes_selecionados()
            await self.load_categories_api(self.ui_components['inicio'].padrao_dropdown.value)
            self.carregar_categorias_locais()

            self.recover_active_countings()
            
            # Atualizar a aba de contagem
            if 'contagem' in self.ui_components:
                self.ui_components['contagem'].setup_ui()

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
        
            # Atualizar UI sempre, mesmo em caso de erro
            if 'contagem' in self.ui_components:
                self.ui_components['contagem'].setup_ui()
        
            self.page.update() 

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao carregar padrões: {ex}")

    def _carregar_binds_locais(self, padrao=None):
        """Backup para carregar binds do banco local quando a API falha"""
        try:
            if not padrao:
                return {}
            
            categorias = self.session.query(Categoria).filter_by(padrao=padrao).all()
            binds_locais = {}
            
            for cat in categorias:
                if cat.veiculo not in binds_locais and cat.bind != "N/A":
                    binds_locais[cat.veiculo] = cat.bind
                
            logging.info(f"✅ Binds carregados do banco local: {len(binds_locais)} itens")
            return binds_locais
        except Exception as ex:
            logging.error(f"❌ Erro ao carregar binds locais: {ex}")
            return {}
            
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
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        async def run_end_session():
            try:
                dialog.open = False
                self.page.update()
                logging.info("Iniciando processo de finalização via diálogo...")
                await self.end_session()
            except Exception as ex:
                logging.error(f"Erro ao finalizar sessão via diálogo: {ex}")

        dialog = ft.AlertDialog(
            title=ft.Text("Finalizar Sessão"),
            content=ft.Text("Você tem certeza que deseja finalizar a sessão?"),
            actions=[
                ft.TextButton("Sim", on_click=lambda e: self.page.run_task(run_end_session)),
                ft.TextButton("Cancelar", on_click=close_dialog),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def carregar_categorias_locais(self, padrao=None):
        padrao_atual = padrao or self.ui_components['inicio'].padrao_dropdown.value

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

                if 'contagem' in self.ui_components:
                    self.ui_components['contagem'].setup_ui()
                self.page.update()

            except Exception as ex:
                logging.error(f"[ERROR] Erro ao carregar categorias locais: {ex}")
                self.session.rollback()
                self.categorias = []

        return self.categorias

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