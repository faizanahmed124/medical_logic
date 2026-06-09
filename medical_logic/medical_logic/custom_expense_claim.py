import frappe
from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim

class CustomExpenseClaim(ExpenseClaim):

    def validate(self):
        self.inject_missing_fields()
        super().validate()

    def on_submit(self):
        self.inject_missing_fields()
        super().on_submit()

    def inject_missing_fields(self):
        if not self.expense_claim_type:
            frappe.throw("Please select Expense Claim Type.")

        account = frappe.db.get_value(
            "Expense Claim Account",
            {
                "parent": self.expense_claim_type,
                "company": self.company
            },
            "default_account"
        )

        if not account:
            frappe.throw(
                f"<b>{self.expense_claim_type}</b> mein company "
                f"<b>{self.company}</b> ka Default Account set nahi hai."
            )

        self.default_account = account

        for expense in self.expenses:
            expense.default_account = account
            expense.expense_type = self.expense_claim_type