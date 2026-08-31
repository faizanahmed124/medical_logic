import frappe
from frappe.utils import flt


def set_basic_pay(doc, method=None):
    """
    Employee ke employment_type ke hisaab se CTC aur custom_basic_pay
    ko ek doosre se auto-calculate karta hai.

    Jo field is dafa user ne change ki hai, usi se doosri field calculate hogi.
    Dono fields ki value round-off (whole number) rakhi jati hai.
    """

    employment_type = (doc.get("employment_type") or "").strip().upper()

    if employment_type not in ("PERMANENT", "DAILY WAGES"):
        return

    ctc_changed = doc.has_value_changed("ctc")
    basic_changed = doc.has_value_changed("custom_basic_pay")

    ctc = flt(doc.get("ctc"))
    basic_pay = flt(doc.get("custom_basic_pay"))

    if employment_type == "PERMANENT":
        if ctc_changed or (not basic_changed and ctc):
            doc.custom_basic_pay = round(ctc * 0.85)
        elif basic_changed and basic_pay:
            doc.ctc = round(basic_pay / 0.85)

    elif employment_type == "DAILY WAGES":
        if ctc_changed or (not basic_changed and ctc):
            doc.custom_basic_pay = round(ctc / 30)
        elif basic_changed and basic_pay:
            doc.ctc = round(basic_pay * 30)