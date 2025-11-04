"""Pytest configuration: ensure project src/ is importable and load .env."""
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # allow `import src...`
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))   # also allow direct modules if needed

if load_dotenv:
    # Load .env at project root
    load_dotenv(dotenv_path=ROOT / ".env", override=False)
