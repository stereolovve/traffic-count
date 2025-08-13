#aba_config.py
import flet as ft
from utils.change_binds import abrir_configuracao_binds
from utils.api import async_api_request
from utils.config import API_URL
import logging

class AbaConfig(ft.Column):
    def __init__(self, contador):
        super().__init__()
        self.contador = contador
        self.scroll = ft.ScrollMode.AUTO
        self.spacing = 10
        
        # Inicializar todos os componentes primeiro
        self.setup_components()
        
        # Então adicionar aos controles
        self.controls = [self.config_layout]

    def setup_components(self):
        """Initialize all UI components with proper dark theme"""
        
        # Dark theme username text (following UI guidelines)
        self.username_text = ft.Text(
            f"Conectado como: {self.contador.username}",
            weight=ft.FontWeight.W_400,
            size=15,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.WHITE  # Light text for dark theme
        )

        # Dark theme profile container
        self.profile_container = ft.Column(
            controls=[
                ft.Container(
                    self.username_text, 
                    alignment=ft.alignment.center,
                    border_radius=8,
                    padding=10
                ),
            ],
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        # Dark theme switch
        self.modo_claro_escuro = ft.Switch(
            label="Modo claro", 
            on_change=self.theme_changed,
            active_color=ft.Colors.BLUE_400,  # Blue accent for switch
            inactive_track_color=ft.Colors.GREY_600
        )

        # Dark theme slider
        self.opacity_slider = ft.Slider(
            value=100, 
            min=20, 
            max=100, 
            divisions=20, 
            label="Opacidade",
            on_change=self.ajustar_opacidade,
            active_color=ft.Colors.BLUE_400,  # Blue accent
            inactive_color=ft.Colors.GREY_600
        )

        # CRITICAL FIX: Configurar Binds button with proper event handler
        self.config_button = ft.ElevatedButton(
            text="Configurar Binds", 
            on_click=self.abrir_configurar_binds_handler,
            icon=ft.Icons.SETTINGS,
            bgcolor=ft.Colors.BLUE_700,  # Dark blue background
            color=ft.Colors.WHITE,  # White text for contrast
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8)
            ),
            width=200,  # Fixed width for better appearance
            height=40   # Fixed height for better click area
        )

        # Logout button
        self.logout_button = ft.ElevatedButton(
            text="Sair",
            bgcolor=ft.Colors.RED_700,  # Dark red following guidelines
            color=ft.Colors.WHITE,  # White text for contrast
            on_click=self.logout_handler,  # Fixed: Use proper logout handler
            icon=ft.Icons.LOGOUT,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8)
            ),
            width=200,
            height=40
        )

        # Dark theme section headers
        self.aparencia_header = ft.Text(
            "Aparência", 
            weight=ft.FontWeight.BOLD, 
            size=16,
            color=ft.Colors.WHITE
        )
        
        self.transparencia_header = ft.Text(
            "Transparência da Janela", 
            weight=ft.FontWeight.BOLD, 
            size=16,
            color=ft.Colors.WHITE
        )
        
        self.configuracoes_header = ft.Text(
            "Configurações Avançadas", 
            weight=ft.FontWeight.BOLD, 
            size=16,
            color=ft.Colors.WHITE
        )
        
        self.deslogar_header = ft.Text(
            "Deslogar:", 
            weight=ft.FontWeight.BOLD, 
            size=16,
            color=ft.Colors.WHITE
        )

        # Dark theme layout with proper colors
        self.config_layout = ft.Column(
            controls=[
                self.profile_container,
                ft.Divider(color=ft.Colors.GREY_600),  # Dark divider
                self.aparencia_header,
                self.modo_claro_escuro,
                ft.Divider(color=ft.Colors.GREY_600),
                self.transparencia_header,
                self.opacity_slider,
                ft.Divider(color=ft.Colors.GREY_600),
                self.configuracoes_header,
                ft.Container(  # Wrap button in container for better positioning
                    self.config_button,
                    alignment=ft.alignment.center,
                    padding=10
                ),
                ft.Divider(color=ft.Colors.GREY_600),
                self.deslogar_header,
                ft.Container(  # Wrap button in container for better positioning
                    self.logout_button,
                    alignment=ft.alignment.center,
                    padding=10
                )
            ],
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            scroll=ft.ScrollMode.AUTO
        )

    def abrir_configurar_binds_handler(self, e):
        """CRITICAL FIX: Proper handler for opening bind configuration dialog"""
        try:
            logging.info("📋 Abrindo configuração de binds...")
            
            # Verificar se temos as dependências necessárias
            if not hasattr(self, 'contador'):
                raise Exception("Contador não encontrado")
                
            if not hasattr(self.contador, 'page'):
                raise Exception("Page não encontrado no contador")
        
            
            # Call the function with correct parameters
            abrir_configuracao_binds(self.contador.page, self.contador)
            
            logging.info("✅ Dialog de configuração aberto com sucesso")
            
        except Exception as ex:
            print(f"❌ TESTE: Erro capturado: {ex}")
            logging.error(f"❌ Erro ao abrir configuração de binds: {ex}")
            
            # Show error to user with dark theme
            try:
                snackbar = ft.SnackBar(
                    ft.Text(f"Erro ao abrir configuração: {str(ex)}", color=ft.Colors.WHITE),
                    bgcolor=ft.Colors.RED_700
                )
                self.contador.page.overlay.append(snackbar)
                snackbar.open = True
                self.contador.page.update()
            except Exception as snack_error:
                print(f"❌ TESTE: Erro ao mostrar snackbar: {snack_error}")

    def logout_handler(self, e):
        """Proper logout handler"""
        try:
            if hasattr(self.contador, 'logout_user'):
                self.contador.logout_user(e)
            else:
                logging.error("Método logout_user não encontrado no contador")
        except Exception as ex:
            logging.error(f"Erro no logout: {ex}")

    def theme_changed(self, e):
        try:
            self.contador.page.theme_mode = (
                ft.ThemeMode.DARK if self.contador.page.theme_mode == ft.ThemeMode.LIGHT 
                else ft.ThemeMode.LIGHT
            )
            self.modo_claro_escuro.label = (
                "Modo claro" if self.contador.page.theme_mode == ft.ThemeMode.LIGHT 
                else "Modo escuro"
            )
            self.contador.page.update()
        except Exception as ex:
            logging.error(f"Erro ao mudar tema: {ex}")

    def ajustar_opacidade(self, e):
        try:
            nova_opacidade = e.control.value / 100
            self.contador.page.window.opacity = nova_opacidade
            self.contador.page.update()
        except Exception as ex:
            logging.error(f"Erro ao ajustar opacidade: {ex}")

    def force_ui_update(self):
        try:
            if hasattr(self.contador, 'username'):
                self.username_text.value = f"Conectado como: {self.contador.username}"
                self.contador.page.update()
        except Exception as ex:
            logging.error(f"Erro ao atualizar UI: {ex}")