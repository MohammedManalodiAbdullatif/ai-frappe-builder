"""
script_generator.py — Generates Frappe server/client scripts from patterns.

Flow:
1. Pick the right snippet template based on `pattern`
2. Send template + doctype fields + purpose to OpenRouter
3. LLM adapts the template (does NOT redesign from scratch)
4. ast.parse validates the output
5. If over 40 lines, split into two scripts
6. Return the final script string
"""

from __future__ import annotations

import ast
import logging
from typing import Optional

import httpx

from config import get_settings
from snippets import SNIPPET_LIBRARY

logger = logging.getLogger(__name__)

SCRIPT_SYSTEM_PROMPT = """You are a Frappe server script generator.
You are given a snippet template and must adapt it to the specific doctype and purpose.
Rules:
- Keep under 40 lines
- Only use: frappe.db.get_value, frappe.db.get_list, frappe.db.set_value, frappe.get_doc, frappe.throw, frappe.msgprint, frappe.utils, frappe.session
- NO import statements
- Return ONLY the Python code, no markdown fences, no explanations
- Replace all {placeholders} with real field names from the doctype fields provided
"""


async def generate_script(
    pattern: str,
    purpose: str,
    doctype_name: str,
    fields: list[dict],
    extra_context: dict | None = None,
) -> str:
    """
    Generate a Frappe server script by adapting a snippet template.

    Args:
        pattern:       Key in SNIPPET_LIBRARY (e.g. "overlap_check")
        purpose:       Plain-language description of what the script should do
        doctype_name:  Name of the DocType the script targets
        fields:        List of field dicts from DocTypeSpec (fieldname, fieldtype, label)
        extra_context: Optional extra key-value context passed to the LLM

    Returns:
        Validated Python code string (≤40 lines).

    Raises:
        ValueError: If the generated code has a syntax error.
    """
    settings = get_settings()
    template = SNIPPET_LIBRARY.get(pattern, "")

    field_summary = "\n".join(
        f"- {f.get('fieldname')}: {f.get('fieldtype')} ({f.get('label', '')})"
        for f in fields[:30]
    )

    user_message = f"""DocType: {doctype_name}
Purpose: {purpose}
Pattern: {pattern}

Available fields:
{field_summary}

Template to adapt:
{template}

Adapt this template for the purpose above. Use the real field names from the fields list.
Return only Python code."""

    if extra_context:
        user_message += f"\n\nExtra context: {extra_context}"

    base_url = settings.get_effective_base_url()
    api_key = settings.get_effective_llm_key()
    model = settings.get_effective_llm_model()

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SCRIPT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.1,
            },
        )
        response.raise_for_status()
        data = response.json()
        script_code = data["choices"][0]["message"]["content"].strip()

    # Strip markdown fences if the model returned them anyway
    if script_code.startswith("```"):
        lines = script_code.split("\n")
        script_code = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    # Validate syntax with ast.parse
    try:
        ast.parse(script_code)
    except SyntaxError as e:
        logger.error("Generated script has syntax error: %s", e)
        raise ValueError(f"Generated script has syntax error: {e}") from e

    # Truncate to 40 lines if the model overshot the limit
    lines = script_code.strip().split("\n")
    if len(lines) > 40:
        logger.warning("Script over 40 lines (%d), truncating to 40", len(lines))
        script_code = "\n".join(lines[:40])

    return script_code


# ---------------------------------------------------------------------------
# Client-script generation (JavaScript)
# ---------------------------------------------------------------------------

#: Built-in JS pattern templates used as a starting point for the LLM.
_CLIENT_PATTERNS: dict[str, str] = {
    "set_query_filter": (
        "frappe.ui.form.on('{doctype}', {{"
        " {link_field}: function(frm) {{"
        " frm.set_query('{link_field}', function() {{"
        " return {{ filters: {{ status: 'Available' }} }};"
        " }});"
        " }} }});"
    ),
    "custom_button": (
        "frappe.ui.form.on('{doctype}', {{"
        " refresh: function(frm) {{"
        " if (frm.doc.docstatus === 1) {{"
        " frm.add_custom_button('{button_label}', function() {{"
        " frappe.model.open_mapped_doc({{ method: '{method}', frm: frm }});"
        " }});"
        " }} }} }});"
    ),
    "live_total": (
        "frappe.ui.form.on('{child_doctype}', {{"
        " amount: function(frm) {{"
        " let total = 0;"
        " (frm.doc.{items_field} || []).forEach(r => total += (r.amount || 0));"
        " frm.set_value('{total_field}', total);"
        " }} }});"
    ),
    "toggle_fields": (
        "frappe.ui.form.on('{doctype}', {{"
        " {toggle_field}: function(frm) {{"
        " frm.toggle_display(['{field1}', '{field2}'], frm.doc.{toggle_field});"
        " }} }});"
    ),
}


async def generate_client_script(
    pattern: str,
    purpose: str,
    doctype_name: str,
    fields: list[dict],
) -> str:
    """
    Generate a Frappe client script (JavaScript).

    Args:
        pattern:      Key in _CLIENT_PATTERNS (e.g. "live_total")
        purpose:      Plain-language description of the script's purpose
        doctype_name: Name of the DocType the script targets
        fields:       List of field dicts from DocTypeSpec

    Returns:
        JavaScript code string.
    """
    settings = get_settings()

    template = _CLIENT_PATTERNS.get(
        pattern,
        "// Custom client script\n// Purpose: {purpose}",
    )

    user_message = (
        f"DocType: {doctype_name}\n"
        f"Purpose: {purpose}\n"
        f"Pattern: {pattern}\n"
        f"Template: {template}\n\n"
        f"Available fields: {[f.get('fieldname') for f in fields[:20]]}\n\n"
        "Adapt the template to a working Frappe client script (JavaScript). "
        "Return only JS code."
    )

    base_url = settings.get_effective_base_url()
    api_key = settings.get_effective_llm_key()
    model = settings.get_effective_llm_model()

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a Frappe client script generator. "
                            "Return only JavaScript code. No markdown."
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.1,
            },
        )
        response.raise_for_status()
        data = response.json()
        js_code = data["choices"][0]["message"]["content"].strip()

    # Strip markdown fences if present
    if js_code.startswith("```"):
        lines = js_code.split("\n")
        js_code = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return js_code
