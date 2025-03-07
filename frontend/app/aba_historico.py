import flet as ft
from sqlalchemy.exc import SQLAlchemyError
from database.models import Session, Categoria, Sessao, Contagem, Historico, init_db
import logging


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
    try:
        registros = self.session.query(Historico)\
            .filter_by(sessao=self.sessao)\
            .order_by(Historico.timestamp.desc())\
            .limit(self.historico_page_size)\
            .all()
        
        self.historico_lista.controls.clear()
        for registro in registros:
            if registro.acao == "edição manual":
                cor = "purple"
            elif registro.acao == "salvamento":
                cor = "blue"
            elif registro.acao == "reset":
                cor = "orange"
            elif registro.acao == "increment":
                cor = "green"
            elif registro.acao == "decrement":
                cor = "red"
            else:
                cor = "black"

            veiculo = registro.categoria.veiculo if registro.categoria else "N/A"  # Access via relationship
            linha = ft.Container(
                content=ft.Text(
                    f"{registro.timestamp.strftime('%d/%m/%Y %H:%M:%S')} | Categoria: {veiculo} | Movimento: {registro.movimento} | Ação: {registro.acao}",
                    color=cor),
                padding=10,
                border_radius=5
            )
            self.historico_lista.controls.append(linha)

        if not registros:
            self.historico_lista.controls.append(ft.Text("Nenhum registro encontrado."))

        self.page.update()
    except SQLAlchemyError as ex:
        logging.error(f"Erro ao carregar histórico: {ex}")
        self.historico_lista.controls.append(ft.Text("Erro ao carregar histórico."))
        self.page.update()
        
