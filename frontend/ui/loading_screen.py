# ui/loading_screen.py
"""
Tela de carregamento com indicadores de progresso e diagnóstico
"""
import flet as ft
import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from utils.diagnostic import SystemDiagnostic, run_quick_diagnostic

# Setup logging
loading_logger = logging.getLogger('loading_screen')

class LoadingScreen(ft.Column):
    """Tela de carregamento com diagnóstico e indicadores de progresso"""
    
    def __init__(self, page: ft.Page, on_complete: Optional[Callable] = None):
        super().__init__()
        self.page = page
        self.on_complete = on_complete
        self.diagnostic = SystemDiagnostic()
        
        # UI Components
        self.progress_bar = ft.ProgressBar(value=0, width=400)
        self.status_text = ft.Text("Iniciando aplicação...", size=16)
        self.current_step_text = ft.Text("", size=14, color=ft.Colors.BLUE)
        self.detailed_log = ft.Column([], scroll=ft.ScrollMode.AUTO, height=200, visible=False)
        
        # Controls for diagnostic mode
        self.show_details_button = ft.ElevatedButton(
            "Mostrar Detalhes",
            on_click=self._toggle_details,
            visible=False
        )
        
        self.retry_button = ft.ElevatedButton(
            "Tentar Novamente",
            on_click=self._retry_initialization,
            visible=False
        )
        
        self.diagnostic_button = ft.ElevatedButton(
            "Executar Diagnóstico",
            on_click=self._run_full_diagnostic,
            visible=False
        )
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configurar interface da tela de carregamento"""
        # Logo/Title
        title = ft.Text(
            "Contador Perplan",
            size=32,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE,
            text_align=ft.TextAlign.CENTER
        )
        
        # Loading animation
        loading_ring = ft.ProgressRing(width=60, height=60, stroke_width=4)
        
        # Main content
        content = ft.Column([
            ft.Container(height=50),  # Spacer
            title,
            ft.Container(height=30),  # Spacer
            loading_ring,
            ft.Container(height=20),  # Spacer
            self.status_text,
            self.current_step_text,
            ft.Container(height=20),  # Spacer
            self.progress_bar,
            ft.Container(height=30),  # Spacer
            ft.Row([
                self.show_details_button,
                self.retry_button,
                self.diagnostic_button
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=20),  # Spacer
            self.detailed_log,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        # Main container with background
        main_container = ft.Container(
            content=content,
            padding=40,
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=ft.Colors.GREY,
                offset=ft.Offset(0, 2)
            )
        )
        
        self.controls.clear()
        self.controls.append(
            ft.Container(
                content=main_container,
                alignment=ft.alignment.center,
                expand=True,
                bgcolor=ft.Colors.BLUE_50
            )
        )
    
    async def start_initialization(self):
        """Iniciar processo de carregamento com steps"""
        loading_logger.info("Starting application initialization")
        
        steps = [
            ("Verificando sistema...", self._step_system_check, 0.1),
            ("Inicializando banco de dados...", self._step_database_init, 0.3),
            ("Verificando conectividade...", self._step_network_check, 0.5),
            ("Carregando configurações...", self._step_load_config, 0.7),
            ("Inicializando interface...", self._step_ui_init, 0.9),
            ("Finalizando...", self._step_finalize, 1.0)
        ]
        
        try:
            for step_name, step_function, progress in steps:
                await self._update_progress(step_name, progress)
                success = await step_function()
                
                if not success:
                    await self._handle_initialization_error(f"Falha em: {step_name}")
                    return False
                
                # Small delay for better UX
                await asyncio.sleep(0.5)
            
            await self._complete_initialization()
            return True
            
        except Exception as e:
            loading_logger.error(f"Initialization error: {e}")
            await self._handle_initialization_error(f"Erro inesperado: {str(e)}")
            return False
    
    async def _update_progress(self, step_name: str, progress: float):
        """Atualizar progresso na tela"""
        self.current_step_text.value = step_name
        self.progress_bar.value = progress
        
        # Add to detailed log
        log_entry = ft.Text(f"[{progress*100:.0f}%] {step_name}", size=12)
        self.detailed_log.controls.append(log_entry)
        
        # Keep log manageable
        if len(self.detailed_log.controls) > 20:
            self.detailed_log.controls.pop(0)
        
        self.page.update()
        loading_logger.info(f"Step: {step_name} ({progress*100:.0f}%)")
    
    async def _step_system_check(self) -> bool:
        """Step 1: Verificar sistema básico"""
        try:
            quick_diag = run_quick_diagnostic()
            if not quick_diag.get('filesystem', False):
                self._add_log_entry("❌ Sistema de arquivos não acessível", ft.Colors.RED)
                return False
            
            self._add_log_entry("✅ Sistema verificado", ft.Colors.GREEN)
            return True
            
        except Exception as e:
            self._add_log_entry(f"❌ Erro na verificação: {e}", ft.Colors.RED)
            return False
    
    async def _step_database_init(self) -> bool:
        """Step 2: Inicializar banco de dados"""
        try:
            from database.models import init_db
            success = init_db()
            
            if success:
                self._add_log_entry("✅ Banco de dados inicializado", ft.Colors.GREEN)
                return True
            else:
                self._add_log_entry("❌ Falha na inicialização do banco", ft.Colors.RED)
                return False
                
        except Exception as e:
            self._add_log_entry(f"❌ Erro no banco: {e}", ft.Colors.RED)
            return False
    
    async def _step_network_check(self) -> bool:
        """Step 3: Verificar conectividade"""
        try:
            import httpx
            from utils.config import API_URL
            
            if not API_URL:
                self._add_log_entry("⚠️ API URL não configurada", ft.Colors.AMBER)
                return True  # Continue without API
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    response = await client.get(f"{API_URL}/", timeout=5.0)
                    if response.status_code < 400:
                        self._add_log_entry("✅ Conectividade OK", ft.Colors.GREEN)
                        return True
                    else:
                        self._add_log_entry(f"⚠️ API retornou {response.status_code}", ft.Colors.AMBER)
                        return True  # Continue anyway
                except httpx.TimeoutException:
                    self._add_log_entry("⚠️ Timeout na API (continuando)", ft.Colors.AMBER)
                    return True  # Continue anyway
                except:
                    self._add_log_entry("⚠️ API não acessível (continuando)", ft.Colors.AMBER)
                    return True  # Continue anyway
            
        except Exception as e:
            self._add_log_entry(f"⚠️ Erro na conectividade: {e}", ft.Colors.AMBER)
            return True  # Continue anyway
    
    async def _step_load_config(self) -> bool:
        """Step 4: Carregar configurações"""
        try:
            # Load basic configuration
            from utils.config import API_URL, EXCEL_BASE_DIR, DESKTOP_DIR
            
            config_items = [
                ("API_URL", API_URL),
                ("EXCEL_BASE_DIR", EXCEL_BASE_DIR),
                ("DESKTOP_DIR", DESKTOP_DIR),
            ]
            
            for name, value in config_items:
                if value:
                    self._add_log_entry(f"✅ {name} carregado", ft.Colors.GREEN)
                else:
                    self._add_log_entry(f"⚠️ {name} não configurado", ft.Colors.AMBER)
            
            return True
            
        except Exception as e:
            self._add_log_entry(f"❌ Erro ao carregar config: {e}", ft.Colors.RED)
            return False
    
    async def _step_ui_init(self) -> bool:
        """Step 5: Inicializar interface"""
        try:
            # Simulate UI initialization
            await asyncio.sleep(0.5)
            self._add_log_entry("✅ Interface preparada", ft.Colors.GREEN)
            return True
            
        except Exception as e:
            self._add_log_entry(f"❌ Erro na UI: {e}", ft.Colors.RED)
            return False
    
    async def _step_finalize(self) -> bool:
        """Step 6: Finalizar inicialização"""
        try:
            self._add_log_entry("✅ Inicialização completa!", ft.Colors.GREEN)
            return True
            
        except Exception as e:
            self._add_log_entry(f"❌ Erro na finalização: {e}", ft.Colors.RED)
            return False
    
    def _add_log_entry(self, message: str, color: Optional[str] = None):
        """Adicionar entrada no log detalhado"""
        log_entry = ft.Text(message, size=12, color=color)
        self.detailed_log.controls.append(log_entry)
        
        # Keep log manageable
        if len(self.detailed_log.controls) > 30:
            self.detailed_log.controls.pop(0)
        
        self.page.update()
    
    async def _complete_initialization(self):
        """Finalizar inicialização com sucesso"""
        self.status_text.value = "✅ Inicialização completa!"
        self.status_text.color = ft.Colors.GREEN
        self.current_step_text.value = "Redirecionando..."
        
        self.page.update()
        
        # Wait a moment then call completion callback
        await asyncio.sleep(1)
        
        if self.on_complete:
            await self.on_complete()
    
    async def _handle_initialization_error(self, error_message: str):
        """Lidar com erros de inicialização"""
        self.status_text.value = f"❌ {error_message}"
        self.status_text.color = ft.Colors.RED
        self.current_step_text.value = "Verifique os detalhes abaixo"
        
        # Show action buttons
        self.show_details_button.visible = True
        self.retry_button.visible = True
        self.diagnostic_button.visible = True
        
        self._add_log_entry(f"❌ {error_message}", ft.Colors.RED)
        self._add_log_entry("💡 Clique em 'Executar Diagnóstico' para mais informações", ft.Colors.BLUE)
        
        self.page.update()
    
    def _toggle_details(self, e):
        """Toggle visibility of detailed log"""
        self.detailed_log.visible = not self.detailed_log.visible
        self.show_details_button.text = "Ocultar Detalhes" if self.detailed_log.visible else "Mostrar Detalhes"
        self.page.update()
    
    async def _retry_initialization(self, e):
        """Retry initialization process"""
        # Reset UI
        self.show_details_button.visible = False
        self.retry_button.visible = False
        self.diagnostic_button.visible = False
        self.detailed_log.visible = False
        self.detailed_log.controls.clear()
        
        self.status_text.color = ft.Colors.BLACK
        self.progress_bar.value = 0
        
        self.page.update()
        
        # Restart initialization
        await self.start_initialization()
    
    async def _run_full_diagnostic(self, e):
        """Execute full system diagnostic"""
        self.status_text.value = "🔍 Executando diagnóstico completo..."
        self.current_step_text.value = "Isso pode levar alguns segundos..."
        
        # Clear previous log
        self.detailed_log.controls.clear()
        self.detailed_log.visible = True
        self.show_details_button.text = "Ocultar Detalhes"
        
        self.page.update()
        
        try:
            # Run diagnostic
            results = self.diagnostic.run_full_diagnostic()
            
            # Save diagnostic report
            report_file = self.diagnostic.save_diagnostic_report()
            
            # Display summary
            summary = results.get('summary', {})
            overall_status = summary.get('overall_status', 'UNKNOWN')
            
            if overall_status == 'OK':
                self.status_text.value = "✅ Diagnóstico: Sistema OK"
                self.status_text.color = ft.Colors.GREEN
            elif overall_status == 'WARNING':
                self.status_text.value = "⚠️ Diagnóstico: Avisos encontrados"
                self.status_text.color = ft.Colors.AMBER
            else:
                self.status_text.value = "❌ Diagnóstico: Problemas encontrados"
                self.status_text.color = ft.Colors.RED
            
            self.current_step_text.value = f"Relatório salvo: {report_file}"
            
            # Display critical issues
            for issue in summary.get('critical_issues', []):
                self._add_log_entry(f"🚨 CRÍTICO: {issue}", ft.Colors.RED)
            
            # Display warnings
            for warning in summary.get('warnings', []):
                self._add_log_entry(f"⚠️ AVISO: {warning}", ft.Colors.AMBER)
            
            if overall_status == 'OK':
                self._add_log_entry("💡 Sistema parece estar funcionando corretamente", ft.Colors.GREEN)
                self._add_log_entry("💡 Se ainda tiver problemas, tente reiniciar o aplicativo", ft.Colors.BLUE)
            else:
                self._add_log_entry("💡 Verifique os problemas listados acima", ft.Colors.BLUE)
                self._add_log_entry(f"💡 Relatório completo salvo em: {report_file}", ft.Colors.BLUE)
            
        except Exception as e:
            self.status_text.value = "❌ Erro no diagnóstico"
            self.status_text.color = ft.Colors.RED
            self._add_log_entry(f"❌ Erro ao executar diagnóstico: {e}", ft.Colors.RED)
        
        self.page.update()