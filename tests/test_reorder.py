import requests
import json

# Test reorder API
response = requests.put(
    'http://127.0.0.1:5000/api/notes/reorder',
    json={'note_ids': [1, 2, 3]},
    timeout=10
)
print(f"Status: {response.status_code}")
print(f"Response:")
try:
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
except:
    print(response.text)
