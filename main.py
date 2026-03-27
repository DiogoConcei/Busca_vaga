import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
from app.core.db import engine
from app.models.vaga import Base
from migrate_db import migrate

# Cria as tabelas no banco de dados se não existirem
Base.metadata.create_all(bind=engine)
# Garante que colunas novas sejam adicionadas se necessário
migrate()

app = FastAPI(title="InternHunt API - Pro Edition")

# Configuração Robusta de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Em produção, use o endereço real do seu front
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui as rotas modulares
app.include_router(router)

if __name__ == "__main__":
    print("🚀 Servidor InternHunt iniciado em http://localhost:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
