"""
Static domain data for the shopping assistant.

Sources are public/common-knowledge grocery data:
- Category mapping is a hand-built keyword lexicon.
- Seasonal produce follows USDA "Seasonal Produce Guide" (Northern Hemisphere).
- Substitutes follow common cooking-swap references.
- The product catalog is a small representative sample with typical US retail
  prices, used to power voice search / price filtering.

Everything here is intentionally dependency-free so it can be imported anywhere
and used as a deterministic fallback when the LLM is unavailable.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Categories                                                                   #
# --------------------------------------------------------------------------- #
# Order matters: the first category whose keywords match wins.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "produce": [
        "apple", "apples", "banana", "bananas", "orange", "oranges", "lemon",
        "lime", "grape", "grapes", "strawberry", "strawberries", "blueberry",
        "blueberries", "melon", "watermelon", "mango", "avocado", "avocados",
        "tomato", "tomatoes", "potato", "potatoes", "onion", "onions", "garlic",
        "carrot", "carrots", "lettuce", "spinach", "kale", "broccoli", "pepper",
        "peppers", "cucumber", "celery", "mushroom", "mushrooms", "zucchini",
        "corn", "peach", "peaches", "pear", "pears", "cherry", "cherries",
        "pineapple", "berries", "greens", "herbs", "cilantro", "basil", "ginger",
    ],
    "dairy": [
        "milk", "cheese", "butter", "yogurt", "yoghurt", "cream", "egg", "eggs",
        "sour cream", "cottage cheese", "mozzarella", "cheddar", "parmesan",
        "half and half", "whipped cream", "margarine",
    ],
    "meat & seafood": [
        "chicken", "beef", "pork", "bacon", "sausage", "turkey", "ham", "steak",
        "fish", "salmon", "tuna", "shrimp", "cod", "lamb", "mince", "ground beef",
        "meat", "seafood",
    ],
    "bakery": [
        "bread", "bagel", "bagels", "bun", "buns", "roll", "rolls", "croissant",
        "muffin", "muffins", "tortilla", "tortillas", "cake", "pastry", "baguette",
        "pita", "naan",
    ],
    "pantry": [
        "rice", "pasta", "flour", "sugar", "salt", "oil", "olive oil", "vinegar",
        "cereal", "oats", "oatmeal", "beans", "lentils", "canned", "soup", "sauce",
        "ketchup", "mustard", "mayo", "mayonnaise", "honey", "peanut butter", "jam",
        "spice", "spices", "stock", "broth", "noodles", "quinoa", "coffee", "tea",
    ],
    "frozen": [
        "ice cream", "frozen", "pizza", "fries", "frozen vegetables", "popsicle",
        "frozen fruit", "waffles",
    ],
    "beverages": [
        "water", "juice", "soda", "cola", "sparkling water", "lemonade", "beer",
        "wine", "kombucha", "energy drink", "smoothie", "drink", "drinks",
    ],
    "snacks": [
        "chips", "crackers", "cookies", "candy", "chocolate", "popcorn", "pretzels",
        "nuts", "granola bar", "snack", "snacks", "trail mix",
    ],
    "household": [
        "paper towel", "paper towels", "toilet paper", "napkins", "trash bags",
        "detergent", "dish soap", "sponge", "foil", "cling film", "batteries",
        "light bulb", "bleach",
    ],
    "personal care": [
        "toothpaste", "toothbrush", "shampoo", "conditioner", "soap", "deodorant",
        "razor", "razors", "lotion", "sunscreen", "floss", "mouthwash", "tissues",
    ],
    "baby": ["diapers", "wipes", "formula", "baby food"],
    "pet": ["dog food", "cat food", "cat litter", "pet food", "treats"],
}

DEFAULT_CATEGORY = "other"


def categorize(item_name: str) -> str:
    """Return the best-guess category for an item name using keyword lookup."""
    name = (item_name or "").strip().lower()
    if not name:
        return DEFAULT_CATEGORY
    # Prefer the longest keyword match so "sour cream" beats "cream", etc.
    best_category = DEFAULT_CATEGORY
    best_len = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name and len(kw) > best_len:
                best_category = category
                best_len = len(kw)
    return best_category


# --------------------------------------------------------------------------- #
# Seasonal produce (Northern Hemisphere, by month number 1-12)                 #
# --------------------------------------------------------------------------- #
SEASONAL_BY_MONTH: dict[int, list[str]] = {
    1: ["oranges", "grapefruit", "kale", "leeks", "pomegranate"],
    2: ["oranges", "lemons", "cabbage", "kiwi", "brussels sprouts"],
    3: ["asparagus", "artichokes", "broccoli", "lettuce", "peas"],
    4: ["asparagus", "strawberries", "spinach", "radishes", "rhubarb"],
    5: ["strawberries", "cherries", "apricots", "zucchini", "peas"],
    6: ["cherries", "blueberries", "peaches", "corn", "tomatoes"],
    7: ["watermelon", "peaches", "blueberries", "corn", "bell peppers"],
    8: ["tomatoes", "corn", "peaches", "plums", "melon"],
    9: ["apples", "grapes", "figs", "pears", "pumpkin"],
    10: ["apples", "pumpkin", "squash", "sweet potatoes", "cranberries"],
    11: ["pumpkin", "sweet potatoes", "cranberries", "pears", "brussels sprouts"],
    12: ["oranges", "pomegranate", "squash", "potatoes", "citrus"],
}


def seasonal_items(month: int) -> list[str]:
    return SEASONAL_BY_MONTH.get(month, [])


# --------------------------------------------------------------------------- #
# Substitutes (common cooking swaps)                                           #
# --------------------------------------------------------------------------- #
SUBSTITUTES: dict[str, list[str]] = {
    "milk": ["almond milk", "oat milk", "soy milk"],
    "butter": ["margarine", "olive oil", "coconut oil"],
    "sugar": ["honey", "maple syrup", "stevia"],
    "eggs": ["flax eggs", "applesauce", "banana"],
    "flour": ["almond flour", "oat flour", "gluten-free flour"],
    "rice": ["quinoa", "couscous", "cauliflower rice"],
    "pasta": ["zucchini noodles", "rice noodles", "chickpea pasta"],
    "cream": ["coconut cream", "greek yogurt", "cashew cream"],
    "sour cream": ["greek yogurt", "creme fraiche"],
    "mayonnaise": ["greek yogurt", "avocado", "hummus"],
    "beef": ["ground turkey", "lentils", "mushrooms"],
    "chicken": ["tofu", "tempeh", "chickpeas"],
    "cheese": ["nutritional yeast", "vegan cheese"],
    "yogurt": ["coconut yogurt", "soy yogurt"],
    "bread": ["lettuce wraps", "gluten-free bread", "pita"],
    "soy sauce": ["tamari", "coconut aminos"],
}


def substitutes_for(item_name: str) -> list[str]:
    name = (item_name or "").strip().lower()
    if name in SUBSTITUTES:
        return SUBSTITUTES[name]
    # fall back to matching the head noun (e.g. "whole milk" -> "milk")
    for key, subs in SUBSTITUTES.items():
        if key in name:
            return subs
    return []


# --------------------------------------------------------------------------- #
# Searchable product catalog                                                   #
# Representative sample with typical US retail prices (USD).                    #
# --------------------------------------------------------------------------- #
PRODUCTS: list[dict] = [
    # produce
    {"name": "Organic Fuji Apples", "brand": "Nature's Pick", "category": "produce", "size": "3 lb bag", "price": 4.99, "tags": ["organic", "apples", "fruit"]},
    {"name": "Gala Apples", "brand": "Store Brand", "category": "produce", "size": "per lb", "price": 1.49, "tags": ["apples", "fruit"]},
    {"name": "Organic Bananas", "brand": "Chiquita", "category": "produce", "size": "per lb", "price": 0.79, "tags": ["organic", "bananas", "fruit"]},
    {"name": "Organic Baby Spinach", "brand": "Earthbound Farm", "category": "produce", "size": "5 oz", "price": 3.49, "tags": ["organic", "spinach", "greens"]},
    {"name": "Roma Tomatoes", "brand": "Store Brand", "category": "produce", "size": "per lb", "price": 1.99, "tags": ["tomatoes", "vegetable"]},
    {"name": "Organic Avocados", "brand": "Hass", "category": "produce", "size": "4 count", "price": 5.99, "tags": ["organic", "avocado", "fruit"]},
    # dairy
    {"name": "Whole Milk", "brand": "Horizon Organic", "category": "dairy", "size": "1 gallon", "price": 6.49, "tags": ["organic", "milk"]},
    {"name": "2% Reduced Fat Milk", "brand": "Store Brand", "category": "dairy", "size": "1 gallon", "price": 3.79, "tags": ["milk"]},
    {"name": "Almond Milk Unsweetened", "brand": "Almond Breeze", "category": "dairy", "size": "64 oz", "price": 3.99, "tags": ["almond milk", "dairy-free", "milk"]},
    {"name": "Oat Milk", "brand": "Oatly", "category": "dairy", "size": "64 oz", "price": 4.99, "tags": ["oat milk", "dairy-free", "milk"]},
    {"name": "Large Eggs", "brand": "Store Brand", "category": "dairy", "size": "12 count", "price": 3.29, "tags": ["eggs"]},
    {"name": "Organic Cage-Free Eggs", "brand": "Vital Farms", "category": "dairy", "size": "12 count", "price": 7.49, "tags": ["organic", "eggs"]},
    {"name": "Sharp Cheddar Cheese", "brand": "Tillamook", "category": "dairy", "size": "8 oz", "price": 4.49, "tags": ["cheese", "cheddar"]},
    {"name": "Greek Yogurt Plain", "brand": "Chobani", "category": "dairy", "size": "32 oz", "price": 5.29, "tags": ["yogurt", "greek"]},
    # bakery
    {"name": "Whole Wheat Bread", "brand": "Dave's Killer Bread", "category": "bakery", "size": "27 oz", "price": 5.49, "tags": ["bread", "whole wheat"]},
    {"name": "White Sandwich Bread", "brand": "Wonder", "category": "bakery", "size": "20 oz", "price": 2.79, "tags": ["bread", "white"]},
    {"name": "Plain Bagels", "brand": "Thomas'", "category": "bakery", "size": "6 count", "price": 3.99, "tags": ["bagels"]},
    # meat & seafood
    {"name": "Boneless Chicken Breast", "brand": "Store Brand", "category": "meat & seafood", "size": "per lb", "price": 4.99, "tags": ["chicken"]},
    {"name": "Organic Ground Beef 85/15", "brand": "Store Brand", "category": "meat & seafood", "size": "per lb", "price": 7.99, "tags": ["organic", "beef", "ground beef"]},
    {"name": "Atlantic Salmon Fillet", "brand": "Store Brand", "category": "meat & seafood", "size": "per lb", "price": 11.99, "tags": ["fish", "salmon"]},
    # pantry
    {"name": "Extra Virgin Olive Oil", "brand": "California Olive Ranch", "category": "pantry", "size": "16.9 oz", "price": 9.99, "tags": ["olive oil", "oil"]},
    {"name": "Jasmine Rice", "brand": "Store Brand", "category": "pantry", "size": "5 lb", "price": 6.49, "tags": ["rice"]},
    {"name": "Spaghetti Pasta", "brand": "Barilla", "category": "pantry", "size": "16 oz", "price": 1.79, "tags": ["pasta"]},
    {"name": "Creamy Peanut Butter", "brand": "Jif", "category": "pantry", "size": "16 oz", "price": 3.49, "tags": ["peanut butter"]},
    {"name": "Rolled Oats", "brand": "Quaker", "category": "pantry", "size": "42 oz", "price": 4.29, "tags": ["oats", "oatmeal"]},
    {"name": "Ground Coffee Medium Roast", "brand": "Folgers", "category": "pantry", "size": "25.9 oz", "price": 8.99, "tags": ["coffee"]},
    # beverages
    {"name": "Spring Water 24-Pack", "brand": "Poland Spring", "category": "beverages", "size": "24 x 16.9 oz", "price": 4.99, "tags": ["water"]},
    {"name": "Sparkling Water Lime", "brand": "LaCroix", "category": "beverages", "size": "8-pack", "price": 4.49, "tags": ["sparkling water", "water"]},
    {"name": "Orange Juice No Pulp", "brand": "Tropicana", "category": "beverages", "size": "52 oz", "price": 4.29, "tags": ["juice", "orange juice"]},
    # snacks
    {"name": "Tortilla Chips", "brand": "Tostitos", "category": "snacks", "size": "13 oz", "price": 4.29, "tags": ["chips"]},
    {"name": "Dark Chocolate Bar", "brand": "Lindt", "category": "snacks", "size": "3.5 oz", "price": 3.49, "tags": ["chocolate", "candy"]},
    # personal care
    {"name": "Cavity Protection Toothpaste", "brand": "Colgate", "category": "personal care", "size": "6 oz", "price": 3.49, "tags": ["toothpaste"]},
    {"name": "Whitening Toothpaste", "brand": "Crest", "category": "personal care", "size": "4.1 oz", "price": 4.79, "tags": ["toothpaste"]},
    {"name": "2-in-1 Shampoo", "brand": "Head & Shoulders", "category": "personal care", "size": "13.5 oz", "price": 6.49, "tags": ["shampoo"]},
    # household
    {"name": "Paper Towels 6 Rolls", "brand": "Bounty", "category": "household", "size": "6 rolls", "price": 12.99, "tags": ["paper towels"]},
    {"name": "Dish Soap", "brand": "Dawn", "category": "household", "size": "19.4 oz", "price": 3.99, "tags": ["dish soap"]},
]


def search_products(
    query: str = "",
    brand: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    tags: list[str] | None = None,
    limit: int = 12,
) -> list[dict]:
    """Filter the product catalog by free-text query, brand, price and tags."""
    q = (query or "").strip().lower()
    tag_set = {t.strip().lower() for t in (tags or []) if t.strip()}
    results: list[dict] = []

    for product in PRODUCTS:
        haystack = f"{product['name']} {product['brand']} {' '.join(product['tags'])}".lower()

        if q and not all(word in haystack for word in q.split()):
            continue
        if brand and brand.strip().lower() not in product["brand"].lower():
            continue
        if tag_set and not tag_set.issubset({t.lower() for t in product["tags"]}):
            continue
        if price_min is not None and product["price"] < price_min:
            continue
        if price_max is not None and product["price"] > price_max:
            continue
        results.append(product)

    results.sort(key=lambda p: p["price"])
    return results[:limit]
