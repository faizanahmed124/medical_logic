"""
medical_logic/medical_logic/medical_logic/medical_logic.py

Handles:
  1. on_update hook       - Every Employee save triggers eligibility check;
                            if eligible (PERMANENT + 3 yrs), auto-enables Medical Allow
  2. Auto-check (daily)   - Bulk job for any missed employees
  3. Manual check guard   - Daily Wages: Admin manually checks with 3-yr validation
  4. Admin-only field     - custom_medical_allow cannot be changed by non-Admin
  5. Medical calculation  - CTC x marital_status multiplier
                            Married -> CTC x 1.5  |  Single/Other -> CTC x 1.0
  6. Expense Claim submit - deduct medical claim from remaining balance
  7. Expense Claim cancel - reverse the deduction
  8. Annual reset (31 Dec)- reset consumed & recalculate for new year
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_years, date_diff


# ─────────────────────────────────────────────────────────────────────────────
# 1. EMPLOYEE — validate hooks
# ─────────────────────────────────────────────────────────────────────────────

def validate_medical_allow(doc, method):
    """
    Administrator-only guard for custom_medical_allow.
    3-year check from final_confirmation_date when manually enabling.

    Hook: Employee -> validate
    """
    before   = None if doc.is_new() else doc.get_doc_before_save()
    is_admin = frappe.session.user == "Administrator"

    new_val = bool(doc.get("custom_medical_allow"))
    old_val = bool(before.get("custom_medical_allow")) if before else False

    # Nothing changed — skip
    if new_val == old_val:
        return

    # ── A) Admin-only permission check ───────────────────────────────────────
    if not is_admin:
        doc.custom_medical_allow = old_val
        frappe.throw(
            _("Only the Administrator can change 'Medical Allow' for Employee {0}.").format(
                doc.employee_name
            ),
            frappe.PermissionError,
            title=_("Permission Denied"),
        )

    # ── B) 3-Year check (only when enabling) ─────────────────────────────────
    if new_val:
        ref_date  = doc.get("final_confirmation_date") or doc.get("date_of_joining")
        ref_label = "Final Confirmation Date" if doc.get("final_confirmation_date") \
                    else "Date of Joining"

        if not ref_date:
            doc.custom_medical_allow = False
            frappe.throw(
                _("Neither Final Confirmation Date nor Date of Joining is set for "
                  "Employee {0}. Cannot verify the 3-year service requirement.").format(
                      doc.employee_name),
                title=_("Medical Allow — Date Missing"),
            )

        eligible_from = add_years(getdate(ref_date), 3)
        today         = getdate(nowdate())

        if today < eligible_from:
            days_remaining  = date_diff(eligible_from, today)
            years_remaining = round(days_remaining / 365, 1)
            doc.custom_medical_allow = False
            frappe.throw(
                _("Medical Allow is not permitted for Employee {0}. "
                  "3 years from {1} have not been completed yet. "
                  "Eligible from: {2} ({3} year(s) remaining).").format(
                      doc.employee_name,
                      ref_label,
                      eligible_from.strftime("%d-%b-%Y"),
                      years_remaining,
                  ),
                title=_("Medical Allow — Not Eligible"),
            )


def calculate_medical_amount(doc, method):
    """
    Calculate Medical Amount from CTC and marital_status (Personal Details tab).

    Formula:
        Married        -> Medical Amount = CTC x 1.5
        Single / Other -> Medical Amount = CTC x 1.0

    Hook: Employee -> validate
    """
    if not doc.get("custom_medical_allow"):
        doc.custom_medical_amount           = 0.0
        doc.custom_remaining_medical_amount = 0.0
        return

    ctc = flt(doc.get("ctc") or 0.0)

    if not ctc:
        frappe.msgprint(
            _("CTC (Cost to Company) is not set for Employee {0}. "
              "Medical Amount could not be calculated.").format(doc.employee_name),
            indicator="orange",
            title=_("Medical Calculation"),
        )
        return

    marital_status = (doc.get("marital_status") or "").strip()
    multiplier     = 1.5 if marital_status == "Married" else 1.0

    doc.custom_medical_amount = flt(ctc * multiplier, 2)

    consumed = flt(doc.get("custom_consumed_medical_amount") or 0.0, 2)
    doc.custom_remaining_medical_amount = flt(
        doc.custom_medical_amount - consumed, 2
    )



# ─────────────────────────────────────────────────────────────────────────────
# 1b. EMPLOYEE — eligibility warning on validate
# ─────────────────────────────────────────────────────────────────────────────

def warn_if_eligible_not_enabled(doc, method):
    """
    Shows a warning if the employee is eligible for Medical Allow
    (3+ years from confirmation date) but it is NOT yet enabled.

    - Permanent employees: auto_check_on_employee_update handles them,
      but this also warns in case something was missed.
    - Daily Wages: Admin must manually enable, so warning is critical here.

    Hook: Employee -> validate
    """
    # Already enabled — no warning needed
    if doc.get("custom_medical_allow"):
        return

    # Only warn Administrator (non-admins can't act on it anyway)
    if frappe.session.user != "Administrator":
        return

    # Check eligibility date
    ref_date = doc.get("final_confirmation_date") or doc.get("date_of_joining")
    if not ref_date:
        return

    if getdate(nowdate()) < add_years(getdate(ref_date), 3):
        return  # Not yet eligible — no warning

    # Eligible but not enabled — show warning
    employment_type = (doc.get("employment_type") or "").upper()
    ref_label = "Final Confirmation Date" if doc.get("final_confirmation_date") \
                else "Date of Joining"

    frappe.msgprint(
        _("⚠️ Employee {0} has completed 3+ years from {1} and is "
          "eligible for Medical Allow, but it is currently NOT enabled. "
          "Please enable it from the Company Benefits tab.").format(
              doc.employee_name, ref_label
          ),
        indicator="orange",
        title=_("Medical Allow — Eligibility Warning"),
    )



def auto_check_on_employee_update(doc, method):
    """
    Fires after every Employee save.
    If the employee is PERMANENT and has 3+ years from final_confirmation_date,
    automatically enables Medical Allow and calculates the amount.

    This ensures auto-check happens immediately when any field is edited —
    no need to wait for the daily scheduled job.

    Hook: Employee -> on_update
    """
    # Already enabled — recalculate in case CTC or marital_status changed
    already_enabled = bool(doc.get("custom_medical_allow"))

    # Only PERMANENT employees get auto-checked
    if (doc.get("employment_type") or "").upper() != "PERMANENT":
        return

    # Check 3-year eligibility
    ref_date = doc.get("final_confirmation_date") or doc.get("date_of_joining")
    if not ref_date:
        return

    if getdate(nowdate()) < add_years(getdate(ref_date), 3):
        return  # Not yet eligible

    # Need a valid CTC to calculate
    ctc = flt(doc.get("ctc") or 0.0)
    if not ctc:
        return

    # Calculate
    marital_status = (doc.get("marital_status") or "").strip()
    multiplier     = 1.5 if marital_status == "Married" else 1.0
    medical_amount = flt(ctc * multiplier, 2)
    consumed       = flt(doc.get("custom_consumed_medical_amount") or 0.0, 2)
    remaining      = flt(medical_amount - consumed, 2)

    # Save directly to DB (after save hook — must use set_value)
    frappe.db.set_value("Employee", doc.name, {
        "custom_medical_allow":            1,
        "custom_medical_amount":           medical_amount,
        "custom_consumed_medical_amount":  consumed,
        "custom_remaining_medical_amount": remaining,
    })

    if not already_enabled:
        frappe.msgprint(
            _("Medical Allow has been automatically enabled for Employee {0}. "
              "Amount: {1} ({2})").format(
                  doc.employee_name,
                  frappe.format_value(medical_amount, {"fieldtype": "Currency"}),
                  marital_status or "Single",
              ),
            indicator="green",
            title=_("Medical Allow — Auto Enabled"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. EXPENSE CLAIM — submit & cancel hooks
# ─────────────────────────────────────────────────────────────────────────────

def validate_expense_claim_medical(doc, method):
    """
    Server-side block: prevent saving Expense Claim if employee
    does not have Medical Allow enabled.
    Works even if client script is bypassed (API, imports, etc.)

    Hook: Expense Claim -> validate
    """
    employee = doc.employee
    if not employee:
        return

    medical_allow, employee_name = frappe.db.get_value(
        "Employee", employee, ["custom_medical_allow", "employee_name"]
    ) or (0, employee)

    if not medical_allow:
        frappe.throw(
            _("Medical Allow is not enabled for Employee {0}. "
              "This Expense Claim cannot be saved.").format(
                  employee_name or employee),
            title=_("Medical Allow — Not Enabled"),
        )


def on_expense_claim_submit(doc, method):
    """
    On Expense Claim submit: deduct medical claim from employee's remaining balance.
    Hook: Expense Claim -> on_submit
    """
    employee = doc.employee
    if not employee:
        return

    if not frappe.db.get_value("Employee", employee, "custom_medical_allow"):
        return

    medical_claim_amount = _get_medical_amount_from_claim(doc)
    if not medical_claim_amount:
        return

    emp = frappe.db.get_value(
        "Employee", employee,
        ["custom_medical_amount", "custom_consumed_medical_amount",
         "custom_remaining_medical_amount", "employee_name"],
        as_dict=True,
    )

    remaining = flt(emp.custom_remaining_medical_amount)

    if medical_claim_amount > remaining:
        frappe.throw(
            _("Medical claim amount {0} exceeds the remaining medical balance "
              "of {1} for Employee {2}. Cannot submit this claim.").format(
                  frappe.format_value(medical_claim_amount, {"fieldtype": "Currency"}),
                  frappe.format_value(remaining,            {"fieldtype": "Currency"}),
                  emp.employee_name,
              ),
            title=_("Insufficient Medical Balance"),
        )

    new_consumed  = flt(emp.custom_consumed_medical_amount) + medical_claim_amount
    new_remaining = flt(emp.custom_medical_amount) - new_consumed

    frappe.db.set_value("Employee", employee, {
        "custom_consumed_medical_amount":  round(new_consumed,  2),
        "custom_remaining_medical_amount": round(new_remaining, 2),
    })

    frappe.msgprint(
        _("Medical balance updated for Employee {0}. "
          "Claimed: {1} | Remaining: {2}").format(
              emp.employee_name,
              frappe.format_value(medical_claim_amount, {"fieldtype": "Currency"}),
              frappe.format_value(new_remaining,        {"fieldtype": "Currency"}),
          ),
        indicator="green",
        title=_("Medical Balance Updated"),
    )


def on_expense_claim_cancel(doc, method):
    """
    On Expense Claim cancel: reverse the medical deduction.
    Hook: Expense Claim -> on_cancel
    """
    employee = doc.employee
    if not employee:
        return

    if not frappe.db.get_value("Employee", employee, "custom_medical_allow"):
        return

    medical_claim_amount = _get_medical_amount_from_claim(doc)
    if not medical_claim_amount:
        return

    emp = frappe.db.get_value(
        "Employee", employee,
        ["custom_medical_amount", "custom_consumed_medical_amount",
         "custom_remaining_medical_amount", "employee_name"],
        as_dict=True,
    )

    new_consumed  = max(0.0, flt(emp.custom_consumed_medical_amount) - medical_claim_amount)
    new_remaining = flt(emp.custom_medical_amount) - new_consumed

    frappe.db.set_value("Employee", employee, {
        "custom_consumed_medical_amount":  round(new_consumed,  2),
        "custom_remaining_medical_amount": round(new_remaining, 2),
    })

    frappe.msgprint(
        _("Medical balance reversed for Employee {0} after claim cancellation. "
          "Restored: {1} | Remaining: {2}").format(
              emp.employee_name,
              frappe.format_value(medical_claim_amount, {"fieldtype": "Currency"}),
              frappe.format_value(new_remaining,        {"fieldtype": "Currency"}),
          ),
        indicator="blue",
        title=_("Medical Balance Reversed"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. SCHEDULED JOBS
# ─────────────────────────────────────────────────────────────────────────────

def auto_check_medical_for_permanent():
    """
    Daily job: Auto-enable Medical Allow for Permanent employees
    who have completed 3+ years from final_confirmation_date.
    Scheduled: daily
    """
    today = getdate(nowdate())
    log   = frappe.logger("medical_logic")

    candidates = frappe.db.sql(
        """
        SELECT   name, employee_name, marital_status, ctc,
                 final_confirmation_date, date_of_joining,
                 custom_consumed_medical_amount
        FROM     `tabEmployee`
        WHERE    status                = 'Active'
          AND    UPPER(employment_type) = 'PERMANENT'
          AND    custom_medical_allow   = 0
          AND    (final_confirmation_date IS NOT NULL OR date_of_joining IS NOT NULL)
        """,
        as_dict=True,
    )

    enabled = 0
    failed  = []

    for emp in candidates:
        ref_date = emp.final_confirmation_date or emp.date_of_joining
        if not ref_date:
            continue

        if today < add_years(getdate(ref_date), 3):
            continue  # Not yet eligible

        try:
            # Calculate amount directly without loading full doc
            ctc            = flt(emp.ctc or 0.0)
            marital_status = (emp.marital_status or "").strip()
            multiplier     = 1.5 if marital_status == "Married" else 1.0
            medical_amount = flt(ctc * multiplier, 2)
            consumed       = flt(emp.custom_consumed_medical_amount or 0.0, 2)
            remaining      = flt(medical_amount - consumed, 2)

            # Save directly to DB — reliable for custom fields
            frappe.db.set_value("Employee", emp.name, {
                "custom_medical_allow":            1,
                "custom_medical_amount":           medical_amount,
                "custom_consumed_medical_amount":  consumed,
                "custom_remaining_medical_amount": remaining,
            })
            enabled += 1

            log.info(
                f"auto_check: Enabled {emp.name} ({emp.employee_name}) | "
                f"CTC={ctc} | {marital_status} | Amount={medical_amount}"
            )

        except Exception as exc:
            failed.append(emp.employee_name)
            log.error(f"auto_check ERROR — {emp.name} ({emp.employee_name}): {exc}")

    if enabled or failed:
        frappe.db.commit()
        log.info(f"auto_check Done | Enabled={enabled} | Failed={len(failed)}")
        if failed:
            log.warning(f"auto_check Failed: {failed}")


def yearly_medical_refresh():
    """
    31 December: Reset consumed to 0 and recalculate medical for all enabled employees.
    Scheduled: daily (internal date check)
    """
    today = getdate(nowdate())
    if not (today.month == 12 and today.day == 31):
        return

    log = frappe.logger("medical_logic")
    log.info("yearly_medical_refresh > Starting (31 Dec)")

    employees = frappe.db.sql(
        """
        SELECT name, employee_name, marital_status, ctc
        FROM   `tabEmployee`
        WHERE  custom_medical_allow = 1
          AND  status = 'Active'
        """,
        as_dict=True,
    )

    if not employees:
        log.info("yearly_medical_refresh — No eligible employees.")
        return

    refreshed = 0
    failed    = []

    for emp in employees:
        try:
            ctc            = flt(emp.ctc or 0.0)
            marital_status = (emp.marital_status or "").strip()
            multiplier     = 1.5 if marital_status == "Married" else 1.0
            medical_amount = flt(ctc * multiplier, 2)

            frappe.db.set_value("Employee", emp.name, {
                "custom_medical_amount":           medical_amount,
                "custom_consumed_medical_amount":  0.0,       # Reset for new year
                "custom_remaining_medical_amount": medical_amount,
            })
            refreshed += 1

        except Exception as exc:
            failed.append(emp.employee_name)
            log.error(f"yearly_refresh ERROR — {emp.name}: {exc}")

    frappe.db.commit()
    log.info(f"yearly_medical_refresh Done | Refreshed={refreshed} | Failed={len(failed)}")
    if failed:
        log.warning(f"yearly_refresh Failed: {failed}")

    _notify_admin_after_refresh(refreshed, failed)


def notify_hr_about_eligible_employees():
    """
    Daily job: Find all employees who are eligible for Medical Allow
    but do NOT have it enabled yet. Creates a Frappe Notification
    for the Administrator so nothing gets missed.

    - Permanent employees: auto_check handles them, but catches any failures.
    - Daily Wages: must be manually enabled by Admin — this is the reminder.

    Scheduled: daily
    """
    today = getdate(nowdate())
    log   = frappe.logger("medical_logic")

    pending = frappe.db.sql("""
        SELECT   name, employee_name, employment_type,
                 final_confirmation_date, date_of_joining, ctc
        FROM     `tabEmployee`
        WHERE    status               = 'Active'
          AND    custom_medical_allow  = 0
          AND    ctc                  > 0
          AND    (final_confirmation_date IS NOT NULL OR date_of_joining IS NOT NULL)
    """, as_dict=True)

    eligible = []
    for emp in pending:
        ref_date = emp.final_confirmation_date or emp.date_of_joining
        if not ref_date:
            continue
        if today >= add_years(getdate(ref_date), 3):
            eligible.append(emp)

    if not eligible:
        return

    # Build notification message
    rows_html = "".join([
        f"<tr><td>{e.name}</td><td>{e.employee_name}</td>"
        f"<td>{e.employment_type}</td></tr>"
        for e in eligible
    ])

    message = f"""
        <p>The following <b>{len(eligible)}</b> employee(s) are eligible for
        <b>Medical Allow</b> but it has not been enabled yet:</p>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;width:100%">
            <thead>
                <tr style="background:#8B1A1A;color:white">
                    <th>Employee ID</th>
                    <th>Name</th>
                    <th>Employment Type</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        <p style="margin-top:10px">Please review and enable Medical Allow
        from each employee's <b>Company Benefits</b> tab.</p>
    """

    # Create Frappe notification for Administrator
    try:
        frappe.get_doc({
            "doctype":   "Notification Log",
            "subject":   f"⚠️ {len(eligible)} Employee(s) Eligible for Medical Allow — Not Yet Enabled",
            "for_user":  "Administrator",
            "type":      "Alert",
            "document_type": "Employee",
            "message":   message,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        log.info(f"notify_hr: Created notification for {len(eligible)} eligible employees.")

    except Exception as exc:
        log.error(f"notify_hr ERROR: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_medical_amount_from_claim(doc) -> float:
    """
    Sum sanctioned amounts for expense lines where expense_type contains 'medical'.
    Falls back to claimed amount if sanctioned_amount is not set.
    """
    total = 0.0
    for line in (doc.expenses or []):
        if "medical" in (line.get("expense_type") or "").lower():
            sanctioned = flt(line.get("sanctioned_amount") or 0.0)
            claimed    = flt(line.get("amount") or 0.0)
            total     += sanctioned if sanctioned else claimed
    return round(total, 2)


def _notify_admin_after_refresh(refreshed: int, failed: list):
    """Email summary to Administrator after 31 Dec refresh. Fails silently."""
    try:
        admin_email = frappe.db.get_value("User", "Administrator", "email") \
                      or "admin@example.com"
        frappe.sendmail(
            recipients=[admin_email],
            subject="Annual Medical Refresh — 31 December",
            message=f"""
                <h3>Annual Medical Refresh Completed</h3>
                <p><b>Date:</b> {getdate(nowdate())}</p>
                <p><b>Refreshed:</b> {refreshed} employees</p>
                <p><b>Failed:</b> {len(failed)} employees</p>
                {"<p><b>Failed:</b> " + ", ".join(failed) + "</p>" if failed else ""}
            """,
        )
    except Exception:
        pass