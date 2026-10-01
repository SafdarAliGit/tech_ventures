// Copyright (c) 2021, Tech Ventures and contributors
// For license information, please see license.txt

frappe.ui.form.on('Print Order', {
    setup(frm) {
        // Replace the standard Submit: the server submits only after Stock Entry and Sales Invoice succeed.
        // Overriding savesubmit covers every Submit path (toolbar re-renders, dirty/clean toggles, shortcuts).
        frm.savesubmit = function () {
            return new Promise((resolve) => {
                frappe.confirm(__('Create Stock Entry and Sales Invoice, then submit this Print Order?'), function () {
                    (frm.is_dirty() ? frm.save() : Promise.resolve()).then(() => {
                        frappe.call({
                            method: "submit_with_postings",
                            doc: frm.doc,
                            freeze: true
                        }).then(resolve);
                    });
                });
            });
        };
    },
    before_workflow_action(frm) {
        // A workflow action that submits (e.g. Post) must go through the background postings too
        const wf = frappe.workflow.workflows[frm.doctype];
        const state_field = frappe.workflow.get_state_fieldname(frm.doctype);
        const transition = (wf.transitions || []).find(t =>
            t.state === frm.doc[state_field] && t.action === frm.selected_workflow_action);
        const next_state = transition && (wf.states || []).find(s => s.state === transition.next_state);
        if (frm.doc.docstatus !== 0 || !next_state || cint(next_state.doc_status) !== 1) return;

        frappe.dom.unfreeze();
        frm.selected_workflow_action = null;
        frappe.confirm(__('Create Stock Entry and Sales Invoice, then submit this Print Order?'), function () {
            frappe.call({
                method: "submit_with_postings",
                doc: frm.doc,
                args: { workflow_action: transition.action },
                freeze: true
            });
        });
        // Stop the standard apply_workflow call; the background job applies the state on success
        return Promise.reject();
    },
    qty(frm) {
        var items = frm.doc.items
        for (var i in items) {
            items[i].qty = items[i].qty_per_book * frm.doc.qty
        }
        frm.refresh_field("items");
        calculate_sales_commission(frm);
    },
    refresh(frm) {
        cur_frm.add_custom_button(__('Create Invoice'), function () {
            frappe.call({
                method: "create_invoice",
                doc: frm.doc,
                callback: function (r) {
                    if (r.message) {
                        frappe.set_route("Form", "Sales Invoice", r.message)
                    }
                }
            })
        })
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Retry Postings'), function () {
                frappe.call({
                    method: "retry_postings",
                    doc: frm.doc,
                    freeze: true,
                    callback: function () {
                        frappe.show_alert({ message: __("Stock Entry and Sales Invoice queued for creation"), indicator: "blue" });
                    }
                })
            })
        }
    },
    book_name(frm) {
        frappe.call({
            method: "get_raw",
            doc: frm.doc,
            callback: function (r) {
                frm.refresh_field("items")
                calculate_sales_commission(frm);

            }
        })
    },
    agent(frm) {
        calculate_sales_commission(frm);
    }
});


frappe.ui.form.on('Print Order Item', {
    qty_per_book(frm, cdt, cdn) {
        set_qty(frm, cdt, cdn);
    },
    items_add(frm, cdt, cdn) {
        set_qty(frm, cdt, cdn);
    },
    consumption_cf(frm, cdt, cdn) {
        set_qty(frm, cdt, cdn);
    }
});

function set_qty(frm, cdt, cdn) {
    var d = locals[cdt][cdn];
    frappe.model.set_value(d.doctype, d.name, "qty", (Math.ceil(frm.doc.qty * d.qty_per_book * d.consumption_cf)));
    set_total_qty(frm);
}

function set_total_qty(frm) {
    frm.doc.total_qty_per_book = 0;
    for (var i in frm.doc.items) {
        frm.doc.total_qty_per_book += frm.doc.items[i].qty_per_book
    }
    frm.refresh_field("total_qty_per_book")
}

function calculate_sales_commission(frm) {
    frm.set_value("total_sales_commission", (frm.doc.sale_commission_per_piece || 0) * (frm.doc.qty || 0));
    frm.refresh_field("total_sales_commission");
}

cur_frm.set_query("book_name", function () {
    return {
        filters: {
            "item_group": "Books"
        }
    }
})

cur_frm.set_query("raw_material", "items", function () {
    return {
        filters: {
            "item_group": "Services"
        }
    }
})

cur_frm.set_query("item_code", "items", function () {
    return {
        filters: {
            "item_group": ["in", ["Raw Material", "Sheet"]]
        }
    }
})