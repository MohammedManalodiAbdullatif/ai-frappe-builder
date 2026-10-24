"""
validator.py — Pure-Python validation of an AppSpec before applying it.

validate(spec, site_context) -> (is_valid, messages)

  is_valid  — False if ANY error is found; warnings don't flip the flag.
  messages  — list of strings, prefixed with "ERROR:" or "WARNING:"
"""

from __future__ import annotations

import re

from models import AppSpec, DocTypeSpec

# ---------------------------------------------------------------------------
# Reserved field names that Frappe uses internally
# ---------------------------------------------------------------------------

RESERVED_FIELDNAMES = {
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

# Standard built-in Frappe & ERPNext DocTypes that can be linked to freely
STANDARD_CORE_DOCTYPES = {
    # Core Frappe
    "User", "Role", "DocType", "Module Def", "File", "Communication", "Activity Log",
    "Workflow", "Workflow State", "Workflow Action Master", "Report", "Page", "Print Format",
    # Core ERPNext
    "Customer", "Supplier", "Company", "Item", "Item Group", "Customer Group",
    "Supplier Group", "Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry",
    "Sales Order", "Purchase Order", "Delivery Note", "Purchase Receipt", "Quotation",
    "Warehouse", "Cost Center", "Account", "Currency", "Currency Exchange",
    "Address", "Contact", "Territory", "Price List", "Item Price", "Serial No", "Batch",
    "Employee", "Department", "Designation", "Branch", "Terms and Conditions", "Project",
    "Task", "Asset", "Asset Category", "Stock Entry", "Mode of Payment", "UOM",
}

NAMING_SERIES_PATTERN = re.compile(r"^[A-Z]{2,10}(-\..*)?-\.##+$")

MAX_FIELDS = 40


def validate(spec: AppSpec, site_context: dict) -> tuple[bool, list[str]]:
    """
    Validate an AppSpec against Frappe rules and the live site context.

    Parameters
    ----------
    spec          The AppSpec produced by the planner.
    site_context  Dict with keys: doctypes, modules, roles, installed_apps
                  (as returned by FrappeClient.introspect_site).

    Returns
    -------
    (is_valid, messages)
    """
    messages: list[str] = []
    has_error = False

    if spec.status != "ready" or spec.app is None:
        messages.append("ERROR: Spec status is not 'ready' — nothing to validate.")
        return False, messages

    # Build lookup sets from site context
    site_doctype_names: set[str] = {
        dt["name"] for dt in site_context.get("doctypes", [])
    }
    site_roles: set[str] = set(site_context.get("roles", []))

    # Parse doctypes from spec
    try:
        doctypes: list[DocTypeSpec] = spec.get_doctypes()
    except Exception as exc:
        messages.append(f"ERROR: Could not parse doctypes from spec — {exc}")
        return False, messages

    spec_doctype_names: set[str] = {dt.name for dt in doctypes}
    child_doctype_names: set[str] = {dt.name for dt in doctypes if dt.istable}
    all_known_doctypes = site_doctype_names | spec_doctype_names | STANDARD_CORE_DOCTYPES

    def error(msg: str) -> None:
        nonlocal has_error
        has_error = True
        messages.append(f"ERROR: {msg}")

    def warning(msg: str) -> None:
        messages.append(f"WARNING: {msg}")

    # -------------------------------------------------------------------
    # Rule 1 — Title Case names
    # -------------------------------------------------------------------
    for dt in doctypes:
        words = dt.name.split()
        bad_words = [w for w in words if w and not w[0].isupper()]
        if bad_words:
            error(
                f"DocType '{dt.name}' is not Title Case "
                f"(bad words: {bad_words})"
            )

    # -------------------------------------------------------------------
    # Rule 2 — No reserved field names
    # -------------------------------------------------------------------
    for dt in doctypes:
        for field in dt.fields:
            if field.fieldname in RESERVED_FIELDNAMES:
                error(
                    f"DocType '{dt.name}' field '{field.fieldname}' "
                    f"uses a reserved Frappe fieldname."
                )

    # -------------------------------------------------------------------
    # Rule 3 — Link fields reference known DocTypes
    # -------------------------------------------------------------------
    for dt in doctypes:
        for field in dt.fields:
            if field.fieldtype == "Link":
                if not field.options:
                    error(
                        f"DocType '{dt.name}' field '{field.fieldname}' "
                        f"is a Link but has no options (target DocType)."
                    )
                elif field.options not in all_known_doctypes:
                    error(
                        f"DocType '{dt.name}' field '{field.fieldname}' "
                        f"links to unknown DocType '{field.options}'."
                    )

    # -------------------------------------------------------------------
    # Rule 4 — Table fields reference child DocTypes
    # -------------------------------------------------------------------
    for dt in doctypes:
        for field in dt.fields:
            if field.fieldtype in ("Table", "Table MultiSelect"):
                if not field.options:
                    error(
                        f"DocType '{dt.name}' field '{field.fieldname}' "
                        f"is a Table but has no options (child DocType)."
                    )
                elif field.options not in child_doctype_names:
                    error(
                        f"DocType '{dt.name}' field '{field.fieldname}' "
                        f"references '{field.options}' which either doesn't "
                        f"exist in spec or doesn't have istable: true."
                    )

    # -------------------------------------------------------------------
    # Rule 5 — Child tables have no permissions and autoname == hash
    # -------------------------------------------------------------------
    for dt in doctypes:
        if dt.istable:
            if dt.permissions:
                error(
                    f"Child DocType '{dt.name}' must NOT have permissions rows."
                )
            if dt.autoname.lower() != "hash":
                error(
                    f"Child DocType '{dt.name}' autoname must be 'hash', "
                    f"got '{dt.autoname}'."
                )

    # -------------------------------------------------------------------
    # Rule 6 — Non-child DocTypes must have autoname and permissions
    # -------------------------------------------------------------------
    for dt in doctypes:
        if not dt.istable:
            if not dt.autoname:
                error(f"DocType '{dt.name}' missing autoname.")
            if not dt.permissions and not dt.is_single:
                error(
                    f"DocType '{dt.name}' has no permissions rows. "
                    f"At minimum System Manager must be included."
                )

    # -------------------------------------------------------------------
    # Rule 7 — naming_series autoname format
    # -------------------------------------------------------------------
    for dt in doctypes:
        if dt.autoname.startswith("naming_series:"):
            opts = dt.naming_series_options or ""
            # Each line should match the pattern
            for line in opts.strip().splitlines():
                line = line.strip()
                if line and not NAMING_SERIES_PATTERN.match(line):
                    warning(
                        f"DocType '{dt.name}' naming_series_options line "
                        f"'{line}' doesn't match expected pattern "
                        f"(e.g. 'RA-.YYYY.-.#####')."
                    )

    # -------------------------------------------------------------------
    # Rule 8 — Workflows: at least 2 states and 1 transition
    # -------------------------------------------------------------------
    try:
        workflows = spec.get_workflows()
    except Exception as exc:
        error(f"Could not parse workflows — {exc}")
        workflows = []

    for wf in workflows:
        if len(wf.states) < 2:
            error(
                f"Workflow '{wf.name}' must have at least 2 states, "
                f"got {len(wf.states)}."
            )
        if len(wf.transitions) < 1:
            error(
                f"Workflow '{wf.name}' must have at least 1 transition, "
                f"got {len(wf.transitions)}."
            )

    # -------------------------------------------------------------------
    # Rule 9 — Workflow doc_status values are 0, 1, or 2
    # -------------------------------------------------------------------
    for wf in workflows:
        for state in wf.states:
            if state.doc_status not in (0, 1, 2):
                error(
                    f"Workflow '{wf.name}' state '{state.state}' has "
                    f"invalid doc_status {state.doc_status} (must be 0, 1, or 2)."
                )

    # -------------------------------------------------------------------
    # Rule 10 — System Manager always has full permissions
    # -------------------------------------------------------------------
    for dt in doctypes:
        if dt.istable:
            continue
        sm_rows = [p for p in dt.permissions if p.role == "System Manager"]
        if not sm_rows:
            error(
                f"DocType '{dt.name}' is missing a 'System Manager' permission row."
            )
        else:
            sm = sm_rows[0]
            missing = []
            for attr in ("read", "write", "create", "delete"):
                if not getattr(sm, attr):
                    missing.append(attr)
            if missing:
                error(
                    f"DocType '{dt.name}' System Manager permission row "
                    f"is missing: {missing}."
                )

    # -------------------------------------------------------------------
    # Rule 11 — No DocType over 40 fields (warning)
    # -------------------------------------------------------------------
    for dt in doctypes:
        real_fields = [
            f for f in dt.fields
            if f.fieldtype not in ("Section Break", "Column Break", "Tab Break", "Heading", "Fold")
        ]
        if len(real_fields) > MAX_FIELDS:
            warning(
                f"DocType '{dt.name}' has {len(real_fields)} data fields "
                f"(recommended max is {MAX_FIELDS}). Consider splitting."
            )

    # -------------------------------------------------------------------
    # Rule 12 — Every child DocType referenced in Table fields has istable: true
    #           (redundant with Rule 4 but explicit cross-check)
    # -------------------------------------------------------------------
    for dt in doctypes:
        for field in dt.fields:
            if field.fieldtype in ("Table", "Table MultiSelect") and field.options:
                target = next(
                    (d for d in doctypes if d.name == field.options), None
                )
                if target and not target.istable:
                    error(
                        f"DocType '{dt.name}' field '{field.fieldname}' "
                        f"references '{field.options}' but it does NOT have "
                        f"istable: true."
                    )

    is_valid = not has_error
    return is_valid, messages


async def validate_with_jev(spec: AppSpec, site_context: dict) -> tuple[bool, list[str], str]:
    """
    Combined validation:
      1. Deterministic Python hard rules (Rule 1 - 12)
      2. Jev decision gate (fuzzy duplicate checks, readiness score)

    Returns:
      (is_valid, messages, readiness_score)
    """
    import decide

    is_valid, messages = validate(spec, site_context)
    readiness_score = "Unusable"

    if spec.status == "ready" and spec.app:
        try:
            jev_eval = await decide.judge_spec_gate(spec.app, site_context)
            readiness_score = jev_eval.get("readiness_score", "Ship-ready")
            if jev_eval.get("has_duplicates"):
                messages.append("WARNING: [Jev] A planned DocType may duplicate existing core site functionality.")
        except Exception:
            readiness_score = "Ship-ready" if is_valid else "Major gaps"

    return is_valid, messages, readiness_score
