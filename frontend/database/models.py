#models.py
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import os
from sqlalchemy.orm import relationship
Base = declarative_base()

db_path = os.path.join(os.getenv('USERPROFILE'), 'dados.db')

engine = create_engine('sqlite:///dados.db')

Session = sessionmaker(bind=engine)

class Categoria(Base):
    __tablename__ = 'categorias'
    id = Column(Integer, primary_key=True, autoincrement=True)
    padrao = Column(String, nullable=False)
    veiculo = Column(String, nullable=False)
    movimento = Column(String, nullable=False)
    bind = Column(String)
    count = Column(Integer, default=0)
    criado_em = Column(DateTime, default=datetime.now)
    __table_args__ = (
        UniqueConstraint('padrao', 'veiculo', 'movimento', name='uq_categorias_padrao_veiculo_movimento'),
    )

    historicos = relationship("Historico", back_populates="categoria")

    def __repr__(self):
        return f"<Categoria(id={self.id}, padrao='{self.padrao}', veiculo='{self.veiculo}', movimento='{self.movimento}')>"

class Sessao(Base):
    __tablename__ = 'sessoes'
    sessao = Column(String, primary_key=True)
    details = Column(String)
    padrao = Column(String)
    criada_em = Column(DateTime, default=datetime.now)
    ativa = Column(Boolean)

    contagens = relationship("Contagem", back_populates="sessao_obj")  # Relacionamento com Contagem

    def __repr__(self):
        return f"<Sessao(sessao='{self.sessao}', ativa={self.ativa})>"


class Contagem(Base):
    __tablename__ = 'contagens'
    id = Column(Integer, primary_key=True)
    sessao = Column(String, ForeignKey('sessoes.sessao'), nullable=False)
    veiculo = Column(String, nullable=False)
    movimento = Column(String, nullable=False)
    count = Column(Integer, default=0)  # Contagem do período
    contagem_total = Column(Integer, default=0)  # Contagem total da sessão

    sessao_obj = relationship("Sessao", back_populates="contagens")  # Relacionamento com Sessao

    def __repr__(self):
        return f"<Contagem(sessao='{self.sessao}', veiculo='{self.veiculo}', movimento='{self.movimento}')>"


class Historico(Base):
    __tablename__ = 'historico'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sessao = Column(String, ForeignKey('sessoes.sessao'))
    categoria_id = Column(Integer, ForeignKey('categorias.id'))  # Referencia o ID da Categoria
    movimento = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    acao = Column(String)

    categoria = relationship("Categoria", back_populates="historicos")  # Relacionamento com Categoria

    def __repr__(self):
        return f"<Historico(sessao='{self.sessao}', categoria_id={self.categoria_id}, movimento='{self.movimento}')>"


def init_db():
    Base.metadata.create_all(engine)

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
    self.details = {"Movimentos": []}  # Inicializar com Movimentos vazio
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