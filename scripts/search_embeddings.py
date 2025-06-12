import os
import json
import numpy as np
import openai
from config.settings import DOC_EMBEDDINGS_PATH

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_query_embedding(query, model="text-embedding-3-large"):
    # Or "text-embedding-ada-002" for legacy
    try:
        resp = openai.embeddings.create(input=[query], model=model)
    except openai.AuthenticationError:
        print(
            "OpenAI authentication failed. Please set the OPENAI_API_KEY environment variable with a valid API key."
        )
        return None
    return np.array(resp.data[0].embedding, dtype=np.float32)

def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)

def search_embeddings(query, top_k=3):
    """Semantic search with OpenAI embeddings."""
    with open(DOC_EMBEDDINGS_PATH, "r", encoding="utf-8") as f:
        embeddings = json.load(f)
    # Get embedding for query
    query_emb = get_query_embedding(query)
    if query_emb is None:
        return []
    # For each doc chunk, compute similarity
    results = []
    for chunk in embeddings:
        chunk_emb = np.array(chunk["embedding"], dtype=np.float32)
        sim = cosine_sim(query_emb, chunk_emb)
        results.append({
            "similarity": float(sim),
            "chunk": chunk.get("chunk", ""),
            "document": chunk.get("document", ""),
        })
    # Sort by similarity descending, return top_k
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]
