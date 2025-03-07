# utils/config.py
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()
API_URL = os.getenv("API_URL", "http://perplan.tech")
EXCEL_BASE_DIR = os.getenv("EXCEL_BASE_DIR", "Z:\\0Pesquisa\\_0ContadorDigital\\ContagensNovas")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

APP_DATA_DIR = Path(__file__).parent.parent 
try:
    APP_DATA_DIR.mkdir(exists_ok=True)
except TypeError:
    if not APP_DATA_DIR.exists():
        APP_DATA_DIR.mkdir()