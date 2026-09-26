# Copyright (c) 2021, Tech Ventures and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils.background_jobs import is_job_enqueued

class PrintOrder(Document):
	@frappe.whitelist()
	def get_item_price(self, item_code):
		return frappe.db.get_value("Item Price", 
			{"item_code": item_code, "price_list":self.price_list, "valid_from":["<=", self.order_date]}, 
			"price_list_rate") or 0

	def before_submit(self):
		# Cheap checks only; the heavy postings run in a background job after submit
		if not any(row.item_code for row in self.items):
			frappe.throw(_("At least one row must have an Item Code to create the Stock Entry"))

	def on_submit(self):
		self.enqueue_postings()
		frappe.msgprint(_("Stock Entry and Sales Invoice are being created in the background. "
			"You will be notified when done."), alert=True)

	def enqueue_postings(self):
		job_id = "print_order_postings::" + self.name
		if is_job_enqueued(job_id):
			frappe.msgprint(_("Postings for {0} are already in progress").format(self.name))
			return
		frappe.enqueue(
			"tech_ventures.tech_ventures.doctype.print_order.print_order.process_postings",
			queue="long",
			timeout=3000,
			enqueue_after_commit=True,
			job_id=job_id,
			print_order=self.name,
		)

	@frappe.whitelist()
	def retry_postings(self):
		if self.docstatus != 1:
			frappe.throw(_("Print Order must be submitted"))
		self.enqueue_postings()

	def make_stock_entry(self):
		# Skip if already posted (safe for retries)
		if frappe.db.exists("Stock Entry", {"print_order": self.name, "docstatus": 1}):
			return
		ste = frappe.new_doc("Stock Entry")
		ste.stock_entry_type = "Material Issue"
		ste.posting_date = frappe.utils.today()
		ste.from_warehouse = "Stores - EP"
		ste.print_order = self.name
		ste.expense_account = frappe.db.get_value("Company", frappe.db.get_single_value("Global Defaults", "default_company"), "default_expense_account")
		for row in self.items:
			if row.item_code:
				sti = ste.append("items")
				sti.item_code = row.item_code
				sti.qty = row.qty
				sti.uom = row.uom
		ste.save()
		ste.submit()

	def get_customer_rates(self):
		raw_materials = [row.raw_material for row in self.items if row.raw_material]
		if not raw_materials:
			return {}
		rows = frappe.get_all("Customer Price List",
			filters={"parent": self.customer, "item_code": ["in", raw_materials]},
			fields=["item_code", "rate"])
		return {r.item_code: r.rate for r in rows}

	def post_invoice(self):
		# Skip if already posted (safe for retries)
		if frappe.db.exists("Sales Invoice", {"print_order": self.name, "docstatus": 1}):
			return
		rates = self.get_customer_rates()
		inv = frappe.new_doc("Sales Invoice")
		inv.posting_date = frappe.utils.today()
		inv.customer = self.customer
		inv.print_order = self.name
		inv.agent = self.agent
		inv.total_sales_commission = self.total_sales_commission
		inv.commission_account = self.commission_account
		for row in self.items:
			ini = inv.append("items")
			ini.item_code = row.raw_material
			ini.qty = flt(row.qty_per_book) * flt(self.qty)
			ini.rate = rates.get(row.raw_material)
		inv.save()
		inv.submit()

	@frappe.whitelist()
	def create_invoice(self):
		inv = frappe.new_doc("Sales Invoice")
		inv.posting_date = frappe.utils.today()
		inv.customer = self.customer
		inv.print_order = self.name
		inv.agent = self.agent
		inv.total_sales_commission = self.total_sales_commission
		inv.commission_account = self.commission_account
		rates = self.get_customer_rates()
		for row in self.items:
			ini = inv.append("items")
			ini.item_code = row.raw_material
			ini.qty = flt(row.qty_per_book) * flt(self.qty)
			ini.rate = rates.get(row.raw_material)
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



def process_postings(print_order):
	"""Background job: create and submit Stock Entry and Sales Invoice for a submitted Print Order."""
	doc = frappe.get_doc("Print Order", print_order)
	if doc.docstatus != 1:
		return
	try:
		doc.make_stock_entry()
		doc.post_invoice()
		frappe.db.commit()
	except Exception as e:
		# Undo partial postings so a retry starts clean
		frappe.db.rollback()
		error = frappe.log_error(title=_("Print Order {0}: postings failed").format(print_order),
			reference_doctype="Print Order", reference_name=print_order)
		reason = frappe.utils.strip_html_tags(str(e))
		doc.add_comment("Comment", _("Stock Entry / Sales Invoice creation failed: {0} (Error Log {1}). "
			"Fix the issue and click Retry Postings.").format(reason, error.name if error else ""))
		frappe.db.commit()
		frappe.publish_realtime("msgprint", _("Print Order {0}: Stock Entry / Sales Invoice creation failed: {1}<br>"
			"Fix the issue and use Retry Postings on the Print Order.").format(print_order, reason),
			user=frappe.session.user)
		return
	frappe.publish_realtime("msgprint", _("Print Order {0}: Stock Entry and Sales Invoice created.").format(print_order),
		user=frappe.session.user)


def custom_on_update(doc, method):
	doc.total_sales_commission = (doc.sale_commission_per_piece or 0) * doc.qty
	
	