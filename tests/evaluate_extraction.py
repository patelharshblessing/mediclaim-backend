# scripts/evaluate_extraction.py
import asyncio
import os
import json
import sys
from typing import Dict, Any, Tuple, List

import requests
from fastapi import UploadFile
import io

# Add the root project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Configuration ---
# Update these paths and credentials as needed
PDF_DIR = "/home/harsh/Desktop/Personal_project/mediclaim_backend/tests/medical bills"
GOLDEN_DIR = "/home/harsh/Desktop/Personal_project/mediclaim_backend/tests/true_labels"
API_BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_USERNAME = "harsh-user"
TEST_PASSWORD = "harsh-user"


def get_auth_token() -> str:
    """Logs in and retrieves a JWT access token."""
    print("Authenticating...")
    # Add a proxy bypass for local development if needed
    proxies = {"http": None, "https": None}
    response = requests.post(
        f"{API_BASE_URL}/token",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        proxies=proxies
    )
    response.raise_for_status()
    print("Authentication successful.")
    return response.json()["access_token"]


async def get_prediction(pdf_path: str, token: str) -> Dict[str, Any]:
    """Calls the /extract API and returns the AI's simplified output."""
    headers = {"Authorization": f"Bearer {token}"}
    proxies = {"http": None, "https": None}
    with open(pdf_path, "rb") as f:
        files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
        response = requests.post(f"{API_BASE_URL}/claims/extract", files=files, headers=headers, proxies=proxies)
        response.raise_for_status()
        
        # Strip confidence scores to compare values directly
        data_with_confidence = response.json()
        print(data_with_confidence)
        simple_data = {}
        for key, field in data_with_confidence.items():
            if key != 'line_items' and isinstance(field, dict):
                simple_data[key] = field.get('value')
        
        simple_line_items = []
        if 'line_items' in data_with_confidence:
            for item in data_with_confidence['line_items']:
                simple_item = {key: field.get('value') for key, field in item.items()}
                simple_line_items.append(simple_item)
        simple_data['line_items'] = simple_line_items
        return simple_data


def compare_fields(predicted: Dict[str, Any], golden: Dict[str, Any]) -> Tuple[Dict[str, int], List[str]]:
    """Compares extracted fields and returns stats and a list of specific errors."""
    stats = {"tp": 0, "fp": 0, "fn": 0}
    errors = []
    
    all_keys = set(golden.keys()) | set(predicted.keys())
    
    for key in all_keys:
        if key == 'line_items': continue

        predicted_val = predicted.get(key)
        golden_field = golden.get(key)

        # --- FIX: Extract the 'value' from the golden data if it's a dict ---
        if isinstance(golden_field, dict) and 'value' in golden_field:
            golden_val = golden_field['value']
        else:
            golden_val = golden_field
        
        # Normalize for fair comparison (e.g., handle floats, strings, None)
        g_str = str(golden_val or "").strip().lower()
        p_str = str(predicted_val or "").strip().lower()

        if g_str == p_str:
            stats["tp"] += 1
        else:
            if predicted_val is not None:
                stats["fp"] += 1
                errors.append(f"  - Field '{key}': Expected '{g_str}', but Predicted '{p_str}'")
            if golden_val is not None and predicted_val is None:
                stats["fn"] += 1
                errors.append(f"  - Field '{key}': Expected '{g_str}', but missed (Predicted None)")

    predicted_lines = len(predicted.get('line_items', []))
    golden_lines = len(golden.get('line_items', []))
    if predicted_lines == golden_lines:
        stats["tp"] += 1
    else:
        stats["fp"] += 1
        stats["fn"] += 1
        errors.append(f"  - Field 'line_items': Expected {golden_lines} items, but Predicted {predicted_lines} items")
        
    return stats, errors


def calculate_metrics(stats: Dict[str, int]) -> Dict[str, float]:
    """Calculates precision, recall, and F1-score."""
    tp, fp, fn = stats["tp"], stats["fp"], stats["fn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1_score": f1}


async def main():
    """Main function to run the evaluation."""
    try:
        token = get_auth_token()
        total_stats = {"tp": 0, "fp": 0, "fn": 0}
        all_errors = []

        pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
        
        print(f"\nFound {len(pdf_files)} bills to evaluate...")

        for pdf_file in pdf_files:
            pdf_path = os.path.join(PDF_DIR, pdf_file)
            json_filename = f"{os.path.splitext(pdf_file)[0]}.json"
            golden_path = os.path.join(GOLDEN_DIR, json_filename)
            if not os.path.exists(golden_path): continue

            print(f"\nProcessing: {pdf_file}")
            prediction = await get_prediction(pdf_path, token)
            with open(golden_path, 'r') as f:
                golden = json.load(f)

            file_stats, file_errors = compare_fields(prediction, golden)
            total_stats["tp"] += file_stats["tp"]
            total_stats["fp"] += file_stats["fp"]
            total_stats["fn"] += file_stats["fn"]
            
            if file_errors:
                all_errors.append(f"\n--- Errors in: {pdf_file} ---")
                all_errors.extend(file_errors)

        final_metrics = calculate_metrics(total_stats)

        # Print the final report
        print("\n" + "="*50)
        print("          Extraction Accuracy Report")
        print("="*50)
        print(f"Total True Positives (Correct Fields):  {total_stats['tp']}")
        print(f"Total False Positives (Incorrect Fields): {total_stats['fp']}")
        print(f"Total False Negatives (Missed Fields):  {total_stats['fn']}")
        print("-"*50)
        print(f"Precision: {final_metrics['precision']:.2%}")
        print(f"Recall:    {final_metrics['recall']:.2%}")
        print(f"F1-Score:  {final_metrics['f1_score']:.2%}")
        print("="*50)

        if all_errors:
            print("\n" + "="*50)
            print("          Detailed Error Log")
            print("="*50)
            for error in all_errors:
                print(error)
            print("="*50)
        else:
            print("\n✅ No errors found in any of the processed files!")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ A network or API error occurred: {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())