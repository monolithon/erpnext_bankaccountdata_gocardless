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
                if (this.is_debug) !frm._set.logs && frappe._gc_logs.init(frm);
                else frm._set.logs && frappe._gc_logs.destroy(frm);
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
    refresh: function(frm) {
        !frm._set.logs && frappe._gc_logs.init(frm);
    },
    validate: function(frm) {
        let tkey = 'access';
        if (!frappe.gc().$isArrVal(frm.doc[tkey])) {
            frappe.gc().fatal(__('At least one valid company access data is required.'));
            return false;
        }
        let table = __('Gocardless Access');
        for (let i = 0, l = frm.doc[tkey].length, v, k; i < l; i++) {
            v = frm.doc[tkey][i];
            k = 'company';
            if (!frappe.gc().$isStrVal(v[k])) {
                frappe.gc().rfield_status(frm, tkey, v.name, k, __('A valid company is required.'));
                frappe.gc().fatal(__('{0} - #{1}: A valid company is required.', [table, i + 1]));
                return false;
            }
            k = 'secret_id';
            if (!frappe.gc().$isStrVal(v[k])) {
                frappe.gc().rfield_status(frm, tkey, v.name, k, __('A valid secret id is required.'));
                frappe.gc().fatal(__('{0} - #{1}: A valid secret id is required.', [table, i + 1]));
                return false;
            }
            if (!frm._set.is_valid_secret_id(v[k])) {
                frappe.gc().rfield_status(frm, tkey, v.name, k, __('Secret id is invalid.'));
                frappe.gc().fatal(__('{0} - #{1}: Secret id is invalid.', [table, i + 1]));
                return false;
            }
            k = 'secret_key';
            if (!frappe.gc().$isStrVal(v[k])) {
                frappe.gc().rfield_status(frm, tkey, v.name, k, __('A valid secret key is required.'));
                frappe.gc().fatal(__('{0} - #{1}: A valid secret key is required.', [table, i + 1]));
                return false;
            }
            if (!frm._set.is_valid_secret_key(v[k])) {
                frappe.gc().rfield_status(frm, tkey, v.name, k, __('Secret key is invalid.'));
                frappe.gc().fatal(__('{0} - #{1}: Secret key is invalid.', [table, i + 1]));
                return false;
            }
        }
    },
    setup_table: function(frm) {
        let tkey = 'access';
        if (!frappe.gc().$isArrVal(frm.doc[tkey])) return;
        for (let i = 0, l = frm.doc[tkey].length, v; i < l; i++) {
            v = frm.doc[tkey][i];
            frm._set.table.add(cstr(v.name), cstr(v.company));
        }
    },
    destroy_table: function(frm) {
        let tkey = 'access';
        if (!frappe.gc().$isArrVal(frm.doc[tkey])) return;
        for (let i = 0, l = frm.doc[tkey].length, v; i < l; i++) {
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
        } else if (
            frm._set.table.has(val, 1)
            && frm._set.table.val(val, 1) !== cdn
        ) {
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
    _tpl: {},
    init: function(frm) {
        if (frm._set.logs) return;
        frappe.gc()._log('Logs list init.');
        frm._set.logs = 1;
        this._destroy = frappe.gc().$afn(this.destroy, [frm], this);
        //frappe.gc().once('page_clean', this._destroy);
        let $el = frm.get_field('logs_html').$wrapper;
        this._$el = $el;
        this._events();
        if (!frappe.gc().$hasElem('gocardless_css'))
            frappe.gc().$loadCss(
                '/assets/erpnext_gocardless_bank/css/gocardless.bundle.css',
                {id: 'gocardless_css'}
            );
        $el.append('<div class="gc-flex-wrapper gc-mh-300 mt-2 mb-4 mx-md-2 mx-1"></div>');
        this._$wrapper = $el.find('.gc-flex-wrapper').first();
        frm.toggle_display('logs_section', 1);
        frm.toggle_display('logs_html', 1);
        this._refresh();
    },
    destroy: function(frm) {
        if (!frm._set.logs) return;
        frm._set.logs = 0;
        frm.toggle_display('logs_section', 0);
        frm.toggle_display('logs_html', 0);
        //frappe.gc().off('page_clean', this._destroy);
        this._$el.off('click', 'button.refresh-logs', this._handlers.refresh);
        this._$el.off('click', 'button.view-log', this._handlers.view);
        this._$el.empty();
        try { this._dialog && this._dialog.dialog('destroy'); } catch(_) {}
        try { this._dialog.$wrapper && this._dialog.$wrapper.remove(); } catch(_) {}
        this._tpl = {};
        this._elkey = null;
        delete this._destroy;
        delete this._$el;
        delete this._$wrapper;
        delete this._handlers;
        delete this._list;
        delete this._dialog;
    },
    _events: function() {
        this._handlers = {
            refresh: frappe.gc().$fn(this._refresh, this),
            view: frappe.gc().$fn(function(e) {
                let $tr = $(e.target);
                if (!$tr.is('tr')) $tr = $tr.parents('tr');
                let name = $tr.attr('data-file-name');
                if (frappe.gc().$isStrVal(name)) this._open(name);
                else frappe.gc()._error('Log filename from attr is invalid.', name);
            }, this),
            remove: frappe.gc().$fn(function(e) {
                let $tr = $(e.target);
                if (!$tr.is('tr')) $tr = $tr.parents('tr');
                let name = $tr.attr('data-file-name');
                if (frappe.gc().$isStrVal(name)) this._remove(name, $tr);
                else frappe.gc()._error('Log filename from attr is invalid.', name);
            }, this),
        };
        this._$el.on('click', 'button.refresh-logs', this._handlers.refresh);
        this._$el.on('click', 'button.view-log', this._handlers.view);
        this._$el.on('click', 'button.remove-log', this._handlers.remove);
    },
    _refresh: function() {
        if (this._refreshing) return;
        this._refreshing = 1;
        this._loading();
        var me = this;
        frappe.gc().request(
            'get_log_files', null,
            function(ret) {
                me._refreshing = 0;
                if (!this.$isArr(ret)) {
                    this._error('Logs list received is invalid.', ret);
                    me._error();
                } else {
                    this._log('Logs list received.', ret);
                    me._list = ret;
                    me._render();
                }
            },
            function(e) {
                me._refreshing = 0;
                this._error('Failed to load logs list.', e.message);
                me._error();
            }
        );
    },
    _toggle: function(key) {
        let $e;
        if (this._elkey) {
            $e = this._$wrapper.find('.' + this._elkey).first();
            !$e.hasClass('lu-hidden') && $e.toggleClass('lu-hidden', 1);
        }
        this._elkey = key;
        $e = this._$wrapper.find('.' + this._elkey).first();
        $e.hasClass('lu-hidden') && $e.toggleClass('lu-hidden', 0);
    },
    _loading: function() {
        if (!this._tpl.loading) {
            this._tpl.loading = 1;
            this._$wrapper.append('\
<div class="logs-loading text-center lu-hidden">\
    <div class="spinner-border text-info" role="status">\
        <span class="sr-only">' + __('Loading') + '</span>\
    </div>\
    <div class="text-center text-info">\
        ... ' + __('Loading Logs') + ' ...\
    </div>\
</div>\
            ');
        }
        this._toggle('logs-loading');
    },
    _error: function(message) {
        if (!this._tpl.error) {
            this._tpl.error = 1;
            this._$wrapper.append('\
<div class="logs-error text-center text-danger lu-hidden">\
    ' + __('Failed to list logs files.') + '\
</div>\
            ');
        }
        this._toggle('logs-error');
    },
    _render: function() {
        if (!this._tpl.table) {
            this._tpl.table = 1;
            this._$wrapper.append('\
<div class="logs-table w-100 lu-hidden">\
    <div class="w-100 mb-1">\
        <button type="button" class="btn btn-default btn-sm refresh-logs">\
            ' + __('Refresh') + '\
        </button>\
    </div>\
    <div class="table-responsive w-100">\
        <table class="table table-bordered table-hover gc-table">\
            <thead class="thead-dark">\
                <tr>\
                    <th scope="col">' + __('File') + '</th>\
                    <th>' + __('Action') + '</th>\
                </tr>\
            </thead>\
            <tbody class="gc-table-body">\
            </tbody>\
        </table>\
    </div>\
</div>\
            ');
        }
        this._$wrapper.find('.gc-table-body').first().empty().append(
            this._list && this._list.length
            ? frappe.gc().$map(this._list, function(v) {
                return '\
                <tr data-file-name="' + v + '">\
                    <td scope="row">' + v + '</td>\
                    <td>\
                        <div class="btn-group btn-group-sm">\
                            <button type="button" class="btn btn-default btn-sm view-log">\
                                ' + __('View') + '\
                            </button>\
                            <button type="button" class="btn btn-danger btn-sm remove-log">\
                                ' + __('Remove') + '\
                            </button>\
                        </div>\
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
        );
        this._toggle('logs-table');
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
                this._error('Failed to load the log file content.', name, e.message);
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
        this._dialog.get_field('file_loading').$wrapper.html('\
<div class="gc-flex-wrapper gc-mh-300 mx-md-2 mx-1 text-center">\
    <div class="spinner-border text-info" role="status">\
        <span class="sr-only">' + __('Loading') + '</span>\
    </div>\
</div>\
        ');
        this._dialog.get_field('file_error').$wrapper.html('\
<div class="gc-flex-wrapper gc-mh-300 mx-md-2 mx-1 text-center text-mute">\
    ' + __('Log file is empty, does not exist or failed to be loaded.') + '\
</div>\
        ');
    },
    _remove: function(name, $tr) {
        frappe.warn(
            __('Warning'),
            '\
            <p class="text-danger font-weight-bold">\
                ' + __('You are about to remove the log file "{0}".', [name]) + '\
            </p>\
            <p class="text-danger">\
                ' + __('This action will remove the file completely from the system so it can\'t be undone.') + '\
            </p>\
            <p class="text-danger">\
                ' + __('Make sure that the file is exactly the one you wish to remove before proceeding.') + '\
            </p>\
            ',
            function() {
                frappe.gc().request(
                    'remove_log_file',
                    {filename: name},
                    function(ret) {
                        if (ret) $tr.remove();
                        else this.error_(__('Unable to remove log file "{0}".', [name]));
                    },
                    function(e) {
                        this._error('Failed to remove log file.', name, e.message);
                        this.error_(e.self ? e.message : __('Failed to remove log file "{0}".', [name]));
                    }
                );
            },
            __('Continue')
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