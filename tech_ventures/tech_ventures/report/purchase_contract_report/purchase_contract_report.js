// Copyright (c) 2023, Tech Ventures and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Purchase Contract Report"] = {
	"filters": [
		{
			"fieldname":"file_no",
			"label": __("File No"),
			"fieldtype": "Link",
			"options": "File No",
			"reqd": 1
			},
	]
};
