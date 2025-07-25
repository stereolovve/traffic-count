#main.py
import flet as ft
import logging
from dotenv import load_dotenv
import os
import json
import asyncio
from pathlib import Path
import sys
from app.contador import ContadorPerplan
from utils.config import API_URL, EXCEL_BASE_DIR, DESKTOP_DIR, LOG_FILE, AUTH_TOKENS_FILE, APP_VERSION
from utils.api import async_api_request
from utils.update_checker import UpdateChecker
from loginregister.register import RegisterPage
from loginregister.login import LoginPage

load_dotenv()

# Configurar encoding para UTF-8 no Windows com verificação para None
if sys.platform == 'win32':
    try:
        if sys.stdout is not None:
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr is not None:
            sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        logging.warning("Não foi possível reconfigurar o encoding para UTF-8. Isso pode ocorrer quando executado como executável.")

# Configurar logging com encoding UTF-8
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Ignorar erros de executor após shutdown (avoid "cannot schedule new futures after shutdown")
def _ignore_executor_shutdown(loop, context):
    msg = context.get("message", "")
    if "cannot schedule new futures after shutdown" in msg:
        return
    loop.default_exception_handler(context)

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
loop.set_exception_handler(_ignore_executor_shutdown)

class MyApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.tokens = None
        self.username = None
        self.user_preferences = {}
        self.contador = None
        self.update_checker = UpdateChecker(page)

    async def load_user_preferences(self):
        try:
            headers = {"Authorization": f"Bearer {self.tokens['access']}"}
            response = await async_api_request("GET", "/padroes/user/preferences/", headers=headers)
            
            self.user_preferences = response
            logging.info("[OK] Preferências carregadas com sucesso!")
        except Exception as ex:
            logging.error(f"[ERRO] Erro ao carregar preferências: {ex}")

    async def verificar_token(self):
        if not self.tokens or 'access' not in self.tokens:
            print("[ERRO] Nenhum token disponível!")
            return False
        try:
            headers = {"Authorization": f"Bearer {self.tokens['access']}"}
            response = await async_api_request("GET", "/padroes/user/info/", headers=headers)

            if "error" in response:
                print(f"[ERRO] Token inválido! Erro: {response['error']}")
                return False

            print("[OK] Token válido! Dados do usuário:", response)
            return True

        except Exception as ex:
            logging.error(f"[ERRO] Erro ao verificar token: {ex}")
            return False

    def save_tokens(self):
        try:
            with open(AUTH_TOKENS_FILE, "w") as f:
                json.dump({"access": self.tokens.get("access"), "username": self.username}, f)
            logging.info(f"[OK] Tokens salvos em: {AUTH_TOKENS_FILE}")
        except Exception as ex:
            logging.error(f"[ERRO] Erro ao salvar tokens: {ex}")

    def load_tokens(self):
        if AUTH_TOKENS_FILE.exists():
            try:
                with open(AUTH_TOKENS_FILE, "r") as f:
                    saved_data = json.load(f)
                self.tokens = {"access": saved_data.get("access")}
                self.username = saved_data.get("username")
                logging.info(f"[OK] Tokens carregados de: {AUTH_TOKENS_FILE}")
                return True
            except (json.JSONDecodeError, ValueError, KeyError) as ex:
                logging.error(f"[ERRO] Erro ao carregar tokens: {ex}")
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

            self.page.scroll = ft.ScrollMode.AUTO
            self.page.expand = True
            
            await self.contador.atualizar_binds()
            self.page.update()
            
            # Verificar atualizações disponíveis após carregar a interface principal
            self.page.run_task(self.check_for_updates)
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao mudar para app principal: {ex}")
            
    async def check_for_updates(self):
        """Verifica se há atualizações disponíveis"""
        try:
            # Aguarda um pouco para não sobrecarregar a inicialização
            await asyncio.sleep(3)
            logging.info(f"Verificando atualizações. Versão atual: {APP_VERSION}")
            await self.update_checker.check_for_updates()
        except Exception as e:
            logging.error(f"Erro ao verificar atualizações: {str(e)}")
            # Não exibe erro ao usuário para não atrapalhar a experiência

    def show_login_page(self):
        """Mostra a página de login usando a abordagem de views"""
        try:
            self.page.run_task(self._perform_switch_to_login)
        except Exception as ex:
            logging.error(f"Erro ao mostrar página de login: {ex}")
            self.page.controls.clear()
            login_page = LoginPage(self)
            self.page.add(login_page)
            self.page.update()

    def show_register_page(self):
        """Mostra a página de registro usando a abordagem de views"""
        try:
            self.page.views.clear()
            
            register_page = RegisterPage(self)
            self.page.views.append(
                ft.View(
                    "/register",
                    [register_page],
                    padding=20,
                    scroll=ft.ScrollMode.AUTO,
                )
            )
            
            self.page.update()
        except Exception as ex:
            logging.error(f"Erro ao mostrar página de registro: {ex}")
            self.page.controls.clear()
            self.page.add(RegisterPage(self))
            self.page.update()

    def reset_app(self):
        """Reset o estado da aplicação e volta para a tela de login"""
        try:
            if AUTH_TOKENS_FILE.exists():
                AUTH_TOKENS_FILE.unlink()
                logging.info("Arquivo de tokens removido")
            
            self.tokens = None
            self.username = None
            
            self.page.run_task(self._perform_switch_to_login)
            
        except Exception as ex:
            logging.error(f"Erro ao resetar aplicação: {ex}")
            self.page.controls.clear()
            self.page.add(ft.Text("Erro ao fazer logout. Reinicie a aplicação."))
            self.page.update()

    async def _perform_switch_to_login(self):
        """Implementação assíncrona da mudança para login"""
        try:
            self.page.views.clear()
            
            login_page = LoginPage(self)
            self.page.views.append(
                ft.View(
                    "/login",
                    [login_page],
                    padding=20,
                    scroll=ft.ScrollMode.AUTO,
                )
            )
            
            self.page.window.width = 800
            self.page.window.height = 600
            
            self.page.update()
            
        except Exception as ex:
            logging.error(f"Erro ao mudar para tela de login: {ex}")

    def load_active_session(self):
        if not self.contador:
            self.contador = ContadorPerplan(self.page, username=self.username, app=self)
        return self.contador.load_active_session()

    async def switch_to_login_page(self):
        """Muda o aplicativo para a tela de login"""
        try:
            # Limpar todas as views existentes
            self.page.views.clear()
            
            # Limpar dados de autenticação
            self.tokens = None
            self.username = None
            
            # Criar e configurar a view de login
            login_page = LoginPage(self)
            self.page.views.append(
                ft.View(
                    "/login",
                    [login_page],
                    padding=20,
                    scroll=ft.ScrollMode.AUTO,
                )
            )
            
            # Ajustar o tamanho da janela
            self.page.window.width = 800
            self.page.window.height = 600
            
            # Atualizar a página
            self.page.update()
            
        except Exception as ex:
            logging.error(f"Erro ao mudar para tela de login: {ex}")
         
    async def _perform_switch_to_register(self):
        """Implementação assíncrona da mudança para registro"""
        try:
            # Limpar todas as views existentes
            self.page.views.clear()
            
            # Criar e configurar a view de registro
            register_page = RegisterPage(self)
            self.page.views.append(
                ft.View(
                    "/register",
                    [register_page],
                    padding=20,
                    scroll=ft.ScrollMode.AUTO,
                )
            )
            
            # Atualizar a página
            self.page.update()
            
        except Exception as ex:
            logging.error(f"Erro ao mudar para tela de registro: {ex}")

async def main(page: ft.Page):
    page.title = "Contador Perplan"
    page.window.width = 800
    page.window.height = 600

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
