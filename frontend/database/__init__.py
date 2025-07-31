from .models import Sessao, Categoria, Historico  # Importa os modelos (Contagem removida)
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

__all__ = ["Sessao", "Categoria", "Historico", "Session", "init_db"]
