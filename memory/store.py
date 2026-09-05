"""
Persistent Memory Store
JSON file-based storage for user preferences and meal history.
Supports reading, writing, and merge-updates (won't overwrite entire memory).
"""

import json
import copy
from pathlib import Path
from config import MEMORY_FILE, DEFAULT_MEMORY, DATA_DIR


class MemoryStore:
    """JSON-backed persistent memory for user preferences."""

    def __init__(self, filepath: Path = MEMORY_FILE):
        self.filepath = filepath
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create the data directory and default memory file if they don't exist."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.filepath.exists():
            self._write_raw(DEFAULT_MEMORY)

    def _read_raw(self) -> dict:
        """Read the raw JSON file."""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return copy.deepcopy(DEFAULT_MEMORY)

    def _write_raw(self, data: dict):
        """Write data to JSON file atomically."""
        # Write to a temp file first, then rename (atomic on most OS)
        temp_path = self.filepath.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(self.filepath)

    def get_all(self) -> dict:
        """Get all user preferences."""
        return self._read_raw()

    def get(self, key: str, default=None):
        """Get a specific preference value."""
        data = self._read_raw()
        return data.get(key, default)

    def update(self, updates: dict):
        """
        Merge-update preferences. Lists are extended (deduplicated), 
        scalars are overwritten.
        
        Example:
            update({"disliked_ingredients": ["mushroom"], "spice_preference": "high"})
        """
        data = self._read_raw()

        for key, value in updates.items():
            if key in data and isinstance(data[key], list) and isinstance(value, list):
                # Extend list and deduplicate while preserving order
                combined = data[key] + [v for v in value if v not in data[key]]
                data[key] = combined
            else:
                data[key] = value

        self._write_raw(data)
        return data

    def remove_from_list(self, key: str, values: list):
        """Remove specific values from a list preference."""
        data = self._read_raw()
        if key in data and isinstance(data[key], list):
            data[key] = [item for item in data[key] if item not in values]
            self._write_raw(data)
        return data

    def add_meal_to_history(self, meal_name: str, rating: int = 0):
        """Add a meal to the user's history."""
        from datetime import date
        data = self._read_raw()
        data.setdefault("past_meals", []).append({
            "name": meal_name,
            "date": str(date.today()),
            "rating": rating
        })
        # Keep only last 20 meals
        data["past_meals"] = data["past_meals"][-20:]
        self._write_raw(data)
        return data

    def reset(self):
        """Reset memory to defaults."""
        self._write_raw(copy.deepcopy(DEFAULT_MEMORY))
        return DEFAULT_MEMORY

    def get_summary(self) -> str:
        """Get a human-readable summary of user preferences for the agent prompt."""
        data = self._read_raw()
        lines = []

        if data.get("dietary_restrictions"):
            lines.append(f"- Dietary restrictions: {', '.join(data['dietary_restrictions'])}")
        if data.get("disliked_ingredients"):
            lines.append(f"- Dislikes these ingredients: {', '.join(data['disliked_ingredients'])}")
        if data.get("preferred_cuisines"):
            lines.append(f"- Preferred cuisines: {', '.join(data['preferred_cuisines'])}")
        if data.get("spice_preference"):
            lines.append(f"- Spice preference: {data['spice_preference']}")
        if data.get("cooking_equipment"):
            lines.append(f"- Cooking equipment: {', '.join(data['cooking_equipment'])}")
        if data.get("default_servings"):
            lines.append(f"- Usually cooks for: {data['default_servings']} people")
        if data.get("budget_preference_inr"):
            lines.append(f"- Default budget: ₹{data['budget_preference_inr']}")
        if data.get("past_meals"):
            recent = data["past_meals"][-5:]
            meal_names = [m["name"] for m in recent]
            lines.append(f"- Recent meals: {', '.join(meal_names)}")

        if not lines:
            return "No preferences stored yet."
        return "User Preferences:\n" + "\n".join(lines)
