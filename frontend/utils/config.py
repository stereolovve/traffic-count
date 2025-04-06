# utils/config.py
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
EXCEL_BASE_DIR = os.getenv("EXCEL_BASE_DIR", "Z:\\0Pesquisa\\_0ContadorDigital\\ContagensQ2")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if os.name == "nt": 
    DESKTOP_DIR = Path.home() / "Desktop" / "Contador" 
    DESKTOP_DIR = Path.home() / "Contador"

DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = DESKTOP_DIR / "log.txt"  
AUTH_TOKENS_FILE = DESKTOP_DIR / "auth_tokens.json"
