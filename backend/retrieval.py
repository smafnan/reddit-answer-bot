import os
import re
import urllib.request
import json
import logging
from typing import List, Dict, Any
from duckduckgo_search import DDGS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def search_reddit_via_praw(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Searches Reddit using PRAW and retrieves thread comments."""
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "reddit-intel-engine-v1.0")
    
    if not client_id or not client_secret:
        logger.info("PRAW credentials missing. Skipping PRAW retrieval.")
        return []
        
    logger.info(f"Searching Reddit via PRAW for: '{query}'")
    try:
        import praw
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        
        # Search all subreddits
        submissions = reddit.subreddit("all").search(query, limit=max_results)
        comments = []
        for submission in submissions:
            logger.info(f"Fetching comments for PRAW thread: {submission.title}")
            submission.comment_sort = 'top'
            try:
                submission.comments.replace_more(limit=0) # get top level comments
                # Retrieve up to 10 comments per post to keep context small
                for c in submission.comments[:10]:
                    if c.body and c.body != "[deleted]" and c.body != "[removed]":
                        comments.append({
                            "post_title": submission.title,
                            "post_url": f"https://reddit.com{submission.permalink}",
                            "subreddit": submission.subreddit.display_name,
                            "author": c.author.name if c.author else "[deleted]",
                            "ups": c.score,
                            "body": c.body,
                            "depth": c.depth,
                            "created_utc": c.created_utc
                        })
            except Exception as comment_err:
                logger.warning(f"Error fetching comments for PRAW post {submission.id}: {comment_err}")
                
        return comments
    except Exception as e:
        logger.error(f"Error initializing or fetching via PRAW: {e}")
        return []

def fetch_json_from_url(url: str) -> List[Dict[str, Any]]:
    """Fetches the JSON content of a Reddit post by appending .json to its URL."""
    # Ensure URL ends in .json
    clean_url = url.split('?')[0]  # strip query params
    if not clean_url.endswith('.json'):
        clean_url = clean_url.rstrip('/') + '.json'
    
    # Use urllib with a standard browser user agent to avoid rate limits/blocking
    req = urllib.request.Request(
        clean_url, 
        headers={'User-Agent': USER_AGENT}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        logger.warning(f"Failed to fetch JSON from {clean_url}: {e}")
    return []

def extract_comments_from_json(reddit_json: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extracts comments and post details from Reddit JSON data."""
    extracted = []
    if not reddit_json or len(reddit_json) < 2:
        return extracted
    
    # Post detail
    post_data = {}
    try:
        post_child = reddit_json[0].get("data", {}).get("children", [{}])[0].get("data", {})
        post_data = {
            "title": post_child.get("title", ""),
            "author": post_child.get("author", "anonymous"),
            "selftext": post_child.get("selftext", ""),
            "ups": post_child.get("ups", 0),
            "permalink": f"https://reddit.com{post_child.get('permalink', '')}",
            "subreddit": post_child.get("subreddit", "")
        }
    except Exception as e:
        logger.error(f"Error parsing post data: {e}")
        
    # Comments details
    try:
        comments_list = reddit_json[1].get("data", {}).get("children", [])
        for child in comments_list:
            data = child.get("data", {})
            body = data.get("body", "")
            if body and body != "[deleted]" and body != "[removed]":
                extracted.append({
                    "post_title": post_data.get("title", ""),
                    "post_url": post_data.get("permalink", ""),
                    "subreddit": post_data.get("subreddit", ""),
                    "author": data.get("author", "anonymous"),
                    "ups": data.get("ups", 0),
                    "body": body,
                    "depth": data.get("depth", 0),
                    "created_utc": data.get("created_utc", 0)
                })
    except Exception as e:
        logger.error(f"Error parsing comments: {e}")
        
    return extracted

def search_reddit_via_ddg(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Searches Google/DuckDuckGo for site:reddit.com and fetches thread comments."""
    search_query = f"site:reddit.com {query}"
    logger.info(f"Searching DuckDuckGo: {search_query}")
    
    reddit_threads = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(search_query, max_results=max_results)
            for r in results:
                url = r.get("href", "")
                # We only want actual comment threads
                if "/comments/" in url:
                    reddit_threads.append({
                        "title": r.get("title", ""),
                        "url": url,
                        "snippet": r.get("body", "")
                    })
    except Exception as e:
        logger.error(f"Error during DuckDuckGo search: {e}")
        
    all_comments = []
    
    # If search failed or returned nothing, return empty
    if not reddit_threads:
        return []
        
    for thread in reddit_threads:
        logger.info(f"Fetching thread JSON for: {thread['url']}")
        json_data = fetch_json_from_url(thread["url"])
        if json_data:
            comments = extract_comments_from_json(json_data)
            all_comments.extend(comments)
        else:
            # Fallback to the snippet if json fetch fails
            all_comments.append({
                "post_title": thread["title"],
                "post_url": thread["url"],
                "subreddit": "unknown",
                "author": "snippet",
                "ups": 1,
                "body": thread["snippet"],
                "depth": 0,
                "created_utc": 0
            })
            
    return all_comments

def search_reddit_via_old_scraping(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search Reddit via old.reddit.com scraping (no API keys needed, fallback from master branch)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    from urllib.parse import quote
    import requests
    import re
    
    search_url = f"https://old.reddit.com/search?q={quote(query)}&sort=relevance&limit={limit}"
    results = []
    
    logger.info(f"Searching old.reddit.com: {search_url}")
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200:
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
                title = title.replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<").replace("&quot;", '"').replace("&#39;", "'")
                title = re.sub(r'\s+', ' ', title).strip()
                
                body_match = re.search(r'<div class="search-result-body">.*?<div class="md"><p>(.*?)</p>', block, re.DOTALL)
                body = ""
                if body_match:
                    body = re.sub(r'<[^>]+>', '', body_match.group(1))
                    body = body.replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<").replace("&quot;", '"').replace("&#39;", "'")
                    body = re.sub(r'\s+', ' ', body).strip()
                    
                sub_match = re.search(r'/r/(\w+)', url)
                subreddit = sub_match.group(1) if sub_match else "unknown"
                
                results.append({
                    "post_title": title,
                    "post_url": url,
                    "subreddit": subreddit,
                    "author": "old_scraper",
                    "ups": 1,
                    "body": body or "Reddit discussion thread submission.",
                    "depth": 0,
                    "created_utc": 0
                })
    except Exception as e:
        logger.error(f"Error scraping old.reddit.com: {e}")
        
    return results

def search_reddit_hybrid(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Tries PRAW search first; falls back to combined DuckDuckGo search + old.reddit.com scraping if PRAW fails."""
    comments = []
    try:
        comments = search_reddit_via_praw(query, max_results=max_results)
    except Exception as e:
        logger.warning(f"PRAW search failed, falling back to DDG + old.reddit scraping: {e}")
        
    if not comments:
        logger.info("No comments fetched via PRAW. Running fallback retrievers...")
        ddg_comments = search_reddit_via_ddg(query, max_results=max_results)
        old_comments = search_reddit_via_old_scraping(query, limit=max_results)
        comments = ddg_comments + old_comments
        
    return comments

if __name__ == "__main__":
    # Test retrieval
    test_results = search_reddit_hybrid("best laptop for Ollama", max_results=2)
    print(f"Retrieved {len(test_results)} items.")
    if test_results:
        print("First result snippet:", test_results[0])

