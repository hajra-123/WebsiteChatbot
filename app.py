import os
import time
from collections import defaultdict, deque

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from chatbot import MAX_MESSAGE_CHARS, stream_response
from knowledge import COMPANY_NAME, EMAIL, PHONE, QUICK_REPLIES, WELCOME_MESSAGE

app = Flask(__name__)

# Who may show the chat in an iframe. "https:" = any https website.
# GoDaddy puts custom code inside its own iframe, so a strict list can block the chat.
# To lock it down later, set ALLOWED_PARENTS on Render, e.g.
# "https://www.theessentialindia.com https://theessentialindia.com"
ALLOWED_PARENTS = os.getenv("ALLOWED_PARENTS", "https:")

# Simple abuse protection: max messages per visitor per minute
RATE_LIMIT = 20
RATE_WINDOW = 60
_hits = defaultdict(deque)


def rate_limited(ip):
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        return True
    q.append(now)
    return False


@app.after_request
def allow_embedding(resp):
    resp.headers["Content-Security-Policy"] = f"frame-ancestors 'self' {ALLOWED_PARENTS}"
    return resp


@app.route("/")
def home():
    return render_template(
        "index.html",
        company=COMPANY_NAME,
        phone=PHONE,
        email=EMAIL,
        welcome=WELCOME_MESSAGE,
        quick_replies=QUICK_REPLIES,
    )


@app.route("/health")
def health():
    # Used to "wake up" Render's free instance before the visitor types
    return "ok", 200


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Please type a message."}), 400
    if len(message) > MAX_MESSAGE_CHARS:
        return jsonify({"error": f"Please keep messages under {MAX_MESSAGE_CHARS} characters."}), 400

    ip = (request.headers.get("X-Forwarded-For", request.remote_addr or "") or "").split(",")[0].strip()
    if rate_limited(ip):
        return jsonify({"error": "You're sending messages very quickly. Please wait a moment."}), 429

    return Response(
        stream_with_context(stream_response(message.strip(), data.get("history"))),
        mimetype="text/plain",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=int(os.getenv("PORT", 5000)))
