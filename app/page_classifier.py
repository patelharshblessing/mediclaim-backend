#app/page_classifier.py
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List

import fitz  # PyMuPDF
import joblib
from google.cloud import vision
from sentence_transformers import SentenceTransformer

# --- Configuration ---
# Sunishchit karein ki yeh files aapke project ke root folder mein hain
MODEL_FILE = "best_xgboost_classifier.joblib"
LABEL_ENCODER_FILE = "label_encoder.joblib"
SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"


class PageClassifier:
    """
    A service to classify pages from a PDF as 'relevant' or 'irrelevant'.

    This class loads a pre-trained text classification model and uses Google
    Cloud Vision OCR to extract text from each page, ensuring it can handle
    both text-based and image-based PDFs.
    """

    def __init__(self):
        """
        Initializes the classifier by loading all necessary models.
        This is done only once when the application starts.
        """
        print("🧠 Initializing the custom Page Classifier...")
        try:
            self.classifier = joblib.load(MODEL_FILE)
            self.label_encoder = joblib.load(LABEL_ENCODER_FILE)
            self.st_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
            # Google Vision client ko thread-safe use ke liye yahan initialize karein
            self.vision_client = vision.ImageAnnotatorClient()
            print("✅ Page Classifier initialized successfully.")
        except FileNotFoundError as e:
            print(f"❌ CRITICAL ERROR: Could not find a model file: {e}")
            print("Please make sure the trained model files exist in the root directory.")
            raise

    def _extract_text_with_ocr(self, image_bytes: bytes) -> str:
        """Helper function to extract text from a single image using OCR."""
        try:
            image = vision.Image(content=image_bytes)
            response = self.vision_client.document_text_detection(image=image)
            if response.error.message:
                raise Exception(f"Vision API Error: {response.error.message}")
            return response.full_text_annotation.text or ""
        except Exception as e:
            print(f"OCR failed for a page: {e}")
            return ""

    async def classify_pages(self, pdf_content: bytes) -> List[bool]:
        """
        Classifies all pages of a given PDF in parallel.

        Args:
            pdf_content: The raw bytes of the PDF file.

        Returns:
            A list of booleans, where True means 'relevant' and False
            means 'irrelevant', corresponding to each page.
        """
        print(f"📄 Starting classification for a PDF with {len(pdf_content)} bytes...")
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return []

        page_images = []
        for page in doc:
            # High DPI for better OCR accuracy
            pix = page.get_pixmap(dpi=300)
            page_images.append(pix.tobytes("png"))
        doc.close()

        print(f"Found {len(page_images)} pages. Extracting text in parallel...")

        # Use an event loop and a thread pool for parallel OCR calls
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            tasks = [
                loop.run_in_executor(pool, self._extract_text_with_ocr, img)
                for img in page_images
            ]
            extracted_texts = await asyncio.gather(*tasks)

        print("Text extraction complete. Creating vector embeddings...")
        
        # Filter out pages where OCR might have failed
        valid_texts = [text for text in extracted_texts if text]
        if not valid_texts:
            print("⚠️ No text could be extracted from any page.")
            return [False] * len(page_images)

        # Convert text to vectors
        vectors = self.st_model.encode(valid_texts, show_progress_bar=False)

        print("Predicting labels with the custom XGBoost model...")
        predictions_encoded = self.classifier.predict(vectors)
        
        # Convert numerical predictions (0, 1) back to labels ('irrelevant', 'relevant')
        predicted_labels = self.label_encoder.inverse_transform(predictions_encoded)
        
        # Create the final boolean list
        is_relevant_list = [label == "relevant" for label in predicted_labels]
        
        print(f"✅ Classification complete. Found {sum(is_relevant_list)} relevant page(s).")
        return is_relevant_list

# # --- Example Usage (How to test this file) ---
# async def main_test():
#     """A simple async function to test the classifier."""
#     # Replace this with a path to a multi-page PDF for testing
#     # test_pdf_path = "/home/harsh/mediclaim_backend/dataset/original_bills/6437344-Medical-Billing-Simple-Manual.pdf"
#     test_pdf_path = "/home/harsh/mediclaim_backend/dataset/original_bills/claim_document/bill10.pdf"
    
#     if not os.path.exists(test_pdf_path):
#         print(f"Test file not found at: {test_pdf_path}")
#         return

#     with open(test_pdf_path, "rb") as f:
#         pdf_bytes = f.read()

#     classifier = PageClassifier()
#     results = await classifier.classify_pages(pdf_bytes)
    
#     print("\n--- Classification Results ---")
#     for i, result in enumerate(results):
#         print(f"Page {i+1}: {'Relevant' if result else 'Irrelevant'}")

# if __name__ == "__main__":
#     # To run this test, you'd need an async context
#     asyncio.run(main_test())
#     print("This is the PageClassifier module. It should be imported, not run directly.")