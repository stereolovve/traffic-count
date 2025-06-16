#models.py
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint, PrimaryKeyConstraint, Index, text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import os
import logging
from sqlalchemy.orm import relationship
from urllib.parse import quote_plus
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
from pathlib import Path

# Get the frontend directory path
FRONTEND_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the frontend directory
load_dotenv(os.path.join(FRONTEND_DIR, '.env'))

Base = declarative_base()

# Configuração do PostgreSQL com senha do ambiente
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = quote_plus(os.getenv('DB_PASSWORD', ''))  # Codifica caracteres especiais
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'contadordb')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Configuração do engine com pool de conexões e tratamento de erros
try:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,  # Verifica conexão antes de usar
        echo=False,  # Desativa logs SQL
        connect_args={
            'connect_timeout': 10,  # Timeout de conexão em segundos
            'options': '-c statement_timeout=10000 -c lock_timeout=10000'  # Timeouts em milissegundos
        }
    )
    
    # Testa a conexão
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.commit()
        logging.info("Conexão com o banco de dados estabelecida com sucesso!")
except Exception as e:
    logging.error(f"Erro ao conectar ao banco de dados: {e}")
    raise

# Configuração da sessão com timeout
Session = sessionmaker(
    bind=engine,
    expire_on_commit=False,  # Evita problemas de expiração
    autocommit=False,
    autoflush=False
)

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
        Index('idx_categorias_padrao_veiculo', 'padrao', 'veiculo'),  # Índice para melhorar performance
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

    __table_args__ = (
        Index('idx_sessoes_ativa', 'ativa'),  # Índice para filtrar sessões ativas
    )

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
    periodo = Column(String)  # Formato HH:MM

    __table_args__ = (
        Index('idx_contagens_sessao', 'sessao'),  # Índice para melhorar joins
        Index('idx_contagens_veiculo_movimento', 'veiculo', 'movimento'),  # Índice para consultas comuns
    )

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

    __table_args__ = (
        Index('idx_historico_timestamp', 'timestamp'),  # Índice para consultas por data
        Index('idx_historico_sessao', 'sessao'),  # Índice para joins
    )

    categoria = relationship("Categoria", back_populates="historicos")

    def __repr__(self):
        return f"<Historico(sessao='{self.sessao}', categoria_id={self.categoria_id}, movimento='{self.movimento}')>"


def init_db():
    try:
        Base.metadata.create_all(engine)
        logging.info("Tabelas criadas com sucesso!")
    except Exception as e:
        logging.error(f"Erro ao criar tabelas: {e}")
        raise