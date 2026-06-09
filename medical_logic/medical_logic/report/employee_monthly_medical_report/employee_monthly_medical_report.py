import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "employee",
            "label": _("Employee ID"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 130,
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "department",
            "label": _("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "width": 150,
        },
        {
            "fieldname": "medical_allowance",
            "label": _("Medical Allowance"),
            "fieldtype": "Currency",
            "width": 140,
        },
        # ── Monthly columns (Jul 2025 – Jun 2026) ───────────────────
        {"fieldname": "jul_2025", "label": _("Jul 2025"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "aug_2025", "label": _("Aug 2025"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "sep_2025", "label": _("Sep 2025"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "oct_2025", "label": _("Oct 2025"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "nov_2025", "label": _("Nov 2025"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "dec_2025", "label": _("Dec 2025"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "jan_2026", "label": _("Jan 2026"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "feb_2026", "label": _("Feb 2026"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "mar_2026", "label": _("Mar 2026"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "apr_2026", "label": _("Apr 2026"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "may_2026", "label": _("May 2026"), "fieldtype": "Currency", "width": 110},
        {"fieldname": "jun_2026", "label": _("Jun 2026"), "fieldtype": "Currency", "width": 110},
        # ── Summary ─────────────────────────────────────────────────
        {
            "fieldname": "total_claimed",
            "label": _("Total Claimed"),
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "fieldname": "balance",
            "label": _("Balance"),
            "fieldtype": "Currency",
            "width": 130,
        },
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    query = """
        SELECT
            ec.employee,
            ec.employee_name,
            ec.department,
            ROUND(ec.custom_salary * 1.5, 0)                                           AS medical_allowance,

            /* ── Monthly Totals ── */
            SUM(CASE WHEN MONTH(ecd.expense_date) = 7  AND YEAR(ecd.expense_date) = 2025
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS jul_2025,
            SUM(CASE WHEN MONTH(ecd.expense_date) = 8  AND YEAR(ecd.expense_date) = 2025
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS aug_2025,
            SUM(CASE WHEN MONTH(ecd.expense_date) = 9  AND YEAR(ecd.expense_date) = 2025
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS sep_2025,
            SUM(CASE WHEN MONTH(ecd.expense_date) = 10 AND YEAR(ecd.expense_date) = 2025
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS oct_2025,
            SUM(CASE WHEN MONTH(ecd.expense_date) = 11 AND YEAR(ecd.expense_date) = 2025
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS nov_2025,
            SUM(CASE WHEN MONTH(ecd.expense_date) = 12 AND YEAR(ecd.expense_date) = 2025
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS dec_2025,
            SUM(CASE WHEN MONTH(ecd.expense_date) = 1  AND YEAR(ecd.expense_date) = 2026
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS jan_2026,
            SUM(CASE WHEN MONTH(ecd.expense_date) = 2  AND YEAR(ecd.expense_date) = 2026
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS feb_2026,
            SUM(CASE WHEN MONTH(ecd.expense_date) = 3  AND YEAR(ecd.expense_date) = 2026
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS mar_2026,
            SUM(CASE WHEN MONTH(ecd.expense_date) = 4  AND YEAR(ecd.expense_date) = 2026
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS apr_2026,
            SUM(CASE WHEN MONTH(ecd.expense_date) = 5  AND YEAR(ecd.expense_date) = 2026
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS may_2026,
            SUM(CASE WHEN MONTH(ecd.expense_date) = 6  AND YEAR(ecd.expense_date) = 2026
                THEN ecd.sanctioned_amount ELSE 0 END)                                  AS jun_2026,

            /* ── Summary ── */
            SUM(ecd.sanctioned_amount)                                                  AS total_claimed,
            (ROUND(ec.custom_salary * 1.5, 0) - SUM(ecd.sanctioned_amount))            AS balance

        FROM `tabExpense Claim` ec
        LEFT JOIN `tabExpense Claim Detail` ecd
            ON ec.name = ecd.parent
        WHERE
            ecd.expense_date BETWEEN '2025-07-01' AND '2026-06-30'
            {conditions}
        GROUP BY
            ec.employee, ec.employee_name, ec.department, ec.custom_salary
        ORDER BY
            ec.department, ec.employee
    """.format(conditions=conditions)

    return frappe.db.sql(query, filters or {}, as_dict=True)


def get_conditions(filters):
    conditions = ""
    if not filters:
        return conditions

    if filters.get("department"):
        conditions += " AND ec.department = %(department)s"

    if filters.get("employee"):
        conditions += " AND ec.employee = %(employee)s"

    if filters.get("approval_status"):
        conditions += " AND ec.approval_status = %(approval_status)s"

    return conditions