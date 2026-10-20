"""Dedicated single-process uvicorn probe with Sudachi explicitly loaded."""

import argparse
import os
from pathlib import Path

import uvicorn

from app.nlp.tokenizer import tokenize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--pid-file", type=Path)
    args = parser.parse_args()
    tokenize("緊張して")
    if args.pid_file:
        args.pid_file.write_text(str(os.getpid()), encoding="ascii")
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
