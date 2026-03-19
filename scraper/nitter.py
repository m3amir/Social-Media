"""X API v2 client for scraping high-engagement tweets."""

import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

import config

logger = logging.getLogger(__name__)

API_BASE = "https://api.x.com/2"


def _get_client() -> httpx.Client:
    """Create an authenticated HTTP client for the X API."""
    if not config.X_BEARER_TOKEN:
        raise RuntimeError(
            "X_BEARER_TOKEN not set. Create a free app at https://developer.x.com "
            "and add your Bearer Token to .env"
        )
    return httpx.Client(
        base_url=API_BASE,
        timeout=30.0,
        headers={"Authorization": f"Bearer {config.X_BEARER_TOKEN}"},
    )


def search_recent_tweets(query: str, max_results: int = None) -> list[dict]:
    """Search recent tweets using the X API v2 recent search endpoint.

    Free tier: up to 1,500 tweets/month, 1 request/second, 7-day lookback.
    """
    if max_results is None:
        max_results = config.TWEETS_PER_QUERY

    # Clamp to API limits (10-100 per request)
    max_results = max(10, min(max_results, 100))

    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,public_metrics,author_id,text",
        "user.fields": "username,name,profile_image_url",
        "expansions": "author_id",
    }

    try:
        with _get_client() as client:
            resp = client.get("/tweets/search/recent", params=params)

            if resp.status_code == 429:
                reset = resp.headers.get("x-rate-limit-reset")
                wait = 60
                if reset:
                    wait = max(1, int(reset) - int(time.time()))
                logger.warning("Rate limited. Resets in %ds", wait)
                return []

            if resp.status_code == 403:
                logger.error(
                    "403 Forbidden — your API key may not have access to the "
                    "recent search endpoint. Check your app permissions at "
                    "https://developer.x.com"
                )
                return []

            if resp.status_code != 200:
                logger.error("X API returned %d: %s", resp.status_code, resp.text[:300])
                return []

            data = resp.json()

    except httpx.HTTPError as e:
        logger.error("X API request failed: %s", e)
        return []

    tweets = data.get("data", [])
    if not tweets:
        return []

    # Build user lookup from includes
    users = {}
    for user in data.get("includes", {}).get("users", []):
        users[user["id"]] = user

    posts = []
    for tweet in tweets:
        metrics = tweet.get("public_metrics", {})
        author = users.get(tweet.get("author_id"), {})
        username = author.get("username", "unknown")

        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        quotes = metrics.get("quote_count", 0)
        replies = metrics.get("reply_count", 0)
        impressions = metrics.get("impression_count", 0)

        posts.append({
            "username": username,
            "display_name": author.get("name", username),
            "content": tweet.get("text", ""),
            "url": f"https://x.com/{username}/status/{tweet['id']}",
            "timestamp": tweet.get("created_at", datetime.now(timezone.utc).isoformat()),
            "likes": likes,
            "retweets": retweets,
            "quotes": quotes,
            "comments": replies,
            "impressions": impressions,
            "images": [],
            "engagement_score": likes + (retweets * 3) + (quotes * 2) + replies,
        })

    return posts


def scrape_all_topics() -> list[dict]:
    """Fetch tweets for all configured topics and return high-engagement ones."""
    all_posts = []
    seen_urls = set()

    for topic in config.TRACKED_TOPICS:
        topic_name = topic["name"]
        query = topic["query"]
        logger.info("Fetching topic: %s", topic_name)

        posts = search_recent_tweets(query)
        for post in posts:
            if post["url"] in seen_urls:
                continue
            seen_urls.add(post["url"])

            if post["likes"] >= config.MIN_LIKES or post["retweets"] >= config.MIN_RETWEETS:
                post["topic"] = topic_name
                all_posts.append(post)

        # Respect rate limits — 1 request/sec on free tier
        time.sleep(1.5)

    all_posts.sort(key=lambda p: p["engagement_score"], reverse=True)
    logger.info("Found %d high-engagement posts across all topics", len(all_posts))
    return all_posts
