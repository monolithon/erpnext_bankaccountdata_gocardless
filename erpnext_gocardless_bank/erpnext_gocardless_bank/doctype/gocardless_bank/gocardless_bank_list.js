/*
*  ERPNext Gocardless Bank © 2023
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


frappe.provide("frappe.listview_settings");


frappe.listview_settings['Gocardless Bank'] = {
    onload: function(list) {
        frappe.gc()
            .on('ready change', function() { this.setup_list(list); })
            .once('page_change', function() { delete this.account_link_clicked; })
            .once('ready', function() {
                var ret = this.check_auth();
                if (ret.disabled || ret.no_route) return;
                if (ret.invalid_ref) return this.error(__('Authorization reference ID is invalid.'));
                if (ret.not_found) return this.error(__('Authorization data is missing.'));
                if (ret.invalid_data) {
                    frappe.gc()._error('Invalid authorization data.', ret.data);
                    return this.error(__('Authorization data is invalid.'));
                }
                ret = ret.data;
                this.save_auth(
                    {
                        name: ret.name,
                        bank: ret.bank,
                        bank_id: ret.bank_id,
                        auth_id: ret.auth_id,
                        auth_expiry: ret.auth_expiry,
                    },
                    function(ret) {
                        if (!ret) return this.error(__('Unable to store bank authorization for "{0}".', [ret.name]));
                        this.success_(__('{0} has been authorized successfully.', [ret.name]));
                        list.refresh();
                    },
                    function(e) {
                        this._error('Failed to store bank authorization.', ret, e.message);
                        this.error(e.self ? e.message : __('Failed to store bank authorization.', [ret.name]));
                    }
                );
            });
    },
    get_indicator: function(doc) {
        if (doc.disabled) return [__('Disabled'), 'red', 'disabled,=,Yes'];
        return [__('Enabled'), 'green', 'disabled,=,No'];
    },
    button: {
        show: function(doc) {
            return frappe.gc().is_ready
                && frappe.gc().is_enabled
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
            if (!frappe.gc().account_link_clicked) frappe.gc().account_link_clicked = {};
            if (frappe.gc().account_link_clicked[doc.name]) return;
            frappe.gc().account_link_clicked[doc.name] = 1;
            frappe.gv().connect_to_bank(
                doc.bank_id,
                cint(doc.transaction_days),
                null,
                function(link, ref_id, auth_id, auth_expiry) {
                    this.cache().set(
                        'gocardless_' + ref_id,
                        this.$toJson({
                            name: doc.name,
                            bank: doc.bank,
                            id: auth_id,
                            expiry: moment().add(cint(auth_expiry), 'days')
                                .format(frappe.defaultDateFormat)
                        })
                    );
                    this.info_(__('Redirecting to {0} authorization page.', [doc.bank]));
                    this.$timeout(function() {
                        delete this.account_link_clicked;
                        window.location.href = link;
                    }, 2000);
                },
                function(e) {
                    delete this.account_link_clicked[doc.name];
                    this._error('list action', e.message);
                }
            );
        },
    },
    formatters: {
        auth_expiry: function(v) {
            if (!cstr(v).length) return '';
            return moment(v, frappe.defaultDateFormat).fromNow();
        },
    },
};