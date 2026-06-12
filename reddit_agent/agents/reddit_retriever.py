import re
import requests
import time
from typing import List, Dict
from urllib.parse import quote


def search_reddit(query: str, limit: int = 8) -> List[Dict]:
    """Search Reddit via old.reddit.com (no API key needed)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    search_url = f"https://old.reddit.com/search?q={quote(query)}&sort=relevance&limit={limit}"
    results = []

    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text

        blocks = re.findall(
            r'<div class=" search-result search-result-link[^"]*"[^>]*>.*?</div>\s*</div>',
            html, re.DOTALL
        )

        for block in blocks[:limit]:
            title_match = re.search(r'<a\s+href="(https?://[^"]+)"\s+class="search-title[^"]*"[^>]*>(.*?)</a>', block, re.DOTALL)
            if not title_match:
                continue

            url = title_match.group(1)
            title = re.sub(r'<[^>]+>', '', title_match.group(2)).strip()
            title = _clean(title)
            title = re.sub(r'\s+', ' ', title).strip()

            body_match = re.search(r'<div class="search-result-body">.*?<div class="md"><p>(.*?)</p>', block, re.DOTALL)
            body = ""
            if body_match:
                body = re.sub(r'<[^>]+>', '', body_match.group(1))
                body = _clean(body)
                body = re.sub(r'\s+', ' ', body).strip()

            subreddit = _extract_subreddit(url)

            results.append({
                "title": title,
                "url": url,
                "subreddit": subreddit or "unknown",
                "score": 0,
                "text": body or "",
            })

    except Exception as e:
        print(f"  Search error: {e}")

    return results


def retrieve(query: str, max_queries: int = 3) -> List[Dict]:
    """Retrieve Reddit posts across multiple query variations."""
    all_posts = []
    seen_urls = set()

    results = search_reddit(query, limit=8)
    for post in results:
        if post["url"] not in seen_urls:
            seen_urls.add(post["url"])
            all_posts.append(post)

    return all_posts


def _clean(text: str) -> str:
    text = text.replace("&amp;", "&")
    text = text.replace("&gt;", ">")
    text = text.replace("&lt;", "<")
    text = text.replace("&quot;", '"')
    text = text.replace("&#x27;", "'")
    text = text.replace("&#39;", "'")
    return text


def _extract_subreddit(url: str) -> str:
    match = re.search(r'/r/(\w+)', url)
    return match.group(1) if match else ""
