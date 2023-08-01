import frappe

def execute():
    i = 801
    for v in range(200):
        inv = {}
        ple = {}
        inv_no = "SINV-{0:003d}".format(i)
        if frappe.db.exists("Sales Invoice", inv_no):
            inv = frappe.get_doc("Sales Invoice", inv_no)
            if inv.docstatus == 1:
                inv.cancel()
                print("Cancelling Sales Invoice: {}".format(inv.name))
        if frappe.db.exists("Payment Ledger Entry", {"voucher_no":inv_no}):
            ple = frappe.get_doc("Payment Ledger Entry", {"voucher_no":inv_no})
            if ple.docstatus == 1:    
                ple.cancel()
                
                print("Cancelling PLE: {}".format(ple.name))
                
       
        if ple:
            frappe.db.delete("Payment Ledger Entry", ple.name)
            print("Deleting PLE: {}".format(ple.name))     
        if inv:
            frappe.db.delete("Sales Invoice", inv.name)
            print("Deleting Sales Invoice: {}".format(inv.name))
        
        i = i+1 
