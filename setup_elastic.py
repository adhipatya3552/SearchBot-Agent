# setup_elastic.py — run this ONCE to create the index
import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

es = Elasticsearch(
    cloud_id=os.getenv("ELASTIC_CLOUD_ID"),
    api_key=os.getenv("ELASTIC_API_KEY")
)

# Delete old index if it exists (fresh start)
if es.indices.exists(index="searchbot_docs"):
    es.indices.delete(index="searchbot_docs")
    print("Deleted old index")

# Create new index with vector search (768 dims = Gemini embedding size)
es.indices.create(
    index="searchbot_docs",
    settings={
        "number_of_shards": 1,
        "number_of_replicas": 0
    },
    mappings={
        "properties": {
            "content":   {"type": "text"},
            "embedding": {
                "type": "dense_vector",
                "dims": 768,
                "index": True,
                "similarity": "cosine"
            },
            "doc_name":  {"type": "keyword"},
            "page_num":  {"type": "integer"},
            "chunk_id":  {"type": "keyword"}
        }
    }
)

print("✅ Elasticsearch index 'searchbot_docs' created successfully!")

es.close()