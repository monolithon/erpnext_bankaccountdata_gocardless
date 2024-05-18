/*
*  ERPNext Gocardless Bank © 2024
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


frappe.provide("frappe.listview_settings");


frappe.listview_settings['Gocardless Sync Log'] = {
    onload: function(list) {
        frappe.gc().disable_list(list, __('Doctype is read only.'));
    },
    primary_action: function() {
        frappe.gc().error(__('You cannot add logs manually.'));
    },
};