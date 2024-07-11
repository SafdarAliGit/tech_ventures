import frappe




class GeneralLedger:
    def __init__(self, from_date=None, to_date=None, account=None, party=None, party_type=None):
        if not from_date:
            from_date = frappe.utils.today()
        if not to_date:
            to_date = frappe.utils.today()
        self.account = account
        self.from_date = from_date
        self.to_date = to_date
        self.data = []
        self.party_type = party_type
        self.party = party
        


    def get_ledger_entries(self):
        filters = {"is_cancelled":0, "posting_date":[ "between", [self.from_date, self.to_date]]}
        if self.account:
            filters.update({"account": self.account})
        if self.party_type and self.party:
            filters.update({
                "party_type":self.party_type,
                "party": ["in", self.party]
            })

        self.les = frappe.get_all("GL Entry", filters=filters, fields=["*"], order_by='posting_date asc, creation asc')

    def get_data(self):
        self.get_ledger_entries()
        for le in self.les:
            items = []
            data_dict = le
            if le.voucher_type in ["Sales Invoice", "Purchase Invoice", "Purchase Receipt", "Delivery Note"]:
                items = frappe.get_all("{0} Item".format(le.voucher_type), filters={"parent":le.voucher_no}, fields = ["*"])
            data_dict.update({
                "items": items
            })
            self.data.append(data_dict)
            


@frappe.whitelist()
def get_data(from_date=None, to_date=None, account=None, party_type=None, party=None):
    GL = GeneralLedger(from_date, to_date, account, party_type, party)
    GL.get_data()
    return GL.data