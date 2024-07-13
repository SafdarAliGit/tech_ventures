import frappe


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
