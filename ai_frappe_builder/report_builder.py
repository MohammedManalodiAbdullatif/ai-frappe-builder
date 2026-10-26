"""
report_builder.py — Creates Frappe Reports, Number Cards, Dashboard Charts, and Dashboards.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from frappe_client import FrappeClient

logger = logging.getLogger(__name__)


async def create_report(spec: dict[str, Any], frappe_client: FrappeClient) -> dict:
    """
    Create a Frappe Report record.

    spec format:
    {
        "name": "Fleet Utilisation",
        "ref_doctype": "Rental Agreement",
        "report_type": "Script Report",  # or "Query Report"
        "columns": [...],
        "filters": [...],
        "script": "...",
        "query": "..."
    }
    """
    payload: dict[str, Any] = {
        "doctype": "Report",
        "name": spec["name"],
        "report_name": spec["name"],
        "ref_doctype": spec.get("ref_doctype") or spec.get("doctype"),
        "report_type": spec.get("report_type", "Script Report"),
        "is_standard": "No",
    }
    if "columns" in spec:
        payload["columns"] = spec["columns"] if isinstance(spec["columns"], str) else json.dumps(spec["columns"])
    if "filters" in spec:
        payload["filters"] = spec["filters"] if isinstance(spec["filters"], str) else json.dumps(spec["filters"])
    if spec.get("script"):
        payload["script"] = spec["script"]
    if spec.get("query"):
        payload["query"] = spec["query"]

    return await frappe_client.post("/api/resource/Report", payload)


async def create_number_card(spec: dict[str, Any], frappe_client: FrappeClient) -> dict:
    """
    Create a Frappe Number Card.
    spec: {
        "name": "Vehicles Out",
        "document_type": "Rental Agreement",
        "function": "Count",
        "filters_json": "[...]",
        "label": "Vehicles Out"
    }
    """
    filters_val = spec.get("filters_json", "[]")
    if not isinstance(filters_val, str):
        filters_val = json.dumps(filters_val)

    payload = {
        "doctype": "Number Card",
        "name": spec["name"],
        "label": spec.get("label", spec["name"]),
        "document_type": spec.get("document_type", ""),
        "function": spec.get("function", "Count"),
        "filters_json": filters_val,
        "color": spec.get("color", "#5e64ff"),
    }
    return await frappe_client.post("/api/resource/Number Card", payload)


async def create_dashboard_chart(spec: dict[str, Any], frappe_client: FrappeClient) -> dict:
    """
    Create a Frappe Dashboard Chart.
    """
    filters_val = spec.get("filters_json", "[]")
    if not isinstance(filters_val, str):
        filters_val = json.dumps(filters_val)

    payload = {
        "doctype": "Dashboard Chart",
        "name": spec["name"],
        "chart_name": spec["name"],
        "document_type": spec.get("document_type", ""),
        "chart_type": spec.get("chart_type", "Count"),
        "type": spec.get("type", "Bar"),
        "based_on": spec.get("based_on", "creation"),
        "timeseries": 1 if spec.get("timeseries", True) else 0,
        "filters_json": filters_val,
    }
    return await frappe_client.post("/api/resource/Dashboard Chart", payload)


async def create_dashboard(spec: dict[str, Any], frappe_client: FrappeClient) -> dict:
    """
    Create a full Frappe Dashboard with cards and charts.
    """
    cards_payload = [
        {"card": c.get("card", c.get("name"))}
        for c in spec.get("cards", [])
    ]
    charts_payload = [
        {"chart": c.get("chart", c.get("name"))}
        for c in spec.get("charts", [])
    ]

    payload = {
        "doctype": "Dashboard",
        "name": spec["name"],
        "dashboard_name": spec["name"],
        "module": spec.get("module", ""),
        "is_default": 0,
        "cards": cards_payload,
        "charts": charts_payload,
    }
    return await frappe_client.post("/api/resource/Dashboard", payload)


async def build_reports_and_dashboard(app_spec_app: dict[str, Any], frappe_client: FrappeClient) -> dict[str, Any]:
    """
    Build all reports and dashboard from the app spec's reports/dashboard section.
    """
    results: dict[str, Any] = {"reports": [], "dashboard": None, "errors": []}

    # Reports
    for report_spec in app_spec_app.get("reports", []):
        name = report_spec.get("name", "Unknown Report")
        try:
            await create_report(report_spec, frappe_client)
            results["reports"].append(name)
            logger.info("Created report: %s", name)
        except Exception as exc:
            msg = f"Report '{name}': {exc}"
            logger.warning(msg)
            results["errors"].append(msg)

    # Dashboard & widgets
    dashboard_spec = app_spec_app.get("dashboard")
    if isinstance(dashboard_spec, dict) and dashboard_spec:
        # Create number cards first
        for card in dashboard_spec.get("number_cards", []):
            card_name = card.get("name", "Card")
            try:
                await create_number_card(card, frappe_client)
                logger.info("Created number card: %s", card_name)
            except Exception as exc:
                msg = f"Number card '{card_name}': {exc}"
                logger.warning(msg)
                results["errors"].append(msg)

        # Create charts
        for chart in dashboard_spec.get("charts", []):
            chart_name = chart.get("name", "Chart")
            try:
                await create_dashboard_chart(chart, frappe_client)
                logger.info("Created chart: %s", chart_name)
            except Exception as exc:
                msg = f"Dashboard chart '{chart_name}': {exc}"
                logger.warning(msg)
                results["errors"].append(msg)

        # Create dashboard container
        dash_name = dashboard_spec.get("name", "Main Dashboard")
        try:
            await create_dashboard(dashboard_spec, frappe_client)
            results["dashboard"] = dash_name
            logger.info("Created dashboard: %s", dash_name)
        except Exception as exc:
            msg = f"Dashboard '{dash_name}': {exc}"
            logger.warning(msg)
            results["errors"].append(msg)

    return results
