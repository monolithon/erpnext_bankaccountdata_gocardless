/*
*  ERPNext Gocardless Bank © 2023
*  Author:  Ameen Ahmed
*  Company: Level Up Marketing & Software Development Services
*  Licence: Please refer to LICENSE file
*/


(function() {
    var LU = {
        $type(v) {
            if (v == null) return v === null ? 'Null' : 'Undefined';
            let t = Object.prototype.toString.call(v).slice(8, -1);
            return t === 'Number' && isNaN(v) ? 'NaN' : t;
        },
        $hasProp(k, o) { return Object.prototype.hasOwnProperty.call(o || this, k); },
        $is(v, t) { return v != null && this.$type(v) === t; },
        $of(v, t) { return typeof v === t; },
        $isObjLike(v) { return v != null && this.$of(v, 'object'); },
        $isStr(v) { return this.$is(v, 'String'); },
        $isStrVal(v) { return this.$isStr(v) && v.length; },
        $isNum(v) { return this.$is(v, 'Number') && isFinite(v); },
        $isBool(v) { return v === true || v === false; },
        $isBoolLike(v) { return this.$isBool(v) || v === 0 || v === 1; },
        $isFunc(v) { return this.$of(v, 'function') || /(Function|^Proxy)$/.test(this.$type(v)); },
        $isArr(v) { return this.$is(v, 'Array'); },
        $isArrVal(v) { return this.$isArr(v) && v.length; },
        $isArgs(v) { return this.$is(v, 'Arguments'); },
        $isArgsVal(v) { return this.$isArgs(v) && v.length; },
        $isArrLike(v) { return this.$isArr(v) || this.$isArgs(v); },
        $isArrLikeVal(v) { return this.$isArrLike(v) && v.length; },
        $isEmptyObj(v) {
            if (this.$isObjLike(v)) for (let k in v) { if (this.$hasProp(k, v)) return false; }
            return true;
        },
        $isBaseObj(v) { return !this.$isArgs(v) && this.$is(v, 'Object'); },
        $isBaseObjVal(v) { return this.$isBaseObj(v) && !this.$isEmptyObj(v); },
        $fnStr(v) { return Function.prototype.toString.call(v); },
        $isObj(v, _) {
            if (!this.$isObjLike(v)) return false;
            let k = 'constructor';
            v = Object.getPrototypeOf(v);
            return this.$hasProp(k, v) && this.$isFunc(v[k])
                && (!_ || this.$fnStr(v[k]) === this.$fnStr(Object));
        },
        $isObjVal(v) { return this.$isObj(v) && !this.$isEmptyObj(v); },
        $isDataObj(v) { return this.$isObj(v, 1); },
        $isDataObjVal(v) { return this.$isDataObj(v) && !this.$isEmptyObj(v); },
        $isIter(v) { return this.$isBaseObj(v) || this.$isArrLike(v); },
        $isEmpty(v) {
            return v == null || v === '' || v === 0 || v === false
                || (this.$isArrLike(v) && v.length < 1) || this.$isEmptyObj(v);
        },
        $toArr(v, s, e) { try { return Array.prototype.slice.call(v, s, e); } catch(_) { return []; } },
        $toJson(v, d) { try { return JSON.stringify(v); } catch(_) { return d; } },
        $parseJson(v, d) { try { return JSON.parse(v); } catch(_) { return d; } },
        $clone(v) { return this.$parseJson(this.$toJson(v)); },
        $filter(v, fn) {
            fn = this.$fn(fn) || function(v) { return v != null; };
            let o = this.$isBaseObj(v), r = o ? {} : [];
            if (o) for (let k in v) { if (this.$hasProp(k, v) && fn(v[k], k) !== false) r[k] = v[k]; }
            else for (let i = 0, x = 0, l = v.length; i < l; i++) { if (fn(v[i], i) !== false) r[x++] = v[i]; }
            return r;
        },
        $map(v, fn) {
            if (!(fn = this.$fn(fn))) return this.$clone(v);
            let o = this.$isBaseObj(v), r = o ? {} : [];
            if (o) for (let k in v) { if (this.$hasProp(k, v)) r[k] = fn(v[k], k); }
            else for (let i = 0, x = 0, l = v.length; i < l; i++) { r[x++] = fn(v[i], i); }
            return r;
        },
        $assign() {
            let a = arguments.length && this.$filter(arguments, this.$isBaseObj);
            if (!a || !a.length) return {};
            a.length > 1 && Object.assign.apply(null, a);
            return a[0];
        },
        $extend() {
            let a = arguments.length && this.$filter(arguments, this.$isBaseObj);
            if (!a || a.length < 2) return a && a.length ? a[0] : {};
            let d = this.$isBool(arguments[0]) && arguments[0];
            for (let i = 1, l = a.length; i < l; i++) {
                for (let k in a[i]) {
                    if (!this.$hasProp(k, a[i]) || a[i][k] == null) continue;
                    d && this.$isBaseObj(a[0][k]) && this.$isBaseObj(a[i][k])
                        ? this.$extend(d, a[0][k], a[i][k]) : (a[0][k] = a[i][k]);
                }
            }
            return a[0];
        },
        $fn(fn, o) { if (this.$isFunc(fn)) return fn.bind(o || this); },
        $afn(fn, a, o) {
            if (a == null) return this.$fn(fn, o);
            if (!this.$isFunc(fn)) return;
            a = !this.$isArr(a) ? [a] : a.slice();
            a.unshift(o || this);
            return fn.bind.apply(fn, a);
        },
        $call(fn, a, o) {
            a = a == null || this.$isArrLike(a) ? a : [a];
            o = o || this;
            let l = a != null && a.length;
            if (!l) return fn.call(o);
            if (l < 2) return fn.call(o, a[0]);
            if (l < 3) return fn.call(o, a[0], a[1]);
            if (l < 4) return fn.call(o, a[0], a[1], a[2]);
            return fn.apply(o, a);
        },
        $try(fn, a, o) {
            try { return this.$call(fn, a, o); } catch(e) { console.error(e.message, e.stack); }
        },
        $xtry(fn, a, o) { return this.$afn(this.$try, [fn, a, o]); },
        $timeout(fn, tm, a, o) {
            return (tm != null && setTimeout(this.$afn(fn, a, o), tm)) || (fn && clearTimeout(fn)) || this;
        },
        $proxy(fn, tm) {
            fn = this.$fn(fn);
            return {
                _fn(a, d) {
                    this.cancel();
                    let f = function() { a.length ? fn.apply(null, a) : fn(); };
                    this._r = d ? setTimeout(f, tm) : f();
                },
                call() { this._fn(arguments); },
                delay() { this._fn(arguments, 1); },
                cancel() { if (this._r) this._r = clearTimeout(this._r); },
            };
        },
        $def(v, o) { return this.$ext(v, o, 0); },
        $xdef(v, o) { return this.$ext(v, o, 0, 1); },
        $static(v, o) { return this.$ext(v, o, 1); },
        $ext(v, o, s, e) {
            for (let k in v) { if (this.$hasProp(k, v)) this.$getter(k, v[k], s, e, o); }
            return this;
        },
        $getter(k, v, s, e, o) {
            o = o || this;
            if (!s && k[0] === '_') k = k.substring(1);
            if (!s) o['_' + k] = v;
            if (s || (e && o[k] == null)) Object.defineProperty(o, k, s ? {value: v} : {get() { return this['_' + k]; }});
            return this;
        },
        $hasElem(id) { return !!document.getElementById(id); },
        $makeElem(tag, opt) {
            let $el = document.createElement(tag);
            if (opt) for (let k in opt) { $el[k] = opt[k]; }
            return $el;
        },
        $loadJs(src, opt) {
            opt = this.$assign(opt || {}, {src, type: 'text/javascript', 'async': true});
            document.getElementsByTagName('body')[0].appendChild(this.$makeElem('script', opt));
            return this;
        },
        $loadCss(href, opt) {
            opt = this.$assign(opt || {}, {href, type: 'text/css', rel: 'stylesheet', 'async': true});
            document.getElementsByTagName('head')[0].appendChild(this.$makeElem('link', opt));
            return this;
        },
        $load(css, opt) {
            opt = this.$assign(opt || {}, {innerHTML: css, type: 'text/css'});
            document.getElementsByTagName('head')[0].appendChild(this.$makeElem('style', opt));
            return this;
        }
    };
    
    
    class LevelUpCore {
        destroy() { for (let k in this) { if (this.$hasProp(k)) delete this[k]; } }
    }
    LU.$extend(LevelUpCore.prototype, LU);
    frappe.LevelUpCore = LevelUpCore;
    
    
    class LevelUpBase extends LevelUpCore {
        constructor(mod, key, doc, ns, prod) {
            super();
            this._mod = mod;
            this._key = key;
            this._tmp = '_' + this._key;
            this._doc = new RegExp('^' + doc);
            this._real = this._key + '_';
            this._pfx = '[' + this._key.toUpperCase() + ']';
            this._ns = ns + (!ns.endsWith('.') ? '.' : '');
            this._prod = prod;
            this._events = {
                list: {},
                real: {},
                once: 'ready page_change page_pop page_clean destroy after_destroy'.split(' ')
            };
        }
        get module() { return this._mod; }
        get key() { return this._key; }
        $alert(t, m, i, x) {
            m == null && (m = t) && (t = this._mod);
            t = this.$assign({title: t, indicator: i}, this.$isBaseObj(m) ? m : {message: m});
            this.call('on_alert', t, x);
            (x === 'fatal' && (this._err = 1) ? frappe.throw : frappe.msgprint)(t);
            return this;
        }
        debug(t, m) { return this._prod ? this : this.$alert(t, m, 'gray', 'debug'); }
        log(t, m) { return this._prod ? this : this.$alert(t, m, 'cyan', 'log'); }
        info(t, m) { return this.$alert(t, m, 'light-blue', 'info'); }
        warn(t, m) { return this.$alert(t, m, 'orange', 'warn'); }
        error(t, m) { return this.$alert(t, m, 'red', 'error'); }
        fatal(t, m) { return this.$alert(t, m, 'red', 'fatal'); }
        $toast(m, i) { frappe.show_alert({message: m, indicator: i}); return this; }
        success_(m) { return this.$toast(m, 'green'); }
        info_(m) { return this.$toast(m, 'blue'); }
        warn_(m) { return this.$toast(m, 'orange'); }
        error_(m) { return this.$toast(m, 'red'); }
        $console(fn, a) {
            if (this._prod) return this;
            !this.$isStr(a[0]) ? Array.prototype.unshift.call(a, this._pfx)
                : (a[0] = (this._pfx + ' ' + a[0]).trim());
            (console[fn] || console.log).apply(null, a);
            return this;
        }
        _debug() { return this.$console('debug', arguments); }
        _log() { return this.$console('log', arguments); }
        _info() { return this.$console('info', arguments); }
        _warn() { return this.$console('warn', arguments); }
        _error() { return this.$console('error', arguments); }
        ajax(u, o, s, f) {
            o = this.$extend(1, {
                url: u, method: 'GET', cache: false, 'async': true, crossDomain: true,
                headers: {'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
                success: this.$fn(s),
                error: this.$fn(function(r, t) {
                    r = (this.$isStrVal(r) && __(r)) || (this.$isStrVal(t) && __(t))
                        || __('The ajax request sent raised an error.');
                    (f = this.$fn(f)) ? f({message: r}) : this._error(r);
                })
            }, o);
            if (o.contentType == null)
                o.contentType = 'application/' + (o.method == 'post' ? 'json' : 'x-www-form-urlencoded') + '; charset=utf-8';
            this.call('on_ajax', o);
            try { $.ajax(o); } catch(e) {
                (f = this.$fn(f)) ? f(e) : this._error(e.message);
                if (this._err) throw e;
            } finally { this._err = 0; }
            return this;
        }
        get_method(v) { return this._ns + v; }
        request(m, a, s, f) {
            let d = {
                method: m.includes('.') ? m : this.get_method(m),
                callback: this.$fn(function(r) {
                    r = (this.$isBaseObj(r) && r.message) || r;
                    if (!this.$isBaseObj(r) || !r.error) return (s = this.$fn(s)) && s(r);
                    let x = this.$isArrVal(r.list);
                    if (x) r = this.$map(r.list, function(v) { return __(v); });
                    else r = this.$isBaseObj(r) && ((this.$isStrVal(r.message) && __(r.message))
                        || (this.$isStrVal(r.error) && __(r.error)))
                        || __('The request sent returned an invalid response.');
                    (f = this.$fn(f)) ? f({message: x ? r.join('\n') : r, self: true}) : this._error(r);
                }),
                error: this.$fn(function(r, t) {
                    r = (this.$isStrVal(r) && __(r)) || (this.$isStrVal(t) && __(t))
                        || __('The request sent raised an error.');
                    (f = this.$fn(f)) ? f({message: r}) : this._error(r);
                })
            };
            !this.$isBaseObj(a) && (a = {});
            this.call('on_request', a);
            !this.$isEmptyObj(a) && this.$assign(d, {type: 'POST', args: a});
            try { frappe.call(d); } catch(e) {
                (f = this.$fn(f)) ? f(e) : this._error(e.message);
                if (this._err) throw e;
            } finally { this._err = 0; }
            return this;
        }
        on(e, fn)  { return this._on(e, fn); }
        xon(e, fn)  { return this._on(e, fn, 0, 1); }
        once(e, fn) { return this._on(e, fn, 1); }
        xonce(e, fn) { return this._on(e, fn, 1, 1); }
        real(e, fn, n) { return this._on(e, fn, n, 0, 1); }
        xreal(e, fn, n) { return this._on(e, fn, n, 1, 1); }
        off(e, fn, rl) {
            if (e == null) return this._off();
            if (this.$isBoolLike(e)) return this._off(0, 1);
            fn = this.$isFunc(fn) && fn;
            e = e.split(' ');
            for (let i = 0, l = e.length, ev; i < l; i++)
                (ev = (rl ? this._real : '') + e[i]) && this._events.list[ev] && this._off(ev, fn);
            return this;
        }
        emit(e) {
            e = e.split(' ');
            for (let a = this.$toArr(arguments, 1), p = Promise.resolve(), i = 0, l = e.length; i < l; i++)
                this._events.list[e[i]] && this._emit(e[i], a, p);
            return this;
        }
        call(e) {
            e = e.split(' ');
            for (let a = this.$toArr(arguments, 1), i = 0, l = e.length; i < l; i++)
                this._events.list[e[i]] && this._emit(e[i], a);
            return this;
        }
        _on(ev, fn, o, s, r) {
            ev = ev.split(' ');
            fn = this.$fn(fn);
            let rd;
            for (let es = this._events, i = 0, l = ev.length, e; i < l; i++) {
                e = (r ? this._real : '') + ev[i];
                e === es.once[0] && this._is_ready && (rd = es.once[0]);
                es.once.includes(e) && (o = 1);
                !es.list[e] && (es.list[e] = []) && (!r || frappe.realtime.on(e, (es.real[e] = this._rfn(e))));
                es.list[e].push({f: fn, o, s});
            }
            return rd ? this.emit(rd) : this;
        }
        _rfn(e) {
            return this.$fn(function(r) {
                (r = (this.$isBaseObj(r) && r.message) || r) && this._emit(e, r != null ? [r] : r, Promise.wait(300));
            });
        }
        _off(e, fn) {
            if (e && fn) this._del(e, fn);
            else if (!e) for (let ev in this._events.list) { (fn ? this._off : this._del)(ev, fn); }
            else {
                let es = this._events;
                es.real[e] && frappe.realtime.off(e, es.real[e]);
                delete es.list[e];
                delete es.real[e];
            }
            return this;
        }
        _del(e, fn) {
            let ev = this._events.list[e].slice(), ret = [];
            for (let x = 0, i = 0, l = ev.length; i < l; i++)
                (fn ? ev[i].f !== fn : ev[i].s) && (ret[x++] = ev[i]);
            !ret.length ? this._off(e) : (this._events.list[e] = ret);
        }
        _emit(e, a, p) {
            let ev = this._events.list[e].slice(), ret = [];
            p && p.catch(this.$fn(function(z) { this._error('Events emit', e, a, z.message); }));
            for (let x = 0, i = 0, l = ev.length; i < l; i++) {
                p ? p.then(this.$xtry(ev[i].f, a)) : this.$try(ev[i].f, a);
                !ev[i].o && (ret[x++] = ev[i]);
            }
            !ret.length ? this._off(e) : (this._events.list[e] = ret);
        }
    }
    
    
    var LUR = {
        on(o) {
            for (let k = ['router', 'route'], i = 0, l = k.length; i < l; i++)
                frappe[k[i]] && (o._router.obj = frappe[k[i]]) && (i < 1 || (o._router.old = 1));
            this._reg(o, 'on');
            this.get(o);
        },
        off(o) { this._reg(o, 'off') && (o._router.obj = o._router.old = null); },
        get(o) {
            let d = ['app'], v;
            if (!o._router.val) o._router.val = d;
            try { if (o._router.obj) v = !o._router.old ? frappe.get_route() : o._router.obj.parse(); } catch(_) {}
            if (!LU.$isArrVal(v)) v = d;
            else v[0] = v[0].toLowerCase();
            let f;
            if (o._router.val.length !== v.length) f = d;
            else f = LU.$filter(v, function(z, i) {
                return o._router.val.indexOf(z) !== i;
            });
            if (f.length) o._router.val = v;
            return f.length > 0;
        },
        _reg(o, a) {
            if (!o._router.obj || !o._router.obj[a]) return;
            o._router.obj[a]('change', o._win.e.change);
        },
    },
    LUF = {
        has_flow(f) { try { return f && !f.is_new() && f.states && f.states.get_state(); } catch(_) {} },
        is_field(f) { return f && f.df && !/^((Tab|Section|Column) Break|Table)$/.test(f.df.fieldtype); },
        is_table(f) { return f && f.df && f.df.fieldtype === 'Table'; },
        get_field(f, k, g, r, c, m) {
            return ((f = f.get_field(k)) && (!g || ((f = f.grid)
                && (r == null || ((f = f.get_row(r)) && (!m || (f = f.grid_form))))))
                && (!c || (f = r != null && m ? f.fields_dict[c] : f.get_field(c))) && f) || null;
        },
        reload_field(f, k, r, c) {
            if (r == null && !c) {
                if (LU.$isStrVal(k)) k = [k];
                if (LU.$isArrVal(k)) {
                    for (let i = 0, l = k.length; i < l; i++)
                        f.refresh_field && f.refresh_field(k[i]);
                }
                return;
            }
            if (r != null && !c) {
                if (!LU.$isArr(r)) r = [r];
                if (!LU.$isArrVal(r)) return;
                f = this.get_field(f, k, 1);
                for (let i = 0, l = r.length; i < l; i++) { f && f.refresh_row(r[i]); }
                return;
            }
            if (LU.$isStrVal(c)) c = [c];
            else if (!LU.$isArrVal(c)) return;
            if (r != null && c) {
                let g = (f = this.get_field(f, k, 1, r)) && f.grid_form && f.grid_form.refresh_field;
                for (let i = 0, l = c.length, x; i < l; i++) {
                    (x = f && f.on_grid_fields_dict[c[i]]) && x.refresh && x.refresh();
                    g && g(c[i]);
                }
                return;
            }
            if (!(f = this.get_field(f, k, 1)) || !LU.$isArrVal(f.grid_rows)) return;
            for (let i = 0, l = f.grid_rows, cl = c.length, g; i < l; i++) {
                r = f.grid_rows[i];
                (g = r && r.grid_form) && (g = g.refresh_field);
                for (let x = 0, z; x < cl; x++) {
                    (z = r && r.on_grid_fields_dict[c[x]]) && z.refresh && z.refresh();
                    g && g(c[x]);
                }
            }
        },
        field_prop(f, k, g, r, c, p, v, t) {
            if (LU.$isBaseObj(k)) for (let x in k) { this.field_prop(f, x, g, r, c, k[x], null, t); }
            else if (LU.$isBaseObj(c)) for (let x in c) { this.field_prop(f, k, g, r, x, c[x], null, t); }
            else {
                (g || r != null) && (t || (f = this.get_field(f, k, g, r))) && (k = c);
                let m = r != null ? 'set_field_property' : (g ? 'update_docfield_property' : 'set_df_property');
                if (!LU.$isBaseObj(p)) f[m](k, p, v);
                else for (let x in p) { f[m](k, x, p[x]); }
                g && r == null && f.debounced_refresh();
            }
        },
        toggle_field(f, k, g, r, c, e, i) {
            k && (f = this.get_field(f, k, g, r, c));
            e = e ? 0 : 1;
            if ((k && (!f || !f.df)) || cint(f.df.hidden) || (i && f.df._ignore) || cint(f.df.read_only) === e) return;
            this.field_prop(f, k, g, r, c, 'read_only', e, 1);
            this._toggle_translatable(f, e ? 1 : 0);
        },
        get_field_desc(f, k, g, r, c, b, t) {
            !t && (f = this.get_field(f, k, g, r, c));
            return cstr(f && f.df && ((b && f.df._description) || (!b && f.df.description) || ''));
        },
        field_desc(f, k, g, r, c, m, t) {
            let x = 0;
            !t && (f = this.get_field(f, k, g, r, c));
            f.df._description = f.df._description || this.get_field_desc(f, k, g, r, c, 0, 1);
            !LU.$isStrVal(m) && (m = '');
            if (m.length && f.set_new_description) ++x && f.set_new_description(m);
            else if (f.set_description) {
                !m.length && ((m = f.df._description || '') || delete f.df._description);
                ++x && f.set_description(m);
            }
            f.toggle_description && f.toggle_description(m.length > 0);
            return x;
        },
        field_status(f, k, g, r, c, m) {
            let v = LU.$isStrVal(m), tf = this.get_field(f, k, g, r, c), x = 0;
            if ((!v && tf.df.invalid) || (v && !tf.df.invalid))
                ++x && ((tf.df.invalid = v ? 1 : 0) || 1) && tf.set_invalid && tf.set_invalid();
            this.field_desc(tf, k, g, r, c, m, 1) && x++;
            x && this.reload_field(f, k, r, c);
        },
        _toggle_translatable(f, s) {
            f.df.translatable && f.$wrapper
            && (f = f.$wrapper.find('.clearfix .btn-translation')) && f.hidden(!s);
        },
    },
    LUT = {
        setup_table(f, k) {
            cint(k.df.read_only) && (k.df._ignore = 1);
            for (let ds = this._docfields(this._grid(f, k.df.fieldname)), i = 0, l = ds.length, d; i < l; i++)
                (d = ds[i]) && cint(d.read_only) && (d._ignore = 1);
        },
        toggle_table(f, k, e, o, i) {
            let tf = this._grid(f, k, i), x = !e || tf._;
            x && (!o || !o.add) && this.toggle_table_add(tf, 0, e);
            x && (!o || !o.del) && this.toggle_table_del(tf, 0, e);
            x && (!o || !o.edit) && this.toggle_table_edit(tf, 0, o && o.keep, e);
            x && (!o || !o.sort) && this.toggle_table_sort(tf, 0, e);
            LUF.reload_field(f, k);
            x && (!o || !o.del) && this.toggle_table_check(tf, 0, e);
            e && delete tf._;
        },
        toggle_table_add(f, k, e) {
            k && (f = this._grid(f, k));
            if (e) {
                (!f._ || f._.add != null) && (f.df.cannot_add_rows = f._ ? f._.add : false);
                k && f._ && delete f._.add;
            } else {
                (f._ = f._ || {}) && (f._.add = f.df.cannot_add_rows);
                f.df.cannot_add_rows = true;
            }
            return 1;
        },
        toggle_table_del(f, k, e) {
            k && (f = this._grid(f, k));
            if (e) {
                (!f._ || f._.del != null) && (f.df.cannot_delete_rows = f._ ? f._.del : false);
                k && f._ && delete f._.del;
            } else {
                (f._ = f._ || {}) && (f._.del = f.df.cannot_delete_rows);
                f.df.cannot_delete_rows = true;
            }
            return 1;
        },
        toggle_table_edit(f, k, g, e) {
            k && (f = this._grid(f, k));
            if (e) {
                (!f._ || f._.edit != null) && (f.df.in_place_edit = f._ ? f._.edit : true);
                f._ && f._.grid != null && f.meta && (f.meta.editable_grid = f._.grid);
                (!f._ || f._.static != null) && (f.static_rows = f._ ? f._.static : false);
                if (f._ && f._.read && f._.read.length) {
                    for (let ds = this._docfields(f), i = 0, l = ds.length, d; i < l; i++)
                        (d = ds[i]) && !d._ignore && f._.read.includes(d.fieldname) && (d.read_only = 0);
                }
                if (k && f._) for (let x = ['edit', 'grid', 'static', 'read'], i = 0; i < 4; i++) { delete f._[k[x]]; }
                return 1;
            }
            (f._ = f._ || {}) && (f._.edit = f.df.in_place_edit);
            f.df.in_place_edit = false;
            f.meta && (f._.grid = f.meta.editable_grid);
            f.meta && (f.meta.editable_grid = false);
            f._.static = f.static_rows;
            f.static_rows = true;
            f._.read = [];
            for (let ds = this._docfields(f), i = 0, x = 0, l = ds.length, d; i < l; i++)
                (d = ds[i]) && !d._ignore && !cint(d.read_only) && (!g || !g.includes(d.fieldname))
                && (d.read_only = 1) && (f._.read[x++] = d.fieldname);
            return 1;
        },
        toggle_table_sort(f, k, e) {
            k && (f = this._grid(f, k));
            if (e) {
                (!f._ || f._.sort != null) && (f.sortable_status = f._ ? f._.sort : true);
                k && f._ && delete f._.sort;
            } else {
                (f._ = f._ || {}) && (f._.sort = f.sortable_status);
                f.sortable_status = false;
            }
            return 1;
        },
        toggle_table_check(f, k, e) {
            k && (f = this._grid(f, k));
            if (e) {
                (!f._ || f._.check) && f.toggle_checkboxes(1);
                k && f._ && delete f._.check;
            } else {
                (f._ = f._ || {}) && (f._.check = 1) && f.toggle_checkboxes(0);
            }
            return 1;
        },
        _grid(f, k, i) {
            return ((!k && (f = f.grid)) || (f = LUF.get_field(f, k, 1))) && !cint(f.df.hidden) && (!i || !f.df._ignore) && f;
        },
        _docfields(f) {
            let ds = [];
            if (LU.$isArrVal(f.grid_rows)) {
                for (let i = 0, l = f.grid_rows.length, r; i < l; i++)
                    (r = f.grid_rows[i]) && LU.$isArrVal(r.docfields) && ds.push.apply(ds, r.docfields);
            }
            LU.$isArrVal(f.docfields) && ds.push.apply(ds, f.docfields);
            return ds;
        },
    };
    
    
    class LevelUp extends LevelUpBase {
        constructor(mod, key, doc, ns, prod) {
            super(mod, key, doc, ns, prod);
            this.$xdef({is_enabled: true});
            this._router = {obj: null, old: 0, val: ['app']};
            this._win = {
                e: {
                    unload: this.$fn(this.destroy),
                    popstate: this.$fn(function() { !this._win.c && this._win.fn.delay(); }),
                    change: this.$fn(function() { !this._win.c && this._win.fn.call(1); }),
                },
                c: 0,
                fn: this.$proxy(function(n) {
                    if (this._win.c || !LUR.get(this)) return;
                    this._win.c++;
                    this.emit((n ? 'page_change' : 'page_pop') + ' page_clean');
                    this.$timeout(function() { this._win.c--; }, n ? 2000 : 1200);
                }, 200),
            };
            addEventListener('beforeunload', this._win.e.unload);
            addEventListener('popstate', this._win.e.popstate);
            LUR.on(this);
        }
        options(opts) { return this.$static(opts); }
        destroy() {
            this._win.fn.cancel();
            LUR.off(this);
            removeEventListener('popstate', this._win.e.popstate);
            removeEventListener('beforeunload', this._win.e.unload);
            this.emit('page_clean destroy after_destroy').off(1);
            super.destroy();
        }
        route(i) { return this._router.val[i] || this._router.val[0]; }
        get is_list() { return this.route(0) === 'list'; }
        get is_tree() { return this.route(0) === 'tree'; }
        get is_form() { return this.route(0) === 'form'; }
        get is_self() { return this._doc.test(this.route(1)); }
        is_doctype(v) { return this.route(1) === v; }
        _is_self_view(f) { return this._doc.test((f && f.doctype) || this.route(1)); }
        get_list(f) { f = f || cur_list; if (this.$isObjLike(f)) return f; }
        get_tree(f) { f = f || cur_tree; if (this.$isObjLike(f)) return f; }
        get_form(f) { f = f || cur_frm; if (this.$isObjLike(f)) return f; }
        get app_disabled_note() { return __('{0} app is disabled.', [this._mod]); }
        setup_list(f) {
            if (!this.is_list || !(f = this.get_list(f)) || !this._is_self_view(f)) return this;
            let n = !f[this._tmp];
            if (this._is_enabled) this.enable_list(f);
            else this.disable_list(f, this.app_disabled_note);
            n && this.off('page_clean').once('page_clean', function() { this.enable_list(f); });
            return this;
        }
        enable_list(f) {
            if (!(f = this.get_list(f)) || (f[this._tmp] && !f[this._tmp].disabled)) return this;
            let k = 'toggle_actions_menu_button';
            f[this._tmp] && f[this._tmp][k] && (f[k] = f[this._tmp][k]);
            f.page.clear_inner_toolbar();
            f.set_primary_action();
            delete f[this._tmp];
            return this;
        }
        disable_list(f, m) {
            if (!(f = this.get_list(f)) || (f[this._tmp] && f[this._tmp].disabled)) return this;
            f.page.hide_actions_menu();
            f.page.clear_primary_action();
            f.page.clear_inner_toolbar();
            m && f.page.add_inner_message(m).removeClass('text-muted').addClass('text-danger');
            let k = 'toggle_actions_menu_button';
            !f[this._tmp] && (f[this._tmp] = {});
            (f[this._tmp][k] = f[k]) && (f[k] = function() {}) && (f[this._tmp].disabled = 1);
            return this;
        }
        setup_tree(f) {
            if (!this.is_tree || !(f = this.get_tree(f)) || !this._is_self_view(f)) return this;
            let n = !f[this._tmp];
            if (this._is_enabled) this.enable_tree(f);
            else this.disable_tree(f, this.app_disabled_note);
            n && this.$xdef({tree: f}).off('page_clean').once('page_clean', function() { this.$xdef({tree: null}).enable_tree(f); });
            return this;
        }
        enable_tree(f) {
            if (!(f = this.get_tree(f)) || (f[this._tmp] && !f[this._tmp].disabled)) return this;
            let k = 'can_create';
            f[this._tmp] && f[this._tmp][k] && (f[k] = f[this._tmp][k]);
            f.page.clear_inner_toolbar();
            f.set_primary_action();
            delete f[this._tmp];
            f.refresh();
            return this;
        }
        disable_tree(f, m) {
            if (!(f = this.get_tree(f)) || (f[this._tmp] && f[this._tmp].disabled)) return this;
            f.page.hide_actions_menu();
            f.page.clear_primary_action();
            f.page.clear_inner_toolbar();
            m && f.page.add_inner_message(m).removeClass('text-muted').addClass('text-danger');
            let k = 'can_create';
            !f[this._tmp] && (f[this._tmp] = {});
            (f[this._tmp][k] = f[k]) && (f[k] = false) && (f[this._tmp].disabled = 1);
            f.refresh();
            return this;
        }
        setup_form(f) {
            if (!this.is_form || !(f = this.get_form(f)) || !this._is_self_view(f)) return this;
            let n = !f[this._tmp];
            if (n && this.$isArrVal(f.fields))
                try {
                    for (let i = 0, l = f.fields.length, c; i < l; i++) {
                        if (!(c = f.fields[i])) continue;
                        if (LUF.is_table(c)) LUT.setup_table(f, c);
                        else if (LUF.is_field(c) && cint(c.df.read_only)) c.df._ignore = 0;
                    }
                } catch(_) {}
            if (this._is_enabled) this.enable_form(f);
            else this.disable_form(f, this.app_disabled_note);
            n && this.off('page_clean').once('page_clean', function() { this.enable_form(f); });
            return this;
        }
        enable_form(f) {
            if (!(f = this.get_form(f)) || (f[this._tmp] && !f[this._tmp].disabled)) return this;
            try {
                if (this.$isArrVal(f.fields))
                    for (let i = 0, l = f.fields.length, c; i < l; i++) {
                        if (!(c = f.fields[i]) || !c.df.fieldname) continue;
                        if (LUF.is_table(c)) LUT.toggle_table(c, 0, 1, 0, 1);
                        else if (LUF.is_field(c)) LUF.toggle_field(c, 0, 0, null, 0, 1, 1);
                    }
                LUF.has_flow(f) ? f.page.show_actions_menu() : f.enable_save();
                f.set_intro();
            } catch(e) { this._error('Enable form', e.message, e.stack); }
            finally {
                delete f[this._tmp];
                this.emit('form_enabled', f);
            }
            return this;
        }
        disable_form(f, m, r) {
            if (!(f = this.get_form(f)) || (f[this._tmp] && f[this._tmp].disabled)) return this;
            try {
                if (this.$isArrVal(f.fields))
                    for (let i = 0, l = f.fields.length, c; i < l; i++) {
                        if (!(c = f.fields[i]) || !c.df.fieldname) continue;
                        if (LUF.is_table(c)) LUT.toggle_table(c, 0, 0, 0, 1);
                        else if (LUF.is_field(c)) LUF.toggle_field(c, 0, 0, null, 0, 0, 1);
                    }
                LUF.has_flow(f) ? f.page.hide_actions_menu() : f.disable_save();
                f.set_intro(m, r || 'red');
            } catch(e) { this._error('Disable form', e.message, e.stack); }
            finally {
                (f[this._tmp] || (f[this._tmp] = {})) && (f[this._tmp].disabled = 1);
                this.emit('form_disabled', f);
            }
            return this;
        }
        get_field(f, k) { if ((f = this.get_form(f))) return LUF.get_field(f, k); }
        get_grid(f, k) { if ((f = this.get_form(f))) return LUF.get_field(f, k, 1); }
        get_tfield(f, k, c) { if ((f = this.get_form(f))) return LUF.get_field(f, k, 1, null, c); }
        get_row(f, k, r) { if ((f = this.get_form(f))) return LUF.get_field(f, k, 1, r); }
        get_rfield(f, k, r, c) { if ((f = this.get_form(f))) return LUF.get_field(f, k, 1, r, c); }
        get_r(f, k, r) { if ((f = this.get_form(f))) return LUF.get_field(f, k, 1, r, 0, 1); }
        get_rmfield(f, k, r, c) { if ((f = this.get_form(f))) return LUF.get_field(f, k, 1, r, c, 1); }
        reload_field(f) {
            arguments.length > 1 && (f = this.get_form(f)) && LUF.reload_field(f, this.$toArr(arguments, 1));
            return this;
        }
        reload_tfield(f, k) {
            arguments.length > 2 && (f = this.get_form(f)) && LUF.reload_field(f, k, null, this.$toArr(arguments, 2));
            return this;
        }
        reload_row(f, k) {
            arguments.length > 2 && (f = this.get_form(f)) && LUF.reload_field(f, k, this.$toArr(arguments, 2));
            return this;
        }
        reload_rfield(f, k, r) {
            arguments.length > 3 && (f = this.get_form(f)) && LUF.reload_field(f, k, r, this.$toArr(arguments, 3));
            return this;
        }
        field_prop(f, k, p, v) {
            (f = this.get_form(f)) && LUF.field_prop(f, k, 0, null, 0, p, v);
            return this;
        }
        tfield_prop(f, k, c, p, v) {
            (f = this.get_form(f)) && LUF.field_prop(f, k, 1, null, c, p, v);
            return this;
        }
        rfield_prop(f, k, r, c, p, v) {
            (f = this.get_form(f)) && LUF.field_prop(f, k, 1, r, c, p, v);
            return this;
        }
        toggle_field(f, k, e) {
            (f = this.get_form(f)) && LUF.toggle_field(f, k, 0, null, 0, e);
            return this;
        }
        toggle_table(f, k, e) {
            (f = this.get_form(f)) && LUT.toggle_table(f, k, e ? 1 : 0);
            return this;
        }
        toggle_table_add(f, k, e) {
            (f = this.get_form(f)) && LUT.toggle_table_add(f, k, e ? 1 : 0) && LUF.reload_field(f, k);
            return this;
        }
        toggle_table_edit(f, k, i, e) {
            if (!this.$isArrVal(i)) {
                if (e == null) e = i;
                i = null;
            }
            (f = this.get_form(f)) && LUT.toggle_table_edit(f, k, i, e ? 1 : 0) && LUF.reload_field(f, k);
            return this;
        }
        toggle_table_del(f, k, e) {
            (f = this.get_form(f)) && LUT.toggle_table_del(f, k, e ? 1 : 0) && LUF.reload_field(f, k);
            return this;
        }
        toggle_table_sort(f, k, e) {
            (f = this.get_form(f)) && LUT.toggle_table_sort(f, k, e ? 1 : 0) && LUF.reload_field(f, k);
            return this;
        }
        toggle_table_check(f, k, e) {
            (f = this.get_form(f)) && LUT.toggle_table_check(f, k, e ? 1 : 0) && LUF.reload_field(f, k);
            return this;
        }
        toggle_tfield(f, k, c, e) {
            (f = this.get_form(f)) && LUF.toggle_field(f, k, 1, null, c, e);
            return this;
        }
        toggle_rfield(f, k, r, c, e) {
            (f = this.get_form(f)) && LUF.toggle_field(f, k, 1, r, c, e);
            return this;
        }
        field_view(f, k, s) { return this.field_prop(f, k, 'hidden', s ? 0 : 1); }
        tfield_view(f, k, c, s) { return this.tfield_prop(f, k, c, 'hidden', s ? 0 : 1); }
        rfield_view(f, k, r, c, s) { return this.rfield_prop(f, k, r, c, 'hidden', s ? 0 : 1); }
        field_desc(f, k, m) {
            (f = this.get_form(f)) && LUF.field_desc(f, k, 0, null, 0, m);
            return this;
        }
        tfield_desc(f, k, c, m) {
            (f = this.get_form(f)) && LUF.field_desc(f, k, 1, null, c, m);
            return this;
        }
        rfield_desc(f, k, r, c, m) {
            (f = this.get_form(f)) && LUF.field_desc(f, k, 1, r, c, m);
            return this;
        }
        get_field_desc(f, k, b) {
            return ((f = this.get_form(f)) && LUF.get_field_desc(f, k, 0, null, 0, b)) || '';
        }
        get_tfield_desc(f, k, c, b) {
            return ((f = this.get_form(f)) && LUF.get_field_desc(f, k, 1, null, c, b)) || '';
        }
        get_rfield_desc(f, k, r, c, b) {
            return ((f = this.get_form(f)) && LUF.get_field_desc(f, k, 1, r, c, b)) || '';
        }
        field_status(f, k, m) {
            (f = this.get_form(f)) && LUF.field_status(f, k, 0, null, 0, m);
            return this;
        }
        tfield_status(f, k, c, m) {
            (f = this.get_form(f)) && LUF.field_status(f, k, 1, null, c, m);
            return this;
        }
        rfield_status(f, k, r, c, m) {
            (f = this.get_form(f)) && LUF.field_status(f, k, 1, r, c, m);
            return this;
        }
    }
    
    
    class LevelUpCache extends LevelUpCore {
        constructor(pfx) {
            super();
            this._pfx = this.$isStrVal(pfx) ? pfx : 'lu_';
        }
        has(k) { return this._get(k) != null; }
        get(k) { return (k = this._get(k)) && k.___ != null ? k.___ : k; }
        pop(k) {
            let v = this.get(k);
            v != null && this.del(k);
            return v;
        }
        set(k, v, t) {
            if (!this.$isStrVal(k)) return this;
            v = {___: v};
            if (this.$isNum(t) && t > 0)
                v.e = (new Date()).getTime() + (t * 1000);
            try { localStorage.setItem(this._pfx + k, this.$toJson(v)); } catch(_) {}
            return this;
        }
        del(k) {
            if (this.$isStrVal(k))
                try { localStorage.removeItem(this._pfx + k); } catch(_) {}
            return this;
        }
        _get(k) {
            if (!this.$isStrVal(k)) return;
            let v;
            try { v = sessionStorage.getItem(this._pfx + k); } catch(_) { return; }
            if (v == null) return;
            v = this.$parseJson(v);
            if (v == null) return;
            if (v.___ != null) {
                if (v.e != null && v.e < (new Date()).getTime()) {
                    this.del(k);
                    return;
                }
                v = v.___;
            }
            return v;
        }
    }
    LevelUp.prototype.cache = function() { return this._cache || (this._cache = new LevelUpCache(this._real)); };
    
    
    class LevelUpTable {
        constructor(n) {
            this._c = [];
            this._n = (n || 0) + 1;
            for (let x = 0; x < this._n; x++) { this._c[x] = []; }
        }
        get length() { return this._c[0].length; }
        col(i) { return this._c[i || 0]; }
        idx(v, i) { return this.col(i).indexOf(v); }
        has(v, i) { return (v = this.idx(v, i)) >= 0 && this.col(i)[v] != null; }
        add() {
            let a = arguments, i = this.idx(a[0]);
            if (i < 0) for (let x = 0; x < this._n; x++) { this._c[x].push(a[x]); }
            else for (let x = 1; x < this._n; x++)
                (a[x] != null || this._c[x][i] == null) && (this._c[x][i] = a[x]);
            return this;
        }
        del(v, i) {
            if ((i = this.idx(v, i)) >= 0)
                for (let x = 0; x < this._n; x++) { this._c[x].splice(i, 1); }
            return this;
        }
        row(v, i) {
            if ((i = this.idx(v, i)) < 0) return;
            let r = [];
            for (let x = 0; x < this._n; x++) { r[x] = this._c[x][i]; }
            return r;
        }
        clear() {
            for (let x = 0; x < this._n; x++) { this._c[x] = []; }
            return this;
        }
    }
    LevelUp.prototype.table = function(cols) { return new LevelUpTable(cols); };
    
    
    class Gocardless extends LevelUp {
        constructor() {
            super(
                __("ERPNext Gocardless Bank"),
                "gocardless", "Gocardless",
                "erpnext_gocardless_bank.libs", 0
            );
            
            this.$xdef({
                is_ready: false,
                is_enabled: false,
                is_debug: false,
            });
            this._bank_link = {};
            this.request(
                'get_settings', null, this._init,
                function() { this._error('Getting settings failed.'); }
            );
        }
        _init(opts) {
            this._is_ready = true;
            opts && this.$xdef(opts);
            this._prod = !this._is_debug;
            this.xreal('status_changed', function(ret) {
                let old = this._is_enabled;
                ret && this.$xdef(ret);
                this._prod = !this._is_debug;
                this._is_enabled !== old && this.emit('changed');
            })
            .emit('ready');
        }
        connect_to_bank(company, id, transaction_days, docname, success, error) {
            transaction_days = cint(transaction_days || 0);
            var key = [company, id, transaction_days];
            if (docname) key.push(docname);
            key = key.join('-');
            if (this._bank_link[key]) {
                let data = this._bank_link[key];
                this.$isFunc(success) && success(
                    data.link,
                    data.ref_id,
                    data.id,
                    data.access_valid_for_days
                );
                return;
            }
            
            var ref_id = '_' + Math.random().toString(36).substr(2);
            let args = {
                company,
                bank_id: id,
                ref_id: ref_id,
                transaction_days: transaction_days,
            };
            if (docname) args.docname = docname;
            this.request(
                'get_bank_link',
                args,
                function(ret) {
                    if (!this.$isDataObj(ret))
                        return this.error('Bank link received is invalid.');
                    
                    ret.access_valid_for_days = cint(ret.access_valid_for_days || 180);
                    this._bank_link[key] = ret;
                    this._bank_link[key].ref_id = ref_id;
                    this.$isFunc(success) && success(
                        res.link,
                        ref_id,
                        res.id,
                        res.access_valid_for_days
                    );
                },
                function(e) {
                    this.error(e.self ? e.message : __('Unable to get Gocardless bank link data.'));
                    this.$isFunc(error) && error(e);
                }
            );
        }
    }
    
    
    frappe.gc = function() {
        if (!frappe.gc._) frappe.gc._ = new Gocardless();
        return frappe.gc._;
    };
    
    
    $(document).ready(function() {
        if (!frappe || typeof frappe !== 'object')
            throw new Error('Frappe framework is required.');
        let id = 'core-polyfill';
        function $onload() {
            Promise.wait = function(ms) { return new Promise(function(resolve) { setTimeout(resolve, ms); }); };
            Promise.prototype.timeout = function(ms) {
                return Promise.race([this, Promise.wait(ms).then(function() { throw new Error('Time out'); })]);
            };
        }
        if (
            LU.$isFunc(Promise) && LU.$isFunc(id.trim)
            && LU.$isFunc(id.includes) && LU.$isFunc(id.startsWith)
            && LU.$isFunc(id.endsWith) && LU.$isFunc([].includes)
            && LU.$isFunc(LU.$isFunc.bind)
        ) $onload();
        else if (LU.$hasElem(id)) $onload();
        else LU.$loadJs(
            'https://polyfill.io/v3/polyfill.min.js?features=String.prototype.trim%2CString.prototype.includes%2CString.prototype.startsWith%2CString.prototype.endsWith%2CArray.prototype.includes%2CFunction.prototype.bind%2CPromise',
            {id: id, onload: $onload}
        );
        $.fn.hidden = function(s) { return this.toggleClass('lu-hidden', !!s); };
        $.fn.isHidden = function() { return this.hasClass('lu-hidden'); };
        !LU.$hasElem('lu-style') && LU.$load('.lu-hidden { display: none; }', {id: 'lu-style'});
    });
}());