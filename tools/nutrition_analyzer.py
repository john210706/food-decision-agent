"""
Nutrition Analyzer Tool
Analyzes nutritional content (calories, protein, carbs, fat) of ingredients/meals.
Uses a local database of common Indian food items.
"""

import json
from langchain_core.tools import tool


# ─── Nutrition Database (per 100g unless specified) ─────────
# Values are approximate for common Indian food items
NUTRITION_DB = {
    # Proteins
    "chicken": {"calories": 239, "protein": 27, "carbs": 0, "fat": 14, "fiber": 0},
    "chicken breast": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "fiber": 0},
    "chicken thigh": {"calories": 209, "protein": 26, "carbs": 0, "fat": 11, "fiber": 0},
    "mutton": {"calories": 294, "protein": 25, "carbs": 0, "fat": 21, "fiber": 0},
    "lamb": {"calories": 294, "protein": 25, "carbs": 0, "fat": 21, "fiber": 0},
    "fish": {"calories": 206, "protein": 22, "carbs": 0, "fat": 12, "fiber": 0},
    "prawns": {"calories": 99, "protein": 24, "carbs": 0.2, "fat": 0.3, "fiber": 0},
    "shrimp": {"calories": 99, "protein": 24, "carbs": 0.2, "fat": 0.3, "fiber": 0},
    "egg": {"calories": 155, "protein": 13, "carbs": 1.1, "fat": 11, "fiber": 0},
    "eggs": {"calories": 155, "protein": 13, "carbs": 1.1, "fat": 11, "fiber": 0},
    "paneer": {"calories": 265, "protein": 18, "carbs": 1.2, "fat": 21, "fiber": 0},
    "tofu": {"calories": 76, "protein": 8, "carbs": 1.9, "fat": 4.8, "fiber": 0.3},

    # Grains & Staples
    "rice": {"calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3, "fiber": 0.4},
    "basmati rice": {"calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3, "fiber": 0.4},
    "wheat flour": {"calories": 340, "protein": 13, "carbs": 72, "fat": 2.5, "fiber": 11},
    "atta": {"calories": 340, "protein": 13, "carbs": 72, "fat": 2.5, "fiber": 11},
    "bread": {"calories": 265, "protein": 9, "carbs": 49, "fat": 3.2, "fiber": 2.7},
    "pasta": {"calories": 131, "protein": 5, "carbs": 25, "fat": 1.1, "fiber": 1.8},
    "noodles": {"calories": 138, "protein": 4.5, "carbs": 25, "fat": 2, "fiber": 1},
    "oats": {"calories": 389, "protein": 17, "carbs": 66, "fat": 7, "fiber": 11},
    "poha": {"calories": 110, "protein": 2.5, "carbs": 23, "fat": 0.6, "fiber": 0.5},

    # Lentils & Legumes
    "toor dal": {"calories": 343, "protein": 22, "carbs": 63, "fat": 1.5, "fiber": 15},
    "moong dal": {"calories": 347, "protein": 24, "carbs": 60, "fat": 1.2, "fiber": 16},
    "chana dal": {"calories": 364, "protein": 22, "carbs": 58, "fat": 5.3, "fiber": 18},
    "masoor dal": {"calories": 352, "protein": 25, "carbs": 60, "fat": 1.1, "fiber": 11},
    "rajma": {"calories": 333, "protein": 23, "carbs": 60, "fat": 0.8, "fiber": 15},
    "chickpeas": {"calories": 364, "protein": 19, "carbs": 61, "fat": 6, "fiber": 17},
    "chole": {"calories": 364, "protein": 19, "carbs": 61, "fat": 6, "fiber": 17},
    "dal": {"calories": 345, "protein": 23, "carbs": 60, "fat": 1.5, "fiber": 15},
    "lentils": {"calories": 345, "protein": 23, "carbs": 60, "fat": 1.5, "fiber": 15},

    # Vegetables
    "onion": {"calories": 40, "protein": 1.1, "carbs": 9.3, "fat": 0.1, "fiber": 1.7},
    "tomato": {"calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2, "fiber": 1.2},
    "potato": {"calories": 77, "protein": 2, "carbs": 17, "fat": 0.1, "fiber": 2.2},
    "capsicum": {"calories": 31, "protein": 1, "carbs": 6, "fat": 0.3, "fiber": 2.1},
    "carrot": {"calories": 41, "protein": 0.9, "carbs": 10, "fat": 0.2, "fiber": 2.8},
    "cauliflower": {"calories": 25, "protein": 1.9, "carbs": 5, "fat": 0.3, "fiber": 2},
    "spinach": {"calories": 23, "protein": 2.9, "carbs": 3.6, "fat": 0.4, "fiber": 2.2},
    "peas": {"calories": 81, "protein": 5.4, "carbs": 14, "fat": 0.4, "fiber": 5.7},
    "brinjal": {"calories": 25, "protein": 1, "carbs": 6, "fat": 0.2, "fiber": 3},
    "mushroom": {"calories": 22, "protein": 3.1, "carbs": 3.3, "fat": 0.3, "fiber": 1},
    "corn": {"calories": 86, "protein": 3.3, "carbs": 19, "fat": 1.4, "fiber": 2.7},
    "cabbage": {"calories": 25, "protein": 1.3, "carbs": 6, "fat": 0.1, "fiber": 2.5},
    "beans": {"calories": 31, "protein": 1.8, "carbs": 7, "fat": 0.1, "fiber": 3.4},
    "cucumber": {"calories": 15, "protein": 0.7, "carbs": 3.6, "fat": 0.1, "fiber": 0.5},
    "beetroot": {"calories": 43, "protein": 1.6, "carbs": 10, "fat": 0.2, "fiber": 2.8},

    # Dairy
    "milk": {"calories": 62, "protein": 3.2, "carbs": 4.8, "fat": 3.3, "fiber": 0},
    "curd": {"calories": 61, "protein": 3.5, "carbs": 4.7, "fat": 3.3, "fiber": 0},
    "yogurt": {"calories": 61, "protein": 3.5, "carbs": 4.7, "fat": 3.3, "fiber": 0},
    "butter": {"calories": 717, "protein": 0.9, "carbs": 0.1, "fat": 81, "fiber": 0},
    "ghee": {"calories": 900, "protein": 0, "carbs": 0, "fat": 100, "fiber": 0},
    "cheese": {"calories": 402, "protein": 25, "carbs": 1.3, "fat": 33, "fiber": 0},
    "cream": {"calories": 340, "protein": 2.1, "carbs": 2.8, "fat": 36, "fiber": 0},

    # Oils
    "oil": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100, "fiber": 0},
    "cooking oil": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100, "fiber": 0},
    "olive oil": {"calories": 884, "protein": 0, "carbs": 0, "fat": 100, "fiber": 0},
    "coconut oil": {"calories": 862, "protein": 0, "carbs": 0, "fat": 100, "fiber": 0},
    "coconut milk": {"calories": 230, "protein": 2.3, "carbs": 5.5, "fat": 24, "fiber": 0},
}

# Nutritional targets
NUTRITION_TARGETS = {
    "high-protein": {"protein_min": 25, "description": "High Protein (≥25g protein per serving)"},
    "low-carb": {"carbs_max": 30, "description": "Low Carb (≤30g carbs per serving)"},
    "low-fat": {"fat_max": 15, "description": "Low Fat (≤15g fat per serving)"},
    "balanced": {"description": "Balanced (moderate macros across all categories)"},
    "high-fiber": {"fiber_min": 8, "description": "High Fiber (≥8g fiber per serving)"},
    "low-calorie": {"calories_max": 400, "description": "Low Calorie (≤400 kcal per serving)"},
}

# Typical quantity per serving by category (in grams)
SERVING_QUANTITIES = {
    "protein": 150,
    "grains": 100,
    "lentils": 75,
    "vegetables": 100,
    "dairy": 50,
    "oils": 15,
}


def _categorize(name: str) -> str:
    """Categorize ingredient for serving size estimation."""
    name_lower = name.lower()
    proteins = ["chicken", "mutton", "lamb", "fish", "prawns", "shrimp", "egg", "paneer", "tofu"]
    grains = ["rice", "flour", "atta", "bread", "pasta", "noodles", "oats", "poha"]
    lentils_list = ["dal", "rajma", "chickpeas", "chole", "lentils"]
    dairy = ["milk", "curd", "yogurt", "butter", "ghee", "cheese", "cream"]
    oils = ["oil"]

    for k in proteins:
        if k in name_lower:
            return "protein"
    for k in grains:
        if k in name_lower:
            return "grains"
    for k in lentils_list:
        if k in name_lower:
            return "lentils"
    for k in dairy:
        if k in name_lower:
            return "dairy"
    for k in oils:
        if k in name_lower:
            return "oils"
    return "vegetables"


def _find_nutrition(ingredient_name: str) -> dict | None:
    """Fuzzy match ingredient name against the nutrition database."""
    name_lower = ingredient_name.lower().strip()
    if name_lower in NUTRITION_DB:
        return NUTRITION_DB[name_lower]
    for db_key, info in NUTRITION_DB.items():
        if db_key in name_lower or name_lower in db_key:
            return info
    return None


@tool
def analyze_nutrition(ingredients_json: str, servings: int = 2, goal: str = "") -> str:
    """
    Analyze the nutritional content of a meal based on its ingredients.
    Calculates calories, protein, carbs, fat, and fiber per serving.
    Optionally checks against a nutritional goal.

    Use this tool when:
    - The user asks for "high protein", "low carb", "healthy", etc.
    - You need to verify if a recipe meets nutritional requirements
    - The user wants to know the calorie count of a meal

    Args:
        ingredients_json: A JSON list of ingredient names.
            Example: '["chicken breast", "rice", "onion", "tomato", "oil"]'
        servings: Number of servings (default: 2).
        goal: Optional nutritional goal to check against.
              Options: "high-protein", "low-carb", "low-fat", "balanced",
                       "high-fiber", "low-calorie", or empty string for no goal.

    Returns:
        Nutritional breakdown per serving with goal compliance check.
    """
    try:
        ingredients = json.loads(ingredients_json)
    except json.JSONDecodeError:
        return "Invalid JSON. Provide a list like: '[\"chicken\", \"rice\", \"onion\"]'"

    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0}
    details = []
    not_found = []

    for ingredient in ingredients:
        info = _find_nutrition(ingredient)
        if info:
            category = _categorize(ingredient)
            qty_g = SERVING_QUANTITIES.get(category, 100)
            factor = qty_g / 100.0  # nutrition DB is per 100g

            item_nutrition = {
                "calories": info["calories"] * factor,
                "protein": info["protein"] * factor,
                "carbs": info["carbs"] * factor,
                "fat": info["fat"] * factor,
                "fiber": info["fiber"] * factor,
            }

            for key in total:
                total[key] += item_nutrition[key]

            details.append(
                f"  {ingredient} (~{qty_g}g): "
                f"{item_nutrition['calories']:.0f} kcal, "
                f"P:{item_nutrition['protein']:.1f}g, "
                f"C:{item_nutrition['carbs']:.1f}g, "
                f"F:{item_nutrition['fat']:.1f}g"
            )
        else:
            not_found.append(ingredient)

    # Per serving values
    per_serving = {k: v / max(servings, 1) for k, v in total.items()}

    # Build output
    lines = [f"🥗 Nutrition Analysis ({servings} serving(s)):\n"]
    lines.append("Per-Ingredient Breakdown (total quantities):")
    lines.extend(details)

    if not_found:
        lines.append(f"\n⚠️ No nutrition data for: {', '.join(not_found)}")

    lines.append(f"\n{'='*45}")
    lines.append(f"  📊 PER SERVING:")
    lines.append(f"     Calories:  {per_serving['calories']:.0f} kcal")
    lines.append(f"     Protein:   {per_serving['protein']:.1f}g")
    lines.append(f"     Carbs:     {per_serving['carbs']:.1f}g")
    lines.append(f"     Fat:       {per_serving['fat']:.1f}g")
    lines.append(f"     Fiber:     {per_serving['fiber']:.1f}g")
    lines.append(f"{'='*45}")

    # Goal check
    if goal and goal.lower() in NUTRITION_TARGETS:
        target = NUTRITION_TARGETS[goal.lower()]
        lines.append(f"\n🎯 Goal Check: {target['description']}")

        checks_passed = True
        if "protein_min" in target and per_serving["protein"] < target["protein_min"]:
            lines.append(f"  ❌ Protein {per_serving['protein']:.1f}g < {target['protein_min']}g target")
            checks_passed = False
        elif "protein_min" in target:
            lines.append(f"  ✅ Protein {per_serving['protein']:.1f}g ≥ {target['protein_min']}g target")

        if "carbs_max" in target and per_serving["carbs"] > target["carbs_max"]:
            lines.append(f"  ❌ Carbs {per_serving['carbs']:.1f}g > {target['carbs_max']}g limit")
            checks_passed = False
        elif "carbs_max" in target:
            lines.append(f"  ✅ Carbs {per_serving['carbs']:.1f}g ≤ {target['carbs_max']}g limit")

        if "fat_max" in target and per_serving["fat"] > target["fat_max"]:
            lines.append(f"  ❌ Fat {per_serving['fat']:.1f}g > {target['fat_max']}g limit")
            checks_passed = False
        elif "fat_max" in target:
            lines.append(f"  ✅ Fat {per_serving['fat']:.1f}g ≤ {target['fat_max']}g limit")

        if "fiber_min" in target and per_serving["fiber"] < target["fiber_min"]:
            lines.append(f"  ❌ Fiber {per_serving['fiber']:.1f}g < {target['fiber_min']}g target")
            checks_passed = False
        elif "fiber_min" in target:
            lines.append(f"  ✅ Fiber {per_serving['fiber']:.1f}g ≥ {target['fiber_min']}g target")

        if "calories_max" in target and per_serving["calories"] > target["calories_max"]:
            lines.append(f"  ❌ Calories {per_serving['calories']:.0f} > {target['calories_max']} limit")
            checks_passed = False
        elif "calories_max" in target:
            lines.append(f"  ✅ Calories {per_serving['calories']:.0f} ≤ {target['calories_max']} limit")

        if checks_passed:
            lines.append(f"\n  ✅ MEETS {goal.upper()} GOAL!")
        else:
            lines.append(f"\n  ❌ DOES NOT MEET {goal.upper()} GOAL — consider alternative recipes.")
    elif goal:
        lines.append(f"\n⚠️ Unknown goal '{goal}'. Available: {', '.join(NUTRITION_TARGETS.keys())}")

    return "\n".join(lines)
