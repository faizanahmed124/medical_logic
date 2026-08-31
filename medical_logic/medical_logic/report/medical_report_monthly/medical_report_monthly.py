"""
medical_logic/medical_logic/report/medical_report_monthly/medical_report_monthly.py

Medical Report Monthly — shows each expense line with date, claim type and amount.
"""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters  = filters or {}
    columns  = get_columns()
    data     = get_data(filters)
    chart    = get_chart(data)
    summary  = get_summary(data)
    return columns, data, None, chart, summary


# ─────────────────────────────────────────────────────────────────────────────
# COLUMNS
# ─────────────────────────────────────────────────────────────────────────────

def get_columns():
    return [
        {
            "label":     _("Claim No."),
            "fieldname": "name",
            "fieldtype": "Link",
            "options":   "Expense Claim",
            "width":     160,
        },
        {
            "label":     _("Employee ID"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options":   "Employee",
            "width":     110,
        },
        {
            "label":     _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width":     180,
        },
        {
            "label":     _("Department"),
            "fieldname": "department",
            "fieldtype": "Data",
            "width":     140,
        },
        {
            "label":     _("Bill of Month"),
            "fieldname": "custom_bill_of_month",
            "fieldtype": "Data",
            "width":     120,
        },
        {
            "label":     _("Expense Date"),
            "fieldname": "expense_date",
            "fieldtype": "Date",
            "width":     110,
        },
        {
            "label":     _("Claim Type"),
            "fieldname": "custom_claim_type",
            "fieldtype": "Data",
            "width":     110,
        },
        {
            "label":     _("Medical Claimed (Rs)"),
            "fieldname": "medical_claimed",
            "fieldtype": "Currency",
            "width":     170,
        },
        {
            "label":     _("Medical Balance (Rs)"),
            "fieldname": "remaining_medical",
            "fieldtype": "Currency",
            "width":     170,
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
# DATA — one row per expense detail line
# ─────────────────────────────────────────────────────────────────────────────

def get_data(filters):
    conditions = _get_conditions(filters)

    rows = frappe.db.sql(f"""
        SELECT
            ec.name,
            ec.employee,
            ec.employee_name,
            ec.department,
            ec.custom_bill_of_month,
            ecd.expense_date,
            ecd.custom_claim_type,
            IFNULL(NULLIF(ecd.sanctioned_amount, 0), ecd.amount) AS medical_claimed,
            IFNULL(emp.custom_remaining_medical_amount, 0)        AS remaining_medical
        FROM
            `tabExpense Claim`        ec
        JOIN
            `tabExpense Claim Detail` ecd ON ecd.parent = ec.name
        LEFT JOIN
            `tabEmployee`             emp ON emp.name   = ec.employee
        WHERE
            ec.docstatus != 2
            {conditions}
        ORDER BY
            FIELD(
                ec.custom_bill_of_month,
                'January','February','March','April','May','June',
                'July','August','September','October','November','December'
            ),
            ec.employee_name,
            ecd.expense_date
    """, filters, as_dict=True)

    return rows


def _get_conditions(filters):
    conds = ""

    if filters.get("bill_of_month"):
        conds += " AND ec.custom_bill_of_month = %(bill_of_month)s"

    if filters.get("employee"):
        conds += " AND ec.employee = %(employee)s"

    if filters.get("department"):
        conds += " AND ec.department = %(department)s"

    if filters.get("approval_status"):
        conds += " AND ec.approval_status = %(approval_status)s"

    return conds


# ─────────────────────────────────────────────────────────────────────────────
# CHART — Bar: total medical claimed per month
# ─────────────────────────────────────────────────────────────────────────────

def get_chart(data):
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY — totals at bottom
# ─────────────────────────────────────────────────────────────────────────────

def get_summary(data):
    if not data:
        return []

    total_medical = sum(flt(r.get("medical_claimed") or 0) for r in data)
    total_lines   = len(data)

    return [
        {
            "label":    _("Total Expense Lines"),
            "value":    total_lines,
            "indicator": "blue",
            "datatype": "Int",
        },
        {
            "label":    _("Total Medical Claimed"),
            "value":    total_medical,
            "indicator": "orange",
            "datatype": "Currency",
        },
    ]