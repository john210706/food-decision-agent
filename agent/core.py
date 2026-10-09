"""
Food Decision Agent — Core
Sets up the ReAct agent using LangGraph with Google Gemini and all registered tools.
"""

import errno

import httpx
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
    if not GOOGLE_API_KEY or GOOGLE_API_KEY.startswith("your_"):
        raise ValueError(
            "GOOGLE_API_KEY not set! Please create a .env file with your "
            "Google AI Studio API key. Get one free at: https://aistudio.google.com/"
        )

    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=LLM_TEMPERATURE,
        timeout=60,
        max_retries=3,
    )

    # Load user memory to inject into system prompt
    memory_store = MemoryStore()
    memory_summary = memory_store.get_summary()
    system_prompt = build_system_prompt(memory_summary)

    tool_model = llm.bind_tools(ALL_TOOLS)

    def select_model(state, runtime):
        # Reserve the last model round for an answer, with tools disabled.
        tool_rounds = sum(bool(getattr(msg, "tool_calls", None)) for msg in state["messages"])
        return llm if tool_rounds >= MAX_AGENT_ITERATIONS - 1 else tool_model

    agent = create_react_agent(
        model=select_model,
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



def run_agent(agent, user_message: str, chat_history: list = None):
    """Run a bounded tool loop and return the answer and tool trace."""
    messages = [
        {"role": role, "content": content}
        for role, content in (chat_history or [])
    ]
    messages.append({"role": "user", "content": user_message})
    try:
        result = agent.invoke(
            {"messages": messages},
            config={"recursion_limit": 2 * MAX_AGENT_ITERATIONS + 1},
        )
    except Exception as exc:
        if isinstance(exc, httpx.TransportError) or (
            isinstance(exc, OSError) and exc.errno in {
                errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ECONNRESET,
                errno.ECONNREFUSED, errno.ETIMEDOUT,
            }
        ):
            raise RuntimeError(
                "Could not reach Gemini after retrying. Check the server's internet "
                "connection and retry your request."
            ) from exc
        if "503" in str(exc) or "UNAVAILABLE" in str(exc):
            raise RuntimeError(
                "Gemini is temporarily busy. Your request is saved; please retry shortly."
            ) from exc
        if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
            raise RuntimeError(
                "Gemini quota or rate limit reached. Check your API quota "
                "in Google AI Studio, then retry when quota is available."
            ) from exc
        raise

    # Extract the final response and intermediate steps
    all_messages = result.get("messages", [])

    # The final AI message is the answer
    final_output = ""
    steps = []

    for msg in all_messages[len(messages):]:
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
