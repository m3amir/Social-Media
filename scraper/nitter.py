"""Nitter-based scraper for X/Twitter posts."""

import random
import time
import logging
from datetime import datetime
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


def _get_client() -> httpx.Client:
    """Create an HTTP client with browser-like headers."""
    return httpx.Client(
        timeout=15.0,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )


def _try_instances(path: str) -> httpx.Response | None:
    """Try fetching a path across Nitter instances, rotating on failure."""
    instances = list(config.NITTER_INSTANCES)
    random.shuffle(instances)

    for instance in instances:
        url = f"{instance}{path}"
        try:
            with _get_client() as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    return resp
                logger.warning("Instance %s returned %d", instance, resp.status_code)
        except httpx.HTTPError as e:
            logger.warning("Instance %s failed: %s", instance, e)
        time.sleep(0.5)

    logger.error("All Nitter instances failed for path: %s", path)
    return None


def _parse_stat(text: str) -> int:
    """Parse engagement stat text like '1.2K' or '350' into an integer."""
    if not text:
        return 0
    text = text.strip().replace(",", "")
    multiplier = 1
    if text.endswith("K"):
        multiplier = 1_000
        text = text[:-1]
    elif text.endswith("M"):
        multiplier = 1_000_000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return 0


def _parse_post(article, instance_url: str) -> dict | None:
    """Parse a single post/tweet from a Nitter search result page."""
    try:
        # Username and display name
        fullname_el = article.select_one(".fullname")
        username_el = article.select_one(".username")
        if not username_el:
            return None

        username = username_el.get_text(strip=True).lstrip("@")
        display_name = fullname_el.get_text(strip=True) if fullname_el else username

        # Tweet content
        content_el = article.select_one(".tweet-content, .timeline-item .tweet-body .tweet-content")
        content = content_el.get_text(strip=True) if content_el else ""
        if not content:
            return None

        # Link to original tweet
        link_el = article.select_one(".tweet-link, a.tweet-link")
        tweet_path = link_el.get("href", "") if link_el else ""
        tweet_url = f"https://x.com{tweet_path}" if tweet_path else ""

        # Timestamp
        time_el = article.select_one(".tweet-date a")
        timestamp_str = time_el.get("title", "") if time_el else ""
        try:
            timestamp = datetime.strptime(timestamp_str, "%b %d, %Y · %I:%M %p %Z")
        except (ValueError, TypeError):
            timestamp = datetime.utcnow()

        # Engagement stats
        stat_els = article.select(".tweet-stat .tweet-stat-text, .icon-container span")
        stats = [_parse_stat(el.get_text()) for el in stat_els]

        # Nitter stats order: comments, retweets, quotes, likes
        comments = stats[0] if len(stats) > 0 else 0
        retweets = stats[1] if len(stats) > 1 else 0
        quotes = stats[2] if len(stats) > 2 else 0
        likes = stats[3] if len(stats) > 3 else 0

        # Images
        images = []
        for img in article.select(".attachment.image img, .still-image img"):
            src = img.get("src", "")
            if src:
                if src.startswith("/"):
                    src = f"{instance_url}{src}"
                images.append(src)

        return {
            "username": username,
            "display_name": display_name,
            "content": content,
            "url": tweet_url,
            "timestamp": timestamp.isoformat(),
            "likes": likes,
            "retweets": retweets,
            "quotes": quotes,
            "comments": comments,
            "images": images,
            "engagement_score": likes + (retweets * 3) + (quotes * 2) + comments,
        }
    except Exception as e:
        logger.debug("Failed to parse post: %s", e)
        return None


def search_posts(query: str, limit: int = None) -> list[dict]:
    """Search for posts matching a query via Nitter."""
    if limit is None:
        limit = config.POSTS_PER_QUERY

    encoded_query = quote(query)
    path = f"/search?f=tweets&q={encoded_query}"
    resp = _try_instances(path)
    if not resp:
        return []

    # Determine which instance responded
    instance_url = str(resp.url).split("/search")[0]

    soup = BeautifulSoup(resp.text, "lxml")
    articles = soup.select(".timeline-item, .tweet-item")

    posts = []
    for article in articles[:limit]:
        post = _parse_post(article, instance_url)
        if post:
            posts.append(post)

    return posts


def scrape_all_topics() -> list[dict]:
    """Scrape posts for all configured topics and return high-engagement ones."""
    all_posts = []
    seen_urls = set()

    for topic in config.TRACKED_TOPICS:
        topic_name = topic["name"]
        logger.info("Scraping topic: %s", topic_name)

        for query in topic["queries"]:
            posts = search_posts(query)
            for post in posts:
                # Deduplicate by URL
                if post["url"] in seen_urls:
                    continue
                seen_urls.add(post["url"])

                # Apply engagement thresholds
                if post["likes"] >= config.MIN_LIKES or post["retweets"] >= config.MIN_RETWEETS:
                    post["topic"] = topic_name
                    all_posts.append(post)

            # Be polite — small delay between queries
            time.sleep(random.uniform(1.0, 2.5))

    # Sort by engagement score descending
    all_posts.sort(key=lambda p: p["engagement_score"], reverse=True)
    logger.info("Found %d high-engagement posts across all topics", len(all_posts))
    return all_posts
