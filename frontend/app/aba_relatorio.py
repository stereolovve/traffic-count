import flet as ft
import pandas as pd
import os
from utils.config import EXCEL_BASE_DIR

def setup_aba_relatorio(contador):

    def load_data():
        try:
            if not contador.sessao:
                return ft.Container(
                    content=ft.Text(
                        "Nenhuma sessão ativa. Inicie uma sessão para visualizar o relatório.",
                        size=16,
                        color=ft.colors.RED_700,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    ),
                    padding=20,
                    bgcolor=ft.colors.RED_50,
                    border_radius=10
                )

            nome_pesquisador = contador.username  
            codigo = ''.join(c for c in contador.details.get('Código', '') if c.isalnum())
            arquivo_sessao = os.path.join(EXCEL_BASE_DIR, nome_pesquisador, codigo, f"{contador.sessao}.xlsx")

            if not os.path.exists(arquivo_sessao):
                diretorio_base = os.path.join(EXCEL_BASE_DIR, nome_pesquisador, codigo)
                arquivos_existentes = os.listdir(diretorio_base) if os.path.exists(diretorio_base) else []
                return ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"Planilha da sessão '{contador.sessao}' não encontrada.",
                                size=16,
                                color=ft.colors.RED_700,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                f"Caminho: {arquivo_sessao}",
                                size=12,
                            ),
                            ft.Text(
                                f"Arquivos no diretório: {arquivos_existentes}",
                                size=12,
                            )
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=5
                    ),
                    padding=20,
                    bgcolor=ft.colors.RED_50,
                    border_radius=10
                )

            xl = pd.ExcelFile(arquivo_sessao)
            movimentos = [sheet for sheet in xl.sheet_names if sheet != "Detalhes"]
            if not movimentos:
                return ft.Container(
                    content=ft.Text(
                        "Nenhum movimento registrado na planilha.",
                        size=16,
                        color=ft.colors.ORANGE_700,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    ),
                    padding=20,
                    bgcolor=ft.colors.ORANGE_50,
                    border_radius=10
                )

            df_consolidado = None
            for movimento in movimentos:
                df = pd.read_excel(arquivo_sessao, sheet_name=movimento)
                df["Movimento"] = movimento
                if df_consolidado is None:
                    df_consolidado = df
                else:
                    df_consolidado = pd.concat([df_consolidado, df], ignore_index=True)

            if df_consolidado.empty:
                return ft.Container(
                    content=ft.Text(
                        "Nenhum dado registrado na planilha.",
                        size=16,
                        color=ft.colors.ORANGE_700,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    ),
                    padding=20,
                    bgcolor=ft.colors.ORANGE_50,
                    border_radius=10
                )

            colunas_esperadas = ["das", "às", "observacao"]
            for col in colunas_esperadas:
                if col not in df_consolidado.columns:
                    df_consolidado[col] = "" if col == "observacao" else "00:00"

            veiculos = [col for col in df_consolidado.columns if col not in ["das", "às", "observacao", "Movimento"]]
            df_consolidado["Período"] = df_consolidado["das"] + " - " + df_consolidado["às"]
            colunas_exibição = ["Período", "Movimento", "observacao"] + veiculos
            df_final = df_consolidado[colunas_exibição]

            colunas = [ft.DataColumn(ft.Text(col, size=14, weight=ft.FontWeight.BOLD)) for col in df_final.columns]
            linhas = []
            for _, row in df_final.iterrows():
                linha = [ft.DataCell(ft.Text(str(row[col]), size=12)) for col in df_final.columns]
                linhas.append(ft.DataRow(cells=linha))

            tabela_relatorio = ft.DataTable(
                columns=colunas,
                rows=linhas,
            )

            tabela_container = ft.Container(
                content=ft.Row(
                    controls=[tabela_relatorio],
                    scroll=ft.ScrollMode.ALWAYS 
                ),
                padding=10,
                expand=True,
                border_radius=10,
            )

            return tabela_container

        except Exception as e:
            return ft.Container(
                content=ft.Text(
                    f"Erro ao carregar dados da planilha: {e}",
                    size=16,
                    color=ft.colors.RED_700,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                padding=20,
                bgcolor=ft.colors.RED_50,
                border_radius=10
            )

    def atualizar_relatorio(e):
        if not contador.page:
            print("[ERROR] Página não disponível para atualizar o relatório.")
            return

        novo_relatorio = load_data()
        conteudo_aba.controls[1].controls[0] = novo_relatorio
        contador.page.update()

    atualizar_button = ft.ElevatedButton(
        text="Atualizar Relatório",
        icon=ft.icons.REFRESH,
        on_click=atualizar_relatorio,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=10
        )
    )

    titulo = ft.Text(
        "Relatório da Sessão",
        size=20,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER
    )

    barra_superior = ft.Container(
        content=ft.Row(
            controls=[titulo, atualizar_button],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        padding=10,
        border_radius=ft.BorderRadius(top_left=10, top_right=10, bottom_left=0, bottom_right=0)
    )

    tabela_relatorio = load_data()
    conteudo_aba = ft.Column(
        controls=[
            barra_superior,
            ft.Column(
                controls=[tabela_relatorio],
                scroll=ft.ScrollMode.AUTO,
                expand=True
            )
        ],
        spacing=0,
        expand=True
    )

    for tab in contador.tabs.tabs:
        if tab.text == "Relatório":
            tab.content = conteudo_aba
            contador.page.update()
            return

    contador.tabs.tabs.append(ft.Tab(
        text="Relatório",
        content=conteudo_aba,
        icon=ft.icons.TABLE_CHART
    ))
    contador.page.update()