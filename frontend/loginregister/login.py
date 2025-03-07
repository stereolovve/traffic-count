# loginregister/login.py
import flet as ft
import logging
import json
from pathlib import Path
from utils.config import API_URL, APP_DATA_DIR
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

        # Container content with centered layout
        self.content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Login", size=30, weight="bold"),
                    self.username_field,
                    self.password_field,
                    self.login_button,
                    self.register_button,
                    self.error_text,
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
            self.update()
        else:
            logging.warning("Tentativa de atualizar LoginPage fora do contexto da página.")

    async def perform_login(self, username, password):
        """Realiza a operação de login de forma assíncrona."""
        try:
            payload = {"username": username, "password": password}
            response = await async_api_request(
                url=f"{API_URL}/api/login/",
                method="POST",
                json_data=payload
            )

            if isinstance(response, dict) and "access" in response:  # ✅ Verifica corretamente
                self.app.tokens = {"access": response["access"], "refresh": response["refresh"]}
                self.app.username = username

                # Salva tokens no disco
                tokens_path = APP_DATA_DIR / "auth_tokens.json"
                with open(tokens_path, "w") as f:
                    json.dump({
                        "username": username,
                        "access": response["access"],
                        "refresh": response["refresh"]
                    }, f)

                print(f"🔑 Token salvo com sucesso: {self.app.tokens}")

                # Carregar preferências do usuário
                await self.app.load_user_preferences()

                # Mostra mensagem de sucesso e redireciona
                snackbar = ft.SnackBar(ft.Text("Login realizado com sucesso!"), bgcolor="GREEN")
                self.page.overlay.append(snackbar)
                snackbar.open = True

                await self.app.switch_to_main_app()  # ✅ Aguarda a troca de tela
            else:
                raise ValueError("Credenciais inválidas!")

        except ValueError as ve:
            self.show_error(str(ve))
        except Exception as ex:
            logging.error(f"Erro ao fazer login: {ex}")
            self.show_error(f"Erro ao conectar: {str(ex)}")


    def login(self, e):
        """Handles the login button click, scheduling the async login operation."""
        username = self.username_field.value
        password = self.password_field.value

        if not username or not password:
            self.show_error("Usuário e senha são obrigatórios!")
            return

        # Define a standalone coroutine function for page.run_task
        async def wrapped_login():
            await self.perform_login(username, password)

        # Schedule the coroutine using page.run_task
        self.page.run_task(wrapped_login)

    def show_register(self, e):
        """Switches to the register page (synchronous)."""
        print("🔄 Alternando para tela de registro...")
        self.app.show_register_page()