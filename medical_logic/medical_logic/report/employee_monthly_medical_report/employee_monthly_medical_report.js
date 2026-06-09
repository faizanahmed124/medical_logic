// Copyright (c) 2026, Your Company
// Licence: MIT

frappe.query_reports["Employee Monthly Medical Report"] = {

	// ── Filters ────────────────────────────────────────────────────────────────
	filters: [
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: function () {
				let dept = frappe.query_report.get_filter_value("department");
				return dept ? { filters: { department: dept } } : {};
			},
		},
		{
			fieldname: "approval_status",
			label: __("Approval Status"),
			fieldtype: "Select",
			options: "\nDraft\nSubmitted\nApproved\nRejected",
			default: "Approved",
		},
	],

	// ── Cell Formatter ─────────────────────────────────────────────────────────
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "balance" && data) {
			if (data.balance < 0) {
				value = `<span style="color:var(--red-500);font-weight:700;">${value}</span>`;
			} else if (data.balance > 0) {
				value = `<span style="color:var(--green-500);font-weight:700;">${value}</span>`;
			}
		}

		if (column.fieldname === "medical_allowance" && data) {
			value = `<b>${value}</b>`;
		}

		if (column.fieldname === "total_claimed" && data) {
			value = `<b>${value}</b>`;
		}

		return value;
	},

	// ── Buttons ────────────────────────────────────────────────────────────────
	onload(report) {

		// Export Excel
		report.page.add_inner_button(__("Export Excel"), () => {
			report.datatable && report.export_report("Excel");
		});

		// Print Report
		report.page.add_inner_button(__("Print Report"), () => {
			const data    = report.data;
			const filters = report.get_values();

			if (!data || !data.length) {
				frappe.msgprint(__("No data to print. Please run the report first."));
				return;
			}

			// Month column fieldnames in order
			const months = [
				{ key: "jul_2025", label: "Jul 2025" },
				{ key: "aug_2025", label: "Aug 2025" },
				{ key: "sep_2025", label: "Sep 2025" },
				{ key: "oct_2025", label: "Oct 2025" },
				{ key: "nov_2025", label: "Nov 2025" },
				{ key: "dec_2025", label: "Dec 2025" },
				{ key: "jan_2026", label: "Jan 2026" },
				{ key: "feb_2026", label: "Feb 2026" },
				{ key: "mar_2026", label: "Mar 2026" },
				{ key: "apr_2026", label: "Apr 2026" },
				{ key: "may_2026", label: "May 2026" },
				{ key: "jun_2026", label: "Jun 2026" },
			];

			const fmt = (n) =>
				Number(n || 0).toLocaleString("en-PK", {
					minimumFractionDigits: 0,
					maximumFractionDigits: 0,
				});

			// Totals row
			const totals = { medical_allowance: 0, total_claimed: 0, balance: 0 };
			months.forEach(m => (totals[m.key] = 0));
			data.forEach(row => {
				totals.medical_allowance += Number(row.medical_allowance || 0);
				totals.total_claimed     += Number(row.total_claimed     || 0);
				totals.balance           += Number(row.balance           || 0);
				months.forEach(m => (totals[m.key] += Number(row[m.key] || 0)));
			});

			// Table rows HTML
			const rows = data.map((row, i) => {
				const balClass = row.balance < 0 ? "neg" : row.balance > 0 ? "pos" : "";
				const monthCells = months
					.map(m => `<td>${row[m.key] ? fmt(row[m.key]) : "—"}</td>`)
					.join("");
				return `
					<tr class="${i % 2 === 0 ? "even" : "odd"}">
						<td class="center">${i + 1}</td>
						<td class="emp-id">${row.employee}</td>
						<td>${row.employee_name}</td>
						<td>${row.department || "—"}</td>
						<td class="num">${fmt(row.medical_allowance)}</td>
						${monthCells}
						<td class="num bold">${fmt(row.total_claimed)}</td>
						<td class="num ${balClass}">${fmt(row.balance)}</td>
					</tr>`;
			}).join("");

			const totalMonthCells = months
				.map(m => `<td class="num bold">${fmt(totals[m.key])}</td>`)
				.join("");

			const dept   = filters.department    || "All Departments";
			const emp    = filters.employee       || "All Employees";
			const status = filters.approval_status || "All";
			const today  = frappe.datetime.now_date();

			const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Employee Monthly Medical Report</title>
<style>
  @page { size: A3 landscape; margin: 14mm 10mm; }
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 9px;
    color: #1a1a2e;
    background: #fff;
  }

  /* ── Header ── */
  .header {
    text-align: center;
    padding: 18px 0 12px;
    border-bottom: 2.5px solid #1a4fa0;
    margin-bottom: 10px;
  }
  .header .company {
    font-size: 20px;
    font-weight: 700;
    color: #1a4fa0;
    letter-spacing: -0.3px;
  }
  .header .report-title {
    font-size: 12px;
    font-weight: 600;
    color: #374151;
    margin-top: 3px;
  }
  .header .period {
    font-size: 9px;
    color: #6b7280;
    margin-top: 2px;
  }
  .header .meta-row {
    margin-top: 6px;
    font-size: 8.5px;
    color: #6b7280;
  }
  .header .meta-row span { color: #374151; font-weight: 600; }
  .badge {
    display: inline-block;
    background: #e8f0fe;
    color: #1a4fa0;
    font-size: 8px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 10px;
    margin-bottom: 4px;
  }
  /* ── Summary Cards ── */
  .summary {
    display: flex;
    gap: 8px;
    margin-bottom: 10px;
  }
  .card {
    flex: 1;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 8px 10px;
    background: #f9fafb;
  }
  .card .c-label { font-size: 8px; color: #6b7280; margin-bottom: 2px; }
  .card .c-value { font-size: 14px; font-weight: 700; color: #1a4fa0; }
  .card.green  .c-value { color: #059669; }
  .card.red    .c-value { color: #dc2626; }
  .card.orange .c-value { color: #d97706; }

  /* ── Table ── */
  table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
  }
  colgroup col.c-sr   { width: 24px; }
  colgroup col.c-id   { width: 60px; }
  colgroup col.c-name { width: 90px; }
  colgroup col.c-dept { width: 70px; }
  colgroup col.c-sal  { width: 52px; }
  colgroup col.c-mon  { width: 42px; }
  colgroup col.c-tot  { width: 52px; }
  colgroup col.c-bal  { width: 52px; }

  thead tr th {
    background: #1a4fa0;
    color: #fff;
    font-size: 8px;
    font-weight: 600;
    padding: 5px 4px;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  thead tr.sub-head th {
    background: #2563eb;
    color: #dbeafe;
    font-size: 7.5px;
    padding: 3px 3px;
  }
  tbody tr.even { background: #f8faff; }
  tbody tr.odd  { background: #ffffff; }
  tbody tr:hover { background: #eff6ff; }

  td {
    font-size: 8px;
    padding: 4px 4px;
    border-bottom: 0.5px solid #e5e7eb;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #374151;
  }
  td.center { text-align: center; color: #9ca3af; }
  td.emp-id  { font-family: monospace; font-size: 7.5px; color: #1a4fa0; }
  td.num     { text-align: right; font-variant-numeric: tabular-nums; }
  td.bold    { font-weight: 700; }
  td.pos     { color: #059669; font-weight: 700; }
  td.neg     { color: #dc2626; font-weight: 700; }

  tfoot tr td {
    background: #1e3a6e;
    color: #fff;
    font-size: 8.5px;
    font-weight: 700;
    padding: 5px 4px;
    text-align: right;
    border: none;
  }
  tfoot tr td:first-child { text-align: center; }
  tfoot tr td.pos { color: #6ee7b7; }
  tfoot tr td.neg { color: #fca5a5; }

  /* ── Footer ── */
  .footer {
    margin-top: 12px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-top: 1px solid #e5e7eb;
    padding-top: 8px;
    font-size: 8px;
    color: #9ca3af;
  }
  .sig-block { text-align: center; }
  .sig-line  { border-top: 1px solid #374151; width: 120px; margin: 20px auto 3px; }
  .sig-name  { font-size: 8px; color: #374151; font-weight: 600; }
  .sig-title { font-size: 7.5px; color: #9ca3af; }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="badge">CONFIDENTIAL</div>
  <div class="company">Employee Monthly Medical  Report</div>
  <div class="period">Financial Year: Jul 2025 &ndash; Jun 2026 &nbsp;|&nbsp; Generated: ${today}</div>
  <div class="meta-row">
    Department: <span>${dept}</span>
    &nbsp;&nbsp;|&nbsp;&nbsp;
    Employee: <span>${emp}</span>
    &nbsp;&nbsp;|&nbsp;&nbsp;
    Status: <span>${status}</span>
    &nbsp;&nbsp;|&nbsp;&nbsp;
    Total Records: <span>${data.length}</span>
  </div>
</div>

<!-- Summary Cards -->
<div class="summary">
  <div class="card">
    <div class="c-label">Total Employees</div>
    <div class="c-value">${data.length}</div>
  </div>
  <div class="card">
    <div class="c-label">Total Medical Allowance</div>
    <div class="c-value">PKR ${fmt(totals.medical_allowance)}</div>
  </div>
  <div class="card orange">
    <div class="c-label">Total Claimed</div>
    <div class="c-value">PKR ${fmt(totals.total_claimed)}</div>
  </div>
  <div class="card ${totals.balance >= 0 ? 'green' : 'red'}">
    <div class="c-label">Net Balance</div>
    <div class="c-value">PKR ${fmt(totals.balance)}</div>
  </div>
  <div class="card">
    <div class="c-label">Utilisation</div>
    <div class="c-value">${totals.medical_allowance ? Math.round((totals.total_claimed / totals.medical_allowance) * 100) : 0}%</div>
  </div>
</div>

<!-- Table -->
<table>
  <colgroup>
    <col class="c-sr">
    <col class="c-id">
    <col class="c-name">
    <col class="c-dept">
    <col class="c-sal">
    ${months.map(() => `<col class="c-mon">`).join("")}
    <col class="c-tot">
    <col class="c-bal">
  </colgroup>
  <thead>
    <tr>
      <th rowspan="2">#</th>
      <th rowspan="2">Emp ID</th>
      <th rowspan="2">Employee Name</th>
      <th rowspan="2">Department</th>
      <th rowspan="2">Medical Allowance</th>
      <th colspan="12">Monthly Claimed Amount</th>
      <th rowspan="2">Total Claimed</th>
      <th rowspan="2">Balance</th>
    </tr>
    <tr class="sub-head">
      ${months.map(m => `<th>${m.label}</th>`).join("")}
    </tr>
  </thead>
  <tbody>
    ${rows}
  </tbody>
  <tfoot>
    <tr>
      <td colspan="4" style="text-align:left; padding-left:6px;">GRAND TOTAL</td>
      <td class="num">${fmt(totals.medical_allowance)}</td>
      ${totalMonthCells}
      <td class="num">${fmt(totals.total_claimed)}</td>
      <td class="num ${totals.balance >= 0 ? 'pos' : 'neg'}">${fmt(totals.balance)}</td>
    </tr>
  </tfoot>
</table>

<!-- Footer -->
<div class="footer">
  <div>Printed on ${today} &nbsp;|&nbsp; Employee Monthly Medical Report &nbsp;|&nbsp; ATS HR System</div>
  <div style="display:flex; gap:40px;">
    <div class="sig-block">
      <div class="sig-line"></div>
      <div class="sig-name">HR Manager</div>
      <div class="sig-title">Signature &amp; Stamp</div>
    </div>
    <div class="sig-block">
      <div class="sig-line"></div>
      <div class="sig-name">Accounts Manager</div>
      <div class="sig-title">Signature &amp; Stamp</div>
    </div>
    <div class="sig-block">
      <div class="sig-line"></div>
      <div class="sig-name">Authorized By</div>
      <div class="sig-title">Signature &amp; Stamp</div>
    </div>
  </div>
</div>

</body>
</html>`;

			// Open print window
			const win = window.open("", "_blank", "width=1400,height=900");
			win.document.write(html);
			win.document.close();
			win.onload = () => win.print();
		});
	},
};