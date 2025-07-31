import flet as ft
import pandas as pd
import os
import re
from utils.config import get_excel_dir

class AbaRelatorio(ft.Column):
    def __init__(self, contador):
        super().__init__()
        self.contador = contador
        self.scroll = ft.ScrollMode.AUTO
        self.spacing = 10
        self.setup_ui()

    def setup_ui(self):
        """Configura a interface minimalista e organizada"""
        try:
            self.controls.clear()
            
            # Cabeçalho estilizado
            header = ft.Container(
                content=ft.Text(
                    "📊 Relatório da Sessão",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE
                ),
                bgcolor=ft.Colors.GREY_900,
                padding=15,
                border_radius=8
            )

            # Barra de controles
            self.atualizar_btn = ft.ElevatedButton(
                text="🔄 Atualizar",
                on_click=self.atualizar_relatorio,
                bgcolor=ft.Colors.GREY_700,
                color=ft.Colors.WHITE
            )
            
            self.exportar_btn = ft.ElevatedButton(
                text="📑 Exportar",
                on_click=self.exportar_dados,
                bgcolor=ft.Colors.GREY_700,
                color=ft.Colors.WHITE
            )

            controles = ft.Row([
                self.atualizar_btn,
                self.exportar_btn
            ], spacing=10)

            # Status
            self.status_text = ft.Text(
                "Carregando dados...",
                size=12,
                color=ft.Colors.WHITE
            )

            # Container principal para dados
            self.main_container = ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Carregando relatório...", 
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.WHITE,
                        size=14
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                height=600,
                bgcolor=ft.Colors.GREY_900,
                border_radius=8,
                padding=20
            )
            
            # Layout principal
            self.controls.extend([
                header,
                controles,
                self.status_text,
                self.main_container
            ])
            
            # Carregar dados automaticamente
            self.carregar_relatorio()
            
        except Exception as ex:
            print(f"Erro ao configurar UI do relatório: {ex}")

    def carregar_relatorio(self):
        """Carrega e exibe os dados do relatório"""
        try:
            dados = self.load_data()
            if dados:
                self.main_container.content = dados
                self.main_container.update()
                self._show_success("✅ Relatório carregado com sucesso")
            else:
                self._show_empty_state()
                
        except Exception as ex:
            print(f"Erro ao carregar relatório: {ex}")
            self._show_error(f"❌ Erro: {str(ex)}")

    def _show_empty_state(self):
        """Mostra estado vazio"""
        empty_content = ft.Column([
            ft.Text(
                "📭 Nenhum dado encontrado",
                size=16,
                color=ft.Colors.WHITE,
                text_align=ft.TextAlign.CENTER
            ),
            ft.Text(
                "Inicie uma sessão para visualizar o relatório",
                size=12,
                color=ft.Colors.WHITE70,
                text_align=ft.TextAlign.CENTER
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        self.main_container.content = empty_content
        self.main_container.update()

    def _show_success(self, message):
        """Mostra mensagem de sucesso"""
        self.status_text.value = message
        self.status_text.color = ft.Colors.WHITE
        self.status_text.update()

    def _show_error(self, message):
        """Mostra mensagem de erro"""
        self.status_text.value = message
        self.status_text.color = ft.Colors.WHITE
        self.status_text.update()

    def _show_warning(self, message):
        """Mostra mensagem de aviso"""
        self.status_text.value = message
        self.status_text.color = ft.Colors.WHITE
        self.status_text.update()

    def load_data(self):
        try:
            if not self.contador.sessao:
                return ft.Container(
                    content=ft.Text(
                        "Nenhuma sessão ativa. Inicie uma sessão para visualizar o relatório.",
                        size=16,
                        color=ft.Colors.RED_700,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    ),
                    padding=20,
                    bgcolor=ft.Colors.RED_50,
                    border_radius=10
                )

            nome_pesquisador = self.contador.username  
            codigo = ''.join(c for c in self.contador.details.get('Código', '') if c.isalnum())
            excel_dir = get_excel_dir()
            arquivo_sessao = os.path.join(excel_dir, nome_pesquisador, codigo, f"{self.contador.sessao}.xlsx")

            if not os.path.exists(arquivo_sessao):
                diretorio_base = os.path.join(excel_dir, nome_pesquisador, codigo)
                arquivos_existentes = os.listdir(diretorio_base) if os.path.exists(diretorio_base) else []
                return ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"Planilha da sessão '{self.contador.sessao}' não encontrada.",
                                size=16,
                                color=ft.Colors.RED_700,
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
                    bgcolor=ft.Colors.RED_50,
                    border_radius=10
                )

            xl = pd.ExcelFile(arquivo_sessao)
            movimentos = [sheet for sheet in xl.sheet_names if sheet != "Detalhes"]
            if not movimentos:
                return ft.Container(
                    content=ft.Text(
                        "Nenhum movimento registrado na planilha.",
                        size=16,
                        color=ft.Colors.ORANGE_700,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    ),
                    padding=20,
                    bgcolor=ft.Colors.ORANGE_50,
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
                        color=ft.Colors.ORANGE_700,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER
                    ),
                    padding=20,
                    bgcolor=ft.Colors.ORANGE_50,
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
                    color=ft.Colors.RED_700,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                padding=20,
                bgcolor=ft.Colors.RED_50,
                border_radius=10
            )

    def atualizar_relatorio(self, e):
        if not self.contador.page:
            print("[ERROR] Página não disponível para atualizar o relatório.")
            return

        novo_relatorio = self.load_data()
        self.conteudo_aba.controls[1].controls[0] = novo_relatorio
        self.contador.page.update()

        for tab in self.contador.tabs.tabs:
            if tab.text == "Relatório":
                tab.content = self.conteudo_aba
                break
        self.contador.page.update()
