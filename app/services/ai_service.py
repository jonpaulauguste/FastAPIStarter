import hashlib
import json
import logging
import os
import re
from urllib import request as urllib_request

from sqlmodel import Session, select

from app.database import engine
from app.models import MenuItem, Place

LOGGER = logging.getLogger(__name__)

AI_API_KEY = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://ai-gen.sundaebytestt.com/v1").rstrip("/")
AI_MODEL = os.getenv("AI_MODEL", "meta/llama-3.2-3b-instruct")
AI_TIMEOUT_SEC = float(os.getenv("AI_TIMEOUT_SEC", "4"))

_STOP_WORDS = {
    "a",
    "about",
    "an",
    "and",
    "any",
    "at",
    "be",
    "can",
    "do",
    "eat",
    "for",
    "food",
    "give",
    "i",
    "in",
    "is",
    "it",
    "like",
    "me",
    "of",
    "on",
    "or",
    "please",
    "recommend",
    "something",
    "suggest",
    "that",
    "the",
    "to",
    "want",
    "with",
}

_GREETING_PHRASES = {
    "hey",
    "hi",
    "hello",
    "yo",
    "sup",
    "good morning",
    "good afternoon",
    "good evening",
}

_INTENT_KEYWORDS = {
    "coffee": {"coffee", "cafe", "espresso", "latte", "pastry", "breakfast"},
    "spicy": {"spicy", "hot", "pepper", "curry", "jerk"},
    "quick": {"quick", "fast", "grab", "snack", "bite"},
    "cheap": {"cheap", "budget", "affordable", "price", "low", "under"},
    "healthy": {"healthy", "light", "grilled", "salad"},
}


def _tokenize_prompt(prompt: str) -> list[str]:
    words = re.findall(r"[a-zA-Z']+", prompt.lower())
    return [word for word in words if word not in _STOP_WORDS and len(word) > 1]


def _hash_text(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _is_greeting(prompt: str) -> bool:
    normalized = re.sub(r"[^a-zA-Z\s]", "", prompt.lower()).strip()
    return normalized in _GREETING_PHRASES


def _has_alpha_text(prompt: str) -> bool:
    return bool(re.search(r"[a-zA-Z]", prompt))


def _query_places_and_menu() -> tuple[list[Place], dict[int, list[MenuItem]]]:
    with Session(engine) as session:
        places = session.exec(select(Place)).all()
        menu_items = session.exec(select(MenuItem)).all()

    menu_by_place: dict[int, list[MenuItem]] = {}
    for item in menu_items:
        menu_by_place.setdefault(item.place_id, []).append(item)
    return places, menu_by_place


def _build_haystack(place: Place, menu: list[MenuItem]) -> str:
    menu_names = " ".join(item.name for item in menu)
    return " ".join(
        [
            place.name.lower(),
            place.cuisine.lower(),
            place.location.lower(),
            place.description.lower(),
            menu_names.lower(),
        ]
    )


def _rotate_items(items: list[Place], prompt: str, limit: int = 3) -> list[Place]:
    if len(items) <= limit:
        return items
    start_index = _hash_text(prompt.lower()) % len(items)
    rotated = items[start_index:] + items[:start_index]
    return rotated[:limit]


def _intent_score(prompt_lower: str, haystack: str, menu: list[MenuItem]) -> int:
    score = 0

    for keywords in _INTENT_KEYWORDS.values():
        if any(keyword in prompt_lower for keyword in keywords):
            score += sum(
                2
                for keyword in keywords
                if keyword in prompt_lower and keyword in haystack
            )

    if any(keyword in prompt_lower for keyword in _INTENT_KEYWORDS["cheap"]):
        menu_prices = [item.price for item in menu]
        if menu_prices:
            min_price = min(menu_prices)
            if min_price <= 10:
                score += 6
            elif min_price <= 20:
                score += 4
            elif min_price <= 30:
                score += 2

    if any(keyword in prompt_lower for keyword in _INTENT_KEYWORDS["coffee"]):
        if any(token in haystack for token in ("coffee", "cafe", "pastry", "cappuccino", "espresso", "latte")):
            score += 8

    if any(keyword in prompt_lower for keyword in _INTENT_KEYWORDS["spicy"]):
        if any(token in haystack for token in ("curry", "jerk", "wok", "pepper", "chow")):
            score += 7

    if any(keyword in prompt_lower for keyword in _INTENT_KEYWORDS["quick"]):
        if any(token in haystack for token in ("quick", "street", "express", "bites", "sandwich", "fries")):
            score += 5

    if any(keyword in prompt_lower for keyword in _INTENT_KEYWORDS["healthy"]):
        if any(token in haystack for token in ("grilled", "wrap", "rice", "veggie", "fresh")):
            score += 4

    return score


def _best_place_matches(
    prompt: str,
    places: list[Place],
    menu_by_place: dict[int, list[MenuItem]],
) -> tuple[list[Place], bool]:
    tokens = _tokenize_prompt(prompt)
    prompt_lower = prompt.lower()
    scored_places: list[tuple[int, float, Place]] = []

    for place in places:
        menu = menu_by_place.get(place.id or -1, [])
        haystack = _build_haystack(place, menu)

        token_hits = sum(3 for token in tokens if token in haystack)
        name_match_bonus = 8 if place.name.lower() in prompt_lower else 0
        intent_bonus = _intent_score(prompt_lower, haystack, menu)

        final_score = token_hits + name_match_bonus + intent_bonus
        scored_places.append((final_score, float(place.rating), place))

    ranked = sorted(scored_places, key=lambda row: (row[0], row[1]), reverse=True)
    if not ranked:
        return [], False

    has_signal = ranked[0][0] > 0
    if has_signal:
        top_matches = [place for _, _, place in ranked[:3]]
        return top_matches, True

    top_rated = sorted(places, key=lambda place: float(place.rating), reverse=True)
    return _rotate_items(top_rated, prompt, limit=3), False


def _top_menu_snippet(menu: list[MenuItem]) -> str:
    if not menu:
        return "popular menu items available"
    return ", ".join(item.name for item in menu[:2])


def _format_local_response(prompt: str) -> str:
    places, menu_by_place = _query_places_and_menu()

    if not places:
        return "I couldn't find any restaurants yet. Please check back after restaurants are added."

    if _is_greeting(prompt):
        featured = _rotate_items(
            sorted(places, key=lambda place: float(place.rating), reverse=True),
            prompt,
            limit=3,
        )
        featured_names = ", ".join(place.name for place in featured)
        return (
            f"Hey! I can help you pick food on campus. Popular spots right now: {featured_names}. "
            "Tell me what you want, like spicy, budget-friendly, coffee, quick bite, or a cuisine."
        )

    if not _has_alpha_text(prompt):
        return "I can help with restaurant picks. Try a request like 'cheap lunch', 'spicy food', or 'coffee near library'."

    picks, matched_by_intent = _best_place_matches(prompt, places, menu_by_place)
    if not picks:
        return "I couldn't find a good match right now. Try asking by cuisine, spice level, budget, or location."

    intro_options = (
        [
            "Based on your request, try these:",
            "Here are strong matches for what you asked:",
            "These should fit what you're looking for:",
        ]
        if matched_by_intent
        else [
            "I couldn't detect a specific preference, so here are good all-round picks:",
            "Try one of these popular spots:",
            "Here are a few campus favorites:",
        ]
    )
    intro = intro_options[_hash_text(prompt) % len(intro_options)]

    lines = [intro]
    for place in picks:
        menu = menu_by_place.get(place.id or -1, [])
        top_items = _top_menu_snippet(menu)
        lines.append(f"- {place.name} ({place.cuisine}, {place.location}) - {top_items}.")
    lines.append("Want me to narrow this down by budget, spice level, or location?")
    return "\n".join(lines)


def _ask_remote(prompt: str) -> str:
    if not AI_API_KEY:
        raise RuntimeError("AI_API_KEY is not configured.")

    payload = {
        "model": AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }

    raw_request = urllib_request.Request(
        url=f"{AI_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib_request.urlopen(raw_request, timeout=AI_TIMEOUT_SEC) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data["choices"][0]["message"]["content"].strip()


def ask_ai(prompt: str) -> str:
    clean_prompt = prompt.strip()
    if not clean_prompt:
        return "Ask me what you're in the mood for and I can suggest restaurants."

    try:
        return _ask_remote(clean_prompt)
    except Exception as error:
        LOGGER.warning("Remote AI unavailable, using local fallback: %s", error)
        return _format_local_response(clean_prompt)
