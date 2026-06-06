from __future__ import annotations

import sys


def configure_utf8_stdio() -> None:
    """Windows PowerShell often uses cp1251; force UTF-8 for Cyrillic logs."""
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
