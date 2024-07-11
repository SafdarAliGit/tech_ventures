// Copyright (c) 2021, Tech Ventures and contributors
// For license information, please see license.txt

frappe.ui.form.on('Print Order', {
	qty(frm) {
		var items = frm.doc.items
		for(var i in items){
			items[i].qty = items[i].qty_per_book * frm.doc.qty
		}
		frm.refresh_field("items");
	},
	refresh(frm){
		cur_frm.add_custom_button(__('Create Invoice'), function(){
			frappe.call({
				method: "create_invoice",
				doc: frm.doc,
				callback: function(r){
					if(r.message){
						frappe.set_route("Form", "Sales Invoice", r.message)
					}
				}
			})
		})
	},
	book_name(frm){
		frappe.call({
			method: "get_raw",
			doc:frm.doc,
			callback: function(r){
				frm.refresh_field("items")
			}
		})
	}
});



frappe.ui.form.on('Print Order Item', {
	qty_per_book(frm, cdt, cdn){
		set_qty(frm, cdt, cdn);
	},
	items_add(frm, cdt, cdn){
		set_qty(frm, cdt, cdn);
	},
	consumption_cf(frm, cdt, cdn){
		set_qty(frm, cdt, cdn);
	}
});

function set_qty(frm, cdt, cdn){
	var d = locals[cdt][cdn];
	frappe.model.set_value(d.doctype, d.name, "qty", frm.doc.qty* (Math.ceil(d.qty_per_book*d.consumption_cf)));
	set_total_qty(frm);
}

function set_total_qty(frm){
	frm.doc.total_qty_per_book = 0;
	for(var i in frm.doc.items) {
		frm.doc.total_qty_per_book += frm.doc.items[i].qty_per_book
	}
	frm.refresh_field("total_qty_per_book")
}

cur_frm.set_query("book_name", function(){
	return {
		filters:{
			"item_group": "Books"
		}
	}
})

cur_frm.set_query("raw_material", "items", function(){
	return {
		filters:{
			"item_group": "Services"
		}
	}
})

cur_frm.set_query("item_code", "items", function(){
	return {
		filters:{
			"item_group": ["in", ["Raw Material", "Sheet"]]
		}
	}
})