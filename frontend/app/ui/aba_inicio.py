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
            options=[],
            on_change=self.on_ponto_selected,
            expand=True,
            border_radius=8
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
        self.inputs_container.content.controls.append(self.time_picker_button)

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
                f"{API_URL}/trabalhos/api/codigos/", 
                headers=headers,
                use_cache=True,
                cache_key="codigos"
            )
            
            self.codigo_dropdown.options = [
                ft.dropdown.Option(
                    key=str(codigo['id']),
                    text=codigo['codigo']
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
                headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"}
                url = f"{API_URL}/trabalhos/api/codigos/{codigo_id}/"
                logging.info(f"Carregando detalhes do código {codigo_id} da URL: {url}")
                
                response = await async_api_request(url, headers=headers)
                logging.info(f"Resposta da API para código: {response}")
                
                if not response:
                    logging.error(f"Código {codigo_id} não encontrado")
                    return
                
                # Carregar pontos do código
                await self.load_pontos(codigo_id)
            except Exception as ex:
                logging.error(f"Erro ao carregar detalhes do código: {ex}")
                self.ponto_dropdown.options = []
                self.ponto_dropdown.value = None
                self.page.update()
        else:
            self.ponto_dropdown.options = []
            self.ponto_dropdown.value = None
            self.page.update()

    async def load_pontos(self, codigo_id):
        try:
            headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"}
            url = f"{API_URL}/trabalhos/api/pontos/?codigo={codigo_id}"
            logging.info(f"Carregando pontos para código {codigo_id} da URL: {url}")
            
            response = await async_api_request(url, headers=headers)
            logging.info(f"Resposta da API para pontos: {response}")
            
            if not response:
                logging.warning(f"Nenhum ponto encontrado para o código {codigo_id}")
                self.ponto_dropdown.options = []
                self.ponto_dropdown.value = None
                self.page.update()
                return
            
            self.ponto_dropdown.options = [
                ft.dropdown.Option(
                    key=str(ponto['id']),
                    text=f"{ponto['nome']} - {ponto['localizacao']}"
                ) for ponto in response
            ]
            
            self.ponto_dropdown.value = None
            
            if self.page:
                self.page.update()
                logging.info(f"Pontos carregados com sucesso: {len(response)} pontos encontrados")
        except Exception as ex:
            logging.error(f"Erro ao carregar pontos: {ex}")
            self.ponto_dropdown.options = [ft.dropdown.Option("Erro na API")]
            if self.page:
                self.page.update()

    async def on_ponto_selected(self, e):
        ponto_id = e.control.value
        if ponto_id:
            try:
                headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"}
                response = await async_api_request(
                    f"{API_URL}/trabalhos/api/pontos/{ponto_id}/",
                    headers=headers
                )
                
                self.codigo_ponto_input.value = response['codigo_info']['codigo']
                self.nome_ponto_input.value = response['nome']
                
                if self.page:
                    self.page.update()
            except Exception as ex:
                logging.error(f"Erro ao carregar detalhes do ponto: {ex}")

    async def load_padroes(self):
        try:
            if not self.page:
                self.page = self.contador.page
            
            headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"} if self.contador.tokens and 'access' in self.contador.tokens else {}

            url = f"{API_URL}/padroes/tipos-de-padrao/"
            response = await async_api_request(
                url, 
                method="GET", 
                headers=headers,
                use_cache=True,
                cache_key="padroes"
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
                f"{API_URL}/padroes/merged-binds/?pattern_type={padrao_selecionado_str}",
                method="GET",
                headers=headers,
                use_cache=True,
                cache_key=cache_key
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

        # Criar objeto de sessão com os dados dos dropdowns
            session_data = {
                "pesquisador": self.contador.username,
            "codigo": self.codigo_ponto_input.value,
            "ponto": self.nome_ponto_input.value,
                "horario_inicio": self.selected_time,
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