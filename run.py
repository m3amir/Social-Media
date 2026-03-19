#!/usr/bin/env python3
"""
X Engagement Scraper Agent
Scrapes high-engagement posts from X communities and serves them via a web dashboard.

Usage:
    python run.py              # Start dashboard + background scraper
    python run.py --scrape     # Run a one-time scrape (no dashboard)
    python run.py --dashboard  # Start dashboard only (no scraper)
"""

import argparse
import logging
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from scraper.storage import init_db, save_posts, reset_db
from scraper.nitter import scrape_all_topics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agent")


def run_scrape():
    """Execute a single scrape cycle."""
    logger.info("Starting scrape cycle...")
    posts = scrape_all_topics()
    if posts:
        count = save_posts(posts)
        logger.info("Scrape complete: %d posts saved/updated", count)
    else:
        logger.warning("Scrape returned no posts — credits may be depleted or no new tweets")
    return posts


def run_dashboard(with_scheduler: bool = True):
    """Start the Flask dashboard, optionally with a background scraper."""
    from dashboard.app import app

    if with_scheduler:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()

        # Schedule scrapes at specific hours (morning, midday, evening)
        for hour in config.SCRAPE_HOURS:
            scheduler.add_job(
                run_scrape,
                "cron",
                hour=hour,
                minute=0,
                id=f"scrape_{hour}",
                max_instances=1,
            )

        scheduler.start()
        schedule_str = ", ".join(f"{h}:00" for h in config.SCRAPE_HOURS)
        logger.info("Scraper scheduled at: %s", schedule_str)

        # Run initial scrape on startup
        run_scrape()

    logger.info("Starting dashboard at http://%s:%d", config.DASHBOARD_HOST, config.DASHBOARD_PORT)
    app.run(
        host=config.DASHBOARD_HOST,
        port=config.DASHBOARD_PORT,
        debug=False,
    )


def main():
    parser = argparse.ArgumentParser(description="X Engagement Scraper Agent")
    parser.add_argument("--scrape", action="store_true", help="Run a one-time scrape only")
    parser.add_argument("--dashboard", action="store_true", help="Start dashboard only (no scraper)")
    parser.add_argument("--reset", action="store_true", help="Clear all old data before scraping")
    args = parser.parse_args()

    # Initialize database
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    init_db()

    if args.reset:
        reset_db()
        logger.info("Database cleared. Run --scrape to fetch fresh posts.")
        if not args.scrape and not args.dashboard:
            return

    if args.scrape:
        run_scrape()
    elif args.dashboard:
        run_dashboard(with_scheduler=False)
    else:
        run_dashboard(with_scheduler=True)


if __name__ == "__main__":
    main()
