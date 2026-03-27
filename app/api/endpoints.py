import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from ..core.db import get_db
from ..models.vaga import Vaga, Curriculo
from ..services.scraper_service import real_scrape
from ..services.resume_service import parse_resume

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.get("/vagas", response_model=List[dict])
def list_vagas(area: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Vaga)
    if area:
        query = query.filter(Vaga.area == area)
    vagas = query.order_by(Vaga.data_postagem.desc()).all()
    
    return [
        {
            "id": v.id, "titulo": v.titulo, "empresa": v.empresa,
            "link": v.link, "localizacao": v.localizacao, "area": v.area,
            "data_postagem": v.data_postagem, "status": v.status,
            "match_score": v.match_score, "insights": v.insights,
            "descricao_completa": v.descricao_completa, "keywords_ats": v.keywords_ats
        }
        for v in vagas
    ]

@router.patch("/vagas/{vaga_id}/status")
def update_status(vaga_id: int, status: str, db: Session = Depends(get_db)):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    vaga.status = status
    db.commit()
    return {"message": f"Status atualizado para {status}"}

@router.post("/vagas/atualizar")
def update_vagas(db: Session = Depends(get_db)):
    real_scrape(db)
    return {"message": "Busca concluída"}

# --- CURRICULOS ---

@router.post("/curriculos/upload")
async def upload_curriculo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        texto = parse_resume(file_path)
        if not texto:
            if os.path.exists(file_path): os.remove(file_path)
            raise HTTPException(status_code=400, detail="Extração falhou")

        db.query(Curriculo).update({Curriculo.is_active: False})
        novo = Curriculo(nome=file.filename, caminho=file_path, texto_extraido=texto, is_active=True)
        db.add(novo)
        db.commit()
        db.refresh(novo)
        return {"id": novo.id, "message": "Sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/curriculos")
def list_curriculos(db: Session = Depends(get_db)):
    curr = db.query(Curriculo).all()
    return [{"id": c.id, "nome": c.nome, "is_active": c.is_active, "texto_extraido": c.texto_extraido} for c in curr]

@router.delete("/curriculos/{curriculo_id}")
def delete_curriculo(curriculo_id: int, db: Session = Depends(get_db)):
    c = db.query(Curriculo).filter(Curriculo.id == curriculo_id).first()
    if c:
        if os.path.exists(c.caminho): os.remove(c.caminho)
        db.delete(c)
        db.commit()
    return {"message": "Removido"}

@router.patch("/curriculos/{curriculo_id}/toggle")
def toggle_curriculo(curriculo_id: int, db: Session = Depends(get_db)):
    c = db.query(Curriculo).filter(Curriculo.id == curriculo_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Currículo não encontrado")
    
    if c.is_active:
        c.is_active = False
    else:
        active_count = db.query(Curriculo).filter(Curriculo.is_active == True).count()
        if active_count >= 2:
            raise HTTPException(status_code=400, detail="Limite de 2 currículos ativos atingido. Desative um primeiro.")
        c.is_active = True
    
    db.commit()
    return {"message": "Status atualizado", "is_active": c.is_active}

@router.patch("/curriculos/{curriculo_id}/activate")
def activate_curriculo(curriculo_id: int, db: Session = Depends(get_db)):
    # Mantendo por compatibilidade se necessário, mas redirecionando ou sugerindo toggle
    return toggle_curriculo(curriculo_id, db)
