import flet as ft
from datetime import datetime
import json
import logging
import re
from database.models import Sessao, Session
from utils.config import API_URL
from utils.api import async_api_request


class AbaInicio(ft.Column):
    def __init__(self, contador):
        super().__init__()
        self.contador = contador
        self.page = contador.page
        self.tokens = contador.tokens
        
        # Label para mostrar mensagem de sessão ativa
        self.session_active_label = ft.Text(
            "⚠️ Já existe uma sessão ativa. Encerre a sessão atual antes de iniciar uma nova.",
            size=16,
            weight=ft.FontWeight.BOLD,
            color="RED",
            visible=False
        )
        self.controls.append(self.session_active_label)

        # Container para os controles que serão bloqueados
        self.inputs_container = ft.Container(
            content=ft.Column(
                controls=[],
                spacing=10
            ),
            padding=ft.padding.all(16),
            border_radius=10,
            bgcolor=ft.colors.SURFACE_VARIANT
        )
        self.controls.append(self.inputs_container)
        
        hoje_str = datetime.now().strftime("%d-%m-%Y")
        user_label = ft.Text(
            f"Usuário logado: {self.contador.username}", 
            size=16, 
            weight=ft.FontWeight.BOLD, 
            color="BLUE"
        )
        self.inputs_container.content.controls.append(user_label)

        # Campo de busca para o código
        self.codigo_search_input = ft.TextField(
            label="Pesquisar Código",
            hint_text="Digite para filtrar...",
            on_change=self.filtrar_codigos,
            expand=True,
            border_radius=8
        )
        self.inputs_container.content.controls.append(self.codigo_search_input)

        # Dropdowns para Código e Ponto
        self.codigo_dropdown = ft.Dropdown(
            label="Código",
            options=[],
            on_change=self.on_codigo_selected,
            expand=True,
            border_radius=8
        )
        self.inputs_container.content.controls.append(self.codigo_dropdown)

        self.ponto_dropdown = ft.Dropdown(
            label="Ponto",
            options=[ft.dropdown.Option(key="placeholder", text="Selecione o código primeiro...")],
            value="placeholder",
            on_change=self.on_ponto_selected,
            expand=True,
            border_radius=8,
            disabled=True
        )
        self.inputs_container.content.controls.append(self.ponto_dropdown)

        # Campos ocultos que serão preenchidos automaticamente
        self.codigo_ponto_input = ft.TextField(
            label="Código do Ponto",
            hint_text="Ex: ER2403",
            icon=ft.icons.CODE,
            expand=True,
            border_radius=8,
            visible=False
        )
        self.inputs_container.content.controls.append(self.codigo_ponto_input)

        self.nome_ponto_input = ft.TextField(
            label="Nome do Ponto",
            hint_text="Ex: P10; P15",
            icon=ft.icons.LOCATION_PIN,
            expand=True,
            border_radius=8,
            visible=False
        )
        self.inputs_container.content.controls.append(self.nome_ponto_input)

        self.data_ponto_input = ft.TextField(
            label="Data",
            hint_text="dd-mm-aaaa",
            value=hoje_str,
            icon=ft.icons.CALENDAR_MONTH,
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
            border_radius=8
        )
        self.inputs_container.content.controls.append(self.data_ponto_input)

        self.selected_time = "00:00"

        # Substituir time picker por campo de texto com máscara/validação
        self.horario_input = ft.TextField(
            label="Horário de Início",
            hint_text="HH:MM",
            value=self.selected_time,
            icon=ft.icons.ACCESS_ALARM,
            expand=True,
            border_radius=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self.validar_horario
        )
        self.inputs_container.content.controls.append(self.horario_input)

        self.padrao_dropdown = ft.Dropdown(
            label="Selecione o Padrão",
            options=[],
            on_change=self.carregar_padroes_selecionados,
            expand=True,
        )
        self.inputs_container.content.controls.append(self.padrao_dropdown)

        self.movimentos_container = ft.Column()
        self.inputs_container.content.controls.append(self.movimentos_container)

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
        self.inputs_container.content.controls.append(adicionar_movimento_button)

        criar_sessao_button = ft.ElevatedButton(
            text="Criar Sessão",
            on_click=self.iniciar_criacao_sessao,
            width=float('inf'),
            height=50,
            icon=ft.icons.SEND
        )
        self.inputs_container.content.controls.append(criar_sessao_button)

        self.api_padroes_container = ft.Column()
        self.inputs_container.content.controls.append(self.api_padroes_container)

        self.page.update()

        # Carregar dados iniciais e verificar sessão ativa
        async def load_initial_data():
            await self.check_active_session()
            await self.load_codigos()
            await self.load_padroes()

        self.page.run_task(load_initial_data)

    async def check_active_session(self):
        """Verifica se existe uma sessão ativa e atualiza a interface"""
        try:
            # Criar uma nova sessão do SQLAlchemy
            session = Session()
            
            # Verificar no banco de dados local usando SQLAlchemy
            active_session = session.query(Sessao).filter(Sessao.ativa == True).first()
            
            if active_session:
                # Sessão ativa encontrada
                self.session_active_label.visible = True
                self.inputs_container.visible = False
                # Desabilitar todos os controles
                for control in self.inputs_container.content.controls:
                    if hasattr(control, 'disabled'):
                        control.disabled = True
            else:
                # Nenhuma sessão ativa
                self.session_active_label.visible = False
                self.inputs_container.visible = True
                # Habilitar todos os controles
                for control in self.inputs_container.content.controls:
                    if hasattr(control, 'disabled'):
                        control.disabled = False
            
            # Fechar a sessão
            session.close()
            
            if self.page:
                self.page.update()
        except Exception as ex:
            logging.error(f"Erro ao verificar sessão ativa: {ex}")
            if self.page:
                self.page.update()

    async def load_codigos(self):
        try:
            headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"}
            response = await async_api_request(
                "GET",
                "/trabalhos/api/codigos/", 
                headers=headers
            )
            
            # Converter a resposta de texto para JSON se necessário
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except json.JSONDecodeError:
                    logging.error("Resposta da API não é um JSON válido")
                    self.codigo_dropdown.options = [ft.dropdown.Option("Erro na API")]
                    if self.page:
                        self.page.update()
                    return
            
            # Ordenar alfabeticamente
            response = sorted(response, key=lambda x: x['codigo'])
            self.todos_codigos = response
            self.codigo_dropdown.options = [
                ft.dropdown.Option(
                    key=str(codigo['id']),
                    text=codigo['codigo'],
                    data=codigo
                ) for codigo in response
            ]
            
            if self.page:
                self.page.update()
        except Exception as ex:
            logging.error(f"Erro ao carregar códigos: {ex}")
            self.codigo_dropdown.options = [ft.dropdown.Option("Erro na API")]
            if self.page:
                self.page.update()

    async def on_codigo_selected(self, e):
        codigo_id = e.control.value
        if codigo_id:
            try:
                # Atualizar mensagem do dropdown de ponto
                self.ponto_dropdown.options = [ft.dropdown.Option(key="loading", text="Carregando pontos...")]
                self.ponto_dropdown.value = "loading"
                self.ponto_dropdown.disabled = True
                self.ponto_dropdown.update()

                headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"}
                response = await async_api_request(
                    "GET",
                    f"/trabalhos/api/codigos/{codigo_id}/",
                    headers=headers
                )
                
                if not response:
                    logging.error(f"Código {codigo_id} não encontrado")
                    self.ponto_dropdown.options = [ft.dropdown.Option(key="no_points", text="Nenhum ponto encontrado")]
                    self.ponto_dropdown.value = "no_points"
                    self.ponto_dropdown.update()
                    return
                
                # Carregar pontos do código
                await self.load_pontos(codigo_id)
            except Exception as ex:
                logging.error(f"Erro ao carregar detalhes do código: {ex}")
                self.ponto_dropdown.options = [ft.dropdown.Option(key="error", text="Erro ao carregar pontos")]
                self.ponto_dropdown.value = "error"
                self.ponto_dropdown.disabled = True
                self.ponto_dropdown.update()
        else:
            self.ponto_dropdown.options = [ft.dropdown.Option(key="placeholder", text="Selecione o código primeiro...")]
            self.ponto_dropdown.value = "placeholder"
            self.ponto_dropdown.disabled = True
            self.ponto_dropdown.update()

    async def load_pontos(self, codigo_id):
        try:
            headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"}
            response = await async_api_request(
                "GET",
                f"/trabalhos/api/pontos/?codigo={codigo_id}",
                headers=headers
            )
            
            # Converter a resposta de texto para JSON se necessário
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except json.JSONDecodeError:
                    logging.error("Resposta da API não é um JSON válido")
                    self.ponto_dropdown.options = [ft.dropdown.Option(key="error", text="Erro ao carregar pontos")]
                    self.ponto_dropdown.value = "error"
                    self.ponto_dropdown.disabled = True
                    if self.page:
                        self.page.update()
                    return
            
            if not response:
                self.ponto_dropdown.options = [ft.dropdown.Option(key="no_points", text="Nenhum ponto encontrado")]
                self.ponto_dropdown.value = "no_points"
                self.ponto_dropdown.disabled = True
                self.page.update()
                return
            
            self.ponto_dropdown.options = [
                ft.dropdown.Option(
                    key=str(ponto['id']),
                    text=ponto['nome']  # Agora só o nome, sem localização
                ) for ponto in response
            ]
            
            self.ponto_dropdown.value = None
            self.ponto_dropdown.disabled = False
            
            if self.page:
                self.page.update()
        except Exception as ex:
            logging.error(f"Erro ao carregar pontos: {ex}")
            self.ponto_dropdown.options = [ft.dropdown.Option(key="error", text="Erro ao carregar pontos")]
            self.ponto_dropdown.value = "error"
            self.ponto_dropdown.disabled = True
            if self.page:
                self.page.update()

    async def on_ponto_selected(self, e):
        ponto_id = e.control.value
        # Ignorar requisições para valores de placeholder/loading/error
        if ponto_id in ["placeholder", "loading", "error", "no_points"]:
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"}
            response = await async_api_request(
                "GET",
                f"/trabalhos/api/pontos/{ponto_id}/",
                headers=headers
            )
            
            # Converter a resposta de texto para JSON se necessário
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except json.JSONDecodeError:
                    logging.error("Resposta da API não é um JSON válido")
                    return
            
            self.codigo_ponto_input.value = response['codigo_info']['codigo']
            self.nome_ponto_input.value = response['nome']  # Agora só o nome, sem localização
            
            if self.page:
                self.page.update()
        except Exception as ex:
            logging.error(f"Erro ao carregar detalhes do ponto: {ex}")

    async def load_padroes(self):
        try:
            if not self.page:
                self.page = self.contador.page
            
            headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"} if self.contador.tokens and 'access' in self.contador.tokens else {}

            response = await async_api_request(
                "GET",
                "/padroes/tipos-de-padrao/", 
                headers=headers
            )
            
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

            if self.page:
                self.page.update()
        except Exception as ex:
            logging.error(f"Erro ao carregar tipos de padrões: {ex}")
            self.padrao_dropdown.options = [ft.dropdown.Option("Erro na API")]
            if self.page:
                self.page.update()

    def validar_campos(self):
        campos_obrigatorios = [
            (self.codigo_dropdown, "Código"),
            (self.ponto_dropdown, "Ponto"),
            (self.data_ponto_input, "Data do Ponto")
        ]

        campos_vazios = []
        for campo, nome in campos_obrigatorios:
            if isinstance(campo, ft.Dropdown) or isinstance(campo, ft.TextField):
                if not campo.value:
                    campos_vazios.append(nome)
            elif isinstance(campo, ft.ElevatedButton):
                if campo.text == "00:00":  # Verifica se o horário não foi selecionado
                    campos_vazios.append(nome)

        if campos_vazios:
            mensagem = "Por favor, preencha os seguintes campos obrigatórios:\n" + "\n".join(campos_vazios)
            self.page.show_snack_bar(ft.SnackBar(ft.Text(mensagem)))
            return False
        return True

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
            cache_key = f"padrao_binds_{padrao_selecionado_str}"
            
            headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"} if self.contador.tokens and 'access' in self.contador.tokens else {}
            response = await async_api_request(
                "GET",
                f"/padroes/merged-binds/?pattern_type={padrao_selecionado_str}",
                headers=headers
            )

            # Usar um dicionário para garantir unicidade dos binds
            binds_dict = {}
            for item in response:
                veiculo = item["veiculo"]
                if veiculo not in binds_dict:
                    binds_dict[veiculo] = item["bind"]

            self.contador.binds = binds_dict
            
            if 'contagem' in self.contador.ui_components:
                self.contador.ui_components['contagem'].setup_ui()
            
            self.page.update()

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao carregar padrões do usuário: {ex}")
            self.padrao_dropdown.options = [ft.dropdown.Option("Erro na API")]
            if self.page:
                self.page.update()

    async def iniciar_criacao_sessao(self, e):
        if not self.validar_campos():
            return

        # Desabilitar botão e mostrar loading
        e.control.disabled = True
        e.control.text = "Criando sessão..."
        e.control.update()
        
        banner = self.contador.show_loading("Criando sessão e carregando padrões...")

        try:
            # Criar objeto de sessão com os dados dos dropdowns
            session_data = {
                "pesquisador": self.contador.username,
                "codigo": self.codigo_ponto_input.value,
                "ponto": self.nome_ponto_input.value,
                "horario_inicio": self.horario_input.value,
                "data_ponto": self.data_ponto_input.value,
                "padrao": self.padrao_dropdown.value,
                "movimentos": [
                    movimento.controls[0].value 
                    for movimento in self.movimentos_container.controls
                    if movimento.controls[0].value
                ]
            }

            await self.contador.create_session(session_data)
            # Após criar a sessão, verificar novamente o estado
            await self.check_active_session()

        except Exception as ex:
            logging.error(f"Erro ao criar sessão: {ex}")
            self.contador.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"Erro ao criar sessão: {str(ex)}"),
                    bgcolor="red"
                )
            )
        finally:
            # Restaurar estado do botão
            e.control.disabled = False
            e.control.text = "Criar Sessão"
            e.control.update()
            
            # Remover banner de loading
            if banner:
                self.contador.hide_loading(banner)

    def validar_horario(self, e):
        value = e.control.value
        # Aceita apenas formato HH:MM
        if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", value):
            e.control.error_text = "Formato deve ser HH:MM"
            e.control.update()
        else:
            e.control.error_text = None
            self.selected_time = value
            e.control.update()

    def filtrar_codigos(self, e):
        filtro = e.control.value.lower()
        if hasattr(self, 'todos_codigos'):
            codigos = self.todos_codigos
        else:
            codigos = [opt.data for opt in self.codigo_dropdown.options if hasattr(opt, 'data') and opt.data]
        if not codigos:
            return
        opcoes_filtradas = []
        for codigo in codigos:
            if filtro in codigo['codigo'].lower() or (filtro and codigo['codigo'].lower().startswith(filtro)):
                opcoes_filtradas.append(ft.dropdown.Option(key=str(codigo['id']), text=codigo['codigo'], data=codigo))
        self.codigo_dropdown.options = opcoes_filtradas if filtro else [ft.dropdown.Option(key=str(c['id']), text=c['codigo'], data=c) for c in codigos]
        self.codigo_dropdown.value = None
        self.codigo_dropdown.update()