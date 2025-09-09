# app/ai_processor.py
import base64
import json
from fastapi import UploadFile, HTTPException, status
from pdf2image import convert_from_bytes
from pydantic import ValidationError
import httpx

from .config import settings
from .pydantic_schemas import ExtractedDataWithConfidence

# --- The Master Prompt (remains the same) ---
MASTER_PROMPT = """
Your task is to act as an expert data extraction agent for Indian medical bills.
Analyze the provided image(s) of a hospital bill and respond ONLY with a valid JSON object
that strictly follows the schema provided below.
For every field, you must provide the extracted `value` and a `confidence` score from 0.0 to 1.0.
...
(The rest of your detailed prompt remains here)
...
JSON Output Structure:
{
  "hospital_name": { "value": "String", "confidence": "Float" },
  "patient_name": { "value": "String", "confidence": "Float" },
  "bill_no": { "value": "String", "confidence": "Float" },
  "bill_date": { "value": "YYYY-MM-DD", "confidence": "Float" },
  "admission_date": { "value": "YYYY-MM-DD", "confidence": "Float" },
  "discharge_date": { "value": "YYYY-MM-DD", "confidence": "Float" },
  "net_payable_amount": { "value": "Float", "confidence": "Float" },
  "line_items": [
    {
      "description": { "value": "String", "confidence": "Float" },
      "quantity": { "value": "Float", "confidence": "Float" },
      "unit_price": { "value": "Float", "confidence": "Float" },
      "total_amount": { "value": "Float", "confidence": "Float" }
    }
  ]
}
"""

def convert_pdf_to_base64_images(file_content: bytes) -> list[str]:
    """Converts all pages of a PDF to Base64 encoded JPEG images."""
    try:
        images = convert_from_bytes(file_content, fmt='jpeg')
        if not images:
            raise ValueError("Could not convert PDF to images.")
        
        base64_images = []
        for image in images:
            import io
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            base64_images.append(base64.b64encode(buffered.getvalue()).decode('utf-8'))
        
        return base64_images
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to process PDF: {e}")

async def extract_data_from_bill(file: UploadFile) -> ExtractedDataWithConfidence:
    """
    Orchestrates file conversion and AI data extraction using the Gemini 2.5 Pro model.
    """
    file_content = await file.read()
    base64_images = convert_pdf_to_base64_images(file_content)
    
    # --- NEW: Gemini API Call ---
    GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={settings.GEMINI_API_KEY}"

    # Construct the parts of the request: one text part and multiple image parts
    request_parts = [{"text": MASTER_PROMPT}]
    for image_data in base64_images:
        request_parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": image_data
            }
        })

    # Construct the final payload
    payload = {
        "contents": [{"parts": request_parts}],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }

    try:
        # Use an async HTTP client to make the API call
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(GEMINI_API_URL, json=payload)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # Extract the JSON string from the Gemini response
        result = response.json()
        ai_response_str = result['candidates'][0]['content']['parts'][0]['text']
        ai_response_json = json.loads(ai_response_str)

        # Validate the AI's response against our Pydantic schema
        validated_data = ExtractedDataWithConfidence(**ai_response_json)
        
        return validated_data
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from Gemini API: {e.response.text}")
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(status_code=500, detail="AI returned a malformed or unexpected response.")
    except ValidationError as e:
        raise HTTPException(status_code=500, detail=f"AI response failed validation: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")