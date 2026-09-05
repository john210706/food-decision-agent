"""
Web Search Tool
Uses DuckDuckGo to search the web for recipes, prices, cooking tips, etc.
No API key required.
"""

from langchain_core.tools import tool
from duckduckgo_search import DDGS
from config import MAX_SEARCH_RESULTS


@tool
def web_search(query: str) -> str:
    """
    Search the web for information about recipes, ingredient prices,
    cooking techniques, nutritional info, or food-related topics.

    Use this tool when you need real-time information that isn't available
    from the recipe database, such as:
    - Current market prices of ingredients in India
    - Cooking tips for specific equipment (induction stove, microwave, etc.)
    - Ingredient substitutions
    - Regional recipe variations
    - Nutritional information for specific foods

    Args:
        query: The search query string. Be specific for better results.
               Example: "chicken biryani recipe ingredients price India INR"

    Returns:
        A formatted string with top search results including title, snippet, and URL.
    """
    try:
        with DDGS(timeout=3) as ddgs:
            results = list(ddgs.text(query, max_results=MAX_SEARCH_RESULTS))

        if not results:
            return f"No search results found for: '{query}'. Try a different query."

        formatted = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            snippet = r.get("body", "No description")
            url = r.get("href", "")
            formatted.append(f"{i}. **{title}**\n   {snippet}\n   URL: {url}")

        return f"Web Search Results for '{query}':\n\n" + "\n\n".join(formatted)

    except Exception as e:
        return f"Web search failed: {str(e)}. Try rephrasing the query."
