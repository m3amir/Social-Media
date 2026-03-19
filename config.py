"""Configuration for the X Engagement Scraper agent."""

import os
from dotenv import load_dotenv

load_dotenv()

# X API v2 credentials — set in .env file or environment
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")

# ──────────────────────────────────────────────────────────────────────
# TOPIC STRATEGY
# ──────────────────────────────────────────────────────────────────────
# Optimized for ORGANIC FOUNDER POSTS — the kind that show up on your
# For You page with no hashtags, just real people sharing milestones,
# asking questions, and building in public.
#
# These posts get natural engagement (likes, replies, quotes) because
# they're authentic — not because they're gaming hashtags.
#
# Strategy: search for PHRASES founders actually say, not hashtags.
# The X API query limit is 512 chars so these get batched automatically.
# ──────────────────────────────────────────────────────────────────────

TRACKED_TOPICS = [
    # ── Revenue Milestones — "$3K MRR", "crossed $10K", etc. ────────
    {
        "name": "Revenue Milestones",
        "terms": [
            '"hit $"', '"crossed $"', '"reached $"',
            '"MRR"', '"monthly recurring"',
            '"first sale"', '"first revenue"',
        ],
    },
    # ── Paying Customers — first users, signups, conversions ────────
    {
        "name": "Paying Customers",
        "terms": [
            '"paying user"', '"paying customer"',
            '"first customer"', '"first user"',
            '"signed up"', '"converted"',
        ],
    },
    # ── Founder Questions — "what's the best way to..." ─────────────
    {
        "name": "Founder Questions",
        "terms": [
            '"as a founder"', '"best way to get"',
            '"how do you get"', '"how did you get"',
            '"what\'s your strategy"', '"any advice on"',
        ],
    },
    # ── Growth & Traction — organic growth stories ──────────────────
    {
        "name": "Growth & Traction",
        "terms": [
            '"ramen profitable"', '"product market fit"',
            '"growing fast"', '"growth is"',
            '"users in"', '"customers in"',
        ],
    },
    # ── Building in Public — updates without hashtags ───────────────
    {
        "name": "Build in Public",
        "terms": [
            '"building in public"', '"build in public"',
            '"shipped"', '"just launched"',
            '"working on"', '"side project"',
        ],
    },
    # ── Startup Struggles — relatable founder pain ──────────────────
    {
        "name": "Startup Struggles",
        "terms": [
            '"biggest mistake"', '"wish I knew"',
            '"lessons learned"', '"almost gave up"',
            '"hardest part of"', '"founder life"',
        ],
    },
    # ── SaaS Tactics — strategy posts that invite discussion ────────
    {
        "name": "SaaS Tactics",
        "terms": [
            '"cold DMs"', '"cold email"',
            '"content marketing"', '"SEO for"',
            '"pricing strategy"', '"churn rate"',
        ],
    },
    # ── Indie Hacker Wins — small victories, relatable posts ────────
    {
        "name": "Indie Hacker Wins",
        "terms": [
            '"solo founder"', '"indie hacker"',
            '"bootstrapped"', '"no funding"',
            '"quit my job"', '"side hustle"',
        ],
    },
]

# ──────────────────────────────────────────────────────────────────────
# CONTENT FILTERS — skip hard-sell promo, keep organic founder posts
# ──────────────────────────────────────────────────────────────────────
# Only penalize aggressive self-promotion (affiliate spam, giveaways).
# Organic milestone posts ("just hit $3K MRR!") are what we WANT.
SELF_PROMO_KEYWORDS = [
    "check out my", "sign up", "join our waitlist",
    "use code", "discount", "giveaway", "drop a follow",
    "link in bio", "subscribe to", "download now",
    "affiliate", "sponsored", "ad:",
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
