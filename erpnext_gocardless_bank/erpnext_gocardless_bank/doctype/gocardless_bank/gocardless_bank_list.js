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
            .once('page_change page_pop', function() { delete this.account_link_clicked; })
            .once('ready', function() {
                if (
                    !this.is_enabled
                    || !frappe.has_route_options()
                    || !this.$isStrVal(frappe.route_options.ref)
                ) return;
                let ref_id = frappe.route_options.ref,
                key = 'gocardless_' + ref_id;
                delete frappe.route_options.ref;
                if (!this.cache().has(key)) return;
                let auth = this.cache().pop(key);
                if (this.$isStrVal(auth)) auth = this.$parseJson(auth);
                if (!this.$isDataObj(auth) || !auth.name || !auth.bank || !auth.id || !auth.expiry) return;
                this.request(
                    'save_bank_link',
                    {
                        name: cstr(auth.name),
                        auth_id: auth.id,
                        auth_expiry: auth.expiry,
                    },
                    function(ret) {
                        if (!res) return this.error(__('Unable to link bank account to {0}.', [auth.bank]));
                        this.success_(__('{0} is linked successfully', [auth.bank]));
                        list.refresh();
                    },
                    function(e) {
                        this._error('Failed to link bank account.', auth, e.message);
                        this.error(__('Failed to link bank account to {0}.', [auth.bank]));
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