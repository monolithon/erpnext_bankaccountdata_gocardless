/*
*  ERPNext Gocardless Bank © 2024
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


frappe.ui.form.on('Gocardless Sync Log', {
    onload: function(frm) {
        frappe.gc().disable_form(frm, __('Doctype is read only.'));
    }
});