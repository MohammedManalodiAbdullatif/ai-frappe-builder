import json
from pathlib import Path
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
from ai_frappe_builder.services.exporter import FrappeAppExporter


def test_exporter_workflow_fixtures_and_hooks(tmp_path: Path):
    exporter = FrappeAppExporter(output_root=str(tmp_path))

    spec = AppSpecV2(
        status="ready",
        app=AppMetadata(
            app_name="fleet_rental",
            title="Fleet Rental",
            modules=["Fleet"],
            roles=["Rental Agent", "Fleet Manager"],
            doctypes=[
                DocTypeSpec(
                    name="Rental Agreement",
                    module="Fleet",
                    is_submittable=True,
                    fields=[
                        FieldSpec(fieldname="agreement_no", label="Agreement No", fieldtype="Data"),
                        FieldSpec(fieldname="workflow_state", label="Workflow State", fieldtype="Select", options="Draft\nActive\nClosed", read_only=True, in_list_view=True, in_standard_filter=True, allow_on_submit=True),
                    ],
                    permissions=[
                        PermissionSpec(role="System Manager", read=True, write=True, create=True, delete=True),
                        PermissionSpec(role="Rental Agent", read=True, write=True, create=True, submit=True),
                        PermissionSpec(role="Fleet Manager", read=True, write=True, submit=True),
                    ],
                )
            ],
            workflows=[
                WorkflowSpec(
                    name="Rental Agreement Workflow",
                    document_type="Rental Agreement",
                    workflow_state_field="workflow_state",
                    is_active=1,
                    states=[
                        WorkflowState(state="Draft", doc_status=0, style="", allow_edit="Rental Agent"),
                        WorkflowState(state="Active", doc_status=1, style="Success", allow_edit="Fleet Manager"),
                        WorkflowState(state="Closed", doc_status=1, style="Warning", allow_edit="Fleet Manager"),
                    ],
                    transitions=[
                        WorkflowTransition(state="Draft", action="Activate Agreement", next_state="Active", allowed="Rental Agent"),
                        WorkflowTransition(state="Active", action="Close Agreement", next_state="Closed", allowed="Fleet Manager"),
                    ],
                )
            ],
        ),
    )

    res = exporter.export(spec)
    app_dir = Path(res["app_path"])
    fixtures_dir = app_dir / "fleet_rental" / "fixtures"

    # 1. workflow.json check
    wf_file = fixtures_dir / "workflow.json"
    assert wf_file.is_file()
    wf_content = wf_file.read_text(encoding="utf-8")
    assert wf_content.endswith("\n")
    wf_data = json.loads(wf_content)
    assert len(wf_data) == 1
    wf_doc = wf_data[0]
    assert wf_doc["doctype"] == "Workflow"
    assert wf_doc["workflow_name"] == "Rental Agreement Workflow"
    assert wf_doc["states"][0]["doctype"] == "Workflow Document State"
    assert wf_doc["transitions"][0]["doctype"] == "Workflow Transition"
    # Byte-stable key sorting check
    assert wf_content == json.dumps(wf_data, indent=1, sort_keys=True) + "\n"

    # 2. workflow_state.json check
    ws_file = fixtures_dir / "workflow_state.json"
    assert ws_file.is_file()
    ws_content = ws_file.read_text(encoding="utf-8")
    assert ws_content.endswith("\n")
    ws_data = json.loads(ws_content)
    assert len(ws_data) == 3
    state_names = [s["workflow_state_name"] for s in ws_data]
    assert state_names == ["Active", "Closed", "Draft"]
    assert ws_content == json.dumps(ws_data, indent=1, sort_keys=True) + "\n"

    # 3. workflow_action_master.json check
    act_file = fixtures_dir / "workflow_action_master.json"
    assert act_file.is_file()
    act_content = act_file.read_text(encoding="utf-8")
    assert act_content.endswith("\n")
    act_data = json.loads(act_content)
    assert len(act_data) == 2
    act_names = [a["workflow_action_name"] for a in act_data]
    assert act_names == ["Activate Agreement", "Close Agreement"]
    assert act_content == json.dumps(act_data, indent=1, sort_keys=True) + "\n"

    # 4. role.json check
    role_file = fixtures_dir / "role.json"
    assert role_file.is_file()
    role_content = role_file.read_text(encoding="utf-8")
    assert role_content.endswith("\n")
    role_data = json.loads(role_content)
    role_names = [r["role_name"] for r in role_data]
    assert "Rental Agent" in role_names
    assert "Fleet Manager" in role_names
    assert "System Manager" not in role_names
    assert role_content == json.dumps(role_data, indent=1, sort_keys=True) + "\n"

    # 5. hooks.py check
    hooks_file = app_dir / "fleet_rental" / "hooks.py"
    assert hooks_file.is_file()
    hooks_content = hooks_file.read_text(encoding="utf-8")
    assert '"dt": "Role"' in hooks_content
    assert '"Fleet Manager"' in hooks_content
    assert '"Rental Agent"' in hooks_content
    assert '"dt": "Workflow"' in hooks_content
    assert '"Rental Agreement Workflow"' in hooks_content
    assert '"dt": "Workflow State"' in hooks_content
    assert '"dt": "Workflow Action Master"' in hooks_content

    # 6. test_<doctype>.py workflow transition test check
    test_file = app_dir / "fleet_rental" / "fleet" / "doctype" / "rental_agreement" / "test_rental_agreement.py"
    assert test_file.is_file()
    test_content = test_file.read_text(encoding="utf-8")
    assert "test_workflow_transitions" in test_content
    assert "frappe.model.workflow.apply_workflow" in test_content
    assert "Activate Agreement" in test_content
    assert "docstatus" in test_content
