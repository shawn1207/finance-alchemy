
import httpx
from src.config import get_settings

def test_news_via_screen():
    settings = get_settings()
    api_key = settings.eastmoney_api_key
    url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/stock-screen"
    
    headers = {
        "Content-Type": "application/json",
        "apikey": api_key
    }
    
    payload = {
        "keyword": "000423 最新新闻",
        "pageNo": 1,
        "pageSize": 5
    }
    
    print(f"Testing URL: {url} with keyword '000423 最新新闻'")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:1000]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_news_via_screen()
