"""
Voice Command Shopping Assistant — FastAPI backend.

Endpoints
---------
# Shopping list (no auth required — single shared list)
GET    /api/health              service + LLM status
GET    /api/items               current shopping list
POST   /api/items               add an item directly
PATCH  /api/items/{id}          update quantity / name / checked
DELETE /api/items/{id}          remove an item
DELETE /api/items               clear the list
POST   /api/command             parse a voice/typed transcript and act on it
GET    /api/suggestions         smart suggestions (history / seasonal / substitute)
GET    /api/search              voice-activated product search

# Optional extras (auth-gated) — not needed for the core voice experience
POST   /api/auth/register       register a new user
POST   /api/auth/login          login and get a JWT token
GET    /api/auth/me             current user
POST   /api/checkout            turn the list into an order
GET    /api/orders              a user's orders
GET    /api/orders/{id}         order details
GET    /api/orders/{id}/invoice download the invoice PDF
"""

from __future__ import annotations

import os
from typing import Optional

try:  # Load a local .env if present (no-op in production if the file is absent).
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import models
from auth import create_token_response, hash_password, verify_access_token, verify_password
from catalog import categorize, search_products
from database import Base, engine, get_db
from invoices import generate_invoice_pdf
from nlp import GROQ_API_KEY, parse_command
from schemas import (
    CheckoutRequest,
    CommandRequest,
    CommandResult,
    ItemCreate,
    ItemOut,
    ItemUpdate,
    OrderOut,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)
from suggestions import build_suggestions, record_purchase

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Voice Command Shopping Assistant", version="2.0.0")

# CORS — the frontend may be served from a different origin (e.g. Vercel).
origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Auth helper                                                                  #
# --------------------------------------------------------------------------- #
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> models.User:
    """Extract and validate the current user from the Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    payload = verify_access_token(parts[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(models.User).filter(models.User.id == payload.get("user_id")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


# --------------------------------------------------------------------------- #
# Health                                                                       #
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return {"status": "ok", "llm_enabled": bool(GROQ_API_KEY)}


# --------------------------------------------------------------------------- #
# List CRUD                                                                    #
# --------------------------------------------------------------------------- #
@app.get("/api/items", response_model=list[ItemOut])
def list_items(db: Session = Depends(get_db)):
    return db.query(models.Item).order_by(models.Item.created_at.desc()).all()


@app.post("/api/items", response_model=ItemOut, status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    return _add_item(db, payload.name, payload.quantity, payload.unit, payload.category, payload.price)


@app.patch("/api/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)):
    item = db.get(models.Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    data = payload.model_dump(exclude_unset=True)
    if data.get("name"):
        item.name = data["name"].strip()
        item.category = categorize(item.name)
    for field in ("quantity", "unit", "checked", "price"):
        if field in data and data[field] is not None:
            setattr(item, field, data[field])
    if data.get("category"):
        item.category = data["category"]

    db.commit()
    db.refresh(item)
    return item


@app.delete("/api/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()


@app.delete("/api/items", status_code=204)
def clear_list(db: Session = Depends(get_db)):
    db.query(models.Item).delete()
    db.commit()


# --------------------------------------------------------------------------- #
# Voice / typed command                                                        #
# --------------------------------------------------------------------------- #
@app.post("/api/command", response_model=CommandResult)
def run_command(payload: CommandRequest, db: Session = Depends(get_db)):
    parsed = parse_command(payload.transcript, payload.language)
    intent = parsed["intent"]
    used_llm = parsed.get("_used_llm", False)
    changed: list[models.Item] = []
    search_results: list[dict] = []
    message = ""

    if intent == "add":
        for spec in parsed["items"]:
            changed.append(_add_item(db, spec["name"], spec["quantity"], spec["unit"], spec["category"], None))
        message = _summarise("Added", changed) or "I couldn't catch an item to add."

    elif intent == "remove":
        for spec in parsed["items"]:
            removed = _remove_by_name(db, spec["name"])
            if removed:
                changed.append(removed)
        message = _summarise("Removed", changed) or "I couldn't find that on your list."

    elif intent == "update":
        for spec in parsed["items"]:
            updated = _update_by_name(db, spec["name"], spec["quantity"], spec["unit"])
            if updated:
                changed.append(updated)
        message = _summarise("Updated", changed) or "I couldn't find that to update."

    elif intent == "check":
        for spec in parsed["items"]:
            item = _find_by_name(db, spec["name"])
            if item:
                item.checked = True
                db.commit()
                db.refresh(item)
                changed.append(item)
        message = _summarise("Checked off", changed) or "I couldn't find that to check off."

    elif intent == "clear":
        count = db.query(models.Item).count()
        db.query(models.Item).delete()
        db.commit()
        message = f"Cleared {count} item{'s' if count != 1 else ''} from your list."

    elif intent == "search":
        s = parsed["search"]
        search_results = search_products(
            query=s.get("query", ""),
            brand=s.get("brand"),
            price_min=s.get("price_min"),
            price_max=s.get("price_max"),
            tags=s.get("tags", []),
        )
        message = (
            f"Found {len(search_results)} match{'es' if len(search_results) != 1 else ''}."
            if search_results
            else "No products matched that search."
        )

    else:
        message = "I didn't quite get that. Try 'add milk' or 'find organic apples under $5'."

    return CommandResult(
        intent=intent,
        message=message,
        items_changed=[ItemOut.model_validate(i) for i in changed],
        search_results=search_results,
        suggestions=build_suggestions(db),
        transcript=payload.transcript,
        used_llm=used_llm,
    )


# --------------------------------------------------------------------------- #
# Suggestions + search                                                         #
# --------------------------------------------------------------------------- #
@app.get("/api/suggestions")
def get_suggestions(db: Session = Depends(get_db)):
    return build_suggestions(db)


@app.get("/api/search")
def get_search(
    query: str = "",
    brand: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    tags: list[str] = Query(default=[]),
):
    return search_products(query=query, brand=brand, price_min=price_min, price_max=price_max, tags=tags)


# --------------------------------------------------------------------------- #
# Authentication (optional extras)                                             #
# --------------------------------------------------------------------------- #
@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_token_response(user)


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")
    return create_token_response(user)


@app.get("/api/auth/me", response_model=UserOut)
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


# --------------------------------------------------------------------------- #
# Checkout & orders (optional extras)                                          #
# --------------------------------------------------------------------------- #
@app.post("/api/checkout", response_model=OrderOut)
def checkout(
    payload: CheckoutRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cannot checkout with an empty cart")

    total_amount = sum(item.price * item.quantity for item in payload.items)
    order = models.Order(user_id=current_user.id, total_amount=total_amount, status="completed")

    for item_data in payload.items:
        order.items.append(
            models.OrderItem(
                name=item_data.name,
                quantity=item_data.quantity,
                unit=item_data.unit,
                category=item_data.category or categorize(item_data.name),
                price=item_data.price,
                subtotal=item_data.price * item_data.quantity,
            )
        )

    db.add(order)
    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(order)


@app.post("/api/list/checkout", response_model=OrderOut)
def checkout_current_list(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Turn the current voice-built list into a priced order + invoice.

    Voice-added items don't carry a price, so we look each one up in the
    product catalog (falling back to a small default) to build a real invoice.
    """
    items = db.query(models.Item).order_by(models.Item.created_at.desc()).all()
    if not items:
        raise HTTPException(status_code=400, detail="Your list is empty")

    order = models.Order(user_id=current_user.id, total_amount=0.0, status="completed")
    total = 0.0
    for it in items:
        price = it.price
        if price is None:
            match = search_products(query=it.name, limit=1)
            price = match[0]["price"] if match else 3.99
        qty = it.quantity or 1
        subtotal = round(price * qty, 2)
        total += subtotal
        order.items.append(
            models.OrderItem(
                name=it.name,
                quantity=qty,
                unit=it.unit,
                category=it.category,
                price=price,
                subtotal=subtotal,
            )
        )

    order.total_amount = round(total, 2)
    db.add(order)
    db.commit()
    db.refresh(order)
    return OrderOut.model_validate(order)


@app.get("/api/orders", response_model=list[OrderOut])
def get_orders(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = (
        db.query(models.Order)
        .filter(models.Order.user_id == current_user.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )
    return [OrderOut.model_validate(o) for o in orders]


@app.get("/api/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = (
        db.query(models.Order)
        .filter(models.Order.id == order_id, models.Order.user_id == current_user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderOut.model_validate(order)


@app.get("/api/orders/{order_id}/invoice")
def download_invoice(order_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = (
        db.query(models.Order)
        .filter(models.Order.id == order_id, models.Order.user_id == current_user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    pdf_buffer = generate_invoice_pdf(order)
    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice-{order_id:06d}.pdf"},
    )


# --------------------------------------------------------------------------- #
# Internal helpers                                                             #
# --------------------------------------------------------------------------- #
def _add_item(db, name, quantity, unit, category, price) -> models.Item:
    name = name.strip()
    category = category or categorize(name)
    existing = _find_by_name(db, name)
    if existing:
        # Merge duplicates by bumping the quantity instead of adding a new row.
        existing.quantity = (existing.quantity or 1) + (quantity or 1)
        db.commit()
        db.refresh(existing)
        record_purchase(db, name, category)
        return existing

    item = models.Item(name=name, quantity=quantity or 1, unit=unit, category=category, price=price)
    db.add(item)
    db.commit()
    db.refresh(item)
    record_purchase(db, name, category)
    return item


def _find_by_name(db, name: str) -> models.Item | None:
    target = name.strip().lower()
    for item in db.query(models.Item).all():
        n = item.name.lower()
        if n == target or target in n or n in target:
            return item
    return None


def _remove_by_name(db, name: str) -> models.Item | None:
    item = _find_by_name(db, name)
    if not item:
        return None
    snapshot = models.Item(
        id=item.id, name=item.name, quantity=item.quantity,
        unit=item.unit, category=item.category, checked=item.checked,
        created_at=item.created_at,
    )
    db.delete(item)
    db.commit()
    return snapshot


def _update_by_name(db, name, quantity, unit) -> models.Item | None:
    item = _find_by_name(db, name)
    if not item:
        return None
    if quantity:
        item.quantity = quantity
    if unit:
        item.unit = unit
    db.commit()
    db.refresh(item)
    return item


def _summarise(verb: str, items: list[models.Item]) -> str:
    if not items:
        return ""
    parts = []
    for i in items:
        qty = int(i.quantity) if float(i.quantity).is_integer() else i.quantity
        label = f"{qty} {i.unit} {i.name}" if i.unit else (f"{qty} {i.name}" if qty != 1 else i.name)
        parts.append(label)
    return f"{verb} {', '.join(parts)}."


# --------------------------------------------------------------------------- #
# Serve the frontend as static files (single-service deploy). Must be LAST so  #
# it doesn't shadow the /api routes above.                                     #
# --------------------------------------------------------------------------- #
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
