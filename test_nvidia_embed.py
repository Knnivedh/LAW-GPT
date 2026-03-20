import requests
import os

api_key = os.getenv("NVIDIA_API_KEY", "your_nvapi_key_here")
invoke_url = "https://integrate.api.nvidia.com/v1/embeddings"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

payload = {
    "input": ["Hello World"],
    "model": "nvidia/llama-3.2-nv-embedqa-1b-v2",
    "input_type": "query",
    "encoding_format": "float"
}

try:
    response = requests.post(invoke_url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    print(f"Success! First 5 dims: {data['data'][0]['embedding'][:5]}")
    print(f"Dimensions: {len(data['data'][0]['embedding'])}")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'response') and e.response:
        print(f"Status Code: {e.response.status_code}")
        print(f"Response: {e.response.text}")
