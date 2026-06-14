"""
Unit tests for CodeIterAgent.

These tests mock the Anthropic client so they run without an API key and
without using any tokens.
"""

import unittest
from unittest.mock import patch, MagicMock

from agent import CodeIterAgent


def fake_response(text: str):
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


class TestExtractCode(unittest.TestCase):
    def setUp(self):
        with patch("agent.Anthropic"):
            self.agent = CodeIterAgent()

    def test_extract_python_fenced_block(self):
        raw = "Here you go:\n```python\nprint('hi')\n```"
        self.assertEqual(self.agent._extract_code(raw), "print('hi')")

    def test_extract_plain_fenced_block(self):
        raw = "```\nprint('hi')\n```"
        self.assertEqual(self.agent._extract_code(raw), "print('hi')")

    def test_extract_no_fence_returns_stripped_text(self):
        raw = "  print('hi')  "
        self.assertEqual(self.agent._extract_code(raw), "print('hi')")


class TestRunLoop(unittest.TestCase):
    def _agent(self, responses):
        with patch("agent.Anthropic"):
            agent = CodeIterAgent(max_iterations=5, timeout=5)
        agent.client.messages.create = MagicMock(
            side_effect=[fake_response(r) for r in responses]
        )
        return agent

    def test_succeeds_on_first_try(self):
        code = "```python\nprint('hello')\n```"
        agent = self._agent([code])
        result = agent.run("print hello")
        self.assertTrue(result.success)
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(result.attempts[0].reason, "passed")
        self.assertIn("hello", result.attempts[0].stdout)

    def test_fixes_itself_after_crash(self):
        broken = "```python\nprint(undefined_variable)\n```"
        fixed = "```python\nprint('fixed')\n```"
        agent = self._agent([broken, fixed])
        result = agent.run("print something")
        self.assertTrue(result.success)
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.attempts[0].reason, "crashed")
        self.assertFalse(result.attempts[0].success)
        self.assertIn("NameError", result.attempts[0].stderr)
        self.assertEqual(result.attempts[1].reason, "passed")
        self.assertTrue(result.attempts[1].success)

    def test_gives_up_after_max_iterations(self):
        broken = "```python\nraise ValueError('nope')\n```"
        agent = self._agent([broken] * 3)
        agent.max_iterations = 3
        result = agent.run("always fails")
        self.assertFalse(result.success)
        self.assertEqual(len(result.attempts), 3)
        self.assertTrue(all(a.reason == "crashed" for a in result.attempts))

    def test_expected_output_mismatch_triggers_retry(self):
        wrong = "```python\nprint('wrong')\n```"
        right = "```python\nprint('right')\n```"
        agent = self._agent([wrong, right])
        result = agent.run("print right", expected_output="right")
        self.assertTrue(result.success)
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.attempts[0].reason, "wrong_output")
        self.assertFalse(result.attempts[0].success)
        self.assertEqual(result.attempts[1].reason, "passed")

    def test_expected_output_match_succeeds_immediately(self):
        code = "```python\nprint('42')\n```"
        agent = self._agent([code])
        result = agent.run("print the answer", expected_output="42")
        self.assertTrue(result.success)
        self.assertEqual(len(result.attempts), 1)

    def test_timeout_counts_as_failure(self):
        infinite_loop = "```python\nwhile True:\n    pass\n```"
        fixed = "```python\nprint('done')\n```"
        agent = self._agent([infinite_loop, fixed])
        agent.timeout = 1
        result = agent.run("loop forever then fix")
        self.assertTrue(result.success)
        self.assertEqual(len(result.attempts), 2)
        self.assertIn("TimeoutError", result.attempts[0].stderr)
        self.assertEqual(result.attempts[1].reason, "passed")


if __name__ == "__main__":
    unittest.main()
