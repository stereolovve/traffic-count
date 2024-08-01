import flet as ft
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from pynput import keyboard
import pandas as pd
from datetime import datetime
import json
import os

Base = declarative_base()
engine = create_engine('sqlite:///dados.db')
Session = sessionmaker(bind=engine)
session = Session()

class Categoria(Base):
    __tablename__ = 'categorias'
    veiculo = Column(String)
    movimento = Column(Integer)
    bind = Column(String)
    count = Column(Integer, default=0)
    criado_em = Column(DateTime, default=datetime.now)
    __table_args__ = (PrimaryKeyConstraint('veiculo', 'movimento'),)

class Sessao(Base):
    __tablename__ = 'sessoes'
    sessao = Column(String, primary_key=True)
    detalhes = Column(String)
    criada_em = Column(DateTime, default=datetime.now)
    ativa = Column(Boolean)

class Contagem(Base):
    __tablename__ = 'contagens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sessao = Column(String, ForeignKey('sessoes.sessao'))
    movimento = Column(Integer)
    veiculo = Column(String, ForeignKey('categorias.veiculo'))
    count = Column(Integer, default=0)

Base.metadata.create_all(engine)

class ContadorPerplan(ft.Column):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.sessao = None
        self.movimentos = 1
        self.detalhes = {}
        self.contagens = {}
        self.binds = {}
        self.categorias = []
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
        self.selected_movimento = None
        self.setup_ui()
        self.carregar_sessao_ativa()

    def carregar_categorias_padrao(self, caminho_json):
        try:
            with open(caminho_json, 'r') as f:
                categorias_padrao = json.load(f)
                for categoria in categorias_padrao:
                    veiculo = categoria.get('veiculo')
                    movimento = categoria.get('movimento')
                    bind = categoria.get('bind')
                    if veiculo and bind:
                        
                        nova_categoria = Categoria(
                            veiculo=veiculo,
                            movimento=movimento,
                            bind=bind,
                            criado_em=datetime.now()
                        )
                        session.merge(nova_categoria)
                session.commit()
        except (FileNotFoundError, json.JSONDecodeError, SQLAlchemyError) as ex:
            print(f"Erro ao carregar categorias padrão: {ex}")
            session.rollback()

    def carregar_config(self):
        try:
            data = session.query(Categoria).order_by(Categoria.criado_em).all()
            contagens = {}
            for categoria in data:
                contagens[(categoria.veiculo, categoria.movimento)] = 0

            binds = {categoria.bind: (categoria.veiculo, categoria.movimento) for categoria in data}
            return contagens, binds, data
        except SQLAlchemyError as ex:
            print(f"Erro ao carregar config: {ex}")
            return {}, {}, []

    def carregar_sessao_ativa(self):
        try:
            sessao_ativa = session.query(Sessao).filter_by(ativa=True).first()
            if sessao_ativa:
                self.sessao = sessao_ativa.sessao
                self.detalhes = json.loads(sessao_ativa.detalhes)
                self.movimentos = int(self.detalhes["Movimentos"])
                self.page.overlay.append(ft.SnackBar(ft.Text("Sessão ativa recuperada.")))
                self.contagens, self.binds, self.categorias = self.carregar_config()
                self.setup_aba_contagem()
                self.tabs.selected_index = 1
                self.tabs.tabs[1].content.visible = True
                self.update_sessao_status()
                self.recuperar_contagens()
        except SQLAlchemyError as ex:
            print(f"Erro ao carregar sessão ativa: {ex}")

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
        except SQLAlchemyError as ex:
            print(f"Erro ao salvar sessão: {ex}")
            session.rollback()

    def finalizar_sessao(self):
        try:
            sessao_existente = session.query(Sessao).filter_by(sessao=self.sessao).first()
            if sessao_existente:
                sessao_existente.ativa = False
                session.commit()
        except SQLAlchemyError as ex:
            print(f"Erro ao finalizar sessão: {ex}")
            session.rollback()

    def setup_ui(self):
        self.tabs = ft.Tabs(
            animation_duration=150,
            tabs=[
                ft.Tab(text="Inicio", content=ft.Column()),
                ft.Tab(text="Contador", content=ft.Column()),
                ft.Tab(text="Categorias", content=ft.Column()),
                ft.Tab(text="", icon=ft.icons.SETTINGS, content=ft.Column())
            ]
        )
        self.controls.clear()
        self.controls.append(self.tabs)
        self.setup_aba_inicio()
        self.setup_aba_categorias()
        self.setup_aba_perfil()
        self.tabs.tabs[1].content.visible = False

    def setup_aba_inicio(self):
        tab = self.tabs.tabs[0].content
        tab.controls.clear()
        self.pesquisador_input = ft.TextField(label="Pesquisador")
        self.codigo_ponto_input = ft.TextField(label="Código")
        self.nome_ponto_input = ft.TextField(label="Ponto (ex: P10N)")
        self.horas_contagem_input = ft.TextField(label="Periodo (ex: 6h-18h)")
        self.movimentos_input = ft.Dropdown(
            label="Movimentos",
            options=[ft.dropdown.Option(str(i)) for i in range(1, 4)],
            value="1"
        )
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
            self.movimentos = int(self.movimentos_input.value)
            self.sessao = f"Sessao_{self.detalhes['Código']}_{self.detalhes['Ponto']}_{self.detalhes['Movimentos']}_{self.detalhes['Data do Ponto']}"
            self.carregar_categorias_padrao('categorias_padrao.json')  # Carregar categorias padrão apenas ao criar sessão
            self.salvar_sessao()
            self.contagens, self.binds, self.categorias = self.carregar_config()  # Recarregar configurações
            self.setup_aba_contagem()
            self.page.overlay.append(ft.SnackBar(ft.Text("Sessão criada com sucesso!")))
            self.tabs.selected_index = 1
            self.tabs.tabs[1].content.visible = True
            self.update_sessao_status()
        except Exception as ex:
            print(f"Erro ao criar sessão: {ex}")

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
        except SQLAlchemyError as ex:
            print(f"Erro ao validar campos: {ex}")
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
            icon_color="lightblue",
            tooltip="Salvar contagem",
            on_click=self.save_contagens
        )

        end_session_button = ft.IconButton(
            icon=ft.icons.STOP,
            tooltip="Finalizar sessão",
            icon_size=30,
            icon_color="RED",
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

        # Cabeçalho da Tabela
        header = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(content=ft.Text("Categoria", weight=ft.FontWeight.W_400, size=12), width=80),
                ft.Container(content=ft.Text("Bind", weight=ft.FontWeight.W_400, size=12), width=50),
                ft.Container(content=ft.Text("Contagem", weight=ft.FontWeight.W_400, size=12), width=80),
                ft.Container(content=ft.Text("Ações", weight=ft.FontWeight.W_400, size=12), width=50),
            ],
        )
        tab.controls.append(header)

        # Adicionar Divider
        divider = ft.Divider(height=2, thickness=1)
        tab.controls.append(divider)

        # Adicionar Columns para cada movimento com VerticalDivider
        colunas = []
        for movimento in range(1, self.movimentos + 1):
            col = ft.Column([ft.Text(f"Mov. {movimento}", weight=ft.FontWeight.BOLD)])
            for categoria in self.categorias:
                if categoria.movimento == movimento:
                    if movimento == 1:
                        self.add_contagem_row(col, categoria.veiculo, categoria.bind, self.contagens[(categoria.veiculo, movimento)], movimento)
                    else:
                        self.add_contagem_row_movimentos(col, categoria.veiculo, categoria.bind, self.contagens[(categoria.veiculo, movimento)], movimento)
            colunas.append(col)
            if movimento < self.movimentos:
                colunas.append(ft.VerticalDivider(width=5, thickness=2, color="white"))

        tab.controls.append(ft.Row(controls=colunas, alignment=ft.MainAxisAlignment.CENTER, spacing=10))
        self.page.update()

    def add_contagem_row(self, col, veiculo, bind, contagem, movimento):
        label_veiculo = ft.Text(f"{veiculo}", size=15, width=80)
        label_bind = ft.Text(f"({bind})", color="cyan", size=15, width=50)
        label_count = ft.Text(f"{contagem}", size=15, width=50)
        self.labels[(veiculo, movimento)] = label_count

        popup_menu = ft.PopupMenuButton(
            icon_color="teal",
            items=[
                ft.PopupMenuItem(text=" ", icon=ft.icons.ADD, on_click=lambda e, v=veiculo, m=movimento: self.increment(v, m)),
                ft.PopupMenuItem(text=" ", icon=ft.icons.REMOVE, on_click=lambda e, v=veiculo, m=movimento: self.decrement(v, m)),
                ft.PopupMenuItem(text=" ", icon=ft.icons.LOOP, on_click=lambda e, v=veiculo, m=movimento: self.reset(v, m))
            ]
        )

        row = ft.Row(
            alignment=ft.MainAxisAlignment.START,
            spacing=5,
            controls=[
                ft.Container(content=label_veiculo, alignment=ft.alignment.center_left),
                ft.Container(content=label_bind, alignment=ft.alignment.center),
                ft.Container(content=label_count, alignment=ft.alignment.center_right),
                popup_menu
            ]
        )
        col.controls.append(row)

    def add_contagem_row_movimentos(self, col, veiculo, bind, contagem, movimento):
        label_bind = ft.Text(f"({bind})", color="cyan", size=15, width=50)
        label_count = ft.Text(f"{contagem}", size=15, width=50)
        self.labels[(veiculo, movimento)] = label_count

        popup_menu = ft.PopupMenuButton(
            icon_color="teal",
            items=[
                ft.PopupMenuItem(text=" ", icon=ft.icons.ADD, on_click=lambda e, v=veiculo, m=movimento: self.increment(v, m)),
                ft.PopupMenuItem(text=" ", icon=ft.icons.REMOVE, on_click=lambda e, v=veiculo, m=movimento: self.decrement(v, m)),
                ft.PopupMenuItem(text=" ", icon=ft.icons.LOOP, on_click=lambda e, v=veiculo, m=movimento: self.reset(v, m))
            ]
        )

        row = ft.Row(
            alignment=ft.MainAxisAlignment.START,
            spacing=5,
            controls=[
                ft.Container(content=label_bind, alignment=ft.alignment.center),
                ft.Container(content=label_count, alignment=ft.alignment.center_right),
                popup_menu
            ]
        )
        col.controls.append(row)







    def toggle_contagem(self, e):
        self.contagem_ativa = e.control.value
        self.page.update()

    def increment(self, veiculo, movimento):
        try:
            self.contagens[(veiculo, movimento)] += 1
            self.update_labels(veiculo, movimento)
            self.save_to_db(veiculo, movimento)
        except Exception as ex:
            print(f"Erro ao incrementar: {ex}")

    def decrement(self, veiculo, movimento):
        try:
            if self.contagens[(veiculo, movimento)] > 0:
                self.contagens[(veiculo, movimento)] -= 1
                self.update_labels(veiculo, movimento)
                self.save_to_db(veiculo, movimento)
        except Exception as ex:
            print(f"Erro ao decrementar: {ex}")

    def reset(self, veiculo, movimento):
        try:
            self.contagens[(veiculo, movimento)] = 0
            self.update_labels(veiculo, movimento)
            self.save_to_db(veiculo, movimento)
        except Exception as ex:
            print(f"Erro ao resetar: {ex}")

    def update_labels(self, veiculo, movimento):
        try:
            self.labels[(veiculo, movimento)].value = str(self.contagens[(veiculo, movimento)])
            self.page.update()
        except Exception as ex:
            print(f"Erro ao atualizar labels: {ex}")

    def save_contagens(self, e):
        try:
            for movimento in range(1, self.movimentos + 1):
                contagens_df = pd.DataFrame([{veiculo: count for (veiculo, mov), count in self.contagens.items() if mov == movimento}])
                detalhes_df = pd.DataFrame([self.detalhes])
                
                contagens_df.fillna(0, inplace=True)
                
                if not os.path.exists('contagens'):
                    os.makedirs('contagens')
                arquivo_sessao = f'contagens/{self.sessao}.xlsx'

                try:
                    existing_df = pd.read_excel(arquivo_sessao, sheet_name=None)
                    if f'Movimento_{movimento}' in existing_df and 'Detalhes' in existing_df:
                        contagens_df = pd.concat([existing_df[f'Movimento_{movimento}'], contagens_df])
                        detalhes_df = pd.concat([existing_df['Detalhes'], detalhes_df])

                except FileNotFoundError:
                    pass

                with pd.ExcelWriter(arquivo_sessao, engine='xlsxwriter') as writer:
                    contagens_df.to_excel(writer, sheet_name=f'Movimento_{movimento}', index=False)
                    detalhes_df.to_excel(writer, sheet_name='Detalhes', index=False)
        except Exception as ex:
            print(f"Erro ao salvar contagens: {ex}")

    def confirmar_finalizar_sessao(self, e):
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        def end_and_close(e):
            try:
                dialog.open = False
                self.page.update()
                self.end_session()
            except Exception as ex:
                print(f"Erro ao finalizar sessão: {ex}")
            
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
            for veiculo, movimento in self.contagens:
                self.contagens[(veiculo, movimento)] = 0
                self.update_labels(veiculo, movimento)
                self.save_to_db(veiculo, movimento)
            self.sessao = None
            self.page.overlay.append(ft.SnackBar(ft.Text("Sessão finalizada!")))
            self.page.update()
            self.restart_app()
        except Exception as ex:
            print(f"Erro ao finalizar sessão: {ex}")

    def restart_app(self):
        self.stop_listener()
        self.sessao = None
        self.detalhes = {}
        self.contagens = {}
        self.binds = {}
        self.labels = {}
        self.setup_ui()
        self.page.update()
        self.start_listener()  # Reiniciar o listener para a nova sessão

    def save_to_db(self, veiculo, movimento):
        try:
            contagem = session.query(Contagem).filter_by(sessao=self.sessao, veiculo=veiculo, movimento=movimento).first()
            if contagem:
                contagem.count = self.contagens[(veiculo, movimento)]
            else:
                nova_contagem = Contagem(
                    sessao=self.sessao,
                    veiculo=veiculo,
                    movimento=movimento,
                    count=self.contagens[(veiculo, movimento)]
                )
                session.add(nova_contagem)
            session.commit()
        except SQLAlchemyError as ex:
            print(f"Erro ao salvar no DB: {ex}")
            session.rollback()

    def recuperar_contagens(self):
        try:
            contagens_db = session.query(Contagem).filter_by(sessao=self.sessao).all()
            for contagem in contagens_db:
                self.contagens[(contagem.veiculo, contagem.movimento)] = contagem.count
                self.update_labels(contagem.veiculo, contagem.movimento)
        except SQLAlchemyError as ex:
            print(f"Erro ao recuperar contagens: {ex}")

    def setup_aba_categorias(self):
        tab = self.tabs.tabs[2].content
        tab.controls.clear()

        movimentos = sorted(set(c.movimento for c in session.query(Categoria).all()))
        movimento_dropdown = ft.Dropdown(
            label="Selecione o movimento",
            options=[ft.dropdown.Option(str(mov)) for mov in movimentos],
            on_change=self.on_movimento_change,
        )
        tab.controls.append(movimento_dropdown)

        self.movimento_content = ft.Column()
        tab.controls.append(self.movimento_content)

        self.page.update()

    def on_movimento_change(self, e):
        self.selected_movimento = int(e.control.value)
        self.load_categorias(self.movimento_content)

    def load_categorias(self, container):
        container.controls.clear()
        try:
            if self.selected_movimento is not None:
                categorias = session.query(Categoria).filter_by(movimento=self.selected_movimento).order_by(Categoria.criado_em).all()
                for categoria in categorias:
                    container.controls.append(self.create_category_control(categoria.veiculo, categoria.bind, self.selected_movimento))
        except SQLAlchemyError as ex:
            print(f"Erro ao carregar categorias: {ex}")

        self.page.update()

    def create_category_control(self, veiculo, bind, movimento):
        veiculo_input = ft.TextField(value=veiculo, width=150, disabled=True)
        bind_input = ft.TextField(value=bind, width=90)
        update_button = ft.IconButton(icon=ft.icons.UPDATE, icon_color="BLUE", on_click=lambda e, v=veiculo, bi=bind_input: self.update_bind(v, bi.value, movimento))
        return ft.Row([veiculo_input, bind_input, update_button])

    def update_bind(self, veiculo, new_bind, movimento):
        if new_bind:
            try:
                categoria = session.query(Categoria).filter_by(veiculo=veiculo, movimento=movimento).first()
                if categoria:
                    categoria.bind = new_bind
                    session.commit()
                self.update_binds()
                self.update_ui()
            except SQLAlchemyError as ex:
                print(f"Erro ao atualizar bind: {ex}")
                session.rollback()

    def update_binds(self):
        try:
            self.binds = {categoria.bind: (categoria.veiculo, categoria.movimento) for categoria in session.query(Categoria).all()}
        except SQLAlchemyError as ex:
            print(f"Erro ao atualizar binds: {ex}")

    def update_ui(self):
        if self.selected_movimento is not None:
            self.load_categorias(self.movimento_content)

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
        except Exception as ex:
            print(f"Erro ao ajustar opacidade: {ex}")

    def on_key_press(self, key):
        if not self.contagem_ativa:
            return
        try:
            char = None
            if hasattr(key, 'vk') and key.vk in self.numpad_mappings:
                char = self.numpad_mappings[key.vk]
            elif hasattr(key, 'char'):
                char = key.char
            else:
                char = str(key).strip("'")
            if char and char in self.binds:
                veiculo, movimento = self.binds[char]
                self.increment(veiculo, movimento)
        except Exception as ex:
            print(f"Erro ao pressionar tecla: {ex}")

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
    page.window.height = 1080
    page.window.always_on_top = True
    page.add(contador)
    
    contador.start_listener()
    page.on_close = lambda e: contador.stop_listener()

ft.app(target=main)