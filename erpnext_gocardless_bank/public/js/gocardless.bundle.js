/*
*  ERPNext Gocardless Bank © 2023
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/

frappe.provide('frappe.Gocardless');
frappe.provide('frappe.gocardless');


function $class(v) {
    var t = v == null ? (v === void 0 ? 'Undefined' : 'Null')
        : Object.prototype.toString.call(v).slice(8, -1);
    return t === 'Number' && isNaN(v) ? 'NaN' : t;
}


frappe.Gocardless = class Gocardless {
    constructor() {
        this.is_ready = false;
        this.is_enabled = false;
        this.request(
            'is_enabled',
            null,
            function(res) {
                this.is_ready = true;
                if (res) {
                    this.is_enabled = true;
                    this._bank_link = {};
                }
                if (this.is_enabled) this._on_ready && this._on_ready.call(this);
                this._on_ready = null;
                if (!res) this.destroy();
            },
            function() {
                this.fatal('Unable to get Gocardless plugin status.');
            }
        );
    }
    on_ready(fn) {
        if (this.is_ready) {
            if (this.is_enabled) fn && fn.call(this);
        } else {
            this._on_ready = fn;
        }
    }
    destroy() {
        this._on_ready = this._bank_link = null;
        frappe.gocardless._init = null;
    }
    error(title, msg, args) {
        if (msg && Array.isArray(msg)) {
            args = msg;
            msg = null;
        }
        if (!msg) {
            msg = title;
            title = null;
        }
        frappe.msgprint({
            title: '[Gocardless]: ' + __(title || 'Error'),
            indicator: 'red',
            message: __(msg, args),
        });
    }
    info(title, msg, args) {
        if (msg && Array.isArray(msg)) {
            args = msg;
            msg = null;
        }
        if (!msg) {
            msg = title;
            title = null;
        }
        frappe.msgprint({
            title: '[Gocardless]: ' + __(title || 'Info'),
            indicator: 'blue',
            message: __(msg, args),
        });
    }
    fatal(msg, args) {
        this.destroy();
        frappe.throw('[Gocardless]: ' + __(msg, args));
    }
    _console() {
        let args = Array.prototype.slice.call(arguments),
        fn = args.shift();
        args = args.shift();
        if ($class(args) === 'Arguments')
            args = Array.prototype.slice.call(args);
        if ($class(args[0]) === 'Arguments')
            args = Array.prototype.slice.call(args[0]);
        if ($class(args[0]) !== 'String') args.unshift('[Gocardless]:');
        else args[0] = '[Gocardless]: ' + __(args[0]);
        console[fn].apply(console, args);
    }
    _log() {
        this._console('log', arguments);
    }
    _info() {
        this._console('info', arguments);
    }
    _error() {
        this._console('error', arguments);
    }
    _warn() {
        this._console('warn', arguments);
    }
    request(method, args, callback, error, _freeze) {
        var me = this;
        let opts = {
            method: 'erpnext_gocardless_bank.libs.gocardless.' + method,
            freeze: _freeze != null ? _freeze : false,
            callback: function(ret) {
                if (ret && $.isPlainObject(ret)) ret = ret.message || ret;
                if (!ret.error) {
                    callback.call(me, ret);
                    return;
                }
                let message = !!ret.message ? __(ret.message) : '';
                if (ret.list) {
                    let msg = [];
                    ret.list.forEach(function(d) {
                        msg.push(_(d.message));
                    });
                    message = msg.join('\n');
                }
                if (error) error.call(me, {message: __(message, args)});
                else me.error(message, args);
            },
            error: function(ret, txt) {
                let err = {};
                if (ret && $class(ret) === 'String') err.message = ret;
                else if (txt && $class(txt) === 'String') err.message = txt;
                else err.message = 'The request sent have failed.';
                if (error) error.call(me, err);
                else me.error(err.message, args);
            }
        };
        if (args) {
            opts.type = 'POST';
            opts.args = args;
        }
        try {
            frappe.call(opts);
        } catch(e) {
            if (error) error.call(this, e);
            else this._log('Error caught.', e);
        }
    }
    connect_to_bank(id, transaction_days, docname, callback, error) {
        transaction_days = cint(transaction_days || 0);
        var key = (docname ? docname + '-' : '') + id + '-' + transaction_days;
        
        if (this._bank_link[key]) {
            let bank = this._bank_link[key];
            callback.call(
                this,
                bank.link,
                bank.reference_id,
                bank.id,
                bank.access_valid_for_days
            );
            return;
        }
        
        var reference_id = '_' + Math.random().toString(36).substr(2),
        args = {
            bank_id: id,
            reference_id: reference_id,
            transaction_days: transaction_days,
        };
        if (docname) args.docname = docname;
        this.request(
            'get_bank_link',
            args,
            function(res) {
                if (!$.isPlainObject(res)) {
                    this.error('The bank link received is invalid.');
                    return;
                }
                res.access_valid_for_days = cint(res.access_valid_for_days || 90);
                
                this._bank_link[key] = res;
                this._bank_link[key].reference_id = reference_id;
                
                callback.call(
                    this,
                    res.link,
                    reference_id,
                    res.id,
                    res.access_valid_for_days
                );
            },
            function() {
                this.error('Unable to connect to the bank through api.');
                if (error) error.call(this);
            }
        );
    }
};

frappe.gocardless = function() {
    frappe.gocardless._init = frappe.gocardless._init || new frappe.Gocardless();
    return frappe.gocardless._init;
};