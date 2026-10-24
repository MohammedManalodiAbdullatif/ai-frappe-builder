"""
snippets/overlap_check.py — Prevent double-booking of a resource.

Pattern: overlap_check
Event:   Before Save
"""

TEMPLATE = '''
# Overlap Check — Before Save
# Checks that {resource_field} is not already booked for the same date range
doc_list = frappe.db.get_list(
    "{doctype}",
    filters=[
        ["{resource_field}", "=", doc.{resource_field}],
        ["docstatus", "<", 2],
        ["name", "!=", doc.name],
        ["{start_field}", "<", doc.{end_field}],
        ["{end_field}", ">", doc.{start_field}],
    ],
    fields=["name"],
    limit=1,
)
if doc_list:
    frappe.throw(
        f"{{doc.{resource_field}}} is already booked from {{doc.{start_field}}} to {{doc.{end_field}}}. "
        f"Clashes with {{doc_list[0]['name']}}."
    )
'''

TEST_CODE = '''
# Test: overlap_check
# Manually call with two overlapping bookings to verify frappe.throw is raised.
import unittest

class TestOverlapCheck(unittest.TestCase):
    def test_no_overlap(self):
        """Non-overlapping bookings should not raise."""
        pass  # Integration test — requires live Frappe site

    def test_overlap_raises(self):
        """Overlapping bookings must raise ValidationError."""
        pass  # Integration test — requires live Frappe site
'''
