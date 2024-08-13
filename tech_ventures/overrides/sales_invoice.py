import frappe
from frappe.model.naming import make_autoname
from tech_ventures.utils.utils_functions import get_doctype_by_field


def post_journal_entry(doc, method):
    if doc.total_sales_commission > 0 and doc.agent and doc.commission_account:
        je = frappe.new_doc("Journal Entry")
        je.posting_date = doc.posting_date
        je.company = doc.company,
        je.voucher_type = "Journal Entry"
        je.ref_no = doc.name
        je.ref_doctype = "Sales Invoice"
        je.append("accounts", {
            'account': "Debtors - EP",
            'party_type': "Customer",
            'party': doc.agent,
            'debit_in_account_currency': 0,
            'credit_in_account_currency': doc.total_sales_commission
        })
        je.append("accounts", {
            'account': doc.commission_account,
            'party_type': "",
            'party': "",
            'debit_in_account_currency': doc.total_sales_commission,
            'credit_in_account_currency': 0
        })
        try:
            je.save()
            je.submit()
        except Exception as e:
            frappe.log_error(e, frappe.get_traceback())


def on_cancel(doc, method):
    je = get_doctype_by_field('Journal Entry', 'ref_no', doc.name)
    je.cancel()
    frappe.db.commit()
    if je.amended_from:
        new_name = int(je.name.split("-")[-1]) + 1
    else:
        new_name = f"{je.name}-{1}"
    make_autoname(new_name, 'Journal Entry')
