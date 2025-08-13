# utils/change_binds.py
import logging
import flet as ft
import asyncio
import threading
from pathlib import Path
import json
from utils.config import API_URL, DESKTOP_DIR
from utils.api import async_api_request

logging.getLogger(__name__).setLevel(logging.ERROR)

class BindManager:
    def __init__(self, page=None, contador=None):
        self.page = page
        self.contador = contador

    async def load_tokens(self):
        tokens_path = DESKTOP_DIR / "auth_tokens.json"
        if tokens_path.exists():
            try:
                with open(tokens_path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError as ex:
                logging.error(f"Erro ao carregar tokens: {ex}")
        return None

    async def get_authenticated_headers(self):
        tokens = await self.load_tokens()
        if not tokens or "access" not in tokens:
            logging.warning("[WARNING] ❌ Nenhum token encontrado.")
            return None
        
        return {"Authorization": f"Bearer {tokens['access']}"}

    async def carregar_padroes(self):
        headers = await self.get_authenticated_headers()
        if not headers:
            logging.error("❌ Falha ao recuperar token! Abortando requisição.")
            return []
        
        try:
            response = await async_api_request("GET", "padroes/tipos-de-padrao/", None, headers)
            return response if isinstance(response, list) else []
        except Exception as e:
            logging.error(f"Erro ao carregar padrões: {e}")
            return []

    async def carregar_categorias(self, tipo_padrao):
        headers = await self.get_authenticated_headers()
        if not headers:
            return []
        
        try:
            response = await async_api_request("GET", f"padroes/merged-binds/?pattern_type={tipo_padrao}", None, headers)
            return response if isinstance(response, list) else []
        except Exception as e:
            logging.error(f"Erro ao carregar categorias: {e}")
            return []

    async def salvar_bind(self, tipo_padrao, veiculo, novo_bind):
        headers = await self.get_authenticated_headers()
        if not headers:
            return False
        
        try:
            dados = {"pattern_type": tipo_padrao, "veiculo": veiculo, "bind": novo_bind}
            response = await async_api_request("POST", "padroes/user-padroes/", dados, headers)
            return "erro" not in response and "error" not in response
        except Exception as e:
            logging.error(f"Erro ao salvar bind: {e}")
            return False

def executar_async(coroutine):
    """Execute async coroutine in a thread-safe way"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coroutine)  
    except RuntimeError:
        threading.Thread(target=lambda: asyncio.run(coroutine)).start()

def abrir_configuracao_binds(page, contador):
    """Open bind configuration dialog using Flet 0.28.3+ syntax"""
    
    bind_manager = BindManager(page, contador)
    
    # State variables for the dialog
    padroes_list = []
    categorias_list = []
    
    # UI Components
    padrao_dropdown = ft.Dropdown(
        label="Selecione um Tipo de Padrão",
        options=[ft.dropdown.Option("Carregando...")],
        width=300
    )
    
    binds_container = ft.Column(
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        height=300,
        controls=[
            ft.Text(
                "Aguardando seleção de padrão...",
                size=14
            )
        ]
    )
    
    def close_dialog(e=None):
        page.close(dialog)
    
    def save_bind(veiculo, text_field):
        """Save bind for a specific vehicle"""
        def _save(e):
            novo_bind = text_field.value.strip()
            if not novo_bind:
                page.open(ft.SnackBar(ft.Text("Digite uma tecla válida!")))
                return
                
            tipo_padrao = padrao_dropdown.value
            if not tipo_padrao:
                page.open(ft.SnackBar(ft.Text("Selecione um tipo de padrão!")))
                return
            
            # Execute async save operation
            executar_async(save_bind_async(tipo_padrao, veiculo, novo_bind, text_field))
        
        return _save
    
    async def save_bind_async(tipo_padrao, veiculo, novo_bind, text_field):
        """Async function to save bind"""
        sucesso = await bind_manager.salvar_bind(tipo_padrao, veiculo, novo_bind)
        if sucesso:
            text_field.bgcolor = ft.Colors.GREEN_800
            page.open(ft.SnackBar(ft.Text(f"Bind '{novo_bind}' salvo para {veiculo}!")))
            
            # Usar método direto do contador para recarregar binds
            if contador and hasattr(contador, 'reload_binds_from_api'):
                contador.reload_binds_from_api(tipo_padrao)
            else:
                print("🔧 DEBUG: Contador não tem método reload_binds_from_api")
            
        else:
            text_field.bgcolor = ft.Colors.RED_100
            page.open(ft.SnackBar(ft.Text("Erro ao salvar bind!")))
        page.update()
    
    def on_padrao_change(e):
        """Handle pattern type selection change"""
        if not padrao_dropdown.value or padrao_dropdown.value == "Carregando...":
            return
            
        executar_async(carregar_categorias_async(padrao_dropdown.value))
    
    async def carregar_categorias_async(tipo_padrao):
        """Load categories for selected pattern type"""
        binds_container.controls.clear()
        binds_container.controls.append(
            ft.Text("Carregando categorias...")
        )
        page.update()
        
        categorias = await bind_manager.carregar_categorias(tipo_padrao)
        
        binds_container.controls.clear()
        
        if not categorias:
            binds_container.controls.append(
                ft.Text("Nenhuma categoria encontrada.")
            )
        else:
            for categoria in categorias:
                veiculo = categoria.get('veiculo', 'N/A')
                bind_atual = categoria.get('bind', '')
                
                # Create text field for bind input
                bind_field = ft.TextField(
                    label=f"Tecla para {veiculo}",
                    value=bind_atual,
                    width=200,
                    max_length=10,
                    hint_text="Ex: a, 1, np1, f1, space"
                )
                
                # Save button for this bind
                save_btn = ft.ElevatedButton(
                    "Salvar",
                    on_click=save_bind(veiculo, bind_field)
                )
                
                # Row with vehicle name, input field, and save button
                bind_row = ft.Row([
                    ft.Text(veiculo, width=100),
                    bind_field,
                    save_btn
                ], alignment=ft.MainAxisAlignment.START)
                
                binds_container.controls.append(bind_row)
        
        page.update()
    
    # Set dropdown change handler
    padrao_dropdown.on_change = on_padrao_change
    
    # Create the dialog
    dialog = ft.AlertDialog(
        title=ft.Text("Configuração de Binds"),
        content=ft.Container(
            content=ft.Column([
                ft.Text(
                    "Escolha um tipo de padrão e defina as teclas de atalho para cada veículo.",
                    size=14
                ),
                padrao_dropdown,
                ft.Divider(),
                binds_container,
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            height=500,
            width=600,
            border_radius=10,
            padding=20
        ),
        actions=[
            ft.TextButton(
                "Fechar",
                on_click=close_dialog
            )
        ],
        modal=True
    )
    
    # Load pattern types async
    async def carregar_padroes_async():
        padroes = await bind_manager.carregar_padroes()
        padrao_dropdown.options.clear()
        
        if padroes:
            padrao_dropdown.options = [
                ft.dropdown.Option(padrao if isinstance(padrao, str) else padrao.get('tipo', 'N/A'))
                for padrao in padroes
            ]
        else:
            padrao_dropdown.options = [ft.dropdown.Option("Nenhum padrão encontrado")]
        
        page.update()
    
    
    page.open(dialog)
    
    executar_async(carregar_padroes_async())

def criar_dialog_completo(page, contador):
    """Create the full bind configuration dialog (separate function for testing)"""
    
    bind_manager = BindManager(page, contador)

    # Dark theme components following UI guidelines
    subtitulo = ft.Text(
        "Escolha um tipo de padrão e defina as teclas de atalho para cada veículo.",
        size=14, 
    )

    padrao_dropdown = ft.Dropdown(
        label="Selecione um Tipo de Padrão",
        options=[ft.dropdown.Option("Carregando...")],
    )

    binds_container = ft.Column(
        spacing=10, 
        scroll=ft.ScrollMode.AUTO, 
        expand=True,
        controls=[
            ft.Text(
                "Aguardando seleção de padrão...", 
                size=14
            )
        ]
    )

    def fechar_dialogo(e=None):
        """Close dialog safely"""
        if page.dialog:
            page.dialog.open = False
            page.dialog = None
            page.update()

    # Create dialog with complete dark theme following UI guidelines
    dialog = ft.AlertDialog(
        title=ft.Text("Configuração de Binds", color=ft.Colors.WHITE),
        content=ft.Container(
            content=ft.Column([
                subtitulo,
                padrao_dropdown,
                ft.Divider(),  # Dark theme divider
                binds_container,
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            height=500,
            width=600,  # Added explicit width
            border_radius=10,
            padding=20
        ),
        actions=[
            ft.TextButton(
                "Fechar", 
                on_click=fechar_dialogo
            )
        ],
        modal=True,
    )

    return dialog
