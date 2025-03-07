#aba_config.py
import flet as ft
from utils.change_binds import abrir_configuracao_binds

def setup_aba_config(self):
    tab = self.tabs.tabs[3].content
    tab.controls.clear()

    # Avatar com inicial do usuário
    avatar = ft.CircleAvatar(
        content=ft.Text(self.username[0].upper() if self.username else "U"),
        radius=40,
        bgcolor=ft.colors.BLUE_200
    )
    username_text = ft.Text(
        f"Conectado como: {self.username}",
        weight=ft.FontWeight.W_400,
        size=15,
        text_align=ft.TextAlign.CENTER
    )

    profile_container = ft.Column(
        controls=[avatar, username_text],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=5
    )

    self.modo_claro_escuro = ft.Switch(
        label="Modo claro" if self.page.theme_mode == ft.ThemeMode.LIGHT else "Modo escuro",
        value=self.page.theme_mode == ft.ThemeMode.LIGHT,
        on_change=self.theme_changed
    )

    opacity = ft.Slider(
        value=100, min=20, max=100, divisions=20, label="Opacidade {value}%",
        on_change=self.ajustar_opacidade
    )

    config_button = ft.ElevatedButton(
        text="Configurar Binds",
        icon=ft.icons.SETTINGS,
        on_click=lambda e: abrir_configuracao_binds(self.page, self)
    )

    logout_button = ft.ElevatedButton(
        text="Sair",
        bgcolor=ft.colors.RED,
        color=ft.colors.WHITE,
        icon=ft.icons.LOGOUT,
        on_click=self.logout_user
    )

    config_layout = ft.Column(
        controls=[
            profile_container,
            ft.Divider(),
            ft.Text("Aparência", weight=ft.FontWeight.BOLD, size=16),
            self.modo_claro_escuro,
            ft.Divider(),
            ft.Text("Transparência da Janela", weight=ft.FontWeight.BOLD, size=16),
            opacity,
            ft.Divider(),
            ft.Text("Configurações Avançadas", weight=ft.FontWeight.BOLD, size=16),
            config_button,
            ft.Divider(),
            ft.Text("Deslogar", weight=ft.FontWeight.BOLD, size=16),
            logout_button
        ],
        spacing=20,
        scroll=ft.ScrollMode.AUTO
    )

    tab.controls.append(config_layout)
    self.page.update()

def theme_changed(self, e):
    self.page.theme_mode = ft.ThemeMode.LIGHT if e.control.value else ft.ThemeMode.DARK
    self.modo_claro_escuro.label = "Modo claro" if self.page.theme_mode == ft.ThemeMode.LIGHT else "Modo escuro"
    self.page.update()

def ajustar_opacidade(self, e):
    try:
        self.page.window.opacity = e.control.value / 100
        self.page.update()
    except Exception as ex:
        logger.error(f"Erro ao ajustar opacidade: {ex}")

def abrir_configurar_binds(self):
    """Abre a configuração de binds e carrega as preferências do usuário se existirem."""
    padrao_atual = self.padrao_dropdown.value
    binds_salvas = self.user_preferences.get(padrao_atual, {})

    for movimento, tecla in binds_salvas.items():
        self.atualizar_bind_movimento(movimento, tecla)  # Aplicar no Flet

async def save_user_preferences(self, padrao, binds):
    """Salva as preferências do usuário na API."""
    try:
        headers = {"Authorization": f"Bearer {self.tokens['access']}"}
        response = await async_api_request(
            url=f"{API_URL}/api/user/preferences/",
            method="POST",
            headers=headers,
            data={"padrao": padrao, "binds": binds}
        )
        logger.info("Preferências salvas com sucesso!")
        self.page.overlay.append(ft.SnackBar(ft.Text("Preferências salvas!"), bgcolor=ft.colors.GREEN))
    except Exception as ex:
        logger.error(f"Erro ao salvar preferências: {ex}")
        self.page.overlay.append(ft.SnackBar(ft.Text(f"Erro ao salvar preferências: {ex}"), bgcolor=ft.colors.RED))
    self.page.update()