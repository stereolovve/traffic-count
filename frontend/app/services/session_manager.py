import logging
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from database.models import Sessao, Categoria, Contagem
import threading
import asyncio
import flet as ft
import re


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

            if not all(session_data.get(key) for key in ["codigo", "ponto", "horario_inicio", "data_ponto", "padrao"]):
                raise ValueError("Dados da sessão incompletos")

            if not session_data.get("movimentos"):
                raise ValueError("É necessário definir pelo menos um movimento")

            self.contador.details = {
                "Pesquisador": session_data["pesquisador"],
                "Código": session_data["codigo"],
                "Ponto": session_data["ponto"],
                "HorarioInicio": session_data["horario_inicio"],
                "Data do Ponto": session_data["data_ponto"],
                "Movimentos": session_data["movimentos"]
            }

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

            await self.contador.carregar_padroes_selecionados()
            await self.contador.load_categories_api(session_data["padrao"])
            self.contador.carregar_categorias_locais()

            nova_sessao = Sessao(
                sessao=self.contador.sessao,
                details=json.dumps(self.contador.details),
                padrao=session_data["padrao"],
                ativa=True
            )
            with self.contador.session_lock:
                self.contador.session.add(nova_sessao)
                self.contador.session.commit()

            self.contador.inicializar_arquivo_excel()

            success = await self.contador.send_session_to_django()
            if not success:
                logging.warning("⚠️ Sessão criada localmente, mas não registrada no servidor.")

            if 'contagem' in self.contador.ui_components:
                self.contador.ui_components['contagem'].setup_ui()

            self.contador.tabs.selected_index = 1
            self.contador.tabs.tabs[1].content.visible = True

            self.contador.page.overlay.append(
                ft.SnackBar(
                    content=ft.Text(
                        "Sessão criada com sucesso!" +
                        (" e registrada no servidor." if success else "")
                    ),
                    bgcolor="green"
                )
            )
            self.contador.page.update()

            self.contador.current_timeslot = datetime.strptime(session_data["horario_inicio"], "%H:%M")
            self.contador.details["current_timeslot"] = self.contador.current_timeslot.strftime("%H:%M")

        except Exception as ex:
            logging.error(f"Erro ao criar sessão: {ex}")
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
            details_json = json.dumps(self.contador.details)
            sessao_existente = self.contador.session.query(Sessao).filter_by(sessao=self.contador.sessao).first()
            if sessao_existente:
                sessao_existente.details = details_json
                sessao_existente.ativa = True
            else:
                nova_sessao = Sessao(
                    sessao=self.contador.sessao,
                    details=details_json,
                    ativa=True
                )
                self.contador.session.add(nova_sessao)
            self.contador.session.commit()
            logging.info(f"✅ Sessão {self.contador.sessao} salva e marcada como ativa!")
            
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao salvar sessão: {ex}")
            self.contador.session.rollback()

    async def load_active_session(self):
        try:
            sessao_ativa = self.contador.session.query(Sessao).filter_by(ativa=True).first()
            if not sessao_ativa:
                logging.info("[INFO] Nenhuma sessão ativa encontrada, iniciando sem sessão")
                self.contador.setup_ui()
                return False

            self.contador.sessao = sessao_ativa.sessao  
            self.contador.details = json.loads(sessao_ativa.details) 

            hoje = datetime.now().date()
            if "current_timeslot" in self.contador.details:
                horario = datetime.strptime(self.contador.details["current_timeslot"], "%H:%M").time()
            elif "HorarioInicio" in self.contador.details:
                horario = datetime.strptime(self.contador.details["HorarioInicio"], "%H:%M").time()
            else:
                horario = datetime.now().time()
            
            self.contador.current_timeslot = datetime.combine(hoje, horario)
            
            if "last_save_time" in self.contador.details:
                self.contador.last_save_time = datetime.strptime(self.contador.details["last_save_time"], "%H:%M:%S")
            else:
                self.contador.last_save_time = None

            self.contador.setup_ui()  
            await asyncio.sleep(0.5)

            if sessao_ativa:
                self.contador.ui_components['inicio'].padrao_dropdown.value = sessao_ativa.padrao

            await self.contador.ui_components['inicio'].load_padroes()
            await self.contador.carregar_padroes_selecionados()
            await self.contador.load_categories_api(self.contador.ui_components['inicio'].padrao_dropdown.value)
            self.contador.carregar_categorias_locais()

            self.contador.recover_active_countings()
            
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
            with self.contador.session_lock:
                if self.session.in_transaction():
                    self.session.commit()  

                contagem_periodo = self.contagens.get((veiculo, movimento), 0)
                
                with self.session.begin():
                    contagem = self.session.query(Contagem).filter_by(
                        sessao=self.contador.sessao,
                        veiculo=veiculo,
                        movimento=movimento
                    ).first()

                    if contagem:
                        contagem.count = contagem_periodo
                        contagem.contagem_total += contagem_periodo
                    else:
                        nova_contagem = Contagem(
                            sessao=self.contador.sessao,
                            veiculo=veiculo,
                            movimento=movimento,
                            count=contagem_periodo,
                            contagem_total=contagem_periodo
                        )
                        self.session.add(nova_contagem)
                
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

    def save_categories_in_local(self, categorias):
        try:
            with self.contador.session_lock:
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
                logging.debug("[DEBUG] Commit realizado!")

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao salvar categorias no banco: {ex}")
            self.session.rollback()

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

                logging.debug(f"[DEBUG] Categorias carregadas do banco: {[(c.veiculo, c.movimento) for c in self.categorias]}")

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
            logging.info("Iniciando processo de finalização da sessão...")
            
            # Tentar registrar a sessão no Django caso ainda não tenha sido feito
            await self.contador.send_session_to_django()
            
            # Notificar o Django para finalizar a sessão
            success = await self.contador.django_service.end_session(self.contador.sessao)
            
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
                    logging.info(f"Sessão {self.contador.sessao} marcada como inativa no banco local")

            # Limpar o estado atual
            self.contador.sessao = None
            self.contador.details = {"Movimentos": []}
            self.contagens.clear()
            self.contador.binds.clear()
            self.contador.labels.clear()

            # Feedback visual
            snackbar = ft.SnackBar(
                content=ft.Text("Sessão finalizada com sucesso!"),
                bgcolor="blue"
            )
            self.contador.page.overlay.append(snackbar)
            snackbar.open = True

            # Reiniciar a aplicação
            logging.info("Reiniciando aplicação após finalização da sessão...")
            self.contador.restart_app()
            
            # Voltar para a aba inicial
            self.contador.tabs.selected_index = 0
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
                logging.info("Iniciando processo de finalização via diálogo...")
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
