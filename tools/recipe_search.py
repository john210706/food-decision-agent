"""
Recipe Search Tool
Searches TheMealDB API for recipes by name, ingredient, or random.
Free API — no key required (uses test key '1').
"""

import requests
from langchain_core.tools import tool
from config import MEALDB_SEARCH_URL, MEALDB_FILTER_URL, MEALDB_LOOKUP_URL, MEALDB_RANDOM_URL


def _parse_meal(meal: dict) -> str:
    """Parse a meal object from TheMealDB into a readable string."""
    name = meal.get("strMeal", "Unknown")
    category = meal.get("strCategory", "N/A")
    area = meal.get("strArea", "N/A")
    instructions = meal.get("strInstructions", "No instructions available.")
    thumbnail = meal.get("strMealThumb", "")

    # Extract ingredients and measures (TheMealDB uses strIngredient1..20)
    ingredients = []
    for i in range(1, 21):
        ingredient = meal.get(f"strIngredient{i}", "")
        measure = meal.get(f"strMeasure{i}", "")
        if ingredient and ingredient.strip():
            ingredients.append(f"  - {measure.strip()} {ingredient.strip()}")

    ingredients_str = "\n".join(ingredients) if ingredients else "  No ingredients listed."

    # Truncate instructions to keep output manageable
    if len(instructions) > 800:
        instructions = instructions[:800] + "..."

    return (
        f"🍽️ **{name}**\n"
        f"   Category: {category} | Cuisine: {area}\n"
        f"   Thumbnail: {thumbnail}\n\n"
        f"   **Ingredients:**\n{ingredients_str}\n\n"
        f"   **Instructions:**\n   {instructions}\n"
    )


def _parse_meal_brief(meal: dict) -> str:
    """Parse a meal object into a brief summary (for filtered results without full details)."""
    name = meal.get("strMeal", "Unknown")
    thumb = meal.get("strMealThumb", "")
    meal_id = meal.get("idMeal", "")
    return f"  - {name} (ID: {meal_id}) | Thumbnail: {thumb}"


@tool
def search_recipe_by_name(name: str) -> str:
    """
    Search for recipes by name using TheMealDB database.
    Returns detailed recipe information including ingredients and instructions.

    Use this tool when:
    - The user asks for a specific dish (e.g., "chicken biryani", "pasta")
    - You want to find recipes matching a keyword

    Args:
        name: The recipe name or keyword to search for.
              Example: "chicken curry", "pasta", "paneer"

    Returns:
        Detailed recipe information including ingredients, instructions, and category.
    """
    try:
        response = requests.get(MEALDB_SEARCH_URL, params={"s": name}, timeout=10)
        response.raise_for_status()
        data = response.json()

        meals = data.get("meals")
        if not meals:
            return f"No recipes found for '{name}'. Try a different search term or use web_search for more options."

        # Return up to 3 detailed results
        results = [_parse_meal(meal) for meal in meals[:3]]
        return f"Found {len(meals)} recipe(s) for '{name}':\n\n" + "\n---\n".join(results)

    except requests.RequestException as e:
        return f"Recipe search failed: {str(e)}. Try using web_search instead."


@tool
def search_recipe_by_ingredient(ingredient: str) -> str:
    """
    Find recipes that use a specific ingredient.
    Returns a list of matching recipes (brief format — use search_recipe_by_name 
    to get full details of a specific recipe).

    Use this tool when:
    - The user says "I have chicken" or "I have paneer, what can I make?"
    - You need to find recipes that use specific available ingredients

    Args:
        ingredient: A single main ingredient to search for.
                    Example: "chicken", "rice", "paneer", "egg"

    Returns:
        A list of recipe names that use the given ingredient.
    """
    try:
        response = requests.get(MEALDB_FILTER_URL, params={"i": ingredient}, timeout=10)
        response.raise_for_status()
        data = response.json()

        meals = data.get("meals")
        if not meals:
            return f"No recipes found using '{ingredient}'. Try a different ingredient or use web_search."

        results = [_parse_meal_brief(meal) for meal in meals[:10]]
        return (
            f"Found {len(meals)} recipe(s) using '{ingredient}' (showing top 10):\n\n"
            + "\n".join(results)
            + "\n\n💡 Use search_recipe_by_name to get full details for any of these dishes."
        )

    except requests.RequestException as e:
        return f"Ingredient-based search failed: {str(e)}. Try using web_search instead."


@tool
def get_random_recipe() -> str:
    """
    Get a random recipe suggestion from TheMealDB.
    Useful when the user wants inspiration or says "surprise me".

    Returns:
        A detailed random recipe with ingredients and instructions.
    """
    try:
        response = requests.get(MEALDB_RANDOM_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        meals = data.get("meals")
        if not meals:
            return "Could not fetch a random recipe. Try again."

        return "🎲 Here's a random recipe suggestion:\n\n" + _parse_meal(meals[0])

    except requests.RequestException as e:
        return f"Random recipe fetch failed: {str(e)}."
