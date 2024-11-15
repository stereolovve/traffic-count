import json
from datetime import datetime
from database.models import Session, Categoria, Sessao, Contagem, Historico, init_db
from sqlalchemy.exc import SQLAlchemyError
import logging


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
    except (FileNotFoundError, json.JSONDecodeError, SQLAlchemyError) as ex:
        logging.error(f"Erro ao carregar categorias padrão: {ex}")
        self.session.rollback()