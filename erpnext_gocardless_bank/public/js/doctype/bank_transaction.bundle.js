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
        if (frm.is_new()) return;
        if (cstr(frm.doc.description).length)
            frm.toggle_display('description', true);
        
        function gc_init() {
            if (typeof frappe.gc !== 'function')
                return setTimeout(gc_init, 300);
            
            frappe.gc()
                .on('ready', function() {
                    if (cint(frm.doc.from_gocardless))
                        this.disable_form(frm, {message: __('Linked to Gocardless.'), color: 'green', ignore: this.$filter(frm.meta.fields, function(v) {
                            return ![
                                'date',
                                'status',
                                'bank_account',
                                'deposit',
                                'withdrawal',
                                'currency',
                                'description',
                                'gocardless_transaction_info',
                                'reference_number',
                                'transaction_id',
                                'from_gocardless'
                            ].includes(v.fieldname);
                        })});
                })
                .on('ready change', function() {
                    if (cint(frm.doc.from_gocardless) && this.$isStrVal(frm.doc.gocardless_transaction_info))
                        frm.toggle_display('gocardless_transaction_info', true);
                });
        }
        gc_init();
    },
});