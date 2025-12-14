#!/usr/bin/env python3
"""
Instagram API Server for n8n Integration

This Flask server provides REST endpoints for Instagram actions
that can be called from n8n workflows.

Endpoints:
- POST /api/like - Like posts by IDs
- POST /api/dm - Send direct message
- GET /api/health - Health check

Usage:
    python api_server.py

Then configure n8n to call http://localhost:5000/api/...
"""

import os
import time
import random
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import structlog
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    ChallengeRequired,
    FeedbackRequired,
    PleaseWaitFewMinutes,
)

load_dotenv()

app = Flask(__name__)
logger = structlog.get_logger()

# Global Instagram client (reused across requests)
ig_client = None
session_file = "session/instagram.json"


def get_instagram_client():
    """Get or create Instagram client with session persistence."""
    global ig_client

    if ig_client is not None:
        return ig_client

    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")

    if not username or not password:
        raise ValueError("INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD required")

    ig_client = Client()

    # Configure client
    ig_client.delay_range = [2, 5]  # Short delays for API calls

    # Try to load existing session
    os.makedirs("session", exist_ok=True)
    if os.path.exists(session_file):
        try:
            logger.info("Loading existing session")
            ig_client.load_settings(session_file)
            ig_client.login(username, password)
            ig_client.get_timeline_feed()  # Verify session
            logger.info("Session loaded successfully")
            return ig_client
        except Exception as e:
            logger.warning("Session load failed, doing fresh login", error=str(e))

    # Fresh login
    logger.info("Performing fresh login")
    ig_client.login(username, password)
    ig_client.dump_settings(session_file)
    logger.info("Login successful")

    return ig_client


def random_delay(min_sec=2, max_sec=5):
    """Add random delay between actions."""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "instagram-api"})


@app.route("/api/like", methods=["POST"])
def like_posts():
    """
    Like posts by their IDs.

    Request body:
    {
        "post_ids": ["123456789", "987654321"]
    }

    Response:
    {
        "success": true,
        "liked": 2,
        "failed": 0,
        "details": [...]
    }
    """
    try:
        data = request.get_json()
        post_ids = data.get("post_ids", [])

        if not post_ids:
            return jsonify({"success": False, "error": "No post_ids provided"}), 400

        client = get_instagram_client()
        results = []
        liked = 0
        failed = 0

        for post_id in post_ids:
            try:
                client.media_like(post_id)
                results.append({"post_id": post_id, "status": "liked"})
                liked += 1
                logger.info("Liked post", post_id=post_id)
                random_delay()

            except FeedbackRequired as e:
                logger.warning("Rate limited", error=str(e))
                results.append({"post_id": post_id, "status": "rate_limited"})
                failed += 1
                break

            except PleaseWaitFewMinutes:
                logger.warning("Instagram requesting wait")
                results.append({"post_id": post_id, "status": "wait_required"})
                failed += 1
                break

            except Exception as e:
                logger.error("Failed to like post", post_id=post_id, error=str(e))
                results.append({"post_id": post_id, "status": "error", "error": str(e)})
                failed += 1

        return jsonify({
            "success": failed == 0,
            "liked": liked,
            "failed": failed,
            "details": results,
        })

    except Exception as e:
        logger.error("Like endpoint error", error=str(e))
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dm", methods=["POST"])
def send_dm():
    """
    Send a direct message.

    Request body:
    {
        "username": "target_user",
        "message": "Hello!"
    }

    Response:
    {
        "success": true,
        "thread_id": "..."
    }
    """
    try:
        data = request.get_json()
        username = data.get("username")
        message = data.get("message")

        if not username or not message:
            return jsonify({"success": False, "error": "username and message required"}), 400

        client = get_instagram_client()

        # Get user ID from username
        user_id = client.user_id_from_username(username)
        random_delay()

        # Send message
        result = client.direct_send(message, [user_id])

        logger.info("DM sent", username=username)

        return jsonify({
            "success": True,
            "username": username,
            "thread_id": str(result.thread_id) if result else None,
        })

    except FeedbackRequired as e:
        logger.warning("Rate limited on DM", error=str(e))
        return jsonify({"success": False, "error": "rate_limited"}), 429

    except PleaseWaitFewMinutes:
        logger.warning("Instagram requesting wait on DM")
        return jsonify({"success": False, "error": "wait_required"}), 429

    except Exception as e:
        logger.error("DM endpoint error", error=str(e))
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/user/<username>", methods=["GET"])
def get_user(username):
    """Get user info by username."""
    try:
        client = get_instagram_client()
        user = client.user_info_by_username(username)

        return jsonify({
            "success": True,
            "user": {
                "id": str(user.pk),
                "username": user.username,
                "full_name": user.full_name,
                "biography": user.biography,
                "follower_count": user.follower_count,
                "following_count": user.following_count,
                "is_private": user.is_private,
                "is_verified": user.is_verified,
            }
        })

    except Exception as e:
        logger.error("Get user error", username=username, error=str(e))
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/user/<username>/posts", methods=["GET"])
def get_user_posts(username):
    """Get recent posts from a user."""
    try:
        count = request.args.get("count", 3, type=int)
        client = get_instagram_client()

        user_id = client.user_id_from_username(username)
        medias = client.user_medias(user_id, amount=count)

        posts = []
        for media in medias:
            posts.append({
                "id": str(media.pk),
                "type": media.media_type,
                "caption": media.caption_text[:100] if media.caption_text else None,
                "like_count": media.like_count,
                "comment_count": media.comment_count,
            })

        return jsonify({
            "success": True,
            "username": username,
            "posts": posts,
        })

    except Exception as e:
        logger.error("Get posts error", username=username, error=str(e))
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         Instagram API Server for n8n Integration           ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Endpoints:                                                ║
    ║    POST /api/like    - Like posts                          ║
    ║    POST /api/dm      - Send direct message                 ║
    ║    GET  /api/user/X  - Get user info                       ║
    ║    GET  /api/health  - Health check                        ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Make sure INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD       ║
    ║  are set in your .env file                                 ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    app.run(host="0.0.0.0", port=5000, debug=True)
