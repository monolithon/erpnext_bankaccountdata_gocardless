/*
*  ERPNext Gocardless Bank © 2023
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/
        
frappe.ui.form.on('Gocardless Settings', {
    setup: function(frm) {
        frm._is_valid_secret_id = function() {
            let field = frm.get_field('secret_id'),
            val = frm.doc.secret_id;
            if (
                val.length !== 36
                || !(new RegExp('^([a-z0-9]{8})-([a-z0-9]{4})-([a-z0-9]{4})-([a-z0-9]{4})-([a-z0-9]{12})$', 'ig')).test(val)
            ) {
                field && field.set_invalid && field.set_invalid();
                return false;
            }
            return true;
        };
        frm._is_valid_secret_key = function() {
            let field = frm.get_field('secret_key'),
            val = frm.doc.secret_key;
            if (val.length !== 128 || !(new RegExp('^([a-z0-9]+)$', 'ig')).test(val)) {
                field && field.set_invalid && field.set_invalid();
                return false;
            }
            return true;
        };
    },
    refresh: function(frm) {
        let btn = frm.get_field('access_button');
        if (btn && btn.$input && !btn.$input.get(0).__ready) {
            btn.$input.get(0).__ready = true;
            btn.$input
                .removeClass('btn-default')
                .addClass('btn-success')
                .on('click', function(e) {
                    window.open('https://ob.gocardless.com/overview/', '_blank');
                });
        }
    },
    secret_id: function(frm) {
        frm._is_valid_secret_id();
    },
    secret_key: function(frm) {
        frm._is_valid_secret_key();
    },
    validate: function(frm) {
        let error = false;
        if (!frm._is_valid_secret_id()) {
            frappe.msgprint(__('The secret id is invalid.'));
            error = true;
        }
        if (!frm._is_valid_secret_key()) {
            frappe.msgprint(__('The secret key is invalid.'));
            error = true;
        }
        if (error) return false;
    }
});