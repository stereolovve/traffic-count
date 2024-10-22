import flet as ft
from database import Session, Categoria, Sessao, Contagem, Historico, init_db  # Importar os modelos e sessão do arquivo database.py
from sqlalchemy.exc import SQLAlchemyError
import aba_inicio
from initializer import inicializar_variaveis, configurar_numpad_mappings
import sessao
from pynput import keyboard
import pandas as pd
from datetime import datetime
import json
import os
import re

init_db()

class ContadorPerplan(ft.Column):
    #------------------------ CONSTRUTOR ------------------------
    def __init__(self, page):
        super().__init__()
        self.page = page
        # Inicializa variáveis e mapeamentos de teclado
        inicializar_variaveis(self)  # Chama a função para inicializar variáveis
        configurar_numpad_mappings(self)  # Chama a função para configurar mapeamento do numpad
        # Inicializa a interface e carrega a sessão ativa
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
        aba_inicio.validar_campos(self)


    def setup_aba_contagem(self):
        tab = self.tabs.tabs[1].content
        tab.controls.clear()
        self.contagem_ativa = False

        self.toggle_button = ft.Switch(
            tooltip="Ativar contagem",
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

        reset_all_button = ft.IconButton(
            icon=ft.icons.REFRESH,
            icon_color="orange",
            tooltip="Resetar todas as contagens",
            on_click=self.confirmar_resetar_todas_contagens  # Chama o diálogo de confirmação
        )

        # Adicionando o indicador de último salvamento
        self.last_save_label = ft.Text("Último salvamento: ainda não salvo", size=12, color="gray")

        controls_row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            controls=[self.toggle_button, save_button, end_session_button, reset_all_button],
        )

        tab.controls.append(controls_row)
        tab.controls.append(self.last_save_label)  # Exibe o texto de salvamento

        # Adicionar cabeçalho dentro de cada aba de contagem
        self.movimento_tabs = ft.Tabs(
            selected_index=0,
            animation_duration=50,
            tabs=[ft.Tab(text=movimento, content=self.criar_conteudo_movimento(movimento))
                for movimento in self.detalhes["Movimentos"]],
            expand=1,
        )

        tab.controls.append(self.movimento_tabs)

        # Cabeçalho movido para dentro da função criar_conteudo_movimento
        self.page.update()



    
    def resetar_todas_contagens(self, e):
        try:
            current_movimento = self.movimento_tabs.tabs[self.movimento_tabs.selected_index].text
            for veiculo in [v for v, m in self.contagens.keys() if m == current_movimento]:
                self.contagens[(veiculo, current_movimento)] = 0
                self.update_labels(veiculo, current_movimento)
                self.save_to_db(veiculo, current_movimento)
            snackbar = ft.SnackBar(ft.Text(f"Contagens do movimento '{current_movimento}' foram resetadas."), bgcolor="BLUE")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

            # Salvar no histórico
            self.salvar_historico(veiculo="N/A", movimento=current_movimento, acao="reset")

        except Exception as ex:
            print(f"Erro ao resetar contagens do movimento '{current_movimento}': {ex}")
            snackbar = ft.SnackBar(ft.Text(f"Erro ao resetar contagens do movimento '{current_movimento}'."), bgcolor="RED")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()


    def confirmar_resetar_todas_contagens(self, e):
        """Diálogo de confirmação para resetar todas as contagens"""
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        def reset_and_close(e):
            dialog.open = False
            self.page.update()
            self.resetar_todas_contagens(None)  # Chama o método real de resetar as contagens

        dialog = ft.AlertDialog(
            title=ft.Text("Resetar Todas as Contagens"),
            content=ft.Text("Você tem certeza que deseja resetar todas as contagens?"),
            actions=[
                ft.TextButton("Sim", on_click=reset_and_close),
                ft.TextButton("Cancelar", on_click=close_dialog),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    # Alterar o botão para chamar a confirmação
    

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
                ft.PopupMenuItem(text="Editar Contagem", icon=ft.icons.EDIT, on_click=lambda e: self.abrir_edicao_contagem(veiculo, movimento)  # Corrigir para passar os argumentos
),  # Exibe o campo para editar
                ft.PopupMenuItem(text="Editar Bind", icon=ft.icons.EDIT, on_click=lambda e, v=veiculo, m=movimento: self.editar_bind(v, m))
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
        """Atualiza a cor da borda (fundo) da janela com base no status do contador"""
        if self.contagem_ativa:
            # Cor verde para indicar que o contador está ativo
            self.page.window.bgcolor = "green"
            self.toggle_button.bgcolor = "lightgreen"
            self.toggle_button.shadow = ft.BoxShadow(blur_radius=15, color="lightgreen")  # Efeito de brilho
            
            # Efeito pulsante usando Animation
            self.toggle_button.scale = 1.1
            self.toggle_button.animate_scale = ft.Animation(duration=500, curve=ft.AnimationCurve.BOUNCE_OUT)
        else:
            # Cor vermelha para indicar que o contador está desativado
            self.page.window.bgcolor = "red"
            self.toggle_button.bgcolor = "orange"
            self.toggle_button.shadow = ft.BoxShadow(blur_radius=15, color="orange")
            
            # Remover animação quando o contador está desligado
            self.toggle_button.scale = 1.1
            self.toggle_button.animate_scale = ft.Animation(duration=500, curve=ft.AnimationCurve.EASE_IN_OUT)
        
        self.page.update()



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
            print(f"Erro ao incrementar: {ex}")

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
            print(f"Erro ao decrementar: {ex}")

    def reset(self, veiculo, movimento):
        print(f"Entrou no reset: veiculo={veiculo}, movimento={movimento}")  # Verificação de entrada
        try:
            self.contagens[(veiculo, movimento)] = 0
            self.update_labels(veiculo, movimento)
            self.save_to_db(veiculo, movimento)

            # Verifica o reset antes de salvar no histórico
            print(f"Registrando reset: veiculo={veiculo}, movimento={movimento}")

            # Salva no histórico a ação de reset
            self.salvar_historico(veiculo, movimento, "reset")

            snackbar = ft.SnackBar(ft.Text(f"Contagem de '{veiculo}' no movimento '{movimento}' foi resetada."), bgcolor="BLUE")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()

        except Exception as ex:
            print(f"Erro ao resetar contagem: {ex}")
            snackbar = ft.SnackBar(ft.Text(f"Erro ao resetar contagem de '{veiculo}' no movimento '{movimento}'."), bgcolor="RED")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()
    

    def abrir_edicao_contagem(self, veiculo, movimento):
        self.contagem_ativa = False
        self.atualizar_borda_contagem()
        self.page.update()
        def on_submit(e):
            try:
                # Capturar o valor inserido no campo de contagem
                print(f"[DEBUG] Valor inserido no campo de contagem: {input_contagem.value}")  # Debug
                nova_contagem = int(input_contagem.value)
                self.contagens[(veiculo, movimento)] = nova_contagem
                print(f"[DEBUG] Contagem atualizada: {self.contagens[(veiculo, movimento)]}")  # Debug
                self.update_labels(veiculo, movimento)
                self.save_to_db(veiculo, movimento)

                # Verificar se os valores de veículo e movimento estão corretos
                print(f"[DEBUG] Veículo: {veiculo}, Movimento: {movimento}, Sessão: {self.sessao}")

                # Registro no histórico da edição manual
                print(f"[DEBUG] Salvando no histórico: Veículo={veiculo}, Movimento={movimento}, Ação=edição manual")  # Debug
                self.salvar_historico(veiculo, movimento, "edição manual")  # Chamada para salvar no histórico

                # Notificação para o usuário
                snackbar = ft.SnackBar(ft.Text(f"Contagem de '{veiculo}' no movimento '{movimento}' foi atualizada para {nova_contagem}."), bgcolor="BLUE")
                self.page.overlay.append(snackbar)
                snackbar.open = True

                # Fechar o diálogo
                dialog.open = False
                self.contagem_ativa = True

                self.page.update()

                print(f"[DEBUG] Edição concluída e diálogo fechado.")  # Debug
            except ValueError:
                print("[ERROR] Valor de contagem inválido.")  # Debug

        # Campo para o usuário inserir a nova contagem
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
            print(f"Salvando no histórico: veiculo={veiculo}, movimento={movimento}, acao={acao}")
            novo_registro = Historico(
                sessao=self.sessao,
                veiculo=veiculo,
                movimento=movimento,
                timestamp=datetime.now(),
                acao=acao  # Salva a ação corretamente
            )
            self.session.add(novo_registro)
            self.session.commit()
            print(f"Ação '{acao}' registrada no histórico para veículo {veiculo} e movimento {movimento}.")
        except SQLAlchemyError as ex:
            print(f"Erro ao salvar histórico: {ex}")
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

            nome_pesquisador = re.sub(r'[<>:"/\\|?*]', '', self.detalhes['Pesquisador'])
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

            print(f"Contagem salva em {arquivo_sessao}")
            snackbar = ft.SnackBar(ft.Text("Contagens salvas com sucesso!"), bgcolor="GREEN")
            self.page.overlay.append(snackbar)
            snackbar.open = True

            # Atualizando o texto do último salvamento
            self.last_save_label.value = f"Último salvamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            self.page.update()

            # Registro no histórico que a contagem foi salva
            self.salvar_historico(veiculo="", movimento="", acao="salvamento")

        except Exception as ex:
            print(f"Erro ao salvar contagens: {ex}")
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
            print(f"Erro ao finalizar sessão: {ex}")
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
            print(f"Erro ao salvar no DB: {ex}")
            self.session.rollback()

    def recuperar_contagens(self):
        try:
            contagens_db = self.session.query(Contagem).filter_by(sessao=self.sessao).all()
            for contagem in contagens_db:
                self.contagens[(contagem.veiculo, contagem.movimento)] = contagem.count
                self.update_labels(contagem.veiculo, contagem.movimento)
        except SQLAlchemyError as ex:
            print(f"Erro ao recuperar contagens: {ex}")

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
            print(f"Erro ao atualizar atalho: {ex}")
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
            print(f"Erro ao atualizar bind: {ex}")
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
                print(f"Erro ao atualizar bind: {ex}")
                self.session.rollback()

    def update_binds(self):
        try:
            self.binds = {(categoria.bind, categoria.movimento): (categoria.veiculo, categoria.movimento) 
                        for categoria in self.session.query(Categoria).all()}
        except SQLAlchemyError as ex:
            print(f"Erro ao atualizar binds: {ex}")

    def update_ui(self):
        self.setup_aba_contagem()
        self.page.update()

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
            text="Carregar próximos 10 registros",
            on_click=self.carregar_historico
        )

        tab.controls.extend([
            header,
            carregar_historico_button,
            self.historico_lista
        ])
        self.page.update()

    def carregar_historico(self, e):
        try:
            registros = self.session.query(Historico)\
                .filter_by(sessao=self.sessao)\
                .order_by(Historico.timestamp.desc())\
                .limit(self.historico_page_size)\
                .all()

            # Verificar se registros foram encontrados
            print(f"Registros encontrados para a sessão {self.sessao}: {len(registros)}")
            
            self.historico_lista.controls.clear()
            for registro in registros:
                # Log para verificar o conteúdo de cada registro
                print(f"Registro: {registro.acao}, Veículo: {registro.veiculo}, Movimento: {registro.movimento}")

                # Condicional para exibir a ação "edição manual" em roxo
                if registro.acao == "edição manual":
                    cor = "purple"  # Destacar como roxo para edição manual
                elif registro.acao == "salvamento":
                    cor = "blue"
                elif registro.acao == "reset":
                    cor = "orange"
                elif registro.acao == "incremento":
                    cor = "green"
                elif registro.acao == "remoção":
                    cor = "red"
                else:
                    cor = "black"

                # Exibir cada registro no histórico
                linha = ft.Container(
                    content=ft.Text(
                        f"{registro.timestamp.strftime('%d/%m/%Y %H:%M:%S')} | Categoria: {registro.veiculo} | Movimento: {registro.movimento} | Ação: {registro.acao}",
                        color=cor),
                    padding=10,
                    border_radius=5
                )
                self.historico_lista.controls.append(linha)

            self.page.update()

        except SQLAlchemyError as ex:
            print(f"Erro ao carregar histórico: {ex}")

    def setup_aba_config(self):
        tab = self.tabs.tabs[3].content
        tab.controls.clear()
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.modo_claro_escuro = ft.Switch(label="Modo claro", on_change=self.theme_changed)
        opacity = ft.Slider(value=100, min=20, max=100, divisions=80, label="Opacidade", on_change=self.ajustar_opacidade)
        tab.controls.append(self.modo_claro_escuro)
        tab.controls.append(opacity)

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
            
            if hasattr(key, 'name') and key.name == 'caps_lock':
                # Controlar navegação apenas entre as abas de contagem (desconsiderando outros controles)
                self.movimento_tabs.selected_index = (self.movimento_tabs.selected_index + 1) % len(self.movimento_tabs.tabs)
                self.page.update()
                return

            # Alternar entre as abas com setas (navegação manual)
            if hasattr(key, 'name') and key.name == 'up':
                self.movimento_tabs.selected_index = (self.movimento_tabs.selected_index + 1) % len(self.movimento_tabs.tabs)
                self.page.update()
                return

            if hasattr(key, 'name') and key.name == 'down':
                self.movimento_tabs.selected_index = (self.movimento_tabs.selected_index - 1) % len(self.movimento_tabs.tabs)
                self.page.update()
                return

            # Mapeamento para controle do bind
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
            sessao_ativa = self.session.query(Sessao).filter_by(ativa=True).first()
            if sessao_ativa:
                self.sessao = sessao_ativa.sessao
                self.detalhes = json.loads(sessao_ativa.detalhes)
                snackbar = ft.SnackBar(ft.Text("Sessão ativa recuperada."), bgcolor="GREEN")
                self.page.overlay.append(snackbar)
                snackbar.open = True
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
            sessao_existente = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
            if sessao_existente:
                sessao_existente.detalhes = detalhes_json
                sessao_existente.ativa = True
            else:
                nova_sessao = Sessao(
                    sessao=self.sessao,
                    detalhes=detalhes_json,
                    ativa=True
                )
                self.session.add(nova_sessao)
            self.session.commit()
        except SQLAlchemyError as ex:
            print(f"Erro ao salvar sessão: {ex}")
            self.session.rollback()

    def finalizar_sessao(self):
        try:
            # Primeiro, remover todas as contagens associadas à sessão
            contagens_a_remover = self.session.query(Contagem).filter_by(sessao=self.sessao).all()
            for contagem in contagens_a_remover:
                self.session.delete(contagem)

            # Em seguida, remover a própria sessão
            sessao_a_remover = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
            if sessao_a_remover:
                self.session.delete(sessao_a_remover)

            self.session.commit()
            print(f"Sessão '{self.sessao}' e seus dados foram removidos com sucesso.")

            # Resetar contagens locais e atualizar a interface
            self.contagens.clear()
            self.binds.clear()
            self.labels.clear()
            self.sessao = None
            self.page.overlay.append(ft.SnackBar(ft.Text("Sessão finalizada e removida!")))
            self.page.update()

            self.restart_app()

        except Exception as ex:
            print(f"Erro ao finalizar e remover sessão: {ex}")
            self.page.overlay.append(ft.SnackBar(ft.Text(f"Erro ao finalizar sessão: {ex}")))
            self.session.rollback()
            self.page.update()



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
                            self.session.merge(nova_categoria)
                self.session.commit()
        except (FileNotFoundError, json.JSONDecodeError, SQLAlchemyError) as ex:
            print(f"Erro ao carregar categorias padrão: {ex}")
            self.session.rollback()

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
            print(f"Erro ao carregar config: {ex}")
            return {}, {}, []

    def update_sessao_status(self):
        self.sessao_status.value = f"Sessão ativa: {self.sessao}" if self.sessao else "Nenhuma sessão ativa"
        self.page.update()
        

def main(page: ft.Page):
    contador = ContadorPerplan(page)
    page.fonts = {
        'RobotoMono': "https://github.com/google/fonts/raw/main/apache/robotomono/RobotoMono%5Bwght%5D.ttf"}

    page.theme = ft.Theme(font_family="RobotoMono")
    page.scroll = ft.ScrollMode.AUTO
    
    page.window.width = 450
    page.window.height = 1080
    page.window.always_on_top = True
    

    page.add(contador)
    
    contador.start_listener()
    page.on_close = lambda e: contador.stop_listener()

ft.app(target=main)
