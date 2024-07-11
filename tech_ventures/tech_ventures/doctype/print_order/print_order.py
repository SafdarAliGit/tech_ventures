# Copyright (c) 2021, Tech Ventures and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class PrintOrder(Document):
	@frappe.whitelist()
	def get_item_price(self, item_code):
		return frappe.db.get_value("Item Price", 
			{"item_code": item_code, "price_list":self.price_list, "valid_from":["<=", self.order_date]}, 
			"price_list_rate") or 0

	def before_submit(self):
		ste = frappe.new_doc("Stock Entry")
		ste.stock_entry_type = "Material Issue"
		ste.posting_date = frappe.utils.today()
		ste.from_warehouse = "Stores - EP"
		ste.print_order = self.name
		for row in self.items:
			if row.item_code:
				sti = ste.append("items")
				sti.item_code = row.item_code
				sti.qty = row.qty
				sti.uom = row.uom
				ste.expense_account = frappe.db.get_value("Company", frappe.db.get_single_value("Global Defaults", "default_company"), "default_expense_account")
		ste.save()
		ste.submit()
		self.post_invoice()

	def post_invoice(self):
		inv = frappe.new_doc("Sales Invoice")
		inv.posting_date = frappe.utils.today()
		inv.customer = self.customer
		inv.print_order = self.name
		for row in self.items:
			ini = inv.append("items")
			ini.item_code = row.raw_material
			ini.qty = row.qty_per_book * self.qty
			ini.rate = frappe.db.get_value("Customer Price List", {"parent":self.customer, "item_code":row.raw_material}, "rate")
		inv.save()
		inv.submit()

	@frappe.whitelist()
	def create_invoice(self):
		inv = frappe.new_doc("Sales Invoice")
		inv.posting_date = frappe.utils.today()
		inv.customer = self.customer
		inv.print_order = self.name
		for row in self.items:
			ini = inv.append("items")
			ini.item_code = row.raw_material
			ini.qty = row.qty_per_book * self.qty
			ini.rate = frappe.db.get_value("Customer Price List", {"parent":self.customer, "item_code":row.raw_material}, "rate")
		inv.save()
		return inv.name

	@frappe.whitelist()
	def get_raw(self):
		self.items = []
		order = frappe.get_doc("Print Order", {"book_name":self.book_name})
		if order:
			items = frappe.get_all("Print Order Item", filters={"parent": order.name}, fields=["raw_material", "item_code", "qty_per_book", "uom"])
			for it in items:
				itt = self.append("items")
				itt.item_code = it.item_code
				itt.raw_material = it.raw_material
				itt.uom = it.uom
				itt.qty_per_book = it.qty_per_book
				itt.qty = itt.qty_per_book * self.qty
			self.file_name = order.file_name
			self.total_qty_per_book = order.total_qty_per_book
			self.file_name_2 = order.file_name_2
			self.file_name_3 = order.file_name_3
			self.file_name_4 = order.file_name_4
			self.file_name_5 = order.file_name_5



