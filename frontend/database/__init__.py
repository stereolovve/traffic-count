from .models import Sessao, Categoria, Contagem, Historico  # Importa os modelos
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuração do banco de dados
DATABASE_URL = "sqlite:///traffic_counter.db"  # Altere conforme necessário
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Função para inicializar o banco de dados
def init_db():
    from .models import Base  # Certifique-se de importar Base aqui
    Base.metadata.create_all(bind=engine)

__all__ = ["Sessao", "Categoria", "Contagem", "Historico", "Session", "init_db"]
