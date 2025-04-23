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

        self.username_text = ft.Text(
            f"Conectado como: {self.contador.username}",
            weight=ft.FontWeight.W_400,
            size=15,
            text_align=ft.TextAlign.CENTER
        )

        # Criar container do perfil
        self.profile_container = ft.Column(
            controls=[
                ft.Container(self.username_text, alignment=ft.alignment.center),
            ],
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        # Criar switch de tema
        self.modo_claro_escuro = ft.Switch(
            label="Modo claro", 
            on_change=self.theme_changed
        )

        # Criar slider de opacidade (renomeado de opacity para opacity_slider)
        self.opacity_slider = ft.Slider(
            value=100, 
            min=20, 
            max=100, 
            divisions=20, 
            label="Opacidade",
            on_change=self.ajustar_opacidade
        )

        # Criar botões
        self.config_button = ft.ElevatedButton(
            text="Configurar Binds", 
            on_click=lambda e: abrir_configuracao_binds(self.contador.page, self.contador),
            icon=ft.icons.SETTINGS
        )

        self.logout_button = ft.ElevatedButton(
            text="Sair",
            bgcolor="RED",
            color="WHITE",
            on_click=self.contador.logout_user,
            icon=ft.icons.LOGOUT
        )

        # Montar o layout completo
        self.config_layout = ft.Column(
            controls=[
                self.profile_container,
                ft.Divider(),
                ft.Text("Aparência", weight=ft.FontWeight.BOLD, size=16),
                self.modo_claro_escuro,
                ft.Divider(),
                ft.Text("Transparência da Janela", weight=ft.FontWeight.BOLD, size=16),
                self.opacity_slider,
                ft.Divider(),
                ft.Text("Configurações Avançadas", weight=ft.FontWeight.BOLD, size=16),
                self.config_button,
                ft.Divider(),
                ft.Text("Deslogar:", weight=ft.FontWeight.BOLD, size=16),
                self.logout_button
            ],
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            scroll=ft.ScrollMode.AUTO
        )

        # Adicionar o layout à aba
        self.controls = [self.config_layout]

    def theme_changed(self, e):
        self.contador.page.theme_mode = (
            ft.ThemeMode.DARK if self.contador.page.theme_mode == ft.ThemeMode.LIGHT 
            else ft.ThemeMode.LIGHT
        )
        self.modo_claro_escuro.label = (
            "Modo claro" if self.contador.page.theme_mode == ft.ThemeMode.LIGHT 
            else "Modo escuro"
        )
        self.contador.page.update()

    def ajustar_opacidade(self, e):
        try:
            nova_opacidade = e.control.value / 100
            self.contador.page.window.opacity = nova_opacidade
            self.contador.page.update()
        except Exception as ex:
            logging.error(f"Erro ao ajustar opacidade: {ex}")

    def abrir_configurar_binds(self):
        padrao_atual = self.padrao_dropdown.value
        binds_salvas = self.user_preferences.get(padrao_atual, {})

        for movimento, tecla in binds_salvas.items():
            self.atualizar_bind_movimento(movimento, tecla)

    async def save_user_preferences(self, padrao, binds):
        try:
            headers = {"Authorization": f"Bearer {self.tokens['access']}"}
            response = await async_api_request(
                "POST",
                "/padroes/user/preferences/",
                data={"padrao": padrao, "binds": binds},
                headers=headers
            )
            logger.info("Preferências salvas com sucesso!")
            self.page.overlay.append(ft.SnackBar(ft.Text("Preferências salvas!"), bgcolor=ft.colors.GREEN))
        except Exception as ex:
            logger.error(f"Erro ao salvar preferências: {ex}")
            self.page.overlay.append(ft.SnackBar(ft.Text(f"Erro ao salvar preferências: {ex}"), bgcolor=ft.colors.RED))
        self.page.update()