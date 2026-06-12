import re
import requests
from typing import List, Dict
from urllib.parse import quote

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def search_reddit(query: str, limit: int = 6) -> List[Dict]:
    url = f"https://old.reddit.com/search?q={quote(query)}&sort=relevance&limit={limit}"
    results = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
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
            title = clean_html(title)
            title = re.sub(r'\s+', ' ', title).strip()
            body_match = re.search(r'<div class="search-result-body">.*?<div class="md"><p>(.*?)</p>', block, re.DOTALL)
            body = ""
            if body_match:
                body = re.sub(r'<[^>]+>', '', body_match.group(1))
                body = clean_html(body)
                body = re.sub(r'\s+', ' ', body).strip()
            subreddit = extract_subreddit(url)
            score_match = re.search(r'<span class="search-score">(\d+)</span>', block)
            score = int(score_match.group(1)) if score_match else 0
            results.append({
                "title": title,
                "url": url,
                "subreddit": subreddit or "unknown",
                "score": score,
                "text": body or "",
            })
    except Exception as e:
        print(f"  Search error: {e}")
    return results


def retrieve(query: str) -> List[Dict]:
    all_posts = []
    seen_urls = set()
    results = search_reddit(query, limit=6)
    for post in results:
        if post["url"] not in seen_urls:
            seen_urls.add(post["url"])
            all_posts.append(post)
    return all_posts


def clean_html(text: str) -> str:
    text = text.replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<")
    text = text.replace("&quot;", '"').replace("&#x27;", "'").replace("&#39;", "'")
    return text


def extract_subreddit(url: str) -> str:
    match = re.search(r'/r/(\w+)', url)
    return match.group(1) if match else ""
