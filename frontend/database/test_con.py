# create_tables.py
from models import init_db, engine, Session
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)

def create_tables():
    """Cria todas as tabelas definidas nos models"""
    try:
        print("Iniciando criação das tabelas...")
        
        # Criar todas as tabelas
        init_db()
        
        print("✅ Todas as tabelas foram criadas com sucesso!")
        
        # Verificar se as tabelas foram criadas
        verify_tables()
        
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        raise

def verify_tables():
    """Verifica se as tabelas foram criadas corretamente"""
    try:
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # Listar todas as tabelas
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            print("\n📋 Tabelas criadas:")
            for table in tables:
                print(f"  - {table}")
                
            # Verificar estrutura de cada tabela
            expected_tables = ['categorias', 'sessoes', 'contagens', 'historico']
            
            for table in expected_tables:
                if table in tables:
                    print(f"✅ Tabela '{table}' criada com sucesso")
                else:
                    print(f"❌ Tabela '{table}' não encontrada")
                    
    except Exception as e:
        print(f"Erro ao verificar tabelas: {e}")

if __name__ == "__main__":
    create_tables()