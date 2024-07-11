from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		
		'transactions': [
			{
				'label': _('References'),
				'items': ['Stock Entry', 'Sales Invoice']
			}
		]
	}