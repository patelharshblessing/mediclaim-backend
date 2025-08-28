# app/normalization_service.py

import faiss
import pickle
import numpy as np
import sys
import os
# Add the root project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sentence_transformers import SentenceTransformer
from app.data.master_data import MASTER_ITEM_LIST

# --- Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2'
INDEX_PATH = "app/data/medical_items.index"
ID_MAP_PATH = "app/data/master_item_ids.pkl"
SIMILARITY_THRESHOLD = 0.5  # Similarity score must be above this to be considered a match

class NormalizationService:
    """
    A service to normalize medical item descriptions using a vector database.
    """
    def __init__(self):
        print("Initializing Normalization Service...")
        try:
            self.model = SentenceTransformer(MODEL_NAME)
            self.index = faiss.read_index(INDEX_PATH)
            
            with open(ID_MAP_PATH, 'rb') as f:
                self.id_map = pickle.load(f)
            
            # Create a fast lookup dictionary from the master list
            self.master_data_map = {item['id']: item for item in MASTER_ITEM_LIST}
            print("✅ Normalization Service loaded successfully.")

        except FileNotFoundError:
            print("\n❌ ERROR: Index files not found.")
            print("Please run the 'scripts/build_vector_db.py' script first to create the index.")
            raise

    def normalize_description(self, description: str) -> dict | None:
        """
        Finds the closest matching canonical item for a given raw description.

        Args:
            description: The raw text from the bill (e.g., "fee for dr visit").

        Returns:
            The full master item dictionary if a confident match is found, otherwise None.
        """
        # 1. Encode the input description into a query vector
        query_vector = self.model.encode([description], convert_to_numpy=True)
        faiss.normalize_L2(query_vector)

        # 2. Search the FAISS index for the single closest match (k=1)
        # The 'distances' are cosine similarities, 'indices' are the positions
        distances, indices = self.index.search(query_vector, k=1)
        
        best_match_index = indices[0][0]
        best_match_similarity = distances[0][0]

        # 3. Check if the match is good enough
        if best_match_similarity >= SIMILARITY_THRESHOLD:
            # 4. Translate the index position back to our canonical ID
            matched_id = self.id_map[best_match_index]
            
            # 5. Return the full master data record for that ID
            return self.master_data_map.get(matched_id)
        else:
            # The best match was not similar enough, so we can't be confident.
            print(f"No confident match for '{description}'. Best similarity: {best_match_similarity:.2f} of '{self.id_map[best_match_index]}'")
            return None

# We can create a single instance to be used throughout the app