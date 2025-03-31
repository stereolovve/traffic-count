import flet as ft
from datetime import datetime
import json
import logging
import re
from database.models import Sessao
from utils.config import API_URL
from utils.api import async_api_request


class AbaInicio(ft.Column):
    def __init__(self, contador):
        super().__init__()
        self.contador = contador
        self.page = contador.page
        self.tokens = contador.tokens
        
        hoje_str = datetime.now().strftime("%d-%m-%Y")
        user_label = ft.Text(
            f"Usuário logado: {self.contador.username}", 
            size=16, 
            weight=ft.FontWeight.BOLD, 
            color="BLUE"
        )
        self.controls.append(user_label)
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
            on_click=self.iniciar_criacao_sessao,
            width=float('inf'),
            height=50,
            icon=ft.icons.SEND
        )

        self.api_padroes_container = ft.Column()

        self.controls.extend([
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
            if not self.page:
                self.page = self.contador.page
            
            headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"} if self.contador.tokens and 'access' in self.contador.tokens else {}

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

            if self.page:
                self.page.update()
        except Exception as ex:
            logging.error(f"Erro ao carregar tipos de padrões: {ex}")
            self.padrao_dropdown.options = [ft.dropdown.Option("Erro na API")]
            if self.page:
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
            
            headers = {"Authorization": f"Bearer {self.contador.tokens['access']}"} if self.contador.tokens and 'access' in self.contador.tokens else {}
            response = await async_api_request(api_url, method="GET", headers=headers)

            self.contador.binds = {item["veiculo"]: item["bind"] for item in response}
            
            self.contador.setup_aba_contagem()
            self.page.update()

        except Exception as ex:
            logging.error(f"[ERROR] Erro ao carregar padrões do usuário: {ex}")
            self.padrao_dropdown.options = [ft.dropdown.Option("Erro na API")]
            if self.page:
                self.page.update()

    async def iniciar_criacao_sessao(self, e):
        """
        Coleta os dados do formulário e envia para o contador criar a sessão.
        """
        try:
            # 1. Validar campos
            if not self.validar_campos():
                return

            # 2. Coletar dados do formulário
            session_data = {
                "pesquisador": self.contador.username,
                "codigo": self.codigo_ponto_input.value.strip(),
                "ponto": self.nome_ponto_input.value.strip(),
                "horario_inicio": self.selected_time,
                "data_ponto": self.data_ponto_input.value.strip(),
                "movimentos": [
                    mov.controls[0].value.strip().upper() 
                    for mov in self.movimentos_container.controls 
                    if mov.controls[0].value and mov.controls[0].value.strip()
                ],
                "padrao": self.padrao_dropdown.value
            }

            # 3. Chamar o método de criação no contador
            await self.contador.criar_sessao(session_data)

        except Exception as ex:
            logging.error(f"Erro ao preparar dados da sessão: {ex}")
            self.page.overlay.append(
                ft.SnackBar(
                    content=ft.Text(str(ex)),
                    bgcolor="red"
                )
            )
            self.page.update()