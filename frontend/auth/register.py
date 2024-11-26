
import flet as ft
import httpx

class RegisterPage(ft.Container):
    def __init__(self, app):
        self.app = app
        super().__init__()

        # Campos de entrada
        self.name_field = ft.TextField(label="Primeiro nome", width=300)
        self.last_name_field = ft.TextField(label="Ultimo nome", width=300)
        self.username_field = ft.TextField(label="Usuário (Coloque seunome.seunobrenome)", width=300)
        self.email_field = ft.TextField(label="E-mail", width=300)
        self.password_field = ft.TextField(label="Senha", password=True, width=300)
        self.confirm_password_field = ft.TextField(label="Confirme a Senha", password=True, width=300)

        # Menu suspenso para selecionar o setor
        self.setor_field = ft.Dropdown(
            label="Setor",
            options=[
                ft.dropdown.Option("CON", "Contagem"),
                ft.dropdown.Option("DIG", "Digitação"),
                ft.dropdown.Option("P&D", "Perci"),
                ft.dropdown.Option("SUPER", "Supervisao"),
            ],
            width=300
        )

        # Botões
        self.register_button = ft.ElevatedButton("Registrar", on_click=self.register)
        self.error_text = ft.Text(value="", color="red", visible=False)
        self.back_to_login_button = ft.TextButton("Já tem uma conta? Entrar", on_click=self.back_to_login)

        # Adicionar os controles ao Container
        self.content = ft.Container(
            ft.Column(
            [
                ft.Text("Registrar", size=20, weight="bold"),
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
        ),
            border_radius=10,  # Borda arredondada
            width=800,  # Largura fixa para centralizar
            height=600  # Altura fixa
            
            )

    def register(self, e):
        # Capturar valores dos campos
        name = self.name_field.value
        last_name = self.last_name_field.value
        username = self.username_field.value
        email = self.email_field.value
        password = self.password_field.value
        confirm_password = self.confirm_password_field.value
        setor = self.setor_field.value

        # Validar os campos
        if not all([name, last_name, username, email, password, confirm_password, setor]):
            self.error_text.value = "Todos os campos são obrigatórios!"
            self.error_text.visible = True
            if self.page:  # Verifique se o controle foi adicionado à página
                self.update()
            return

        if password != confirm_password:
            self.error_text.value = "As senhas não correspondem!"
            self.error_text.visible = True
            if self.page:
                self.update()
            return

        # Fazer requisição para o backend
        try:
            with httpx.Client() as client:
                response = client.post(
                    "http://3.91.159.225/api/register/",
                    json={
                        "username": username,
                        "password": password,
                        "name": name,
                        "last_name": last_name,
                        "email": email,
                        "setor": setor,
                    },
                )

            if response.status_code == 201:
                self.error_text.value = "Registro bem-sucedido! Faça login."
                self.error_text.color = "green"
                self.error_text.visible = True
                if self.page:
                    self.update()
                self.app.switch_to_main_app()
            elif response.status_code == 400:
                error_data = response.json()
                self.error_text.value = (
                    error_data.get("detail") or
                    ", ".join(f"{key}: {', '.join(value)}" for key, value in error_data.items()) or
                    "Erro ao registrar!"
                )
                self.error_text.color = "red"
                self.error_text.visible = True
                if self.page:
                    self.update()
            else:
                self.error_text.value = f"Erro {response.status_code}: {response.text}"
                self.error_text.color = "red"
                self.error_text.visible = True
                if self.page:
                    self.update()
        except httpx.RequestError as req_err:
            self.error_text.value = f"Erro de conexão: {req_err}"
            self.error_text.visible = True
            if self.page:
                self.update()
        except Exception as ex:
            self.error_text.value = f"Erro inesperado: {str(ex)}"
            self.error_text.visible = True
            if self.page:
                self.update()




    def back_to_login(self, e):
        self.app.show_login_page()
