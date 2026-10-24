"""
ai_frappe_builder — Multi-agent AI-driven Frappe/ERPNext application generator.
"""

import sys
from pathlib import Path

_pkg_dir = str(Path(__file__).resolve().parent)
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

__version__ = "2.0.0"
