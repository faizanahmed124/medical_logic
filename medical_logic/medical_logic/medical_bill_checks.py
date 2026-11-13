"""
medical_logic/medical_logic/medical_logic/medical_bill_checks.py

Expense Claim -> validate (runs on save and on submit, also for API / import):

  1. Bill of Month - an employee can have only ONE medical claim for a month: the 'Bill of Month'
                     field of the claim. A second claim with the same Bill of Month is blocked.
                     Nothing in the expenses table (dates, bill numbers, amounts) is checked.
  2. Limit         - the medical amount of the claim must not be more than the employee's
                     remaining medical balance (never goes into minus). Blocked with a clear message.

Cancelled / rejected claims do not count. Claims without a medical line are not touched.
"""

import re

import frappe
from frappe import _
from frappe.utils import flt, getdate

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]


def _is_medical(line):
    return "medical" in (line.get("expense_type") or "").lower()


def _clean(value):
    return (value or "").strip().lower()


def _line_amount(line):
    return flt(line.get("sanctioned_amount") or 0) or flt(line.get("amount") or 0)


def validate_medical_claim(doc, method=None):
    """Hook: Expense Claim -> validate"""
    if not doc.get("employee"):
        return
    lines = doc.get("expenses") or []
    medical_lines = [l for l in lines if _is_medical(l)]
    if not medical_lines and "medical" in _clean(doc.get("custom_expense_type")):
        # the claim's Expense Type says medical, the lines just do not carry it (API / import)
        medical_lines = list(lines)
    if not medical_lines:
        return

    check_one_bill_a_month(doc)
    check_medical_limit(doc, medical_lines)


# ─────────────────────────────────────────────────────────────────────────────
# 1. ONE MEDICAL BILL FOR A 'BILL OF MONTH'
# ─────────────────────────────────────────────────────────────────────────────

def _bill_month_fieldname():
    """The 'Bill of Month' field of the Expense Claim (found by its label, so the fieldname of the
    custom field does not have to be known). None when the form has no such field."""
    for f in frappe.get_meta("Expense Claim").fields:
        if (f.label or "").strip().lower() in ("bill of month", "bill month"):
            return f.fieldname
    return None


def _month_number(value):
    value = _clean(value)
    if value.isdigit() and 1 <= int(value) <= 12:
        return int(value)
    for i, name in enumerate(MONTHS, start=1):
        if value == name or value == name[:3]:
            return i
    return None


def _bill_period(month_value, posting_date):
    """(year, month) of a 'Bill of Month' value. The field holds only a month name, so the
    year is the posting year, or the year before when the month is later than the posting month
    (a December bill posted in January belongs to the previous year)."""
    month = _month_number(month_value)
    if not month:
        return None
    posting = getdate(posting_date)
    return (posting.year if month <= posting.month else posting.year - 1, month)


def check_one_bill_a_month(doc):
    fieldname = _bill_month_fieldname()
    if not fieldname or not doc.get(fieldname) or not re.fullmatch(r"[A-Za-z0-9_]+", fieldname):
        return
    period = _bill_period(doc.get(fieldname), doc.get("posting_date"))
    if not period:
        return

    others = frappe.db.sql(
        f"""
        SELECT ec.name, ec.posting_date, ec.`{fieldname}` AS bill_month
        FROM `tabExpense Claim` ec
        WHERE ec.employee = %(employee)s
          AND ec.name != %(exclude)s
          AND ec.docstatus < 2
          AND IFNULL(ec.approval_status, '') NOT IN ('Rejected', 'Cancelled')
          AND IFNULL(ec.status, '') NOT IN ('Rejected', 'Cancelled')
          AND IFNULL(ec.`{fieldname}`, '') != ''
          AND EXISTS (
                SELECT 1 FROM `tabExpense Claim Detail` ecd
                WHERE ecd.parent = ec.name AND LOWER(IFNULL(ecd.expense_type, '')) LIKE '%%medical%%')
        """,
        {"employee": doc.employee, "exclude": doc.name or ""},
        as_dict=True,
    )
    same = [o.name for o in others if _bill_period(o.bill_month, o.posting_date) == period]
    if same:
        frappe.throw(
            _("{0} already has a medical bill for {1}: {2}.<br><br>"
              "Only one medical bill is allowed for a month, so a second one cannot be made. "
              "Cancel that claim first, or choose another Bill of Month.").format(
                doc.get("employee_name") or doc.employee,
                doc.get(fieldname),
                ", ".join(sorted(same)),
            ),
            title=_("⚠️ Medical Bill Already Made For This Month"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. LIMIT
# ─────────────────────────────────────────────────────────────────────────────

def check_medical_limit(doc, medical_lines):
    claim_amount = round(sum(_line_amount(l) for l in medical_lines), 2)
    if claim_amount <= 0:
        return

    emp = frappe.db.get_value(
        "Employee",
        doc.employee,
        ["employee_name", "custom_medical_amount", "custom_consumed_medical_amount",
         "custom_remaining_medical_amount"],
        as_dict=True,
    )
    if not emp:
        return

    remaining = flt(emp.custom_remaining_medical_amount)
    if claim_amount <= remaining:
        return

    money = lambda v: frappe.format_value(v, {"fieldtype": "Currency"})
    if remaining <= 0:
        lead = _("The medical limit of {0} is finished.").format(emp.employee_name)
    else:
        lead = _("The medical balance of {0} is not enough for this bill.").format(emp.employee_name)

    frappe.throw(
        _("{0}<br><br>Yearly medical limit: <b>{1}</b><br>Already used: <b>{2}</b><br>"
          "Remaining: <b>{3}</b><br>This bill: <b style='color:red'>{4}</b><br><br>"
          "The bill cannot be saved: the balance would go into minus.").format(
            lead,
            money(emp.custom_medical_amount),
            money(emp.custom_consumed_medical_amount),
            money(remaining),
            money(claim_amount),
        ),
        title=_("⚠️ Medical Amount Not Enough"),
    )
