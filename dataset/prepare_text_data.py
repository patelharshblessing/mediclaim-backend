import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz  # PyMuPDF
import pandas as pd
from google.cloud import vision

# --- NEW: Import the tenacity library for retries ---
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

# --- Configuration ---
LABELED_DATA_FOLDER = "./dataset/labeled_dataset"
OUTPUT_CSV_FILE = "training_data.csv"
MAX_WORKERS = 20


# --- NEW: Add a @retry decorator to the API call function ---
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=60),  # Wait 2s, then 4s, 8s, etc.
    stop=stop_after_attempt(3),  # Try a maximum of 3 times
    reraise=True,  # If all retries fail, re-raise the last exception
)
def extract_text_from_single_page_pdf(pdf_path: str) -> str:
    """
    Extracts text from a single-page PDF using Google Cloud Vision API.
    This function will automatically retry on transient network errors.
    """
    # NOTE: The logic inside the function does not need to change.
    # The @retry decorator automatically wraps it.
    try:
        client = vision.ImageAnnotatorClient()
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=300)
        image_bytes = pix.tobytes("png")
        doc.close()

        image = vision.Image(content=image_bytes)
        response = client.document_text_detection(image=image)

        if response.error.message:
            # We raise an exception to let tenacity know it should retry
            raise Exception(f"Google Cloud Vision API error: {response.error.message}")

        return (
            response.full_text_annotation.text if response.full_text_annotation else ""
        )

    except Exception as e:
        # Re-raise the exception so tenacity can catch it and decide whether to retry
        raise e


def process_single_file(file_info: tuple) -> dict:
    """
    Helper function to process one file: extract text, clean it, and return a dictionary.
    """
    pdf_path, label = file_info
    filename = os.path.basename(pdf_path)

    try:
        # Call the new, retry-enabled function
        extracted_text = extract_text_from_single_page_pdf(pdf_path)
        cleaned_text = " ".join(extracted_text.split()).strip()

        if cleaned_text:
            return {"filename": filename, "text": cleaned_text, "label": label}
    except Exception as e:
        # If all retries fail, print an error and continue with other files
        print(f"\nFailed to process {filename} after multiple retries. Error: {e}")

    return None


# --- Main Script Logic (remains unchanged) ---
def create_training_dataset():
    """
    Main function to process all labeled PDFs in parallel and create a final CSV.
    """
    print(f"🚀 Starting dataset preparation...")
    # ... (the rest of the main function is exactly the same)
    # --- NEW: Resumable Logic ---
    processed_files = set()
    if os.path.exists(OUTPUT_CSV_FILE):
        print(
            f"Found existing output file '{OUTPUT_CSV_FILE}'. Will resume processing."
        )
        df_existing = pd.read_csv(OUTPUT_CSV_FILE)
        processed_files = set(df_existing["filename"])
        print(f"Found {len(processed_files)} already processed files.")
    # --- END NEW ---

    all_files_to_process = []
    categories = ["relevant", "irrelevant"]

    for category in categories:
        folder_path = os.path.join(LABELED_DATA_FOLDER, category)
        if not os.path.isdir(folder_path):
            print(f"\n⚠️ Warning: Subfolder '{category}' not found. Skipping.")
            continue

        for filename in os.listdir(folder_path):
            # --- NEW: Check if file has already been processed ---
            if filename.lower().endswith(".pdf") and filename not in processed_files:
                pdf_path = os.path.join(folder_path, filename)
                all_files_to_process.append((pdf_path, category))

    if not all_files_to_process:
        print("\n✅ All files have already been processed. Nothing to do.")
        return

    print(
        f"\nFound a total of {len(all_files_to_process)} new files to process. Starting parallel processing..."
    )

    newly_processed_data = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(process_single_file, file_info): file_info
            for file_info in all_files_to_process
        }

        for future in tqdm(
            as_completed(future_to_file),
            total=len(all_files_to_process),
            desc="Processing files",
        ):
            result = future.result()
            if result:
                newly_processed_data.append(result)

    if not newly_processed_data:
        print(
            "\n❌ Error: No new data was extracted. The output file will not be changed."
        )
        return

    # --- NEW: Append to existing CSV instead of overwriting ---
    print("\n---")
    print("✅ All new files processed! Updating the final CSV file...")
    df_new = pd.DataFrame(newly_processed_data)

    if os.path.exists(OUTPUT_CSV_FILE):
        # Check if df_existing is defined
        if "df_existing" not in locals():
            df_existing = pd.DataFrame()
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_final = df_new

    df_final.to_csv(OUTPUT_CSV_FILE, index=False)

    print(
        f"\n🎉 Successfully updated '{OUTPUT_CSV_FILE}'. It now contains {len(df_final)} records!"
    )
    print("\nHere's a sample of the newly added data:")
    print(df_new.head())


if __name__ == "__main__":
    create_training_dataset()
