# ERPNext Bankaccountdata Gocardless

A plugin that integrates Nordigen open banking services with ERPNext.

---

### Table of Contents
- [Requirements](#requirements)
- [Setup](#setup)
  - [Install](#install)
  - [Update](#update)
  - [Uninstall](#uninstall)
- [Usage](#usage)
- [Issues](#issues)
- [License](#license)

---

### Requirements

- Frappe >= v14.0.0
- ERPNext >= v14.0.0

---

### Setup

#### Install
1. Go to bench directory

`cd ~/frappe-bench`

2. Get plugin from Github

*(Required only once)*

`bench get-app https://github.com/monolithon/erpnext_nordigen`

3. Install plugin on a specific site

`bench --site [sitename] install-app erpnext_nordigen`

4. Check the usage section below

#### Update
1. Go to app directory

`cd ~/frappe-bench/apps/erpnext_nordigen`

2. Get updates from Github

`git pull`

3. Go to bench directory

`cd ~/frappe-bench`

4. Update a specific site

`bench --site [sitename] migrate`

5. Restart bench

`bench restart`

#### Uninstall
1. Go to bench directory

`cd ~/frappe-bench`

2. Uninstall plugin from a specific site

`bench --site [sitename] uninstall-app erpnext_nordigen`

3. Remove plugin from bench

`bench remove-app erpnext_nordigen`

4. Restart bench

`bench restart`

---

### Usage

- Go to [Nordigen](https://ob.nordigen.com/overview/) to create an account
- Get your Nordigen **Secret ID** and **Secret Key** to be used later
- Open **Nordigen Settings** doctype and check the **Is Enabled** box to enable the plugin
- Paste your Nordigen **Secret ID** and **Secret Key** in their respective fields and save the settings
- Go to **Nordigen Bank** doctype, add a new bank and then save the entry
- After saving, click on **Authorize** buttom from the top to grant access to your bank's data
- After a successful authorization, the **Bank Accounts** table will appear at the bottom of the form
- Click on the **Add** button from the table to add the account to ERPNext
- Click on the **Sync** button from the top to manually sync the transactions of the lined bank accounts

---

### Issues
If you find bug in the plugin, please create a [bug report](https://github.com/monolithon/erpnext_nordigen/issues/new/choose) and let us know about it.

---

### License
This repository has been released under the [MIT License](https://github.com/monolithon/erpnext_nordigen/blob/main/LICENSE).
