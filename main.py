from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import models, database, scraper

# Criar tabelas ao iniciar
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Bot-Vagas Intern API")

# Configurar CORS para permitir que o React se comunique
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/vagas", response_model=List[dict])
def list_vagas(area: Optional[str] = None, db: Session = Depends(database.get_db)):
    query = db.query(models.Vaga)
    if area:
        query = query.filter(models.Vaga.area == area)
    vagas = query.order_by(models.Vaga.data_postagem.desc()).all()
    
    return [
        {
            "id": v.id,
            "titulo": v.titulo,
            "empresa": v.empresa,
            "link": v.link,
            "localizacao": v.localizacao,
            "area": v.area,
            "data_postagem": v.data_postagem,
            "status": v.status
        }
        for v in vagas
    ]

@app.patch("/vagas/{vaga_id}/status")
def update_status(vaga_id: int, status: str, db: Session = Depends(database.get_db)):
    # Localiza a vaga no banco
    vaga = db.query(models.Vaga).filter(models.Vaga.id == vaga_id).first()
    
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    
    # Atualiza o status
    vaga.status = status
    db.commit()
    
    return {"message": f"Status atualizado para {status}"}

@app.post("/vagas/atualizar")
def update_vagas(db: Session = Depends(database.get_db)):
    # Aciona o scraper real implementado em scraper.py
    scraper.real_scrape(db)
    return {"message": "Busca de vagas concluída com sucesso"}
