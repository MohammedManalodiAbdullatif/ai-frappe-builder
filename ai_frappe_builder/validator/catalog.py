"""
catalog.py — Knowledge base loader and cache for Frappe validator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

_CACHE: dict[str, Any] = {}

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge"


def _load_yaml(filename: str) -> dict[str, Any]:
    if filename in _CACHE:
        return cast(dict[str, Any], _CACHE[filename])
    path = KNOWLEDGE_DIR / filename
    if not path.is_file():
        # Fallback to local package directory if deployed as standalone package
        path = Path(__file__).resolve().parent / "knowledge" / filename
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    result = data if isinstance(data, dict) else {}
    _CACHE[filename] = result
    return result


def get_fieldtypes_catalog() -> dict[str, Any]:
    data = _load_yaml("fieldtypes.yaml")
    res = data.get("fieldtypes", {})
    return res if isinstance(res, dict) else {}


def get_erpnext_doctypes_catalog() -> dict[str, Any]:
    data = _load_yaml("erpnext_doctypes.yaml")
    res = data.get("standard_doctypes", {})
    return res if isinstance(res, dict) else {}


def get_conventions_catalog() -> dict[str, Any]:
    return _load_yaml("conventions.yaml")


def get_standard_doctype_names() -> set[str]:
    core_builtin = {
        "User",
        "Role",
        "DocType",
        "Module Def",
        "File",
        "Communication",
        "Activity Log",
        "Workflow",
        "Workflow State",
        "Workflow Action Master",
        "Report",
        "Page",
        "Print Format",
        "Custom Field",
        "Property Setter",
        "Workspace",
        "Number Card",
        "Dashboard Chart",
    }
    catalog = get_erpnext_doctypes_catalog()
    return core_builtin | set(catalog.keys())


def get_reserved_fieldnames() -> set[str]:
    conv = get_conventions_catalog()
    names = conv.get("reserved_fieldnames", [])
    if not names:
        return {
            "name",
            "owner",
            "creation",
            "modified",
            "modified_by",
            "docstatus",
            "idx",
            "parent",
            "parentfield",
            "parenttype",
            "doctype",
            "_user_tags",
            "_comments",
            "_assign",
            "_liked_by",
        }
    return set(names)
