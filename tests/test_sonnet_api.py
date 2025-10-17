"""
Simple standalone script to test Claude Sonnet (Anthropic) API connectivity and response.
Make sure to set your API key in the environment variable:
    export CLAUDE_API_KEY="your-anthropic-api-key"
"""

import os
import httpx
import json
import time
import sys  

# Add the root project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings


CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_API_KEY = settings.CLAUDE_API_KEY  # Read from environment variable
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"  # ✅ correct Anthropic model name


def test_sonnet_api():
    if not CLAUDE_API_KEY:
        print("❌ CLAUDE_API_KEY not found in environment. Please export it first.")
        return

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # A very simple text test to confirm JSON-based response works
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 500,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are a helpful assistant. "
                            "Reply ONLY in JSON format. Return {\"status\": \"API is working fine\"}."
                        ),
                    }
                ],
            }
        ],
    }

    print("🚀 Sending test request to Claude Sonnet API...")
    start_time = time.time()
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(CLAUDE_API_URL, headers=headers, json=payload)
        duration = time.time() - start_time
        print(f"✅ Response received in {duration:.2f} seconds.")
        print(f"Status Code: {response.status_code}")

        if response.status_code != 200:
            print("❌ API returned an error:")
            print(response.text)
            return

        data = response.json()
        if not data.get("content"):
            print("⚠️ No 'content' field found in API response.")
            print(json.dumps(data, indent=2))
            return

        # Extract text from the first content block
        first_block = data["content"][0]
        if first_block.get("type") == "text":
            text = first_block.get("text", "")
            print("🧠 Raw Text Response:\n", text)
            try:
                parsed = json.loads(text)
                print("✅ Parsed JSON Response:\n", json.dumps(parsed, indent=2))
            except json.JSONDecodeError:
                print("⚠️ Response not valid JSON, raw text shown above.")
        else:
            print("⚠️ Unexpected response block type:", first_block.get("type"))

    except Exception as e:
        print("❌ Error communicating with Claude Sonnet API:", e)


if __name__ == "__main__":
    test_sonnet_api()
