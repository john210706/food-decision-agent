"""
Price Estimator Tool
Estimates ingredient costs in ₹ INR using a local price database
of common Indian grocery items, with web search fallback.
"""

import json
from langchain_core.tools import tool


# ─── Local Indian Grocery Price Database (per standard unit) ─────
# Prices are approximate averages in ₹ INR as of 2026
PRICE_DATABASE = {
    # Vegetables (per kg)
    "onion": {"price": 40, "unit": "kg"},
    "tomato": {"price": 50, "unit": "kg"},
    "potato": {"price": 35, "unit": "kg"},
    "garlic": {"price": 200, "unit": "kg"},
    "ginger": {"price": 180, "unit": "kg"},
    "green chili": {"price": 80, "unit": "kg"},
    "capsicum": {"price": 80, "unit": "kg"},
    "carrot": {"price": 50, "unit": "kg"},
    "cauliflower": {"price": 40, "unit": "piece"},
    "cabbage": {"price": 30, "unit": "piece"},
    "spinach": {"price": 30, "unit": "bunch"},
    "peas": {"price": 80, "unit": "kg"},
    "beans": {"price": 60, "unit": "kg"},
    "brinjal": {"price": 40, "unit": "kg"},
    "lady finger": {"price": 50, "unit": "kg"},
    "okra": {"price": 50, "unit": "kg"},
    "mushroom": {"price": 120, "unit": "200g pack"},
    "paneer": {"price": 350, "unit": "kg"},
    "tofu": {"price": 120, "unit": "200g pack"},
    "corn": {"price": 30, "unit": "piece"},
    "beetroot": {"price": 40, "unit": "kg"},
    "cucumber": {"price": 30, "unit": "kg"},
    "lemon": {"price": 10, "unit": "piece"},
    "coriander": {"price": 10, "unit": "bunch"},
    "mint": {"price": 10, "unit": "bunch"},
    "curry leaves": {"price": 10, "unit": "bunch"},

    # Proteins (per kg unless specified)
    "chicken": {"price": 250, "unit": "kg"},
    "chicken breast": {"price": 350, "unit": "kg"},
    "chicken thigh": {"price": 280, "unit": "kg"},
    "mutton": {"price": 700, "unit": "kg"},
    "lamb": {"price": 700, "unit": "kg"},
    "fish": {"price": 300, "unit": "kg"},
    "prawns": {"price": 500, "unit": "kg"},
    "shrimp": {"price": 500, "unit": "kg"},
    "egg": {"price": 7, "unit": "piece"},
    "eggs": {"price": 7, "unit": "piece"},

    # Grains & Staples
    "rice": {"price": 60, "unit": "kg"},
    "basmati rice": {"price": 120, "unit": "kg"},
    "wheat flour": {"price": 40, "unit": "kg"},
    "atta": {"price": 40, "unit": "kg"},
    "maida": {"price": 45, "unit": "kg"},
    "bread": {"price": 40, "unit": "pack"},
    "pasta": {"price": 80, "unit": "500g pack"},
    "noodles": {"price": 30, "unit": "pack"},
    "oats": {"price": 100, "unit": "500g pack"},
    "poha": {"price": 50, "unit": "kg"},
    "semolina": {"price": 50, "unit": "kg"},
    "suji": {"price": 50, "unit": "kg"},
    "besan": {"price": 80, "unit": "kg"},

    # Lentils & Legumes
    "toor dal": {"price": 130, "unit": "kg"},
    "moong dal": {"price": 120, "unit": "kg"},
    "chana dal": {"price": 100, "unit": "kg"},
    "masoor dal": {"price": 110, "unit": "kg"},
    "urad dal": {"price": 140, "unit": "kg"},
    "rajma": {"price": 140, "unit": "kg"},
    "chickpeas": {"price": 100, "unit": "kg"},
    "chole": {"price": 100, "unit": "kg"},
    "lentils": {"price": 120, "unit": "kg"},
    "dal": {"price": 120, "unit": "kg"},

    # Dairy
    "milk": {"price": 56, "unit": "litre"},
    "curd": {"price": 60, "unit": "kg"},
    "yogurt": {"price": 60, "unit": "kg"},
    "butter": {"price": 55, "unit": "100g"},
    "ghee": {"price": 550, "unit": "litre"},
    "cheese": {"price": 350, "unit": "kg"},
    "cream": {"price": 60, "unit": "200ml"},
    "malai": {"price": 60, "unit": "200ml"},

    # Oils & Fats
    "oil": {"price": 150, "unit": "litre"},
    "cooking oil": {"price": 150, "unit": "litre"},
    "mustard oil": {"price": 180, "unit": "litre"},
    "olive oil": {"price": 600, "unit": "litre"},
    "coconut oil": {"price": 200, "unit": "litre"},

    # Spices & Condiments
    "salt": {"price": 25, "unit": "kg"},
    "sugar": {"price": 45, "unit": "kg"},
    "turmeric": {"price": 200, "unit": "kg"},
    "red chili powder": {"price": 300, "unit": "kg"},
    "cumin": {"price": 350, "unit": "kg"},
    "coriander powder": {"price": 200, "unit": "kg"},
    "garam masala": {"price": 400, "unit": "kg"},
    "black pepper": {"price": 600, "unit": "kg"},
    "cinnamon": {"price": 500, "unit": "kg"},
    "cardamom": {"price": 2000, "unit": "kg"},
    "bay leaf": {"price": 300, "unit": "kg"},
    "soy sauce": {"price": 80, "unit": "200ml bottle"},
    "vinegar": {"price": 40, "unit": "500ml bottle"},
    "tomato ketchup": {"price": 100, "unit": "500g bottle"},
    "coconut milk": {"price": 60, "unit": "200ml can"},
}

# Typical quantities needed per serving for common ingredient types
TYPICAL_QUANTITIES = {
    "vegetables": 0.15,    # 150g per serving
    "protein": 0.15,       # 150g per serving
    "grains": 0.1,         # 100g per serving
    "lentils": 0.075,      # 75g per serving
    "dairy": 0.05,         # 50g per serving
    "oil": 0.02,           # 20ml per serving
    "spices": 0.005,       # 5g per serving
}


def _categorize_ingredient(name: str) -> str:
    """Categorize an ingredient for quantity estimation."""
    name_lower = name.lower()
    proteins = ["chicken", "mutton", "lamb", "fish", "prawns", "shrimp", "egg", "paneer", "tofu"]
    grains = ["rice", "flour", "atta", "bread", "pasta", "noodles", "oats", "poha", "semolina", "suji", "besan", "maida"]
    lentils = ["dal", "rajma", "chickpeas", "chole", "lentils"]
    dairy = ["milk", "curd", "yogurt", "butter", "ghee", "cheese", "cream", "malai"]
    oils = ["oil", "ghee"]
    spices = ["salt", "sugar", "turmeric", "chili", "cumin", "coriander", "garam masala", "pepper",
              "cinnamon", "cardamom", "bay leaf", "soy sauce", "vinegar", "ketchup"]

    for keyword in proteins:
        if keyword in name_lower:
            return "protein"
    for keyword in grains:
        if keyword in name_lower:
            return "grains"
    for keyword in lentils:
        if keyword in name_lower:
            return "lentils"
    for keyword in dairy:
        if keyword in name_lower:
            return "dairy"
    for keyword in oils:
        if keyword in name_lower:
            return "oil"
    for keyword in spices:
        if keyword in name_lower:
            return "spices"
    return "vegetables"


def _find_price(ingredient_name: str) -> dict | None:
    """Fuzzy match ingredient name against the price database."""
    name_lower = ingredient_name.lower().strip()

    # Direct match
    if name_lower in PRICE_DATABASE:
        return PRICE_DATABASE[name_lower]

    # Partial match — check if any DB key is contained in the ingredient name
    for db_key, price_info in PRICE_DATABASE.items():
        if db_key in name_lower or name_lower in db_key:
            return price_info

    return None


@tool
def estimate_meal_cost(ingredients_json: str, servings: int = 2) -> str:
    """
    Estimate the total cost of a meal based on its ingredients.
    Uses a local database of Indian grocery prices in INR (₹).

    Use this tool when:
    - The user specifies a budget and you need to check if a recipe fits
    - You want to compare costs between different recipe options
    - The user asks "how much will this cost?"

    Args:
        ingredients_json: A JSON string containing a list of ingredient names.
            Example: '["chicken", "rice", "onion", "tomato", "garam masala", "oil"]'
        servings: Number of servings to calculate cost for (default: 2).

    Returns:
        A detailed cost breakdown per ingredient plus total cost and per-serving cost.
    """
    try:
        ingredients = json.loads(ingredients_json)
    except json.JSONDecodeError:
        return "Invalid JSON format. Please provide a JSON list of ingredient names like: '[\"chicken\", \"rice\", \"onion\"]'"

    if not isinstance(ingredients, list):
        return "Please provide a list of ingredient names as a JSON array."

    results = []
    total_cost = 0.0
    not_found = []

    for ingredient in ingredients:
        price_info = _find_price(ingredient)
        if price_info:
            category = _categorize_ingredient(ingredient)
            qty_per_serving = TYPICAL_QUANTITIES.get(category, 0.1)
            total_qty = qty_per_serving * servings

            # Calculate cost based on quantity needed
            unit_price = price_info["price"]
            unit = price_info["unit"]

            # Normalize to per-kg/litre price for calculation
            if "100g" in unit:
                per_kg_price = unit_price * 10
            elif "200g" in unit or "200ml" in unit:
                per_kg_price = unit_price * 5
            elif "500g" in unit or "500ml" in unit:
                per_kg_price = unit_price * 2
            elif unit == "piece" or unit == "bunch" or unit == "pack":
                # For items sold by piece, estimate differently
                if category == "protein" and "egg" in ingredient.lower():
                    item_cost = unit_price * max(2, servings)  # 2 eggs per serving
                    results.append(f"  {ingredient}: ₹{item_cost:.0f} ({max(2, servings)} pieces × ₹{unit_price}/piece)")
                    total_cost += item_cost
                    continue
                else:
                    item_cost = unit_price
                    results.append(f"  {ingredient}: ₹{item_cost:.0f} ({unit})")
                    total_cost += item_cost
                    continue
            else:
                per_kg_price = unit_price

            item_cost = per_kg_price * total_qty
            results.append(
                f"  {ingredient}: ₹{item_cost:.0f} "
                f"(~{total_qty*1000:.0f}g for {servings} servings, "
                f"₹{unit_price}/{unit})"
            )
            total_cost += item_cost
        else:
            not_found.append(ingredient)

    # Build output
    output_lines = [f"💰 Cost Estimate for {servings} serving(s):\n"]
    output_lines.append("Ingredient Breakdown:")
    output_lines.extend(results)

    if not_found:
        output_lines.append(f"\n⚠️ Price not found for: {', '.join(not_found)}")
        output_lines.append("  → Use web_search to find current prices for these items.")

    output_lines.append(f"\n{'='*40}")
    output_lines.append(f"  TOTAL ESTIMATED COST: ₹{total_cost:.0f}")
    output_lines.append(f"  PER SERVING: ₹{total_cost/max(servings, 1):.0f}")
    output_lines.append(f"{'='*40}")

    return "\n".join(output_lines)
