# Approach

I split the problem into three layers: **Capture → Understand → Act.**

**Capture** happens entirely in the browser via the Web Speech API — no paid
speech-to-text service, and multilingual support comes almost for free since
the API already handles multiple locales. A typed-input fallback mirrors the
same code path, so the app stays fully usable in browsers without speech
support, or when a user simply prefers typing.

**Understand** is the core of the system. Every transcript is sent to
FastAPI, which prompts Groq (Llama 3.3, free tier) to return a strict-JSON
structured intent — action, items, quantities, units, categories, and search
filters. Since a live demo should never hard-fail on a missing key or a rate
limit, I built a deterministic rule-based parser as a fallback. It handles
spoken numbers, units, price ranges, multi-item phrases, and the common
add/remove/search wordings, so basic functionality never depends entirely on
an external service.

**Act** is straightforward CRUD on top of that structured intent. Every add
is logged to a purchase-history table, which — combined with a seasonal
product map and a substitutes table — powers the three suggestion types
(history, seasonal, substitute).

The UI is a single voice-first screen: a large listening orb with live
transcript and ripple feedback, a category-grouped shopping list, and toast
confirmations, fronted by a short landing page. Optional accounts unlock a
priced order flow and a downloadable PDF invoice. FastAPI serves the frontend
directly, so the whole application deploys as one Render service plus a
database — no separate frontend host, no build step, minimal moving parts.

**Trade-offs:** favoring a browser-native speech API over a dedicated STT
service traded some recognition accuracy for zero infrastructure cost and
faster setup within the time window. Similarly, keeping the LLM as an
enhancement rather than a dependency trades a bit of parsing flexibility for
reliability — the app keeps working even when Groq doesn't.
