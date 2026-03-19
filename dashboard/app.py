"""Flask web dashboard for the X Engagement Scraper."""

import json
import logging
import os

import boto3
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
    hot_only = request.args.get("hot_only", "true").lower() != "false"
    search = request.args.get("search")

    posts = get_posts(
        topic=topic,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
        bookmarked_only=bookmarked,
        search=search,
        hot_only=hot_only,
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


@app.route("/api/generate-reply", methods=["POST"])
def api_generate_reply():
    """Generate a reply using Claude Haiku via AWS Bedrock."""
    data = request.get_json()
    tweet_content = data.get("tweet_content", "")
    tweet_author = data.get("tweet_author", "")
    insight = data.get("insight", "")
    tone = data.get("tone", "insightful and conversational")

    if not tweet_content or not insight:
        return jsonify({"error": "Tweet content and insight are required"}), 400

    prompt = f"""You are a Twitter/X reply strategist. Your goal is to craft a reply that gets engagement and visibility.

ORIGINAL TWEET by @{tweet_author}:
"{tweet_content}"

THE USER'S INSIGHT/ANGLE:
"{insight}"

TONE: {tone}

Write a reply tweet (max 280 chars) that:
1. Directly responds to the original tweet
2. Weaves in the user's insight naturally — don't just restate it
3. Adds value so people want to like/retweet the reply
4. Feels authentic, not salesy or generic
5. Does NOT use hashtags or emojis
6. Does NOT start with "Great point" or similar filler

Return ONLY the reply text, nothing else."""

    try:
        bedrock = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        })

        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            contentType="application/json",
            accept="application/json",
            body=body,
        )

        result = json.loads(response["body"].read())
        reply_text = result["content"][0]["text"].strip()

        # Trim to 280 chars if needed
        if len(reply_text) > 280:
            reply_text = reply_text[:277] + "..."

        return jsonify({"reply": reply_text})

    except Exception as e:
        logger.error("Bedrock API error: %s", e)
        return jsonify({"error": str(e)}), 500
