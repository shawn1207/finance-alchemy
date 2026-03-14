
import httpx
from src.config import get_settings

def check_news_result_type():
    settings = get_settings()
    api_key = settings.eastmoney_api_key
    url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search"
    
    headers = {
        "Content-Type": "application/json",
        "apikey": api_key
    }
    
    payload = {
        "query": "000423",
        "pageNo": 1,
        "pageSize": 5
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)
            resp_json = response.json()
            print(f"News Search Result Type: {resp_json.get('data', {}).get('resultType')}")
            # print(f"Data Sample: {str(resp_json.get('data', {}).get('data'))[:500]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_news_result_type()
