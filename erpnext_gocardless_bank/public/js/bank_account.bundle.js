/*
*  ERPNext Gocardless Bank © 2023
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/

frappe.gocardless.events = {
    init: false,
    list: {},
    has: function(name) {
        return this.list[name] != null;
    },
    add: function(name, fn, once) {
        if (this.has(name)) return;
        if (!this.init) {
            frappe.socketio.init();
            this.init = true;
        }
        var me = this;
        let callback = once ? function(ret) {
            frappe.realtime.off(name, me.list[name]);
            delete me.list[name];
            fn(ret);
        } : fn;
        this.list[name] = callback;
        frappe.realtime.on(name, callback);
    },
    clear: function() {
        for (var name in this.list) {
            frappe.realtime.off(name, this.list[name]);
            delete this.list[name];
        }
    },
};


frappe.ui.form.on('Bank Account', {
    setup: function(frm) {
        frm._gocardless_setup = false;
        frm._gocardless_data = null;
        frm._gocardless_fields = false;
        frm._gocardless_toolbar = false;
        frm._gocardless_btn = null;
    },
    refresh: function(frm) {
        if (frm.doc.__needs_refresh) {
            frappe.gocardless.events.clear();
            frm.reload_doc();
        } else frm.trigger('check_status');
    },
    check_status: function(frm) {
        if (frm.is_new()) return;
        if (!frm._gocardless_setup) {
            frm.trigger('setup_gocardless');
            return;
        }
        if (!frm._gocardless_data) return;
        if (!frm._gocardless_fields) {
            frm._gocardless_fields = true;
            frm.toggle_display('bank_account_no', false);
            frm.toggle_display('gocardless_bank_account_no', true);
        }
        if (!frm._gocardless_toolbar)
            frm.trigger('load_toolbar');
    },
    setup_gocardless: function(frm) {
        frm._gocardless_setup = true;
        frappe.gocardless().on_ready(function() {
            if (!this.is_enabled) return;
            this.request(
                'get_bank_account_data',
                {
                    bank_account: frm.doc.name,
                },
                function(ret) {
                    if (!$.isPlainObject(ret)) {
                        if (cint(ret) === 0)
                            this._error('The Gocardless plugin is disabled.');
                        else if (cint(ret) === -1)
                            this._info(__('The bank account "{0}" is not part of any Gocardless linked bank.',
                                [frm.doc.name]));
                        return;
                    }
                    if (!ret.bank_account || ret.bank_account !== frm.doc.name) {
                        this._error('The bank account data received is invalid.', ret);
                        return;
                    }
                    if (ret.error) {
                        this._error(ret.error);
                        return;
                    }
                    let status = cstr(ret.status).toLowerCase();
                    if (!status.length) {
                        this._error('The bank account data received is invalid.', ret);
                        return;
                    }
                    let color = 'green';
                    if (
                        status === 'error' || status === 'expired'
                        || status === 'suspended'
                    ) color = 'red';
                    if (status === 'discovered' || status === 'processing') color = 'blue';
                    frm.set_intro(
                        __('Linked to Gocardless (Status: <strong>{0}</strong>).', [ret.status]),
                        color
                    );
                    if (!ret.bank || !ret.account || status !== 'ready') return;
                    frm._gocardless_data = ret;
                    frm.trigger('check_status');
                },
                function() {
                    this._error(__('Unable to get the bank account data for {0}.', [frm.doc.name]));
                }
            );
        });
    },
    load_toolbar: function(frm) {
        if (!frappe.gocardless.events.has('gocardless_bank_error'))
            frappe.gocardless.events.add(
                'gocardless_bank_error',
                function(ret) {
                    frappe.gocardless()._log('error event received');
                    if (ret && $.isPlainObject(ret)) ret = ret.message || ret;
                    if (
                        $.isPlainObject(ret) && ret.error && (ret.name || ret.bank)
                        && (ret.name === frm.doc.name || ret.bank === frm.doc.bank)
                    ) {
                        frappe.gocardless().error(ret.error);
                    } else {
                        frappe.gocardless()._error('invalid error data received', ret);
                    }
                    frappe.gocardless.events.clear();
                    frm._gocardless_fields = false;
                    frm.reload_doc();
                }
            );
        let sync_btn = __('Sync');
        if (frm.custom_buttons[sync_btn]) return;
        frm._gocardless_toolbar = true;
        if (frm._gocardless_btn) frm._gocardless_btn.remove();
        frm._gocardless_btn = null;
        function enqueue_account_sync(from_date, to_date) {
            frm._gocardless_btn.prop('disabled', true);
            let args = {
                bank: frm._gocardless_data.bank,
                account: frm._gocardless_data.account,
            };
            if (from_date) args.from_date = from_date;
            if (to_date) args.to_date = to_date;
            frappe.gocardless().request(
                'enqueue_bank_account_sync',
                args,
                function(ret) {
                    frm._gocardless_btn.prop('disabled', false);
                    if (!ret) {
                        this.error('Unable to sync the bank account "{0}".', [frm.doc.name]);
                        return;
                    }
                    if (cint(ret) === -1) {
                        this.error('The Gocardless plugin is disabled.');
                        return;
                    }
                    if (cint(ret) === -2) {
                        this.error('The bank "{0}" is not linked to Gocardless.', [frm._gocardless_data.bank]);
                        return;
                    }
                    if (cint(ret) === -3) {
                        this.error('The bank account "{0}" is not part of the Gocardless linked bank "{1}".',
                            [frm.doc.name, frm._gocardless_data.bank]);
                        return;
                    }
                    frappe.show_alert({
                        message: __('Bank account "{0}" is syncing in background', [frm.doc.name]),
                        indicator: 'green'
                    });
                },
                function() {
                    frm._gocardless_btn.prop('disabled', false);
                    this.error('Unable to sync the bank account "{0}".', [frm.doc.name]);
                }
            );
        }
        frm._gocardless_btn = frm.add_custom_button(sync_btn, function() {
            if (!frm._gocardless_data) {
                frm._gocardless_btn.prop('disabled', true);
                return;
            }
            if (cstr(frm._gocardless_data.last_sync).length) {
                enqueue_account_sync();
                return;
            }
            frappe.prompt(
                [
                    {
                        'fieldname': 'from_date',
                        'fieldtype': 'Date',
                        'label': __('From Date'),
                        'reqd': 1,
                        'default': frappe.datetime.nowdate(),
                        'max_date': frappe.datetime.now_date(true),
                    },
                    {
                        'fieldname': 'to_date',
                        'fieldtype': 'Date',
                        'label': __('To Date'),
                        'reqd': 1,
                        'default': frappe.datetime.nowdate(),
                        'max_date': frappe.datetime.now_date(true),
                    },
                ],
                function(values) {
                    frm._gocardless_data.last_sync = frappe.datetime.nowdate();
                    enqueue_account_sync(values.from_date, values.to_date);
                },
                __('Sync Bank Account Transactions'),
                sync_btn
            );
        });
        frm.change_custom_button_type(sync_btn, null, 'success');
    }
});