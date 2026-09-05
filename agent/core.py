"""
Food Decision Agent — Core
Sets up the ReAct agent using LangGraph with Google Gemini and all registered tools.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from config import GOOGLE_API_KEY, LLM_MODEL, LLM_TEMPERATURE, MAX_AGENT_ITERATIONS
from agent.prompts import build_system_prompt
from memory.store import MemoryStore

# Import all tools
from tools.web_search import web_search
from tools.recipe_search import search_recipe_by_name, search_recipe_by_ingredient, get_random_recipe
from tools.memory_manager import get_user_preferences, update_user_preferences
from tools.price_estimator import estimate_meal_cost
from tools.nutrition_analyzer import analyze_nutrition
from tools.pantry_matcher import match_pantry_ingredients


# All tools the agent can use
ALL_TOOLS = [
    web_search,
    search_recipe_by_name,
    search_recipe_by_ingredient,
    get_random_recipe,
    get_user_preferences,
    update_user_preferences,
    estimate_meal_cost,
    analyze_nutrition,
    match_pantry_ingredients,
]


def create_food_agent():
    """
    Create and return the Food Decision Agent with all tools registered.
    
    Returns:
        A LangGraph ReAct agent executor that can be invoked with messages.
    """
    if not GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY not set! Please create a .env file with your "
            "Google AI Studio API key. Get one free at: https://aistudio.google.com/"
        )

    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )

    # Load user memory to inject into system prompt
    memory_store = MemoryStore()
    memory_summary = memory_store.get_summary()
    system_prompt = build_system_prompt(memory_summary)

    # Create the ReAct agent using LangGraph's prebuilt helper
    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=system_prompt,
    )

    return agent


def _clean_content(content) -> str:
    """Extract plain text from AIMessage content, handling Gemini 3 list structure."""
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    parts.append(item["text"])
                elif "text" in item:
                    parts.append(str(item["text"]))
        return "\n".join(parts)
    return str(content)


import time
import logging

FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-flash-latest"]


def run_agent(agent, user_message: str, chat_history: list = None):
    """
    Run the agent with user message, with automatic retry and model fallback for 429 rate limits.
    """
    messages = []
    if chat_history:
        for role, content in chat_history:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    # Try running primary agent, with automatic retry if rate limited
    max_retries = 3
    result = None

    for attempt in range(max_retries):
        try:
            result = agent.invoke(
                {"messages": messages},
                config={"recursion_limit": MAX_AGENT_ITERATIONS}
            )
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if attempt < max_retries - 1:
                    wait_time = 15 * (attempt + 1)
                    time.sleep(wait_time)
                    # Try creating agent with fallback model
                    try:
                        fallback_model = FALLBACK_MODELS[attempt % len(FALLBACK_MODELS)]
                        fallback_llm = ChatGoogleGenerativeAI(
                            model=fallback_model,
                            google_api_key=GOOGLE_API_KEY,
                        )
                        fallback_agent = create_react_agent(
                            model=fallback_llm,
                            tools=ALL_TOOLS,
                            prompt=build_system_prompt(MemoryStore().get_summary()),
                        )
                        result = fallback_agent.invoke(
                            {"messages": messages},
                            config={"recursion_limit": MAX_AGENT_ITERATIONS}
                        )
                        break
                    except Exception:
                        continue
                else:
                    raise Exception("⏳ Free tier API rate limit reached (20 requests/minute). Please wait 30 seconds and try again!") from e
            else:
                raise e

    if not result:
        raise Exception("Could not get a response from the AI model. Please try again in a few seconds.")

    # Extract the final response and intermediate steps
    all_messages = result.get("messages", [])

    # The final AI message is the answer
    final_output = ""
    steps = []

    for msg in all_messages:
        msg_type = msg.__class__.__name__

        if msg_type == "AIMessage":
            # Check if this is a tool-calling step or the final answer
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    steps.append({
                        "type": "tool_call",
                        "tool": tc.get("name", "unknown"),
                        "input": tc.get("args", {}),
                    })
            if msg.content and not (hasattr(msg, "tool_calls") and msg.tool_calls):
                text_content = _clean_content(msg.content)
                if text_content.strip():
                    final_output = text_content

        elif msg_type == "ToolMessage":
            obs_text = _clean_content(msg.content)
            steps.append({
                "type": "observation",
                "tool": getattr(msg, "name", "unknown"),
                "output": obs_text[:500] if obs_text else "",  # Truncate for UI
            })

    # If no clean final output, use the last AI message
    if not final_output:
        for msg in reversed(all_messages):
            if msg.__class__.__name__ == "AIMessage" and msg.content:
                text_content = _clean_content(msg.content)
                if text_content.strip():
                    final_output = text_content
                    break

    return {
        "output": final_output or "I couldn't generate a response. Please try again.",
        "steps": steps,
    }
