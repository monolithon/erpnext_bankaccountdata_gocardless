/*
*  ERPNext Gocardless Bank © 2024
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


frappe.ui.form.on('Gocardless Bank', {
    onload: function(frm) {
        frappe.gc()
            .on('ready change', function() { this.setup_form(frm); })
            .on('on_alert', function(d, t) {
                frm._bank.errs.includes(t) && (d.title = __(frm.doctype));
            });
        frm._bank = {
            errs: ['fatal', 'error'],
            is_draft: 1,
            is_submitted: 0,
            is_cancelled: 0,
            inits: {sync: 0},
        };
        frm.events.check_doc(frm);
        if (!frm._bank.is_draft) return;
        frm.set_query('company', function(doc) {
            return {query: frappe.gc().get_method('search_companies')};
        });
        frm.add_fetch('company', 'country', 'country', frm.doctype);
    },
    refresh: function(frm) {
        if (frm.doc.__needs_refresh) return frm.reload_doc();
        !frm._bank.inits.errors && frm.events.setup_errors(frm);
        !frm.is_new() && frm.events.check_status(frm);
        delete frm._bank.inits.reload;
    },
    company: function(frm) {
        let val = cstr(frm.doc.company);
        if (!val.length) frm.set_value('country', '');
    },
    country: function(frm) {
        if (cstr(frm.doc.country).length)
            return frm.events.enqueue_load_banks(frm);
        
        frm.events.enqueue_load_banks(frm, 1);
        frm.events.reset_bank(frm);
        frappe.gc_banks.reset(frm);
    },
    bank: function(frm) {
        let val = cstr(frm.doc.bank);
        if (!val.length) return frm.events.reset_bank(frm);
        let obj = frappe.gc_banks.get(val);
        if (obj) return frm.events.reset_bank(frm, obj);
        frm.events.reset_bank(frm);
        frappe.gc().error(__('"{0}" isn\'t supported by Gocardless.', [val]));
    },
    validate: function(frm) {
        if (!frm._bank.is_draft) return;
        let errs = [];
        if (!frappe.gc().$isStrVal(frm.doc.company))
            errs.push(__('A valid company is required.'));
        else if (!frappe.gc().$isStrVal(frm.doc.country))
            errs.push(__('Company "{0}" doesn\'t have a valid country.', [frm.doc.company]));
        if (!frappe.gc().$isStrVal(frm.doc.bank))
            errs.push(__('A valid bank is required.'));
        else if (!frappe.gc_banks.key)
            errs.push(__('Unable to validate support for "{0}" with Gocardless.', [frm.doc.bank]));
        else {
            let obj = frappe.gc_banks.get(frm.doc.bank);
            if (!obj) errs.push(__('"{0}" isn\'t supported by Gocardless.', [frm.doc.bank]));
            else if (!frappe.gc().$isStrVal(obj.id))
                errs.push(__('Unable to get Gocardless Bank ID for "{0}".', [frm.doc.bank]));
            else frm.events.reset_bank(frm, obj);
        }
        if (!errs.length) return;
        frappe.gc().fatal(errs);
        return false;
    },
    before_submit: function(frm) {
        delete frm._bank.inits.doc;
    },
    check_doc: function(frm) {
        frm._bank.inits.doc = 1;
        let docstatus = cint(frm.doc.docstatus);
        frm._bank.is_draft = docstatus === 0;
        frm._bank.is_submitted = docstatus === 1;
        frm._bank.is_cancelled = docstatus === 2;
    },
    check_status: function(frm) {
        !frm._bank.inits.doc && frm.events.check_doc(frm);
        frappe.gc()._log('Form doc status', {
            draft: frm._bank.is_draft,
            submitted: frm._bank.is_submitted,
            cancelled: frm._bank.is_cancelled
        });
        if (frm._bank.is_cancelled) return;
        let setup = !frm._bank.inits.setup;
        setup && frm.events.load_banks(frm, 1);
        if (!frm._bank.is_submitted) return;
        frm._bank.inits.auth = frappe.gc().$isStrVal(frm.doc.auth_id)
            && frappe.gc().$isStrVal(frm.doc.auth_expiry)
            && cstr(frm.doc.auth_status) !== 'Unlinked' ? 1 : 0;
        frappe.gc()._log('Form auth status', frm._bank.inits.auth);
        if (!frm._bank.inits.auth) {
            frm._bank.inits.sync && frm.events.setup_sync_data(frm, 1);
            !frm._bank.inits.bar && frm.events.setup_toolbar(frm);
            !frm._bank.inits.link && frm.events.check_link(frm);
        } else {
            if (!frm._bank.inits.reload_accounts) {
                frm._bank.inits.reload_accounts = 1;
                frappe.gc_accounts.wait();
                frappe.gc().real('reload_bank_accounts', function(ret) {
                    if (
                        !this.$isDataObj(ret) || (
                            (!this.$isStrVal(ret.name) || ret.name !== cstr(frm.docname))
                            && (!this.$isStrVal(ret.bank) || ret.bank !== cstr(frm.doc.bank))
                        )
                    ) return this._error('Accounts: invalid bank accounts reloading data received', ret);
                    frappe.gc_accounts.reset();
                    frm._bank.inits.reload = 1;
                    frm.reload_doc();
                });
            }
            frm._bank.inits.bar && frm.events.setup_toolbar(frm, 1);
            !frm._bank.inits.sync && frm.events.setup_sync_data(frm);
            (frm._bank.inits.reload || setup) && frm.events.load_accounts(frm);
        }
    },
    check_link: function(frm) {
        let ret = frappe.gc().check_auth();
        if (ret.not_ready) return frappe.gc().$timeout(function() {
            frm.events.check_link(frm);
        }, 300);
        if (ret.disabled) return;
        frm._bank.inits.link = 1;
        if (ret.no_route) return;
        if (ret.invalid_ref)
            return frappe.gc().error(__('Authorization reference ID is invalid.'));
        if (ret.not_found)
            return frappe.gc().error(__('Authorization data is missing.'));
        if (
            ret.invalid_data
            || ret.data.name !== cstr(frm.docname)
            || ret.data.bank !== cstr(frm.doc.bank)
            || ret.data.bank_id !== cstr(frm.doc.bank_id)
        ) {
            frappe.gc()._error('Invalid authorization data.', ret.data);
            return frappe.gc().error(__('Authorization data is invalid.'));
        }
        frm._bank.inits.bar && frm.events.setup_toolbar(frm, 1);
        ret = ret.data;
        frappe.gc().save_auth(
            {
                name: ret.name,
                bank: ret.bank,
                bank_id: ret.bank_id,
                auth_id: ret.auth_id,
                auth_expiry: ret.auth_expiry,
            },
            function(ret) {
                if (!ret) this.error(__('Unable to store bank authorization.'));
                else this.success_(__('Bank has been authorized successfully.'));
                frm._bank.inits.reload = 1;
                frm.reload_doc();
            },
            function(e) {
                this._error('Failed to store bank authorization.', ret, e.message);
                this.error(e.self ? e.message : __('Failed to store bank authorization.'));
                frm._bank.inits.reload = 1;
                frm.reload_doc();
            }
        );
    },
    setup_errors: function(frm) {
        frm._bank.inits.errors = 1;
        frappe.gc().real('bank_error', function(ret) {
            if (
                !this.$isDataObj(ret) || !this.$isStrVal(ret.error)
                || (
                    ret.any == null
                    && (!this.$isStrVal(ret.name) || ret.name !== cstr(frm.docname))
                    && (!this.$isStrVal(ret.bank) || ret.bank !== cstr(frm.doc.bank))
                )
            ) return this._error('Invalid error data received', ret);
            this.error(ret.error);
            frm._bank.is_submitted && frm._bank.inits.auth && frappe.gc_accounts.reset();
            frm._bank.inits.reload = 1;
            frm.reload_doc();
        });
    },
    enqueue_load_banks: function(frm, clear) {
        if (frm._bank.load_banks_tm) frappe.gc().$timeout(frm._bank.load_banks_tm);
        if (clear) delete frm._bank.load_banks_tm;
        if (!clear) frm._bank.load_banks_tm = frappe.gc().$timeout(function() {
            delete frm._bank.load_banks_tm;
            frm.events.load_banks(frm);
        }, 800);
    },
    load_banks: function(frm, init) {
        if (init) frm._bank.inits.setup = 1;
        var key = cstr(frm.doc.country);
        if (frappe.gc_banks.key === key) return;
        !frappe.gc_banks.field && frappe.gc_banks.setup(frm);
        let data = frappe.gc_banks.load(key);
        if (data) return frappe.gc_banks.update(key, data);
        if (!frm._bank.is_draft) return frappe.gc_banks.reset(frm);
        frappe.gc().request(
            'get_banks',
            {
                company: cstr(frm.doc.company),
                country: key
            },
            function(ret) {
                if (!this.$isArr(ret)) {
                    if (init) return frappe.gc_banks.reset(frm);
                    this._error('Invalid banks list.', key, ret);
                    return this.error(__('Gocardless banks list received is invalid.'));
                }
                if (!ret.length) {
                    if (init) return frappe.gc_banks.reset(frm);
                    this._error('Empty banks list.', ret);
                    return this.error(__('Gocardless banks list received is empty.'));
                }
                frappe.gc_banks.store(key, ret);
                frappe.gc_banks.update(key, ret);
            },
            function(e) {
                if (init) return frappe.gc_banks.reset(frm);
                this._error('Failed to get banks list.', key, e.message);
                this.error(e.self ? e.message : __('Failed to get banks list from Gocardless.'));
            }
        );
    },
    reset_bank: function(frm, obj) {
        if (!obj || frm.doc.bank_id !== obj.id)
            frm.set_value('bank_id', obj ? obj.id : '');
        let tdays = obj ? cint(obj.transaction_total_days) : 0;
        if (tdays < 1) tdays = cint(frappe.gc().transaction_days);
        if (cint(frm.doc.transaction_days) !== tdays)
            frm.set_value('transaction_days', tdays);
    },
    setup_toolbar: function(frm, clear) {
        let label = __('Authorize');
        if (frm.custom_buttons[label]) {
            if (!clear) return;
            frappe.gc()._log('Remove auth button');
            frm.custom_buttons[label].remove();
            delete frm.custom_buttons[label];
            delete frm._bank.inits.bar;
        }
        if (clear || frm._bank.inits.bar) return;
        frappe.gc()._log('Setup auth button');
        frm._bank.inits.bar = 1;
        frm.add_custom_button(label, function() {
            var name = cstr(frm.docname),
            company = cstr(frm.doc.company),
            bank = cstr(frm.doc.bank),
            bank_id = cstr(frm.doc.bank_id),
            transaction_days = cint(frm.doc.transaction_days);
            
            frappe.gc().get_auth(
                name, company, bank_id, transaction_days,
                function(ref_id, auth_id, auth_expiry, auth_link) {
                    auth_expiry = moment().add(cint(auth_expiry), 'days').format(frappe.defaultDateFormat);
                    this.cache().set('gocardless_' + ref_id, {
                        name: name,
                        bank: bank,
                        bank_id: bank_id,
                        auth_id: auth_id,
                        auth_expiry: auth_expiry
                    });
                    this.info_(__('Redirecting to "{0}" authorization page.', [bank]));
                    this.$timeout(function() { window.location.href = auth_link; }, 2000);
                },
                function(e) {
                    this._error('Failed to connect to bank.', company, bank, bank_id, transaction_days, e.message);
                    this.error(e.self ? e.message : __('Failed to connect to {0}.', [bank]))
                }
            );
        });
        frm.change_custom_button_type(label, null, 'success');
    },
    setup_sync_data: function(frm, clear) {
        let val = !clear ? 1 : 0;
        if (val && !frm._bank.inits.sync_note) {
            frm._bank.inits.sync_note = 1;
            frm.get_field('sync_html').html(
                '<p class="text-danger">'
                    + __('For security reasons, transactions sync for each bank account, both auto and manual, are limited to a total of 4 times per day.')
                + '</p>'
            );
        }
        if (frm._bank.inits.sync === val) return;
        frm._bank.inits.sync = val;
        frm.toggle_display('auto_sync', val);
        frm.toggle_display('sync_html', val);
    },
    load_accounts: function(frm) {
        if (frappe.gc_accounts.ready) return frappe.gc_accounts.check();
        frappe.gc_accounts.init(frm);
        if (!frappe.gc_accounts.ready)
            frappe.gc()._error('Unable to get the accounts html field.');
    },
});


frappe.gc_banks = {
    time: 2 * 24 * 60 * 60,
    key: null,
    field: null,
    data: null,
    load: function(key) {
        if (!key) return;
        let data = frappe.gc().cache().get('banks_list_' + key);
        if (data) this.store(key, data);
        return data;
    },
    store: function(key, data) {
        frappe.gc().cache().set('banks_list_' + key, data, this.time);
    },
    update: function(key, data) {
        if (!this.field) return;
        this.key = key;
        this.data = data;
        this.field.set_data(frappe.gc().$map(this.data, function(v, i) {
            return {value: v.name, label: __(v.name)};
        }));
        this.field.translate_values = false;
    },
    reset: function(frm) {
        if (!this.field) this._get_field(frm);
        if (!this.field) return;
        this.key = null;
        this.data = null;
        let val = !frm.is_new() ? cstr(frm.doc.bank) : '';
        this.field.set_data(val.length ? [{label: __(val), value: val}] : []);
    },
    get: function(name) {
        if (!this.data) return null;
        for (let i = 0, l = this.data.length; i < l; i++) {
            if (this.data[i].name === name) return this.data[i];
        }
    },
    setup: function(frm) {
        if (this.field || !frm._bank.is_draft) return;
        if (!this.field) this._get_field(frm);
        if (!this.field) return;
        let awesomplete = this.field.awesomplete;
        if (!awesomplete || !frappe.gc().$isFunc(awesomplete.item))
            return frappe.gc()._error('Unable to get bank field awesomplete.');
        awesomplete.__item = awesomplete.item;
        awesomplete.item = function(item) {
            if (cur_frm && cur_frm.doctype === 'Gocardless Bank' && frappe.gc_banks)
                return frappe.gc_banks.build_item(item, this.get_item(item.value));
            if (this.__item) {
                this.item = this.__item;
                delete this.__item;
                return this.item(item);
            }
            window.location.reload(true);
        };
    },
    build_item: function(item, data) {
        if (!data) data = item;
        if (!data.label) data.label = data.value;
        let obj = this.get(data.value),
        html = '<strong>' + data.label + '</strong>',
        img = '<img id="{0}" src="{1}" alt="{2}" style="width:18px;height:18px;border:1px solid #6c757d;border-radius:50%;"/> ',
        label = data.label,
        def_logo = 'https://placehold.co/100x100/4b535a/fff/png?text=' + label[0],
        logo = def_logo;
        if (obj && frappe.gc().$isStrVal(obj.id)) {
            label = obj.name;
            logo = obj.logo;
        }
        let iobj = frappe.gc().image().add(logo, {fall: def_logo, width: 18, height: 18, cache: this.time});
        html = img.replace('{0}', iobj.id).replace('{1}', iobj.src).replace('{2}', __(label)) + html;
        if (data.description) html += '<br><span class="small">' + __(data.description) + '</span>';
        return $('<li></li>')
            .data('item.autocomplete', data)
            .prop('aria-selected', 'false')
            .html('<a><p>' + html + '</p></a>')
            .get(0);
    },
    destroy: function() {
        for (let k in this) {
            if (frappe.gc().$hasProp(k, this)) delete this[k];
        }
    },
    _get_field: function(frm) {
        let field = frm.get_field('bank');
        if (field) this.field = field;
        else frappe.gc()._error('Unable to get bank field.');
    }
};


frappe.gc_accounts = {
    _wait_time: 1 * 60 * 1000,
    init(frm) {
        let field = frm.get_field('bank_accounts_html');
        if (!field || !field.$wrapper) return;
        this.ready = 1;
        this._frm = frm;
        this._field = field;
        this._enabled = frappe.gc().is_enabled;
        this._destroy = frappe.gc().$fn(this.destroy, this);
        this._refresh = frappe.gc().$fn(this._refresh_btns, this);
        frappe.gc().once('page_change', this._destroy);
        frappe.gc().on('change', this._refresh);
        this.check();
        return 1;
    },
    wait() {
        if (!this._wait_tm) this._wait_tm = frappe.gc().$timeout(function() {
            this.reset();
            this._frm._bank.inits.reload = 1;
            this._frm.reload_doc();
        }, this._wait_time, null, this);
    },
    check() {
        if (this.ready) this._wait_tm ? this._loading() : this._render();
    },
    reset() {
        this._wait_tm && frappe.gc().$timeout(this._wait_tm);
        this._wait_tm = this._linked = null;
    },
    destroy() {
        this._refresh && frappe.gc().off('change', this._refresh);
        if (this._$table) {
            this._$table.off('click', 'button.gc-balance', this._on_balance);
            this._$table.off('click', 'button.gc-action', this._on_action);
            this._$table.off('click', 'button.gc-link', this._on_link);
        }
        if (this._balance_dialog) {
            try { this._balance_dialog.hide(); } catch(_) {}
            try { this._balance_dialog.modal('dispose'); } catch(_) {}
            try { this._balance_dialog.wrapper.remove(); } catch(_) {}
        }
        if (this._dialog) {
            try { this._dialog.hide(); } catch(_) {}
            try {
                this._dialog.modal_body.off('click', 'button.gc-new-account', this._dialog.gc.on_new_click);
                this._dialog.modal_body.off('click', 'button.gc-link-account', this._dialog.gc.on_link_click);
            } catch(_) {}
            try { this._dialog.modal('dispose'); } catch(_) {}
            try { this._dialog.wrapper.remove(); } catch(_) {}
        }
        if (this._field) try { this._field.$wrapper.empty(); } catch(_) {}
        this.reset();
        for (let k in this) {
            if (frappe.gc().$hasProp(k, this)) delete this[k];
        }
    },
    _loading() {
        if (!this._$loading) this._$loading = $('\
<div class="mb-4 mx-md-2 mx-1 text-center">\
    <div class="spinner-border m-2" role="status">\
        <span class="sr-only">' + __('Loading') + '...</span>\
    </div>\
    <div class="text-center">\
        ' + __('Syncing Bank Accounts') + '\
    </div>\
</div>\
        ').appendTo(this._field.$wrapper);
        this._switch('loading');
    },
    _render() {
        frappe.gc()._log('Accounts: rendering bank account table');
        if (!this._$table) this._build();
        else this._$body.empty();
        if (!frappe.gc().$isArr(this._frm.doc.bank_accounts)) this._length = 0;
        else this._length = this._frm.doc.bank_accounts.length;
        if (!this._length) {
            this._$body.append('\
<tr>\
    <td scope="row" colspan="4" class="text-center text-muted">\
        ' + __('No bank account was received.') + '\
    </td>\
</tr>\
            ');
        } else {
            for (let i = 0, r, h; i < this._length; i++) {
                r = this._frm.doc.bank_accounts[i];
                this._$body.append('\
<tr data-gc-account="' + r.account + '">\
    ' + [
        this._render_account(r),
        this._render_balance(r),
        this._render_status(r),
        this._render_action(r)
    ].join('\n') + '\
</tr>\
                ');
            }
            this._refresh_btns();
        }
        this._switch('table');
    },
    _switch(key) {
        let k = '_$' + key;
        if (!this[k] || this._view === key) return;
        let p = '_$' + this._view;
        this[p] && this[p].hide();
        this[k].show();
        this._view = key;
    },
    _build() {
        if (!frappe.gc().$hasElem('gocardless_css'))
            frappe.gc().$loadCss(
                '/assets/erpnext_gocardless_bank/css/gocardless.bundle.css',
                {id: 'gocardless_css'}
            );
        let $wrapper = $('<div class="table-responsive mb-4 mx-md-2 mx-1"></div>')
            .append('\
<table class="table table-bordered table-hover gc-table">\
    <thead class="thead-dark">\
        <tr>\
            <th scope="col">' + __('Account') + '</th>\
            <th>' + __('Balance') + '</th>\
            <th>' + __('Status') + '</th>\
            <th>' + __('Actions') + '</th>\
        </tr>\
    </thead>\
    <tbody>\
    </tbody>\
</table>\
            ')
            .appendTo(this._field.$wrapper);
        this._$table = $wrapper.find('.gc-table').first();
        this._$body = this._$table.find('tbody').first();
        this._on_balance = frappe.gc().$fn(this._on_balance, this);
        this._on_action = frappe.gc().$fn(this._on_action, this);
        this._on_link = frappe.gc().$fn(this._on_link, this);
        this._$table.on('click', 'button.gc-balance', this._on_balance);
        this._$table.on('click', 'button.gc-action', this._on_action);
        this._$table.on('click', 'button.gc-link', this._on_link);
    },
    _refresh_btns() {
        if (frappe.gc().is_enabled === this._enabled) return;
        this._enabled = !!frappe.gc().is_enabled;
        this._toggle_btns('action', this._enabled);
        this._toggle_btns('link', this._enabled);
    },
    _render_account(row) {
        let html = '<strong>' + row.account + '</strong>';
        html += '<br/><small class="text-muted">' + __('ID') + ': ' + row.account_id + '</small>';
        if (frappe.gc().$isStrVal(row.last_sync)) {
            html += '<br/><small class="text-muted">' + __('Last Update') + ': '
                + moment(row.last_sync, frappe.defaultDateFormat).fromNow() + '</small>';
        }
        return '<td scope="row">' + html + '</td>';
    },
    _render_balance(row) {
        let data = {};
        if (row.balances) {
            let list = frappe.gc().$parseJson(row.balances);
            if (frappe.gc().$isArrVal(list))
                for (let i = 0, l = list.length, v; i < l; i++) {
                    v = list[i];
                    if (cint(v.reqd)) data[v.type] = format_currency(v.amount, v.currency);
                }
        }
        return '\
        <td class="text-center">\
            ' + Object.values(frappe.gc().$map({
                opening: this._balance_labels.opening,
                closing: this._balance_labels.closing,
            }, function(v, k) {
                return '<small>' + v + ': ' + (data[k] != null ? data[k] : 'N/A') + '</small>';
            })).join('<br />') + '\
        </td>\
        ';
    },
    _render_status(row) {
        let color = 'text-muted';
        if (row.status === 'Ready' || row.status === 'Enabled') color = 'text-success';
        else if (row.status === 'Expired' || row.status === 'Error' || row.status === 'Deleted') color = 'text-danger';
        else if (row.status === 'Processing') color = 'text-info';
        else if (row.status === 'Suspended' || row.status === 'Blocked') color = 'text-warning';
        return '<td><span class="' + color + '">' + __(row.status) + '</span></td>';
    },
    _render_action(row) {
        let html = '<button type="button" class="btn btn-{color} {action}"{attr}>{label}</button>',
        actions = [],
        exists = frappe.gc().$isStrVal(row.bank_account_ref),
        disabled = row.status !== 'Ready' && row.status !== 'Enabled';
        actions.push(html
            .replace('{action}', 'gc-balance')
            .replace('{color}', 'info')
            .replace('{attr}', '')
            .replace('{label}', __('Balance'))
        );
        exists && actions.push(html
            .replace('{action}', 'gc-link')
            .replace('{color}', 'default')
            .replace('{attr}', '')
            .replace('{label}', __('Edit'))
        );
        actions.push(html
            .replace('{action}', 'gc-action')
            .replace('{color}', exists ? 'warning' : 'success')
            .replace('{attr}', disabled ? ' disabled' : '')
            .replace('{label}', exists ? __('Sync') : __('Add'))
        );
        return '<td><div class="btn-group btn-group-sm">' + actions.join('') + '</div></td>';
    },
    _on_balance(e) {
        if (!this._balance_dialog) {
            this._balance_dialog = new frappe.ui.Dialog({
                title: __('Bank Account Balance'),
                indicator: 'blue',
            });
            this._balance_dialog.modal_body.append('\
<div class="table-responsive m-0 p-0">\
    <table class="table table-sm table-borderless gc-table">\
        <tbody>\
        </tbody>\
    </table>\
</div>\
            ');
            this._balance_dialog.$wrapper.on('hidden.bs.modal', frappe.gc().$fn(function() {
                this._balance_dialog.modal_body.find('tbody').first().empty();
            }, this));
            this._balance_dialog.get_primary_btn().addClass('hide');
            this._balance_dialog.set_secondary_action_label(__('Close'));
            this._balance_dialog.set_secondary_action(frappe.gc().$fn(function() {
                this._balance_dialog.hide();
            }, this));
        }
        let $el = $(e.target),
        account = $el.parents('tr').attr('data-gc-account');
        var data = {};
        if (frappe.gc().$isStrVal(account)) {
            let row = this._get_bank_account(account);
            if (row && row.balances) {
                let list = frappe.gc().$parseJson(row.balances);
                if (frappe.gc().$isArrVal(list))
                    for (let i = 0, l = list.length, v; i < l; i++) {
                        v = list[i];
                        data[v.type] = format_currency(v.amount, v.currency);
                    }
            }
        }
        this._balance_dialog.modal_body.find('tbody').first().append('\
            ' + Object.values(frappe.gc().$map(this._balance_labels, function(v, k) {
                    return '\
            <tr>\
                <td scope="row">' + v + '</td>\
                <td class="text-center">' + (data[k] != null ? data[k] : 'N/A') + '</td>\
            </tr>\
                    ';
            })).join('\n') + '\
        ');
        this._balance_dialog.show();
    },
    _on_action(e) {
        if (this._action_clicked) return;
        frappe.gc()._log('Accounts: table add action button clicked');
        this._action_clicked++;
        frappe.gc().$timeout(function() {
            this._action_clicked--;
        }, 1000, null, this);
        let $el = $(e.target);
        if ($el.data('gc_account_action_clicked')) {
            frappe.gc()._log('Accounts: table action ignored');
            return;
        }
        if ($el.attr('disabled') || $el.prop('disabled')) {
            frappe.gc()._log('Accounts: table action is disabled');
            return;
        }
        let account = $el.parents('tr').attr('data-gc-account');
        if (!frappe.gc().$isStrVal(account)) {
            this._toggle_btn($el, false);
            frappe.gc()._log('Accounts: unable to get account from table action');
            return;
        }
        let row = this._get_bank_account(account);
        if (!row) frappe.gc()._log('Accounts: table action row not found');
        else if (row.status !== 'Ready' && row.status !== 'Enabled')
            frappe.gc()._log('Accounts: table account not ready', row);
        if (!row || (row.status !== 'Ready' && row.status !== 'Enabled')) {
            this._toggle_btn($el, false);
            return;
        }
        $el.data('gc_account_action_clicked', true);
        frappe.gc().$timeout(function($el) {
            $el.removeData('gc_account_action_clicked');
        }, 3000, [$el]);
        if (!frappe.gc().$isStrVal(row.bank_account_ref)) {
            this._show_dialog($el, row.account);
            return;
        }
        if (frappe.gc().$isStrVal(row.last_sync)) {
            frappe.gc()._log('Accounts: syncing bank account');
            this._enqueue_sync($el, row.account);
            return;
        }
        this._show_prompt($el, row.account);
    },
    _on_link(e) {
        let $el = $(e.target),
        account = $el.parents('tr').attr('data-gc-account');
        if (!frappe.gc().$isStrVal(account)) {
            frappe.gc()._log('Accounts Link: unable to get account from table action');
            return;
        }
        let row = this._get_bank_account(account);
        if (!row) frappe.gc()._log('Accounts Link: table action row not found');
        else if (row.status !== 'Ready' && row.status !== 'Enabled')
            frappe.gc()._log('Accounts Link: table account not ready', row);
        if (!row || (row.status !== 'Ready' && row.status !== 'Enabled')) {
            this._toggle_btn($el, false);
            return;
        }
        frappe.set_route('Form', 'Bank Account', row.bank_account_ref);
    },
    _show_prompt($el, account) {
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
            frappe.gc().$fn(function(vals) {
                frappe.gc()._log('Accounts: syncing bank account', vals);
                this._enqueue_sync($el, account, vals.from_dt, vals.to_dt);
            }, this),
            __('Sync Bank Account Transactions'),
            __('Sync')
        );
    },
    _get_bank_account(account) {
        if (frappe.gc().$isArrVal(this._frm.doc.bank_accounts))
            for (let i = 0, l = this._frm.doc.bank_accounts.length; i < l; i++) {
                if (this._frm.doc.bank_accounts[i].account === account) {
                    frappe.gc()._log('Accounts Link: table action row found');
                    return this._frm.doc.bank_accounts[i];
                }
            }
    },
    _balance_labels: {
        closing: __('Closing'),
        closing_booked: __('Closing Booked'),
        day_balance: __('Day End Balance'),
        forward: __('Forward Balance'),
        info_balance: __('Info. Balance'),
        temp_balance: __('Temp. Balance'),
        temp_booked: __('Temp. Booked'),
        uninvoiced: __('Non-Invoiced'),
        opening: __('Opening'),
        opening_booked: __('Opening Booked'),
        prev_closing_booked: __('Prev Closing Booked'),
    },
    _create_spinner(el) {
        let spinner = $('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>');
        this._toggle_btn(el, false);
        el.prepend(spinner);
        return spinner;
    },
    _remove_spinner(el, spinner) {
        spinner && spinner.remove();
        el && this._toggle_btn(el, true);
    },
    _toggle_btns(type, state) {
        this._$table && this._$table.find('button.gc-' + type)
            .each(frappe.gc().$fn(function(i, el) {
                this._toggle_btn($(el), state);
            }, this));
    },
    _toggle_btn(el, state) {
        el.attr('disabled', state === false)
            .prop('disabled', state === false);
    },
    _enqueue_sync($el, account, from_dt, to_dt) {
        var me = this,
        $spinner = this._create_spinner($el);
        let args = {
            bank: cstr(this._frm.docname),
            account: account,
        };
        if (from_dt) {
            args.from_dt = from_dt;
            if (to_dt) args.to_dt = to_dt;
        }
        frappe.gc().request(
            'enqueue_bank_transactions_sync',
            args,
            function(ret) {
                if (!this.$isDataObj(ret)) {
                    me._remove_spinner($el, $spinner);
                    this._error('Accounts: bank account sync failed');
                    return this.error_(__('Unable to sync the bank account "{0}".', [account]));
                }
                me._remove_spinner($el, $spinner);
                this._log('Accounts: bank account sync success');
                this.success_(__('Bank account "{0}" is syncing in background', [account]));
            },
            function(e) {
                if (!e.self) me._remove_spinner($el, $spinner);
                else {
                    me._remove_spinner(null, $spinner);
                    if (!e.disabled) me._toggle_btn($el, false);
                    else me._toggle_btns('action', false);
                }
                this._error('Accounts: bank account sync error');
                this.error_(e.self ? e.message : __('Unable to sync the bank account "{0}".', [account]));
            }
        );
    },
    _show_dialog($el, account) {
        if (!this._dialog) {
            this._dialog = new frappe.ui.Dialog({
                title: __('Add Bank Account'),
                indicator: 'green',
            });
            this._dialog.modal_body.append('\
<div class="container-fluid p-0">\
    <div class="row border-bottom">\
        <div class="col-12 text-center my-4">\
            <button type="button" class="btn btn-primary btn-lg gc-new-account">\
                <i class="fa fa-plus fa-fw"></i> ' + __('Create New Account') + '\
            </button>\
        </div>\
    </div>\
    <div class="row">\
        <div class="col-12 text-center my-2">\
            <h4> ' + __('Link To Existing Account') + '</h4>\
        </div>\
        <div class="col-12 text-center gc-accounts-loading">\
            <div class="spinner-border m-2" role="status">\
                <span class="sr-only">' + __('Loading') + '...</span>\
            </div>\
            <div class="text-center">\
                ' + __('Loading Bank Accounts') + '\
            </div>\
        </div>\
        <div class="col-12 gc-accounts-container">\
            <div class="table-responsive">\
                <table class="table table-bordered table-hover gc-table gc-accounts-table">\
                    <thead class="thead-dark">\
                        <tr>\
                            <th scope="col">' + __('Name') + '</th>\
                            <th>' + __('Action') + '</th>\
                        </tr>\
                    </thead>\
                    <tbody>\
                    </tbody>\
                </table>\
            </div>\
        </div>\
    </div>\
</div>\
            ');
            this._dialog.gc = {
                $loading: this._dialog.modal_body.find('.gc-accounts-loading').first(),
                $cont: this._dialog.modal_body.find('.gc-accounts-container').first(),
                $table: this._dialog.modal_body.find('table.gc-accounts-table').first(),
                $body: this._dialog.modal_body.find('tbody').first(),
                tpl: {
                    def: '\
<tr>\
    <td scope="row">{account_name}</td>\
    <td>{account_link}</td>\
</tr>\
                    ',
                    empty: '\
<tr>\
    <td scope="row" colspan="2" class="text-center text-muted">\
        ' + __('No bank account was found.') + '\
    </td>\
</tr>\
                    ',
                },
                $el: null,
                $spinner: null,
                account: null,
                hide_spinner: frappe.gc().$fn(function(disable) {
                    this._dialog.gc.$spinner && this._remove_spinner(
                        !disable ? this._dialog.gc.$el : null,
                        this._dialog.gc.$spinner
                    );
                    this._dialog.gc.$spinner = null;
                }, this),
                list_bank_accounts: frappe.gc().$fn(function() {
                    if (frappe.gc().$isArrVal(this._accounts)) {
                        if (!this._linked) {
                            if (!frappe.gc().$isArrVal(this._frm.doc.bank_accounts)) this._linked = [];
                            else this._linked = frappe.gc().$filter(frappe.gc().$map(
                                this._frm.doc.bank_accounts, function(v) {
                                    return this.$isStrVal(v.bank_account_ref) ? v.bank_account_ref : null;
                            }));
                        }
                        for (let i = 0, l = this._accounts.length, r, a; i < l; i++) {
                            r = this._accounts[i];
                            if (this._linked.includes(r.name)) a = '<span class="text-success">' + __('Linked') + '</span>';
                            else a = '<button type="button" class="btn btn-primary btn-sm gc-link-account" data-bank-account="{name}">' + __('Link') + '</button>';
                            this._dialog.gc.$body.append(
                                this._dialog.gc.tpl.def
                                    .replace('{account_name}', r.account_name)
                                    .replace('{account_link}', a.replace('{name}', r.name))
                            );
                        }
                    } else {
                        this._dialog.gc.$body.append(this._dialog.gc.tpl.empty);
                    }
                    this._dialog.gc.$loading.hide();
                    this._dialog.gc.$cont.show();
                }, this),
                on_new_click: frappe.gc().$fn(function(e) {
                    this._dialog.hide();
                    var me = this;
                    frappe.gc().request(
                        'store_bank_account',
                        {
                            name: cstr(this._frm.docname),
                            account: this._dialog.gc.account
                        },
                        function(res) {
                            if (!res) {
                                me._dialog.gc.hide_spinner(true);
                                frappe.gc()._error('Accounts: storing bank account failed');
                                return;
                            }
                            me._dialog.gc.hide_spinner();
                            frappe.gc()._log('Accounts: storing bank account success');
                            frappe.gc().success_(__('The Gocardless bank account "{0}" has been added successfully', [me._dialog.gc.account]));
                            me._frm._bank.inits.reload = 1;
                            me._frm.reload_doc();
                        },
                        function() {
                            me._dialog.gc.hide_spinner();
                            frappe.gc()._error('Accounts: storing bank account error');
                            frappe.gc().error(__('Unable to add the Gocardless bank account "{0}" for the bank "{1}".', [me._dialog.gc.account, cstr(me._frm.docname)]));
                        }
                    );
                }, this),
                on_link_click: frappe.gc().$fn(function(e) {
                    this._dialog.hide();
                    var acc_name = $(e.target).attr('data-bank-account');
                    if (!frappe.gc().$isStrVal(acc_name)) {
                        this._dialog.gc.hide_spinner(true);
                        frappe.gc()._log('Accounts: unable to get the bank account name');
                        return;
                    }
                    var me = this;
                    frappe.gc().request(
                        'change_bank_account',
                        {
                            name: cstr(this._frm.docname),
                            account: this._dialog.gc.account,
                            bank_account: acc_name,
                        },
                        function(res) {
                            if (!res) {
                                me._dialog.gc.hide_spinner(true);
                                this._error('Accounts: linking bank account failed');
                                return;
                            }
                            me._dialog.gc.hide_spinner();
                            this._log('Accounts: linking bank account success');
                            this.success_(__('The bank account "{0}" has been linked successfully', [acc_name]));
                            me._frm._bank.inits.reload = 1;
                            me._frm.reload_doc();
                        },
                        function(e) {
                            me._dialog.gc.hide_spinner();
                            this._error('Accounts: linking bank account error');
                            this.error(__('Unable to link the bank account "{0}".', [acc_name]));
                        }
                    );
                }, this),
            };
            this._dialog.gc.$cont.hide();
            this._dialog.modal_body.on('click', 'button.gc-new-account', this._dialog.gc.on_new_click);
            this._dialog.modal_body.on('click', 'button.gc-link-account', this._dialog.gc.on_link_click);
            this._dialog.set_secondary_action_label(__('Cancel'));
            this._dialog.set_secondary_action(frappe.gc().$fn(function() {
                this._dialog.hide();
                this._dialog.gc.hide_spinner();
            }, this));
            this._dialog.$wrapper.on('hidden.bs.modal', frappe.gc().$fn(function() {
                this._dialog.gc.$cont.hide();
                this._dialog.gc.$loading.show();
                this._dialog.gc.hide_spinner();
                this._dialog.gc.$el = null;
                this._dialog.gc.account = null;
            }, this));
        }
        this._dialog.gc.$el = $el;
        this._dialog.gc.$spinner = this._create_spinner($el);
        this._dialog.gc.account = account;
        if (!this._accounts) {
            this._dialog.show();
            var me = this;
            frappe.gc().request(
                'get_bank_accounts_list',
                null,
                function(res) {
                    if (!this.$isArrVal(res)) res = null;
                    me._accounts = res;
                    me._dialog.gc.list_bank_accounts();
                },
                function() {
                    this._error('Accounts: bank accounts list error');
                    me._dialog.gc.list_bank_accounts();
                }
            );
        } else {
            this._dialog.gc.list_bank_accounts();
            this._dialog.show();
        }
    },
};