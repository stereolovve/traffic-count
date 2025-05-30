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

        self.name_field = ft.TextField(
            label="Primeiro nome", 
            width=300, 
            hint_text="Ex.: João",
            on_change=self.update_username
        )
        
        self.last_name_field = ft.TextField(
            label="Sobrenome", 
            width=300, 
            hint_text="Ex.: Silva",
            on_change=self.update_username
        )
        
        self.username_field = ft.TextField(
            label="Usuário", 
            width=300, 
            hint_text="Ex.: joao.silva",
            read_only=True,
        )
        
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
        self.register_button = ft.ElevatedButton(
            "Registrar", on_click=self.register, width=150, bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE
        )
        self.back_to_login_button = ft.TextButton(
            "Já tem uma conta? Entrar", on_click=self.back_to_login
        )
        self.error_text = ft.Text(value="", color=ft.colors.RED_600, visible=False, size=14)

        self.loading_indicator = ft.ProgressRing(
            width=50,
            height=50,
            visible=False,
            stroke_width=6,
            color=ft.colors.BLUE_700
        )

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
                self.loading_indicator,
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
        if self.page: 
            self.error_text.value = message
            self.error_text.color = ft.colors.GREEN_600 if is_success else ft.colors.RED_600
            self.error_text.visible = True
            self.loading_indicator.visible = False
            self.page.update()
        else:
            logging.warning("Tentativa de atualizar RegisterPage com self.page inválido.")

    def validate_fields(self) -> tuple[bool, str]:
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

        if not self.setor_field.value:
            return False, "Setor é obrigatório!"

        if self.password_field.value != self.confirm_password_field.value:
            return False, "As senhas não correspondem!"

        return True, ""

    async def perform_register(self):
        is_valid, error_message = self.validate_fields()
        if not is_valid:
            self.show_error(error_message)
            return

        if self.page:
            self.loading_indicator.visible = True
            self.register_button.disabled = True
            self.page.update()
        else:
            logging.error("self.page é None durante o início do registro.")
            return

        try:
            payload = {
                "username": self.username_field.value.strip(),
                "password": self.password_field.value,
                "name": self.name_field.value.strip(),
                "last_name": self.last_name_field.value.strip(),
                "email": self.email_field.value.strip(),
                "setor": self.setor_field.value,
                "password1": self.password_field.value,
                "password2": self.confirm_password_field.value,
            }
            logger.debug(f"Register payload: {payload}")

            response = await async_api_request(
                "POST",
                "/auth/register/",
                data=payload
            )

            if isinstance(response, dict) and response.get("id"):
                self.show_error("Registro bem-sucedido! Retornando ao login... 😊👌", is_success=True)
                await asyncio.sleep(2)
                self.page.run_task(self.app._perform_switch_to_login)
            else:
                # Exibir detalhe ou mensagem de erro vinda da API
                error_msg = response.get("detail") or response.get("erro") or "Erro ao registrar: resposta inesperada"
                self.show_error(error_msg)
                logger.error(f"[ERROR] Resposta da API sem confirmação de registro: {response}")

        except Exception as ex:
            logger.error(f"[ERROR] Erro ao registrar: {ex}")
            self.show_error(f"Erro ao registrar: {str(ex)}")
        finally:
            if self.page:
                self.loading_indicator.visible = False
                self.register_button.disabled = False
                self.page.update()
            else:
                logging.warning("self.page é None no finally do registro.")

    def register(self, e):
        logger.info("[INFO] Iniciando processo de registro...")
        self.error_text.visible = False
        if self.page:
            self.page.run_task(self.perform_register)
        else:
            logging.error("self.page é None ao iniciar o registro.")

    def back_to_login(self, e):
        logger.info("[INFO] Alternando para tela de login...")
        self.page.run_task(self.app._perform_switch_to_login)

    def update_username(self, e):
        """Atualiza o campo de usuário baseado no nome e sobrenome"""
        try:
            nome = self.name_field.value.strip().lower() if self.name_field.value else ""
            sobrenome = self.last_name_field.value.strip().lower() if self.last_name_field.value else ""
            
            # Remover acentos e caracteres especiais
            nome = self.remove_special_chars(nome)
            sobrenome = self.remove_special_chars(sobrenome)
            
            # Criar o nome de usuário
            if nome and sobrenome:
                username = f"{nome}.{sobrenome}"
            elif nome:
                username = nome
            elif sobrenome:
                username = sobrenome
            else:
                username = ""
            
            # Atualizar o campo
            self.username_field.value = username
            self.page.update()
        except Exception as ex:
            logger.error(f"Erro ao atualizar nome de usuário: {ex}")

    def remove_special_chars(self, text):
        """Remove acentos e caracteres especiais de um texto"""
        import unicodedata
        import re
        
        # Normaliza para forma NFD e remove os diacríticos
        normalized = unicodedata.normalize('NFD', text)
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
        
        # Remove caracteres que não são alfanuméricos ou pontos
        normalized = re.sub(r'[^a-zA-Z0-9.]', '', normalized)
        
        return normalized