# FastAPI PDF Vector Search

A starter project for uploading PDFs, extracting text, generating embeddings, and searching vectors using FastAPI, PostgreSQL (with pgvector), and Docker.

## Features
- Upload and parse PDF files
- Generate and store vector embeddings in PostgreSQL (pgvector)
- Search/query against the vector database
- Dockerized setup for easy development
- Example integration with LangChain (optional)

## Stack
- FastAPI
- Pydantic
- PostgreSQL + pgvector
- Docker
- PyPDF2/pdfplumber
- (Optional) LangChain

## Getting Started

### Prerequisites
- Docker & Docker Compose
- (Optional) OpenAI API key for LangChain

### Setup
```bash
git clone <this-repo-url>
cd fastapi-pgvector-pdf
docker-compose up --build
```

The API will be available at [http://localhost:8000/docs](http://localhost:8000/docs)

### Endpoints
- `POST /upload-pdf/` — Upload and parse a PDF
- `POST /search/` — Search/query the vector database

### Environment Variables
- `DATABASE_URL` (set automatically in Docker Compose)

### Development
- Edit code in the `app/` directory
- Add your own vector generation and search logic

### Example: LangChain Integration
See `examples/langchain_example.py` (to be added)

## License
MIT
