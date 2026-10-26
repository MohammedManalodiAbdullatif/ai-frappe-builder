import pytest
from ai_frappe_builder.models.app_spec_v2 import (
    AppMetadata,
    AppSpecV2,
    DocTypeSpec,
    FieldSpec,
    PermissionSpec,
    WorkflowSpec,
    WorkflowState,
    WorkflowTransition,
)
from ai_frappe_builder.validator.rule_engine import validate_spec


def make_spec(workflow: WorkflowSpec, is_submittable: bool = True, extra_fields: list[FieldSpec] | None = None, roles: list[str] | None = None, dt_permissions: list[PermissionSpec] | None = None) -> AppSpecV2:
    expected_opts = "\n".join(s.state for s in workflow.states)
    fields = [
        FieldSpec(fieldname="title", label="Title", fieldtype="Data", reqd=True),
        FieldSpec(fieldname="workflow_state", label="Workflow State", fieldtype="Select", options=expected_opts, read_only=True),
    ]
    if extra_fields:
        fields = extra_fields

    perms = dt_permissions or [
        PermissionSpec(role="System Manager", read=True, write=True, create=True, delete=True),
        PermissionSpec(role="Manager", read=True, write=True),
    ]

    dt = DocTypeSpec(
        name="Booking",
        module="Operations",
        is_submittable=is_submittable,
        fields=fields,
        permissions=perms,
    )

    return AppSpecV2(
        status="ready",
        app=AppMetadata(
            app_name="test_app",
            title="Test App",
            modules=["Operations"],
            roles=roles or ["System Manager", "Manager"],
            doctypes=[dt],
            workflows=[workflow],
        )
    )


def test_wf001_unknown_state_in_transition():
    wf = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
        ],
        transitions=[
            WorkflowTransition(state="Draft", action="Approve", next_state="UnknownState", allowed="System Manager"),
        ]
    )
    report = validate_spec(make_spec(wf))
    assert not report.is_valid
    assert any("WF001" in e for e in report.errors)


def test_wf002_initial_state_rules():
    # Two initial states
    wf_multi = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="DraftA", doc_status=0),
            WorkflowState(state="DraftB", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
        ],
        transitions=[
            WorkflowTransition(state="DraftA", action="Approve", next_state="Approved", allowed="System Manager"),
        ]
    )
    report = validate_spec(make_spec(wf_multi))
    assert any("WF002" in e for e in report.errors)

    # Initial state doc_status != 0
    wf_bad_docstatus = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=1),
            WorkflowState(state="Approved", doc_status=1),
        ],
        transitions=[
            WorkflowTransition(state="Draft", action="Approve", next_state="Approved", allowed="System Manager"),
        ]
    )
    report2 = validate_spec(make_spec(wf_bad_docstatus))
    assert any("WF002" in e for e in report2.errors)


def test_wf003_unreachable_state():
    wf = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
            WorkflowState(state="Orphan", doc_status=0),
        ],
        transitions=[
            WorkflowTransition(state="Draft", action="Approve", next_state="Approved", allowed="System Manager"),
        ]
    )
    report = validate_spec(make_spec(wf))
    assert any("WF003" in e for e in report.errors)


def test_wf004_role_must_exist_in_app_roles_and_doctype_permissions():
    wf = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0, allow_edit="Ghost Role"),
            WorkflowState(state="Approved", doc_status=1, allow_edit="System Manager"),
        ],
        transitions=[
            WorkflowTransition(state="Draft", action="Approve", next_state="Approved", allowed="Unknown Role"),
        ]
    )
    report = validate_spec(make_spec(wf))
    assert any("WF004" in e for e in report.errors)


def test_wf005_workflow_state_field_presence_and_properties():
    wf = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
        ],
        transitions=[
            WorkflowTransition(state="Draft", action="Approve", next_state="Approved", allowed="System Manager"),
        ]
    )
    # Missing workflow_state field entirely
    no_field_spec = make_spec(wf, extra_fields=[FieldSpec(fieldname="title", label="Title", fieldtype="Data")])
    report = validate_spec(no_field_spec)
    assert any("WF005" in e for e in report.errors)

    # workflow_state not read_only
    writable_spec = make_spec(wf, extra_fields=[
        FieldSpec(fieldname="workflow_state", label="State", fieldtype="Select", options="Draft\nApproved", read_only=False)
    ])
    report2 = validate_spec(writable_spec)
    assert any("WF005" in e for e in report2.errors)


def test_wf006_doc_status_never_decreases():
    wf = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
            WorkflowState(state="Reverted", doc_status=0),
        ],
        transitions=[
            WorkflowTransition(state="Draft", action="Approve", next_state="Approved", allowed="System Manager"),
            WorkflowTransition(state="Approved", action="Revert", next_state="Reverted", allowed="System Manager"),
        ]
    )
    report = validate_spec(make_spec(wf))
    assert any("WF006" in e for e in report.errors)


def test_wf007_submittable_consistency():
    wf = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
        ],
        transitions=[
            WorkflowTransition(state="Draft", action="Approve", next_state="Approved", allowed="System Manager"),
        ]
    )
    # DocType is_submittable=False but doc_status 1 used
    report = validate_spec(make_spec(wf, is_submittable=False))
    assert any("WF007" in e for e in report.errors)


def test_wf008_single_workflow_per_doctype():
    wf1 = WorkflowSpec(
        name="Booking Workflow 1",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
        ],
        transitions=[
            WorkflowTransition(state="Draft", action="Approve", next_state="Approved", allowed="System Manager"),
        ]
    )
    wf2 = WorkflowSpec(
        name="Booking Workflow 2",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
        ],
        transitions=[
            WorkflowTransition(state="Draft", action="Approve", next_state="Approved", allowed="System Manager"),
        ]
    )
    spec = make_spec(wf1)
    spec.app.workflows.append(wf2)
    report = validate_spec(spec)
    assert any("WF008" in e for e in report.errors)


def test_wf009_duplicate_transitions():
    wf = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
        ],
        transitions=[
            WorkflowTransition(state="Draft", action="Approve", next_state="Approved", allowed="System Manager"),
            WorkflowTransition(state="Draft", action="Approve", next_state="Approved", allowed="Manager"),
        ]
    )
    report = validate_spec(make_spec(wf))
    assert any("WF009" in e for e in report.errors)


def test_wf010_condition_safety():
    wf_valid = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
        ],
        transitions=[
            WorkflowTransition(
                state="Draft", action="Approve", next_state="Approved", allowed="System Manager", condition="doc.grand_total > 100"
            ),
        ]
    )
    assert validate_spec(make_spec(wf_valid)).is_valid

    # Disallowed global (e.g. os.system or import)
    wf_invalid = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
        ],
        transitions=[
            WorkflowTransition(
                state="Draft", action="Approve", next_state="Approved", allowed="System Manager", condition="__import__('os').system('ls')"
            ),
        ]
    )
    report = validate_spec(make_spec(wf_invalid))
    assert any("WF010" in e for e in report.errors)


def test_wf011_select_options_equal_states():
    wf = WorkflowSpec(
        name="Booking Workflow",
        document_type="Booking",
        states=[
            WorkflowState(state="Draft", doc_status=0),
            WorkflowState(state="Approved", doc_status=1),
        ],
        transitions=[
            WorkflowTransition(state="Draft", action="Approve", next_state="Approved", allowed="System Manager"),
        ]
    )
    # Options have extra 'Cancelled'
    spec = make_spec(wf, extra_fields=[
        FieldSpec(fieldname="title", label="Title", fieldtype="Data"),
        FieldSpec(fieldname="workflow_state", label="State", fieldtype="Select", options="Draft\nApproved\nCancelled", read_only=True),
    ])
    report = validate_spec(spec)
    assert any("WF011" in e for e in report.errors)
