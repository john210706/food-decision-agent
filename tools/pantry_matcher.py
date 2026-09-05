"""
Pantry Matcher Tool
Compares a recipe's required ingredients against the user's available ingredients.
Returns match percentage, matched items, and missing items.
"""

import json
from langchain_core.tools import tool


# Common ingredient aliases to improve matching accuracy
ALIASES = {
    "coriander leaves": ["coriander", "cilantro", "dhania"],
    "green chili": ["green chilli", "hari mirch", "chili"],
    "red chili powder": ["chili powder", "lal mirch", "red chilli"],
    "garam masala": ["masala"],
    "cooking oil": ["oil", "vegetable oil", "sunflower oil"],
    "curd": ["yogurt", "dahi", "yoghurt"],
    "capsicum": ["bell pepper", "green pepper"],
    "brinjal": ["eggplant", "aubergine", "baingan"],
    "lady finger": ["okra", "bhindi"],
    "chickpeas": ["chole", "chana", "garbanzo"],
    "wheat flour": ["atta", "flour", "whole wheat flour"],
    "semolina": ["suji", "sooji", "rava"],
    "basmati rice": ["rice", "chawal"],
    "paneer": ["cottage cheese"],
    "prawns": ["shrimp"],
    "mutton": ["lamb", "goat meat"],
    "tomato ketchup": ["ketchup", "tomato sauce"],
}

# Staple ingredients that most Indian kitchens typically have
ASSUMED_STAPLES = [
    "salt", "water", "oil", "cooking oil", "sugar",
    "turmeric", "red chili powder", "cumin",
]


def _normalize(name: str) -> str:
    """Normalize ingredient name for comparison."""
    return name.lower().strip().rstrip("s")  # basic singular


def _is_match(recipe_ingredient: str, pantry_item: str) -> bool:
    """Check if a pantry item matches a recipe ingredient (fuzzy)."""
    r = _normalize(recipe_ingredient)
    p = _normalize(pantry_item)

    # Direct or substring match
    if r == p or r in p or p in r:
        return True

    # Check aliases
    for canonical, aliases in ALIASES.items():
        canon_norm = _normalize(canonical)
        all_forms = [canon_norm] + [_normalize(a) for a in aliases]
        if any(form in r or r in form for form in all_forms):
            if any(form in p or p in form for form in all_forms):
                return True

    return False


@tool
def match_pantry_ingredients(recipe_ingredients_json: str, pantry_items_json: str) -> str:
    """
    Compare a recipe's required ingredients against the user's available pantry items.
    Returns which ingredients match, which are missing, and the match percentage.

    Use this tool when:
    - The user lists their available ingredients and asks what they can make
    - You need to check if a recipe is feasible with what the user has
    - You want to determine what the user needs to buy

    Args:
        recipe_ingredients_json: JSON list of ingredients required by the recipe.
            Example: '["chicken", "rice", "onion", "tomato", "ginger", "garlic", "garam masala", "oil", "salt"]'
        pantry_items_json: JSON list of ingredients the user currently has.
            Example: '["chicken", "rice", "onion", "oil"]'

    Returns:
        A detailed matching report with:
        - Matched ingredients (what the user already has) ✅
        - Missing ingredients (what needs to be bought) 🛒
        - Staple items assumed available 🏠
        - Match percentage
    """
    try:
        recipe_ingredients = json.loads(recipe_ingredients_json)
        pantry_items = json.loads(pantry_items_json)
    except json.JSONDecodeError:
        return "Invalid JSON. Provide two JSON lists of ingredient names."

    matched = []
    missing = []
    staples_assumed = []

    for ingredient in recipe_ingredients:
        # Check if it's in the pantry
        found_in_pantry = any(_is_match(ingredient, p) for p in pantry_items)

        if found_in_pantry:
            matched.append(ingredient)
        elif any(_is_match(ingredient, s) for s in ASSUMED_STAPLES):
            staples_assumed.append(ingredient)
        else:
            missing.append(ingredient)

    total = len(recipe_ingredients)
    available = len(matched) + len(staples_assumed)
    match_pct = (available / total * 100) if total > 0 else 0

    # Build output
    lines = [f"🔍 Pantry Match Report:\n"]

    if matched:
        lines.append(f"  ✅ You have ({len(matched)}):")
        for item in matched:
            lines.append(f"     • {item}")

    if staples_assumed:
        lines.append(f"\n  🏠 Assumed staples ({len(staples_assumed)}):")
        for item in staples_assumed:
            lines.append(f"     • {item}")

    if missing:
        lines.append(f"\n  🛒 Need to buy ({len(missing)}):")
        for item in missing:
            lines.append(f"     • {item}")

    lines.append(f"\n{'='*40}")
    lines.append(f"  Match: {match_pct:.0f}% ({available}/{total} ingredients available)")

    if match_pct == 100:
        lines.append("  🎉 You have everything needed!")
    elif match_pct >= 70:
        lines.append("  👍 Good match! Only a few items to pick up.")
    elif match_pct >= 40:
        lines.append("  🤔 Partial match. Several items needed.")
    else:
        lines.append("  ⚠️ Low match. Consider a different recipe.")
    lines.append(f"{'='*40}")

    return "\n".join(lines)
