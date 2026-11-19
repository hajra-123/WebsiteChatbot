import os

from dotenv import load_dotenv
from openai import OpenAI

from knowledge import SYSTEM_PROMPT, EMAIL

load_dotenv()

# Works with OpenAI by default. To use another provider (e.g. Google Gemini's free
# tier), set LLM_BASE_URL and OPENAI_MODEL on Render - no code change needed.
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL") or None,
)
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

MAX_HISTORY = 12          # how many earlier messages the AI can "remember"
MAX_MESSAGE_CHARS = 1000  # longest message we accept from a visitor

FALLBACK = (
    "⚠️ Our assistant is temporarily unavailable. Please try again in a moment "
    f"or email us at {EMAIL}."
)


def _clean_history(history):
    """Keep only valid, recent user/assistant turns sent by the browser."""
    cleaned = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role, content = item.get("role"), item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            cleaned.append({"role": role, "content": content.strip()[: MAX_MESSAGE_CHARS * 2]})
    return cleaned[-MAX_HISTORY:]


def stream_response(user_message, history=None):
    """Yield the AI's answer piece by piece (so the visitor sees it being typed)."""
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + _clean_history(history)
        + [{"role": "user", "content": user_message[:MAX_MESSAGE_CHARS]}]
    )
    produced = False
    try:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=1000,  # headroom: some models count internal 'thinking' in this limit
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                produced = True
                yield chunk.choices[0].delta.content
    except Exception as exc:  # network issue, bad key, quota, etc.
        print("OpenAI error:", repr(exc))
    if not produced:
        yield FALLBACK
