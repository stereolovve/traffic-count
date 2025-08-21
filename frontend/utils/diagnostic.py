# utils/diagnostic.py
"""
Sistema de diagnóstico para identificar problemas na inicialização do frontend
"""
import logging
import os
import sys
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import platform
import httpx
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
from database.models import health_check, db_path
from utils.config import API_URL, AUTH_TOKENS_FILE

# Setup diagnostic logger
diagnostic_logger = logging.getLogger('diagnostic')

class SystemDiagnostic:
    """Sistema de diagnóstico completo para o frontend"""
    
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        
    def run_full_diagnostic(self) -> Dict[str, Any]:
        """Execute diagnóstico completo do sistema"""
        diagnostic_logger.info("=== INICIANDO DIAGNÓSTICO COMPLETO ===")
        
        # System information
        self.results['system'] = self._check_system_info()
        
        # Environment checks
        self.results['environment'] = self._check_environment()
        
        # Database checks
        self.results['database'] = self._check_database()
        
        # Network/API checks
        self.results['network'] = asyncio.run(self._check_network())
        
        # File system checks
        self.results['filesystem'] = self._check_filesystem()
        
        # Resource checks
        self.results['resources'] = self._check_resources()
        
        # Summary
        self.results['summary'] = self._generate_summary()
        self.results['timestamp'] = datetime.now().isoformat()
        self.results['duration'] = time.time() - self.start_time
        
        diagnostic_logger.info(f"=== DIAGNÓSTICO COMPLETO EM {self.results['duration']:.2f}s ===")
        return self.results
    
    def _check_system_info(self) -> Dict[str, Any]:
        """Verificar informações do sistema"""
        try:
            return {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': sys.version,
                'working_directory': os.getcwd(),
                'executable_path': sys.executable,
                'is_frozen': getattr(sys, 'frozen', False),
                'status': 'OK'
            }
        except Exception as e:
            diagnostic_logger.error(f"Error checking system info: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _check_environment(self) -> Dict[str, Any]:
        """Verificar variáveis de ambiente e configuração"""
        try:
            env_vars = {
                'PATH': os.environ.get('PATH', ''),
                'PYTHONPATH': os.environ.get('PYTHONPATH', ''),
                'TEMP': os.environ.get('TEMP', ''),
                'TMP': os.environ.get('TMP', ''),
                'USERPROFILE': os.environ.get('USERPROFILE', ''),
                'APPDATA': os.environ.get('APPDATA', ''),
            }
            
            return {
                'environment_variables': env_vars,
                'current_directory_writable': os.access('.', os.W_OK),
                'temp_directory_writable': os.access(os.environ.get('TEMP', '.'), os.W_OK),
                'api_url_configured': bool(API_URL),
                'api_url': API_URL,
                'status': 'OK'
            }
        except Exception as e:
            diagnostic_logger.error(f"Error checking environment: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _check_database(self) -> Dict[str, Any]:
        """Verificar estado da base de dados"""
        try:
            db_info = {
                'database_path': str(db_path),
                'database_exists': os.path.exists(db_path),
                'database_readable': os.path.exists(db_path) and os.access(db_path, os.R_OK),
                'database_writable': os.path.exists(db_path) and os.access(db_path, os.W_OK),
                'database_size': os.path.getsize(db_path) if os.path.exists(db_path) else 0,
            }
            
            # Tentar health check
            try:
                db_info['health_check'] = health_check()
                db_info['status'] = 'OK' if db_info['health_check'] else 'WARNING'
            except Exception as e:
                db_info['health_check'] = False
                db_info['health_check_error'] = str(e)
                db_info['status'] = 'ERROR'
                
            return db_info
            
        except Exception as e:
            diagnostic_logger.error(f"Error checking database: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    async def _check_network(self) -> Dict[str, Any]:
        """Verificar conectividade de rede e API"""
        try:
            network_info = {
                'api_url': API_URL,
                'dns_resolution': False,
                'connection_test': False,
                'api_health_check': False,
                'response_time': None,
                'auth_tokens_exist': AUTH_TOKENS_FILE.exists() if AUTH_TOKENS_FILE else False,
            }
            
            if not API_URL:
                network_info['status'] = 'WARNING'
                network_info['message'] = 'API_URL not configured'
                return network_info
            
            # Test basic connectivity with timeout
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Try to connect to API
                    response = await client.get(f"{API_URL}/", timeout=10.0)
                    network_info['connection_test'] = True
                    network_info['response_time'] = time.time() - start_time
                    network_info['status_code'] = response.status_code
                    
                    # Try health check endpoint
                    try:
                        health_response = await client.get(f"{API_URL}/health/", timeout=5.0)
                        network_info['api_health_check'] = health_response.status_code == 200
                    except:
                        pass  # Health endpoint may not exist
                        
            except httpx.ConnectError:
                network_info['connection_error'] = 'Cannot connect to API server'
            except httpx.TimeoutException:
                network_info['connection_error'] = 'Connection timeout'
            except Exception as e:
                network_info['connection_error'] = str(e)
            
            network_info['status'] = 'OK' if network_info['connection_test'] else 'ERROR'
            return network_info
            
        except Exception as e:
            diagnostic_logger.error(f"Error checking network: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _check_filesystem(self) -> Dict[str, Any]:
        """Verificar sistema de arquivos e permissões"""
        try:
            current_dir = os.getcwd()
            filesystem_info = {
                'current_directory': current_dir,
                'current_dir_exists': os.path.exists(current_dir),
                'current_dir_readable': os.access(current_dir, os.R_OK),
                'current_dir_writable': os.access(current_dir, os.W_OK),
                'temp_dir_writable': os.access(os.environ.get('TEMP', '.'), os.W_OK),
            }
            
            # Check disk space
            try:
                import shutil
                total, used, free = shutil.disk_usage(current_dir)
                filesystem_info.update({
                    'disk_total_gb': total // (1024**3),
                    'disk_used_gb': used // (1024**3),
                    'disk_free_gb': free // (1024**3),
                    'disk_usage_percent': (used / total) * 100,
                })
            except Exception:
                filesystem_info['disk_info'] = 'Not available'
            
            # Test file creation
            test_file = os.path.join(current_dir, 'diagnostic_test.tmp')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                filesystem_info['file_creation_test'] = True
            except:
                filesystem_info['file_creation_test'] = False
            
            filesystem_info['status'] = 'OK' if filesystem_info['current_dir_writable'] else 'ERROR'
            return filesystem_info
            
        except Exception as e:
            diagnostic_logger.error(f"Error checking filesystem: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _check_resources(self) -> Dict[str, Any]:
        """Verificar recursos do sistema"""
        try:
            if not PSUTIL_AVAILABLE:
                return {
                    'status': 'WARNING',
                    'message': 'psutil not available - resource monitoring disabled'
                }
                
            # Memory information
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            resource_info = {
                'memory_total_mb': memory.total // (1024**2),
                'memory_available_mb': memory.available // (1024**2),
                'memory_usage_percent': memory.percent,
                'disk_usage_percent': disk.percent,
                'cpu_count': psutil.cpu_count(),
                'cpu_usage_percent': psutil.cpu_percent(interval=1),
            }
            
            # Check if resources are adequate
            low_memory = memory.available < 512 * 1024 * 1024  # Less than 512MB
            high_disk = disk.percent > 90
            high_cpu = resource_info['cpu_usage_percent'] > 80
            
            if low_memory or high_disk or high_cpu:
                resource_info['status'] = 'WARNING'
                resource_info['warnings'] = []
                if low_memory:
                    resource_info['warnings'].append('Low available memory')
                if high_disk:
                    resource_info['warnings'].append('High disk usage')
                if high_cpu:
                    resource_info['warnings'].append('High CPU usage')
            else:
                resource_info['status'] = 'OK'
            
            return resource_info
            
        except Exception as e:
            diagnostic_logger.error(f"Error checking resources: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Gerar resumo do diagnóstico"""
        summary = {
            'total_checks': len(self.results),
            'ok_checks': 0,
            'warning_checks': 0,
            'error_checks': 0,
            'critical_issues': [],
            'warnings': [],
            'overall_status': 'UNKNOWN'
        }
        
        for check_name, check_result in self.results.items():
            if check_name == 'summary':
                continue
                
            status = check_result.get('status', 'UNKNOWN')
            if status == 'OK':
                summary['ok_checks'] += 1
            elif status == 'WARNING':
                summary['warning_checks'] += 1
                summary['warnings'].append(f"{check_name}: {check_result.get('message', 'Warning')}")
            elif status == 'ERROR':
                summary['error_checks'] += 1
                summary['critical_issues'].append(f"{check_name}: {check_result.get('error', 'Unknown error')}")
        
        # Determine overall status
        if summary['error_checks'] > 0:
            summary['overall_status'] = 'CRITICAL'
        elif summary['warning_checks'] > 0:
            summary['overall_status'] = 'WARNING'
        else:
            summary['overall_status'] = 'OK'
        
        return summary
    
    def save_diagnostic_report(self, filename: Optional[str] = None) -> str:
        """Salvar relatório de diagnóstico em arquivo"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"diagnostic_report_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, default=str)
            diagnostic_logger.info(f"Diagnostic report saved to: {filename}")
            return filename
        except Exception as e:
            diagnostic_logger.error(f"Error saving diagnostic report: {e}")
            raise

def run_quick_diagnostic() -> Dict[str, Any]:
    """Executar diagnóstico rápido (apenas checks essenciais)"""
    diagnostic_logger.info("=== DIAGNÓSTICO RÁPIDO ===")
    
    quick_results = {}
    
    # Database check
    try:
        quick_results['database'] = health_check()
    except Exception as e:
        quick_results['database'] = False
        quick_results['database_error'] = str(e)
    
    # File system check
    try:
        quick_results['filesystem'] = os.access('.', os.W_OK)
    except:
        quick_results['filesystem'] = False
    
    # API check (simple sync version for quick diagnostic)
    def quick_api_check():
        try:
            import requests
            response = requests.get(f"{API_URL}/", timeout=3.0)
            return response.status_code < 400
        except:
            return False
    
    try:
        quick_results['api'] = quick_api_check()
    except Exception as e:
        diagnostic_logger.warning(f"API check failed: {e}")
        quick_results['api'] = False
    
    quick_results['overall'] = all([
        quick_results.get('database', False),
        quick_results.get('filesystem', False)
    ])
    
    return quick_results