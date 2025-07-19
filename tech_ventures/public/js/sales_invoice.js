frappe.ui.form.on('Sales Invoice', {

    customer: function(frm) {
        frappe.call({
            method: "tech_ventures.overrides.sales_invoice.get_withholding_tax",
            args: {
                customer: frm.doc.customer
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_value("withholding_tax", r.message)
                }
            }
        })
    }
})