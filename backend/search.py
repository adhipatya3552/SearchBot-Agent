import os
import google.generativeai as genai
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

es = Elasticsearch(
    cloud_id=os.getenv("ELASTIC_CLOUD_ID"),
    api_key=os.getenv("ELASTIC_API_KEY")
)

def get_query_embedding(query: str) -> list:
    """Get embedding for search query"""
    result = genai.embed_content(
        model="models/gemini-embedding-2",
        content=query,
        task_type="retrieval_query",   # different task type for queries
        output_dimensionality=768
    )
    return result["embedding"]

def semantic_search(query: str, top_k: int = 5) -> list:
    """Pure vector similarity search"""
    query_embedding = get_query_embedding(query)

    result = es.search(
        index="searchbot_docs",
        knn={
            "field":        "embedding",
            "query_vector": query_embedding,
            "k":            top_k,
            "num_candidates": 50
        },
        source=["content", "doc_name", "page_num"]
    )

    return _format_hits(result)

def hybrid_search(query: str, top_k: int = 6) -> list:
    """
    Hybrid search = keyword search + vector search combined.
    This gives better results than either method alone.
    """
    query_embedding = get_query_embedding(query)

    result = es.search(
        index="searchbot_docs",
        query={
            "match": {
                "content": {
                    "query": query,
                    "boost": 0.3   # weight for keyword match
                }
            }
        },
        knn={
            "field":          "embedding",
            "query_vector":   query_embedding,
            "k":              top_k,
            "num_candidates": 50,
            "boost":          0.7   # weight for semantic match
        },
        size=top_k,
        source=["content", "doc_name", "page_num"]
    )

    return _format_hits(result)

def _format_hits(result: dict) -> list:
    """Format Elasticsearch hits into clean list"""
    hits = []
    seen = set()

    for hit in result["hits"]["hits"]:
        src = hit["_source"]
        key = f"{src['doc_name']}_p{src['page_num']}"

        if key not in seen:
            seen.add(key)
            hits.append({
                "content":  src["content"],
                "doc_name": src["doc_name"],
                "page_num": src["page_num"],
                "score":    round(hit["_score"], 4)
            })

    return hits