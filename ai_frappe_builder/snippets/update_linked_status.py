"""
snippets/update_linked_status.py — Propagate status to a parent/linked document on submit.

Pattern: update_linked_status
Event:   After Submit
"""

TEMPLATE = '''
# Update Linked Status — After Submit
frappe.db.set_value(
    "{parent_doctype}",
    doc.{parent_link_field},
    "{status_field}",
    "{new_status}",
)
frappe.msgprint(
    f"{parent_doctype} status updated to {new_status}.",
    indicator="blue",
    alert=True,
)
'''

TEST_CODE = '''
# Test: update_linked_status
# Verify that submitting the child doc updates the parent's status field.
import unittest

class TestUpdateLinkedStatus(unittest.TestCase):
    def test_parent_status_updated(self):
        """Parent status field must be updated after child submit."""
        pass  # Integration test — requires live Frappe site
'''
