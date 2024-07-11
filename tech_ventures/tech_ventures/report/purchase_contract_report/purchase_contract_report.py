# Copyright (c) 2023, Tech Ventures and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cstr, flt


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_data(filters):
	data = []

	po = frappe.qb.DocType('Purchase Order')
	poi = frappe.qb.DocType('Purchase Order Item')
	fn = frappe.qb.DocType('File No')

	pr = frappe.qb.DocType('Purchase Receipt')
	pri = frappe.qb.DocType('Purchase Receipt Item')

	dn = frappe.qb.DocType('Delivery Note')
	dni = frappe.qb.DocType('Delivery Note Item')

	se = frappe.qb.DocType('Stock Entry')
	sed = frappe.qb.DocType('Stock Entry Detail')

	gle = frappe.qb.DocType('GL Entry')
	pe = frappe.qb.DocType('Payment Entry')

	total_dict_po_data = frappe._dict({'party': 'Total', 'qty': 0, 'amount_usd': 0, 'amount_pkr': 0})
	total_dict_pr_data = frappe._dict({'party': 'Total', 'amount_usd': 0, 'amount_pkr': 0, 'rate_usd': 0})
	total_dict_dn_data = frappe._dict({'party': 'Total', 'qty': 0, 'amount_usd': 0})
	total_dict_se_data = frappe._dict({'party': 'Total', 'qty': 0, 'amount_usd': 0})

	purchase_order_data = (
		frappe.qb.from_(po)
		.inner_join(poi).on(po.name == poi.parent)
		.inner_join(fn).on(fn.name == poi.file_no)
		.select(
			po.supplier.as_("party"), fn.file_description.as_("item_description"), po.name.as_("doc_name"),
			poi.rate.as_("rate_usd"), po.transaction_date.as_("date"), poi.item_code.as_("item"), poi.qty,
			poi.uom, po.currency.as_("supplier_currency"), poi.amount.as_("amount_usd"),
			po.conversion_rate.as_("rate"), poi.base_net_rate.as_("rate_pkr"), poi.base_net_amount.as_("amount_pkr")
		).where(poi.file_no == filters.get('file_no')).where(po.docstatus == 1)
	).run(as_dict=True)

	purchase_receipt_data = (
		frappe.qb.from_(pr)
		.inner_join(pri).on(pr.name == pri.parent)
		.inner_join(fn).on(fn.name == pri.file_no)
		.select(
			pr.posting_date.as_("party"), pr.name.as_("item_description"),
			pr.container_number.as_("date"), pr.seal_number.as_("doc_name"),
			pri.rate, pr.currency, pri.qty.as_("qtyy"), pri.uom.as_("uomm"),
			pr.posting_date.as_("party"), pri.item_code.as_("item"),
			pri.amount.as_("amount_usd"),
			pr.conversion_rate.as_("rate"), pri.base_net_rate.as_("rate_pkr"), pri.base_net_amount.as_("amount_pkr"),
			pr.lr_no.as_('uom'), pr.bl_number.as_("qty")

		).where(pri.file_no == filters.get('file_no')).where(pr.docstatus == 1)
	).run(as_dict=True)

	delivery_note_data = (
		frappe.qb.from_(dn)
		.inner_join(dni).on(dn.name == dni.parent)
		.inner_join(fn).on(fn.name == dni.file_no)
		.select(
			dn.posting_date.as_("date"), dn.name.as_("doc_name"), dni.item_code.as_("item"),
			dni.qty, dni.uom, dni.rate.as_('rate_usd'), dni.amount.as_('amount_usd'),
			dn.customer.as_('party'), fn.file_description.as_("item_description")
		).where(dni.file_no == filters.get('file_no')).where(dn.docstatus == 1)
	).run(as_dict=True)

	stock_entry_data = (
		frappe.qb.from_(se)
		.inner_join(sed).on(se.name == sed.parent)
		.inner_join(fn).on(fn.name == sed.file_no)
		.select(
			se.posting_date.as_("date"), se.name.as_("doc_name"), sed.item_code.as_("item"),
			sed.qty, sed.uom, sed.valuation_rate.as_('rate_usd'), sed.amount.as_('amount_usd'),
			fn.file_description.as_("item_description")
		)
		.where(sed.file_no == filters.get('file_no'))
		.where(se.docstatus == 1)
		.where(se.stock_entry_type == 'Material Transfer')
	).run(as_dict=True)

	gl_entry_data = (
		frappe.qb.from_(gle)
		.inner_join(fn).on(fn.name == gle.file_no)
		.select(
			gle.posting_date.as_("date"), gle.voucher_type.as_("doc_name"), gle.voucher_no.as_("item"),
			gle.debit, gle.credit, gle.account, gle.party, fn.file_description.as_("item_description")
		).where(gle.file_no == filters.get('file_no')).where(gle.docstatus == 1)
		.where(gle.voucher_type.isin(['Payment Entry', 'Sales Invoice', 'Journal Entry'])) # ['Payment Entry', 'Sale Invoice', 'Journal Entry']
		.orderby(gle.posting_date, gle.voucher_type)
	).run(as_dict=True)

	if purchase_order_data:
		data.extend([{
			'heading': 'Purchase Order Data', 'party': 'Supplier', 'item_description': 'Item Description',
			'date': 'Purchase Order Date', 'doc_name': 'Purchase Order', 'item': 'Item Description',
			'qty': 'Qty', 'uom': 'UOM', 'rate_usd': 'Rate (USD)', 'supplier_currency': 'Supplier Currency',
			'amount_usd': 'Amount', 'rate': 'Rate (Exchange)', 'rate_pkr': 'Rate (PKR)', 'amount_pkr': 'Amount (PKR)'
		}])

		for d in purchase_order_data:
			total_dict_po_data.qty += d.qty
			total_dict_po_data.amount_usd += d.amount_usd
			total_dict_po_data.amount_pkr += d.amount_pkr

			data.append(d)

		total_dict_bold = {}
		for key, value in total_dict_po_data.items():
			total_dict_bold[key] = '{0}'.format(value)

		data.extend([total_dict_bold])

	# pr.posting_date.as_("party"), pr.name.as_("item_description")
	if purchase_receipt_data:
		data.extend([{
			'party': 'Purchase Receipt Date', 'item_description': 'Purchase Receipt',
			'date': 'Container No', 'doc_name': 'Seal No',
			'heading': 'Purchase Receipt Data',
			'item': 'Item Description', 'qty': 'BL No',
			'rate_usd': 'Qty and UOM', 'supplier_currency': 'Rate (USD)', 'uom': 'Vehicle No',
			'amount_usd': 'Amount', 'rate': 'Rate (Exchange)', 'rate_pkr': 'Rate (PKR)', 'amount_pkr': 'Amount (PKR)',
		}])

		for d in purchase_receipt_data:
			total_dict_pr_data.rate_usd += d.qtyy
			total_dict_pr_data.amount_usd += d.amount_usd
			total_dict_pr_data.amount_pkr += d.amount_pkr
			d['supplier_currency'] = '{0} {1}'.format(cstr(d.rate), cstr(d.currency))
			d['rate_usd'] = '{0} {1}'.format(cstr(d.qtyy), cstr(d.uomm))

			data.append(d)

		total_dict_bold = {}
		for key, value in total_dict_pr_data.items():
			total_dict_bold[key] = '{0}'.format(value)

		data.extend([total_dict_bold])

	if delivery_note_data:
		data.extend([{
			'heading': 'Delivery Note Data', 'party': 'Customer', 'item_description': 'Item Description',
			'date': 'Delivery Note Date', 'doc_name': 'Delivery Note', 'item': 'Item Description',
			'qty': 'Qty', 'uom': 'UOM', 'rate_usd': 'Rate', 'amount_usd': 'Amount'
		}])

		for d in delivery_note_data:
			total_dict_dn_data.qty += d.qty
			total_dict_dn_data.amount_usd += d.amount_usd
			data.append(d)

		total_dict_bold = {}
		for key, value in total_dict_dn_data.items():
			total_dict_bold[key] = '{0}'.format(value)

		data.extend([total_dict_bold])

	if stock_entry_data:
		data.extend([{
			'heading': 'Stock Entry Data', 'item_description': 'Item Description',
			'date': 'Stock Entry Date', 'doc_name': 'Stock Entry', 'item': 'Item Description',
			'qty': 'Qty', 'uom': 'UOM', 'rate_usd': 'Rate', 'amount_usd': 'Amount'
		}])

		for d in stock_entry_data:
			total_dict_se_data.qty += d.qty
			total_dict_se_data.amount_usd += d.amount_usd

			data.append(d)

		total_dict_bold = {}
		for key, value in total_dict_se_data.items():
			total_dict_bold[key] = '{0}'.format(value)

		data.extend([total_dict_bold])

	balance = 0
	if gl_entry_data:
		data.extend([{
			'heading': 'Payment Detail Data',
			'date': 'Entry Date', 'doc_name': 'Voucher Type', 'item': 'Voucher No',
			'qty': 'Debit', 'uom': 'Credit', 'rate_usd': 'Balance', 'supplier_currency': 'Account'
		}])

		for d in gl_entry_data:

			if d.get('doc_name') in ['Payment Entry', 'Journal Entry']:
				if d.get('doc_name') == 'Payment Entry':
					payment_type = frappe.get_cached_value(d.get('doc_name'), d.get('item'), 'payment_type')
					if payment_type == 'Pay' and d.debit:
						balance = balance + (flt(d.debit) - flt(d.credit))
						d['qty'] = d.debit
						d['rate_usd'] = balance
						d['supplier_currency'] = d.party
						data.append(d)
				else:
					if d.debit:
						balance = balance + (flt(d.debit) - flt(d.credit))
						d['qty'] = d.debit
						d['rate_usd'] = balance
						d['supplier_currency'] = d.account
						data.append(d)

			elif d.get('doc_name') == 'Sales Invoice':
				balance = balance + (flt(d.debit) - flt(d.credit))
				d['uom'] = d.credit
				d['rate_usd'] = balance
				d['supplier_currency'] = frappe.get_cached_value(d.get('doc_name'), d.get('item'), 'customer')

				data.append(d)

	summary_list = [{'heading': 'Summary (Stock)', 'party': 'Purchase Detail', 'date': 'Production Detail'}]

	if total_dict_po_data.qty:
		copperc = cstr(flt((total_dict_se_data.qty * 100) / total_dict_pr_data.rate_usd, 3)) if total_dict_pr_data.rate_usd else 0
		copper_qty_and_perc = '{0}\t ({1}%age)'.format(total_dict_se_data.qty, copperc)
		summary_list.append(
			{
				'party': 'Item Purchased Qty', 'item_description': total_dict_po_data.qty,
				'date': 'Copper Qty', 'doc_name': copper_qty_and_perc,
				'item': 'Stock Short/Excess', 'qty': total_dict_po_data.qty - total_dict_pr_data.rate_usd
			}
		)

	if total_dict_pr_data.rate_usd or total_dict_dn_data.qty:
		other_item_prec = cstr(flt((total_dict_dn_data.qty * 100) / total_dict_pr_data.rate_usd, 3)) if total_dict_pr_data.rate_usd else 0
		copper_qty_and_perc = '{0}\t ({1}%age)'.format(total_dict_dn_data.qty, other_item_prec)
		summary_list.append(
			{
				'party': 'Received Qty', 'item_description': total_dict_pr_data.rate_usd,
				'date': 'Other Item Qty', 'doc_name': copper_qty_and_perc, 'item': 'Qty in stock',
				'qty': total_dict_pr_data.rate_usd - total_dict_dn_data.qty - total_dict_se_data.qty
			}
		)

	if total_dict_po_data.qty or total_dict_pr_data.rate_usd or total_dict_dn_data.qty:
		data.extend(summary_list)
		if total_dict_se_data.amount_usd and balance:
			profit_or_loss = total_dict_se_data.amount_usd - balance
			data.append(
				{
					'heading': 'Net Value (profit & Loss)/Stock In hand value',
					'party': profit_or_loss
				}
			)

	return data


def get_columns(filters):
	columns = [
		{
			"label": _("A"),
			"fieldtype": "Data",
			"fieldname": "heading",
			"width": 200,
		},
		{
			"label": _("B"),
			"fieldtype": "Data",
			"fieldname": "party",
			"width": 170,
		},
		{
			"label": _("C"),
			"fieldtype": "Data",
			"fieldname": "item_description",
			"width": 150,
		},
		{
			"label": _("D"),
			"fieldtype": "Data",
			"fieldname": "date",
			"width": 150,
		},
		{
			"label": _("E"),
			"fieldtype": "Data",
			"fieldname": "doc_name",
			"width": 170,
		},
		{
			"label": _("F"),
			"fieldtype": "Data",
			"fieldname": "item",
			"options": "Item",
			"width": 170,
		},
		{
			"label": _("G"),
			"fieldtype": "Data",
			"fieldname": "qty",
			"width": 130,
		},
		{
			"label": _("H"),
			"fieldtype": "Data",
			"fieldname": "uom",
			"width": 130,
		},
		{
			"label": _("I"),
			"fieldtype": "Data",
			"fieldname": "rate_usd",
			"width": 100,
		},
		{
			"label": _("J"),
			"fieldtype": "Data",
			"fieldname": "supplier_currency",
			"width": 170,
		},
		{
			"label": _("K"),
			"fieldtype": "Data",
			"fieldname": "amount_usd",
			"width": 100,
		},
		{
			"label": _("L"),
			"fieldtype": "Data",
			"fieldname": "rate",
			"width": 120,
		},
		{
			"label": _("M"),
			"fieldtype": "Data",
			"fieldname": "rate_pkr",
			"width": 100,
		},
		{
			"label": _("N"),
			"fieldtype": "Data",
			"fieldname": "amount_pkr",
			"width": 120,
		}
	]

	return columns
