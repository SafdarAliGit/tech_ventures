import frappe

def delete_ledger_entries(doc, method):
	gle = frappe.get_all('GL Entry', filters={'voucher_no': doc.name}, fields=['name'])
	for gl in gle:
	    gg = frappe.get_doc('GL Entry', gl['name'])
	    gg.cancel()
	    gg.delete()
	sle = frappe.get_all('Stock Ledger Entry', filters={'voucher_no': doc.name}, fields=['name'])
	for sl in sle:
	    ss = frappe.get_doc('Stock Ledger Entry', sl['name'])
	    ss.cancel()
	    ss.delete()