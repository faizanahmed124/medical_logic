# Copyright (c) 2026, Faizan and contributors
# For license information, please see license.txt

import re

import frappe

VEHICLES = ("Car", "Bike")
RUNNING = ("Fuel", "Maintenance")  # benefits that belong to a vehicle

# Custom fields on the "Benefit" child table (added from Customize Form)
VEHICLE_FIELD = "custom_vehicle"     # Select: Car / Bike  (for Fuel / Maintenance rows)
OWNER_FIELD = "custom_owned_by"      # Select: Company / Self

# Words in the "Type" text that tell which vehicle it is
BIKE_WORDS = re.compile(r"\b(bike|motor\s*cycle|motorcycle|motorbike|honda\s*(cd|125|70)|cd\s*70)\b", re.I)
CAR_WORDS = re.compile(r"\b(car|vitz|civic|corolla|city|cultus|alto|mehran|suzuki|toyota|honda\s*city)\b", re.I)


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    if "Maintenance" in (filters.get("benefit") or ""):
        columns = [c for c in columns if c["fieldname"] != "type"]
    return columns, get_data(filters)


def get_columns():
    return [
        {"label": "Employee ID", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 110},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 160},
        {"label": "Designation", "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},
        {"label": "Issue Date", "fieldname": "issue_date", "fieldtype": "Date", "width": 100},
        {"label": "Benefit Category", "fieldname": "category", "fieldtype": "Data", "width": 190},
        {"label": "Item / Qty", "fieldname": "type", "fieldtype": "Data", "width": 160},
        {"label": "Owned By", "fieldname": "owned_by", "fieldtype": "Data", "width": 100},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
    ]


def _clean(v):
    return " ".join(str(v or "").split())


def _norm_benefit(v):
    """'fuel ', 'FUEL' -> 'Fuel'; unknown values are kept as they are."""
    v = _clean(v)
    for known in ("Mobile", "Car", "Bike", "Fuel", "Maintenance"):
        if v.lower() == known.lower():
            return known
    return v or "Not Set"


def _vehicle_from_text(text):
    """'Bike Maintenance' -> Bike, 'CAR MAINTENANCE' -> Car, '38 Ltrs' -> ''."""
    if BIKE_WORDS.search(text or ""):
        return "Bike"
    if CAR_WORDS.search(text or ""):
        return "Car"
    return ""


def get_data(filters):
    meta = frappe.get_meta("Benefit")
    has_vehicle = meta.has_field(VEHICLE_FIELD)
    has_owner = meta.has_field(OWNER_FIELD)

    conditions = ["e.status = 'Active'", "ob.parenttype = 'Employee'"]
    values = {}
    if filters.get("employee"):
        conditions.append("e.name = %(employee)s")
        values["employee"] = filters.employee
    if filters.get("department"):
        conditions.append("e.department = %(department)s")
        values["department"] = filters.department

    extra = ""
    if has_vehicle:
        extra += f", ob.`{VEHICLE_FIELD}` AS vehicle"
    if has_owner:
        extra += f", ob.`{OWNER_FIELD}` AS owner_field"

    rows = frappe.db.sql(
        "SELECT e.name AS employee, e.employee_name, e.department, e.designation, "
        "ob.issue_date, ob.type, ob.benefit, ob.amount" + extra + " "
        "FROM `tabEmployee` e INNER JOIN `tabBenefit` ob ON ob.parent = e.name "
        "WHERE " + " AND ".join(conditions) + " "
        "ORDER BY e.employee_name, ob.idx",
        values,
        as_dict=True,
    )

    emp_owner = {}  # employee -> {vehicle: owner} from Car / Bike rows
    emp_seen = {}   # employee -> vehicles known from any row
    for r in rows:
        r.benefit = _norm_benefit(r.benefit)
        r.vehicle = _clean(r.get("vehicle"))
        r.owner_field = _clean(r.get("owner_field"))
        if r.benefit in VEHICLES:
            r.vehicle = r.benefit
            emp_owner.setdefault(r.employee, {})[r.benefit] = r.owner_field or "Company"
        elif r.benefit in RUNNING and not r.vehicle:
            # "Bike Maintenance" / "CAR MAINTENANCE" written in Type
            r.vehicle = _vehicle_from_text(r.type)
        if r.vehicle:
            emp_seen.setdefault(r.employee, set()).add(r.vehicle)

    out = []
    for r in rows:
        owners = emp_owner.get(r.employee, {})
        seen = emp_seen.get(r.employee, set())
        if r.benefit in VEHICLES:
            r.owned_by = r.owner_field or "Company"
            r.category = r.benefit
        elif r.benefit in RUNNING:
            # Still unknown: use the employee's only vehicle (e.g. fuel of the same bike)
            if not r.vehicle and len(seen) == 1:
                r.vehicle = next(iter(seen))
            # Owner: from the row, else the employee's vehicle row, else the employee's own vehicle
            r.owned_by = r.owner_field or owners.get(r.vehicle) or "Self"
            r.category = f"{r.vehicle} {r.benefit}" if r.vehicle else r.benefit
        else:
            r.owned_by = ""
            r.category = r.benefit

        if _match(r, filters):
            out.append(r)
    return out


def _match(r, filters):
    want = (filters.get("benefit") or "All").strip()
    if want == "All":
        return True
    if want.startswith("Self "):  # "Self Fuel" / "Self Maintenance"
        return r.benefit == want[5:] and r.owned_by == "Self"
    if " " in want:  # e.g. "Car Fuel", "Bike Maintenance"
        vehicle, benefit = want.split(" ", 1)
        return r.vehicle == vehicle and r.benefit == benefit
    return r.benefit == want