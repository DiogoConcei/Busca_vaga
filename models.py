from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database import Base

class Vaga(Base):
    __tablename__ = "vagas"

    # Usando Mapped para garantir que o Python entenda os tipos corretamente
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String)
    empresa: Mapped[str] = mapped_column(String)
    link: Mapped[str] = mapped_column(String, unique=True)
    localizacao: Mapped[str] = mapped_column(String)
    area: Mapped[str] = mapped_column(String) # Dados, Front, Back, Web
    data_postagem: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String, default="Novo") # Novo, Candidatado, Rejeitado
