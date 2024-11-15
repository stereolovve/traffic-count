import flet as ft
from database.models import Session, Categoria, Sessao, Contagem, Historico, init_db  # Importar os modelos e sessão do arquivo database.py
from sqlalchemy.exc import SQLAlchemyError
from app import aba_inicio, aba_contagem, aba_historico, listener, sessao
from utils.initializer import inicializar_variaveis, configurar_numpad_mappings
from auth.login import LoginPage
from auth.register import RegisterPage
from pynput import keyboard
from utils.padrao_contagem import carregar_categorias_padrao
import pandas as pd
from datetime import datetime
import os
import re
from utils.change_binds import change_binds
import logging
import httpx
import json

#------------------------ LOGGING -------------------------
logging.basicConfig(
    level=logging.ERROR, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), 
              logging.StreamHandler()]
)
#------------------------ SETUP DATABASE ------------------
init_db()
#------------------------ CONTADOR PERPLAN ----------------
class ContadorPerplan(ft.Column):
    #------------------------ CONSTRUTOR ------------------
    def __init__(self, page, username, app):
        
        
        super().__init__()
        self.tokens = None
        self.page = page
        self.username = username # nome do user autenticado pelo django
        self.app = app
        inicializar_variaveis(self)  
        configurar_numpad_mappings(self) 
        self.setup_ui()
        self.carregar_sessao_ativa()


    #------------------------ SETUP UI ------------------------
    def setup_ui(self):
        self.tabs = ft.Tabs(
            tabs=[
                ft.Tab(text="Inicio", content=ft.Column(width=450, height=900)),  # Substituindo o content por Column
                ft.Tab(text="Contador", content=ft.Column(width=450, height=900)),
                ft.Tab(text="Histórico", content=ft.Column(width=450, height=900)),
                ft.Tab(text="", icon=ft.icons.SETTINGS, content=ft.Column(width=450, height=900))
            ]
        )
        self.controls.clear()
        self.controls.append(self.tabs)
        self.setup_aba_inicio()
        self.setup_aba_contagem()
        self.setup_aba_historico()
        self.setup_aba_config()
        self.tabs.tabs[1].content.visible = False
        self.atualizar_borda_contagem()


    #------------------------ ABA INICIO ------------------------
    def setup_aba_inicio(self):
        aba_inicio.setup_aba_inicio(self)
        
    def adicionar_campo_movimento(self, e):
        aba_inicio.adicionar_campo_movimento(self, e)

    def remover_campo_movimento(self, movimento_input, remover_button):
        aba_inicio.remover_campo_movimento(self, movimento_input, remover_button)

    def criar_sessao(self, e):
        sessao.criar_sessao(self, e)

    def confirmar_finalizar_sessao(self, e):
        sessao.confirmar_finalizar_sessao(self, e)

    def end_session(self):
        sessao.end_session(self)


    def validar_campos(self):
        campos_obrigatorios = [
            (self.codigo_ponto_input, "Código"),
            (self.nome_ponto_input, "Ponto"),
            (self.horas_contagem_input, "Periodo"),
            (self.data_ponto_input, "Data do Ponto")
        ]

        for campo, nome in campos_obrigatorios:
            if not campo.value:
                snackbar = ft.SnackBar(ft.Text(f"{nome} é obrigatório!"), bgcolor="ORANGE")
                self.page.overlay.append(snackbar)
                snackbar.open = True
                self.page.update()
                return False

        if not self.movimentos_container.controls:
            snackbar = ft.SnackBar(ft.Text("Adicione pelo menos um movimento!"), bgcolor="ORANGE")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()
            return False

        try:
            sessao_existente = self.session.query(Sessao).filter_by(sessao=f"Sessao_{self.codigo_ponto_input.value}_{self.nome_ponto_input.value}_{self.data_ponto_input.value}").first()
            if sessao_existente:
                snackbar = ft.SnackBar(ft.Text("Sessão já existe com esses detalhes!"), bgcolor="YELLOW")
                self.page.overlay.append(snackbar)
                snackbar.open = True
                self.page.update()
                return False
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao validar campos: {ex}")
            return False

        return True

    # ------------------------ ABA CONTADOR ------------------------
    def setup_aba_contagem(self):
        aba_contagem.setup_aba_contagem(self)
  
    def resetar_todas_contagens(self, e):
        aba_contagem.resetar_todas_contagens(self, e)

    def confirmar_resetar_todas_contagens(self, e):
        aba_contagem.confirmar_resetar_todas_contagens(self, e)

    def criar_conteudo_movimento(self, movimento):
        content = ft.Column()
        # Adicionar o cabeçalho para cada movimento, colocando em um Row com height fixo para evitar sobreposição
        header = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(content=ft.Text("       Categoria", weight=ft.FontWeight.W_400, size=12), width=150, height=40),
                ft.Container(content=ft.Text("Bind", weight=ft.FontWeight.W_400, size=12), width=50, height=40),
                ft.Container(content=ft.Text("Contagem", weight=ft.FontWeight.W_400, size=12), width=80, height=40),
                ft.Container(content=ft.Text("Ações", weight=ft.FontWeight.W_400, size=12), width=50, height=40),
            ],
            height=50,  # Define uma altura fixa para evitar que ele suba e cause sobreposição
        )

        content.controls.append(header)

        categorias = [c for c in self.categorias if c.movimento == movimento]
        for categoria in categorias:
            control = self.create_category_control(categoria.veiculo, categoria.bind, movimento)
            content.controls.append(control)

        return content


    def create_category_control(self, veiculo, bind, movimento):
        label_veiculo = ft.Text(f"{veiculo}", size=15, width=100)
        label_bind = ft.Text(f"({bind})", color="cyan", size=15, width=50)
        label_count = ft.Text(f"{self.contagens.get((veiculo, movimento), 0)}", size=15, width=50)
        self.labels[(veiculo, movimento)] = label_count

        # Variável para manter o campo escondido até ser necessário
        campo_visivel = False

        popup_menu = ft.PopupMenuButton(
            icon_color="teal",
            items=[
                ft.PopupMenuItem(text="Adicionar", icon=ft.icons.ADD, on_click=lambda e, v=veiculo, m=movimento: self.increment(v, m)),
                ft.PopupMenuItem(text="Remover", icon=ft.icons.REMOVE, on_click=lambda e, v=veiculo, m=movimento: self.decrement(v, m)),
                ft.PopupMenuItem(text="Editar Contagem", icon=ft.icons.EDIT, on_click=lambda e: self.abrir_edicao_contagem(veiculo, movimento)),
            ]
        )

        return ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
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
        self.atualizar_borda_contagem()  # Atualiza a borda ao alternar o estado do contador
        self.page.update()

    def atualizar_borda_contagem(self):
        aba_contagem.atualizar_borda_contagem(self)


    def increment(self, veiculo, movimento):
        try:
            self.contagens[(veiculo, movimento)] = self.contagens.get((veiculo, movimento), 0) + 1
            self.update_labels(veiculo, movimento)
            self.save_to_db(veiculo, movimento)
            self.salvar_historico(veiculo, movimento, "incremento")
            self.update_current_tab()

            # Adiciona uma entrada no feed
            self.page.update()

        except Exception as ex:
            logging.error(f"Erro ao incrementar: {ex}")

    def decrement(self, veiculo, movimento):
        try:
            if self.contagens.get((veiculo, movimento), 0) > 0:
                self.contagens[(veiculo, movimento)] = self.contagens.get((veiculo, movimento), 0) - 1
                self.update_labels(veiculo, movimento)
                self.save_to_db(veiculo, movimento)
                self.salvar_historico(veiculo, movimento, "remoção")

                # Adiciona uma entrada no feed
                self.page.update()

        except Exception as ex:
            logging.error(f"Erro ao decrementar: {ex}")


    def abrir_edicao_contagem(self, veiculo, movimento):
        self.contagem_ativa = False
        self.atualizar_borda_contagem()
        self.page.update()
        def on_submit(e):
            try:
                # Capturar o valor inserido no campo de contagem
                nova_contagem = int(input_contagem.value)
                self.contagens[(veiculo, movimento)] = nova_contagem
                self.update_labels(veiculo, movimento)
                self.save_to_db(veiculo, movimento)

                # Registro no histórico da edição manual
                self.salvar_historico(veiculo, movimento, "edição manual")  # Chamada para salvar no histórico

                # Notificação para o usuário
                snackbar = ft.SnackBar(ft.Text(f"Contagem de '{veiculo}' no movimento '{movimento}' foi atualizada para {nova_contagem}."), bgcolor="BLUE")
                self.page.overlay.append(snackbar)
                snackbar.open = True

                # Fechar o diálogo
                dialog.open = False
                self.contagem_ativa = True

                self.page.update()

            except ValueError:
                logging.error("[ERROR] Valor de contagem inválido.")  # Debug

        input_contagem = ft.TextField(label="Nova Contagem", keyboard_type=ft.KeyboardType.NUMBER, on_submit=on_submit)
        dialog = ft.AlertDialog(
            title=ft.Text(f"Editar Contagem: {veiculo}"),
            content=input_contagem,
            actions=[ft.TextButton("Salvar", on_click=on_submit)],
            on_dismiss=lambda e: dialog.open == False,
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()


    def salvar_historico(self, veiculo, movimento, acao):
        try:
            # Verificar se a função está sendo chamada
            novo_registro = Historico(
                sessao=self.sessao,
                veiculo=veiculo,
                movimento=movimento,
                timestamp=datetime.now(),
                acao=acao  # Salva a ação corretamente
            )
            self.session.add(novo_registro)
            self.session.commit()
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao salvar histórico: {ex}")
            self.session.rollback()


    def update_current_tab(self):
        current_tab = self.movimento_tabs.tabs[self.movimento_tabs.selected_index]
        current_tab.content.update()
        self.page.update()

    def update_labels(self, veiculo, movimento):
            self.labels[(veiculo, movimento)].value = str(self.contagens.get((veiculo, movimento), 0))
            self.page.update()
            
    def update_sessao_status(self):
        self.sessao_status.value = f"Sessão ativa: {self.sessao}" if self.sessao else "Nenhuma sessão ativa"
        self.page.update()

    def save_contagens(self, e):
        try:
            contagens_dfs = {}
            for movimento in self.detalhes["Movimentos"]:
                contagens_movimento = {veiculo: count for (veiculo, mov), count in self.contagens.items() if mov == movimento}
                contagens_df = pd.DataFrame([contagens_movimento])
                contagens_df.fillna(0, inplace=True)
                contagens_dfs[movimento] = contagens_df

            detalhes_df = pd.DataFrame([self.detalhes])

            nome_pesquisador = re.sub(r'[<>:"/\\|?*]', '', self.username)
            codigo = re.sub(r'[<>:"/\\|?*]', '', self.detalhes['Código'])

            diretorio_base = r'Z:\0Pesquisa\_0ContadorDigital\Contagens'
            
            if not os.path.exists(diretorio_base):
                diretorio_base = os.getcwd()

            diretorio_pesquisador_codigo = os.path.join(diretorio_base, nome_pesquisador, codigo)
            if not os.path.exists(diretorio_pesquisador_codigo):
                os.makedirs(diretorio_pesquisador_codigo)

            arquivo_sessao = os.path.join(diretorio_pesquisador_codigo, f'{self.sessao}.xlsx')

            try:
                existing_df = pd.read_excel(arquivo_sessao, sheet_name=None)
                for movimento in self.detalhes["Movimentos"]:
                    if movimento in existing_df:
                        contagens_dfs[movimento] = pd.concat([existing_df[movimento], contagens_dfs[movimento]])
                if 'Detalhes' in existing_df:
                    detalhes_df = pd.concat([existing_df['Detalhes'], detalhes_df])
            except FileNotFoundError:
                pass

            with pd.ExcelWriter(arquivo_sessao, engine='xlsxwriter') as writer:
                for movimento, df in contagens_dfs.items():
                    df.to_excel(writer, sheet_name=movimento, index=False)
                detalhes_df.to_excel(writer, sheet_name='Detalhes', index=False)

            logging.info(f"Contagem salva em {arquivo_sessao}")
            snackbar = ft.SnackBar(ft.Text("Contagens salvas com sucesso!"), bgcolor="GREEN")
            self.page.overlay.append(snackbar)
            snackbar.open = True

            # Atualizando o texto do último salvamento
            self.last_save_label.value = f"Último salvamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            self.page.update()

            # Registro no histórico que a contagem foi salva
            self.salvar_historico(veiculo="", movimento="", acao="salvamento")

        except Exception as ex:
            logging.error(f"Erro ao salvar contagens: {ex}")
            snackbar = ft.SnackBar(ft.Text("Erro ao salvar contagens."), bgcolor="RED")
            self.page.overlay.append(snackbar)
            snackbar.open = True
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

    def end_session(self):
        try:
            self.finalizar_sessao()  # Marca a sessão como finalizada no banco de dados
            
            # Reseta as contagens atuais para 0
            for veiculo, movimento in list(self.contagens.keys()):
                self.contagens[(veiculo, movimento)] = 0
                self.update_labels(veiculo, movimento)
                self.save_to_db(veiculo, movimento)
            
            # Limpa a sessão ativa
            self.sessao = None
            self.detalhes = {"Movimentos": []}
            self.contagens = {}
            self.binds = {}
            self.labels = {}

            # Notifica o usuário
            self.page.overlay.append(ft.SnackBar(ft.Text("Sessão finalizada!")))
            self.page.update()

            # Reinicia o aplicativo
            self.restart_app()
        except Exception as ex:
            logging.error(f"Erro ao finalizar sessão: {ex}")
            self.page.overlay.append(ft.SnackBar(ft.Text(f"Erro ao finalizar sessão: {ex}")))
            self.page.update()


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
            contagem = self.session.query(Contagem).filter_by(sessao=self.sessao, veiculo=veiculo, movimento=movimento).first()
            if contagem:
                contagem.count = self.contagens.get((veiculo, movimento), 0)
            else:
                nova_contagem = Contagem(
                    sessao=self.sessao,
                    veiculo=veiculo,
                    movimento=movimento,
                    count=self.contagens.get((veiculo, movimento), 0)
                )
                self.session.add(nova_contagem)
            self.session.commit()
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao salvar no DB: {ex}")
            self.session.rollback()

    def recuperar_contagens(self):
        try:
            contagens_db = self.session.query(Contagem).filter_by(sessao=self.sessao).all()
            for contagem in contagens_db:
                self.contagens[(contagem.veiculo, contagem.movimento)] = contagem.count
                self.update_labels(contagem.veiculo, contagem.movimento)
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao recuperar contagens: {ex}")

    def atualizar_atalho(self, e, veiculo, movimento):
        novo_atalho = e.control.value
        try:
            categoria = self.session.query(Categoria).filter_by(veiculo=veiculo, movimento=movimento).first()
            if categoria:
                categoria.bind = novo_atalho
                self.session.commit()
                self.update_binds()
                snackbar = ft.SnackBar(ft.Text(f"Atalho atualizado para {veiculo}"), bgcolor="GREEN")
                self.page.overlay.append(snackbar)
                snackbar.open = True
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao atualizar atalho: {ex}")
            self.session.rollback()
        self.page.update()

    def atualizar_bind(self, e, veiculo, movimento):
        novo_bind = e.control.value
        try:
            categoria = self.session.query(Categoria).filter_by(veiculo=veiculo, movimento=movimento).first()
            if categoria:
                categoria.bind = novo_bind
                self.session.commit()
                self.update_binds()
                snackbar = ft.SnackBar(ft.Text(f"Bind atualizado para {veiculo}"), bgcolor="GREEN")
                self.page.overlay.append(snackbar)
                snackbar.open = True
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao atualizar bind: {ex}")
            self.session.rollback()
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
                categorias = self.session.query(Categoria).filter_by(veiculo=veiculo).all()
                for categoria in categorias:
                    categoria.bind = new_bind
                self.session.commit()
                self.update_binds()
                self.update_ui()
            except SQLAlchemyError as ex:
                logging.error(f"Erro ao atualizar bind: {ex}")
                self.session.rollback()

    def update_binds(self):
        try:
            self.binds = {(categoria.bind, categoria.movimento): (categoria.veiculo, categoria.movimento) 
                        for categoria in self.session.query(Categoria).all()}
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao atualizar binds: {ex}")

    def update_ui(self):
        self.setup_aba_contagem()
        self.page.update()

    #------------------- ABA HISTÓRICO -----------------------------
    def setup_aba_historico(self):
        tab = self.tabs.tabs[2].content
        tab.controls.clear()

        header = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(content=ft.Text("Histórico de Contagens", weight=ft.FontWeight.W_400, size=15))
            ]
        )

        self.historico_lista = ft.ListView(spacing=10, padding=20, auto_scroll=True)

        carregar_historico_button = ft.ElevatedButton(
            text="Carregar próximos 30 registros",
            on_click=self.carregar_historico
        )

        tab.controls.extend([
            header,
            carregar_historico_button,
            self.historico_lista
        ])
        self.page.update()

    def carregar_historico(self, e):
        aba_historico.carregar_historico(self, e)

    #------------------- ABA CONFIGURACOES -----------------------------
    def setup_aba_config(self):
        tab = self.tabs.tabs[3].content
        tab.controls.clear()
        
        # Controle de modo claro/escuro
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.modo_claro_escuro = ft.Switch(label="Modo claro", on_change=self.theme_changed)
        
        # Slider para opacidade
        opacity = ft.Slider(value=100, min=20, max=100, divisions=80, label="Opacidade", on_change=self.ajustar_opacidade)
        
        # Botão para configurar binds
        config_button = ft.ElevatedButton(text="Configurar Binds", on_click=lambda e: change_binds(self.page, self))
        self.page.update()
        
        logout_button = ft.ElevatedButton(
        text="Sair",
        bgcolor="RED",
        color="WHITE",
        on_click=self.logout_user
        )
        
        # Adicionando controles à aba de configurações
        tab.controls.append(self.modo_claro_escuro)
        tab.controls.append(opacity)
        tab.controls.append(config_button)  # Adiciona o botão de configuração de binds
        tab.controls.append(logout_button)
        self.page.update()

    def theme_changed(self, e):
        self.page.theme_mode = (
            ft.ThemeMode.DARK
            if self.page.theme_mode == ft.ThemeMode.LIGHT
            else ft.ThemeMode.LIGHT
        )
        self.modo_claro_escuro.label = (
            "Modo claro" if self.page.theme_mode == ft.ThemeMode.LIGHT else "Modo escuro"
        )
        self.page.update()

    def ajustar_opacidade(self, e):
        try:
            nova_opacidade = e.control.value / 100
            self.page.window.opacity = nova_opacidade
            self.page.update()
        except Exception as ex:
            logging.error(f"Erro ao ajustar opacidade: {ex}")
    #------------------- LISTENER -----------------------------
    def on_key_press(self, key):
        listener.on_key_press(self, key)

    def start_listener(self):
        if self.listener is None:
            self.listener = keyboard.Listener(on_press=self.on_key_press)
            self.listener.start()

    def stop_listener(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener = None

    def carregar_sessao_ativa(self):
        sessao.carregar_sessao_ativa(self)

    def salvar_sessao(self):
        sessao.salvar_sessao(self)

    def finalizar_sessao(self):
        sessao.finalizar_sessao(self)

    def carregar_categorias_padrao(self, caminho_json):
        carregar_categorias_padrao(self, caminho_json)

    def carregar_config(self):
        try:
            data = self.session.query(Categoria).order_by(Categoria.criado_em).all()
            contagens = {}
            binds = {}
            for categoria in data:
                contagens[(categoria.veiculo, categoria.movimento)] = 0
                binds[(categoria.bind, categoria.movimento)] = (categoria.veiculo, categoria.movimento)
            
            return contagens, binds, data
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao carregar config: {ex}")
            return {}, {}, []

    def update_sessao_status(self):
        self.sessao_status.value = f"Sessão ativa: {self.sessao}" if self.sessao else "Nenhuma sessão ativa"
        self.page.update()
        
        
    def logout_user(self, e):
        try:
            # Limpar os tokens e dados do usuário
            self.tokens = None
            self.username = None

            # Remove o arquivo de tokens local (se existir)
            if os.path.exists("auth_tokens.json"):
                os.remove("auth_tokens.json")

            self.app.reset_app()
            self.page.controls.clear()
            self.page.add(LoginPage(self))  # Mostra a página de login
            self.page.update()

            logging.info("Usuário desconectado com sucesso.")
        except AttributeError as ex:
            logging.error(f"Erro ao deslogar: {ex}")
            if not self.page:
                logging.error("Página está faltando ao tentar deslogar.")
        

#------------------- MAIN -----------------------------
def main(page: ft.Page):
    print("A função main foi chamada.")
    page.title = "Contador Perplan"
    page.window.width = 800
    page.window.height = 600
    page.window.center()
    class MyApp:
        def __init__(self, page):
            self.page = page
            self.tokens = None
            self.username = None
        
        def switch_to_main_app(self):
            
            self.page.controls.clear()
            contador = ContadorPerplan(page, username=self.username, app=self)
            self.page.add(contador)

            # Configuração da janela
            self.page.window.width = 450
            self.page.window.height = 1080
            self.page.window.always_on_top = True

            # Iniciar o listener
            contador.start_listener()

            # Configurar fechamento
            self.page.on_close = lambda e: contador.stop_listener()
            self.page.update()

        def show_login_page(self):
            """Mostra a tela de login."""
            self.page.controls.clear()
            self.page.add(LoginPage(self))
            self.page.update()

        def show_register_page(self):
            """Mostra a tela de registro."""
            self.page.controls.clear()
            self.page.add(RegisterPage(self))
            self.page.update()

        def reset_app(self):
            """Reinicia a aplicação para o estado inicial."""
            self.tokens = None
            self.username = None
            self.page.controls.clear()
            self.show_login_page()
    app = MyApp(page)
    
    if os.path.exists("auth_tokens.json"):
        try:
            with open("auth_tokens.json", "r") as f:
                saved_data = json.load(f)
                app.tokens = saved_data["tokens"]
                app.username = saved_data["username"]
                app.switch_to_main_app()
        except Exception as ex:
            logging.error(f"Erro ao carregar tokens salvos: {ex}")
            app.show_login_page()
    else:
        app.show_login_page()
        


# Inicia o aplicativo Flet
ft.app(target=main)

