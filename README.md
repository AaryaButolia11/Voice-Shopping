# 🥬 Speaklist — Voice Command Shopping Assistant

Build your shopping list by **talking**. Add items, set quantities, remove things,
and search a product catalogue by price or brand — all with your voice, in ten
languages. Speaklist understands natural phrasing ("I want to buy bananas",
"add milk and eggs", "find toothpaste under $5"), auto-categorises every item,
and offers smart suggestions from your history, the season, and common substitutes.

A **landing page**, **voice app**, **account sign-in**, and a **priced order +
PDF invoice** flow are all included and wired to one FastAPI backend.

---

## ✨ Features (mapped to the brief)

**1. Voice input**
- **Voice recognition** in the browser via the Web Speech API — tap the mic and talk.
- **Natural language** understanding: "add milk", "I need apples", "I want to buy bananas", "buy 5 oranges" all work.
- **Multilingual**: pick from English, Spanish, French, German, Italian, Portuguese, Hindi, Japanese, and Chinese.
- **Typed fallback** everywhere, so the app is fully usable where speech isn't supported.

**2. Smart suggestions**
- **History** — items you add often that aren't on the list right now ("You've added this 3 times — running low?").
- **Seasonal** — produce in season for the current month.
- **Substitutes** — alternatives for items on your list (e.g. oat milk for milk).

**3. Shopping list management**
- **Add / remove / update** by voice or type, including multiple items at once ("add milk and eggs and 3 oranges").
- **Auto-categorised** into produce, dairy, bakery, pantry, and more.
- **Quantities & units** — "add 2 bottles of water", "buy 5 oranges", "change eggs to a dozen".
- Check items off as you shop; adjust quantity inline; clear the list.

**4. Voice-activated search**
- **Item search** across a product catalogue with brand and size ("find organic apples").
- **Price / brand filtering** — "toothpaste under $5", "milk under 5 dollars".

**UI / UX**
- Minimalist, mobile-first, voice-first single screen with a **listening orb**, live transcript, and ripple feedback.
- Real-time confirmations (toasts), loading states, dark / light mode, keyboard focus, and reduced-motion support.

**Extras (bonus)**
- Email + password **accounts** (JWT), and a one-tap **"Create order"** that prices your list from the catalogue and generates a downloadable **PDF invoice**.

---

## 🏗️ Architecture

Three layers — **capture → understand → act**:

- **Capture** happens in the browser (Web Speech API), with a typed input that mirrors the same path.
- **Understand** is a FastAPI `/api/command` endpoint. It first tries **Groq (Llama 3.3, free tier)** for strict-JSON intent parsing; if no API key is set or the call fails, it falls back to a **deterministic rule-based parser** that handles spoken numbers, units, price ranges, and multi-item phrases. The app never hard-fails on a missing key.
- **Act** is plain CRUD over the database. Every add is logged to a history table that — with a seasonal map and a substitutes table — powers the suggestions.

```
speaklist-voice-shopping/
├── backend/
│   ├── main.py          # FastAPI app + all routes
│   ├── nlp.py           # Groq + rule-based command parser
│   ├── catalog.py       # categories, seasonal map, substitutes, product catalogue
│   ├── suggestions.py   # history / seasonal / substitute engine
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   ├── database.py      # engine/session (SQLite dev, Postgres prod)
│   ├── auth.py          # bcrypt hashing + JWT
│   ├── invoices.py      # ReportLab PDF invoices
│   └── requirements.txt
├── frontend/
│   ├── index.html       # landing + app + modals (single page)
│   ├── app.js           # router, voice engine, list, suggestions, auth, checkout
│   ├── styles.css       # design system, dark mode, responsive
│   ├── config.js        # API base URL
│   └── vercel.json      # optional split-deploy config
├── render.yaml          # one-file Render Blueprint (backend serves the frontend)
├── APPROACH.md          # 200-word write-up
├── .env.example
└── README.md
```

FastAPI serves the frontend as static files, so the whole thing runs as a
**single service** (plus a database). You can also split it (frontend on Vercel,
backend on Render) by setting `API_BASE` in `frontend/config.js`.

---

## 🚀 Run locally

**Prerequisites:** Python 3.11+

```bash
cd backend
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt

# optional: enable smarter LLM parsing (free key from https://console.groq.com)
cp ../.env.example .env           # then edit values

uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** — FastAPI serves the frontend and the API together.
Interactive API docs are at **http://localhost:8000/docs**.

> **Browser note:** the Web Speech API works best in Chrome and Edge. In browsers
> without it (e.g. Firefox), the mic is hidden and the typed command box handles
> everything.

---

## ☁️ Deploy

### Option A — one service on Render (recommended)

1. Push this repo to GitHub.
2. In Render: **New → Blueprint**, point it at the repo. `render.yaml` provisions a
   web service **and** a free Postgres database, and wires `DATABASE_URL` automatically.
3. (Optional) In the service settings, set `GROQ_API_KEY` for smarter parsing.
4. Deploy. The single URL serves both the app and the API.

### Option B — split deploy

- Backend on Render (as above).
- Frontend on Vercel: set the project root to `frontend/`, and set
  `window.APP_CONFIG.API_BASE` in `frontend/config.js` to your backend URL.

---

## 🔧 Environment variables

| Variable          | Default                     | Purpose                                             |
| ----------------- | --------------------------- | --------------------------------------------------- |
| `DATABASE_URL`    | `sqlite:///./shopping.db`   | DB connection. Render provides a Postgres URL.      |
| `SECRET_KEY`      | dev fallback                | JWT signing key — **set a strong value in prod**.   |
| `GROQ_API_KEY`    | _(unset)_                   | Enables LLM parsing. Without it, rules are used.    |
| `GROQ_MODEL`      | `llama-3.3-70b-versatile`   | Groq model name.                                    |
| `ALLOWED_ORIGINS` | `*`                         | Comma-separated CORS origins for split deploys.     |

---

## 📡 API reference

**List & voice (no auth)**

| Method   | Path                | Description                                  |
| -------- | ------------------- | -------------------------------------------- |
| `GET`    | `/api/health`       | Service status + whether LLM parsing is on   |
| `GET`    | `/api/items`        | Current list                                 |
| `POST`   | `/api/items`        | Add an item directly                         |
| `PATCH`  | `/api/items/{id}`   | Update quantity / name / checked             |
| `DELETE` | `/api/items/{id}`   | Remove an item                               |
| `DELETE` | `/api/items`        | Clear the list                               |
| `POST`   | `/api/command`      | Parse a voice/typed transcript and act       |
| `GET`    | `/api/suggestions`  | History / seasonal / substitute suggestions  |
| `GET`    | `/api/search`       | Product search (query, brand, price, tags)   |

**Accounts & orders (JWT)**

| Method | Path                          | Description                          |
| ------ | ----------------------------- | ------------------------------------ |
| `POST` | `/api/auth/register`          | Create an account, returns a token   |
| `POST` | `/api/auth/login`             | Log in, returns a token              |
| `GET`  | `/api/auth/me`                | Current user                         |
| `POST` | `/api/list/checkout`          | Turn the list into a priced order    |
| `GET`  | `/api/orders`                 | A user's orders                      |
| `GET`  | `/api/orders/{id}/invoice`    | Download the invoice PDF             |

Example:

```bash
curl -X POST localhost:8000/api/command \
  -H "Content-Type: application/json" \
  -d '{"transcript":"add 2 bottles of sparkling water and a dozen eggs","language":"en"}'
```

---

## 🧰 Tech stack

- **Backend:** FastAPI, SQLAlchemy 2, Pydantic v2, python-jose (JWT), bcrypt, ReportLab, httpx
- **Frontend:** Vanilla JS (no build step), Web Speech API, CSS custom properties
- **NLP:** Groq (Llama 3.3, free tier) with a deterministic rule-based fallback
- **DB:** SQLite (dev) / PostgreSQL (prod)
- **Hosting:** Render (single service) or Render + Vercel (split)

---

## 🧪 Quick test checklist

- [ ] "add milk and a dozen eggs" adds two categorised items
- [ ] "buy 5 oranges" sets quantity 5
- [ ] "remove bread from my list" removes it
- [ ] "find toothpaste under $5" returns filtered results
- [ ] Suggestions show history / seasonal / substitute tags
- [ ] Typed commands work when the mic isn't available
- [ ] Sign in → Create order → download the PDF invoice
- [ ] Dark mode + mobile layout hold up
