/*
*  ERPNext Nordigen © 2023
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


frappe.provide("frappe.listview_settings");


frappe.listview_settings['Nordigen Bank'] = {
    add_fields: ['auth_expiry'],
    onload: function(list) {
        try {
            list._get_args = list.get_args;
            list.get_args = function() {
                let args = this._get_args();
                if (this.doctype === 'Nordigen Bank')
                    args.fields.push(frappe.model.get_full_column_name(
                        'auth_status', this.doctype
                    ));
                return args;
            };
            list.setup_columns();
            list.refresh(true);
            
            frappe.nordigen().on_ready(function() {
                localStorage.removeItem('nordigen_account_action_clicked');
                if (!this.is_enabled) {
                    list.page.clear_actions();
                    frappe.show_alert({
                        message: __('The Nordigen plugin is disabled.'),
                        indicator: 'red'
                    });
                    return;
                }
                let reference_id = null;
                if (frappe.has_route_options() && frappe.route_options.ref) {
                    reference_id = frappe.route_options.ref;
                    delete frappe.route_options.ref;
                }
                if (reference_id) {
                    let key = 'nordigen_' + reference_id,
                    auth = localStorage.getItem(key);
                    if (!auth) return;
                    localStorage.removeItem(key);
                    try {
                        auth = JSON.parse(auth);
                    } catch(e) {
                        auth = null;
                    }
                    if (
                        !$.isPlainObject(auth)
                        || !auth.name || !auth.bank
                        || !auth.id || !auth.expiry
                    ) {
                        this.error('The authorization data for reference id "{0}" is invalid.', [reference_id]);
                        return;
                    }
                    this.request(
                        'save_bank_link',
                        {
                            name: auth.name,
                            auth_id: auth.id,
                            auth_expiry: auth.expiry,
                        },
                        function(ret) {
                            if (!ret) {
                                this.error('Unable to link to {0}.', [auth.bank]);
                                return;
                            }
                            frappe.show_alert({
                                message: __('{0} is linked successfully', [auth.bank]),
                                indicator: 'green'
                            });
                            list.refresh();
                        },
                        function() {
                            this.error('Unable to link {0}.', [auth.bank]);
                        }
                    );
                }
            });
        } catch(e) {
            frappe.nordigen()._error('list onload', e.message);
        }
    },
    hide_name_column: true,
    get_indicator: function(doc) {
        if (doc.disabled) return [__('Disabled'), 'red', 'disabled,=,Yes'];
        return [__('Enabled'), 'green', 'disabled,=,No'];
    },
    button: {
        show: function(doc) {
            return frappe.nordigen().is_ready
                && frappe.nordigen().is_enabled
                && !cint(doc.disabled)
                && doc.auth_status === 'Unlinked';
        },
        get_label: function(doc) {
            return __('Link');
        },
        get_description: function(doc) {
            return __('Link to {0}', [doc.name]);
        },
        action: function(doc) {
            let action_clicked = localStorage.getItem('nordigen_account_action_clicked');
            if (action_clicked) return;
            localStorage.setItem('nordigen_account_action_clicked', true);
            try {
                frappe.nordigen().connect_to_bank(
                    doc.bank_id,
                    cint(doc.transaction_days),
                    null,
                    function(link, reference_id, auth_id, auth_expiry) {
                        localStorage.setItem(
                            'nordigen_' + reference_id,
                            JSON.stringify({
                                name: doc.name,
                                bank: doc.bank,
                                id: auth_id,
                                expiry: moment().add(cint(auth_expiry), 'days')
                                    .format(frappe.defaultDateFormat)
                            })
                        );
                        this.info('Redirecting to {0} authorization page.', [doc.bank]);
                        window.setTimeout(function() {
                            window.location.href = link;
                        }, 2000);
                    },
                    function(e) {
                        localStorage.removeItem('nordigen_account_action_clicked');
                        this._error('list action', e.message);
                    }
                );
            } catch(e) {
                localStorage.removeItem('nordigen_account_action_clicked');
                frappe.nordigen()._error('list action', e.message);
            }
        },
    },
    formatters: {
        title: function(v, df, doc) {
            frappe.nordigen()._log('The auth status for ' + doc.title + 'is:', doc.auth_status);
            if (!doc.auth_status || doc.auth_status === 'Linked') return v;
            return v + ' <span class="badge badge-danger">' + __('Unlinked') + '</span>';
        },
        auth_expiry: function(v) {
            if (!v || !v.length) return '';
            return moment(v, frappe.defaultDateFormat).fromNow();
        },
    },
};