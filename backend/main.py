import os
import tempfile
import threading
import shutil
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from ingest import ingest_document, delete_document, list_documents, ingest_document_generator
from agent import agent
from elastic_mcp import elastic_mcp

load_dotenv()

# ─── App Setup ──────────────────────────────────────────────────────
app = FastAPI(
    title="SearchBot Agent API",
    description="AI-powered document search using Gemini + Elasticsearch",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ─── Models ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    status: str

# ─── Health Check ───────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "app":     "SearchBot Agent",
        "status":  "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

# ─── Document Routes ────────────────────────────────────────────────
@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document file and index it in Elasticsearch (streaming progress)"""

    # Validate file type
    allowed_extensions = (".pdf", ".txt", ".docx", ".csv", ".md")
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {', '.join(allowed_extensions)}"
        )

    # Validate file size (max 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB"
        )

    # Save to temp file
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    def generate_progress():
        try:
            for update in ingest_document_generator(tmp_path, file.filename):
                yield json.dumps(update) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    return StreamingResponse(generate_progress(), media_type="text/event-stream")

@app.get("/documents")
def get_documents():
    """List all indexed documents"""
    docs = list_documents()
    return {"documents": docs, "count": len(docs)}

@app.delete("/documents/{doc_name}")
def remove_document(doc_name: str):
    """Remove a document from the index"""
    result = delete_document(doc_name)
    return {
        "status":  "success",
        "message": f"'{doc_name}' removed",
        "deleted": result["deleted"]
    }

# ─── Agent Routes ────────────────────────────────────────────────────
@app.post("/ask", response_model=AskResponse)
def ask_question(body: AskRequest):
    """Ask a question — agent searches docs and answers with citations"""

    if not body.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    # Fire Elastic MCP in background (required for hackathon track) — non-blocking
    threading.Thread(
        target=elastic_mcp.search_via_mcp,
        args=(body.question,),
        daemon=True
    ).start()

    answer = agent.ask(body.question)
    return AskResponse(answer=answer, status="success")

@app.post("/reset")
def reset_conversation():
    """Clear conversation history"""
    agent.reset()
    return {"status": "success", "message": "Conversation reset"}

@app.get("/mcp/status")
def mcp_status():
    """Check Elastic MCP connection status"""
    info = elastic_mcp.get_agent_info()
    return {"status": "connected", "info": info}