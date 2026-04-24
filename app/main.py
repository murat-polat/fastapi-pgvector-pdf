from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List
import pdfplumber
import os

app = FastAPI()

class SearchRequest(BaseModel):
    query: str

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    content = await file.read()
    with open(f"/tmp/{file.filename}", "wb") as f:
        f.write(content)
    text = ""
    with pdfplumber.open(f"/tmp/{file.filename}") as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    os.remove(f"/tmp/{file.filename}")
    # TODO: Generate and store vectors in DB
    return {"filename": file.filename, "text_excerpt": text[:200]}

@app.post("/search/")
async def search_vectors(request: SearchRequest):
    # TODO: Implement vector search in DB
    return {"query": request.query, "results": []}
