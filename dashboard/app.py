"""Flask web dashboard for the X Engagement Scraper."""

import logging

from flask import Flask, render_template, request, jsonify

from scraper.storage import get_posts, get_topics, get_stats, toggle_bookmark

logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)


@app.route("/")
def index():
    """Main dashboard page."""
    topics = get_topics()
    stats = get_stats()
    return render_template("index.html", topics=topics, stats=stats)


@app.route("/api/posts")
def api_posts():
    """JSON API for fetching posts with filtering."""
    topic = request.args.get("topic")
    sort_by = request.args.get("sort", "engagement_score")
    order = request.args.get("order", "desc")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    bookmarked = request.args.get("bookmarked", "").lower() == "true"
    search = request.args.get("search")

    posts = get_posts(
        topic=topic,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
        bookmarked_only=bookmarked,
        search=search,
    )
    return jsonify(posts)


@app.route("/api/topics")
def api_topics():
    """JSON API for topic listing."""
    return jsonify(get_topics())


@app.route("/api/stats")
def api_stats():
    """JSON API for stats."""
    return jsonify(get_stats())


@app.route("/api/bookmark/<int:post_id>", methods=["POST"])
def api_bookmark(post_id):
    """Toggle bookmark on a post."""
    new_state = toggle_bookmark(post_id)
    return jsonify({"bookmarked": new_state})
