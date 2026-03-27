import os
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrai texto de um arquivo PDF."""
    try:
        text = extract_pdf_text(pdf_path)
        return text.strip() if text else ""
    except Exception as e:
        print(f"Erro ao extrair PDF {pdf_path}: {e}")
        return ""

def extract_text_from_docx(docx_path: str) -> str:
    """Extrai texto de um arquivo DOCX."""
    try:
        doc = Document(docx_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return "\n".join(full_text).strip()
    except Exception as e:
        print(f"Erro ao extrair DOCX {docx_path}: {e}")
        return ""

def parse_resume(file_path: str) -> str:
    """Detecta a extensão e extrai o texto do currículo."""
    _, ext = os.path.splitext(file_path.lower())
    
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        return extract_text_from_docx(file_path)
    else:
        return ""
