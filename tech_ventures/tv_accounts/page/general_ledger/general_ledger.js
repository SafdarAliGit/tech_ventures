frappe.pages['general-ledger'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'General Ledger',
		single_column: true
	});

	
	wrapper.sales_report = new erpnext.SalesReport(wrapper);

	frappe.breadcrumbs.add("Accounting");
}


erpnext.SalesReport = class SalesReport {
	constructor(wrapper) {
		var me = this;
		// 0 setTimeout hack - this gives time for canvas to get width and height
		setTimeout(function() {
			me.setup(wrapper);
			//me.get_data();
		}, 0);
	}

	setup(wrapper) {
		var me = this;
		this.from_date_field = wrapper.page.add_field({"fieldtype": "Date", "fieldname": "from_date",
			"label": __("From Date"), "reqd": 1, "default": "Today",
			change: function() {
				me.from_date = this.value || frappe.datetime.nowdate();
				me.get_data();
			}
		}),
		this.to_date_field = wrapper.page.add_field({"fieldtype": "Date", "fieldname": "to_date",
			"label": __("To Date"), "reqd": 1, "default": "Today",
			change: function() {
				me.to_date = this.value || frappe.datetime.nowdate();
				me.get_data();
			}
		}),
		this.account_field = wrapper.page.add_field({
			"fieldname":"account",
			"label": __("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"default": "",
			get_query: function(){
				return {
					filters:{
						is_group:0
					}
				}
			},
			change: function() {
				me.account = this.value
				me.get_data();
			}
		}),
		
		this.party_type_field = wrapper.page.add_field({
			"fieldname":"party_type",
			"label": __("Party Type"),
			"fieldtype": "Link",
			"options": "Party Type",
			"default": "",
			change: function() {
				me.party_type = this.value
				this.party_field.values = ""
				
			}
		}),
		this.party_field = wrapper.page.add_field({
			"fieldname":"party",
			"label": __("Party"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				let party_type = me.party_type;
				if (!party_type) return;
				return frappe.db.get_link_options(party_type, txt);
			},
			change: function() {
				
				me.get_data();
				
			}
		}),




		wrapper.page.set_primary_action(__("Refresh"),
				function() { me.get_data(); }, "fa fa-refresh")
			wrapper.page.set_secondary_action(__("Print"),
				function() { me.print_report(); }, "fa fa-print")
		this.elements = {
			layout: $(wrapper).find(".layout-main-section"),
		};

		this.elements.no_data = $('<div class="alert alert-warning">' + __("No Data") + '</div>')
			.toggle(false)
			.appendTo(this.elements.layout);
		this.options = {
			date: frappe.datetime.get_today()
		};
		this.elements.funnel_wrapper = $('<br><div style="display: block;" class="page-form row data-show"></div>')
			.appendTo(this.elements.layout);
		// set defaults and bind on change

		// bind refresh
	}
	get_data(btn) {
			var me = this;
			console.log(this.party_field.values)
		frappe.call({
			method:"tech_ventures.tv_accounts.page.general_ledger.general_ledger.get_data",
			args:{
				from_date: this.from_date,
				to_date: this.to_date,
				account: this.account,
				party_type: this.party_type,
				party: this.party_field.values
			},
			callback: function(r) {
				if(r.message){
					console.log(r.message)
					me.add_row(r.message)
				}
			}
		}) 		
	}
	add_row(data) {
		const $parent = this.elements.funnel_wrapper
		var table_data = frappe.render_template("general_ledger",{"data":data, "from_date":String(this.from_date), "to_date":String(this.to_date)});	
		$parent.html(table_data)
		//console.log(String(table_data))
	}
	print_report(btn){
	
		window.print()
		
	}
		 		   		


};