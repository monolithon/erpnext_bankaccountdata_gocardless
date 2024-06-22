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
        function gc_init() {
            if (typeof frappe.gc !== 'function')
                return setTimeout(gc_init, 300);
            
            frm._gc = {};
            if (frm._gc_refresh) frm.events.gc_check_status(frm);
        }
        gc_init();
    },
    refresh: function(frm) {
        if (frm.doc.__needs_refresh) return frm.reload_doc();
        if (!frm._gc) frm._gc_refresh = 1;
        else frm.events.gc_check_status(frm);
    },
    gc_check_status: function(frm) {
        if (frm.is_new() || !frm._gc) return;
        if (!frm._gc.setup) return frm.events.gc_setup_form(frm);
        if (!frm._gc.data) return;
        if (!frm._gc.fields) frm.events.gc_setup_fields(frm);
        if (!frm._gc.error) frm.events.gc_setup_error(frm);
        if (!frm._gc.bar) frm.events.gc_load_toolbar(frm);
    },
    gc_setup_form: function(frm) {
        frm._gc.setup = 1;
        frappe.gc()
            .on('page_change', function() {
                this.off('bank_error');
                frm && delete frm._gc;
            })
            .on('ready change', function() {
                if (frm._gc.enabled == null) frm._gc.enabled = this.is_enabled;
                else if (frm._gc.enabled == this.is_enabled) return;
                frm.events.gc_setup_fields(frm, frm._gc.enabled ? 1 : 0);
                frm.events.gc_load_toolbar(frm, frm._gc.enabled ? 1 : 0);
                frm._gc.enabled = this.is_enabled;
                frm._gc.enabled && !frm._gc.data && frm.events.gc_get_data(frm);
            });
    },
    gc_setup_fields: function(frm, del) {
        let val = !del ? 1 : 0;
        if (frm._gc.fields === val) return;
        if (val) frm._gc.fields = 1;
        else delete frm._gc.fields;
        frm.toggle_display('bank_account_no', !val);
        frm.toggle_display('gocardless_bank_account_no', val);
    },
    gc_setup_error: function(frm) {
        frm._gc.error = 1;
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
            delete frm._gc.fields;
            frm.reload_doc();
        });
    },
    gc_load_toolbar: function(frm, del) {
        let label = __('Sync');
        if (frm.custom_buttons[label]) {
            if (del) {
                frm.custom_buttons[label].remove();
                delete frm.custom_buttons[label];
                delete frm._gc.bar;
                delete frm._gc.btn;
            }
            return;
        }
        if (del || frm._gc.bar) return;
        frm._gc.bar = 1;
        frm._gc.btn = frm.add_custom_button(label, function() {
            if (!frm._gc.data) return frm._gc.btn.prop('disabled', true);
            if (frappe.gc().$isStrVal(frm._gc.data.last_sync))
                return frm.events.gc_enqueue_sync(frm);
            frm.events.gc_show_prompt(frm);
        });
        frm.change_custom_button_type(label, null, 'success');
        !frm._gc.data && frm._gc.btn.prop('disabled', true);
    },
    gc_get_data: function(frm) {
        frappe.gc().request(
            'get_bank_account_data',
            {account: cstr(frm.docname)},
            function(ret) {
                if (
                    !this.$isDataObj(ret)
                    || !this.$isStrVal(ret.bank_account)
                    || !this.$isStrVal(ret.status)
                ) {
                    frm.events.gc_setup_fields(frm, 1);
                    frm.events.gc_load_toolbar(frm, 1);
                    return this._error('Bank account data received is invalid.');
                }
                if (ret.bank_account !== frm.docname) {
                    frm.events.gc_setup_fields(frm, 1);
                    frm.events.gc_load_toolbar(frm, 1);
                    return this._info('Bank account data received is for different bank account.', ret);
                }
                let status = ret.status.toLowerCase(),
                color = 'green';
                if ('error expired suspended'.indexOf(status) >= 0) color = 'red';
                else if ('discovered processing'.indexOf(status) >= 0) color = 'blue';
                frm.set_intro(
                    __('Linked to Gocardless [<strong>{0}</strong>].', [__(ret.status)]),
                    color
                );
                if (
                    !this.$isStrVal(ret.bank)
                    || !this.$isStrVal(ret.account)
                    || status !== 'ready'
                ) {
                    frm.events.gc_setup_fields(frm);
                    frm.events.gc_load_toolbar(frm, 1);
                    return;
                }
                frm._gc.data = ret;
                frm._gc.btn && frm._gc.btn.prop('disabled', false);
                frm.events.gc_check_status(frm);
            },
            function(e) {
                this._error(e.self ? e.message : __('Unable to get the bank account data for {0}.', [frm.docname]));
            }
        );
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
        frm._gc.btn.prop('disabled', true);
        let args = {
            bank: frm._gc.data.bank,
            account: frm._gc.data.account,
        };
        if (from_dt) {
            args.from_dt = from_dt;
            if (to_dt) args.to_dt = to_dt;
        }
        frappe.gc().request(
            'enqueue_bank_transactions_sync', args,
            function(ret) {
                frm._gc.btn.prop('disabled', false);
                if (!ret) {
                    this._error('Accounts: bank account sync failed');
                    return this.error_(__('Unable to sync the bank account "{0}".', [frm.docname]));
                }
                this._log('Accounts: bank account sync success');
                if (this.$isDataObj(ret) && ret.info) this.info_(ret.info);
                else this.success_(__('Bank account "{0}" is syncing in background', [frm.docname]));
            },
            function(e) {
                frm._gc.btn.prop('disabled', false);
                this.error(e.self ? e.message : __('Unable to sync the bank account "{0}".', [frm.docname]));
            }
        );
    },
});