"""Small, real Chroma vector retrieval + Gemini Text-to-SQL pipeline."""
import os
import re
from functools import lru_cache

import chromadb
from google import genai
from sklearn.feature_extraction.text import HashingVectorizer

# Stateless, deterministic embeddings: no model download, API key, or training needed.
# Chroma performs vector similarity search on these 512-dimensional vectors.
_EMBEDDER = HashingVectorizer(n_features=512, alternate_sign=False, norm="l2", ngram_range=(1, 2))


def _embed(texts):
    return _EMBEDDER.transform(texts).toarray().astype(float).tolist()


def _knowledge(questions):
    docs = [
        "PostgreSQL schema: public.restaurants(name text, address text, distance_miles numeric, rating numeric, cuisine text, avg_cost numeric, personal_rank integer). One row per restaurant. All quiz questions query only restaurants.",
        "Column meanings: name is restaurant name; distance_miles is distance in miles; rating is review rating (higher is better); cuisine is cuisine category; avg_cost is average price in dollars; personal_rank is a personal ordering. PostgreSQL syntax only.",
        "Business rules: nearby means distance_miles <= 2.0; highly rated means rating >= 4.5; sales tax is 7.5 percent, so after-tax price is ROUND(avg_cost * 1.075, 2).",
        "SQL guidance: SELECT only; use ORDER BY for ranking; GROUP BY cuisine and COUNT(*) for counts; do not invent columns, tables, or joins. Preserve requested output column aliases and ordering.",
    ]
    for q in questions:
        docs.append(f"SQL example {q['id']}: Question: {q['description']}\nSQL:\n{q['hint_sql'].strip()}")
    return docs


@lru_cache(maxsize=1)
def _vector_store_cached(knowledge):
    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection(name="restaurant_sql_knowledge", metadata={"hnsw:space": "cosine"})
    docs = list(knowledge)
    collection.upsert(ids=[f"knowledge_{i}" for i in range(len(docs))], documents=docs, embeddings=_embed(docs))
    return collection


def retrieve_context(question, questions, top_k=4):
    """Perform ACTUAL ChromaDB nearest-neighbor vector retrieval."""
    docs = _knowledge(questions)
    collection = _vector_store_cached(tuple(docs))
    results = collection.query(query_embeddings=_embed([question]), n_results=min(top_k, len(docs)), include=["documents", "distances"])
    return [{"document": doc, "distance": float(distance)} for doc, distance in zip(results["documents"][0], results["distances"][0])]


def generate_sql(question, questions, model=None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to .env locally or Streamlit Cloud Secrets.")
    if not question.strip():
        raise ValueError("Enter a natural-language question.")
    retrieved = retrieve_context(question, questions)
    context = "\n\n".join(f"Context {i+1}:\n{hit['document']}" for i, hit in enumerate(retrieved))
    prompt = (
        "You are a PostgreSQL text-to-SQL assistant. Generate exactly ONE read-only SELECT statement "
        "using only the restaurants table. Use the retrieved context to identify column names and SQL patterns. "
        "Return SQL only, no explanation or markdown fences. Never write modifications or multiple statements.\n\n"
        f"RETRIEVED KNOWLEDGE:\n{context}\n\nUSER QUESTION:\n{question}"
    )
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=prompt)
    raw = (response.text or "").strip()
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
    if not re.match(r"^SELECT\b", sql, flags=re.IGNORECASE) or ";" in sql.rstrip(";"):
        raise ValueError("The AI did not return one safe SELECT statement. Try again.")
    return sql, retrieved
