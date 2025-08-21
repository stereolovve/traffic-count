#models.py
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint, PrimaryKeyConstraint, text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import os
import logging
import time
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError, OperationalError

Base = declarative_base()

# Setup logging for database operations
db_logger = logging.getLogger('database')

# Banco na raiz do projeto (diretório onde o app é iniciado)
def get_db_path():
    """Get database path with error handling"""
    try:
        cwd = os.getcwd()
        db_path = os.path.join(cwd, 'contador.db')
        db_logger.info(f"Database path: {db_path}")
        return db_path
    except Exception as e:
        db_logger.error(f"Error getting database path: {e}")
        # Fallback to current directory
        return 'contador.db'

db_path = get_db_path()

# Create engine with better error handling and connection pooling
def create_db_engine():
    """Create SQLite engine with robust error handling"""
    try:
        engine = create_engine(
            f'sqlite:///{db_path}',
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=3600,   # Recycle connections every hour
            echo=False,          # Set to True for SQL debugging
            connect_args={
                'check_same_thread': False,  # Allow multi-threading
                'timeout': 30,               # 30 second timeout
            }
        )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_logger.info("Database engine created successfully")
            
        return engine
        
    except Exception as e:
        db_logger.error(f"Error creating database engine: {e}")
        raise

engine = create_db_engine()
Session = sessionmaker(bind=engine)

class Categoria(Base):
    __tablename__ = 'categorias'
    id = Column(Integer, primary_key=True, autoincrement=True)
    padrao = Column(String, nullable=False, index=True)  # Índice para performance
    veiculo = Column(String, nullable=False)
    movimento = Column(String, nullable=False)
    bind = Column(String)
    ativo = Column(Boolean, default=True)  # Soft delete
    criado_em = Column(DateTime, default=datetime.now)
    atualizado_em = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # Auditoria
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


def init_db(max_retries=3, retry_delay=1):
    """Initialize database with robust error handling and retries"""
    for attempt in range(max_retries):
        try:
            db_logger.info(f"Initializing database (attempt {attempt + 1}/{max_retries})")
            
            # Check if database directory is writable
            db_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else '.'
            if not os.access(db_dir, os.W_OK):
                raise PermissionError(f"No write permission for database directory: {db_dir}")
            
            # Create all tables
            Base.metadata.create_all(engine)
            
            # Verify database was created successfully
            with engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result.fetchall()]
                expected_tables = ['categorias', 'sessoes', 'historico']
                
                for table in expected_tables:
                    if table not in tables:
                        raise Exception(f"Table '{table}' was not created")
                
                db_logger.info(f"Database initialized successfully with tables: {tables}")
                return True
                
        except PermissionError as e:
            db_logger.error(f"Permission error during database initialization: {e}")
            raise  # Don't retry on permission errors
            
        except (OperationalError, SQLAlchemyError) as e:
            db_logger.warning(f"Database initialization attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                db_logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                db_logger.error(f"Database initialization failed after {max_retries} attempts")
                raise
                
        except Exception as e:
            db_logger.error(f"Unexpected error during database initialization: {e}")
            if attempt < max_retries - 1:
                db_logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise
    
    return False

def health_check():
    """Perform database health check"""
    try:
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT 1")).fetchone()
            if result and result[0] == 1:
                db_logger.info("Database health check passed")
                return True
            else:
                db_logger.error("Database health check failed - unexpected result")
                return False
                
    except Exception as e:
        db_logger.error(f"Database health check failed: {e}")
        return False