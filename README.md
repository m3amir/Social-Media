# X Engagement Scraper Agent

Finds high-engagement posts from X/Twitter communities (Build in Public, Indie Hackers, SaaS, Startups, AI, Dev Tools) using the X API v2 and serves them through a web dashboard.

## Setup

### 1. Get your X API Bearer Token (free)

1. Go to [developer.x.com](https://developer.x.com) and sign up
2. Create a Project and an App
3. Go to **Keys and tokens** → generate a **Bearer Token**

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env and paste your Bearer Token
```

### 3. Install and run

```bash
pip install -r requirements.txt
python run.py
```

Open **http://127.0.0.1:5000** in your browser.

## Usage Modes

| Command | What it does |
|---|---|
| `python run.py` | Dashboard + background scraper (every 30 min) |
| `python run.py --scrape` | One-time scrape, no dashboard |
| `python run.py --dashboard` | Dashboard only, no scraping |

## Features

- **X API v2** — uses the free tier recent search endpoint (1,500 tweets/month)
- **Engagement scoring** — posts ranked by `likes + 3×retweets + 2×quotes + comments`
- **Impressions tracking** — see how many views each post got
- **Web dashboard** — dark-themed UI with topic filtering, search, sorting, and bookmarks
- **Auto-refresh** — background scheduler scrapes new posts on a configurable interval
- **SQLite storage** — lightweight, zero-config persistence

## Configuration

Edit `config.py` to customize:

- `TRACKED_TOPICS` — communities/hashtags to monitor (uses X API search operators)
- `MIN_LIKES` / `MIN_RETWEETS` — engagement thresholds
- `TWEETS_PER_QUERY` — how many tweets to fetch per topic (max 100)
- `SCRAPE_INTERVAL_MINUTES` — how often to fetch new posts
- `DASHBOARD_PORT` — web server port

## API Rate Limits (Free Tier)

- 1,500 tweets/month total reads
- 1 request per second
- 7-day tweet lookback window
- The agent respects these limits automatically

## Project Structure

```
├── run.py                  # Entry point
├── config.py               # All settings
├── .env.example            # Credential template
├── requirements.txt
├── scraper/
│   ├── nitter.py           # X API v2 client
│   └── storage.py          # SQLite database layer
├── dashboard/
│   ├── app.py              # Flask routes & API
│   ├── templates/
│   │   └── index.html      # Dashboard template
│   └── static/
│       ├── css/style.css
│       └── js/app.js
└── data/                   # SQLite DB (auto-created)
```
