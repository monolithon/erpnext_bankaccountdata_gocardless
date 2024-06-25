/*
*  ERPNext Gocardless Bank © 2024
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


if (typeof frappe.gc !== 'function')
    frappe.require('/assets/erpnext_gocardless_bank/js/gocardless.bundle.js');


frappe.ui.form.on('Customer', {
    onload: function(frm) {
        if (frm.is_new()) return;
        function gc_init() {
            if (typeof frappe.gc !== 'function')
                return setTimeout(gc_init, 300);
            
            frappe.gc().on('ready', function() {
                if (cint(frm.doc.from_gocardless))
                    this.disable_form(frm, {message: __('Linked to Gocardless.'), color: 'green'});
            });
        }
        gc_init();
    },
});