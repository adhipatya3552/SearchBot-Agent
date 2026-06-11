import os
import uuid
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

# Initialize clients
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

es = Elasticsearch(
    cloud_id=os.getenv("ELASTIC_CLOUD_ID"),
    api_key=os.getenv("ELASTIC_API_KEY")
)

def get_embedding(text: str) -> list:
    """Get embedding vector from Gemini API"""
    response = client.models.embed_content(
        model="gemini-embedding-2",
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768
        )
    )
    return response.embeddings[0].values

def extract_chunks(file_path: str, doc_name: str, chunk_size: int = 400) -> list:
    """Extract text from PDF, DOCX, CSV, TXT, or MD, and split into chunks"""
    import os
    ext = os.path.splitext(doc_name)[1].lower()
    chunks = []

    if ext == ".pdf":
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().strip()
            if not text or len(text) < 50:
                continue

            # Split page text into chunks of ~400 words
            words = text.split()
            for i in range(0, len(words), chunk_size):
                chunk_text = " ".join(words[i : i + chunk_size])
                if len(chunk_text) > 100:
                    chunks.append({
                        "content":  chunk_text,
                        "page_num": page_num + 1
                    })
        doc.close()
    else:
        # Extract full text for docx, csv, txt, md, etc.
        full_text = ""
        try:
            if ext == ".docx":
                import docx
                doc = docx.Document(file_path)
                full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            elif ext == ".csv":
                import csv
                lines = []
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row:
                            lines.append(" | ".join(row))
                full_text = "\n".join(lines)
            else:  # txt, md, etc.
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    full_text = f.read().strip()
        except Exception as e:
            print(f"   Error reading file {doc_name}: {e}")
            return []

        if not full_text or len(full_text) < 50:
            return []

        # Chunk the entire text and simulate pages (~500 words per page)
        words = full_text.split()
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i : i + chunk_size])
            if len(chunk_text) > 100:
                simulated_page_num = (i // 500) + 1
                chunks.append({
                    "content":  chunk_text,
                    "page_num": simulated_page_num
                })
    return chunks

def ingest_document_generator(file_path: str, doc_name: str):
    """Generator version of ingest_document that yields progress data chunk by chunk"""
    print(f"📄 Processing (streaming): {doc_name}")

    # Step 1: Extract text chunks
    chunks = extract_chunks(file_path, doc_name)
    total_chunks = len(chunks)

    if not total_chunks:
        yield {
            "type": "error",
            "message": "No readable text found in document"
        }
        return

    print(f"   Found {total_chunks} chunks, creating embeddings...")

    # Step 2: Create embeddings and index each chunk
    indexed = 0
    errors = 0

    for i, chunk in enumerate(chunks, 1):
        try:
            embedding = get_embedding(chunk["content"])

            doc = {
                "doc_name":  doc_name,
                "page_num":  chunk["page_num"],
                "content":   chunk["content"],
                "embedding": embedding,
                "chunk_id":  str(uuid.uuid4())
            }

            es.index(index="searchbot_docs", document=doc)
            indexed += 1

        except Exception as e:
            print(f"   Error indexing chunk: {e}")
            errors += 1

        yield {
            "type": "progress",
            "current": i,
            "total": total_chunks,
            "doc_name": doc_name
        }

    print(f"✅ Indexed {indexed} chunks | Errors: {errors}")

    yield {
        "type":           "complete",
        "status":         "success",
        "doc_name":       doc_name,
        "chunks_indexed": indexed,
        "errors":         errors
    }

def ingest_document(file_path: str, doc_name: str) -> dict:
    """Full pipeline: PDF/DOCX/CSV/TXT/MD → chunks → embeddings → Elasticsearch"""
    res = {}
    for update in ingest_document_generator(file_path, doc_name):
        if update["type"] == "complete":
            res = {
                "status":         update["status"],
                "doc_name":       update["doc_name"],
                "chunks_indexed": update["chunks_indexed"],
                "errors":         update["errors"]
            }
        elif update["type"] == "error":
            res = {
                "status": "error",
                "message": update["message"]
            }
    return res

def delete_document(doc_name: str) -> dict:
    """Remove all chunks of a document from Elasticsearch"""
    result = es.delete_by_query(
        index="searchbot_docs",
        query={
            "term": {"doc_name": doc_name}
        }
    )
    deleted = result.get("deleted", 0)
    print(f"🗑️ Deleted {deleted} chunks for '{doc_name}'")
    return {"status": "success", "deleted": deleted}

def list_documents() -> list:
    """Get all unique document names stored in Elasticsearch"""
    try:
        result = es.search(
            index="searchbot_docs",
            size=0,
            aggs={
                "unique_docs": {
                    "terms": {
                        "field": "doc_name",
                        "size": 100
                    }
                }
            }
        )
        return [
            b["key"]
            for b in result["aggregations"]["unique_docs"]["buckets"]
        ]
    except Exception:
        return []