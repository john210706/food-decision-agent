"""
Memory Manager Tool
Agent-callable tool to read and write persistent user preferences.
The agent uses this to personalize recommendations and learn from the user.
"""

import json
from langchain_core.tools import tool
from memory.store import MemoryStore


# Shared instance — created once, reused across tool calls
_store = MemoryStore()


@tool
def get_user_preferences() -> str:
    """
    Retrieve the user's stored preferences and profile information.
    
    ALWAYS call this tool at the start of a conversation or when you need
    to check the user's dietary restrictions, dislikes, equipment, 
    budget preferences, or past meal history.

    Returns:
        A formatted summary of all stored user preferences including:
        - Dietary restrictions (vegetarian, vegan, gluten-free, etc.)
        - Disliked ingredients (foods the user doesn't like)
        - Preferred cuisines (Indian, Chinese, Italian, etc.)
        - Spice preference (low, medium, high)
        - Cooking equipment (induction stove, oven, microwave, etc.)
        - Default serving size
        - Budget preference in INR
        - Recent meal history
    """
    try:
        summary = _store.get_summary()
        all_data = _store.get_all()
        return (
            f"{summary}\n\n"
            f"Raw preferences data:\n{json.dumps(all_data, indent=2, ensure_ascii=False)}"
        )
    except Exception as e:
        return f"Failed to read user preferences: {str(e)}"


@tool
def update_user_preferences(preferences_json: str) -> str:
    """
    Save or update user preferences. Call this when the user tells you 
    about their food preferences, restrictions, or equipment.

    Examples of when to use this:
    - User says "I don't like mushrooms" → update disliked_ingredients
    - User says "I'm vegetarian" → update dietary_restrictions
    - User says "I have a microwave" → update cooking_equipment
    - User says "I prefer spicy food" → update spice_preference
    - User says "I usually cook for 4 people" → update default_servings

    Args:
        preferences_json: A JSON string with the preferences to update.
            Valid keys and their expected types:
            - "dietary_restrictions": list of strings, e.g. ["vegetarian", "gluten-free"]
            - "disliked_ingredients": list of strings, e.g. ["mushroom", "olives"]
            - "preferred_cuisines": list of strings, e.g. ["Indian", "Chinese"]
            - "spice_preference": string, one of "low", "medium", "high"
            - "cooking_equipment": list of strings, e.g. ["induction_stove", "oven"]
            - "default_servings": integer, e.g. 2
            - "budget_preference_inr": integer, e.g. 500
            
            Example input: '{"disliked_ingredients": ["mushroom"], "spice_preference": "high"}'

    Returns:
        Confirmation of what was updated.
    """
    try:
        updates = json.loads(preferences_json)
    except json.JSONDecodeError as e:
        return f"Invalid JSON format: {str(e)}. Please provide valid JSON."

    valid_keys = {
        "dietary_restrictions", "disliked_ingredients", "preferred_cuisines",
        "spice_preference", "cooking_equipment", "default_servings",
        "budget_preference_inr", "past_meals"
    }

    # Filter to only valid keys
    filtered = {k: v for k, v in updates.items() if k in valid_keys}
    if not filtered:
        return f"No valid preference keys found. Valid keys are: {', '.join(valid_keys)}"

    updated_data = _store.update(filtered)
    updated_keys = list(filtered.keys())

    return (
        f"✅ Successfully updated user preferences: {', '.join(updated_keys)}\n"
        f"Current preferences:\n{_store.get_summary()}"
    )
