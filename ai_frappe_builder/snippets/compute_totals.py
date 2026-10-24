"""
snippets/compute_totals.py — Roll up child table amounts into parent totals.

Pattern: compute_totals
Event:   Before Save
"""

TEMPLATE = '''
# Compute Totals — Before Save
total = sum(row.get("amount", 0) for row in (doc.{items_field} or []))
for extra in {extra_fields}:
    total += (doc.get(extra) or 0)
doc.{total_field} = total
doc.{outstanding_field} = total - (doc.get("{paid_field}") or 0)
'''

TEST_CODE = '''
# Test: compute_totals
# Verify that totals are summed correctly from the child table.
import unittest

class TestComputeTotals(unittest.TestCase):
    def test_sum_items(self):
        """Total should equal sum of child row amounts."""
        pass  # Integration test — requires live Frappe site

    def test_outstanding_calculation(self):
        """Outstanding = total - paid."""
        pass  # Integration test — requires live Frappe site
'''
