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
        self.spacing = 10
        self.periodos_data = {}
        self.data_tables = {}
        self.has_changes = False
        self.setup_ui()

    def setup_ui(self):
        """Configura a interface reorganizada e elegante"""
        try:
            self.controls.clear()

            
            # Barra de controles reorganizada
            self.carregar_btn = ft.ElevatedButton(
                text="🔄 Carregar Dados",
                on_click=self.carregar_periodos,
                bgcolor=ft.Colors.BLUE_600,
                color=ft.Colors.WHITE,
                height=40,
                width=150
            )
            
            self.salvar_btn = ft.ElevatedButton(
                text="💾 Salvar Alterações",
                on_click=self.salvar_todas_alteracoes,
                bgcolor=ft.Colors.GREEN_600,
                color=ft.Colors.WHITE,
                height=40,
                width=150,
                disabled=True
            )
            
            controles = ft.Container(
                content=ft.Row([
                    self.carregar_btn,
                    ft.VerticalDivider(width=20, color=ft.Colors.TRANSPARENT),
                    self.salvar_btn
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor=ft.Colors.GREY_800,
                padding=15,
                border_radius=8,
                margin=ft.margin.only(bottom=10)
            )
            
            # Status centralizado
            self.status_text = ft.Container(
                content=ft.Text(
                    "Carregue os dados para começar",
                    size=14,
                    color=ft.Colors.WHITE,
                    text_align=ft.TextAlign.CENTER
                ),
                bgcolor=ft.Colors.GREY_700,
                padding=10,
                border_radius=8,
                margin=ft.margin.only(bottom=10)
            )

            # Container principal redesenhado com scroll vertical
            self.main_container = ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.TABLE_CHART, size=50, color=ft.Colors.GREY_500),
                            ft.Text(
                                "Nenhum dado carregado", 
                                text_align=ft.TextAlign.CENTER,
                                color=ft.Colors.GREY_400,
                                size=16
                            ),
                            ft.Text(
                                "Clique em 'Carregar Dados' para começar", 
                                text_align=ft.TextAlign.CENTER,
                                color=ft.Colors.GREY_500,
                                size=12
                            )
                        ], 
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10)
                    )
                ], 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO),
                height=650,
                bgcolor=ft.Colors.GREY_900,
                border_radius=10,
                padding=30,
                border=ft.border.all(1, ft.Colors.GREY_700)
            )
            
            # Layout final reorganizado
            self.controls.extend([
                controles,
                self.status_text,
                self.main_container
            ])
            
        except Exception as ex:
            logging.error(f"Erro ao configurar UI de edição de períodos: {ex}")

    def carregar_periodos(self, e=None):
        """Carrega dados dos períodos com feedback visual melhorado"""
        try:
            # Feedback visual de carregamento
            if hasattr(self, 'carregar_btn'):
                self.carregar_btn.disabled = True
                self.carregar_btn.text = "🔄 Carregando..."
                self.carregar_btn.bgcolor = ft.Colors.GREY_600
                self.carregar_btn.update()
            
            # Verificação de sessão
            if not self.contador.sessao:
                self._show_error("❌ Nenhuma sessão ativa")
                return
            
            self._update_status_with_style("🔄 Carregando dados do Excel...", ft.Colors.BLUE_700, "🔄")
            
            excel_path = self._get_excel_path()
            
            if not os.path.exists(excel_path):
                self._show_error(f"❌ Arquivo não encontrado: {os.path.basename(excel_path)}")
                return
            
            self.periodos_data = {}
            movimentos = self.contador.details.get("Movimentos", [])
            
            if not movimentos:
                self._show_error("❌ Nenhum movimento definido na sessão")
                return
            
            dados_carregados = 0
            total_periodos = 0
            
            for movimento in movimentos:
                try:
                    df = pd.read_excel(excel_path, sheet_name=movimento)
                    if not df.empty:
                        self.periodos_data[movimento] = df
                        dados_carregados += 1
                        total_periodos += len(df)
                        logging.info(f"Movimento {movimento}: {len(df)} períodos carregados")
                except Exception as ex:
                    logging.warning(f"Erro ao carregar movimento {movimento}: {ex}")
            
            if dados_carregados > 0:
                self._create_movement_tabs()
                self._show_success(f"✅ Dados carregados com sucesso!")
                logging.info(f"[SUCCESS] {dados_carregados} movimento(s) com {total_periodos} períodos carregados")
            else:
                self._show_warning("⚠️ Nenhum período encontrado")
                self._show_empty_state()
            
        except Exception as ex:
            logging.error(f"Erro ao carregar períodos: {ex}")
            self._show_error(f"❌ Erro: {str(ex)}")
        finally:
            # Restaurar botão
            if hasattr(self, 'carregar_btn'):
                self.carregar_btn.disabled = False
                self.carregar_btn.text = "🔄 Carregar Dados"
                self.carregar_btn.bgcolor = ft.Colors.BLUE_600
                self.carregar_btn.update()

    def _create_movement_tabs(self):
        """Cria abas elegantes para cada movimento"""
        try:
            if not self.periodos_data:
                return
            
            # Criar abas com design melhorado
            tabs = []
            for movimento, df in self.periodos_data.items():
                tab_content = self._create_movement_table(movimento, df)
                
                # Aba com ícone e contador
                tab = ft.Tab(
                    text=f"📊 {movimento.upper()} ({len(df)} períodos)",
                    content=tab_content
                )
                tabs.append(tab)
            
            # Container de abas com estilo aprimorado
            tabs_container = ft.Container(
                content=ft.Tabs(
                    tabs=tabs,
                    selected_index=0,
                    label_color=ft.Colors.WHITE,
                    unselected_label_color=ft.Colors.GREY_400,
                    indicator_color=ft.Colors.BLUE_400,
                    tab_alignment=ft.TabAlignment.START
                ),
                bgcolor=ft.Colors.GREY_900,
                border_radius=10,
                border=ft.border.all(1, ft.Colors.GREY_700)
            )
            
            self.main_container.content = tabs_container
            self.main_container.update()
            
        except Exception as ex:
            logging.error(f"Erro ao criar abas de movimentos: {ex}")

    def _create_movement_table(self, movimento, df):
        """Cria tabela elegante e bem organizada para um movimento específico"""
        try:
            # Cabeçalhos da tabela com estilo melhorado
            columns = []
            for col in df.columns:
                # Definir largura específica por tipo de coluna
                if col in ['das', 'às']:
                    col_width = 120
                elif col == 'observacao':
                    col_width = 120
                else:
                    col_width = 120
                
                columns.append(
                    ft.DataColumn(
                        label=ft.Container(
                            content=ft.Text(
                                col.replace('_', ' ').title(),
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                                size=13,
                                text_align=ft.TextAlign.CENTER
                            ),
                            width=col_width,
                            alignment=ft.alignment.center
                        )
                    )
                )
            
            # Linhas da tabela com formatação consistente
            rows = []
            for index, row in df.iterrows():
                cells = []
                for col_idx, col in enumerate(df.columns):
                    value = str(row[col]) if pd.notna(row[col]) else ""
                    
                    # Definir largura e alinhamento por tipo de coluna
                    if col in ['das', 'às']:
                        width = 120
                        alignment = ft.TextAlign.CENTER
                        prefix = "🕐 " if col == 'das' else "🕑 "
                    elif col == 'observacao':
                        width = 120
                        alignment = ft.TextAlign.LEFT
                        prefix = ""
                    else:
                        width = 120
                        alignment = ft.TextAlign.CENTER
                        prefix = " "
                    
                    cell_content = ft.Container(
                        content=ft.TextField(
                            value=value,
                            text_size=12,
                            dense=True,
                            width=width - 10,
                            height=45,
                            bgcolor=ft.Colors.GREY_800,
                            color=ft.Colors.WHITE,
                            border_color=ft.Colors.BLUE_400,
                            content_padding=ft.padding.all(8),
                            text_align=alignment,
                            hint_text=f"{prefix}{col.title()}" if not value else None,
                            hint_style=ft.TextStyle(color=ft.Colors.GREY_500, size=10),
                            on_change=lambda e, mov=movimento, r=index, c=col: self._on_cell_change_unified(e, mov, r, c)
                        ),
                        width=width,
                        alignment=ft.alignment.center
                    )
                    
                    cells.append(ft.DataCell(content=cell_content))
                
                # Alternar cores das linhas para melhor legibilidade
                row_color = ft.Colors.GREY_800 if index % 2 == 0 else ft.Colors.GREY_900
                rows.append(ft.DataRow(cells=cells, color=row_color))
            
            # Criar tabela com estilo profissional
            data_table = ft.DataTable(
                columns=columns,
                rows=rows,
                bgcolor=ft.Colors.GREY_900,
                heading_row_color=ft.Colors.BLUE_700,
                heading_row_height=50,
                data_row_min_height=55,
                data_row_max_height=55,
                column_spacing=5,
                horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_700),
                show_checkbox_column=False,
                border_radius=8
            )
            
            # Armazenar referência da tabela
            self.data_tables[movimento] = data_table
            
            # Container da tabela com scroll otimizado (horizontal e vertical)
            table_container = ft.Container(
                content=ft.Column([
                    # Título do movimento
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.TRAFFIC, color=ft.Colors.WHITE, size=20),
                            ft.Text(
                                f"Movimento: {movimento.upper()}",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE
                            )
                        ]),
                        bgcolor=ft.Colors.BLUE_600,
                        padding=10,
                        border_radius=ft.border_radius.only(top_left=8, top_right=8)
                    ),
                    # Tabela com scroll horizontal e vertical
                    ft.Container(
                        content=ft.Column([
                            ft.Row([data_table], scroll=ft.ScrollMode.AUTO)
                        ], scroll=ft.ScrollMode.AUTO),
                        height=520,
                        bgcolor=ft.Colors.GREY_900,
                        border_radius=ft.border_radius.only(bottom_left=8, bottom_right=8),
                        padding=15
                    )
                ], spacing=0),
                border=ft.border.all(1, ft.Colors.GREY_700),
                border_radius=8
            )
            
            return table_container
            
        except Exception as ex:
            logging.error(f"Erro ao criar tabela para movimento {movimento}: {ex}")
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED, size=40),
                    ft.Text(f"Erro ao carregar movimento: {movimento}", color=ft.Colors.RED)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                height=200,
                alignment=ft.alignment.center
            )

    def _on_cell_change_unified(self, e, movimento, row_index, column_name):
        """Callback unificado para mudanças em células"""
        self._mark_changes()

    def _mark_changes(self):
        """Marca que há alterações pendentes"""
        if not self.has_changes:
            self.has_changes = True
            self.salvar_btn.disabled = False
            self.salvar_btn.update()
            self.status_text.value = "⚠️ Alterações pendentes"
            self.status_text.color = ft.Colors.WHITE
            self.status_text.update()

    async def salvar_todas_alteracoes(self, e=None):
        """Salva todas as alterações no Excel e sincroniza com Django"""
        try:
            if not self.has_changes:
                self._show_warning("⚠️ Nenhuma alteração pendente")
                return
            
            # Feedback visual de salvamento
            self.salvar_btn.disabled = True
            self.salvar_btn.text = "💾 Salvando..."
            self.salvar_btn.bgcolor = ft.Colors.GREY_600
            self.salvar_btn.update()
            
            self._update_status_with_style("💾 Salvando alterações...", ft.Colors.BLUE_700, "💾")
            
            banner = self.contador.show_loading("💾 Salvando alterações...")
            
            # Coletar dados de todas as tabelas
            dados_atualizados = {}
            alteracoes_processadas = 0
            
            for movimento, data_table in self.data_tables.items():
                if movimento in self.periodos_data:
                    df_original = self.periodos_data[movimento].copy()
                    
                    # Atualizar DataFrame com dados da tabela
                    for row_idx, row in enumerate(data_table.rows):
                        for col_idx, cell in enumerate(row.cells):
                            column_name = df_original.columns[col_idx]
                            new_value = cell.content.value
                            
                            # Converter tipos apropriados com tratamento de erros
                            try:
                                if column_name in ['das', 'às', 'observacao']:
                                    # Strings - usar .astype() para conversão segura
                                    df_original[column_name] = df_original[column_name].astype(str)
                                    df_original.at[row_idx, column_name] = str(new_value) if new_value else ""
                                else:
                                    # Colunas numéricas (veículos) - usar .astype() para conversão segura
                                    try:
                                        numeric_value = int(new_value) if new_value else 0
                                        df_original.at[row_idx, column_name] = numeric_value
                                    except ValueError:
                                        df_original.at[row_idx, column_name] = 0
                            except (ValueError, TypeError) as ex:
                                logging.warning(f"Erro ao converter valor '{new_value}' para coluna {column_name}: {ex}")
                                # Usar valor padrão seguro
                                if column_name in ['das', 'às', 'observacao']:
                                    df_original.at[row_idx, column_name] = ""
                                else:
                                    df_original.at[row_idx, column_name] = 0
                    
                    dados_atualizados[movimento] = df_original
                    alteracoes_processadas += len(df_original)
            
            # Salvar no Excel
            await self._salvar_excel(dados_atualizados)
            
            # Sincronizar com Django
            await self._sincronizar_django(dados_atualizados)
            
            # Atualizar cache local
            self.periodos_data.update(dados_atualizados)
            
            # Resetar estado
            self.has_changes = False
            
            self._show_success(f"✅ Alterações salvas com sucesso!")
            logging.info(f"Períodos salvos e sincronizados: {alteracoes_processadas} registros processados")
            
        except Exception as ex:
            logging.error(f"Erro ao salvar alterações: {ex}")
            self._show_error(f"❌ Erro ao salvar: {str(ex)}")
        finally:
            # Restaurar botão
            self.salvar_btn.disabled = True  # Manter desabilitado até nova alteração
            self.salvar_btn.text = "💾 Salvar Alterações"
            self.salvar_btn.bgcolor = ft.Colors.GREEN_600
            self.salvar_btn.update()
            
            if 'banner' in locals():
                self.contador.hide_loading(banner)

    async def _salvar_excel(self, dados_atualizados):
        """Salva dados atualizados no Excel"""
        excel_path = self._get_excel_path()
        
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            for movimento, df in dados_atualizados.items():
                df.to_excel(writer, sheet_name=movimento, index=False)

    async def _sincronizar_django(self, dados_atualizados):
        """Envia dados atualizados para o Django"""
        try:
            if not hasattr(self.contador, 'api_manager'):
                logging.warning("API Manager não disponível - pulando sincronização Django")
                return
            
            logging.info(f"[DEBUG] Iniciando sincronização com Django para {len(dados_atualizados)} movimentos")
            
            # Preparar dados para envio
            for movimento, df in dados_atualizados.items():
                contagens_para_envio = []
                
                logging.info(f"[DEBUG] Processando movimento {movimento} com {len(df)} linhas")
                
                for idx, row in df.iterrows():
                    periodo = row.get('das', '')
                    if periodo:
                        # Extrair contagens de veículos
                        for col in df.columns:
                            if col not in ['das', 'às', 'observacao']:
                                count = row[col] if pd.notna(row[col]) else 0
                                try:
                                    count = int(count)
                                except (ValueError, TypeError):
                                    count = 0
                                    
                                contagens_para_envio.append({
                                    'veiculo': col,
                                    'movimento': movimento,
                                    'count': count,
                                    'periodo': periodo
                                })
                
                logging.info(f"[DEBUG] Movimento {movimento}: {len(contagens_para_envio)} contagens preparadas")
                
                # Enviar para Django
                if contagens_para_envio:
                    data = {
                        "sessao": self.contador.sessao,
                        "usuario": self.contador.username,
                        "contagens": contagens_para_envio
                    }
                    
                    logging.info(f"[DEBUG] Enviando para Django: sessao={data['sessao']}, usuario={data['usuario']}, contagens={len(data['contagens'])}")
                    
                    try:
                        response = await self.contador.api_manager.client.post(
                            "/contagens/atualizar-contagens/",
                            json=data
                        )
                        
                        logging.info(f"[DEBUG] Resposta Django: status={response.status_code}")
                        
                        if response.status_code in [200, 201]:
                            resp_data = response.json()
                            logging.info(f"[SUCCESS] Movimento {movimento} sincronizado: {resp_data}")
                        else:
                            error_text = response.text
                            logging.error(f"[ERROR] Falha ao sincronizar movimento {movimento}: {response.status_code} - {error_text}")
                            
                    except Exception as req_ex:
                        logging.error(f"[ERROR] Erro na requisição para movimento {movimento}: {str(req_ex)}")
        
        except Exception as ex:
            logging.error(f"[ERROR] Erro geral ao sincronizar com Django: {ex}")
            import traceback
            logging.error(f"[ERROR] Traceback: {traceback.format_exc()}")

    def exportar_dados(self, e=None):
        """Mostra informações básicas dos dados"""
        try:
            if not self.periodos_data:
                self._show_warning("⚠️ Nenhum dado")
                return
            
            total_periodos = sum(len(df) for df in self.periodos_data.values())
            self._show_success(f"📊 {total_periodos} períodos disponíveis")
            
        except Exception as ex:
            logging.error(f"Erro ao exportar dados: {ex}")

    def _show_empty_state(self):
        """Mostra estado vazio minimalista"""
        empty_content = ft.Column([
            ft.Text(
                "📭 Nenhum período encontrado",
                size=16,
                color=ft.Colors.WHITE,
                text_align=ft.TextAlign.CENTER
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        self.main_container.content = empty_content
        self.main_container.update()

    def _show_success(self, message):
        """Mostra mensagem de sucesso com visual elegante"""
        self._update_status_with_style(message, ft.Colors.GREEN_700, "✅")

    def _show_error(self, message):
        """Mostra mensagem de erro com visual elegante"""
        self._update_status_with_style(message, ft.Colors.RED_700, "❌")

    def _show_warning(self, message):
        """Mostra mensagem de aviso com visual elegante"""
        self._update_status_with_style(message, ft.Colors.ORANGE_700, "⚠️")
        
    def _update_status_with_style(self, message, bg_color, icon):
        """Atualiza status com visual melhorado e contador"""
        try:
            # Calcular estatísticas dos dados
            stats_text = ""
            if self.periodos_data:
                total_periods = sum(len(df) for df in self.periodos_data.values())
                movements_count = len(self.periodos_data)
                stats_text = f" | 📊 {movements_count} movimentos | 📋 {total_periods} períodos"
            
            # Criar container de status elegante
            status_content = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text(
                            f"{icon} {message}{stats_text}",
                            color=ft.Colors.WHITE,
                            size=14,
                            weight=ft.FontWeight.BOLD
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                bgcolor=bg_color,
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                border_radius=8,
                border=ft.border.all(1, ft.Colors.WHITE12)
            )
            
            self.status_text.content = status_content
            self.status_text.update()
            
        except Exception as ex:
            logging.error(f"Erro ao atualizar status: {ex}")

    def _get_excel_path(self):
        """Retorna caminho do arquivo Excel da sessão atual"""
        nome_pesquisador = re.sub(r'[<>:"/\\|?*]', '', self.contador.username)
        codigo = re.sub(r'[<>:"/\\|?*]', '', self.contador.details['Código'])
        excel_dir = get_excel_dir()
        diretorio_pesquisador_codigo = os.path.join(excel_dir, nome_pesquisador, codigo)
        return os.path.join(diretorio_pesquisador_codigo, f'{self.contador.sessao}.xlsx')

    def force_ui_update(self):
        """OBRIGATÓRIO: Para recuperação de sessões"""
        self.setup_ui()
        # Auto-carregar dados se há sessão ativa
        if self.contador.sessao:
            self.carregar_periodos()
        self.update()
