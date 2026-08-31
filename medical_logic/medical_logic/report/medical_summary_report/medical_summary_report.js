// medical_logic/medical_logic/report/medical_summary_report/medical_summary_report.js

frappe.query_reports["Medical Summary Report"] = {

    filters: [
        {
            fieldname:  "year",
            label:      __("Year"),
            fieldtype:  "Select",
            options:    get_year_options(),
            default:    frappe.datetime.get_today().split("-")[0],
            reqd:       1,
        },
        {
            fieldname: "from_month",
            label:     __("From Month"),
            fieldtype: "Select",
            options: [
                "",
                "January","February","March","April","May","June",
                "July","August","September","October","November","December",
            ].join("\n"),
        },
        {
            fieldname: "to_month",
            label:     __("To Month"),
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
        },
        {
            fieldname: "department",
            label:     __("Department"),
            fieldtype: "Link",
            options:   "Department",
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

            var fv = frappe.query_report.get_filter_values();
            var filters_html = Object.keys(fv)
                .filter(k => fv[k])
                .map(k => `<span style="margin-right:18px"><b>${__(k.replace(/_/g," "))}:</b> ${fv[k]}</span>`)
                .join("");

            var thead = "<tr>" + columns.map(c => `<th>${__(c.label)}</th>`).join("") + "</tr>";

            var grand_total = 0;
            var tbody = data.map(function(row) {
                grand_total += parseFloat(row["total_claimed"] || 0);
                return "<tr>" + columns.map(function(col) {
                    var val = row[col.fieldname];
                    if (val == null) val = "";
                    if (col.fieldtype === "Currency") {
                        val = "Rs " + parseFloat(val || 0).toLocaleString("en-PK", {
                            minimumFractionDigits: 2, maximumFractionDigits: 2
                        });
                    }
                    return `<td>${val}</td>`;
                }).join("") + "</tr>";
            }).join("");

            // Grand total row
            var total_row = columns.map(function(col, i) {
                if (col.fieldname === "total_claimed") {
                    return `<td style="font-weight:bold;color:#5E64FF">Rs ${grand_total.toLocaleString("en-PK",{minimumFractionDigits:2,maximumFractionDigits:2})}</td>`;
                } else if (i === 0) {
                    return `<td style="font-weight:bold">Grand Total</td>`;
                }
                return "<td></td>";
            }).join("");

            var print_html = `
            <html><head><title>Medical Summary Report</title>
            <style>
                body   { font-family:Arial,sans-serif; font-size:11px; margin:20px; }
                h2     { text-align:center; font-size:15px; margin-bottom:2px; }
                h3     { text-align:center; font-size:12px; color:#444; margin:0 0 4px; }
                .meta  { text-align:center; font-size:10px; color:#999; margin-bottom:10px; }
                .flt   { font-size:10px; color:#555; margin-bottom:10px; }
                table  { width:100%; border-collapse:collapse; }
                th     { background:#4472C4; color:#fff; padding:7px 10px; text-align:left; font-size:11px; }
                td     { padding:6px 10px; border-bottom:1px solid #eee; font-size:11px; }
                tr:nth-child(even) td { background:#f5f7ff; }
                .total-row td { background:#e8ecff!important; font-weight:bold; }
                @media print { @page { size:A4 landscape; margin:10mm; } }
            </style></head>
            <body>
                <h2>ATS SYNTHETIC (PVT.) LTD.</h2>
                <h3>Medical Summary Report</h3>
                <div class="meta">Printed: ${frappe.datetime.now_datetime()}</div>
                <div class="flt">${filters_html}</div>
                <table>
                    <thead>${thead}</thead>
                    <tbody>${tbody}<tr class="total-row">${total_row}</tr></tbody>
                </table>
            </body></html>`;

            var w = window.open("", "_blank");
            w.document.write(print_html);
            w.document.close();
            w.focus();
            setTimeout(() => w.print(), 500);
        });
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname === "total_claimed" && data && data.total_claimed > 0) {
            value = `<span style="color:#5E64FF;font-weight:bold">${value}</span>`;
        }
        return value;
    },
};

function get_year_options() {
    var current = parseInt(frappe.datetime.get_today().split("-")[0]);
    var opts = [];
    for (var y = current; y >= current - 5; y--) opts.push(y);
    return opts.join("\n");
}