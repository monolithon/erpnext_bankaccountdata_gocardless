/*
*  ERPNext Gocardless Bank © 2024
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


if (typeof frappe.gc !== 'function')
    frappe.require('/assets/erpnext_gocardless_bank/js/gocardless.bundle.js');


frappe.ui.form.on('Bank Account', {
    onload: function(frm) {
        if (frm.is_new()) return;
        function gc_init() {
            if (typeof frappe.gc !== 'function')
                return setTimeout(gc_init, 300);
            
            frappe.gc()
                .on('page_change', function() {
                    if (frm) delete frm._gc;
                })
                .on('ready', function() {
                    if (!cint(frm.doc.from_gocardless)) return;
                    frm.toggle_display('bank_account_no', false);
                    frm.toggle_display('gocardless_bank_account_no', true);
                    frm.events.gc_get_data(frm);
                })
                .on('change', function() {
                    if (!cint(frm.doc.from_gocardless)) return;
                    if (frm._gc) frm.events.gc_load_toolbar(frm, !this.is_enabled || !frm._gc.ready);
                });
        }
        gc_init();
    },
    gc_get_data: function(frm) {
        var ignore = frappe.gc().$map(frappe.gc().$filter(frm.meta.fields, function(v) {
            return ![
                'account_name',
                'gocardless_bank_account_no',
                'account_type',
                'iban',
                'bank',
                'company',
                'party_type',
                'party',
                'from_gocardless'
            ].includes(v.fieldname);
        }), function(v) { return v.fieldname; });
        frappe.gc().request(
            'get_bank_account_data',
            {account: cstr(frm.docname)},
            function(ret) {
                if (
                    !this.$isDataObj(ret)
                    || !this.$isStrVal(ret.bank_account)
                    || !this.$isStrVal(ret.status)
                ) {
                    this.disable_form(frm, {message: __('Linked to Gocardless.'), color: 'blue', ignore: ignore});
                    return this._error('Bank account data received is invalid.');
                }
                if (ret.bank_account !== frm.docname) {
                    this.disable_form(frm, {message: __('Linked to Gocardless.'), color: 'blue', ignore: ignore});
                    return this._info('Bank account data received is for different bank account.', ret);
                }
                frm._gc = ret;
                let status = ret.status.toLowerCase(),
                color = 'green';
                frm._gc.ready = status === 'ready';
                if ('error expired suspended'.indexOf(status) >= 0) color = 'red';
                else if ('discovered processing'.indexOf(status) >= 0) color = 'blue';
                this.disable_form(frm, {
                    message: __('Linked to Gocardless [<strong>{0}</strong>].', [__(ret.status)]),
                    color: color,
                    ignore: ignore
                });
                if (frm._gc.ready) frm.events.gc_setup_error(frm);
                if (this.is_enabled && frm._gc.ready) frm.events.gc_load_toolbar(frm);
            },
            function(e) {
                this.disable_form(frm, {message: __('Linked to Gocardless.'), color: 'blue', ignore: ignore});
                this._error(e.self ? e.message : __('Unable to get the bank account data for {0}.', [frm.docname]));
            }
        );
    },
    gc_setup_error: function(frm) {
        frappe.gc().real('bank_error', function(ret) {
            if (!this.is_enabled) return;
            this._log('error event received');
            if (
                !this.$isDataObj(ret) || !this.$isStrVal(ret.error)
                || (
                    ret.any == null
                    && (!this.$isStrVal(ret.name) || ret.name !== cstr(frm.doc.name))
                    && (!this.$isStrVal(ret.bank) || ret.bank !== cstr(frm.doc.bank))
                )
            ) return this._error('Invalid error data received', ret);
            this.error(ret.error);
            frm.reload_doc();
        });
    },
    gc_load_toolbar: function(frm, del) {
        var label = __('Sync');
        if (frm.custom_buttons[label]) {
            if (!del) return;
            frm.custom_buttons[label].remove();
            delete frm.custom_buttons[label];
        }
        if (del) return;
        frm.add_custom_button(label, function() {
            if (frappe.gc().$isStrVal(frm._gc.last_sync)) frm.events.gc_enqueue_sync(frm);
            else frm.events.gc_show_prompt(frm);
        });
        frm.change_custom_button_type(label, null, 'success');
    },
    gc_show_prompt: function(frm) {
        frappe.gc()._log('Accounts: prompting bank account sync dates');
        frappe.prompt(
            [
                {
                    fieldname: 'from_dt',
                    fieldtype: 'Date',
                    label: __('From Date'),
                    reqd: 1,
                    bold: 1,
                    'default': frappe.datetime.nowdate(),
                    max_date: frappe.datetime.now_date(true),
                },
                {
                    fieldname: 'to_dt',
                    fieldtype: 'Date',
                    label: __('To Date'),
                    reqd: 1,
                    bold: 1,
                    'default': frappe.datetime.nowdate(),
                    max_date: frappe.datetime.now_date(true),
                },
            ],
            function(vals) {
                frappe.gc()._log('Accounts: syncing bank account', vals);
                frm.events.gc_enqueue_sync(frm, vals.from_dt, vals.to_dt);
            },
            __('Sync Bank Account Transactions'),
            __('Sync')
        );
    },
    gc_enqueue_sync: function(frm, from_dt, to_dt) {
        var label = __('Sync');
        frm.custom_buttons[label].prop('disabled', true);
        let args = {
            bank: frm._gc.bank,
            account: frm._gc.account,
        };
        if (from_dt) {
            args.from_dt = from_dt;
            if (to_dt) args.to_dt = to_dt;
        }
        frappe.gc().request(
            'enqueue_bank_transactions_sync', args,
            function(ret) {
                if (!ret) {
                    frm.custom_buttons[label].prop('disabled', false);
                    this._error('Accounts: bank account sync failed');
                    return this.error_(__('Unable to sync the bank account "{0}".', [frm.docname]));
                }
                if (this.$isDataObj(ret) && ret.info) return this.info_(ret.info);
                frm.custom_buttons[label].prop('disabled', false);
                this.success_(__('Bank account "{0}" is syncing in background', [frm.docname]));
            },
            function(e) {
                frm.custom_buttons[label].prop('disabled', false);
                this.error(e.self ? e.message : __('Unable to sync the bank account "{0}".', [frm.docname]));
            }
        );
    },
});