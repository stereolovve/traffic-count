import flet as ft
import datetime
from database.models import Sessao
from sqlalchemy.exc import SQLAlchemyError


def setup_aba_inicio(self):
    tab = self.tabs.tabs[0].content
    tab.controls.clear()

    self.codigo_ponto_input = ft.TextField(label="Código (ex: ER2403. Tudo junto)")
    self.nome_ponto_input = ft.TextField(label="Ponto (ex: P10N)")

    self.inicio_input = ft.TextField(label="Horário de início (ex: 06:00)", keyboard_type=ft.KeyboardType.DATETIME)

    self.datepicker = ft.DatePicker(
        on_change=lambda e: self.change_date(e),
    )
    self.data_ponto_button = ft.ElevatedButton(
        "Selecionar Data",
        icon=ft.icons.CALENDAR_MONTH,
        on_click=self.open_date_picker,
    )
    self.data_ponto_label = ft.Text("Nenhuma data selecionada")

    self.padrao_dropdown = ft.Dropdown(
        label="Selecione o padrão",
        options=[
            ft.dropdown.Option("Padrão Perplan"),
            ft.dropdown.Option("Padrão Perci"),
            ft.dropdown.Option("Padrão Simplificado"),
        ],
        on_change=self.carregar_padroes_selecionados,
    )

    self.movimentos_container = ft.Column()
    adicionar_movimento_button = ft.ElevatedButton(
        text="Adicionar Movimento",
        on_click=self.adicionar_campo_movimento
    )

    criar_sessao_button = ft.ElevatedButton(text="Criar Sessão", on_click=self.criar_sessao)

    tab.controls.extend([
        ft.Text(""),
        self.codigo_ponto_input,
        self.nome_ponto_input,
        self.inicio_input,
        self.data_ponto_button,
        self.data_ponto_label,
        self.padrao_dropdown,
        self.movimentos_container,
        adicionar_movimento_button,
        criar_sessao_button
    ])

    self.sessao_status = ft.Text("", weight=ft.FontWeight.BOLD)
    tab.controls.append(self.sessao_status)

    self.page.overlay.append(self.datepicker)
    self.update_sessao_status()
    self.page.update()


def open_date_picker(self, e):
    self.datepicker.pick_date()

def change_date(self, e):
    self.data_ponto_label.value = f"Data selecionada: {self.datepicker.value}"
    self.page.update()


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


def criar_sessao(self):
    try:
        data_ponto = self.data_ponto_label.value.replace("Data selecionada: ", "")
        print(f"Data selecionada: {data_ponto}")
        print("Sessão criada com sucesso!")
        self.sessao_status.value = "Sessão criada com sucesso!"
    except SQLAlchemyError as e:
        print(f"Erro ao criar a sessão: {e}")
        self.sessao_status.value = f"Erro ao criar a sessão: {e}"
    self.page.update()
