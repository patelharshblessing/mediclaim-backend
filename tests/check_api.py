import requests
import json

# It's a best practice to not hardcode your API key directly in the script.
# Instead, you can set it as an environment variable.
# For this example, we'll use the key you provided.

api_key = ""
# This is the endpoint for chat completions.
api_endpoint = "https://api.openai.com/v1/chat/completions"

# The headers now include the Content-Type for the JSON payload.
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# This is the payload that will be sent to the API.
# It specifies the model and the message to send.
payload = {
    "model": "gpt-4o",
    "messages": [
        {"role": "user", "content": "Say 'Hello, uck uu!' to confirm the API call is working."}
    ]
}

def invoke_gpt4o(endpoint, headers, data):
    """
    Sends a request to the chat completions endpoint to invoke the gpt-4o model.

    Args:
        endpoint (str): The API endpoint URL.
        headers (dict): The request headers.
        data (dict): The payload for the request.

    Returns:
        None
    """
    print(f"Attempting to invoke gpt-4o at endpoint: {endpoint}...")
    try:
        # A POST request is used to send data to the chat completions endpoint.
        response = requests.post(endpoint, headers=headers, json=data, timeout=20)

        # Check the HTTP status code from the response
        if response.status_code == 200:
            print("\n✅ Success! Your API key is working and gpt-4o was invoked.")
            response_data = response.json()
            message_content = response_data.get('choices', [{}])[0].get('message', {}).get('content')
            if message_content:
                print(f"Model Response: {message_content.strip()}")
            else:
                print("Could not parse model response, but the request was successful.")
        elif response.status_code == 401:
            print("\n❌ Error: Authentication failed (401 Unauthorized).")
            print("This usually means your API key is invalid, expired, or has been revoked.")
        elif response.status_code == 403:
            print("\n❌ Error: Access denied (403 Forbidden).")
            print("Your API key may be correct, but you don't have permission for this resource.")
        elif response.status_code == 429:
            print("\n❌ Error: Rate limit exceeded or insufficient quota (429).")
            print("You have sent too many requests or your account may not have enough funds.")
        else:
            print(f"\n⚠️  Received an unexpected status code: {response.status_code}")
            try:
                # Try to print more detailed error info from the API response
                error_details = response.json()
                print("Error Details:", error_details)
            except json.JSONDecodeError:
                print("Response Body:", response.text)

    except requests.exceptions.RequestException as e:
        print(f"\n❌ An error occurred during the request: {e}")
        print("This could be due to a network issue or an incorrect endpoint URL.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    invoke_gpt4o(api_endpoint, headers, payload)
