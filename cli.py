"""
CLI for CodeIter - shows the write -> run -> fix -> repeat loop live.

Usage:
    python -m codeiter.cli "write a function that parses this CSV: ..."
    python -m codeiter.cli "print the first 10 fibonacci numbers" --expect "0 1 1 2 3 5 8 13 21 34"
"""

import sys
from codeiter.agent import CodeIterAgent


def main():
    if len(sys.argv) < 2:
        print('Usage: python -m codeiter.cli "<task description>" [--expect "<expected output>"]')
        sys.exit(1)

    args = sys.argv[1:]
    expected_output = None
    if "--expect" in args:
        idx = args.index("--expect")
        expected_output = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    task = " ".join(args)
    agent = CodeIterAgent(max_iterations=5)

    print(f"Task: {task}\n")
    result = agent.run(task, expected_output=expected_output)

    for attempt in result.attempts:
        status = "PASSED" if attempt.success else f"FAILED ({attempt.reason})"
        print(f"--- Iteration {attempt.iteration}: {status} ---")
        print(attempt.code)
        if not attempt.success:
            if attempt.reason == "crashed":
                print("\nError:")
                print(attempt.stderr)
            elif attempt.reason == "wrong_output":
                print("\nGot:")
                print(attempt.stdout)
        print()

    if result.success:
        print(f"Solved in {len(result.attempts)} iteration(s).")
    else:
        print(f"Did not pass after {len(result.attempts)} iterations.")


if __name__ == "__main__":
    main()
