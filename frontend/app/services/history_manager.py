from datetime import datetime
import logging
from database.models import Session, Historico
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

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
            # Criar uma nova sessão para esta operação
            session = Session()
            try:
                # Configurar timeouts para esta sessão
                session.execute(text("SET LOCAL statement_timeout = '5s'"))
                session.execute(text("SET LOCAL lock_timeout = '5s'"))
                
                # Criar registro de histórico
                historico = Historico(
                    sessao=self.contador.sessao,
                    categoria_id=categoria_id,
                    movimento=movimento,
                    timestamp=datetime.now(),
                    acao=acao
                )
                
                # Adicionar e commitar em uma única transação
                session.add(historico)
                session.commit()
                logging.info(f"✅ Histórico salvo: {acao} - {movimento}")
                
            except Exception as e:
                session.rollback()
                logging.error(f"[ERROR] Erro ao salvar histórico: {e}")
                # Não propaga o erro para não travar a interface
            finally:
                session.close()
                
        except Exception as ex:
            logging.error(f"[ERROR] Erro ao salvar histórico: {ex}")
            # Não propaga o erro para não travar a interface
                
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
