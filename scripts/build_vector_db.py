import os
import sys
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Add the root project directory to the Python path
# This allows us to import from the 'app' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.data.master_data import MASTER_ITEM_LIST

# --- Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2'
INDEX_PATH = "app/data/medical_items.index"
ID_MAP_PATH = "app/data/master_item_ids.pkl"


def build_vector_database():
    """
    Encodes the master item list and builds a FAISS index for vector search.
    """
    print(f"Loading sentence transformer model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    # 1. Prepare the data
    # We need a list of the names to encode and a list of the original IDs
    item_names = [item['name'] for item in MASTER_ITEM_LIST]
    item_ids = [item['id'] for item in MASTER_ITEM_LIST]

    if not item_names:
        print("Master item list is empty. Aborting.")
        return

    # 2. Encode the item names into vectors
    print(f"Encoding {len(item_names)} item names into vectors. This may take a moment...")
    embeddings = model.encode(item_names, show_progress_bar=True, convert_to_numpy=True)
    
    # Normalize embeddings for cosine similarity search (optional but good practice)
    faiss.normalize_L2(embeddings)
    
    vector_dimension = embeddings.shape[1]
    print(f"Embeddings created with dimension: {vector_dimension}")

    # 3. Build the FAISS index
    print("Building the FAISS index...")
    # Using IndexFlatIP for cosine similarity after normalization
    index = faiss.IndexFlatIP(vector_dimension)
    index.add(embeddings)

    # 4. Save the index and the ID map
    print(f"Saving FAISS index to {INDEX_PATH}")
    faiss.write_index(index, INDEX_PATH)

    print(f"Saving ID map to {ID_MAP_PATH}")
    with open(ID_MAP_PATH, 'wb') as f:
        pickle.dump(item_ids, f)
        
    print("\n✅ Vector database build complete!")
    print(f"Indexed {index.ntotal} items.")


if __name__ == "__main__":
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    build_vector_database()