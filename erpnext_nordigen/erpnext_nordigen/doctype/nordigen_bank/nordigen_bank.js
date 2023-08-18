/*
*  ERPNext Nordigen © 2023
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/

frappe.nordigen.events = {
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


frappe.ui.form.on('Nordigen Bank', {
    setup: function(frm) {
        frappe.nordigen();
        frm._is_old = cstr(frm.doc.bank).length > 0 && cstr(frm.doc.bank_id).length > 0;
        frm._form_disabled = false;
        frm._nordigen_setup = false;
        frm._nordigen_disabled = false;
        frm._banks = {key: '', list: {}, cache: {}};
        frm._bank_accounts_loading_key = 'nordigen_loading_accounts_ts';
        frm._bank_accounts_loading_timeout = 5;
        frm._linked_bank_accounts = null;
    },
    onload: function(frm) {
        frm.get_field('sync_html').html(
            '<p class="text-danger">'
                + __('For security reasons, transactions synchronization for each bank account, both manual and auto sync, is limited to a total of four times per day.')
            + '</p>'
        );
    },
    refresh: function(frm) {
        if (frm.doc.__needs_refresh) {
            frappe.nordigen.events.clear();
            frm.reload_doc();
        } else frm.trigger('check_status');
    },
    company: function(frm) {
        if (frm._form_disabled) return;
        if (!cstr(frm.doc.company).length || cstr(frm.doc.country).length) return;
        frappe.db.get_value('Company', frm.doc.company, 'country')
        .then(function(ret) {
            if (ret && $.isPlainObject(ret)) ret = ret.message || ret;
            if (typeof ret === 'string') frm.set_value('country', ret);
        });
    },
    country: function(frm) {
        if (!frm._form_disabled && !frm._is_old) frm.trigger('load_banks');
    },
    bank: function(frm) {
        let val = cstr(frm.doc.bank);
        if (!val.length) return;
        if (frm._is_old) {
            frm.get_field('bank').set_data([{label: __(val), value: val}]);
            return;
        }
        if (frm._form_disabled) return;
        let cache = frm._banks.cache[frm._banks.key],
        found = false,
        i = 0,
        l = cache.length;
        for (; i < l; i++) {
            if (cache[i].name === val) {
                frm.set_value('bank_id', cache[i].id);
                frm.set_value('transaction_days', cint(cache[i].transaction_total_days || 90));
                found = true;
                break;
            }
        }
        if (!found) frappe.nordigen().error('Please select a valid bank.');
    },
    validate: function(frm) {
        if (!cstr(frm.doc.company).length)
            frappe.nordigen().error('Please select a company.');
        if (!cstr(frm.doc.bank).length)
            frappe.nordigen().error('Please select a bank.');
        if (!cstr(frm.doc.bank_id).length || !cint(frm.doc.transaction_days))
            frappe.nordigen().error('The bank data is invalid.');
    },
    after_save: function(frm) {
        frappe.nordigen()._log('Bank is saved');
        frm._is_old = cstr(frm.doc.bank).length > 0 && cstr(frm.doc.bank_id).length > 0;
    },
    check_status: function(frm) {
        if (cint(frm.doc.disabled)) {
            if (!frm._form_disabled) {
                frm._form_disabled = true;
                frm.disable_form();
                frm.set_intro(__('Nordigen bank is disabled.'), 'red');
            }
            return;
        }
        
        if (!frappe.nordigen.events.has('nordigen_bank_error'))
            frm.trigger('register_events');
        
        if (!frm._nordigen_setup) {
            frm.trigger('setup_nordigen');
            return;
        }
        
        if (frm._nordigen_disabled) {
            if (!frm._form_disabled) {
                frm._form_disabled = true;
                frm.disable_form();
                frm.set_intro(__('The Nordigen plugin is disabled.'), 'red');
            }
            return;
        }
        
        if (frm._form_disabled) {
            if (!cint(frm.doc.disabled)) {
                frm._form_disabled = false;
                frm.refresh();
            }
            return;
        }
        
        if (!frm._is_old) frm.trigger('load_banks');
        frm.trigger('load_toolbar');
        frm.trigger('load_accounts');
    },
    register_events: function(frm) {
        frappe.nordigen()._log('register_events');
        frappe.nordigen.events.add(
            'nordigen_bank_error',
            function(ret) {
                frappe.nordigen()._log('Error event received');
                if (ret && $.isPlainObject(ret)) ret = ret.message || ret;
                if (
                    $.isPlainObject(ret) && ret.error && (ret.name || ret.bank)
                    && (ret.name === frm.doc.name || ret.bank === frm.doc.bank)
                ) {
                    frappe.nordigen().error(ret.error);
                } else {
                    frappe.nordigen()._error('Invalid error data received', ret);
                }
                localStorage.removeItem(frm._bank_accounts_loading_key);
                frm._linked_bank_accounts = null;
                frappe.nordigen.events.clear();
                frm.reload_doc();
            }
        );
        frappe.nordigen()._log('error event is registered');
    },
    setup_nordigen: function(frm) {
        frappe.nordigen()._log('setup_nordigen');
        frm._nordigen_setup = true;
        frappe.nordigen().on_ready(function() {
            if (!this.is_enabled) {
                this._log('nordigen is disabled');
                frm._nordigen_disabled = true;
                frm.trigger('check_status');
                return;
            }
            if (frm._is_old && !frm._form_disabled && (
                !cstr(frm.doc.auth_id).length
                || cstr(frm.doc.auth_status) === 'Unlinked'
            )) {
                let reference_id = null;
                if (frappe.has_route_options() && frappe.route_options.ref) {
                    reference_id = frappe.route_options.ref;
                    delete frappe.route_options.ref;
                }
                if (reference_id) {
                    let key = 'nordigen_' + reference_id,
                    auth = localStorage.getItem(key);
                    if (!auth) {
                        frm.trigger('check_status');
                        return;
                    }
                    localStorage.removeItem(key);
                    try {
                        auth = JSON.parse(auth);
                    } catch(_) {
                        auth = null;
                    }
                    if (
                        !$.isPlainObject(auth)
                        || !auth.id || !auth.expiry
                    ) {
                        this.error('The authorization data for {0} is invalid.', [frm.doc.bank]);
                        frm.trigger('check_status');
                        return;
                    }
                    frappe.call({
                        method: 'save_link',
                        doc: frm.doc,
                        args: {
                            auth_id: auth.id,
                            auth_expiry: auth.expiry,
                        },
                        callback: function(res) {
                            if (!res) {
                                frappe.nordigen().error('Unable to link to {0}.', [frm.doc.bank]);
                                frappe.nordigen.events.clear();
                                frm.reload_doc();
                                return;
                            }
                            frappe.show_alert({
                                message: __('{0} is linked successfully', [frm.doc.bank]),
                                indicator: 'green'
                            });
                            let ts = new Date();
                            ts.setMinutes(ts.getMinutes() + frm._bank_accounts_loading_timeout);
                            localStorage.setItem(frm._bank_accounts_loading_key, ts.getTime());
                            frappe.nordigen()._log('bank account is linked');
                            frappe.nordigen.events.clear();
                            frm.reload_doc();
                        },
                        error: function(e) {
                            frappe.nordigen().error('Unable to link to {0}.', [frm.doc.bank]);
                            frappe.nordigen.events.clear();
                            frm.reload_doc();
                        }
                    });
                    return;
                }
            }
            frm.trigger('check_status');
        });
    },
    load_banks: function(frm) {
        if (frm._form_disabled) return;
        let country = cstr(frm.doc.country);
        var key = country.length ? country : 'all';
        if (frm._banks.key === key) return;
        if (frm._banks.list[key]) {
            frm._banks.key = key;
            frm.get_field('bank').set_data(frm._banks.list[key]);
            frappe.nordigen()._log('setting banks');
            return;
        }
        frappe.nordigen()._log('loading banks');
        frappe.nordigen().request(
            'get_banks',
            country.length ? {country: country} : null,
            function(ret) {
                if (!Array.isArray(ret)) {
                    this._error('Invalid banks list.', ret);
                    this.error('The banks list received is invalid.');
                    return;
                }
                
                // @todo: For debug, remove in production
                ret.unshift({
                    id: 'SANDBOXFINANCE_SFIN0000',
                    name: 'Sandbox Finance (Testing)',
                });
                
                let data = [],
                cache = [];
                ret.forEach(function(v) {
                    let row = Object.assign({}, v);
                    cache.push(row);
                    data.push({label: __(v.name), value: v.name});
                });
                frm._banks.key = key;
                frm._banks.list[key] = data;
                frm._banks.cache[key] = cache;
                frm.get_field('bank').set_data(data);
                frappe.nordigen()._log('setting banks');
            },
            function() {
                this.error('Unable to load the list of banks.');
            }
        );
    },
    load_toolbar: function(frm) {
        if (
            !frm._is_old || frm._form_disabled
            || (
                cstr(frm.doc.auth_id).length
                && cstr(frm.doc.auth_status) === 'Linked'
            )
        ) return;
        let auth_btn = __('Authorize');
        if (frm.custom_buttons[auth_btn]) {
            frappe.nordigen()._log('Toolbar: already visible');
            return;
        }
        frappe.nordigen()._log('Toolbar: adding auth button');
        frm.add_custom_button(auth_btn, function() {
            frappe.nordigen().connect_to_bank(
                frm.doc.bank_id,
                cint(frm.doc.transaction_days),
                cstr(frm.doc.name),
                function(link, reference_id, auth_id, auth_expiry) {
                    localStorage.setItem(
                        'nordigen_' + reference_id,
                        JSON.stringify({
                            id: auth_id,
                            expiry: moment().add(cint(auth_expiry), 'days')
                                .format(frappe.defaultDateFormat)
                        })
                    );
                    this.info('Redirecting to {0} authorization page.', [frm.doc.bank]);
                    window.setTimeout(function() {
                        window.location.href = link;
                    }, 2000);
                },
                function(e) {
                    this._error('Toolbar: auth error', e.message);
                }
            );
        });
        frm.change_custom_button_type(auth_btn, null, 'success');
    },
    load_accounts: function(frm) {
        if (!frm._is_old || !cstr(frm.doc.auth_id).length) return;
        let field = frm.get_field('bank_accounts_html');
        if (!field || !field.$wrapper) {
            frappe.nordigen()._log('Accounts: table field doesn\'t exist.');
            return;
        }
        if (!frappe.nordigen.events.has('nordigen_reload_bank_accounts')) {
            frappe.nordigen()._log('register bank accounts reload event');
            frappe.nordigen.events.add(
                'nordigen_reload_bank_accounts',
                function(ret) {
                    frappe.nordigen()._log('Accounts: reload event received');
                    if (ret && $.isPlainObject(ret)) ret = ret.message || ret;
                    if (
                        $.isPlainObject(ret) && (ret.name || ret.bank)
                        && (ret.name === frm.doc.name || ret.bank === frm.doc.bank)
                    ) {
                        frappe.nordigen()._log('Accounts: reloading doc event');
                    } else {
                        frappe.nordigen()._error('Accounts: invalid bank accounts reloading data received', ret);
                    }
                    localStorage.removeItem(frm._bank_accounts_loading_key);
                    frm._linked_bank_accounts = null;
                    frappe.nordigen.events.clear();
                    frm.reload_doc();
                }
            );
            frappe.nordigen()._log('Accounts: reload event registered');
        }
        let ts = cint(localStorage.getItem(frm._bank_accounts_loading_key));
        if (ts > 0) {
            if (ts > (new Date()).getTime()) {
                window.setTimeout(function() {
                    let ots = cint(localStorage.getItem(frm._bank_accounts_loading_key));
                    if (!ots) return;
                    localStorage.removeItem(frm._bank_accounts_loading_key);
                    frm._linked_bank_accounts = null;
                    frappe.nordigen.events.clear();
                    frm.reload_doc();
                }, frm._bank_accounts_loading_timeout * 10000);
                frappe.nordigen.accounts.build_loading(frm, field);
                return;
            }
            localStorage.removeItem(frm._bank_accounts_loading_key);
        }
        
        frappe.nordigen.accounts.build_table(frm, field);
        frappe.nordigen.accounts.render_table(frm);
    },
});

frappe.nordigen.accounts = {
    build_loading: function(frm, field) {
        frappe.nordigen()._log('Accounts: empty table');
        if (frm._accounts_table) {
            frappe.nordigen()._log('Accounts: hiding table');
            frm._accounts_table.hide();
        }
        if (!frm._accounts_loading) {
            frappe.nordigen()._log('Accounts: building loading');
            frm._accounts_loading = $(
                '<div class="mb-4 mx-md-2 mx-1 text-center">'
                    + '<div class="spinner-border m-2" role="status">'
                        + '<span class="sr-only">' + __('Loading') + '...</span>'
                    + '</div>'
                    + '<div class="text-center">'
                        + __('Syncing Bank Accounts')
                    + '</div>'
                + '</div>'
            ).appendTo(field.$wrapper);
        }
        frappe.nordigen()._log('Accounts: showing loading');
        frm._accounts_loading.show();
    },
    build_table: function(frm, field) {
        if (frm._accounts_loading) {
            frappe.nordigen()._log('Accounts: hiding loading');
            frm._accounts_loading.hide();
        }
        if (frm._accounts) return;
        frappe.nordigen()._log('Accounts: building table');
        $('<style type="text/css">\
            .nordigen-table {\
                table-layout: auto;\
                margin-bottom: 0;\
            }\
            .nordigen-table th,\
            .nordigen-table td {\
                vertical-align: middle;\
                white-space: nowrap;\
                text-align: center;\
                width: auto;\
            }\
            .nordigen-table th[scope="col"],\
            .nordigen-table td[scope="row"] {\
                width: 100%;\
                text-align: left;\
                font-weight: bold;\
            }\
            html[dir="rtl"] .nordigen-table th[scope="col"],\
            html[dir="rtl"] .nordigen-table td[scope="row"] {\
                text-align: right;\
            }\
            .nordigen-action > .spinner-border {\
                margin-right: 0.5rem;\
            }\
            html[dir="rtl"] .nordigen-action > .spinner-border {\
                margin-left: 0.5rem;\
            }\
            .nordigen-link {\
                margin-right: 0.5rem;\
            }\
            html[dir="rtl"] .nordigen-link {\
                margin-left: 0.5rem;\
            }\
        </style>').appendTo('head');
        frm._accounts_wrapper = $('<div class="table-responsive mb-4 mx-md-2 mx-1"></div>').appendTo(field.$wrapper);
        let columns = [
            '<th scope="col">' + __('Account') + '</th>',
            '<th>' + __('Balance') + '</th>',
            '<th>' + __('Status') + '</th>'
        ];
        if (!frm._form_disabled) columns.push('<th>' + __('Actions') + '</th>');
        frm._accounts_table = $('<table class="table table-bordered table-hover nordigen-table">'
            + '<thead class="thead-dark">'
                + '<tr>'
                    + columns.join('')
                + '</tr>'
            + '</thead>'
            + '<tbody>'
            + '</tbody>'
        + '</table>').appendTo(frm._accounts_wrapper);
        frm._accounts_table_body = frm._accounts_table.find('tbody').first();
        frm._accounts = {};
        frm._accounts.$account = function(row) {
            let html = '<strong>' + row.account + '</strong>';
            html += '<br/><small class="text-muted">' + __('ID') + ': ' + row.account_id + '</small>';
            if (cstr(row.last_sync).length) {
                html += '<br/><small class="text-muted">' + __('Last Update') + ': '
                    + moment(row.last_sync, frappe.defaultDateFormat).fromNow() + '</small>';
            }
            return '<td scope="row">' + html + '</td>';
        };
        frm._accounts.$balance = function(row) {
            if (!row.balances) return '<td></td>';
            let list = null;
            try {
                list = JSON.parse(row.balances);
            } catch(_) {
                list = null;
            }
            if (!list || !list.length) return '<td></td>';
            let html = [];
            list.forEach(function(v) {
                html.push(
                    '<small class="text-muted">'
                    + __(frappe.nordigen.accounts.get_balance_label(v.type))
                    + ': ' + format_currency(v.amount, v.currency)
                    + '</small>'
                );
            });
            html = html.join('<br/>');
            return '<td>' + html + '</td>';
        };
        frm._accounts.$status = function(row) {
            let color = 'text-muted';
            if (row.status === 'Ready' || row.status === 'Enabled') color = 'text-success';
            else if (row.status === 'Expired' || row.status === 'Error' || row.status === 'Deleted') color = 'text-danger';
            else if (row.status === 'Processing') color = 'text-info';
            else if (row.status === 'Suspended' || row.status === 'Blocked') color = 'text-warning';
            return '<td><span class="' + color + '">' + __(row.status) + '</span></td>';
        };
        if (frm._form_disabled) {
            frm._accounts.$action = function(row) { return ''; };
            return;
        }
        frappe.nordigen()._log('Accounts: building table actions');
        frm._accounts.$action = function(row) {
            let html = '<button type="button" class="btn {color} btn-sm {action}"{attr}>{label}</button>',
            actions = [],
            exists = cstr(row.bank_account).length > 0,
            disabled = row.status !== 'Ready' && row.status !== 'Enabled';
            if (exists) {
                actions.push(
                    html
                        .replace('{action}', 'nordigen-link')
                        .replace('{color}', 'btn-success')
                        .replace('{attr}', ' data-nordigen-account="' + row.account + '"')
                        .replace('{label}', __('Edit'))
                );
            }
            actions.push(
                html
                    .replace('{action}', 'nordigen-action')
                    .replace('{color}', disabled ? 'btn-default' : (exists ? 'btn-info' : 'btn-primary'))
                    .replace('{attr}', disabled ? ' disabled' : ' data-nordigen-account="' + row.account + '"')
                    .replace('{label}', exists ? __('Sync') : __('Add'))
            );
            return '<td>' + actions.join('') + '</td>';
        };
        frm._accounts_table.on('click', 'button.nordigen-action', function() {
            if (frm._accounts_table_action_clicked) return;
            frappe.nordigen()._log('Accounts: table add action button clicked');
            frm._accounts_table_action_clicked = true;
            window.setTimeout(function() {
                delete frm._accounts_table_action_clicked;
            }, 1000);
            frappe.nordigen.accounts.action_handler(frm, $(this));
        });
        frm._accounts_table.on('click', 'button.nordigen-link', function() {
            let $el = $(this),
            account = $el.attr('data-nordigen-account');
            if (account == null) {
                frappe.nordigen()._log('Accounts Link: unable to get account from table action');
                return;
            }
            var row = null;
            if ((frm.doc.bank_accounts || []).length) {
                for (let i = 0, l = frm.doc.bank_accounts.length; i < l; i++) {
                    if (frm.doc.bank_accounts[i].account === account) {
                        frappe.nordigen()._log('Accounts Link: table action row found');
                        row = frm.doc.bank_accounts[i];
                        break;
                    }
                }
            }
            if (!row) frappe.nordigen()._log('Accounts Link: table action row not found');
            if (row.status !== 'Ready' && row.status !== 'Enabled')
                frappe.nordigen()._log('Accounts Link: table account not ready', row);
            if (!row || (row.status !== 'Ready' && row.status !== 'Enabled')) {
                frappe.nordigen.accounts.toggle_action($el, false);
                return;
            }
            frappe.set_route('Form', 'Bank Account', row.bank_account);
        });
    },
    render_table: function(frm) {
        frappe.nordigen()._log('Accounts: rendering bank account table');
        frm._accounts_table_body.empty();
        
        if ((frm.doc.bank_accounts || []).length) {
            frm.doc.bank_accounts.forEach(function(row) {
                frm._accounts_table_body.append($('<tr>'
                    + frm._accounts.$account(row)
                    + frm._accounts.$balance(row)
                    + frm._accounts.$status(row)
                    + frm._accounts.$action(row)
                + '</tr>'));
            });
        } else {
            frm._accounts_table_body.append($('<tr>'
                + '<td scope="row" colspan="' + (3 + (!frm._form_disabled ? 1 : 0)) + '" class="text-center text-muted">'
                    + __('No bank account was received.')
                + '</td>'
            + '</tr>'));
        }
    },
    balance_labels: {
        openingBooked: 'Opening',
        closingBooked: 'closing',
        expected: 'Expected',
        forwardAvailable: 'Fwd. Interim',
        interimAvailable: 'Avail. Interim',
        interimBooked: 'Interim',
        nonInvoiced: 'Non Invoiced',
    },
    get_balance_label: function(key) {
        return frappe.nordigen.accounts.balance_labels[key];
    },
    toggle_action: function(el, state) {
        el.attr('disabled', state === false)
            .prop('disabled', state === false);
    },
    create_spinner: function(el) {
        var spinner = $('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>');
        frappe.nordigen.accounts.toggle_action(el, false);
        el.prepend(spinner);
        return spinner;
    },
    remove_spinner: function(el, spinner) {
        if (spinner) spinner.remove();
        if (el) frappe.nordigen.accounts.toggle_action(el, true);
    },
    disable_actions: function(frm) {
        if (frm._accounts_table)
            frm._accounts_table.find('button.nordigen-action').each(function(i, el) {
                frappe.nordigen.accounts.toggle_action($(el), false);
            });
    },
    enqueue_sync: function(frm, $el, account, from_date, to_date) {
        var $spinner = frappe.nordigen.accounts.create_spinner($el);
        let args = {
            bank: frm.doc.name,
            account: account,
        };
        if (from_date) args.from_date = from_date;
        if (to_date) args.to_date = to_date;
        frappe.nordigen().request(
            'enqueue_bank_account_sync',
            args,
            function(ret) {
                if (!ret) {
                    frappe.nordigen.accounts.remove_spinner($el, $spinner);
                    this._error('Accounts: bank account sync failed');
                    this.error('Unable to sync the bank account "{0}".', [account]);
                    return;
                }
                if (cint(ret) === -1) {
                    frappe.nordigen.accounts.remove_spinner(null, $spinner);
                    frappe.nordigen.accounts.disable_actions(frm);
                    this._error('Accounts: bank account sync failed');
                    this.error('The Nordigen plugin is disabled.');
                    return;
                }
                if (cint(ret) === -2) {
                    frappe.nordigen.accounts.remove_spinner(null, $spinner);
                    this._error('Accounts: bank account sync failed since bank doesn\'t exist');
                    this.error('Unable to find the Nordigen bank "{0}".', [frm.doc.name]);
                    return;
                }
                if (cint(ret) === -3) {
                    frappe.nordigen.accounts.remove_spinner(null, $spinner);
                    this._error('Accounts: bank account sync failed since bank account is not part of the bank');
                    this.error('The Nordigen bank account "{0}" is not part of {1}.', [account, frm.doc.name]);
                    return;
                }
                frappe.nordigen.accounts.remove_spinner($el, $spinner);
                this._log('Accounts: bank account sync success');
                frappe.show_alert({
                    message: __('Bank account "{0}" is syncing in background', [account]),
                    indicator: 'green'
                });
            },
            function(e) {
                frappe.nordigen.accounts.remove_spinner($el, $spinner);
                this._error('Accounts: bank account sync error');
                this.error('Unable to sync the bank account "{0}".', [account]);
            }
        );
    },
    action_handler: function(frm, $el) {
        if ($el.data('nordigen_account_action_clicked')) {
            frappe.nordigen()._log('Accounts: table action ignored');
            return;
        }
        if ($el.attr('disabled') || $el.prop('disabled')) {
            frappe.nordigen()._log('Accounts: table action is disabled');
            return;
        }
        let account = $el.attr('data-nordigen-account');
        if (account == null) {
            frappe.nordigen.accounts.toggle_action($el, false);
            frappe.nordigen()._log('Accounts: unable to get account from table action');
            return;
        }
        var row = null;
        if ((frm.doc.bank_accounts || []).length) {
            for (let i = 0, l = frm.doc.bank_accounts.length; i < l; i++) {
                if (frm.doc.bank_accounts[i].account === account) {
                    frappe.nordigen()._log('Accounts: table action row found');
                    row = frm.doc.bank_accounts[i];
                    break;
                }
            }
        }
        if (!row) frappe.nordigen()._log('Accounts: table action row not found');
        else if (row.status !== 'Ready' && row.status !== 'Enabled')
            frappe.nordigen()._log('Accounts: table account not ready', row);
        if (!row || (row.status !== 'Ready' && row.status !== 'Enabled')) {
            frappe.nordigen.accounts.toggle_action($el, false);
            return;
        }
        $el.data('nordigen_account_action_clicked', true);
        window.setTimeout(function() {
            $el.removeData('nordigen_account_action_clicked');
        }, 3000);
        if (cstr(row.bank_account).length < 1) {
            frappe.nordigen.accounts.build_dialog(frm, $el, row.account);
            return;
        }
        if (cstr(row.last_sync).length) {
            frappe.nordigen()._log('Accounts: syncing bank account');
            frappe.nordigen.accounts.enqueue_sync(frm, $el, row.account);
            return;
        }
        frappe.nordigen()._log('Accounts: prompting bank account sync dates');
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
                frappe.nordigen()._log('Accounts: syncing bank account', values);
                frappe.nordigen.accounts.enqueue_sync(frm, $el, row.account, values.from_date, values.to_date);
            },
            __('Sync Bank Account Transactions'),
            __('Sync')
        );
    },
    build_dialog: function(frm, $el, account) {
        var $spinner = frappe.nordigen.accounts.create_spinner($el),
        dialog = new frappe.ui.Dialog({
            title: __('Add Bank Account'),
            indicator: 'green',
        }),
        $cont = $('<div class="container-fluid p-0">'
            + '<div class="row border-bottom">'
                + '<div class="col-12 text-center my-4">'
                    + '<button type="button" class="btn btn-primary btn-lg nordigen-new-account">'
                        + '<i class="fa fa-plus fa-fw"></i> '
                        + __('Create New Account')
                    + '</button>'
                + '</div>'
            + '</div>'
            + '<div class="row">'
                + '<div class="col-12 text-center my-2">'
                    + '<h4>'
                        + __('Link To Existing Account')
                    + '</h4>'
                + '</div>'
                + '<div class="col-12 text-center nordigen-accounts-loading">'
                    + '<div class="spinner-border m-2" role="status">'
                        + '<span class="sr-only">' + __('Loading') + '...</span>'
                    + '</div>'
                    + '<div class="text-center">'
                        + __('Loading Bank Accounts')
                    + '</div>'
                + '</div>'
                + '<div class="col-12 nordigen-accounts-container">'
                    + '<div class="table-responsive">'
                        + '<table class="table table-bordered table-hover nordigen-table nordigen-accounts-table">'
                            + '<thead class="thead-dark">'
                                + '<tr>'
                                    + '<th scope="col">'
                                        + __('Name')
                                    + '</th>'
                                    + '<th>'
                                        + __('Action')
                                    + '</th>'
                                + '</tr>'
                            + '</thead>'
                            + '<tbody>'
                            + '</tbody>'
                        + '</table>'
                    + '</div>'
                + '</div>'
            + '</div>'
        + '</div>').appendTo(dialog.modal_body),
        $add_new = dialog.modal_body.find('button.nordigen-new-account').first(),
        $loading = dialog.modal_body.find('.nordigen-accounts-loading').first(),
        $cont = dialog.modal_body.find('.nordigen-accounts-container').first(),
        $table = dialog.modal_body.find('table.nordigen-accounts-table').first(),
        $table_body = $table.find('tbody').first(),
        account_row = '<tr>'
            + '<td scope="row">'
                + '<strong>{account_name}</strong>'
            + '</td>'
            + '<td>{account_link}</td>'
        + '</tr>',
        account_empty_row = '<tr>'
            + '<td scope="row" colspan="2" class="text-center text-muted">'
                + __('No bank account was found.')
            + '</td>'
        + '</tr>';
        $cont.hide();
        $add_new.click(function(e) {
            dialog.hide();
            frappe.call({
                method: 'store_bank_account',
                doc: frm.doc,
                args: {account: account},
                callback: function(res) {
                    if (!res) {
                        hide_spinner(true);
                        frappe.nordigen()._error('Accounts: storing bank account failed');
                        return;
                    }
                    hide_spinner();
                    frappe.nordigen()._log('Accounts: storing bank account success');
                    frappe.show_alert({
                        message: __('The Nordigen bank account "{0}" has been added successfully', [account]),
                        indicator: 'green'
                    });
                    frappe.nordigen.events.clear();
                    frm.reload_doc();
                },
                error: function() {
                    hide_spinner();
                    frappe.nordigen()._error('Accounts: storing bank account error');
                    frappe.nordigen().error('Unable to add the Nordigen bank account "{0}" for the bank "{1}".',
                        [account, frm.doc.name]);
                }
            });
        });
        $table.on('click', 'button.nordigen-link-account', function() {
            dialog.hide();
            var acc_name = cstr($(this).attr('data-bank-account'));
            if (!acc_name.length) {
                hide_spinner(true);
                frappe.nordigen()._log('Accounts: unable to get the bank account name');
                return;
            }
            frappe.call({
                method: 'update_bank_account',
                doc: frm.doc,
                args: {
                    account: account,
                    bank_account: acc_name,
                },
                callback: function(res) {
                    if (!res) {
                        hide_spinner(true);
                        frappe.nordigen()._error('Accounts: linking bank account failed');
                        return;
                    }
                    hide_spinner();
                    frappe.nordigen()._log('Accounts: linking bank account success');
                    frappe.show_alert({
                        message: __('The bank account "{0}" has been linked successfully', [acc_name]),
                        indicator: 'green'
                    });
                    frappe.nordigen.events.clear();
                    frm.reload_doc();
                },
                error: function() {
                    hide_spinner();
                    frappe.nordigen()._error('Accounts: linking bank account error');
                    frappe.nordigen().error('Unable to link the bank account "{0}".', [acc_name]);
                }
            });
        });
        dialog.set_secondary_action_label(__('Cancel'));
        dialog.set_secondary_action(function() {
            dialog.hide();
            hide_spinner();
        });
        dialog.$wrapper.on('hidden.bs.modal', function() {
            hide_spinner();
        });
        function hide_spinner(disable) {
            if ($spinner) frappe.nordigen.accounts.remove_spinner(!disable ? $el : null, $spinner);
            $spinner = null;
        }
        function list_bank_accounts() {
            if (frm._bank_accounts && frm._bank_accounts.length) {
                if (!frm._linked_bank_accounts) {
                    frm._linked_bank_accounts = [];
                    if ((frm.doc.bank_accounts || []).length) {
                        frm.doc.bank_accounts.forEach(function(row) {
                            if (cstr(row.bank_account).length)
                                frm._linked_bank_accounts.push(cstr(row.bank_account));
                        });
                    }
                }
                frm._bank_accounts.forEach(function(row) {
                    let account_link = '';
                    if (frm._linked_bank_accounts.indexOf(row.name) < 0) {
                        account_link = (
                            '<button type="button" class="btn btn-primary btn-sm nordigen-link-account" data-bank-account="{name}">'
                                + __('Link')
                            + '</button>'
                        ).replace('{name}', row.name);
                    } else {
                        account_link = '<span class="text-success">' + __('Linked') + '</span>';
                    }
                    $table_body.append(
                        account_row
                            .replace('{account_name}', row.account_name)
                            .replace('{account_link}', account_link)
                    );
                });
            } else {
                $table_body.append($(account_empty_row));
            }
            $loading.hide();
            $cont.show();
        }
        if (!frm._bank_accounts) {
            dialog.show();
            frappe.nordigen().request(
                'get_bank_accounts_list',
                null,
                function(res) {
                    if (!res || !Array.isArray(res) || !res.length) res = null;
                    frm._bank_accounts = res;
                    list_bank_accounts();
                },
                function() {
                    this._error('Accounts: bank accounts list error');
                    list_bank_accounts();
                }
            );
        } else {
            list_bank_accounts();
            dialog.show();
        }
    },
};