
import sys
import os

# Adiciona o diretório atual ao path para permitir imports relativos/locais
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.db import SessionLocal
from app.services.scraper_service import real_scrape

def main():
    db = SessionLocal()
    try:
        print("[*] Iniciando busca real de vagas...")
        vagas_encontradas = real_scrape(db)
        print(f"\n[✓] Busca finalizada!")
        print(f"[+] Foram adicionadas {vagas_encontradas} novas vagas ao banco.")
        
        # Verifica se algo novo foi adicionado
        count = db.execute("SELECT COUNT(*) FROM vagas").fetchone()[0]
        print(f"[*] Total de vagas no banco agora: {count}")
        
    except Exception as e:
        print(f"[-] Erro crítico durante o scrape real: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
