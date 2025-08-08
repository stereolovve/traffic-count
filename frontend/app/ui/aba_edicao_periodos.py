import flet as ft
import logging
import pandas as pd
import os
import traceback
from datetime import datetime, timedelta
from utils.config import get_excel_dir
import re
import asyncio

class AbaEdicaoPeriodos(ft.Column):
    def __init__(self, contador):
        super().__init__()
        self.contador = contador
        self.scroll = ft.ScrollMode.AUTO
        self.spacing = 20
        self.periodos_data = {}
        self.data_tables = {}
        self.has_changes = False
        self.setup_ui()

    def setup_ui(self):

        self.load_btn = ft.ElevatedButton(
            "Carregar Dados",
            icon=ft.Icons.REFRESH,
            on_click=self.carregar_periodos,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)
        )
        self.save_btn = ft.ElevatedButton(
            "Salvar",
            icon=ft.Icons.SAVE,
            on_click=self.salvar_todas_alteracoes,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE)
        )
        
        header = ft.Row(
            [ft.Text("Edição de Períodos", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([self.load_btn, self.save_btn], spacing=10)],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        self.status = ft.Text("Carregue os dados para começar", size=14, color=ft.Colors.GREY_600)
        
        self.content_area = ft.Column(
            [ft.Text("Nenhum dado carregado", size=16, color=ft.Colors.GREY_500)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            spacing=10
        )
        
        self.controls = [header, ft.Divider(), self.status,
                        ft.Container(self.content_area, expand=True, padding=20)]
        
        self.controls = [
            header,
            ft.Divider(),
            self.status,
            ft.Container(
                self.content_area,
                expand=True,
                padding=20
            )
        ]

    def carregar_periodos(self, e=None):
        """Carrega dados com feedback visual simples"""
        self.load_btn.disabled = True
        self.load_btn.text = "Carregando..."
        self.status.value = "Carregando dados..."
        self.status.color = ft.Colors.BLUE_600
        self.update()

        try:
            if not self.contador.sessao:
                self._show_status("Nenhuma sessão ativa", ft.Colors.RED_600)
                return
            
            excel_path = self._get_excel_path()
            if not os.path.exists(excel_path):
                self._show_status(f"Arquivo não encontrado: {os.path.basename(excel_path)}", ft.Colors.RED_600)
                return
            
            self.periodos_data = {}
            movimentos = self.contador.details.get("Movimentos", [])
            
            if not movimentos:
                self._show_status("Nenhum movimento definido", ft.Colors.RED_600)
                return
            
            for movimento in movimentos:
                try:
                    df = pd.read_excel(excel_path, sheet_name=movimento)
                    if not df.empty:
                        self.periodos_data[movimento] = df
                except Exception as ex:
                    logging.warning(f"Erro ao carregar movimento {movimento}: {ex}")
            
            if self.periodos_data:
                self._create_simple_interface()
                self._show_status(f"Carregados {len(self.periodos_data)} movimentos", ft.Colors.GREEN_600)
            else:
                self._show_status("Nenhum dado encontrado", ft.Colors.ORANGE_600)
                
        except Exception as ex:
            logging.error(f"Erro ao carregar períodos: {ex}")
            self._show_status(f"Erro: {str(ex)}", ft.Colors.RED_600)
        finally:
            self.load_btn.disabled = False
            self.load_btn.text = "Carregar Dados"
            self.update()

    def _create_simple_interface(self):
        if not self.periodos_data:
            return
        
        tabs = []
        for movimento, df in self.periodos_data.items():
            tab_content = self._create_simple_table(movimento, df)
            tabs.append(ft.Tab(
                text=f"{movimento} ({len(df)})",
                content=tab_content
            ))
        
        # Limpar completamente o conteúdo anterior e adicionar as abas
        self.content_area.controls.clear()  # Remove o texto "Nenhum dado carregado"
        self.content_area.controls = [
            ft.Tabs(
                tabs=tabs,
                selected_index=0,
                label_color=ft.Colors.BLUE_600,
                unselected_label_color=ft.Colors.GREY_500,
                indicator_color=ft.Colors.BLUE_600
            )
        ]
        self.content_area.update()

    def _create_simple_table(self, movimento, df):
        columns = []
        for col in df.columns:
            columns.append(ft.DataColumn(
                label=ft.Text(col.title(), weight=ft.FontWeight.BOLD)
            ))
        
        rows = []
        for idx, row in df.iterrows():
            cells = []
            for col in df.columns:
                value = str(row[col]) if pd.notna(row[col]) else ""
                
                if col.lower() in ['das', 'às']:
                    field = ft.TextField(
                        value=value,
                        dense=True,
                        width=120,
                        text_size=12,
                        hint_text="HH:MM" if not value else None,
                        on_change=lambda e: self._mark_changes(),
                        border_radius=4
                    )
                elif col.lower() == 'observacao':
                    field = ft.TextField(
                        value=value,
                        dense=True,
                        width=200,
                        text_size=12,
                        multiline=True,
                        max_lines=2,
                        on_change=lambda e: self._mark_changes(),
                        border_radius=4
                    )
                else:
                    field = ft.TextField(
                        value=value,
                        dense=True,
                        width=80,
                        text_size=12,
                        keyboard_type=ft.KeyboardType.NUMBER,
                        on_change=lambda e: self._mark_changes(),
                        border_radius=4
                    )
                
                cells.append(ft.DataCell(field))
            
            rows.append(ft.DataRow(cells=cells))
        
        # Tabela otimizada - sem configurações desnecessárias
        table = ft.DataTable(
            columns=columns,
            rows=rows,
            show_checkbox_column=False,
            column_spacing=8,  # Reduzido para melhor performance
            horizontal_margin=8,
            data_row_min_height=45,  # Reduzido para melhor performance
        )
        
        # Armazenar referência
        self.data_tables[movimento] = table
        
        # Estrutura simplificada - SEM cores fixas, SEM containers desnecessários
        return ft.Column(
            [
                # Título sem estilização fixa
                ft.Text(
                    f"Movimento: {movimento.upper()}", 
                    size=16, 
                    weight=ft.FontWeight.BOLD
                ),
                # Tabela diretamente no ListView para scroll otimizado
                ft.ListView(
                    [table],
                    height=400,  # Altura fixa para evitar conflitos de scroll
                    padding=ft.padding.all(10)
                )
            ],
            spacing=10,
            tight=True  # Otimização para performance
        )

    def _mark_changes(self):
        """Marca alterações pendentes"""
        if not self.has_changes:
            self.has_changes = True
            self.save_btn.disabled = False
            self._show_status("Alterações pendentes", ft.Colors.ORANGE_600)
            self.update()

    async def salvar_todas_alteracoes(self, e=None):
        """Salva alterações com feedback simples"""
        if not self.has_changes:
            self._show_status("Nenhuma alteração pendente", ft.Colors.GREY_600)
            return
        
        self.save_btn.disabled = True
        self.save_btn.text = "Salvando..."
        self._show_status("Salvando alterações...", ft.Colors.BLUE_600)
        self.update()
        
        try:
            # Coletar dados das tabelas
            dados_atualizados = {}
            
            for movimento, table in self.data_tables.items():
                if movimento in self.periodos_data:
                    df_original = self.periodos_data[movimento].copy()
                    
                    # Atualizar dados da tabela
                    for row_idx, row in enumerate(table.rows):
                        for col_idx, cell in enumerate(row.cells):
                            column_name = df_original.columns[col_idx]
                            # Access the TextField value directly from the cell content
                            new_value = cell.content.value if hasattr(cell.content, 'value') else ""
                            
                            # Conversão de tipos com tratamento adequado de dtype
                            if column_name in ['das', 'às', 'observacao']:
                                # Para colunas de texto, usar astype para garantir compatibilidade
                                df_original[column_name] = df_original[column_name].astype('object')
                                df_original.at[row_idx, column_name] = str(new_value) if new_value else ""
                            else:
                                # Para colunas numéricas, garantir conversão adequada
                                try:
                                    numeric_value = int(new_value) if new_value else 0
                                    # Verificar se a coluna é numérica, se não, converter
                                    if not pd.api.types.is_numeric_dtype(df_original[column_name]):
                                        df_original[column_name] = pd.to_numeric(df_original[column_name], errors='coerce').fillna(0).astype(int)
                                    df_original.at[row_idx, column_name] = numeric_value
                                except ValueError:
                                    # Se falhar, garantir que a coluna seja numérica e definir como 0
                                    df_original[column_name] = pd.to_numeric(df_original[column_name], errors='coerce').fillna(0).astype(int)
                                    df_original.at[row_idx, column_name] = 0
                    
                    dados_atualizados[movimento] = df_original
            
            # Salvar Excel
            await self._salvar_excel(dados_atualizados)
            
            # Sincronizar Django
            await self._sincronizar_django(dados_atualizados)
            
            # Atualizar cache
            self.periodos_data.update(dados_atualizados)
            self.has_changes = False
            
            self._show_status("Alterações salvas com sucesso!", ft.Colors.GREEN_600)
            
        except Exception as ex:
            logging.error(f"Erro ao salvar alterações: {ex}")
            self._show_status(f"Erro ao salvar: {str(ex)}", ft.Colors.RED_600)
        finally:
            self.save_btn.disabled = True
            self.save_btn.text = "Salvar"
            self.update()

    async def _salvar_excel(self, dados_atualizados):
        """Salva dados no Excel"""
        excel_path = self._get_excel_path()
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            for movimento, df in dados_atualizados.items():
                df.to_excel(writer, sheet_name=movimento, index=False)

    async def _sincronizar_django(self, dados_atualizados):
        """Sincroniza com Django"""
        try:
            if not hasattr(self.contador, 'api_manager'):
                return
            
            for movimento, df in dados_atualizados.items():
                contagens = []
                
                for _, row in df.iterrows():
                    periodo = row.get('das', '')
                    if periodo:
                        for col in df.columns:
                            if col not in ['das', 'às', 'observacao']:
                                count = int(row[col]) if pd.notna(row[col]) else 0
                                contagens.append({
                                    'veiculo': col,
                                    'movimento': movimento,
                                    'count': count,
                                    'periodo': periodo
                                })
                
                if contagens:
                    data = {
                        "sessao": self.contador.sessao,
                        "usuario": self.contador.username,
                        "contagens": contagens
                    }
                    
                    try:
                        response = await self.contador.api_manager.client.post(
                            "/contagens/atualizar-contagens/",
                            json=data
                        )
                        if response.status_code not in [200, 201]:
                            logging.error(f"Erro ao sincronizar: {response.status_code}")
                    except Exception as req_ex:
                        logging.error(f"Erro na requisição: {req_ex}")
        
        except Exception as ex:
            logging.error(f"Erro geral ao sincronizar: {ex}")

    def _show_status(self, message, color=ft.Colors.GREY_600):
        """Mostra status simples"""
        self.status.value = message
        self.status.color = color
        self.status.update()

    def _get_excel_path(self):
        """Retorna caminho do Excel"""
        nome_pesquisador = re.sub(r'[<>:"/\\|?*]', '', self.contador.username)
        codigo = re.sub(r'[<>:"/\\|?*]', '', self.contador.details['Código'])
        excel_dir = get_excel_dir()
        diretorio = os.path.join(excel_dir, nome_pesquisador, codigo)
        return os.path.join(diretorio, f'{self.contador.sessao}.xlsx')

    def force_ui_update(self):
        """Atualiza interface"""
        self.setup_ui()
        if self.contador.sessao:
            self.carregar_periodos()
        self.update()