"""
snippets/fetch_and_validate.py — Validate a linked document's status before saving.

Pattern: fetch_and_validate
Event:   Before Save
"""

TEMPLATE = '''
# Fetch and Validate — Before Save
if doc.{link_field}:
    status = frappe.db.get_value("{linked_doctype}", doc.{link_field}, "{status_field}")
    if status != "{required_status}":
        frappe.throw(
            f"{doc.{link_field}} must have status '{required_status}' but is '{status}'."
        )
'''

TEST_CODE = '''
# Test: fetch_and_validate
# Verify that referencing a linked doc with the wrong status raises ValidationError.
import unittest

class TestFetchAndValidate(unittest.TestCase):
    def test_wrong_status_raises(self):
        """Referencing a doc with wrong status must raise."""
        pass  # Integration test — requires live Frappe site

    def test_correct_status_passes(self):
        """Referencing a doc with correct status must not raise."""
        pass  # Integration test — requires live Frappe site
'''
