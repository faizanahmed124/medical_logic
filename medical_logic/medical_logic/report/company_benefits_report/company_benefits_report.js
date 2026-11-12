// Copyright (c) 2026, Faizan and contributors
// For license information, please see license.txt

frappe.query_reports["Company Benefits Report"] = {
	"filters": [
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department"
		},
		{
			"fieldname": "benefit",
			"label": __("Benefit Type"),
			"fieldtype": "Select",
			"options": "All\nMobile\nCar\nBike\nCar Fuel\nBike Fuel\nCar Maintenance\nBike Maintenance\nSelf Fuel\nSelf Maintenance",
			"default": "All"
		}
	],
	onload: function (report) {
		report.page.add_inner_button(__("Print"), function () {
			print_benefits_report(report);
		});
	}
};

function cbr_esc(value) {
	if (value === null || value === undefined) return "";
	return String(value)
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;");
}

function print_benefits_report(report) {
	const data = report.data || [];
	let f = {};
	try {
		f = report.get_filter_values ? report.get_filter_values() : {};
	} catch (e) {
		f = {};
	}

	const logo = window.location.origin + "/files/ats.jpeg";
	const company = "ATS Synthetic (Pvt) Ltd";
	const printed_by = frappe.session.user_fullname || frappe.session.user;
	const now_long = moment().format("dddd, DD-MMMM-YYYY hh:mm a");
	const d = function (v) { return v ? frappe.datetime.str_to_user(v) : ""; };
	const money = function (v) { return format_number(v || 0, null, 0); };
	const show_qty = (f.benefit || "").indexOf("Maintenance") === -1;

	let total = 0;
	let rows_html = "";
	data.forEach(function (r, i) {
		total += flt(r.amount);
		rows_html +=
			"<tr>" +
			"<td>" + (i + 1) + "</td>" +
			"<td>" + cbr_esc(r.employee) + "</td>" +
			"<td><b>" + cbr_esc(r.employee_name) + "</b></td>" +
			"<td>" + cbr_esc(r.department) + "</td>" +
			"<td>" + cbr_esc(r.designation) + "</td>" +
			"<td class='nw'>" + d(r.issue_date) + "</td>" +
			"<td>" + cbr_esc((r.category || "").replace(" - Self", "")) + "</td>" +
			(show_qty ? "<td>" + cbr_esc(r.type) + "</td>" : "") +
			"<td>" + cbr_esc(r.owned_by) + "</td>" +
			"<td class='num'>" + money(r.amount) + "</td>" +
			"</tr>";
	});
	if (!data.length) {
		rows_html = "<tr><td colspan='10' class='empty'>No benefits found for the selected filters.</td></tr>";
	} else {
		rows_html +=
			"<tr class='tot'><td colspan='" + (show_qty ? 9 : 8) + "'>Total (" + data.length + " rows)</td>" +
			"<td class='num'>" + money(total) + "</td></tr>";
	}

	const css =
		"@page { size: A4 landscape; margin: 8mm; }" +
		"body { margin: 0; }" +
		".le { font-family: Arial, Helvetica, sans-serif; font-size: 9.5px; color: #111; }" +
		".le, .le * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }" +
		".le table { width: 100%; border-collapse: collapse; }" +
		".le .hdr td { border: 1px solid #222; vertical-align: middle; }" +
		".le .logo-cell { width: 15%; padding: 4px; text-align: center; }" +
		".le .logo { width: 100%; height: 92px; object-fit: contain; display: block; }" +
		".le .band { background: #ececec; color: #222; font-size: 20px; font-weight: bold; text-align: center; padding: 11px; letter-spacing: .5px; }" +
		".le .ttl { text-align: center; padding: 10px; }" +
		".le .ttl span { font-size: 16px; font-weight: bold; text-decoration: underline; }" +
		".le .meta td { border: 1px solid #222; border-top: none; padding: 7px 8px; font-size: 9px; }" +
		".le .meta .m1 { width: 40%; }" +
		".le .meta .m2 { width: 32%; background: #f4f4f4; }" +
		".le .meta .m3 { text-align: right; }" +
		".le .info td { padding: 5px 4px; font-size: 9px; }" +
		".le .grid { margin-top: 4px; }" +
		".le .grid th { border-bottom: 1.5px solid #111; text-align: left; padding: 5px 4px; font-size: 9.5px; font-weight: bold; color: #111; white-space: nowrap; }" +
		".le .grid td { padding: 6px 4px; border-bottom: 1px dashed #777; vertical-align: top; }" +
		".le .num { text-align: right; white-space: nowrap; }" +
		".le .nw { white-space: nowrap; }" +
		".le .tot td { font-weight: bold; border-top: 1.5px solid #111; border-bottom: 1.5px solid #111; }" +
		".le .empty { text-align: center; padding: 20px; color: #777; }" +
		".le .signs { margin-top: 50px; page-break-inside: avoid; }" +
		".le .signs td { text-align: center; width: 33%; padding: 0 10px; }" +
		".le .signs span { display: inline-block; border-top: 1px solid #111; padding-top: 3px; width: 70%; }";

	const html =
		"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Company Benefits Report</title>" +
		"<style>" + css + "</style></head><body><div class='le'>" +
		"<table class='hdr'>" +
		"<tr><td class='logo-cell' rowspan='2'><img class='logo' src='" + logo + "' alt='ATS'></td>" +
		"<td class='band'>" + cbr_esc(company) + "</td></tr>" +
		"<tr><td class='ttl'><span>Company Benefits Report</span></td></tr>" +
		"</table>" +
		"<table class='meta'><tr>" +
		"<td class='m1'>" + cbr_esc(now_long) + "</td>" +
		"<td class='m2'>Printed By &nbsp;|&nbsp; " + cbr_esc(printed_by) + "</td>" +
		"<td class='m3'>Benefit &nbsp;|&nbsp; <b>" + cbr_esc(f.benefit || "All") + "</b></td>" +
		"</tr></table>" +
		"<table class='info'><tr>" +
		"<td>Department: <b>" + cbr_esc(f.department || "All") + "</b></td>" +
		"<td style='text-align:center;'>Employee: <b>" + cbr_esc(f.employee || "All") + "</b></td>" +
		"<td></td>" +
		"</tr></table>" +
		"<table class='grid'><thead><tr>" +
		"<th>Sr.No</th><th>Code</th><th>Name</th><th>Department</th><th>Designation</th>" +
		"<th>Issue Date</th><th>Benefit</th>" + (show_qty ? "<th>Item / Qty</th>" : "") + "<th>Owned By</th><th class='num'>Amount</th>" +
		"</tr></thead><tbody>" + rows_html + "</tbody></table>" +
		"<table class='signs'><tr>" +
		"<td><span>Prepared By</span></td><td><span>HR Manager</span></td><td><span>General Manager</span></td>" +
		"</tr></table>" +
		"</div></body></html>";

	const win = window.open("", "_blank");
	win.document.open();
	win.document.write(html);
	win.document.close();
	win.focus();
	setTimeout(function () {
		win.print();
	}, 500);
}