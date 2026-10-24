"""
run_tests.py — Verify created DocTypes by inserting, validating, and cleaning up a test record.
"""

from __future__ import annotations

import logging
from typing import Any

from frappe_client import FrappeClient

logger = logging.getLogger(__name__)


async def run_tests(
    doctype_name: str,
    frappe_client: FrappeClient,
    sample_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Test a DocType by:
      1. Inserting a test document
      2. Checking it was created with a valid name
      3. Deleting it (cleanup)

    Returns:
      {"passed": bool, "error": str | None, "doc_name": str | None}
    """
    payload = {"doctype": doctype_name, **(sample_fields or {})}
    try:
        created = await frappe_client.create_document(doctype_name, payload)
        doc_name = (
            created.get("data", {}).get("name")
            or created.get("name")
            or (created if isinstance(created, str) else None)
        )
        if doc_name:
            # Cleanup - delete the test record
            try:
                await frappe_client.delete(f"/api/resource/{doctype_name}/{doc_name}")
            except Exception as del_exc:
                logger.debug("Cleanup delete failed (non-fatal): %s", del_exc)

            return {"passed": True, "error": None, "doc_name": str(doc_name)}
        else:
            return {"passed": False, "error": "No name returned from insert", "doc_name": None}
    except Exception as exc:
        return {"passed": False, "error": str(exc), "doc_name": None}


async def run_all_tests(
    doctypes: list[str],
    frappe_client: FrappeClient,
) -> dict[str, Any]:
    """
    Run tests for a list of DocTypes. Returns summary of pass/fail.
    """
    results: dict[str, Any] = {}
    for dt in doctypes:
        result = await run_tests(dt, frappe_client)
        results[dt] = result
        if result["passed"]:
            logger.info("Test passed for DocType: %s", dt)
        else:
            logger.warning("Test failed for DocType '%s': %s", dt, result["error"])

    passed = sum(1 for r in results.values() if r.get("passed"))
    failed = len(doctypes) - passed
    return {
        "total": len(doctypes),
        "passed": passed,
        "failed": failed,
        "results": results,
    }
