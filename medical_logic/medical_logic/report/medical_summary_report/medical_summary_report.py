"""
medical_logic/medical_logic/report/medical_summary_report/medical_summary_report.py

Medical Summary Report — month-wise aggregated totals.
One row per month showing employee count, claim count and total claimed.
"""

import frappe
from frappe import _
from frappe.utils import flt


MONTH_ORDER = [
    "January", "February", "March",    "April",
    "May",     "June",     "July",     "August",
    "September","October", "November", "December",
]


def execute(filters=None):
    filters = filters or {}
    validate_filters(filters)
    columns = get_columns()
    data    = get_data(filters)
    summary = get_summary(data)
    return columns, data, None, None, summary


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATE
# ─────────────────────────────────────────────────────────────────────────────

def validate_filters(filters):
    if not filters.get("year"):
        frappe.throw(_("Please select a Year to generate the report."))


# ─────────────────────────────────────────────────────────────────────────────
# COLUMNS
# ─────────────────────────────────────────────────────────────────────────────

def get_columns():
    return [
        {
            "label":     _("Month"),
            "fieldname": "month",
            "fieldtype": "Data",
            "width":     120,
        },
        {
            "label":     _("Year"),
            "fieldname": "year",
            "fieldtype": "Data",
            "width":     70,
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
            "width":     150,
        },
        {
            "label":     _("Total Claims"),
            "fieldname": "claim_count",
            "fieldtype": "Int",
            "width":     110,
        },
        {
            "label":     _("Total Medical Claimed (Rs)"),
            "fieldname": "total_claimed",
            "fieldtype": "Currency",
            "width":     200,
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────────────────────

def get_data(filters):
    year       = filters.get("year")
    from_month = filters.get("from_month")
    to_month   = filters.get("to_month")
    employee   = filters.get("employee")
    department = filters.get("department")

    extra = ""
    if employee:
        extra += " AND ec.employee = %(employee)s"
    if department:
        extra += " AND ec.department = %(department)s"

    sql_filters = {
        "year":       year,
        "employee":   employee,
        "department": department,
    }

    rows = frappe.db.sql(f"""
        SELECT
            ec.custom_bill_of_month                         AS month,
            %(year)s                                        AS year,
            ec.employee                                     AS employee,
            ec.employee_name                                AS employee_name,
            ec.department                                   AS department,
            COUNT(DISTINCT ec.name)                         AS claim_count,
            SUM(
                CASE
                    WHEN IFNULL(ecd.sanctioned_amount, 0) > 0
                    THEN ecd.sanctioned_amount
                    ELSE IFNULL(ecd.amount, 0)
                END
            )                                               AS total_claimed
        FROM
            `tabExpense Claim`        ec
        JOIN
            `tabExpense Claim Detail` ecd ON ecd.parent = ec.name
        WHERE
            ec.docstatus              != 2
            AND YEAR(ec.creation)      = %(year)s
            AND ec.custom_bill_of_month IS NOT NULL
            AND ec.custom_bill_of_month != ''
            {extra}
        GROUP BY
            ec.custom_bill_of_month, ec.employee
        ORDER BY
            ec.employee_name
    """, sql_filters, as_dict=True)

    # Sort by calendar month order
    month_index = {m: i for i, m in enumerate(MONTH_ORDER)}
    rows = sorted(rows, key=lambda r: month_index.get(r.get("month") or "", 99))

    # Apply from_month / to_month slice
    if from_month or to_month:
        from_idx = month_index.get(from_month, 0)   if from_month else 0
        to_idx   = month_index.get(to_month,   11)  if to_month   else 11
        rows = [
            r for r in rows
            if from_idx <= month_index.get(r.get("month") or "", 99) <= to_idx
        ]

    for r in rows:
        r["total_claimed"] = flt(r["total_claimed"], 2)

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def get_summary(data):
    if not data:
        return []

    total_claimed   = sum(flt(r.get("total_claimed")  or 0) for r in data)
    total_claims    = sum(int(r.get("claim_count")     or 0) for r in data)
    total_employees = sum(int(r.get("employee_count")  or 0) for r in data)
    total_months    = len(data)

    return [
        {
            "label":    _("Months"),
            "value":    total_months,
            "indicator": "blue",
            "datatype": "Int",
        },
        {
            "label":    _("Total Claims"),
            "value":    total_claims,
            "indicator": "orange",
            "datatype": "Int",
        },
        {
            "label":    _("Total Employees Claimed"),
            "value":    total_employees,
            "indicator": "purple",
            "datatype": "Int",
        },
        {
            "label":    _("Grand Total Medical Claimed"),
            "value":    total_claimed,
            "indicator": "green",
            "datatype": "Currency",
        },
    ]