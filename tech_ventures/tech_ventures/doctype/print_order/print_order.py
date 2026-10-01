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
		# Submission only happens from the background job, after the postings succeed
		if not self.flags.postings_done:
			frappe.throw(_("Use the Submit button on the form. The Print Order is submitted "
				"automatically once the Stock Entry and Sales Invoice are created."))

	def validate_postings(self):
		if not any(row.item_code for row in self.items):
			frappe.throw(_("At least one row must have an Item Code to create the Stock Entry"))

	@frappe.whitelist()
	def submit_with_postings(self, workflow_action=None):
		"""Queue Stock Entry and Sales Invoice creation; the Print Order is submitted only if both succeed."""
		self.queue_submit(workflow_action)
		frappe.msgprint(_("Stock Entry and Sales Invoice are being created in the background. "
			"The Print Order will be submitted once they succeed."), alert=True)

	def queue_submit(self, workflow_action=None):
		if self.docstatus != 0:
			frappe.throw(_("Print Order is already submitted"))
		self.check_permission("submit")
		self.validate_postings()
		self.get_submit_workflow_state(workflow_action)
		self.enqueue_postings(workflow_action=workflow_action)

	def get_submit_workflow_state(self, workflow_action):
		"""Return (state field, next state) for a workflow action that submits, or None without a workflow."""
		from frappe.model.workflow import get_transitions, get_workflow_name, get_workflow

		if not get_workflow_name(self.doctype):
			return None
		if not workflow_action:
			frappe.throw(_("Use the workflow action to submit this Print Order"))
		workflow = get_workflow(self.doctype)
		# get_transitions only returns transitions the current user's roles allow
		transition = [t for t in get_transitions(self, workflow) if t.action == workflow_action]
		if not transition:
			frappe.throw(_("Workflow action {0} is not allowed").format(frappe.bold(workflow_action)))
		next_state = transition[0].next_state
		state_row = [s for s in workflow.states if s.state == next_state]
		if not state_row or frappe.utils.cint(state_row[0].doc_status) != 1:
			frappe.throw(_("Workflow action {0} does not submit the Print Order").format(frappe.bold(workflow_action)))
		return workflow.workflow_state_field, next_state

	def enqueue_postings(self, workflow_action=None):
		job_id = "print_order_postings::" + self.name
		if is_job_enqueued(job_id):
			frappe.throw(_("Postings for {0} are already in progress").format(self.name))
		frappe.enqueue(
			"tech_ventures.tech_ventures.doctype.print_order.print_order.process_postings",
			queue="long",
			timeout=3000,
			enqueue_after_commit=True,
			job_id=job_id,
			print_order=self.name,
			workflow_action=workflow_action,
		)

	@frappe.whitelist()
	def retry_postings(self):
		# For Print Orders submitted before postings were tied to submission
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



def process_postings(print_order, workflow_action=None):
	"""Background job: create and submit Stock Entry and Sales Invoice, then submit the Print Order.
	All three happen in one transaction, so a failure leaves the Print Order in draft with nothing posted."""
	doc = frappe.get_doc("Print Order", print_order)
	if doc.docstatus == 2:
		return
	try:
		doc.validate_postings()
		doc.make_stock_entry()
		doc.post_invoice()
		if doc.docstatus == 0:
			# Move to the workflow's submitted state (e.g. Posted), as apply_workflow would
			workflow_state = doc.get_submit_workflow_state(workflow_action)
			if workflow_state:
				doc.set(*workflow_state)
			doc.flags.postings_done = True
			doc.submit()
		frappe.db.commit()
	except Exception as e:
		# Undo partial postings so a retry starts clean
		frappe.db.rollback()
		error = frappe.log_error(title=_("Print Order {0}: postings failed").format(print_order),
			reference_doctype="Print Order", reference_name=print_order)
		reason = frappe.utils.strip_html_tags(str(e))
		doc.add_comment("Comment", _("Stock Entry / Sales Invoice creation failed: {0} (Error Log {1}). "
			"Fix the issue and submit again.").format(reason, error.name if error else ""))
		frappe.db.commit()
		frappe.publish_realtime("msgprint", _("Print Order {0}: Stock Entry / Sales Invoice creation failed: {1}<br>"
			"The Print Order was not submitted. Fix the issue and submit again.").format(print_order, reason),
			user=frappe.session.user)
		return
	# frappe.publish_realtime("msgprint", _("Print Order {0}: Stock Entry and Sales Invoice created and Print Order submitted.").format(print_order),
	# 	user=frappe.session.user)


def is_workflow_submit_action(doc, action):
	"""True if the workflow action takes this draft Print Order to a submitted state."""
	from frappe.model.workflow import get_transitions, get_workflow

	if doc.docstatus != 0:
		return False
	workflow = get_workflow(doc.doctype)
	for t in get_transitions(doc, workflow):
		if t.action == action:
			state_row = [s for s in workflow.states if s.state == t.next_state]
			return bool(state_row) and frappe.utils.cint(state_row[0].doc_status) == 1
	return False


@frappe.whitelist()
def bulk_submit_cancel_or_update_docs(doctype, docnames, action="submit", data=None):
	"""Override of list view bulk Submit: Print Orders are queued through the postings job
	instead of being submitted directly. Everything else goes to the standard method."""
	from frappe.desk.doctype.bulk_update.bulk_update import show_progress, submit_cancel_or_update_docs

	if doctype != "Print Order" or action != "submit":
		return submit_cancel_or_update_docs(doctype, docnames, action, data)

	docnames = frappe.parse_json(docnames)
	failed = []
	for i, name in enumerate(docnames, 1):
		try:
			frappe.get_doc(doctype, name).queue_submit()
			frappe.db.commit()
			show_progress(docnames, _("Queueing {0}").format(doctype), i, name)
		except Exception:
			failed.append(name)
			frappe.db.rollback()

	if len(failed) < len(docnames):
		frappe.msgprint(_("Stock Entry and Sales Invoice are being created in the background. "
			"Print Orders will be submitted once they succeed."), alert=True)
	return failed


@frappe.whitelist()
def bulk_workflow_approval(docnames, doctype, action):
	"""Override of list view bulk workflow actions: for Print Order, actions that submit (e.g. Post)
	are queued through the postings job. Everything else goes to the standard method."""
	from collections import defaultdict
	from frappe.model.workflow import bulk_workflow_approval as standard_bulk_workflow_approval
	from frappe.model.workflow import print_workflow_log, show_progress

	if doctype != "Print Order":
		return standard_bulk_workflow_approval(docnames, doctype, action)

	docnames = frappe.parse_json(docnames)
	to_queue, others = [], []
	for name in docnames:
		try:
			submits = is_workflow_submit_action(frappe.get_doc(doctype, name), action)
		except Exception:
			submits = False
		(to_queue if submits else others).append(name)

	# Standard method clears the message log, so run it before collecting our own messages
	if others:
		standard_bulk_workflow_approval(frappe.as_json(others), doctype, action)
	if not to_queue:
		return

	failed, successful = defaultdict(list), defaultdict(list)
	for i, name in enumerate(to_queue, 1):
		show_progress(to_queue, _("Applying: {0}").format(action), i, name)
		message_count = len(frappe.message_log)
		try:
			frappe.get_doc(doctype, name).queue_submit(action)
			frappe.db.commit()
			successful[name].append({"message": _("Stock Entry and Sales Invoice are being created in the background. "
				"The Print Order will be submitted once they succeed.")})
		except Exception as e:
			frappe.db.rollback()
			messages = frappe.message_log[message_count:]
			del frappe.message_log[message_count:]
			reason = ", ".join(frappe.parse_json(m).get("message", "") for m in messages) or str(e)
			failed[name].append({"message": reason})

	indicator = "orange" if failed and successful else ("red" if failed else "green")
	print_workflow_log(failed, _("Failed Transactions"), doctype, indicator)
	print_workflow_log(successful, _("Queued Transactions"), doctype, indicator)


def custom_on_update(doc, method):
	doc.total_sales_commission = (doc.sale_commission_per_piece or 0) * doc.qty
	
	