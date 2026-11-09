"""Command line: python ask.py "Which category had the highest gross margin in 2025?" """
import sys

from analyst import Analyst
from analyst.llm import default_llm


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    res = Analyst(default_llm()).ask(" ".join(sys.argv[1:]))
    if not res.ok:
        print(f"Couldn't answer: {res.error}")
        sys.exit(2)
    print(res.answer, "\n")
    if res.assumption:
        print(f"Assumption: {res.assumption}\n")
    print(res.data.head(15).to_string(index=False), "\n")
    print("SQL:\n" + res.sql)


if __name__ == "__main__":
    main()
