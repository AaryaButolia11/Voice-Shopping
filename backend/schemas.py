"""Pydantic request/response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ===== Authentication =====


class UserRegister(BaseModel):
    """User registration request."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class UserOut(BaseModel):
    """User response (public data)."""

    id: int
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ===== Shopping =====


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    quantity: float = 1
    unit: str | None = None
    category: str | None = None
    price: float | None = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    quantity: float | None = None
    unit: str | None = None
    category: str | None = None
    price: float | None = None
    checked: bool | None = None


class ItemOut(ItemBase):
    id: int
    category: str
    checked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CommandRequest(BaseModel):
    """Raw voice transcript from the client plus the recognised language."""

    transcript: str = Field(..., min_length=1)
    language: str = "en"


class ParsedItem(BaseModel):
    name: str
    quantity: float = 1
    unit: str | None = None
    category: str | None = None


class SearchQuery(BaseModel):
    query: str = ""
    brand: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    tags: list[str] = []


class CommandResult(BaseModel):
    """What the client renders after a voice command is processed."""

    intent: str
    message: str
    items_changed: list[ItemOut] = []
    search_results: list[dict] = []
    suggestions: list[dict] = []
    transcript: str
    used_llm: bool = False


class SuggestionOut(BaseModel):
    name: str
    reason: str
    type: str  # "history" | "seasonal" | "substitute"
    category: str | None = None


# ===== Checkout =====


class OrderItemCreate(BaseModel):
    """Item to add to order."""

    name: str = Field(..., min_length=1, max_length=120)
    quantity: float
    unit: str | None = None
    category: str | None = None
    price: float


class OrderItemOut(BaseModel):
    """Order item response."""

    id: int
    name: str
    quantity: float
    unit: str | None
    category: str
    price: float
    subtotal: float

    class Config:
        from_attributes = True


class CheckoutRequest(BaseModel):
    """Checkout request with items."""

    items: list[OrderItemCreate]


class OrderOut(BaseModel):
    """Order response."""

    id: int
    user_id: int
    total_amount: float
    status: str
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut] = []

    class Config:
        from_attributes = True
