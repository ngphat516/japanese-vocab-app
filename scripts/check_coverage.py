"""Enforce 70% for every implemented service and the NLP package as a whole."""

import json
import sys
from pathlib import Path


def check(path):
    files = json.loads(Path(path).read_text(encoding="utf-8"))["files"]
    services = []
    nlp = []
    for name, data in files.items():
        name = name.replace("\\", "/")
        if (
            name.startswith("app/modules/")
            and name.endswith("/service.py")
            and data["summary"]["num_statements"]
        ):
            services.append((name, data["summary"]["percent_covered"]))
        if name.startswith("app/nlp/"):
            nlp.append(data["summary"])
    total = sum(x["num_statements"] for x in nlp)
    covered = sum(x["covered_lines"] for x in nlp)
    if total:
        services.append(("app/nlp/", covered / total * 100))
    failures = [f"{name}: {value:.1f}%" for name, value in services if value < 70]
    expected = {
        f"app/modules/{name}/service.py"
        for name in ["auth", "dictionary", "textbooks", "imports", "search"]
    }
    missing = expected - {name for name, _ in services}
    failures.extend(f"{name}: missing" for name in sorted(missing))
    if not services or not nlp or failures:
        raise SystemExit("Coverage check failed: " + ", ".join(failures or ["missing coverage"]))
    print("\n".join(f"{name}: {value:.1f}%" for name, value in services))


if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else "coverage.json")
