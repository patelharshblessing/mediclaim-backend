import fitz  # PyMuPDF
from google.cloud import vision
from typing import List

def extract_text_from_pdf_with_ocr(pdf_path: str) -> str:
    """
    Extracts all text from a multi-page PDF using Google Cloud Vision API.

    This function converts each page of the PDF into a high-resolution image
    and sends it to Google's Document Text Detection service for accurate OCR.

    Args:
        pdf_path: The full path to the PDF file.

    Returns:
        A single string containing all the extracted text from all pages,
        separated by newlines.
    """
    all_text = []
    
    try:
        # 1. Initialize the Google Vision Client
        client = vision.ImageAnnotatorClient()
        
        # 2. Open the PDF file
        doc = fitz.open(pdf_path)

        # 3. Iterate through each page of the PDF
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # 4. Convert the page to a high-resolution image for better OCR
            pix = page.get_pixmap(dpi=300)
            image_bytes = pix.tobytes("png")
            
            # 5. Prepare the image for the Vision API
            image = vision.Image(content=image_bytes)
            
            # 6. Call the API for document text detection
            print(f"  - Sending page {page_num + 1}/{len(doc)} to Google Cloud Vision...")
            response = client.document_text_detection(image=image)

            if response.error.message:
                raise Exception(
                    f"Google Cloud Vision API error on page {page_num + 1}: {response.error.message}"
                )
            
            # 7. Append the extracted text for the page
            if response.full_text_annotation:
                all_text.append(response.full_text_annotation.text)

        doc.close()
        
    except Exception as e:
        print(f"\nAn error occurred while processing {pdf_path}: {e}")
        return "" # Return empty string on failure

    # 8. Join all the text together and return
    return "\n".join(all_text)

# --- Example Usage (How to test this function) ---
# if __name__ == '__main__':
#     # Replace this with the path to one of your single-page PDF files
#     # from the 'labeled_dataset/relevant/' folder to test.
#     test_pdf_path = '/home/harsh/mediclaim_backend/dataset/output_folder/relevant/205064886-Medical-Bill_page_1.pdf' 
    
#     print(f"Extracting text from: {test_pdf_path}")
#     extracted_content = extract_text_from_pdf_with_ocr(test_pdf_path)
    
#     print("\n--- Extracted Content ---")
#     print(extracted_content)
#     print("\n-------------------------")
