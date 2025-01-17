import flet as ft
import httpx
import json

class LoginPage(ft.Container): 
    def __init__(self, app):
        self.app = app
        super().__init__()
        self.app = app
        self.page = app.page

        self.username_field = ft.TextField(label="Usuário", width=300)
        self.password_field = ft.TextField(
            label="Senha", 
            password=True, 
            width=300, 
            on_submit=self.login  
        )
        self.remember_me_checkbox = ft.Checkbox(label="Mantenha-se conectado")
        self.login_button = ft.ElevatedButton("Entrar", on_click=self.login)
        self.register_button = ft.TextButton("Não tem uma conta? Registrar", on_click=self.show_register)
        self.error_text = ft.Text(value="", color="red", visible=False)

        self.content = ft.Container(
    content=ft.Column(
        [
            ft.Text("Login", size=30, weight="bold"),
            self.username_field,
            self.password_field,
            ft.Row(
                [
                    self.remember_me_checkbox,
                ],
                alignment=ft.MainAxisAlignment.CENTER,  
            ),
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

    def login(self, e):
        username = self.username_field.value
        password = self.password_field.value

        if not username or not password:
            self.error_text.value = "Usuário e senha são obrigatórios!"
            self.error_text.visible = True
            self.update()
            return

        try:
            with httpx.Client() as client:
                response = client.post(
                    "http://3.91.159.225/api/login/",
                    json={"username": username, "password": password},
                )

            if response.status_code == 200:
                tokens = response.json()
                self.app.tokens = tokens
                self.app.username = username
                
                if self.remember_me_checkbox.value:
                    with open("auth_tokens.json", "w") as f:
                        json.dump({"username": username, "tokens": tokens}, f)
                        
                snackbar = ft.SnackBar(ft.Text("Login realizado com sucesso!"), bgcolor="GREEN")
                self.app.page.overlay.append(snackbar)
                snackbar.open = True
                
                self.app.switch_to_main_app()
            
            elif response.status_code == 401:
                self.error_text.value = "Credenciais inválidas!"
                self.error_text.visible = True
                self.update()
            
            else:
                self.error_text.value = "Credenciais inválidas!"
                self.error_text.visible = True
                self.update()
        except Exception as ex:
            self.error_text.value = f"Erro ao conectar: {str(ex)}"
            self.error_text.visible = True
            self.update()


    def show_register(self, e):
        """Alterna para a tela de registro."""
        self.app.show_register_page()

