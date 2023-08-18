/*
*  ERPNext Nordigen © 2023
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


frappe.provide("frappe.listview_settings");


frappe.listview_settings['Nordigen Sync Log'] = {
    hide_name_column: true,
    onload: function(list) {
        list.page.clear_primary_action();
    },
    primary_action: function() {
        frappe.throw(__('You cannot add logs manually.'));
    },
};