#!/usr/bin/env python3
"""
Scrapes Reddit university subreddits using the public JSON API (no auth needed).
Fetches top posts with quality filtering, focusing on substantive discussions.
Only includes posts with meaningful engagement (upvotes, comments, content).
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output" / "reddit"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "uni-recommender/0.1 (educational project)"}

# Quality thresholds for filtering posts
MIN_SCORE = 10  # Minimum upvotes
MIN_COMMENTS = 5  # Minimum number of comments
MIN_SELFTEXT_LENGTH = 100  # Minimum post body length (characters)

UNIVERSITIES = [
    {
        "name": "Massachusetts Institute of Technology",
        "slug": "mit",
        "subreddits": ["mit", "MITAdmissions"],
        "search_terms": ["campus life", "social life", "culture", "housing", "food", "safety", "female"],
    },
    {
        "name": "Stanford University",
        "slug": "stanford",
        "subreddits": ["stanford", "ApplyingToCollege"],
        "search_terms": ["stanford campus life", "stanford social", "stanford culture", "stanford housing"],
    },
    {
        "name": "University of Michigan Ann Arbor",
        "slug": "university-of-michigan-ann-arbor",
        "subreddits": ["uofm", "uofmichigan"],
        "search_terms": ["campus life", "social life", "ann arbor", "greek life", "safety"],
    },
    {
        "name": "Georgia Institute of Technology",
        "slug": "georgia-institute-of-technology",
        "subreddits": ["gatech"],
        "search_terms": ["campus life", "social life", "atlanta", "culture", "housing"],
    },
    {
        "name": "University of Texas Austin",
        "slug": "university-of-texas-austin",
        "subreddits": ["UTAustin", "LonghornNation"],
        "search_terms": ["campus life", "social", "austin", "culture", "housing", "safety"],
    },
]


def fetch_json(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code}: {url}")
        return None
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return None


def fetch_posts(subreddit: str, sort: str = "hot", limit: int = 25) -> list:
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    data = fetch_json(url)
    if not data:
        return []
    posts = []
    for child in data.get("data", {}).get("children", []):
        p = child["data"]
        posts.append({
            "title": p.get("title", ""),
            "selftext": p.get("selftext", ""),
            "score": p.get("score", 0),
            "url": p.get("url", ""),
            "permalink": "https://reddit.com" + p.get("permalink", ""),
            "num_comments": p.get("num_comments", 0),
            "id": p.get("id", ""),
        })
    return posts


def fetch_comments(post_id: str, subreddit: str, limit: int = 10) -> list:
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json?limit={limit}&depth=1"
    data = fetch_json(url)
    if not data or len(data) < 2:
        return []
    comments = []
    for child in data[1].get("data", {}).get("children", []):
        c = child.get("data", {})
        body = c.get("body", "")
        if body and body != "[deleted]" and body != "[removed]" and len(body) > 30:
            comments.append({
                "body": body,
                "score": c.get("score", 0),
            })
    return comments


def fetch_subreddit_search(subreddit: str, query: str, limit: int = 10) -> list:
    url = f"https://www.reddit.com/r/{subreddit}/search.json?q={urllib.parse.quote(query)}&restrict_sr=1&sort=relevance&limit={limit}"
    data = fetch_json(url)
    if not data:
        return []
    posts = []
    for child in data.get("data", {}).get("children", []):
        p = child["data"]
        posts.append({
            "title": p.get("title", ""),
            "selftext": p.get("selftext", ""),
            "score": p.get("score", 0),
            "permalink": "https://reddit.com" + p.get("permalink", ""),
            "id": p.get("id", ""),
            "num_comments": p.get("num_comments", 0),
        })
    return posts


def is_quality_post(post: dict) -> bool:
    """
    Filter for high-quality posts with meaningful engagement.

    Criteria:
    - Has substantive content (not just a title)
    - Has community engagement (upvotes and comments)
    - Provides insights rather than just asking a narrow question
    """
    return (
        post.get("score", 0) >= MIN_SCORE
        and post.get("num_comments", 0) >= MIN_COMMENTS
        and len(post.get("selftext", "")) >= MIN_SELFTEXT_LENGTH
    )


def scrape_university(uni: dict) -> dict:
    import urllib.parse

    name = uni["name"]
    slug = uni["slug"]
    print(f"\nScraping: {name}")

    result = {
        "name": name,
        "slug": slug,
        "posts": [],
        "search_results": [],
    }

    all_posts = []

    # Fetch top posts from each subreddit (fetch more to have enough after filtering)
    for subreddit in uni["subreddits"]:
        print(f"  r/{subreddit} - fetching top posts (year)...")
        top_url = f"https://www.reddit.com/r/{subreddit}/top.json?limit=50&t=year"
        top_data = fetch_json(top_url)

        if top_data:
            for child in top_data.get("data", {}).get("children", []):
                p = child["data"]
                post = {
                    "title": p.get("title", ""),
                    "selftext": p.get("selftext", ""),
                    "score": p.get("score", 0),
                    "permalink": "https://reddit.com" + p.get("permalink", ""),
                    "num_comments": p.get("num_comments", 0),
                    "id": p.get("id", ""),
                    "url": p.get("url", ""),
                }
                all_posts.append(post)
        time.sleep(1.5)

    # Filter for quality posts
    print(f"  Filtering for quality posts (score>={MIN_SCORE}, comments>={MIN_COMMENTS}, content>={MIN_SELFTEXT_LENGTH} chars)...")
    quality_posts = [post for post in all_posts if is_quality_post(post)]
    print(f"  Found {len(quality_posts)} quality posts out of {len(all_posts)} total")

    # Fetch comments for all quality posts (up to 15 to avoid excessive API calls)
    posts_with_comments = sorted(quality_posts, key=lambda x: x.get("num_comments", 0), reverse=True)[:15]
    for post in posts_with_comments:
        if post.get("id"):
            # Extract subreddit from permalink: https://reddit.com/r/SUBREDDIT/comments/...
            permalink_parts = post["permalink"].split("/")
            subreddit = permalink_parts[4] if len(permalink_parts) > 4 else None
            if subreddit:
                print(f"    Fetching comments for: {post['title'][:60]}...")
                post["comments"] = fetch_comments(post["id"], subreddit)
                time.sleep(1)

    result["posts"].extend(quality_posts)

    # Search for specific qualitative topics and filter them too
    print(f"  Searching for qualitative topics...")
    for term in uni["search_terms"]:
        for subreddit in uni["subreddits"][:1]:  # search primary subreddit only
            results = fetch_subreddit_search(subreddit, term, limit=10)
            # Filter search results for quality
            quality_results = [r for r in results if is_quality_post(r)]
            result["search_results"].extend(quality_results)
            time.sleep(1)

    print(f"  Total: {len(result['posts'])} quality posts, {len(result['search_results'])} quality search results")
    return result


def main():
    all_data = []
    for uni in UNIVERSITIES:
        data = scrape_university(uni)
        all_data.append(data)

        out_path = OUTPUT_DIR / f"{data['slug']}.json"
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"  Saved to {out_path.name}")

        time.sleep(2)

    combined = OUTPUT_DIR / "all.json"
    combined.write_text(json.dumps(all_data, indent=2, ensure_ascii=False))
    print(f"\nDone. Combined saved to {combined}")


if __name__ == "__main__":
    main()
