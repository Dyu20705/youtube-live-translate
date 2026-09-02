"""
Pytest configuration and PYTHONPATH setup for S3 tests.
"""

import sys
from pathlib import Path

POC_DIR = Path(__file__).parent.parent.resolve()
WORKSPACE_DIR = POC_DIR.parent.parent.resolve()
S2_DIR = WORKSPACE_DIR / "poc" / "s2-streaming-asr"

if str(POC_DIR) not in sys.path:
    sys.path.insert(0, str(POC_DIR))

if str(S2_DIR) not in sys.path:
    sys.path.insert(0, str(S2_DIR))
