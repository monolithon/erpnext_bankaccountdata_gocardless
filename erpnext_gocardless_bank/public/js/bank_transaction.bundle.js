/*
*  ERPNext Gocardless Bank © 2024
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


if (typeof frappe.gc !== 'function')
    frappe.require('/assets/erpnext_gocardless_bank/js/gocardless.bundle.js');


frappe.ui.form.on('Bank Transaction', {
    onload: function(frm) {
        if (cstr(frm.doc.description).length)
            frm.toggle_display('description', true);
        
        function gc_init() {
            if (typeof frappe.gc !== 'function')
                return setTimeout(gc_init, 300);
            
            frappe.gc().on('ready change', function() {
                if (this.$isStrVal(frm.doc.gocardless_transaction_info))
                    frm.toggle_display('gocardless_transaction_info', !!this.is_enabled);
            });
        }
        gc_init();
    },
});