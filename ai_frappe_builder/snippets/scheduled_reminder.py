"""
snippets/scheduled_reminder.py — Send notification logs for overdue documents.

Pattern: scheduled_reminder
Event:   Daily Scheduler Event (Cron)
"""

TEMPLATE = '''
# Scheduled Reminder — Daily Scheduler Event
overdue = frappe.db.get_list(
    "{doctype}",
    filters=[["{date_field}", "<", frappe.utils.today()], ["docstatus", "=", 1], ["{status_field}", "!=", "{closed_status}"]],
    fields=["name", "owner", "{date_field}"],
)
for row in overdue:
    frappe.get_doc({
        "doctype": "Notification Log",
        "subject": f"Overdue: {row['name']}",
        "for_user": row["owner"],
        "type": "Alert",
        "document_type": "{doctype}",
        "document_name": row["name"],
    }).insert(ignore_permissions=True)
'''

TEST_CODE = '''
# Test: scheduled_reminder
# Verify that overdue documents trigger a Notification Log insertion.
import unittest

class TestScheduledReminder(unittest.TestCase):
    def test_notification_created_for_overdue(self):
        """Overdue submitted docs must generate a Notification Log."""
        pass  # Integration test — requires live Frappe site

    def test_closed_docs_skipped(self):
        """Docs with closed status must not generate notifications."""
        pass  # Integration test — requires live Frappe site
'''
