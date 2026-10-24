"""
snippets/__init__.py — Script pattern library for Frappe server scripts.

Exports all snippet templates as a unified SNIPPET_LIBRARY dict.
Each template is a Python code string with {placeholder} variables
that the LLM adapts to the specific DocType and purpose.
"""

from .overlap_check import TEMPLATE as overlap_check
from .compute_totals import TEMPLATE as compute_totals
from .create_document_on_submit import TEMPLATE as create_document_on_submit
from .validate_required_child_rows import TEMPLATE as validate_required_child_rows
from .update_linked_status import TEMPLATE as update_linked_status
from .fetch_and_validate import TEMPLATE as fetch_and_validate
from .scheduled_reminder import TEMPLATE as scheduled_reminder

SNIPPET_LIBRARY = {
    "overlap_check": overlap_check,
    "compute_totals": compute_totals,
    "create_document_on_submit": create_document_on_submit,
    "validate_required_child_rows": validate_required_child_rows,
    "update_linked_status": update_linked_status,
    "fetch_and_validate": fetch_and_validate,
    "scheduled_reminder": scheduled_reminder,
}

__all__ = ["SNIPPET_LIBRARY"]
