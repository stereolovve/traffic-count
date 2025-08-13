# utils/updater.py
import asyncio
import aiohttp
import os
import sys
import subprocess
import logging
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from utils.config import API_URL, APP_VERSION

logger = logging.getLogger(__name__)

class AppUpdater:
    """
    Sistema de auto-update para o aplicativo Contador Perplan
    """
    
    def __init__(self):
        self.api_url = API_URL
        self.current_version = APP_VERSION
        self.update_endpoint = f"{self.api_url}/updates/api/check-version/"
        self.download_endpoint = f"{self.api_url}/updates/api/download/"
        
        # Diretórios de trabalho
        self.app_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path.cwd()
        self.temp_dir = Path(tempfile.gettempdir()) / "contador_updates"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Estado do updater
        self.update_info = None
        self.download_progress = 0
        self.is_downloading = False
        self.is_installing = False
        
    async def check_for_updates(self, silent: bool = False) -> Dict[str, Any]:
        """
        Verifica se há atualizações disponíveis
        
        Args:
            silent: Se True, não faz log de informações normais
            
        Returns:
            Dict com informações sobre atualizações disponíveis
        """
        try:
            params = {
                'version': self.current_version,
                'platform': 'windows'
            }
            
            if not silent:
                logger.info(f"Verificando atualizações... Versão atual: {self.current_version}")
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(self.update_endpoint, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.update_info = data
                        
                        if data.get('has_update'):
                            logger.info(f"Atualização disponível: v{data['latest_version']}")
                            if data.get('update_required'):
                                logger.warning("Atualização obrigatória detectada!")
                        elif not silent:
                            logger.info("Aplicativo está atualizado")
                            
                        return data
                    else:
                        error_msg = f"Erro HTTP {response.status} ao verificar atualizações"
                        logger.error(error_msg)
                        return {'error': error_msg, 'has_update': False}
                        
        except asyncio.TimeoutError:
            error_msg = "Timeout ao verificar atualizações"
            logger.error(error_msg)
            return {'error': error_msg, 'has_update': False}
        except Exception as e:
            error_msg = f"Erro ao verificar atualizações: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg, 'has_update': False}
    
    async def download_update(self, progress_callback: Optional[callable] = None) -> bool:
        """
        Faz download da atualização
        
        Args:
            progress_callback: Função para receber progresso (0-100)
            
        Returns:
            True se download foi bem-sucedido
        """
        if not self.update_info or not self.update_info.get('has_update'):
            logger.error("Nenhuma atualização disponível para download")
            return False
        
        self.is_downloading = True
        self.download_progress = 0
        
        try:
            download_url = self.update_info['download_url']
            file_size = self.update_info.get('file_size', 0)
            version = self.update_info['latest_version']
            
            # Nome do arquivo temporário
            filename = f"ContadorPerplan_v{version}.exe"
            temp_file_path = self.temp_dir / filename
            
            logger.info(f"Iniciando download da versão {version}...")
            logger.info(f"URL: {download_url}")
            logger.info(f"Destino: {temp_file_path}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status != 200:
                        logger.error(f"Erro no download: HTTP {response.status}")
                        return False
                    
                    # Obter tamanho real do arquivo se não foi fornecido
                    if not file_size:
                        file_size = int(response.headers.get('content-length', 0))
                    
                    downloaded = 0
                    
                    with open(temp_file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Atualizar progresso
                            if file_size > 0:
                                self.download_progress = int((downloaded / file_size) * 100)
                                if progress_callback:
                                    progress_callback(self.download_progress)
            
            # Verificar se arquivo foi baixado corretamente
            if temp_file_path.exists() and temp_file_path.stat().st_size > 0:
                logger.info(f"Download concluído: {temp_file_path}")
                self.update_info['local_file'] = str(temp_file_path)
                return True
            else:
                logger.error("Arquivo baixado está corrompido ou vazio")
                return False
                
        except Exception as e:
            logger.error(f"Erro durante download: {str(e)}")
            return False
        finally:
            self.is_downloading = False
    
    def install_update(self) -> bool:
        """
        Instala a atualização baixada
        
        Returns:
            True se instalação foi iniciada com sucesso
        """
        if not self.update_info or not self.update_info.get('local_file'):
            logger.error("Nenhum arquivo de atualização disponível")
            return False
        
        try:
            self.is_installing = True
            local_file = Path(self.update_info['local_file'])
            
            if not local_file.exists():
                logger.error(f"Arquivo de atualização não encontrado: {local_file}")
                return False
            
            logger.info(f"Iniciando instalação da atualização...")
            
            # Criar script de atualização
            update_script = self._create_update_script(local_file)
            
            # Executar script de atualização
            subprocess.Popen([update_script], shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            
            logger.info("Instalação iniciada. O aplicativo será reiniciado...")
            return True
            
        except Exception as e:
            logger.error(f"Erro durante instalação: {str(e)}")
            return False
        finally:
            self.is_installing = False
    
    def _create_update_script(self, new_exe_path: Path) -> str:
        """
        Cria script batch para realizar a atualização
        
        Args:
            new_exe_path: Caminho para o novo executável
            
        Returns:
            Caminho para o script de atualização
        """
        current_exe = Path(sys.executable)
        backup_exe = current_exe.parent / f"{current_exe.stem}_backup.exe"
        script_path = self.temp_dir / "update.bat"
        
        # Script batch para atualização
        script_content = f"""@echo off
echo Aplicando atualização do Contador Perplan...

REM Aguardar fechamento do aplicativo
timeout /t 3 /nobreak >nul

REM Fazer backup do executável atual
if exist "{current_exe}" (
    echo Fazendo backup...
    copy /y "{current_exe}" "{backup_exe}" >nul
)

REM Substituir executável
echo Instalando nova versão...
copy /y "{new_exe_path}" "{current_exe}" >nul

if %errorlevel% equ 0 (
    echo Atualização concluída com sucesso!
    
    REM Reiniciar aplicativo
    echo Reiniciando aplicativo...
    start "" "{current_exe}"
    
    REM Limpar arquivos temporários
    timeout /t 2 /nobreak >nul
    del /q "{new_exe_path}" >nul 2>&1
    del /q "{backup_exe}" >nul 2>&1
) else (
    echo Erro na atualização! Restaurando backup...
    if exist "{backup_exe}" (
        copy /y "{backup_exe}" "{current_exe}" >nul
        del /q "{backup_exe}" >nul 2>&1
    )
    echo Pressione qualquer tecla para continuar...
    pause >nul
)

REM Auto-deletar script
del /q "%~f0" >nul 2>&1
"""
        
        # Escrever script
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return str(script_path)
    
    def rollback_update(self) -> bool:
        """
        Desfaz a última atualização usando backup
        
        Returns:
            True se rollback foi bem-sucedido
        """
        try:
            current_exe = Path(sys.executable)
            backup_exe = current_exe.parent / f"{current_exe.stem}_backup.exe"
            
            if not backup_exe.exists():
                logger.error("Arquivo de backup não encontrado")
                return False
            
            logger.info("Fazendo rollback da atualização...")
            
            # Restaurar backup
            shutil.copy2(backup_exe, current_exe)
            backup_exe.unlink()  # Remover backup
            
            logger.info("Rollback concluído com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro durante rollback: {str(e)}")
            return False
    
    async def auto_update_check(self, ui_callback: Optional[callable] = None) -> bool:
        """
        Verifica e aplica atualizações automaticamente (se configurado)
        
        Args:
            ui_callback: Função para atualizar UI com status
            
        Returns:
            True se atualização foi aplicada
        """
        try:
            if ui_callback:
                ui_callback("Verificando atualizações...")
            
            # Verificar atualizações
            update_info = await self.check_for_updates(silent=True)
            
            if update_info.get('error'):
                if ui_callback:
                    ui_callback(f"Erro: {update_info['error']}")
                return False
            
            if not update_info.get('has_update'):
                if ui_callback:
                    ui_callback("Aplicativo atualizado")
                return False
            
            # Atualização disponível
            version = update_info['latest_version']
            is_required = update_info.get('update_required', False)
            
            if ui_callback:
                status = "Atualização obrigatória" if is_required else "Atualização disponível"
                ui_callback(f"{status}: v{version}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro em auto_update_check: {str(e)}")
            if ui_callback:
                ui_callback(f"Erro na verificação: {str(e)}")
            return False
    
    def get_update_status(self) -> Dict[str, Any]:
        """
        Retorna o status atual do sistema de atualizações
        
        Returns:
            Dict com informações de status
        """
        return {
            'current_version': self.current_version,
            'update_available': self.update_info.get('has_update', False) if self.update_info else False,
            'latest_version': self.update_info.get('latest_version') if self.update_info else None,
            'is_downloading': self.is_downloading,
            'download_progress': self.download_progress,
            'is_installing': self.is_installing,
            'update_required': self.update_info.get('update_required', False) if self.update_info else False
        }
    
    def cleanup_temp_files(self):
        """
        Limpa arquivos temporários de atualizações
        """
        try:
            if self.temp_dir.exists():
                for file_path in self.temp_dir.glob("*"):
                    if file_path.is_file():
                        file_path.unlink()
                        logger.debug(f"Removido: {file_path}")
                logger.info("Arquivos temporários limpos")
        except Exception as e:
            logger.error(f"Erro ao limpar arquivos temporários: {str(e)}")

# Instância global do updater
app_updater = AppUpdater()