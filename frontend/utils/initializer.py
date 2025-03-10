#initializer
import os
from database.models import Session, Contagem, init_db
import logging
import json


def __init__(self, page):
    super().__init__()
    self.page = page
    self.inicializar_variaveis()
    self.configurar_numpad_mappings()
    self.setup_ui()
    self.load_active_session()

def inicializar_variaveis(self):
    self.sessao = None
    self.session = Session()
    self.details = {"Movimentos": []}
    self.contagens = {}
    self.binds = {}
    self.categorias = []
    self.labels = {}
    self.listener = None
    self.contagem_ativa = False
    self.historico_page_size = 30  # Número de registros a serem carregados por vez

def configurar_numpad_mappings(self):
    self.numpad_mappings = {
        96: "np0", 97: "np1", 98: "np2", 99: "np3", 100: "np4",
        101: "np5", 102: "np6", 103: "np7", 104: "np8", 105: "np9",
        106: "np*", 110: "np,", 111: "np/"
    }