import flet as ft
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from pynput import keyboard
import pandas as pd
from datetime import datetime
import json
import os
import logging
import sys

# Configuração do logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')

Base = declarative_base()
engine = create_engine('sqlite:///dados.db')
Session = sessionmaker(bind=engine)
session = Session()

class Categoria(Base):
    __tablename__ = 'categorias'
    veiculo = Column(String, primary_key=True)
    bind = Column(String)
    count = Column(Integer, default=0)
    criado_em = Column(DateTime, default=datetime.now)

class Sessao(Base):
    __tablename__ = 'sessoes'
    sessao = Column(String, primary_key=True)
    detalhes = Column(String)
    criada_em = Column(DateTime, default=datetime.now)
    ativa = Column(Boolean)

Base.metadata.create_all(engine)

class ContadorPerplan(ft.Column):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.sessao = None
        self.detalhes = {}
        self.carregar_categorias_padrao('categorias_padrao.json')
        self.contagens, self.binds, self.categorias = self.carregar_config()
        self.labels = {}
        self.listener = None
        self.contagem_ativa = False
        self.novo_veiculo_input = None
        self.nova_bind_input = None
        self.numpad_mappings = {
            96: "np0",
            97: "np1",
            98: "np2",
            99: "np3",
            100: "np4",
            101: "np5",
            102: "np6",
            103: "np7",
            104: "np8",
            105: "np9",
        }
        self.setup_ui()
        self.carregar_sessao_ativa()

    def carregar_categorias_padrao(self, caminho_json):
        try:
            count = session.query(Categoria).count()
            if count == 0:
                with open(caminho_json, 'r') as f:
                    categorias_padrao = json.load(f)
                    for categoria in categorias_padrao:
                        veiculo = categoria.get('veiculo')
                        bind = categoria.get('bind')
                        if veiculo and bind:
                            nova_categoria = Categoria(
                                veiculo=veiculo,
                                bind=bind,
                                criado_em=datetime.now()
                            )
                            session.add(nova_categoria)
                    session.commit()
        except (FileNotFoundError, json.JSONDecodeError, SQLAlchemyError) as e:
            logging.error(f"Erro ao carregar categorias padrão: {e}")

    def carregar_config(self):
        try:
            data = session.query(Categoria).order_by(Categoria.criado_em).all()
            contagens = {categoria.veiculo: categoria.count for categoria in data}
            binds = {categoria.bind: categoria.veiculo for categoria in data}
            return contagens, binds, data
        except SQLAlchemyError as e:
            logging.error(f"Erro ao carregar configuração: {e}")
            return {}, {}, []

    def carregar_sessao_ativa(self):
        try:
            sessao_ativa = session.query(Sessao).filter_by(ativa=True).first()
            if sessao_ativa:
                self.sessao = sessao_ativa.sessao
                self.detalhes = json.loads(sessao_ativa.detalhes)
                self.page.overlay.append(ft.SnackBar(ft.Text("Sessão ativa recuperada.")))
                self.setup_aba_contagem()
                self.tabs.selected_index = 1
                self.tabs.tabs[1].content.visible = True
                self.update_sessao_status()
        except SQLAlchemyError as e:
            logging.error(f"Erro ao carregar sessão ativa: {e}")

    def salvar_sessao(self):
        try:
            detalhes_json = json.dumps(self.detalhes)
            sessao_existente = session.query(Sessao).filter_by(sessao=self.sessao).first()
            if sessao_existente:
                sessao_existente.detalhes = detalhes_json
                sessao_existente.ativa = True
            else:
                nova_sessao = Sessao(
                    sessao=self.sessao,
                    detalhes=detalhes_json,
                    ativa=True
                )
                session.add(nova_sessao)
            session.commit()
        except SQLAlchemyError as e:
            logging.error(f"Erro ao salvar sessão: {e}")

    def finalizar_sessao(self):
        try:
            sessao_existente = session.query(Sessao).filter_by(sessao=self.sessao).first()
            if sessao_existente:
                sessao_existente.ativa = False
                session.commit()
        except SQLAlchemyError as e:
            logging.error(f"Erro ao finalizar sessão: {e}")

    def setup_ui(self):
        self.tabs = ft.Tabs(
            animation_duration=150,
            tabs=[
                ft.Tab(text="Inicio", content=ft.Column()),
                ft.Tab(text="Contador", content=ft.Column()),
                ft.Tab(text="Categorias", content=ft.Column()),
                ft.Tab(text="", icon=ft.icons.SETTINGS, content=ft.Column()),
                ft.Tab(text="", icon=ft.icons.BAR_CHART, content=ft.Column()),
            ]
        )
        self.controls.clear()
        self.controls.append(self.tabs)
        self.setup_aba_inicio()
        self.setup_aba_categorias()
        self.setup_aba_perfil()
        self.setup_aba_relatorio()
        self.tabs.tabs[1].content.visible = False

    def setup_aba_inicio(self):
        tab = self.tabs.tabs[0].content
        tab.controls.clear()
        self.pesquisador_input = ft.TextField(label="Pesquisador")
        self.codigo_ponto_input = ft.TextField(label="Código")
        self.nome_ponto_input = ft.TextField(label="Ponto (ex: P10N)")
        self.horas_contagem_input = ft.TextField(label="Periodo (ex: 6h-18h)")
        self.movimentos_input = ft.TextField(label="Movimentos (ex: A-B)")
        self.data_ponto_input = ft.TextField(label="Data do Ponto (dd-mm-aaaa)")
        criar_sessao_button = ft.ElevatedButton(text="Criar Sessão", on_click=self.criar_sessao)

        tab.controls.extend([
            self.pesquisador_input,
            self.codigo_ponto_input,
            self.nome_ponto_input,
            self.horas_contagem_input,
            self.movimentos_input,
            self.data_ponto_input,
            criar_sessao_button
        ])

        self.sessao_status = ft.Text("", weight=ft.FontWeight.BOLD)
        tab.controls.append(self.sessao_status)
        self.update_sessao_status()

    def criar_sessao(self, e):
        if not self.validar_campos():
            return

        try:
            self.detalhes = {
                "Pesquisador": self.pesquisador_input.value,
                "Código": self.codigo_ponto_input.value,
                "Ponto": self.nome_ponto_input.value,
                "Periodo": self.horas_contagem_input.value,
                "Movimentos": self.movimentos_input.value,
                "Data do Ponto": self.data_ponto_input.value
            }
            self.sessao = f"Sessao_{self.detalhes['Código']}_{self.detalhes['Ponto']}_{self.detalhes['Movimentos']}_{self.detalhes['Data do Ponto']}"
            self.salvar_sessao()
            self.contagens, self.binds, self.categorias = self.carregar_config()  # Recarregar configurações
            self.setup_aba_contagem()
            self.page.overlay.append(ft.SnackBar(ft.Text("Sessão criada com sucesso!")))
            self.tabs.selected_index = 1
            self.tabs.tabs[1].content.visible = True
            self.update_sessao_status()
        except Exception as e:
            logging.error(f"Erro ao criar sessão: {e}")

    def validar_campos(self):
        if not self.pesquisador_input.value:
            self.page.overlay.append(ft.SnackBar(ft.Text("Pesquisador é obrigatório!")))
            self.page.update()
            return False
        if not self.codigo_ponto_input.value:
            self.page.overlay.append(ft.SnackBar(ft.Text("Código é obrigatório!")))
            self.page.update()
            return False
        if not self.nome_ponto_input.value:
            self.page.overlay.append(ft.SnackBar(ft.Text("Ponto é obrigatório!")))
            self.page.update()
            return False
        if not self.horas_contagem_input.value:
            self.page.overlay.append(ft.SnackBar(ft.Text("Periodo é obrigatório!")))
            self.page.update()
            return False
        if not self.movimentos_input.value:
            self.page.overlay.append(ft.SnackBar(ft.Text("Movimentos são obrigatórios!")))
            self.page.update()
            return False
        if not self.data_ponto_input.value:
            self.page.overlay.append(ft.SnackBar(ft.Text("Data do Ponto é obrigatória!")))
            self.page.update()
            return False

        try:
            sessao_existente = session.query(Sessao).filter_by(sessao=f"Sessao_{self.codigo_ponto_input.value}_{self.nome_ponto_input.value}_{self.movimentos_input.value}_{self.data_ponto_input.value}").first()
            if sessao_existente:
                self.page.overlay.append(ft.SnackBar(ft.Text("Sessão já existe com esses detalhes!")))
                self.page.update()
                return False
        except SQLAlchemyError as e:
            logging.error(f"Erro ao validar campos: {e}")
            return False

        return True

    def update_sessao_status(self):
        self.sessao_status.value = f"Sessão ativa: {self.sessao}" if self.sessao else "Nenhuma sessão ativa"
        self.page.update()

    def setup_aba_contagem(self):
        tab = self.tabs.tabs[1].content
        tab.controls.clear()
        self.contagem_ativa = False
        
        self.toggle_button = ft.Switch(
            label="",
            label_position="left",
            value=False,
            on_change=self.toggle_contagem
        )
        
        save_button = ft.IconButton(
            icon=ft.icons.SAVE,
            tooltip="Salvar contagem",
            on_click=self.save_contagens
        )
        
        end_session_button = ft.IconButton(
            icon=ft.icons.STOP,
            tooltip="Finalizar sessão",
            icon_size=30,
            on_click=self.confirmar_finalizar_sessao
        )
        
        container_switch = ft.Container(
            content=self.toggle_button,
            tooltip="Contagem Ativada/Desativada",
        )
        
        container_save = ft.Container(
            content=save_button,
        )
        
        container_stop = ft.Container(
            content=end_session_button,
        )
        
        row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            controls=[
                container_switch,
                container_save,
                container_stop
            ],
        )
        
        tab.controls.append(row)
        
        for categoria in self.categorias:
            self.add_row(categoria.veiculo, categoria.bind, tab)
        self.page.update()

    def toggle_contagem(self, e):
        self.contagem_ativa = e.control.value
        print("Contagem ativada" if self.contagem_ativa else "Contagem desativada")
        self.page.update()

    def add_row(self, veiculo, bind, tab):
        label_bind = ft.Text(f"({bind})", width=30, size=16, color="AMBER")
        label_veiculo = ft.Text(f"{veiculo}", width=80, size=18)
        label_count = ft.Text(f"{self.contagens[veiculo]}", width=50, size=20)
        self.labels[veiculo] = label_count
        
        add_button = ft.IconButton(
            ft.icons.ADD,
            style=ft.ButtonStyle(color=ft.colors.GREEN),
            on_click=lambda e, v=veiculo: self.increment(v)
        )
        
        remove_button = ft.IconButton(
            ft.icons.REMOVE,
            style=ft.ButtonStyle(color=ft.colors.RED),
            on_click=lambda e, v=veiculo: self.decrement(v)
        )
        
        reset_button = ft.IconButton(
            ft.icons.RESTART_ALT_ROUNDED,
            style=ft.ButtonStyle(color=ft.colors.BLUE),
            on_click=lambda e, v=veiculo: self.reset(v)
        )
        
        row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                label_bind,
                label_veiculo,
                label_count,
                add_button,
                remove_button,
                reset_button
            ]
        )
        tab.controls.append(row)

    def increment(self, veiculo):
        try:
            self.contagens[veiculo] += 1
            self.update_labels(veiculo)
            self.save_to_db(veiculo)
        except Exception as e:
            logging.error(f"Erro ao incrementar contagem: {e}")

    def decrement(self, veiculo):
        try:
            if self.contagens[veiculo] > 0:
                self.contagens[veiculo] -= 1
                self.update_labels(veiculo)
                self.save_to_db(veiculo)
        except Exception as e:
            logging.error(f"Erro ao decrementar contagem: {e}")

    def reset(self, veiculo):
        try:
            self.contagens[veiculo] = 0
            self.update_labels(veiculo)
            self.save_to_db(veiculo)
        except Exception as e:
            logging.error(f"Erro ao resetar contagem: {e}")

    def update_labels(self, veiculo):
        try:
            self.labels[veiculo].value = str(self.contagens[veiculo])
            self.page.update()
        except Exception as e:
            logging.error(f"Erro ao atualizar rótulos: {e}")

    def save_contagens(self, e):
        try:
            contagens_df = pd.DataFrame([self.contagens])
            detalhes_df = pd.DataFrame([self.detalhes])
            
            contagens_df.fillna(0, inplace=True)
            
            if not os.path.exists('contagens'):
                os.makedirs('contagens')
            arquivo_sessao = f'contagens/{self.sessao}.xlsx'

            try:
                existing_df = pd.read_excel(arquivo_sessao, sheet_name=None)
                if 'Detalhes' in existing_df and 'Contagens' in existing_df:
                    contagens_df = pd.concat([existing_df['Contagens'], contagens_df])
                    detalhes_df = pd.concat([existing_df['Detalhes'], detalhes_df])

            except FileNotFoundError:
                pass

            with pd.ExcelWriter(arquivo_sessao, engine='xlsxwriter') as writer:
                contagens_df.to_excel(writer, sheet_name='Contagens', index=False)
                detalhes_df.to_excel(writer, sheet_name='Detalhes', index=False)

            print(f"Contagem salva em {arquivo_sessao}")
            self.load_data_table()
        except Exception as e:
            logging.error(f"Erro ao salvar contagens: {e}")

    def confirmar_finalizar_sessao(self, e):
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        def end_and_close(e):
            try:
                dialog.open = False
                self.page.update()
                self.end_session()
            except Exception as e:
                logging.error(f"Erro ao finalizar sessão no diálogo: {e}")
            
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

    def end_session(self):
        try:
            self.finalizar_sessao()
            for veiculo in self.contagens:
                self.contagens[veiculo] = 0
                self.update_labels(veiculo)
                self.save_to_db(veiculo)
            self.sessao = None
            self.page.overlay.append(ft.SnackBar(ft.Text("Sessão finalizada!")))
            self.page.update()
            self.restart_app()
        except Exception as e:
            logging.error(f"Erro ao finalizar sessão: {e}")

    def restart_app(self):
        self.stop_listener()
        self.sessao = None
        self.detalhes = {}
        self.contagens = {}
        self.binds = {}
        self.labels = {}
        self.carregar_categorias_padrao('categorias_padrao.json')
        self.contagens, self.binds, self.categorias = self.carregar_config()  # Recarregar configurações
        self.setup_ui()
        self.page.update()
        self.start_listener()  # Reiniciar o listener para a nova sessão

    def save_to_db(self, veiculo):
        try:
            categoria = session.query(Categoria).filter_by(veiculo=veiculo).first()
            if categoria:
                categoria.count = self.contagens[veiculo]
                session.commit()
        except SQLAlchemyError as e:
            logging.error(f"Erro ao salvar no banco de dados: {e}")

    def setup_aba_categorias(self):
        tab = self.tabs.tabs[2].content
        tab.controls.clear()
        self.load_categorias(tab)

    def load_categorias(self, tab):
        try:
            categorias = session.query(Categoria).order_by(Categoria.criado_em).all()
            for categoria in categorias:
                self.add_category_row(categoria.veiculo, categoria.bind, tab)
        except SQLAlchemyError as e:
            logging.error(f"Erro ao carregar categorias: {e}")

    def add_category_row(self, veiculo, bind, tab):
        veiculo_input = ft.TextField(value=veiculo, width=150, disabled=True)
        bind_input = ft.TextField(value=bind, width=90)
        update_button = ft.IconButton(icon=ft.icons.UPDATE, icon_color="BLUE", on_click=lambda e, v=veiculo, bi=bind_input: self.update_bind(v, bi.value))
        row = ft.Row([veiculo_input, bind_input, update_button])
        tab.controls.append(row)

    def update_bind(self, veiculo, new_bind):
        if new_bind:
            try:
                categoria = session.query(Categoria).filter_by(veiculo=veiculo).first()
                if categoria:
                    categoria.bind = new_bind
                    session.commit()
                self.update_categorias()
            except SQLAlchemyError as e:
                logging.error(f"Erro ao atualizar bind: {e}")

    def update_categorias(self):
        self.categorias = self.carregar_config()[2]
        self.update_ui()

    def update_ui(self):
        tab_categorias = self.tabs.tabs[2].content
        tab_categorias.controls.clear()
        self.load_categorias(tab_categorias)

        tab_contagem = self.tabs.tabs[1].content
        tab_contagem.controls.clear()
        self.setup_aba_contagem()
        
        self.page.update()

    def setup_aba_perfil(self):
        tab = self.tabs.tabs[3].content
        tab.controls.clear()
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.c = ft.Switch(label="Modo claro", on_change=self.theme_changed)
        opacity = ft.Slider(value=100, min=20, max=100, divisions=80, label="Opacidade", on_change=self.ajustar_opacidade)
        tab.controls.append(self.c)
        tab.controls.append(opacity)

    def theme_changed(self, e):
        self.page.theme_mode = (
            ft.ThemeMode.DARK
            if self.page.theme_mode == ft.ThemeMode.LIGHT
            else ft.ThemeMode.LIGHT
        )
        self.c.label = (
            "Modo claro" if self.page.theme_mode == ft.ThemeMode.LIGHT else "Modo escuro"
        )
        self.page.update()

    def ajustar_opacidade(self, e):
        try:
            nova_opacidade = e.control.value / 100
            self.page.window.opacity = nova_opacidade
            self.page.update()
        except Exception as e:
            logging.error(f"Erro ao ajustar opacidade: {e}")

    def setup_aba_relatorio(self):
        tab = self.tabs.tabs[4].content
        tab.controls.clear()
        self.page.scroll = ft.ScrollMode.AUTO
        self.view_relatorio(tab)

    def view_relatorio(self, tab):
        try:
            arquivo_sessao = f'contagens/{self.sessao}.xlsx'
            df_contagens = pd.read_excel(arquivo_sessao, sheet_name='Contagens')
            if df_contagens.empty:
                tab.controls.append(ft.Text("Não há dados salvos."))
            else:
                detalhes_texto = "\n".join([f"{key}: {value}" for key, value in self.detalhes.items()])
                tab.controls.append(ft.Text(detalhes_texto, weight=ft.FontWeight.BOLD))
                columns = [
                    ft.DataColumn(ft.Text(col, weight=ft.FontWeight.BOLD))
                    for col in df_contagens.columns
                ]
                rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(int(row[col])) if pd.api.types.is_numeric_dtype(row[col]) else str(row[col]))) for col in df_contagens.columns if pd.notna(row[col])
                        ]
                    )
                    for _, row in df_contagens.iterrows()
                ]
                data_table = ft.DataTable(
                    columns=columns,
                    rows=rows,
                    border=ft.border.all(2, "red"),
                    divider_thickness=0,
                    border_radius=5,
                    show_checkbox_column=False,
                )
                tab.controls.append(data_table)
        except FileNotFoundError:
            tab.controls.append(ft.Text("Não há dados salvos."))
        except ValueError as e:
            tab.controls.append(ft.Text(str(e)))
        except Exception as e:
            logging.error(f"Erro ao visualizar relatório: {e}")
        self.page.update()

    def load_data_table(self):
        tab = self.tabs.tabs[4].content
        tab.controls.clear()
        self.view_relatorio(tab)

    def on_key_press(self, key):
        if not self.contagem_ativa:
            return
        try:
            char = None
            if hasattr(key, 'vk') and key.vk in self.numpad_mappings:
                char = self.numpad_mappings[key.vk]
            elif hasattr(key, 'char'):
                char = key.char
            if char:
                veiculo = self.binds.get(char)
                if veiculo:
                    self.increment(veiculo)
        except Exception as e:
            logging.error(f"Erro ao processar tecla: {e}")

    def start_listener(self):
        if self.listener is None:
            self.listener = keyboard.Listener(on_press=self.on_key_press)
            self.listener.start()

    def stop_listener(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener = None

def main(page: ft.Page):
    contador = ContadorPerplan(page)
    page.fonts = {
        "Jetbrains": "assets/fonts/JetbrainsMono.ttf",
        "RobotoMono": "assets/fonts/RobotoMono.ttf",
    }

    page.theme = ft.Theme(font_family="Jetbrains")
    page.scroll = ft.ScrollMode.AUTO
    
    page.window.width = 450
    page.window.height = 700
    page.window.always_on_top = True
    page.add(contador)
    
    contador.start_listener()
    page.on_close = lambda e: contador.stop_listener()

ft.app(target=main)
