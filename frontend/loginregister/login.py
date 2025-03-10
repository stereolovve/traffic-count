import flet as ft
import logging
import json
from pathlib import Path
from utils.config import API_URL, DESKTOP_DIR
from utils.api import async_api_request

logging.getLogger(__name__).setLevel(logging.ERROR)

class LoginPage(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.page = app.page

        # UI Components
        self.username_field = ft.TextField(label="Usuário", width=300)
        self.password_field = ft.TextField(
            label="Senha",
            password=True,
            width=300,
        )
        self.login_button = ft.ElevatedButton("Entrar", on_click=self.login)
        self.register_button = ft.TextButton("Não tem uma conta? Registrar", on_click=self.show_register)
        self.error_text = ft.Text(value="", color="red", visible=False)
        # Indicador de carregamento
        self.loading_indicator = ft.ProgressRing(
            width=50,
            height=50,
            visible=False,
            stroke_width=6,
            color=ft.colors.BLUE_700
        )

        # Container content with centered layout
        self.content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Login", size=30, weight="bold"),
                    self.username_field,
                    self.password_field,
                    self.login_button,
                    self.loading_indicator,  # Adiciona o indicador ao layout
                    self.error_text,
                    self.register_button,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=15,
            ),
            border_radius=10,
            width=800,
            height=600,
            alignment=ft.alignment.center,
        )

    def build(self):
        """Builds the login UI."""
        return self.content

    def show_error(self, message: str, is_success: bool = False):
        """Displays an error or success message in the UI."""
        if self.page and self in self.page.controls:  # Verifica se o controle está na página
            self.error_text.value = message
            self.error_text.color = "green" if is_success else "red"
            self.error_text.visible = True
            self.loading_indicator.visible = False  # Oculta o indicador ao mostrar mensagem
            self.page.update()
        else:
            logging.warning("Tentativa de atualizar LoginPage fora do contexto da página.")

    async def perform_login(self, username, password):
        """Realiza a operação de login de forma assíncrona."""
        # Mostra o indicador de carregamento
        if self.page:
            self.loading_indicator.visible = True
            self.login_button.disabled = True  # Desativa o botão para evitar cliques múltiplos
            self.page.update()
        else:
            logging.error("self.page é None durante o início do login.")
            return

        try:
            payload = {"username": username, "password": password}
            response = await async_api_request(
                url=f"{API_URL}/api/login/",
                method="POST",
                json_data=payload
            )

            if isinstance(response, dict) and "access" in response:
                self.app.tokens = {"access": response["access"], "refresh": response["refresh"]}
                self.app.username = username

                tokens_path = DESKTOP_DIR / "auth_tokens.json"
                with open(tokens_path, "w") as f:
                    json.dump({
                        "username": username,
                        "access": response["access"],
                        "refresh": response["refresh"]
                    }, f)


                await self.app.load_user_preferences()

                snackbar = ft.SnackBar(ft.Text("Login realizado com sucesso!"), bgcolor="GREEN")
                if self.page:
                    self.page.overlay.append(snackbar)
                    snackbar.open = True
                    self.page.update()
                else:
                    logging.warning("self.page é None ao mostrar snackbar de sucesso no login.")

                await self.app.switch_to_main_app() 
            else:
                raise ValueError("Credenciais inválidas!")

        except ValueError as ve:
            self.show_error(str(ve))
        except Exception as ex:
            logging.error(f"Erro ao fazer login: {ex}")
            self.show_error(f"Erro ao conectar: {str(ex)}")
        finally:
            if self.page:
                self.loading_indicator.visible = False
                self.login_button.disabled = False
                self.page.update()
            else:
                logging.warning("self.page é None no finally do login.")

    def login(self, e):
        username = self.username_field.value
        password = self.password_field.value

        if not username or not password:
            self.show_error("Usuário e senha são obrigatórios!")
            return

        async def wrapped_login():
            await self.perform_login(username, password)

        if self.page:
            self.page.run_task(wrapped_login)
        else:
            logging.error("self.page é None ao iniciar o login.")

    def show_register(self, e):
        self.app.show_register_page()