#main.py
import flet as ft
import logging
import traceback
from dotenv import load_dotenv
import os
import json
import asyncio
from pathlib import Path
import sys
from datetime import datetime
from app.contador import ContadorPerplan
from utils.config import API_URL, EXCEL_BASE_DIR, DESKTOP_DIR, LOG_FILE, AUTH_TOKENS_FILE, APP_VERSION
from utils.api import async_api_request
from utils.updater import app_updater
from loginregister.register import RegisterPage
from loginregister.login import LoginPage
from utils.diagnostic import run_quick_diagnostic
from utils.logging_config import setup_application_logging

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

# Setup enhanced logging system
try:
    # Determine if we're in debug mode
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Setup application logging
    app_logger = setup_application_logging(
        app_name="contador_perplan",
        debug_mode=debug_mode
    )
    
    main_logger = logging.getLogger('main')
    main_logger.info("=== APPLICATION STARTUP ===")
    main_logger.info(f"App Version: {APP_VERSION}")
    main_logger.info(f"Debug Mode: {debug_mode}")
    
except Exception as e:
    print(f"Failed to setup enhanced logging: {e}")
    # Fallback to basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s:%(funcName)s - %(message)s"
    )
    main_logger = logging.getLogger('main')
    main_logger.warning("Using fallback logging configuration")

class MyApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.tokens = None
        self.username = None
        self.user_preferences = {}
        self.contador = None
        self.initialization_attempts = 0
        self.max_initialization_attempts = 2  # Reduced from 3 to 2
        
        # Setup global error handler
        self.setup_error_handling()
    
    def setup_error_handling(self):
        """Setup global error handling for the application"""
        try:
            # Setup exception handler for asyncio
            loop = asyncio.get_event_loop()
            loop.set_exception_handler(self._handle_async_exception)
        except RuntimeError:
            # No event loop running yet, will be setup later
            pass
    
    def _handle_async_exception(self, loop, context):
        """Handle uncaught asyncio exceptions"""
        exc = context.get('exception')
        if exc:
            main_logger.error(f"Uncaught async exception: {exc}")
            main_logger.error(f"Context: {context}")
            
            # Show error to user if possible
            if hasattr(self, 'page') and self.page:
                try:
                    self.show_error_snackbar(f"Erro interno: {str(exc)[:100]}")
                except:
                    pass  # Don't fail if UI is not available
    
    def show_error_snackbar(self, message: str, duration: int = 5000):
        """Show error message to user"""
        try:
            if self.page:
                snackbar = ft.SnackBar(
                    content=ft.Text(message),
                    bgcolor=ft.Colors.RED,
                    duration=duration
                )
                self.page.show_snack_bar(snackbar)
        except Exception as e:
            main_logger.error(f"Failed to show error snackbar: {e}")
    
    async def safe_initialize(self):
        """Simplified initialization with silent retry"""
        self.initialization_attempts += 1
        
        try:
            # Quick diagnostic check
            quick_diag = run_quick_diagnostic()
            if not quick_diag.get('overall', False):
                main_logger.warning("Quick diagnostic failed, but continuing")
            
            # Initialize database with retry
            from database.models import init_db
            if not init_db():
                main_logger.error("Database initialization failed")
                if self.initialization_attempts < self.max_initialization_attempts:
                    return await self.safe_initialize()  # Silent retry
                else:
                    self._show_critical_error("Falha na inicialização da base de dados")
                    return False
            
            # Proceed with authentication flow
            if self.load_tokens() and await self.verificar_token():
                await self.switch_to_main_app()
            else:
                self.show_login_page()
                
            return True
                
        except Exception as e:
            main_logger.error(f"Critical error during initialization: {e}")
            main_logger.error(f"Traceback: {traceback.format_exc()}")
            
            if self.initialization_attempts < self.max_initialization_attempts:
                return await self.safe_initialize()  # Silent retry
            else:
                self._show_critical_error(f"Erro crítico na inicialização: {str(e)}")
                return False
    
    
    def _show_critical_error(self, message: str):
        """Show critical error screen"""
        try:
            error_content = ft.Column([
                ft.Icon(ft.Icons.ERROR, size=64, color=ft.Colors.RED),
                ft.Text("Erro Crítico", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                ft.Text(message, size=16, text_align=ft.TextAlign.CENTER),
                ft.Divider(),
                ft.Text("Possíveis soluções:", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("• Reinicie o aplicativo", size=12),
                ft.Text("• Verifique as permissões de arquivo", size=12),
                ft.Text("• Execute como administrador", size=12),
                ft.Text("• Entre em contato com o suporte", size=12),
                ft.Container(height=20),
                ft.ElevatedButton(
                    "Tentar Novamente",
                    on_click=self._retry_initialization,
                    bgcolor=ft.Colors.BLUE
                ),
                ft.TextButton(
                    "Sair",
                    on_click=lambda e: self.page.window_close()
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.page.views.clear()
            self.page.views.append(
                ft.View(
                    "/error",
                    [ft.Container(
                        content=error_content,
                        alignment=ft.alignment.center,
                        expand=True,
                        padding=40
                    )],
                    padding=20,
                )
            )
            
            self.page.update()
            
        except Exception as e:
            main_logger.error(f"Failed to show critical error screen: {e}")
            # Last resort - just exit
            print(f"CRITICAL ERROR: {message}")
            print("Application will exit.")
    
    def _retry_initialization(self, e=None):
        """Retry initialization after error"""
        if self.initialization_attempts < self.max_initialization_attempts:
            main_logger.info(f"Retrying initialization (attempt {self.initialization_attempts + 1})")
            self.page.run_task(self.safe_initialize)
        else:
            main_logger.error(f"Maximum initialization attempts ({self.max_initialization_attempts}) exceeded")
            self._show_critical_error("Número máximo de tentativas excedido. Reinicie o aplicativo.")

    async def load_user_preferences(self, timeout: float = 10.0):
        try:
            headers = {"Authorization": f"Bearer {self.tokens['access']}"}
            
            # Implement timeout using asyncio.wait_for
            response = await asyncio.wait_for(
                async_api_request("GET", "/padroes/user/preferences/", headers=headers),
                timeout=timeout
            )
            
            self.user_preferences = response
            # Remove verbose success log
        except asyncio.TimeoutError:
            # Silent timeout handling
            self.user_preferences = {}  # Use empty preferences as fallback
        except Exception as ex:
            main_logger.error(f"Erro ao carregar preferências: {ex}")
            self.user_preferences = {}  # Use empty preferences as fallback

    async def verificar_token(self, timeout: float = 15.0):
        if not self.tokens or 'access' not in self.tokens:
            print("[ERRO] Nenhum token disponível!")
            return False
        try:
            headers = {"Authorization": f"Bearer {self.tokens['access']}"}
            
            # Implement timeout for token verification
            response = await asyncio.wait_for(
                async_api_request("GET", "/padroes/user/info/", headers=headers),
                timeout=timeout
            )

            if "error" in response:
                print(f"[ERRO] Token inválido! Erro: {response['error']}")
                return False

            # Atualizar o username com os dados mais recentes do servidor
            if "username" in response:
                old_username = self.username
                self.username = response["username"]
                print(f"[OK] Username atualizado do servidor: {self.username}")
                
                # Se o username mudou, salvar os tokens atualizados
                if old_username != self.username:
                    self.save_tokens()
                    print(f"[OK] Username atualizado de '{old_username}' para '{self.username}' e salvo nos tokens")

            # Remove verbose success log
            return True

        except asyncio.TimeoutError:
            # Silent timeout handling
            return False
        except Exception as ex:
            main_logger.error(f"Erro ao verificar token: {ex}")
            return False

    def save_tokens(self):
        try:
            # Salvar tokens junto com o username atualizado
            tokens_data = {
                "access": self.tokens.get("access"),
                "username": self.username,
                "refresh": self.tokens.get("refresh", "")  # Adicionar refresh se disponível
            }
            with open(AUTH_TOKENS_FILE, "w") as f:
                json.dump(tokens_data, f)
            logging.info(f"[OK] Tokens e username salvos em: {AUTH_TOKENS_FILE}")
            logging.info(f"[OK] Username salvo: {self.username}")
        except Exception as ex:
            logging.error(f"[ERRO] Erro ao salvar tokens: {ex}")

    def load_tokens(self):
        if AUTH_TOKENS_FILE.exists():
            try:
                with open(AUTH_TOKENS_FILE, "r") as f:
                    saved_data = json.load(f)
                # Carregar tokens e username do arquivo
                self.tokens = {
                    "access": saved_data.get("access"),
                    "refresh": saved_data.get("refresh", "")
                }
                self.username = saved_data.get("username")
                logging.info(f"[OK] Tokens carregados de: {AUTH_TOKENS_FILE}")
                logging.info(f"[OK] Username carregado: {self.username}")
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
            
            # Carregar preferências do usuário
            await self.load_user_preferences()
            
            # Atualizar binds (a verificação de sessão ativa será feita automaticamente pelo contador)
            await self.contador.atualizar_binds()
            
            # Verificar atualizações em background (não bloqueia a interface)
            self.page.run_task(self.check_for_updates)
            
            self.page.update()
            
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao mudar para app principal: {ex}")

    async def check_for_updates(self):
        """Verifica se há atualizações disponíveis e notifica o usuário"""
        try:
            logging.info("Verificando atualizações disponíveis...")
            
            # Verificar atualizações
            update_info = await app_updater.check_for_updates(silent=True)
            
            if update_info.get('error'):
                logging.warning(f"Erro ao verificar atualizações: {update_info['error']}")
                return
            
            if not update_info.get('has_update'):
                logging.info("Aplicativo está atualizado")
                return
            
            # Atualização disponível
            latest_version = update_info['latest_version']
            is_required = update_info.get('update_required', False)
            changelog = update_info.get('changelog', 'Melhorias e correções')
            
            logging.info(f"Atualização disponível: v{latest_version}")
            
            # Mostrar notificação no snackbar
            if self.page and hasattr(self.page, 'show_snack_bar'):
                update_type = "Atualização Obrigatória" if is_required else "Nova Versão"
                message = f"{update_type} v{latest_version} disponível!"
                
                snack_bar = ft.SnackBar(
                    content=ft.Text(message),
                    action=ft.TextButton("Atualizar", on_click=lambda e: self.page.run_task(self.show_update_dialog)),
                    action_color=ft.colors.BLUE,
                    duration=10000,  # 10 segundos
                    bgcolor=ft.colors.ORANGE if is_required else ft.colors.BLUE,
                )
                
                self.page.show_snack_bar(snack_bar)
            
        except Exception as ex:
            logging.error(f"Erro ao verificar atualizações: {ex}")

    async def show_update_dialog(self):
        """Mostra dialog para confirmar atualização"""
        try:
            if not app_updater.update_info:
                return
            
            update_info = app_updater.update_info
            latest_version = update_info['latest_version']
            changelog = update_info.get('changelog', 'Melhorias e correções')
            is_required = update_info.get('update_required', False)
            file_size = update_info.get('file_size', 0)
            size_mb = round(file_size / (1024 * 1024), 1) if file_size > 0 else '?'
            
            # Criar dialog de atualização
            dialog_content = ft.Column([
                ft.Text(
                    f"Nova Versão Disponível: v{latest_version}",
                    size=18,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Text(f"Versão atual: v{app_updater.current_version}"),
                ft.Text(f"Tamanho: {size_mb} MB"),
                ft.Divider(),
                ft.Text("Novidades:", weight=ft.FontWeight.BOLD),
                ft.Text(changelog, selectable=True),
                ft.Divider(),
                ft.Text(
                    "⚠️ Esta atualização é obrigatória!" if is_required else "Recomendamos manter o aplicativo sempre atualizado.",
                    color=ft.colors.ORANGE if is_required else ft.colors.BLUE
                ),
            ])
            
            def handle_update(e):
                dialog.open = False
                self.page.update()
                self.page.run_task(self.perform_update)
            
            def handle_later(e):
                if not is_required:
                    dialog.open = False
                    self.page.update()
            
            actions = [
                ft.TextButton("Atualizar Agora", on_click=handle_update),
            ]
            
            if not is_required:
                actions.append(ft.TextButton("Mais Tarde", on_click=handle_later))
            
            dialog = ft.AlertDialog(
                title=ft.Text("Atualização Disponível"),
                content=dialog_content,
                actions=actions,
                modal=True,
            )
            
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()
            
        except Exception as ex:
            logging.error(f"Erro ao mostrar dialog de atualização: {ex}")

    async def perform_update(self):
        """Executa o processo de atualização"""
        try:
            # Mostrar dialog de progresso
            progress_bar = ft.ProgressBar(value=0, width=300)
            status_text = ft.Text("Preparando download...")
            
            progress_dialog = ft.AlertDialog(
                title=ft.Text("Atualizando..."),
                content=ft.Column([
                    status_text,
                    progress_bar,
                    ft.Text("Não feche o aplicativo durante a atualização.", size=12, color=ft.colors.ORANGE)
                ]),
                modal=True,
            )
            
            self.page.dialog = progress_dialog
            progress_dialog.open = True
            self.page.update()
            
            # Callback para atualizar progresso
            def update_progress(percent):
                progress_bar.value = percent / 100
                status_text.value = f"Baixando... {percent}%"
                self.page.update()
            
            # Fazer download
            status_text.value = "Baixando atualização..."
            self.page.update()
            
            success = await app_updater.download_update(progress_callback=update_progress)
            
            if not success:
                status_text.value = "Erro no download!"
                status_text.color = ft.colors.RED
                self.page.update()
                await asyncio.sleep(3)
                progress_dialog.open = False
                self.page.update()
                return
            
            # Instalar atualização
            status_text.value = "Instalando..."
            progress_bar.value = 1.0
            self.page.update()
            
            install_success = app_updater.install_update()
            
            if install_success:
                status_text.value = "Reiniciando aplicativo..."
                self.page.update()
                await asyncio.sleep(2)
                
                # Fechar aplicativo (o script de atualização cuidará do restart)
                self.page.window_close()
            else:
                status_text.value = "Erro na instalação!"
                status_text.color = ft.colors.RED
                self.page.update()
                await asyncio.sleep(3)
                progress_dialog.open = False
                self.page.update()
            
        except Exception as ex:
            logging.error(f"Erro durante atualização: {ex}")
            if hasattr(self, 'page') and self.page.dialog:
                self.page.dialog.open = False
                self.page.update()

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
            self.page.window.height = 700
            
            self.page.update()
            
        except Exception as ex:
            logging.error(f"Erro ao mudar para tela de login: {ex}")

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
            self.page.window.height = 700
            
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
    """Main entry point with enhanced error handling"""
    try:
        main_logger.info("=== STARTING MAIN APPLICATION ===")
        
        # Configure page
        page.title = "Contador Perplan"
        page.window.width = 800
        page.window.height = 700
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

        # Create app instance
        app = MyApp(page)
        
        # Setup exception handler for the event loop
        try:
            loop = asyncio.get_event_loop()
            loop.set_exception_handler(app._handle_async_exception)
        except:
            pass  # Already set or no loop
        
        # Use safe initialization
        success = await app.safe_initialize()
        
        if success:
            main_logger.info("Application started successfully")
    
    except Exception as e:
        main_logger.critical(f"Critical error in main: {e}")
        main_logger.critical(f"Traceback: {traceback.format_exc()}")
        
        try:
            # Show critical error if page is available
            page.views.clear()
            error_view = ft.View(
                "/critical_error",
                [ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.ERROR, size=64, color=ft.Colors.RED),
                        ft.Text("Erro Crítico na Inicialização", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Erro: {str(e)}", size=14, text_align=ft.TextAlign.CENTER),
                        ft.Container(height=20),
                        ft.Text("O aplicativo não pode continuar.", size=12),
                        ft.Container(height=20),
                        ft.ElevatedButton(
                            "Fechar",
                            on_click=lambda e: page.window_close(),
                            bgcolor=ft.Colors.RED
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    expand=True,
                    padding=40
                )],
                padding=20
            )
            page.views.append(error_view)
            page.update()
        except:
            # Last resort
            print(f"CRITICAL ERROR: {e}")
            print("Application cannot start. Check logs for details.")

def run_application():
    """Run the application with global exception handling"""
    try:
        main_logger.info("=== INITIALIZING FLET APPLICATION ===")
        
        # Check if assets directory exists
        assets_dir = "assets"
        if not os.path.exists(assets_dir):
            main_logger.warning(f"Assets directory not found: {assets_dir}")
            assets_dir = None
        
        # Run Flet application
        ft.app(target=main, assets_dir=assets_dir)
        
    except Exception as e:
        main_logger.critical(f"Failed to start Flet application: {e}")
        main_logger.critical(f"Traceback: {traceback.format_exc()}")
        print(f"CRITICAL ERROR: Cannot start application - {e}")
        print("Check the log file for more details.")

if __name__ == "__main__":
    run_application()