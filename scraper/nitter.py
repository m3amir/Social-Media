"""X API v2 client — optimized for minimal credit usage.

Optimizations:
1. Batches all hashtags into 2 API calls instead of 12
2. Uses since_id to only fetch NEW tweets (no re-reading)
3. Logs every API call for credit tracking
"""

import logging
import time
from datetime import datetime, timezone

import httpx

import config
from scraper.storage import get_since_id, set_since_id, log_credit_usage

logger = logging.getLogger(__name__)

API_BASE = "https://api.x.com/2"

# X API query max length is 512 chars. We batch hashtags into groups
# that fit within this limit.
MAX_QUERY_LENGTH = 512


def _get_client() -> httpx.Client:
    """Create an authenticated HTTP client for the X API."""
    if not config.X_BEARER_TOKEN:
        raise RuntimeError(
            "X_BEARER_TOKEN not set. Add your Bearer Token to .env"
        )
    return httpx.Client(
        base_url=API_BASE,
        timeout=30.0,
        headers={"Authorization": f"Bearer {config.X_BEARER_TOKEN}"},
    )


def _build_batched_queries() -> list[dict]:
    """Combine all topic hashtags into minimal batched API queries.

    Returns a list of {"batch_name": str, "query": str, "topics": {hashtag: topic_name}}
    where each query stays under the 512-char limit.
    """
    batches = []
    current_hashtags = []
    current_topics = {}  # hashtag -> topic_name mapping
    batch_num = 1

    for topic in config.TRACKED_TOPICS:
        for tag in topic["hashtags"]:
            current_hashtags.append(tag)
            current_topics[tag.lower()] = topic["name"]

            # Check if adding more would exceed the query limit
            test_query = _format_query(current_hashtags)
            if len(test_query) > MAX_QUERY_LENGTH:
                # Remove the last hashtag and finalize this batch
                current_hashtags.pop()
                del current_topics[tag.lower()]

                batches.append({
                    "batch_name": f"batch_{batch_num}",
                    "query": _format_query(current_hashtags),
                    "topics": dict(current_topics),
                })
                batch_num += 1

                # Start new batch with the overflow hashtag
                current_hashtags = [tag]
                current_topics = {tag.lower(): topic["name"]}

    # Don't forget the last batch
    if current_hashtags:
        batches.append({
            "batch_name": f"batch_{batch_num}",
            "query": _format_query(current_hashtags),
            "topics": dict(current_topics),
        })

    logger.info(
        "Batched %d topics into %d API calls (saves ~%d calls/cycle)",
        len(config.TRACKED_TOPICS),
        len(batches),
        len(config.TRACKED_TOPICS) - len(batches),
    )
    return batches


def _format_query(hashtags: list[str]) -> str:
    """Format hashtags into an X API search query string."""
    joined = " OR ".join(hashtags)
    return f"({joined}) -is:retweet lang:en"


def _classify_topic(text: str, topics_map: dict) -> str:
    """Determine which topic a tweet belongs to based on its content."""
    text_lower = text.lower()
    for hashtag, topic_name in topics_map.items():
        if hashtag.lstrip("#") in text_lower:
            return topic_name
    return "General"


def search_recent_tweets(
    query: str,
    since_id: str | None = None,
    max_results: int = None,
) -> tuple[list[dict], dict, int]:
    """Search recent tweets using X API v2.

    Returns (raw_tweets_data, users_dict, api_call_count).
    """
    if max_results is None:
        max_results = config.TWEETS_PER_QUERY

    max_results = max(10, min(max_results, 100))

    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,public_metrics,author_id,text",
        "user.fields": "username,name,profile_image_url",
        "expansions": "author_id",
    }

    # Only fetch tweets newer than what we already have
    if since_id:
        params["since_id"] = since_id

    try:
        with _get_client() as client:
            resp = client.get("/tweets/search/recent", params=params)

            if resp.status_code == 429:
                reset = resp.headers.get("x-rate-limit-reset")
                wait = 60
                if reset:
                    wait = max(1, int(reset) - int(time.time()))
                logger.warning("Rate limited. Resets in %ds. Skipping this cycle.", wait)
                return [], {}, 1

            if resp.status_code == 402:
                logger.error("Credits depleted! Add credits at https://developer.x.com > Billing > Credits")
                return [], {}, 1

            if resp.status_code != 200:
                logger.error("X API returned %d: %s", resp.status_code, resp.text[:300])
                return [], {}, 1

            data = resp.json()

    except httpx.HTTPError as e:
        logger.error("X API request failed: %s", e)
        return [], {}, 1

    tweets = data.get("data", [])
    users = {}
    for user in data.get("includes", {}).get("users", []):
        users[user["id"]] = user

    return tweets, users, 1


def scrape_all_topics() -> list[dict]:
    """Fetch tweets using batched queries with since_id tracking.

    Credit-efficient: typically 2 API calls per cycle instead of 12.
    """
    batches = _build_batched_queries()
    all_posts = []
    seen_ids = set()
    total_api_calls = 0
    total_tweets_read = 0

    for batch in batches:
        batch_name = batch["batch_name"]
        query = batch["query"]
        topics_map = batch["topics"]

        since_id = get_since_id(batch_name)
        if since_id:
            logger.info("Fetching %s (only tweets newer than %s)", batch_name, since_id)
        else:
            logger.info("Fetching %s (first run — full fetch)", batch_name)

        tweets, users, api_calls = search_recent_tweets(query, since_id=since_id)
        total_api_calls += api_calls
        total_tweets_read += len(tweets)

        if not tweets:
            logger.info("%s: no new tweets", batch_name)
            time.sleep(1.5)
            continue

        # Track the newest tweet ID for next run
        newest_id = max(tweets, key=lambda t: int(t["id"]))["id"]
        set_since_id(batch_name, newest_id)

        for tweet in tweets:
            tweet_id = tweet["id"]
            if tweet_id in seen_ids:
                continue
            seen_ids.add(tweet_id)

            metrics = tweet.get("public_metrics", {})
            author = users.get(tweet.get("author_id"), {})
            username = author.get("username", "unknown")

            likes = metrics.get("like_count", 0)
            retweets = metrics.get("retweet_count", 0)
            quotes = metrics.get("quote_count", 0)
            replies = metrics.get("reply_count", 0)
            impressions = metrics.get("impression_count", 0)

            # Skip low-engagement posts
            if likes < config.MIN_LIKES and retweets < config.MIN_RETWEETS:
                continue

            content = tweet.get("text", "")
            topic = _classify_topic(content, topics_map)

            all_posts.append({
                "tweet_id": tweet_id,
                "username": username,
                "display_name": author.get("name", username),
                "content": content,
                "url": f"https://x.com/{username}/status/{tweet_id}",
                "timestamp": tweet.get("created_at", datetime.now(timezone.utc).isoformat()),
                "likes": likes,
                "retweets": retweets,
                "quotes": quotes,
                "comments": replies,
                "impressions": impressions,
                "images": [],
                "topic": topic,
                "engagement_score": likes + (retweets * 3) + (quotes * 2) + replies,
            })

        # Respect rate limits between batches
        time.sleep(1.5)

    # Log credit usage
    log_credit_usage(total_api_calls, total_tweets_read)
    logger.info(
        "Scrape complete: %d API calls, %d tweets read, %d high-engagement posts found",
        total_api_calls, total_tweets_read, len(all_posts),
    )

    all_posts.sort(key=lambda p: p["engagement_score"], reverse=True)
    return all_posts
