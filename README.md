# 🥬 Speaklist — Voice Command Shopping Assistant

> A voice-first shopping assistant that converts natural language commands into an intelligent, organized shopping list.

🔗 **Live Demo:** https://voice-shopping-assistant-hqho.onrender.com/

🔗 **GitHub:** https://github.com/AaryaButolia11/Voice-Shopping

---

## 📌 Overview

**Speaklist** is a voice-based shopping assistant designed to make shopping-list management as simple as speaking naturally.

Users can add, remove, update, and search for products using voice or text commands.

Examples:
- 🎙️ `"Add milk"`
- 🎙️ `"I need apples"`
- 🎙️ `"Buy 5 oranges"`
- 🎙️ `"Add 2 bottles of water"`
- 🎙️ `"Remove bread from my list"`
- 🎙️ `"Find organic apples"`
- 🎙️ `"Find toothpaste under $5"`

The application combines **browser-based speech recognition, NLP, smart recommendations, product search, authentication, and order generation** into a single responsive application.

---

## ✨ Features

### 🎙️ 1. Voice Input & NLP

- Browser-based voice recognition using the **Web Speech API**
- Natural language command understanding
- Typed input fallback
- Multiple-item commands
- Quantity and unit extraction
- Add / remove / update actions
- Voice-based product search

Examples:

```text
"Add milk"
"I want to buy bananas"
"Add 2 bottles of water and a dozen eggs"
"Remove bread from my list"
"Change eggs to a dozen"
```

### 🌍 2. Multilingual Support

Voice commands can be recognized in multiple languages through the browser's speech-recognition configuration.

Supported languages include:
- 🇬🇧 English
- 🇪🇸 Spanish
- 🇫🇷 French
- 🇩🇪 German
- 🇮🇹 Italian
- 🇵🇹 Portuguese
- 🇮🇳 Hindi
- 🇯🇵 Japanese
- 🇨🇳 Chinese

A typed-command fallback is provided for browsers without Web Speech API support.

### 🧠 3. Natural Language Processing

The `/api/command` endpoint processes natural-language transcripts.

```text
User Speech
     ↓
Web Speech API
     ↓
Transcript
     ↓
FastAPI /api/command
     ↓
Groq / Llama
     ↓
Structured Intent
     ↓
Application Logic
     ↓
Database
     ↓
Updated Shopping List
```

The application uses Groq-hosted Llama for structured intent parsing when an API key is available.

A deterministic rule-based parser acts as a fallback when:
- The API key is unavailable
- The LLM request fails
- The external service is temporarily unavailable

This prevents the core shopping-list functionality from completely depending on an external AI service.

### 💡 4. Smart Suggestions

Speaklist generates recommendations using three signals:

#### 🧾 Shopping History
Frequently added products can be recommended based on previous shopping behavior.
*Example:* `"You've added bread 3 times — running low?"`

#### 🌱 Seasonal Recommendations
The application maintains a seasonal-product mapping and recommends products appropriate for the current month.

#### 🔄 Product Substitutes
Alternative products can be suggested for items currently on the shopping list.
*Example:*
```text
Milk
 ├── Almond Milk
 ├── Oat Milk
 └── Soy Milk
```

Suggestions are classified as:
- `history`
- `seasonal`
- `substitute`

### 🛒 5. Shopping List Management

Users can manage their list through voice or typed commands.

- **Add Items:** `"Add milk"`, `"Buy 5 oranges"`, `"Add 2 bottles of water"`
- **Remove Items:** `"Remove milk"`, `"Remove bread from my list"`
- **Update Items:** `"Change eggs to a dozen"`
- **Multiple Items:** `"Add milk, eggs and 3 oranges"`

#### Automatic Categorization
Products are automatically categorized into groups such as:
- Produce
- Dairy
- Bakery
- Pantry
- Snacks
- Beverages
- Household

#### Quantity Management
The parser supports natural quantity expressions:
- 5 oranges
- 2 bottles of water
- a dozen eggs
- 3 packets of biscuits

### 🔎 6. Voice-Activated Product Search

Users can search the product catalogue using natural language.

Examples:
- `"Find organic apples"`
- `"Find toothpaste under $5"`
- `"Find milk from Brand X"`
- `"Find shampoo between $5 and $10"`

Search supports:
- Product name
- Brand
- Size
- Tags
- Minimum price
- Maximum price

### 🎨 7. UI / UX

The application follows a voice-first and mobile-first design approach.

**UX Features:**
- Minimal shopping-list interface
- Large listening orb
- Live speech transcript
- Voice activity feedback
- Action confirmations
- Loading states
- Error states
- Typed-command fallback
- Dark / light mode
- Responsive mobile layout
- Keyboard focus support
- Reduced-motion support

Primary interaction flow:

```text
Tap Microphone
      ↓
Speak Naturally
      ↓
Live Transcript
      ↓
Command Processing
      ↓
Action Confirmation
      ↓
Updated Shopping List
```

### 👤 8. Authentication

The application includes account functionality using:
- Email/password registration
- Password hashing
- JWT authentication
- Protected user endpoints

Authentication is handled by the FastAPI backend.

### 🧾 9. Order & PDF Invoice

Users can convert their shopping list into a priced order.

```text
Shopping List
      ↓
Product Catalogue
      ↓
Price Calculation
      ↓
Order Creation
      ↓
PDF Invoice
```

PDF invoices are generated using ReportLab.

---

## 🏗️ Architecture

Speaklist follows a simple Capture → Understand → Act architecture.

```text
                    ┌─────────────────────┐
                    │       Browser       │
                    │                     │
                    │  Web Speech API     │
                    │  Typed Input        │
                    │  Shopping UI        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │                     │
                    │ /api/command        │
                    │ /api/items          │
                    │ /api/search         │
                    │ /api/suggestions    │
                    │ /api/auth/*         │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    NLP Pipeline     │
                    │                     │
                    │  Groq / Llama       │
                    │        ↓            │
                    │ Rule-based Fallback │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Business Logic    │
                    │                     │
                    │ CRUD                │
                    │ Suggestions         │
                    │ Search              │
                    │ Orders              │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Database       │
                    │                     │
                    │ Users               │
                    │ Items               │
                    │ Purchase History    │
                    │ Orders              │
                    └─────────────────────┘
```

---

## 📁 Project Structure

```text
Voice-Shopping/
│
├── backend/
│   ├── main.py              # FastAPI application & API routes
│   ├── nlp.py               # Groq + rule-based NLP parser
│   ├── catalog.py           # Product catalogue & recommendation data
│   ├── suggestions.py       # History / seasonal / substitute engine
│   ├── models.py            # SQLAlchemy database models
│   ├── schemas.py           # Pydantic schemas
│   ├── database.py          # Database configuration
│   ├── auth.py              # JWT authentication
│   ├── invoices.py          # PDF invoice generation
│   └── requirements.txt
│
├── frontend/
│   ├── index.html           # Main application UI
│   ├── app.js               # Application & voice logic
│   ├── styles.css           # Responsive styling
│   ├── config.js            # API configuration
│   └── vercel.json          # Optional Vercel deployment
│
├── render.yaml              # Render deployment configuration
├── APPROACH.md              # Assignment approach write-up
├── .env.example             # Environment variable template
├── .gitignore
└── README.md
```

---

## 🔌 API Reference

### Shopping List & Voice

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health and NLP status |
| `GET` | `/api/items` | Get current shopping list |
| `POST` | `/api/items` | Add an item |
| `PATCH` | `/api/items/{id}` | Update an item |
| `DELETE` | `/api/items/{id}` | Remove an item |
| `DELETE` | `/api/items` | Clear shopping list |
| `POST` | `/api/command` | Process voice/text command |
| `GET` | `/api/suggestions` | Get smart suggestions |
| `GET` | `/api/search` | Search product catalogue |

### Authentication & Orders

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register a user |
| `POST` | `/api/auth/login` | Authenticate user |
| `GET` | `/api/auth/me` | Get current user |
| `POST` | `/api/list/checkout` | Create an order |
| `GET` | `/api/orders` | Get user orders |
| `GET` | `/api/orders/{id}/invoice` | Generate/download invoice |

#### Example API Request

```bash
curl -X POST http://localhost:8000/api/command \
  -H "Content-Type: application/json" \
  -d '{"transcript":"add 2 bottles of sparkling water and a dozen eggs","language":"en"}'
```

---

## 🧰 Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy 2
- Pydantic v2
- JWT / bcrypt
- ReportLab
- httpx

### Frontend
- HTML5
- CSS3
- Vanilla JavaScript
- Web Speech API

### AI / NLP
- Groq API
- Llama 3.3
- Deterministic rule-based NLP fallback

### Database
- SQLite (local development)
- PostgreSQL (production)

### Deployment
- Render (Single-service deployment serving FastAPI & static frontend)

---

## 🚀 Run Locally

### Prerequisites
- Python 3.11+
- Git
- Modern browser (Chrome or Edge recommended)

### 1. Clone the repository
```bash
git clone https://github.com/AaryaButolia11/Voice-Shopping.git
cd Voice-Shopping
```

### 2. Create virtual environment
```bash
cd backend
python -m venv venv
```

Activate virtual environment:
- **Windows:** `venv\Scripts\activate`
- **macOS / Linux:** `source venv/bin/activate`

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
DATABASE_URL=sqlite:///./shopping.db
SECRET_KEY=your_secret_key
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
ALLOWED_ORIGINS=*
```

> ⚠️ `.env` is intentionally excluded from Git. Never commit API keys or secrets.

### 5. Start the backend
```bash
uvicorn main:app --reload --port 8000
```

- **Application UI:** `http://localhost:8000`
- **API Documentation:** `http://localhost:8000/docs`

---

## ☁️ Deployment

The application is deployed as a single Render service.

```text
                    Render
                      │
             ┌────────▼────────┐
             │     FastAPI     │
             │                 │
             │ Backend APIs    │
             │        +        │
             │ Frontend files  │
             └────────┬────────┘
                      │
                PostgreSQL
```

- **Production URL:** https://voice-shopping-assistant-hqho.onrender.com/

### Deployment Flow
1. Repository hosted on GitHub
2. Render connected to the repository
3. Render installs `backend/requirements.txt`
4. Uvicorn starts the FastAPI application
5. FastAPI serves the frontend as static files
6. Production database uses PostgreSQL
7. Environment secrets are configured through Render

---

## 🧪 Testing & Validation

The following scenarios were tested against the application:

- [x] Add milk and eggs
- [x] Add 5 oranges
- [x] Add 2 bottles of water
- [x] Remove bread
- [x] Update quantity
- [x] Multiple-item commands
- [x] Product search
- [x] Price filtering
- [x] Brand filtering
- [x] History-based suggestions
- [x] Seasonal suggestions
- [x] Substitute suggestions
- [x] Typed commands
- [x] Authentication
- [x] Order creation
- [x] PDF invoice generation
- [x] Responsive UI
- [x] Dark/light mode
- [x] LLM fallback behavior

### Example Command Tests

| Input | Expected Behavior |
| :--- | :--- |
| `Add milk` | Adds milk to the list |
| `Buy 5 oranges` | Adds oranges with quantity 5 |
| `Add a dozen eggs` | Adds eggs with quantity 12 |
| `Remove bread` | Removes bread |
| `Find organic apples` | Searches catalogue |
| `Find toothpaste under $5` | Applies price filter |
| `Add milk and eggs` | Adds multiple products |

---

## 🛡️ Error Handling & Reliability

The application includes production-oriented safeguards:
- Input validation through Pydantic
- Standard HTTP error responses
- Database transaction handling
- JWT authentication & Password hashing
- LLM failure fallback
- Loading and action-confirmation states
- User-facing error messages
- Typed-input fallback for unsupported speech recognition

A key design decision was to make LLM parsing an enhancement rather than a hard dependency:

```text
Groq unavailable
      ↓
Rule-based parser
      ↓
Continue processing command
```

This keeps basic functionality available even during external API failures.

---

## 📋 Assignment Requirement Mapping

| Assignment Requirement | Implementation |
| :--- | :--- |
| **Voice command recognition** | Web Speech API |
| **Natural language processing** | Groq / Llama + rule-based fallback |
| **Multilingual support** | Browser speech recognition language selection |
| **Product recommendations** | Purchase-history engine |
| **Seasonal recommendations** | Seasonal product mapping |
| **Product substitutes** | Substitute mapping |
| **Add / remove / modify** | Voice + typed commands |
| **Automatic categorization** | Product categorization logic |
| **Quantity management** | NLP quantity/unit extraction |
| **Voice product search** | `/api/command` + `/api/search` |
| **Price filtering** | Product search filters |
| **Brand filtering** | Product search filters |
| **Minimalist interface** | Responsive single-page UI |
| **Visual feedback** | Transcript, loading states, toasts |
| **Mobile optimization** | Responsive CSS |
| **Voice-only interaction** | Speech-first workflow |
| **Hosting** | Render |
| **Error handling** | Validation + fallback logic |
| **Documentation** | README + APPROACH.md |

---

## 🧠 Design Decisions

- **Why Web Speech API?**
  The browser already provides speech recognition capabilities without requiring an additional speech-to-text infrastructure layer. This keeps the project lightweight and suitable for an 8-hour implementation window.

- **Why Groq + Llama?**
  LLMs are useful for interpreting flexible natural-language commands where traditional keyword matching becomes brittle (e.g., *"Could you please put five oranges on my shopping list?"* vs. *"I think I need 5 oranges"*).

- **Why a rule-based fallback?**
  An external LLM should not be a single point of failure for basic list management. The fallback handles common command patterns deterministically.

- **Why a single Render service?**
  The frontend is a static Vanilla JS application with no build step. FastAPI can serve these files directly, reducing deployment complexity while keeping the frontend and backend under one origin.

---

## ⚠️ Known Limitations

- Web Speech API availability depends on browser support.
- Speech recognition quality depends on the browser and user's microphone.
- The product catalogue is demonstration/test data rather than a live retailer catalogue.
- Seasonal and substitute recommendations are based on predefined mappings.
- LLM parsing depends on the availability and limits of the configured Groq API.
- Render's free infrastructure may experience cold starts.

---

## 📈 Possible Future Improvements

- Real supermarket/product APIs integration
- User-specific recommendation models
- Semantic product search using embeddings
- Persistent per-user shopping history
- Better multilingual NLP models
- Streaming voice responses
- Barcode scanning
- Price comparison across retailers
- Real payment gateway integration
- Push notifications for shopping reminders
- Personalized seasonal recommendations
- Automated evaluation dataset for NLP accuracy

---

## 📄 Assignment Approach

A concise 200-word approach write-up is included separately in `APPROACH.md`. It covers:
- Problem understanding
- Architecture
- NLP approach
- Recommendation strategy
- Reliability decisions
- Technology choices
- Trade-offs

---

## 👨‍💻 Author

**Aarya Butolia**
*B.Tech CSE — AI & ML*
GitHub: [AaryaButolia11](https://github.com/AaryaButolia11)

---

## ⭐ Submission

- **Live Application:** https://voice-shopping-assistant-hqho.onrender.com/
- **Source Code:** https://github.com/AaryaButolia11/Voice-Shopping
