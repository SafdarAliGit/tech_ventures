# Copyright (c) 2024, Tech Ventures and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from tech_ventures.utils.utils_functions import get_doctype_by_field
from frappe.model.naming import make_autoname


class SheetTransfer(Document):
    def on_submit(self):
        # Ensure the POS Profile exists
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Transfer"
        se.ref_no = self.name

        # Append source items
        for item in self.sheet_transfer_item:
            it = se.append("items", {})
            it.item_code = item.item_code
            it.s_warehouse = self.source_warehouse
            it.t_warehouse = self.target_warehouse
            it.qty = item.qty
        try:
            se.submit()
        except Exception as e:
            frappe.throw(frappe._("Error submitting Sheet Transfer: {0}".format(str(e))))

    def on_cancel(self):
        pi = get_doctype_by_field('Stock Entry', 'ref_no', self.name)
        pi.cancel()
        frappe.db.commit()
        if pi.amended_from:
            new_name = int(pi.name.split("-")[-1]) + 1
        else:
            new_name = f"{pi.name}-{1}"
        make_autoname(new_name, 'Stock Entry')
