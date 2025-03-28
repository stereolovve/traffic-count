# utils/change_binds.py
import logging
import httpx
import flet as ft
import asyncio
import threading
from pathlib import Path
import json
from utils.config import API_URL,DESKTOP_DIR
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
        
        response = await async_api_request(f"{API_URL}/padroes/tipos-de-padrao/", headers=headers)
        return response if isinstance(response, list) else []

    async def carregar_categorias(self, tipo_padrao):
        headers = await self.get_authenticated_headers()
        if not headers:
            return []
        
        response = await async_api_request(f"{API_URL}/padroes/merged-binds/?pattern_type={tipo_padrao}", headers=headers)
        return response if isinstance(response, list) else []

    async def salvar_bind(self, tipo_padrao, veiculo, novo_bind):
        headers = await self.get_authenticated_headers()
        if not headers:
            return False
        
        dados = {"pattern_type": tipo_padrao, "veiculo": veiculo, "bind": novo_bind}
        response = await async_api_request(
            f"{API_URL}/padroes/user-padroes/", 
            method="POST", 
            headers=headers,
            json_data=dados 
        )
        return "error" not in response
def executar_async(coroutine):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coroutine)  
    except RuntimeError:
        threading.Thread(target=lambda: asyncio.run(coroutine)).start()

def abrir_configuracao_binds(page, contador):
    if hasattr(page, 'dialog') and page.dialog is not None:
        page.dialog.open = False
        page.dialog = None

    bind_manager = BindManager(page, contador)

    subtitulo = ft.Text(
        "Escolha um tipo de padrão e defina as teclas de atalho para cada veículo.",
        size=14, color="GRAY"
    )

    padrao_dropdown = ft.Dropdown(
        label="Selecione um Tipo de Padrão",
        options=[]
    )

    binds_container = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    async def carregar_padroes_e_atualizar():
        padroes = await bind_manager.carregar_padroes()

        if isinstance(padroes, list) and padroes:
            padrao_dropdown.options = [ft.dropdown.Option(str(p)) for p in padroes]
            padrao_dropdown.value = padroes[0] 

            executar_async(carregar_categorias_e_atualizar(padroes[0]))
        else:
            logging.error("Erro: `padroes` não é uma lista válida.")
            padrao_dropdown.options = [ft.dropdown.Option("Nenhum padrão encontrado")]

        padrao_dropdown.update()
        page.update()

    async def carregar_categorias_e_atualizar(tipo_padrao):
        categorias = await bind_manager.carregar_categorias(tipo_padrao)
        binds_container.controls.clear()

        if isinstance(categorias, list) and categorias:
            for cat in categorias:
                veiculo = cat.get("veiculo", "Desconhecido")
                bind_inicial = cat.get("bind", "Não definido")

                bind_input = ft.TextField(
                    value=bind_inicial,
                    label=f"Tecla para {veiculo}",
                    width=150,
                    text_align=ft.TextAlign.CENTER
                )

                salvar_button = ft.IconButton(
                    icon=ft.icons.SAVE,
                    tooltip="Salvar Bind",
                    on_click=lambda e, v=veiculo, b=bind_input: executar_async(salvar_bind_e_atualizar(v, b.value, tipo_padrao))
                )

                binds_container.controls.append(ft.Row(
                    controls=[
                        ft.Text(veiculo, size=16, weight=ft.FontWeight.W_500),
                        bind_input,
                        salvar_button
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ))

        else:
            binds_container.controls.append(
                ft.Text("Nenhuma categoria encontrada.", color="RED")
            )

        binds_container.update()
        page.update()

    async def salvar_bind_e_atualizar(veiculo, novo_bind, tipo_padrao):
        if await bind_manager.salvar_bind(tipo_padrao, veiculo, novo_bind):
            snackbar = ft.SnackBar(
                ft.Text(f"✅ Bind atualizado para {veiculo}!"),
                bgcolor="GREEN"
            )

            if hasattr(contador, "binds"):
                contador.binds[veiculo] = novo_bind
                contador.atualizar_binds_na_ui()
        else:
            snackbar = ft.SnackBar(
                ft.Text(f"❌ Erro ao atualizar bind para {veiculo}."), bgcolor="RED"
            )

        page.overlay.append(snackbar)
        snackbar.open = True
        page.update()

    def fechar_dialogo():
        page.dialog.open = False
        page.update()

    padrao_dropdown.on_change = lambda e: executar_async(carregar_categorias_e_atualizar(e.control.value))

    dialog = ft.AlertDialog(
        title=ft.Text("Configuração de Binds"),
        content=ft.Container(
            content=ft.Column([
                subtitulo,
                padrao_dropdown,
                ft.Divider(),
                binds_container,
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            height=500,
            expand=True
        ),
        actions=[
            ft.TextButton("Fechar", on_click=lambda e: fechar_dialogo())
        ],
        modal=True
    )

    page.dialog = dialog
    page.dialog.open = True
    page.update()

    executar_async(carregar_padroes_e_atualizar())

