"""
test_golden_exports.py — Comprehensive verification of 5 golden app archetypes:
Car Rental, B2B Wholesale, Medical Clinic, School Academy, and Field Service.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from ai_frappe_builder.models.migration import migrate_v1_to_v2
from ai_frappe_builder.services.exporter import FrappeAppExporter
from ai_frappe_builder.validator.rule_engine import validate_spec

GOLDEN_DIR = Path(__file__).resolve().parent

ARCHETYPES = [
    "car_rental.json",
    "b2b_wholesale.json",
    "medical_clinic.json",
    "school_academy.json",
    "field_service.json",
]


@pytest.mark.parametrize("filename", ARCHETYPES)
def test_golden_spec_validity_and_export(filename: str, tmp_path: Path) -> None:
    file_path = GOLDEN_DIR / filename
    assert file_path.is_file(), f"Missing golden spec file: {filename}"

    with open(file_path, encoding="utf-8") as f:
        raw_dict = json.load(f)

    spec = migrate_v1_to_v2(raw_dict)
    assert spec.status == "ready"
    assert spec.app is not None

    # Step 1: Deterministic Schema Validation
    report = validate_spec(spec)
    assert report.is_valid is True, (
        f"Golden spec {filename} failed validation with errors: {report.errors}"
    )
    assert len(report.errors) == 0

    # Step 2: Canonical App Export
    exporter = FrappeAppExporter(output_root=str(tmp_path))
    export_result = exporter.export(spec)

    app_name = export_result["app_name"]
    app_dir = Path(export_result["app_path"])
    zip_path = Path(export_result["zip_path"])

    assert app_dir.is_dir(), f"Export directory {app_dir} does not exist"
    assert zip_path.is_file(), f"Zip bundle {zip_path} does not exist"
    assert zip_path.stat().st_size > 500

    # Step 3: Verify Canonical Root Files
    expected_root_files = [
        "pyproject.toml",
        "README.md",
        "license.txt",
        ".gitignore",
        ".pre-commit-config.yaml",
    ]
    for rf in expected_root_files:
        assert (app_dir / rf).is_file(), f"Missing root file: {rf}"

    # Step 4: Verify Canonical Package Structure
    expected_package_files = [
        f"{app_name}/__init__.py",
        f"{app_name}/hooks.py",
        f"{app_name}/modules.txt",
        f"{app_name}/patches.txt",
        f"{app_name}/install.py",
        f"{app_name}/uninstall.py",
        f"{app_name}/api.py",
        f"{app_name}/tasks.py",
        f"{app_name}/utils.py",
        f"{app_name}/fixtures/role.json",
        f"{app_name}/fixtures/workflow.json",
    ]
    for pf in expected_package_files:
        assert (app_dir / pf).is_file(), f"Missing package file: {pf}"

    # Step 5: Verify All Generated DocTypes
    for dt in spec.app.doctypes:
        dt_snake = dt.name.lower().replace(" ", "_")
        module_snake = (dt.module or "custom").lower().replace(" ", "_")
        dt_dir = app_dir / app_name / module_snake / "doctype" / dt_snake

        json_file = dt_dir / f"{dt_snake}.json"
        py_file = dt_dir / f"{dt_snake}.py"
        js_file = dt_dir / f"{dt_snake}.js"
        test_file = dt_dir / f"test_{dt_snake}.py"

        assert json_file.is_file(), f"Missing DocType JSON: {json_file}"
        assert py_file.is_file(), f"Missing DocType controller: {py_file}"
        assert js_file.is_file(), f"Missing DocType client script: {js_file}"
        assert test_file.is_file(), f"Missing DocType test: {test_file}"

        # JSON load check
        with open(json_file, encoding="utf-8") as jf:
            dt_data = json.load(jf)
            assert dt_data.get("name") == dt.name
            assert dt_data.get("doctype") == "DocType"

        # AST compile check
        with open(py_file, encoding="utf-8") as pf:
            ast.parse(pf.read())

        with open(test_file, encoding="utf-8") as tf:
            ast.parse(tf.read())

    # Step 6: Verify Package Integrity Self-Tests
    test_integrity_file = app_dir / "tests" / "test_package_integrity.py"
    assert test_integrity_file.is_file()
    with open(test_integrity_file, encoding="utf-8") as tif:
        ast.parse(tif.read())

    # Step 7: Verify Hierarchy Tree API
    tree = exporter.get_file_tree(app_name)
    assert tree["name"] == app_name
    assert tree["is_dir"] is True
    assert len(tree["children"]) > 0

    # Step 8: Verify File Content Retrieval API
    readme_content = exporter.read_exported_file(app_name, "README.md")
    assert spec.app.title in readme_content
