// Copyright (c) 2024, Tech Ventures and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sheet Transfer', {
    refresh: function (frm) {
        frm.fields_dict['target_warehouse'].get_query = function (doc) {
            return {
                filters: [
                    ["Warehouse", "parent_warehouse", "=", "In House Copy - EP"]
                ]

            };
        };
        frm.set_query('item_code', 'sheet_transfer_item', function (doc, cdt, cdn) {
            var d = locals[cdt][cdn];
            return {
                filters: [
                    ["Item", "item_group", "=", 'Sheet']
                ]
            };
        });
    }
});
