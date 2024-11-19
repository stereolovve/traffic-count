import json
from datetime import datetime
from database.models import Session, Categoria, Sessao, Contagem, Historico, init_db
from sqlalchemy.exc import SQLAlchemyError
import logging
import os
import flet as ft



def carregar_categorias_padrao(self, caminho_json):
    try:
        with open(caminho_json, 'r') as f:
            categorias_padrao = json.load(f)
            for categoria in categorias_padrao:
                veiculo = categoria.get('veiculo')
                bind = categoria.get('bind')
                if veiculo and bind:
                    for movimento in self.detalhes["Movimentos"]:
                        nova_categoria = Categoria(
                            veiculo=veiculo,
                            movimento=movimento,
                            bind=bind,
                            criado_em=datetime.now()
                        )
                        self.session.merge(nova_categoria)
            self.session.commit()
    except FileNotFoundError:
        logging.error(f"Arquivo JSON não encontrado: {caminho_json}")
        raise Exception("Arquivo JSON não encontrado.")
    except json.JSONDecodeError:
        logging.error(f"Erro ao decodificar JSON: {caminho_json}")
        raise Exception("Erro ao decodificar JSON.")
    except SQLAlchemyError as ex:
        logging.error(f"Erro ao salvar padrões no banco de dados: {ex}")
        self.session.rollback()
        raise Exception("Erro ao salvar no banco de dados.")


def carregar_padroes_selecionados(self, e):
    padrao_selecionado = self.padrao_dropdown.value
    base_path = os.path.join(os.getcwd(), "utils")
    caminho_json = None

    if padrao_selecionado == "Padrão Perplan":
        caminho_json = os.path.join(base_path, "padrao_perplan.json")
    elif padrao_selecionado == "Padrão Perci":
        caminho_json = os.path.join(base_path, "padrao_perci.json")
    elif padrao_selecionado == "Padrão Simplificado":
        caminho_json = os.path.join(base_path, "padrao_simplificado.json")

    else:
        snackbar = ft.SnackBar(ft.Text("Selecione um padrão!"), bgcolor="ORANGE")
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()
        return

    try:
        carregar_categorias_padrao(self, caminho_json)
        snackbar = ft.SnackBar(ft.Text("Categorias padrao carregadas!"), bgcolor="GREEN")
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()

    except (FileNotFoundError, json.JSONDecodeError, SQLAlchemyError) as ex:
        logging.error(f"Erro ao carregar categorias padrão: {ex}")
        snackbar = ft.SnackBar(ft.Text(f"Erro ao carregar categorias padrão: {ex}"), bgcolor="RED")
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()
