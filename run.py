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
from scraper.storage import init_db, save_posts
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
        logger.warning("Scrape returned no posts — Nitter instances may be down")
    return posts


def run_dashboard(with_scheduler: bool = True):
    """Start the Flask dashboard, optionally with a background scraper."""
    from dashboard.app import app

    if with_scheduler:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            run_scrape,
            "interval",
            minutes=config.SCRAPE_INTERVAL_MINUTES,
            id="scrape_job",
            max_instances=1,
        )
        scheduler.start()
        logger.info(
            "Background scraper scheduled every %d minutes", config.SCRAPE_INTERVAL_MINUTES
        )

        # Run initial scrape
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
    args = parser.parse_args()

    # Initialize database
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    init_db()

    if args.scrape:
        run_scrape()
    elif args.dashboard:
        run_dashboard(with_scheduler=False)
    else:
        run_dashboard(with_scheduler=True)


if __name__ == "__main__":
    main()
