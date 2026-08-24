"""
Natural-language understanding for voice commands.

Primary path: Groq (OpenAI-compatible) chat completions with a strict JSON
schema. If no GROQ_API_KEY is set, or the call fails, we fall back to a
deterministic rule-based parser so the product never hard-fails on a command.

The parser turns a free-form transcript such as:
    "add two bottles of sparkling water"
    "I need some organic apples under 5 dollars"
    "remove the milk from my list"
into a structured intent the API layer can act on.
"""

from __future__ import annotations

import json
import os
import re

import httpx

from catalog import categorize

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are the parser for a voice shopping-list assistant.
Convert the user's transcript into a single JSON object. Respond with JSON only,
no prose, no markdown fences.

Schema:
{
  "intent": "add" | "remove" | "update" | "search" | "clear" | "check" | "unknown",
  "items": [
    {"name": string, "quantity": number, "unit": string|null, "category": string|null}
  ],
  "search": {
    "query": string,
    "brand": string|null,
    "price_min": number|null,
    "price_max": number|null,
    "tags": [string]
  }
}

Rules:
- "add", "buy", "need", "want", "get", "put", "grab" => intent "add".
- "remove", "delete", "take off", "cross off" => intent "remove".
- "change", "make it", "update", "set" a quantity => intent "update".
- "find", "search", "look for", "show me" => intent "search".
- "clear", "empty", "start over" the list => intent "clear".
- "check off", "mark", "got" => intent "check".
- Singularise item names ("apples" stays "apples" only if naturally plural is fine; keep it readable).
- Parse spoken numbers ("two", "a couple", "half a dozen") into numeric quantity. Default quantity 1.
- category must be one of: produce, dairy, meat & seafood, bakery, pantry, frozen,
  beverages, snacks, household, personal care, baby, pet, other. Pick the best fit or null.
- For search, extract price limits ("under 5", "less than $10") and descriptive
  tags like "organic", "gluten-free". Put the core noun in query.
- Always return the full schema; use empty arrays / nulls where not applicable.
The transcript may be in any language; translate item names to English for the fields.
"""

# Spoken-number lexicon for the fallback parser.
_WORD_NUMBERS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "dozen": 12, "couple": 2, "few": 3, "half": 0.5,
}
_UNITS = {
    "bottle", "bottles", "can", "cans", "box", "boxes", "bag", "bags", "pack",
    "packs", "jar", "jars", "carton", "cartons", "loaf", "loaves", "bunch",
    "bunches", "dozen", "lb", "lbs", "pound", "pounds", "kg", "gram", "grams",
    "liter", "liters", "gallon", "gallons", "cup", "cups", "piece", "pieces",
    "packet", "packets", "container", "containers",
}
# Verb phrases mapped to intents, longest first so multi-word phrases win.
_VERB_INTENTS: list[tuple[str, str]] = [
    ("take off", "remove"), ("cross off", "remove"), ("take out", "remove"),
    ("look for", "search"), ("show me", "search"), ("search for", "search"),
    ("check off", "check"), ("cross out", "check"), ("pick up", "add"),
    ("remove", "remove"), ("delete", "remove"), ("find", "search"),
    ("search", "search"), ("purchase", "add"), ("add", "add"), ("buy", "add"),
    ("make it", "update"), ("change", "update"), ("update", "update"),
    ("set", "update"), ("need", "add"), ("want", "add"), ("grab", "add"),
    ("get", "add"), ("put", "add"), ("mark", "check"),
]
_CLEAR_WORDS = ("clear the list", "empty the list", "start over", "clear my list")
# Connector words stripped from the start of the item phrase after the verb.
_LEADING_CONNECTORS = ("to buy", "to get", "to purchase", "to", "some", "me", "a few of")
_STOPWORDS = {
    "the", "a", "an", "some", "my", "list", "to", "from", "of", "please",
    "i", "would", "like", "for", "and", "me", "on", "in", "shopping",
}


def parse_command(transcript: str, language: str = "en") -> dict:
    """Return a normalised intent dict. Adds an ``_used_llm`` flag internally."""
    transcript = (transcript or "").strip()
    if not transcript:
        return _empty_result("unknown", used_llm=False)

    if GROQ_API_KEY:
        try:
            result = _parse_with_groq(transcript, language)
            result["_used_llm"] = True
            return _normalise(result)
        except Exception:  # noqa: BLE001 - any failure => graceful fallback
            pass

    result = _parse_with_rules(transcript)
    result["_used_llm"] = False
    return _normalise(result)


# --------------------------------------------------------------------------- #
# Groq path                                                                    #
# --------------------------------------------------------------------------- #
def _parse_with_groq(transcript: str, language: str) -> dict:
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=15) as client:
        resp = client.post(GROQ_URL, json=payload, headers=headers)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)


# --------------------------------------------------------------------------- #
# Rule-based fallback                                                          #
# --------------------------------------------------------------------------- #
def _parse_with_rules(transcript: str) -> dict:
    text = re.sub(r"\s+", " ", transcript.lower().strip())

    if any(phrase in text for phrase in _CLEAR_WORDS):
        return _empty_result("clear")

    # Find the earliest verb phrase anywhere in the sentence. This lets us skip
    # lead-ins like "I", "I'd like to", "can you please" without enumerating them.
    intent = "add"
    body = text
    best_pos = None
    for phrase, mapped_intent in _VERB_INTENTS:
        m = re.search(rf"\b{re.escape(phrase)}\b", text)
        if m and (best_pos is None or m.start() < best_pos):
            best_pos = m.start()
            intent = mapped_intent
            body = text[m.end():].strip()

    # Strip connector words the verb leaves behind ("want to buy X" -> "X").
    changed = True
    while changed:
        changed = False
        for conn in _LEADING_CONNECTORS:
            if body.startswith(conn + " "):
                body = body[len(conn):].strip()
                changed = True

    if intent == "search":
        return {"intent": "search", "items": [], "search": _parse_search(body)}

    if intent == "update":
        name, quantity = _parse_update(body)
        name = _clean_name(name)
        if not name:
            return _empty_result("unknown")
        return {
            "intent": "update",
            "items": [{"name": name, "quantity": quantity, "unit": None,
                       "category": categorize(name)}],
            "search": _empty_search(),
        }

    # add / remove / check may name several items at once:
    # "milk and eggs", "2 avocados and a loaf of bread", "apples, bananas".
    items = []
    for fragment in _split_items(body):
        quantity, unit, name = _parse_quantity_unit(fragment)
        name = _clean_name(name)
        if not name:
            continue
        items.append({
            "name": name,
            "quantity": quantity,
            "unit": unit,
            "category": categorize(name),
        })

    if not items:
        return _empty_result("unknown")

    return {"intent": intent, "items": items, "search": _empty_search()}


# Split a phrase into separate items on natural connectors ("and", commas, "&").
_ITEM_SPLIT = re.compile(r"\s*(?:,|;|/|&|\band\b|\bplus\b)\s*")


def _split_items(body: str) -> list[str]:
    parts = [p.strip() for p in _ITEM_SPLIT.split(body) if p.strip()]
    if len(parts) <= 1:
        return [body.strip()] if body.strip() else []
    return parts


def _parse_search(body: str) -> dict:
    price_min = price_max = None

    # "under 5", "less than $10", "below 3.50"
    m = re.search(r"(under|below|less than|cheaper than)\s*\$?\s*(\d+(?:\.\d+)?)", body)
    if m:
        price_max = float(m.group(2))
    m = re.search(r"(over|above|more than)\s*\$?\s*(\d+(?:\.\d+)?)", body)
    if m:
        price_min = float(m.group(2))
    m = re.search(r"between\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:and|-)\s*\$?\s*(\d+(?:\.\d+)?)", body)
    if m:
        price_min, price_max = float(m.group(1)), float(m.group(2))

    tags = [t for t in ("organic", "gluten-free", "vegan", "low-fat", "whole wheat")
            if t in body]

    # Remove price phrases and tags from the query.
    query = re.sub(r"(under|below|less than|cheaper than|over|above|more than|between).*", "", body)
    for tag in tags:
        query = query.replace(tag, "")
    query = _clean_name(query)

    return {
        "query": query,
        "brand": None,
        "price_min": price_min,
        "price_max": price_max,
        "tags": tags,
    }


def _parse_quantity_unit(body: str) -> tuple[float, str | None, str]:
    tokens = body.split()
    quantity: float = 1
    unit: str | None = None
    start = 0

    if tokens:
        first = tokens[0]
        # "a couple of avocados" / "a dozen eggs": article + spoken number.
        if first in ("a", "an") and len(tokens) > 1 and tokens[1] in _WORD_NUMBERS and tokens[1] != "half":
            quantity = _WORD_NUMBERS[tokens[1]]
            start = 2
        elif re.fullmatch(r"\d+(\.\d+)?", first):
            quantity = float(first)
            start = 1
        elif first in _WORD_NUMBERS:
            quantity = _WORD_NUMBERS[first]
            start = 1
            # "half a dozen"
            if quantity == 0.5 and len(tokens) > 2 and tokens[2] in _WORD_NUMBERS:
                quantity = 0.5 * _WORD_NUMBERS[tokens[2]]
                start = 3

    # Optional unit right after the number, e.g. "2 bottles of water".
    if start < len(tokens) and tokens[start] in _UNITS:
        unit = tokens[start]
        start += 1
        if start < len(tokens) and tokens[start] == "of":
            start += 1

    name = " ".join(tokens[start:])
    return quantity, unit, name


def _parse_update(body: str) -> tuple[str, float]:
    """Parse 'milk to 3' / 'eggs to a dozen' -> (name, quantity)."""
    quantity: float = 1
    m = re.search(r"\bto\b(.*)$", body)
    if m:
        # "milk to a dozen" -> parse the tail with the same number logic.
        quantity, _, _ = _parse_quantity_unit(m.group(1).strip() + " x")
        name = body[: m.start()].strip()
    else:
        # No "to": accept a trailing number, e.g. "milk 3".
        tail = body.split()[-1] if body.split() else ""
        if re.fullmatch(r"\d+(\.\d+)?", tail):
            quantity = float(tail)
        elif tail in _WORD_NUMBERS:
            quantity = _WORD_NUMBERS[tail]
        name = re.sub(r"\s*\b[\w.]+\b\s*$", "", body).strip() if quantity != 1 else body
    return name, quantity


def _clean_name(name: str) -> str:
    words = [w for w in re.sub(r"[^\w\s-]", "", name).split() if w not in _STOPWORDS]
    return " ".join(words).strip()


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _empty_search() -> dict:
    return {"query": "", "brand": None, "price_min": None, "price_max": None, "tags": []}


def _empty_result(intent: str, used_llm: bool = False) -> dict:
    return {"intent": intent, "items": [], "search": _empty_search(), "_used_llm": used_llm}


def _normalise(result: dict) -> dict:
    """Guarantee the shape and fill categories for any items missing one."""
    result.setdefault("intent", "unknown")
    result.setdefault("items", [])
    result.setdefault("search", _empty_search())

    clean_items = []
    for item in result.get("items") or []:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        try:
            quantity = float(item.get("quantity") or 1)
        except (TypeError, ValueError):
            quantity = 1
        category = item.get("category") or categorize(name)
        clean_items.append({
            "name": name,
            "quantity": quantity,
            "unit": item.get("unit"),
            "category": category,
        })
    result["items"] = clean_items

    search = result.get("search") or _empty_search()
    for key, default in _empty_search().items():
        search.setdefault(key, default)
    result["search"] = search
    return result
