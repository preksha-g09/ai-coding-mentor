from sentence_transformers import SentenceTransformer

# This model is small (90MB), fast, and great for code + text similarity
# Downloads once, cached forever after
model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_text(text: str) -> list:
    """
    Converts any string into a 384-dimensional vector.
    Similar meaning = similar vector = ChromaDB finds it.
    """
    embedding = model.encode(text, convert_to_tensor=False)
    return embedding.tolist()