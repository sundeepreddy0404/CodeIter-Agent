"""
CodeIter - a self-debugging code agent.

Given a task description, the agent generates Python code, executes it in a
sandbox, and if it fails, feeds the error back to itself to produce a fix.
Repeats until the code runs successfully or max_iterations is reached.
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are CodeIter, an expert Python coding agent.

Rules:
- Respond with ONLY a single Python code block, nothing else.
- The code must be self-contained and runnable with `python script.py`.
- If given a previous attempt and an error, fix the code to address that
  specific error while still solving the original task.
- Do not explain your reasoning outside the code block.
"""


@dataclass
class Attempt:
    iteration: int
    code: str
    stdout: str
    stderr: str
    success: bool
    reason: str = ""


@dataclass
class Result:
    task: str
    success: bool
    final_code: str
    attempts: list = field(default_factory=list)


class CodeIterAgent:
    def __init__(self, max_iterations: int = 5, timeout: int = 10, api_key: str | None = None):
        self.max_iterations = max_iterations
        self.timeout = timeout
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def _extract_code(self, text: str) -> str:
        if "```python" in text:
            text = text.split("```python", 1)[1]
        elif "```" in text:
            text = text.split("```", 1)[1]
        if "```" in text:
            text = text.split("```", 1)[0]
        return text.strip()

    def _generate(self, messages: list) -> str:
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text

    def _run(self, code: str) -> tuple[str, str, bool]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            path = f.name
        try:
            proc = subprocess.run(
                ["python3", path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            success = proc.returncode == 0
            return proc.stdout, proc.stderr, success
        except subprocess.TimeoutExpired:
            return "", f"TimeoutError: code took longer than {self.timeout}s to run", False
        finally:
            os.unlink(path)

    def run(self, task: str, expected_output: str | None = None) -> Result:
        """Run the write -> run -> fix -> repeat loop for a task.

        If `expected_output` is given, a run that executes without crashing
        is only considered successful if its stdout matches (after
        stripping surrounding whitespace). Otherwise, "no error" counts as
        success.
        """
        messages = [{"role": "user", "content": f"Task: {task}"}]
        attempts = []

        for i in range(1, self.max_iterations + 1):
            raw = self._generate(messages)
            code = self._extract_code(raw)
            stdout, stderr, ran_ok = self._run(code)

            success = ran_ok
            reason = ""
            feedback = ""

            if not ran_ok:
                reason = "crashed"
                feedback = (
                    f"That code failed with this error:\n\n{stderr}\n\n"
                    "Fix the code. Respond with the corrected full script only."
                )
            elif expected_output is not None and stdout.strip() != expected_output.strip():
                success = False
                reason = "wrong_output"
                feedback = (
                    f"The code ran without errors, but the output was incorrect.\n\n"
                    f"Expected output:\n{expected_output.strip()}\n\n"
                    f"Actual output:\n{stdout.strip()}\n\n"
                    "Fix the code so its output matches exactly. "
                    "Respond with the corrected full script only."
                )
            else:
                reason = "passed"

            attempts.append(Attempt(i, code, stdout, stderr, success, reason))

            if success:
                return Result(task=task, success=True, final_code=code, attempts=attempts)

            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": feedback})

        return Result(task=task, success=False, final_code=attempts[-1].code, attempts=attempts)
