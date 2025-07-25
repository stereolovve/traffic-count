import logging
from database.models import Historico
from sqlalchemy.exc import SQLAlchemyError

class HistoryManager:
    def __init__(self, contador):
        self.contador = contador
        
    def salvar_historico(self, categoria_id, movimento, acao):
        """
        Salva uma ação no histórico
        
        Args:
            categoria_id: ID da categoria (pode ser None para ações gerais)
            movimento: Movimento relacionado à ação
            acao: Tipo de ação realizada (increment, decrement, reset, etc.)
        """
        try:
            novo_historico = Historico(
                sessao=self.contador.sessao,
                categoria_id=categoria_id,
                movimento=movimento,
                acao=acao
            )
            with self.contador.session_lock:
                self.contador.session.add(novo_historico)
                self.contador.session.commit()
            logging.info(f"[INFO] Histórico salvo com sucesso para ação: {acao}")
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao salvar histórico: {ex}")
            with self.contador.session_lock:
                self.contador.session.rollback()
                
    def carregar_historico(self, page_size=30):
        """
        Carrega os registros do histórico
        
        Args:
            page_size: Quantidade de registros a serem retornados
        Returns:
            Lista de registros do histórico
        """
        try:
            registros = self.contador.session.query(Historico)\
                .filter_by(sessao=self.contador.sessao)\
                .order_by(Historico.timestamp.desc())\
                .limit(page_size)\
                .all()
            return registros
        except SQLAlchemyError as ex:
            logging.error(f"Erro ao carregar histórico: {ex}")
            return []
