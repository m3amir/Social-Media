"""Configuration for the X Engagement Scraper agent."""

import os
from dotenv import load_dotenv

load_dotenv()

# X API v2 credentials — set in .env file or environment
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")

# ──────────────────────────────────────────────────────────────────────
# TOPIC STRATEGY
# ──────────────────────────────────────────────────────────────────────
# Optimized for THOUGHT LEADERSHIP — finding debates, opinions, hot
# takes, and open questions where a smart reply builds your reputation.
#
# NOT for: project announcements, "just shipped" posts, self-promo.
#
# We use TWO types of search terms:
#   - hashtags: #tag searches (community-based)
#   - keywords: phrase searches (catches posts without hashtags)
#
# The X API query limit is 512 chars so these get batched automatically.
# ──────────────────────────────────────────────────────────────────────

TRACKED_TOPICS = [
    # ── AI Agents — opinions & questions in your core niche ──────────
    {
        "name": "AI Agents",
        "terms": [
            "#AIagents", "#AgenticAI",
            '"AI agent"', '"agentic AI"', '"multi-agent"',
            '"agent framework"',
        ],
    },
    # ── LLMs & Models — debates, not announcements ───────────────────
    {
        "name": "LLMs",
        "terms": [
            "#LLM", "#GenAI", "#GenerativeAI",
            '"LLM hallucination"', '"fine-tuning" vs',
            '"RAG"', '"prompt engineering is"',
        ],
    },
    # ── AI Dev Frameworks — where builders debate tools ──────────────
    {
        "name": "AI Dev",
        "terms": [
            "#langchain", "#crewai", "#autogen",
            '"AI SDK"', '"vector database" vs',
        ],
    },
    # ── AI Hot Takes & Debates ───────────────────────────────────────
    {
        "name": "AI Debates",
        "terms": [
            '"AI will replace"', '"AI won\'t replace"',
            '"unpopular opinion" AI', '"hot take" AI',
            '"overrated" AI', '"underrated" AI',
        ],
    },
    # ── AI Questions & Help ──────────────────────────────────────────
    {
        "name": "AI Questions",
        "terms": [
            '"should I use" AI', '"what\'s the best" AI',
            '"anyone tried" AI', '"how are you using" AI',
            '"struggling with" AI',
        ],
    },
    # ── AI Strategy & Predictions ────────────────────────────────────
    {
        "name": "AI Strategy",
        "terms": [
            '"the problem with" AI', '"AI hype"',
            '"AI bubble"', '"the future of" AI',
            '"AI in 2026"', '"AI is not"',
        ],
    },
    # ── Build in Public — find discussions, not just launches ────────
    {
        "name": "Build in Public",
        "terms": [
            "#buildinpublic", "#indiehackers",
            "#shipfast",
        ],
    },
    # ── SaaS & Startups — strategy discussions ───────────────────────
    {
        "name": "SaaS & Startups",
        "terms": [
            "#saas", "#microsaas", "#startup", "#founders",
            '"AI wrapper"', '"moat" AI',
            '"build vs buy" AI', '"open source vs" AI',
        ],
    },
    # ── AI Impact & Ethics — high-engagement controversial topics ────
    {
        "name": "AI Impact",
        "terms": [
            '"AI ethics"', '"AI regulation"',
            '"AI jobs"', '"AI risk"',
            '"AI safety"',
        ],
    },
]

# ──────────────────────────────────────────────────────────────────────
# CONTENT FILTERS — skip self-promo & announcements, keep discussions
# ──────────────────────────────────────────────────────────────────────
# Tweets matching these patterns get deprioritized (scored lower).
# They're not removed entirely in case they spark good discussions.
SELF_PROMO_KEYWORDS = [
    "just launched", "just shipped", "check out my", "i built",
    "we just released", "now available", "sign up", "join our waitlist",
    "use code", "discount", "giveaway", "drop a follow",
    "link in bio", "subscribe to", "download now",
]
SELF_PROMO_PENALTY = 0.3  # multiply engagement score by this

# ──────────────────────────────────────────────────────────────────────
# ENGAGEMENT THRESHOLDS — only keep hot posts
# ──────────────────────────────────────────────────────────────────────
# For testing: set low. For production: 50 likes, 10 retweets
MIN_LIKES = 3
MIN_RETWEETS = 1

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
