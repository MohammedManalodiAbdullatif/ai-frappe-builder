"""
snippets/validate_required_child_rows.py — Enforce at least one row in a child table.

Pattern: validate_required_child_rows
Event:   Before Save
"""

TEMPLATE = '''
# Validate Required Child Rows — Before Save
if not doc.{child_table_field}:
    frappe.throw("Please add at least one row in {child_table_label} before saving.")
'''

TEST_CODE = '''
# Test: validate_required_child_rows
# Verify that saving without child rows raises ValidationError.
import unittest

class TestValidateRequiredChildRows(unittest.TestCase):
    def test_empty_table_raises(self):
        """Saving with empty child table must raise."""
        pass  # Integration test — requires live Frappe site

    def test_non_empty_table_passes(self):
        """Saving with at least one row must succeed."""
        pass  # Integration test — requires live Frappe site
'''
