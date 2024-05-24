/*
*  ERPNext Gocardless Bank © 2024
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


frappe.ui.form.on('Gocardless Settings', {
    onload: function(frm) {
        frappe.gc()
            .on('ready change', function() {
                if (frm._set.debug == null && !this.is_debug) return;
                if (this.is_debug !== frm._set.debug) {
                    frm._set.debug = this.is_debug;
                    frappe._gc_logs.setup(frm);
                }
            })
            /*.on('page_clean', function() {
                frm && frm.events.destroy_table(frm);
                frm && delete frm._set;
            })*/
            .on('on_alert', function(d, t) {
                frm._set.errs.includes(t) && (d.title = __(frm.doctype));
            });
        frm._set = {
            errs: ['fatal', 'error'],
            ignore: 0,
            debug: null,
            table: frappe.gc().table(1),
            html: frappe.gc().table(),
            is_valid_secret_id: function(val) {
                return val.length === 36
                && !!(new RegExp('^([a-z0-9]{8})-([a-z0-9]{4})-([a-z0-9]{4})-([a-z0-9]{4})-([a-z0-9]{12})$', 'ig')).test(val);
            },
            is_valid_secret_key: function(val) {
                return val.length === 128 && !!(new RegExp('^([a-z0-9]+)$', 'ig')).test(val);
            },
        };
        frm.set_query('company', 'access', function(doc) {
            return {filters: {is_group: 0}};
        });
        frm.events.setup_table(frm);
    },
    validate: function(frm) {
        let tkey = 'access';
        if (!frappe.gc().$isArrVal(frm.doc[tkey])) {
            frappe.gc().fatal(__('At least one valid company access data is required.'));
            return false;
        }
        for (let i = 0, l = frm.doc[tkey].length, v, k; i < l; i++) {
            v = frm.doc[tkey][i];
            k = 'company';
            if (!frappe.gc().$isStrVal(v[k])) {
                frappe.gc().rfield_status(frm, tkey, v.name, k, __('A valid company is required.'));
                frappe.gc().fatal(__('A valid access company in row #{0} is required.', [i]));
                return false;
            }
            k = 'secret_id';
            if (!frappe.gc().$isStrVal(v[k])) {
                frappe.gc().rfield_status(frm, tkey, v.name, k, __('A valid secret id is required.'));
                frappe.gc().fatal(__('A valid access secret id in row #{0} is required.', [i]));
                return false;
            }
            if (!frm._set.is_valid_secret_id(v[k])) {
                frappe.gc().rfield_status(frm, tkey, v.name, k, __('Secret id is invalid.'));
                frappe.gc().fatal(__('Access secret id in row #{0} is invalid.', [i]));
                return false;
            }
            k = 'secret_key';
            if (!frappe.gc().$isStrVal(v[k])) {
                frappe.gc().rfield_status(frm, tkey, v.name, k, __('A valid secret key is required.'));
                frappe.gc().fatal(__('A valid access secret key in row #{0} is required.', [i]));
                return false;
            }
            if (!frm._set.is_valid_secret_key(v[k])) {
                frappe.gc().rfield_status(frm, tkey, v.name, k, __('Secret key is invalid.'));
                frappe.gc().fatal(__('Access secret key in row #{0} is invalid.', [i]));
                return false;
            }
        }
    },
    setup_table: function(frm) {
        let tkey = 'access';
        if (!frappe.gc().$isArrVal(frm.doc[tkey])) return;
        for (let i = 0, l = frm.doc[tkey].length, v, f; i < l; i++) {
            v = frm.doc[tkey][i];
            frm._set.table.add(cstr(v.name), cstr(v.company));
        }
    },
    destroy_table: function(frm) {
        let tkey = 'access';
        if (!frappe.gc().$isArrVal(frm.doc[tkey])) return;
        for (let i = 0, l = frm.doc[tkey].length, v, f; i < l; i++) {
            v = cstr(frm.doc[tkey][i].name);
            frappe._gc_access.destroy(frm, v);
        }
    },
});


frappe.ui.form.on('Gocardless Access', {
    before_access_remove: function(frm, cdt, cdn) {
        frm._set.table.del(cdn);
        frappe._gc_access.destroy(frm, cdn);
    },
    access_on_form_rendered: function(frm, cdt, cdn) {
        frappe._gc_access.render(frm, cdn);
    },
    company: function(frm, cdt, cdn) {
        if (frm._set.ignore) return;
        let row = locals[cdt][cdn],
        key = 'company',
        val = cstr(row[key]),
        err;
        if (!val.length) {
            err = __('A valid company is required.');
        } else if (frm._set.table.has(val, 1)) {
            err = __('Access for company "{0}" already exist.', [val]);
            val = '';
            frm._set.ignore++;
            frappe.model.set_value(cdt, cdn, key, val);
            frm._set.ignore--;
        }
        frm._set.table.add(cdn, val);
        frappe.gc().rfield_status(frm, 'access', cdn, key, err);
    },
    secret_id: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn],
        key = 'secret_id',
        val = cstr(row[key]),
        err;
        if (!val.length) err = __('A valid secret id is required.');
        else if (!frm._set.is_valid_secret_id(val)) err = __('Secret id is invalid.');
        frappe.gc().rfield_status(frm, 'access', cdn, key, err);
    },
    secret_key: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn],
        key = 'secret_key',
        val = cstr(row[key]),
        err;
        if (!val.length) err = __('A valid secret key is required.');
        else if (!frm._set.is_valid_secret_key(val)) err = __('Secret key is invalid.');
        frappe.gc().rfield_status(frm, 'access', cdn, key, err);
    },
});


frappe._gc_logs = {
    _event: 0,
    _handler: null,
    _list: null,
    _dialog: null,
    setup: function(frm) {
        var $el = frm.get_field('logs_html').$wrapper;
        this.destroy = frappe.gc().$afn(this.destroy, [$el], this);
        
        let val = frappe.gc().is_debug ? 1 : 0;
        frm.toggle_display('logs_section', val);
        frm.toggle_display('logs_html', val);
        if (!val) {
            frappe.gc().off('page_change page_pop', this.destroy);
            return this.destroy();
        }
        frappe.gc().once('page_change page_pop', this.destroy);
        !this._event && this._events($el);
        if (this._list) return this._render($el);
        if (!frappe.gc().$hasElem('gocardless-style'))
            frappe.gc().$loadCss(
                '/assets/erpnext_gocardless_bank/css/gocardless.bundle.css',
                {id: 'gocardless-style'}
            );
        this._loading($el);
        var me = this;
        frappe.gc().request(
            'get_log_files', null,
            function(ret) {
                if (!this.$isArrVal(ret)) {
                    this._error('Logs list received is invalid.', ret);
                    me._error($el);
                } else {
                    me._list = ret;
                    me._render($el);
                }
            },
            function(e) {
                this._error('Failed to load logs list.', e.message, e.stack);
                me._error($el);
            }
        );
    },
    destroy: function($el) {
        if (!this._event) return;
        $el.empty().off('click', '.view-log', this._handler);
        try { this._dialog && this._dialog.dialog('destroy'); } catch(_) {}
        this._handler = null;
        this._list = null;
        this._dialog = null;
        this._event--;
    },
    _events: function($el) {
        this._handler = frappe.gc().$fn(function(e) {
            let $btn = $(e.target);
            if (!$btn.is('button')) $btn = $btn.find('button.view-log').first();
            let name = $btn.attr('data-file-name');
            if (frappe.gc().$isStrVal(name)) this._open(name);
            else frappe.gc()._error('Log filename from button attr is invalid.', name);
        }, this);
        $el.on('click', 'button.view-log', this._handler);
        this._event++;
    },
    _loading: function($el) {
        $el.empty().html('\
<div class="w-100 mb-4 mx-md-2 mx-1 text-center">\
    <div class="spinner-border text-info m-2" role="status">\
        <span class="sr-only">' + __('Loading') + '</span>\
    </div>\
    <div class="text-center text-info">\
        ... ' + __('Loading Logs') + ' ...\
    </div>\
</div>\
        ');
    },
    _error: function($el, message) {
        $el.empty().html('\
<div class="w-100 mb-4 mx-md-2 mx-1">\
    <div class="text-center ' + (message ? 'text-mute' : 'text-danger') + '">\
        ' + (message || __('Failed to load the list of logs.')) + '\
    </div>\
</div>\
        ');
    },
    _render: function($el) {
        $el.empty().html('\
<div class="table-responsive w-100 mb-4 mx-md-2 mx-1">\
    <table class="table table-bordered table-hover gc-table">\
        <thead class="thead-dark">\
            <tr>\
                <th scope="col">' + __('File') + '</th>\
                <th>' + __('Action') + '</th>\
            </tr>\
        </thead>\
        <tbody>\
            ' + (this._list.length
                ? frappe.gc().$map(this._list, function(v) {
                    return '\
            <tr>\
                <td scope="row">' + v + '</td>\
                <td>\
                    <button type="button" class="btn btn-default btn-sm view-log" data-file-name="' + v + '">\
                        ' + __('View') + '\
                    </button>\
                </td>\
            </tr>\
                    ';
                }).join('\n')
                : '\
            <tr>\
                <td colspan="2" class="text-center text-mute">\
                    ' + __('No log files found.') + '\
                </td>\
            </tr>\
                '
            ) + '\
        </tbody>\
    </table>\
</div>\
        ');
    },
    _open: function(name) {
        if (!this._dialog) this._make();
        this._dialog.set_title(__('Log File: {0}', [name]));
        this._dialog.toggle_loading();
        this._dialog.show();
        
        var me = this;
        frappe.gc().request(
            'load_log_file',
            {filename: name},
            function(ret) {
                if (!this.$isStrVal(ret)) me._dialog.toggle_error();
                else me._dialog.toggle_content(ret);
            },
            function(e) {
                this._error('Failed to load the log file content.', name, e.message, e.stack);
                me._dialog.toggle_error();
            }
        );
    },
    _make: function() {
        this._dialog = new frappe.ui.Dialog({
            indicator: 'green',
            fields: [
                {
                    fieldname: 'file_loading',
                    fieldtype: 'HTML',
                    read_only: 1,
                    hidden: 1,
                },
                {
                    fieldname: 'file_error',
                    fieldtype: 'HTML',
                    read_only: 1,
                    hidden: 1,
                },
                {
                    fieldname: 'file_content',
                    fieldtype: 'Long Text',
                    read_only: 1,
                    hidden: 1,
                },
            ],
        });
        this._dialog._toggle_fields = function(x) {
            for (let k = ['file_loading', 'file_error', 'file_content'], i = 0, l = k.length; i < l; i++)
                this.set_df_property(k[i], 'hidden', x === i ? 0 : 1);
        };
        this._dialog.toggle_loading = function() { this._toggle_fields(0); };
        this._dialog.toggle_error = function() { this._toggle_fields(1); };
        this._dialog.toggle_content = function(v) {
            this.set_value('file_content', v);
            this._toggle_fields(2);
        };
        this._loading(this._dialog.get_field('file_loading').$wrapper);
        this._error(
            this._dialog.get_field('file_error').$wrapper,
            __('Log file is empty or does not exist.')
        );
    },
};


frappe._gc_access = {
    render(frm, cdn) {
        if (frm._set.html.has(cdn)) return;
        frm._set.html.add(cdn);
        let field = frappe.gc().get_rmfield(frm, 'access', cdn, 'access_html');
        if (!field || !field.$wrapper) return;
        let module = frappe.gc().module;
        field.$wrapper.html('\
<div class="row m-0 p-0">\
    <div class="col-md-6 col-12">\
        <h4>' + __('Authorization') + '</h4>\
        <div class="text-justify">\
            ' + __('Create a new <strong>Gocardless Open Banking Portal</strong> account, or log in to your already existing account, in order to obtain your personal <strong>Secret ID</strong> and <strong>Secret Key</strong> that are required for access authorization.') + '\
        </div>\
        <div class="btn-group">\
            <button type="button" class="btn btn-default gc-login">\
                ' + __('Login') + '\
            </button>\
            <button type="button" class="btn btn-success gc-signup">\
                ' + __('Sign Up') + '\
            </button>\
        </div>\
    </div>\
    <div class="col-md-6 col-12">\
        <h4>' + __('Privacy Policy') + '</h4>\
        <div class="text-justify">\
            ' + [
                __('<strong>{0}</strong> is an app that links between <strong>Gocardless</strong> and <strong>ERPNext</strong> for the purpose of synchronizing <strong>Banks</strong>, <strong>Bank Accounts</strong> and <strong>Bank Transactions</strong> only.', [module]),
                __('<strong>{0}</strong> app doesn\'t collect any of the information, provided and synchronized, and everything is stored locally within <strong>ERPNext</strong> database.', [module]),
                __('Both <strong>Login</strong> and <strong>Sign Up</strong> are fully handled by <strong>Gocardless</strong> directly and without any interference from <strong>{0}</strong> app and anyone else.', [module]),
                __('<strong>Secret ID</strong> and <strong>Secret Key</strong> provided are only used to obtain the <strong>Access Token</strong> that is required for authorizing the communication with <strong>Gocardless</strong> Open Banking API service.'),
            ].join(' ') + '\
        </div>\
        <div class="w-100">\
            ' + __('If you have any question or concern regarding <strong>{0}</strong> app, please feel free to contact us by sending an email to <strong>{1}</strong>.', [module, 'erpnextgc@monolithon.com']) + '\
        </div>\
    </div>\
</div>\
        ');
        field.$wrapper
            .on('click', 'button.gc-login', function(e) {
                e && e.preventDefault && e.preventDefault();
                window.open('https://manage.gocardless.com/sign-in', '_blank');
            })
            .on('click', 'button.gc-signup', function(e) {
                e && e.preventDefault && e.preventDefault();
                window.open('https://manage.gocardless.com/sign-up', '_blank');
            });
    },
    destroy(frm, cdn) {
        if (!frm._set.html.has(cdn)) return;
        frm._set.html.del(cdn);
        let field = frappe.gc().get_rmfield(frm, 'access', cdn, 'access_html');
        field && field.$wrapper && field.$wrapper
            .off('click', 'button.gc-login')
            .off('click', 'button.gc-signup');
    },
};