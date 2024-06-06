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
            //.on('page_clean', function() { frm && delete frm._bank; })
            .on('on_alert', function(d, t) {
                frm._bank.errs.includes(t) && (d.title = __(frm.doctype));
            });
        frm._bank = {
            errs: ['fatal', 'error'],
            is_draft: 1,
            is_submitted: 0,
            inits: {},
            country: {},
            list: {
                key: null,
                val: null,
                data: {},
                cache: {},
                idx: {},
                time: 2 * 24 * 60 * 60,
            },
        };
        frm.events.check_doc();
        if (!frm._bank.is_draft) return;
        frm._bank.init.setup = 1;
        frm.set_query('company', function(doc) {
            return {query: frappe.gc().get_method('search_companies')};
        });
    },
    refresh: function(frm) {
        if (frm.doc.__needs_refresh) return frm.reload_doc();
        !frm.is_new() && frm.events.check_status(frm);
        !frm._bank.inits.errors && frm.events.setup_errors(frm);
    },
    company: function(frm) {
        if (!frm._bank.is_draft) return;
        var key = 'company',
        val = cstr(frm.doc[key]);
        if (!val.length) return frm.events.load_banks(frm, val);
        if (frm._bank.country[val]) {
            if (frm._bank.country[val] !== cstr(frm.doc.country))
                frm.set_value('country', frm._bank.country[val]);
            return frm.events.load_banks(frm, val);
        }
        frappe.gc().request(
            'get_company_country',
            {company: val},
            function(ret) {
                if (!this.$isStrVal(ret)) return;
                frm._bank.country[val] = ret;
                frm.set_value('country', ret);
                frm.events.load_banks(frm, val);
            }
        );
    },
    bank: function(frm) {
        if (!frm._bank.is_draft) return;
        let key = 'bank',
        val = cstr(frm.doc[key]);
        if (frm._bank.list.val === val) return;
        frm.events.reset_bank(frm);
        if (!val.length) return;
        let idx = frm._bank.list.idx[frm._bank.list.key];
        if (!idx) return;
        idx = idx[val];
        let found = 0;
        if (frappe.gc().$isNum(idx) && idx >= 0) {
            idx = frm._bank.list.cache[frm._bank.list.key][idx];
            if (idx && idx.id) {
                frm._bank.list.val = val;
                frm.set_value('bank_id', idx.id);
                let tdays = cint(idx.transaction_total_days);
                if (tdays < 1) tdays = frappe.gc().transaction_days;
                frm.set_value('transaction_days', tdays);
                found++;
            }
        }
        if (!found) {
            frm.set_value('bank_id', '');
            frm.set_value('transaction_days', frappe.gc().transaction_days);
            frappe.gc().error(__('Selected bank "{0}" is invalid.', [val]));
        }
    },
    validate: function(frm) {
        if (!frm._bank.is_draft) return;
        if (!frappe.gc().$isStrVal(frm.doc.company)) {
            frappe.gc().fatal(__('A valid company is required.'));
            return false;
        }
        if (!frappe.gc().$isStrVal(frm.doc.country)) {
            frappe.gc().fatal(__('Company "{0}" doesn\'t have a valid country.', [frm.doc.company]));
            return false;
        }
        if (!frappe.gc().$isStrVal(frm.doc.bank)) {
            frappe.gc().fatal(__('A valid bank is required.'));
            return false;
        }
        if (!frappe.gc().$isStrVal(frm.doc.bank_id)) {
            frappe.gc().fatal(__('Bank id for selected bank isn\'t found.'));
            return false;
        }
        if (cint(frm.doc.transaction_days) < 1)
            frm.set_value('transaction_days', frappe.gc().transaction_days);
    },
    check_doc: function(frm) {
        let is_new = frm.is_new(),
        docstatus = !is_new ? cint(frm.doc.docstatus) : 0;
        frm._bank.is_draft = is_new || docstatus === 0;
        frm._bank.is_submitted = !is_new && docstatus === 1;
    },
    check_status: function(frm) {
        frm.events.check_doc();
        if (!frm._bank.init.setup) {
            frm._bank.init.setup = 1;
            frm.events.load_banks(frm);
        }
        if (
            !frappe.gc().$isStrVal(frm.doc.auth_id)
            || cstr(frm.doc.auth_status) === 'Unlinked'
        ) {
            frm._bank.is_draft && !frm._bank.inits.link && frm.events.check_link(frm);
            frm._bank.inits.sync && frm.events.setup_sync_data(frm, 1);
            return !frm.is_dirty() && !frm._bank.inits.bar
                && frappe.gc().$isStrVal(frm.doc.bank)
                && frm.events.setup_toolbar(frm);
        }
        if (!frm._bank.init.auth) {
            frm._bank.init.auth++;
            frappe.gc().real(
                'reload_bank_accounts',
                function(ret) {
                    if (
                        !this.$isDataObj(ret) || (
                            (!this.$isStrVal(ret.name) || ret.name !== cstr(frm.docname))
                            && (!this.$isStrVal(ret.bank) || ret.bank !== cstr(frm.doc.bank))
                        )
                    ) return this._error('Accounts: invalid bank accounts reloading data received', ret);
                    frm._bank.is_submitted && frappe.gc_accounts.reset();
                    frm.reload_doc();
                }
            );
            frm.events.remove_toolbar(frm);
            !frm._bank.inits.sync && frm.events.setup_sync_data(frm);
        }
        !frm._bank.is_draft && frm._bank.init.auth && frm.events.load_accounts(frm);
    },
    check_link: function(frm) {
        if (!frappe.gc().is_enabled) return;
        frm._bank.inits.link = 1;
        if (
            !frappe.has_route_options()
            || !frappe.gc().$isStrVal(frappe.route_options.ref)
        ) return;
        
        let key = 'gocardless_' + frappe.route_options.ref;
        delete frappe.route_options.ref;
        if (!frappe.gc().cache().has(key))
            return frappe.gc().error(__('Authorization data for {0} is missing.', [frm.doc.bank]));
        
        var auth = frappe.gc().cache().pop(key);
        if (
            !auth
            || !frappe.gc().$isStrVal(auth.id)
            || !frappe.gc().$isStrVal(auth.expiry)
        ) {
            frappe.gc()._error('Invalid authorization data.', frm.doc.bank, auth);
            return frappe.gc().error(__('The authorization data for {0} is invalid.', [frm.doc.bank]));
        }
        frappe.gc().request(
            'save_bank_link',
            {
                name: cstr(frm.docname),
                auth_id: auth.id,
                auth_expiry: auth.expiry,
            },
            function(ret) {
                if (!ret) return this.error(__('Unable to link {0}.', [frm.doc.bank]));
                this.success_(__('{0} is linked successfully', [frm.doc.bank]));
                //frappe.gc_accounts.wait();
                frm.reload_doc();
            },
            function(e) {
                this._error('Failed to link bank.', frm.doc.bank, auth, e.message);
                this.error(e.self ? e.message : __('Failed to link {0}.', [frm.doc.bank]));
                frm.reload_doc();
            }
        );
    },
    setup_errors: function(frm) {
        frm._bank.inits.errors = 1;
        frappe.gc().real(
            'bank_error',
            function(ret) {
                if (
                    !this.$isDataObj(ret) || !this.$isStrVal(ret.error)
                    || (
                        ret.any == null
                        && (!this.$isStrVal(ret.name) || ret.name !== cstr(frm.docname))
                        && (!this.$isStrVal(ret.bank) || ret.bank !== cstr(frm.doc.bank))
                    )
                ) this._error('Invalid error data received', ret);
                else {
                    this.error(ret.error);
                    frm._bank.is_submitted && frappe.gc_accounts.reset();
                    frm.reload_doc();
                }
            }
        );
    },
    reset_bank: function(frm) {
        frm._bank.list.val = null;
        if (frappe.gc().$isStrVal(frm.doc.auth_id))
            frm.set_value('auth_id', '');
        if (cstr(frm.doc.auth_status) !== 'Unlinked')
            frm.set_value('auth_status', 'Unlinked');
        frm._bank.inits.sync && frm.events.setup_sync_data(frm, 1);
        frm.events.remove_toolbar(frm);
    },
    load_banks: function(frm, country) {
        if (!country) country = cstr(frm.doc.country);
        if (frm._bank.list.key === country) return;
        frm._bank.list.key = null;
        frm._bank.list.val = cstr(frm.doc.bank).length ? cstr(frm.doc.bank) : null;
        frm.events.remove_toolbar(frm);
        if (!country.length) return frappe.gc_banks.reset(frm, 1);
        let data = frm._bank.list.data[country];
        if (data) return frappe.gc_banks.update(frm, country, data, 1);
        frappe.gc_banks.field(frm);
        data = frappe.gc_banks.load(country);
        if (data) {
            frappe.gc_banks.store(frm, country, data);
            return frappe.gc_banks.update(frm, country, data);
        }
        frappe.gc().request(
            'get_banks',
            {
                company: cstr(frm.doc.company),
                country: country,
                cache_only: !frm._bank.is_draft ? 1 : 0
            },
            function(ret) {
                if (!this.$isArr(ret)) {
                    this._error('Invalid banks list.', ret);
                    if (!frm._bank.is_draft) return frappe.gc_banks.reset(frm);
                    return this.error(__('Gocardless banks list received is invalid.'));
                }
                if (!this.is_debug && !ret.length) {
                    this._error('Empty banks list.', ret);
                    if (!frm._bank.is_draft) return frappe.gc_banks.reset(frm);
                    return this.error(__('Gocardless banks list received is empty.'));
                }
                
                this.is_debug && ret.unshift({
                    id: 'SANDBOXFINANCE_SFIN0000',
                    name: 'Testing Sandbox Finance',
                    logo: 'https://cdn.iconscout.com/icon/free/png-512/free-s-characters-character-alphabet-letter-36031.png?w=512',
                });
                
                let country = cstr(frm.doc.country);
                frappe.gc_banks.store(frm, country, ret);
                frappe.gc_banks.update(frm, country, ret);
            },
            function(e) {
                this._error('Failed to get banks list.', country, e.message);
                if (!frm._bank.is_draft) return frappe.gc_banks.reset(frm);
                this.error(e.self ? e.message : __('Failed to get banks list from Gocardless.'));
            }
        );
    },
    remove_toolbar: function(frm) {
        !frm.is_new() && frm._bank.inits.bar && frm.events.setup_toolbar(frm, 1);
    },
    setup_toolbar: function(frm, del) {
        let label = __('Authorize');
        if (frm.custom_buttons[label]) {
            if (!del) return;
            frm.custom_buttons[label].remove();
            delete frm.custom_buttons[label];
            delete frm._bank.inits.bar;
        }
        if (del || frm._bank.inits.bar) return;
        frm._bank.inits.bar = 1;
        frm.add_custom_button(label, function() {
            var company = cstr(frm.doc.company),
            bank_id = cstr(frm.doc.bank_id),
            transaction_days = cint(frm.doc.transaction_days),
            docname = cstr(frm.docname);
            
            frappe.gc().connect_to_bank(
                company, bank_id, transaction_days, docname,
                function(link, ref_id, auth_id, auth_expiry) {
                    auth_expiry = moment().add(cint(auth_expiry), 'days').format(frappe.defaultDateFormat);
                    this.cache().set(
                        'gocardless_' + ref_id,
                        {id: auth_id, expiry: auth_expiry}
                    );
                    this.info_(__('Redirecting to {0} authorization page.', [frm.doc.bank]));
                    this.$timeout(function() { window.location.href = link; }, 2000);
                },
                function(e) {
                    this._error('Failed to connect to bank.', company, bank_id, transaction_days, docname, e.message);
                    this.error(e.self ? e.message : __('Failed to connect to {0}.', [frm.doc.bank]))
                }
            );
        });
        frm.change_custom_button_type(label, null, 'success');
    },
    setup_sync_data: function(frm, clear) {
        if (clear) {
            delete frm._bank.inits.sync;
            frm.toggle_display('auto_sync', 0);
            frm.toggle_display('sync_html', 0);
            return;
        }
        frm._bank.inits.sync = 1;
        if (!frm._bank.inits.sync_note) {
            frm._bank.inits.sync_note = 1;
            frm.get_field('sync_html').html(
                '<p class="text-danger">'
                    + __('For security reasons, transactions sync for each bank account, both auto and manual, are limited to a total of 4 times per day.')
                + '</p>'
            );
        }
        frm.toggle_display('auto_sync', 1);
        frm.toggle_display('sync_html', 1);
    },
    load_accounts: function(frm) {
        if (!frm._bank.inits.accounts) {
            let field = frm.get_field('bank_accounts_html');
            if (!field || !field.$wrapper)
                return frappe.gc()._error('Unable to get the accounts html field.');
            frappe.gc_accounts.init(frm, field);
            frm._bank.inits.accounts = 1;
        }
        frappe.gc_accounts.check();
    },
});


frappe.gc_banks = {
    load: function(country) {
        return frappe.gc().cache().get('banks_list_' + country);
    },
    store: function(frm, country, data) {
        frm._bank.list.cache[country] = data;
        frappe.gc().cache().set('banks_list_' + country, data, frm._bank.list.time);
    },
    field: function(frm) {
        if (frm._bank.inits.banks_field) return;
        let field = this._field(frm)
        if (!field) return;
        field = field.awesomplete;
        if (
            !field
            || frappe.gc().$isFunc(field.__item)
            || !frappe.gc().$isFunc(field.item)
        ) return;
        frm._bank.inits.banks_field = 1;
        if (!field.__item) field.__item = field.item;
        field.item = function(item) {
            if (!cur_frm || cur_frm.doctype !== 'Gocardless Bank') {
                if (!this.__item) return window.location.reload(true);
                else {
                    this.item = this.__item;
                    return this.item(item);
                }
            }
            let d = this.get_item(item.value);
            if (!d) d = item;
            if (!d.label) d.label = d.value;
            let idx = frm._bank.list.idx[frm._bank.list.key][d.value],
            html = '<strong>' + d.label + '</strong>',
            img = '<img src="{0}" alt="{1}" style="width:18px;height:18px;border:1px solid #6c757d;border-radius:50%;"/> ',
            fnd = 0;
            if (frappe.gc().$isNum(idx) && idx >= 0) {
                idx = frm._bank.list.cache[frm._bank.list.key][idx];
                if (idx && frappe.gc().$isStrVal(idx.logo) && ++fnd)
                    html = img.replace('{1}', idx.name).replace('{0}', frappe.gc().image().load(
                        idx.logo, 18, 18, frm._bank.list.time
                    )) + html;
            }
            if (!fnd) {
                idx = idx && frappe.gc().$isStrVal(idx.name) ? idx.name : 'Bank';
                html = img.replace('{1}', idx)
                .replace('{0}', 'https://placehold.co/100x100/4b535a/fff/png?text=' + idx[0]) + html;
            }
            if (d.description) html += '<br><span class="small">' + __(d.description) + '</span>';
            return $('<li></li>')
                .data('item.autocomplete', d)
                .prop('aria-selected', 'false')
                .html('<a><p>' + html + '</p></a>')
                .get(0);
        };
    },
    update: function(frm, country, data, ready) {
        let field = this._field(frm)
        if (!field) return;
        if (!ready) {
            frm._bank.list.idx[country] = {};
            data = frappe.gc().$map(data, function(v, i) {
                frm._bank.list.idx[country][v.name] = i;
                return {value: v.name, label: __(v.name)};
            });
            frm._bank.list.data[country] = data;
        }
        frm._bank.list.key = country;
        field.set_data(data);
        field.translate_values = false;
    },
    reset: function(frm, empty) {
        let field = this._field(frm)
        if (!field) return;
        let val = cstr(frm.doc.bank),
        data = [];
        if (!empty && val.length) data[0] = {label: __(val), value: val};
        field.set_data(data);
    },
    _field(frm) {
        let field = frm.get_field('bank');
        if (field) return field;
        frappe.gc()._error('Unable to get the bank form field.');
        return null;
        
    },
};


frappe.gc_accounts = {
    _wait_time: 1 * 60 * 1000,
    init(frm, field) {
        if (this._ready) return;
        this._enabled = frappe.gc().is_enabled;
        this._destroy = frappe.gc().$fn(this.destroy, this);
        this._refresh = frappe.gc().$fn(this.refresh, this);
        frappe.gc().once('page_change', this._destroy);
        frappe.gc().on('change', this._refresh);
        this._ready = 1;
        this._frm = frm;
        this._field = field;
    },
    wait() {
        if (this._wait_tm) return;
        this._ready && this._loading();
        this._wait_tm = frappe.gc().$timeout(function() {
            this._wait_tm = this._linked = null;
            this._ready && this._frm.reload_doc();
        }, this._wait_time, null, this);
    },
    check() {
        if (this._ready) this._wait_tm ? this._loading() : this._render();
    },
    reset() {
        this._wait_tm && frappe.gc().$timeout(this._wait_tm);
        this._wait_tm = this._linked = null;
    },
    refresh() {
        if (frappe.gc().is_enabled === this._enabled) return;
        this._enabled = !!frappe.gc().is_enabled;
        this._toggle_btns('action', this._enabled);
        this._toggle_btns('link', this._enabled);
    },
    destroy() {
        this._refresh && frappe.gc().off('change', this._refresh);
        if (this._$table) {
            this._$table.off('click', 'button.gc-action', this._on_action);
            this._$table.off('click', 'button.gc-link', this._on_link);
        }
        if (this._dialog) try {
            this._dialog.modal_body.off('click', 'button.gc-new-account', this._dialog.gc.on_new_click);
            this._dialog.modal_body.off('click', 'button.gc-link-account', this._dialog.gc.on_link_click);
            this._dialog.modal('destroy');
        } catch(_) {}
        if (this._field) try { this._field.$wrapper.empty(); } catch(_) {}
        this.reset();
        this._frm = null;
        this._field = null;
        this._$loading = null;
        this._$wrapper = null;
        this._$table = null;
        this._$body = null;
        this._dialog = null;
        this._accounts = null;
        this._linked = null;
        this._destroy = null;
        this._refresh = null;
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
        if (!this._$wrapper) this._build();
        else {
            this._destroy_popover();
            this._$body.empty();
        }
        if (!frappe.gc().$isArrVal(this._frm.doc.bank_accounts)) {
            this._$body.append('\
<tr>\
    <td scope="row" colspan="4" class="text-center text-muted">\
        ' + __('No bank account was received.') + '\
    </td>\
</tr>\
            ');
        } else {
            for (let i = 0, l = this._frm.doc.bank_accounts.length, r, h; i < l; i++) {
                r = this._frm.doc.bank_accounts[i];
                h = [
                    this._render_account(r),
                    this._render_balance(r),
                    this._render_status(r),
                    this._render_action(r)
                ].join('\n');
                this._$body.append('<tr data-gc-account="' + r.account + '">' + h + '</tr>');
            }
            this._init_popover();
            this.refresh();
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
        this._$wrapper = $('<div class="table-responsive mb-4 mx-md-2 mx-1"></div>');
        this._$table = $('\
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
        ').appendTo(this._$wrapper);
        this._$body = this._$table.find('tbody').first();
        this._on_action = frappe.gc().$fn(this._on_action, this);
        this._on_link = frappe.gc().$fn(this._on_link, this);
        this._$table.on('click', 'button.gc-action', this._on_action);
        this._$table.on('click', 'button.gc-link', this._on_link);
        this._$wrapper.appendTo(this._field.$wrapper);
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
        <td>\
            <small class="d-block w-100 text-center">\
                ' + Object.values(frappe.gc().$map({
                    opening: this._balance_labels.opening,
                    closing: this._balance_labels.closing,
                }, function(v, k) {
                    return v + ': ' + (data[k] != null ? data[k] : 'N/A');
                })).join('<br />') + '\
            </small>\
            <small class="d-block w-100 text-center text-muted gc-balance">\
                ' + __('View All') + '\
            </small>\
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
        exists && actions.push(html
            .replace('{action}', 'gc-link')
            .replace('{color}', 'success')
            .replace('{attr}', '')
            .replace('{label}', __('Edit'))
        );
        actions.push(html
            .replace('{action}', 'gc-action')
            .replace('{color}', disabled ? 'default' : (exists ? 'info' : 'primary'))
            .replace('{attr}', disabled ? ' disabled' : '')
            .replace('{label}', exists ? __('Sync') : __('Add'))
        );
        return '<td><div class="btn-group btn-group-sm">' + actions.join('') + '</div></td>';
    },
    _init_popover() {
        var me = this;
        this._$body.find('.gc-balance').popover({
            trigger: 'hover click',
            placement: 'top',
            title: __('Account Balance'),
            content: function() {
                let $el = $(this),
                account = $el.parents('tr').attr('data-gc-account'),
                data = {};
                if (frappe.gc().$isStrVal(account)) {
                    let row = me._get_bank_account(account);
                    if (row && row.balances) {
                        let list = frappe.gc().$parseJson(row.balances);
                        if (frappe.gc().$isArrVal(list))
                            for (let i = 0, l = list.length, v; i < l; i++) {
                                v = list[i];
                                data[v.type] = format_currency(v.amount, v.currency);
                            }
                    }
                }
                return '\
<div class="table-responsive m-0 p-0">\
    <table class="table table-sm table-borderless gc-table">\
        <tbody>\
            ' + Object.values(frappe.gc().$map(me._balance_labels, function(v, k) {
                    return '\
            <tr>\
                <td scope="row">' + v + '</td>\
                <td class="text-center">' + (data[k] != null ? data[k] : 'N/A') + '</td>\
            </tr>\
                    ';
            })).join('\n') + '\
        </tbody>\
    </table>\
</div>\
                ';
            },
            html: true
        });
    },
    _destroy_popover() {
        try {
            this._$body.find('.gc-balance').popover('dispose');
        } catch(_) {}
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