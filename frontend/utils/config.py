# utils/config.py
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

API_URL = os.getenv("API_URL", "http://perplan.tech")
EXCEL_BASE_DIR = os.getenv("EXCEL_BASE_DIR", "Z:\\0Pesquisa\\_0ContadorDigital\\ContagensNovas")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# 📂 Definir diretórios persistentes
if os.name == "nt":  # Windows
    DESKTOP_DIR = Path.home() / "Desktop" / "Contador"  # Pasta "Contador" na Área de Trabalho
else:  # Linux/Mac
    DESKTOP_DIR = Path.home() / "Contador"

# 📂 Criar a pasta "Contador" na Área de Trabalho se não existir
DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

# 📄 Caminhos dos arquivos
LOG_FILE = DESKTOP_DIR / "log.txt"  # Logs de erro
AUTH_TOKENS_FILE = DESKTOP_DIR / "auth_tokens.json"  # 🔑 Tokens do usuário
