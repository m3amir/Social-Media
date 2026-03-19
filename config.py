"""Configuration for the X Engagement Scraper agent."""

import os
from dotenv import load_dotenv

load_dotenv()

# X API v2 credentials — set in .env file or environment
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")

# Communities/topics to track — search queries for the X API
# The X API recent search supports operators: #hashtag, keyword, from:user, etc.
TRACKED_TOPICS = [
    {
        "name": "Build in Public",
        "query": "(#buildinpublic OR #BuildInPublic) -is:retweet lang:en",
    },
    {
        "name": "Indie Hackers",
        "query": "(#indiehackers OR #IndieHackers) -is:retweet lang:en",
    },
    {
        "name": "SaaS",
        "query": "(#saas OR #microsaas) -is:retweet lang:en",
    },
    {
        "name": "Startups",
        "query": "(#startup OR #startups) -is:retweet lang:en",
    },
    {
        "name": "AI",
        "query": "(#ai OR #llm OR #artificialintelligence) -is:retweet lang:en",
    },
    {
        "name": "Dev Tools",
        "query": "(#devtools OR #developer OR #opensource) -is:retweet lang:en",
    },
]

# Engagement thresholds — posts below these are filtered out
MIN_LIKES = 5
MIN_RETWEETS = 2

# How many tweets to fetch per query (max 100 per request on free tier)
TWEETS_PER_QUERY = 50

# Scrape interval in minutes
SCRAPE_INTERVAL_MINUTES = 30

# Web dashboard settings
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5000

# SQLite database path
DB_PATH = "data/posts.db"
