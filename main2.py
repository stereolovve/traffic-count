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
    movimento = Column(String)
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
    movimento = Column(String)
    veiculo = Column(String, ForeignKey('categorias.veiculo'))
    count = Column(Integer, default=0)

Base.metadata.create_all(engine)

class ContadorPerplan(ft.Column):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.sessao = None
        self.detalhes = {"Movimentos": []}  # Inicializar com Movimentos vazio
        self.contagens = {}
        self.binds = {}
        self.categorias = []
        self.labels = {}
        self.listener = None
        self.contagem_ativa = False
        self.novo_veiculo_input = None
        self.nova_bind_input = None
        self.numpad_mappings = {
            96: "np0", 97: "np1", 98: "np2", 99: "np3", 100: "np4",
            101: "np5", 102: "np6", 103: "np7", 104: "np8", 105: "np9",
        }
        self.movimento_tabs = None
        self.setup_ui()
        self.carregar_sessao_ativa()

    def setup_ui(self):
        self.tabs = ft.Tabs(
            animation_duration=150,
            tabs=[
                ft.Tab(text="Inicio", content=ft.Column()),
                ft.Tab(text="Contador", content=ft.Column()),
                ft.Tab(text="", icon=ft.icons.SETTINGS, content=ft.Column())
            ]
        )
        self.controls.clear()
        self.controls.append(self.tabs)
        self.setup_aba_inicio()
        self.setup_aba_perfil()
        self.tabs.tabs[1].content.visible = False

    def setup_aba_inicio(self):
        tab = self.tabs.tabs[0].content
        tab.controls.clear()
        self.pesquisador_input = ft.TextField(label="Pesquisador")
        self.codigo_ponto_input = ft.TextField(label="Código")
        self.nome_ponto_input = ft.TextField(label="Ponto (ex: P10N)")
        self.horas_contagem_input = ft.TextField(label="Periodo (ex: 6h-18h)")
        self.data_ponto_input = ft.TextField(label="Data do Ponto (dd-mm-aaaa)")
        
        self.movimentos_container = ft.Column()
        adicionar_movimento_button = ft.ElevatedButton(
            text="Adicionar Movimento",
            on_click=self.adicionar_campo_movimento
        )
        
        criar_sessao_button = ft.ElevatedButton(text="Criar Sessão", on_click=self.criar_sessao)

        tab.controls.extend([
            self.pesquisador_input,
            self.codigo_ponto_input,
            self.nome_ponto_input,
            self.horas_contagem_input,
            self.data_ponto_input,
            ft.Text("Movimentos:"),
            self.movimentos_container,
            adicionar_movimento_button,
            criar_sessao_button
        ])

        self.sessao_status = ft.Text("", weight=ft.FontWeight.BOLD)
        tab.controls.append(self.sessao_status)
        self.update_sessao_status()

    def adicionar_campo_movimento(self, e):
        movimento_input = ft.TextField(label=f"Nome do Movimento {len(self.movimentos_container.controls) + 1}")
        remover_button = ft.IconButton(
            icon=ft.icons.REMOVE,
            on_click=lambda _: self.remover_campo_movimento(movimento_input, remover_button)
        )
        row = ft.Row([movimento_input, remover_button])
        self.movimentos_container.controls.append(row)
        self.page.update()

    def remover_campo_movimento(self, movimento_input, remover_button):
        for row in self.movimentos_container.controls:
            if movimento_input in row.controls and remover_button in row.controls:
                self.movimentos_container.controls.remove(row)
                break
        self.page.update()

    def criar_sessao(self, e):
        if not self.validar_campos():
            return

        try:
            self.detalhes = {
                "Pesquisador": self.pesquisador_input.value,
                "Código": self.codigo_ponto_input.value,
                "Ponto": self.nome_ponto_input.value,
                "Periodo": self.horas_contagem_input.value,
                "Data do Ponto": self.data_ponto_input.value,
                "Movimentos": [mov.controls[0].value for mov in self.movimentos_container.controls]
            }
            self.sessao = f"Sessao_{self.detalhes['Código']}_{self.detalhes['Ponto']}_{self.detalhes['Data do Ponto']}"
            self.salvar_sessao()
            self.carregar_categorias_padrao('padrao.json')
            self.contagens, self.binds, self.categorias = self.carregar_config()
            self.setup_aba_contagem()
            self.page.overlay.append(ft.SnackBar(ft.Text("Sessão criada com sucesso!")))
            self.tabs.selected_index = 1
            self.tabs.tabs[1].content.visible = True
            self.update_sessao_status()
        except Exception as ex:
            print(f"Erro ao criar sessão: {ex}")

    def validar_campos(self):
        campos_obrigatorios = [
            (self.pesquisador_input, "Pesquisador"),
            (self.codigo_ponto_input, "Código"),
            (self.nome_ponto_input, "Ponto"),
            (self.horas_contagem_input, "Periodo"),
            (self.data_ponto_input, "Data do Ponto")
        ]

        for campo, nome in campos_obrigatorios:
            if not campo.value:
                self.page.overlay.append(ft.SnackBar(ft.Text(f"{nome} é obrigatório!")))
                self.page.update()
                return False

        if not self.movimentos_container.controls:
            self.page.overlay.append(ft.SnackBar(ft.Text("Adicione pelo menos um movimento!")))
            self.page.update()
            return False

        try:
            sessao_existente = session.query(Sessao).filter_by(sessao=f"Sessao_{self.codigo_ponto_input.value}_{self.nome_ponto_input.value}_{self.data_ponto_input.value}").first()
            if sessao_existente:
                self.page.overlay.append(ft.SnackBar(ft.Text("Sessão já existe com esses detalhes!")))
                self.page.update()
                return False
        except SQLAlchemyError as ex:
            print(f"Erro ao validar campos: {ex}")
            return False

        return True

    def setup_aba_contagem(self):
        tab = self.tabs.tabs[1].content
        tab.controls.clear()
        self.contagem_ativa = False

        self.toggle_button = ft.Switch(
            label="Ativar Contagem",
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
            icon_color="RED",
            on_click=self.confirmar_finalizar_sessao
        )

        controls_row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            controls=[self.toggle_button, save_button, end_session_button],
        )

        tab.controls.append(controls_row)

        self.movimento_tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[ft.Tab(text=movimento, content=self.criar_conteudo_movimento(movimento)) 
              for movimento in self.detalhes["Movimentos"]],
            expand=1,
        )

        for i, movimento in enumerate(self.detalhes["Movimentos"]):
            movimento_content = self.criar_conteudo_movimento(movimento)
            self.movimento_tabs.tabs[i].content = ft.Container(content=movimento_content, height=400)  # Altura fixa para teste

        tab.controls.append(self.movimento_tabs)

        atalhos_text = ft.Text(
            "Atalhos: F1, F2, F3... para alternar entre movimentos",
            size=12,
            color=ft.colors.GREY_400
        )
        tab.controls.append(atalhos_text)

        self.page.update()

    def criar_conteudo_movimento(self, movimento):
        content = ft.Column()
        categorias = [c for c in self.categorias if c.movimento == movimento]
        print(f"Criando conteúdo para {movimento}: {len(categorias)} categorias")
        for categoria in categorias:
            control = self.create_category_control(categoria.veiculo, categoria.bind, movimento)
            content.controls.append(control)
        return content

    def create_category_control(self, veiculo, bind, movimento):
        label_veiculo = ft.Text(f"{veiculo}", size=15, width=80)
        label_bind = ft.Text(f"({bind})", color="cyan", size=15, width=50)
        label_count = ft.Text(f"{self.contagens.get((veiculo, movimento), 0)}", size=15, width=50)
        self.labels[(veiculo, movimento)] = label_count

        popup_menu = ft.PopupMenuButton(
            icon_color="teal",
            items=[
                ft.PopupMenuItem(text=" ", icon=ft.icons.ADD, on_click=lambda e, v=veiculo, m=movimento: self.increment(v, m)),
                ft.PopupMenuItem(text=" ", icon=ft.icons.REMOVE, on_click=lambda e, v=veiculo, m=movimento: self.decrement(v, m)),
                ft.PopupMenuItem(text=" ", icon=ft.icons.LOOP, on_click=lambda e, v=veiculo, m=movimento: self.reset(v, m)),
                ft.PopupMenuItem(text="Editar Bind", icon=ft.icons.EDIT, on_click=lambda e, v=veiculo, m=movimento: self.editar_bind(v, m))
            ]
        )

        return ft.Row(
            alignment=ft.MainAxisAlignment.START,
            spacing=5,
            controls=[
                ft.Container(content=label_veiculo, alignment=ft.alignment.center_left),
                ft.Container(content=label_bind, alignment=ft.alignment.center),
                ft.Container(content=label_count, alignment=ft.alignment.center_right),
                popup_menu
            ]
        )

    def toggle_contagem(self, e):
        self.contagem_ativa = e.control.value
        self.page.update()

    def increment(self, veiculo, movimento):
        try:
            self.contagens[(veiculo, movimento)] = self.contagens.get((veiculo, movimento), 0) + 1
            print(f"Incrementado {veiculo} no movimento {movimento}. Nova contagem: {self.contagens[(veiculo, movimento)]}")
            self.update_labels(veiculo, movimento)
            self.save_to_db(veiculo, movimento)
            self.update_current_tab()
        except Exception as ex:
            print(f"Erro ao incrementar: {ex}")

    def update_current_tab(self):
        current_tab = self.movimento_tabs.tabs[self.movimento_tabs.selected_index]
        print(f"Atualizando aba: {current_tab.text}")
        current_tab.content.update()
        self.page.update()

    def decrement(self, veiculo, movimento):
        try:
            if self.contagens.get((veiculo, movimento), 0) > 0:
                self.contagens[(veiculo, movimento)] = self.contagens.get((veiculo, movimento), 0) - 1
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
            self.labels[(veiculo, movimento)].value = str(self.contagens.get((veiculo, movimento), 0))
            self.page.update()
        except Exception as ex:
            print(f"Erro ao atualizar labels: {ex}")

    def save_contagens(self, e):
        try:
            if not os.path.exists('contagens'):
                os.makedirs('contagens')
            arquivo_sessao = f'contagens/{self.sessao}.xlsx'

            with pd.ExcelWriter(arquivo_sessao, engine='xlsxwriter') as writer:
                for movimento in self.detalhes["Movimentos"]:
                    contagens_movimento = {veiculo: count for (veiculo, mov), count in self.contagens.items() if mov == movimento}
                    contagens_df = pd.DataFrame([contagens_movimento])
                    contagens_df.fillna(0, inplace=True)
                    contagens_df.to_excel(writer, sheet_name=movimento, index=False)

                detalhes_df = pd.DataFrame([self.detalhes])
                detalhes_df.to_excel(writer, sheet_name='Detalhes', index=False)

            self.page.overlay.append(ft.SnackBar(ft.Text("Contagens salvas com sucesso!")))
            self.page.update()
        except Exception as ex:
            print(f"Erro ao salvar contagens: {ex}")
            self.page.overlay.append(ft.SnackBar(ft.Text("Erro ao salvar contagens.")))
            self.page.update()

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
            for veiculo, movimento in list(self.contagens.keys()):
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
        self.detalhes = {"Movimentos": []}  # Reset Movimentos ao reiniciar
        self.contagens = {}
        self.binds = {}
        self.labels = {}
        self.setup_ui()
        self.page.update()
        self.start_listener()

    def save_to_db(self, veiculo, movimento):
        try:
            contagem = session.query(Contagem).filter_by(sessao=self.sessao, veiculo=veiculo, movimento=movimento).first()
            if contagem:
                contagem.count = self.contagens.get((veiculo, movimento), 0)
            else:
                nova_contagem = Contagem(
                    sessao=self.sessao,
                    veiculo=veiculo,
                    movimento=movimento,
                    count=self.contagens.get((veiculo, movimento), 0)
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

    def atualizar_atalho(self, e, veiculo, movimento):
        novo_atalho = e.control.value
        try:
            categoria = session.query(Categoria).filter_by(veiculo=veiculo, movimento=movimento).first()
            if categoria:
                categoria.bind = novo_atalho
                session.commit()
                self.update_binds()
                self.page.overlay.append(ft.SnackBar(ft.Text(f"Atalho atualizado para {veiculo}")))
        except SQLAlchemyError as ex:
            print(f"Erro ao atualizar atalho: {ex}")
            session.rollback()
        self.page.update()

    def atualizar_bind(self, e, veiculo, movimento):
        novo_bind = e.control.value
        try:
            categoria = session.query(Categoria).filter_by(veiculo=veiculo, movimento=movimento).first()
            if categoria:
                categoria.bind = novo_bind
                session.commit()
                self.update_binds()
                self.page.overlay.append(ft.SnackBar(ft.Text(f"Bind atualizado para {veiculo}")))
        except SQLAlchemyError as ex:
            print(f"Erro ao atualizar bind: {ex}")
            session.rollback()
        self.page.update()



    def adicionar_categoria(self, movimento):
        def salvar_categoria(e):
            novo_veiculo = veiculo_input.value
            novo_bind = bind_input.value
            if novo_veiculo and novo_bind:
                try:
                    nova_categoria = Categoria(veiculo=novo_veiculo, movimento=movimento, bind=novo_bind)
                    session.add(nova_categoria)
                    session.commit()
                    self.update_binds()
                    dialog.open = False
                    self.page.overlay.append(ft.SnackBar(ft.Text(f"Categoria {novo_veiculo} adicionada")))
                except SQLAlchemyError as ex:
                    print(f"Erro ao adicionar categoria: {ex}")
                    session.rollback()
            self.page.update()

        veiculo_input = ft.TextField(label="Veículo")
        bind_input = ft.TextField(label="Bind")
        dialog = ft.AlertDialog(
            title=ft.Text("Adicionar Nova Categoria"),
            content=ft.Column([veiculo_input, bind_input]),
            actions=[
                ft.TextButton("Salvar", on_click=salvar_categoria),
                ft.TextButton("Cancelar", on_click=lambda _: setattr(dialog, 'open', False))
            ]
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def editar_bind(self, veiculo, movimento):
        def on_bind_submit(e):
            new_bind = bind_input.value
            self.update_bind(veiculo, new_bind, movimento)
            dialog.open = False
            self.page.update()

        bind_input = ft.TextField(label="Novo Bind", width=100)
        dialog = ft.AlertDialog(
            title=ft.Text("Editar Bind"),
            content=bind_input,
            actions=[
                ft.TextButton("Salvar", on_click=on_bind_submit),
                ft.TextButton("Cancelar", on_click=lambda e: self.close_dialog(dialog)),
            ]
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def update_bind(self, veiculo, new_bind, movimento):
        if new_bind:
            try:
                categorias = session.query(Categoria).filter_by(veiculo=veiculo).all()
                for categoria in categorias:
                    categoria.bind = new_bind
                session.commit()
                self.update_binds()
                self.update_ui()
            except SQLAlchemyError as ex:
                print(f"Erro ao atualizar bind: {ex}")
                session.rollback()

    def update_binds(self):
        try:
            self.binds = {(categoria.bind, categoria.movimento): (categoria.veiculo, categoria.movimento) 
                        for categoria in session.query(Categoria).all()}
        except SQLAlchemyError as ex:
            print(f"Erro ao atualizar binds: {ex}")

    def update_ui(self):
        self.setup_aba_contagem()
        self.page.update()

    def setup_aba_perfil(self):
        tab = self.tabs.tabs[2].content
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
            if hasattr(key, 'name') and key.name.startswith('f') and key.name[1:].isdigit():
                index = int(key.name[1:]) - 1
                if 0 <= index < len(self.movimento_tabs.tabs):
                    self.movimento_tabs.selected_index = index
                    self.page.update()
                return

            char = None
            if hasattr(key, 'vk') and key.vk in self.numpad_mappings:
                char = self.numpad_mappings[key.vk]
            elif hasattr(key, 'char'):
                char = key.char
            else:
                char = str(key).strip("'")
            
            current_movimento = self.movimento_tabs.tabs[self.movimento_tabs.selected_index].text
            if (char, current_movimento) in self.binds:
                veiculo, movimento = self.binds[(char, current_movimento)]
                print(f"Char: {char}, Veículo: {veiculo}, Movimento: {movimento}, Movimento Atual: {current_movimento}")
                self.increment(veiculo, movimento)
            else:
                print(f"Nenhum bind encontrado para a tecla {char} no movimento {current_movimento}")
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

    def carregar_sessao_ativa(self):
        try:
            sessao_ativa = session.query(Sessao).filter_by(ativa=True).first()
            if sessao_ativa:
                self.sessao = sessao_ativa.sessao
                self.detalhes = json.loads(sessao_ativa.detalhes)
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

    def carregar_categorias_padrao(self, caminho_json):
        try:
            with open(caminho_json, 'r') as f:
                categorias_padrao = json.load(f)
                for categoria in categorias_padrao:
                    veiculo = categoria.get('veiculo')
                    bind = categoria.get('bind')
                    if veiculo and bind:
                        for movimento in self.detalhes["Movimentos"]:
                            nova_categoria = Categoria(
                                veiculo=veiculo,
                                movimento=movimento,
                                bind=bind,
                                criado_em=datetime.now()
                            )
                            session.merge(nova_categoria)
                session.commit()
            print("Categorias padrão carregadas com sucesso")
        except (FileNotFoundError, json.JSONDecodeError, SQLAlchemyError) as ex:
            print(f"Erro ao carregar categorias padrão: {ex}")
            session.rollback()

    def carregar_config(self):
        try:
            data = session.query(Categoria).order_by(Categoria.criado_em).all()
            print(f"Categorias carregadas: {len(data)}")
            contagens = {}
            binds = {}
            for categoria in data:
                contagens[(categoria.veiculo, categoria.movimento)] = 0
                binds[(categoria.bind, categoria.movimento)] = (categoria.veiculo, categoria.movimento)
            
            print(f"Binds carregados: {binds}")
            return contagens, binds, data
        except SQLAlchemyError as ex:
            print(f"Erro ao carregar config: {ex}")
            return {}, {}, []

    def update_sessao_status(self):
        self.sessao_status.value = f"Sessão ativa: {self.sessao}" if self.sessao else "Nenhuma sessão ativa"
        self.page.update()

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
