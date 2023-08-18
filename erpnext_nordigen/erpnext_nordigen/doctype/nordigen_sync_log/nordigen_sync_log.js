/*
*  ERPNext Nordigen © 2023
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


frappe.ui.form.on('Nordigen Sync Log', {
    onload: function(frm) {
        frappe.router.set_route('List', 'Nordigen Sync Log');
    }
});