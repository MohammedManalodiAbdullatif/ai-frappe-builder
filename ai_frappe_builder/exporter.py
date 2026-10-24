"""
exporter.py — Backward-compatible wrapper for the canonical FrappeAppExporter.
"""

from ai_frappe_builder.services.exporter import (
    FrappeAppExporter,
    canonical_doctype_json,
    export_app,
)

generate_doctype_json = canonical_doctype_json

__all__ = [
    "FrappeAppExporter",
    "canonical_doctype_json",
    "export_app",
    "generate_doctype_json",
]
