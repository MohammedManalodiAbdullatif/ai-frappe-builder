"""
snippets/create_document_on_submit.py — Auto-create a linked document on submit.

Pattern: create_document_on_submit
Event:   After Submit
"""

TEMPLATE = '''
# Create Document on Submit — After Submit
new_doc = frappe.get_doc({
    "doctype": "{target_doctype}",
    "{source_link_field}": doc.name,
    "company": doc.get("company"),
    "customer": doc.get("customer"),
    "posting_date": frappe.utils.today(),
})
new_doc.insert(ignore_permissions=True)
frappe.db.set_value("{doctype}", doc.name, "{target_link_field}", new_doc.name)
frappe.msgprint(f"{target_doctype} {new_doc.name} created.", indicator="green", alert=True)
'''

TEST_CODE = '''
# Test: create_document_on_submit
# Verify that submitting the source doc creates the target doc.
import unittest

class TestCreateDocumentOnSubmit(unittest.TestCase):
    def test_linked_doc_created(self):
        """Submitting source doc should create target doc."""
        pass  # Integration test — requires live Frappe site
'''
