import frappe
from frappe.model.naming import make_autoname
from tech_ventures.utils.utils_functions import get_doctype_by_field
from frappe.utils import nowdate

def post_journal_entry(doc, method):
    # for with holding tax
    # Get the Sales Invoice
   
    discount_amount = doc.withholding_tax_amount or 0
    
    # If discount amount is 0, do nothing
    if discount_amount > 0:
        # Create Journal Entry
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.posting_date = doc.posting_date
        je.company = doc.company
        je.remark = f"Withholding Tax for Sales Invoice {doc.name}, Print Order {doc.print_order}"
        je.user_remark = je.remark
        je.ref_no = doc.name
        je.ref_doctype = "Sales Invoice"

        # Debit Discount Allowed
        je.append("accounts", {
            "account": "Sales - EP",
            "debit_in_account_currency": discount_amount,
        })  

        # Credit Customer Receivable Account
        je.append("accounts", {
            "account": "Withholding Tax - EP",
            "credit_in_account_currency": discount_amount,
        })

        # Save and submit
        je.save()
        je.submit()
        frappe.msgprint(f"Journal Entry {je.name} created for Withholding Tax.")
        

    
    
    # for commission
    if doc.total_sales_commission > 0 and doc.agent and doc.commission_account:
        je = frappe.new_doc("Journal Entry")
        je.posting_date = doc.posting_date
        je.company = doc.company
        je.voucher_type = "Journal Entry"
        je.ref_no = doc.name
        je.ref_doctype = "Sales Invoice"
        je.remark = f"Commission for Sales Invoice {doc.name}, Print Order {doc.print_order}"
        
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


@frappe.whitelist()
def get_withholding_tax(**args):
    if args.get('customer'):
        customer = frappe.get_doc('Customer', args.get('customer'))
        if customer.withholding_tax > 0:
            return customer.withholding_tax
        else:
            return 0
    
    
def custom_on_update(doc, method):
    if doc.qty and doc.total:
        doc.custom_rate_per_book = doc.total / doc.qty
    if doc.withholding_tax > 0:
        doc.withholding_tax_amount = float(doc.grand_total) * (float(doc.withholding_tax) / 100)    

def on_cancel(doc, method):
    # Fetch all Journal Entries where ref_no = doc.name
    journal_entries = frappe.get_all(
        'Journal Entry',
        filters={'ref_no': doc.name, 'docstatus': 1},  # only submitted JEs
        fields=['name', 'amended_from']
    )

    for je_data in journal_entries:
        je = frappe.get_doc("Journal Entry", je_data.name)
        je.cancel()
        frappe.db.commit()

        # Optional: If you want to generate the next name (though not necessary in cancel)
        if je_data.amended_from:
            try:
                base, suffix = je.name.rsplit("-", 1)
                new_name = f"{base}-{int(suffix) + 1}"
            except ValueError:
                new_name = f"{je.name}-1"
        else:
            new_name = f"{je.name}-1"

        # Not needed unless you are using this name somewhere
        make_autoname(new_name, 'Journal Entry')  # This line is optional and may not do anything

