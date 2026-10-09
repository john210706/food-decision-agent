import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from agent.core import run_agent
from memory.store import MemoryStore
from tools.nutrition_analyzer import analyze_nutrition
from tools.price_estimator import estimate_meal_cost
from tools.pantry_matcher import match_pantry_ingredients, _is_match
from tools.memory_manager import update_user_preferences
from tools.recipe_search import _parse_meal


class RegressionTests(unittest.TestCase):
    def test_nutrition_per_serving_is_consistent(self):
        for servings in (1, 2, 4):
            result = analyze_nutrition.invoke({
                "ingredients_json": '["chicken breast"]', "servings": servings,
                "goal": "high-protein",
            })
            self.assertIn("Protein:   46.5g", result)
            self.assertIn("MEETS HIGH-PROTEIN GOAL", result)

    def test_two_eggs_per_serving(self):
        result = estimate_meal_cost.invoke({"ingredients_json": '["eggs"]', "servings": 3})
        self.assertIn("6 pieces", result)

    def test_invalid_tool_inputs(self):
        for tool in (analyze_nutrition, estimate_meal_cost):
            for invalid in ('null', '{}', '[2]', '[""]'):
                self.assertIn("list", tool.invoke({"ingredients_json": invalid}).lower())
            self.assertIn("positive", tool.invoke({"ingredients_json": '["rice"]', "servings": 0}))
        self.assertIn("non-empty", match_pantry_ingredients.invoke({
            "recipe_ingredients_json": '["rice"]', "pantry_items_json": '[""]'}))
        self.assertIn("JSON object", update_user_preferences.invoke({"preferences_json": "[]"}))

    def test_memory_merge_replace_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "nested" / "memory.json")
            store.update({"disliked_ingredients": ["olives"]})
            store.update({"disliked_ingredients": ["mushrooms"]})
            self.assertEqual(store.get("disliked_ingredients"), ["olives", "mushrooms"])
            store.update({"disliked_ingredients": []}, replace_lists=True)
            self.assertEqual(store.get("disliked_ingredients"), [])
            with self.assertRaises(ValueError):
                store.update({"dietary_restrictions": "vegan"})
            self.assertEqual(store.get("dietary_restrictions"), [])

    def test_agent_trace_and_history(self):
        agent = Mock()
        agent.invoke.return_value = {"messages": [
            HumanMessage(content="old"), AIMessage(content="old answer"),
            HumanMessage(content="meal"),
            AIMessage(content="", tool_calls=[{"name": "test", "args": {}, "id": "1"}]),
            ToolMessage(content="observation", tool_call_id="1", name="test"),
            AIMessage(content=[{"type": "text", "text": "new answer"}]),
        ]}
        result = run_agent(agent, "meal", [("user", "old"), ("assistant", "old answer")])
        self.assertEqual(result["output"], "new answer")
        self.assertEqual(len(result["steps"]), 2)
        self.assertEqual(agent.invoke.call_args.kwargs["config"]["recursion_limit"], 13)

    def test_rate_limit_is_actionable(self):
        agent = Mock()
        agent.invoke.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED")
        with self.assertRaisesRegex(RuntimeError, "quota"):
            run_agent(agent, "meal")
        self.assertEqual(agent.invoke.call_count, 1)

    def test_connection_and_service_errors_are_actionable(self):
        import errno
        import httpx
        for error, expected in (
            (OSError(errno.ENETUNREACH, "Network is unreachable"), "internet"),
            (httpx.ConnectError("connection failed"), "internet"),
            (RuntimeError("503 UNAVAILABLE"), "temporarily busy"),
        ):
            agent = Mock()
            agent.invoke.side_effect = error
            with self.assertRaisesRegex(RuntimeError, expected):
                run_agent(agent, "meal")

    def test_sdk_retries_transient_model_requests(self):
        import httpx
        from langchain_google_genai import ChatGoogleGenerativeAI
        from agent.core import create_food_agent
        responses = [
            httpx.ConnectError("Network is unreachable"),
            httpx.Response(503, json={"error": {"code": 503, "message": "busy", "status": "UNAVAILABLE"}}),
            httpx.Response(200, json={"candidates": [{
                "content": {"role": "model", "parts": [{"text": "Recovered"}]},
                "finishReason": "STOP",
            }]}),
        ]

        def handle(request):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        def make_model(**kwargs):
            kwargs["google_api_key"] = "test-key"
            kwargs["client_args"] = {"transport": httpx.MockTransport(handle)}
            return ChatGoogleGenerativeAI(**kwargs)

        with patch("agent.core.GOOGLE_API_KEY", "test-key"), patch(
            "agent.core.ChatGoogleGenerativeAI", side_effect=make_model
        ):
            result = run_agent(create_food_agent(), "hello")
        self.assertEqual(result["output"], "Recovered")
        self.assertEqual(responses, [])

    def test_tool_loop_reserves_a_final_answer(self):
        from agent.core import create_food_agent
        from langchain_core.runnables import RunnableLambda
        from tools.memory_manager import get_user_preferences
        model = Mock()
        model.bind_tools.return_value = "tool-model"
        with patch("agent.core.ChatGoogleGenerativeAI", return_value=model), patch(
            "agent.core.GOOGLE_API_KEY", "test-key"
        ), patch("agent.core.create_react_agent") as create:
            create_food_agent()
        selector = create.call_args.kwargs["model"]
        self.assertEqual(selector({"messages": []}, None), "tool-model")
        calls = [AIMessage(content="", tool_calls=[{
            "name": "get_user_preferences", "args": {}, "id": str(i)
        }]) for i in range(5)]
        self.assertIs(selector({"messages": calls}, None), model)

        from langgraph.prebuilt import create_react_agent
        counter = 0

        def choose(state, runtime):
            nonlocal counter
            counter += 1
            if counter <= 5:
                reply = AIMessage(content="", tool_calls=[{
                    "name": "get_user_preferences", "args": {}, "id": str(counter)
                }])
            else:
                reply = AIMessage(content="Final recommendation")
            return RunnableLambda(lambda messages: reply)

        agent = create_react_agent(choose, [get_user_preferences])
        self.assertEqual(run_agent(agent, "meal")["output"], "Final recommendation")

    def test_ui_retry_preserves_request_without_duplicate_messages(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.json")
            with patch("agent.core.create_food_agent", return_value=Mock()), patch(
                "memory.store.MemoryStore", return_value=store
            ), patch("agent.core.run_agent", side_effect=[
                RuntimeError("Connection failed"),
                {"output": "Recovered recommendation", "steps": []},
            ]) as run:
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
                app.chat_input[0].set_value("Cook my meal").run()
                self.assertEqual(app.session_state.failed_prompt, "Cook my meal")
                self.assertEqual(len(app.session_state.messages), 1)
                next(button for button in app.button if button.label == "🔄 Retry last request").click().run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(app.session_state.messages), 2)
                self.assertEqual(app.session_state.messages[-1]["content"], "Recovered recommendation")
                self.assertIsNone(run.call_args.kwargs["chat_history"])

    def test_pantry_does_not_confuse_distinct_ingredients(self):
        self.assertFalse(_is_match("coconut milk", "milk"))
        self.assertFalse(_is_match("chicken", "chicken stock"))
        self.assertTrue(_is_match("yogurt", "curd"))

    def test_nullable_recipe_fields(self):
        self.assertIn("rice", _parse_meal({
            "strInstructions": None, "strIngredient1": "rice", "strMeasure1": None}))

    def test_streamlit_load_and_chat(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "memory.json")
            store.update({"preferred_cuisines": ["Korean"]})
            with patch("agent.core.create_food_agent", return_value=Mock()):
                with patch("memory.store.MemoryStore", return_value=store), patch(
                    "agent.core.run_agent", return_value={"output": "Test recommendation", "steps": []}
                ):
                    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
                    self.assertEqual(len(app.exception), 0)
                    app.chat_input[0].set_value("What can I cook?").run(timeout=30)
                    self.assertEqual(len(app.exception), 0)
                    self.assertEqual(app.session_state.messages[-1]["content"], "Test recommendation")


if __name__ == "__main__":
    unittest.main()
