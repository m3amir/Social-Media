# X Engagement Scraper Agent

Scrapes high-engagement posts from X/Twitter communities (Build in Public, Indie Hackers, SaaS, Startups, AI, Dev Tools) via Nitter and serves them through a web dashboard.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run (dashboard + auto-scraper)
python run.py
```

Open **http://localhost:5000** in your browser.

## Usage Modes

| Command | What it does |
|---|---|
| `python run.py` | Dashboard + background scraper (every 30 min) |
| `python run.py --scrape` | One-time scrape, no dashboard |
| `python run.py --dashboard` | Dashboard only, no scraping |

## Features

- **Nitter-based scraping** — no API keys needed, rotates across instances
- **Engagement scoring** — posts ranked by `likes + 3×retweets + 2×quotes + comments`
- **Web dashboard** — dark-themed UI with topic filtering, search, sorting, and bookmarks
- **Auto-refresh** — background scheduler scrapes new posts on a configurable interval
- **SQLite storage** — lightweight, zero-config persistence

## Configuration

Edit `config.py` to customize:

- `NITTER_INSTANCES` — list of Nitter mirrors to use
- `TRACKED_TOPICS` — communities/hashtags to monitor
- `MIN_LIKES` / `MIN_RETWEETS` — engagement thresholds
- `SCRAPE_INTERVAL_MINUTES` — how often to fetch new posts
- `DASHBOARD_PORT` — web server port

## Project Structure

```
├── run.py                  # Entry point
├── config.py               # All settings
├── requirements.txt
├── scraper/
│   ├── nitter.py           # Nitter scraping logic
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
