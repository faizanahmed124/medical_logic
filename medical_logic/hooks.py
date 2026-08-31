app_name        = "medical_logic"
app_title       = "Medical Logic"
app_publisher   = "Faizan"
app_description = "App for logic of medical billing"
app_email       = "Faizanahmed1295@gmail.com"
app_license     = "mit"

# ─────────────────────────────────────────────────────────────────────────────
# Installation
# ─────────────────────────────────────────────────────────────────────────────

after_install = "medical_logic.medical_logic.install.after_install"

# ─────────────────────────────────────────────────────────────────────────────
# Document Events
# ─────────────────────────────────────────────────────────────────────────────

doc_events = {
    "Employee": {
        "validate": [
            "medical_logic.medical_logic.medical_logic.validate_medical_allow",
            "medical_logic.medical_logic.medical_logic.calculate_medical_amount",
            # Warn Administrator if employee is eligible but Medical Allow not enabled
            "medical_logic.medical_logic.medical_logic.warn_if_eligible_not_enabled",
            "medical_logic.medical_logic.ctc_to_basic.set_basic_pay",
            "medical_logic.medical_logic.Gratuity_calculation.calculate_gratuity",
        ],
        "on_update": [
            "medical_logic.medical_logic.medical_logic.auto_check_on_employee_update",
        ],
    },
    "Expense Claim": {
        # Block save if employee doesn't have Medical Allow
        "validate":  "medical_logic.medical_logic.medical_logic.validate_expense_claim_medical",
        "on_submit": "medical_logic.medical_logic.medical_logic.on_expense_claim_submit",
        "on_cancel": "medical_logic.medical_logic.medical_logic.on_expense_claim_cancel",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Scheduler Events
# ─────────────────────────────────────────────────────────────────────────────

scheduler_events = {
    "daily": [
        # Auto-enable Medical Allow for eligible Permanent employees
        "medical_logic.medical_logic.medical_logic.auto_check_medical_for_permanent",
        # Notify Administrator about eligible employees who are still not enabled
        "medical_logic.medical_logic.medical_logic.notify_hr_about_eligible_employees",
        # 31 Dec annual reset
        "medical_logic.medical_logic.medical_logic.yearly_medical_refresh",
    ],
}