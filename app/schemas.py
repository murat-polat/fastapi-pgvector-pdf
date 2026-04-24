from pydantic import BaseModel
from typing import List

class PDFUploadResponse(BaseModel):
    filename: str
    text_excerpt: str

class SearchRequest(BaseModel):
    query: str

class SearchResult(BaseModel):
    id: int
    score: float
    text_excerpt: str

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
