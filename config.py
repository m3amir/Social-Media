"""Configuration for the X Engagement Scraper agent."""

import os
from dotenv import load_dotenv

load_dotenv()

# X API v2 credentials — set in .env file or environment
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")

# Communities/topics to track — search queries for the X API
# The X API recent search supports operators: #hashtag, keyword, from:user, etc.
# COST OPTIMIZATION: We batch these into as few API calls as possible.
# The X API query limit is 512 chars, so we split into 2 batched queries.
TRACKED_TOPICS = [
    {
        "name": "Build in Public",
        "hashtags": ["#buildinpublic", "#BuildInPublic"],
    },
    {
        "name": "Indie Hackers",
        "hashtags": ["#indiehackers", "#IndieHackers"],
    },
    {
        "name": "SaaS",
        "hashtags": ["#saas", "#microsaas"],
    },
    {
        "name": "Startups",
        "hashtags": ["#startup", "#startups"],
    },
    {
        "name": "AI",
        "hashtags": ["#ai", "#llm", "#artificialintelligence"],
    },
    {
        "name": "Dev Tools",
        "hashtags": ["#devtools", "#developer", "#opensource"],
    },
]

# Engagement thresholds — posts below these are filtered out
MIN_LIKES = 5
MIN_RETWEETS = 2

# How many tweets to fetch per API call (max 100)
TWEETS_PER_QUERY = 100

# Scrape schedule — 3 times/day (morning, midday, evening)
# Uses ~6 API calls/day ≈ $1-3/month
SCRAPE_HOURS = [8, 13, 19]  # 8 AM, 1 PM, 7 PM

# Web dashboard settings
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5000

# SQLite database path
DB_PATH = "data/posts.db"
