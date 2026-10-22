import frappe


def execute():
    """Claims cancelled before the on_cancel fix kept Approval Status "Approved"."""
    frappe.db.set_value(
        "Expense Claim",
        {"docstatus": 2, "approval_status": ["!=", "Cancelled"]},
        {"approval_status": "Cancelled", "status": "Cancelled"},
        update_modified=False,
    )
