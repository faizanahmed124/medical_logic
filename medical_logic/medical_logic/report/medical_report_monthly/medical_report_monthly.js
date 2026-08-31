// medical_logic/medical_logic/report/medical_report_monthly/medical_report_monthly.js

frappe.query_reports["Medical Report Monthly"] = {

    // ── Filters ───────────────────────────────────────────────────────────────
    filters: [
        {
            fieldname: "bill_of_month",
            label:     __("Bill of Month"),
            fieldtype: "Select",
            options: [
                "",
                "January","February","March","April","May","June",
                "July","August","September","October","November","December",
            ].join("\n"),
        },
        {
            fieldname: "employee",
            label:     __("Employee"),
            fieldtype: "Link",
            options:   "Employee",
            get_query: function() { return { filters: { status: "Active" } }; },
        },
        {
            fieldname: "department",
            label:     __("Department"),
            fieldtype: "Link",
            options:   "Department",
        },
        {
            fieldname: "approval_status",
            label:     __("Status"),
            fieldtype: "Select",
            options:   "\nDraft\nApproved\nRejected",
        },
    ],

    // ── Print Button ──────────────────────────────────────────────────────────
    onload: function(report) {
        report.page.add_inner_button(__("🖨️  Print"), function() {
            var data    = frappe.query_report.data;
            var columns = frappe.query_report.columns;

            if (!data || !data.length) {
                frappe.msgprint(__("No data to print."));
                return;
            }

            // Print columns — exclude remaining_medical (balance shown in summary only)
            var print_cols = columns.filter(function(c) {
                return c.fieldname !== "remaining_medical";
            });

            // Active filters line
            var fv           = frappe.query_report.get_filter_values();
            var filters_html = Object.keys(fv)
                .filter(function(k) { return fv[k]; })
                .map(function(k) {
                    return `<span style="margin-right:18px"><b>${__(k.replace(/_/g," "))}:</b> ${fv[k]}</span>`;
                }).join("");

            // Table header
            var thead = "<tr>" + print_cols.map(function(col) {
                return `<th>${__(col.label)}</th>`;
            }).join("") + "</tr>";

            // Table rows
            var grand_total = 0;
            var tbody = data.map(function(row) {
                grand_total += parseFloat(row["medical_claimed"] || 0);
                return "<tr>" + print_cols.map(function(col) {
                    var val = row[col.fieldname];
                    if (val == null) val = "";
                    if (col.fieldtype === "Currency") {
                        val = "Rs " + parseFloat(val || 0).toLocaleString("en-PK", {
                            minimumFractionDigits: 2, maximumFractionDigits: 2
                        });
                    }
                    if (col.fieldtype === "Date" && val) {
                        val = frappe.datetime.str_to_user(val);
                    }
                    return `<td>${val}</td>`;
                }).join("") + "</tr>";
            }).join("");

            // Grand total row
            var total_cols_html = print_cols.map(function(col, i) {
                if (col.fieldname === "medical_claimed") {
                    return `<td style="font-weight:bold;color:#5E64FF">Rs ${grand_total.toLocaleString("en-PK",{minimumFractionDigits:2,maximumFractionDigits:2})}</td>`;
                } else if (i === 0) {
                    return `<td style="font-weight:bold">Total</td>`;
                } else {
                    return `<td></td>`;
                }
            }).join("");

            var print_html = `
            <html>
            <head>
                <title>Medical Report Monthly</title>
                <style>
                    body   { font-family: Arial, sans-serif; font-size: 11px; margin: 20px; }
                    h2     { text-align: center; margin-bottom: 2px; font-size: 14px; }
                    h3     { text-align: center; margin: 0 0 4px; font-size: 12px; color:#333; }
                    .meta  { text-align: center; font-size: 10px; color:#777; margin-bottom:10px; }
                    .flt   { font-size: 10px; color:#444; margin-bottom:8px; }
                    table  { width:100%; border-collapse:collapse; }
                    th     { background:#4472C4; color:#fff; padding:6px 8px;
                             text-align:left; font-size:10px; }
                    td     { padding:5px 8px; border-bottom:1px solid #ddd; font-size:10px; }
                    tr:nth-child(even) td { background:#f5f7ff; }
                    .total-row td { background:#e8ecff !important; }
                    @media print { @page { size: A4 landscape; margin: 10mm; } }
                </style>
            </head>
            <body>
                <h2>Employee Monthly Medical Report.</h2>
                <h3>Medical Report Monthly</h3>
                <div class="meta">Printed: ${frappe.datetime.now_datetime()}</div>
                <div class="flt">${filters_html}</div>
                <table>
                    <thead>${thead}</thead>
                    <tbody>
                        ${tbody}
                        <tr class="total-row">${total_cols_html}</tr>
                    </tbody>
                </table>
            </body>
            </html>`;

            var w = window.open("", "_blank");
            w.document.write(print_html);
            w.document.close();
            w.focus();
            setTimeout(function() { w.print(); }, 500);
        });
    },

    // ── Row Formatting ────────────────────────────────────────────────────────
    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "medical_claimed" && data && data.medical_claimed > 0) {
            value = `<span style="color:#5E64FF;font-weight:bold">${value}</span>`;
        }

        if (column.fieldname === "remaining_medical" && data) {
            var color = (data.remaining_medical <= 0) ? "#E74C3C" : "#27AE60";
            value = `<span style="color:${color};font-weight:bold">${value}</span>`;
        }

        return value;
    },
};