from app.core.db import SessionLocal
from app.models.vaga import Vaga
from app.services.scraper_service import analyze_vaga_match

db = SessionLocal()
vagas = db.query(Vaga).all()

print(f"Processando {len(vagas)} vagas para aplicar IA (Nova Arquitetura)...")

for vaga in vagas:
    # A nova versão do analyze_vaga_match precisa do DB para o currículo ativo
    score, insight = analyze_vaga_match(db, vaga.titulo, vaga.localizacao, vaga.descricao_completa or "")
    vaga.match_score = score
    vaga.insights = insight
    print(f"   [IA] Refinando: {vaga.titulo[:40]}... -> {score}%")

db.commit()
db.close()
print("IA aplicada com sucesso em todas as vagas!")
