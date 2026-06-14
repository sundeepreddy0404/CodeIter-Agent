"""
Example tasks for demoing CodeIter.

Run any of these with:
    python -m codeiter.cli "<task>" [--expect "<expected output>"]

These are picked because a naive single-shot LLM response is likely to
get them slightly wrong on the first try (off-by-one, wrong type, edge
case), giving the self-correction loop something real to do.
"""

EXAMPLES = [
    {
        "task": "Write a function fib(n) that returns the nth Fibonacci "
                "number (0-indexed, fib(0)=0, fib(1)=1) using memoization. "
                "Then print fib(20).",
        "expect": "6765",
    },
    {
        "task": "Parse this messy CSV-like string into rows of dicts and "
                "print the result: "
                "'name,age,city\\nAlice, 30 ,NY\\nBob,25,  LA  \\n,40,Chicago' "
                "(handle the missing name and strip whitespace from values).",
        "expect": None,  # open-ended, good for showing the crash-and-fix loop
    },
    {
        "task": "Write a function that takes a list of file paths like "
                "['/a/b/c.txt', '/a/b/d.csv', '/a/e.txt'] and returns a dict "
                "counting how many files have each extension. Print the "
                "result for that exact list.",
        "expect": "{'.txt': 2, '.csv': 1}",
    },
    {
        "task": "Write a function that flattens an arbitrarily nested list, "
                "e.g. [1, [2, [3, 4], 5], 6], using recursion. Print the "
                "flattened result for that exact input.",
        "expect": "[1, 2, 3, 4, 5, 6]",
    },
]


if __name__ == "__main__":
    for ex in EXAMPLES:
        print(ex["task"])
        print(f"  expect: {ex['expect']}")
        print()
