from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Vaga(Base):
    __tablename__ = "vagas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String)
    empresa: Mapped[str] = mapped_column(String)
    link: Mapped[str] = mapped_column(String, unique=True)
    localizacao: Mapped[str] = mapped_column(String)
    modalidade: Mapped[str] = mapped_column(String, default="Não Especificado")
    area: Mapped[str] = mapped_column(String)
    data_postagem: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String, default="Novo")
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    insights: Mapped[str] = mapped_column(String, nullable=True)
    descricao_completa: Mapped[str] = mapped_column(String, nullable=True)
    keywords_ats: Mapped[str] = mapped_column(String, nullable=True)

class Curriculo(Base):
    __tablename__ = "curriculos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String)
    caminho: Mapped[str] = mapped_column(String)
    texto_extraido: Mapped[str] = mapped_column(String)
    data_upload: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Integer, default=1)
