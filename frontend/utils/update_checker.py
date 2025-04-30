"""
Módulo para verificar atualizações disponíveis do aplicativo
"""
import asyncio
import flet as ft
from .api import async_api_request
from .config import API_URL, APP_VERSION

class UpdateChecker:
    """
    Classe para verificar e notificar sobre novas versões do aplicativo
    """
    def __init__(self, page: ft.Page):
        self.page = page
        self.update_available = False
        self.latest_version = None
        self.download_url = None
        self.changelog = None
        self.published_at = None

    async def check_for_updates(self):
        """
        Verifica se há atualizações disponíveis no servidor
        """
        try:
            # Endpoint que criamos no Django
            endpoint = "updates/api/check-version/"
            params = f"?version={APP_VERSION}"
            
            # Faz a requisição para o backend
            response = await async_api_request("GET", f"{endpoint}{params}")
            
            if response and "erro" not in response:
                self.update_available = response.get("has_update", False)
                
                if self.update_available:
                    self.latest_version = response.get("latest_version")
                    self.download_url = response.get("download_url")
                    self.changelog = response.get("changelog")
                    self.published_at = response.get("published_at")
                    
                    # Mostra a notificação de atualização
                    await self.show_update_notification()
            
            return self.update_available
        except Exception as e:
            print(f"Erro ao verificar atualizações: {str(e)}")
            return False

    async def show_update_notification(self):
        """
        Exibe uma notificação de atualização disponível
        """
        if not self.update_available or not self.latest_version:
            return
        
        # Cria um banner de notificação
        update_banner = ft.Banner(
            leading=ft.Icon(
                name=ft.icons.SYSTEM_UPDATE,
                size=40,
            ),
            content=ft.Column([
                ft.Text(
                    f"Nova versão disponível! Atualize para v{self.latest_version}",
                    weight=ft.FontWeight.BOLD,
                    size=16,
                ),
                ft.Text(
                    f"Publicado em {self.published_at}",
                    size=12,
                ),
            ]),
            actions=[
                ft.TextButton(
                    "Ignorar",
                    on_click=lambda e: self.close_banner(e, update_banner),
                ),
                ft.TextButton(
                    "Ver detalhes",
                    on_click=self.handle_show_dialog_click,
                ),
            ],
        )
        
        # Adiciona o banner à página
        self.page.banner = update_banner
        self.page.banner.open = True
        await self.page.update_async()

    def handle_show_dialog_click(self, e):
        """Manipulador de evento para o clique no botão 'Ver detalhes'"""
        # Chamando a versão síncrona do método
        self.show_update_dialog_sync()
        
    def close_banner(self, e, banner):
        """Fecha o banner de notificação"""
        banner.open = False
        self.page.update()

    def show_update_dialog_sync(self):
        """Versão síncrona para mostrar um diálogo com detalhes da atualização e opção para download"""
        # Fecha o banner se estiver aberto
        if self.page.banner and self.page.banner.open:
            self.page.banner.open = False
            self.page.update()
        
        # Cria o diálogo de atualização com melhor visibilidade
        update_dialog = ft.AlertDialog(
            title=ft.Text(
                f"Versão v{self.latest_version} disponível! Baixe e coloque essa versão na pasta Contador e execute!",
                size=20,
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Column([
                ft.Text(
                    "Registro de alterações:",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Container(
                    content=ft.Text(
                        self.changelog,
                        size=14,
                    ),
                    border=ft.border.all(1),
                    border_radius=8,
                    padding=15,
                    margin=ft.margin.only(top=10, bottom=10),
                    width=500,  # Aumentado para melhor legibilidade
                    height=250,  # Aumentado para mostrar mais conteúdo
                ),
                ft.Text(
                    f"Publicado em: {self.published_at}",
                    size=14,
                    weight=ft.FontWeight.BOLD
                ),
            ], 
            scroll=ft.ScrollMode.AUTO,
            height=350,  # Aumentado para acomodar o conteúdo maior
            width=550),   # Aumentado para melhor legibilidade
            actions=[
                ft.TextButton(
                    "Fechar",
                    on_click=self.close_dialog,
                ),
                ft.ElevatedButton(
                    "Baixar atualização",
                    on_click=self.open_download_url,
                    style=ft.ButtonStyle(
                        elevation=5,
                        padding=15,
                    ),
                    icon=ft.icons.DOWNLOAD,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        self.page.dialog = update_dialog
        self.page.dialog.open = True
        self.page.update()
    async def show_update_dialog(self):
        """Mostra um diálogo com detalhes da atualização e opção para download"""
        # Fecha o banner se estiver aberto
        if self.page.banner and self.page.banner.open:
            self.page.banner.open = False
            await self.page.update_async()
        
        # Cria o diálogo de atualização com melhor visibilidade
        update_dialog = ft.AlertDialog(
            title=ft.Text(
                f"Versão v{self.latest_version} disponível!",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=ft.colors.BLUE_700
            ),
            content=ft.Column([
                ft.Text(
                    "Registro de alterações:",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Container(
                    content=ft.Text(
                        self.changelog,
                        size=14,
                    ),
                    border=ft.border.all(1, ft.colors.BLUE_200),
                    border_radius=8,
                    padding=15,
                    margin=ft.margin.only(top=10, bottom=10),
                    width=500,  # Aumentado para melhor legibilidade
                    height=250,  # Aumentado para mostrar mais conteúdo
                    scroll=ft.ScrollMode.AUTO,
                ),
                ft.Text(
                    f"Publicado em: {self.published_at}",
                    size=14,
                    weight=ft.FontWeight.BOLD
                ),
            ], 
            scroll=ft.ScrollMode.AUTO,
            height=350,  # Aumentado para acomodar o conteúdo maior
            width=550),   # Aumentado para melhor legibilidade
            actions=[
                ft.TextButton(
                    "Fechar",
                    on_click=self.close_dialog,
                    style=ft.ButtonStyle(color=ft.colors.GREY_700),
                ),
                ft.ElevatedButton(
                    "Baixar atualização",
                    on_click=self.open_download_url,
                    style=ft.ButtonStyle(
                        bgcolor=ft.colors.BLUE_700,
                        elevation=5,
                        padding=15,
                    ),
                    icon=ft.icons.DOWNLOAD,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Exibe o diálogo
        self.page.dialog = update_dialog
        self.page.dialog.open = True
        await self.page.update_async()
        
    # Método removido pois foi incorporado ao show_update_dialog_sync

    def close_dialog(self, e):
        """Fecha o diálogo de atualização"""
        self.page.dialog.open = False
        self.page.update()

    def open_download_url(self, e):
        """Abre a URL de download no navegador"""
        import webbrowser
        if self.download_url:
            webbrowser.open(self.download_url)
            self.close_dialog(e)
