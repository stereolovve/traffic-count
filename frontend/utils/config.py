# utils/config.py
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

# Versão atual do aplicativo - atualize este valor a cada nova versão
APP_VERSION = "7.4.0"

API_URL = os.getenv("API_URL", "https://perplan.tech")
#API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
EXCEL_BASE_DIR = os.getenv("EXCEL_BASE_DIR", "Z:\\0Pesquisa\\_0ContadorDigital\\ContagensQ3")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if os.name == "nt": 
    DESKTOP_DIR = Path.home() / "Desktop" / "Contador" 
    DESKTOP_DIR = Path.home() / "Contador"

DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

# Criar diretório para contagens
CONTAGENS_DIR = DESKTOP_DIR / "Contagens"
CONTAGENS_DIR.mkdir(exist_ok=True)

# Cache para verificação de rede (evita testar sempre)
_network_cache = {
    'last_check': None,
    'is_available': False,
    'cache_duration': 60  # Cache por 60 segundos
}

def get_excel_dir(show_feedback=False):
    """
    Verifica se diretório da rede está acessível com timeout e cache.
    
    Args:
        show_feedback (bool): Se deve retornar informações sobre onde salvou
        
    Returns:
        tuple: (path, feedback_info) se show_feedback=True
        Path: apenas o path se show_feedback=False
    """
    import time
    from datetime import datetime, timedelta
    
    current_time = time.time()
    
    # Verificar cache
    if (_network_cache['last_check'] and 
        current_time - _network_cache['last_check'] < _network_cache['cache_duration']):
        
        if _network_cache['is_available']:
            result_path = Path(EXCEL_BASE_DIR)
            feedback = {
                'success': True, 
                'location': 'network', 
                'path': str(result_path),
                'message': f"✅ Salvo na rede: {result_path}"
            }
        else:
            result_path = CONTAGENS_DIR
            feedback = {
                'success': True, 
                'location': 'local', 
                'path': str(result_path),
                'message': f"⚠️ Rede indisponível - Salvo localmente: {result_path}"
            }
        
        return (result_path, feedback) if show_feedback else result_path
    
    # Testar acesso à rede com timeout
    network_available = False
    feedback = None
    
    try:
        network_path = Path(EXCEL_BASE_DIR)
        
        # Timeout multiplataforma usando threading
        import threading
        import queue
        
        def test_network_access():
            """Testa acesso à rede de forma segura"""
            try:
                test_file = network_path / f".test_access_{int(current_time)}"
                test_file.touch()
                test_file.unlink()
                return True, None
            except Exception as e:
                return False, str(e)
        
        # Usar thread com timeout para testar acesso
        result_queue = queue.Queue()
        
        def worker():
            success, error = test_network_access()
            result_queue.put((success, error))
        
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        thread.join(timeout=3)  # 3 segundos de timeout
        
        try:
            # Verificar se thread completou
            if thread.is_alive():
                # Timeout - thread ainda rodando
                network_available = False
                result_path = CONTAGENS_DIR
                feedback = {
                    'success': True, 
                    'location': 'local', 
                    'path': str(result_path),
                    'message': f"⚠️ Timeout na rede - Salvo localmente: {result_path}",
                    'error': 'Network timeout (3s)'
                }
            else:
                # Thread completou - verificar resultado
                success, error = result_queue.get_nowait()
                if success:
                    network_available = True
                    result_path = network_path
                    feedback = {
                        'success': True, 
                        'location': 'network', 
                        'path': str(result_path),
                        'message': f"✅ Salvo na rede: {result_path}"
                    }
                else:
                    network_available = False
                    result_path = CONTAGENS_DIR
                    feedback = {
                        'success': True, 
                        'location': 'local', 
                        'path': str(result_path),
                        'message': f"⚠️ Rede indisponível - Salvo localmente: {result_path}",
                        'error': error
                    }
        except queue.Empty:
            # Queue vazia - algo deu errado
            network_available = False
            result_path = CONTAGENS_DIR
            feedback = {
                'success': True, 
                'location': 'local', 
                'path': str(result_path),
                'message': f"⚠️ Erro no teste de rede - Salvo localmente: {result_path}",
                'error': 'Queue empty'
            }
                
    except Exception as e:
        # Fallback completo
        network_available = False
        result_path = CONTAGENS_DIR
        feedback = {
            'success': False, 
            'location': 'local', 
            'path': str(result_path),
            'message': f"❌ Erro ao verificar rede - Usando local: {result_path}",
            'error': str(e)
        }
    
    # Atualizar cache
    _network_cache['last_check'] = current_time
    _network_cache['is_available'] = network_available
    
    return (result_path, feedback) if show_feedback else result_path

LOG_FILE = Path.cwd() / "log.txt"  
AUTH_TOKENS_FILE = DESKTOP_DIR / "auth_tokens.json"
