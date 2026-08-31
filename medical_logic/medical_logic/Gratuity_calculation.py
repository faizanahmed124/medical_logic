import frappe
from frappe.utils import getdate, date_diff, flt


def calculate_gratuity(doc, method=None):
    """
    Employee ki Gratuity calculate karta hai.

    - Daily Wages employees: koi Gratuity nahi.
    - Permanent employees:
        - final_confirmation_date se aaj tak agar 2 saal se kam guzre hain -> Gratuity 0, allow = unchecked.
        - 2 saal ya zyada guzre hain -> custom_gratuity_allow khud check ho jayega.
        - Gratuity = (ctc * 0.80) * rounded_years_since_confirmation
        - Rounding: 6 ya zyada extra months -> agle saal mein round-up
                    6 se kam extra months -> round-down (floor)
    """

    employment_type = (doc.get("employment_type") or "").strip().upper()

    # Daily Wages ke liye koi gratuity nahi
    if employment_type != "PERMANENT":
        doc.custom_gratuity_allow = 0
        doc.custom_total_gratuity = 0
        return

    final_confirmation_date = doc.get("final_confirmation_date")

    if not final_confirmation_date:
        doc.custom_gratuity_allow = 0
        doc.custom_total_gratuity = 0
        return

    today = getdate()
    confirmation_date = getdate(final_confirmation_date)

    # Total months guzre hain confirmation date se aaj tak
    total_months = (today.year - confirmation_date.year) * 12 + (today.month - confirmation_date.month)
    if today.day < confirmation_date.day:
        total_months -= 1

    if total_months < 0:
        total_months = 0

    full_years = total_months // 12
    extra_months = total_months % 12

    years_since_confirmation = full_years + (extra_months / 12.0)

    # 2 saal se kam -> koi gratuity nahi
    if years_since_confirmation < 2:
        doc.custom_gratuity_allow = 0
        doc.custom_total_gratuity = 0
        return

    # 2 saal ya zyada -> gratuity allow khud mark ho jayega
    doc.custom_gratuity_allow = 1

    # Rounding rule: 6+ extra months -> round up, warna round down
    if extra_months >= 6:
        rounded_years = full_years + 1
    else:
        rounded_years = full_years

    ctc = flt(doc.get("ctc"))
    gratuity_per_year = ctc * 0.80

    doc.custom_total_gratuity = gratuity_per_year * rounded_years