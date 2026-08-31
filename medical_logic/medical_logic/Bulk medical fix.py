"""
ONE-TIME BULK SCRIPT
Run this ONCE in bench console to auto-enable Medical Allow
for ALL eligible Permanent employees immediately.

Usage:
    bench --site atshr.com console
    exec(open('/path/to/bulk_medical_fix.py').read())

OR paste directly in console:
"""

from frappe.utils import flt, getdate, nowdate, add_years

today = getdate(nowdate())

candidates = frappe.db.sql("""
    SELECT   name, employee_name, marital_status, ctc,
             final_confirmation_date, date_of_joining,
             custom_consumed_medical_amount, custom_medical_allow
    FROM     `tabEmployee`
    WHERE    status                = 'Active'
      AND    UPPER(employment_type) = 'PERMANENT'
      AND    (final_confirmation_date IS NOT NULL OR date_of_joining IS NOT NULL)
""", as_dict=True)

enabled   = []
skipped   = []
no_ctc    = []
not_ready = []

for emp in candidates:
    ref_date = emp.final_confirmation_date or emp.date_of_joining
    if not ref_date:
        skipped.append(emp.employee_name)
        continue

    if today < add_years(getdate(ref_date), 3):
        not_ready.append(emp.employee_name)
        continue

    ctc = flt(emp.ctc or 0.0)
    if not ctc:
        no_ctc.append(emp.employee_name)
        continue

    marital_status = (emp.marital_status or "").strip()
    multiplier     = 1.5 if marital_status == "Married" else 1.0
    medical_amount = flt(ctc * multiplier, 2)
    consumed       = flt(emp.custom_consumed_medical_amount or 0.0, 2)
    remaining      = flt(medical_amount - consumed, 2)

    frappe.db.set_value("Employee", emp.name, {
        "custom_medical_allow":            1,
        "custom_medical_amount":           medical_amount,
        "custom_consumed_medical_amount":  consumed,
        "custom_remaining_medical_amount": remaining,
    })
    enabled.append(f"{emp.employee_name} → {medical_amount:,.2f} ({marital_status or 'Single'})")

frappe.db.commit()

print("\n" + "="*60)
print(f"✅ ENABLED  ({len(enabled)})")
for e in enabled:
    print(f"   {e}")

if no_ctc:
    print(f"\n⚠️  NO CTC SET ({len(no_ctc)}) — skipped:")
    for e in no_ctc:
        print(f"   {e}")

if not_ready:
    print(f"\n⏳ NOT YET 3 YEARS ({len(not_ready)}) — skipped")

if skipped:
    print(f"\n❌ NO DATE ({len(skipped)}) — skipped")

print("="*60 + "\n")