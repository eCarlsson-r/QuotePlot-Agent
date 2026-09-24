"""Deterministic coverage for Lucy's evidence and Gemini tool registration."""

import json
import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("GEMINI_API_KEY", "unit-test-key")

from backend.routers import agent
from backend.brain import classify_user_intent


class AgentInvestigationTests(unittest.TestCase):
    def test_gemini_session_registers_read_only_token_lookup_tool(self):
        captured = {}

        class Chats:
            def create(self, **kwargs):
                captured.update(kwargs)
                return object()

        class Client:
            chats = Chats()

        with patch.object(agent.genai, "Client", return_value=Client()):
            lucy = agent.LucyAgent()
            lucy.get_or_create_session("tools-test")

        self.assertIn(agent.get_token_onchain_data, captured["config"].tools)

    def test_onchain_tool_returns_structured_resolver_result(self):
        class FakeDB:
            closed = False

            def close(self):
                self.closed = True

        db = FakeDB()
        expected = {"symbol": "DAI", "chain": "ethereum", "block_number": 20}
        with patch.object(agent, "SessionLocal", return_value=db), patch.object(
            agent, "get_token_on_chain_intelligence", new=AsyncMock(return_value=expected)
        ):
            result = json.loads(agent.get_token_onchain_data("DAI"))

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["data"], expected)
        self.assertTrue(db.closed)

    def test_missing_sources_are_reported_as_insufficient_not_negative(self):
        evidence = agent._build_investigation_evidence(
            [], "Neutral", 0.0, "", "", "",
            {"status": "unavailable", "message": "No TokenMap entry."},
        )

        self.assertEqual([item["status"] for item in evidence], [
            "unavailable", "insufficient", "unavailable", "unavailable"
        ])
        self.assertIn("Insufficient", evidence[1]["summary"])
        self.assertIn("No TokenMap entry", evidence[3]["summary"])

    def test_onchain_queries_enter_the_token_investigation_flow(self):
        self.assertEqual(classify_user_intent("Show me DAI on-chain metadata"), "market_query")


if __name__ == "__main__":
    unittest.main()
