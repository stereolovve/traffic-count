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
        """Configura a interface simplificada e limpa"""
        try:
            self.controls.clear()
            
            # Cabeçalho com controles integrados
            header_content = ft.Row([
                ft.Text(
                    "📊 Relatório da Sessão",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE
                ),
                ft.Row([
                    ft.ElevatedButton(
                        text="🔄",
                        on_click=self.atualizar_relatorio,
                        bgcolor=ft.Colors.BLUE_600,
                        color=ft.Colors.WHITE,
                        width=40,
                        height=35,
                        tooltip="Atualizar relatório"
                    ),
                    ft.ElevatedButton(
                        text="📑",
                        on_click=self.exportar_dados,
                        bgcolor=ft.Colors.GREEN_600,
                        color=ft.Colors.WHITE,
                        width=40,
                        height=35,
                        tooltip="Exportar dados"
                    )
                ], spacing=5)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

            header = ft.Container(
                content=header_content,
                bgcolor=ft.Colors.GREY_800,
                padding=15,
                border_radius=8,
                margin=ft.margin.only(bottom=10)
            )

            # Status integrado
            self.status_text = ft.Container(
                content=ft.Text(
                    "Carregando dados...",
                    size=12,
                    color=ft.Colors.WHITE,
                    text_align=ft.TextAlign.CENTER
                ),
                bgcolor=ft.Colors.GREY_700,
                padding=8,
                border_radius=6,
                margin=ft.margin.only(bottom=10)
            )

            # Container principal simplificado
            self.main_container = ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Carregando relatório...", 
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.GREY_400,
                        size=14
                    )
                ], 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO),
                expand=True,
                bgcolor=ft.Colors.GREY_900,
                border_radius=8,
                padding=15,
                border=ft.border.all(1, ft.Colors.GREY_700)
            )
            
            # Layout principal simplificado
            self.controls.extend([
                header,
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
        self.status_text.content.value = message
        self.status_text.bgcolor = ft.Colors.GREEN_700
        self.status_text.update()

    def _show_error(self, message):
        """Mostra mensagem de erro"""
        self.status_text.content.value = message
        self.status_text.bgcolor = ft.Colors.RED_700
        self.status_text.update()

    def _show_warning(self, message):
        """Mostra mensagem de aviso"""
        self.status_text.content.value = message
        self.status_text.bgcolor = ft.Colors.ORANGE_700
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

            # Create simplified table with better styling
            colunas = []
            for col in df_final.columns:
                colunas.append(ft.DataColumn(
                    label=ft.Text(
                        col.replace("_", " ").title(),
                        size=13, 
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE
                    )
                ))
            
            linhas = []
            for idx, row in df_final.iterrows():
                cells = []
                for col in df_final.columns:
                    value = str(row[col]) if pd.notna(row[col]) else ""
                    cells.append(ft.DataCell(
                        ft.Text(value, size=12, color=ft.Colors.WHITE)
                    ))
                
                # Alternate row colors for better readability
                row_color = ft.Colors.GREY_800 if idx % 2 == 0 else ft.Colors.GREY_900
                linhas.append(ft.DataRow(cells=cells, color=row_color))

            tabela_relatorio = ft.DataTable(
                columns=colunas,
                rows=linhas,
                bgcolor=ft.Colors.GREY_900,
                heading_row_color=ft.Colors.BLUE_700,
                heading_row_height=45,
                data_row_min_height=40,
                horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_700),
                show_checkbox_column=False,
                border_radius=6
            )

            # Single scroll container - no nested scrolls
            return ft.Column([
                ft.Row([tabela_relatorio], scroll=ft.ScrollMode.AUTO)
            ], scroll=ft.ScrollMode.AUTO, spacing=0)

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
        """Atualiza o relatório com novos dados"""
        try:
            self._show_warning("🔄 Atualizando relatório...")
            self.carregar_relatorio()
        except Exception as ex:
            print(f"Erro ao atualizar relatório: {ex}")
            self._show_error("❌ Erro ao atualizar")
    
    def exportar_dados(self, e):
        """Placeholder para exportação de dados"""
        self._show_warning("🚧 Funcionalidade em desenvolvimento")
