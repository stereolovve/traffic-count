#models.py
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import os
from sqlalchemy.orm import relationship
Base = declarative_base()

db_path = os.path.join(os.getenv('USERPROFILE'), 'banco_dados_contador.db')

engine = create_engine('sqlite:///banco_dados_contador.db')

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

    contagens = relationship("Contagem", back_populates="sessao_obj")

    def __repr__(self):
        return f"<Sessao(sessao='{self.sessao}', ativa={self.ativa})>"


class Contagem(Base):
    __tablename__ = 'contagens'
    id = Column(Integer, primary_key=True)
    sessao = Column(String, ForeignKey('sessoes.sessao'), nullable=False)
    veiculo = Column(String, nullable=False)
    movimento = Column(String, nullable=False)
    count = Column(Integer, default=0)
    contagem_total = Column(Integer, default=0)

    sessao_obj = relationship("Sessao", back_populates="contagens")

    def __repr__(self):
        return f"<Contagem(sessao='{self.sessao}', veiculo='{self.veiculo}', movimento='{self.movimento}')>"


class Historico(Base):
    __tablename__ = 'historico'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sessao = Column(String, ForeignKey('sessoes.sessao'))
    categoria_id = Column(Integer, ForeignKey('categorias.id'))
    movimento = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    acao = Column(String)

    categoria = relationship("Categoria", back_populates="historicos")

    def __repr__(self):
        return f"<Historico(sessao='{self.sessao}', categoria_id={self.categoria_id}, movimento='{self.movimento}')>"


def init_db():
    Base.metadata.create_all(engine)