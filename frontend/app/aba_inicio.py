import flet as ft
from database.models import Sessao
from sqlalchemy.exc import SQLAlchemyError


def setup_aba_inicio(self):
    tab = self.tabs.tabs[0].content
    tab.controls.clear()
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
        ft.Text(""),
        self.codigo_ponto_input,
        self.nome_ponto_input,
        self.horas_contagem_input,
        self.data_ponto_input,
        ft.Text("Adicione os movimentos:"),
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


