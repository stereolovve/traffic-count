# loginregister/register.py
import flet as ft
import logging
import asyncio
from utils.config import API_URL
from utils.api import async_api_request


logger = logging.getLogger(__name__)

class RegisterPage(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.page = app.page

        # Campos de entrada
        self.name_field = ft.TextField(label="Primeiro nome", width=300, hint_text="Ex.: João")
        self.last_name_field = ft.TextField(label="Sobrenome", width=300, hint_text="Ex.: Silva")
        self.username_field = ft.TextField(label="Usuário", width=300, hint_text="Ex.: joao.silva")
        self.email_field = ft.TextField(label="E-mail", width=300, hint_text="Ex.: joao@exemplo.com")
        self.password_field = ft.TextField(label="Senha", width=300, password=True, can_reveal_password=True)
        self.confirm_password_field = ft.TextField(label="Confirme a Senha", width=300, password=True, can_reveal_password=True)
        self.setor_field = ft.Dropdown(
            label="Setor",
            options=[
                ft.dropdown.Option(key="CON", text="Contagem"),
                ft.dropdown.Option(key="DIG", text="Digitação"),
                ft.dropdown.Option(key="P&D", text="Perci"),
                ft.dropdown.Option(key="SUPER", text="Supervisão"),
            ],
            width=300
        )
        # Botões
        self.register_button = ft.ElevatedButton(
            "Registrar", on_click=self.register, width=150, bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE
        )
        self.back_to_login_button = ft.TextButton(
            "Já tem uma conta? Entrar", on_click=self.back_to_login
        )
        self.error_text = ft.Text(value="", color=ft.colors.RED_600, visible=False, size=14)

        # Layout
        self.content = ft.Column(
            controls=[
                ft.Text("Registrar", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                self.name_field,
                self.last_name_field,
                self.username_field,
                self.email_field,
                self.password_field,
                self.confirm_password_field,
                self.setor_field,
                self.register_button,
                self.error_text,
                self.back_to_login_button,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            expand=True
        )
        self.padding = 20
        self.alignment = ft.alignment.center

    def show_error(self, message: str, is_success: bool = False):
        """Exibe mensagem de erro ou sucesso na UI."""
        self.error_text.value = message
        self.error_text.color = ft.colors.GREEN_600 if is_success else ft.colors.RED_600
        self.error_text.visible = True
        self.page.update()

    def validate_fields(self) -> tuple[bool, str]:
        """Valida os campos de entrada."""
        fields = {
            "Primeiro nome": self.name_field.value.strip(),
            "Sobrenome": self.last_name_field.value.strip(),
            "Usuário": self.username_field.value.strip(),
            "E-mail": self.email_field.value.strip(),
            "Senha": self.password_field.value,
            "Confirme a Senha": self.confirm_password_field.value,
        }

        for field_name, value in fields.items():
            if not value or value.strip() == "":
                return False, f"{field_name} é obrigatório!"

        # 🔹 Verifica se o setor foi selecionado corretamente
        if not self.setor_field.value:
            return False, "Setor é obrigatório!"

        # 🔹 Verifica se as senhas coincidem
        if self.password_field.value != self.confirm_password_field.value:
            return False, "As senhas não correspondem!"

        return True, ""

    async def perform_register(self):
        """Realiza o registro do usuário."""
        is_valid, error_message = self.validate_fields()
        if not is_valid:
            self.show_error(error_message)
            return

        try:
            payload = {
                "username": self.username_field.value.strip(),
                "password": self.password_field.value,
                "name": self.name_field.value.strip(),
                "last_name": self.last_name_field.value.strip(),
                "email": self.email_field.value.strip(),
                "setor": self.setor_field.value,
            }

            print(f"🔍 Enviando payload para API: {payload}")

            response = await async_api_request(
                url=f"{API_URL}/api/register/",
                method="POST",
                json_data=payload
            )

            if isinstance(response, dict) and response.get("id"):  # ✅ Verifica corretamente
                self.show_error("Registro bem-sucedido! Retornando ao login... 😊👌", is_success=True)
                await asyncio.sleep(2)
                self.app.show_login_page()
            else:
                error_msg = response.get("detail", "Erro ao registrar: resposta inesperada")
                self.show_error(error_msg)
                logger.error(f"[ERROR] Resposta da API sem confirmação de registro: {response}")

        except Exception as ex:
            logger.error(f"[ERROR] Erro ao registrar: {ex}")
            self.show_error(f"Erro ao registrar: {str(ex)}")



    def register(self, e):
        """Inicia o processo de registro de forma assíncrona."""
        logger.info("[INFO] Iniciando processo de registro...")
        self.error_text.visible = False
        self.page.run_task(self.perform_register)

    def back_to_login(self, e):
        """Retorna à página de login."""
        logger.info("[INFO] Alternando para tela de login...")
        self.app.show_login_page()