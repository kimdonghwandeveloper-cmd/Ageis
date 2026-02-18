import httpx
from bs4 import BeautifulSoup

def web_scrape_tool(args: dict) -> str:
    """
    URL에서 본문 텍스트만 추출 (최대 2000자 제한)
    
    Args:
        args: {"url": "https://example.com"}
    """
    url = args.get("url", "")
    if not url:
        return "ERROR: 'url' argument is required."

    # http/https 프로토콜 없으면 추가
    if not url.startswith("http"):
        url = "https://" + url

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
        resp.raise_for_status() # 4xx, 5xx 에러 체크
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "meta", "noscript"]):
            tag.decompose()
            
        text = soup.get_text(separator="\n", strip=True)
        
        # 너무 긴 텍스트는 잘라서 반환 (토큰 절약)
        if len(text) > 2000:
            return text[:2000] + "\n... (content truncated)"
        return text
        
    except httpx.HTTPError as e:
        return f"ERROR: HTTP Request failed - {e}"
    except Exception as e:
        return f"ERROR: Scraper failed - {e}"
