"""
test_migration.py — Tests for AppSpec 1.0 to 2.0 migration and RFC 6902 JSON Patching.
"""

from __future__ import annotations

from ai_frappe_builder.models import (
    AppSpecV2,
    SpecPatch,
    make_spec_patch,
    migrate_v1_to_v2,
)


def test_migrate_v1_to_v2_basic() -> None:
    v1_dict = {
        "status": "ready",
        "spec_version": "1.0",
        "assumptions": ["Assumed standard currency is USD"],
        "questions": [
            "Do you rent hourly or daily?",
            {"id": "q_insurance", "question": "Include insurance?", "options": ["Yes", "No"]},
        ],
        "app": {
            "app_name": "car-rental",
            "title": "Car Rental System",
            "modules": ["Fleet"],
            "doctypes": [
                {
                    "doctype": "Rental Vehicle",
                    "fields": [
                        {
                            "fieldname": "license_plate",
                            "label": "License Plate",
                            "fieldtype": "Data",
                            "reqd": True,
                        },
                        {"fieldname": "daily_rate", "label": "Daily Rate", "fieldtype": "Currency"},
                    ],
                },
                {
                    "name": "Vehicle Addon Item",
                    "istable": True,
                    "fields": [
                        {"fieldname": "addon_name", "label": "Addon Name", "fieldtype": "Data"},
                        {"fieldname": "rate", "label": "Rate", "fieldtype": "Currency"},
                    ],
                },
            ],
            "workflows": [
                {
                    "name": "Vehicle Approval",
                    "doctype": "Rental Vehicle",
                    "states": [
                        {"state": "Draft", "docs": "Draft"},
                        {"state": "Active", "docs": "Active / Submitted"},
                    ],
                    "transitions": [
                        {
                            "state": "Draft",
                            "action": "Activate",
                            "next_state": "Active",
                            "allow_role": "Fleet Manager",
                        },
                    ],
                }
            ],
        },
    }

    v2 = migrate_v1_to_v2(v1_dict)
    assert isinstance(v2, AppSpecV2)
    assert v2.spec_version == "2.0"
    assert v2.status == "ready"
    assert len(v2.questions) == 2
    assert v2.questions[0].question == "Do you rent hourly or daily?"
    assert len(v2.questions[1].options) == 2

    assert v2.app is not None
    assert v2.app.app_name == "car_rental"  # snake_case normalized
    assert len(v2.app.doctypes) == 2

    vehicle_dt = v2.app.doctypes[0]
    assert vehicle_dt.name == "Rental Vehicle"
    assert vehicle_dt.module == "Fleet"
    assert vehicle_dt.kind.value == "master"

    addon_dt = v2.app.doctypes[1]
    assert addon_dt.name == "Vehicle Addon Item"
    assert addon_dt.istable is True
    assert addon_dt.autoname == "hash"
    assert addon_dt.kind.value == "child"

    wf = v2.app.workflows[0]
    assert wf.document_type == "Rental Vehicle"
    assert wf.states[0].doc_status == 0
    assert wf.states[1].doc_status == 1
    assert wf.transitions[0].allowed == "Fleet Manager"


def test_rfc6902_json_patch_and_diff() -> None:
    initial_spec = {
        "app_name": "car_rental",
        "title": "Car Rental",
        "doctypes": [
            {
                "name": "Vehicle",
                "fields": [
                    {"fieldname": "make", "fieldtype": "Data"},
                ],
            }
        ],
    }

    target_spec = {
        "app_name": "car_rental",
        "title": "Car Rental",
        "doctypes": [
            {
                "name": "Vehicle",
                "fields": [
                    {"fieldname": "make", "fieldtype": "Data"},
                    {"fieldname": "model_year", "fieldtype": "Int"},
                ],
            }
        ],
    }

    patch = make_spec_patch(initial_spec, target_spec, description="Add model_year field")
    assert isinstance(patch, SpecPatch)
    assert len(patch.operations) > 0

    applied = patch.apply(initial_spec)
    assert applied["doctypes"][0]["fields"][1]["fieldname"] == "model_year"
    assert applied == target_spec
