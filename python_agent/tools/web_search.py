from duckduckgo_search import DDGS

def web_search_tool(args: dict) -> str:
    """
    웹에서 키워드를 검색하고 상위 결과의 제목·URL·요약을 반환합니다.
    web_scrape 도구로 본문을 읽기 전에 먼저 이 도구로 URL을 찾으세요.

    Args:
        args: {"query": "검색어", "max_results": 5}
    """
    query = args.get("query", "")
    max_results = int(args.get("max_results", 5))

    if not query:
        return "ERROR: 'query' argument is required."

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return "검색 결과가 없습니다."

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r.get('title', '(제목 없음)')}")
            lines.append(f"    URL: {r.get('href', '')}")
            lines.append(f"    요약: {r.get('body', '')[:200]}")
            lines.append("")
        return "\n".join(lines)

    except Exception as e:
        return f"ERROR: 검색 실패 - {e}"
