from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os
# Inicializa a base declarativa do SQLAlchemy
Base = declarative_base()

# Configura o engine do banco de dados
db_path = os.path.join(os.getenv('USERPROFILE'), 'dados.db')

engine = create_engine('sqlite:///dados.db')

# Cria a sessão do banco de dados
Session = sessionmaker(bind=engine)

# Definição das tabelas do banco de dados
class Categoria(Base):
    __tablename__ = 'categorias'
    padrao = Column(String, nullable=False)
    veiculo = Column(String)
    movimento = Column(String)
    bind = Column(String)
    count = Column(Integer, default=0)
    criado_em = Column(DateTime, default=datetime.now)
    __table_args__ = (PrimaryKeyConstraint('veiculo', 'movimento'),)

class Sessao(Base):
    __tablename__ = 'sessoes'
    sessao = Column(String, primary_key=True)
    details = Column(String)
    padrao = Column(String)
    criada_em = Column(DateTime, default=datetime.now)
    ativa = Column(Boolean)

class Contagem(Base):
    __tablename__ = 'contagens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sessao = Column(String, ForeignKey('sessoes.sessao'))
    movimento = Column(String)
    veiculo = Column(String, ForeignKey('categorias.veiculo'))
    count = Column(Integer, default=0)

class Historico(Base):
    __tablename__ = 'historico'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sessao = Column(String, ForeignKey('sessoes.sessao'))
    veiculo = Column(String, ForeignKey('categorias.veiculo'))
    movimento = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    acao = Column(String)

# Cria as tabelas no banco de dados
def init_db():
    Base.metadata.create_all(engine)

