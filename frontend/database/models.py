#models.py
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import os
from sqlalchemy.orm import relationship
Base = declarative_base()

db_path = os.path.join(os.getenv('USERPROFILE'), 'contadordb.db')

engine = create_engine('sqlite:///contadordb.db')

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
    padrao = Column(String)
    codigo = Column(String)
    ponto = Column(String)
    data = Column(String)
    horario_inicio = Column(String)
    horario_fim = Column(String)
    criada_em = Column(DateTime, default=datetime.now)
    status = Column(String, default="Aguardando")
    movimentos = Column(String)  # Campo para salvar movimentos como JSON
    contagens_atuais = Column(String)  # Campo para salvar contagens atuais como JSON

    def __repr__(self):
        return f"<Sessao(sessao='{self.sessao}', status={self.status})>"


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