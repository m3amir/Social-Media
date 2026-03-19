"""X API v2 client — optimized for minimal credit usage.

Optimizations:
1. Batches all search terms into minimal API calls (512-char query limit)
2. Uses since_id to only fetch NEW tweets (no re-reading)
3. Supports start_time for N-day lookback
4. Calculates reply opportunity score (high impressions, low replies = gold)
5. Logs every API call for credit tracking
"""

import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

import config
from scraper.storage import get_since_id, set_since_id, log_credit_usage

logger = logging.getLogger(__name__)

API_BASE = "https://api.x.com/2"

# X API query max length is 512 chars
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
    """Combine all topic search terms into minimal batched API queries.

    Handles both hashtags (#buildinpublic) and keyword phrases ("AI agent").
    Returns list of {"batch_name", "query", "topics"} dicts.
    """
    batches = []
    current_terms = []
    current_topics = {}  # term -> topic_name mapping
    batch_num = 1

    for topic in config.TRACKED_TOPICS:
        for term in topic["terms"]:
            current_terms.append(term)
            # Use the raw term (lowered, stripped of quotes/hash) as lookup key
            lookup = term.lower().strip('"').lstrip("#")
            current_topics[lookup] = topic["name"]

            test_query = _format_query(current_terms)
            if len(test_query) > MAX_QUERY_LENGTH:
                current_terms.pop()
                del current_topics[lookup]

                batches.append({
                    "batch_name": f"batch_{batch_num}",
                    "query": _format_query(current_terms),
                    "topics": dict(current_topics),
                })
                batch_num += 1
                current_terms = [term]
                current_topics = {lookup: topic["name"]}

    if current_terms:
        batches.append({
            "batch_name": f"batch_{batch_num}",
            "query": _format_query(current_terms),
            "topics": dict(current_topics),
        })

    logger.info(
        "Batched %d topics into %d API calls",
        len(config.TRACKED_TOPICS), len(batches),
    )
    return batches


def _format_query(terms: list[str]) -> str:
    """Format search terms into an X API query string."""
    joined = " OR ".join(terms)
    return f"({joined}) -is:retweet -is:reply lang:en"


def _classify_topic(text: str, topics_map: dict) -> str:
    """Determine which topic a tweet belongs to based on its content."""
    text_lower = text.lower()
    for term, topic_name in topics_map.items():
        if term in text_lower:
            return topic_name
    return "General"


def _is_self_promo(text: str) -> bool:
    """Check if a tweet is self-promotional or a launch announcement."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in config.SELF_PROMO_KEYWORDS)


def _calc_reply_opportunity(impressions: int, replies: int) -> int:
    """Calculate reply opportunity score.

    High impressions + low replies = your reply gets maximum eyeballs.
    Score = impressions / (replies + 1)
    A post with 50K views and 10 replies scores 4545.
    A post with 50K views and 500 replies scores 99.
    """
    if not config.REPLY_OPPORTUNITY_ENABLED or impressions == 0:
        return 0
    return impressions // (replies + 1)


def search_recent_tweets(
    query: str,
    since_id: str | None = None,
    start_time: str | None = None,
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

    # Incremental: only fetch tweets newer than last seen
    if since_id:
        params["since_id"] = since_id
    elif start_time:
        # First run: use start_time for N-day lookback
        params["start_time"] = start_time

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

    On first run: looks back LOOKBACK_DAYS.
    On subsequent runs: only fetches new tweets since last scrape.
    """
    batches = _build_batched_queries()
    all_posts = []
    seen_ids = set()
    total_api_calls = 0
    total_tweets_read = 0

    # Calculate start_time for first-run lookback
    lookback_start = (
        datetime.now(timezone.utc) - timedelta(days=config.LOOKBACK_DAYS)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    for batch in batches:
        batch_name = batch["batch_name"]
        query = batch["query"]
        topics_map = batch["topics"]

        since_id = get_since_id(batch_name)
        if since_id:
            logger.info("Fetching %s (incremental, since %s)", batch_name, since_id)
            start_time = None
        else:
            logger.info("Fetching %s (first run, %d-day lookback)", batch_name, config.LOOKBACK_DAYS)
            start_time = lookback_start

        tweets, users, api_calls = search_recent_tweets(
            query, since_id=since_id, start_time=start_time,
        )
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

            content = tweet.get("text", "")
            topic = _classify_topic(content, topics_map)
            reply_opp = _calc_reply_opportunity(impressions, replies)
            is_hot = likes >= config.MIN_LIKES or retweets >= config.MIN_RETWEETS

            raw_score = likes + (retweets * 3) + (quotes * 2) + replies

            # Deprioritize self-promo / announcement tweets
            if _is_self_promo(content):
                raw_score = int(raw_score * config.SELF_PROMO_PENALTY)

            # Boost tweets that ask questions (high engagement potential)
            if "?" in content:
                raw_score = int(raw_score * 1.5)

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
                "reply_opportunity": reply_opp,
                "images": [],
                "topic": topic,
                "engagement_score": raw_score,
                "is_hot": is_hot,
            })

        # Respect rate limits between batches
        time.sleep(1.5)

    # Log credit usage
    log_credit_usage(total_api_calls, total_tweets_read)
    logger.info(
        "Scrape complete: %d API calls, %d tweets read, %d hot posts found",
        total_api_calls, total_tweets_read, len(all_posts),
    )

    all_posts.sort(key=lambda p: p["engagement_score"], reverse=True)

    # Cap total posts if MAX_POSTS_PER_SCRAPE is set
    limit = config.MAX_POSTS_PER_SCRAPE
    if limit and len(all_posts) > limit:
        logger.info("Capping results to %d posts (MAX_POSTS_PER_SCRAPE)", limit)
        all_posts = all_posts[:limit]

    return all_posts
