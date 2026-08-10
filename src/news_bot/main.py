from __future__ import annotations

import os

from dotenv import load_dotenv

from .pipeline import run_news_pipeline


def main() -> None:
    load_dotenv()
    result = run_news_pipeline()
    print(result.raw)


if __name__ == "__main__":
    main()

