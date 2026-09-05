"""
Food Decision Agent — Configuration
Centralized settings for the entire application.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── Paths ───────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MEMORY_FILE = DATA_DIR / "user_memory.json"

# ─── API Keys ────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# ─── LLM Settings ────────────────────────────────────────
LLM_MODEL = "gemini-3.6-flash"
LLM_TEMPERATURE = 0.4

# ─── TheMealDB API ───────────────────────────────────────
MEALDB_BASE_URL = "https://www.themealdb.com/api/json/v1/1"
MEALDB_SEARCH_URL = f"{MEALDB_BASE_URL}/search.php"
MEALDB_FILTER_URL = f"{MEALDB_BASE_URL}/filter.php"
MEALDB_LOOKUP_URL = f"{MEALDB_BASE_URL}/lookup.php"
MEALDB_RANDOM_URL = f"{MEALDB_BASE_URL}/random.php"

# ─── Web Search Settings ─────────────────────────────────
MAX_SEARCH_RESULTS = 5

# ─── Agent Settings ──────────────────────────────────────
MAX_AGENT_ITERATIONS = 6  # Max ReAct loop iterations before stopping

# ─── Default User Preferences (for new users) ────────────
DEFAULT_MEMORY = {
    "dietary_restrictions": [],
    "disliked_ingredients": [],
    "preferred_cuisines": [],
    "spice_preference": "medium",
    "cooking_equipment": [],
    "default_servings": 2,
    "budget_preference_inr": 500,
    "past_meals": []
}
