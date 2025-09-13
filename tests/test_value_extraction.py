# tests/test_value_extractor.py

import asyncio
import io
import os
import sys

from fastapi import UploadFile

# Add the root project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app.pydantic_schemas import ExtractedDataWithConfidence
    from app.value_extractor import extract_data_from_bill
except (ImportError, FileNotFoundError) as e:
    print(
        f"\nERROR: Could not import necessary modules. Please check your project structure and file names."
    )
    print(f"Details: {e}")
    sys.exit(1)

# --- Configuration ---
# IMPORTANT: Place a sample PDF file in your project's root directory
# and update this filename if it's different.
TEST_PDF_PATH = "/home/harsh/Desktop/Personal_project/mediclaim_backend/tests/medical bills/205064886-Medical-Bill.pdf"


def print_result(data: ExtractedDataWithConfidence):
    """Prints the extracted data in a readable format."""
    print("\n--- ✅ AI Extraction Successful ---")

    def print_field(name, field):
        print(
            f"{name:<20} | Value: {str(field.value):<30} | Confidence: {field.confidence:.2f}"
        )

    print_field("Hospital Name", data.hospital_name)
    print_field("Patient Name", data.patient_name)
    print_field("Bill Number", data.bill_no)
    print_field("Bill Date", data.bill_date)
    print_field("Admission Date", data.admission_date)
    print_field("Discharge Date", data.discharge_date)
    print("\n--- Line Items ---")
    for i, item in enumerate(data.line_items):
        print(f"\n[Item {i+1}]")
        print_field("  Description", item.description)
        print_field("  Quantity", item.quantity)
        print_field("  Unit Price", item.unit_price)
        print_field("  Total Amount", item.total_amount)

    print("\n--- Totals ---")
    print_field("Gross Amount", data.gross_amount)
    print_field("Net Payable Amount", data.net_payable_amount)
    print("------------------------------------")


async def run_test():
    """
    Main function to run the extraction test.
    """
    print(f"--- Starting Value Extraction Test ---")
    print(f"Attempting to read test file: '{TEST_PDF_PATH}'")

    if not os.path.exists(TEST_PDF_PATH):
        print(f"\n❌ ERROR: Test file not found at '{TEST_PDF_PATH}'.")
        print("Please place a sample PDF in the root of your project directory.")
        return

    try:
        # Simulate a FastAPI UploadFile object
        with open(TEST_PDF_PATH, "rb") as f:
            pdf_bytes = f.read()
            file_like_object = io.BytesIO(pdf_bytes)
            upload_file = UploadFile(file=file_like_object, filename=TEST_PDF_PATH)

            print("File loaded. Calling the extraction service...")
            # Call the actual extraction function
            result = await extract_data_from_bill(upload_file)

            # Print the formatted results
            print_result(result)

    except Exception as e:
        print(f"\n❌ An error occurred during the test: {e}")


# --- Main execution block ---
if __name__ == "__main__":
    # Use asyncio.run() to execute the async test function
    asyncio.run(run_test())
