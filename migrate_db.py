import sqlite3
import os

# Caminho absoluto para o banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'vagas.db')

def migrate():
    print(f"Iniciando migração no banco: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Colunas que queremos garantir que existem na tabela 'vagas'
    vagas_columns = {
        "match_score": "INTEGER DEFAULT 0",
        "insights": "TEXT",
        "descricao_completa": "TEXT",
        "keywords_ats": "TEXT"
    }
    
    # Colunas que queremos garantir que existem na tabela 'curriculos'
    curriculos_columns = {
        "is_active": "INTEGER DEFAULT 1"
    }
    
    # Função auxiliar para adicionar colunas se não existirem
    def add_columns_if_missing(table_name, columns_dict):
        cursor.execute(f"PRAGMA table_info({table_name});")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        for col_name, col_type in columns_dict.items():
            if col_name not in existing_columns:
                print(f"   [+] Adicionando coluna '{col_name}' em '{table_name}'...")
                try:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type};")
                except sqlite3.OperationalError as e:
                    print(f"   [!] Erro ao adicionar {col_name}: {e}")
            else:
                print(f"   [ok] Coluna '{col_name}' já existe em '{table_name}'.")

    try:
        # Garantir que a tabela 'vagas' existe antes de migrar
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vagas';")
        if cursor.fetchone():
            add_columns_if_missing("vagas", vagas_columns)
        else:
            print("   [!] Tabela 'vagas' não encontrada. Pulando.")

        # Garantir que a tabela 'curriculos' existe antes de migrar
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='curriculos';")
        if cursor.fetchone():
            add_columns_if_missing("curriculos", curriculos_columns)
        else:
            print("   [!] Tabela 'curriculos' não encontrada. Pulando.")
            
        conn.commit()
        print("Migração concluída com sucesso!")
    except Exception as e:
        print(f"Erro fatal durante a migração: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
