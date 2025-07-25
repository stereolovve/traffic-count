# utils/config.py
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

# Versão atual do aplicativo - atualize este valor a cada nova versão
APP_VERSION = "6.4.2"

API_URL = os.getenv("API_URL", "http://perplan.tech")
EXCEL_BASE_DIR = os.getenv("EXCEL_BASE_DIR", "Z:\\0Pesquisa\\_0ContadorDigital\\ContagensQ3")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if os.name == "nt": 
    DESKTOP_DIR = Path.home() / "Desktop" / "Contador" 
    DESKTOP_DIR = Path.home() / "Contador"

DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

# Criar diretório para contagens
CONTAGENS_DIR = DESKTOP_DIR / "Contagens"
CONTAGENS_DIR.mkdir(exist_ok=True)

# Função para verificar se o diretório da rede está acessível
def get_excel_dir():
    try:
        network_path = Path(EXCEL_BASE_DIR)
        # Tenta criar um arquivo temporário para testar acesso
        test_file = network_path / ".test_access"
        test_file.touch()
        test_file.unlink()
        return network_path
    except (PermissionError, OSError):
        # Se não conseguir acessar o diretório da rede, usa o diretório local
        return CONTAGENS_DIR

LOG_FILE = Path.cwd() / "log.txt"  
AUTH_TOKENS_FILE = DESKTOP_DIR / "auth_tokens.json"
