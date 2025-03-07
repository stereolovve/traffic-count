# app/sessao.py
import flet as ft
import logging
import json
import asyncio
import re
from pathlib import Path
from database.models import Session, Sessao
from sqlalchemy.exc import SQLAlchemyError
import threading
from openpyxl import Workbook

from datetime import datetime
from typing import Optional
from utils.config import API_URL, APP_DATA_DIR
from utils.api import async_api_request

logging.getLogger(__name__).setLevel(logging.ERROR)

def criar_sessao(self, e):
    if not self.validar_campos():
        return
    
    try:
        horario_inicial = self.time_picker_button.text
        horario_inicial_file_safe = horario_inicial.replace(":", "h")
        original_date = self.data_ponto_input.value.strip()

        if not original_date:
            raise ValueError("Data não foi preenchida.")
        
        self.formated_date = datetime.strptime(original_date, "%d-%m-%Y").strftime("%d-%m-%Y")
        movimentos_raw = [
            mov.controls[0].value.strip().upper() 
            for mov in self.movimentos_container.controls 
            if mov.controls[0].value.strip()
        ]
        logging.debug(f"[DEBUG] Movimentos brutos coletados: {movimentos_raw}")

        if not movimentos_raw:
            logging.warning("[WARNING] Nenhum movimento definido na UI")
            raise ValueError("Nenhum movimento definido")

        self.details = {
            "Pesquisador": self.username,
            "Código": self.codigo_ponto_input.value,
            "Ponto": self.nome_ponto_input.value,
            "HorarioInicio": self.selected_time,
            "Data do Ponto": self.data_ponto_input.value,
            "Movimentos": movimentos_raw
        }
        logging.debug(f"[DEBUG] self.details criado: {self.details}")

        movimentos_str = "-".join(self.details["Movimentos"])
        movimentos_str = re.sub(r'[<>:"/\\|?*]', '', movimentos_str)
        base_sessao = f"{self.details['Ponto']}_{self.formated_date}_{movimentos_str}_{horario_inicial_file_safe}"

        self.sessao = base_sessao
        counter = 1
        while self.session.query(Sessao).filter_by(sessao=self.sessao).first():
            self.sessao = f"{base_sessao}_{counter}"
            counter += 1

        padrao_selecionado = self.padrao_dropdown.value
        self.current_timeslot = datetime.strptime(self.selected_time, "%H:%M")
        self.details["current_timeslot"] = self.selected_time

        sessao_existente = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
        if sessao_existente:
            if not sessao_existente.ativa:
                sessao_existente.ativa = True
                sessao_existente.details = json.dumps(self.details)
                sessao_existente.padrao = padrao_selecionado
                self.session.commit()
                logging.debug("[DEBUG] ✅ Sessão reativada com sucesso!")
            else:
                raise ValueError("Uma sessão ativa com esse nome já existe.")
        else:
            nova_sessao = Sessao(
                sessao=self.sessao,
                details=json.dumps(self.details),
                padrao=padrao_selecionado,
                ativa=True
            )
            self.session.add(nova_sessao)
            self.session.commit()
            logging.debug("[DEBUG] ✅ Sessão criada com sucesso!")

        async def setup_session():
            await self.load_categories_api(padrao_selecionado)
            await self.carregar_padroes_selecionados()
            await self.update_binds()

        self.page.run_task(setup_session)

        self._inicializar_arquivo_excel()
        self.setup_aba_contagem()

        self.tabs.selected_index = 1
        self.tabs.tabs[1].content.visible = True

        snackbar = ft.SnackBar(ft.Text("Sessão criada localmente com sucesso!"), bgcolor="GREEN")
        self.page.overlay.append(snackbar)
        snackbar.open = True

    except Exception as ex:
        logging.error(f"[ERROR] Erro ao criar sessão localmente: {ex}")
        snackbar = ft.SnackBar(ft.Text(f"Erro ao criar sessão: {ex}"), bgcolor="RED")
        self.page.overlay.append(snackbar)
        snackbar.open = True


def salvar_sessao(self):
    try:
        details_json = json.dumps(self.details)
        sessao_existente = self.session.query(Sessao).filter_by(sessao=self.sessao).first()
        if sessao_existente:
            sessao_existente.details = details_json
            sessao_existente.ativa = True
        else:
            nova_sessao = Sessao(
                sessao=self.sessao,
                details=details_json,
                ativa=True
            )
            self.session.add(nova_sessao)
        self.session.commit()
        logging.info(f"✅ Sessão {self.sessao} salva e marcada como ativa!")

    except SQLAlchemyError as ex:
        logging.error(f"Erro ao salvar sessão: {ex}")
        self.session.rollback()