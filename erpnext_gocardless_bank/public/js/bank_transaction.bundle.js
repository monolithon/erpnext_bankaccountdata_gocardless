/*
*  ERPNext Gocardless Bank © 2023
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


frappe.ui.form.on('Bank Transaction', {
    setup: function(frm) {
        if (cstr(frm.doc.description).length)
            frm.toggle_display('description', true);
        if (cstr(frm.doc.gocardless_transaction_info).length)
            frm.toggle_display('gocardless_transaction_info', true);
    },
});