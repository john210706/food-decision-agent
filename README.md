# 🍽️ Food Decision Agent

An autonomous, multi-constraint **Food Decision Agent** powered by a **ReAct (Reason → Act → Observe)** reasoning loop. This isn't a recipe finder — it's an intelligent agent that reasons about your budget, time, available ingredients, nutritional goals, and personal preferences to deliver optimized meal recommendations.

## 🏗️ Architecture

```
User Query → Agent Understands Goal → Reasoning/Planning → Tool Selection
     → Tool Call → Observe Result → Need More Info? → Reason Again → Final Answer
```

### ReAct Loop (Reason → Act → Observe)

The agent follows an iterative decision-making cycle:

1. **🧠 Reason** — Analyze user constraints (budget, time, ingredients, nutrition, preferences)
2. **🔧 Act** — Call the appropriate tool (search recipes, check prices, match pantry, etc.)
3. **👁️ Observe** — Process the tool's output and check if constraints are satisfied
4. **🔄 Iterate** — If not all constraints are met, reason and act again
5. **✅ Answer** — Present the optimized recommendation with full reasoning trace

## 🛠️ Tool Suite (6 Tools)

| Tool | Purpose |
|:---|:---|
| 🔍 **Web Search** | DuckDuckGo search for real-time recipes, prices, cooking tips |
| 📖 **Recipe Search** | TheMealDB database — search by name, ingredient, or get random |
| 💰 **Price Estimator** | Indian grocery price database (₹ INR) — estimates per-serving cost |
| 🥗 **Nutrition Analyzer** | Macro calculator (protein, carbs, fat, calories) with goal checking |
| 🧺 **Pantry Matcher** | Compares recipe ingredients vs. your available ingredients |
| 🧠 **Memory Manager** | Persistent user preferences — dislikes, diet, equipment, history |

## 🧠 Memory System

The agent **remembers your preferences** across sessions:
- Dietary restrictions (vegetarian, vegan, gluten-free, etc.)
- Disliked ingredients (the agent will NEVER recommend these)
- Preferred cuisines
- Spice preference (low / medium / high)
- Cooking equipment (induction stove, microwave, etc.)
- Default serving size
- Past meal history (avoids repetition)

Memory is stored locally in `data/user_memory.json` and persists between sessions.

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- A free Google Gemini API key

### Step 1: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure API key
```bash
copy .env.example .env
```
Edit `.env` and add your free Gemini API key from [Google AI Studio](https://aistudio.google.com/):
```
GOOGLE_API_KEY=your_actual_key_here
```

### Step 3: Run the app
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## 💬 Example Queries

| Query | What the Agent Does |
|:---|:---|
| *"I have ₹300, 45 min, chicken and rice. High protein meal."* | Searches recipes → matches pantry → checks price → verifies nutrition → recommends |
| *"I don't like olives. Remember that."* | Saves to memory → confirms preference stored |
| *"What can I make with eggs, onions, and tomatoes?"* | Searches by ingredient → matches pantry → suggests feasible recipes |
| *"Surprise me with something spicy!"* | Loads memory (spice=high) → gets random recipe → filters by preference |

## 📂 Project Structure

```
Food Decision Agent/
├── app.py                      # Streamlit chat UI with agent trace
├── config.py                   # Centralized configuration
├── requirements.txt            # Python dependencies
├── .env.example                # API key template
├── agent/
│   ├── __init__.py
│   ├── core.py                 # ReAct agent (LangGraph + Gemini)
│   └── prompts.py              # System prompt with reasoning rules
├── tools/
│   ├── __init__.py
│   ├── web_search.py           # DuckDuckGo search (free)
│   ├── recipe_search.py        # TheMealDB API (free)
│   ├── price_estimator.py      # Indian grocery price database
│   ├── nutrition_analyzer.py   # Macro/calorie calculator
│   ├── pantry_matcher.py       # Ingredient matching engine
│   └── memory_manager.py       # Preference read/write tool
├── memory/
│   ├── __init__.py
│   └── store.py                # JSON-based persistent memory
└── data/
    └── user_memory.json        # Stored user preferences
```

## 🧪 Tech Stack

| Layer | Technology |
|:---|:---|
| **Language** | Python 3.10+ |
| **Agent Framework** | LangChain + LangGraph (ReAct agent) |
| **LLM** | Google Gemini 2.5 Flash (free tier) |
| **UI** | Streamlit |
| **Web Search** | DuckDuckGo (free, no API key) |
| **Recipe Data** | TheMealDB API (free, no signup) |
| **Memory** | JSON file-based persistent store |

## 📝 License

This project is for educational purposes.

## OUTPUT

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/a29e4406-d830-48c7-bb91-b6e469b17ba0" />
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/16e54df6-c9a7-46c1-8f3f-46fdefde0386" />
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/4b7d61e4-405c-4863-8765-12fc1a0a95eb" />


