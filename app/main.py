
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
import pdfplumber
import os
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError
from models import Base, PDFChunk
import dotenv
from openai import OpenAI
from db import create_tables
import requests
import json



dotenv.load_dotenv('.env')


app = FastAPI()





app.mount("/static", StaticFiles(directory="static"), name="static")


# templates
templates = Jinja2Templates(directory="templates")


# Database setup
DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@db:5432/{os.getenv('POSTGRES_DB')}"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)




def embed_texts(texts):
    """
    Returnerer en liste med embeddings fra OpenAI API.
    Forutsetter at OPENAI_API_KEY er satt i miljøvariabler.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY ikke satt i miljøvariabler")
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "input": texts,
        "model": "text-embedding-ada-002"
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code != 200:
        raise RuntimeError(f"OpenAI embedding-feil: {response.text}")
    result = response.json()
    return [d["embedding"] for d in result["data"]]

def embed_query(text):
    return embed_texts([text])[0]




class SearchRequest(BaseModel):
    query: str



# Helper: split PDF into paragraph chunks with page reference
import re
def split_pdf_paragraphs_with_page(pdf_path):
    """
    Returnerer liste av (tekst, side_nr) for hvert avsnitt i PDF.
    """
    import pdfplumber
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            # Del på dobbel linjeskift (avsnitt)
            for para in re.split(r'\n\s*\n', text):
                para = para.strip()
                if para:
                    chunks.append((para, i+1))  # i+1 for 1-basert side
    return chunks

# Helper: ensure table and extension exists
def ensure_table():
    with engine.connect() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
    # Opprett tabellen via ORM
    Base.metadata.create_all(bind=engine)

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    content = await file.read()
    with open(f"/tmp/{file.filename}", "wb") as f:
        f.write(content)
    tmp_path = f"/tmp/{file.filename}"
    with open(tmp_path, "wb") as f:
        f.write(content)

    # Chunk per avsnitt med side-nummer
    para_chunks = split_pdf_paragraphs_with_page(tmp_path)
    os.remove(tmp_path)

    ensure_table()
    if not para_chunks:
        return {"error": "Ingen tekst funnet i PDF.", "filename": file.filename}
    texts = [c[0] for c in para_chunks]
    pages = [c[1] for c in para_chunks]
    try:
        chunk_embeddings = embed_texts(texts)
    except NotImplementedError:
        return {"error": "Embedding-funksjon ikke implementert. Se backend-kode.", "filename": file.filename}

    # Store in DB

    db = SessionLocal()
    try:
        for chunk, page, emb in zip(texts, pages, chunk_embeddings):
            db.add(PDFChunk(filename=file.filename, chunk=chunk, page=page, embedding=emb))
        db.commit()
    finally:
        db.close()

    return {"filename": file.filename, "text_excerpt": texts[0][:200]}


@app.post("/search/")
async def search_vectors(request: SearchRequest):
    ensure_table()
    try:
        query_embedding = embed_query(request.query)
    except NotImplementedError:
        return {"error": "Embedding-funksjon ikke implementert. Se backend-kode.", "query": request.query, "results": []}
    # Finn topp 3 relevante tekstbiter
    # Konverter Python-listen til en Postgres vector-literal
    def to_pgvector_literal(vec):
        return "'[%s]'" % (', '.join(str(x) for x in vec))

    pgvector_literal = to_pgvector_literal(query_embedding)
    # Bruk ORM for uthenting, men raw SQL for vektorsøk
    db = SessionLocal()
    try:
        sql = f"""
            SELECT id, chunk, page, embedding <#> {pgvector_literal}::vector AS distance
            FROM pdf_chunks
            ORDER BY distance ASC
            LIMIT 3
        """
        result = db.execute(text(sql))
        results = [
            {"id": row[0], "text": row[1], "page": row[2], "score": row[3]} for row in result
        ]
    finally:
        db.close()
    return {"query": request.query, "results": results}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Pass the context as a named argument
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"request": request}
    )
