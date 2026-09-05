"""
Food Decision Agent — Streamlit Application
Main UI with chat interface, ReAct agent trace visualization,
sidebar with memory management, and quick input helpers.
"""

import streamlit as st
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.core import create_food_agent, run_agent
from memory.store import MemoryStore


# ─── Page Configuration ──────────────────────────────────
st.set_page_config(
    page_title="🍽️ Food Decision Agent",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─── Custom CSS ───────────────────────────────────────────
st.markdown("""
<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    div[data-testid="stStatusWidget"] { background-color: #0e1117; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ─── Helper Functions ─────────────────────────────────────
def display_agent_steps(steps):
    """Render the ReAct loop steps in the UI."""
    for i, step in enumerate(steps):
        if step["type"] == "tool_call":
            st.markdown(f"**🔧 Tool Call: `{step['tool']}`**")
            input_str = json.dumps(step["input"], indent=2, ensure_ascii=False)
            st.code(input_str, language="json")
        elif step["type"] == "observation":
            st.markdown(f"**👁️ Observation from `{step['tool']}`:**")
            output_text = step["output"]
            if len(output_text) > 400:
                output_text = output_text[:400] + "..."
            st.text(output_text)
        if i < len(steps) - 1:
            st.markdown("---")


def process_user_input(prompt: str):
    """Process user input through the agent and display results."""
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Build chat history for context
    chat_history = []
    for msg in st.session_state.messages[:-1]:
        role = "user" if msg["role"] == "user" else "assistant"
        chat_history.append((role, msg["content"]))

    # Run the agent with trace visualization
    with st.chat_message("assistant"):
        with st.status("🧠 Agent is thinking...", expanded=True) as status:
            try:
                result = run_agent(
                    st.session_state.agent,
                    prompt,
                    chat_history=chat_history if chat_history else None,
                )
                steps = result.get("steps", [])
                for step in steps:
                    if step["type"] == "tool_call":
                        st.markdown(f"🔧 **Calling tool:** `{step['tool']}`")
                        st.json(step["input"])
                    elif step["type"] == "observation":
                        st.markdown(f"👁️ **Observed from** `{step['tool']}`:")
                        obs = step["output"]
                        st.text(obs[:250] + ("..." if len(obs) > 250 else ""))

                status.update(
                    label=f"✅ Agent completed — used {len(steps)} tool actions",
                    state="complete", expanded=False,
                )
            except Exception as e:
                status.update(label="❌ Agent error", state="error")
                st.error(f"Agent encountered an error: {str(e)}")
                result = {"output": f"Sorry, I encountered an error: {str(e)}. Please try again.", "steps": []}

        st.markdown(result["output"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["output"],
        "steps": result.get("steps", []),
    })


# ─── Initialize Session State ─────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Always instantiate agent from current config
try:
    st.session_state.agent = create_food_agent()
    st.session_state.agent_error = None
except Exception as e:
    st.session_state.agent = None
    st.session_state.agent_error = str(e)

if "memory_store" not in st.session_state:
    st.session_state.memory_store = MemoryStore()


# ─── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    # ── Quick Input Helpers ──
    st.header("⚡ Quick Inputs")
    st.caption("Set constraints, then ask your question in the chat.")

    budget = st.slider("💰 Budget (₹)", min_value=100, max_value=2000, value=500, step=50)
    time_limit = st.slider("⏱️ Time Limit (minutes)", min_value=10, max_value=120, value=45, step=5)
    servings = st.number_input("👥 Servings", min_value=1, max_value=10, value=2)
    nutrition_goal = st.selectbox(
        "🎯 Nutrition Goal",
        ["None", "High Protein", "Low Carb", "Low Fat", "Low Calorie", "High Fiber", "Balanced"],
    )
    pantry_input = st.text_area(
        "🧺 My Pantry (comma-separated)",
        placeholder="chicken, rice, onion, tomato, garlic...",
        height=80,
    )

    if st.button("✨ Generate Smart Prompt", use_container_width=True, type="primary"):
        parts = [f"I have a budget of ₹{budget} and {time_limit} minutes."]
        if pantry_input.strip():
            parts.append(f"I have these ingredients: {pantry_input.strip()}.")
        parts.append(f"Cooking for {servings} people.")
        if nutrition_goal != "None":
            parts.append(f"I want a {nutrition_goal.lower()} meal.")
        parts.append("What should I cook?")
        st.session_state.generated_prompt = " ".join(parts)
        st.rerun()

    st.divider()

    # ── Memory Display & Editing ──
    st.header("🧠 User Memory")
    st.caption("Your preferences are remembered across sessions.")

    memory = st.session_state.memory_store.get_all()

    # Editable preferences
    with st.expander("✏️ Edit Preferences", expanded=False):
        new_diet = st.multiselect(
            "Dietary Restrictions",
            ["vegetarian", "vegan", "gluten-free", "lactose-free", "halal", "jain"],
            default=memory.get("dietary_restrictions", []),
        )
        new_dislikes = st.text_input(
            "Disliked Ingredients (comma-separated)",
            value=", ".join(memory.get("disliked_ingredients", [])),
        )
        new_cuisines = st.multiselect(
            "Preferred Cuisines",
            ["Indian", "Chinese", "Italian", "Mexican", "Thai", "Japanese", "Continental", "South Indian"],
            default=memory.get("preferred_cuisines", []),
        )
        new_spice = st.select_slider(
            "🌶️ Spice Preference",
            options=["low", "medium", "high"],
            value=memory.get("spice_preference", "medium"),
        )
        new_equipment = st.multiselect(
            "Cooking Equipment",
            ["induction_stove", "gas_stove", "oven", "microwave", "pressure_cooker", "air_fryer", "mixer_grinder"],
            default=memory.get("cooking_equipment", []),
        )

        if st.button("💾 Save Preferences", use_container_width=True):
            dislikes_list = [d.strip() for d in new_dislikes.split(",") if d.strip()]
            st.session_state.memory_store.update({
                "dietary_restrictions": new_diet,
                "disliked_ingredients": dislikes_list,
                "preferred_cuisines": new_cuisines,
                "spice_preference": new_spice,
                "cooking_equipment": new_equipment,
            })
            st.success("✅ Preferences saved!")
            st.rerun()

    # Display current preferences (read-only summary)
    st.subheader("Current Profile")

    if memory.get("dietary_restrictions"):
        st.markdown(f"🥗 **Diet:** {', '.join(memory['dietary_restrictions'])}")
    else:
        st.markdown("🥗 **Diet:** No restrictions")

    if memory.get("disliked_ingredients"):
        st.markdown(f"👎 **Dislikes:** {', '.join(memory['disliked_ingredients'])}")

    if memory.get("preferred_cuisines"):
        st.markdown(f"🌍 **Cuisines:** {', '.join(memory['preferred_cuisines'])}")

    st.markdown(f"🌶️ **Spice:** {memory.get('spice_preference', 'medium')}")

    if memory.get("cooking_equipment"):
        st.markdown(f"🍳 **Equipment:** {', '.join(memory['cooking_equipment'])}")

    st.markdown(f"👥 **Servings:** {memory.get('default_servings', 2)}")
    st.markdown(f"💰 **Budget:** ₹{memory.get('budget_preference_inr', 500)}")

    if memory.get("past_meals"):
        st.subheader("📋 Recent Meals")
        for meal in memory["past_meals"][-5:]:
            rating = "⭐" * meal.get("rating", 0) if meal.get("rating") else ""
            st.markdown(f"- {meal['name']} {rating}")

    st.divider()

    if st.button("🗑️ Reset Memory", use_container_width=True):
        st.session_state.memory_store.reset()
        st.rerun()

    st.divider()
    st.subheader("ℹ️ Agent Tools")
    st.markdown(
        "- 🔍 Web Search\n"
        "- 📖 Recipe Database\n"
        "- 💰 Price Estimator\n"
        "- 🥗 Nutrition Analyzer\n"
        "- 🧺 Pantry Matcher\n"
        "- 🧠 Memory Manager"
    )


# ─── Main Chat Interface ─────────────────────────────────
st.title("🍽️ Food Decision Agent")
st.caption("I don't just find recipes — I reason, plan, and optimize your meal decisions.")

# Show error if agent couldn't be initialized
if st.session_state.agent_error:
    st.error(
        f"⚠️ {st.session_state.agent_error}\n\n"
        "**Setup:** Copy `.env.example` to `.env` and add your free Gemini API key from "
        "[Google AI Studio](https://aistudio.google.com/)"
    )
    st.stop()

# Example prompts for new users
if not st.session_state.messages:
    st.markdown("### 💡 Try asking me something like:")
    cols = st.columns(2)
    example_prompts = [
        "I have ₹300, 45 min, chicken and rice. High protein meal.",
        "I don't like mushrooms. Remember that. Now suggest a quick pasta.",
        "What can I make with eggs, onions, and tomatoes?",
        "Surprise me with something spicy for dinner!",
    ]
    for i, prompt in enumerate(example_prompts):
        col = cols[i % 2]
        if col.button(f"💬 {prompt}", key=f"example_{i}", use_container_width=True):
            process_user_input(prompt)
            st.rerun()

# Handle generated prompt from sidebar
if "generated_prompt" in st.session_state:
    prompt = st.session_state.pop("generated_prompt")
    process_user_input(prompt)
    st.rerun()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("steps"):
            with st.expander("🔍 View Agent's Reasoning Trace", expanded=False):
                display_agent_steps(message["steps"])

# Chat input
if prompt := st.chat_input("What should I cook today? Tell me your constraints..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    process_user_input(prompt)
    st.rerun()
