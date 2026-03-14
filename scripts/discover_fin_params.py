
import httpx
from src.config import get_settings

def discover_fin_params():
    settings = get_settings()
    api_key = settings.eastmoney_api_key
    base_url = "https://mkapi2.dfcfs.com/finskillshub/api/claw"
    
    headers = {
        "Content-Type": "application/json",
        "apikey": api_key
    }
    
    endpoints = ["stock-fundamental", "stock-technical", "info-search", "fundamental-search", "technical-search"]
    
    for endpoint in endpoints:
        url = f"{base_url}/{endpoint}"
        payload = {
            "query": "000423",
            "pageNo": 1,
            "pageSize": 5
        }
        print(f"Trying endpoint: {endpoint}...")
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    resp_json = response.json()
                    print(f"  Result: {resp_json.get('status')} - {resp_json.get('message')}")
                    if resp_json.get('status') == 0:
                        print(f"  !!! FOUND WORKING ENDPOINT: {endpoint} !!!")
                        print(f"  Response Sample: {str(resp_json)[:200]}...")
                else:
                    print(f"  Status: {response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    discover_fin_params()
