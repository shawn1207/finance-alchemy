
import httpx
from src.config import get_settings

def discover_news_params():
    settings = get_settings()
    api_key = settings.eastmoney_api_key
    url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search"
    
    headers = {
        "Content-Type": "application/json",
        "apikey": api_key
    }
    
    params_to_try = ["question", "keyword", "q", "kw", "query", "text", "prompt", "input", "searchKey", "keyWord"]
    
    for param in params_to_try:
        payload = {
            param: "000423",
            "pageNo": 1,
            "pageSize": 5
        }
        print(f"Trying param: {param}...")
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(url, headers=headers, json=payload)
                resp_json = response.json()
                msg = resp_json.get("message", "")
                print(f"  Result: {resp_json.get('status')} - {msg}")
                if "不能为空" not in msg:
                    print(f"  !!! FOUND POSSIBLE PARAM: {param} !!!")
                    print(f"  Response: {response.text[:200]}")
                    # If we found it, we can stop or continue
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    discover_news_params()
