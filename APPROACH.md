# Approach

I split the problem into three layers: **capture, understand, act.**

**Capture** happens in the browser using the Web Speech API — no paid speech
service, and language selection is free since the API handles many locales. A
typed input mirrors the same path, so the app stays usable in browsers without
speech support.

**Understand** is the core. A transcript goes to FastAPI, which asks Groq
(Llama 3.3, free tier) for a strict-JSON intent: action, items, quantities,
categories, and search filters. So a demo never hard-fails on a missing key, I
wrote a deterministic rule-based fallback that handles spoken numbers, units,
price ranges, multi-item phrases, and the common add/remove/search wordings.

**Act** is plain CRUD. Every add is logged to a history table which — with a
seasonal-produce map and a substitutes table — drives the three suggestion types.

The UI is one voice-first screen: a listening orb with live transcript and
ripple feedback, a category-grouped list, and toast confirmations, fronted by a
short landing page. Optional accounts add a priced order and PDF invoice.
FastAPI serves the frontend, so it deploys as a single Render service plus a
database.
