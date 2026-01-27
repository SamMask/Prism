
import requests
import json
import sys

def test_rag():
    url = "http://127.0.0.1:5000/api/rag/search"
    payload = {
        "query": "Prism",
        "limit": 1
    }
    
    print(f"Testing RAG API: {url}")
    try:
        response = requests.post(url, json=payload, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response Data:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if data['status'] == 'success':
                print("\n✅ RAG API Verification Successful!")
            else:
                print(f"\n❌ API Error: {data.get('message')}")
        elif response.status_code == 503:
             print("\n⚠️ Service Unavailable (Vector Store loading?)")
             print(response.text)
        elif response.status_code == 404:
             print("\n❌ 404 Not Found - Did you verify the blueprint registration?")
        else:
             print(f"\n❌ Failed with status {response.status_code}")
             print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Is the backend running on port 5000?")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_rag()
