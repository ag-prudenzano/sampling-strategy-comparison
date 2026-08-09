from __future__ import annotations

import atexit
from pathlib import Path
import os
import sys


def _should_publish() -> bool:
    if os.environ.get("SKIP_WEBSITE_PUBLISH") == "1":
        return False
    return Path(sys.argv[0]).name == "analysis.py"


def _publish_after_analysis() -> None:
    try:
        from website_publish import publish_website

        publish_website()
    except Exception as exc:
        print(f"Website publishing failed: {exc}", file=sys.stderr)


if _should_publish():
    atexit.register(_publish_after_analysis)
