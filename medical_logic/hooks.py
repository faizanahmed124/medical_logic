vapp_name        = "medical_logic"
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
            "medical_logic.medical_logic.ctc_to_basic.set_basic_pay",
            "medical_logic.medical_logic.Gratuity_calculation.calculate_gratuity",
        ],
        # Fires after every save — auto-enables Medical Allow if eligible
        "on_update": [
            "medical_logic.medical_logic.medical_logic.auto_check_on_employee_update",
        ],
    },
    "Expense Claim": {
        "on_submit": "medical_logic.medical_logic.medical_logic.on_expense_claim_submit",
        "on_cancel": "medical_logic.medical_logic.medical_logic.on_expense_claim_cancel",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Scheduler Events
# ─────────────────────────────────────────────────────────────────────────────

scheduler_events = {
    "daily": [
        # Backup bulk job — catches any employees missed by on_update
        "medical_logic.medical_logic.medical_logic.auto_check_medical_for_permanent",
        # 31 Dec annual reset
        "medical_logic.medical_logic.medical_logic.yearly_medical_refresh",
    ],
}