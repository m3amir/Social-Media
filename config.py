"""Configuration for the X Engagement Scraper agent."""

# Nitter instances to try (rotated on failure)
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.woodland.cafe",
    "https://nitter.1d4.us",
]

# Communities/topics to track — hashtags and search keywords
TRACKED_TOPICS = [
    {"name": "Build in Public", "queries": ["#buildinpublic", "#BuildInPublic"]},
    {"name": "Indie Hackers", "queries": ["#indiehackers", "#IndieHackers"]},
    {"name": "SaaS", "queries": ["#saas", "#microsaas"]},
    {"name": "Startups", "queries": ["#startup", "#startups"]},
    {"name": "AI", "queries": ["#ai", "#artificialintelligence", "#llm"]},
    {"name": "Dev Tools", "queries": ["#devtools", "#developer", "#opensource"]},
]

# Engagement thresholds — posts below these are filtered out
MIN_LIKES = 5
MIN_RETWEETS = 2

# How many posts to fetch per query
POSTS_PER_QUERY = 30

# Scrape interval in minutes
SCRAPE_INTERVAL_MINUTES = 30

# Web dashboard settings
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000

# SQLite database path
DB_PATH = "data/posts.db"
