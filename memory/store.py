import chromadb
from memory.embedder import embed_text
from datetime import datetime

# Creates a local folder called chroma_db/ in your project
# All memories persist here between sessions — this is your long-term memory
client = chromadb.PersistentClient(path="./chroma_db")

# A "collection" is like a table in a normal database
# get_or_create means it won't crash if it already exists
collection = client.get_or_create_collection(
    name="coding_sessions",
    metadata={"heuristic": "cosine"}  # cosine similarity = best for text/meaning
)

def save_session(code: str, review: str, weak_spot: str):
    """
    After every code review, save:
    - The code submitted
    - The review given  
    - The weak spot detected (e.g. 'error handling', 'recursion')
    
    We embed the review text because that's what contains the meaningful feedback.
    """
    embedding = embed_text(review)
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    collection.add(
        ids=[session_id],
        embeddings=[embedding],
        documents=[review],          # the full review text
        metadatas=[{
            "code": code[:500],      # first 500 chars of code (ChromaDB metadata limit)
            "weak_spot": weak_spot[:40],  # cleaner truncation
            "timestamp": datetime.now().isoformat()
        }]
    )
    print(f"Memory saved: {session_id} | Weak spot: {weak_spot}")

def get_past_mistakes(current_code: str, n_results: int = 3) -> str:
    """
    Before reviewing new code, search for the most relevant past mistakes.
    Returns a formatted string that gets injected into the LLM prompt.
    
    n_results=3 means top 3 most similar past sessions.
    """
    # Need at least one session saved before we can search
    if collection.count() == 0:
        return "None yet — this is the first session."
    
    embedding = embed_text(current_code)
    
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(n_results, collection.count())  # can't fetch more than exists
    )
    
    if not results["documents"][0]:
        return "No relevant past mistakes found."
    
    # Format the past mistakes nicely for the LLM prompt
    past = []
    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        weak_spot = meta.get("weak_spot", "unknown")
        timestamp = meta.get("timestamp", "")[:10]  # just the date
        past.append(f"Session {i+1} ({timestamp}) — Weak spot: {weak_spot}\nFeedback: {doc[:300]}...")
    
    return "\n\n".join(past)

def get_weakness_summary() -> dict:
    """
    Counts how many times each weak spot appeared across all sessions.
    Used later to build the heatmap in the Streamlit dashboard.
    """
    if collection.count() == 0:
        return {}
    
    all_data = collection.get()
    weakness_count = {}
    
    for meta in all_data["metadatas"]:
        spot = meta.get("weak_spot", "unknown")
        weakness_count[spot] = weakness_count.get(spot, 0) + 1
    
    return weakness_count