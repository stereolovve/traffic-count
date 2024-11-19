import json
from datetime import datetime
from database.models import Session, Categoria, Sessao, Contagem, Historico, init_db
from sqlalchemy.exc import SQLAlchemyError
import logging
import os
import flet as ft



def carregar_categorias_padrao(self, caminho_json, padrao):
    try:
        with open(caminho_json, 'r') as f:
            categorias_padrao = json.load(f)
            for categoria in categorias_padrao:
                veiculo = categoria.get('veiculo')
                bind = categoria.get('bind')
                if veiculo and bind:
                    for movimento in self.detalhes["Movimentos"]:
                        nova_categoria = Categoria(
                            padrao=padrao,  # Certifique-se de passar o valor correto aqui
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
    try:
        padrao_selecionado = self.padrao_dropdown.value
        if not padrao_selecionado:
            snackbar = ft.SnackBar(ft.Text("Selecione um padrão!"), bgcolor="ORANGE")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()
            return

        caminho_json = self.obter_caminho_json(padrao_selecionado)
        if not caminho_json:
            snackbar = ft.SnackBar(ft.Text(f"Padrão '{padrao_selecionado}' não encontrado!"), bgcolor="RED")
            self.page.overlay.append(snackbar)
            snackbar.open = True
            return

        # Carregar as categorias do JSON
        carregar_categorias_padrao(self, caminho_json)
        snackbar = ft.SnackBar(ft.Text(f"Padrão '{padrao_selecionado}' carregado com sucesso!"), bgcolor="GREEN")
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()
    except Exception as ex:
        logging.error(f"Erro ao carregar padrões: {ex}")
        snackbar = ft.SnackBar(ft.Text(f"Erro ao carregar padrões: {ex}"), bgcolor="RED")
        self.page.overlay.append(snackbar)
        snackbar.open = True



def obter_caminho_json(self, padrao_selecionado):
    base_path = os.path.join(os.getcwd(), "utils")
    if padrao_selecionado == "Padrão Perplan":
        return os.path.join(base_path, "padrao_perplan.json")
    elif padrao_selecionado == "Padrão Perci":
        return os.path.join(base_path, "padrao_perci.json")
    elif padrao_selecionado == "Padrão Simplificado":
        return os.path.join(base_path, "padrao_simplificado.json")
    return None