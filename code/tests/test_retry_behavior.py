"""Deterministic test of corrective specialist retries (no Groq calls)."""
import unittest
from unittest.mock import patch

import orchestrator


def duplicate_answer(invoice_id, recommendation):
    return {
        "agent": "duplicate",
        "invoice_id": invoice_id,
        "recommendation": recommendation,
        "reason": "Mock response for retry testing",
    }


class AgentRetryTests(unittest.TestCase):
    def setUp(self):
        self.invoice_id = "INV-RETRY-DEMO"
        self.patches = [
            patch.object(orchestrator, "get_invoice", return_value={"invoice_id": self.invoice_id}),
            patch.object(orchestrator, "check_three_way_match", return_value={"status": "MATCH", "exceptions": []}),
            patch.object(orchestrator, "check_duplicates", return_value={"status": "DUPLICATE"}),
            patch.object(orchestrator, "check_invoice_risk", return_value={"status": "CLEAR", "risks": []}),
            patch.object(orchestrator, "ask_ai_json", return_value={"agents": ["duplicate"], "reason": "Duplicate found"}),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_corrected_second_attempt(self):
        responses = [
            duplicate_answer(self.invoice_id, "CLEAR"),
            duplicate_answer(self.invoice_id, "HOLD"),
        ]
        with patch.dict(orchestrator.AGENTS, {"duplicate": lambda _: responses.pop(0)}):
            result = orchestrator.run_orchestrator(self.invoice_id)
        self.assertEqual(len(responses), 0, "Specialist should be called twice")
        self.assertEqual(result["evidence_errors"], [])
        self.assertEqual(result["decision"], "ESCALATE")  # Business rule: duplicate => escalate
        self.assertEqual(result["agent_results"][0]["recommendation"], "HOLD")

    def test_two_bad_attempts_escalate_safely(self):
        calls = []
        def wrong_answer(inv):
            calls.append(inv)
            return duplicate_answer(inv, "CLEAR")
        with patch.dict(orchestrator.AGENTS, {"duplicate": wrong_answer}):
            result = orchestrator.run_orchestrator(self.invoice_id)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["decision"], "ESCALATE")
        self.assertTrue(result["evidence_errors"])


if __name__ == "__main__":
    unittest.main()
