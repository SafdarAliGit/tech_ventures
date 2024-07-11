import frappe

@frappe.whitelist()
def get_delivery_notes(from_date, to_date, customer):
	items = []
	dns = frappe.db.sql("""select name from `tabDelivery Note` where docstatus = 1 and status = 'To Bill' and customer =%s and posting_date between %s and %s""", (customer, from_date, to_date))
	for dn in dns:
		dnis = frappe.get_all('Delivery Note Item', {'parent': dn[0]})
		for dni in dnis:
			items.append(frappe.get_doc('Delivery Note Item', dni['name']))

	return items