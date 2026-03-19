"""Configuration for the X Engagement Scraper agent."""

import os
from dotenv import load_dotenv

load_dotenv()

# X API v2 credentials — set in .env file or environment
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")

# ──────────────────────────────────────────────────────────────────────
# TOPIC STRATEGY
# ──────────────────────────────────────────────────────────────────────
# Optimized for someone promoting an AI/Agent product.
# Goal: find viral posts where a smart reply gets maximum eyeballs.
#
# We use TWO types of search terms:
#   - hashtags: #tag searches (community-based)
#   - keywords: phrase searches (catches posts without hashtags)
#
# The X API query limit is 512 chars so these get batched automatically.
# ──────────────────────────────────────────────────────────────────────

TRACKED_TOPICS = [
    # ── AI Agents (your core niche) ──────────────────────────────────
    {
        "name": "AI Agents",
        "terms": [
            "#AIagents", "#AgenticAI", "#AIagent",
            '"AI agent"', '"AI agents"', '"agentic AI"',
        ],
    },
    # ── LLMs & Foundation Models ─────────────────────────────────────
    {
        "name": "LLMs",
        "terms": [
            "#LLM", "#GPT", "#Claude", "#GenAI", "#GenerativeAI",
            '"large language model"',
        ],
    },
    # ── AI Tools & Automation ────────────────────────────────────────
    {
        "name": "AI Tools",
        "terms": [
            "#AItools", "#AIautomation", "#nocode",
            '"AI tool"', '"AI workflow"', '"AI automation"',
        ],
    },
    # ── AI Dev Frameworks (where builders hang out) ──────────────────
    {
        "name": "AI Dev",
        "terms": [
            "#langchain", "#crewai", "#autogen",
            '"AI API"', '"AI SDK"', '"prompt engineering"',
        ],
    },
    # ── Build in Public / Indie Hackers (launch exposure) ────────────
    {
        "name": "Build in Public",
        "terms": [
            "#buildinpublic", "#indiehackers", "#shipfast",
            "#justlaunched", "#launched",
        ],
    },
    # ── SaaS & Startups ─────────────────────────────────────────────
    {
        "name": "SaaS & Startups",
        "terms": [
            "#saas", "#microsaas", "#startup",
            "#founders", "#ProductHunt",
        ],
    },
    # ── Tech Twitter thought leaders (keyword, not hashtag) ──────────
    {
        "name": "AI Thought Leaders",
        "terms": [
            '"the future of AI"', '"AI is"', '"just built"',
            '"AI startup"', '"AI product"',
        ],
    },
]

# ──────────────────────────────────────────────────────────────────────
# ENGAGEMENT THRESHOLDS — only keep hot posts
# ──────────────────────────────────────────────────────────────────────
MIN_LIKES = 50
MIN_RETWEETS = 10

# ──────────────────────────────────────────────────────────────────────
# REPLY OPPORTUNITY SCORING
# ──────────────────────────────────────────────────────────────────────
# Posts with high impressions but low reply counts = best reply spots.
# A post with 50K impressions and 20 replies means your reply gets seen
# by way more people vs one with 50K impressions and 500 replies.
# The "reply opportunity score" is: impressions / (replies + 1)
# Higher = better opportunity.
REPLY_OPPORTUNITY_ENABLED = True

# ──────────────────────────────────────────────────────────────────────
# LOOKBACK & SCHEDULE
# ──────────────────────────────────────────────────────────────────────
# How many days back to search (max 7 on X API free/basic)
LOOKBACK_DAYS = 5

# How many tweets to fetch per API call (max 100)
# Set low (e.g. 10) to test without burning credits
TWEETS_PER_QUERY = 10

# Max total posts to keep per scrape cycle (None = unlimited)
# Set to 5 for testing, None for production
MAX_POSTS_PER_SCRAPE = 5

# Scrape schedule — 3 times/day (morning, midday, evening)
SCRAPE_HOURS = [8, 13, 19]  # 8 AM, 1 PM, 7 PM

# Web dashboard settings
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5000

# SQLite database path
DB_PATH = "data/posts.db"
