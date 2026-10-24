"""
test_knowledge.py — Unit tests verifying knowledge base catalogs.
"""

from __future__ import annotations

from ai_frappe_builder.validator.catalog import (
    get_conventions_catalog,
    get_erpnext_doctypes_catalog,
    get_fieldtypes_catalog,
    get_reserved_fieldnames,
    get_standard_doctype_names,
)


def test_fieldtypes_catalog_completeness() -> None:
    catalog = get_fieldtypes_catalog()
    assert len(catalog) >= 30, f"Expected at least 30 fieldtypes, got {len(catalog)}"

    required_types = [
        "Data",
        "Link",
        "Dynamic Link",
        "Table",
        "Table MultiSelect",
        "Select",
        "Currency",
        "Float",
        "Int",
        "Check",
        "Date",
        "Datetime",
        "Section Break",
        "Column Break",
        "Tab Break",
    ]
    for rtype in required_types:
        assert rtype in catalog, f"Missing core fieldtype {rtype}"
        info = catalog[rtype]
        assert "category" in info
        assert "description" in info


def test_erpnext_doctypes_catalog() -> None:
    catalog = get_erpnext_doctypes_catalog()
    assert len(catalog) >= 20, f"Expected at least 20 standard doctypes, got {len(catalog)}"

    for dt_name in ["Customer", "Supplier", "Item", "Company", "Sales Invoice", "User"]:
        assert dt_name in catalog, f"Missing standard ERPNext entity {dt_name}"
        data = catalog[dt_name]
        assert "module" in data
        assert "standard_fields" in data
        assert len(data["standard_fields"]) > 0


def test_conventions_catalog() -> None:
    conventions = get_conventions_catalog()
    assert "naming_conventions" in conventions
    assert "autoname_patterns" in conventions
    assert "reserved_fieldnames" in conventions

    reserved = get_reserved_fieldnames()
    assert "name" in reserved
    assert "docstatus" in reserved
    assert "creation" in reserved
    assert "modified" in reserved


def test_standard_doctype_names_lookup() -> None:
    names = get_standard_doctype_names()
    assert "Customer" in names
    assert "User" in names
    assert "DocType" in names
    assert "Workflow" in names
