"""
medical_logic/medical_logic/medical_logic/medical_bill_checks.py

Expense Claim -> validate (runs on save and on submit, also for API / import):

  1. Limit            - the medical amount of the claim must not be more than the employee's
                        remaining medical balance (never goes into minus). Blocked with a clear message.
  2. One bill a month - an employee can have only ONE medical claim per month (month of the bill's
                        Expense Date). A second claim for the same month is blocked.
  3. No duplicates    - the same bill (Medicine Bill / Lab Test / Emergency Bill number) cannot be
                        claimed twice by the same employee, and a claim cannot hold the same line twice.

Cancelled / rejected claims do not count. Claims without a medical line are not touched.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_first_day, get_last_day, getdate, formatdate

from medical_logic.medical_logic.medical_logic import _get_medical_amount_from_claim

BILL_FIELDS = {
    "custom_medicine_bill": "Medicine Bill",
    "custom_lab_test": "Lab Test",
    "custom_emergency_bill": "Emergency Bill",
}
# values people type when there is no bill number
NOT_A_BILL = {"", "-", "--", "na", "n/a", "nil", "none", "no", "null", "0"}


def _is_medical(line):
    return "medical" in (line.get("expense_type") or "").lower()


def _clean(value):
    return (value or "").strip().lower()


def _line_amount(line):
    return flt(line.get("sanctioned_amount") or 0) or flt(line.get("amount") or 0)


def _bill_numbers(line):
    """{field: normalised bill number} of the lines's bill fields that really hold a number."""
    out = {}
    for field in BILL_FIELDS:
        value = _clean(line.get(field))
        if value not in NOT_A_BILL and len(value) >= 2:
            out[field] = value
    return out


def validate_medical_claim(doc, method=None):
    """Hook: Expense Claim -> validate"""
    if not doc.get("employee"):
        return
    medical_lines = [l for l in (doc.get("expenses") or []) if _is_medical(l)]
    if not medical_lines:
        return

    check_duplicate_lines(doc, medical_lines)
    check_one_bill_a_month(doc, medical_lines)
    check_bill_not_claimed_before(doc, medical_lines)
    check_medical_limit(doc)


# ─────────────────────────────────────────────────────────────────────────────
# 1. LIMIT
# ─────────────────────────────────────────────────────────────────────────────

def check_medical_limit(doc):
    claim_amount = _get_medical_amount_from_claim(doc)
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


# ─────────────────────────────────────────────────────────────────────────────
# 2. ONE MEDICAL BILL A MONTH
# ─────────────────────────────────────────────────────────────────────────────

def _active_medical_lines(employee, exclude_claim, date_from=None, date_to=None):
    """Medical lines of the employee's other claims that still count (not cancelled / rejected)."""
    conditions = [
        "ec.employee = %(employee)s",
        "ec.name != %(exclude)s",
        "ec.docstatus < 2",
        "IFNULL(ec.approval_status, '') NOT IN ('Rejected', 'Cancelled')",
        "IFNULL(ec.status, '') NOT IN ('Rejected', 'Cancelled')",
        "LOWER(IFNULL(ecd.expense_type, '')) LIKE '%%medical%%'",
    ]
    values = {"employee": employee, "exclude": exclude_claim or ""}
    if date_from and date_to:
        conditions.append("ecd.expense_date BETWEEN %(date_from)s AND %(date_to)s")
        values.update({"date_from": date_from, "date_to": date_to})

    return frappe.db.sql(
        f"""
        SELECT ec.name AS claim, ec.docstatus, ecd.expense_date, ecd.amount, ecd.sanctioned_amount,
               ecd.custom_medicine_bill, ecd.custom_lab_test, ecd.custom_emergency_bill
        FROM `tabExpense Claim Detail` ecd
        JOIN `tabExpense Claim` ec ON ec.name = ecd.parent
        WHERE {' AND '.join(conditions)}
        """,
        values,
        as_dict=True,
    )


def check_one_bill_a_month(doc, medical_lines):
    months = {}
    for line in medical_lines:
        date = getdate(line.get("expense_date") or doc.get("posting_date"))
        months.setdefault((date.year, date.month), date)

    for (_year, _month), date in sorted(months.items()):
        others = _active_medical_lines(
            doc.employee, doc.name, get_first_day(date), get_last_day(date)
        )
        if others:
            claims = sorted({o.claim for o in others})
            frappe.throw(
                _("{0} already has a medical bill for {1}: {2}.<br><br>"
                  "Only one medical bill is allowed in a month, so a second one cannot be made. "
                  "Cancel that claim first, or use a bill date of another month.").format(
                    doc.get("employee_name") or doc.employee,
                    date.strftime("%B %Y"),
                    ", ".join(claims),
                ),
                title=_("⚠️ Medical Bill Already Made For This Month"),
            )


# ─────────────────────────────────────────────────────────────────────────────
# 3. DUPLICATES
# ─────────────────────────────────────────────────────────────────────────────

def check_duplicate_lines(doc, medical_lines):
    """The same medical line twice inside one claim."""
    seen = {}
    for line in medical_lines:
        key = (
            str(getdate(line.get("expense_date") or doc.get("posting_date"))),
            round(_line_amount(line), 2),
            _clean(line.get("expense_type")),
            tuple(sorted(_bill_numbers(line).items())),
        )
        if key in seen:
            frappe.throw(
                _("Row {0} and row {1} are the same bill (same date, amount and bill number). "
                  "A duplicate bill cannot be added.").format(seen[key], line.get("idx")),
                title=_("⚠️ Duplicate Medical Bill"),
            )
        seen[key] = line.get("idx")


def check_bill_not_claimed_before(doc, medical_lines):
    """A bill number that the employee already claimed in another claim."""
    wanted = {}
    for line in medical_lines:
        for field, number in _bill_numbers(line).items():
            wanted[(field, number)] = line.get("idx")
    if not wanted:
        return

    for other in _active_medical_lines(doc.employee, doc.name):
        for field in BILL_FIELDS:
            number = _clean(other.get(field))
            if (field, number) in wanted:
                frappe.throw(
                    _("{0} <b>{1}</b> (row {2}) was already claimed in {3} dated {4}. "
                      "A bill cannot be claimed twice.").format(
                        BILL_FIELDS[field],
                        other.get(field),
                        wanted[(field, number)],
                        other.claim,
                        formatdate(other.expense_date),
                    ),
                    title=_("⚠️ Duplicate Medical Bill"),
                )
