"""
report_builder.py — Script reports, metrics, charts, and Workspace JSON generator.
"""

from __future__ import annotations

import json
from typing import Any

from ai_frappe_builder.models.app_spec_v2 import (
    DashboardChartSpec,
    NumberCardSpec,
    ReportSpec,
    WorkspaceSpec,
)


class ReportBuilder:
    """Emits Frappe Script Reports, Query Reports, Dashboards, and Workspaces."""

    def generate_script_report_files(self, report: ReportSpec) -> dict[str, str]:
        """
        Generate .json, .py, and .js bundle for a Frappe Script Report.
        """
        json_meta = {
            "doctype": "Report",
            "name": report.name,
            "report_name": report.name,
            "report_type": report.report_type,
            "ref_doctype": report.ref_doctype,
            "is_standard": "Yes",
            "module": "Custom",
            "columns": report.columns,
            "filters": report.filters,
        }

        # Python execution script
        py_code = [
            "# Copyright (c) 2026, Frappe Builder and contributors",
            "# For license information, please see license.txt",
            "",
            "import frappe",
            "",
            "",
            "def execute(filters=None):",
            "    columns = get_columns()",
            "    data = get_data(filters)",
            "    return columns, data",
            "",
            "",
            "def get_columns():",
            f"    return {json.dumps(report.columns, indent=8)}",
            "",
            "",
            "def get_data(filters):",
            f'    return frappe.get_all("{report.ref_doctype}", fields=["*"], limit=100)',
            "",
        ]

        # JS filter script
        js_code = [
            "// Copyright (c) 2026, Frappe Builder and contributors",
            f"frappe.query_reports['{report.name}'] = {{",
            "    filters: [",
            "        // Report filters",
            "    ]",
            "};",
            "",
        ]

        return {
            f"{report.name}.json": json.dumps(json_meta, indent=1),
            f"{report.name}.py": "\n".join(py_code),
            f"{report.name}.js": "\n".join(js_code),
        }

    def generate_workspace_json(self, workspace: WorkspaceSpec) -> str:
        """
        Generate Workspace JSON matching Frappe Desk v15 layout.
        """
        ws_dict: dict[str, Any] = {
            "doctype": "Workspace",
            "name": workspace.name,
            "label": workspace.label,
            "title": workspace.title,
            "module": workspace.module,
            "icon": workspace.icon,
            "is_standard": 1,
            "public": 1,
            "shortcuts": [
                {
                    "label": s.label,
                    "type": s.type,
                    "link_to": s.link_to,
                }
                for s in workspace.shortcuts
            ],
            "links": [
                {
                    "label": lnk.label,
                    "link_to": lnk.link_to,
                    "link_type": lnk.link_type,
                }
                for lnk in workspace.links
            ],
            "charts": [{"chart_name": c} for c in workspace.charts],
            "number_cards": [{"number_card_name": nc} for nc in workspace.number_cards],
        }
        return json.dumps(ws_dict, indent=1)

    def generate_number_card_json(self, card: NumberCardSpec) -> str:
        """
        Generate Desk Number Card metric JSON.
        """
        card_dict = {
            "doctype": "Number Card",
            "name": card.name,
            "label": card.label,
            "document_type": card.document_type,
            "function": card.function,
            "aggregate_function_based_on": card.aggregate_function_based_on,
            "filters_json": card.filters_json,
            "is_standard": 1,
        }
        return json.dumps(card_dict, indent=1)

    def generate_dashboard_chart_json(self, chart: DashboardChartSpec) -> str:
        """
        Generate Desk Dashboard Chart JSON.
        """
        chart_dict = {
            "doctype": "Dashboard Chart",
            "chart_name": chart.chart_name,
            "chart_type": chart.chart_type,
            "document_type": chart.document_type,
            "based_on": chart.based_on,
            "value_based_on": chart.value_based_on,
            "group_by_type": chart.group_by_type,
            "is_standard": 1,
        }
        return json.dumps(chart_dict, indent=1)
