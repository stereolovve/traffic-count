#main.py
import flet as ft
import logging
from dotenv import load_dotenv
import os
import json
import asyncio
from pathlib import Path
from app.contador import ContadorPerplan
from utils.config import API_URL, EXCEL_BASE_DIR, DESKTOP_DIR, LOG_FILE, AUTH_TOKENS_FILE
from utils.api import async_api_request
from loginregister.register import RegisterPage

from loginregister.login import LoginPage

load_dotenv()

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

class MyApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.tokens = None
        self.username = None
        self.user_preferences = {}
        self.contador = None

    async def load_user_preferences(self):
        if not self.tokens:
            logging.warning("❌ Nenhum token encontrado. Preferências não carregadas.")
            return
        try:
            headers = {"Authorization": f"Bearer {self.tokens['access']}"}
            response = await async_api_request(f"{API_URL}/padroes/user/preferences/", headers=headers)
            
            self.user_preferences = response
            logging.info("✅ Preferências carregadas com sucesso!")
        except Exception as ex:
            logging.error(f"Erro ao carregar preferências: {ex}")

    async def verificar_token(self):
        if not self.tokens or 'access' not in self.tokens:
            print("❌ Nenhum token disponível!")
            return False
        try:
            headers = {"Authorization": f"Bearer {self.tokens['access']}"}
            response = await async_api_request(f"{API_URL}/padroes/user/info/", headers=headers)

            if "error" in response:
                print(f"❌ Token inválido! Erro: {response['error']}")
                return False

            print("✅ Token válido! Dados do usuário:", response)
            return True

        except Exception as ex:
            logging.error(f"Erro ao verificar token: {ex}")
            return False

    def save_tokens(self):
        try:
            with open(AUTH_TOKENS_FILE, "w") as f:
                json.dump({"access": self.tokens.get("access"), "username": self.username}, f)
            logging.info(f"✅ Tokens salvos em: {AUTH_TOKENS_FILE}")
        except Exception as ex:
            logging.error(f"❌ Erro ao salvar tokens: {ex}")

    def load_tokens(self):
        if AUTH_TOKENS_FILE.exists():
            try:
                with open(AUTH_TOKENS_FILE, "r") as f:
                    saved_data = json.load(f)
                self.tokens = {"access": saved_data.get("access")}
                self.username = saved_data.get("username")
                logging.info(f"🔑 Tokens carregados de: {AUTH_TOKENS_FILE}")
                return True
            except (json.JSONDecodeError, ValueError, KeyError) as ex:
                logging.error(f"❌ Erro ao carregar tokens: {ex}")
                AUTH_TOKENS_FILE.unlink()
        return False

    async def switch_to_main_app(self):
        try:
            self.page.views.clear()
            self.contador = ContadorPerplan(self.page, self.username, self)
            self.page.views.append(
                ft.View(
                    "/",
                    [self.contador],
                    padding=20,
                    scroll=ft.ScrollMode.AUTO,
                )
            )
            self.page.window.min_width = 800
            self.page.window.min_height = 600
            self.page.scroll = ft.ScrollMode.AUTO
            self.page.expand = True
            
            await self.contador.atualizar_binds()
            self.page.update()
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao mudar para app principal: {ex}")

    def show_login_page(self):
        self.page.controls.clear()
        login_page = LoginPage(self)
        self.page.add(login_page)
        self.page.window.width = 400 
        self.page.window.height = 500
        self.page.window.center()
        self.page.update()

    def show_register_page(self):
        self.page.controls.clear()
        self.page.add(RegisterPage(self))
        self.page.update()

    def reset_app(self):
        self.tokens = None
        self.username = None
        if not self.page:
            logging.error("Página não está configurada ao tentar resetar o app.")
            return
        self.page.controls.clear()
        self.show_login_page()

    def load_active_session(self):
        if not self.contador:
            self.contador = ContadorPerplan(self.page, username=self.username, app=self)
        return self.contador.load_active_session()
         
async def main(page: ft.Page):
    page.title = "Contador Perplan"
    page.window.width = 800
    page.window.height = 600
    page.window.min_width = 800
    page.window.min_height = 600
    page.window.always_on_top = True
    page.scroll = ft.ScrollMode.AUTO
    page.expand = True
    page.window.center()
    
    page.theme = ft.Theme(
        scrollbar_theme=ft.ScrollbarTheme(
            thickness=10,
            radius=5,
            main_axis_margin=2,
            cross_axis_margin=2,
        )
    )

    app = MyApp(page)

    if app.load_tokens():
        if await app.verificar_token():
            await app.switch_to_main_app()
            return
        else:
            print("❌ Token inválido!")
            app.show_login_page()
    else:
        app.show_login_page()

ft.app(target=main, assets_dir="assets")
