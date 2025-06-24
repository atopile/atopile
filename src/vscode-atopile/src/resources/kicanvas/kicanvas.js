var ps = Object.defineProperty;
var on = Object.getOwnPropertyDescriptor;
var l = (s, t) => ps(s, 'name', { value: t, configurable: !0 });
var P = (s, t, e, r) => {
    for (var i = r > 1 ? void 0 : r ? on(t, e) : t, n = s.length - 1, o; n >= 0; n--)
        (o = s[n]) && (i = (r ? o(t, e, i) : o(i)) || i);
    return r && i && ps(t, e, i), i;
};
function ue(s) {
    window.setTimeout(() => {
        s();
    }, 0);
}
l(ue, 'later');
var Me = class {
        static {
            l(this, 'DeferredPromise');
        }
        #e;
        #t;
        #r;
        #i;
        #s;
        constructor() {
            this.#e = new Promise((t, e) => {
                (this.#t = t), (this.#r = e);
            });
        }
        get rejected() {
            return this.#i === 1;
        }
        get resolved() {
            return this.#i === 0;
        }
        get settled() {
            return !!this.#i;
        }
        get value() {
            return this.#s;
        }
        then(t, e) {
            return this.#e.then(t, e);
        }
        resolve(t) {
            (this.#i = 0), (this.#s = t), this.#t(t);
        }
        reject(t) {
            (this.#i = 1), (this.#s = t), this.#r(t);
        }
    },
    fe = class extends Me {
        static {
            l(this, 'Barrier');
        }
        get isOpen() {
            return this.resolved && this.value === !0;
        }
        open() {
            this.resolve(!0);
        }
    };
function hs(s) {
    return s instanceof URL && (s = s.pathname), s.split('/').slice(0, -1).join('/');
}
l(hs, 'dirname');
function Xe(s) {
    return s instanceof URL && (s = s.pathname), s.split('/').at(-1);
}
l(Xe, 'basename');
function D3(s) {
    return s.split('.').at(-1) ?? '';
}
l(D3, 'extension');
function Gt(s) {
    let t, e;
    s instanceof File ? ((t = URL.createObjectURL(s)), (e = s.name)) : ((t = s.href), (e = Xe(t)));
    let r = document.createElement('a');
    (r.href = t),
        (r.download = e),
        (r.target = '_blank'),
        console.log(r),
        r.click(),
        s instanceof File && URL.revokeObjectURL(t);
}
l(Gt, 'initiate_download');
var it = class {
        static {
            l(this, 'VirtualFileSystem');
        }
        *list_matches(t) {
            for (let e of this.list()) e.match(t) && (yield e);
        }
        *list_ext(t) {
            t.startsWith('.') || (t = `.${t}`);
            for (let e of this.list()) e.endsWith(t) && (yield e);
        }
    },
    st = class extends it {
        constructor(e, r = null) {
            super();
            this.urls = new Map();
            this.resolver = r ?? this.#e;
            for (let i of e) this.#t(i);
        }
        static {
            l(this, 'FetchFileSystem');
        }
        #e(e) {
            return new URL(e, window.location.toString());
        }
        #t(e) {
            if (typeof e == 'string') {
                let r = this.urls.get(e);
                if (r) return r;
                {
                    let i = this.resolver(e),
                        n = Xe(i);
                    return this.urls.set(n, i), i;
                }
            }
            return e;
        }
        *list() {
            yield* this.urls.keys();
        }
        async has(e) {
            return Promise.resolve(this.urls.has(e));
        }
        async get(e) {
            let r = this.#t(e);
            if (!r) throw new Error(`File ${e} not found!`);
            let i = new Request(r, { method: 'GET' }),
                n = await fetch(i);
            if (!n.ok) throw new Error(`Unable to load ${r}: ${n.status} ${n.statusText}`);
            let o = await n.blob();
            return new File([o], e);
        }
        async download(e) {
            Gt(await this.get(e));
        }
    },
    Y2 = class s extends it {
        constructor(e) {
            super();
            this.items = e;
        }
        static {
            l(this, 'DragAndDropFileSystem');
        }
        static async fromDataTransfer(e) {
            let r = [];
            for (let i = 0; i < e.items.length; i++) {
                let n = e.items[i]?.webkitGetAsEntry();
                n && r.push(n);
            }
            if (r.length == 1 && r[0]?.isDirectory) {
                let i = r[0].createReader();
                (r = []),
                    await new Promise((n, o) => {
                        i.readEntries((c) => {
                            for (let u of c) u.isFile && r.push(u);
                            n(!0);
                        }, o);
                    });
            }
            return new s(r);
        }
        *list() {
            for (let e of this.items) yield e.name;
        }
        async has(e) {
            for (let r of this.items) if (r.name == e) return !0;
            return !1;
        }
        async get(e) {
            let r = null;
            for (let i of this.items)
                if (i.name == e) {
                    r = i;
                    break;
                }
            if (r == null) throw new Error(`File ${e} not found!`);
            return await new Promise((i, n) => {
                r.file(i, n);
            });
        }
        async download(e) {
            Gt(await this.get(e));
        }
    };
var K2 = class {
    static {
        l(this, 'DropTarget');
    }
    constructor(t, e) {
        t.addEventListener(
            'dragenter',
            (r) => {
                r.preventDefault();
            },
            !1,
        ),
            t.addEventListener(
                'dragover',
                (r) => {
                    r.dataTransfer && (r.preventDefault(), (r.dataTransfer.dropEffect = 'move'));
                },
                !1,
            ),
            t.addEventListener(
                'drop',
                async (r) => {
                    r.stopPropagation(), r.preventDefault();
                    let i = r.dataTransfer;
                    if (!i) return;
                    let n = await Y2.fromDataTransfer(i);
                    e(n);
                },
                !1,
            );
    }
};
var H2 = class s extends Event {
    constructor(e, r) {
        super(s.type, { bubbles: !0, cancelable: !0, composed: !0 });
        this.context_name = e;
        this._callback = r;
    }
    static {
        l(this, 'ContextRequestEvent');
    }
    static {
        this.type = 'context-request';
    }
    callback(e) {
        this.stopPropagation(), this._callback(e);
    }
};
async function ds(s, t) {
    return new Promise((e) => {
        s.dispatchEvent(
            new H2(t, (r) => {
                e(r);
            }),
        );
    });
}
l(ds, 'requestContext');
function ms(s, t, e) {
    s.addEventListener(H2.type, (r) => {
        let i = r;
        i.context_name == t && i.callback(e);
    });
}
l(ms, 'provideContext');
async function an(s, t) {
    return (await ds(s, t))();
}
l(an, 'requestLazyContext');
async function ln(s, t, e) {
    ms(s, t, e);
}
l(ln, 'provideLazyContext');
function bs(s) {
    return class extends s {
        static {
            l(this, 'WithContext');
        }
        constructor(...e) {
            super(...e);
        }
        async requestContext(e) {
            return await ds(this, e);
        }
        provideContext(e, r) {
            ms(this, e, r);
        }
        async requestLazyContext(e) {
            return await an(this, e);
        }
        provideLazyContext(e, r) {
            ln(this, e, r);
        }
    };
}
l(bs, 'WithContext');
function B3(s) {
    return s === null || (typeof s != 'object' && typeof s != 'function');
}
l(B3, 'is_primitive');
function G(s) {
    return typeof s == 'string';
}
l(G, 'is_string');
function le(s) {
    return typeof s == 'number' && !isNaN(s);
}
l(le, 'is_number');
function Et(s) {
    return Array.isArray(s) || typeof s?.[Symbol.iterator] == 'function';
}
l(Et, 'is_iterable');
function $3(s) {
    return Array.isArray(s);
}
l($3, 'is_array');
function _s(s) {
    return typeof s == 'object' && s !== null && !Array.isArray(s) && !(s instanceof RegExp) && !(s instanceof Date);
}
l(_s, 'is_object');
var Ms = new Map(),
    Ne = class {
        constructor(t) {
            this.css_string = t;
        }
        static {
            l(this, 'CSS');
        }
        get stylesheet() {
            let t = Ms.get(this.css_string);
            return (
                t == null && ((t = new CSSStyleSheet()), t.replaceSync(this.css_string), Ms.set(this.css_string, t)), t
            );
        }
    };
function T(s, ...t) {
    let e = '';
    for (let r = 0; r < s.length - 1; r++) {
        e += s[r];
        let i = t[r];
        if (i instanceof Ne) e += i.css_string;
        else if (le(i)) e += String(i);
        else throw new Error('Only CSS or number variables allowed in css template literal');
    }
    return (e += s.at(-1)), new Ne(e);
}
l(T, 'css');
function fs(s, t) {
    s.adoptedStyleSheets = s.adoptedStyleSheets.concat(t.map((e) => (e instanceof CSSStyleSheet ? e : e.stylesheet)));
}
l(fs, 'adopt_styles');
function G2(s) {
    return $3(s) ? s : [s];
}
l(G2, 'as_array');
function Ns(s) {
    return $3(s) ? s : Et(s) ? Array.from(s) : [s];
}
l(Ns, 'iterable_as_array');
var cn = new Intl.Collator(void 0, { numeric: !0 });
function pe(s, t) {
    return s.slice().sort((e, r) => cn.compare(t(e), t(r)));
}
l(pe, 'sorted_by_numeric_strings');
var nt = class {
    constructor() {
        this._disposables = new Set();
        this._is_disposed = !1;
    }
    static {
        l(this, 'Disposables');
    }
    add(t) {
        if (this._is_disposed) throw new Error("Tried to add item to a DisposableStack that's already been disposed");
        return this._disposables.add(t), t;
    }
    disposeAndRemove(t) {
        t && (t.dispose(), this._disposables.delete(t));
    }
    get isDisposed() {
        return this._is_disposed;
    }
    dispose() {
        if (this._is_disposed) {
            console.trace('dispose() called on an already disposed resource');
            return;
        }
        for (let t of this._disposables.values()) t.dispose();
        this._disposables.clear(), (this._is_disposed = !0);
    }
};
function Rn(s) {
    return typeof HTMLElement == 'object' && s instanceof HTMLElement;
}
l(Rn, 'is_HTMLElement');
function _(s, ...t) {
    let e = document.createElement('template');
    e.innerHTML = un(s, t);
    let r = e.content;
    return (r = document.importNode(r, !0)), pn(r, t), r.childElementCount == 1 ? r.firstElementChild : r;
}
l(_, 'html');
var j3 = class {
        constructor(t) {
            this.text = t;
        }
        static {
            l(this, 'Literal');
        }
    },
    z3 = /\$\$:(\d+):\$\$/g;
function un(s, t) {
    let e = [];
    for (let i = 0; i < s.length - 1; i++) e.push(s[i]), t[i] instanceof j3 ? e.push(t[i].text) : e.push(`$$:${i}:$$`);
    return e.push(s[s.length - 1]), e.join('');
}
l(un, 'prepare_template_html');
function pn(s, t) {
    let e = document.createTreeWalker(s, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, null),
        r;
    for (; (r = e.nextNode()) !== null; )
        if (r.nodeType == Node.TEXT_NODE) hn(r.parentNode, r, t);
        else if (r.nodeType == Node.ELEMENT_NODE) {
            let i = r;
            for (let n of i.getAttributeNames()) {
                let o = i.getAttributeNode(n);
                dn(i, o, t);
            }
        }
}
l(pn, 'apply_values_to_tree');
function hn(s, t, e) {
    if (!s) return;
    let r = t.data.split(z3);
    if (!(!r || r.length == 1)) {
        if (Rn(s) && ['script', 'style'].includes(s.localName))
            throw new Error('Cannot bind values inside of <script> or <style> tags');
        for (let i = 0; i < r.length; i++) {
            let n = r[i];
            if (n)
                if (i % 2 == 0) s.insertBefore(new Text(n), t);
                else for (let o of Vs(e[parseInt(n, 10)])) o != null && s.insertBefore(o, t);
        }
        t.data = '';
    }
}
l(hn, 'apply_content_value');
function dn(s, t, e) {
    let r = t.value.split(z3);
    if (!(!r || r.length == 1)) {
        if (t.localName.startsWith('on')) throw new Error(`Cannot bind to event handler ${t.localName}.`);
        if (r.length == 3 && r[0] == '' && r[2] == '') {
            let i = e[parseInt(r[1], 10)];
            i === !0
                ? (t.value = '')
                : i === !1 || i === null || i === void 0
                  ? s.removeAttribute(t.name)
                  : (t.value = q3(i, t.name));
            return;
        }
        t.value = t.value.replaceAll(z3, (i, n) => {
            let o = e[parseInt(n, 10)];
            return q3(o, t.localName);
        });
    }
}
l(dn, 'apply_attribute_value');
function* Vs(s) {
    if (!(s == null || s == null)) {
        if (B3(s)) {
            yield new Text(s.toString());
            return;
        }
        if (s instanceof Node || s instanceof DocumentFragment) {
            yield s;
            return;
        }
        if (Et(s)) {
            for (let t of s) yield* Vs(t);
            return;
        }
        throw new Error(`Invalid value ${s}`);
    }
}
l(Vs, 'convert_value_for_content');
function q3(s, t) {
    if (s == null || s == null) return '';
    if (B3(s)) return s.toString();
    if (Et(s))
        return Array.from(s)
            .map((e) => q3(e, t))
            .join('');
    throw new Error(`Invalid value ${s}`);
}
l(q3, 'convert_value_for_attr');
var Oe = class extends HTMLElement {
    constructor() {
        super();
        this.updateComplete = new Me();
        this.disposables = new nt();
        let e = this.constructor;
        e.exportparts.length && this.setAttribute('exportparts', e.exportparts.join(','));
    }
    static {
        l(this, 'CustomElement');
    }
    static {
        this.useShadowRoot = !0;
    }
    static {
        this.exportparts = [];
    }
    addDisposable(e) {
        return this.disposables.add(e);
    }
    get renderRoot() {
        return this.shadowRoot ?? this;
    }
    connectedCallback() {
        this.#e();
    }
    disconnectedCallback() {
        this.disposables.dispose();
    }
    initialContentCallback() {}
    render() {
        return _``;
    }
    renderedCallback() {}
    async update() {
        for (this.updateComplete = new Me(); this.renderRoot.firstChild; ) this.renderRoot.firstChild.remove();
        return (
            this.renderRoot.appendChild(await this.render()),
            this.renderedCallback(),
            window.requestAnimationFrame(() => {
                this.updateComplete.resolve(!0);
            }),
            this.updateComplete
        );
    }
    #e() {
        let e = this.constructor;
        return (
            (this.updateComplete = new Me()),
            this.constructor.useShadowRoot && this.attachShadow({ mode: 'open' }),
            e.styles && fs(this.shadowRoot ?? document, G2(e.styles)),
            (async () => {
                let r = this.render();
                this.renderRoot.appendChild(r),
                    this.renderedCallback(),
                    this.initialContentCallback(),
                    window.requestAnimationFrame(() => {
                        this.updateComplete.resolve(!0);
                    });
            })(),
            this.updateComplete
        );
    }
    queryAssignedElements(e, r) {
        let n = this.renderRoot.querySelector(`slot${e ? `[name=${e}]` : ':not([name])'}`)?.assignedElements() ?? [];
        return r ? n.filter((o) => o.matches(r)) : n;
    }
};
function L(s) {
    let t = s.converter?.to_attribute ?? gs.to_attribute,
        e = s.converter?.from_attribute ?? gs.from_attribute;
    return (r, i) => {
        let n = i.replace('_', '-'),
            o = !1;
        Object.defineProperty(r, i, {
            enumerable: !0,
            configurable: !0,
            get() {
                return e(this.getAttribute(n), s.type);
            },
            set(c) {
                let u = this[i],
                    p = t(c, s.type);
                p === null ? this.removeAttribute(n) : this.setAttribute(n, p),
                    o || ((o = !0), s.on_change?.(u, c), (o = !1));
            },
        });
    };
}
l(L, 'attribute');
var gs = {
    to_attribute(s, t) {
        if (s === null) return s;
        switch (t) {
            case Boolean:
                return s ? '' : null;
            case String:
                return s;
            case Number:
                return `${s}`;
            default:
                throw new Error(`Can not convert type "${t}" and value "${s} to attribute`);
        }
    },
    from_attribute(s, t) {
        switch (t) {
            case Boolean:
                return s !== null;
            case String:
                return s;
            case Number:
                return s === null ? null : Number(s);
            default:
                throw new Error(`Can not convert type "${t}" and value "${s} to attribute`);
        }
    },
};
function Q(s, t) {
    return (e, r) => {
        let i = typeof r == 'symbol' ? Symbol() : `__${r}`;
        Object.defineProperty(e, r, {
            enumerable: !0,
            configurable: !0,
            get() {
                let n = this;
                if (t && n[i] !== void 0) return n[i];
                let o = this.renderRoot?.querySelector(s) ?? null;
                return t && o && (n[i] = o), o;
            },
        });
    };
}
l(Q, 'query');
function Ps(s) {
    return (t, e) => {
        Object.defineProperty(t, e, {
            enumerable: !0,
            configurable: !0,
            get() {
                return this.renderRoot?.querySelectorAll(s) ?? [];
            },
        });
    };
}
l(Ps, 'query_all');
function k(s, t, e, r) {
    return (
        s.addEventListener(t, e, r),
        {
            dispose: () => {
                s.removeEventListener(t, e, r);
            },
        }
    );
}
l(k, 'listen');
function he(s, t, e, r, i) {
    return k(
        s,
        e,
        (n) => {
            let o = n.target.closest(t);
            o && r(n, o);
        },
        i,
    );
}
l(he, 'delegate');
var mn = T`
    :host {
        box-sizing: border-box;
    }

    :host *,
    :host *::before,
    :host *::after {
        box-sizing: inherit;
    }

    [hidden] {
        display: none !important;
    }

    :host {
        scrollbar-width: thin;
        scrollbar-color: #ae81ff #282634;
    }

    ::-webkit-scrollbar {
        position: absolute;
        width: 6px;
        height: 6px;
        margin-left: -6px;
        background: var(--scrollbar-bg);
    }

    ::-webkit-scrollbar-thumb {
        position: absolute;
        background: var(--scrollbar-fg);
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--scrollbar-hover-fg);
    }

    ::-webkit-scrollbar-thumb:active {
        background: var(--scrollbar-active-fg);
    }

    .invert-scrollbar::-webkit-scrollbar {
        position: absolute;
        width: 6px;
        height: 6px;
        margin-left: -6px;
        background: var(--scrollbar-fg);
    }

    .invert-scrollbar::-webkit-scrollbar-thumb {
        position: absolute;
        background: var(--scrollbar-bg);
    }

    .invert-scrollbar::-webkit-scrollbar-thumb:hover {
        background: var(--scrollbar-hover-bg);
    }

    .invert-scrollbar::-webkit-scrollbar-thumb:active {
        background: var(--scrollbar-active-bg);
    }
`,
    N = class extends bs(Oe) {
        static {
            l(this, 'KCUIElement');
        }
        static {
            this.styles = [mn];
        }
    };
var Jt = class s extends N {
    static {
        l(this, 'KCUIIconElement');
    }
    static {
        this.sprites_url = '';
    }
    static {
        this.styles = [
            T`
            :host {
                box-sizing: border-box;
                font-family: "Material Symbols Outlined";
                font-weight: normal;
                font-style: normal;
                font-size: inherit;
                line-height: 1;
                letter-spacing: normal;
                text-transform: none;
                white-space: nowrap;
                word-wrap: normal;
                direction: ltr;
                -webkit-font-feature-settings: "liga";
                -moz-font-feature-settings: "liga";
                font-feature-settings: "liga";
                -webkit-font-smoothing: antialiased;
                user-select: none;
            }

            svg {
                width: 1.2em;
                height: auto;
                fill: currentColor;
            }
        `,
        ];
    }
    render() {
        let t = this.textContent ?? '';
        if (t.startsWith('svg:')) {
            let e = t.slice(4),
                r = `${s.sprites_url}#${e}`;
            return _`<svg viewBox="0 0 48 48" width="48">
                <use xlink:href="${r}" />
            </svg>`;
        } else return _`<slot></slot>`;
    }
};
window.customElements.define('kc-ui-icon', Jt);
var de = class extends N {
    static {
        l(this, 'KCUIButtonElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                display: inline-flex;
                position: relative;
                width: auto;
                cursor: pointer;
                user-select: none;
                align-items: center;
                justify-content: center;
            }

            button {
                all: unset;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 0.5em;
                border: 1px solid transparent;
                border-radius: 0.25em;
                font-weight: medium;
                font-size: 1em;
                background: var(--button-bg);
                color: var(--button-fg);
                transition:
                    color var(--transition-time-short) ease,
                    border var(--transition-time-short) ease,
                    background var(--transition-time-short) ease;
            }

            :host {
                fill: var(--button-fg);
            }

            button:hover {
                background: var(--button-hover-bg);
                color: var(--button-hover-fg);
            }

            button:disabled {
                background: var(--button-disabled-bg);
                color: var(--button-disabled-fg);
            }

            button:focus {
                outline: var(--button-focus-outline);
            }

            :host([selected]) button {
                background: var(--button-selected-bg);
                color: var(--button-selected-fg);
            }

            /* variants */

            button.outline {
                background: var(--button-outline-bg);
                color: var(--button-outline-fg);
            }

            button.outline:hover {
                background: var(--button-outline-hover-bg);
                color: var(--button-outline-hover-fg);
            }

            button.outline:disabled {
                background: var(--button-outline-disabled-bg);
                color: var(--button-outline-disabled-fg);
            }

            :host([selected]) button.outline {
                background: var(--button-outline-disabled-bg);
                color: var(--button--outline-disabled-fg);
            }

            button.toolbar {
                background: var(--button-toolbar-bg);
                color: var(--button-toolbar-fg);
            }

            button.toolbar:hover {
                background: var(--button-toolbar-hover-bg);
                color: var(--button-toolbar-hover-fg);
            }

            button.toolbar:disabled {
                background: var(--button-toolbar-disabled-bg);
                color: var(--button-toolbar-disabled-fg);
            }

            :host([selected]) button.toolbar {
                background: var(--button-toolbar-disabled-bg);
                color: var(--button--toolbar-disabled-fg);
            }

            button.toolbar-alt {
                background: var(--button-toolbar-alt-bg);
                color: var(--button-toolbar-alt-fg);
            }

            button.toolbar-alt:hover {
                background: var(--button-toolbar-alt-hover-bg);
                color: var(--button-toolbar-alt-hover-fg);
            }

            button.toolbar-alt:disabled {
                background: var(--button-toolbar-alt-disabled-bg);
                color: var(--button-toolbar-alt-disabled-fg);
            }

            :host([selected]) button.toolbar-alt {
                background: var(--button-toolbar-alt-disabled-bg);
                color: var(--button--toolbar-alt-disabled-fg);
            }

            button.menu {
                background: var(--button-menu-bg);
                color: var(--button-menu-fg);
                padding: 0;
            }

            button.menu:hover {
                background: var(--button-menu-hover-bg);
                color: var(--button-menu-hover-fg);
                outline: none;
            }

            button.menu:focus {
                outline: none;
            }

            button.menu:disabled {
                background: var(--button-menu-disabled-bg);
                color: var(--button-menu-disabled-fg);
            }

            :host([selected]) button.menu {
                background: var(--button-menu-disabled-bg);
                color: var(--button--menu-disabled-fg);
                outline: none;
            }
        `,
        ];
    }
    static get observedAttributes() {
        return ['disabled', 'icon'];
    }
    attributeChangedCallback(e, r, i) {
        if (this.button)
            switch (e) {
                case 'disabled':
                    this.button.disabled = i != null;
                    break;
                case 'icon':
                    this.button_icon.innerText = i ?? '';
                    break;
            }
    }
    initialContentCallback() {
        this.variant && this.button.classList.add(this.variant), (this.button.disabled = this.disabled);
    }
    render() {
        let e = this.icon ? _`<kc-ui-icon part="icon">${this.icon}</kc-ui-icon>` : void 0;
        return _`<button part="base">
            ${e}
            <slot part="contents"></slot>
        </button>`;
    }
};
P([Q('button', !0)], de.prototype, 'button', 2),
    P([Q('button_icon', !0)], de.prototype, 'button_icon', 2),
    P([L({ type: String })], de.prototype, 'name', 2),
    P([L({ type: String })], de.prototype, 'icon', 2),
    P([L({ type: String })], de.prototype, 'variant', 2),
    P([L({ type: Boolean })], de.prototype, 'disabled', 2),
    P([L({ type: Boolean })], de.prototype, 'selected', 2);
window.customElements.define('kc-ui-button', de);
var ot = class extends N {
    static {
        l(this, 'KCUIActivitySideBarElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                flex-shrink: 0;
                display: flex;
                flex-direction: row;
                height: 100%;
                overflow: hidden;
                min-width: calc(max(20%, 200px));
                max-width: calc(max(20%, 200px));
            }

            div {
                display: flex;
                overflow: hidden;
                flex-direction: column;
            }

            div.bar {
                flex-grow: 0;
                flex-shrink: 0;
                height: 100%;
                z-index: 1;
                display: flex;
                flex-direction: column;
                background: var(--activity-bar-bg);
                color: var(--activity-bar-fg);
                padding: 0.2em;
                user-select: none;
            }

            div.start {
                flex: 1;
            }

            div.activities {
                flex-grow: 1;
            }

            kc-ui-button {
                --button-bg: transparent;
                --button-fg: var(--activity-bar-fg);
                --button-hover-bg: var(--activity-bar-active-bg);
                --button-hover-fg: var(--activity-bar-active-fg);
                --button-selected-bg: var(--activity-bar-active-bg);
                --button-selected-fg: var(--activity-bar-active-fg);
                --button-focus-outline: none;
                margin-bottom: 0.25em;
            }

            kc-ui-button:last-child {
                margin-bottom: 0;
            }

            ::slotted(kc-ui-activity) {
                display: none;
                height: 100%;
            }

            ::slotted(kc-ui-activity[active]) {
                display: block;
            }
        `,
        ];
    }
    #e;
    get #t() {
        return this.querySelectorAll('kc-ui-activity');
    }
    get #r() {
        return Array.from(this.#t).map((e) => (e.getAttribute('name') ?? '').toLowerCase());
    }
    get #i() {
        return (this.#t[0]?.getAttribute('name') ?? '').toLowerCase();
    }
    render() {
        let e = [],
            r = [];
        for (let i of this.#t) {
            let n = i.getAttribute('name'),
                o = i.getAttribute('icon');
            (i.getAttribute('button-location') == 'bottom' ? r : e).push(_`
                    <kc-ui-button
                        type="button"
                        tooltip-left="${n}"
                        name="${n?.toLowerCase()}"
                        title="${n}"
                        icon=${o}>
                    </kc-ui-button>
                `);
        }
        return _`<div class="bar">
                <div class="start">${e}</div>
                <div class="end">${r}</div>
            </div>
            <div class="activities">
                <slot name="activities"></slot>
            </div>`;
    }
    initialContentCallback() {
        this.collapsed ? this.change_activity(null) : this.change_activity(this.#i),
            he(this.renderRoot, 'kc-ui-button', 'click', (r, i) => {
                this.change_activity(i.name, !0);
            }),
            new MutationObserver(async (r) => {
                await this.update(), this.#e && !this.#r.includes(this.#e) && this.change_activity(this.#i);
            }).observe(this, { childList: !0 });
    }
    static get observedAttributes() {
        return ['collapsed'];
    }
    attributeChangedCallback(e, r, i) {
        switch (e) {
            case 'collapsed':
                i == null ? this.show_activities() : this.hide_activities();
                break;
            default:
                break;
        }
    }
    get activity() {
        return this.#e;
    }
    set activity(e) {
        this.change_activity(e, !1);
    }
    hide_activities() {
        this.activities_container &&
            ((this.style.width = 'unset'),
            (this.style.minWidth = 'unset'),
            (this.style.maxWidth = ''),
            (this.activities_container.style.width = '0px'));
    }
    show_activities() {
        this.activities_container &&
            (this.#e || this.change_activity(this.#i),
            (this.style.minWidth = ''),
            (this.activities_container.style.width = ''));
    }
    change_activity(e, r = !1) {
        (e = e?.toLowerCase()),
            this.#e == e && r ? (this.#e = null) : (this.#e = e),
            this.#e ? (this.collapsed = !1) : (this.collapsed = !0),
            this.update_state();
    }
    update_state() {
        for (let e of this.buttons) e.selected = e.name == this.#e;
        for (let e of this.#t)
            e.getAttribute('name')?.toLowerCase() == this.#e
                ? e.setAttribute('active', '')
                : e.removeAttribute('active');
    }
};
P([Q('.activities', !0)], ot.prototype, 'activities_container', 2),
    P([Ps('kc-ui-button')], ot.prototype, 'buttons', 2),
    P([L({ type: Boolean })], ot.prototype, 'collapsed', 2);
window.customElements.define('kc-ui-activity-side-bar', ot);
var er = class extends Oe {
    static {
        l(this, 'KCUIAppElement');
    }
    static {
        this.useShadowRoot = !1;
    }
};
window.customElements.define('kc-ui-app', er);
var tr = class extends N {
    static {
        l(this, 'KCUIControlListElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                display: flex;
                flex-direction: column;
                flex-wrap: nowrap;
                background: var(--list-item-bg);
                color: var(--list-item-fg);
                padding-top: 0.2em;
            }
        `,
        ];
    }
    render() {
        return _`<slot></slot>`;
    }
};
window.customElements.define('kc-ui-control-list', tr);
var rr = class extends N {
    static {
        l(this, 'KCUIControlListItemElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                margin-top: 0.2em;
                display: flex;
                flex-direction: column;
                flex-wrap: nowrap;
                user-select: none;
                background-color: transparent;
                transition:
                    color var(--transition-time-short) ease,
                    background-color var(--transition-time-short) ease;
            }

            ::slotted(label) {
                flex: 1 1 100%;
                display: block;
                margin: 0;
                text-overflow: ellipsis;
                white-space: nowrap;
                overflow: hidden;
            }

            ::slotted(input),
            ::slotted(select) {
                margin: 0;
                padding-left: 0;
                padding-right: 0;
            }
        `,
        ];
    }
    render() {
        return _`<slot></slot>`;
    }
};
window.customElements.define('kc-ui-control-list-item', rr);
function at(s, t, e) {
    let r = e.value,
        i = !1;
    e.value = function (...n) {
        if (!i) {
            i = !0;
            try {
                r.apply(this, n);
            } finally {
                i = !1;
            }
        }
    };
}
l(at, 'no_self_recursion');
var E2 = class extends N {
    static {
        l(this, 'KCUIMenuElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                width 100%;
                display: flex;
                flex-direction: column;
                flex-wrap: nowrap;
                background: var(--list-item-bg);
                color: var(--list-item-fg);
            }

            :host(.outline) ::slotted(kc-ui-menu-item) {
                border-bottom: 1px solid var(--grid-outline);
            }

            :host(.dropdown) {
                --list-item-padding: 0.3em 0.6em;
                --list-item-bg: var(--dropdown-bg);
                --list-item-fg: var(--dropdown-fg);
                --list-item-hover-bg: var(--dropdown-hover-bg);
                --list-item-hover-fg: var(--dropdown-hover-fg);
                --list-item-active-bg: var(--dropdown-active-bg);
                --list-item-active-fg: var(--dropdown-active-fg);
                max-height: 50vh;
                overflow-y: auto;
            }
        `,
        ];
    }
    constructor() {
        super(), (this.role = 'menu');
    }
    items() {
        return this.querySelectorAll('kc-ui-menu-item');
    }
    item_by_name(t) {
        for (let e of this.items()) if (e.name == t) return e;
        return null;
    }
    deselect() {
        for (let t of this.items()) t.selected = !1;
    }
    get selected() {
        for (let t of this.items()) if (t.selected) return t;
        return null;
    }
    set selected(t) {
        let e;
        G(t) ? (e = this.item_by_name(t)) : (e = t),
            this.deselect(),
            !(!e || !(e instanceof Ue)) && ((e.selected = !0), this.send_selected_event(e));
    }
    send_selected_event(t) {
        this.dispatchEvent(new CustomEvent('kc-ui-menu:select', { detail: t, bubbles: !0, composed: !0 }));
    }
    initialContentCallback() {
        super.initialContentCallback(),
            he(this, 'kc-ui-menu-item', 'click', (t, e) => {
                t.target.tagName != 'KC-UI-BUTTON' && (t.stopPropagation(), (this.selected = e));
            });
    }
    render() {
        return _`<slot></slot>`;
    }
};
P([at], E2.prototype, 'send_selected_event', 1);
window.customElements.define('kc-ui-menu', E2);
var Ue = class extends N {
    constructor() {
        super();
        this.role = 'menuitem';
    }
    static {
        l(this, 'KCUIMenuItemElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                display: flex;
                align-items: center;
                flex-wrap: nowrap;
                padding: var(--list-item-padding, 0.2em 0.3em);
                user-select: none;
                background: transparent;
                transition:
                    color var(--transition-time-short) ease,
                    background-color var(--transition-time-short) ease;
                cursor: pointer;
            }

            :host(:hover) {
                background: var(--list-item-hover-bg);
                color: var(--list-item-hover-fg);
            }

            :host([selected]) {
                background: var(--list-item-active-bg);
                color: var(--list-item-active-fg);
            }

            :host([disabled]) {
                background: var(--list-item-disabled-bg);
                color: var(--list-item-disabled-fg);
            }

            ::slotted(*) {
                flex: 1 1 100%;
                display: block;
                text-overflow: ellipsis;
                white-space: nowrap;
                overflow: hidden;
            }

            ::slotted(.narrow) {
                max-width: 100px;
            }

            ::slotted(.very-narrow) {
                max-width: 50px;
            }

            kc-ui-icon {
                margin-right: 0.5em;
                margin-left: -0.1em;
            }
        `,
        ];
    }
    render() {
        let e = this.icon ? _`<kc-ui-icon>${this.icon}</kc-ui-icon>` : void 0;
        return _`${e}<slot></slot>`;
    }
};
P([L({ type: String })], Ue.prototype, 'name', 2),
    P([L({ type: String })], Ue.prototype, 'icon', 2),
    P([L({ type: Boolean })], Ue.prototype, 'selected', 2),
    P([L({ type: Boolean })], Ue.prototype, 'disabled', 2);
window.customElements.define('kc-ui-menu-item', Ue);
var ir = class extends N {
    static {
        l(this, 'KCUIMenuLabelElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                width: 100%;
                display: flex;
                flex-wrap: nowrap;
                padding: 0.2em 0.3em;
                background: var(--panel-subtitle-bg);
                color: var(--panel-subtitle-fg);
            }
        `,
        ];
    }
    render() {
        return _`<slot></slot>`;
    }
};
window.customElements.define('kc-ui-menu-label', ir);
var It = class extends N {
    constructor() {
        super();
        this.mouseout_padding ??= 50;
    }
    static {
        l(this, 'KCUIDropdownElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                border-radius: 5px;
                border: 1px solid transparent;
                display: none;
                flex-direction: column;
                overflow: hidden;
                user-select: none;
                background: var(--dropdown-bg);
                color: var(--dropdown-fg);
                font-weight: 300;
            }

            :host([visible]) {
                display: flex;
            }
        `,
        ];
    }
    show() {
        this.visible ||
            ((this.visible = !0),
            this.dispatchEvent(new CustomEvent('kc-ui-dropdown:show', { bubbles: !0, composed: !0 })));
    }
    hide() {
        this.visible &&
            ((this.visible = !1),
            this.dispatchEvent(new CustomEvent('kc-ui-dropdown:hide', { bubbles: !0, composed: !0 })));
    }
    toggle() {
        this.visible ? this.hide() : this.show();
    }
    get menu() {
        return this.querySelector('kc-ui-menu');
    }
    initialContentCallback() {
        super.initialContentCallback(),
            this.hasAttribute('auto-hide') && this.setup_leave_event(),
            this.menu.classList.add('invert-scrollbar');
    }
    setup_leave_event() {
        this.addEventListener('mouseleave', (e) => {
            if (!this.visible) return;
            let r = this.mouseout_padding,
                i = this.getBoundingClientRect(),
                n = k(window, 'mousemove', (o) => {
                    this.visible || n.dispose(),
                        (o.clientX > i.left - r &&
                            o.clientX < i.right + r &&
                            o.clientY > i.top - r &&
                            o.clientY < i.bottom + r) ||
                            (this.hide(), n.dispose());
                });
        });
    }
    render() {
        return _`<slot></slot>`;
    }
};
P([L({ type: Boolean })], It.prototype, 'visible', 2), P([L({ type: Number })], It.prototype, 'mouseout_padding', 2);
window.customElements.define('kc-ui-dropdown', It);
var sr = class extends N {
    static {
        l(this, 'KCUIFilteredListElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                display: contents;
            }
        `,
        ];
    }
    render() {
        return _`<slot></slot>`;
    }
    #e;
    set filter_text(t) {
        (this.#e = t?.toLowerCase() ?? null), this.apply_filter();
    }
    get filter_text() {
        return this.#e;
    }
    get item_selector() {
        return this.getAttribute('item-selector') ?? '[data-match-text]';
    }
    *items() {
        for (let t of this.queryAssignedElements()) yield* t.querySelectorAll(this.item_selector);
    }
    apply_filter() {
        ue(() => {
            for (let t of this.items())
                this.#e == null || t.dataset.matchText?.toLowerCase().includes(this.#e)
                    ? t.style.removeProperty('display')
                    : (t.style.display = 'none');
        });
    }
};
window.customElements.define('kc-ui-filtered-list', sr);
var nr = class extends N {
    static {
        l(this, 'KCUIFloatingToolbarElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                z-index: 10;
                user-select: none;
                pointer-events: none;
                position: absolute;
                left: 0;
                width: 100%;
                padding: 0.5em;
                display: flex;
                flex-direction: row;
                align-items: center;
                justify-content: flex-start;
            }

            :host([location="top"]) {
                top: 0;
            }

            :host([location="bottom"]) {
                bottom: 0;
            }

            ::slotted(*) {
                user-select: initial;
                pointer-events: initial;
            }

            slot[name="left"] {
                flex-grow: 999;
                display: flex;
            }

            slot[name="right"] {
                display: flex;
            }

            ::slotted(kc-ui-button) {
                margin-left: 0.25em;
            }
        `,
        ];
    }
    render() {
        return _`<slot name="left"></slot><slot name="right"></slot>`;
    }
};
window.customElements.define('kc-ui-floating-toolbar', nr);
var or = class extends N {
    static {
        l(this, 'KCUIFocusOverlay');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                z-index: 10;
                user-select: none;
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                pointer-events: initial;
                background: transparent;
                contain: paint;
            }

            :host(.has-focus) {
                z-index: -10;
                pointer-events: none;
            }

            .bg {
                background: var(--focus-overlay-bg);
                opacity: 0;
                transition: opacity var(--transition-time-short);
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
            }

            :host(:hover) .bg {
                opacity: var(--focus-overlay-opacity);
            }

            :host(.has-focus) .bg {
                opacity: 0;
            }

            .fg {
                position: absolute;
                font-size: 1.5rem;
                color: var(--focus-overlay-fg);
                text-shadow: rgba(0, 0, 0, 0.5) 0px 0px 15px;
                opacity: 0;
                pointer-events: none;
            }

            :host(:hover) .fg {
                opacity: 1;
            }

            :host(.has-focus) .fg {
                opacity: 0;
            }
        `,
        ];
    }
    #e;
    initialContentCallback() {
        this.addEventListener('click', () => {
            this.classList.add('has-focus');
        }),
            this.addDisposable(
                k(document, 'click', (t) => {
                    !t.composedPath().includes(this.parentElement) && this.classList.remove('has-focus');
                }),
            ),
            (this.#e = new IntersectionObserver((t) => {
                for (let e of t) console.log(e), e.isIntersecting || this.classList.remove('has-focus');
            })),
            this.#e.observe(this),
            this.addDisposable({
                dispose: () => {
                    this.#e.disconnect();
                },
            });
    }
    render() {
        return _`
            <div class="bg"></div>
            <div class="fg">Click or tap to interact</div>
        `;
    }
};
window.customElements.define('kc-ui-focus-overlay', or);
var ar = class extends N {
    static {
        l(this, 'KCUIPanelElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                width: 100%;
                height: 100%;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                background: var(--panel-bg);
                color: var(--panel-fg);
                --bg: var(--panel-bg);
            }

            :host(:last-child) {
                flex-grow: 1;
            }
        `,
        ];
    }
    render() {
        return _`<slot></slot>`;
    }
};
window.customElements.define('kc-ui-panel', ar);
var lr = class extends N {
    static {
        l(this, 'KCUIPanelTitleElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                flex: 0;
                width: 100%;
                text-align: left;
                padding: 0.2em 0.8em 0.2em 0.4em;
                display: flex;
                align-items: center;
                background: var(--panel-title-bg);
                color: var(--panel-title-fg);
                border-top: var(--panel-title-border);
                user-select: none;
            }

            div.title {
                flex: 1;
            }

            div.actions {
                flex: 0 1;
                display: flex;
                flex-direction: row;
                /* cheeky hack to work around scrollbar causing placement to be off. */
                padding-right: 6px;
            }
        `,
        ];
    }
    render() {
        return _`<div class="title">${this.title}</div>
            <div class="actions">
                <slot name="actions"></slot>
            </div>`;
    }
};
window.customElements.define('kc-ui-panel-title', lr);
var cr = class extends N {
    static {
        l(this, 'KCUIPanelBodyElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                width: 100%;
                min-height: 0;
                overflow-y: auto;
                overflow-x: hidden;
                flex: 1 0;
                font-weight: 300;
                font-size: 1em;
            }

            :host([padded]) {
                padding: 0.1em 0.8em 0.1em 0.4em;
            }
        `,
        ];
    }
    render() {
        return _`<slot></slot>`;
    }
};
window.customElements.define('kc-ui-panel-body', cr);
var Rr = class extends N {
    static {
        l(this, 'KCUIPanelLabelElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                width: 100%;
                display: flex;
                flex-wrap: nowrap;
                padding: 0.2em 0.3em;
                background: var(--panel-subtitle-bg);
                color: var(--panel-subtitle-fg);
            }
        `,
        ];
    }
    render() {
        return _`<slot></slot>`;
    }
};
window.customElements.define('kc-ui-panel-label', Rr);
var ur = class extends N {
    static {
        l(this, 'KCUIPropertyList');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                display: grid;
                gap: 1px;
                grid-template-columns: fit-content(50%) 1fr;
                background: var(--grid-outline);
                border-bottom: 1px solid var(--grid-outline);
            }
        `,
        ];
    }
    render() {
        return _`<slot></slot>`;
    }
};
window.customElements.define('kc-ui-property-list', ur);
var J2 = class extends N {
    static {
        l(this, 'KCUIPropertyListItemElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                display: contents;
            }

            span {
                padding: 0.2em;
                background: var(--bg);
                text-overflow: ellipsis;
                white-space: nowrap;
                overflow: hidden;
                user-select: all;
            }

            :host(.label) span:first-child {
                user-select: none;
                grid-column-end: span 2;
                background: var(--panel-subtitle-bg);
                color: var(--panel-subtitle-fg);
            }

            :host(.label) span:last-child {
                display: none;
            }

            ::slotted(*) {
                vertical-align: middle;
            }
        `,
        ];
    }
    render() {
        return _`<span title="${this.name}">${this.name}</span
            ><span><slot></slot></span>`;
    }
};
P([L({ type: String })], J2.prototype, 'name', 2);
window.customElements.define('kc-ui-property-list-item', J2);
var Ve = class extends N {
    static {
        l(this, 'KCUIRangeElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                display: block;
                width: 100%;
                user-select: none;
            }

            input[type="range"] {
                all: unset;
                box-sizing: border-box;
                display: block;
                width: 100%;
                max-width: 100%;
                padding-top: 0.25em;
                padding-bottom: 0.25em;
                -webkit-appearance: none;
                appearance: none;
                font: inherit;
                cursor: grab;
                background: transparent;
                transition:
                    color var(--transition-time-medium) ease,
                    box-shadow var(--transition-time-medium) ease,
                    outline var(--transition-time-medium) ease,
                    background var(--transition-time-medium) ease,
                    border var(--transition-time-medium) ease;
            }

            input[type="range"]:hover {
                z-index: 10;
                box-shadow: var(--input-range-hover-shadow);
            }

            input[type="range"]:focus {
                box-shadow: none;
                outline: none;
            }

            input[type="range"]:disabled:hover {
                cursor: unset;
            }

            input[type="range"]::-webkit-slider-runnable-track {
                box-sizing: border-box;
                height: 0.5em;
                border: 1px solid transparent;
                border-radius: 0.5em;
                background: var(--input-range-bg);
            }
            input[type="range"]::-moz-range-track {
                box-sizing: border-box;
                height: 0.5em;
                border: 1px solid transparent;
                border-radius: 0.5em;
                background: var(--input-range-bg);
            }

            input[type="range"]:hover::-webkit-slider-runnable-track,
            input[type="range"]:focus::-webkit-slider-runnable-track {
                border: 1px solid var(--input-range-hover-bg);
            }
            input[type="range"]:hover::-moz-range-track,
            input[type="range"]:focus::-moz-range-track {
                border: 1px solid var(--input-range-hover-bg);
            }

            input[type="range"]:disabled::-webkit-slider-runnable-track {
                background: var(--input-range-disabled-bg);
            }
            input[type="range"]:disabled::-moz-range-track {
                background: var(--input-range-disabled-bg);
            }

            input[type="range"]::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                height: 1em;
                width: 1em;
                border-radius: 0.5em;
                margin-top: -0.3em;
                background: var(--input-range-fg);
            }
            input[type="range"]::-moz-range-thumb {
                border: none;
                height: 1em;
                width: 1em;
                border-radius: 100%;
                margin-top: -0.3em;
                background: var(--input-range-fg);
            }

            input[type="range"]:focus::-webkit-slider-thumb {
                box-shadow: var(--input-range-handle-shadow);
            }
            input[type="range"]:focus::-moz-range-thumb {
                box-shadow: var(--input-range-handle-shadow);
            }
        `,
        ];
    }
    static get observedAttributes() {
        return ['disabled', 'min', 'max', 'step', 'value'];
    }
    get value() {
        return this.input.value;
    }
    set value(e) {
        this.input.value = e;
    }
    get valueAsNumber() {
        return this.input.valueAsNumber;
    }
    attributeChangedCallback(e, r, i) {
        if (this.input)
            switch (e) {
                case 'disabled':
                    this.input.disabled = i != null;
                    break;
                case 'min':
                    this.input.min = i ?? '';
                    break;
                case 'max':
                    this.input.max = i ?? '';
                    break;
                case 'step':
                    this.input.step = i ?? '';
                    break;
                case 'value':
                    this.value = i ?? '';
                    break;
            }
    }
    initialContentCallback() {
        (this.input.disabled = this.disabled),
            this.input.addEventListener('input', (e) => {
                e.stopPropagation(),
                    this.dispatchEvent(new CustomEvent('kc-ui-range:input', { composed: !0, bubbles: !0 }));
            });
    }
    render() {
        return _`<input
            type="range"
            min="${this.min}"
            max="${this.max}"
            step="${this.step}"
            value="${this.getAttribute('value')}">
        </input>`;
    }
};
P([L({ type: String })], Ve.prototype, 'name', 2),
    P([L({ type: String })], Ve.prototype, 'min', 2),
    P([L({ type: String })], Ve.prototype, 'max', 2),
    P([L({ type: String })], Ve.prototype, 'step', 2),
    P([L({ type: Boolean })], Ve.prototype, 'disabled', 2),
    P([Q('input', !0)], Ve.prototype, 'input', 2);
window.customElements.define('kc-ui-range', Ve);
var pr = class extends N {
    static {
        l(this, 'KCUIResizerElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                z-index: 999;
                user-select: none;
                display: block;
                width: 6px;
                margin-left: -6px;
                cursor: col-resize;
                background: transparent;
                opacity: 0;
                transition: opacity var(--transition-time-medium, 500) ease;
            }

            :host(:hover) {
                background: var(--resizer-bg, rebeccapurple);
                opacity: 1;
                transition: opacity var(--transition-time-short) ease;
            }

            :host(:hover.active),
            :host(.active) {
                background: var(--resizer-active-bg, rebeccapurple);
            }
        `,
        ];
    }
    initialContentCallback() {
        let t = this.previousElementSibling,
            e = this.nextElementSibling;
        this.addEventListener('mousedown', (r) => {
            let i = r.clientX,
                n = e.getBoundingClientRect().width;
            (document.body.style.cursor = 'col-resize'),
                (t.style.pointerEvents = 'none'),
                (t.style.userSelect = 'none'),
                (e.style.pointerEvents = 'none'),
                (e.style.userSelect = 'none'),
                (e.style.width = `${n}px`),
                (e.style.maxWidth = 'unset'),
                this.classList.add('active'),
                e.hasAttribute('collapsed') && (console.log('removing collapsed'), e.removeAttribute('collapsed'));
            let o = l((p) => {
                    let m = i - p.clientX,
                        b = ((n + m) * 100) / this.parentElement.getBoundingClientRect().width;
                    e.style.width = `${b}%`;
                }, 'mouse_move'),
                c = this.addDisposable(k(window, 'mousemove', o)),
                u = l((p) => {
                    (document.body.style.cursor = ''),
                        (t.style.pointerEvents = ''),
                        (t.style.userSelect = ''),
                        (e.style.pointerEvents = ''),
                        (e.style.userSelect = ''),
                        this.classList.remove('active'),
                        c.dispose();
                }, 'mouse_up');
            window.addEventListener('mouseup', u, { once: !0 });
        });
    }
};
window.customElements.define('kc-ui-resizer', pr);
var Ws = T`
    :host(.grow) {
        flex-basis: unset;
        flex-grow: 999;
    }

    :host(.shrink) {
        flex-grow: 0;
        flex-shrink: 1;
        width: unset;
    }

    :host:(.fixed) {
        flex-grow: 0;
        flex-shrink: 0;
    }
`,
    hr = class extends N {
        static {
            l(this, 'KCUIView');
        }
        static {
            this.styles = [
                ...N.styles,
                Ws,
                T`
            :host {
                flex-grow: 1;
                display: flex;
                overflow: hidden;
                flex-direction: column;
                position: relative;
            }
        `,
            ];
        }
        render() {
            return _`<slot></slot>`;
        }
    };
window.customElements.define('kc-ui-view', hr);
var dr = class extends N {
    static {
        l(this, 'KCUISplitView');
    }
    static {
        this.styles = [
            ...N.styles,
            Ws,
            T`
            :host {
                display: flex;
                height: 100%;
                overflow: hidden;
            }

            :host([horizontal]) {
                flex-direction: column;
                max-height: 100%;
            }

            :host([vertical]) {
                flex-direction: row;
                max-width: 100%;
            }
        `,
        ];
    }
    render() {
        return _`<slot></slot>`;
    }
};
window.customElements.define('kc-ui-split-view', dr);
var kt = class extends N {
    static {
        l(this, 'KCUITextFilterInputElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                display: flex;
                align-items: center;
                align-content: center;
                position: relative;
                border-bottom: 1px solid var(--grid-outline);
            }

            kc-ui-icon.before {
                pointer-events: none;
                position: absolute;
                left: 0;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                padding-left: 0.25em;
            }

            input {
                all: unset;
                display: block;
                width: 100%;
                max-width: 100%;
                border-radius: 0;
                padding: 0.4em;
                padding-left: 1.5em;
                text-align: left;
                font: inherit;
                background: var(--input-bg);
                color: var(--input-fg);
            }

            input:placeholder-shown + button {
                display: none;
            }

            button {
                all: unset;
                box-sizing: border-box;
                display: flex;
                align-items: center;
                color: var(--input-fg);
                padding: 0.25em;
            }

            button:hover {
                cursor: pointer;
                color: var(--input-accent);
            }
        `,
        ];
    }
    get value() {
        return this.input.value;
    }
    set value(e) {
        (this.input.value = e), this.input.dispatchEvent(new Event('input', { bubbles: !0, composed: !0 }));
    }
    initialContentCallback() {
        super.initialContentCallback(),
            this.button.addEventListener('click', (e) => {
                e.preventDefault(), e.stopPropagation(), (this.value = '');
            });
    }
    render() {
        return _`<kc-ui-icon class="flex before">search</kc-ui-icon>
            <input style="" type="text" placeholder="search" name="search" />
            <button type="button">
                <kc-ui-icon>close</kc-ui-icon>
            </button>`;
    }
};
P([Q('input', !0)], kt.prototype, 'input', 2), P([Q('button', !0)], kt.prototype, 'button', 2);
window.customElements.define('kc-ui-text-filter-input', kt);
var At = class extends N {
    static {
        l(this, 'KCUIToggleMenuElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            * {
                box-sizing: border-box;
            }

            button {
                all: unset;
                box-sizing: border-box;
                user-select: none;
                width: 100%;
                max-width: 100%;
                margin: unset;
                font: inherit;
                padding: 0.3em 0.6em 0.3em 0.6em;
                display: flex;
                align-items: flex-end;
                justify-content: left;
                border: 1px solid transparent;
                border-radius: 0.25em;
                font-weight: 300;
                font-size: 1em;
                background: var(--dropdown-bg);
                color: var(--dropdown-fg);
                transition:
                    color var(--transition-time-medium, 500) ease,
                    background var(--transition-time-medium, 500) ease;
            }

            button:hover {
                background: var(--dropdown-hover-bg);
                color: var(--dropdown-hover-fg);
                box-shadow: none;
                outline: none;
            }

            button kc-ui-icon {
                font-size: 1em;
                margin-top: 0.1em;
                margin-bottom: 0.1em;
            }

            button span {
                display: none;
                margin-left: 0.5em;
            }

            :host([visible]) button {
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
            }

            :host([visible]) button span {
                display: revert;
            }

            ::slotted(kc-ui-dropdown) {
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }
        `,
        ];
    }
    get dropdown() {
        return this.queryAssignedElements('dropdown', 'kc-ui-dropdown')[0];
    }
    get button() {
        return this.renderRoot.querySelector('button');
    }
    initialContentCallback() {
        this.button.addEventListener('click', (e) => {
            this.dropdown.toggle();
        }),
            this.addEventListener('kc-ui-dropdown:show', () => {
                this.visible = !0;
            }),
            this.addEventListener('kc-ui-dropdown:hide', () => {
                this.visible = !1;
            });
    }
    render() {
        return _`<button name="toggle" type="button" title="${this.title}">
                <kc-ui-icon>${this.icon ?? 'question-mark'}</kc-ui-icon>
                <span>${this.title}</span>
            </button>
            <slot name="dropdown"></slot>`;
    }
};
P([L({ type: String })], At.prototype, 'icon', 2), P([L({ type: Boolean })], At.prototype, 'visible', 2);
window.customElements.define('kc-ui-toggle-menu', At);
var Zs = `<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs/><symbol id="pcb_file" viewBox="0 0 48 48">
    <path d="M11,44C10.2,44 9.5,43.7 8.9,43.1C8.3,42.5 8,41.8 8,41L8,7C8,6.2 8.3,5.5 8.9,4.9C9.5,4.3 10.2,4 11,4L29.05,4L40,14.95L40,41C40,41.8 39.7,42.5 39.1,43.1C38.5,43.7 37.8,44 37,44L11,44ZM27.55,16.3L27.55,7L11,7L11,41L37,41L37,16.3L27.55,16.3ZM11,7L11,16.3L11,7L11,41L11,7Z"/>
    <path d="M20.231,37.681C20.231,37.681 20.231,36.001 20.231,36.001L18.007,36.001C17.437,36.001 16.936,35.792 16.509,35.365C16.081,34.937 15.872,34.437 15.872,33.867L15.872,31.643L13.693,31.643L13.693,29.008C13.693,29.008 15.872,29.008 15.872,29.008L15.872,26.63L13.693,26.63L13.693,23.995C13.693,23.995 15.872,23.995 15.872,23.995L15.872,21.771C15.872,21.201 16.081,20.701 16.509,20.273C16.936,19.846 17.437,19.636 18.007,19.636C18.007,19.636 20.231,19.636 20.231,19.636L20.231,17.566L22.865,17.566C22.865,17.566 22.865,19.636 22.865,19.636C22.865,19.636 25.244,19.636 25.244,19.636L25.244,17.566L27.878,17.566C27.878,17.566 27.878,19.636 27.878,19.636L30.102,19.636C30.672,19.636 31.173,19.846 31.6,20.273C32.028,20.701 32.237,21.201 32.237,21.771C32.237,21.771 32.237,23.995 32.237,23.995L34.307,23.995L34.307,26.63C34.307,26.63 32.237,26.63 32.237,26.63C32.237,26.63 32.237,29.008 32.237,29.008L34.307,29.008L34.307,31.643C34.307,31.643 32.237,31.643 32.237,31.643L32.237,33.867C32.237,34.437 32.028,34.937 31.6,35.365C31.173,35.792 30.672,36.001 30.102,36.001L27.878,36.001L27.878,38.181L25.244,38.181C25.244,38.181 25.244,36.001 25.244,36.001L22.865,36.001L22.865,38.181L20.231,38.181L20.231,37.681ZM29.602,33.367L29.602,22.271L18.507,22.271L18.507,33.367L29.602,33.367ZM20.694,24.595L27.279,24.595L27.279,31.179L20.694,31.179L20.694,24.595ZM23.329,28.545C23.329,28.545 24.644,28.545 24.644,28.545C24.644,28.545 24.644,27.229 24.644,27.229C24.644,27.229 23.329,27.229 23.329,27.229L23.329,28.545Z"/>
</symbol><symbol id="schematic_file" viewBox="0 0 48 48">
    <path d="M11,44C10.2,44 9.5,43.7 8.9,43.1C8.3,42.5 8,41.8 8,41L8,7C8,6.2 8.3,5.5 8.9,4.9C9.5,4.3 10.2,4 11,4L29.05,4L40,14.95L40,41C40,41.8 39.7,42.5 39.1,43.1C38.5,43.7 37.8,44 37,44L11,44ZM27.55,16.3L27.55,7L11,7L11,41L37,41L37,16.3L27.55,16.3ZM11,7L11,16.3L11,7L11,41L11,7Z"/>
    <path d="M18.256,26.367L15.377,26.367L15.377,23.367L18.256,23.367L18.256,23.184C18.256,22.155 18.784,21.198 19.654,20.648C20.524,20.098 21.615,20.033 22.544,20.475L24.69,21.494L24.69,19.353L27.69,19.353L27.69,22.92L32.411,25.164C33.457,25.661 34.123,26.715 34.123,27.873C34.123,29.031 33.457,30.086 32.411,30.583L27.69,32.827L27.69,36.394L24.69,36.394L24.69,34.252L22.544,35.272C21.615,35.714 20.524,35.648 19.654,35.099C18.784,34.549 18.256,33.592 18.256,32.563L18.256,32.38L15.377,32.38L15.377,29.38L18.256,29.38L18.256,26.367ZM21.256,32.563L31.123,27.873L21.256,23.184L21.256,32.563Z"/>
</symbol><symbol id="zoom_footprint" viewBox="0 0 48 48">
    <g>
        <path d="M33,38.5C34.567,38.5 35.875,37.975 36.925,36.925C37.975,35.875 38.5,34.567 38.5,33C38.5,31.433 37.975,30.125 36.925,29.075C35.875,28.025 34.567,27.5 33,27.5C31.433,27.5 30.125,28.025 29.075,29.075C28.025,30.125 27.5,31.433 27.5,33C27.5,34.567 28.025,35.875 29.075,36.925C30.125,37.975 31.433,38.5 33,38.5ZM43.2,45.3L37.842,39.95C37.147,40.417 36.392,40.792 35.575,41.075C34.758,41.358 33.9,41.5 33,41.5C30.639,41.5 28.632,40.673 26.979,39.019C25.326,37.365 24.5,35.357 24.5,32.994C24.5,30.631 25.327,28.625 26.981,26.975C28.635,25.325 30.643,24.5 33.006,24.5C35.369,24.5 37.375,25.326 39.025,26.979C40.675,28.632 41.5,30.639 41.5,33C41.5,33.9 41.358,34.758 41.075,35.575C40.792,36.392 40.417,37.147 39.95,37.842L45.3,43.2L43.2,45.3Z"/>
        <path d="M22.597,38L21,38L21,42L18,42L18,38L13,38C12.2,38 11.5,37.7 10.9,37.1C10.3,36.5 10,35.8 10,35L10,30L6,30L6,27L10,27L10,20.8L6,20.8L6,17.8L10,17.8L10,12.8C10,12 10.3,11.3 10.9,10.7C11.5,10.1 12.2,9.8 13,9.8L18,9.8L18,6L21,6L21,9.8L27.2,9.8L27.2,6L30.2,6L30.2,9.8L35.2,9.8C36,9.8 36.7,10.1 37.3,10.7C37.9,11.3 38.2,12 38.2,12.8L38.2,17.8L42,17.8L42,20.8L38.2,20.8L38.2,22.691C37.262,22.214 36.262,21.88 35.2,21.69L35.2,12.8L13,12.8L13,35L21.657,35C21.83,36.06 22.143,37.06 22.597,38ZM22.119,29.15L18.85,29.15L18.85,18.9L29.1,18.9L29.1,22.139C28.029,22.515 27.029,23.058 26.1,23.767L26.1,21.9L21.85,21.9L21.85,26.15L23.727,26.15C23.025,27.079 22.489,28.079 22.119,29.15Z"/>
    </g>
</symbol><symbol id="zoom_page" viewBox="0 0 48 48">
    <g>
        <path d="M9,41L24.75,41C25.417,41.7 26.158,42.3 26.975,42.8C27.792,43.3 28.683,43.7 29.65,44L9,44C8.2,44 7.5,43.7 6.9,43.1C6.3,42.5 6,41.8 6,41L6.02,9.006C6.02,8.206 6.32,7.506 6.92,6.906C7.52,6.306 8.22,6.006 9.02,6.006L27.07,6.006L38,14.95L38,22.65C37.533,22.417 37.05,22.217 36.55,22.05C36.05,21.883 35.533,21.75 35,21.65L35,16.3L25.55,16.3L25.57,9.006L9.02,9.006L9,16.3L9,41Z"/>
        <path d="M43.2,45.3L37.842,39.95C37.147,40.417 36.392,40.792 35.575,41.075C34.758,41.358 33.9,41.5 33,41.5C30.639,41.5 28.632,40.673 26.979,39.019C25.326,37.365 24.5,35.357 24.5,32.994C24.5,30.631 25.327,28.625 26.981,26.975C28.635,25.325 30.643,24.5 33.006,24.5C35.369,24.5 37.375,25.326 39.025,26.979C40.675,28.632 41.5,30.639 41.5,33C41.5,33.9 41.358,34.758 41.075,35.575C40.792,36.392 40.417,37.147 39.95,37.842L45.3,43.2L43.2,45.3ZM33,38.5C34.567,38.5 35.875,37.975 36.925,36.925C37.975,35.875 38.5,34.567 38.5,33C38.5,31.433 37.975,30.125 36.925,29.075C35.875,28.025 34.567,27.5 33,27.5C31.433,27.5 30.125,28.025 29.075,29.075C28.025,30.125 27.5,31.433 27.5,33C27.5,34.567 28.025,35.875 29.075,36.925C30.125,37.975 31.433,38.5 33,38.5Z"/>
    </g>
</symbol></svg>`;
var Ss = URL.createObjectURL(new Blob([Zs], { type: 'image/svg+xml' }));
function Ct(s) {
    return s[Symbol.iterator]().next().value;
}
l(Ct, 'first');
function* Ts(s, t) {
    let e = 0;
    for (let r of s) yield t(r, e), e++;
}
l(Ts, 'map');
function Dt(s) {
    let t = 0;
    for (let e of s) t++;
    return t;
}
l(Dt, 'length');
var ce = class {
        constructor(t, e = 1) {
            this.name = t;
            this.level = e;
        }
        static {
            l(this, 'Logger');
        }
        #e(t, ...e) {
            t(`%c${this.name}:%c`, 'color: ButtonText', 'color: inherit', ...e);
        }
        debug(...t) {
            this.level >= 2 && this.#e(console.debug, ...t);
        }
        info(...t) {
            this.level >= 1 && this.#e(console.info.bind(window.console), ...t);
        }
        warn(...t) {
            this.level >= 0 && this.#e(console.warn, ...t);
        }
        error(...t) {
            this.level >= 0 && this.#e(console.error, ...t);
        }
    },
    _n = new ce('kicanvas');
function Bt(...s) {
    _n.warn(...s);
}
l(Bt, 'warn');
var U = class s {
    static {
        l(this, 'Matrix3');
    }
    constructor(t) {
        if (t.length != 9) throw new Error(`Matrix3 requires 9 elements, got ${t}`);
        this.elements = new Float32Array(t);
    }
    static from_DOMMatrix(t) {
        return new s([t.m11, t.m12, t.m14, t.m21, t.m22, t.m24, t.m41, t.m42, t.m44]);
    }
    to_DOMMatrix() {
        let t = this.elements;
        return new DOMMatrix([t[0], t[3], t[1], t[4], t[6], t[7]]);
    }
    to_4x4_DOMMatrix() {
        let t = this.elements;
        return new DOMMatrix([t[0], t[1], 0, t[2], t[3], t[4], 0, t[5], 0, 0, 1, 0, t[6], t[7], 0, 1]);
    }
    static identity() {
        return new s([1, 0, 0, 0, 1, 0, 0, 0, 1]);
    }
    static orthographic(t, e) {
        return new s([2 / t, 0, 0, 0, -2 / e, 0, -1, 1, 1]);
    }
    copy() {
        return new s(this.elements);
    }
    set(t) {
        if (t.length != 9) throw new Error(`Matrix3 requires 9 elements, got ${t}`);
        this.elements.set(t);
    }
    transform(t) {
        let e = this.elements[0],
            r = this.elements[0 * 3 + 1],
            i = this.elements[1 * 3 + 0],
            n = this.elements[1 * 3 + 1],
            o = this.elements[2 * 3 + 0],
            c = this.elements[2 * 3 + 1],
            u = t.x,
            p = t.y,
            m = u * e + p * i + o,
            b = u * r + p * n + c;
        return new d(m, b);
    }
    *transform_all(t) {
        for (let e of t) yield this.transform(e);
    }
    static transform_all(t, e) {
        return t ? Array.from(t.transform_all(e)) : e;
    }
    multiply_self(t) {
        let e = this.elements[0],
            r = this.elements[0 * 3 + 1],
            i = this.elements[0 * 3 + 2],
            n = this.elements[1 * 3 + 0],
            o = this.elements[1 * 3 + 1],
            c = this.elements[1 * 3 + 2],
            u = this.elements[2 * 3 + 0],
            p = this.elements[2 * 3 + 1],
            m = this.elements[2 * 3 + 2],
            b = t.elements[0 * 3 + 0],
            M = t.elements[0 * 3 + 1],
            f = t.elements[0 * 3 + 2],
            V = t.elements[1 * 3 + 0],
            S = t.elements[1 * 3 + 1],
            y = t.elements[1 * 3 + 2],
            v = t.elements[2 * 3 + 0],
            te = t.elements[2 * 3 + 1],
            X = t.elements[2 * 3 + 2];
        return (
            (this.elements[0] = b * e + M * n + f * u),
            (this.elements[1] = b * r + M * o + f * p),
            (this.elements[2] = b * i + M * c + f * m),
            (this.elements[3] = V * e + S * n + y * u),
            (this.elements[4] = V * r + S * o + y * p),
            (this.elements[5] = V * i + S * c + y * m),
            (this.elements[6] = v * e + te * n + X * u),
            (this.elements[7] = v * r + te * o + X * p),
            (this.elements[8] = v * i + te * c + X * m),
            this
        );
    }
    multiply(t) {
        return this.copy().multiply_self(t);
    }
    inverse() {
        let t = this.elements[0],
            e = this.elements[0 * 3 + 1],
            r = this.elements[0 * 3 + 2],
            i = this.elements[1 * 3 + 0],
            n = this.elements[1 * 3 + 1],
            o = this.elements[1 * 3 + 2],
            c = this.elements[2 * 3 + 0],
            u = this.elements[2 * 3 + 1],
            p = this.elements[2 * 3 + 2],
            m = p * n - o * u,
            b = -p * i + o * c,
            M = u * i - n * c,
            V = 1 / (t * m + e * b + r * M);
        return new s([
            m * V,
            (-p * e + r * u) * V,
            (o * e - r * n) * V,
            b * V,
            (p * t - r * c) * V,
            (-o * t + r * i) * V,
            M * V,
            (-u * t + e * c) * V,
            (n * t - e * i) * V,
        ]);
    }
    static translation(t, e) {
        return new s([1, 0, 0, 0, 1, 0, t, e, 1]);
    }
    translate_self(t, e) {
        return this.multiply_self(s.translation(t, e));
    }
    translate(t, e) {
        return this.copy().translate_self(t, e);
    }
    static scaling(t, e) {
        return new s([t, 0, 0, 0, e, 0, 0, 0, 1]);
    }
    scale_self(t, e) {
        return this.multiply_self(s.scaling(t, e));
    }
    scale(t, e) {
        return this.copy().scale_self(t, e);
    }
    static rotation(t) {
        let e = new W(t).radians,
            r = Math.cos(e),
            i = Math.sin(e);
        return new s([r, -i, 0, i, r, 0, 0, 0, 1]);
    }
    rotate_self(t) {
        return this.multiply_self(s.rotation(t));
    }
    rotate(t) {
        return this.copy().rotate_self(t);
    }
    get absolute_translation() {
        return this.transform(new d(0, 0));
    }
    get absolute_rotation() {
        let t = this.transform(new d(0, 0));
        return this.transform(new d(1, 0)).sub(t).angle.normalize();
    }
};
var d = class s {
    static {
        l(this, 'Vec2');
    }
    constructor(t = 0, e) {
        this.set(t, e);
    }
    copy() {
        return new s(...this);
    }
    set(t, e) {
        let r = null;
        if (
            (le(t) && le(e)
                ? (r = t)
                : t instanceof s
                  ? ((r = t.x), (e = t.y))
                  : t instanceof Array
                    ? ((r = t[0]), (e = t[1]))
                    : t instanceof Object && Object.hasOwn(t, 'x')
                      ? ((r = t.x), (e = t.y))
                      : t == 0 && e == null && ((r = 0), (e = 0)),
            r == null || e == null)
        )
            throw new Error(`Invalid parameters x: ${t}, y: ${e}.`);
        (this.x = r), (this.y = e);
    }
    *[Symbol.iterator]() {
        yield this.x, yield this.y;
    }
    get magnitude() {
        return Math.sqrt(this.x ** 2 + this.y ** 2);
    }
    get squared_magnitude() {
        return this.x ** 2 + this.y ** 2;
    }
    get normal() {
        return new s(-this.y, this.x);
    }
    get angle() {
        return new W(Math.atan2(this.y, this.x));
    }
    get kicad_angle() {
        return this.x == 0 && this.y == 0
            ? new W(0)
            : this.y == 0
              ? this.x >= 0
                  ? new W(0)
                  : W.from_degrees(-180)
              : this.x == 0
                ? this.y >= 0
                    ? W.from_degrees(90)
                    : W.from_degrees(-90)
                : this.x == this.y
                  ? this.x >= 0
                      ? W.from_degrees(45)
                      : W.from_degrees(-135)
                  : this.x == -this.y
                    ? this.x >= 0
                        ? W.from_degrees(-45)
                        : W.from_degrees(135)
                    : this.angle;
    }
    normalize() {
        if (this.x == 0 && this.y == 0) return new s(0, 0);
        let t = this.magnitude,
            e = (this.x /= t),
            r = (this.y /= t);
        return new s(e, r);
    }
    equals(t) {
        return this.x == t?.x && this.y == t?.y;
    }
    add(t) {
        return new s(this.x + t.x, this.y + t.y);
    }
    sub(t) {
        return new s(this.x - t.x, this.y - t.y);
    }
    scale(t) {
        return new s(this.x * t.x, this.y * t.y);
    }
    rotate(t) {
        return U.rotation(t).transform(this);
    }
    multiply(t) {
        return le(t) ? new s(this.x * t, this.y * t) : new s(this.x * t.x, this.y * t.y);
    }
    resize(t) {
        return this.normalize().multiply(t);
    }
    cross(t) {
        return this.x * t.y - this.y * t.x;
    }
    static segment_intersect(t, e, r, i) {
        let n = e.sub(t),
            o = i.sub(r),
            c = r.sub(t),
            u = o.cross(n),
            p = o.cross(c),
            m = n.cross(c);
        return u == 0 || (u > 0 && (m < 0 || m > u || p < 0 || p > u)) || (u < 0 && (m < u || p < u || p > 0 || m > 0))
            ? null
            : new s(r.x + (m / u) * o.x, r.y + (m / u) * o.y);
    }
};
var W = class s {
    static {
        l(this, 'Angle');
    }
    #e;
    #t;
    static rad_to_deg(t) {
        return (t / Math.PI) * 180;
    }
    static deg_to_rad(t) {
        return (t / 180) * Math.PI;
    }
    static round(t) {
        return Math.round((t + Number.EPSILON) * 100) / 100;
    }
    constructor(t) {
        if (t instanceof s) return t;
        this.radians = t;
    }
    copy() {
        return new s(this.radians);
    }
    get radians() {
        return this.#e;
    }
    set radians(t) {
        (this.#e = t), (this.#t = s.round(s.rad_to_deg(t)));
    }
    get degrees() {
        return this.#t;
    }
    set degrees(t) {
        (this.#t = t), (this.#e = s.deg_to_rad(t));
    }
    static from_degrees(t) {
        return new s(s.deg_to_rad(t));
    }
    add(t) {
        let e = this.radians + new s(t).radians;
        return new s(e);
    }
    sub(t) {
        let e = this.radians - new s(t).radians;
        return new s(e);
    }
    normalize() {
        let t = s.round(this.degrees);
        for (; t < 0; ) t += 360;
        for (; t >= 360; ) t -= 360;
        return s.from_degrees(t);
    }
    normalize180() {
        let t = s.round(this.degrees);
        for (; t <= -180; ) t += 360;
        for (; t > 180; ) t -= 360;
        return s.from_degrees(t);
    }
    normalize720() {
        let t = s.round(this.degrees);
        for (; t < -360; ) t += 360;
        for (; t >= 360; ) t -= 360;
        return s.from_degrees(t);
    }
    negative() {
        return new s(-this.radians);
    }
    get is_vertical() {
        return this.degrees == 90 || this.degrees == 270;
    }
    get is_horizontal() {
        return this.degrees == 0 || this.degrees == 180;
    }
    rotate_point(t, e = new d(0, 0)) {
        let r = t.x - e.x,
            i = t.y - e.y,
            n = this.normalize();
        if (n.degrees != 0)
            if (n.degrees == 90) [r, i] = [i, -r];
            else if (n.degrees == 180) [r, i] = [-r, -i];
            else if (n.degrees == 270) [r, i] = [-i, r];
            else {
                let o = Math.sin(n.radians),
                    c = Math.cos(n.radians),
                    [u, p] = [r, i];
                (r = p * o + u * c), (i = p * c - u * o);
            }
        return (r += e.x), (i += e.y), new d(r, i);
    }
};
var O = class s {
    constructor(t = 0, e = 0, r = 0, i = 0, n) {
        this.x = t;
        this.y = e;
        this.w = r;
        this.h = i;
        this.context = n;
        this.w < 0 && ((this.w *= -1), (this.x -= this.w)), this.h < 0 && ((this.h *= -1), (this.y -= this.h));
    }
    static {
        l(this, 'BBox');
    }
    copy() {
        return new s(this.x, this.y, this.w, this.h, this.context);
    }
    static from_corners(t, e, r, i, n) {
        return r < t && ([t, r] = [r, t]), i < e && ([e, i] = [i, e]), new s(t, e, r - t, i - e, n);
    }
    static from_points(t, e) {
        if (t.length == 0) return new s(0, 0, 0, 0);
        let r = t[0],
            i = r.copy(),
            n = r.copy();
        for (let o of t)
            (i.x = Math.min(i.x, o.x)),
                (i.y = Math.min(i.y, o.y)),
                (n.x = Math.max(n.x, o.x)),
                (n.y = Math.max(n.y, o.y));
        return s.from_corners(i.x, i.y, n.x, n.y, e);
    }
    static combine(t, e) {
        let r = Number.POSITIVE_INFINITY,
            i = Number.POSITIVE_INFINITY,
            n = Number.NEGATIVE_INFINITY,
            o = Number.NEGATIVE_INFINITY;
        for (let c of t)
            c.valid &&
                ((r = Math.min(r, c.x)), (i = Math.min(i, c.y)), (n = Math.max(n, c.x2)), (o = Math.max(o, c.y2)));
        return r == Number.POSITIVE_INFINITY ||
            i == Number.POSITIVE_INFINITY ||
            n == Number.NEGATIVE_INFINITY ||
            o == Number.NEGATIVE_INFINITY
            ? new s(0, 0, 0, 0, e)
            : s.from_corners(r, i, n, o, e);
    }
    get valid() {
        return (this.w !== 0 || this.h !== 0) && this.w !== void 0 && this.h !== void 0;
    }
    get start() {
        return new d(this.x, this.y);
    }
    set start(t) {
        (this.x = t.x), (this.y = t.y);
    }
    get end() {
        return new d(this.x + this.w, this.y + this.h);
    }
    set end(t) {
        (this.x2 = t.x), (this.y2 = t.y);
    }
    get top_left() {
        return this.start;
    }
    get top_right() {
        return new d(this.x + this.w, this.y);
    }
    get bottom_left() {
        return new d(this.x, this.y + this.h);
    }
    get bottom_right() {
        return this.end;
    }
    get x2() {
        return this.x + this.w;
    }
    set x2(t) {
        (this.w = t - this.x), this.w < 0 && ((this.w *= -1), (this.x -= this.w));
    }
    get y2() {
        return this.y + this.h;
    }
    set y2(t) {
        (this.h = t - this.y), this.h < 0 && ((this.h *= -1), (this.y -= this.h));
    }
    get center() {
        return new d(this.x + this.w / 2, this.y + this.h / 2);
    }
    transform(t) {
        let e = t.transform(this.start),
            r = t.transform(this.end);
        return s.from_corners(e.x, e.y, r.x, r.y, this.context);
    }
    grow(t, e) {
        return (e ??= t), new s(this.x - t, this.y - e, this.w + t * 2, this.h + e * 2, this.context);
    }
    scale(t) {
        return s.from_points([this.start.multiply(t), this.end.multiply(t)], this.context);
    }
    mirror_vertical() {
        return new s(this.x, -this.y, this.w, -this.h);
    }
    contains(t) {
        return this.contains_point(t.start) && this.contains_point(t.end);
    }
    contains_point(t) {
        return t.x >= this.x && t.x <= this.x2 && t.y >= this.y && t.y <= this.y2;
    }
    constrain_point(t) {
        let e = Math.min(Math.max(t.x, this.x), this.x2),
            r = Math.min(Math.max(t.y, this.y), this.y2);
        return new d(e, r);
    }
    intersect_segment(t, e) {
        if (this.contains_point(t)) return null;
        let r = [this.top_left, this.bottom_left],
            i = [this.top_right, this.bottom_right],
            n = [this.top_left, this.top_right],
            o = [this.bottom_left, this.bottom_right],
            c = t,
            u = e;
        for (let p of [r, i, n, o]) {
            let m = d.segment_intersect(t, e, ...p);
            m && m.sub(c).squared_magnitude < u.sub(c).squared_magnitude && u.set(m);
        }
        return c.equals(u) ? null : u;
    }
};
var z = class s {
    constructor(t, e, r, i, n) {
        this.center = t;
        this.radius = e;
        this.start_angle = r;
        this.end_angle = i;
        this.width = n;
    }
    static {
        l(this, 'Arc');
    }
    static from_three_points(t, e, r, i = 1) {
        let o = Mn(new d(t.x * 1e6, t.y * 1e6), new d(e.x * 1e6, e.y * 1e6), new d(r.x * 1e6, r.y * 1e6));
        (o.x /= 1e6), (o.y /= 1e6);
        let c = o.sub(e).magnitude,
            u = t.sub(o),
            p = e.sub(o),
            m = r.sub(o),
            b = u.angle,
            M = p.angle,
            f = m.angle,
            V = M.sub(b).normalize180(),
            S = f.sub(M).normalize180(),
            y = V.add(S);
        return (f = b.add(y)), new s(o, c, b, f, i);
    }
    static from_center_start_end(t, e, r, i) {
        let n = e.sub(t).magnitude,
            o = e.sub(t),
            c = r.sub(t),
            u = o.kicad_angle,
            p = c.kicad_angle;
        return (
            p.degrees == u.degrees && (p.degrees = u.degrees + 360),
            u.degrees > p.degrees &&
                (p.degrees < 0 ? (p = p.normalize()) : (u = u.normalize().sub(W.from_degrees(-360)))),
            new s(t, n, u, p, i)
        );
    }
    get start_radial() {
        return this.start_angle.rotate_point(new d(this.radius, 0));
    }
    get start_point() {
        return this.center.add(this.start_radial);
    }
    get end_radial() {
        return this.end_angle.rotate_point(new d(this.radius, 0));
    }
    get end_point() {
        return this.center.add(this.end_radial);
    }
    get mid_angle() {
        return new W((this.start_angle.radians + this.end_angle.radians) / 2);
    }
    get mid_radial() {
        return this.mid_angle.rotate_point(new d(this.radius, 0));
    }
    get mid_point() {
        return this.center.add(this.mid_radial);
    }
    get arc_angle() {
        return this.end_angle.sub(this.start_angle);
    }
    to_polyline() {
        let t = [],
            e = this.start_angle.radians,
            r = this.end_angle.radians;
        e > r && ([r, e] = [e, r]);
        for (let n = e; n < r; n += Math.PI / 32)
            t.push(new d(this.center.x + Math.cos(n) * this.radius, this.center.y + Math.sin(n) * this.radius));
        let i = new d(this.center.x + Math.cos(r) * this.radius, this.center.y + Math.sin(r) * this.radius);
        return i.equals(t[t.length - 1]) || t.push(i), t;
    }
    to_polygon() {
        let t = this.to_polyline();
        return t.push(this.center), t;
    }
    get bbox() {
        let t = [this.start_point, this.mid_point, this.end_point];
        return (
            this.start_angle.degrees < 0 &&
                this.end_angle.degrees >= 0 &&
                t.push(this.center.add(new d(this.radius, 0))),
            this.start_angle.degrees < 90 &&
                this.end_angle.degrees >= 90 &&
                t.push(this.center.add(new d(0, this.radius))),
            this.start_angle.degrees < 180 &&
                this.end_angle.degrees >= 180 &&
                t.push(this.center.add(new d(-this.radius, 0))),
            this.start_angle.degrees < 270 &&
                this.end_angle.degrees >= 270 &&
                t.push(this.center.add(new d(0, this.radius))),
            this.start_angle.degrees < 360 &&
                this.end_angle.degrees >= 360 &&
                t.push(this.center.add(new d(0, this.radius))),
            O.from_points(t)
        );
    }
};
function Mn(s, t, e) {
    let r = Math.SQRT1_2,
        i = new d(0, 0),
        n = t.y - s.y,
        o = t.x - s.x,
        c = e.y - t.y,
        u = e.x - t.x;
    if ((o == 0 && c == 0) || (n == 0 && u == 0)) return (i.x = (s.x + e.x) / 2), (i.y = (s.y + e.y) / 2), i;
    o == 0 && (o = Number.EPSILON), u == 0 && (u = -Number.EPSILON);
    let p = n / o,
        m = c / u,
        b = p * new d(0.5 / n, 0.5 / o).magnitude,
        M = m * new d(0.5 / c, 0.5 / u).magnitude;
    if (p == m) {
        if (s == e) return (i.x = (s.x + t.x) / 2), (i.y = (s.y + t.y) / 2), i;
        (p += Number.EPSILON), (m -= Number.EPSILON);
    }
    p == 0 && (p = Number.EPSILON);
    let f = p * m * (s.y - e.y),
        V = f * Math.sqrt(((b / p) * b) / p + ((M / m) * M) / m + (r / (s.y - e.y)) * (r / (s.y - e.y))),
        S = m * (s.x + t.x),
        y = S * Math.sqrt(((M / m) * M) / m + ((r / (s.x + t.x)) * r) / (s.x + t.x)),
        v = p * (t.x + e.x),
        te = v * Math.sqrt(((b / p) * b) / p + ((r / (t.x + e.x)) * r) / (t.x + e.x)),
        X = 2 * (m - p),
        x = 2 * Math.sqrt(M * M + b * b),
        rt = f + S - v,
        ye = Math.sqrt(V * V + y * y + te * te),
        C = (f + S - v) / X,
        se = C * Math.sqrt(((ye / rt) * ye) / rt + ((x / X) * x) / X),
        C3 = (s.x + t.x) / 2 - C,
        ss = Math.sqrt(1 / 8 + se * se),
        ns = C3 / p,
        os = ns * Math.sqrt(((ss / C3) * ss) / C3 + ((b / p) * b) / p),
        Ht = ns + (s.y + t.y) / 2,
        as = Math.sqrt(os * os + 1 / 8),
        ls = Math.floor((C + 50) / 100) * 100,
        cs = Math.floor((Ht + 50) / 100) * 100,
        Rs = Math.floor((C + 5) / 10) * 10,
        us = Math.floor((Ht + 5) / 10) * 10;
    return (
        Math.abs(ls - C) < se && Math.abs(cs - Ht) < as
            ? ((i.x = ls), (i.y = cs))
            : Math.abs(Rs - C) < se && Math.abs(us - Ht) < as
              ? ((i.x = Rs), (i.y = us))
              : ((i.x = C), (i.y = Ht)),
        i
    );
}
l(Mn, 'arc_center_from_three_points');
var I2 = class {
    constructor(t = new d(0, 0), e = new d(0, 0), r = 1, i = new W(0)) {
        this.viewport_size = t;
        this.center = e;
        this.zoom = r;
        this.rotation = i;
    }
    static {
        l(this, 'Camera2');
    }
    translate(t) {
        (this.center.x += t.x), (this.center.y += t.y);
    }
    rotate(t) {
        this.rotation = this.rotation.add(t);
    }
    get matrix() {
        let t = this.viewport_size.x / 2,
            e = this.viewport_size.y / 2,
            r = this.center.x - this.center.x * this.zoom,
            i = this.center.y - this.center.y * this.zoom,
            n = -(this.center.x - t) + r,
            o = -(this.center.y - e) + i;
        return U.translation(n, o).rotate_self(this.rotation).scale_self(this.zoom, this.zoom);
    }
    get bbox() {
        let t = this.matrix.inverse(),
            e = t.transform(new d(0, 0)),
            r = t.transform(new d(this.viewport_size.x, this.viewport_size.y));
        return new O(e.x, e.y, r.x - e.x, r.y - e.y);
    }
    set bbox(t) {
        let e = this.viewport_size.x / t.w,
            r = this.viewport_size.y / t.h,
            i = t.x + t.w / 2,
            n = t.y + t.h / 2;
        (this.zoom = Math.min(e, r)), this.center.set(i, n);
    }
    get top() {
        return this.bbox.y;
    }
    get bottom() {
        return this.bbox.y2;
    }
    get left() {
        return this.bbox.x;
    }
    get right() {
        return this.bbox.x2;
    }
    apply_to_canvas(t) {
        this.viewport_size.set(t.canvas.clientWidth, t.canvas.clientHeight);
        let e = U.from_DOMMatrix(t.getTransform());
        e.multiply_self(this.matrix), t.setTransform(e.to_DOMMatrix());
    }
    screen_to_world(t) {
        return this.matrix.inverse().transform(t);
    }
    world_to_screen(t) {
        return this.matrix.transform(t);
    }
};
var h = class s {
    constructor(t, e, r, i = 1) {
        this.r = t;
        this.g = e;
        this.b = r;
        this.a = i;
    }
    static {
        l(this, 'Color');
    }
    copy() {
        return new s(this.r, this.g, this.b, this.a);
    }
    static get transparent_black() {
        return new s(0, 0, 0, 0);
    }
    static get black() {
        return new s(0, 0, 0, 1);
    }
    static get white() {
        return new s(1, 1, 1, 1);
    }
    static from_css(t) {
        let e, r, i, n;
        if (t[0] == '#')
            (t = t.slice(1)),
                t.length == 3 && (t = `${t[0]}${t[0]}${t[1]}${t[1]}${t[2]}${t[2]}`),
                t.length == 6 && (t = `${t}FF`),
                ([e, r, i, n] = [
                    parseInt(t.slice(0, 2), 16) / 255,
                    parseInt(t.slice(2, 4), 16) / 255,
                    parseInt(t.slice(4, 6), 16) / 255,
                    parseInt(t.slice(6, 8), 16) / 255,
                ]);
        else if (t.startsWith('rgb')) {
            t.startsWith('rgba') || (t = `rgba(${t.slice(4, -1)}, 1)`), (t = t.trim().slice(5, -1));
            let o = t.split(',');
            if (o.length != 4) throw new Error(`Invalid color ${t}`);
            [e, r, i, n] = [parseFloat(o[0]) / 255, parseFloat(o[1]) / 255, parseFloat(o[2]) / 255, parseFloat(o[3])];
        } else throw new Error(`Unable to parse CSS color string ${t}`);
        return new s(e, r, i, n);
    }
    to_css() {
        return `rgba(${this.r_255}, ${this.g_255}, ${this.b_255}, ${this.a})`;
    }
    to_array() {
        return [this.r, this.g, this.b, this.a];
    }
    get r_255() {
        return Math.round(this.r * 255);
    }
    set r_255(t) {
        this.r = t / 255;
    }
    get g_255() {
        return Math.round(this.g * 255);
    }
    set g_255(t) {
        this.g = t / 255;
    }
    get b_255() {
        return Math.round(this.b * 255);
    }
    set b_255(t) {
        this.b = t / 255;
    }
    get is_transparent_black() {
        return this.r == 0 && this.g == 0 && this.b == 0 && this.a == 0;
    }
    with_alpha(t) {
        let e = this.copy();
        return (e.a = t), e;
    }
    desaturate() {
        if (this.r == this.g && this.r == this.b) return this;
        let [t, e, r] = fn(this.r, this.g, this.b);
        return new s(...Nn(t, 0, r));
    }
    mix(t, e) {
        return new s(t.r * (1 - e) + this.r * e, t.g * (1 - e) + this.g * e, t.b * (1 - e) + this.b * e, this.a);
    }
};
function fn(s, t, e) {
    let r = Math.max(s, t, e),
        i = Math.min(s, t, e),
        n = (i + r) / 2,
        o = r - i,
        [c, u] = [NaN, 0];
    if (o !== 0) {
        switch (((u = n === 0 || n === 1 ? 0 : (r - n) / Math.min(n, 1 - n)), r)) {
            case s:
                c = (t - e) / o + (t < e ? 6 : 0);
                break;
            case t:
                c = (e - s) / o + 2;
                break;
            case e:
                c = (s - t) / o + 4;
        }
        c = c * 60;
    }
    return [c, u * 100, n * 100];
}
l(fn, 'rgb_to_hsl');
function Nn(s, t, e) {
    (s = s % 360), s < 0 && (s += 360), (t /= 100), (e /= 100);
    function r(i) {
        let n = (i + s / 30) % 12,
            o = t * Math.min(e, 1 - e);
        return e - o * Math.max(-1, Math.min(n - 3, 9 - n, 1));
    }
    return l(r, 'f'), [r(0), r(8), r(4)];
}
l(Nn, 'hsl_to_rgb');
var ys = '',
    E = class {
        constructor(t, e = null) {
            this.type = t;
            this.value = e;
        }
        static {
            l(this, 'Token');
        }
        static {
            this.OPEN = Symbol('opn');
        }
        static {
            this.CLOSE = Symbol('clo');
        }
        static {
            this.ATOM = Symbol('atm');
        }
        static {
            this.NUMBER = Symbol('num');
        }
        static {
            this.STRING = Symbol('str');
        }
    };
function A2(s) {
    return s >= '0' && s <= '9';
}
l(A2, 'is_digit');
function Xs(s) {
    return (s >= 'A' && s <= 'Z') || (s >= 'a' && s <= 'z');
}
l(Xs, 'is_alpha');
function k2(s) {
    return (
        s === ys ||
        s === ' ' ||
        s ===
            `
` ||
        s === '\r' ||
        s === '	'
    );
}
l(k2, 'is_whitespace');
function mr(s) {
    return (
        Xs(s) ||
        A2(s) ||
        ['_', '-', ':', '!', '.', '[', ']', '{', '}', '@', '*', '/', '&', '#', '%', '+', '=', '~', '$'].includes(s)
    );
}
l(mr, 'is_atom');
function $t(s, t) {
    let e = s.slice(0, t).lastIndexOf(`
`);
    e < 0 && (e = 0);
    let r = s.slice(t).indexOf(`
`);
    return r < 0 && (r = 20), s.slice(e, t + r);
}
l($t, 'error_context');
function* Vn(s) {
    let t = new E(E.OPEN),
        e = new E(E.CLOSE),
        r = 0,
        i = 0,
        n = !1;
    for (let o = 0; o < s.length + 1; o++) {
        let c = o < s.length ? s[o] : ys;
        if (r == 0)
            if (c === '(') {
                yield t;
                continue;
            } else if (c === ')') {
                yield e;
                continue;
            } else if (c === '"') {
                (r = 1), (i = o);
                continue;
            } else if (c === '-' || c == '+' || A2(c)) {
                (r = 2), (i = o);
                continue;
            } else if (Xs(c) || ['*', '&', '$', '/', '%'].includes(c)) {
                (r = 3), (i = o);
                continue;
            } else {
                if (k2(c)) continue;
                throw new Error(`Unexpected character at index ${o}: ${c}
Context: ${$t(s, o)}`);
            }
        else if (r == 3) {
            if (mr(c)) continue;
            if (c === ')' || k2(c)) yield new E(E.ATOM, s.substring(i, o)), (r = 0), c === ')' && (yield e);
            else
                throw new Error(`Unexpected character while tokenizing atom at index ${o}: ${c}
Context: ${$t(s, o)}`);
        } else if (r == 2) {
            if (c === '.' || A2(c)) continue;
            if (c.toLowerCase() === 'x') {
                r = 4;
                continue;
            } else if (['+', '-', 'a', 'b', 'c', 'd', 'e', 'f'].includes(c.toLowerCase())) {
                r = 3;
                continue;
            } else if (mr(c)) {
                r = 3;
                continue;
            } else if (c === ')' || k2(c)) {
                yield new E(E.NUMBER, parseFloat(s.substring(i, o))), (r = 0), c === ')' && (yield e);
                continue;
            } else
                throw new Error(`Unexpected character at index ${o}: ${c}, expected numeric.
Context: ${$t(s, o)}`);
        } else if (r == 4) {
            if (A2(c) || ['a', 'b', 'c', 'd', 'e', 'f', '_'].includes(c.toLowerCase())) continue;
            if (c === ')' || k2(c)) {
                let u = s.substring(i, o).replace('_', '');
                yield new E(E.NUMBER, Number.parseInt(u, 16)), (r = 0), c === ')' && (yield e);
                continue;
            } else if (mr(c)) {
                r = 3;
                continue;
            } else
                throw new Error(`Unexpected character at index ${o}: ${c}, expected hexadecimal.
Context: ${$t(s, o)}`);
        } else if (r == 1)
            if (!n && c === '"') {
                yield new E(
                    E.STRING,
                    s
                        .substring((i ?? 0) + 1, o)
                        .replaceAll(
                            '\\n',
                            `
`,
                        )
                        .replaceAll('\\\\', '\\'),
                ),
                    (r = 0),
                    (n = !1);
                continue;
            } else if (!n && c === '\\') {
                n = !0;
                continue;
            } else {
                n = !1;
                continue;
            }
        else
            throw new Error(`Unknown tokenizer state ${r}
Context: ${$t(s, o)}`);
    }
}
l(Vn, 'tokenize');
function* Os(s) {
    let t, e;
    for (;;)
        switch (((e = s.next()), (t = e.value), t?.type)) {
            case E.ATOM:
            case E.STRING:
            case E.NUMBER:
                yield t.value;
                break;
            case E.OPEN:
                yield Array.from(Os(s));
                break;
            case E.CLOSE:
            case void 0:
                return;
        }
}
l(Os, 'listify_tokens');
function Us(s) {
    let t = Vn(s);
    return Array.from(Os(t));
}
l(Us, 'listify');
var br = new ce('kicanvas:parser');
var R = {
        any(s, t, e) {
            return e;
        },
        boolean(s, t, e) {
            switch (e) {
                case 'false':
                case 'no':
                    return !1;
                case 'true':
                case 'yes':
                    return !0;
                default:
                    return !!e;
            }
        },
        string(s, t, e) {
            if (G(e)) return e;
        },
        number(s, t, e) {
            if (le(e)) return e;
        },
        item(s, ...t) {
            return (e, r, i) => new s(i, ...t);
        },
        object(s, ...t) {
            return (e, r, i) => {
                let n = {};
                return s !== null && (n = e[r] ?? s ?? {}), { ...n, ...g(i, a.start(r), ...t) };
            };
        },
        vec2(s, t, e) {
            let r = e;
            return new d(r[1], r[2]);
        },
        color(s, t, e) {
            let r = e;
            return new h(r[1] / 255, r[2] / 255, r[3] / 255, r[4]);
        },
    },
    a = {
        start(s) {
            return { kind: 0, name: s, fn: R.string };
        },
        positional(s, t = R.any) {
            return { kind: 1, name: s, fn: t };
        },
        pair(s, t = R.any) {
            return { kind: 2, name: s, accepts: [s], fn: (e, r, i) => t(e, r, i[1]) };
        },
        list(s, t = R.any) {
            return { kind: 3, name: s, accepts: [s], fn: (e, r, i) => i.slice(1).map((n) => t(e, r, n)) };
        },
        collection(s, t, e = R.any) {
            return {
                kind: 5,
                name: s,
                accepts: [t],
                fn: (r, i, n) => {
                    let o = r[i] ?? [];
                    return o.push(e(r, i, n)), o;
                },
            };
        },
        mapped_collection(s, t, e, r = R.any) {
            return {
                kind: 5,
                name: s,
                accepts: [t],
                fn: (i, n, o) => {
                    let c = i[n] ?? new Map(),
                        u = r(i, n, o),
                        p = e(u);
                    return c.set(p, u), c;
                },
            };
        },
        dict(s, t, e = R.any) {
            return {
                kind: 5,
                name: s,
                accepts: [t],
                fn: (r, i, n) => {
                    let o = n,
                        c = r[i] ?? {};
                    return (c[o[1]] = e(r, i, o[2])), c;
                },
            };
        },
        atom(s, t) {
            let e;
            return (
                t ? (e = R.string) : ((e = R.boolean), (t = [s])),
                {
                    kind: 4,
                    name: s,
                    accepts: t,
                    fn(r, i, n) {
                        return Array.isArray(n) && n.length == 1 && (n = n[0]), e(r, i, n);
                    },
                }
            );
        },
        expr(s, t = R.any) {
            return { kind: 6, name: s, accepts: [s], fn: t };
        },
        object(s, t, ...e) {
            return a.expr(s, R.object(t, ...e));
        },
        item(s, t, ...e) {
            return a.expr(s, R.item(t, ...e));
        },
        vec2(s) {
            return a.expr(s, R.vec2);
        },
        color(s = 'color') {
            return a.expr(s, R.color);
        },
    };
function g(s, ...t) {
    G(s) &&
        (br.info(`Parsing expression with ${s.length} chars`),
        (s = Us(s)),
        s.length == 1 && Array.isArray(s[0]) && (s = s[0]));
    let e = new Map(),
        r,
        i = 0;
    for (let o of t)
        if (o.kind == 0) r = o;
        else if (o.kind == 1) e.set(i, o), i++;
        else for (let c of o.accepts) e.set(c, o);
    if (r) {
        let o = G2(r.name),
            c = s.at(0);
        if (!o.includes(c)) throw new Error(`Expression must start with ${r.name} found ${c} in ${s}`);
        s = s.slice(1);
    }
    let n = {};
    i = 0;
    for (let o of s) {
        let c = null;
        if ((G(o) && (c = e.get(o)), !c && (G(o) || le(o)))) {
            if (((c = e.get(i)), !c)) {
                br.warn(`no def for bare element ${o} at position ${i} in expression ${s}`);
                continue;
            }
            i++;
        }
        if ((!c && Array.isArray(o) && (c = e.get(o[0])), !c)) {
            br.warn(`No def found for element ${o} in expression ${s}`);
            continue;
        }
        let u = c.fn(n, c.name, o);
        n[c.name] = u;
    }
    return n;
}
l(g, 'parse_expr');
function _r(s) {
    let t = {
        dblquote: '"',
        quote: "'",
        lt: '<',
        gt: '>',
        backslash: '\\',
        slash: '/',
        bar: '|',
        comma: ',',
        colon: ':',
        space: ' ',
        dollar: '$',
        tab: '	',
        return: `
`,
        brace: '{',
    };
    for (let [e, r] of Object.entries(t)) s = s.replaceAll('{' + e + '}', r);
    return s;
}
l(_r, 'unescape_string');
function Ae(s, t) {
    return (
        (s = _r(s)),
        t === void 0 ||
            (s = s.replaceAll(/(\$\{(.+?)\})/g, (e, r, i) => {
                let n = t.resolve_text_var(i);
                return n === void 0 ? r : n;
            })),
        s
    );
}
l(Ae, 'expand_text_vars');
var H = class s {
        constructor(t) {
            this.position = new d(0, 0);
            this.rotation = 0;
            this.unlocked = !1;
            if (t) {
                let e = g(
                    t,
                    a.start('at'),
                    a.positional('x', R.number),
                    a.positional('y', R.number),
                    a.positional('rotation', R.number),
                    a.atom('unlocked'),
                );
                this.position.set(e.x, e.y),
                    (this.rotation = e.rotation ?? this.rotation),
                    (this.unlocked = e.unlocked ?? this.unlocked);
            }
        }
        static {
            l(this, 'At');
        }
        copy() {
            let t = new s();
            return (t.position = this.position.copy()), (t.rotation = this.rotation), (t.unlocked = this.unlocked), t;
        }
    },
    Fs = {
        User: [431.8, 279.4],
        A0: [1189, 841],
        A1: [841, 594],
        A2: [594, 420],
        A3: [420, 297],
        A4: [297, 210],
        A5: [210, 148],
        A: [279.4, 215.9],
        B: [431.8, 279.4],
        C: [558.8, 431.8],
        D: [863.6, 558.8],
        E: [1117.6, 863.6],
        USLetter: [279.4, 215.9],
        USLegal: [355.6, 215.9],
        USLedger: [431.8, 279.4],
    },
    lt = class {
        constructor(t) {
            this.portrait = !1;
            Object.assign(
                this,
                g(
                    t,
                    a.start('paper'),
                    a.atom('size', Object.keys(Fs)),
                    a.positional('width', R.number),
                    a.positional('height', R.number),
                    a.atom('portrait'),
                ),
            );
            let e = Fs[this.size];
            !this.width && e && (this.width = e[0]),
                !this.height && e && (this.height = e[1]),
                this.size != 'User' && this.portrait && ([this.width, this.height] = [this.height, this.width]);
        }
        static {
            l(this, 'Paper');
        }
    },
    Fe = class {
        constructor(t) {
            this.title = '';
            this.date = '';
            this.rev = '';
            this.company = '';
            this.comment = {};
            t &&
                Object.assign(
                    this,
                    g(
                        t,
                        a.start('title_block'),
                        a.pair('title', R.string),
                        a.pair('date', R.string),
                        a.pair('rev', R.string),
                        a.pair('company', R.string),
                        a.expr('comment', (e, r, i) => {
                            let n = i,
                                o = e[r] ?? {};
                            return (o[n[1]] = n[2]), o;
                        }),
                    ),
                );
        }
        static {
            l(this, 'TitleBlock');
        }
        resolve_text_var(t) {
            return new Map([
                ['ISSUE_DATE', this.date],
                ['REVISION', this.rev],
                ['TITLE', this.title],
                ['COMPANY', this.company],
                ['COMMENT1', this.comment[1] ?? ''],
                ['COMMENT2', this.comment[2] ?? ''],
                ['COMMENT3', this.comment[3] ?? ''],
                ['COMMENT4', this.comment[4] ?? ''],
                ['COMMENT5', this.comment[5] ?? ''],
                ['COMMENT6', this.comment[6] ?? ''],
                ['COMMENT7', this.comment[7] ?? ''],
                ['COMMENT8', this.comment[8] ?? ''],
                ['COMMENT9', this.comment[9] ?? ''],
            ]).get(t);
        }
    },
    J = class s {
        constructor(t) {
            this.font = new C2();
            this.justify = new D2();
            this.hide = !1;
            t &&
                Object.assign(
                    this,
                    g(t, a.start('effects'), a.item('font', C2), a.item('justify', D2), a.atom('hide'), a.color()),
                );
        }
        static {
            l(this, 'Effects');
        }
        copy() {
            let t = new s();
            return (t.font = this.font.copy()), (t.justify = this.justify.copy()), (t.hide = this.hide), t;
        }
    },
    C2 = class s {
        constructor(t) {
            this.size = new d(1.27, 1.27);
            this.thickness = 0;
            this.bold = !1;
            this.italic = !1;
            this.color = h.transparent_black;
            t &&
                (Object.assign(
                    this,
                    g(
                        t,
                        a.start('font'),
                        a.pair('face', R.string),
                        a.vec2('size'),
                        a.pair('thickness', R.number),
                        a.atom('bold'),
                        a.atom('italic'),
                        a.pair('line_spacing', R.number),
                        a.color(),
                    ),
                ),
                ([this.size.x, this.size.y] = [this.size.y, this.size.x]));
        }
        static {
            l(this, 'Font');
        }
        copy() {
            let t = new s();
            return (
                (t.face = this.face),
                (t.size = this.size.copy()),
                (t.thickness = this.thickness),
                (t.bold = this.bold),
                (t.italic = this.italic),
                t
            );
        }
    },
    D2 = class s {
        constructor(t) {
            this.horizontal = 'center';
            this.vertical = 'center';
            this.mirror = !1;
            t &&
                Object.assign(
                    this,
                    g(
                        t,
                        a.start('justify'),
                        a.atom('horizontal', ['left', 'right']),
                        a.atom('vertical', ['top', 'bottom']),
                        a.atom('mirror'),
                    ),
                );
        }
        static {
            l(this, 'Justify');
        }
        copy() {
            let t = new s();
            return (t.horizontal = this.horizontal), (t.vertical = this.vertical), (t.mirror = this.mirror), t;
        }
    },
    q = class {
        constructor(t) {
            this.type = 'default';
            Object.assign(
                this,
                g(t, a.start('stroke'), a.pair('width', R.number), a.pair('type', R.string), a.color()),
            );
        }
        static {
            l(this, 'Stroke');
        }
    };
var ge = class {
        constructor(t, e) {
            this.filename = t;
            this.title_block = new Fe();
            this.properties = new Map();
            this.layers = [];
            this.nets = [];
            this.footprints = [];
            this.zones = [];
            this.segments = [];
            this.vias = [];
            this.drawings = [];
            this.groups = [];
            Object.assign(
                this,
                g(
                    e,
                    a.start('kicad_pcb'),
                    a.pair('version', R.number),
                    a.pair('generator', R.string),
                    a.object('general', {}, a.pair('thickness', R.number)),
                    a.item('paper', lt),
                    a.item('title_block', Fe),
                    a.list('layers', R.item(Vr)),
                    a.item('setup', gr),
                    a.mapped_collection('properties', 'property', (r) => r.name, R.item(Mr, this)),
                    a.collection('nets', 'net', R.item(B2)),
                    a.collection('footprints', 'footprint', R.item(xe, this)),
                    a.collection('zones', 'zone', R.item(ct)),
                    a.collection('segments', 'segment', R.item(jt)),
                    a.collection('segments', 'arc', R.item(zt)),
                    a.collection('vias', 'via', R.item(qt)),
                    a.collection('drawings', 'dimension', R.item(e2, this)),
                    a.collection('drawings', 'gr_line', R.item(Rt)),
                    a.collection('drawings', 'gr_circle', R.item(ut)),
                    a.collection('drawings', 'gr_arc', R.item(pt)),
                    a.collection('drawings', 'gr_poly', R.item(ht)),
                    a.collection('drawings', 'gr_rect', R.item(dt)),
                    a.collection('drawings', 'gr_text', R.item(bt, this)),
                    a.collection('groups', 'group', R.item(Fr)),
                ),
            );
        }
        static {
            l(this, 'KicadPCB');
        }
        *items() {
            yield* this.drawings, yield* this.vias, yield* this.segments, yield* this.zones, yield* this.footprints;
        }
        resolve_text_var(t) {
            return t == 'FILENAME'
                ? this.filename
                : this.properties.has(t)
                  ? this.properties.get(t).value
                  : this.title_block.resolve_text_var(t);
        }
        get edge_cuts_bbox() {
            let t = new O(0, 0, 0, 0);
            for (let e of this.drawings) e.layer != 'Edge.Cuts' || !(e instanceof Qe) || (t = O.combine([t, e.bbox]));
            return t;
        }
        find_footprint(t) {
            for (let e of this.footprints) if (e.uuid == t || e.reference == t) return e;
            return null;
        }
    },
    Mr = class {
        static {
            l(this, 'Property');
        }
        constructor(t) {
            Object.assign(
                this,
                g(t, a.start('property'), a.positional('name', R.string), a.positional('value', R.string)),
            );
        }
    },
    jt = class {
        constructor(t) {
            this.locked = !1;
            Object.assign(
                this,
                g(
                    t,
                    a.start('segment'),
                    a.vec2('start'),
                    a.vec2('end'),
                    a.pair('width', R.number),
                    a.pair('layer', R.string),
                    a.pair('net', R.number),
                    a.atom('locked'),
                    a.pair('tstamp', R.string),
                ),
            );
        }
        static {
            l(this, 'LineSegment');
        }
    },
    zt = class {
        constructor(t) {
            this.locked = !1;
            Object.assign(
                this,
                g(
                    t,
                    a.start('arc'),
                    a.vec2('start'),
                    a.vec2('mid'),
                    a.vec2('end'),
                    a.pair('width', R.number),
                    a.pair('layer', R.string),
                    a.pair('net', R.number),
                    a.atom('locked'),
                    a.pair('tstamp', R.string),
                ),
            );
        }
        static {
            l(this, 'ArcSegment');
        }
    },
    qt = class {
        constructor(t) {
            this.type = 'through-hole';
            this.remove_unused_layers = !1;
            this.keep_end_layers = !1;
            this.locked = !1;
            this.free = !1;
            Object.assign(
                this,
                g(
                    t,
                    a.start('via'),
                    a.atom('type', ['blind', 'micro', 'through-hole']),
                    a.item('at', H),
                    a.pair('size', R.number),
                    a.pair('drill', R.number),
                    a.list('layers', R.string),
                    a.pair('net', R.number),
                    a.atom('locked'),
                    a.atom('free'),
                    a.atom('remove_unused_layers'),
                    a.atom('keep_end_layers'),
                    a.pair('tstamp', R.string),
                ),
            );
        }
        static {
            l(this, 'Via');
        }
    },
    ct = class {
        constructor(t, e) {
            this.parent = e;
            this.locked = !1;
            Object.assign(
                this,
                g(
                    t,
                    a.start('zone'),
                    a.atom('locked'),
                    a.pair('net', R.number),
                    a.pair('net_name', R.string),
                    a.pair('net_name', R.string),
                    a.pair('name', R.string),
                    a.pair('layer', R.string),
                    a.list('layers', R.string),
                    a.object('hatch', {}, a.positional('style', R.string), a.positional('pitch', R.number)),
                    a.pair('priority', R.number),
                    a.object('connect_pads', {}, a.positional('type', R.string), a.pair('clearance', R.number)),
                    a.pair('min_thickness', R.number),
                    a.pair('filled_areas_thickness', R.boolean),
                    a.item('keepout', fr),
                    a.item('fill', Nr),
                    a.collection('polygons', 'polygon', R.item(Pe)),
                    a.collection('filled_polygons', 'filled_polygon', R.item(Lr)),
                    a.pair('tstamp', R.string),
                ),
            );
        }
        static {
            l(this, 'Zone');
        }
    },
    fr = class {
        static {
            l(this, 'ZoneKeepout');
        }
        constructor(t) {
            Object.assign(
                this,
                g(
                    t,
                    a.start('keepout'),
                    a.pair('tracks', R.string),
                    a.pair('vias', R.string),
                    a.pair('pads', R.string),
                    a.pair('copperpour', R.string),
                    a.pair('footprints', R.string),
                ),
            );
        }
    },
    Nr = class {
        constructor(t) {
            this.fill = !1;
            this.mode = 'solid';
            Object.assign(
                this,
                g(
                    t,
                    a.start('fill'),
                    a.positional('fill', R.boolean),
                    a.pair('mode', R.string),
                    a.pair('thermal_gap', R.number),
                    a.pair('thermal_bridge_width', R.number),
                    a.expr('smoothing', R.object({}, a.positional('style', R.string), a.pair('radius', R.number))),
                    a.pair('radius', R.number),
                    a.pair('island_removal_mode', R.number),
                    a.pair('island_area_min', R.number),
                    a.pair('hatch_thickness', R.number),
                    a.pair('hatch_gap', R.number),
                    a.pair('hatch_orientation', R.number),
                    a.pair('hatch_smoothing_level', R.number),
                    a.pair('hatch_smoothing_value', R.number),
                    a.pair('hatch_border_algorithm', R.string),
                    a.pair('hatch_min_hole_area', R.number),
                ),
            );
        }
        static {
            l(this, 'ZoneFill');
        }
    },
    Vr = class {
        static {
            l(this, 'Layer');
        }
        constructor(t) {
            Object.assign(
                this,
                g(
                    t,
                    a.positional('ordinal', R.number),
                    a.positional('canonical_name', R.string),
                    a.positional('type', R.string),
                    a.positional('user_name', R.string),
                ),
            );
        }
    },
    gr = class {
        static {
            l(this, 'Setup');
        }
        constructor(t) {
            Object.assign(
                this,
                g(
                    t,
                    a.start('setup'),
                    a.pair('pad_to_mask_clearance', R.number),
                    a.pair('solder_mask_min_width', R.number),
                    a.pair('pad_to_paste_clearance', R.number),
                    a.pair('pad_to_paste_clearance_ratio', R.number),
                    a.vec2('aux_axis_origin'),
                    a.vec2('grid_origin'),
                    a.item('pcbplotparams', Pr),
                    a.item('stackup', Wr),
                ),
            );
        }
    },
    Pr = class {
        constructor(t) {
            this.disableapertmacros = !1;
            this.usegerberextensions = !1;
            this.usegerberattributes = !1;
            this.usegerberadvancedattributes = !1;
            this.creategerberjobfile = !1;
            this.svguseinch = !1;
            this.excludeedgelayer = !1;
            this.plotframeref = !1;
            this.viasonmask = !1;
            this.useauxorigin = !1;
            this.dxfpolygonmode = !1;
            this.dxfimperialunits = !1;
            this.dxfusepcbnewfont = !1;
            this.psnegative = !1;
            this.psa4output = !1;
            this.plotreference = !1;
            this.plotvalue = !1;
            this.plotinvisibletext = !1;
            this.sketchpadsonfab = !1;
            this.subtractmaskfromsilk = !1;
            this.mirror = !1;
            Object.assign(
                this,
                g(
                    t,
                    a.start('pcbplotparams'),
                    a.pair('layerselection', R.number),
                    a.pair('disableapertmacros', R.boolean),
                    a.pair('usegerberextensions', R.boolean),
                    a.pair('usegerberattributes', R.boolean),
                    a.pair('usegerberadvancedattributes', R.boolean),
                    a.pair('creategerberjobfile', R.boolean),
                    a.pair('gerberprecision', R.number),
                    a.pair('svguseinch', R.boolean),
                    a.pair('svgprecision', R.number),
                    a.pair('excludeedgelayer', R.boolean),
                    a.pair('plotframeref', R.boolean),
                    a.pair('viasonmask', R.boolean),
                    a.pair('mode', R.number),
                    a.pair('useauxorigin', R.boolean),
                    a.pair('hpglpennumber', R.number),
                    a.pair('hpglpenspeed', R.number),
                    a.pair('hpglpendiameter', R.number),
                    a.pair('dxfpolygonmode', R.boolean),
                    a.pair('dxfimperialunits', R.boolean),
                    a.pair('dxfusepcbnewfont', R.boolean),
                    a.pair('psnegative', R.boolean),
                    a.pair('psa4output', R.boolean),
                    a.pair('plotreference', R.boolean),
                    a.pair('plotvalue', R.boolean),
                    a.pair('plotinvisibletext', R.boolean),
                    a.pair('sketchpadsonfab', R.boolean),
                    a.pair('subtractmaskfromsilk', R.boolean),
                    a.pair('outputformat', R.number),
                    a.pair('mirror', R.boolean),
                    a.pair('drillshape', R.number),
                    a.pair('scaleselection', R.number),
                    a.pair('outputdirectory', R.string),
                    a.pair('plot_on_all_layers_selection', R.number),
                    a.pair('dashed_line_dash_ratio', R.number),
                    a.pair('dashed_line_gap_ratio', R.number),
                ),
            );
        }
        static {
            l(this, 'PCBPlotParams');
        }
    },
    Wr = class {
        constructor(t) {
            this.dielectric_constraints = !1;
            this.castellated_pads = !1;
            this.edge_plating = !1;
            Object.assign(
                this,
                g(
                    t,
                    a.start('stackup'),
                    a.pair('copper_finish', R.string),
                    a.pair('dielectric_constraints', R.boolean),
                    a.pair('edge_connector', R.string),
                    a.pair('castellated_pads', R.boolean),
                    a.pair('edge_plating', R.boolean),
                    a.collection('layers', 'layer', R.item(Zr)),
                ),
            );
        }
        static {
            l(this, 'Stackup');
        }
    },
    Zr = class {
        static {
            l(this, 'StackupLayer');
        }
        constructor(t) {
            Object.assign(
                this,
                g(
                    t,
                    a.start('layer'),
                    a.positional('name', R.string),
                    a.pair('type', R.string),
                    a.pair('color', R.string),
                    a.pair('thickness', R.number),
                    a.pair('material', R.string),
                    a.pair('epsilon_r', R.number),
                    a.pair('loss_tangent', R.number),
                ),
            );
        }
    },
    B2 = class {
        static {
            l(this, 'Net');
        }
        constructor(t) {
            Object.assign(this, g(t, a.start('net'), a.positional('number', R.number), a.positional('name', R.string)));
        }
    },
    e2 = class {
        constructor(t, e) {
            this.parent = e;
            this.locked = !1;
            Object.assign(
                this,
                g(
                    t,
                    a.start('dimension'),
                    a.atom('locked'),
                    a.pair('type', R.string),
                    a.pair('layer', R.string),
                    a.pair('tstamp', R.string),
                    a.list('pts', R.vec2),
                    a.pair('height', R.number),
                    a.pair('orientation', R.number),
                    a.pair('leader_length', R.number),
                    a.item('gr_text', bt, this),
                    a.item('format', Sr),
                    a.item('style', Tr),
                ),
            );
        }
        static {
            l(this, 'Dimension');
        }
        resolve_text_var(t) {
            return this.parent.resolve_text_var(t);
        }
        get start() {
            return this.pts.at(0) ?? new d(0, 0);
        }
        get end() {
            return this.pts.at(-1) ?? new d(0, 0);
        }
    };
var Sr = class {
    constructor(t) {
        this.suppress_zeroes = !1;
        Object.assign(
            this,
            g(
                t,
                a.start('format'),
                a.pair('prefix', R.string),
                a.pair('suffix', R.string),
                a.pair('units', R.number),
                a.pair('units_format', R.number),
                a.pair('precision', R.number),
                a.pair('override_value', R.string),
                a.atom('suppress_zeroes'),
            ),
        );
    }
    static {
        l(this, 'DimensionFormat');
    }
};
var Tr = class {
        static {
            l(this, 'DimensionStyle');
        }
        constructor(t) {
            Object.assign(
                this,
                g(
                    t,
                    a.start('style'),
                    a.pair('thickness', R.number),
                    a.pair('arrow_length', R.number),
                    a.pair('text_position_mode', R.number),
                    a.pair('extension_height', R.number),
                    a.pair('text_frame', R.number),
                    a.pair('extension_offset', R.number),
                    a.atom('keep_text_aligned'),
                ),
            );
        }
    },
    xe = class {
        constructor(t, e) {
            this.parent = e;
            this.locked = !1;
            this.placed = !1;
            this.attr = {
                through_hole: !1,
                smd: !1,
                virtual: !1,
                board_only: !1,
                exclude_from_pos_files: !1,
                exclude_from_bom: !1,
                allow_solder_mask_bridges: !1,
                allow_missing_courtyard: !1,
            };
            this.properties = {};
            this.drawings = [];
            this.pads = [];
            this.#e = new Map();
            this.zones = [];
            this.models = [];
            Object.assign(
                this,
                g(
                    t,
                    a.start('footprint'),
                    a.positional('library_link', R.string),
                    a.pair('version', R.number),
                    a.pair('generator', R.string),
                    a.atom('locked'),
                    a.atom('placed'),
                    a.pair('layer', R.string),
                    a.pair('tedit', R.string),
                    a.pair('tstamp', R.string),
                    a.item('at', H),
                    a.pair('descr', R.string),
                    a.pair('tags', R.string),
                    a.pair('path', R.string),
                    a.pair('autoplace_cost90', R.number),
                    a.pair('autoplace_cost180', R.number),
                    a.pair('solder_mask_margin', R.number),
                    a.pair('solder_paste_margin', R.number),
                    a.pair('solder_paste_ratio', R.number),
                    a.pair('clearance', R.number),
                    a.pair('zone_connect', R.number),
                    a.pair('thermal_width', R.number),
                    a.pair('thermal_gap', R.number),
                    a.object(
                        'attr',
                        this.attr,
                        a.atom('through_hole'),
                        a.atom('smd'),
                        a.atom('virtual'),
                        a.atom('board_only'),
                        a.atom('exclude_from_pos_files'),
                        a.atom('exclude_from_bom'),
                        a.atom('allow_solder_mask_bridges'),
                        a.atom('allow_missing_courtyard'),
                    ),
                    a.dict('properties', 'property', R.string),
                    a.collection('drawings', 'fp_line', R.item(t2, this)),
                    a.collection('drawings', 'fp_circle', R.item(r2, this)),
                    a.collection('drawings', 'fp_arc', R.item(i2, this)),
                    a.collection('drawings', 'fp_poly', R.item(s2, this)),
                    a.collection('drawings', 'fp_rect', R.item(n2, this)),
                    a.collection('drawings', 'fp_text', R.item(Ce, this)),
                    a.collection('zones', 'zone', R.item(ct, this)),
                    a.collection('models', 'model', R.item(Ur)),
                    a.collection('pads', 'pad', R.item(o2, this)),
                ),
            );
            for (let r of this.pads) this.#e.set(r.number, r);
            for (let r of this.drawings)
                r instanceof Ce &&
                    (r.type == 'reference' && (this.reference = r.text), r.type == 'value' && (this.value = r.text));
        }
        static {
            l(this, 'Footprint');
        }
        #e;
        #t;
        get uuid() {
            return this.tstamp;
        }
        *items() {
            yield* this.drawings ?? [], yield* this.zones ?? [], yield* this.pads.values() ?? [];
        }
        resolve_text_var(t) {
            switch (t) {
                case 'REFERENCE':
                    return this.reference;
                case 'VALUE':
                    return this.value;
                case 'LAYER':
                    return this.layer;
                case 'FOOTPRINT_LIBRARY':
                    return this.library_link.split(':').at(0);
                case 'FOOTPRINT_NAME':
                    return this.library_link.split(':').at(-1);
            }
            let e = /^(NET_NAME|NET_CLASS|PIN_NAME)\(.+?\)$/.exec(t);
            if (e?.length == 3) {
                let [r, i, n] = e;
                switch (i) {
                    case 'NET_NAME':
                        return this.pad_by_number(n)?.net.number.toString();
                    case 'NET_CLASS':
                        return this.pad_by_number(n)?.net.name;
                    case 'PIN_NAME':
                        return this.pad_by_number(n)?.pinfunction;
                }
            }
            return this.properties[t] !== void 0 ? this.properties[t] : this.parent.resolve_text_var(t);
        }
        pad_by_number(t) {
            return this.#e.get(t);
        }
        get bbox() {
            if (!this.#t) {
                let t = new O(this.at.position.x - 0.25, this.at.position.y - 0.25, 0.5, 0.5),
                    e = U.translation(this.at.position.x, this.at.position.y).rotate_self(
                        W.deg_to_rad(this.at.rotation),
                    );
                for (let r of this.drawings) r instanceof Ce || (t = O.combine([t, r.bbox.transform(e)]));
                (t.context = this), (this.#t = t);
            }
            return this.#t;
        }
    },
    Qe = class {
        constructor() {
            this.locked = !1;
        }
        static {
            l(this, 'GraphicItem');
        }
        get bbox() {
            return new O(0, 0, 0, 0);
        }
    },
    $2 = class extends Qe {
        constructor(e, r) {
            super();
            this.parent = r;
            let i = this.constructor;
            Object.assign(
                this,
                g(
                    e,
                    a.start(i.expr_start),
                    a.atom('locked'),
                    a.pair('layer', R.string),
                    a.vec2('start'),
                    a.vec2('end'),
                    a.pair('width', R.number),
                    a.pair('tstamp', R.string),
                    a.item('stroke', q),
                ),
            ),
                (this.width ??= this.stroke?.width || 0);
        }
        static {
            l(this, 'Line');
        }
        static {
            this.expr_start = 'unset';
        }
        get bbox() {
            return O.from_points([this.start, this.end]);
        }
    },
    Rt = class extends $2 {
        static {
            l(this, 'GrLine');
        }
        static {
            this.expr_start = 'gr_line';
        }
    },
    t2 = class extends $2 {
        static {
            l(this, 'FpLine');
        }
        static {
            this.expr_start = 'fp_line';
        }
    },
    j2 = class extends Qe {
        constructor(e, r) {
            super();
            this.parent = r;
            let i = this.constructor;
            Object.assign(
                this,
                g(
                    e,
                    a.start(i.expr_start),
                    a.atom('locked'),
                    a.vec2('center'),
                    a.vec2('end'),
                    a.pair('width', R.number),
                    a.pair('fill', R.string),
                    a.pair('layer', R.string),
                    a.pair('tstamp', R.string),
                    a.item('stroke', q),
                ),
            ),
                (this.width ??= this.stroke?.width || 0);
        }
        static {
            l(this, 'Circle');
        }
        static {
            this.expr_start = 'unset';
        }
        get bbox() {
            let e = this.center.sub(this.end).magnitude,
                r = new d(e, e);
            return O.from_points([this.center.sub(r), this.center.add(r)]);
        }
    },
    ut = class extends j2 {
        static {
            l(this, 'GrCircle');
        }
        static {
            this.expr_start = 'gr_circle';
        }
    },
    r2 = class extends j2 {
        static {
            l(this, 'FpCircle');
        }
        static {
            this.expr_start = 'fp_circle';
        }
    },
    z2 = class extends Qe {
        constructor(e, r) {
            super();
            this.parent = r;
            let i = this.constructor,
                n = g(
                    e,
                    a.start(i.expr_start),
                    a.atom('locked'),
                    a.pair('layer', R.string),
                    a.vec2('start'),
                    a.vec2('mid'),
                    a.vec2('end'),
                    a.pair('angle', R.number),
                    a.pair('width', R.number),
                    a.pair('tstamp', R.string),
                    a.item('stroke', q),
                );
            if (n.angle !== void 0) {
                let o = W.from_degrees(n.angle).normalize720(),
                    c = n.start,
                    u = n.end,
                    p = o.negative().rotate_point(u, c);
                o.degrees < 0 && ([u, p] = [p, u]),
                    (this.#e = z.from_center_start_end(c, u, p, n.width)),
                    (n.start = this.#e.start_point),
                    (n.mid = this.#e.mid_point),
                    (n.end = this.#e.end_point),
                    delete n.angle;
            } else this.#e = z.from_three_points(n.start, n.mid, n.end, n.width);
            Object.assign(this, n), (this.width ??= this.stroke?.width ?? this.#e.width), (this.#e.width = this.width);
        }
        static {
            l(this, 'Arc');
        }
        static {
            this.expr_start = 'unset';
        }
        #e;
        get arc() {
            return this.#e;
        }
        get bbox() {
            return this.arc.bbox;
        }
    },
    pt = class extends z2 {
        static {
            l(this, 'GrArc');
        }
        static {
            this.expr_start = 'gr_arc';
        }
    },
    i2 = class extends z2 {
        static {
            l(this, 'FpArc');
        }
        static {
            this.expr_start = 'fp_arc';
        }
    },
    Pe = class extends Qe {
        constructor(e, r) {
            super();
            this.parent = r;
            let i = this.constructor;
            Object.assign(
                this,
                g(
                    e,
                    a.start(i.expr_start),
                    a.atom('locked'),
                    a.pair('layer', R.string),
                    a.atom('island'),
                    a.list('pts', R.vec2),
                    a.pair('width', R.number),
                    a.pair('fill', R.string),
                    a.pair('tstamp', R.string),
                    a.item('stroke', q),
                ),
            ),
                (this.width ??= this.stroke?.width || 0);
        }
        static {
            l(this, 'Poly');
        }
        static {
            this.expr_start = 'polygon';
        }
        get bbox() {
            return O.from_points(this.pts);
        }
    },
    Lr = class extends Pe {
        static {
            l(this, 'FilledPolygon');
        }
        static {
            this.expr_start = 'filled_polygon';
        }
    },
    ht = class extends Pe {
        static {
            l(this, 'GrPoly');
        }
        static {
            this.expr_start = 'gr_poly';
        }
    },
    s2 = class extends Pe {
        static {
            l(this, 'FpPoly');
        }
        static {
            this.expr_start = 'fp_poly';
        }
    },
    q2 = class extends Qe {
        constructor(e, r) {
            super();
            this.parent = r;
            let i = this.constructor;
            Object.assign(
                this,
                g(
                    e,
                    a.start(i.expr_start),
                    a.atom('locked'),
                    a.vec2('start'),
                    a.vec2('end'),
                    a.pair('layer', R.string),
                    a.pair('width', R.number),
                    a.pair('fill', R.string),
                    a.pair('tstamp', R.string),
                    a.item('stroke', q),
                ),
            ),
                (this.width ??= this.stroke?.width || 0);
        }
        static {
            l(this, 'Rect');
        }
        static {
            this.expr_start = 'rect';
        }
        get bbox() {
            return O.from_points([this.start, this.end]);
        }
    },
    dt = class extends q2 {
        static {
            l(this, 'GrRect');
        }
        static {
            this.expr_start = 'gr_rect';
        }
    },
    n2 = class extends q2 {
        static {
            l(this, 'FpRect');
        }
        static {
            this.expr_start = 'fp_rect';
        }
    },
    yr = class {
        static {
            l(this, 'TextRenderCache');
        }
        constructor(t) {
            Object.assign(
                this,
                g(
                    t,
                    a.start('render_cache'),
                    a.positional('text', R.string),
                    a.positional('angle', R.number),
                    a.collection('polygons', 'polygon', R.item(Pe)),
                ),
            );
            for (let e of this.polygons) e.fill = 'solid';
        }
    },
    mt = class {
        constructor() {
            this.unlocked = !1;
            this.hide = !1;
            this.effects = new J();
        }
        static {
            l(this, 'Text');
        }
        static {
            this.common_expr_defs = [
                a.item('at', H),
                a.atom('hide'),
                a.atom('unlocked'),
                a.object('layer', {}, a.positional('name', R.string), a.atom('knockout')),
                a.pair('tstamp', R.string),
                a.item('effects', J),
                a.item('render_cache', yr),
            ];
        }
        get shown_text() {
            return Ae(this.text, this.parent);
        }
    },
    Ce = class extends mt {
        constructor(e, r) {
            super();
            this.parent = r;
            this.locked = !1;
            Object.assign(
                this,
                g(
                    e,
                    a.start('fp_text'),
                    a.atom('locked'),
                    a.positional('type', R.string),
                    a.positional('text', R.string),
                    ...mt.common_expr_defs,
                ),
            );
        }
        static {
            l(this, 'FpText');
        }
    },
    bt = class extends mt {
        constructor(e, r) {
            super();
            this.parent = r;
            this.locked = !1;
            Object.assign(
                this,
                g(e, a.start('gr_text'), a.atom('locked'), a.positional('text', R.string), ...mt.common_expr_defs),
            );
        }
        static {
            l(this, 'GrText');
        }
    },
    o2 = class {
        constructor(t, e) {
            this.parent = e;
            this.type = 'thru_hole';
            this.locked = !1;
            let r = g(
                t,
                a.start('pad'),
                a.positional('number', R.string),
                a.positional('type', R.string),
                a.positional('shape', R.string),
                a.item('at', H),
                a.atom('locked'),
                a.vec2('size'),
                a.vec2('rect_delta'),
                a.list('layers', R.string),
                a.pair('roundrect_rratio', R.number),
                a.pair('chamfer_ratio', R.number),
                a.expr(
                    'chamfer',
                    R.object(
                        {},
                        a.atom('top_right'),
                        a.atom('top_left'),
                        a.atom('bottom_right'),
                        a.atom('bottom_left'),
                    ),
                ),
                a.pair('pinfunction', R.string),
                a.pair('pintype', R.string),
                a.pair('solder_mask_margin', R.number),
                a.pair('solder_paste_margin', R.number),
                a.pair('solder_paste_margin_ratio', R.number),
                a.pair('clearance', R.number),
                a.pair('thermal_width', R.number),
                a.pair('thermal_gap', R.number),
                a.pair('thermal_bridge_angle', R.number),
                a.pair('zone_connect', R.number),
                a.pair('tstamp', R.string),
                a.item('drill', Xr),
                a.item('net', B2),
                a.item('options', Or),
                a.expr(
                    'primitives',
                    (i, n, o) =>
                        g(
                            o,
                            a.start('primitives'),
                            a.collection('items', 'gr_line', R.item(Rt, this)),
                            a.collection('items', 'gr_circle', R.item(ut, this)),
                            a.collection('items', 'gr_arc', R.item(pt, this)),
                            a.collection('items', 'gr_rect', R.item(dt, this)),
                            a.collection('items', 'gr_poly', R.item(ht, this)),
                        )?.items,
                ),
            );
            Object.assign(this, r);
        }
        static {
            l(this, 'Pad');
        }
    },
    Xr = class {
        constructor(t) {
            this.oval = !1;
            this.diameter = 0;
            this.width = 0;
            this.offset = new d(0, 0);
            Object.assign(
                this,
                g(
                    t,
                    a.start('drill'),
                    a.atom('oval'),
                    a.positional('diameter', R.number),
                    a.positional('width', R.number),
                    a.vec2('offset'),
                ),
            );
        }
        static {
            l(this, 'PadDrill');
        }
    },
    Or = class {
        static {
            l(this, 'PadOptions');
        }
        constructor(t) {
            Object.assign(this, g(t, a.start('options'), a.pair('clearance', R.string), a.pair('anchor', R.string)));
        }
    },
    Ur = class {
        constructor(t) {
            this.hide = !1;
            this.opacity = 1;
            Object.assign(
                this,
                g(
                    t,
                    a.start('model'),
                    a.positional('filename', R.string),
                    a.atom('hide'),
                    a.pair('opacity', R.number),
                    a.object('offset', {}, a.list('xyz', R.number)),
                    a.object('scale', {}, a.list('xyz', R.number)),
                    a.object('rotate', {}, a.list('xyz', R.number)),
                ),
            );
        }
        static {
            l(this, 'Model');
        }
    },
    Fr = class {
        constructor(t) {
            this.locked = !1;
            Object.assign(
                this,
                g(
                    t,
                    a.start('group'),
                    a.positional('name', R.string),
                    a.atom('locked'),
                    a.pair('id', R.string),
                    a.list('members', R.string),
                ),
            );
        }
        static {
            l(this, 'Group');
        }
    };
var A = {
        dangling_symbol_size: 0.3048,
        unselected_end_size: 0.1016,
        pin_length: 2.54,
        pinsymbol_size: 0.635,
        pinnum_size: 1.27,
        pinname_size: 1.27,
        selection_thickness: 0.0762,
        line_width: 0.1524,
        wire_width: 0.1524,
        bus_width: 0.3048,
        noconnect_size: 1.2192,
        junction_diameter: 0.9144,
        target_pin_radius: 0.381,
        sch_entry_size: 2.54,
        text_size: 1.27,
        text_offset_ratio: 0.15,
        label_size_ratio: 0.375,
        pin_name_offset: 0.508,
    },
    me = class {
        constructor(t, e) {
            this.filename = t;
            this.title_block = new Fe();
            this.wires = [];
            this.buses = [];
            this.bus_entries = [];
            this.bus_aliases = [];
            this.junctions = [];
            this.net_labels = [];
            this.global_labels = [];
            this.hierarchical_labels = [];
            this.symbols = new Map();
            this.no_connects = [];
            this.drawings = [];
            this.images = [];
            this.sheets = [];
            Object.assign(
                this,
                g(
                    e,
                    a.start('kicad_sch'),
                    a.pair('version', R.number),
                    a.pair('generator', R.string),
                    a.pair('uuid', R.string),
                    a.item('paper', lt),
                    a.item('title_block', Fe),
                    a.item('lib_symbols', Yr, this),
                    a.collection('wires', 'wire', R.item(a2)),
                    a.collection('buses', 'bus', R.item(l2)),
                    a.collection('bus_entries', 'bus_entry', R.item(c2)),
                    a.collection('bus_aliases', 'bus_alias', R.item(xr)),
                    a.collection('junctions', 'junction', R.item(R2)),
                    a.collection('no_connects', 'no_connect', R.item(u2)),
                    a.collection('net_labels', 'label', R.item(d2)),
                    a.collection('global_labels', 'global_label', R.item(m2, this)),
                    a.collection('hierarchical_labels', 'hierarchical_label', R.item(De, this)),
                    a.mapped_collection('symbols', 'symbol', (r) => r.uuid, R.item(re, this)),
                    a.collection('drawings', 'polyline', R.item(Mt, this)),
                    a.collection('drawings', 'rectangle', R.item(ft, this)),
                    a.collection('drawings', 'arc', R.item(_t, this)),
                    a.collection('drawings', 'text', R.item(Nt, this)),
                    a.collection('images', 'image', R.item(vr)),
                    a.item('sheet_instances', Er),
                    a.item('symbol_instances', Ir),
                    a.collection('sheets', 'sheet', R.item(ne, this)),
                ),
            ),
                this.update_hierarchical_data();
        }
        static {
            l(this, 'KicadSch');
        }
        update_hierarchical_data(t) {
            t ??= '';
            let e = this.project?.root_schematic_page?.document?.symbol_instances,
                r = this.symbol_instances;
            for (let o of this.symbols.values()) {
                let c = `${t}/${o.uuid}`,
                    u = e?.get(c) ?? r?.get(c) ?? o.instances.get(t);
                u &&
                    ((o.reference = u.reference ?? o.reference),
                    (o.value = u.value ?? o.value),
                    (o.footprint = u.footprint ?? o.footprint),
                    (o.unit = u.unit ?? o.unit));
            }
            let i = this.project?.root_schematic_page?.document?.sheet_instances,
                n = this.sheet_instances;
            for (let o of this.sheets) {
                let c = `${t}/${o.uuid}`,
                    u = i?.get(c) ?? n?.get(c) ?? o.instances.get(t);
                if (u && ((o.page = u.page), (o.path = u.path), !o.instances.size)) {
                    let p = new t3();
                    (p.page = u.page), (p.path = u.path), o.instances.set('', p);
                }
            }
        }
        *items() {
            yield* this.wires,
                yield* this.buses,
                yield* this.bus_entries,
                yield* this.junctions,
                yield* this.net_labels,
                yield* this.global_labels,
                yield* this.hierarchical_labels,
                yield* this.no_connects,
                yield* this.symbols.values(),
                yield* this.drawings,
                yield* this.images,
                yield* this.sheets;
        }
        find_symbol(t) {
            if (this.symbols.has(t)) return this.symbols.get(t);
            for (let e of this.symbols.values()) if (e.uuid == t || e.reference == t) return e;
            return null;
        }
        find_sheet(t) {
            for (let e of this.sheets) if (e.uuid == t) return e;
            return null;
        }
        resolve_text_var(t) {
            if (t == 'FILENAME') return this.filename;
            if (t.includes(':')) {
                let [e, r] = t.split(':'),
                    i = this.symbols.get(e);
                if (i) return i.resolve_text_var(r);
            }
            return this.title_block.resolve_text_var(t);
        }
    },
    e3 = class {
        static {
            l(this, 'Fill');
        }
        constructor(t) {
            Object.assign(this, g(t, a.start('fill'), a.pair('type', R.string), a.color()));
        }
    },
    ee = class {
        constructor(t) {
            this.private = !1;
            this.parent = t;
        }
        static {
            l(this, 'GraphicItem');
        }
        static {
            this.common_expr_defs = [
                a.atom('private'),
                a.item('stroke', q),
                a.item('fill', e3),
                a.pair('uuid', R.string),
            ];
        }
    },
    a2 = class {
        static {
            l(this, 'Wire');
        }
        constructor(t) {
            Object.assign(
                this,
                g(t, a.start('wire'), a.list('pts', R.vec2), a.item('stroke', q), a.pair('uuid', R.string)),
            );
        }
    },
    l2 = class {
        static {
            l(this, 'Bus');
        }
        constructor(t) {
            Object.assign(
                this,
                g(t, a.start('bus'), a.list('pts', R.vec2), a.item('stroke', q), a.pair('uuid', R.string)),
            );
        }
    },
    c2 = class {
        static {
            l(this, 'BusEntry');
        }
        constructor(t) {
            Object.assign(
                this,
                g(
                    t,
                    a.start('bus_entry'),
                    a.item('at', H),
                    a.vec2('size'),
                    a.item('stroke', q),
                    a.pair('uuid', R.string),
                ),
            );
        }
    },
    xr = class {
        constructor(t) {
            this.members = [];
            Object.assign(this, g(t, a.start('bus_alias'), a.list('members', R.string)));
        }
        static {
            l(this, 'BusAlias');
        }
    },
    R2 = class {
        static {
            l(this, 'Junction');
        }
        constructor(t) {
            Object.assign(
                this,
                g(
                    t,
                    a.start('junction'),
                    a.item('at', H),
                    a.pair('diameter', R.number),
                    a.color(),
                    a.pair('uuid', R.string),
                ),
            );
        }
    },
    u2 = class {
        static {
            l(this, 'NoConnect');
        }
        constructor(t) {
            Object.assign(this, g(t, a.start('no_connect'), a.item('at', H), a.pair('uuid', R.string)));
        }
    },
    _t = class extends ee {
        constructor(e, r) {
            super(r);
            let i = g(
                e,
                a.start('arc'),
                a.vec2('start'),
                a.vec2('mid'),
                a.vec2('end'),
                a.object('radius', {}, a.start('radius'), a.vec2('at'), a.pair('length'), a.vec2('angles')),
                ...ee.common_expr_defs,
            );
            if (i.radius?.length) {
                let n = z.from_center_start_end(i.radius.at, i.end, i.start, 1);
                n.arc_angle.degrees > 180 && ([n.start_angle, n.end_angle] = [n.end_angle, n.start_angle]),
                    (i.start = n.start_point),
                    (i.mid = n.mid_point),
                    (i.end = n.end_point);
            }
            delete i.radius, Object.assign(this, i);
        }
        static {
            l(this, 'Arc');
        }
    },
    Qr = class extends ee {
        constructor(e, r) {
            super(r);
            Object.assign(this, g(e, a.start('bezier'), a.list('pts', R.vec2), ...ee.common_expr_defs));
        }
        static {
            l(this, 'Bezier');
        }
        get start() {
            return this.pts[0];
        }
        get c1() {
            return this.pts[1];
        }
        get c2() {
            return this.pts[2];
        }
        get end() {
            return this.pts[3];
        }
    },
    p2 = class extends ee {
        constructor(e, r) {
            super(r);
            Object.assign(
                this,
                g(e, a.start('circle'), a.vec2('center'), a.pair('radius', R.number), ...ee.common_expr_defs),
            );
        }
        static {
            l(this, 'Circle');
        }
    },
    Mt = class extends ee {
        constructor(e, r) {
            super(r);
            Object.assign(this, g(e, a.start('polyline'), a.list('pts', R.vec2), ...ee.common_expr_defs));
        }
        static {
            l(this, 'Polyline');
        }
    },
    ft = class extends ee {
        constructor(e, r) {
            super(r);
            Object.assign(this, g(e, a.start('rectangle'), a.vec2('start'), a.vec2('end'), ...ee.common_expr_defs));
        }
        static {
            l(this, 'Rectangle');
        }
    },
    vr = class {
        static {
            l(this, 'Image');
        }
        constructor(t) {
            Object.assign(
                this,
                g(t, a.start('image'), a.item('at', H), a.pair('data', R.string), a.pair('uuid', R.string)),
            );
        }
    },
    Nt = class {
        constructor(t, e) {
            this.parent = e;
            this.private = !1;
            this.effects = new J();
            Object.assign(
                this,
                g(
                    t,
                    a.start('text'),
                    a.positional('text'),
                    a.item('at', H),
                    a.item('effects', J),
                    a.pair('uuid', R.string),
                ),
            ),
                this.text.endsWith(`
`) && (this.text = this.text.slice(0, this.text.length - 1));
        }
        static {
            l(this, 'Text');
        }
        get shown_text() {
            return Ae(this.text, this.parent);
        }
    },
    h2 = class extends Nt {
        constructor(e, r) {
            super(e, r);
            this.parent = r;
            (r instanceof Vt || r instanceof re) && (this.at.rotation /= 10);
        }
        static {
            l(this, 'LibText');
        }
    },
    wr = class extends ee {
        constructor(e, r) {
            super(r);
            this.effects = new J();
            Object.assign(
                this,
                g(
                    e,
                    a.start('text'),
                    a.positional('text'),
                    a.item('at', H),
                    a.vec2('size'),
                    a.item('effects', J),
                    ...ee.common_expr_defs,
                ),
            );
        }
        static {
            l(this, 'TextBox');
        }
    },
    ve = class {
        constructor() {
            this.private = !1;
            this.at = new H();
            this.effects = new J();
            this.fields_autoplaced = !1;
        }
        static {
            l(this, 'Label');
        }
        static {
            this.common_expr_defs = [
                a.positional('text'),
                a.item('at', H),
                a.item('effects', J),
                a.atom('fields_autoplaced'),
                a.pair('uuid', R.string),
            ];
        }
        get shown_text() {
            return _r(this.text);
        }
    },
    d2 = class extends ve {
        static {
            l(this, 'NetLabel');
        }
        constructor(t) {
            super(), Object.assign(this, g(t, a.start('label'), ...ve.common_expr_defs));
        }
    },
    m2 = class extends ve {
        constructor(e) {
            super();
            this.shape = 'input';
            this.properties = [];
            Object.assign(
                this,
                g(
                    e,
                    a.start('global_label'),
                    ...ve.common_expr_defs,
                    a.pair('shape', R.string),
                    a.collection('properties', 'property', R.item(we)),
                ),
            );
        }
        static {
            l(this, 'GlobalLabel');
        }
    },
    De = class extends ve {
        constructor(e) {
            super();
            this.shape = 'input';
            e &&
                Object.assign(
                    this,
                    g(e, a.start('hierarchical_label'), ...ve.common_expr_defs, a.pair('shape', R.string)),
                );
        }
        static {
            l(this, 'HierarchicalLabel');
        }
    },
    Yr = class {
        constructor(t, e) {
            this.parent = e;
            this.symbols = [];
            this.#e = new Map();
            Object.assign(this, g(t, a.start('lib_symbols'), a.collection('symbols', 'symbol', R.item(Vt, e))));
            for (let r of this.symbols) this.#e.set(r.name, r);
        }
        static {
            l(this, 'LibSymbols');
        }
        #e;
        by_name(t) {
            return this.#e.get(t);
        }
    },
    Vt = class s {
        constructor(t, e) {
            this.parent = e;
            this.power = !1;
            this.pin_numbers = { hide: !1 };
            this.pin_names = { offset: A.pin_name_offset, hide: !1 };
            this.in_bom = !1;
            this.on_board = !1;
            this.properties = new Map();
            this.children = [];
            this.drawings = [];
            this.pins = [];
            this.units = new Map();
            this.#e = new Map();
            this.#t = new Map();
            Object.assign(
                this,
                g(
                    t,
                    a.start('symbol'),
                    a.positional('name'),
                    a.atom('power'),
                    a.object('pin_numbers', this.pin_numbers, a.atom('hide')),
                    a.object('pin_names', this.pin_names, a.pair('offset', R.number), a.atom('hide')),
                    a.pair('in_bom', R.boolean),
                    a.pair('on_board', R.boolean),
                    a.mapped_collection('properties', 'property', (r) => r.name, R.item(we, this)),
                    a.collection('pins', 'pin', R.item(Kr, this)),
                    a.collection('children', 'symbol', R.item(s, this)),
                    a.collection('drawings', 'arc', R.item(_t, this)),
                    a.collection('drawings', 'bezier', R.item(Qr, this)),
                    a.collection('drawings', 'circle', R.item(p2, this)),
                    a.collection('drawings', 'polyline', R.item(Mt, this)),
                    a.collection('drawings', 'rectangle', R.item(ft, this)),
                    a.collection('drawings', 'text', R.item(h2, this)),
                    a.collection('drawings', 'textbox', R.item(wr, this)),
                ),
            );
            for (let r of this.pins) this.#e.set(r.number.text, r);
            for (let r of this.properties.values()) this.#t.set(r.id, r);
            for (let r of this.children) {
                let i = r.unit;
                if (i !== null) {
                    let n = this.units.get(i) ?? [];
                    n.push(r), this.units.set(i, n);
                }
            }
        }
        static {
            l(this, 'LibSymbol');
        }
        #e;
        #t;
        get root() {
            return this.parent instanceof s ? this.parent.root : this;
        }
        has_pin(t) {
            return this.#e.has(t);
        }
        pin_by_number(t, e = 1) {
            if (this.has_pin(t)) return this.#e.get(t);
            for (let r of this.children) if ((r.style == 0 || r.style == e) && r.has_pin(t)) return r.pin_by_number(t);
            throw new Error(`No pin numbered ${t} on library symbol ${this.name}`);
        }
        has_property_with_id(t) {
            return this.#t.has(t);
        }
        property_by_id(t) {
            if (this.#t.has(t)) return this.#t.get(t);
            for (let e of this.children) if (e.has_property_with_id(t)) return e.property_by_id(t);
            return null;
        }
        get library_name() {
            return this.name.includes(':') ? this.name.split(':').at(0) : '';
        }
        get library_item_name() {
            return this.name.includes(':') ? this.name.split(':').at(1) : '';
        }
        get unit_count() {
            let t = this.units.size;
            return this.units.has(0) && (t -= 1), t;
        }
        get unit() {
            let t = this.name.split('_');
            return t.length < 3 ? 0 : parseInt(t.at(-2), 10);
        }
        get style() {
            let t = this.name.split('_');
            return t.length < 3 ? 0 : parseInt(t.at(-1), 10);
        }
        get description() {
            return this.properties.get('ki_description')?.text ?? '';
        }
        get keywords() {
            return this.properties.get('ki_keywords')?.text ?? '';
        }
        get footprint_filters() {
            return this.properties.get('ki_fp_filters')?.text ?? '';
        }
        get units_interchangable() {
            return !this.properties.get('ki_locked')?.text;
        }
        resolve_text_var(t) {
            return this.parent?.resolve_text_var(t);
        }
    },
    we = class {
        constructor(t, e) {
            this.parent = e;
            this.show_name = !1;
            this.do_not_autoplace = !1;
            let r = g(
                t,
                a.start('property'),
                a.positional('name', R.string),
                a.positional('text', R.string),
                a.pair('id', R.number),
                a.item('at', H),
                a.item('effects', J),
                a.atom('show_name'),
                a.atom('do_not_autoplace'),
            );
            (this.#e = r.effects), delete r.effects, Object.assign(this, r);
        }
        static {
            l(this, 'Property');
        }
        #e;
        get effects() {
            return this.#e
                ? this.#e
                : (this.parent instanceof re
                      ? (this.#e = new J())
                      : Bt(`Couldn't determine Effects for Property ${this.name}`),
                  this.#e);
        }
        set effects(t) {
            this.#e = t;
        }
        get shown_text() {
            return Ae(this.text, this.parent);
        }
    },
    Kr = class {
        constructor(t, e) {
            this.parent = e;
            this.hide = !1;
            this.name = { text: '', effects: new J() };
            this.number = { text: '', effects: new J() };
            Object.assign(
                this,
                g(
                    t,
                    a.start('pin'),
                    a.positional('type', R.string),
                    a.positional('shape', R.string),
                    a.atom('hide'),
                    a.item('at', H),
                    a.pair('length', R.number),
                    a.object('name', this.name, a.positional('text', R.string), a.item('effects', J)),
                    a.object('number', this.number, a.positional('text', R.string), a.item('effects', J)),
                    a.collection('alternates', 'alternate', R.item(Hr)),
                ),
            );
        }
        static {
            l(this, 'PinDefinition');
        }
        get unit() {
            return this.parent.unit;
        }
    },
    Hr = class {
        static {
            l(this, 'PinAlternate');
        }
        constructor(t) {
            Object.assign(
                this,
                g(
                    t,
                    a.start('alternate'),
                    a.positional('name'),
                    a.positional('type', R.string),
                    a.positional('shaped', R.string),
                ),
            );
        }
    },
    re = class {
        constructor(t, e) {
            this.parent = e;
            this.in_bom = !1;
            this.on_board = !1;
            this.dnp = !1;
            this.fields_autoplaced = !1;
            this.properties = new Map();
            this.pins = [];
            this.instances = new Map();
            let r = g(
                    t,
                    a.start('symbol'),
                    a.pair('lib_name', R.string),
                    a.pair('lib_id', R.string),
                    a.item('at', H),
                    a.pair('mirror', R.string),
                    a.pair('unit', R.number),
                    a.pair('convert', R.number),
                    a.pair('in_bom', R.boolean),
                    a.pair('on_board', R.boolean),
                    a.pair('dnp', R.boolean),
                    a.atom('fields_autoplaced'),
                    a.pair('uuid', R.string),
                    a.mapped_collection('properties', 'property', (n) => n.name, R.item(we, this)),
                    a.collection('pins', 'pin', R.item(b2, this)),
                    a.object(
                        'default_instance',
                        this.default_instance,
                        a.pair('reference', R.string),
                        a.pair('unit', R.string),
                        a.pair('value', R.string),
                        a.pair('footprint', R.string),
                    ),
                    a.object(
                        'instances',
                        {},
                        a.collection(
                            'projects',
                            'project',
                            R.object(
                                null,
                                a.start('project'),
                                a.positional('name', R.string),
                                a.collection(
                                    'paths',
                                    'path',
                                    R.object(
                                        null,
                                        a.start('path'),
                                        a.positional('path'),
                                        a.pair('reference', R.string),
                                        a.pair('value', R.string),
                                        a.pair('unit', R.number),
                                        a.pair('footprint', R.string),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                i = r.instances;
            delete r.instances, Object.assign(this, r);
            for (let n of i?.projects ?? [])
                for (let o of n?.paths ?? []) {
                    let c = new Gr();
                    (c.path = o.path),
                        (c.reference = o.reference),
                        (c.value = o.value),
                        (c.unit = o.unit),
                        (c.footprint = o.footprint),
                        this.instances.set(c.path, c);
                }
            this.get_property_text('Value') == null && this.set_property_text('Value', this.default_instance.value),
                !this.get_property_text('Footprint') == null &&
                    this.set_property_text('Footprint', this.default_instance.footprint);
        }
        static {
            l(this, 'SchematicSymbol');
        }
        get lib_symbol() {
            return this.parent.lib_symbols.by_name(this.lib_name ?? this.lib_id);
        }
        get_property_text(t) {
            return this.properties.get(t)?.text;
        }
        set_property_text(t, e) {
            let r = this.properties.get(t);
            r && (r.text = e);
        }
        get reference() {
            return this.get_property_text('Reference') ?? '?';
        }
        set reference(t) {
            this.set_property_text('Reference', t);
        }
        get value() {
            return this.get_property_text('Value') ?? '';
        }
        set value(t) {
            this.set_property_text('Value', t);
        }
        get footprint() {
            return this.get_property_text('Footprint') ?? '';
        }
        set footprint(t) {
            this.set_property_text('Footprint', t);
        }
        get unit_suffix() {
            if (!this.unit || this.lib_symbol.unit_count <= 1) return '';
            let t = 'A'.charCodeAt(0),
                e = this.unit,
                r = '';
            do {
                let i = (e - 1) % 26;
                (r = String.fromCharCode(t + i) + r), (e = Math.trunc((e - i) / 26));
            } while (e > 0);
            return r;
        }
        get unit_pins() {
            return this.pins.filter((t) => !(this.unit && t.unit && this.unit != t.unit));
        }
        resolve_text_var(t) {
            if (this.properties.has(t)) return this.properties.get(t)?.shown_text;
            switch (t) {
                case 'REFERENCE':
                    return this.reference;
                case 'VALUE':
                    return this.value;
                case 'FOOTPRINT':
                    return this.footprint;
                case 'DATASHEET':
                    return this.properties.get('Datasheet')?.name;
                case 'FOOTPRINT_LIBRARY':
                    return this.footprint.split(':').at(0);
                case 'FOOTPRINT_NAME':
                    return this.footprint.split(':').at(-1);
                case 'UNIT':
                    return this.unit_suffix;
                case 'SYMBOL_LIBRARY':
                    return this.lib_symbol.library_name;
                case 'SYMBOL_NAME':
                    return this.lib_symbol.library_item_name;
                case 'SYMBOL_DESCRIPTION':
                    return this.lib_symbol.description;
                case 'SYMBOL_KEYWORDS':
                    return this.lib_symbol.keywords;
                case 'EXCLUDE_FROM_BOM':
                    return this.in_bom ? '' : 'Excluded from BOM';
                case 'EXCLUDE_FROM_BOARD':
                    return this.on_board ? '' : 'Excluded from board';
                case 'DNP':
                    return this.dnp ? 'DNP' : '';
            }
            return this.parent.resolve_text_var(t);
        }
    },
    Gr = class {
        static {
            l(this, 'SchematicSymbolInstance');
        }
        constructor() {}
    },
    b2 = class {
        constructor(t, e) {
            this.parent = e;
            Object.assign(
                this,
                g(
                    t,
                    a.start('pin'),
                    a.positional('number', R.string),
                    a.pair('uuid', R.string),
                    a.pair('alternate', R.string),
                ),
            );
        }
        static {
            l(this, 'PinInstance');
        }
        get definition() {
            return this.parent.lib_symbol.pin_by_number(this.number, this.parent.convert);
        }
        get unit() {
            return this.definition.unit;
        }
    },
    Er = class {
        constructor(t) {
            this.sheet_instances = new Map();
            Object.assign(
                this,
                g(
                    t,
                    a.start('sheet_instances'),
                    a.mapped_collection('sheet_instances', 'path', (e) => e.path, R.item(Jr)),
                ),
            );
        }
        static {
            l(this, 'SheetInstances');
        }
        get(t) {
            return this.sheet_instances.get(t);
        }
    },
    Jr = class {
        static {
            l(this, 'SheetInstance');
        }
        constructor(t) {
            Object.assign(this, g(t, a.start('path'), a.positional('path', R.string), a.pair('page', R.string)));
        }
    },
    Ir = class {
        constructor(t) {
            this.symbol_instances = new Map();
            Object.assign(
                this,
                g(
                    t,
                    a.start('symbol_instances'),
                    a.mapped_collection('symbol_instances', 'path', (e) => e.path, R.item(kr)),
                ),
            );
        }
        static {
            l(this, 'SymbolInstances');
        }
        get(t) {
            return this.symbol_instances.get(t);
        }
    },
    kr = class {
        static {
            l(this, 'SymbolInstance');
        }
        constructor(t) {
            Object.assign(
                this,
                g(
                    t,
                    a.start('path'),
                    a.positional('path', R.string),
                    a.pair('reference', R.string),
                    a.pair('unit', R.number),
                    a.pair('value', R.string),
                    a.pair('footprint', R.string),
                ),
            );
        }
    },
    ne = class {
        constructor(t, e) {
            this.parent = e;
            this.properties = new Map();
            this.pins = [];
            this.instances = new Map();
            let r = g(
                    t,
                    a.start('sheet'),
                    a.item('at', H),
                    a.vec2('size'),
                    a.item('stroke', q),
                    a.item('fill', e3),
                    a.pair('fields_autoplaced', R.boolean),
                    a.pair('uuid', R.string),
                    a.mapped_collection('properties', 'property', (n) => n.name, R.item(we, this)),
                    a.collection('pins', 'pin', R.item(Ar, this)),
                    a.object(
                        'instances',
                        {},
                        a.collection(
                            'projects',
                            'project',
                            R.object(
                                null,
                                a.start('project'),
                                a.positional('name', R.string),
                                a.collection(
                                    'paths',
                                    'path',
                                    R.object(null, a.start('path'), a.positional('path'), a.pair('page', R.string)),
                                ),
                            ),
                        ),
                    ),
                ),
                i = r.instances;
            delete r.instances, Object.assign(this, r);
            for (let n of i?.projects ?? [])
                for (let o of n?.paths ?? []) {
                    let c = new t3();
                    (c.path = o.path), (c.page = o.page), this.instances.set(c.path, c);
                }
        }
        static {
            l(this, 'SchematicSheet');
        }
        get_property_text(t) {
            return this.properties.get(t)?.text;
        }
        get sheetname() {
            return this.get_property_text('Sheetname') ?? this.get_property_text('Sheet name');
        }
        get sheetfile() {
            return this.get_property_text('Sheetfile') ?? this.get_property_text('Sheet file');
        }
        resolve_text_var(t) {
            return this.parent?.resolve_text_var(t);
        }
    },
    Ar = class {
        constructor(t, e) {
            this.parent = e;
            Object.assign(
                this,
                g(
                    t,
                    a.start('pin'),
                    a.positional('name', R.string),
                    a.positional('shape', R.string),
                    a.item('at', H),
                    a.item('effects', J),
                    a.pair('uuid', R.string),
                ),
            );
        }
        static {
            l(this, 'SchematicSheetPin');
        }
    },
    t3 = class {
        static {
            l(this, 'SchematicSheetInstance');
        }
    };
var Qs = `(kicad_wks (version 20210606) (generator pl_editor)
  (setup
    (textsize 1.5 1.5) (linewidth 0.15) (textlinewidth 0.15)
    (left_margin 10) (right_margin 10) (top_margin 10) (bottom_margin 10))
  (rect (name "") (start 110 34) (end 2 2) (comment "rect around the title block"))
  (rect (name "") (start 0 0 ltcorner) (end 0 0) (repeat 2) (incrx 2) (incry 2))
  (line (name "") (start 50 2 ltcorner) (end 50 0 ltcorner) (repeat 30) (incrx 50))
  (tbtext "1" (name "") (pos 25 1 ltcorner) (font (size 1.3 1.3)) (repeat 100) (incrx 50))
  (line (name "") (start 50 2 lbcorner) (end 50 0 lbcorner) (repeat 30) (incrx 50))
  (tbtext "1" (name "") (pos 25 1 lbcorner) (font (size 1.3 1.3)) (repeat 100) (incrx 50))
  (line (name "") (start 0 50 ltcorner) (end 2 50 ltcorner) (repeat 30) (incry 50))
  (tbtext "A" (name "") (pos 1 25 ltcorner) (font (size 1.3 1.3)) (justify center) (repeat 100) (incry 50))
  (line (name "") (start 0 50 rtcorner) (end 2 50 rtcorner) (repeat 30) (incry 50))
  (tbtext "A" (name "") (pos 1 25 rtcorner) (font (size 1.3 1.3)) (justify center) (repeat 100) (incry 50))
  (tbtext "Date: \${ISSUE_DATE}" (name "") (pos 87 6.9))
  (line (name "") (start 110 5.5) (end 2 5.5))
  (tbtext "\${KICAD_VERSION}" (name "") (pos 109 4.1) (comment "Kicad version"))
  (line (name "") (start 110 8.5) (end 2 8.5))
  (tbtext "Rev: \${REVISION}" (name "") (pos 24 6.9) (font bold))
  (tbtext "Size: \${PAPER}" (name "") (pos 109 6.9) (comment "Paper format name"))
  (tbtext "Id: \${#}/\${##}" (name "") (pos 24 4.1) (comment "Sheet id"))
  (line (name "") (start 110 12.5) (end 2 12.5))
  (tbtext "Title: \${TITLE}" (name "") (pos 109 10.7) (font (size 2 2) bold italic))
  (tbtext "File: \${FILENAME}" (name "") (pos 109 14.3))
  (line (name "") (start 110 18.5) (end 2 18.5))
  (tbtext "Sheet: \${SHEETPATH}" (name "") (pos 109 17))
  (tbtext "\${COMPANY}" (name "") (pos 109 20) (font bold) (comment "Company name"))
  (tbtext "\${COMMENT1}" (name "") (pos 109 23) (comment "Comment 0"))
  (tbtext "\${COMMENT2}" (name "") (pos 109 26) (comment "Comment 1"))
  (tbtext "\${COMMENT3}" (name "") (pos 109 29) (comment "Comment 2"))
  (tbtext "\${COMMENT4}" (name "") (pos 109 32) (comment "Comment 3"))
  (line (name "") (start 90 8.5) (end 90 5.5))
  (line (name "") (start 26 8.5) (end 26 2))
)
`;
var _2 = class s {
        constructor(t) {
            this.setup = new i3();
            this.drawings = [];
            Object.assign(
                this,
                g(
                    t,
                    a.start('kicad_wks'),
                    a.pair('version', R.number),
                    a.pair('generator', R.string),
                    a.item('setup', i3),
                    a.collection('drawings', 'line', R.item(M2, this)),
                    a.collection('drawings', 'rect', R.item(gt, this)),
                    a.collection('drawings', 'polygon', R.item(Cr, this)),
                    a.collection('drawings', 'bitmap', R.item(Dr, this)),
                    a.collection('drawings', 'tbtext', R.item(f2, this)),
                ),
            );
        }
        static {
            l(this, 'DrawingSheet');
        }
        static default() {
            return new s(Qs);
        }
        *items() {
            yield new gt(
                `(rect (name "") (start ${-this.setup.left_margin} ${-this.setup.right_margin} ltcorner) (end ${-this.setup.right_margin} ${-this.setup.bottom_margin} rbcorner) (comment "page outline"))`,
                this,
            ),
                yield* this.drawings;
        }
        get paper() {
            return this.document?.paper;
        }
        get width() {
            return this.paper?.width ?? 297;
        }
        get height() {
            return this.paper?.height ?? 210;
        }
        get size() {
            return new d(this.width, this.height);
        }
        get top_left() {
            return new d(this.setup.left_margin, this.setup.top_margin);
        }
        get top_right() {
            return new d(this.width - this.setup.right_margin, this.setup?.top_margin);
        }
        get bottom_right() {
            return new d(this.width - this.setup.right_margin, this.height - this.setup.bottom_margin);
        }
        get bottom_left() {
            return new d(this.setup.left_margin, this.height - this.setup.bottom_margin);
        }
        get margin_bbox() {
            return O.from_points([this.top_left, this.bottom_right]);
        }
        get page_bbox() {
            return O.from_corners(0, 0, this.width, this.height);
        }
        resolve_text_var(t) {
            switch (t) {
                case 'PAPER':
                    return this.paper?.size || '';
                case '#':
                    return '1';
                case '##':
                    return '1';
                case 'SHEETPATH':
                    return '/';
                case 'KICAD_VERSION':
                    return 'KiCanvas Alpha';
            }
            return this.document?.resolve_text_var(t);
        }
    },
    i3 = class {
        constructor(t) {
            this.linewidth = 0.15;
            this.textsize = new d(1.5, 1.5);
            this.textlinewidth = 0.15;
            this.top_margin = 10;
            this.left_margin = 10;
            this.bottom_margin = 10;
            this.right_margin = 10;
            t &&
                Object.assign(
                    this,
                    g(
                        t,
                        a.start('setup'),
                        a.pair('linewidth', R.number),
                        a.vec2('textsize'),
                        a.pair('textlinewidth', R.number),
                        a.pair('top_margin', R.number),
                        a.pair('left_margin', R.number),
                        a.pair('bottom_margin', R.number),
                        a.pair('right_margin', R.number),
                    ),
                );
        }
        static {
            l(this, 'Setup');
        }
    },
    We = class {
        constructor(t) {
            this.position = new d(0, 0);
            this.anchor = 'rbcorner';
            let e = g(
                t,
                a.positional('start_token'),
                a.positional('x', R.number),
                a.positional('y', R.number),
                a.positional('anchor', R.string),
            );
            (this.position.x = e.x), (this.position.y = e.y), (this.anchor = e.anchor ?? this.anchor);
        }
        static {
            l(this, 'Coordinate');
        }
    },
    oe = class {
        constructor(t) {
            this.repeat = 1;
            this.incry = 0;
            this.incrx = 0;
            this.parent = t;
        }
        static {
            l(this, 'DrawingSheetItem');
        }
        static {
            this.common_expr_defs = [
                a.pair('name', R.string),
                a.pair('comment', R.string),
                a.pair('option', R.string),
                a.pair('repeat', R.number),
                a.pair('incrx', R.number),
                a.pair('incry', R.number),
                a.pair('linewidth', R.number),
            ];
        }
    },
    M2 = class extends oe {
        constructor(e, r) {
            super(r);
            Object.assign(this, g(e, a.start('line'), a.item('start', We), a.item('end', We), ...oe.common_expr_defs));
        }
        static {
            l(this, 'Line');
        }
    },
    gt = class extends oe {
        constructor(e, r) {
            super(r);
            Object.assign(this, g(e, a.start('rect'), a.item('start', We), a.item('end', We), ...oe.common_expr_defs));
        }
        static {
            l(this, 'Rect');
        }
    },
    Cr = class extends oe {
        constructor(e, r) {
            super(r);
            Object.assign(
                this,
                g(
                    e,
                    a.start('polygon'),
                    a.item('pos', We),
                    a.pair('rotate', R.number),
                    a.list('pts', R.vec2),
                    ...oe.common_expr_defs,
                ),
            );
        }
        static {
            l(this, 'Polygon');
        }
    },
    Dr = class extends oe {
        constructor(e, r) {
            super(r);
            Object.assign(
                this,
                g(
                    e,
                    a.start('bitmap'),
                    a.item('pos', We),
                    a.pair('scale', R.number),
                    a.pair('pngdata', R.string),
                    ...oe.common_expr_defs,
                ),
            );
        }
        static {
            l(this, 'Bitmap');
        }
    },
    f2 = class extends oe {
        constructor(e, r) {
            super(r);
            this.incrlabel = 1;
            this.rotate = 0;
            Object.assign(
                this,
                g(
                    e,
                    a.start('tbtext'),
                    a.positional('text'),
                    a.item('pos', We),
                    a.pair('incrlabel', R.number),
                    a.pair('maxlen', R.number),
                    a.pair('maxheight', R.number),
                    a.item('font', Br),
                    a.pair('rotate', R.number),
                    a.pair('justify', R.string),
                    ...oe.common_expr_defs,
                ),
            );
        }
        static {
            l(this, 'TbText');
        }
        get shown_text() {
            return Ae(this.text, this.parent);
        }
    },
    Br = class {
        constructor(t) {
            this.color = h.transparent_black;
            this.size = new d(1.27, 1.27);
            Object.assign(
                this,
                g(
                    t,
                    a.start('font'),
                    a.pair('face', R.string),
                    a.atom('bold'),
                    a.atom('italic'),
                    a.vec2('size'),
                    a.pair('linewidth', R.number),
                ),
            );
        }
        static {
            l(this, 'Font');
        }
    };
function $r(s, t) {
    if (!(t == null || t == null)) for (let e of Object.keys(t)) _s(s[e]) ? $r(s[e], t[e]) : (s[e] = t[e]);
}
l($r, 'merge');
var Be = class s {
        constructor() {
            this.board = new jr();
            this.boards = [];
            this.libraries = { pinned_footprint_libs: [], pinned_symbol_libs: [] };
            this.meta = { filename: 'unknown.kicad_pro', version: 1 };
            this.pcbnew = { page_layout_descr_file: '' };
            this.schematic = new ei();
            this.sheets = [];
            this.text_variables = {};
        }
        static {
            l(this, 'ProjectSettings');
        }
        static load(t) {
            let e = new s();
            return $r(e, t), e;
        }
    },
    jr = class {
        constructor() {
            this.design_settings = new zr();
        }
        static {
            l(this, 'BoardSettings');
        }
    },
    zr = class {
        constructor() {
            this.defaults = new qr();
        }
        static {
            l(this, 'BoardDesignSettings');
        }
    },
    qr = class {
        constructor() {
            this.board_outline_line_width = 0.1;
            this.copper_line_width = 0.2;
            this.copper_text_size_h = 1.5;
            this.copper_text_size_v = 1.5;
            this.copper_text_thickness = 0.3;
            this.other_line_width = 0.15;
            this.silk_line_width = 0.15;
            this.silk_text_size_h = 1;
            this.silk_text_size_v = 1;
            this.silk_text_thickness = 0.15;
        }
        static {
            l(this, 'BoardDesignSettingsDefaults');
        }
    },
    ei = class {
        constructor() {
            this.drawing = new ti();
            this.meta = { version: 1 };
        }
        static {
            l(this, 'SchematicSettings');
        }
    },
    ti = class {
        constructor() {
            this.dashed_lines_dash_length_ratio = 12;
            this.dashed_lines_gap_length_ratio = 3;
            this.default_line_thickness = 6;
            this.default_text_size = 50;
            this.intersheets_ref_own_page = !1;
            this.intersheets_ref_prefix = '';
            this.intersheets_ref_short = !1;
            this.intersheets_ref_show = !1;
            this.intersheets_ref_suffix = '';
            this.junction_size_choice = 3;
            this.label_size_ratio = 0.375;
            this.pin_symbol_size = 25;
            this.text_offset_ratio = 0.15;
        }
        static {
            l(this, 'SchematicDrawingSettings');
        }
    };
var s3 = new ce('kicanvas:project'),
    Wt = class extends EventTarget {
        constructor() {
            super(...arguments);
            this.#t = new Map();
            this.#r = new Map();
            this.loaded = new fe();
            this.settings = new Be();
            this.#a = null;
        }
        static {
            l(this, 'Project');
        }
        #e;
        #t;
        #r;
        #i;
        dispose() {
            this.#t.clear(), this.#r.clear();
        }
        async load(e) {
            s3.info(`Loading project from ${e.constructor.name}`),
                (this.settings = new Be()),
                this.#t.clear(),
                this.#r.clear(),
                (this.#e = e);
            let r = [];
            for (let i of this.#e.list()) r.push(this.#s(i));
            for (await Promise.all(r); r.length; ) {
                r = [];
                for (let i of this.schematics())
                    for (let n of i.sheets)
                        !this.#t.get(n.sheetfile ?? '') && n.sheetfile && r.push(this.#s(n.sheetfile));
                await Promise.all(r);
            }
            this.#c(), this.loaded.open(), this.dispatchEvent(new CustomEvent('load', { detail: this }));
        }
        async #s(e) {
            if ((s3.info(`Loading file ${e}`), e.endsWith('.kicad_sch'))) return await this.#n(me, e);
            if (e.endsWith('.kicad_pcb')) return await this.#n(ge, e);
            if (e.endsWith('.kicad_pro')) return this.#l(e);
            s3.warn(`Couldn't load ${e}: unknown file type`);
        }
        async #n(e, r) {
            if (this.#t.has(r)) return this.#t.get(r);
            let i = await this.#o(r),
                n = new e(r, i);
            if (((n.project = this), this.#t.set(r, n), n instanceof ge)) {
                let o = new Pt(this, 'pcb', n.filename, '', 'Board', '');
                this.#r.set(o.project_path, o);
            }
            return n;
        }
        async #l(e) {
            let r = await this.#o(e),
                i = JSON.parse(r);
            this.settings = Be.load(i);
        }
        async #o(e) {
            return await (await this.#e.get(e)).text();
        }
        #c() {
            s3.info('Determining schematic hierarchy');
            let e = new Map(),
                r = new Map();
            for (let u of this.schematics()) {
                e.set(`/${u.uuid}`, u);
                for (let p of u.sheets)
                    if (this.#t.get(p.sheetfile ?? ''))
                        for (let b of p.instances.values())
                            e.set(b.path, u), r.set(`${b.path}/${p.uuid}`, { sheet: p, instance: b });
            }
            let i = Array.from(r.keys()).sort((u, p) => u.length - p.length),
                n;
            for (let u of i) {
                let p = u.split('/').slice(0, -1).join('/');
                if (p && ((n = e.get(p)), n)) break;
            }
            let o = [];
            if (n) {
                (this.#i = new Pt(this, 'schematic', n.filename, `/${n.uuid}`, 'Root', '1')), o.push(this.#i);
                for (let [u, p] of r.entries())
                    o.push(
                        new Pt(
                            this,
                            'schematic',
                            p.sheet.sheetfile,
                            u,
                            p.sheet.sheetname ?? p.sheet.sheetfile,
                            p.instance.page ?? '',
                        ),
                    );
            }
            o = pe(o, (u) => u.page);
            for (let u of o) this.#r.set(u.project_path, u);
            let c = new Set(Ts(this.#r.values(), (u) => u.filename));
            for (let u of this.schematics())
                if (!c.has(u.filename)) {
                    let p = new Pt(this, 'schematic', u.filename, `/${u.uuid}`, u.filename);
                    this.#r.set(p.project_path, p);
                }
            this.#i = Ct(this.#r.values());
        }
        *files() {
            yield* this.#t.values();
        }
        file_by_name(e) {
            return this.#t.get(e);
        }
        *boards() {
            for (let e of this.#t.values()) e instanceof ge && (yield e);
        }
        get has_boards() {
            return Dt(this.boards()) > 0;
        }
        *schematics() {
            for (let e of this.#t.values()) e instanceof me && (yield e);
        }
        get has_schematics() {
            return Dt(this.schematics()) > 0;
        }
        *pages() {
            yield* this.#r.values();
        }
        get first_page() {
            return Ct(this.pages());
        }
        get root_schematic_page() {
            return this.#i;
        }
        page_by_path(e) {
            return this.#r.get(e);
        }
        async download(e) {
            return this.#r.has(e) && (e = this.#r.get(e).filename), await this.#e.download(e);
        }
        #a;
        get active_page() {
            return this.#a;
        }
        set_active_page(e) {
            let r;
            if ((G(e) ? (r = this.page_by_path(e)) : (r = e), r || (r = this.first_page), !r))
                throw new Error(`Unable to find ${e}`);
            (this.#a = r), this.dispatchEvent(new CustomEvent('change', { detail: this }));
        }
    },
    Pt = class {
        constructor(t, e, r, i, n, o) {
            this.project = t;
            this.type = e;
            this.filename = r;
            this.sheet_path = i;
            this.name = n;
            this.page = o;
        }
        static {
            l(this, 'ProjectPage');
        }
        get project_path() {
            return this.sheet_path ? `${this.filename}:${this.sheet_path}` : this.filename;
        }
        get document() {
            return this.project.file_by_name(this.filename);
        }
    };
var n3 = class extends Error {
        constructor(e, r, i, n) {
            super(`GitHub${e}: ${r}: ${i}`);
            this.name = e;
            this.url = r;
            this.description = i;
            this.response = n;
        }
        static {
            l(this, 'BaseAPIError');
        }
    },
    ri = class extends n3 {
        static {
            l(this, 'UnknownError');
        }
        constructor(t, e, r) {
            super('NotFoundError', t, e, r);
        }
    },
    ii = class extends n3 {
        static {
            l(this, 'NotFoundError');
        }
        constructor(t, e) {
            super('NotFoundError', t, 'not found', e);
        }
    },
    $e = class s {
        static {
            l(this, 'GitHub');
        }
        static {
            this.html_base_url = 'https://github.com';
        }
        static {
            this.base_url = 'https://api.github.com/';
        }
        static {
            this.api_version = '2022-11-28';
        }
        static {
            this.accept_header = 'application/vnd.github+json';
        }
        constructor() {
            this.headers = { Accept: s.accept_header, 'X-GitHub-Api-Version': s.api_version };
        }
        static parse_url(t) {
            t = new URL(t, s.html_base_url);
            let e = t.pathname.split('/');
            if (e.length < 3) return null;
            let [, r, i, ...n] = e,
                o,
                c,
                u;
            return (
                n.length
                    ? (n[0] == 'blob' || n[0] == 'tree') && ((o = n.shift()), (c = n.shift()), (u = n.join('/')))
                    : (o = 'root'),
                { owner: r, repo: i, type: o, ref: c, path: u }
            );
        }
        async request(t, e, r) {
            let i = this.constructor,
                n = new URL(t, i.base_url);
            if (e) {
                let u = new URLSearchParams(e).toString();
                n.search = `?${u}`;
            }
            let o = new Request(n, {
                    method: r ? 'POST' : 'GET',
                    headers: this.headers,
                    body: r ? JSON.stringify(r) : void 0,
                }),
                c = await fetch(o);
            return (
                await this.handle_server_error(c),
                (this.last_response = c),
                (this.rate_limit_remaining = parseInt(c.headers.get('x-ratelimit-remaining') ?? '', 10)),
                c.headers.get('content-type') == 'application/json; charset=utf-8' ? await c.json() : await c.text()
            );
        }
        async handle_server_error(t) {
            switch (t.status) {
                case 200:
                    return;
                case 404:
                    throw new ii(t.url, t);
                case 500:
                    throw new ri(t.url, await t.text(), t);
            }
        }
        async repos_contents(t, e, r, i) {
            return await this.request(`repos/${t}/${e}/contents/${r}`, { ref: i ?? '' });
        }
    },
    o3 = class s {
        static {
            l(this, 'GitHubUserContent');
        }
        static {
            this.base_url = 'https://raw.githubusercontent.com/';
        }
        constructor() {}
        async get(t) {
            let e = new URL(t, s.base_url),
                r = new Request(e, { method: 'GET' }),
                n = await (await fetch(r)).blob(),
                o = Xe(e) ?? 'unknown';
            return new File([n], o);
        }
        convert_url(t) {
            let e = new URL(t, 'https://github.com/');
            if (e.host == 'raw.githubusercontent.com') return e;
            let r = e.pathname.split('/');
            if (r.length < 4) throw new Error(`URL ${t} can't be converted to a raw.githubusercontent.com URL`);
            let [i, n, o, c, u, ...p] = r;
            if (c != 'blob') throw new Error(`URL ${t} can't be converted to a raw.githubusercontent.com URL`);
            let m = [n, o, u, ...p].join('/');
            return new URL(m, s.base_url);
        }
    };
var Wn = ['kicad_pcb', 'kicad_pro', 'kicad_sch'],
    vs = new o3(),
    Zn = new $e(),
    N2 = class s extends it {
        constructor(e) {
            super();
            this.files_to_urls = e;
        }
        static {
            l(this, 'GitHubFileSystem');
        }
        static async fromURLs(...e) {
            let r = new Map();
            for (let i of e) {
                let n = $e.parse_url(i);
                if (!(!n || !n.owner || !n.repo)) {
                    if ((n.type == 'root' && ((n.ref = 'HEAD'), (n.type = 'tree')), n.type == 'blob'))
                        if (['kicad_sch', 'kicad_pcb'].includes(D3(n.path))) {
                            let o = vs.convert_url(i),
                                c = Xe(o);
                            r.set(c, o);
                        } else (n.type = 'tree'), (n.path = hs(n.path));
                    if (n.type == 'tree') {
                        let o = await Zn.repos_contents(n.owner, n.repo, n.path ?? '', n.ref);
                        for (let c of o) {
                            let u = c.name,
                                p = c.download_url;
                            !u || !p || !Wn.includes(D3(u)) || r.set(u, p);
                        }
                    }
                }
            }
            return new s(r);
        }
        *list() {
            yield* this.files_to_urls.keys();
        }
        get(e) {
            let r = this.files_to_urls.get(e);
            if (!r) throw new Error(`File ${e} not found!`);
            return vs.get(r);
        }
        has(e) {
            return Promise.resolve(this.files_to_urls.has(e));
        }
        async download(e) {
            Gt(await this.get(e));
        }
    };
function ws(s, t) {
    let e = (s ?? '').split(' '),
        r = {},
        i = Object.getOwnPropertyNames(t);
    for (let o of i) (r[o] = !1), (r[`no${o}`] = !1);
    for (let o of e) r[o] = !0;
    let n = t;
    for (let o of i) n[o] = ((r[o] || n[o]) && !r[`no${o}`]) ?? !1;
    return t;
}
l(ws, 'parseFlagAttribute');
var V2 = class extends CustomEvent {
        static {
            l(this, 'KiCanvasEvent');
        }
        constructor(t, e, r = !1) {
            super(t, { detail: e, composed: !0, bubbles: r });
        }
    },
    ie = class s extends V2 {
        static {
            l(this, 'KiCanvasLoadEvent');
        }
        static {
            this.type = 'kicanvas:load';
        }
        constructor() {
            super(s.type, null);
        }
    },
    D = class s extends V2 {
        static {
            l(this, 'KiCanvasSelectEvent');
        }
        static {
            this.type = 'kicanvas:select';
        }
        constructor(t) {
            super(s.type, t, !0);
        }
    },
    Zt = class s extends V2 {
        static {
            l(this, 'KiCanvasMouseMoveEvent');
        }
        static {
            this.type = 'kicanvas:mousemove';
        }
        constructor(t) {
            super(s.type, t, !0);
        }
    };
var si = class extends N {
    static {
        l(this, 'KCHelpPanel');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            p {
                margin: 0;
                padding: 0.5em;
            }

            a {
                color: var(--button-bg);
            }

            a:hover {
                color: var(--button-hover-bg);
            }
        `,
        ];
    }
    render() {
        return _`
            <kc-ui-panel>
                <kc-ui-panel-title title="Help"></kc-ui-panel-title>
                <kc-ui-panel-body>
                    <p>
                        You're using
                        <a href="https://kicanvas.org/home">KiCanvas</a>, an
                        interactive, browser-based viewer for KiCAD schematics
                        and boards.
                    </p>
                    <p>
                        KiCanvas is very much in <strong>alpha</strong>, so
                        please
                        <a
                            href="https://github.com/theacodes/kicanvas/issues/new/choose"
                            target="_blank"
                            >file an issue on GitHub</a
                        >
                        if you run into any bugs.
                    </p>
                    <p>
                        KiCanvas is developed by
                        <a href="https://thea.codes" target="_blank"
                            >Thea Flowers</a
                        >
                        and supported by
                        <a
                            href="https://github.com/sponsors/theacodes"
                            target="_blank"
                            >community donations</a
                        >.
                    </p></kc-ui-panel-body
                >
            </kc-ui-panel>
        `;
    }
};
window.customElements.define('kc-help-panel', si);
var a3 = class {
    constructor(t = 'kc', e) {
        this.prefix = t;
        this.reviver = e;
    }
    static {
        l(this, 'LocalStorage');
    }
    key_for(t) {
        return `${this.prefix}:${t}`;
    }
    set(t, e, r) {
        window.localStorage.setItem(this.key_for(t), JSON.stringify({ val: e, exp: r }));
    }
    get(t, e) {
        let r = window.localStorage.getItem(this.key_for(t));
        if (r === null) return e;
        let i = JSON.parse(r, this.reviver);
        return i.exp && i.exp < Date.now() ? (this.delete(t), e) : i.val;
    }
    delete(t) {
        window.localStorage.removeItem(this.key_for(t));
    }
};
var Sn = {
        name: 'witchhazel',
        friendly_name: 'Witch Hazel',
        board: {
            anchor: h.from_css('rgb(100, 203, 150)'),
            aux_items: h.from_css('rgb(255, 98, 0)'),
            b_adhes: h.from_css('rgb(0, 0, 132)'),
            b_crtyd: h.from_css('rgb(174, 129, 255)'),
            b_fab: h.from_css('rgb(113, 103, 153)'),
            b_mask: h.from_css('rgba(78, 129, 137, 0.800)'),
            b_paste: h.from_css('rgba(167, 234, 255, 0.502)'),
            b_silks: h.from_css('rgb(136, 100, 203)'),
            background: h.from_css('rgb(19, 18, 24)'),
            cmts_user: h.from_css('rgb(129, 255, 190)'),
            copper: {
                b: h.from_css('rgb(111, 204, 219)'),
                f: h.from_css('rgb(226, 114, 153)'),
                in1: h.from_css('rgb(127, 200, 127)'),
                in10: h.from_css('rgb(237, 124, 51)'),
                in11: h.from_css('rgb(91, 195, 235)'),
                in12: h.from_css('rgb(247, 111, 142)'),
                in13: h.from_css('rgb(167, 165, 198)'),
                in14: h.from_css('rgb(40, 204, 217)'),
                in15: h.from_css('rgb(232, 178, 167)'),
                in16: h.from_css('rgb(242, 237, 161)'),
                in17: h.from_css('rgb(237, 124, 51)'),
                in18: h.from_css('rgb(91, 195, 235)'),
                in19: h.from_css('rgb(247, 111, 142)'),
                in2: h.from_css('rgb(206, 125, 44)'),
                in20: h.from_css('rgb(167, 165, 198)'),
                in21: h.from_css('rgb(40, 204, 217)'),
                in22: h.from_css('rgb(232, 178, 167)'),
                in23: h.from_css('rgb(242, 237, 161)'),
                in24: h.from_css('rgb(237, 124, 51)'),
                in25: h.from_css('rgb(91, 195, 235)'),
                in26: h.from_css('rgb(247, 111, 142)'),
                in27: h.from_css('rgb(167, 165, 198)'),
                in28: h.from_css('rgb(40, 204, 217)'),
                in29: h.from_css('rgb(232, 178, 167)'),
                in3: h.from_css('rgb(79, 203, 203)'),
                in30: h.from_css('rgb(242, 237, 161)'),
                in4: h.from_css('rgb(219, 98, 139)'),
                in5: h.from_css('rgb(167, 165, 198)'),
                in6: h.from_css('rgb(40, 204, 217)'),
                in7: h.from_css('rgb(232, 178, 167)'),
                in8: h.from_css('rgb(242, 237, 161)'),
                in9: h.from_css('rgb(141, 203, 129)'),
            },
            cursor: h.from_css('rgb(220, 200, 255)'),
            drc_error: h.from_css('rgba(255, 0, 237, 0.800)'),
            drc_exclusion: h.from_css('rgba(255, 255, 255, 0.800)'),
            drc_warning: h.from_css('rgba(255, 208, 66, 0.800)'),
            dwgs_user: h.from_css('rgb(248, 248, 240)'),
            eco1_user: h.from_css('rgb(129, 238, 255)'),
            eco2_user: h.from_css('rgb(255, 129, 173)'),
            edge_cuts: h.from_css('rgb(129, 255, 190)'),
            f_adhes: h.from_css('rgb(132, 0, 132)'),
            f_crtyd: h.from_css('rgb(174, 129, 255)'),
            f_fab: h.from_css('rgb(113, 103, 153)'),
            f_mask: h.from_css('rgb(137, 78, 99)'),
            f_paste: h.from_css('rgba(252, 249, 255, 0.502)'),
            f_silks: h.from_css('rgb(220, 200, 255)'),
            footprint_text_invisible: h.from_css('rgb(40, 38, 52)'),
            grid: h.from_css('rgb(113, 103, 153)'),
            grid_axes: h.from_css('rgb(255, 129, 173)'),
            margin: h.from_css('rgb(78, 137, 107)'),
            no_connect: h.from_css('rgb(255, 148, 0)'),
            pad_plated_hole: h.from_css('rgb(194, 194, 0)'),
            pad_through_hole: h.from_css('rgb(227, 209, 46)'),
            non_plated_hole: h.from_css('rgb(129, 255, 190)'),
            ratsnest: h.from_css('rgb(128, 119, 168)'),
            user_1: h.from_css('rgb(194, 118, 0)'),
            user_2: h.from_css('rgb(89, 148, 220)'),
            user_3: h.from_css('rgb(180, 219, 210)'),
            user_4: h.from_css('rgb(216, 200, 82)'),
            user_5: h.from_css('rgb(194, 194, 194)'),
            user_6: h.from_css('rgb(89, 148, 220)'),
            user_7: h.from_css('rgb(180, 219, 210)'),
            user_8: h.from_css('rgb(216, 200, 82)'),
            user_9: h.from_css('rgb(232, 178, 167)'),
            via_blind_buried: h.from_css('rgb(203, 196, 100)'),
            via_hole: h.from_css('rgb(40, 38, 52)'),
            via_micro: h.from_css('rgb(255, 148, 0)'),
            via_through: h.from_css('rgb(227, 209, 46)'),
            worksheet: h.from_css('rgb(100, 190, 203)'),
        },
        schematic: {
            anchor: h.from_css('rgb(174, 129, 255)'),
            aux_items: h.from_css('rgb(255, 160, 0)'),
            background: h.from_css('rgb(19, 18, 24)'),
            brightened: h.from_css('rgb(200, 255, 227)'),
            bus: h.from_css('rgb(129, 238, 255)'),
            bus_junction: h.from_css('rgb(163, 243, 255)'),
            component_body: h.from_css('rgb(67, 62, 86)'),
            component_outline: h.from_css('rgb(197, 163, 255)'),
            cursor: h.from_css('rgb(220, 200, 255)'),
            erc_error: h.from_css('rgba(255, 55, 162, 0.800)'),
            erc_warning: h.from_css('rgba(255, 92, 0, 0.800)'),
            fields: h.from_css('rgb(174, 129, 255)'),
            grid: h.from_css('rgb(113, 103, 153)'),
            grid_axes: h.from_css('rgb(255, 129, 173)'),
            hidden: h.from_css('rgb(67, 62, 86)'),
            junction: h.from_css('rgb(220, 200, 255)'),
            label_global: h.from_css('rgb(255, 247, 129)'),
            label_hier: h.from_css('rgb(163, 255, 207)'),
            label_local: h.from_css('rgb(220, 200, 255)'),
            no_connect: h.from_css('rgb(255, 129, 173)'),
            note: h.from_css('rgb(248, 248, 240)'),
            pin: h.from_css('rgb(129, 255, 190)'),
            pin_name: h.from_css('rgb(129, 255, 190)'),
            pin_number: h.from_css('rgb(100, 203, 150)'),
            reference: h.from_css('rgb(129, 238, 255)'),
            shadow: h.from_css('rgb(200, 248, 255)'),
            sheet: h.from_css('rgb(174, 129, 255)'),
            sheet_background: h.from_css('rgb(19, 18, 24)'),
            sheet_fields: h.from_css('rgb(129, 255, 190)'),
            sheet_filename: h.from_css('rgb(78, 129, 137)'),
            sheet_label: h.from_css('rgb(129, 255, 190)'),
            sheet_name: h.from_css('rgb(129, 238, 255)'),
            value: h.from_css('rgb(129, 238, 255)'),
            wire: h.from_css('rgb(174, 129, 255)'),
            worksheet: h.from_css('rgb(100, 190, 203)'),
        },
    },
    ni = Sn;
var Tn = {
        name: 'kicad',
        friendly_name: 'KiCAD',
        board: {
            anchor: h.from_css('rgb(255, 38, 226)'),
            aux_items: h.from_css('rgb(255, 255, 255)'),
            b_adhes: h.from_css('rgb(0, 0, 132)'),
            b_crtyd: h.from_css('rgb(38, 233, 255)'),
            b_fab: h.from_css('rgb(88, 93, 132)'),
            b_mask: h.from_css('rgba(2, 255, 238, 0.400)'),
            b_paste: h.from_css('rgba(0, 194, 194, 0.902)'),
            b_silks: h.from_css('rgb(232, 178, 167)'),
            background: h.from_css('rgb(0, 16, 35)'),
            cmts_user: h.from_css('rgb(89, 148, 220)'),
            copper: {
                b: h.from_css('rgb(77, 127, 196)'),
                f: h.from_css('rgb(200, 52, 52)'),
                in1: h.from_css('rgb(127, 200, 127)'),
                in10: h.from_css('rgb(237, 124, 51)'),
                in11: h.from_css('rgb(91, 195, 235)'),
                in12: h.from_css('rgb(247, 111, 142)'),
                in13: h.from_css('rgb(167, 165, 198)'),
                in14: h.from_css('rgb(40, 204, 217)'),
                in15: h.from_css('rgb(232, 178, 167)'),
                in16: h.from_css('rgb(242, 237, 161)'),
                in17: h.from_css('rgb(237, 124, 51)'),
                in18: h.from_css('rgb(91, 195, 235)'),
                in19: h.from_css('rgb(247, 111, 142)'),
                in2: h.from_css('rgb(206, 125, 44)'),
                in20: h.from_css('rgb(167, 165, 198)'),
                in21: h.from_css('rgb(40, 204, 217)'),
                in22: h.from_css('rgb(232, 178, 167)'),
                in23: h.from_css('rgb(242, 237, 161)'),
                in24: h.from_css('rgb(237, 124, 51)'),
                in25: h.from_css('rgb(91, 195, 235)'),
                in26: h.from_css('rgb(247, 111, 142)'),
                in27: h.from_css('rgb(167, 165, 198)'),
                in28: h.from_css('rgb(40, 204, 217)'),
                in29: h.from_css('rgb(232, 178, 167)'),
                in3: h.from_css('rgb(79, 203, 203)'),
                in30: h.from_css('rgb(242, 237, 161)'),
                in4: h.from_css('rgb(219, 98, 139)'),
                in5: h.from_css('rgb(167, 165, 198)'),
                in6: h.from_css('rgb(40, 204, 217)'),
                in7: h.from_css('rgb(232, 178, 167)'),
                in8: h.from_css('rgb(242, 237, 161)'),
                in9: h.from_css('rgb(141, 203, 129)'),
            },
            cursor: h.from_css('rgb(255, 255, 255)'),
            drc_error: h.from_css('rgba(215, 91, 107, 0.800)'),
            drc_exclusion: h.from_css('rgba(255, 255, 255, 0.800)'),
            drc_warning: h.from_css('rgba(255, 208, 66, 0.800)'),
            dwgs_user: h.from_css('rgb(194, 194, 194)'),
            eco1_user: h.from_css('rgb(180, 219, 210)'),
            eco2_user: h.from_css('rgb(216, 200, 82)'),
            edge_cuts: h.from_css('rgb(208, 210, 205)'),
            f_adhes: h.from_css('rgb(132, 0, 132)'),
            f_crtyd: h.from_css('rgb(255, 38, 226)'),
            f_fab: h.from_css('rgb(175, 175, 175)'),
            f_mask: h.from_css('rgba(216, 100, 255, 0.400)'),
            f_paste: h.from_css('rgba(180, 160, 154, 0.902)'),
            f_silks: h.from_css('rgb(242, 237, 161)'),
            footprint_text_invisible: h.from_css('rgb(132, 132, 132)'),
            grid: h.from_css('rgb(132, 132, 132)'),
            grid_axes: h.from_css('rgb(194, 194, 194)'),
            margin: h.from_css('rgb(255, 38, 226)'),
            no_connect: h.from_css('rgb(0, 0, 132)'),
            pad_plated_hole: h.from_css('rgb(194, 194, 0)'),
            pad_through_hole: h.from_css('rgb(227, 183, 46)'),
            non_plated_hole: h.from_css('rgb(26, 196, 210)'),
            ratsnest: h.from_css('rgba(245, 255, 213, 0.702)'),
            user_1: h.from_css('rgb(194, 194, 194)'),
            user_2: h.from_css('rgb(89, 148, 220)'),
            user_3: h.from_css('rgb(180, 219, 210)'),
            user_4: h.from_css('rgb(216, 200, 82)'),
            user_5: h.from_css('rgb(194, 194, 194)'),
            user_6: h.from_css('rgb(89, 148, 220)'),
            user_7: h.from_css('rgb(180, 219, 210)'),
            user_8: h.from_css('rgb(216, 200, 82)'),
            user_9: h.from_css('rgb(232, 178, 167)'),
            via_blind_buried: h.from_css('rgb(187, 151, 38)'),
            via_hole: h.from_css('rgb(227, 183, 46)'),
            via_micro: h.from_css('rgb(0, 132, 132)'),
            via_through: h.from_css('rgb(236, 236, 236)'),
            worksheet: h.from_css('rgb(200, 114, 171)'),
        },
        schematic: {
            anchor: h.from_css('rgb(0, 0, 255)'),
            aux_items: h.from_css('rgb(0, 0, 0)'),
            background: h.from_css('rgb(245, 244, 239)'),
            brightened: h.from_css('rgb(255, 0, 255)'),
            bus: h.from_css('rgb(0, 0, 132)'),
            bus_junction: h.from_css('rgb(0, 0, 132)'),
            component_body: h.from_css('rgb(255, 255, 194)'),
            component_outline: h.from_css('rgb(132, 0, 0)'),
            cursor: h.from_css('rgb(15, 15, 15)'),
            erc_error: h.from_css('rgba(230, 9, 13, 0.800)'),
            erc_warning: h.from_css('rgba(209, 146, 0, 0.800)'),
            fields: h.from_css('rgb(132, 0, 132)'),
            grid: h.from_css('rgb(181, 181, 181)'),
            grid_axes: h.from_css('rgb(0, 0, 132)'),
            hidden: h.from_css('rgb(94, 194, 194)'),
            junction: h.from_css('rgb(0, 150, 0)'),
            label_global: h.from_css('rgb(132, 0, 0)'),
            label_hier: h.from_css('rgb(114, 86, 0)'),
            label_local: h.from_css('rgb(15, 15, 15)'),
            no_connect: h.from_css('rgb(0, 0, 132)'),
            note: h.from_css('rgb(0, 0, 194)'),
            pin: h.from_css('rgb(132, 0, 0)'),
            pin_name: h.from_css('rgb(0, 100, 100)'),
            pin_number: h.from_css('rgb(169, 0, 0)'),
            reference: h.from_css('rgb(0, 100, 100)'),
            shadow: h.from_css('rgba(199, 235, 255, 0.800)'),
            sheet: h.from_css('rgb(132, 0, 0)'),
            sheet_background: h.from_css('rgba(255, 255, 255, 0.000)'),
            sheet_fields: h.from_css('rgb(132, 0, 132)'),
            sheet_filename: h.from_css('rgb(114, 86, 0)'),
            sheet_label: h.from_css('rgb(0, 100, 100)'),
            sheet_name: h.from_css('rgb(0, 100, 100)'),
            value: h.from_css('rgb(0, 100, 100)'),
            wire: h.from_css('rgb(0, 150, 0)'),
            worksheet: h.from_css('rgb(132, 0, 0)'),
        },
    },
    Ys = Tn;
var Ks = [ni, Ys],
    Ln = new Map(Ks.map((s) => [s.name, s])),
    Ze = {
        default: ni,
        by_name(s) {
            return Ln.get(s) ?? this.default;
        },
        list() {
            return Ks;
        },
    };
var Re = class s extends EventTarget {
    constructor() {
        super(...arguments);
        this.storage = new a3('kc:prefs');
        this.theme = Ze.default;
        this.alignControlsWithKiCad = !0;
    }
    static {
        l(this, 'Preferences');
    }
    static {
        this.INSTANCE = new s();
    }
    save() {
        this.storage.set('theme', this.theme.name),
            this.storage.set('alignControlsWithKiCad', this.alignControlsWithKiCad),
            this.dispatchEvent(new l3({ preferences: this }));
    }
    load() {
        (this.theme = Ze.by_name(this.storage.get('theme', Ze.default.name))),
            (this.alignControlsWithKiCad = this.storage.get('alignControlsWithKiCad', !1));
    }
};
Re.INSTANCE.load();
var l3 = class s extends CustomEvent {
    static {
        l(this, 'PreferencesChangeEvent');
    }
    static {
        this.type = 'kicanvas:preferences:change';
    }
    constructor(t) {
        super(s.type, { detail: t, composed: !0, bubbles: !0 });
    }
};
function Hs(s) {
    return class extends s {
        static {
            l(this, 'WithPreferences');
        }
        constructor(...e) {
            super(...e),
                this.addDisposable(
                    k(Re.INSTANCE, l3.type, () => {
                        this.preferenceChangeCallback(this.preferences);
                    }),
                );
        }
        get preferences() {
            return Re.INSTANCE;
        }
        async preferenceChangeCallback(e) {}
    };
}
l(Hs, 'WithPreferences');
var g2 = Re.INSTANCE,
    c3 = class extends N {
        static {
            l(this, 'KCPreferencesPanel');
        }
        static {
            this.styles = [
                ...N.styles,
                T`
            select {
                box-sizing: border-box;
                display: block;
                width: 100%;
                max-width: 100%;
                margin-top: 0.25em;
                font-family: inherit;
                font-size: inherit;
                font-weight: 300;
                margin-top: 0.25em;
                border-radius: 0.25em;
                text-align: left;
                padding: 0.25em;
                background: var(--input-bg);
                color: var(--input-fg);
                border: var(--input-border);
                transition:
                    color var(--transition-time-medium) ease,
                    box-shadow var(--transition-time-medium) ease,
                    outline var(--transition-time-medium) ease,
                    background var(--transition-time-medium) ease,
                    border var(--transition-time-medium) ease;
            }

            select::after {
                display: block;
                content: "▾";
                color: var(--input-fg);
            }

            select:hover {
                z-index: 10;
                box-shadow: var(--input-hover-shadow);
            }

            select:focus {
                z-index: 10;
                box-shadow: none;
                outline: var(--input-focus-outline);
            }
        `,
            ];
        }
        initialContentCallback() {
            this.renderRoot.addEventListener('input', (e) => {
                let r = e.target;
                r.name === 'theme' && (g2.theme = Ze.by_name(this.theme_control.value)),
                    r.name === 'align-controls-kicad' && (g2.alignControlsWithKiCad = r.checked),
                    g2.save();
            });
        }
        render() {
            let e = Ze.list().map(
                (r) => _`<option
                value="${r.name}"
                selected="${g2.theme.name == r.name}">
                ${r.friendly_name}
            </option>`,
            );
            return _`
            <kc-ui-panel>
                <kc-ui-panel-title title="Preferences"></kc-ui-panel-title>
                <kc-ui-panel-body padded>
                    <kc-ui-control-list>
                        <kc-ui-control>
                            <label>Theme</label>
                            <select name="theme" value="kicad">
                                ${e}
                            </select>
                        </kc-ui-control>
                    </kc-ui-control-list>
                    <kc-ui-control>
                        <label>
                            <input
                                type="checkbox"
                                name="align-controls-kicad"
                                checked="${g2.alignControlsWithKiCad}" />
                            Align controls with KiCad
                        </label>
                    </kc-ui-control>
                </kc-ui-panel-body>
            </kc-ui-panel>
        `;
        }
    };
P([Q('[name=theme]', !0)], c3.prototype, 'theme_control', 2);
window.customElements.define('kc-preferences-panel', c3);
var R3 = class extends N {
    static {
        l(this, 'KCProjectPanelElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            .page {
                display: flex;
                align-items: center;
            }

            .page span.name {
                margin-right: 1em;
                text-overflow: ellipsis;
                white-space: nowrap;
                overflow: hidden;
            }

            .page span.filename {
                flex: 1;
                text-overflow: ellipsis;
                white-space: nowrap;
                overflow: hidden;
                margin-left: 1em;
                text-align: right;
                color: #aaa;
            }

            .page kc-ui-button {
                margin-left: 0.5em;
            }

            .page span.number {
                flex: 0;
                background: var(--dropdown-hover-bg);
                border: 1px solid transparent;
                border-radius: 0.5em;
                font-size: 0.8em;
                padding: 0px 0.3em;
                margin-right: 0.5em;
            }

            kc-ui-menu-item:hover span.number {
                background: var(--dropdown-bg);
            }

            kc-ui-menu-item[selected]:hover span.number {
                background: var(--dropdown-hover-bg);
            }
        `,
        ];
    }
    #e;
    connectedCallback() {
        (async () => ((this.project = await this.requestContext('project')), super.connectedCallback()))();
    }
    initialContentCallback() {
        super.initialContentCallback(),
            this.addDisposable(
                k(this.project, 'load', (e) => {
                    this.update();
                }),
            ),
            this.addDisposable(
                k(this.project, 'change', (e) => {
                    this.selected = this.project.active_page?.project_path ?? null;
                }),
            ),
            this.addEventListener('kc-ui-menu:select', (e) => {
                let r = e.detail;
                (this.selected = r?.name ?? null), this.change_current_project_page(this.selected);
            }),
            he(this.renderRoot, 'kc-ui-button', 'click', (e, r) => {
                let i = r.closest('kc-ui-menu-item');
                this.project.download(i.name);
            });
    }
    get selected() {
        return this.#e.selected?.name ?? null;
    }
    set selected(e) {
        this.#e.selected = e;
    }
    change_current_project_page(e) {
        this.project.set_active_page(e);
    }
    render() {
        let e = [];
        if (!this.project) return _``;
        for (let r of this.project.pages()) {
            let i = r.type == 'schematic' ? 'svg:schematic_file' : 'svg:pcb_file',
                n = r.page ? _`<span class="number">${r.page}</span>` : '';
            e.push(_`<kc-ui-menu-item
                    icon="${i}"
                    name="${r.project_path}">
                    <span class="page">
                        ${n}
                        <span class="name">
                            ${r.name ?? r.filename}
                        </span>
                        <span class="filename">
                            ${r.name && r.name !== r.filename ? r.filename : ''}
                        </span>
                        <kc-ui-button
                            variant="menu"
                            icon="download"
                            title="Download"></kc-ui-button>
                    </span>
                </kc-ui-menu-item>`);
        }
        return (
            (this.#e = _`<kc-ui-menu>
            ${e}
        </kc-ui-menu>`),
            _`<kc-ui-panel>
            <kc-ui-panel-title title="Project"></kc-ui-panel-title>
            <kc-ui-panel-body>${this.#e}</kc-ui-panel-body>
        </kc-ui-panel>`
        );
    }
};
P([at], R3.prototype, 'change_current_project_page', 1);
window.customElements.define('kc-project-panel', R3);
var oi = class extends N {
    static {
        l(this, 'KCViewerBottomToolbarElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            output {
                width: unset;
                margin: unset;
                padding: 0.5em;
                color: var(--button-toolbar-fg);
                background: var(--button-toolbar-bg);
                border: 1px solid var(--button-toolbar-bg);
                border-radius: 0.25em;
                font-weight: 300;
                font-size: 0.9em;
                box-shadow: var(--input-hover-shadow);
                user-select: none;
            }
        `,
        ];
    }
    #e;
    #t;
    #r;
    connectedCallback() {
        (async () => (
            (this.viewer = await this.requestLazyContext('viewer')),
            await this.viewer.loaded,
            super.connectedCallback(),
            this.addDisposable(
                this.viewer.addEventListener(Zt.type, () => {
                    this.update_position();
                }),
            ),
            this.addDisposable(
                this.viewer.addEventListener(D.type, (e) => {
                    this.#r.disabled = !e.detail.item;
                }),
            ),
            this.#t.addEventListener('click', (e) => {
                e.preventDefault(), this.viewer.zoom_to_page();
            }),
            this.#r.addEventListener('click', (e) => {
                e.preventDefault(), this.viewer.zoom_to_selection();
            })
        ))();
    }
    update_position() {
        let e = this.viewer.mouse_position;
        this.#e.value = `${e.x.toFixed(2)}, ${e.y.toFixed(2)} mm`;
    }
    render() {
        return (
            (this.#e = _`<output
            slot="left"
            class="toolbar"></output>`),
            (this.#t = _`<kc-ui-button
            slot="right"
            variant="toolbar"
            name="zoom_to_page"
            title="zoom to page"
            icon="svg:zoom_page">
        </kc-ui-button>`),
            (this.#r = _` <kc-ui-button
            slot="right"
            variant="toolbar"
            name="zoom_to_selection"
            title="zoom to selection"
            icon="svg:zoom_footprint"
            disabled>
        </kc-ui-button>`),
            this.update_position(),
            _`<kc-ui-floating-toolbar location="bottom">
            ${this.#e} ${this.#r}
            ${this.#t}
        </kc-ui-floating-toolbar>`
        );
    }
};
window.customElements.define('kc-viewer-bottom-toolbar', oi);
var Se = class extends N {
    constructor() {
        super();
        this.viewerReady = new Me();
        this.provideLazyContext('viewer', () => this.viewer);
    }
    static {
        l(this, 'KCViewerAppElement');
    }
    #e;
    #t;
    get viewer() {
        return this.#e.viewer;
    }
    connectedCallback() {
        (this.hidden = !0),
            (async () => (
                (this.project = await this.requestContext('project')),
                await this.project.loaded,
                super.connectedCallback()
            ))();
    }
    initialContentCallback() {
        this.project.active_page && this.load(this.project.active_page),
            this.addDisposable(
                k(this.project, 'change', async (e) => {
                    let r = this.project.active_page;
                    r ? await this.load(r) : (this.hidden = !0);
                }),
            ),
            this.addDisposable(
                this.viewer.addEventListener(D.type, (e) => {
                    this.on_viewer_select(e.detail.item, e.detail.previous);
                }),
            ),
            he(this.renderRoot, 'kc-ui-button', 'click', (e) => {
                let r = e.target;
                switch ((console.log('button', r), r.name)) {
                    case 'download':
                        this.project.active_page && this.project.download(this.project.active_page.filename);
                        break;
                    default:
                        console.warn('Unknown button', e);
                }
            });
    }
    async load(e) {
        await this.viewerReady, this.can_load(e) ? (await this.#e.load(e), (this.hidden = !1)) : (this.hidden = !0);
    }
    #r() {
        return Dt(this.project.pages()) > 1;
    }
    make_pre_activities() {
        let e = [];
        return (
            this.#r() &&
                e.push(_`<kc-ui-activity
                    slot="activities"
                    name="Project"
                    icon="folder">
                    <kc-project-panel></kc-project-panel>
                </kc-ui-activity>`),
            e
        );
    }
    make_post_activities() {
        return [
            _`<kc-ui-activity
                slot="activities"
                name="Preferences"
                icon="settings"
                button-location="bottom">
                <kc-preferences-panel></kc-preferences-panel>
            </kc-ui-activity>`,
            _` <kc-ui-activity
                slot="activities"
                name="Help"
                icon="help"
                button-location="bottom">
                <kc-help-panel></kc-help-panel>
            </kc-ui-activity>`,
        ];
    }
    change_activity(e) {
        this.#t?.change_activity(e);
    }
    render() {
        let e = this.controls ?? 'none',
            r = ws(
                this.controlslist ?? '',
                e == 'none' ? { fullscreen: !1, download: !1 } : { fullscreen: !0, download: !0 },
            );
        (this.#e = this.make_viewer_element()), (this.#e.disableinteraction = e == 'none');
        let i = null;
        if (e == 'full') {
            let u = this.make_pre_activities(),
                p = this.make_post_activities(),
                m = this.make_activities();
            (this.#t = _`<kc-ui-activity-side-bar
                collapsed="${this.sidebarcollapsed}">
                ${u} ${m} ${p}
            </kc-ui-activity-side-bar>`),
                (i = _`<kc-ui-resizer></kc-ui-resizer>`);
        } else this.#t = null;
        let n = [];
        r.download &&
            !this.#r() &&
            n.push(_`<kc-ui-button
                    slot="right"
                    name="download"
                    title="download"
                    icon="download"
                    variant="toolbar-alt">
                </kc-ui-button>`);
        let o = _`<kc-ui-floating-toolbar location="top">
            ${n}
        </kc-ui-floating-toolbar>`,
            c = null;
        return (
            e != 'none' && (c = _`<kc-viewer-bottom-toolbar></kc-viewer-bottom-toolbar>`),
            _`<kc-ui-split-view vertical>
            <kc-ui-view class="grow">
                ${o} ${this.#e} ${c}
            </kc-ui-view>
            ${i} ${this.#t}
        </kc-ui-split-view>`
        );
    }
    renderedCallback() {
        window.requestAnimationFrame(() => {
            this.viewerReady.resolve(!0);
        });
    }
};
P([L({ type: String })], Se.prototype, 'controls', 2),
    P([L({ type: String })], Se.prototype, 'controlslist', 2),
    P([L({ type: Boolean })], Se.prototype, 'sidebarcollapsed', 2);
var B = class {
        constructor(t, e, r) {
            this.center = t;
            this.radius = e;
            this.color = r;
        }
        static {
            l(this, 'Circle');
        }
    },
    Ye = class {
        constructor(t, e, r, i, n, o) {
            this.center = t;
            this.radius = e;
            this.start_angle = r;
            this.end_angle = i;
            this.width = n;
            this.color = o;
        }
        static {
            l(this, 'Arc');
        }
    },
    F = class s {
        constructor(t, e, r) {
            this.points = t;
            this.width = e;
            this.color = r;
        }
        static {
            l(this, 'Polyline');
        }
        static from_BBox(t, e, r) {
            return new s([t.top_left, t.top_right, t.bottom_right, t.bottom_left, t.top_left], e, r);
        }
    },
    I = class s {
        constructor(t, e) {
            this.points = t;
            this.color = e;
        }
        static {
            l(this, 'Polygon');
        }
        static from_BBox(t, e) {
            return new s([t.top_left, t.top_right, t.bottom_right, t.bottom_left], e);
        }
    };
var Ke = class {
        constructor(t) {
            this.canvas_size = new d(0, 0);
            this.state = new P2();
            this.#t = h.black.copy();
            (this.canvas = t), (this.background_color = this.#t);
        }
        static {
            l(this, 'Renderer');
        }
        #e;
        #t;
        get background_color() {
            return this.#t;
        }
        set background_color(t) {
            (this.#t = t), (this.canvas.style.backgroundColor = this.background_color.to_css());
        }
        start_bbox() {
            this.#e = new O(0, 0, 0, 0);
        }
        add_bbox(t) {
            this.#e && (this.#e = O.combine([this.#e, t], t.context));
        }
        end_bbox(t) {
            let e = this.#e;
            if (e == null) throw new Error('No current bbox');
            return (e.context = t), (this.#e = null), e;
        }
        prep_circle(t, e, r) {
            let i;
            t instanceof B ? (i = t) : (i = new B(t, e, r ?? this.state.fill)),
                (!i.color || i.color.is_transparent_black) && (i.color = this.state.fill ?? h.transparent_black),
                (i.center = this.state.matrix.transform(i.center));
            let n = new d(i.radius, i.radius);
            return this.add_bbox(O.from_points([i.center.add(n), i.center.sub(n)])), i;
        }
        prep_arc(t, e, r, i, n, o) {
            let c;
            t instanceof Ye
                ? (c = t)
                : (c = new Ye(
                      t,
                      e,
                      r ?? new W(0),
                      i ?? new W(Math.PI * 2),
                      n ?? this.state.stroke_width,
                      o ?? this.state.stroke,
                  )),
                (!c.color || c.color.is_transparent_black) && (c.color = this.state.stroke ?? h.transparent_black);
            let p = new z(c.center, c.radius, c.start_angle, c.end_angle, c.width).to_polyline();
            return this.line(new F(p, c.width, c.color)), c;
        }
        prep_line(t, e, r) {
            let i;
            t instanceof F ? (i = t) : (i = new F(t, e ?? this.state.stroke_width, r ?? this.state.stroke)),
                (!i.color || i.color.is_transparent_black) && (i.color = this.state.stroke ?? h.transparent_black),
                (i.points = Array.from(this.state.matrix.transform_all(i.points)));
            let n = O.from_points(i.points);
            return (n = n.grow(i.width)), this.add_bbox(n), i;
        }
        prep_polygon(t, e) {
            let r;
            return (
                t instanceof I ? (r = t) : (r = new I(t, e ?? this.state.fill)),
                (!r.color || r.color.is_transparent_black) && (r.color = this.state.fill ?? h.transparent_black),
                (r.points = Array.from(this.state.matrix.transform_all(r.points))),
                this.add_bbox(O.from_points(r.points)),
                r
            );
        }
        glyphs(t) {}
    },
    He = class {
        constructor(t, e) {
            this.renderer = t;
            this.name = e;
            this.composite_operation = 'source-over';
        }
        static {
            l(this, 'RenderLayer');
        }
        dispose() {
            this.renderer.remove_layer(this);
        }
    },
    ai = class s {
        constructor(t = U.identity(), e = h.black, r = h.black, i = 0) {
            this.matrix = t;
            this.fill = e;
            this.stroke = r;
            this.stroke_width = i;
        }
        static {
            l(this, 'RenderState');
        }
        copy() {
            return new s(this.matrix.copy(), this.fill?.copy(), this.stroke?.copy(), this.stroke_width);
        }
    },
    P2 = class {
        static {
            l(this, 'RenderStateStack');
        }
        #e;
        constructor() {
            this.#e = [new ai()];
        }
        get top() {
            return this.#e.at(-1);
        }
        get matrix() {
            return this.top.matrix;
        }
        set matrix(t) {
            this.top.matrix = t;
        }
        get stroke() {
            return this.top.stroke;
        }
        set stroke(t) {
            this.top.stroke = t;
        }
        get fill() {
            return this.top.fill;
        }
        set fill(t) {
            this.top.fill = t;
        }
        get stroke_width() {
            return this.top.stroke_width;
        }
        set stroke_width(t) {
            this.top.stroke_width = t;
        }
        multiply(t) {
            this.top.matrix.multiply_self(t);
        }
        push() {
            this.#e.push(this.top.copy());
        }
        pop() {
            this.#e.pop();
        }
    };
function T2(s, t, e) {
    e = e || 2;
    var r = t && t.length,
        i = r ? t[0] * e : s.length,
        n = Es(s, 0, i, e, !0),
        o = [];
    if (!n || n.next === n.prev) return o;
    var c, u, p, m, b, M, f;
    if ((r && (n = Fn(s, t, n, e)), s.length > 80 * e)) {
        (c = p = s[0]), (u = m = s[1]);
        for (var V = e; V < i; V += e)
            (b = s[V]), (M = s[V + 1]), b < c && (c = b), M < u && (u = M), b > p && (p = b), M > m && (m = M);
        (f = Math.max(p - c, m - u)), (f = f !== 0 ? 32767 / f : 0);
    }
    return W2(n, o, e, c, u, f, 0), o;
}
l(T2, 'earcut');
function Es(s, t, e, r, i) {
    var n, o;
    if (i === Ri(s, t, e, r) > 0) for (n = t; n < e; n += r) o = Gs(n, s[n], s[n + 1], o);
    else for (n = e - r; n >= t; n -= r) o = Gs(n, s[n], s[n + 1], o);
    return o && h3(o, o.next) && (S2(o), (o = o.next)), o;
}
l(Es, 'linkedList');
function je(s, t) {
    if (!s) return s;
    t || (t = s);
    var e = s,
        r;
    do
        if (((r = !1), !e.steiner && (h3(e, e.next) || w(e.prev, e, e.next) === 0))) {
            if ((S2(e), (e = t = e.prev), e === e.next)) break;
            r = !0;
        } else e = e.next;
    while (r || e !== t);
    return t;
}
l(je, 'filterPoints');
function W2(s, t, e, r, i, n, o) {
    if (s) {
        !o && n && Yn(s, r, i, n);
        for (var c = s, u, p; s.prev !== s.next; ) {
            if (((u = s.prev), (p = s.next), n ? Xn(s, r, i, n) : yn(s))) {
                t.push((u.i / e) | 0), t.push((s.i / e) | 0), t.push((p.i / e) | 0), S2(s), (s = p.next), (c = p.next);
                continue;
            }
            if (((s = p), s === c)) {
                o
                    ? o === 1
                        ? ((s = On(je(s), t, e)), W2(s, t, e, r, i, n, 2))
                        : o === 2 && Un(s, t, e, r, i, n)
                    : W2(je(s), t, e, r, i, n, 1);
                break;
            }
        }
    }
}
l(W2, 'earcutLinked');
function yn(s) {
    var t = s.prev,
        e = s,
        r = s.next;
    if (w(t, e, r) >= 0) return !1;
    for (
        var i = t.x,
            n = e.x,
            o = r.x,
            c = t.y,
            u = e.y,
            p = r.y,
            m = i < n ? (i < o ? i : o) : n < o ? n : o,
            b = c < u ? (c < p ? c : p) : u < p ? u : p,
            M = i > n ? (i > o ? i : o) : n > o ? n : o,
            f = c > u ? (c > p ? c : p) : u > p ? u : p,
            V = r.next;
        V !== t;

    ) {
        if (V.x >= m && V.x <= M && V.y >= b && V.y <= f && St(i, c, n, u, o, p, V.x, V.y) && w(V.prev, V, V.next) >= 0)
            return !1;
        V = V.next;
    }
    return !0;
}
l(yn, 'isEar');
function Xn(s, t, e, r) {
    var i = s.prev,
        n = s,
        o = s.next;
    if (w(i, n, o) >= 0) return !1;
    for (
        var c = i.x,
            u = n.x,
            p = o.x,
            m = i.y,
            b = n.y,
            M = o.y,
            f = c < u ? (c < p ? c : p) : u < p ? u : p,
            V = m < b ? (m < M ? m : M) : b < M ? b : M,
            S = c > u ? (c > p ? c : p) : u > p ? u : p,
            y = m > b ? (m > M ? m : M) : b > M ? b : M,
            v = li(f, V, t, e, r),
            te = li(S, y, t, e, r),
            X = s.prevZ,
            x = s.nextZ;
        X && X.z >= v && x && x.z <= te;

    ) {
        if (
            (X.x >= f &&
                X.x <= S &&
                X.y >= V &&
                X.y <= y &&
                X !== i &&
                X !== o &&
                St(c, m, u, b, p, M, X.x, X.y) &&
                w(X.prev, X, X.next) >= 0) ||
            ((X = X.prevZ),
            x.x >= f &&
                x.x <= S &&
                x.y >= V &&
                x.y <= y &&
                x !== i &&
                x !== o &&
                St(c, m, u, b, p, M, x.x, x.y) &&
                w(x.prev, x, x.next) >= 0)
        )
            return !1;
        x = x.nextZ;
    }
    for (; X && X.z >= v; ) {
        if (
            X.x >= f &&
            X.x <= S &&
            X.y >= V &&
            X.y <= y &&
            X !== i &&
            X !== o &&
            St(c, m, u, b, p, M, X.x, X.y) &&
            w(X.prev, X, X.next) >= 0
        )
            return !1;
        X = X.prevZ;
    }
    for (; x && x.z <= te; ) {
        if (
            x.x >= f &&
            x.x <= S &&
            x.y >= V &&
            x.y <= y &&
            x !== i &&
            x !== o &&
            St(c, m, u, b, p, M, x.x, x.y) &&
            w(x.prev, x, x.next) >= 0
        )
            return !1;
        x = x.nextZ;
    }
    return !0;
}
l(Xn, 'isEarHashed');
function On(s, t, e) {
    var r = s;
    do {
        var i = r.prev,
            n = r.next.next;
        !h3(i, n) &&
            Js(i, r, r.next, n) &&
            Z2(i, n) &&
            Z2(n, i) &&
            (t.push((i.i / e) | 0), t.push((r.i / e) | 0), t.push((n.i / e) | 0), S2(r), S2(r.next), (r = s = n)),
            (r = r.next);
    } while (r !== s);
    return je(r);
}
l(On, 'cureLocalIntersections');
function Un(s, t, e, r, i, n) {
    var o = s;
    do {
        for (var c = o.next.next; c !== o.prev; ) {
            if (o.i !== c.i && Gn(o, c)) {
                var u = Is(o, c);
                (o = je(o, o.next)), (u = je(u, u.next)), W2(o, t, e, r, i, n, 0), W2(u, t, e, r, i, n, 0);
                return;
            }
            c = c.next;
        }
        o = o.next;
    } while (o !== s);
}
l(Un, 'splitEarcut');
function Fn(s, t, e, r) {
    var i = [],
        n,
        o,
        c,
        u,
        p;
    for (n = 0, o = t.length; n < o; n++)
        (c = t[n] * r),
            (u = n < o - 1 ? t[n + 1] * r : s.length),
            (p = Es(s, c, u, r, !1)),
            p === p.next && (p.steiner = !0),
            i.push(Hn(p));
    for (i.sort(xn), n = 0; n < i.length; n++) e = Qn(i[n], e);
    return e;
}
l(Fn, 'eliminateHoles');
function xn(s, t) {
    return s.x - t.x;
}
l(xn, 'compareX');
function Qn(s, t) {
    var e = vn(s, t);
    if (!e) return t;
    var r = Is(e, s);
    return je(r, r.next), je(e, e.next);
}
l(Qn, 'eliminateHole');
function vn(s, t) {
    var e = t,
        r = s.x,
        i = s.y,
        n = -1 / 0,
        o;
    do {
        if (i <= e.y && i >= e.next.y && e.next.y !== e.y) {
            var c = e.x + ((i - e.y) * (e.next.x - e.x)) / (e.next.y - e.y);
            if (c <= r && c > n && ((n = c), (o = e.x < e.next.x ? e : e.next), c === r)) return o;
        }
        e = e.next;
    } while (e !== t);
    if (!o) return null;
    var u = o,
        p = o.x,
        m = o.y,
        b = 1 / 0,
        M;
    e = o;
    do
        r >= e.x &&
            e.x >= p &&
            r !== e.x &&
            St(i < m ? r : n, i, p, m, i < m ? n : r, i, e.x, e.y) &&
            ((M = Math.abs(i - e.y) / (r - e.x)),
            Z2(e, s) && (M < b || (M === b && (e.x > o.x || (e.x === o.x && wn(o, e))))) && ((o = e), (b = M))),
            (e = e.next);
    while (e !== u);
    return o;
}
l(vn, 'findHoleBridge');
function wn(s, t) {
    return w(s.prev, s, t.prev) < 0 && w(t.next, s, s.next) < 0;
}
l(wn, 'sectorContainsSector');
function Yn(s, t, e, r) {
    var i = s;
    do i.z === 0 && (i.z = li(i.x, i.y, t, e, r)), (i.prevZ = i.prev), (i.nextZ = i.next), (i = i.next);
    while (i !== s);
    (i.prevZ.nextZ = null), (i.prevZ = null), Kn(i);
}
l(Yn, 'indexCurve');
function Kn(s) {
    var t,
        e,
        r,
        i,
        n,
        o,
        c,
        u,
        p = 1;
    do {
        for (e = s, s = null, n = null, o = 0; e; ) {
            for (o++, r = e, c = 0, t = 0; t < p && (c++, (r = r.nextZ), !!r); t++);
            for (u = p; c > 0 || (u > 0 && r); )
                c !== 0 && (u === 0 || !r || e.z <= r.z)
                    ? ((i = e), (e = e.nextZ), c--)
                    : ((i = r), (r = r.nextZ), u--),
                    n ? (n.nextZ = i) : (s = i),
                    (i.prevZ = n),
                    (n = i);
            e = r;
        }
        (n.nextZ = null), (p *= 2);
    } while (o > 1);
    return s;
}
l(Kn, 'sortLinked');
function li(s, t, e, r, i) {
    return (
        (s = ((s - e) * i) | 0),
        (t = ((t - r) * i) | 0),
        (s = (s | (s << 8)) & 16711935),
        (s = (s | (s << 4)) & 252645135),
        (s = (s | (s << 2)) & 858993459),
        (s = (s | (s << 1)) & 1431655765),
        (t = (t | (t << 8)) & 16711935),
        (t = (t | (t << 4)) & 252645135),
        (t = (t | (t << 2)) & 858993459),
        (t = (t | (t << 1)) & 1431655765),
        s | (t << 1)
    );
}
l(li, 'zOrder');
function Hn(s) {
    var t = s,
        e = s;
    do (t.x < e.x || (t.x === e.x && t.y < e.y)) && (e = t), (t = t.next);
    while (t !== s);
    return e;
}
l(Hn, 'getLeftmost');
function St(s, t, e, r, i, n, o, c) {
    return (
        (i - o) * (t - c) >= (s - o) * (n - c) &&
        (s - o) * (r - c) >= (e - o) * (t - c) &&
        (e - o) * (n - c) >= (i - o) * (r - c)
    );
}
l(St, 'pointInTriangle');
function Gn(s, t) {
    return (
        s.next.i !== t.i &&
        s.prev.i !== t.i &&
        !En(s, t) &&
        ((Z2(s, t) && Z2(t, s) && Jn(s, t) && (w(s.prev, s, t.prev) || w(s, t.prev, t))) ||
            (h3(s, t) && w(s.prev, s, s.next) > 0 && w(t.prev, t, t.next) > 0))
    );
}
l(Gn, 'isValidDiagonal');
function w(s, t, e) {
    return (t.y - s.y) * (e.x - t.x) - (t.x - s.x) * (e.y - t.y);
}
l(w, 'area');
function h3(s, t) {
    return s.x === t.x && s.y === t.y;
}
l(h3, 'equals');
function Js(s, t, e, r) {
    var i = p3(w(s, t, e)),
        n = p3(w(s, t, r)),
        o = p3(w(e, r, s)),
        c = p3(w(e, r, t));
    return !!(
        (i !== n && o !== c) ||
        (i === 0 && u3(s, e, t)) ||
        (n === 0 && u3(s, r, t)) ||
        (o === 0 && u3(e, s, r)) ||
        (c === 0 && u3(e, t, r))
    );
}
l(Js, 'intersects');
function u3(s, t, e) {
    return (
        t.x <= Math.max(s.x, e.x) && t.x >= Math.min(s.x, e.x) && t.y <= Math.max(s.y, e.y) && t.y >= Math.min(s.y, e.y)
    );
}
l(u3, 'onSegment');
function p3(s) {
    return s > 0 ? 1 : s < 0 ? -1 : 0;
}
l(p3, 'sign');
function En(s, t) {
    var e = s;
    do {
        if (e.i !== s.i && e.next.i !== s.i && e.i !== t.i && e.next.i !== t.i && Js(e, e.next, s, t)) return !0;
        e = e.next;
    } while (e !== s);
    return !1;
}
l(En, 'intersectsPolygon');
function Z2(s, t) {
    return w(s.prev, s, s.next) < 0
        ? w(s, t, s.next) >= 0 && w(s, s.prev, t) >= 0
        : w(s, t, s.prev) < 0 || w(s, s.next, t) < 0;
}
l(Z2, 'locallyInside');
function Jn(s, t) {
    var e = s,
        r = !1,
        i = (s.x + t.x) / 2,
        n = (s.y + t.y) / 2;
    do
        e.y > n != e.next.y > n &&
            e.next.y !== e.y &&
            i < ((e.next.x - e.x) * (n - e.y)) / (e.next.y - e.y) + e.x &&
            (r = !r),
            (e = e.next);
    while (e !== s);
    return r;
}
l(Jn, 'middleInside');
function Is(s, t) {
    var e = new ci(s.i, s.x, s.y),
        r = new ci(t.i, t.x, t.y),
        i = s.next,
        n = t.prev;
    return (
        (s.next = t),
        (t.prev = s),
        (e.next = i),
        (i.prev = e),
        (r.next = e),
        (e.prev = r),
        (n.next = r),
        (r.prev = n),
        r
    );
}
l(Is, 'splitPolygon');
function Gs(s, t, e, r) {
    var i = new ci(s, t, e);
    return r ? ((i.next = r.next), (i.prev = r), (r.next.prev = i), (r.next = i)) : ((i.prev = i), (i.next = i)), i;
}
l(Gs, 'insertNode');
function S2(s) {
    (s.next.prev = s.prev),
        (s.prev.next = s.next),
        s.prevZ && (s.prevZ.nextZ = s.nextZ),
        s.nextZ && (s.nextZ.prevZ = s.prevZ);
}
l(S2, 'removeNode');
function ci(s, t, e) {
    (this.i = s),
        (this.x = t),
        (this.y = e),
        (this.prev = null),
        (this.next = null),
        (this.z = 0),
        (this.prevZ = null),
        (this.nextZ = null),
        (this.steiner = !1);
}
l(ci, 'Node');
T2.deviation = function (s, t, e, r) {
    var i = t && t.length,
        n = i ? t[0] * e : s.length,
        o = Math.abs(Ri(s, 0, n, e));
    if (i)
        for (var c = 0, u = t.length; c < u; c++) {
            var p = t[c] * e,
                m = c < u - 1 ? t[c + 1] * e : s.length;
            o -= Math.abs(Ri(s, p, m, e));
        }
    var b = 0;
    for (c = 0; c < r.length; c += 3) {
        var M = r[c] * e,
            f = r[c + 1] * e,
            V = r[c + 2] * e;
        b += Math.abs((s[M] - s[V]) * (s[f + 1] - s[M + 1]) - (s[M] - s[f]) * (s[V + 1] - s[M + 1]));
    }
    return o === 0 && b === 0 ? 0 : Math.abs((b - o) / o);
};
function Ri(s, t, e, r) {
    for (var i = 0, n = t, o = e - r; n < e; n += r) (i += (s[o] - s[n]) * (s[n + 1] + s[o + 1])), (o = n);
    return i;
}
l(Ri, 'signedArea');
T2.flatten = function (s) {
    for (var t = s[0][0].length, e = { vertices: [], holes: [], dimensions: t }, r = 0, i = 0; i < s.length; i++) {
        for (var n = 0; n < s[i].length; n++) for (var o = 0; o < t; o++) e.vertices.push(s[i][n][o]);
        i > 0 && ((r += s[i - 1].length), e.holes.push(r));
    }
    return e;
};
var ui = class {
        constructor(t, e, r, i) {
            this.gl = t;
            this.name = e;
            this.location = r;
            this.type = i;
        }
        static {
            l(this, 'Uniform');
        }
        f1(t) {
            this.gl.uniform1f(this.location, t);
        }
        f1v(t, e, r) {
            this.gl.uniform1fv(this.location, t, e, r);
        }
        f2(...t) {
            this.gl.uniform2f(this.location, ...t);
        }
        f2v(...t) {
            this.gl.uniform2fv(this.location, ...t);
        }
        f3(...t) {
            this.gl.uniform3f(this.location, ...t);
        }
        f3v(...t) {
            this.gl.uniform3fv(this.location, ...t);
        }
        f4(...t) {
            this.gl.uniform4f(this.location, ...t);
        }
        f4v(...t) {
            this.gl.uniform4fv(this.location, ...t);
        }
        mat3f(...t) {
            this.gl.uniformMatrix3fv(this.location, ...t);
        }
        mat3fv(...t) {
            this.gl.uniformMatrix3fv(this.location, ...t);
        }
    },
    Tt = class s {
        constructor(t, e, r, i) {
            this.gl = t;
            this.name = e;
            this.vertex = r;
            this.fragment = i;
            this.uniforms = {};
            this.attribs = {};
            G(r) && (r = s.compile(t, t.VERTEX_SHADER, r)),
                (this.vertex = r),
                G(i) && (i = s.compile(t, t.FRAGMENT_SHADER, i)),
                (this.fragment = i),
                (this.program = s.link(t, r, i)),
                this.#t(),
                this.#r();
        }
        static {
            l(this, 'ShaderProgram');
        }
        static #e = new WeakMap();
        static async load(t, e, r, i) {
            let n = s.#e.get(t);
            if ((n || ((n = new Map()), s.#e.set(t, n)), !n.has(e))) {
                r instanceof URL && (r = await (await fetch(r)).text()),
                    i instanceof URL && (i = await (await fetch(i)).text());
                let o = new s(t, e, r, i);
                n.set(e, o);
            }
            return n.get(e);
        }
        static compile(t, e, r) {
            let i = t.createShader(e);
            if (i == null) throw new Error('Could not create new shader');
            if ((t.shaderSource(i, r), t.compileShader(i), t.getShaderParameter(i, t.COMPILE_STATUS))) return i;
            let n = t.getShaderInfoLog(i);
            throw (t.deleteShader(i), new Error(`Error compiling ${e} shader: ${n}`));
        }
        static link(t, e, r) {
            let i = t.createProgram();
            if (i == null) throw new Error('Could not create new shader program');
            if ((t.attachShader(i, e), t.attachShader(i, r), t.linkProgram(i), t.getProgramParameter(i, t.LINK_STATUS)))
                return i;
            let n = t.getProgramInfoLog(i);
            throw (t.deleteProgram(i), new Error(`Error linking shader program: ${n}`));
        }
        #t() {
            this.uniforms = {};
            for (let t = 0; t < this.gl.getProgramParameter(this.program, this.gl.ACTIVE_UNIFORMS); t++) {
                let e = this.gl.getActiveUniform(this.program, t);
                if (e == null)
                    throw new Error(`Could not get uniform info for uniform number ${t} for program ${this.program}`);
                let r = this.gl.getUniformLocation(this.program, e.name);
                if (r == null)
                    throw new Error(
                        `Could not get uniform location for uniform number ${t} for program ${this.program}`,
                    );
                this[e.name] = this.uniforms[e.name] = new ui(this.gl, e.name, r, e.type);
            }
        }
        #r() {
            this.attribs = {};
            for (let t = 0; t < this.gl.getProgramParameter(this.program, this.gl.ACTIVE_ATTRIBUTES); t++) {
                let e = this.gl.getActiveAttrib(this.program, t);
                if (e == null)
                    throw new Error(
                        `Could not get attribute info for attribute number ${t} for program ${this.program}`,
                    );
                (this.attribs[e.name] = e), (this[e.name] = this.gl.getAttribLocation(this.program, e.name));
            }
        }
        bind() {
            this.gl.useProgram(this.program);
        }
    },
    Lt = class {
        constructor(t) {
            this.gl = t;
            this.buffers = [];
            this.gl = t;
            let e = this.gl.createVertexArray();
            if (!e) throw new Error('Could not create new VertexArray');
            (this.vao = e), this.bind();
        }
        static {
            l(this, 'VertexArray');
        }
        dispose(t = !0) {
            if ((this.gl.deleteVertexArray(this.vao ?? null), (this.vao = void 0), t))
                for (let e of this.buffers) e.dispose();
        }
        bind() {
            this.gl.bindVertexArray(this.vao);
        }
        buffer(t, e, r, i = !1, n = 0, o = 0, c) {
            r ??= this.gl.FLOAT;
            let u = new pi(this.gl, c);
            return (
                u.bind(),
                this.gl.vertexAttribPointer(t, e, r, i, n, o),
                this.gl.enableVertexAttribArray(t),
                this.buffers.push(u),
                u
            );
        }
    },
    pi = class {
        constructor(t, e) {
            this.gl = t;
            (this.gl = t), (this.target = e ?? t.ARRAY_BUFFER);
            let r = t.createBuffer();
            if (!r) throw new Error('Unable to create new Buffer');
            this.#e = r;
        }
        static {
            l(this, 'Buffer');
        }
        #e;
        dispose() {
            this.#e && this.gl.deleteBuffer(this.#e), (this.#e = void 0);
        }
        bind() {
            this.gl.bindBuffer(this.target, this.#e);
        }
        set(t, e) {
            this.bind(), (e ??= this.gl.STATIC_DRAW), this.gl.bufferData(this.target, t, e);
        }
        get length() {
            return this.bind(), this.gl.getBufferParameter(this.target, this.gl.BUFFER_SIZE);
        }
    };
var ks = `#version 300 es

precision highp float;

uniform float u_depth;
uniform float u_alpha;

in vec4 v_color;

out vec4 o_color;

void main() {
    vec4 i_color = v_color;
    i_color.a *= u_alpha;
    o_color = i_color;
    gl_FragDepth = u_depth;
}
`;
var As = `#version 300 es

uniform mat3 u_matrix;
in vec2 a_position;
in vec4 a_color;
out vec4 v_color;

void main() {
    v_color = a_color;
    gl_Position = vec4((u_matrix * vec3(a_position, 1)).xy, 0, 1);;
}
`;
var hi = `#version 300 es

precision highp float;

uniform float u_depth;
uniform float u_alpha;

in vec2 v_linespace;
in float v_cap_region;
in vec4 v_color;

out vec4 outColor;

void main() {
    vec4 i_color = v_color;
    i_color.a *= u_alpha;

    float v = abs(v_linespace.x);
    float x = v_linespace.x;
    float y = v_linespace.y;

    if(x < (-1.0 + v_cap_region)) {
        float a = (1.0 + x) / v_cap_region;
        x = mix(-1.0, 0.0, a);
        if(x * x + y * y < 1.0) {
            outColor = i_color;
        } else {
            discard;
        }
    } else if (x > (1.0 - v_cap_region)) {
        float a = (x - (1.0 - v_cap_region)) / v_cap_region;
        x = mix(0.0, 1.0, a);
        if(x * x + y * y < 1.0) {
            outColor = i_color;
        } else {
            discard;
        }
    } else {
        outColor = i_color;
    }

    gl_FragDepth = u_depth;
}
`;
var di = `#version 300 es

uniform mat3 u_matrix;

in vec2 a_position;
in vec4 a_color;
in float a_cap_region;

out vec2 v_linespace;
out float v_cap_region;
out vec4 v_color;

vec2 c_linespace[6] = vec2[](
    // first triangle
    vec2(-1, -1),
    vec2( 1, -1),
    vec2(-1,  1),
    // second triangle
    vec2(-1,  1),
    vec2( 1, -1),
    vec2( 1,  1)
);

void main() {
    int triangle_vertex_num = int(gl_VertexID % 6);

    v_linespace = c_linespace[triangle_vertex_num];
    v_cap_region = a_cap_region;

    gl_Position = vec4((u_matrix * vec3(a_position, 1)).xy, 0, 1);

    v_color = a_color;
}
`;
var ze = class {
        static {
            l(this, 'Tesselator');
        }
        static {
            this.vertices_per_quad = 2 * 3;
        }
        static quad_to_triangles(t) {
            let e = [...t[0], ...t[2], ...t[1], ...t[1], ...t[2], ...t[3]];
            if (e.filter((r) => Number.isNaN(r)).length) throw new Error('Degenerate quad');
            return e;
        }
        static populate_color_data(t, e, r, i) {
            e || (e = new h(1, 0, 0, 1));
            let n = e.to_array();
            for (let o = 0; o < i; o++) t[r + o] = n[o % n.length];
        }
        static tesselate_segment(t, e, r) {
            let o = e
                    .sub(t)
                    .normal.normalize()
                    .multiply(r / 2),
                c = o.normal,
                u = t.add(o).add(c),
                p = t.sub(o).add(c),
                m = e.add(o).sub(c),
                b = e.sub(o).sub(c);
            return [u, p, m, b];
        }
        static tesselate_polyline(t) {
            let e = t.width || 0,
                r = t.points,
                i = t.color,
                o = (r.length - 1) * this.vertices_per_quad,
                c = new Float32Array(o * 2),
                u = new Float32Array(o * 4),
                p = new Float32Array(o),
                m = 0;
            for (let b = 1; b < r.length; b++) {
                let M = r[b - 1],
                    f = r[b],
                    V = f.sub(M).magnitude;
                if (V == 0) continue;
                let S = this.tesselate_segment(M, f, e),
                    y = e / (V + e);
                c.set(this.quad_to_triangles(S), m * 2),
                    p.set(Array(this.vertices_per_quad).fill(y), m),
                    this.populate_color_data(u, i, m * 4, this.vertices_per_quad * 4),
                    (m += this.vertices_per_quad);
            }
            return { position_array: c.slice(0, m * 2), cap_array: p.slice(0, m), color_array: u.slice(0, m * 4) };
        }
        static tesselate_circle(t) {
            let e = new d(t.radius, 0),
                r = e.normal,
                i = t.center.add(e).add(r),
                n = t.center.sub(e).add(r),
                o = t.center.add(e).sub(r),
                c = t.center.sub(e).sub(r);
            return [i, n, o, c];
        }
        static tesselate_circles(t) {
            let e = t.length * this.vertices_per_quad,
                r = new Float32Array(e * 2),
                i = new Float32Array(e),
                n = new Float32Array(e * 4),
                o = 0;
            for (let c = 0; c < t.length; c++) {
                let u = t[c],
                    p = 1,
                    m = this.tesselate_circle(u);
                r.set(this.quad_to_triangles(m), o * 2),
                    i.set(Array(this.vertices_per_quad).fill(p), o),
                    this.populate_color_data(n, u.color, o * 4, this.vertices_per_quad * 4),
                    (o += this.vertices_per_quad);
            }
            return { position_array: r.slice(0, o * 2), cap_array: i.slice(0, o), color_array: n.slice(0, o * 4) };
        }
        static triangulate_polygon(t) {
            if (t.vertices) return t;
            let e = t.points,
                r = new Array(e.length * 2);
            for (let o = 0; o < e.length; o++) {
                let c = e[o];
                (r[o * 2] = c.x), (r[o * 2 + 1] = c.y);
            }
            if (e.length == 3) return (t.points = []), (t.vertices = new Float32Array(r)), t;
            let i = T2(r),
                n = new Float32Array(i.length * 2);
            for (let o = 0; o < i.length; o++) {
                let c = i[o];
                (n[o * 2] = r[c * 2]), (n[o * 2 + 1] = r[c * 2 + 1]);
            }
            return (t.points = []), (t.vertices = n), t;
        }
    },
    d3 = class s {
        constructor(t, e) {
            this.gl = t;
            (this.shader = e ?? s.shader),
                (this.vao = new Lt(t)),
                (this.position_buf = this.vao.buffer(this.shader.a_position, 2)),
                (this.cap_region_buf = this.vao.buffer(this.shader.a_cap_region, 1)),
                (this.color_buf = this.vao.buffer(this.shader.a_color, 4)),
                (this.vertex_count = 0);
        }
        static {
            l(this, 'CircleSet');
        }
        static async load_shader(t) {
            this.shader = await Tt.load(t, 'polyline', di, hi);
        }
        dispose() {
            this.vao.dispose(), this.position_buf.dispose(), this.cap_region_buf.dispose(), this.color_buf.dispose();
        }
        set(t) {
            let { position_array: e, cap_array: r, color_array: i } = ze.tesselate_circles(t);
            this.position_buf.set(e),
                this.cap_region_buf.set(r),
                this.color_buf.set(i),
                (this.vertex_count = e.length / 2);
        }
        render() {
            this.vertex_count && (this.vao.bind(), this.gl.drawArrays(this.gl.TRIANGLES, 0, this.vertex_count));
        }
    },
    m3 = class s {
        constructor(t, e) {
            this.gl = t;
            (this.shader = e ?? s.shader),
                (this.vao = new Lt(t)),
                (this.position_buf = this.vao.buffer(this.shader.a_position, 2)),
                (this.cap_region_buf = this.vao.buffer(this.shader.a_cap_region, 1)),
                (this.color_buf = this.vao.buffer(this.shader.a_color, 4)),
                (this.vertex_count = 0);
        }
        static {
            l(this, 'PolylineSet');
        }
        static async load_shader(t) {
            this.shader = await Tt.load(t, 'polyline', di, hi);
        }
        dispose() {
            this.vao.dispose(), this.position_buf.dispose(), this.cap_region_buf.dispose(), this.color_buf.dispose();
        }
        set(t) {
            if (!t.length) return;
            let e = t.reduce((p, m) => p + (m.points.length - 1) * ze.vertices_per_quad, 0),
                r = new Float32Array(e * 2),
                i = new Float32Array(e),
                n = new Float32Array(e * 4),
                o = 0,
                c = 0,
                u = 0;
            for (let p of t) {
                let { position_array: m, cap_array: b, color_array: M } = ze.tesselate_polyline(p);
                r.set(m, o), (o += m.length), i.set(b, c), (c += b.length), n.set(M, u), (u += M.length);
            }
            this.position_buf.set(r), this.cap_region_buf.set(i), this.color_buf.set(n), (this.vertex_count = o / 2);
        }
        render() {
            this.vertex_count && (this.vao.bind(), this.gl.drawArrays(this.gl.TRIANGLES, 0, this.vertex_count));
        }
    },
    b3 = class s {
        constructor(t, e) {
            this.gl = t;
            (this.shader = e ?? s.shader),
                (this.vao = new Lt(t)),
                (this.position_buf = this.vao.buffer(this.shader.a_position, 2)),
                (this.color_buf = this.vao.buffer(this.shader.a_color, 4)),
                (this.vertex_count = 0);
        }
        static {
            l(this, 'PolygonSet');
        }
        static async load_shader(t) {
            this.shader = await Tt.load(t, 'polygon', As, ks);
        }
        dispose() {
            this.vao.dispose(), this.position_buf.dispose(), this.color_buf.dispose();
        }
        static polyline_from_triangles(t, e, r) {
            let i = [];
            for (let n = 0; n < t.length; n += 6) {
                let o = new d(t[n], t[n + 1]),
                    c = new d(t[n + 2], t[n + 3]),
                    u = new d(t[n + 4], t[n + 5]);
                i.push(new F([o, c, u, o], e, r));
            }
            return i;
        }
        set(t) {
            let e = 0;
            for (let u of t) ze.triangulate_polygon(u), (e += u.vertices?.length ?? 0);
            let r = e / 2,
                i = new Float32Array(e),
                n = new Float32Array(r * 4),
                o = 0,
                c = 0;
            for (let u of t) {
                if (u.vertices == null) continue;
                let p = u.vertices.length / 2;
                i.set(u.vertices, o),
                    (o += u.vertices.length),
                    ze.populate_color_data(n, u.color, c, p * 4),
                    (c += p * 4);
            }
            this.position_buf.set(i), this.color_buf.set(n), (this.vertex_count = o / 2);
        }
        render() {
            this.vertex_count && (this.vao.bind(), this.gl.drawArrays(this.gl.TRIANGLES, 0, this.vertex_count));
        }
    },
    L2 = class {
        constructor(t) {
            this.gl = t;
            this.gl = t;
        }
        static {
            l(this, 'PrimitiveSet');
        }
        #e = [];
        #t = [];
        #r = [];
        #i;
        #s;
        #n;
        static async load_shaders(t) {
            await Promise.all([b3.load_shader(t), m3.load_shader(t), d3.load_shader(t)]);
        }
        dispose() {
            this.#i?.dispose(), this.#s?.dispose(), this.#n?.dispose();
        }
        clear() {
            this.#i?.dispose(),
                this.#s?.dispose(),
                this.#n?.dispose(),
                (this.#i = void 0),
                (this.#s = void 0),
                (this.#n = void 0),
                (this.#e = []),
                (this.#t = []),
                (this.#r = []);
        }
        add_circle(t) {
            this.#t.push(t);
        }
        add_polygon(t) {
            this.#e.push(t);
        }
        add_line(t) {
            this.#r.push(t);
        }
        commit() {
            this.#e.length && ((this.#i = new b3(this.gl)), this.#i.set(this.#e), (this.#e = void 0)),
                this.#r.length && ((this.#n = new m3(this.gl)), this.#n.set(this.#r), (this.#r = void 0)),
                this.#t.length && ((this.#s = new d3(this.gl)), this.#s.set(this.#t), (this.#t = void 0));
        }
        render(t, e = 0, r = 1) {
            this.#i &&
                (this.#i.shader.bind(),
                this.#i.shader.u_matrix.mat3f(!1, t.elements),
                this.#i.shader.u_depth.f1(e),
                this.#i.shader.u_alpha.f1(r),
                this.#i.render()),
                this.#s &&
                    (this.#s.shader.bind(),
                    this.#s.shader.u_matrix.mat3f(!1, t.elements),
                    this.#s.shader.u_depth.f1(e),
                    this.#s.shader.u_alpha.f1(r),
                    this.#s.render()),
                this.#n &&
                    (this.#n.shader.bind(),
                    this.#n.shader.u_matrix.mat3f(!1, t.elements),
                    this.#n.shader.u_depth.f1(e),
                    this.#n.shader.u_alpha.f1(r),
                    this.#n.render());
        }
    };
var _3 = class extends Ke {
        constructor(e) {
            super(e);
            this.#e = [];
            this.projection_matrix = U.identity();
        }
        static {
            l(this, 'WebGL2Renderer');
        }
        #e;
        #t;
        async setup() {
            let e = this.canvas.getContext('webgl2', { alpha: !1 });
            if (e == null) throw new Error('Unable to create WebGL2 context');
            (this.gl = e),
                e.enable(e.BLEND),
                e.blendEquation(e.FUNC_ADD),
                e.blendFunc(e.SRC_ALPHA, e.ONE_MINUS_SRC_ALPHA),
                e.enable(e.DEPTH_TEST),
                e.depthFunc(e.GREATER),
                e.clearColor(...this.background_color.to_array()),
                e.clearDepth(0),
                e.clear(e.COLOR_BUFFER_BIT | e.DEPTH_BUFFER_BIT),
                this.update_canvas_size(),
                await L2.load_shaders(e);
        }
        dispose() {
            for (let e of this.layers) e.dispose();
            this.gl = void 0;
        }
        update_canvas_size() {
            if (!this.gl) return;
            let e = window.devicePixelRatio,
                r = this.canvas.getBoundingClientRect(),
                i = r.width,
                n = r.height,
                o = Math.round(r.width * e),
                c = Math.round(r.height * e);
            (this.canvas_size.x == o && this.canvas_size.y == c) ||
                ((this.canvas.width = o),
                (this.canvas.height = c),
                this.gl.viewport(0, 0, o, c),
                (this.projection_matrix = U.orthographic(i, n)));
        }
        clear_canvas() {
            if (this.gl == null) throw new Error('Uninitialized');
            this.update_canvas_size(), this.gl.clear(this.gl.COLOR_BUFFER_BIT | this.gl.DEPTH_BUFFER_BIT);
        }
        start_layer(e, r = 0) {
            if (this.gl == null) throw new Error('Uninitialized');
            this.#t = new mi(this, e, new L2(this.gl));
        }
        end_layer() {
            if (this.#t == null) throw new Error('No active layer');
            return this.#t.geometry.commit(), this.#e.push(this.#t), (this.#t = null), this.#e.at(-1);
        }
        arc(e, r, i, n, o, c) {
            super.prep_arc(e, r, i, n, o, c);
        }
        circle(e, r, i) {
            let n = super.prep_circle(e, r, i);
            n.color && this.#t.geometry.add_circle(n);
        }
        line(e, r, i) {
            let n = super.prep_line(e, r, i);
            n.color && this.#t.geometry.add_line(n);
        }
        polygon(e, r) {
            let i = super.prep_polygon(e, r);
            i.color && this.#t.geometry.add_polygon(i);
        }
        get layers() {
            let e = this.#e;
            return {
                *[Symbol.iterator]() {
                    for (let r of e) yield r;
                },
            };
        }
        remove_layer(e) {
            let r = this.#e.indexOf(e);
            r != -1 && this.#e.splice(r, 1);
        }
    },
    mi = class extends He {
        constructor(e, r, i) {
            super(e, r);
            this.renderer = e;
            this.name = r;
            this.geometry = i;
        }
        static {
            l(this, 'WebGL2RenderLayer');
        }
        dispose() {
            this.clear();
        }
        clear() {
            this.geometry?.dispose();
        }
        render(e, r, i = 1) {
            let n = this.renderer.gl,
                o = this.renderer.projection_matrix.multiply(e);
            this.composite_operation != 'source-over' && n.blendFunc(n.ONE_MINUS_DST_COLOR, n.ONE_MINUS_SRC_ALPHA),
                this.geometry.render(o, r, i),
                this.composite_operation != 'source-over' && n.blendFunc(n.SRC_ALPHA, n.ONE_MINUS_SRC_ALPHA);
        }
    };
var bi = class {
        static {
            l(this, 'Glyph');
        }
    },
    y2 = class s extends bi {
        constructor(e, r) {
            super();
            this.strokes = e;
            this.bbox = r;
        }
        static {
            l(this, 'StrokeGlyph');
        }
        transform(e, r, i, n, o, c) {
            let u = this.bbox.copy();
            (u.x = r.x + u.x * e.x),
                (u.y = r.y + u.y * e.y),
                (u.w = u.w * e.x),
                (u.h = u.h * e.y),
                i && (u.w += u.h * i);
            let p = [];
            for (let m of this.strokes) {
                let b = [];
                for (let M of m) {
                    let f = M.multiply(e);
                    i > 0 && (f.x -= f.y * i),
                        (f = f.add(r)),
                        o && (f.x = c.x - (f.x - c.x)),
                        n.degrees != 0 && (f = n.rotate_point(f, c)),
                        b.push(f);
                }
                p.push(b);
            }
            return new s(p, u);
        }
    };
var X2 = class {
        constructor(t) {
            this.text = t;
            (this.root = Cs(Dn(t))), (this.root.is_root = !0);
        }
        static {
            l(this, 'Markup');
        }
    },
    M3 = class {
        constructor() {
            this.is_root = !1;
            this.subscript = !1;
            this.superscript = !1;
            this.overbar = !1;
            this.text = '';
            this.children = [];
        }
        static {
            l(this, 'MarkupNode');
        }
    };
function* Dn(s) {
    let t = '',
        e = 0,
        r = null,
        i = 0;
    for (let n = 0; n < s.length + 1; n++) {
        let o = n < s.length ? s[n] : t;
        switch (o) {
            case '_':
            case '^':
            case '~':
                r = o;
                break;
            case '{':
                r && (i++, yield { text: s.slice(e, n - 1) }, yield { open: i, control: r }, (r = null), (e = n + 1));
                break;
            case '}':
                i && (yield { text: s.slice(e, n) }, yield { close: i }, (e = n + 1), i--);
                break;
            case t:
                yield { text: s.slice(e, n) };
                break;
            default:
                r = null;
                break;
        }
    }
}
l(Dn, 'tokenize');
function Cs(s) {
    let t,
        e = new M3();
    for (; (t = s.next().value); ) {
        if (t.text) {
            let r = new M3();
            (r.text = t.text), e.children.push(r);
            continue;
        }
        if (t.open) {
            let r = Cs(s);
            switch (t.control) {
                case '^':
                    r.superscript = !0;
                    break;
                case '_':
                    r.subscript = !0;
                    break;
                case '~':
                    r.overbar = !0;
                    break;
            }
            e.children.push(r);
            continue;
        }
        if (t.close) return e;
    }
    return e;
}
l(Cs, 'parse');
var yt = class {
        constructor(t) {
            this.name = t;
        }
        static {
            l(this, 'Font');
        }
        static {
            this.italic_tilt = 1 / 8;
        }
        static {
            this.interline_pitch_ratio = 1.62;
        }
        draw(t, e, r, i) {
            if (!t || !e) return;
            let n = this.get_line_positions(e, r, i);
            t.state.stroke_width = i.stroke_width;
            for (let o of n) this.draw_line(t, o.text, o.position, r, i);
        }
        get_line_extents(t, e, r, i, n) {
            let o = new Ge();
            (o.bold = i), (o.italic = n);
            let { bbox: c } = this.get_markup_as_glyphs(t, new d(0, 0), e, new W(0), !1, new d(0, 0), o);
            return new d(c.w, c.h);
        }
        break_lines(t, e, r, i, n, o) {
            let c = new Ge();
            (c.bold = n), (c.italic = o);
            let u = this.get_text_as_glyphs(' ', r, new d(0, 0), new W(0), !1, new d(0, 0), c).cursor.x,
                p = t.split(`
`),
                m = '';
            for (let b = 0; b < p.length; b++) {
                let M = p[b],
                    f = !0,
                    V = 0,
                    S = this.wordbreak_markup(M, r, c);
                for (let { word: y, width: v } of S)
                    f
                        ? ((m += y), (V += v), (f = !1))
                        : V + u + v < e - i
                          ? ((m += ' ' + y), (V += u + v))
                          : ((m += `
`),
                            (V = 0),
                            (f = !0));
                b != p.length - 1 &&
                    (m += `
`);
            }
            return m;
        }
        draw_line(t, e, r, i, n) {
            if (!t) return new O(0, 0, 0, 0);
            let o = new Ge();
            (o.italic = n.italic), (o.underline = n.underlined);
            let { glyphs: c, bbox: u } = this.get_markup_as_glyphs(e, r, n.size, n.angle, n.mirrored, i, o),
                p = U.scaling(1e-4, 1e-4);
            for (let m of c)
                for (let b of m.strokes) {
                    let M = Array.from(p.transform_all(b));
                    t.line(new F(M, n.stroke_width / 1e4, n.color));
                }
            return u;
        }
        get_line_bbox(t, e, r, i) {
            let n = new Ge();
            n.italic = i;
            let { bbox: o, next_position: c } = this.get_markup_as_glyphs(t, e, r, new W(0), !1, new d(0, 0), n);
            return { bbox: o, cursor: c };
        }
        get_line_positions(t, e, r) {
            let i = [],
                n = [],
                o = t.split(`
`),
                c = o.length,
                u = this.get_interline(r.size.y, r.line_spacing),
                p = 0;
            for (let M = 0; M < c; M++) {
                let f = o[M],
                    V = new d(e.x, e.y + M * u),
                    { cursor: S } = this.get_line_bbox(f, V, r.size, r.italic),
                    y = S.sub(V);
                i.push(y), M == 0 ? (p += r.size.y * 1.17) : (p += u);
            }
            let m = new d(0, r.size.y);
            switch (r.v_align) {
                case 'top':
                    break;
                case 'center':
                    m.y -= p / 2;
                    break;
                case 'bottom':
                    m.y -= p;
                    break;
            }
            for (let M = 0; M < c; M++) {
                let f = i[M],
                    V = m.copy();
                switch (((V.y += M * u), r.h_align)) {
                    case 'left':
                        break;
                    case 'center':
                        V.x = -f.x / 2;
                        break;
                    case 'right':
                        V.x = -f.x;
                        break;
                }
                n.push(e.add(V));
            }
            let b = [];
            for (let M = 0; M < c; M++) b.push({ text: o[M], position: n[M], extents: i[M] });
            return b;
        }
        get_markup_as_glyphs(t, e, r, i, n, o, c) {
            let u = new X2(t);
            return this.get_markup_node_as_glyphs(u.root, e, r, i, n, o, c);
        }
        get_markup_node_as_glyphs(t, e, r, i, n, o, c) {
            let u = [],
                p = [],
                m = e.copy(),
                b = c.copy();
            if (
                !t.is_root &&
                (t.subscript && ((b = new Ge()), (b.subscript = !0)),
                t.superscript && ((b = new Ge()), (b.superscript = !0)),
                (b.overbar ||= t.overbar),
                t.text)
            ) {
                let { glyphs: M, cursor: f, bbox: V } = this.get_text_as_glyphs(t.text, r, e, i, n, o, b);
                (u = M), p.push(V), m.set(f);
            }
            for (let M of t.children) {
                let { next_position: f, bbox: V, glyphs: S } = this.get_markup_node_as_glyphs(M, m, r, i, n, o, b);
                m.set(f), p.push(V), (u = u.concat(S));
            }
            return { next_position: m, bbox: O.combine(p), glyphs: u };
        }
        wordbreak_markup(t, e, r) {
            let i = new X2(t);
            return this.wordbreak_markup_node(i.root, e, r);
        }
        wordbreak_markup_node(t, e, r) {
            let i = r.copy(),
                n = [];
            if (!t.is_root) {
                let o = '';
                if (
                    (t.subscript && ((o = '_'), (i.subscript = !0)),
                    t.superscript && ((o = '^'), (i.superscript = !0)),
                    t.overbar && ((o = '~'), (i.overbar = !0)),
                    o)
                ) {
                    let c = `${o}{`,
                        u = 0;
                    if (t.text) {
                        let { cursor: p } = this.get_text_as_glyphs(
                            t.text,
                            e,
                            new d(0, 0),
                            new W(0),
                            !1,
                            new d(0, 0),
                            i,
                        );
                        (c += t.text), (u += p.x);
                    }
                    for (let p of t.children) {
                        let m = this.wordbreak_markup_node(p, e, i);
                        for (let { word: b, width: M } of m) (c += b), (u += M);
                    }
                    return (c += '}'), [{ word: c, width: u }];
                } else {
                    let c = t.text.trim().split(' ');
                    t.text.endsWith(' ') && c.push(' ');
                    for (let u of c) {
                        let { cursor: p } = this.get_text_as_glyphs(u, e, new d(0, 0), new W(0), !1, new d(0, 0), i);
                        n.push({ word: u, width: p.x });
                    }
                }
            }
            for (let o of t.children) n = n.concat(this.wordbreak_markup_node(o, e, r));
            return n;
        }
    },
    Ge = class s {
        constructor(t = !1, e = !1, r = !1, i = !1, n = !1, o = !1) {
            this.bold = t;
            this.italic = e;
            this.subscript = r;
            this.superscript = i;
            this.overbar = n;
            this.underline = o;
        }
        static {
            l(this, 'TextStyle');
        }
        copy() {
            return new s(this.bold, this.italic, this.subscript, this.superscript, this.overbar, this.underline);
        }
    },
    f3 = class s {
        constructor() {
            this.font = null;
            this.h_align = 'center';
            this.v_align = 'center';
            this.angle = new W(0);
            this.line_spacing = 1;
            this.stroke_width = 0;
            this.italic = !1;
            this.bold = !1;
            this.underlined = !1;
            this.color = h.transparent_black;
            this.visible = !0;
            this.mirrored = !1;
            this.multiline = !0;
            this.size = new d(0, 0);
            this.keep_upright = !1;
        }
        static {
            l(this, 'TextAttributes');
        }
        copy() {
            let t = new s();
            return (
                (t.font = this.font),
                (t.h_align = this.h_align),
                (t.v_align = this.v_align),
                (t.angle = this.angle.copy()),
                (t.line_spacing = this.line_spacing),
                (t.stroke_width = this.stroke_width),
                (t.italic = this.italic),
                (t.bold = this.bold),
                (t.underlined = this.underlined),
                (t.color = this.color.copy()),
                (t.visible = this.visible),
                (t.mirrored = this.mirrored),
                (t.multiline = this.multiline),
                (t.size = this.size.copy()),
                t
            );
        }
    };
var Ds = [
        'E_JSZS',
        'G][EI`',
        'H\\KFXFQNTNVOWPXRXWWYVZT[N[LZKY',
        'I[MUWU RK[RFY[',
        'G\\SPVQWRXTXWWYVZT[L[LFSFUGVHWJWLVNUOSPLP',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH',
        'H[MPTP RW[M[MFWF',
        'G]L[LF RLPXP RX[XF',
        'MWR[RF',
        'G\\L[LF RX[OO RXFLR',
        'F^K[KFRUYFY[',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF',
        'G\\L[LFTFVGWHXJXMWOVPTQLQ',
        'JZLFXF RR[RF',
        'H\\KFY[ RYFK[',
        'I[RQR[ RKFRQYF',
        'NVPESH',
        'HZVZT[P[NZMYLWLQMONNPMTMVN',
        'MWRMR_QaObNb RRFQGRHSGRFRH',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[',
        'JZMMR[WM',
        'G]JMN[RQV[ZM',
        'H\\RbRD',
        'F^K[KFYFY[K[',
        'RR',
        'NVTEQH',
        'JZRRQSRTSSRRRT',
        'MWR[RF RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RIPQP',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RTEQH',
        'I[MUWU RK[RFY[ RN>O@QASAU@V>',
        'IZNMN[ RPSV[ RVMNU',
        'G]KPYP RPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF',
        'I[NNPMTMVNWPWXVZT[P[NZMXMVWT',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[',
        'IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN',
        'MXRMRXSZU[',
        'H[LTWT RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[',
        'G]RFRb RPMTMVNXPYRYVXXVZT[P[NZLXKVKRLPNNPM',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEQH',
        'IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RTEQH',
        'I\\NMN[ RNOONQMTMVNWPWb RTEQH',
        'MXRMRXSZU[ RTEQH',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM',
        'H[MMMXNZP[S[UZVYWWWPVNUM RTEQH',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEQH',
        'LXOTUT',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RPQRPTQUSTURVPUOSPQ',
        'Pf',
    ],
    N3 = [
        'JZ',
        'MWRYSZR[QZRYR[ RRSQGRFSGRSRF',
        'JZNFNJ RVFVJ',
        'H]LM[M RRDL_ RYVJV RS_YD',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RRCR^',
        'F^J[ZF RMFOGPIOKMLKKJIKGMF RYZZXYVWUUVTXUZW[YZ',
        'E_[[Z[XZUWPQNNMKMINGPFQFSGTITJSLRMLQKRJTJWKYLZN[Q[SZTYWUXRXP',
        'MWSFQJ',
        'KYVcUbS_R]QZPUPQQLRISGUDVC',
        'KYNcObQ_R]SZTUTQSLRIQGODNC',
        'JZRFRK RMIRKWI ROORKUO',
        'E_JSZS RR[RK',
        'MWSZS[R]Q^',
        0,
        'MWRYSZR[QZRYR[',
        1,
        'H\\QFSFUGVHWJXNXSWWVYUZS[Q[OZNYMWLSLNMJNHOGQF',
        'H\\X[L[ RR[RFPINKLL',
        'H\\LHMGOFTFVGWHXJXLWOK[X[',
        2,
        'H\\VMV[ RQELTYT',
        'H\\WFMFLPMOONTNVOWPXRXWWYVZT[O[MZLY',
        'H\\VFRFPGOHMKLOLWMYNZP[T[VZWYXWXRWPVOTNPNNOMPLR',
        'H\\KFYFP[',
        'H\\PONNMMLKLJMHNGPFTFVGWHXJXKWMVNTOPONPMQLSLWMYNZP[T[VZWYXWXSWQVPTO',
        'H\\N[R[TZUYWVXRXJWHVGTFPFNGMHLJLOMQNRPSTSVRWQXO',
        'MWRYSZR[QZRYR[ RRNSORPQORNRP',
        'MWSZS[R]Q^ RRNSORPQORNRP',
        'E_ZMJSZY',
        'E_JPZP RZVJV',
        'E_JMZSJY',
        'I[QYRZQ[PZQYQ[ RMGOFTFVGWIWKVMUNSORPQRQS',
        'D_VQUPSOQOOPNQMSMUNWOXQYSYUXVW RVOVWWXXXZW[U[PYMVKRJNKKMIPHTIXK[N]R^V]Y[',
        3,
        4,
        5,
        'G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[',
        6,
        'HZTPMP RM[MFWF',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR',
        7,
        8,
        'JZUFUUTXRZO[M[',
        9,
        'HYW[M[MF',
        10,
        'G]L[LFX[XF',
        11,
        12,
        'G]Z]X\\VZSWQVOV RP[NZLXKTKMLINGPFTFVGXIYMYTXXVZT[P[',
        'G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG',
        13,
        'G]LFLWMYNZP[T[VZWYXWXF',
        'I[KFR[YF',
        'F^IFN[RLV[[F',
        14,
        15,
        'H\\KFYFK[Y[',
        'KYVbQbQDVD',
        'KYID[_',
        'KYNbSbSDND',
        'LXNHREVH',
        'JZJ]Z]',
        16,
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR',
        'H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ',
        17,
        'I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT',
        'MYOMWM RR[RISGUFWF',
        'I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN',
        'H[M[MF RV[VPUNSMPMNNMO',
        'MWR[RM RRFQGRHSGRFRH',
        18,
        'IZN[NF RPSV[ RVMNU',
        'MXU[SZRXRF',
        'D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[',
        'I\\NMN[ RNOONQMTMVNWPW[',
        19,
        'H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ',
        'I\\WMWb RWZU[Q[OZNYMWMQNOONQMUMWN',
        'KXP[PM RPQQORNTMVM',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN',
        'MYOMWM RRFRXSZU[W[',
        'H[VMV[ RMMMXNZP[S[UZVY',
        20,
        21,
        'IZL[WM RLMW[',
        'JZMMR[ RWMR[P`OaMb',
        'IZLMWML[W[',
        'KYVcUcSbR`RVQTOSQRRPRFSDUCVC',
        22,
        'KYNcOcQbR`RVSTUSSRRPRFQDOCNC',
        'KZMSNRPQTSVRWQ',
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        'JZ',
        'MWROQNRMSNRORM RRUSaRbQaRURb',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RRJR^',
        'H[LMTM RL[W[ RO[OIPGRFUFWG',
        'H]LYOV RLLOO RVVYY RVOYL RVVTWQWOVNTNQOOQNTNVOWQWTVV',
        'F^JTZT RJMZM RRQR[ RKFRQYF',
        'MWRbRW RRFRQ',
        'I[N]P^S^U]V[UYOSNQNPONQM RVGTFQFOGNIOKUQVSVTUVSW',
        'LXNFOGNHMGNFNH RVFWGVHUGVFVH',
        '@dVKTJPJNKLMKOKSLUNWPXTXVW RRCMDHGELDQEVH[M^R_W^\\[_V`Q_L\\GWDRC',
        'KZOEQDSDUEVGVN RVMTNQNOMNKOIQHVH',
        'H\\RMLSRY RXWTSXO',
        'E_JQZQZV',
        24,
        '@dWXRR RNXNJTJVKWMWOVQTRNR RRCMDHGELDQEVH[M^R_W^\\[_V`Q_L\\GWDRC',
        'LXMGWG',
        'JZRFPGOIPKRLTKUITGRF',
        'E_JOZO RRWRG RZ[J[',
        'JZNAP@S@UAVCVEUGNNVN',
        'JZN@V@RESEUFVHVKUMSNPNNM',
        25,
        'H^MMMb RWXXZZ[ RMXNZP[T[VZWXWM',
        'F]VMV[ ROMOXNZL[ RZMMMKNJP',
        26,
        'MWR\\T]U_TaRbOb',
        'JZVNNN RNCPBR@RN',
        'KYQNOMNKNGOEQDSDUEVGVKUMSNQN',
        'H\\RMXSRY RLWPSLO',
        'G]KQYQ RVNNN RNCPBR@RN RUYUa RQSN]W]',
        'G]KQYQ RVNNN RNCPBR@RN RNTPSSSUTVVVXUZNaVa',
        'G]KQYQ RN@V@RESEUFVHVKUMSNPNNM RUYUa RQSN]W]',
        'I[SORNSMTNSOSM RWaUbPbNaM_M]N[OZQYRXSVSU',
        'I[MUWU RK[RFY[ RP>SA',
        'I[MUWU RK[RFY[ RT>QA',
        'I[MUWU RK[RFY[ RNAR>VA',
        'I[MUWU RK[RFY[ RMAN@P?TAV@W?',
        'I[MUWU RK[RFY[ RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'I[MUWU RK[RFY[ RRFPEOCPAR@TAUCTERF',
        'F`JURU RRPYP RH[OF\\F RRFR[\\[',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RR\\T]U_TaRbOb',
        'H[MPTP RW[M[MFWF RP>SA',
        'H[MPTP RW[M[MFWF RT>QA',
        'H[MPTP RW[M[MFWF RNAR>VA',
        'H[MPTP RW[M[MFWF RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'MWR[RF RP>SA',
        'MWR[RF RT>QA',
        'MWR[RF RNAR>VA',
        27,
        28,
        'G]L[LFX[XF RMAN@P?TAV@W?',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RP>SA',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RT>QA',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RNAR>VA',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RMAN@P?TAV@W?',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'E_LMXY RXMLY',
        'G]ZFJ[ RP[NZLXKTKMLINGPFTFVGXIYMYTXXVZT[P[',
        'G]LFLWMYNZP[T[VZWYXWXF RP>SA',
        'G]LFLWMYNZP[T[VZWYXWXF RT>QA',
        'G]LFLWMYNZP[T[VZWYXWXF RNAR>VA',
        'G]LFLWMYNZP[T[VZWYXWXF RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'I[RQR[ RKFRQYF RT>QA',
        'G\\LFL[ RLKTKVLWMXOXRWTVUTVLV',
        'F]K[KJLHMGOFRFTGUHVJVMSMQNPPPQQSSTVTXUYWYXXZV[R[PZ',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RPESH',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RTEQH',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNHREVH',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RMHNGPFTHVGWF',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RRHPGOEPCRBTCUETGRH',
        'D`INKMOMQNRP R[ZY[U[SZRXRPSNUMYM[N\\P\\RRSKSITHVHXIZK[O[QZRX',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RR\\T]U_TaRbOb',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RPESH',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RTEQH',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNHREVH',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'MWR[RM RPESH',
        'MWR[RM RTEQH',
        'LXNHREVH RR[RM',
        'LXNFOGNHMGNFNH RVFWGVHUGVFVH RR[RM',
        'I\\SCQI RWNUMQMONNOMQMXNZP[T[VZWXWLVITGRFNE',
        'I\\NMN[ RNOONQMTMVNWPW[ RMHNGPFTHVGWF',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RPESH',
        29,
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNHREVH',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMHNGPFTHVGWF',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'E_ZSJS RRXSYRZQYRXRZ RRLSMRNQMRLRN',
        'H[XMK[ RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[',
        'H[VMV[ RMMMXNZP[S[UZVY RPESH',
        'H[VMV[ RMMMXNZP[S[UZVY RTEQH',
        'H[VMV[ RMMMXNZP[S[UZVY RNHREVH',
        'H[VMV[ RMMMXNZP[S[UZVY RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'JZMMR[ RWMR[P`OaMb RTEQH',
        'H[MFMb RMNOMSMUNVOWQWWVYUZS[O[MZ',
        'JZMMR[ RWMR[P`OaMb RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'I[MUWU RK[RFY[ RM@W@',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RMGWG',
        30,
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE',
        'I[MUWU RK[RFY[ RY[W]V_WaYb[b',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RW[U]T_UaWbYb',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RT>QA',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RTEQH',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RNAR>VA',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RNHREVH',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RR?Q@RAS@R?RA',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RRFQGRHSGRFRH',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RN>RAV>',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RNERHVE',
        'G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RN>RAV>',
        'IfW[WF RWZU[Q[OZNYMWMQNOONQMUMWN RbF`J',
        28,
        'I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RRHZH',
        'H[MPTP RW[M[MFWF RM@W@',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RMGWG',
        'H[MPTP RW[M[MFWF RN>O@QASAU@V>',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNEOGQHSHUGVE',
        'H[MPTP RW[M[MFWF RR?Q@RAS@R?RA',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RRFQGRHSGRFRH',
        'H[MPTP RW[M[MFWF RR[P]O_PaRbTb',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RR[P]O_PaRbTb',
        'H[MPTP RW[M[MFWF RN>RAV>',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNERHVE',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RNAR>VA',
        'I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RNHREVH',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RN>O@QASAU@V>',
        'I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RNEOGQHSHUGVE',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RR?Q@RAS@R?RA',
        'I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RRFQGRHSGRFRH',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RR\\T]U_TaRbOb',
        'I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RRGPFODPBRAUA',
        'G]L[LF RLPXP RX[XF RNAR>VA',
        'H[M[MF RV[VPUNSMPMNNMO RIAM>QA',
        'G]IJ[J RL[LF RLPXP RX[XF',
        'H[M[MF RV[VPUNSMPMNNMO RJHRH',
        'MWR[RF RMAN@P?TAV@W?',
        'MWR[RM RMHNGPFTHVGWF',
        'MWR[RF RM@W@',
        'MWR[RM RMGWG',
        'MWR[RF RN>O@QASAU@V>',
        'MWR[RM RNEOGQHSHUGVE',
        'MWR[RF RR[P]O_PaRbTb',
        'MWR[RM RR[P]O_PaRbTb',
        'MWR[RF RR?Q@RAS@R?RA',
        'MWR[RM',
        'MgR[RF RbFbUaX_Z\\[Z[',
        'MaR[RM RRFQGRHSGRFRH R\\M\\_[aYbXb R\\F[G\\H]G\\F\\H',
        'JZUFUUTXRZO[M[ RQAU>YA',
        'MWRMR_QaObNb RNHREVH',
        'G\\L[LF RX[OO RXFLR RR\\T]U_TaRbOb',
        'IZN[NF RPSV[ RVMNU RR\\T]U_TaRbOb',
        31,
        'HYW[M[MF RO>LA',
        'MXU[SZRXRF RTEQH',
        'HYW[M[MF RR\\T]U_TaRbOb',
        'MXU[SZRXRF RR\\T]U_TaRbOb',
        'HYW[M[MF RVHSK',
        'M^U[SZRXRF RZFXJ',
        'HYW[M[MF RUNTOUPVOUNUP',
        'M\\U[SZRXRF RYOZPYQXPYOYQ',
        'HYW[M[MF RJQPM',
        'MXU[SZRXRF ROQUM',
        'G]L[LFX[XF RT>QA',
        'I\\NMN[ RNOONQMTMVNWPW[ RTEQH',
        'G]L[LFX[XF RR\\T]U_TaRbOb',
        'I\\NMN[ RNOONQMTMVNWPW[ RR\\T]U_TaRbOb',
        'G]L[LFX[XF RN>RAV>',
        'I\\NMN[ RNOONQMTMVNWPW[ RNERHVE',
        'MjSFQJ R\\M\\[ R\\O]N_MbMdNePe[',
        'G]LFL[ RLINGPFTFVGWHXJX^W`VaTbQb',
        'I\\NMN[ RNOONQMTMVNWPW_VaTbRb',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RM@W@',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMGWG',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN>O@QASAU@V>',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNEOGQHSHUGVE',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RQ>NA RX>UA',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RQENH RXEUH',
        'E`RPYP RRFR[ R\\FNFLGJIIMITJXLZN[\\[',
        'C`[ZY[U[SZRXRPSNUMYM[N\\P\\RRT RRQQOPNNMKMINHOGQGWHYIZK[N[PZQYRW',
        'G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RT>QA',
        'KXP[PM RPQQORNTMVM RTEQH',
        'G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RR\\T]U_TaRbOb',
        'KXP[PM RPQQORNTMVM RR\\T]U_TaRbOb',
        'G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RN>RAV>',
        'KXP[PM RPQQORNTMVM RNERHVE',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RT>QA',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RTEQH',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RNAR>VA',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RNHREVH',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RR\\T]U_TaRbOb',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RR\\T]U_TaRbOb',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RN>RAV>',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RNERHVE',
        'JZLFXF RR[RF RR\\T]U_TaRbOb',
        'MYOMWM RRFRXSZU[W[ RR\\T]U_TaRbOb',
        'JZLFXF RR[RF RN>RAV>',
        'M[OMWM RYFXI RRFRXSZU[W[',
        'JZLFXF RR[RF RNQVQ',
        'MYOMWM RRFRXSZU[W[ ROSUS',
        'G]LFLWMYNZP[T[VZWYXWXF RMAN@P?TAV@W?',
        'H[VMV[ RMMMXNZP[S[UZVY RMHNGPFTHVGWF',
        'G]LFLWMYNZP[T[VZWYXWXF RM@W@',
        'H[VMV[ RMMMXNZP[S[UZVY RMGWG',
        'G]LFLWMYNZP[T[VZWYXWXF RN>O@QASAU@V>',
        'H[VMV[ RMMMXNZP[S[UZVY RNEOGQHSHUGVE',
        'G]LFLWMYNZP[T[VZWYXWXF RRAP@O>P<R;T<U>T@RA',
        'H[VMV[ RMMMXNZP[S[UZVY RRHPGOEPCRBTCUETGRH',
        'G]LFLWMYNZP[T[VZWYXWXF RQ>NA RX>UA',
        'H[VMV[ RMMMXNZP[S[UZVY RQENH RXEUH',
        'G]LFLWMYNZP[T[VZWYXWXF RR[P]O_PaRbTb',
        'H[VMV[ RMMMXNZP[S[UZVY RV[T]S_TaVbXb',
        'F^IFN[RLV[[F RNAR>VA',
        'G]JMN[RQV[ZM RNHREVH',
        'I[RQR[ RKFRQYF RNAR>VA',
        'JZMMR[ RWMR[P`OaMb RNHREVH',
        'JZLFXF RR[RF RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'H\\KFYFK[Y[ RT>QA',
        'IZLMWML[W[ RTEQH',
        'H\\KFYFK[Y[ RR?Q@RAS@R?RA',
        'IZLMWML[W[ RRFQGRHSGRFRH',
        'H\\KFYFK[Y[ RN>RAV>',
        'IZLMWML[W[ RNERHVE',
        'MYR[RISGUFWF',
        'H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ RJHRH',
        'C\\LFL[T[VZWYXWXTWRVQSPLP RFKFIGGIFSFUGVHWJWLVNUOSP',
        'G\\VFLFL[R[UZWXXVXSWQUORNLN',
        'H[WFMFM[ RMNOMSMUNVOWQWWVYUZS[O[MZ',
        'H]MFM[S[VZXXYVYSXQVOSNMN',
        'IZNMN[S[UZVXVUUSSRNR',
        'I^MHNGQFSFVGXIYKZOZRYVXXVZS[Q[NZMY',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RMHKGJEKCLB',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RTMTIUGWFYF',
        28,
        'C\\FKFIGGIFQFTGVIWKXOXRWVVXTZQ[L[LF',
        'H]NFXFX[R[OZMXLVLSMQOORNXN',
        'I\\MFWFW[ RWNUMQMONNOMQMWNYOZQ[U[WZ',
        'I\\Q[T[VZWYXWXQWOVNTMQMONNOMQMWNYOZQ[T\\V]W_VaTbPbNa',
        'I\\WPPP RM[W[WFMF',
        'F^MHNGQFSFVGXIYKZOZRYVXXVZS[Q[NZLXKVJRZP',
        'G[PPTP RWGUFPFNGMHLJLLMNNOPPMQLRKTKWLYMZO[U[WZ',
        'HZTPMP RM[MFWF RM[M_LaJbHb',
        'MYOMWM RR[RISGUFWF RR[R_QaObMb',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RMHKGJEKCLB',
        'I[KFU[U_TaRbPaO_O[YF',
        'D`I[IF RIOJNLMOMQNRPRXSZU[X[ZZ[Y\\W\\P[NZM',
        'MZRFRWSYTZV[X[',
        'MWR[RF RNPVP',
        'G_L[LF RX[OO RLRWGYF[G\\I\\K',
        'IZNMN[ RPSV[ RVMNU RNMNIOGQFSF',
        'MXU[SZRXRF RNOVO',
        'JZRMM[ RMFOFPGRMW[ RNLTH',
        'Ca\\F\\[ R\\XZZX[V[TZSYRWRF RRWQYPZN[L[JZIYHWHF',
        'G]L[LFX[XF RL[L_KaIbGb',
        'I\\NMN[ RNOONQMTMVNWPWb',
        32,
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH',
        'DaSGQFMFKGIIHMHTIXKZM[Q[SZUXVTVMUISGUFYF[G\\I\\b',
        'E^RNPMMMKNJOIQIWJYKZM[P[RZSYTWTQSORNTMVMXNYPYb',
        'C\\LFL[ RFKFIGGIFTFVGWHXJXMWOVPTQLQ',
        'H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RRMRISGUFWF',
        'G\\LFL[ RQVXb RLKTKVLWMXOXRWTVUTVLV',
        'H\\XZU[P[NZMYLWLUMSNRPQTPVOWNXLXJWHVGTFOFLG',
        'IZVZT[P[NZMXMWNUPTSTUSVQVPUNSMPMNN',
        'H[W[L[SPLFWF',
        'JYWbUbSaR_RIQGOFMGLIMKOLQKRI',
        'MYOMWM RRFRXSZU[W[ RW[W_VaTbRb',
        'HZR[RF RKKKILGNFXF',
        'MYOMWM RWFUFSGRIRXSZU[W[',
        'JZLFXF RR[RF RR[R_SaUbWb',
        'G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@',
        'H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG',
        'F^ZFUFUJWKYMZPZUYXWZT[P[MZKXJUJPKMMKOJOFJF',
        'G]LFLWMYNZP[T[VZXXYVYIXGWF',
        'I`RQR[ RKFRQXGZF\\G]I]K',
        'J^MMR[ RMbOaP`R[VNXMZN[P[R',
        'H\\KFYFK[Y[ RNPVP',
        'IZLMWML[W[ RNTVT',
        2,
        'H\\YFLFSNPNNOMPLRLWMYNZP[V[XZYY',
        'JZWMNMUVRVPWOXNZN^O`PaRbUbWa',
        'JZMMVMOTSTUUVWVXUZS[Q[O\\N^N_OaQbVb',
        'H\\LHMGOFTFVGWHXJXLWOK[X[ RNSVS',
        'H\\WFMFLPMOONTNVOWPXRXWWYVZT[O[MZLY',
        'JZVMOMNSPRSRUSVUVXUZS[P[NZ',
        'J^MZP[T[WZYXZVZSYQWOTNPNPF RLITI',
        'H[MMMb RMONNPMTMVNWPWSVUM^',
        'MWRFRb',
        'JZOFOb RUFUb',
        'MWRFRb ROWUW ROQUQ',
        'MWRYSZR[QZRYR[ RRSQGRFSGRSRF',
        'GpL[LFQFTGVIWKXOXRWVVXTZQ[L[ R_FmF_[m[ Rb>fAj>',
        'GmL[LFQFTGVIWKXOXRWVVXTZQ[L[ R_MjM_[j[ RaEeHiE',
        'ImW[WF RWZU[Q[OZNYMWMQNOONQMUMWN R_MjM_[j[ RaEeHiE',
        'HiW[M[MF RdFdUcXaZ^[\\[',
        'HcW[M[MF R^M^_]a[bZb R^F]G^H_G^F^H',
        'MbU[SZRXRF R]M]_\\aZbYb R]F\\G]H^G]F]H',
        'GmL[LFX[XF RhFhUgXeZb[`[',
        'GgL[LFX[XF RbMb_aa_b^b RbFaGbHcGbFbH',
        'IfNMN[ RNOONQMTMVNWPW[ RaMa_`a^b]b RaF`GaHbGaFaH',
        'I[MUWU RK[RFY[ RN>RAV>',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNERHVE',
        'MWR[RF RN>RAV>',
        'MWR[RM RNERHVE',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN>RAV>',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNERHVE',
        'G]LFLWMYNZP[T[VZWYXWXF RN>RAV>',
        'H[VMV[ RMMMXNZP[S[UZVY RNERHVE',
        'G]LFLWMYNZP[T[VZWYXWXF RN?O@NAM@N?NA RV?W@VAU@V?VA RM;W;',
        'H[VMV[ RMMMXNZP[S[UZVY RNFOGNHMGNFNH RVFWGVHUGVFVH RM@W@',
        'G]LFLWMYNZP[T[VZWYXWXF RN?O@NAM@N?NA RV?W@VAU@V?VA RT9Q<',
        'H[VMV[ RMMMXNZP[S[UZVY RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA',
        'G]LFLWMYNZP[T[VZWYXWXF RN?O@NAM@N?NA RV?W@VAU@V?VA RN9R<V9',
        'H[VMV[ RMMMXNZP[S[UZVY RNFOGNHMGNFNH RVFWGVHUGVFVH RN>RAV>',
        'G]LFLWMYNZP[T[VZWYXWXF RN?O@NAM@N?NA RV?W@VAU@V?VA RP9S<',
        'H[VMV[ RMMMXNZP[S[UZVY RNFOGNHMGNFNH RVFWGVHUGVFVH RP>SA',
        33,
        'I[MUWU RK[RFY[ RN?O@NAM@N?NA RV?W@VAU@V?VA RM;W;',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNFOGNHMGNFNH RVFWGVHUGVFVH RM@W@',
        'I[MUWU RK[RFY[ RR?Q@RAS@R?RA RM;W;',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RRFQGRHSGRFRH RM@W@',
        'F`JURU RRPYP RH[OF\\F RRFR[\\[ RO@Y@',
        'D`INKMOMQNRP R[ZY[U[SZRXRPSNUMYM[N\\P\\RRSKSITHVHXIZK[O[QZRX RMGWG',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RSV[V',
        'I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RS^[^',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RN>RAV>',
        'I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RNERHVE',
        'G\\L[LF RX[OO RXFLR RN>RAV>',
        'IZN[NF RPSV[ RVMNU RJANDRA',
        'G]R[P]O_PaRbTb RPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF',
        'H[R[P]O_PaRbTb RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[',
        'G]R[P]O_PaRbTb RPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RM@W@',
        'H[R[P]O_PaRbTb RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMGWG',
        'H\\KFXFQNTNVOWPXRXWWYVZT[N[LZKY RN>RAV>',
        'JZMMVMOVRVTWUXVZV^U`TaRbObMa RNERHVE',
        'MWRMR_QaObNb RNERHVE',
        'GpL[LFQFTGVIWKXOXRWVVXTZQ[L[ R_FmF_[m[',
        'GmL[LFQFTGVIWKXOXRWVVXTZQ[L[ R_MjM_[j[',
        'ImW[WF RWZU[Q[OZNYMWMQNOONQMUMWN R_MjM_[j[',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RT>QA',
        'I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RTEQH',
        'CaH[HF RHPTP RTFTXUZW[Z[\\Z]X]M',
        'G\\LFLb RLINGPFTFVGWHXJXOWRUUL^',
        'G]L[LFX[XF RP>SA',
        'I\\NMN[ RNOONQMTMVNWPW[ RPESH',
        'I[MUWU RK[RFY[ RZ9X< RR;P<O>P@RAT@U>T<R;',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RZ@XC RRBPCOEPGRHTGUETCRB',
        'F`JURU RRPYP RH[OF\\F RRFR[\\[ RV>SA',
        'D`INKMOMQNRP R[ZY[U[SZRXRPSNUMYM[N\\P\\RRSKSITHVHXIZK[O[QZRX RTEQH',
        'G]ZFJ[ RP[NZLXKTKMLINGPFTFVGXIYMYTXXVZT[P[ RT>QA',
        'H[XMK[ RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RTEQH',
        'I[MUWU RK[RFY[ ROAL> RVAS>',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR ROHLE RVHSE',
        'I[MUWU RK[RFY[ RNAO?Q>S>U?VA',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNHOFQESEUFVH',
        'H[MPTP RW[M[MFWF ROAL> RVAS>',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT ROHLE RVHSE',
        'H[MPTP RW[M[MFWF RNAO?Q>S>U?VA',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNHOFQESEUFVH',
        'MWR[RF ROAL> RVAS>',
        'MWR[RM ROHLE RVHSE',
        'MWR[RF RNAO?Q>S>U?VA',
        'MWR[RM RNHOFQESEUFVH',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF ROAL> RVAS>',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ ROHLE RVHSE',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RNAO?Q>S>U?VA',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNHOFQESEUFVH',
        'G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ ROAL> RVAS>',
        'KXP[PM RPQQORNTMVM RPHME RWHTE',
        'G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RNAO?Q>S>U?VA',
        'KXP[PM RPQQORNTMVM ROHPFRETEVFWH',
        'G]LFLWMYNZP[T[VZWYXWXF ROAL> RVAS>',
        'H[VMV[ RMMMXNZP[S[UZVY ROHLE RVHSE',
        'G]LFLWMYNZP[T[VZWYXWXF RNAO?Q>S>U?VA',
        'H[VMV[ RMMMXNZP[S[UZVY RNHOFQESEUFVH',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RS`SaRcQd',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RS`SaRcQd',
        'JZLFXF RR[RF RS`SaRcQd',
        'MYOMWM RRFRXSZU[W[ RU`UaTcSd',
        'I]VRXTYVY[X]V_T`Lb RLHMGOFUFWGXHYJYNXPVRTSNU',
        'J[UWVXWZW]V_U`SaMb RMNOMSMUNVOWQWTVVUWSXOY',
        'G]L[LF RLPXP RX[XF RN>RAV>',
        'H[M[MF RV[VPUNSMPMNNMO RI>MAQ>',
        'G]L[LFX[XF RX[Xb',
        'IbWFWXXZZ[\\[^Z_X^V\\UZVV^ RWNUMQMONNOMQMWNYOZQ[T[VZWX',
        'G]NFLGKIKKLMMNOO RVFXGYIYKXMWNUO ROOUOWPXQYSYWXYWZU[O[MZLYKWKSLQMPOO',
        'J[MJMMNORQVOWMWJ RPQTQVRWTWXVZT[P[NZMXMTNRPQ',
        'H\\KFYFK[Y[ RY[Y_XaVbTb',
        'IZLMWML[W[ RW[W_VaTbRb',
        'I[MUWU RK[RFY[ RR?Q@RAS@R?RA',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RRFQGRHSGRFRH',
        'H[MPTP RW[M[MFWF RR\\T]U_TaRbOb',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RR\\T]U_TaRbOb',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN?O@NAM@N?NA RV?W@VAU@V?VA RM;W;',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNFOGNHMGNFNH RVFWGVHUGVFVH RM@W@',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RMAN@P?TAV@W? RM;W;',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMHNGPFTHVGWF RM@W@',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RR?Q@RAS@R?RA',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RRFQGRHSGRFRH',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RR?Q@RAS@R?RA RM;W;',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RRFQGRHSGRFRH RM@W@',
        'I[RQR[ RKFRQYF RM@W@',
        'JZMMR[ RWMR[P`OaMb RMGWG',
        'M]RFRXSZU[W[YZZXYVWUUVQ^',
        'IbNMN[ RNOONQMTMVNWPWXXZZ[\\[^Z_X^V\\UZVV^',
        'M]OMWM RRFRXSZU[W[YZZXYVWUUVQ^',
        'MWRMR_QaObNb',
        'D`R[RF RRZP[L[JZIYHWHQIOJNLMPMRN RTMXMZN[O\\Q\\W[YZZX[T[RZ',
        'D`RMRb RRZP[L[JZIYHWHQIOJNLMPMRN RTMXMZN[O\\Q\\W[YZZX[T[RZ',
        'I[MUWU RK[RFY[ RXCL`',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RXCL`',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RWHM`',
        'HYW[M[MF RIOQO',
        'JZLFXF RR[RF RXCL`',
        'J[P[R^T_W_ RNZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN',
        'IZLMWML[N[P\\R^T_W_',
        'J^MGPFTFWGYIZKZNYPWRTSPSP[',
        'J^NNPMTMVNWOXQXSWUVVTWPWP[',
        'G\\SPVQWRXTXWWYVZT[L[LFSFUGVHWJWLVNUOSPLP RIUOU',
        'G]IM[M RLFLWMYNZP[T[VZWYXWXF',
        'I[Y[RFK[',
        'H[MPTP RW[M[MFWF RXCL`',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RWHM`',
        'JZUFUUTXRZO[M[ RQPYP',
        'MWRMR_QaObNb ROTUT RRFQGRHSGRFRH',
        'G]XFX^Y`Za\\b^b RXIVGTFPFNGLIKMKTLXNZP[T[VZXX',
        'I\\WMW^X`Ya[b]b RWZU[Q[OZNYMWMQNOONQMUMWN',
        'G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RIQOQ',
        'KXP[PM RPQQORNTMVM RMTUT',
        'I[KIYI RRQR[ RKFRQYF',
        'JZLQXQ RMMR[ RWMR[P`OaMb',
        'H[MMMXNZP[T[VZ RMNOMTMVNWPWRVTTUOUMV',
        34,
        'G\\K[NQOOPNRMTMVNWOXRXVWYVZT[R[PZOYNWMPLNJM',
        'H[RFPFNGMIM[ RMNOMSMUNVOWQWWVYUZS[O[MZ',
        'J\\NNPMTMVNWOXQXWWYVZT[P[NZ',
        'HZVNTMPMNNMOLQLWMYNZP[S[UZVXUVSUQVM^',
        'I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RW[W_XaZb\\b',
        'I\\\\FZFXGWIW[ RWZU[Q[OZNYMWMQNOONQMUMWN',
        'I[NZP[T[VZWXWPVNTMPMNNMPMRWT',
        33,
        'IbNNPMTMVNWPWXVZT[P[NZMXMV\\S\\U]W_X`X',
        35,
        'J[TTVSWQWPVNTMPMNN RRTTTVUWWWXVZT[P[NZ',
        'JaRTTTVUWWWXVZT[P[NZ RNNPMTMVNWPWQVSTT[S[U\\W^X_X',
        'H[TTVSWQWPVNTMPMNNMOLRLVMYNZP[T[VZWXWWVUTTRT',
        'MWRMR_QaObNb ROTUT',
        'I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RWMWIXGZF\\F',
        'I\\WYVZT[P[NZMXMQNOONQMWMW^V`UaSbMb',
        'HZUNSMPMNNMOLQLWMYNZP[T[VZVUSU',
        'JZMMU[U_TaRbPaO_O[WM',
        'JZMMTVUXTZR[PZOXPVWM',
        'I\\WMWb RNMNXOZQ[T[VZWY',
        'H[RFPFNGMIM[ RV[VPUNSMPMNNMO',
        'H[RFPFNGMIM[ RV[VPUNSMPMNNMO RV[V_UaSbQb',
        'MWR[RM ROTUT RRFQGRHSGRFRH',
        36,
        'MWR[RM RU[O[ RUMOM',
        'MXU[SZRXRF RMONNPMTOVNWM',
        'IYU[SZRXRF RRQQOONMOLQMSOTWT',
        'MXRFR_SaUbWb',
        'GZLFLXMZO[ RLMVMOVRVTWUXVZV^U`TaRbObMa',
        'D`[M[[ R[YZZX[U[SZRXRM RRXQZO[L[JZIXIM',
        'D`[M[[ R[YZZX[U[SZRXRM RRXQZO[L[JZIXIM R[[[b',
        'D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ R[[[_ZaXbVb',
        'I\\NMN[ RNOONQMTMVNWPW[ RN[N_MaKbIb',
        'I\\NMN[ RNOONQMTMVNWPW[ RW[W_XaZb\\b',
        'H[M[MMV[VM',
        37,
        'E]RTXT RRMR[ RZMMMKNJOIQIWJYKZM[Z[',
        'G]RTRXSZU[V[XZYXYQXOWNUMOMMNLOKQKXLZN[O[QZRX',
        38,
        'LYTMT[ RTWSYRZP[N[',
        'LYTMT[ RTWSYRZP[N[ RTMTF',
        'LYTMT[ RTWSYRZP[N[ RT[T_UaWbYb',
        'KXP[PM RPQQORNTMVM RP[Pb',
        'KXP[PM RPQQORNTMVM RP[P_QaSbUb',
        'KXM[S[ RVMTMRNQOPRP[',
        'LYW[Q[ RNMPMRNSOTRT[',
        'I[RUW[ RN[NMTMVNWPWRVTTUNU',
        'I[RSWM RNMN[T[VZWXWVVTTSNS',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RN[N_OaQbSb',
        'KYWFUFSGRIR_QaObMb',
        'MWRMR_QaObNb ROTUT RRMRISGUFWF',
        'KYMFOFQGRIRXSZU[W[',
        'KYWFUFSGRIR_QaObMaL_M]O\\V\\',
        'KWU[M[ RRbRPQNOMMM',
        'MYOMWM RRFR_SaUbWb',
        'H[JRYR RVMV[ RMMMXNZP[S[UZVY',
        'I\\XMUMUPWRXTXWWYVZT[Q[OZNYMWMTNRPPPMMM',
        'H[MMMXNZP[S[UZVYWWWPVNUM',
        'JZW[RMM[',
        'G]Z[VMRWNMJ[',
        'JZW[RM RM[RMTHUGWF',
        'KYRTR[ RMMRTWM',
        'IZLMWML[W[ RW[W_XaZb\\b',
        'IZLMWML[T[VZWXVVTURVN^',
        'JZMMVMOVRVTWUXVZV^U`TaRbObMa',
        'JZMMVMOVRVTWUXVZV^U`TaRbPbNaM_N]P\\R]Uc',
        'J^MGPFTFWGYIZKZNYPWRTSPSP[',
        'FZWGTFPFMGKIJKJNKPMRPSTST[',
        'J^MZP[T[WZYXZVZSYQWOTNPNPF',
        'F[WHVGSFQFNGLIKKJOJYK]L_NaQbSbVaW`',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RROQPRQSPRORQ',
        'I[STVUWWWXVZT[N[NMSMUNVPVQUSSTNT',
        'I\\PTNUMWMXNZP[T[VZWYXVXRWOVNTMPMNNMPMQNSPTRT',
        'HZUNSMPMNNMOLQLWMYNZP[T[VZVUSU RUMUIVGXFZF',
        'H[MTVT RMMM[ RVMV[',
        'LXRMR_QaObMaL_M]O\\V\\ RRFQGRHSGRFRH',
        'J[VMVb RTUNM RN[VS',
        'JYOMO[V[',
        'I\\WMWb RWZU[Q[OZNYMWMQNOONQMUMWN RWMWIXGZF\\F',
        'J^MGPFTFWGYIZKZNYPWRTSPSP[ RLXTX',
        'FZWGTFPFMGKIJKJNKPMRPSTST[ RPXXX',
        'D`R[RF RRM]MR[][ RRZP[L[JZIYHWHQIOJNLMPMRN',
        'E`RFR[ RRNPMMMKNJOIQIWJYKZM[P[RZ RRM\\MUVXVZW[X\\Z\\^[`ZaXbUbSa',
        'D`R[RF RRM]MR[Z[\\Z]X\\VZUXVT^ RRZP[L[JZIYHWHQIOJNLMPMRN',
        'G^IMQM RLFLXMZO[QZS[W[YZZXZWYUWTTTRSQQQPRNTMWMYN',
        'I[KMTM RNFNXOZQ[T[ RYFWFUGTIT_SaQbOb',
        'F^HMPM RKFKXLZN[P[RZ RZNXMTMRNQOPQPWQYRZT[W[YZZXYVWUUVQ^',
        'F]HMPMP[ RK[KILGNFPF RPOQNSMVMXNYPY_XaVbTb',
        'G^LFLXMZO[QZS[W[YZZXZWYUWTTTRSQQQPRNTMWMYN',
        'H^MM[MP[ RMFMXNZP[[[',
        'G]JSN[RUV[ZS RJFNNRHVNZF',
        'G]XXXSLSLX RXKXFLFLK',
        'I\\WMWb RNMNXOZQ[T[VZWY RNMNIMGKFIF',
        'I\\\\bZbXaW_WM RNMNXOZQ[T[VZWY RNMNIMGKFIF',
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        'H[MFM[ RXPMP',
        'IZNTVT RNMN[',
        'G]R[RF RKOKFYFYO',
        'I[R[RF RMOMFWFWO',
        'MWSFQJ',
        'MWS[Q_',
        'G]LFL[XFX[',
        'H\\MMM[WMW[',
        23,
        23,
        'NVR`RcSdTd',
        'J\\NZP[T[VZWYXWXQWOVNTMPMNN',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RRSQTRUSTRSRU',
        'J\\NZP[T[VZWYXWXQWOVNTMPMNN RRSQTRUSTRSRU',
        'MWSZS[R]Q^ RRNSORPQORNRP',
        23,
        23,
        23,
        23,
        23,
        25,
        'LXNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA',
        'G[MUWU RK[RFY[ RMEJH',
        26,
        'B[MPTP RW[M[MFWF RHEEH',
        'A]L[LF RLPXP RX[XF RGEDH',
        'GWR[RF RMEJH',
        24,
        'B]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RHEEH',
        24,
        '@[RQR[ RKFRQYF RFECH',
        '@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH',
        'MXRMRXSZU[ RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA',
        3,
        4,
        'HZM[MFXF',
        'I[K[RFY[K[',
        6,
        'H\\KFYFK[Y[',
        7,
        'F^OPUP RPFTFVGXIYKZNZSYVXXVZT[P[NZLXKVJSJNKKLINGPF',
        8,
        9,
        'I[K[RFY[',
        10,
        'G]L[LFX[XF',
        'H[L[W[ RLFWF RUPNP',
        11,
        'G]L[LFXFX[',
        12,
        24,
        'H[W[L[SPLFWF',
        13,
        15,
        'G]R[RF RPITIWJYLZNZRYTWVTWPWMVKTJRJNKLMJPI',
        14,
        'G]R[RF RHFJGKIKNLQMROSUSWRXQYNYIZG\\F',
        'F^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[',
        27,
        'I[RQR[ RKFRQYF RN?O@NAM@N?NA RV?W@VAU@V?VA',
        39,
        40,
        41,
        42,
        'H[MMMXNZP[S[UZVYWWWPVNUM RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA',
        34,
        'H[SOUPVQWSWWVYUZS[P[NZMY RKbLaM_MINGPFSFUGVIVLUNSOQO',
        'JZRYRb RLMMMNNRYWM',
        'H[SMPMNNMOLQLWMYNZP[S[UZVYWWWQVOUNSMPLNKMINGPFTFVG',
        35,
        'HZMFWFPMNPMSMWNYOZQ[S[U\\V^V_UaSbRb',
        'I\\NMN[ RNOONQMTMVNWPWb',
        'H[LPWP RPFSFUGVHWKWVVYUZS[P[NZMYLVLKMHNGPF',
        36,
        31,
        'JZRMM[ RMFOFPGRMW[',
        'H^MMMb RWXXZZ[ RMXNZP[T[VZWXWM',
        'J[MMR[WPWOVM',
        'HZMFWF RQFOGNINLONQOUO RQOOPNQMSMWNYOZQ[S[U\\V^V_UaSbRb',
        19,
        'F]VMV[ ROMOXNZL[ RZMMMKNJP',
        'H\\MbMQNOONQMTMVNWOXQXWWYVZT[Q[OZMX',
        'HZVNTMPMNNMOLQLWMYNZP[S[U\\V^V_UaSb',
        'H\\YMPMNNMOLQLWMYNZP[S[UZVYWWWQVOUNSM',
        'H\\LPMNOMXM RRMRXSZU[',
        'H[MMMXNZP[S[UZVYWWWPVNUM',
        'G]MMLNKPKVLXNZP[T[VZXXYVYPXNVMUMSNRPRb',
        'IZWMLb RLMNNOPT_UaWb',
        'G]RMRb RKMKVLXNZP[T[VZXXYVYM',
        43,
        'LXNFOGNHMGNFNH RVFWGVHUGVFVH RRMRXSZU[',
        'H[MMMXNZP[S[UZVYWWWPVNUM RNFOGNHMGNFNH RVFWGVHUGVFVH',
        29,
        44,
        45,
        'G\\L[LF RXFLR ROOX[Qb',
        'H[SOUPVQWSWWVYUZS[P[NZMXMINGPFSFUGVIVLUNSOQO',
        'H[JPKQLSLVMYNZP[S[UZVYWVWKVHUGSFPFNGMHLJLLMNNOPPWP',
        'I\\KFMFOGQIRKR[ RRKSHTGVFWFYGZI',
        'NiTEQH RXFZF\\G^I_K_[ R_K`HaGcFdFfGgI',
        'I\\KFMFOGQIRKR[ RRKSHTGVFWFYGZI RN?O@NAM@N?NA RV?W@VAU@V?VA',
        38,
        'F^RTRX R[MIM RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM',
        'IZLMNNOPOXNZM[LZLXMVVRWPWNVMUNTPTXUZW[V^U`TaRb',
        'G]R[Rb RPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF',
        'H[R[Rb RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[',
        'FZWFQFNGLIKKJOJRKVLXNZQ[R[T\\U^U_TaSbQb',
        'HZVMPMNNMOLQLWMYNZP[R[T\\U^U_TaRbPb',
        'HZTPMP RM[MFWF',
        'MZVPRP RWFUFSGRIR_QaOb',
        'H\\MFOGPILSXNTXUZW[',
        'I[RFMPWPR[',
        'H\\NGNL RXIULTNTW RKIMGPFTFVGXIYKZOZUYYX[',
        'H\\L[UR RR[WV RLMPNSPURWVXZXb',
        'CaRWRR R\\XY]V`SaMa RLFJGHIGLGUHXJZL[N[PZQYRWSYTZV[X[ZZ\\X]U]L\\IZGXF',
        'G]RTRX RXZW\\S`PaOa RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM',
        'G]XFXb RPFNGLIKMKTLXNZP[T[VZXX',
        'I\\WMWb RQMONNOMQMWNYOZQ[T[VZWY',
        'F]KFK[ RKQMOPNTNVOXQYTYWXZW\\U^R`Nb',
        'I[WLWMVPTRRSPSNRMPMONMPLRLTMVPWSWWVYUZS[M[',
        'F]KHLGOFTFWGXHYJYLXOVQJ[N^Q_V_Y^',
        'J[NNPMTMVNWPWRVTTVN[P]R^U^W]',
        'G]I[[[ RIFJFLGXZZ[ R[FZFXGLZJ[',
        'H[KMMNVZX[K[MZVNXM',
        'G\\XEVFOFMGLHKJKWLYMZO[T[VZWYXWXPWNVMTLNLLMKN',
        'H[WEVFTGPGNHMILKLWMYNZP[S[UZVYWWWQVOUNSMOMMNLO',
        'G]RFRb RKQKMYMYQ',
        'I[MMWM RRFRb',
        'IZLMNNOPOXNZM[LZLXMVVRWPWNVMUNTPTXUZW[',
        'H\\WbQbOaN`M^MQNOONQMTMVNWOXQXWWYVZT[Q[OZMX',
        17,
        18,
        32,
        'HZLTST RVZT[P[NZMYLWLQMONNPMTMVN',
        'J\\XTQT RNZP[T[VZWYXWXQWOVNTMPMNN',
        'G\\LFL[ RLKTKVLWMXOXRWTVUTVLV',
        'H[MFMb RMNOMSMUNVOWQWWVYUZS[O[MZ',
        5,
        'F^K[KFRMYFY[',
        'G]LbLMRSXMX[',
        'G\\J`S` RMbMQNOONQMTMVNWOXQXWWYVZT[Q[OZMX',
        'I^MYNZQ[S[VZXXYVZRZOYKXIVGSFQFNGMH',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RROQPRQSPRORQ',
        'I^MYNZQ[S[VZXXYVZRZOYKXIVGSFQFNGMH RROQPRQSPRORQ',
        'H[MPTP RW[M[MFWF RP>SA',
        'H[MPTP RW[M[MFWF RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'JbLFXF RR[RF RRMXM[N]P^S^\\]_[aXbVb',
        'HZM[MFXF RT>QA',
        'F[JPTP RWYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG',
        8,
        27,
        'JZUFUUTXRZO[M[',
        'AbC[D[FZGXILJILGOFRFR[X[[Z]X^V^S]Q[OXNRN',
        'AbF[FF RRFR[X[[Z]X^V^S]Q[OXNFN',
        'JbLFXF RR[RF RRMXM[N]P^S^[',
        'G\\L[LF RX[OO RXFLR RT>QA',
        'G]LFL[XFX[ RP>SA',
        'G[KFRT RYFPXNZL[K[ RN>O@QASAU@V>',
        'G]R[R` RLFL[X[XF',
        3,
        'G\\VFLFL[R[UZWXXVXSWQUORNLN',
        4,
        'HZM[MFXF',
        'F^[`[[I[I` RW[WFRFPGOHNJL[',
        6,
        'BbOOF[ RR[RF RRRFF R^[UO R^FRR',
        'I]PPTP RMGOFTFVGWHXJXLWNVOTPWQXRYTYWXYWZU[O[MZ',
        'G]LFL[XFX[',
        'G]LFL[XFX[ RN>O@QASAU@V>',
        9,
        'F\\W[WFTFQGOINLLXKZI[H[',
        10,
        7,
        11,
        'G]L[LFXFX[',
        12,
        5,
        13,
        'G[KFRT RYFPXNZL[K[',
        'G]R[RF RPITIWJYLZNZRYTWVTWPWMVKTJRJNKLMJPI',
        14,
        'G]XFX[ RLFL[Z[Z`',
        'H\\WFW[ RLFLNMPNQPRWR',
        'CaRFR[ RHFH[\\[\\F',
        'CaRFR[ RHFH[\\[\\F R\\[^[^`',
        'F]HFMFM[S[VZXXYVYSXQVOSNMN',
        'Da\\F\\[ RIFI[O[RZTXUVUSTQROONIN',
        'H]MFM[S[VZXXYVYSXQVOSNMN',
        'I^ZQPQ RMHNGQFSFVGXIYKZOZRYVXXVZS[Q[NZMY',
        'CaHFH[ ROPHP RTFXFZG\\I]M]T\\XZZX[T[RZPXOTOMPIRGTF',
        'G\\RQK[ RW[WFOFMGLHKJKMLOMPOQWQ',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR',
        'H[WEVFTGPGNHMILKLWMYNZP[S[UZVYWWWQVOUNSMOMMNLO',
        'I[STVUWWWXVZT[N[NMSMUNVPVQUSSTNT',
        'JYO[OMWM',
        'H[WOVNTMPMNNMOLQLWMYNZP[S[UZVYWWWJVHUGSFOFMG',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT',
        'F^QTJ[ RRUJM RRMR[ RZ[ST RZMRU',
        'K[RTTT RNNPMTMVNWPWQVSTTVUWWWXVZT[P[NZ',
        'H\\MMM[WMW[',
        'H\\MMM[WMW[ RNEOGQHSHUGVE',
        31,
        'I[V[VMSMQNPPOXNZL[',
        'G]L[LMRXXMX[',
        'H[MTVT RMMM[ RVMV[',
        19,
        'H[M[MMVMV[',
        'H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ',
        17,
        'KYMMWM RRMR[',
        'JZMMR[ RWMR[P`OaMb',
        38,
        'IZL[WM RLMW[',
        'I\\WMW[ RNMN[Y[Y`',
        'J\\VMV[ RNMNROTQUVU',
        'F^RMR[ RKMK[Y[YM',
        'F^RMR[ RKMK[Y[YM RY[[[[`',
        'HZJMNMN[S[UZVXVUUSSRNR',
        'F^YMY[ RKMK[P[RZSXSURSPRKR',
        'IZNMN[S[UZVXVUUSSRNR',
        'J\\XTQT RNNPMTMVNWOXQXWWYVZT[P[NZ',
        'E_JTPT RJMJ[ RT[RZQYPWPQQORNTMWMYNZO[Q[WZYYZW[T[',
        'I[RUM[ RV[VMPMNNMPMRNTPUVU',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RPESH',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'M^OKXK RRFR[ RRSSRUQWQYRZTZ[Y^WaVb',
        'JYO[OMWM RTEQH',
        'HZLTST RVZT[P[NZMYLWLQMONNPMTMVN',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN',
        'MWR[RM RRFQGRHSGRFRH',
        'LXNFOGNHMGNFNH RVFWGVHUGVFVH RR[RM',
        18,
        'E^H[JZKXLPMNOMRMR[W[YZZXZUYSWRRR',
        'D^IMI[ RRMR[W[YZZXZVYTWSIS',
        'M^OKXK RRFR[ RRSSRUQWQYRZTZ[',
        'IZNMN[ RPSV[ RVMNU RTEQH',
        'H\\MMM[WMW[ RPESH',
        'JZMMR[ RWMR[P`OaMb RNEOGQHSHUGVE',
        'H]R[R` RMMM[W[WM',
        'CaRWRR RLFJGHIGLGUHXJZL[N[PZQYRWSYTZV[X[ZZ\\X]U]L\\IZGXF',
        43,
        'F]IIVI RMFM[S[VZXXYVYSXQVOSNMN',
        'HZJMTM RNFN[S[UZVXVUUSSRNR',
        'D`IFI[ RYPIP R\\Y[ZX[V[SZQXPVOROOPKQISGVFXF[G\\H',
        'F^KMK[ RWTKT RZZX[T[RZQYPWPQQORNTMXMZN',
        'F^LSXS RRSR[ RH[RF\\[',
        'I[NUVU RRUR[ RK[RMY[',
        'AbF[FF RFS\\S RVSV[ RL[VF`[',
        'E_J[JM RVUV[ RZUJU RO[VM][',
        'E_R[RPJFZFRP RI[IVJSLQOPUPXQZS[V[[',
        'G]R[RTLMXMRT RK[KXLVMUOTUTWUXVYXY[',
        'AcF[FF RFPSP RV[VPNF^FVP RM[MVNSPQSPYP\\Q^S_V_[',
        'DaI[IM RITST RV[VTPM\\MVT RO[OXPVQUSTYT[U\\V]X][',
        'H\\OPSP RNAQFSBTAUA RLGNFSFUGVHWJWLVNUOSPVQWRXTXWWYVZT[O[M\\L^L_MaObWb',
        'J[RTTT ROHRMTIUHVH RNNPMTMVNWPWQVSTTVUWWWXVZT[Q[O\\N^N_OaQbVb',
        'G]R[RF RHFJGKIKNLQMROSUSWRXQYNYIZG\\F',
        'G]RMRb RKMKVLXNZP[T[VZXXYVYM',
        32,
        37,
        'I[KFR[YF',
        20,
        'I[KFR[YF ROAL> RVAS>',
        'JZMMR[WM ROHLE RVHSE',
        'GmPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF R`Me[ RjMe[c`ba`b',
        'HkP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ R^Mc[ RhMc[a``a^b',
        'CaRXR^ RRCRI RMFJGHIGLGUHXJZM[W[ZZ\\X]U]L\\IZGWFMF',
        'G]RYR] RRKRO ROMMNLOKQKWLYMZO[U[WZXYYWYQXOWNUMOM',
        'CaRWRR RLFJGHIGLGUHXJZL[N[PZQYRWSYTZV[X[ZZ\\X]U]L\\IZGXF RLBM@O?R?U@X@',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RLIMGOFRFUGXG',
        'CaRWRR RLFJGHIGLGUHXJZL[N[PZQYRWSYTZV[X[ZZ\\X]U]L\\IZGXF RM<W< RR<R?',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RMEWE RRERH',
        'FZWGTFPFMGKIJKJNKPMRPSTST[',
        'FZVNTMPMNNMOLQLSMUNVPWTWT[',
        'H[N]UO ROQWU RT[LW',
        'JZMHMFWGWE',
        'JZMHUEVH',
        16,
        25,
        'KZLIMGOFRFUGXG',
        ':j>R?PAOCPDR RC^D\\F[H\\I^ RCFDDFCHDIF ROcPaR`TaUc ROAP?R>T?UA R[^\\\\^[`\\a^ R[F\\D^C`DaF R`RaPcOePfR',
        ':jDQ>Q RH[D_ RHGDC RR_Re RRCR= R\\[`_ R\\G`C R`QfQ',
        'G]LFL[XFX[ RX[[[Ub RN>O@QASAU@V>',
        'H\\MMM[WMW[ RW[Z[Tb RNEOGQHSHUGVE',
        'H]MFM[S[VZXXYVYSXQVOSNMN RJIPI',
        'IZKMQM RNFN[S[UZVXVUUSSRNR',
        'G\\L[LFTFVGWHXJXMWOVPTQLQ RTMXS',
        'H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RSWW]',
        'HZM[MFXFXA',
        'JYO[OMWMWH',
        'HZM[MFXF RJQRQ',
        'JYO[OMWM RLTTT',
        'H]M[MFXF RMMSMVNXPYSY\\X_VaSbQb',
        'J\\O[OMWM ROTTTVUWVXXX[W^UaTb',
        'BbOOF[ RR[RF RRRFF R^[UO R^FRR R^[`[``',
        'F^QTJ[ RRUJM RRMR[ RZ[ST RZMRU RZ[\\[\\`',
        'I]PPTP RMGOFTFVGWHXJXLWNVOTPWQXRYTYWXYWZU[O[MZ RR\\T]U_TaRbOb',
        'K[RTTT RNNPMTMVNWPWQVSTTVUWWWXVZT[P[NZ RR\\T]U_TaRbOb',
        'G\\L[LF RX[OO RXFLR RX[Z[Z`',
        'IZNMN[ RPSV[ RVMNU RV[X[X`',
        'G\\L[LF RX[OO RXFLR RPKPS',
        'IZNMN[ RPSV[ RVMNU RRORW',
        'G\\L[LF RX[OO RXFLR RIJOJ',
        'IZN[NF RPSV[ RVMNU RKJQJ',
        'E\\X[OO RXFLR RGFLFL[',
        'HZPSV[ RVMNU RJMNMN[',
        'G]L[LF RLPXP RX[XF RX[Z[Z`',
        'H[MTVT RMMM[ RVMV[ RV[X[X`',
        'GeL[LF RLPXP RX[XFcF',
        'H`MTVT RMMM[ RV[VM^M',
        'GhL[LFXFX[ RXM^MaNcPdSd\\c_aa^b\\b',
        'HcM[MMVMV[ RVT[T]U^V_X_[^^\\a[b',
        'F^QFNGLIKKJOJRKVLXNZQ[S[VZXXYVZRZMYJWIVITJSMSRTVUXWZY[[[',
        'H\\QMPMNNMOLQLWMYNZP[T[VZWYXWXRWPUOSPRRRWSYTZV[Y[',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RR\\T]U_TaRbOb',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RR\\T]U_TaRbOb',
        'JZLFXF RR[RF RR[T[T`',
        'KYMMWM RRMR[ RR[T[T`',
        15,
        'JZR[Rb RMMR[WM',
        'I[RQR[ RKFRQYF RNUVU',
        'JZR[Rb RMMR[WM RN]V]',
        'H\\KFY[ RYFK[ RX[Z[Z`',
        'IZL[WM RLMW[ RV[X[X`',
        'D]FFRF RXFX[ RLFL[Z[Z`',
        'G\\RMIM RWMW[ RNMN[Y[Y`',
        'H\\WFW[ RLFLNMPNQPRWR RW[Y[Y`',
        'J\\VMV[ RNMNROTQUVU RV[X[X`',
        'H\\WFW[ RLFLNMPNQPRWR RRNRV',
        'J\\VMV[ RNMNROTQUVU RRQRY',
        'G]L[LF RL[ RLPRPUQWSXVX[',
        'H[M[MF RV[VPUNSMPMNNMO',
        '@^WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGXIYKZOJQGQEPDOCMCK',
        'E[VZT[P[NZMXMPNNPMTMVNWPWRMTKTISHQHO',
        '@^WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGXIYKZOJQGQEPDOCMCK RR[P]O_PaRbTb',
        'E[VZT[P[NZMXMPNNPMTMVNWPWRMTKTISHQHO RR[P]O_PaRbTb',
        8,
        'BbOOF[ RR[RF RRRFF R^[UO R^FRR RN>O@QASAU@V>',
        'F^QTJ[ RRUJM RRMR[ RZ[ST RZMRU RNEOGQHSHUGVE',
        'G\\L[LF RX[OO RXFLR RX[X_WaUbSb',
        'IZNMN[ RPSV[ RVMNU RV[V_UaSbQb',
        'F\\W[WFTFQGOINLLXKZI[H[ RW[Z[Tb',
        'I[V[VMSMQNPPOXNZL[ RV[Y[Sb',
        'G]L[LF RLPXP RX[XF RX[X_WaUbSb',
        'H[MTVT RMMM[ RVMV[ RV[V_UaSbQb',
        'G]L[LF RLPXP RX[XF RX[[[Ub',
        'H[MTVT RMMM[ RVMV[ RV[Y[Sb',
        'H\\WFW[ RLFLNMPNQPRWR RW[U[U`',
        'J\\VMV[ RNMNROTQUVU RV[T[T`',
        'F^K[KFRUYFY[ RY[\\[Vb',
        'G]L[LMRXXMX[ RX[[[Ub',
        8,
        30,
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE',
        'I[MUWU RK[RFY[ RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'F`JURU RRPYP RH[OF\\F RRFR[\\[',
        'D`INKMOMQNRP R[ZY[U[SZRXRPSNUMYM[N\\P\\RRSKSITHVHXIZK[O[QZRX',
        'H[MPTP RW[M[MFWF RN>O@QASAU@V>',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNEOGQHSHUGVE',
        'F^MHNGQFSFVGXIYKZOZRYVXXVZS[Q[NZLXKVJRZP',
        33,
        'F^MHNGQFSFVGXIYKZOZRYVXXVZS[Q[NZLXKVJRZP RNBOCNDMCNBND RVBWCVDUCVBVD',
        'I[NNPMTMVNWPWXVZT[P[NZMXMVWT RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'BbOOF[ RR[RF RRRFF R^[UO R^FRR RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'F^QTJ[ RRUJM RRMR[ RZ[ST RZMRU RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'I]PPTP RMGOFTFVGWHXJXLWNVOTPWQXRYTYWXYWZU[O[MZ RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'K[RTTT RNNPMTMVNWPWQVSTTVUWWWXVZT[P[NZ RNFOGNHMGNFNH RVFWGVHUGVFVH',
        2,
        'JZMMVMOVRVTWUXVZV^U`TaRbObMa',
        'G]LFL[XFX[ RM@W@',
        'H\\MMM[WMW[ RMGWG',
        'G]LFL[XFX[ RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'H\\MMM[WMW[ RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNFOGNHMGNFNH RVFWGVHUGVFVH',
        32,
        37,
        'G]KPYP RPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'H[LTWT RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'I^ZPPP RMYNZQ[S[VZXXYVZRZOYKXIVGSFQFNGMH RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'J\\XTQT RNZP[T[VZWYXWXQWOVNTMPMNN RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'G[KFRT RYFPXNZL[K[ RM@W@',
        'JZMMR[ RWMR[P`OaMb RMGWG',
        'G[KFRT RYFPXNZL[K[ RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'JZMMR[ RWMR[P`OaMb RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'G[KFRT RYFPXNZL[K[ RQ>NA RX>UA',
        'JZMMR[ RWMR[P`OaMb RQENH RXEUH',
        'H\\WFW[ RLFLNMPNQPRWR RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'J\\VMV[ RNMNROTQUVU RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'HZM[MFXF RM[O[O`',
        'JYO[OMWM RO[Q[Q`',
        'Da\\F\\[ RIFI[O[RZTXUVUSTQROONIN RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'F^YMY[ RKMK[P[RZSXSURSPRKR RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'HZWFMFM[Q[Q_PaNbLb RJQRQ',
        'JYWMOMO[S[S_RaPbNb RLTTT',
        'H\\KFY[ RYFK[ RX[X_WaUbSb',
        'IZL[WM RLMW[ RV[V_UaSbQb',
        'H\\KFY[ RYFK[ RNPVP',
        'IZL[WM RLMW[ RNTVT',
        'G\\WFW[Q[NZLXKVKSLQNOQNWN',
        'J[VMV[Q[OZNXNUOSQRVR',
        'B_RXSZU[X[ZZ[X[M RRFRXQZO[L[IZGXFVFSGQIOLNRN',
        'E]RXSZU[V[XZYXYQ RRMRXQZO[M[KZJXJUKSMRRR',
        'IePPTP RMGOFTFVGWHXJXLWNVOTPVQWRXTXXYZ[[^[`ZaXaM',
        'KbRTTT RNNPMTMVNWPWQVSTTVUWWWXXZZ[[[]Z^X^Q',
        'I\\PPTP RMGOFTFVGWHXJXLWNVOTPVQWRXTX[Z[Z`',
        'K[RTTT RNNPMTMVNWPWQVSTTVUWWW[Y[Y`',
        'FdH[I[KZLXNLOIQGTFWFWXXZZ[][_Z`X`M',
        'IaL[NZOXPPQNSMVMVXWZY[Z[\\Z]X]Q',
        'CaH[HF RHPTP RTFTXUZW[Z[\\Z]X]M',
        'F^KTTT RKMK[ RTMTXUZW[X[ZZ[X[R',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR',
        'HZUNSMPMNNMOLQLWMYNZP[T[VZVUSU',
        'J_LFXF RRFRXSZU[X[ZZ[X[M',
        'K]MMWM RRMRXSZU[V[XZYXYS',
        'G[PPTP RWGUFPFNGMHLJLLMNNOPPMQLRKTKWLYMZO[U[WZ',
        35,
        'F\\W[WFTFQGOINLLXKZI[H[ RW[W_VaTbRb',
        'I[V[VMSMQNPPOXNZL[ RV[V_UaSbQb',
        'BaP[^F RD[E[GZHXJLKIMGPF^[',
        'E^[MO[ RH[JZKXLPMNOM[[',
        'E_\\FUO\\[ RJ[JFRFTGUHVJVMUOTPRQJQ',
        'F^KMKb R[MUT[[ RKNMMQMSNTOUQUWTYSZQ[M[KZ',
        'DaOQH[ RTFT[^[ R[QLQJPIOHMHJIHJGLF^F',
        'D`H[MU RRPRMKMINHPHRITKURU R[ZY[U[SZRXRPSNUMYM[N\\P\\RRT',
        'G]Z]X\\VZSWQVOV RP[NZLXKTKMLINGPFTFVGXIYMYTXXVZT[P[',
        'I\\WMWb RWZU[Q[OZNYMWMQNOONQMUMWN',
        'F^IFN[RLV[[F',
        21,
        'G\\L[LF RX[OO RXFLR RXKRG',
        'IZNMN[ RPSV[ RVMNU RWQQM',
        'FgW[WFTFQGOINLLXKZI[H[ RWM]M`NbPcSc\\b_`a]b[b',
        'IcV[VMSMQNPPOXNZL[ RVT[T]U^V_X_[^^\\a[b',
        'GhL[LF RLPXP RX[XF RXM^MaNcPdSd\\c_aa^b\\b',
        'HcMTVT RMMM[ RVMV[ RVT[T]U^V_X_[^^\\a[b',
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        'JZNXVX RM[RMW[',
        'H\\LXRX RRTWT RRMR[Y[ RYMPMK[',
        'D`[ZY[U[SZRX RINKMOMQNRPRXQZO[K[IZHXHVRUYU[T\\R\\P[NYMUMSNRP',
        'I[STVUWWWXVZT[N[NMSMUNVPVQUSSTNT RKWQW',
        17,
        'J[SMOMO[S[UZVYWVWRVOUNSM',
        'J[SMOMO[S[UZVYWVWRVOUNSM RLTRT',
        'JYOTTT RVMOMO[V[',
        'J[TTVSWQWPVNTMPMNN RRTTTVUWWWXVZT[P[NZ',
        'MWRMR[ RRbSaR`QaRbR`',
        'LYTMTWSYRZP[O[',
        31,
        'JYOMO[V[ RLVRR',
        'G]L[LMRXXMX[',
        'I\\W[WMN[NM',
        19,
        'J\\NNPMTMVNWOXQXWWYVZT[P[NZ',
        'G]YSYVXXWYUZOZMYLXKVKSLQMPOOUOWPXQYS',
        'G]XYYWYSXQWPUOOOMPLQKSKWLY',
        'G]YNK[ RYSYVXXWYUZOZMYLXKVKSLQMPOOUOWPXQYS',
        'DaINKMOMQNRPRXQZO[K[IZHXHVRT RRWSYTZV[Y[[Z\\Y]W]Q\\O[NYMVMTNSORQ',
        'G]OMNNMPNRPS RTSVRWPVNUM RPSTSVTWVWXVZT[P[NZMXMVNTPS',
        'I\\XTXQWOVNTMQMONNOMQMT',
        'H[LTLWMYNZP[S[UZVYWWWT',
        'I[N[NMTMVNWPWRVTTUNU',
        'I[RUM[ RV[VMPMNNMPMRNTPUVU',
        'I[RSMM RVMV[P[NZMXMVNTPSVS',
        'KYMMWM RRMR[',
        'H[MMMXNZP[S[UZVXVM',
        'G]KPYP RKYVYXXYVYSXQWP',
        '@]KPYP RKYVYXXYVYSXQWP REWFXEYDXEWEY REOFPEQDPEOEQ',
        'G]KKYK RWKXLYNYQXSVTKT RVTXUYWYZX\\V]K]',
        20,
        21,
        'IZLMWML[W[',
        'JZNMVMRRSRUSVUVXUZS[P[NZ',
        'H\\XNUMPMNNMOLQLSMUNVPWTXVYWZX\\X^W`VaTbObLa RRTR\\',
        'JZW[PROPPNRMTNUPTRM[',
        'JYO[OMWM',
        'JZM[RMW[',
        'H[M[MMVMV[',
        'I[N[NMTMVNWPWRVTTUNU',
        'I[RMR[ RLMMNMRNTPUTUVTWRWNXM',
        'I[V[VMSMQNPPOXNZL[',
        'JZNKVK RMNR@WN',
        'H\\LKRK RRGWG RR@RNYN RY@P@KN',
        'I[SGVHWJWKVMTNNNN@S@UAVCVDUFSGNG',
        'I[SGVHWJWKVMTNNNN@S@UAVCVDUFSGNG RKGQG',
        'J[S@O@ONSNUMVLWIWEVBUAS@',
        'JYOGTG RV@O@ONVN',
        'KZUGPG RN@U@UNNN',
        'HZUAS@P@NAMBLDLJMLNMPNTNVMVHSH',
        'H[MGVG RM@MN RV@VN',
        'MWRNR@ RUNON RU@O@',
        'LYT@TJSLRMPNON',
        'IZN@NN RPFVN RV@NH',
        'JYO@ONVN',
        'G]LNL@RKX@XN',
        'H[MNM@VNV@',
        'I\\WNW@NNN@',
        'H[PNNMMLLJLDMBNAP@S@UAVBWDWJVLUMSNPN',
        'G]O@NAMCNEPF RTFVEWCVAU@ RPFTFVGWIWKVMTNPNNMMKMINGPF',
        'I[NNN@T@VAWCWEVGTHNH',
        'I[RHWN RNNN@T@VAWCWEVGTHNH',
        'KYM@W@ RR@RN',
        'H[M@MKNMPNSNUMVKV@',
        'G]J@NNRDVNZ@',
        'KZOEQDSDUEVGVN RVMTNQNOMNKOIQHVH',
        'JYNDNKOMQNSNUM RNEPDSDUEVGUISJNJ',
        'H]WDUKTMRNPNNMMKMGNEPDRDTEVMWN',
        'H\\XMVNUNSMRK RLDODQERHRKQMONNNLMKKKJVJXIYGXEVDUDSERH',
        'KYO@ON ROMQNSNUMVKVGUESDQDOE',
        'KYU@UN RUESDQDOENGNKOMQNSNUM',
        'LYVMTNRNPMOKOGPERDSDUEVGVHOI',
        'LYOEQDSDUEVGVKUMSNRNPMOKOJVI',
        'LXPIRI RUETDPDOEOHPIOJOMPNTNUM',
        'LXRITI ROEPDTDUEUHTIUJUMTNPNOM',
        'KYUDUPTRRSOS RUESDQDOENGNKOMQNSNUM',
        'NVRDRN RRUSTRSQTRURS',
        'IZO@ON RUNQH RUDOJ',
        'G]KNKD RKEMDODQERGRN RRGSEUDVDXEYGYN',
        'KZODON ROEQDSDUEVGVPURSSRS',
        'KYQNOMNKNGOEQDSDUEVGVKUMSNQN',
        'LYOEQDSDUEVGVKUMSNQNOM',
        'KYNINGOEQDSDUEVGVI',
        'KYNINKOMQNSNUMVKVI',
        'KYOSOD ROEQDSDUEVGVKUMSNQNOM',
        'NXPDVD RR@RKSMUNVN',
        'KYUDUN RNDNKOMQNSNUM',
        'I[MFWF RMMTMVLWJWHVF',
        'G]YDYN RYMWNUNSMRKRD RRKQMONNNLMKKKD',
        'LXNDRNVD',
        'LXVNPGPEQDSDTETGNN',
        'KYSFRF RNSOQOCPAR@S@UAVCUESFUGVIVKUMSNQNOM',
        'KXRMRS RMDOERMVD',
        'KYSDQDOENGNKOMQNSNUMVKVGUESDPCOBOAP@U@',
        'I[MDLFLJMLNMPNTNVMWLXJXGWEUDSERGRS',
        'LXVDNS RNDPETRVS',
        'NVRWRa RRPQQRRSQRPRR',
        'LWPWPa RPZQXSWUW',
        'KYUWUa RNWN^O`QaSaU`',
        'LXNWRaVW',
        'KYSYRY RNfOdOVPTRSSSUTVVUXSYUZV\\V^U`SaQaO`',
        'KXR`Rf RMWOXR`VW',
        'KYOfOZPXRWSWUXVZV^U`SaQaO`',
        'I[MWLYL]M_N`PaTaV`W_X]XZWXUWSXRZRf',
        'LXVWNf RNWPXTeVf',
        'D`IMIXJZL[O[QZRX R[ZY[U[SZRXRPSNUMYM[N\\P\\RRT',
        'H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ RIHJGLFPHRGSF',
        'I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RQHRGTFXHZG[F',
        'MYOMWM RR[RISGUFWF RMTNSPRTTVSWR',
        'D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ RMTNSPRTTVSWR',
        'I\\NMN[ RNOONQMTMVNWPW[ RMTNSPRTTVSWR',
        'H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RI`J_L^P`R_S^',
        'KXP[PM RPQQORNTMVM RLTMSORSTUSVR',
        'KXM[S[ RVMTMRNQOPRP[ RLTMSORSTUSVR',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RNTOSQRUTWSXR',
        'MYOMWM RRFRXSZU[W[ RMSNRPQTSVRWQ',
        'IZLMWML[W[ RMTNSPRTTVSWR',
        'H[M[MJNHOGQFTFVG RMNOMSMUNVOWQWWVYUZS[O[MZ',
        'H[MGVG RM@MN RV@VN',
        'JZMMVMOURUTVUWVYV^U`TaRbPbNaM_M^N\\P[V[',
        'MlOMWM RRFRXSZU[W[ R^[^F Rg[gPfNdMaM_N^O RiC]`',
        'MWR[RM RU[O[ RUMOM ROTUT',
        'MXRMRXSZU[ ROTUT',
        'H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RHT\\T',
        'H[MMMXNZP[S[UZVXVM RHT\\T',
        'I\\XMUMUPWRXTXWWYVZT[Q[OZNYMWMTNRPPPMMM RHU\\U',
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        'I[MUWU RK[RFY[ RR`TaUcTeRfPeOcPaR`',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RR`TaUcTeRfPeOcPaR`',
        'G\\SPVQWRXTXWWYVZT[L[LFSFUGVHWJWLVNUOSPLP RR?Q@RAS@R?RA',
        'H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ RN?M@NAO@N?NA',
        'G\\SPVQWRXTXWWYVZT[L[LFSFUGVHWJWLVNUOSPLP RRbSaR`QaRbR`',
        'H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ RRbSaR`QaRbR`',
        'G\\SPVQWRXTXWWYVZT[L[LFSFUGVHWJWLVNUOSPLP RWaMa',
        'H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ RWaMa',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RR\\T]U_TaRbOb RT>QA',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RR\\T]U_TaRbOb RTEQH',
        'G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RR?Q@RAS@R?RA',
        'I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RV?U@VAW@V?VA',
        'G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RRbSaR`QaRbR`',
        'I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RSbTaS`RaSbS`',
        'G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RWaMa',
        'I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RXaNa',
        'G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RQ\\S]T_SaQbNb',
        'I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RS\\U]V_UaSbPb',
        'G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RVcR`Nc',
        'I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RWcS`Oc',
        'H[MPTP RW[M[MFWF RM@W@ RP9S<',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RMGWG RP>SA',
        'H[MPTP RW[M[MFWF RM@W@ RT9Q<',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RMGWG RT>QA',
        'H[MPTP RW[M[MFWF RVcR`Nc',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RVcR`Nc',
        'H[MPTP RW[M[MFWF RW`VaTbP`NaMb',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RW`VaTbP`NaMb',
        'H[MPTP RW[M[MFWF RR\\T]U_TaRbOb RN>O@QASAU@V>',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RR\\T]U_TaRbOb RNEOGQHSHUGVE',
        'HZTPMP RM[MFWF RR?Q@RAS@R?RA',
        'MYOMWM RR[RISGUFWF RT?S@TAU@T?TA',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RM@W@',
        'I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RMGWG',
        'G]L[LF RLPXP RX[XF RR?Q@RAS@R?RA',
        'H[M[MF RV[VPUNSMPMNNMO RM?L@MAN@M?MA',
        'G]L[LF RLPXP RX[XF RRbSaR`QaRbR`',
        'H[M[MF RV[VPUNSMPMNNMO RRbSaR`QaRbR`',
        'G]L[LF RLPXP RX[XF RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'H[M[MF RV[VPUNSMPMNNMO RI?J@IAH@I?IA RQ?R@QAP@Q?QA',
        'G]L[LF RLPXP RX[XF RL\\N]O_NaLbIb',
        'H[M[MF RV[VPUNSMPMNNMO RM\\O]P_OaMbJb',
        'G]L[LF RLPXP RX[XF RV`UbScQcObN`',
        'H[M[MF RV[VPUNSMPMNNMO RV`UbScQcObN`',
        'MWR[RF RW`VaTbP`NaMb',
        'MWR[RM RRFQGRHSGRFRH RW`VaTbP`NaMb',
        'MWR[RF RN?O@NAM@N?NA RV?W@VAU@V?VA RT9Q<',
        'MWR[RM RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA',
        'G\\L[LF RX[OO RXFLR RT>QA',
        'IZN[NF RPSV[ RVMNU RPAMD',
        'G\\L[LF RX[OO RXFLR RRbSaR`QaRbR`',
        'IZN[NF RPSV[ RVMNU RRbSaR`QaRbR`',
        'G\\L[LF RX[OO RXFLR RWaMa',
        'IZN[NF RPSV[ RVMNU RWaMa',
        'HYW[M[MF RRbSaR`QaRbR`',
        'MXU[SZRXRF RSbTaS`RaSbS`',
        'HYW[M[MF RH@R@ RRbSaR`QaRbR`',
        'MXU[SZRXRF RM@W@ RSbTaS`RaSbS`',
        'HYW[M[MF RWaMa',
        'MXU[SZRXRF RXaNa',
        'HYW[M[MF RVcR`Nc',
        'MXU[SZRXRF RWcS`Oc',
        'F^K[KFRUYFY[ RT>QA',
        'D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ RTEQH',
        'F^K[KFRUYFY[ RR?Q@RAS@R?RA',
        'D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ RRFQGRHSGRFRH',
        'F^K[KFRUYFY[ RRbSaR`QaRbR`',
        'D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ RRbSaR`QaRbR`',
        'G]L[LFX[XF RR?Q@RAS@R?RA',
        'I\\NMN[ RNOONQMTMVNWPW[ RRFQGRHSGRFRH',
        'G]L[LFX[XF RRbSaR`QaRbR`',
        'I\\NMN[ RNOONQMTMVNWPW[ RRbSaR`QaRbR`',
        'G]L[LFX[XF RWaMa',
        'I\\NMN[ RNOONQMTMVNWPW[ RWaMa',
        'G]L[LFX[XF RVcR`Nc',
        'I\\NMN[ RNOONQMTMVNWPW[ RVcR`Nc',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RMAN@P?TAV@W? RT9Q<',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMHNGPFTHVGWF RT>QA',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RMAN@P?TAV@W? RN:O;N<M;N:N< RV:W;V<U;V:V<',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMHNGPFTHVGWF RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RM@W@ RP9S<',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMGWG RP>SA',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RM@W@ RT9Q<',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMGWG RT>QA',
        'G\\L[LFTFVGWHXJXMWOVPTQLQ RT>QA',
        'H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RTEQH',
        'G\\L[LFTFVGWHXJXMWOVPTQLQ RR?Q@RAS@R?RA',
        'H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RRFQGRHSGRFRH',
        'G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RR?Q@RAS@R?RA',
        'KXP[PM RPQQORNTMVM RSFRGSHTGSFSH',
        'G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RRbSaR`QaRbR`',
        'KXP[PM RPQQORNTMVM RPbQaP`OaPbP`',
        'G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RM@W@ RRbSaR`QaRbR`',
        'KXP[PM RPQQORNTMVM RNGXG RPbQaP`OaPbP`',
        'G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RWaMa',
        'KXP[PM RPQQORNTMVM RUaKa',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RR?Q@RAS@R?RA',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RRFQGRHSGRFRH',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RRbSaR`QaRbR`',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RRbSaR`QaRbR`',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RU>RA RM>N?M@L?M>M@',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RUERH RMENFMGLFMEMG',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RN>RAV> RR:Q;R<S;R:R<',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RNERHVE RR?Q@RAS@R?RA',
        'H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RR?Q@RAS@R?RA RRbSaR`QaRbR`',
        'J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RRFQGRHSGRFRH RRbSaR`QaRbR`',
        'JZLFXF RR[RF RR?Q@RAS@R?RA',
        'MYOMWM RRFRXSZU[W[ RR?Q@RAS@R?RA',
        'JZLFXF RR[RF RRbSaR`QaRbR`',
        'MYOMWM RRFRXSZU[W[ RTbUaT`SaTbT`',
        'JZLFXF RR[RF RWaMa',
        'MYOMWM RRFRXSZU[W[ RYaOa',
        'JZLFXF RR[RF RVcR`Nc',
        'MYOMWM RRFRXSZU[W[ RXcT`Pc',
        'G]LFLWMYNZP[T[VZWYXWXF RVbUaV`WaVbV` RNbMaN`OaNbN`',
        'H[VMV[ RMMMXNZP[S[UZVY RVbUaV`WaVbV` RNbMaN`OaNbN`',
        'G]LFLWMYNZP[T[VZWYXWXF RW`VaTbP`NaMb',
        'H[VMV[ RMMMXNZP[S[UZVY RW`VaTbP`NaMb',
        'G]LFLWMYNZP[T[VZWYXWXF RVcR`Nc',
        'H[VMV[ RMMMXNZP[S[UZVY RVcR`Nc',
        'G]LFLWMYNZP[T[VZWYXWXF RMAN@P?TAV@W? RT9Q<',
        'H[VMV[ RMMMXNZP[S[UZVY RMHNGPFTHVGWF RT>QA',
        'G]LFLWMYNZP[T[VZWYXWXF RM@W@ RN:O;N<M;N:N< RV:W;V<U;V:V<',
        'H[VMV[ RMMMXNZP[S[UZVY RMGWG RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'I[KFR[YF RMAN@P?TAV@W?',
        'JZMMR[WM RMHNGPFTHVGWF',
        'I[KFR[YF RRbSaR`QaRbR`',
        'JZMMR[WM RRbSaR`QaRbR`',
        'F^IFN[RLV[[F RP>SA',
        'G]JMN[RQV[ZM RPESH',
        'F^IFN[RLV[[F RT>QA',
        'G]JMN[RQV[ZM RTEQH',
        'F^IFN[RLV[[F RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'G]JMN[RQV[ZM RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'F^IFN[RLV[[F RR?Q@RAS@R?RA',
        'G]JMN[RQV[ZM RRFQGRHSGRFRH',
        'F^IFN[RLV[[F RRbSaR`QaRbR`',
        'G]JMN[RQV[ZM RRbSaR`QaRbR`',
        'H\\KFY[ RYFK[ RR?Q@RAS@R?RA',
        'IZL[WM RLMW[ RRFQGRHSGRFRH',
        'H\\KFY[ RYFK[ RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'IZL[WM RLMW[ RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'I[RQR[ RKFRQYF RR?Q@RAS@R?RA',
        'JZMMR[ RWMR[P`OaMb RRFQGRHSGRFRH',
        'H\\KFYFK[Y[ RNAR>VA',
        'IZLMWML[W[ RNHREVH',
        'H\\KFYFK[Y[ RRbSaR`QaRbR`',
        'IZLMWML[W[ RRbSaR`QaRbR`',
        'H\\KFYFK[Y[ RWaMa',
        'IZLMWML[W[ RWaMa',
        'H[M[MF RV[VPUNSMPMNNMO RWaMa',
        'MYOMWM RRFRXSZU[W[ RN?O@NAM@N?NA RV?W@VAU@V?VA',
        'G]JMN[RQV[ZM RRHPGOEPCRBTCUETGRH',
        'JZMMR[ RWMR[P`OaMb RRHPGOEPCRBTCUETGRH',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RWJYIZGYEWD',
        'MYR[RISGUFWF RT?S@TAU@T?TA',
        'MYR[RISGUFWF ROSUO',
        'MYR[RISGUFWF ROLUL',
        'E^J[JLKIMGPFZFSNVNXOYPZRZWYYXZV[R[PZOY',
        'H[SMPMNNMOLQLWMYNZP[S[UZVYWWWQVOUNSMPLNKMINGPFTFVG',
        'I[MUWU RK[RFY[ RRbSaR`QaRbR`',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RRbSaR`QaRbR`',
        'I[MUWU RK[RFY[ RRAT?U=T;R:P:',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RRHTFUDTBRAPA',
        'I[MUWU RK[RFY[ RU>X; RNAR>VA',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RUEXB RNHREVH',
        'I[MUWU RK[RFY[ RO>L; RNAR>VA',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR ROELB RNHREVH',
        'I[MUWU RK[RFY[ RNAR>VA RXAZ?[=Z;X:V:',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNHREVH RXHZF[DZBXAVA',
        'I[MUWU RK[RFY[ RNAR>VA RM<N;P:T<V;W:',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNHREVH RMAN@P?TAV@W?',
        'I[MUWU RK[RFY[ RNAR>VA RRbSaR`QaRbR`',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNHREVH RRbSaR`QaRbR`',
        'I[MUWU RK[RFY[ RN>O@QASAU@V> RT9Q<',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE RT>QA',
        'I[MUWU RK[RFY[ RN>O@QASAU@V> RP9S<',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE RP>SA',
        'I[MUWU RK[RFY[ RN>O@QASAU@V> RP>R<S:R8P7N7',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE RPERCSAR?P>N>',
        'I[MUWU RK[RFY[ RN>O@QASAU@V> RM<N;P:T<V;W:',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE RMAN@P?TAV@W?',
        'I[MUWU RK[RFY[ RN>O@QASAU@V> RRbSaR`QaRbR`',
        'I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE RRbSaR`QaRbR`',
        'H[MPTP RW[M[MFWF RRbSaR`QaRbR`',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RRbSaR`QaRbR`',
        'H[MPTP RW[M[MFWF RRAT?U=T;R:P:',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RRHTFUDTBRAPA',
        'H[MPTP RW[M[MFWF RMAN@P?TAV@W?',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RMHNGPFTHVGWF',
        'H[MPTP RW[M[MFWF RU>X; RNAR>VA',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RUEXB RNHREVH',
        'H[MPTP RW[M[MFWF RO>L; RNAR>VA',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT ROELB RNHREVH',
        'H[MPTP RW[M[MFWF RNAR>VA RXAZ?[=Z;X:V:',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNHREVH RXHZF[DZBXAVA',
        'H[MPTP RW[M[MFWF RNAR>VA RM<N;P:T<V;W:',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNHREVH RMAN@P?TAV@W?',
        'H[MPTP RW[M[MFWF RNAR>VA RRbSaR`QaRbR`',
        'I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNHREVH RRbSaR`QaRbR`',
        'MWR[RF RRAT?U=T;R:P:',
        'MWR[RM RRHTFUDTBRAPA',
        'MWR[RF RRbSaR`QaRbR`',
        'MWR[RM RRFQGRHSGRFRH RRbSaR`QaRbR`',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RRbSaR`QaRbR`',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RRbSaR`QaRbR`',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RRAT?U=T;R:P:',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RRHTFUDTBRAPA',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RU>X; RNAR>VA',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUEXB RNHREVH',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RO>L; RNAR>VA',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ ROELB RNHREVH',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RNAR>VA RXAZ?[=Z;X:V:',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNHREVH RXHZF[DZBXAVA',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RNAR>VA RM<N;P:T<V;W:',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNHREVH RMAN@P?TAV@W?',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RNAR>VA RRbSaR`QaRbR`',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNHREVH RRbSaR`QaRbR`',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA RT>QA',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH RTEQH',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA RP>SA',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH RPESH',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA RRAT?U=T;R:P:',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH RRHTFUDTBRAPA',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA RWAVBTCPANBMC',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH RWHVITJPHNIMJ',
        'G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA RRbSaR`QaRbR`',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH RRbSaR`QaRbR`',
        'G]LFLWMYNZP[T[VZWYXWXF RRbSaR`QaRbR`',
        'H[VMV[ RMMMXNZP[S[UZVY RRbSaR`QaRbR`',
        'G]LFLWMYNZP[T[VZWYXWXF RRAT?U=T;R:P:',
        'H[VMV[ RMMMXNZP[S[UZVY RRHTFUDTBRAPA',
        'G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@ RT>QA',
        'H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG RTEQH',
        'G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@ RP>SA',
        'H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG RPESH',
        'G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@ RRAT?U=T;R:P:',
        'H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG RRHTFUDTBRAPA',
        'G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@ RWAVBTCPANBMC',
        'H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG RWHVITJPHNIMJ',
        'G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@ RRbSaR`QaRbR`',
        'H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG RRbSaR`QaRbR`',
        'I[RQR[ RKFRQYF RP>SA',
        'JZMMR[ RWMR[P`OaMb RPESH',
        'I[RQR[ RKFRQYF RRbSaR`QaRbR`',
        'JZMMR[ RWMR[P`OaMb RVbWaV`UaVbV`',
        'I[RQR[ RKFRQYF RRAT?U=T;R:P:',
        'JZMMR[ RWMR[P`OaMb RRHTFUDTBRAPA',
        'I[RQR[ RKFRQYF RMAN@P?TAV@W?',
        'JZMMR[ RWMR[P`OaMb RMHNGPFTHVGWF',
        'E\\PFP[ RJFJ[Z[',
        'J[MMWM ROFOXPZR[ RX[VZUXUF',
        'G]QFOGMJLMLWMYNZP[T[VZXXYVYTXPVMUL',
        'H[QMONNOMQMWNYOZQ[S[UZVYWWWUVSURSQ',
        'G[KFRT RYFRTPXOZM[KZJXKVMUOVPX',
        'JZMMR[ RWMR[Q_PaNbLaK_L]N\\P]Q_',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQHRHSGSE',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQEQGRHSH',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEWH RMHNHOGOE',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEWH RMEMGNHOH',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RXEUH RMHNHOGOE',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RXEUH RMEMGNHOH',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQHRHSGSE RMAN@P?TAV@W?',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQEQGRHSH RMAN@P?TAV@W?',
        'G[MUWU RK[RFY[ RJHKHLGLE',
        'G[MUWU RK[RFY[ RJEJGKHLH',
        '?[MUWU RK[RFY[ RIELH RBHCHDGDE',
        '?[MUWU RK[RFY[ RIELH RBEBGCHDH',
        '?[MUWU RK[RFY[ RMEJH RBHCHDGDE',
        '?[MUWU RK[RFY[ RMEJH RBEBGCHDH',
        'D[MUWU RK[RFY[ RFAG@I?MAO@P? RJHKHLGLE',
        'D[MUWU RK[RFY[ RFAG@I?MAO@P? RJEJGKHLH',
        'IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RQHRHSGSE',
        'IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RQEQGRHSH',
        'IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RTEWH RMHNHOGOE',
        'IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RTEWH RMEMGNHOH',
        'IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RXEUH RMHNHOGOE',
        'IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RXEUH RMEMGNHOH',
        23,
        23,
        'B[MPTP RW[M[MFWF REHFHGGGE',
        'B[MPTP RW[M[MFWF REEEGFHGH',
        ':[MPTP RW[M[MFWF RDEGH R=H>H?G?E',
        ':[MPTP RW[M[MFWF RDEGH R=E=G>H?H',
        ':[MPTP RW[M[MFWF RHEEH R=H>H?G?E',
        ':[MPTP RW[M[MFWF RHEEH R=E=G>H?H',
        23,
        23,
        'I\\NMN[ RNOONQMTMVNWPWb RQHRHSGSE',
        'I\\NMN[ RNOONQMTMVNWPWb RQEQGRHSH',
        'I\\NMN[ RNOONQMTMVNWPWb RTEWH RMHNHOGOE',
        'I\\NMN[ RNOONQMTMVNWPWb RTEWH RMEMGNHOH',
        'I\\NMN[ RNOONQMTMVNWPWb RXEUH RMHNHOGOE',
        'I\\NMN[ RNOONQMTMVNWPWb RXEUH RMEMGNHOH',
        'I\\NMN[ RNOONQMTMVNWPWb RQHRHSGSE RMAN@P?TAV@W?',
        'I\\NMN[ RNOONQMTMVNWPWb RQEQGRHSH RMAN@P?TAV@W?',
        'A]L[LF RLPXP RX[XF RDHEHFGFE',
        'A]L[LF RLPXP RX[XF RDEDGEHFH',
        '9]L[LF RLPXP RX[XF RCEFH R<H=H>G>E',
        '9]L[LF RLPXP RX[XF RCEFH R<E<G=H>H',
        '9]L[LF RLPXP RX[XF RGEDH R<H=H>G>E',
        '9]L[LF RLPXP RX[XF RGEDH R<E<G=H>H',
        '>]L[LF RLPXP RX[XF R@AA@C?GAI@J? RDHEHFGFE',
        '>]L[LF RLPXP RX[XF R@AA@C?GAI@J? RDEDGEHFH',
        'MXRMRXSZU[ RQHRHSGSE',
        'MXRMRXSZU[ RQEQGRHSH',
        'MXRMRXSZU[ RTEWH RMHNHOGOE',
        'MXRMRXSZU[ RTEWH RMEMGNHOH',
        'MXRMRXSZU[ RXEUH RMHNHOGOE',
        'MXRMRXSZU[ RXEUH RMEMGNHOH',
        'MXRMRXSZU[ RQHRHSGSE RMAN@P?TAV@W?',
        'MXRMRXSZU[ RQEQGRHSH RMAN@P?TAV@W?',
        'GWR[RF RJHKHLGLE',
        'GWR[RF RJEJGKHLH',
        '?WR[RF RIELH RBHCHDGDE',
        '?WR[RF RIELH RBEBGCHDH',
        '?WR[RF RMEJH RBHCHDGDE',
        '?WR[RF RMEJH RBEBGCHDH',
        'DWR[RF RFAG@I?MAO@P? RJHKHLGLE',
        'DWR[RF RFAG@I?MAO@P? RJEJGKHLH',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RQHRHSGSE',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RQEQGRHSH',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RTEWH RMHNHOGOE',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RTEWH RMEMGNHOH',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RXEUH RMHNHOGOE',
        'H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RXEUH RMEMGNHOH',
        23,
        23,
        'B]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF REHFHGGGE',
        'B]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF REEEGFHGH',
        ':]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RDEGH R=H>H?G?E',
        ':]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RDEGH R=E=G>H?H',
        ':]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RHEEH R=H>H?G?E',
        ':]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RHEEH R=E=G>H?H',
        23,
        23,
        'H[MMMXNZP[S[UZVYWWWPVNUM RQHRHSGSE',
        'H[MMMXNZP[S[UZVYWWWPVNUM RQEQGRHSH',
        'H[MMMXNZP[S[UZVYWWWPVNUM RTEWH RMHNHOGOE',
        'H[MMMXNZP[S[UZVYWWWPVNUM RTEWH RMEMGNHOH',
        'H[MMMXNZP[S[UZVYWWWPVNUM RXEUH RMHNHOGOE',
        'H[MMMXNZP[S[UZVYWWWPVNUM RXEUH RMEMGNHOH',
        'H[MMMXNZP[S[UZVYWWWPVNUM RQHRHSGSE RMAN@P?TAV@W?',
        'H[MMMXNZP[S[UZVYWWWPVNUM RQEQGRHSH RMAN@P?TAV@W?',
        23,
        '@[RQR[ RKFRQYF RCECGDHEH',
        23,
        '8[RQR[ RKFRQYF RBEEH R;E;G<H=H',
        23,
        '8[RQR[ RKFRQYF RFECH R;E;G<H=H',
        23,
        '=[RQR[ RKFRQYF R?A@@B?FAH@I? RCECGDHEH',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQHRHSGSE',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQEQGRHSH',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEWH RMHNHOGOE',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEWH RMEMGNHOH',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RXEUH RMHNHOGOE',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RXEUH RMEMGNHOH',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQHRHSGSE RMAN@P?TAV@W?',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQEQGRHSH RMAN@P?TAV@W?',
        '@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RCHDHEGEE',
        '@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RCECGDHEH',
        '8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RBEEH R;H<H=G=E',
        '8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RBEEH R;E;G<H=H',
        '8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH R;H<H=G=E',
        '8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH R;E;G<H=H',
        '=^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ R?A@@B?FAH@I? RCHDHEGEE',
        '=^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ R?A@@B?FAH@I? RCECGDHEH',
        39,
        39,
        40,
        40,
        41,
        41,
        42,
        42,
        29,
        29,
        44,
        44,
        45,
        45,
        23,
        23,
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQHRHSGSE RR`RcSdTd',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQEQGRHSH RR`RcSdTd',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEWH RMHNHOGOE RR`RcSdTd',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEWH RMEMGNHOH RR`RcSdTd',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RXEUH RMHNHOGOE RR`RcSdTd',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RXEUH RMEMGNHOH RR`RcSdTd',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQHRHSGSE RMAN@P?TAV@W? RR`RcSdTd',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQEQGRHSH RMAN@P?TAV@W? RR`RcSdTd',
        'G[MUWU RK[RFY[ RJHKHLGLE RR`RcSdTd',
        'G[MUWU RK[RFY[ RJEJGKHLH RR`RcSdTd',
        '?[MUWU RK[RFY[ RIELH RBHCHDGDE RR`RcSdTd',
        '?[MUWU RK[RFY[ RIELH RBEBGCHDH RR`RcSdTd',
        '?[MUWU RK[RFY[ RMEJH RBHCHDGDE RR`RcSdTd',
        '?[MUWU RK[RFY[ RMEJH RBEBGCHDH RR`RcSdTd',
        'D[MUWU RK[RFY[ RFAG@I?MAO@P? RJHKHLGLE RR`RcSdTd',
        'D[MUWU RK[RFY[ RFAG@I?MAO@P? RJEJGKHLH RR`RcSdTd',
        'I\\NMN[ RNOONQMTMVNWPWb RQHRHSGSE RN`NcOdPd',
        'I\\NMN[ RNOONQMTMVNWPWb RQEQGRHSH RN`NcOdPd',
        'I\\NMN[ RNOONQMTMVNWPWb RTEWH RMHNHOGOE RN`NcOdPd',
        'I\\NMN[ RNOONQMTMVNWPWb RTEWH RMEMGNHOH RN`NcOdPd',
        'I\\NMN[ RNOONQMTMVNWPWb RXEUH RMHNHOGOE RN`NcOdPd',
        'I\\NMN[ RNOONQMTMVNWPWb RXEUH RMEMGNHOH RN`NcOdPd',
        'I\\NMN[ RNOONQMTMVNWPWb RQHRHSGSE RMAN@P?TAV@W? RN`NcOdPd',
        'I\\NMN[ RNOONQMTMVNWPWb RQEQGRHSH RMAN@P?TAV@W? RN`NcOdPd',
        'N]L[LF RLPXP RX[XF RR`RcSdTd',
        'A]L[LF RLPXP RX[XF RDEDGEHFH RR`RcSdTd',
        '9]L[LF RLPXP RX[XF RCEFH R<H=H>G>E RR`RcSdTd',
        '9]L[LF RLPXP RX[XF RCEFH R<E<G=H>H RR`RcSdTd',
        '9]L[LF RLPXP RX[XF RGEDH R<H=H>G>E RR`RcSdTd',
        '9]L[LF RLPXP RX[XF RGEDH R<E<G=H>H RR`RcSdTd',
        '>]L[LF RLPXP RX[XF R@AA@C?GAI@J? RDHEHFGFE RR`RcSdTd',
        '>]L[LF RLPXP RX[XF R@AA@C?GAI@J? RDEDGEHFH RR`RcSdTd',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQHRHSGSE RR`RcSdTd',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQEQGRHSH RR`RcSdTd',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEWH RMHNHOGOE RR`RcSdTd',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEWH RMEMGNHOH RR`RcSdTd',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RXEUH RMHNHOGOE RR`RcSdTd',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RXEUH RMEMGNHOH RR`RcSdTd',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQHRHSGSE RMAN@P?TAV@W? RR`RcSdTd',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQEQGRHSH RMAN@P?TAV@W? RR`RcSdTd',
        '@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RCHDHEGEE RR`RcSdTd',
        '@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RCECGDHEH RR`RcSdTd',
        '8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RBEEH R;H<H=G=E RR`RcSdTd',
        '8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RBEEH R;E;G<H=H RR`RcSdTd',
        '8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH R;H<H=G=E RR`RcSdTd',
        '8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH R;E;G<H=H RR`RcSdTd',
        '=^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ R?A@@B?FAH@I? RCHDHEGEE RR`RcSdTd',
        '=^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ R?A@@B?FAH@I? RCECGDHEH RR`RcSdTd',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RNEOGQHSHUGVE',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RMGWG',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RPESH RR`RcSdTd',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RR`RcSdTd',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEQH RR`RcSdTd',
        23,
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RMHNGPFTHVGWF',
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RMHNGPFTHVGWF RR`RcSdTd',
        30,
        'I[MUWU RK[RFY[ RM@W@',
        'G[MUWU RK[RFY[ RIELH',
        'G[MUWU RK[RFY[ RMEJH',
        'I[MUWU RK[RFY[ RR`RcSdTd',
        'NVQHRHSGSE',
        'NVR`RcSdTd',
        'NVQHRHSGSE',
        'KZMHNGPFTHVGWF',
        'LXMCNBPATCVBWA RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'I\\NMN[ RNOONQMTMVNWPWb RPESH RN`NcOdPd',
        'I\\NMN[ RNOONQMTMVNWPWb RN`NcOdPd',
        'I\\NMN[ RNOONQMTMVNWPWb RTEQH RN`NcOdPd',
        23,
        'I\\NMN[ RNOONQMTMVNWPWb RMHNGPFTHVGWF',
        'I\\NMN[ RNOONQMTMVNWPWb RMHNGPFTHVGWF RN`NcOdPd',
        'B[MPTP RW[M[MFWF RDEGH',
        'B[MPTP RW[M[MFWF RHEEH',
        'A]L[LF RLPXP RX[XF RCEFH',
        'A]L[LF RLPXP RX[XF RGEDH',
        'G]L[LF RLPXP RX[XF RR`RcSdTd',
        'JZTEWH RMHNHOGOE',
        'JZXEUH RMHNHOGOE',
        'NVQHRHSGSE RMAN@P?TAV@W?',
        'MXRMRXSZU[ RNEOGQHSHUGVE',
        'MXRMRXSZU[ RMGWG',
        'MXRMRXSZU[ RNFOGNHMGNFNH RVFWGVHUGVFVH RP>SA',
        'MXRMRXSZU[ RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA',
        23,
        23,
        'MXRMRXSZU[ RMHNGPFTHVGWF',
        'MXRMRXSZU[ RMCNBPATCVBWA RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'MWR[RF RN>O@QASAU@V>',
        'MWR[RF RM@W@',
        'GWR[RF RIELH',
        'GWR[RF RMEJH',
        23,
        'JZTEWH RMEMGNHOH',
        'JZXEUH RMEMGNHOH',
        'NVQEQGRHSH RMAN@P?TAV@W?',
        'H[MMMXNZP[S[UZVYWWWPVNUM RNEOGQHSHUGVE',
        'H[MMMXNZP[S[UZVYWWWPVNUM RMGWG',
        'H[MMMXNZP[S[UZVYWWWPVNUM RNFOGNHMGNFNH RVFWGVHUGVFVH RP>SA',
        'H[MMMXNZP[S[UZVYWWWPVNUM RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA',
        'H\\MbMQNOONQMTMVNWOXQXWWYVZT[Q[OZMX RQHRHSGSE',
        'H\\MbMQNOONQMTMVNWOXQXWWYVZT[Q[OZMX RQEQGRHSH',
        'H[MMMXNZP[S[UZVYWWWPVNUM RMHNGPFTHVGWF',
        'H[MMMXNZP[S[UZVYWWWPVNUM RMCNBPATCVBWA RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'I[RQR[ RKFRQYF RN>O@QASAU@V>',
        'I[RQR[ RKFRQYF RM@W@',
        '@[RQR[ RKFRQYF RBEEH',
        '@[RQR[ RKFRQYF RFECH',
        'A\\L[LFTFVGWHXJXMWOVPTQLQ RDEDGEHFH',
        'LXNFOGNHMGNFNH RVFWGVHUGVFVH RP>SA',
        'LXNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA',
        16,
        23,
        23,
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RPESH RR`RcSdTd',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RR`RcSdTd',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEQH RR`RcSdTd',
        23,
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RMHNGPFTHVGWF',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RMHNGPFTHVGWF RR`RcSdTd',
        'B]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RDEGH',
        'B]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RHEEH',
        '@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RBEEH',
        '@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH',
        'F^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RR`RcSdTd',
        25,
        'NVQEQGRHSH',
        23,
        'F^',
        'LX',
        'F^',
        'LX',
        'NV',
        'OU',
        'PT',
        'H\\',
        'MW',
        'PT',
        'QS',
        24,
        24,
        24,
        24,
        24,
        46,
        46,
        'H\\JRZR',
        'LXVTNT',
        'F^IT[T',
        'F^IT[T',
        'H\\ODOb RUDUb',
        'JZJbZb RJ]Z]',
        'MWQGQFRDSC',
        'MWSFSGRIQJ',
        'MWSZS[R]Q^',
        'MWQFQGRISJ',
        'JZUGUFVDWC RMGMFNDOC',
        'JZOFOGNIMJ RWFWGVIUJ',
        'JZOZO[N]M^ RWZW[V]U^',
        'JZUFUGVIWJ RMFMGNIOJ',
        'I[MMWM RRFRb',
        'I[M[W[ RMMWM RRFRb',
        'E_PQPU RQUQQ RRPRV RSUSQ RTQTU RPTRVTT RPRRPTR RPQRPTQUSTURVPUOSPQ',
        'E_PPPV RQQQU RRQRU RSSUS RSRST ROPUSOV RVSOWOOVS',
        'MWRYSZR[QZRYR[',
        'MaRYSZR[QZRYR[ R\\Y]Z\\[[Z\\Y\\[',
        'MkRYSZR[QZRYR[ R\\Y]Z\\[[Z\\Y\\[ RfYgZf[eZfYf[',
        26,
        24,
        24,
        24,
        24,
        24,
        24,
        24,
        24,
        'FjJ[ZF RMFOGPIOKMLKKJIKGMF RcUeVfXeZc[aZ`XaVcU RYZZXYVWUUVTXUZW[YZ',
        'FvJ[ZF RMFOGPIOKMLKKJIKGMF RcUeVfXeZc[aZ`XaVcU RoUqVrXqZo[mZlXmVoU RYZZXYVWUUVTXUZW[YZ',
        'MWTFQL',
        'JZQFNL RWFTL',
        'G]NFKL RTFQL RZFWL',
        'MWPFSL',
        'JZSFVL RMFPL',
        'G]VFYL RPFSL RJFML',
        'LXVcR`Nc',
        'KYUMOSUY',
        'KYOMUSOY',
        'E_LMXY RXMLY RKRLSKTJSKRKT RRYSZR[QZRYR[ RRKSLRMQLRKRM RYRZSYTXSYRYT',
        'MaRYSZR[QZRYR[ RRSQGRFSGRSRF R\\Y]Z\\[[Z\\Y\\[ R\\S[G\\F]G\\S\\F',
        'I[QFQS RQYRZQ[PZQYQ[ RQYRZQ[PZQYQ[ RMGOFTFVGWIWKVMUNSORPQRQS RMGOFTFVGWIWKVMUNSORPQRQS',
        'E_JGZG',
        'OUb`aa^c\\dYeTfPfKeHdFcCaB`',
        'OUBFCEFCHBKAP@T@YA\\B^CaEbF',
        'E_N_VW RV_R[',
        'CaKRKW RRFRK RYRYW RFUKWPU RH[KWN[ RMIRKWI ROORKUO RTUYW^U RV[YW\\[',
        46,
        1,
        'KYQSVS RVbQbQDVD',
        'KYSSNS RNbSbSDND',
        'ImQYRZQ[PZQYQ[ RMGOFTFVGWIWKVMUNSORPQRQS RcYdZc[bZcYc[ R_GaFfFhGiIiKhMgNeOdPcRcS',
        'IeQYRZQ[PZQYQ[ RMGOFTFVGWIWKVMUNSORPQRQS R`YaZ`[_Z`Y`[ R`S_G`FaG`S`F',
        'MiRYSZR[QZRYR[ RRSQGRFSGRSRF R_Y`Z_[^Z_Y_[ R[G]FbFdGeIeKdMcNaO`P_R_S',
        'KYNMVMPb',
        'G^NMN[ RUMUXVZX[ RJMWMYNZP',
        'H\\NQNU RWPWV RPVPPOQOUPV RQPPPNQMSNUPVQVQP',
        'H\\VQVU RMPMV RTVTPUQUUTV RSPTPVQWSVUTVSVSP',
        'JZR[RV RWXRVMX RURRVOR',
        'MWQZQ[R]S^ RRNQORPSORNRP',
        'OUBFCEFCHBKAP@T@YA\\B^CaEbF Rb`aa^c\\dYeTfPfKeHdFcCaB`',
        'JZRFRK RMIRKWI ROORKUO RRFRK RWIRKMI RUORKOO',
        'JZM^WB RNFOGNHMGNFNH RVYWZV[UZVYV[',
        'E_JSKRNQQRSTVUYTZS',
        '>fB^B]C[EZOZQYRWSYUZ_Za[b]b^',
        'E_JSZS RR[RK RLMXY RXMLY',
        'E_LRMSLTKSLRLT RXYYZX[WZXYX[ RXKYLXMWLXKXM',
        'D`KFHL RQFNL RWFTL R]FZL',
        'E_KRLSKTJSKRKT RRYSZR[QZRYR[ RRKSLRMQLRKRM RYRZSYTXSYRYT',
        'E_LXMYLZKYLXLZ RLLMMLNKMLLLN RRRSSRTQSRRRT RXXYYXZWYXXXZ RXLYMXNWMXLXN',
        'MWRYSZR[QZRYR[ RRNSORPQORNRP',
        'E_KRLSKTJSKRKT RRYSZR[QZRYR[ RRKSLRMQLRKRM RYRZSYTXSYRYT',
        'E_JSZS RR[RK RLXMYLZKYLXLZ RLLMMLNKMLLLN RXXYYXZWYXXXZ RXLYMXNWMXLXN',
        'CaR\\S]R^Q]R\\R^ RRRSSRTQSRRRT RRHSIRJQIRHRJ',
        'CaR^S_R`Q_R^R` RRVSWRXQWRVRX RRNSORPQORNRP RRFSGRHQGRFRH',
        'OU',
        24,
        24,
        24,
        24,
        24,
        23,
        23,
        23,
        23,
        23,
        24,
        24,
        24,
        24,
        24,
        24,
        'JZQ@S@UAVDVJUMSNQNOMNJNDOAQ@',
        'NVRDRN RR=Q>R?S>R=R?',
        23,
        23,
        'JZUFUN RQ@NJWJ',
        'JZV@O@NFPESEUFVHVKUMSNPNNM',
        'JZNHOFQESEUFVHVKUMSNQNOMNKNFOCPAR@U@',
        'JZM@W@PN',
        'JZQFOENCOAQ@S@UAVCUESFQFOGNINKOMQNSNUMVKVIUGSF',
        'JZVFUHSIQIOHNFNCOAQ@S@UAVCVHUKTMRNON',
        'I[LHXH RRBRN',
        'I[LHXH',
        'I[LJXJ RLFXF',
        'MWT=S>RAQFQJROSRTS',
        'MWP=Q>RASFSJROQRPS',
        'KZODON ROEQDSDUEVGVN',
        'JZQSSSUTVWV]U`SaQaO`N]NWOTQS',
        'JZVaNa RNVPURSRa',
        'JZNTPSSSUTVVVXUZNaVa',
        'JZNSVSRXSXUYV[V^U`SaPaN`',
        'JZUYUa RQSN]W]',
        'JZVSOSNYPXSXUYV[V^U`SaPaN`',
        'JZN[OYQXSXUYV[V^U`SaQaO`N^NYOVPTRSUS',
        'JZMSWSPa',
        'JZQYOXNVOTQSSSUTVVUXSYQYOZN\\N^O`QaSaU`V^V\\UZSY',
        'JZVYU[S\\Q\\O[NYNVOTQSSSUTVVV[U^T`RaOa',
        'I[L[X[ RRURa',
        'I[L[X[',
        'I[L]X] RLYXY',
        'MWTPSQRTQYQ]RbSeTf',
        'MWPPQQRTSYS]RbQePf',
        24,
        'KZOXQWSWUXVZVa RV`TaQaO`N^O\\Q[V[',
        'LYV`TaRaP`O^OZPXRWSWUXVZV[O\\',
        'KYQaO`N^NZOXQWSWUXVZV^U`SaQa',
        'KYNWVa RVWNa',
        'LYOXQWSWUXVZV^U`SaRaP`O^O]V\\',
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        'F[XMPMP[X[ RTGRFNFLGKHJJJPKRLSNTUT',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RSBG_ RZBN_',
        'F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RR[RM RRQSOTNVMXM',
        'HZTPMP RM[MFWF RJVRV',
        'H[LMTM RL[W[ RO[OIPGRFUFWG RLSTS',
        'D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ RWHM`',
        'G]L[LFX[XF RHV\\V RHP\\P',
        'GyL[LFTFVGWHXJXMWOVPTQLQ R^MfM RaFaXbZd[f[ RlZn[r[tZuXuWtUrToTmSlQlPmNoMrMtN',
        'GmX[QQ RL[LFTFVGWHXJXMWOVPTQLQ R`Zb[f[hZiXiWhUfTcTaS`Q`PaNcMfMhN',
        'F^IFN[RLV[[F RHV\\V RHP\\P',
        'D`I[IFOFRGTIULUR RONOUPXRZU[[[[F',
        'I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RRHZH RXaNa',
        'F[HSQS RHNTN RWYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH',
        'G\\L[LF RX[OO RXFLR RLOTO',
        'JZLFXF RR[RF ROVUR ROPUL',
        'IoK[RFY[K[ R`b`QaObNdMgMiNjOkQkWjYiZg[d[bZ`X',
        'G]ITJSLRNSOTQUSTXOYLYIXGVFUFSGRIRLSOXTYVYWXYWZT[',
        'G\\L[LFTFVGWHXJXMWOVPTQLQ RHL\\L',
        'F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RRCR^',
        'I[K[RFY[ RHV\\V RHP\\P',
        'H\\XZU[P[NZMYLWLUMSNRPQTPVOWNXLXJWHVGTFOFLG RRCR^',
        'HZVZT[P[NZMYLWLQMONNPMTMVN RRJR^',
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        'F^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[',
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        'E_ZSJS RNWJSNO',
        'E_R[RK RNORKVO',
        'E_JSZS RVWZSVO',
        'E_RKR[ RVWR[NW',
        'E_JSZS RVWZSVO RNOJSNW',
        'E_R[RK RNORKVO RVWR[NW',
        'E_KLYZ RRLKLKS',
        'E_YLKZ RRLYLYS',
        'E_YZKL RRZYZYS',
        'E_KZYL RRZKZKS',
        'E_ZSJS RRWVO RNOJSNW',
        'E_JSZS RRONW RVWZSVO',
        'E_JWJQPQ RJQMTOUQTSRUQWRZU',
        'E_ZWZQTQ RZQWTUUSTQROQMRJU',
        'E_ZSJS RTOPSTW RNWJSNO',
        'E_R[RK RNURQVU RNORKVO',
        'E_JSZS RPOTSPW RVWZSVO',
        'E_RKR[ RVQRUNQ RVWR[NW',
        'E_JSVS RZOVSZW RNWJSNO',
        'E_ZSNS RJONSJW RVWZSVO',
        'E_ZOZW RJSZS RNWJSNO',
        'E_R[RK RV[N[ RNORKVO',
        'E_JOJW RZSJS RVWZSVO',
        'E_RKR[ RNKVK RVWR[NW',
        'E_N[V[ RR[RK RNWR[VW RNORKVO',
        'E_NWJSNO RJSWSYRZPYNWM',
        'E_VWZSVO RZSMSKRJPKNMM',
        'E_NWJSNO RJSWSYRZPYNWMUNTPTW',
        'E_VWZSVO RZSMSKRJPKNMMONPPPW',
        'E_PUJUJO RZWZQTQ RZQWTUUSTQROQMRJU',
        'E_JSZS RTOPW RNOJSNW RVWZSVO',
        'E_PWR[VY ROKLTVOR[',
        'E_V[VOJO RNSJONK',
        'E_N[NOZO RVSZOVK',
        'E_VKVWJW RNSJWN[',
        'E_NKNWZW RVSZWV[',
        'E_JOVOV[ RZWV[RW',
        'E_VKVWJW RNSJWN[',
        'E_OQKUGQ RYRYQXNVLSKQKNLLNKQKU',
        'E_UQYU]Q RKRKQLNNLQKSKVLXNYQYU',
        'E_KLYZ RKHYH RRLKLKS',
        'E_JWZW RJKJS RZSZ[ RZOJO RNSJONK RV[ZWVS',
        'E_[KUKUQ RMMLNKQKSLVNXQYSYVXXVYSYQXNUK',
        'E_IKOKOQ RWMXNYQYSXVVXSYQYNXLVKSKQLNOK',
        'E_ZSJSNO',
        'E_ZSJSNW',
        'E_R[RKVO',
        'E_R[RKNO',
        'E_JSZSVO',
        'E_JSZSVW',
        'E_RKR[VW',
        'E_RKR[NW',
        'E_ZWJW RJOZO RVSZOVK RN[JWNS',
        'E_N[NK RVKV[ RJONKRO RRWV[ZW',
        'E_JWZW RZOJO RNSJONK RV[ZWVS',
        'E_ZWJW RJOZO RN[JWNSJONK',
        'E_N[NK RVKV[ RJONKROVKZO',
        'E_JWZW RZOJO RV[ZWVSZOVK',
        'E_VKV[ RN[NK RZWV[RWN[JW',
        'E_JVZVVZ RZPJPNL',
        'E_ZVJVNZ RJPZPVL',
        'E_ZPMP RZVMV RRXVN ROXJSON',
        'E_MVWV RMPWP RSNQX ROXJSON RUNZSUX',
        'E_JVWV RJPWP RRNNX RUNZSUX',
        'E_ZPMP RZVMV ROXJSON',
        'E_ONO[ RUNU[ RWPRKMP',
        'E_JVWV RJPWP RUNZSUX',
        'E_UXUK ROXOK RMVR[WV',
        'E_MVWV RMPWP ROXJSON RUNZSUX',
        'E_OXON RUXUN RMVR[WV RWPRKMP',
        'E_[XOL RW\\KP RSLKLKT',
        'E_IXUL RM\\YP RQLYLYT',
        'E_INUZ RMJYV RQZYZYR',
        'E_[NOZ RWJKV RSZKZKR',
        'E_ZXOX RZSJS RZNON RQLJSQZ',
        'E_JXUX RJSZS RJNUN RSLZSSZ',
        'E_NWJSNO RZUWQTUQQNULSJS',
        'E_VWZSVO RJUMQPUSQVUXSZS',
        'E_NXVX RNSVS RR[RK RNORKVO',
        'E_VNNN RVSNS RRKR[ RVWR[NW',
        'E_ZSWS RSSQS RMSJS RNOJSNW',
        'E_R[RX RRTRR RRNRK RNORKVO',
        'E_JSMS RQSSS RWSZS RVWZSVO',
        'E_RKRN RRRRT RRXR[ RVWR[NW',
        'E_ZSJS RJWJO RNOJSNW',
        'E_JSZS RZOZW RVWZSVO',
        'E_ZPZVOVOXJSONOPZP',
        'E_U[O[OPMPRKWPUPU[',
        'E_JVJPUPUNZSUXUVJV',
        'E_OKUKUVWVR[MVOVOK',
        'E_U[O[OWUWU[ RUSOSOPMPRKWPUPUS',
        'E_W[M[MWOWOPMPRKWPUPUWWWW[',
        'E_ONUN RW[M[MWOWOPMPRKWPUPUWWWW[',
        'E_RKR[ RW[M[MWOWOPMPRKWPUPUWWWW[',
        'E_PPMPRKWPTP RU[O[OSMSRNWSUSU[',
        'E_PPMPRKWPTP RW[M[MWOWOSMSRNWSUSUWWWW[',
        'E_JNNNNPUPUNZSUXUVNVNXJXJN',
        'E_Z[NO RZKJKJ[ RUONONV',
        'E_JKVW RJ[Z[ZK ROWVWVP',
        'E_MPRKWPUPUVWVR[MVOVOPMP',
        'E_JSZS RVWZSVO RTRTTSVQWOWMVLTLRMPOOQOSPTR',
        'E_V[VK RNKN[ RZOVKRO RRWN[JW',
        'E_J[Z[ RJKZK RZSJS RVGZKVOZSVWZ[V_',
        'E_ZSJS RTWTO RNOJSNW',
        'E_JSZS RPOPW RVWZSVO',
        'E_JSZS RRORW RNOJSNW RVWZSVO',
        'E_ZSJS RWWWO RRWRO RNOJSNW',
        'E_JSZS RMOMW RRORW RVWZSVO',
        'E_JSZS RPOPW RTOTW RNWJSNO RVWZSVO',
        'E_NSZS RNWNOJSNW',
        'E_VSJS RVWVOZSVW',
        'E_NSVS RNWJSNONW RVWVOZSVW',
        'I[MLWL RKFR[YF',
        'HZVHUGSFPFNGMHLKLVMYNZP[S[UZVY',
        'H[WOVNTMPMNNMOLQLWMYNZP[S[UZVYWWWJVHUGSFOFMG',
        'I\\WPPP RM[W[WFMF',
        'I\\WQPQ RMFWFW[M[ RXCL`',
        'C`G[\\F ROFTFXHZJ\\N\\SZWXYT[O[KYIWGSGNIJKHOF',
        'I[K[RFY[K[',
        'I[YFR[KFYF',
        'C`\\QGQ R\\GOGKIIKGOGSIWKYO[\\[',
        'C`[CH^ R\\QGQ R\\GOGKIIKGOGSIWKYO[\\[',
        'E_JSZS RZZPZMYKWJTJRKOMMPLZL',
        'DaHP]P RHZUZYX[V]R]N[JYHUFHF',
        'DaI^\\C RHP]P RHZUZYX[V]R]N[JYHUFHF',
        'E_ZSJS RJZTZWYYWZTZRYOWMTLJL',
        'E_M[WQ RMZWP RMYWO RMXWN RMWWM RMVWL RMUWK RMTVK RMSUK RMRTK RMQSK RMPRK RMOQK RMNPK RMMOK RMLNK RN[WR RO[WS RP[WT RQ[WU RR[WV RS[WW RT[WX RU[WY RV[WZ RM[MKWKW[M[',
        'E_Z`ZFJFJ`',
        'E_ZFZ`J`JF',
        'E_Z`I`TSIF[F',
        0,
        'E_ZWJW RROR_ RJKZK',
        'E_JSZS RR[RK RRDQERFSERDRF',
        1,
        'KYID[_',
        'E_KOYW RR[RK RYOKW',
        'E_PQRPTQUSTURVPUOSPQ',
        'E_PQPU RQUQQ RRPRV RSUSQ RTQTU RPTRVTT RPRRPTR RPQRPTQUSTURVPUOSPQ',
        'IbMTQSS[bB',
        'IbMTQSS[bB RN@V@RESEUFVHVKUMSNPNNM',
        'IbMTQSS[bB RUFUN RQ@NJWJ',
        'E_XPWPUQQUOVMULSMQOPQQUUWVXV',
        'E_TQVPXQYSXUVVTUPQNPLQKSLUNVPUTQ',
        'E_JKJ[Z[',
        'E_ZKJ[Z[',
        'E_ZKJ[Z[ RPSRUTZT]',
        'E_Z[JSZK RSYTWUSTOSM',
        22,
        'H\\NUVQ RRDRb',
        'H\\ODOb RUDUb',
        'H\\LVXP RODOb RUDUb',
        'E_[[RKI[',
        'E_IKR[[K',
        'E_Z[ZQXMTKPKLMJQJ[',
        'E_JKJULYP[T[XYZUZK',
        'H\\L]M_O`Q_R]RISGUFWGXI',
        'D`H]I_K`M_N]NIOGQFSGTI RP]Q_S`U_V]VIWGYF[G\\I',
        '@dD]E_G`I_J]JIKGMFOGPI RL]M_O`Q_R]RISGUFWGXI RT]U_W`Y_Z]ZI[G]F_G`I',
        'H\\L]M_O`Q_R]RISGUFWGXI RRMUNWPXSWVUXRYOXMVLSMPONRM',
        'D`H]I_K`M_N]NIOGQFSGTI RP]Q_S`U_V]VIWGYF[G\\I RVMYN[P\\S[VYXVYNYKXIVHSIPKNNMVM',
        '@dD]E_G`I_J]JIKGMFOGPI RL]M_O`Q_R]RISGUFWGXI RT]U_W`Y_Z]ZI[G]F_G`I RZM]N_P`S_V]XZYJYGXEVDSEPGNJMZM',
        'H\\URXU[R RLSMPONRMUNWPXSXU RL]M_O`Q_R]RISGUFWGXI',
        'H\\UQXT[Q RL]M_O`Q_R]RISGUFWGXI RLSMPONRMUNWPXSWVUXRYOXMVLS',
        'H\\UUXR[U RL]M_O`Q_R]RISGUFWGXI RLSMPONRMUNWPXSWVUXRYOXMVLS',
        'E_KXLYKZJYKXKZ RRLSMRNQMRLRN RYXZYYZXYYXYZ',
        'E_YNXMYLZMYNYL RRZQYRXSYRZRX RKNJMKLLMKNKL',
        'JZRXSYRZQYRXRZ RRLSMRNQMRLRN',
        'E_LXMYLZKYLXLZ RLLMMLNKMLLLN RXXYYXZWYXXXZ RXLYMXNWMXLXN',
        'E_JSZS RRFQGRHSGRFRH',
        'E_JSTS RYXZYYZXYYXYZ RYLZMYNXMYLYN',
        'E_JSZS RLXMYLZKYLXLZ RLLMMLNKMLLLN RXXYYXZWYXXXZ RXLYMXNWMXLXN',
        'E_JSKRNQQRSTVUYTZS RRXSYRZQYRXRZ RRLSMRNQMRLRN',
        'E_JSKRNQQRSTVUYTZS',
        'E_ZSYRVQSRQTNUKTJS',
        'E_WPYQZSYUWVTUPQMPKQJSKUMV',
        'E_JSKNLLNKPLQNSXTZV[XZYXZS',
        'E_RKSLTOSRQTPWQZR[',
        'E_JSKRNQQRSTVUYTZS RVKN[',
        'E_ZPJP RZVYWVXSWQUNTKUJV',
        'E_JVZV RJPKONNQOSQVRYQZP',
        'E_JVZV RJPKONNQOSQVRYQZP RVKN[',
        'E_JYZY RJSZS RJMKLNKQLSNVOYNZM',
        'E_JYZY RJSZS RUPO\\ RJMKLNKQLSNVOYNZM',
        'E_JYZY RJSZS RJMKLNKQLSNVOYNZM RXGL_',
        'E_JVKUNTQUSWVXYWZV RJPKONNQOSQVRYQZP',
        'E_JVKUNTQUSWVXYWZV RJPKONNQOSQVRYQZP RVKN[',
        'E_JYZY RJSKRNQQRSTVUYTZS RJMKLNKQLSNVOYNZM',
        'E_JYKXNWQXSZV[YZZY RJSKRNQQRSTVUYTZS RJMKLNKQLSNVOYNZM',
        'E_ZYJY RZSJS RZMYLVKSLQNNOKNJM',
        'E_JXLWPVTVXWZX RJNLOPPTPXOZN',
        'E_JVNVNWOYQZSZUYVWVVZV RJPNPNOOMQLSLUMVOVPZP',
        'E_ZVJV RJPNPNOOMQLSLUMVOVPZP',
        'E_JPZP RZVJV RRHQIRJSIRHRJ',
        'E_JPZP RZVJV RRXSYRZQYRXRZ RRLSMRNQMRLRN',
        'E_JPZP RZVJV RKJLKKLJKKJKL RYZZ[Y\\X[YZY\\',
        'E_ZPJP RJVZV RYJXKYLZKYJYL RKZJ[K\\L[KZK\\',
        'AcNP^P R^VNV RGVHWGXFWGVGX RGNHOGPFOGNGP',
        'AcVPFP RFVVV R]V\\W]X^W]V]X R]N\\O]P^O]N]P',
        'E_JPZP RZVJV RPQRPTQUSTURVPUOSPQ',
        'E_JPZP RZVJV RRJPIOGPERDTEUGTIRJ',
        'E_JPZP RZVJV RNJOHQGSGUHVJ',
        'E_JPZP RZVJV RNJRGVJ',
        'E_JPZP RZVJV RNGRJVG',
        'E_JPZP RZVJV RRATGOCUCPGRA',
        'E_JPZP RZVJV RR?NJVJR?',
        'E_JPZP RYC]C RZVJV R]?[@ZBZJ RM?MJKJIIHGHEICKBMB RQFVFVCUBRBQCQIRJUJ',
        'E_JPZP RZVJV RMBMJ RMCNBQBRCRJ RRCSBVBWCWJ',
        'E_JPZP RZVJV RRHSIRJQIRHRJ RN@P?S?U@VBUDSE',
        'E_JPZP RTMPY RZVJV',
        'E_JYZY RJSZS RJMZM',
        'E_JYZY RJSZS RJMZM RXGL_',
        'E_J\\Z\\ RJPZP RJJZJ RZVJV',
        'E_ZZJZ RZVJPZJ',
        'E_JZZZ RJVZPJJ',
        'E_J]Z] RZWJW RZSJMZG',
        'E_Z]J] RJWZW RJSZMJG',
        'E_J]Z] RTTP` RZWJW RZSJMZG',
        'E_JWZW RTTP` RZ]J] RJSZMJG',
        '=gRMBSRY RbMRSbY',
        '=gRMbSRY RBMRSBY',
        'I[OCPDRGSITLUQUUTZS]R_PbOc RUcTbR_Q]PZOUOQPLQIRGTDUC',
        'E_JXLWPVTVXWZX RJNLOPPTPXOZN RVKN[',
        'E_ZMJSZY RVKN[',
        'E_JMZSJY RVKN[',
        'E_ZZJZ RZVJPZJ RXGL_',
        'E_JZZZ RJVZPJJ RXGL_',
        'E_ZVJPZJ RJZKYNXQYS[V\\Y[ZZ',
        'E_JVZPJJ RJZKYNXQYS[V\\Y[ZZ',
        'E_ZVJPZJ RJZKYNXQYS[V\\Y[ZZ RXGL_',
        'E_JVZPJJ RJZKYNXQYS[V\\Y[ZZ RXGL_',
        'E_JSZYJ_ RZSJMZG',
        'E_ZSJYZ_ RJSZMJG',
        'E_JSZYJ_ RZSJMZG RXGL_',
        'E_ZSJYZ_ RJSZMJG RXGL_',
        'E_ZKXNVPRRJSRTVVXXZ[',
        'E_JKLNNPRRZSRTNVLXJ[',
        'E_JVRWVYX[Z^ RZHXKVMROJPRQVSXUZX',
        'E_ZVRWNYL[J^ RJHLKNMROZPRQNSLUJX',
        'E_J[KZNYQZS\\V]Y\\Z[ RZHXKVMROJPRQVSXUZX',
        'E_J[KZNYQZS\\V]Y\\Z[ RJXLUNSRQZPRONMLKJH',
        'E_ZKXNVPRRJSRTVVXXZ[ RVKN[',
        'E_JKLNNPRRZSRTNVLXJ[ RVKN[',
        'E_ZMNMLNKOJQJUKWLXNYZY',
        'E_JMVMXNYOZQZUYWXXVYJY',
        'E_ZMNMLNKOJQJUKWLXNYZY RVKN[',
        'E_JMVMXNYOZQZUYWXXVYJY RVKN[',
        'E_J\\Z\\ RZJNJLKKLJNJRKTLUNVZV',
        'E_Z\\J\\ RJJVJXKYLZNZRYTXUVVJV',
        'E_J\\Z\\ RZJNJLKKLJNJRKTLUNVZV RXGL_',
        'E_Z\\J\\ RJJVJXKYLZNZRYTXUVVJV RXGL_',
        'E_J\\Z\\ RZJNJLKKLJNJRKTLUNVZV RSYQ_',
        'E_Z\\J\\ RJJVJXKYLZNZRYTXUVVJV RSYQ_',
        'E_JKJULYP[T[XYZUZK ROSUS RSUUSSQ',
        'E_JKJULYP[T[XYZUZK RRRQSRTSSRRRT',
        'E_JKJULYP[T[XYZUZK RLSXS RRMRY',
        'E_ZYJYJMZM',
        'E_JYZYZMJM',
        'E_Z\\J\\ RZVJVJJZJ',
        'E_J\\Z\\ RJVZVZJJJ',
        'E_Z[ZKJKJ[',
        'E_JKJ[Z[ZK',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RLSXS RRMRY',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RLSXS',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RMNWX RWNMX',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RWFM^',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRRQSRTSSRRRT',
        47,
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRNRS RMQRSWQ ROWRSUW',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RLUXU RLQXQ',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RNSVS',
        'E_JKZKZ[J[JK RLSXS RRMRY',
        'E_JKZKZ[J[JK RLSXS',
        'E_JKZKZ[J[JK RMNWX RWNMX',
        'E_JKZKZ[J[JK RRRQSRTSSRRRT',
        'E_J[JK RJSZS',
        'E_Z[ZK RZSJS',
        'E_ZKJK RRKR[',
        'E_J[Z[ RR[RK',
        'I[NSVS RNKN[',
        'I[NVVV RNPVP RNKN[',
        'E_JVZV RJPZP RJKJ[',
        'E_JKJ[ RPSZS RPKP[',
        'E_JKJ[ ROKO[ RTKT[ RYSTS',
        'E_JKJ[ RPVYV RPPYP RPKP[',
        'E_J[JK RJSZS RXGL_',
        'E_JVZV RJPZP RJKJ[ RXGL_',
        'E_JKJ[ RPSZS RPKP[ RXGL_',
        'E_JKJ[ RPVYV RPPYP RPKP[ RXGL_',
        'E_VKXLYNXPVQRRJSRTVUXVYXXZV[',
        'E_NKLLKNLPNQRRZSRTNULVKXLZN[',
        'E_JSZYZMJS',
        'E_ZSJYJMZS',
        'E_Z[J[ RJQZWZKJQ',
        'E_J[Z[ RZQJWJKZQ',
        'BbXQXU RYQYU RZPZV R[Q[U R\\Q\\U RMSLQJPHQGSHUJVLUMSWSXUZV\\U]S\\QZPXQWS',
        'BbLQLU RKQKU RJPJV RIQIU RHQHU RWSXQZP\\Q]S\\UZVXUWSMSLUJVHUGSHQJPLQMS',
        'E_JSTSUUWVYUZSYQWPUQTS',
        'E_JSNS RR[RW RRKRO RZSVS',
        'I[NFVF RRFR[',
        'E_J[Z[ RZKRVJK',
        'E_ZKJK RJ[RPZ[',
        'E_JKZK RZPR[JP',
        'E_JKJ[Z[ RJOLOQQTTVYV[',
        'E_Z[ZKJ[Z[',
        'Bb_`REE`',
        'BbEFRa_F',
        'Bb]`]O\\KZHWFSEQEMFJHHKGOG`',
        'BbGFGWH[J^M`QaSaW`Z^\\[]W]F',
        'E_RaJSRFZSRa',
        26,
        'I[RRTXOTUTPXRR',
        'E_ZSJS RRXSYRZQYRXRZ RRLSMRNQMRLRN RLMXY RXMLY',
        'E_JKZ[ZKJ[JK',
        'E_ZKJ[JKZ[',
        'E_JKZ[ZKJ[',
        'E_JKZ[ RRSJ[',
        'E_ZKJ[ RRSZ[',
        'E_ZVJV RZPYOVNSOQQNRKQJP',
        'E_JKMMOOQSR[SSUOWMZK',
        'E_Z[WYUWSSRKQSOWMYJ[',
        'E_ZPSPQQPSQUSVZV RZ\\Q\\N[KXJUJQKNNKQJZJ',
        'E_JPQPSQTSSUQVJV RJ\\S\\V[YXZUZQYNVKSJJJ',
        'E_U[UTTRRQPROTO[ R[[[RZOWLTKPKMLJOIRI[',
        'E_OKORPTRUTTURUK RIKITJWMZP[T[WZZW[T[K',
        'E_RKR[ RL[LSMPNOQNSNVOWPXSX[',
        'E_JPZP RZVJV RODOb RUDUb',
        'E_ZMJSZY RYRXSYTZSYRYT',
        'E_JMZSJY RKRJSKTLSKRKT',
        '5oJM:SJY RZMJSZY RjMZSjY',
        '5oZMjSZY RJMZSJY R:MJS:Y',
        'E_ZSJS RJWZ[J_ RZOJKZG',
        'E_JSZS RZWJ[Z_ RJOZKJG',
        'E_ZLJL RZPJVZ\\',
        'E_JLZL RJPZVJ\\',
        'E_JPROVMXKZH RZ^X[VYRWJVRUVSXQZN',
        'E_ZPRONMLKJH RJ^L[NYRWZVRUNSLQJN',
        'E_JPROVMXKZH RZ^X[VYRWJVRUVSXQZN RXGL_',
        'E_ZPRONMLKJH RJ^L[NYRWZVRUNSLQJN RXGL_',
        'E_Z\\J\\ RZVJVJJZJ RXGL_',
        'E_J\\Z\\ RJVZVZJJJ RXGL_',
        'E_Z\\J\\ RZVJVJJZJ RSYQ_',
        'E_J\\Z\\ RJVZVZJJJ RSYQ_',
        'E_ZVJPZJ RJZKYNXQYS[V\\Y[ZZ RSWQ]',
        'E_JVZPJJ RJZKYNXQYS[V\\Y[ZZ RSWQ]',
        'E_J[KZNYQZS\\V]Y\\Z[ RZHXKVMROJPRQVSXUZX RSXQ^',
        'E_J[KZNYQZS\\V]Y\\Z[ RJXLUNSRQZPRONMLKJH RSXQ^',
        'E_JSZYZMJS RXGL_',
        'E_ZSJYJMZS RXGL_',
        'E_Z[J[ RJQZWZKJQ RXGL_',
        'E_J[Z[ RZQJWJKZQ RXGL_',
        'CaR\\S]R^Q]R\\R^ RRRSSRTQSRRRT RRHSIRJQIRHRJ',
        'CaHRISHTGSHRHT RRRSSRTQSRRRT R\\R]S\\T[S\\R\\T',
        'Ca\\H[I\\J]I\\H\\J RRRQSRTSSRRRT RH\\G]H^I]H\\H^',
        'CaHHIIHJGIHHHJ RRRSSRTQSRRRT R\\\\]]\\^[]\\\\\\^',
        '>`BQ\\Q R\\GOGKIIKGOGSIWKYO[\\[',
        '>`GQ\\Q R\\M\\U R\\GOGKIIKGOGSIWKYO[\\[',
        'E_JSZS RZPZV RZZPZMYKWJTJRKOMMPLZL',
        'C`\\QGQ R\\GOGKIIKGOGSIWKYO[\\[ RR@QARBSAR@RB',
        'C`GA\\A R\\QGQ R\\[O[KYIWGSGOIKKIOG\\G',
        'E_JSZS RZGJG RZLPLMMKOJRJTKWMYPZZZ',
        'C`G`\\` R\\PGP R\\FOFKHIJGNGRIVKXOZ\\Z',
        'C`HT\\T RHN\\N R\\GOGKIIKGOGSIWKYO[\\[',
        'DfbQHQ RHGUGYI[K]O]S[WYYU[H[',
        'Df]QHQ RHMHU RHGUGYI[K]O]S[WYYU[H[',
        'E_ZSJS RJPJV RJZTZWYYWZTZRYOWMTLJL',
        'Da]AHA RHQ]Q RH[U[YY[W]S]O[KYIUGHG',
        'E_ZSJS RJGZG RJLTLWMYOZRZTYWWYTZJZ',
        'C`GQ\\Q R\\GGGG[\\[',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RZKJ[',
        'E_JQRWROZU',
        'E_J[JORGZOZ[J[',
        'E_NORKVO',
        'E_VWR[NW',
        'E_ZKJK RJ[RPZ[',
        'E_JNZN RJHZH RJ[RSZ[',
        'H\\RDSETGSIRJQLRNSOTQSSRTQVRXSYT[S]R^Q`Rb',
        'KYQbQDVD',
        'KYSbSDND',
        'KYQDQbVb',
        'KYSDSbNb',
        'E_RWR[ RVSZS',
        'E_RWR[ RNSJS',
        'E_RORK RVSZS',
        'E_RORK RNSJS',
        'E_ZQJQJV',
        'D`[JZLYPYVZZ[\\Y[UZOZK[I\\JZKVKPJLIJKKOLULYK[J',
        'E_JSJQLMPKTKXMZQZS',
        'E_JSJQLMPKTKXMZQZS RJSZS',
        'E_JMLLPKTKXLZMR[JM',
        'E_PUJ[ RTKWLYNZQYTWVTWQVOTNQONQLTK',
        'E_JSZS RR[RK RVRUPSOQOOPNRNTOVQWSWUVVTVR',
        'E_JWZW RJOZO RNKN[ RVKV[',
        'E_LPXPZO[MZKXJVKUMUYV[X\\Z[[YZWXVLVJWIYJ[L\\N[OYOMNKLJJKIMJOLP',
        'E_ZUJUJP',
        'E_RORSUS RPKTKXMZQZUXYT[P[LYJUJQLMPK',
        'E_M[RVW[ RN[RWV[ RP[RYT[ RS[RZQ[ RU[RXO[ RYMRPKMROYM RJFZFZKYMKTJVJ[Z[ZVYTKMJJJF',
        'JZVFNFNM',
        'JZNFVFVM',
        'JZV[N[NT',
        'JZN[V[VT',
        'H\\RbRMSITGVFXGYI',
        'H\\RDRYQ]P_N`L_K]',
        'E_JUKTMSRRWSYTZU',
        'E_ZQYRWSRTMSKRJQ',
        'E_LKHK RXK\\K RNORKVO',
        '@dXK^K RFKLKX[^[',
        'AfJKZ[ RZKJ[ RFKZKbSZ[F[FK',
        'AcJKZ[ RZKJ[ RFK^K^[F[FK',
        '9k>VfV R>LfL RCQCL RD[DV REVEQ RFLFG RHQHL RJVJQ RK[KV RKLKG RMQML ROVOQ RPLPG RRQRL RTVTQ RULUG RWQWL RYVYQ RZ[ZV RZLZG R\\Q\\L R^V^Q R_L_G R`[`V R>QaQaL R>[>GfGf[>[',
        'KYUcOSUC',
        'KYOcUSOC',
        '>cZKJ[ RJKZ[ R^KJKBSJ[^[^K',
        'AcKOKW RR[YW RRKYO RRE^L^ZRaFZFLRE',
        'H\\PNKX RYNTX RVRUPSOQOOPNRNTOVQWSWUVVTVR',
        'E_N[J[JW RZSRSJ[ RVRUPSOQOOPNRNTOVQWSWUVVTVR',
        'E_JSZS RNYVY RVMNM',
        'E_RPRKNN RZPZKVN RRKJ[R[ZK',
        'H\\LS[S RRMRY RXP[SXV RVRUPSOQOOPNRNTOVQWSWUVVTVR',
        'E_ZSJ\\JJZS RJSZS',
        'E_J[JRZ[J[',
        'E_JWJ[Z[ZW',
        'E_VWR[NW',
        'D`JaZa RJFZF RRFRa',
        'D`MFWFWaMaMF',
        'D`IF[F[aIaIF RJPZP RZVJV',
        'D`IF[F[aIaIF RZSJS RRXSYRZQYRXRZ RRLSMRNQMRLRN',
        'D`IF[F[aIaIF RRJ[SR\\ISRJ',
        'D`IF[F[aIaIF RPQRPTQUSTURVPUOSPQ',
        'D`IF[F[aIaIF RPKTKXMZQZUXYT[P[LYJUJQLMPK',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRbRD',
        47,
        'E_JSZS RZKJ[',
        'E_JSZS RJKZ[',
        'D`IaIF[F[aIa[F',
        'D`[a[FIFIa[aIF',
        'D`IF[F[aIaIF RZMJSZY',
        'D`IF[F[aIaIF RJMZSJY',
        'E_ZSJS RNWJSNO RR[RK',
        'E_JSZS RVWZSVO RR[RK',
        'D`IF[F[aIaIF RZSJS RNWJSNO',
        'D`IF[F[aIaIF RJSZS RVWZSVO',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RLGX_',
        'E_J[Z[ RR[RK RZaJa',
        'E_RKX[L[RK RRbRD',
        'D`IF[F[aIaIF RIKR[[K',
        'D`IF[F[aIaIF RRKX[L[RK',
        'E_ZKJK RRKR[ RVRUPSOQOOPNRNTOVQWSWUVVTVR',
        'E_R[RK RNORKVO RJSZS',
        'D`IF[F[aIaIF RR[RK RNORKVO',
        'E_ZKJK RRKR[ RMEWE',
        'E_R[LKXKR[ RRbRD',
        'D`IF[F[aIaIF R[[RKI[',
        'D`IF[F[aIaIF RR[LKXKR[',
        'E_J[Z[ RR[RK RPQRPTQUSTURVPUOSPQ',
        'E_RKR[ RVWR[NW RJSZS',
        'D`IF[F[aIaIF RRKR[ RVWR[NW',
        'JZJ]Z] RSFQJ',
        'E_RKX[L[RK RJ]Z]',
        'E_RJ[SR\\ISRJ RJ]Z]',
        'E_PQRPTQUSTURVPUOSPQ RJ]Z]',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RJ]Z]',
        'E_Z[ZQXMTKPKLMJQJ[ RPQRPTQUSTURVPUOSPQ',
        'D`IF[F[aIaIF RSFQJ',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRPTVORURPVRP',
        'D`IF[F[aIaIF RRYSZR[QZRYR[ RRNSORPQORNRP',
        'E_ZKJK RRKR[ RNDOENFMENDNF RVDWEVFUEVDVF',
        'E_R[LKXKR[ RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'E_RKWZJQZQMZRK RNDOENFMENDNF RVDWEVFUEVDVF',
        'E_PQRPTQUSTURVPUOSPQ RNIOJNKMJNINK RVIWJVKUJVIVK',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RNDOENFMENDNF RVDWEVFUEVDVF',
        'E_JKJULYP[T[XYZUZK RRbRD',
        'E_ZMNMLNKOJQJUKWLXNYZY RRbRD',
        'E_JSKRNQQRSTVUYTZS RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'E_JMZSJY RNFOGNHMGNFNH RVFWGVHUGVFVH',
        'E_JSZS RSZS[R]Q^',
        'E_R[LKXKR[ RJSKRNQQRSTVUYTZS',
        'H\\QFSFUGVHWJXNXSWWVYUZS[Q[OZNYMWLSLNMJNHOGQF RJPKONNQOSQVRYQZP',
        'E_JSKRNQQRSTVUYTZS RRbRD',
        'MWSZS[R]Q^ RRNSORPQORNRP RJ]Z]',
        'D`IF[F[aIaIF RJPZP RTMPY RZVJV',
        'D`IF[F[aIaIF RQYRZQ[PZQYQ[ RMGOFTFVGWIWKVMUNSORPQRQS',
        'E_IKR[[K RJSKRNQQRSTVUYTZS',
        'E_[[RKI[ RJSKRNQQRSTVUYTZS',
        36,
        'H\\MbMQNOONQMTMVNWOXQXWWYVZT[Q[OZMX',
        43,
        'H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RJ]Z]',
        'HZLTST RVZT[P[NZMYLWLQMONNPMTMVN RJ]Z]',
        'MXRMRXSZU[ RJ]Z]',
        'G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RJ]Z]',
        34,
        'IbMTQSS[bB RXL`L',
        'A_J_F_F[ RJKJ[Z[ RF_OVEQOG',
        'E_JWNWN[V[VWZW',
        'E_NSN[J[ RVSV[Z[ RJSJQLMPKTKXMZQZSJS',
        'E_PQPU RQUQQ RRPRV RSUSQ RTQTU RPTRVTT RPRRPTR RPQRPTQUSTURVPUOSPQ RRbRD',
        'E_VWR[NW ROEQDSDUEVGVN RVMTNQNOMNKOIQHVH',
        'BbF[^[ RGLIKKKMLNNNU RUSVTUUTTUSUU R]S^T]U\\T]S]U RNTLUIUGTFRGPIONO',
        'BbF[N[ RV[^[ RGLIKKKMLNNNU RWLYK[K]L^N^U RNTLUIUGTFRGPIONO R^T\\UYUWTVRWPYO^O',
        'BbHPDP RJUFX RJKFH R^XZU R^HZK R`P\\P RTTRUPUNTMRMQNNPLRKVKTU',
        '=_RKR[B[BKRK RPKTKXMZQZUXYT[P[LYJUJQLMPK',
        'E_JKZKZ[J[JK RRbRD',
        'C_ESUS RQWUSQO RJWJ[Z[ZKJKJO',
        '@dX[^[ RZO^KZG RF[L[XK^K',
        'E_KOYW RR[RK RYOKW RRMONMPLSMVOXRYUXWVXSWPUNRM',
        'E_JSOSR[USZS RPKTKXMZQZUXYT[P[LYJUJQLMPK',
        'E_R[KOYOR[ RPKTKXMZQZUXYT[P[LYJUJQLMPK',
        'E_STJK RJOJKNK RSKTKXMZQZUXYT[P[LYJUJT',
        'D`KNKROR RYRWPTOPOMPKR RNXMVKUIVHXIZK[MZNX RVXWZY[[Z\\X[VYUWVVX',
        'E_I[N[NKVKV[[[',
        'E_I[V[VK RN[NK[K',
        'E_JKZK RJSRKZSR[JS',
        'E_Z[J[ RZSR[JSRKZS',
        'E_JKZK RJSRKZSR[JS RJSZS',
        'E_Z[J[ RZSR[JSRKZS RJSZS',
        'E_JVLV RJPZP RQVSV RXVZV',
        'BbL[FQLGXG^QX[L[',
        'D`IF[F[aIaIF',
        'MWTFQL',
        'AcZSJS RRORK RR[RW RNOJSNW R^[F[FK^K^[',
        'AcJSZS RRWR[ RRKRO RVWZSVO RFK^K^[F[FK',
        'BbLHQHQC RLSLHQCXCXSLS RLKJKHLGNGXHZJ[Z[\\Z]X]N\\LZKXK',
        'BbROJW RZORW RGXGNHLJKZK\\L]N]X\\ZZ[J[HZGX',
        'H\\XDVGUITLSQR[Rb',
        22,
        'H\\XbV_U]TZSURKRD',
        'H\\LDNGOIPLQQR[Rb',
        22,
        'H\\LbN_O]PZQURKRD',
        'H\\XGRGRb',
        22,
        'H\\X_R_RD',
        'H\\LGRGRb',
        22,
        'H\\L_R_RD',
        'H\\XDTHSJRNRb',
        'H\\RDRIQMPOLSPWQYR]Rb',
        'H\\XbT^S\\RXRD',
        22,
        'H\\LDPHQJRNRb',
        'H\\RDRISMTOXSTWSYR]Rb',
        'H\\LbP^Q\\RXRD',
        22,
        'H\\HS\\S',
        'H\\WDSHRKR[Q^Mb',
        'H\\MDQHRKR[S^Wb',
        'E_VbIF\\F',
        'E_VDI`\\`',
        '>fC^CYaYa^',
        '>fCHCMaMaH',
        '>fC^CYaYa^ RaHaMCMCH',
        'IbMTQSS[bB',
        22,
        22,
        'H\\HG\\G',
        'H\\HM\\M',
        'H\\\\YHY',
        'H\\\\_H_',
        'E_UFOFO[',
        'E_U[O[OF',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRbRD',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RZEJE RRERa',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RJaZa RRaRE',
        'E_RK[[I[RK RRbRD',
        'E_RK[[I[RK RZEJE RRERa',
        'E_RK[[I[RK RJaZa RRaRE',
        'E_JSKRNQQRSTVUYTZS RRbRD',
        'E_JSKRNQQRSTVUYTZS RZEJE RRERa',
        'E_JSKRNQQRSTVUYTZS RJaZa RRaRE',
        'E_JaZa RRaRE',
        'E_ZEJE RRERa',
        'E_OFUFU[',
        'E_O[U[UF',
        'D`TFQL RMKJKJ[Z[ZKWK',
        'E_IWN\\NZZZZKTKTTNTNRIW',
        'E_Z[J[ RJVRKZV',
        22,
        'H\\NQNROTQUSUUTVRVQ',
        'H\\NQNROTQUSUUTVRVQ RMKWK',
        'H\\NQNROTQUSUUTVRVQ RW[M[',
        'CaGQGRHTJULUNTOROQ RUQURVTXUZU\\T]R]Q RGK]K',
        'CaGQGRHTJULUNTOROQ RUQURVTXUZU\\T]R]Q R][G[',
        'E_JQJRKTMUOUQTRRRQ RRRSTUUWUYTZRZQ',
        'E_JUZUZP',
        'E_JPJUZUZP',
        'E_RPRU RJPJUZUZP',
        'E_HO\\O RLUXU RRFRO RT[P[',
        'E_HS\\S RJMZMZYJYJM',
        '>fB]C\\FZHYKXPWTWYX\\Y^Za\\b]',
        '>fbIaJ^L\\MYNTOPOKNHMFLCJBI',
        '>fB^B]C[EZOZQYRWSYUZ_Za[b]b^',
        '>fbHbIaK_LULSMROQMOLELCKBIBH',
        '>fB^FY^Yb^',
        '>fbH^MFMBH',
        'E_I[NKVK[[I[',
        'AcRE^L^ZRaFZFLRE RQLSLVMXOYRYTXWVYSZQZNYLWKTKRLONMQL',
        0,
        'E_HXMN\\NWXHX',
        'E_JSZS RJSKNLLNKPLQNSXTZV[XZYXZS',
        'E_LMXY RXMLY RPQRPTQUSTURVPUOSPQ',
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        'E_KKK[ RL[LK RMKM[ RN[NK ROKO[ RP[PK RQKQ[ RR[RK RSKS[ RT[TK RUKU[ RV[VK RWKW[ RX[XK RYKY[ RJKZKZ[J[JK',
        'E_JKZKZ[J[JK',
        'E_KLMKWKYLZNZXYZW[M[KZJXJNKL',
        'E_JKZKZ[J[JK RPPPV RQVQP RRPRV RSVSP RTPTV ROVOPUPUVOV',
        'E_JWZW RJSZS RJOZO RJKZKZ[J[JK',
        'E_NKN[ RRKR[ RVKV[ RJKZKZ[J[JK',
        'E_JWZW RJSZS RJOZO RNKN[ RRKR[ RVKV[ RJKZKZ[J[JK',
        'E_JKZ[ RN[JW RT[JQ RZUPK RZOVK RJKZKZ[J[JK',
        'E_J[ZK RJUTK RJONK RP[ZQ RV[ZW RJKZKZ[J[JK',
        'E_J[ZK RJUTK RJONK RJKZ[ RN[JW RP[ZQ RT[JQ RV[ZW RZUPK RZOVK RJKZKZ[J[JK',
        'E_PPPV RQVQP RRPRV RSVSP RTPTV ROVOPUPUVOV',
        'E_OVOPUPUVOV',
        'E_JXTN RJWSN RJVRN RJUQN RJTPN RJSON RJRNN RJQMN RJPLN RJOKN RKXUN RLXVN RMXWN RNXXN ROXYN RPXZN RQXZO RRXZP RSXZQ RTXZR RUXZS RVXZT RWXZU RXXZV RYXZW RJNZNZXJXJN',
        'E_JNZNZXJXJN',
        'E_M[WQ RMZWP RMYWO RMXWN RMWWM RMVWL RMUWK RMTVK RMSUK RMRTK RMQSK RMPRK RMOQK RMNPK RMMOK RMLNK RN[WR RO[WS RP[WT RQ[WU RR[WV RS[WW RT[WX RU[WY RV[WZ RM[MKWKW[M[',
        'E_M[MKWKW[M[',
        'E_NNLP RONKR RPNJT RQNIV RRNHX RSNIX RTNJX RUNKX RVNLX RWNMX RXVVX RXNNX RYTUX RYNOX RZRTX RZNPX R[PSX R[NQX R\\NRX RHXMN\\NWXHX',
        'E_HXMN\\NWXHX',
        'E_JZJ[ RKXK[ RLVL[ RMTM[ RNSN[ ROQO[ RPOP[ RQMQ[ RRKR[ RSMS[ RTOT[ RUQU[ RVSV[ RWTW[ RXVX[ RYXY[ RZ[RLJ[ RZZZ[ RRK[[I[RK',
        'E_RK[[I[RK',
        'E_OUOV RPSPV RQQQV RRORV RSQSV RTSTV RUUUV ROVRPUV RROVVNVRO',
        'E_ROVVNVRO',
        'E_KKK[ RLLLZ RMLMZ RNMNY ROMOY RPNPX RQNQX RRORW RSPSV RTPTV RUQUU RVQVU RWSXS RWRWT RJKYSJ[ RZSJ\\JJZS',
        'E_ZSJ\\JJZS',
        'E_PPPV RQQQU RRQRU RSSUS RSRST ROPUSOV RVSOWOOVS',
        'E_VSOWOOVS',
        'E_KNKX RLNLX RMOMW RNONW ROOOW RPPPV RQPQV RRPRV RSQSU RTQTU RURUT RVRVT RWRWT RXSWS RJNYSJX RZSJYJMZS',
        'E_ZSJYJMZS',
        'E_ZLZK RYNYK RXPXK RWRWK RVSVK RUUUK RTWTK RSYSK RR[RK RQYQK RPWPK ROUOK RNSNK RMRMK RLPLK RKNKK RJKRZZK RJLJK RR[IK[KR[',
        'E_R[IK[KR[',
        'E_UQUP RTSTP RSUSP RRWRP RQUQP RPSPP ROQOP RUPRVOP RRWNPVPRW',
        'E_RWNPVPRW',
        'E_Y[YK RXZXL RWZWL RVYVM RUYUM RTXTN RSXSN RRWRO RQVQP RPVPP ROUOQ RNUNQ RMSLS RMTMR RZ[KSZK RJSZJZ\\JS',
        'E_JSZJZ\\JS',
        'E_TVTP RSUSQ RRURQ RQSOS RQTQR RUVOSUP RNSUOUWNS',
        'E_NSUOUWNS',
        'E_YXYN RXXXN RWWWO RVWVO RUWUO RTVTP RSVSP RRVRP RQUQQ RPUPQ ROTOR RNTNR RMTMR RLSMS RZXKSZN RJSZMZYJS',
        'E_JSZMZYJS',
        'E_JRJT RKUKQ RLPLV RMWMO RNNNX ROYOM RPLPZ RQ[QK RRJR\\ RS[SK RTLTZ RUYUM RVNVX RWWWO RXPXV RYUYQ RZRZT RRJ[SR\\ISRJ',
        'E_RJ[SR\\ISRJ',
        'E_RJ[SR\\ISRJ RPRPT RQUQQ RRPRV RSUSQ RTRTT RRPUSRVOSRP',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RPQPU RQUQQ RRPRV RSUSQ RTQTU RPTRVTT RPRRPTR RPQRPTQUSTURVPUOSPQ',
        'E_RaJSRFZSRa',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK',
        'E_JQKO RKWJU RNLPK RP[NZ RTKVL RVZT[ RYOZQ RZUYW',
        'E_NLNZ RRKR[ RVLVZ RPKTKXMZQZUXYT[P[LYJUJQLMPK',
        47,
        'E_KOKW RLXP[ RLNPK RLMLY RMYMM RNLNZ ROZOL RPKP[ RQ[QK RRKR[ RS[SK RT[XX RTKT[ RTKXN RUZUL RVLVZ RWYWM RXMXY RYWYO RPKTKXMZQZUXYT[P[LYJUJQLMPK',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RKOKW RLYLM RMMMY RNZNL ROLOZ RP[LX RP[PK RLN RQKQ[ RR[P[LYJUJQLMPKRKR[',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RYWYO RXMXY RWYWM RVLVZ RUZUL RTKXN RTKT[ RXX RS[SK RRKTKXMZQZUXYT[R[RK',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RKOKS RLMLS RMSMM RNLNS ROSOL RPKLN RPKPS RQKQS RRKRS RSKSS RTSTK RXN RULUS RVSVL RWMWS RXMXS RYOYS RJSJQLMPKTKXMZQZSJS',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RYWYS RXYXS RWSWY RVZVS RUSUZ RT[XX RT[TS RS[SS RR[RS RQ[QS RPSP[ RLX ROZOS RNSNZ RMYMS RLYLS RKWKS RZSZUXYT[P[LYJUJSZS',
        'E_SSSK RTKTS RTKXN RUSUL RVLVS RWSWM RXMXS RYSYO RZSRSRK RPKTKXMZQZUXYT[P[LYJUJQLMPK',
        'E_QSQ[ RP[PS RP[LX ROSOZ RNZNS RMSMY RLYLS RKSKW RJSRSR[ RT[P[LYJUJQLMPKTKXMZQZUXYT[ RYWYO RXMXY RWYWM RVLVZ RUZUL RTKXN RTKT[ RXX RS[SK RRKTKXMZQZUXYT[R[RK',
        'E_KOKW RLYLM RMMMY RNZNL ROLOZ RP[LX RP[PK RLN RQKQ[ RR[P[LYJUJQLMPKRKR[',
        'E_YWYO RXMXY RWYWM RVLVZ RUZUL RTKXN RTKT[ RXX RS[SK RRKTKXMZQZUXYT[R[RK',
        'E_FDFb RGbGD RHDHb RIbID RJDJb RKbKD RLbLW RLDLO RMXMb RMNMD RNbNY RNDNM ROZOb ROLOD RPbPZ RPDPL RQZQb RQLQD RRbRZ RRDRL RSZSb RSLSD RTbTZ RTDTL RUZUb RULUD RVbVY RVDVM RWXWb RWNWD RXbXW RXDXO RYbYD RZDZb R[b[D R\\D\\b R]b]D R^D^b R_bEbED_D_b RKTKRLONMQLSLVMXOYRYTXWVYSZQZNYLWKT',
        'E_FRFD RGNIJ RGDGN RHLHD RIDIK RJJJD RJJMG RKDKI RLHLD RMHQF RMDMH RNGND ROPOS RODOG RPSPP RPGPD RQPQS RQDQG RRSRO RRGRD RSPSS RSFWH RSDSG RTSTP RTGTD RUPUS RUDUG RVGVD RWGZJ RWDWH RXHXD RYDYI RZJZD R[J]N R[D[K R\\L\\D R]D]N R^R^D ROQROUQ RNSOPROUPVSNS RFSFRGNIKJJMHQGSGWHZJ[K]N^R^S_S_DEDESFS R^T^b R]X[\\ R]b]X R\\Z\\b R[b[[ RZ\\Zb RZ\\W_ RYbY] RX^Xb RW^S` RWbW^ RV_Vb RUVUS RUbU_ RTSTV RT_Tb RSVSS RSbS_ RRSRW RR_Rb RQVQS RQ`M^ RQbQ_ RPSPV RP_Pb ROVOS RObO_ RN_Nb RM_J\\ RMbM^ RL^Lb RKbK] RJ\\Jb RI\\GX RIbI[ RHZHb RGbGX RFTFb RUURWOU RVSUVRWOVNSVS R^S^T]X[[Z\\W^S_Q_M^J\\I[GXFTFSESEb_b_S^S',
        'E_FRFD RGNIJ RGDGN RHLHD RIDIK RJJJD RJJMG RKDKI RLHLD RMHQF RMDMH RNGND ROPOS RODOG RPSPP RPGPD RQPQS RQDQG RRSRO RRGRD RSPSS RSFWH RSDSG RTSTP RTGTD RUPUS RUDUG RVGVD RWGZJ RWDWH RXHXD RYDYI RZJZD R[J]N R[D[K R\\L\\D R]D]N R^R^D ROQROUQ RNSOPROUPVSNS RFSFRGNIKJJMHQGSGWHZJ[K]N^R^S_S_DEDESFS',
        'E_^T^b R]X[\\ R]b]X R\\Z\\b R[b[[ RZ\\Zb RZ\\W_ RYbY] RX^Xb RW^S` RWbW^ RV_Vb RUVUS RUbU_ RTSTV RT_Tb RSVSS RSbS_ RRSRW RR_Rb RQVQS RQ`M^ RQbQ_ RPSPV RP_Pb ROVOS RObO_ RN_Nb RM_J\\ RMbM^ RL^Lb RKbK] RJ\\Jb RI\\GX RIbI[ RHZHb RGbGX RFTFb RUURWOU RVSUVRWOVNSVS R^S^T]X[[Z\\W^S_Q_M^J\\I[GXFTFSESEb_b_S^S',
        'E_JSJQLMPKRK',
        'E_ZSZQXMTKRK',
        'E_ZSZUXYT[R[',
        'E_JSJULYP[R[',
        'E_JSJQLMPKTKXMZQZS',
        'E_ZSZUXYT[P[LYJUJS',
        'E_KZK[ RLYL[ RMXM[ RNWN[ ROVO[ RPUP[ RQTQ[ RRSR[ RSRS[ RTQT[ RUPU[ RVOV[ RWNW[ RXMX[ RYLY[ RZ[ZKJ[Z[',
        'E_YZY[ RXYX[ RWXW[ RVWV[ RUVU[ RTUT[ RSTS[ RRSR[ RQRQ[ RPQP[ ROPO[ RNON[ RMNM[ RLML[ RKLK[ RJ[JKZ[J[',
        'E_YLYK RXMXK RWNWK RVOVK RUPUK RTQTK RSRSK RRSRK RQTQK RPUPK ROVOK RNWNK RMXMK RLYLK RKZKK RJKJ[ZKJK',
        'E_KLKK RLMLK RMNMK RNONK ROPOK RPQPK RQRQK RRSRK RSTSK RTUTK RUVUK RVWVK RWXWK RXYXK RYZYK RZKZ[JKZK',
        'E_PQRPTQUSTURVPUOSPQ',
        'E_JKZKZ[J[JK RK[KK RLKL[ RM[MK RNKN[ RO[OK RPKP[ RQ[QK RJ[JKRKR[J[',
        'E_JKZKZ[J[JK RYKY[ RX[XK RWKW[ RV[VK RUKU[ RT[TK RSKS[ RZKZ[R[RKZK',
        'E_JKZKZ[J[JK RYLYK RXMXK RWNWK RVOVK RUPUK RTQTK RSRSK RRSRK RQTQK RPUPK ROVOK RNWNK RMXMK RLYLK RKZKK RJKJ[ZKJK',
        'E_JKZKZ[J[JK RKZK[ RLYL[ RMXM[ RNWN[ ROVO[ RPUP[ RQTQ[ RRSR[ RSRS[ RTQT[ RUPU[ RVOV[ RWNW[ RXMX[ RYLY[ RZ[ZKJ[Z[',
        'E_JKZKZ[J[JK RR[RK',
        'E_RK[[I[RK RRUQVRWSVRURW',
        'E_J[RL RJZJ[ RKXK[ RLVL[ RMTM[ RNSN[ ROQO[ RPOP[ RQMQ[ RRKR[ RRK[[I[RK',
        'E_Z[RL RZZZ[ RYXY[ RXVX[ RWTW[ RVSV[ RUQU[ RTOT[ RSMS[ RRKR[ RRKI[[[RK',
        'C`OFTFXHZJ\\N\\SZWXYT[O[KYIWGSGNIJKHOF',
        'E_JKZKZ[J[JK RRKRSJS',
        'E_JKZKZ[J[JK RR[RSJS',
        'E_JKZKZ[J[JK RR[RSZS',
        'E_JKZKZ[J[JK RRKRSZS',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRKRSJS',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RR[RSJS',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RR[RSZS',
        'E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRKRSZS',
        'E_JKJ[ZKJK',
        'E_ZKZ[JKZK',
        'E_J[JKZ[J[',
        'E_JKZKZ[J[JK',
        'E_KKK[ RL[LK RMKM[ RN[NK ROKO[ RP[PK RQKQ[ RR[RK RSKS[ RT[TK RUKU[ RV[VK RWKW[ RX[XK RYKY[ RJKZKZ[J[JK',
        'E_OVOPUPUVOV',
        'E_PPPV RQVQP RRPRV RSVSP RTPTV ROVOPUPUVOV',
        'E_Z[ZKJ[Z[',
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        48,
        'PfUUYZ',
        'PfWTYT[V[XYZWZUXUVWT',
        'PfZKXS R^K\\S',
        'PfYFUISMSQUUZXZUXTXRZQ[R[L]N^L^FaIcMcQaU\\X',
        'PfZJYMVQ RYM`M\\T RZR]V',
        'PfbHTWWK^R',
        'PfWG_GcMcS_XWXSSSMWG',
        'PfaD[OaZ',
        'PfUD[OUZ',
        'PfaD[OaZ R^DXO^Z',
        'PfUD[OUZ RXD^OXZ',
        'PfbD^D^R',
        'PfT[X[XO',
        'PfbDbH^H^PZPZDbD',
        'PfT[TWYWYO]O][T[',
        'Pf^DbDaIaOaUbZ^Z^D',
        'PfTDXDX[T[UVUITD',
        'PfUIaI RUNaN R[N[Y',
        'PfUJaJaNUNUJ RURaRaVUVUR',
        'PfbD_H_VbZ',
        'PfTDWHWVTZ',
        'Pf\\DbDaIaOaUbZ\\Z\\D',
        'PfTDZDZ[T[UVUITD',
        'PfbD]F]XbZ R`E`Y',
        'PfTDYFYXTZ RVEVY',
        'PfbD]D][b[ R`D`[',
        'PfTDYDY[T[ RVDV[',
        'PfTOXL^RbO',
        'Pf^EbK RYE]K',
        'PfWDTJ R[DXJ',
        'PfXTTY R]TYY',
        'PfWI_I RWL_L R[L[S RWSXU^U_S RVNXNYPXRVRUPVN R^N`NaP`R^R]P^N RTNRNRSTSVX`XbSdSdNbN',
        'Pf[F[Y',
        'PfXJXU R]F]X',
        'PfVHVX R[J[V R`G`X',
        'PfaK^SUZ RWOaV',
        'PfZHVN]O_R_U]XYXWTWR_M',
        'Pf[M[P RTPbP',
        'Pf[J[M RTMbM RTQbQ',
        'Pf[I[L RTLbL RTPbP RTTbT',
        'PfXLWOTR RWObO R`O_VV[ RVQ[S_Y',
        'PfT\\W\\Y^YaWcTcRaR^T\\',
        'PfTAWAYCYFWHTHRFRCTA',
        'Pf_AbAdCdFbH_H]F]C_A',
        'Pf_\\b\\d^dabc_c]a]^_\\',
        'PfgOjOlQlTjVgVeTeQgO',
        'PfgKjKlMlPjRgRePeMgK RgTjTlVlYj[g[eYeVgT',
        'PfSQVMYQ\\M_QbM',
        'Pf]DWP]Z',
        'Pf]I`L R`HcK R]DWP]Z',
        'Pf_GWY',
        'Pf_MaP RbMdP R_GWY',
        'PfVH_X',
        'PfWG_GcMcS_XWXSSSMWG RWK_K RWO_O R[O[U',
        'PfUFZY R[FUY R\\FaY RaF\\Y',
        'PfULaL R[E[Y',
        'PfTLbL RXEXY R^E^Y',
        'PfTNbN RWGWVUY R[I[V R_H_Y',
        'PfXI^N\\O RXP^U',
        'PfUJaJaWUWUJ RaJUW',
        'PfTLWHZM]JbW',
        'PfTIVI RXIZI R\\I^I R`IbI RbK RbMbO RbQbS RbUbW R`W R^W\\W RZWXW RVWTWTU RTSTQ RTOTM RTKTI RWM[K]N`L RWQ_Q RWT_T R\\PYV',
        'PfUHaHaYUYUH R_JWW RWJ_W',
        48,
        'PfVO]O RYLYTZY R\\QXYWYVXVUZR^R`U`W]Z',
        'PfTI^H RYEXPZY R]LZUVZTUXP^NaRaX][',
        'PfVPVWX[ZX R]Q`W',
        'Pf^J`NaS RTHTOUTWZZT',
        'PfZJ]L RWO]N_Q^VZ[',
        'PfXD]F RUM\\J_M_S]XXZ',
        'PfZN]P RXR^RX[ R[W]W][`[',
        'PfYE]H RWL^KV[ RYU]R]Z`Z',
        'PfUQ[Q RXNX[UYUWZT^T`W`Y[[ R]O`R',
        'PfTJ[I RWEWYTWTSZP^QaS`X[Y R^HaL',
        'PfSLZK\\OZZWY RXDTZ R]IaQ',
        'PfSLZK\\OZZWX RXDTY R]H`Q R`JbM RcIeL',
        'PfVI^G RUNaK RYD]SZS RVTVWXY\\Z',
        'PfVI^G RUNaK RYD]SZS RVTVWXY\\Z R_DaG RbCdF',
        'Pf]EXO]Z',
        'Pf]EXO]Z R_IaL RbHdK',
        'PfZLaL RVDUKURUVVYXS R^E_M_S^W\\Z',
        'PfZLaL RVDUKURUVVYXS R^E_M_S^W\\Z RaEcH RdDfG',
        'PfWG^G[J RWPUUWZ`Z',
        'PfWG^G[J RWPUUWZ`Z R`DbG RcCeF',
        'PfTK`I RYE_R[Q RVRVVXY]Z',
        'PfTK`I RYE_R[Q RVRVVXY]Z R_DaG RbCdF',
        'PfWEWVXYZ[][`YaU',
        'PfWEWVXYZ[][`YaU R\\L^O R_KaN',
        'PfSJaJ R]E]S\\WX[ R\\OZMYMWPWRYSZS\\Q',
        'PfSJaJ R]E]S\\WX[ R\\OZMYMWPWRYSZS\\Q R`DbG RcCeF',
        'PfTMbL R^E^S\\R RWGWZ`Z',
        'PfTMbL R^E^S\\R RWGWZ`Z R`EbH RcDeG',
        'PfWF_EXM RTNaL R_M[PYRYU[X^Z',
        'PfWF_EXM RTNaL R_M[PYRYU[X^Z RaDcG RdCfF',
        'PfTI[I RYDTY RZN`N RYSZW\\YaY',
        'PfTI[I RYDTY RZN`N RYT[YaY R_GaJ RbFdI',
        'PfTI^I RXDUSYO]O_R_V\\YX[',
        'PfTI^I RXDUSYO]O_R_V\\YX[ R^E`H RaDcG',
        'PfTO]M`NaR_UYX',
        'PfSL]I`JaMaP`S]VWX',
        'PfSL]I`JaMaP`S]VWX R`EbH RcDeG',
        'PfTIaG R_H[KYPYV[Y^Z',
        'PfTIaG R_H[KYPYV[Y^Z R`CbF RcBeE',
        'Pf_KWQUSUWWZ_Z RWDXIZN',
        'Pf_KWQUSUWWZ_Z RWDXIZN R_GaJ RbFdI',
        'PfTIZI RXDTU R_HbL R]L]X[YXXXT[SaX',
        'PfZHaH RUDTLTRUYWR RZSZW[XaX',
        'PfUGXW R[EXTUXSUTQWK]JaNaV^Z\\ZZW\\TbY',
        'PfWEWZ RTJWJWK RSVZK^IaJbNaU^Y\\YZXZU]TbX',
        'Pf[GWWTTTLVH[F_GbLbRaV\\Y',
        'PfYIaI R^E^YYXYT\\SaW RUETKTQUYVR',
        'PfYIaI R^E^YYXYT\\SaW RUETKTQUYVR R`EbH RcDeG',
        'PfYIaI R^E^YYXYT\\SaW RUETKTQUYVR RbDcDdEdFcGbGaFaEbD',
        'PfSKYGUNUTVXXZ[Y\\W]S^M]GbO',
        'PfSKYGUNUTVXXZ[Y\\W]S^M]GbO R`EbH RcDeG',
        'PfSKYGUNUTVXXZ[Y\\W]S^M]GbO RbEcEdFdGcHbHaGaFbE',
        'PfYE]H RZK[Q]U\\YYYWW RVPTX R_QaW',
        'PfYE]H RZK[Q]U\\YYYWW RVPTX R_QaW R_DaG RbCdF',
        'PfYE]H RZK[Q]U\\YYYWW RVPTX R_QaW R`DaDbEbFaG`G_F_E`D',
        'PfTRYKbS',
        'Pf^J`M RaIcL RTRYKbS',
        'Pf_I`IaJaK`L_L^K^J_I RTRYKbS',
        'PfYF`F RYL`L R^F^ZZYZW\\UbX RUETKTQUZWS',
        'PfYF`F RYL`L R^F^[ZYZW\\UbX RUETKTQUZWS RaCcF RdBfE',
        'PfYF`F RYL`L R^F^[ZYZW\\UbX RUETKTQUZWS RcCdCeDeEdFcFbEbDcC',
        'PfTH`H RVM^M R[D[YXYUWVUZT`W',
        'PfVG\\GZNVXTUTRWP[PbT R_K_Q^U[Y',
        'PfSHYH RWEVVXZ^Z_V_Q RVRUTTTSRSPTNUNVP R]IaN',
        'PfUHYX R[FYVVZSVSRWM[K_MbRaW]Z',
        'PfYDXVYZ[[^[`ZaV`P RTI\\I RUO\\O',
        'PfUR]N`O`Q_S\\T RVL[[ RYK[M',
        'PfSO_KaLbP_S\\S RUG[[ RYE\\H',
        'PfTLTVWP\\MaQaV]YYV R]J]R[[',
        'PfULUXXP[M_MbPbU_W\\WZU R]J]Y[[',
        'Pf[N[ZVYVVYU`X R[Q_Q',
        'Pf[E[[WZUXUVWTaY R[K`J',
        'PfYE]H RXIVUYQ]P`S_XY[',
        'Pf^E^R]VYZ RWEVJVNWQYN',
        'PfWF_EVS[O`OaRaW][Y[XWZU^Y',
        'PfWEWZ RTJXIWJ RSV\\I_I`L_S_YbU',
        'PfXG^FWT[O`OaRaW^YZZ',
        'PfWIWZ RULXLWN RUU[M^MaNaT_W[Y',
        'PfWEWZ RTKXJWL RSVYN[K_KaMbQ`U[Y',
        'PfWG]FWZUUVQZM^NaQaX][ZY[V_X',
        'PfXE^EVN R\\K`M`QZTWRXP[QTY RVWXW[Z R]W_WaY',
        'PfUH^H RZDUSYM[O\\U R`NWUWXZ[_[',
        'Pf[EU[ZQ\\Q^[_[bV',
        'PfXD]F RUM\\J_M_S]XXZ R`FbI RcEeH',
        'PfUO\\N]P\\YYW RYJUY R^LaQ',
        'PfYP`O RUKTQTUVZWW R]L]V\\X[[',
        48,
        48,
        'Pf^E`H RaDcG',
        'PfaDbDcEcFbGaG`F`EaD',
        'PfSEUH RVDXG',
        'PfTDUDVEVFUGTGSFSETD',
        'PfYI`P\\R',
        'PfYI`P\\R R^G`J RaFcI',
        'PfZJ`J R[EUW RXP^P`S_X\\[YZ',
        'PfTLbL RTTbT',
        'PfVK`K_N]Q R[N[RZUXX',
        'PfTGbGaI_L\\N RZJZQZSYVW[',
        'Pf[P[Z R^J\\NYQVS',
        'Pf[L[[ R`E^H[LWOTQ',
        'PfZHZL RVOVL_L_O^S]U[WXY',
        'Pf[D[H RUOUHaH`N_Q]U[XWZ',
        'PfWL_L R[L[W RVW`W',
        'PfUIaI RTWbW R[I[W',
        'PfWO`O R]K]Z[Y R\\O[RYUVX',
        'PfUKbK R^D^Z[Y R]K[PXSTW',
        'PfUJaJ`Y]W RZCZJZOYSWVUY',
        'PfUJaJ`Y]W RZCZJZOYSWVUY R_EaH RaCcF',
        'PfVL^J RUSaP RYD]Z',
        'Pf]E_G R`DbF RVL^J RUSaP RYD]Z',
        'PfZDYIWLUP RZH`H`L_P]T[WWZ',
        'PfZDYIWLUO RZGaG`L_P]T[WWZ R`DbF RcCeE',
        'PfWKbK RXDWHUMTP R]K]P\\SZVWZ',
        'PfWKbK RXDWHUMTQ R]K]P\\SZVWZ R^G`I RaFcH',
        'PfUIaIaWUW',
        'Pf`FbH RcEeG RUIaIaWUW',
        'PfTKbK RWEWR R_D_K_O^S]U[XYZ',
        'PfTKbK RWEWR R_D_K_O^S]U[XYZ RaDbF RdCeE',
        'PfWFZI RULXO RUYZW]U_SbK',
        'PfWFZI RULXO RUYZW]U_SbK R_GaI RbFdH',
        'PfUF^F]L[PYSWVTY R[Q]T`Y',
        'PfUF^F]L[OYSWVTY R[Q]T`Y R`EbG RcDeF',
        'PfULbJ^R RYEYXaX',
        'Pf_EaG RbDdF RULbJ^R RYDYXaX',
        'PfUFWL R`F`L_P^S\\VWY',
        'PfaG`L_P^T\\WXZ RaDcF RdCfE RUGWM',
        'PfXL]R RYDXHWLUP RYH`H_L^P]T[WXZ',
        'PfXL]R RYDXHWLUP RYH`H_L^P]T[WXZ R`EbG RcDeF',
        'PfTNbN R_E]FZGVH R\\G\\M[QZUYWVZ',
        'PfTNbN R_E]FZGVH R\\G\\M[QZUYWWZ R`DbF RcCeE',
        'PfULWQ RZK[P R`L`Q_T\\WYY',
        'PfUGWN RYF[L R`G`M_Q]U[WXY',
        'PfUGWN RYF[L R`G`M_Q]U[WXY RaEcG RdDfF',
        'PfWG_G RTMbM R[M[RYVVZ',
        'Pf`EbG RcDeF RWG_G RTMbM R[M[RYVVZ',
        'Pf[D[Z R[MaR',
        'Pf_KaM RbJdL R[D[Z R[MaR',
        'PfTLbL R[D[K[QZTXWVZ',
        'PfUKaK RSWcW',
        'PfXM_W RWF`F_L^P\\UZWVZ',
        'PfYD]G R[P[[ R]QaU RVH`H^L\\OYRTU',
        'Pf_F^L]QZUVY',
        'Pf^JbV RYJXOVSTV',
        'Pf^JbV RYJXOVSTV R_HaJ RbGdI',
        'Pf^JbV RYJXOVSTV R`GaGbHbIaJ`J_I_H`G',
        'PfUFUYaY R`J\\MYNVO',
        'PfUFUYaY R`J\\MYNVO R`HbJ RcGeI',
        'PfUFUYaY R`J\\MYNVO RaFbFcGcHbIaI`H`GaF',
        'PfUH`H`M_R]UZWVY',
        'PfUH`H`M_R]UZWVY RaFcH RdEfG',
        'PfUH`H`M_R]UZWVY RbEcEdFdGcHbHaGaFbE',
        'PfTRYJbV',
        'Pf]K_M R`JbL RTRYJbV',
        'Pf_K`KaLaM`N_N^M^L_K RTRYJbV',
        'PfUKaK R[E[ZXY R^OaW RWOVRUTTW',
        'PfUKaK R[E[ZXY R^OaW RWOVRUTTW R`GbI RcFeH',
        'PfUKaK R[E[ZXY R^OaW RWOVRUTTW RaFbFcGcHbIaI`H`GaF',
        'PfTJaJ_N]Q[S RWPZS[U]X',
        'PfWFaJ RWM_P RUT`Y',
        'Pf[FUY_W R]PaZ',
        'Pf`E_J]OZSXUTX RXKZM]Q`U',
        'PfVG`G RSOcO RZGZY`Y',
        'PfUOaL^R RXI[Z',
        'PfXE[Z RTMaI`L_O^Q',
        'PfXL^L^V RVVaV',
        'PfVI`I_W RSWcW',
        'PfWL_L_XWX RWR_R',
        'PfUHaHaXUX RUPaP',
        'PfVG`G RTLaLaQ_T\\WXZ',
        'PfXEXP R_E_M_Q]U\\WYZ',
        'PfWGWOVSUVTY R[E[Y]W_TaP',
        'PfWEWX[W^U`SbO',
        'PfUHUV RUHaHaVUV',
        'PfVPVJ`J_P]UYZ',
        'PfUGUN RaG`M_Q^U\\XYZ RUGaG',
        'PfWJbJ RWJWS RSScS R]D]Z',
        'PfVIaI]P R[L[W RSWcW',
        'PfVM`M RUF`F`L`O_S]VZXVZ',
        'PfUHYL RUXZW]T_QaJ',
        'Pf[D[H RUOUHaH`N_Q]U[XWZ RaEcG RdDfF',
        'PfWM_M^Y\\X R[IZNYSWX',
        'PfYMaM RYIXMWPUS R_M^Q]T\\WZZ',
        'PfaEcG RdDfF RUGUN RaG`N`Q^U\\WYZ RUGaG',
        'Pf`GbI RcFeH RWJbJ RWJWS RSScS R]D]Z',
        'Pf`FbH RcEeG RVIaI]P R[L[W RSWcW',
        'PfVM`M RUF`F`L`O_S]VZXVZ RaEcG RdDfF',
        'PfZP\\P]Q]S\\TZTYSYQZP',
        'PfSPcP',
        'PfWK^U',
        'Pf\\M^O R_KaM RWK^U',
        'PfVF`F`Y',
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        23,
        'PoROlO',
        'PoRFlF RX[`[ R`F`[',
        'PoRFlF R^[e[ RZFVQ RWNiNfZ',
        'Po\\D\\[j[jW RSOkK',
        'PoR[l[ R_D_[',
        'PoRFlF R_F_[',
        'PoRGlG R[UU[ R^LYW R_G\\T',
        'PoRFlF R\\F[PXVT[ R\\NiMiTg[`[',
        'PoRIlI RWLZS^WcYj[ RbDbLaT\\XYZS[',
        'PoTFjF RVPhP RR[l[',
        'Po^MjM RR[l[ R^D^[',
        'PoRElE R^E^[ R^KjQ',
        'PoSGlG RfFf[ RXVR[ RYFYPXV',
        'PoRElE R`H`[ RaGXPRS RaLiOlS',
        'PoYHiH RRTlT R\\[d[ RYCWNgNeZ',
        'PoRElE RURjR Rb[h[ RUJUU R_E_R R_KkKjRi[',
        'PoRElE R_KjK Rb[i[ R_E_P RUQlQi[ RVITR',
        'PoROlO RR[l[ R[FZNX[ RUFgFf[',
        'PoaXhX RR[l[ R`PcT RXUSW R^NVV RVK`P RaH^O RTFkFkNiX',
        'PoTGjG RRLlL ReS`X RYQhQbW R^C\\JXQ RYWeZ',
        'PoWLgL RWTgT RR[l[ RWEW[ RWEgEg[',
        'PoSFkF RR[l[ R`I`Y RcMfOkS RaF`IXQRS',
        'PoRJlJ R_RgR RWYkY RWDW[ R_C_T RgDgT',
        'PoRKlK RWYgY RWCW[ R_C_Y RgCg[',
        'PoWNkN RR[l[ RWGW[ RdNd[ RhEWG',
        'PoRElE Re[j[ RSKS[ RSKkKk[ R_F^PZUVV R^NgV',
        'PoR[l[ R[D[[ RcDc[ RTKXS RjKfS',
        'PoR[l[ RhTlX RaT\\X RYL\\O^T ReMiV RXOTW RcN_W RdHgS RYEWS RdDbR',
        'PoRGlG RUPjP R[[`[ R`K`[ ReSlY RYKUO RXTRZ R\\CYL',
        'Po`VkV RTV]V RR[l[ RkJgN RbJ`NhN`V R]J\\N RVKTO[OTV RZDVM RfDbL',
        'PoYX_X RS[k[ R_J_X RVEgEdG_J RRL[LXQSV RjJgMbN R`JbOgTlV',
        'PoSEkE RUJiJ RRPlP RZZjZ RXZhZ RRZeZ R_E_P ReTl[ R[PWZ',
    ];
var Y = class s extends yt {
    static {
        l(this, 'StrokeFont');
    }
    static {
        this.overbar_position_factor = 1.4;
    }
    static {
        this.underline_position_factor = -0.16;
    }
    static {
        this.font_scale = 1 / 21;
    }
    static {
        this.font_offset = -10;
    }
    static default() {
        return this.instance || (this.instance = new s()), this.instance;
    }
    #e = new Map();
    #t = [];
    constructor() {
        super('stroke'), this.#r();
    }
    #r() {
        for (let t of Ds) this.#t.push($s(t));
        for (let t = 0; t < 256; t++) this.#i(t);
    }
    #i(t) {
        let e = N3[t];
        if (G(e)) this.#e.set(t, $s(e));
        else if (le(e)) {
            let r = this.#t[e];
            this.#e.set(t, r);
        } else throw new Error(`Invalid glyph data for glyph ${t}: ${e}`);
        N3[t] = void 0;
    }
    get_glyph(t) {
        let e = V3(t) - V3(' ');
        return e < 0 || e > N3.length ? this.get_glyph('?') : (this.#e.has(e) || this.#i(e), this.#e.get(e));
    }
    get_line_extents(t, e, r, i, n) {
        let o = super.get_line_extents(t, e, r, i, n),
            c = r * 1.25 * 2;
        return (o.x += c), (o.y += c), o;
    }
    compute_underline_vertical_position(t) {
        return t * s.underline_position_factor;
    }
    compute_overbar_vertical_position(t) {
        return t * s.overbar_position_factor;
    }
    get_interline(t, e = 1) {
        return t * e * s.interline_pitch_ratio;
    }
    get_text_as_glyphs(t, e, r, i, n, o, c) {
        let V = [],
            S = r.copy(),
            y = e.copy(),
            v = c.italic ? s.italic_tilt : 0;
        (c.subscript || c.superscript) &&
            ((y = y.multiply(0.7)), c.subscript ? (S.y += y.y * 0.3) : (S.y -= y.y * 0.5));
        for (let ye of t)
            switch (ye) {
                case '	':
                    {
                        let C = Math.round(y.x * 3.28),
                            se = (S.x - o.x) % C;
                        S.x += C - se;
                    }
                    break;
                case ' ':
                    S.x += Math.round(y.x * 0.6);
                    break;
                default:
                    {
                        let C = this.get_glyph(ye),
                            se = C.bbox.end.multiply(y);
                        V.push(C.transform(y, S, v, i, n, o)), v && (se.x -= se.y * v), (S.x += Math.round(se.x));
                    }
                    break;
            }
        let te = !1,
            X = new d(0, 0),
            x = y.x * 0.1;
        if (
            (c.overbar
                ? ((te = !0), (X.y = this.compute_overbar_vertical_position(y.y)))
                : c.underline && ((te = !0), (X.y = this.compute_underline_vertical_position(y.y))),
            te)
        ) {
            c.italic && (X.x = X.y * s.italic_tilt);
            let ye = new d(r.x + X.x + x, S.y - X.y),
                C = new d(S.x + X.x - x, S.y - X.y),
                se = new y2([[ye, C]], O.from_points([ye, C]));
            V.push(se.transform(new d(1, 1), new d(0, 0), 0, i, n, o));
        }
        let rt = new O();
        return (
            (rt.start = r),
            (rt.end = new d(S.x + X.x - Math.round(y.x * 0.2), S.y + Math.max(y.y, X.y * s.overbar_position_factor))),
            { bbox: rt, glyphs: V, cursor: new d(S.x, r.y) }
        );
    }
};
function V3(s) {
    return s.charCodeAt(0);
}
l(V3, 'ord');
function Bs(s) {
    return V3(s) - V3('R');
}
l(Bs, 'decode_coord_val');
function $n(s) {
    return [Bs(s[0]), Bs(s[1])];
}
l($n, 'decode_coord');
function $s(s) {
    let t = 0,
        e = 0,
        r = 0,
        i = 0,
        n = 0,
        o = [],
        c = null;
    for (let m = 0; m < s.length; m += 2) {
        let b = [s[m], s[m + 1]],
            M = $n(b);
        if (m < 2) (t = M[0] * Y.font_scale), (e = M[1] * Y.font_scale), (r = e - t);
        else if (b[0] == ' ' && b[1] == 'R') c = null;
        else {
            let f = new d(M[0] * Y.font_scale - t, (M[1] + Y.font_offset) * Y.font_scale);
            c == null && ((c = []), o.push(c)), (i = Math.min(i, f.y)), (n = Math.max(n, f.y)), c.push(f);
        }
    }
    let u = new O(0, i, r, n - i);
    return new y2(o, u);
}
l($s, 'decode_glyph');
var $ = class {
    constructor(t) {
        this.text_pos = new d(0, 0);
        this.attributes = new f3();
        this.text = t;
    }
    static {
        l(this, 'EDAText');
    }
    apply_effects(t) {
        (this.attributes.h_align = t.justify.horizontal),
            (this.attributes.v_align = t.justify.vertical),
            (this.attributes.mirrored = t.justify.mirror),
            (this.attributes.italic = t.font.italic),
            (this.attributes.bold = t.font.bold),
            this.attributes.size.set(t.font.size.multiply(1e4)),
            (this.attributes.stroke_width = (t.font.thickness ?? 0) * 1e4),
            (this.attributes.stroke_width = this.get_effective_text_thickness(1588)),
            (this.attributes.color = t.font.color);
    }
    apply_at(t) {
        (this.text_pos = t.position.multiply(1e4)), (this.text_angle = W.from_degrees(t.rotation));
    }
    get shown_text() {
        return this.text;
    }
    get_effective_text_thickness(t) {
        let e = this.text_thickness;
        return (
            e < 1 && ((e = t ?? 0), this.bold ? (e = jn(this.text_width)) : e <= 1 && (e = zn(this.text_width))),
            (e = qn(e, this.text_width, !0)),
            e
        );
    }
    get text_angle() {
        return this.attributes.angle;
    }
    set text_angle(t) {
        this.attributes.angle = t;
    }
    get italic() {
        return this.attributes.italic;
    }
    get bold() {
        return this.attributes.bold;
    }
    get visible() {
        return this.attributes.visible;
    }
    get mirrored() {
        return this.attributes.mirrored;
    }
    get multiline() {
        return this.attributes.multiline;
    }
    get h_align() {
        return this.attributes.h_align;
    }
    set h_align(t) {
        this.attributes.h_align = t;
    }
    get v_align() {
        return this.attributes.v_align;
    }
    set v_align(t) {
        this.attributes.v_align = t;
    }
    get line_spacing() {
        return this.attributes.line_spacing;
    }
    get text_size() {
        return this.attributes.size;
    }
    get text_width() {
        return this.attributes.size.x;
    }
    get text_height() {
        return this.attributes.size.y;
    }
    get text_color() {
        return this.attributes.color;
    }
    get keep_upright() {
        return this.attributes.keep_upright;
    }
    get text_thickness() {
        return this.attributes.stroke_width;
    }
    get_text_box(t, e) {
        let r = this.text_pos.copy(),
            i = new O(0, 0, 0, 0),
            n = [],
            o = this.shown_text,
            c = this.get_effective_text_thickness();
        this.multiline &&
            ((n = o.split(`
`)),
            n.length && (t != null && t < n.length ? (o = n[t]) : (o = n[0])));
        let u = Y.default(),
            p = this.text_size.copy(),
            m = this.bold,
            b = this.italic,
            M = u.get_line_extents(o, p, c, m, b),
            f = 0,
            V = M.copy();
        if (
            (this.multiline && t && t < n.length && (r.y -= Math.round(t * u.get_interline(p.y))),
            o.includes('~{') && (f = M.y / 14),
            e && (r.y = -r.y),
            (i.start = r),
            this.multiline && !t && n.length)
        ) {
            for (let y of n.slice(1)) (M = u.get_line_extents(y, p, c, m, b)), (V.x = Math.max(V.x, M.x));
            V.y += Math.round((n.length - 1) * u.get_interline(p.y));
        }
        (i.w = V.x), (i.h = V.y);
        let S = this.italic ? Math.round(p.y * yt.italic_tilt) : 0;
        switch (this.h_align) {
            case 'left':
                this.mirrored && (i.x = i.x - (i.w - S));
                break;
            case 'center':
                i.x = i.x - (i.w - S) / 2;
                break;
            case 'right':
                this.mirrored || (i.x = i.x - (i.w - S));
                break;
        }
        switch (this.v_align) {
            case 'top':
                break;
            case 'center':
                i.y = i.y - (i.h + f) / 2;
                break;
            case 'bottom':
                i.y = i.y - (i.h + f);
                break;
        }
        return i;
    }
};
function jn(s) {
    return Math.round(s / 5);
}
l(jn, 'get_bold_thickness');
function zn(s) {
    return Math.round(s / 8);
}
l(zn, 'get_normal_thickness');
function qn(s, t, e) {
    let r = Math.round(t * (e ? 0.25 : 0.18));
    return Math.min(s, r);
}
l(qn, 'clamp_thickness');
var g3 = class extends $ {
    static {
        l(this, 'LibText');
    }
    constructor(t) {
        super(t);
    }
    get shown_text() {
        return this.text;
    }
    get bounding_box() {
        let t = this.get_text_box(void 0, !0).mirror_vertical(),
            e = this.text_pos,
            r = t.start,
            i = t.end,
            n = this.text_angle.negative();
        return (
            (r = n.rotate_point(r, e)),
            (i = n.rotate_point(i, e)),
            (t = O.from_points([r, i])),
            (t = t.mirror_vertical()),
            t
        );
    }
    get world_pos() {
        let t = this.bounding_box,
            e = t.center;
        if (this.attributes.angle.is_vertical)
            switch (this.attributes.h_align) {
                case 'left':
                    e.y = t.y2;
                    break;
                case 'center':
                    e.y = (t.y + t.y2) / 2;
                    break;
                case 'right':
                    e.y = t.y;
                    break;
            }
        else
            switch (this.attributes.h_align) {
                case 'left':
                    e.x = t.x;
                    break;
                case 'center':
                    e.x = (t.x + t.x2) / 2;
                    break;
                case 'right':
                    e.x = t.x2;
                    break;
            }
        return e;
    }
    apply_symbol_transformations(t) {
        for (let e = 0; e < t.rotations; e++) this.rotate(new d(0, 0), !0);
        t.mirror_x && this.mirror_vertically(new d(0, 0)),
            t.mirror_y && this.mirror_horizontally(new d(0, 0)),
            (this.text_pos = this.text_pos.add(t.position.multiply(new d(1e4, -1e4))));
    }
    normalize_justification(t) {
        let e = new d(0, 0),
            r = this.get_text_box();
        this.text_angle.is_horizontal
            ? (this.h_align == 'left' ? (e.x = r.w / 2) : this.h_align == 'right' && (e.x = -(r.w / 2)),
              this.v_align == 'top' ? (e.y = -(r.h / 2)) : this.v_align == 'bottom' && (e.y = r.h / 2))
            : (this.h_align == 'left' ? (e.y = r.w / 2) : this.h_align == 'right' && (e.y = -(r.w / 2)),
              this.v_align == 'top' ? (e.x = r.h / 2) : this.v_align == 'bottom' && (e.x = -(r.h / 2))),
            t && (e = e.multiply(-1)),
            (this.text_pos = this.text_pos.add(e));
    }
    rotate(t, e = !1) {
        this.normalize_justification(!1);
        let r = W.from_degrees(e ? -90 : 90);
        (this.text_pos = r.rotate_point(this.text_pos, t)),
            this.text_angle.is_horizontal
                ? (this.text_angle.degrees = 90)
                : ((this.h_align = Xt(this.h_align, 'left', 'right')),
                  (this.v_align = Xt(this.v_align, 'top', 'bottom')),
                  (this.text_angle.degrees = 0)),
            this.normalize_justification(!0);
    }
    mirror_horizontally(t) {
        this.normalize_justification(!1);
        let e = this.text_pos.x;
        (e -= t.x),
            (e *= -1),
            (e += t.x),
            this.text_angle.is_horizontal
                ? (this.h_align = Xt(this.h_align, 'left', 'right'))
                : (this.v_align = Xt(this.v_align, 'top', 'bottom')),
            (this.text_pos.x = e),
            this.normalize_justification(!0);
    }
    mirror_vertically(t) {
        this.normalize_justification(!1);
        let e = this.text_pos.y;
        (e -= t.y),
            (e *= -1),
            (e += t.y),
            this.text_angle.is_horizontal
                ? (this.v_align = Xt(this.v_align, 'top', 'bottom'))
                : (this.h_align = Xt(this.h_align, 'left', 'right')),
            (this.text_pos.y = e),
            this.normalize_justification(!0);
    }
};
function Xt(s, t, e) {
    return s == t ? e : s == e ? t : s;
}
l(Xt, 'swap_values');
var P3 = class extends $ {
    constructor(e, r) {
        super(e);
        this.parent = r;
    }
    static {
        l(this, 'SchField');
    }
    get shown_text() {
        return this.text == '~' ? '' : this.text;
    }
    get draw_rotation() {
        let e = this.text_angle.degrees,
            r = this.parent?.transform ?? U.identity();
        return Math.abs(r.elements[1]) == 1 && (e == 0 || e == 180 ? (e = 90) : (e = 0)), W.from_degrees(e);
    }
    get position() {
        if (this.parent) {
            let e = this.text_pos.sub(this.parent.position);
            return (e = this.parent.transform.transform(e)), e.add(this.parent.position);
        }
        return this.text_pos;
    }
    get bounding_box() {
        let e = this.get_text_box();
        if (!this.parent?.is_symbol) return e;
        let r = this.parent?.position ?? new d(0, 0),
            i = this.text_pos.sub(r),
            n = e.start.sub(r),
            o = e.end.sub(r);
        (n = this.text_angle.rotate_point(n, i)),
            (o = this.text_angle.rotate_point(o, i)),
            (n.y = js(n.y, i.y)),
            (o.y = js(o.y, i.y));
        let c = this.parent?.transform ?? U.identity();
        return (e.start = c.transform(n)), (e.end = c.transform(o)), (e.start = e.start.add(r)), e;
    }
};
function js(s, t = 0) {
    return -(s - t) + t;
}
l(js, 'mirror');
var Ot = class extends $ {
    static {
        l(this, 'SchText');
    }
    constructor(t) {
        super(t);
    }
    apply_at(t) {
        super.apply_at(t), this.set_spin_style_from_angle(this.text_angle);
    }
    set_spin_style_from_angle(t) {
        switch (t.degrees) {
            default:
            case 0:
                (this.text_angle.degrees = 0), (this.h_align = 'left');
                break;
            case 90:
                (this.text_angle.degrees = 90), (this.h_align = 'left');
                break;
            case 180:
                (this.text_angle.degrees = 0), (this.h_align = 'right');
                break;
            case 270:
                (this.text_angle.degrees = 90), (this.h_align = 'right');
                break;
        }
        this.v_align = 'bottom';
    }
    get shown_text() {
        return this.text;
    }
};
var ae = class {
        constructor(t, e, r = !0, i = !1, n = h.white) {
            this.highlighted = !1;
            this.interactive = !1;
            this.bboxes = new Map();
            (this.#e = r),
                (this.layer_set = t),
                (this.name = e),
                (this.color = n),
                (this.interactive = i),
                (this.items = []);
        }
        static {
            l(this, 'ViewLayer');
        }
        #e;
        dispose() {
            this.clear();
        }
        clear() {
            this.graphics?.dispose(), (this.graphics = void 0), (this.items = []), this.bboxes.clear();
        }
        get visible() {
            return this.#e instanceof Function ? this.#e() : this.#e;
        }
        set visible(t) {
            this.#e = t;
        }
        get bbox() {
            return O.combine(this.bboxes.values());
        }
        *query_point(t) {
            for (let e of this.bboxes.values()) e.contains_point(t) && (yield e);
        }
    },
    Ut = class {
        static {
            l(this, 'ViewLayerSet');
        }
        #e = [];
        #t = new Map();
        #r;
        constructor() {
            this.#r = new ae(this, ':Overlay', !0, !1, h.white);
        }
        dispose() {
            this.#r.dispose();
            for (let t of this.#e) t.dispose();
            (this.#e.length = 0), this.#t.clear();
        }
        add(...t) {
            for (let e of t) this.#e.push(e), this.#t.set(e.name, e);
        }
        *in_order() {
            for (let t of this.#e) yield t;
        }
        *in_display_order() {
            for (let t = this.#e.length - 1; t >= 0; t--) {
                let e = this.#e[t];
                e.highlighted || (yield e);
            }
            for (let t = this.#e.length - 1; t >= 0; t--) {
                let e = this.#e[t];
                e.highlighted && (yield e);
            }
            yield this.#r;
        }
        by_name(t) {
            return this.#t.get(t);
        }
        *query(t) {
            for (let e of this.#e) t(e) && (yield e);
        }
        get overlay() {
            return this.#r;
        }
        highlight(t) {
            let e = [];
            t && (e = Ns(t).map((r) => (r instanceof ae ? r.name : r)));
            for (let r of this.#e) e.includes(r.name) ? (r.highlighted = !0) : (r.highlighted = !1);
        }
        is_any_layer_highlighted() {
            for (let t of this.#e) if (t.highlighted) return !0;
            return !1;
        }
        *grid_layers() {
            yield this.by_name(':Grid');
        }
        *interactive_layers() {
            for (let t of this.in_order()) t.interactive && t.visible && (yield t);
        }
        *query_point(t) {
            for (let e of this.interactive_layers()) for (let r of e.query_point(t)) yield { layer: e, bbox: r };
        }
        *query_item_bboxes(t) {
            for (let e of this.interactive_layers()) {
                let r = e.bboxes.get(t);
                r && (yield r);
            }
        }
        get bbox() {
            let t = [];
            for (let e of this.in_order()) t.push(e.bbox);
            return O.combine(t);
        }
    };
var O2 = new ce('kicanvas:project'),
    be = class {
        constructor(t, e) {
            this.view_painter = t;
            this.gfx = e;
        }
        static {
            l(this, 'ItemPainter');
        }
        get theme() {
            return this.view_painter.theme;
        }
    },
    Ee = class {
        constructor(t, e, r) {
            this.gfx = t;
            this.layers = e;
            this.theme = r;
        }
        static {
            l(this, 'DocumentPainter');
        }
        #e = new Map();
        set painter_list(t) {
            for (let e of t) for (let r of e.classes) this.#e.set(r, e);
        }
        get painters() {
            return this.#e;
        }
        paint(t) {
            O2.debug('Painting'), O2.debug('Sorting paintable items into layers');
            for (let e of t.items()) {
                let r = this.painter_for(e);
                if (!r) {
                    O2.warn(`No painter found for ${e?.constructor.name}`);
                    continue;
                }
                for (let i of r.layers_for(e)) this.layers.by_name(i)?.items.push(e);
            }
            for (let e of this.paintable_layers())
                O2.debug(`Painting layer ${e.name} with ${e.items.length} items`), this.paint_layer(e);
            O2.debug('Painting complete');
        }
        *paintable_layers() {
            yield* this.layers.in_display_order();
        }
        paint_layer(t) {
            let e = new Map();
            this.gfx.start_layer(t.name);
            for (let r of t.items) {
                this.gfx.start_bbox(), this.paint_item(t, r);
                let i = this.gfx.end_bbox(r);
                e.set(r, i);
            }
            (t.graphics = this.gfx.end_layer()), (t.bboxes = e);
        }
        paint_item(t, e, ...r) {
            this.painter_for(e)?.paint(t, e, ...r);
        }
        painter_for(t) {
            return this.painters.get(t.constructor);
        }
        layers_for(t) {
            return this.painters.get(t.constructor)?.layers_for(t) || [];
        }
    };
function U2(s, t, e, r = !0) {
    let i = s.top_left,
        n = s.top_right,
        o = s.bottom_left,
        c = s.bottom_right,
        u = s.margin_bbox;
    switch (e) {
        case 'ltcorner':
            t = i.add(t);
            break;
        case 'rbcorner':
            t = c.sub(t);
            break;
        case 'lbcorner':
            t = o.add(new d(t.x, -t.y));
            break;
        case 'rtcorner':
            t = n.add(new d(-t.x, t.y));
            break;
    }
    if (!(r && !u.contains_point(t))) return t;
}
l(U2, 'offset_point');
var _i = class extends be {
        constructor() {
            super(...arguments);
            this.classes = [M2];
        }
        static {
            l(this, 'LinePainter');
        }
        layers_for(e) {
            return [':DrawingSheet'];
        }
        paint(e, r) {
            let i = r.parent,
                [n, o] = [r.incrx ?? 0, r.incry ?? 0];
            for (let c = 0; c < r.repeat; c++) {
                let u = new d(n * c, o * c),
                    [p, m] = [
                        U2(i, r.start.position.add(u), r.start.anchor),
                        U2(i, r.end.position.add(u), r.start.anchor),
                    ];
                if (!p || !m) return;
                this.gfx.line(new F([p, m], r.linewidth || i.setup.linewidth, e.color));
            }
        }
    },
    Mi = class extends be {
        constructor() {
            super(...arguments);
            this.classes = [gt];
        }
        static {
            l(this, 'RectPainter');
        }
        layers_for(e) {
            return [':DrawingSheet'];
        }
        paint(e, r) {
            let i = r.parent,
                [n, o] = [r.incrx ?? 0, r.incry ?? 0];
            for (let c = 0; c < r.repeat; c++) {
                let u = new d(n * c, o * c),
                    [p, m] = [
                        U2(i, r.start.position.add(u), r.start.anchor, c > 0),
                        U2(i, r.end.position.add(u), r.end.anchor, c > 0),
                    ];
                if (!p || !m) return;
                let b = O.from_points([p, m]);
                this.gfx.line(F.from_BBox(b, r.linewidth || i.setup.linewidth, e.color));
            }
        }
    },
    fi = class extends be {
        constructor() {
            super(...arguments);
            this.classes = [f2];
        }
        static {
            l(this, 'TbTextPainter');
        }
        layers_for(e) {
            return [':DrawingSheet'];
        }
        paint(e, r) {
            let i = new $(r.shown_text);
            switch (
                ((i.h_align = 'left'), (i.v_align = 'center'), (i.text_angle = W.from_degrees(r.rotate)), r.justify)
            ) {
                case 'center':
                    (i.h_align = 'center'), (i.v_align = 'center');
                    break;
                case 'left':
                    i.h_align = 'left';
                    break;
                case 'right':
                    i.h_align = 'right';
                    break;
                case 'top':
                    i.v_align = 'top';
                    break;
                case 'bottom':
                    i.v_align = 'bottom';
                    break;
            }
            (i.attributes.bold = r.font?.bold ?? !1),
                (i.attributes.italic = r.font?.italic ?? !1),
                (i.attributes.color = e.color),
                (i.attributes.size = (r.font?.size ?? r.parent.setup.textsize).multiply(1e4)),
                (i.attributes.stroke_width = (r.font?.linewidth ?? r.parent.setup.textlinewidth) * 1e4);
            let [n, o] = [r.incrx ?? 0, r.incry ?? 0];
            for (let c = 0; c < r.repeat; c++) {
                let u = new d(n * c, o * c),
                    p = U2(r.parent, r.pos.position.add(u), r.pos.anchor);
                if (!p) return;
                if (r.incrlabel && r.text.length == 1) {
                    let m = r.incrlabel * c,
                        b = r.text.charCodeAt(0);
                    b >= '0'.charCodeAt(0) && b <= '9'.charCodeAt(0)
                        ? (i.text = `${m + b - '0'.charCodeAt(0)}`)
                        : (i.text = String.fromCharCode(b + m));
                }
                (i.text_pos = p?.multiply(1e4)),
                    this.gfx.state.push(),
                    Y.default().draw(this.gfx, i.shown_text, i.text_pos, i.attributes),
                    this.gfx.state.pop();
            }
        }
    },
    W3 = class extends Ee {
        static {
            l(this, 'DrawingSheetPainter');
        }
        constructor(t, e, r) {
            super(t, e, r), (this.painter_list = [new _i(this, t), new Mi(this, t), new fi(this, t)]);
        }
        *paintable_layers() {
            yield this.layers.by_name(':DrawingSheet');
        }
    };
var S3 = class {
        constructor(t, e, r) {
            this.min_zoom = t;
            this.spacing = e;
            this.radius = r;
        }
        static {
            l(this, 'GridLOD');
        }
    },
    T3 = class {
        constructor(
            t,
            e,
            r,
            i = new d(0, 0),
            n = h.white,
            o = h.white,
            c = [new S3(2.5, 10, 0.2), new S3(15, 1, 0.05)],
        ) {
            this.gfx = t;
            this.camera = e;
            this.layer = r;
            this.origin = i;
            this.color = n;
            this.origin_color = o;
            this.lods = c;
        }
        static {
            l(this, 'Grid');
        }
        #e = new O(0, 0, 0, 0);
        #t;
        reset() {
            (this.#t = void 0), (this.#e.w = 0), (this.#e.h = 0), this.layer.clear();
        }
        update() {
            let t;
            for (let c of this.lods) this.camera.zoom >= c.min_zoom && (t = c);
            if (!t) {
                this.reset();
                return;
            }
            let e = this.camera.bbox;
            if (this.#t == t && this.#e.contains(e)) return;
            (e = e.grow(e.w * 0.2)), (this.#t = t), (this.#e = e);
            let r = Math.round((e.x - this.origin.x) / t.spacing),
                i = Math.round((e.x2 - this.origin.x) / t.spacing),
                n = Math.round((e.y - this.origin.y) / t.spacing),
                o = Math.round((e.y2 - this.origin.y) / t.spacing);
            r > i && ([r, i] = [i, r]),
                n > o && ([n, o] = [o, n]),
                (i += 1),
                (o += 1),
                this.gfx.start_layer(this.layer.name);
            for (let c = r; c <= i; c += 1)
                for (let u = n; u <= o; u += 1) {
                    let p = new d(c * t.spacing + this.origin.x, u * t.spacing + this.origin.y);
                    this.gfx.circle(p, t.radius, this.color);
                }
            if (this.origin.x != 0 && this.origin.y != 0) {
                this.gfx.arc(this.origin, 1, new W(0), new W(2 * Math.PI), t.radius / 2, this.origin_color);
                let c = new d(1.5, 1.5);
                this.gfx.line([this.origin.sub(c), this.origin.add(c)], t.radius / 2, this.origin_color),
                    (c = new d(-1.5, 1.5)),
                    this.gfx.line([this.origin.sub(c), this.origin.add(c)], t.radius / 2, this.origin_color);
            }
            this.layer.graphics = this.gfx.end_layer();
        }
    };
var zs = 8,
    L3 = 24,
    eo = 0.005,
    qs = 1,
    en = Re.INSTANCE,
    y3 = class {
        constructor(t, e, r, i = 0.5, n = 10, o) {
            this.target = t;
            this.camera = e;
            this.callback = r;
            this.min_zoom = i;
            this.max_zoom = n;
            this.bounds = o;
            this.target.addEventListener('wheel', (b) => this.#r(b), { passive: !1 });
            let c = null,
                u = null;
            this.target.addEventListener('touchstart', (b) => {
                b.touches.length === 2 ? (c = this.#t(b.touches)) : b.touches.length === 1 && (u = b.touches);
            }),
                this.target.addEventListener('touchmove', (b) => {
                    if (b.touches.length === 2) {
                        if (c !== null) {
                            let M = this.#t(b.touches);
                            if (Math.abs(c - M) < 10) {
                                let f = (M / c) * 4;
                                c < M ? this.#n(f * -1) : this.#n(f);
                            }
                            c = M;
                        }
                    } else if (b.touches.length === 1 && u !== null) {
                        let M = u[0]?.clientX ?? 0,
                            f = u[0]?.clientY ?? 0,
                            V = b.touches[0]?.clientX ?? 0,
                            S = b.touches[0]?.clientY ?? 0;
                        Math.abs(M - V) < 100 && Math.abs(f - S) < 100 && this.#s(M - V, f - S), (u = b.touches);
                    }
                }),
                this.target.addEventListener('touchend', () => {
                    (c = null), (u = null);
                });
            let p = null,
                m = !1;
            this.target.addEventListener('mousedown', (b) => {
                (b.button === 1 || b.button === 2) && (b.preventDefault(), (m = !0), (p = new d(b.clientX, b.clientY)));
            }),
                this.target.addEventListener('mousemove', (b) => {
                    if (m && p !== null) {
                        let M = new d(b.clientX, b.clientY),
                            f = M.sub(p);
                        this.#s(-f.x, -f.y), (p = M);
                    }
                }),
                this.target.addEventListener('mouseup', (b) => {
                    (b.button === 1 || b.button === 2) && ((m = !1), (p = null));
                }),
                this.target.addEventListener('contextmenu', (b) => {
                    b.preventDefault();
                });
        }
        static {
            l(this, 'PanAndZoom');
        }
        #e;
        #t(t) {
            if (t[0] && t[1]) {
                let e = t[0].clientX - t[1].clientX,
                    r = t[0].clientY - t[1].clientY;
                return Math.sqrt(e * e + r * r);
            }
            return 0;
        }
        #r(t) {
            t.preventDefault();
            let e = t.deltaX,
                r = t.deltaY;
            en.alignControlsWithKiCad
                ? e == 0 && t.ctrlKey && ([e, r] = [r, e])
                : e == 0 && t.shiftKey && ([e, r] = [r, e]),
                t.deltaMode === WheelEvent.DOM_DELTA_LINE
                    ? ((e *= zs), (r *= zs))
                    : t.deltaMode === WheelEvent.DOM_DELTA_PAGE && ((e *= L3), (r *= L3)),
                (e = Math.sign(e) * Math.min(L3, Math.abs(e))),
                (r = Math.sign(r) * Math.min(L3, Math.abs(r))),
                en.alignControlsWithKiCad
                    ? t.shiftKey || t.ctrlKey
                        ? this.#s(-e, r)
                        : ((this.#e = this.target.getBoundingClientRect()), this.#n(r, this.#i(t)))
                    : t.ctrlKey
                      ? ((this.#e = this.target.getBoundingClientRect()), this.#n(r, this.#i(t)))
                      : this.#s(e, r),
                this.target.dispatchEvent(new MouseEvent('panzoom', { clientX: t.clientX, clientY: t.clientY }));
        }
        #i(t) {
            return new d(t.clientX - this.#e.left, t.clientY - this.#e.top);
        }
        #s(t, e) {
            let r = new d(t * qs, e * qs).multiply(1 / this.camera.zoom),
                i = this.camera.center.add(r);
            this.bounds && (i = this.bounds.constrain_point(i)),
                this.camera.center.set(i),
                this.callback && this.callback();
        }
        #n(t, e) {
            if (
                ((this.camera.zoom *= Math.exp(t * -eo)),
                (this.camera.zoom = Math.min(this.max_zoom, Math.max(this.camera.zoom, this.min_zoom))),
                e != null)
            ) {
                let r = this.camera.screen_to_world(e),
                    i = this.camera.screen_to_world(e),
                    n = r.sub(i);
                this.camera.translate(n);
            }
            this.callback && this.callback();
        }
    };
var X3 = class {
    constructor(t, e) {
        this.target = t;
        this.callback = e;
        (this.#e = new ResizeObserver(() => {
            this.callback(this.target);
        })),
            this.#e.observe(t);
    }
    static {
        l(this, 'SizeObserver');
    }
    #e;
    dispose() {
        this.#e?.disconnect(), (this.#e = void 0);
    }
};
var O3 = class {
    constructor(t, e) {
        this.renderer = t;
        this.callback = e;
        this.ready = new fe();
        (this.camera = new I2(new d(0, 0), new d(0, 0), 1, new W(0))),
            (this.#e = new X3(this.renderer.canvas, () => {
                this.#r(), this.callback();
            })),
            this.#r();
    }
    static {
        l(this, 'Viewport');
    }
    #e;
    #t;
    dispose() {
        this.#e.dispose();
    }
    #r() {
        let t = this.renderer.canvas;
        t.clientWidth > 0 &&
            t.clientHeight > 0 &&
            (this.width != t.clientWidth || this.height != t.clientHeight) &&
            ((this.width = t.clientWidth),
            (this.height = t.clientHeight),
            (this.camera.viewport_size = new d(this.width, this.height)),
            this.width && this.height && this.ready.open());
    }
    enable_pan_and_zoom(t, e) {
        this.#t = new y3(
            this.renderer.canvas,
            this.camera,
            () => {
                this.callback();
            },
            t,
            e,
        );
    }
    get view_matrix() {
        return this.camera.matrix;
    }
    set bounds(t) {
        this.#t && (this.#t.bounds = t);
    }
};
var F2 = class extends EventTarget {
    constructor(e, r = !0) {
        super();
        this.canvas = e;
        this.interactive = r;
        this.mouse_position = new d(0, 0);
        this.loaded = new fe();
        this.disposables = new nt();
        this.setup_finished = new fe();
    }
    static {
        l(this, 'Viewer');
    }
    #e;
    dispose() {
        this.disposables.dispose();
    }
    addEventListener(e, r, i) {
        return (
            super.addEventListener(e, r, i),
            {
                dispose: () => {
                    this.removeEventListener(e, r, i);
                },
            }
        );
    }
    async setup() {
        (this.renderer = this.disposables.add(this.create_renderer(this.canvas))),
            await this.renderer.setup(),
            (this.viewport = this.disposables.add(
                new O3(this.renderer, () => {
                    this.on_viewport_change();
                }),
            )),
            this.interactive &&
                (this.viewport.enable_pan_and_zoom(0.5, 190),
                this.disposables.add(
                    k(this.canvas, 'mousemove', (e) => {
                        this.on_mouse_change(e);
                    }),
                ),
                this.disposables.add(
                    k(this.canvas, 'panzoom', (e) => {
                        this.on_mouse_change(e);
                    }),
                ),
                this.disposables.add(
                    k(this.canvas, 'click', (e) => {
                        let r = this.layers.query_point(this.mouse_position);
                        this.on_pick(this.mouse_position, r);
                    }),
                )),
            this.setup_finished.open();
    }
    on_viewport_change() {
        this.interactive && this.draw();
    }
    on_mouse_change(e) {
        let r = this.canvas.getBoundingClientRect(),
            i = this.viewport.camera.screen_to_world(new d(e.clientX - r.left, e.clientY - r.top));
        (this.mouse_position.x != i.x || this.mouse_position.y != i.y) &&
            (this.mouse_position.set(i), this.dispatchEvent(new Zt(this.mouse_position)));
    }
    resolve_loaded(e) {
        e && (this.loaded.open(), this.dispatchEvent(new ie()));
    }
    on_draw() {
        if ((this.renderer.clear_canvas(), !this.layers)) return;
        let e = 0.01,
            r = this.viewport.camera.matrix,
            i = this.layers.is_any_layer_highlighted();
        for (let n of this.layers.in_display_order())
            if (n.visible && n.graphics) {
                let o = n.opacity;
                i && !n.highlighted && (o = 0.25), n.graphics.render(r, e, o), (e += 0.01);
            }
    }
    draw() {
        this.viewport &&
            window.requestAnimationFrame(() => {
                this.on_draw();
            });
    }
    on_pick(e, r) {
        let i = null;
        for (let { bbox: n } of r) {
            i = n;
            break;
        }
        this.select(i);
    }
    select(e) {
        this.selected = e;
    }
    get selected() {
        return this.#e;
    }
    set selected(e) {
        this._set_selected(e);
    }
    _set_selected(e) {
        let r = this.#e;
        (this.#e = e?.copy() || null),
            this.dispatchEvent(new D({ item: this.#e?.context, previous: r?.context })),
            ue(() => this.paint_selected());
    }
    get selection_color() {
        return h.white;
    }
    paint_selected() {
        let e = this.layers.overlay;
        if ((e.clear(), this.#e)) {
            let r = this.#e.copy().grow(this.#e.w * 0.1);
            this.renderer.start_layer(e.name),
                this.renderer.line(F.from_BBox(r, 0.254, this.selection_color)),
                this.renderer.polygon(I.from_BBox(r, this.selection_color)),
                (e.graphics = this.renderer.end_layer()),
                (e.graphics.composite_operation = 'overlay');
        }
        this.draw();
    }
    zoom_to_selection() {
        this.selected && ((this.viewport.camera.bbox = this.selected.grow(10)), this.draw());
    }
};
P([at], F2.prototype, '_set_selected', 1);
var Je = new ce('kicanvas:viewer'),
    Ft = class extends F2 {
        constructor(e, r, i) {
            super(e, r);
            this.theme = i;
        }
        static {
            l(this, 'DocumentViewer');
        }
        get grid_origin() {
            return new d(0, 0);
        }
        async load(e) {
            await this.setup_finished,
                this.document != e &&
                    (Je.info(`Loading ${e.filename} into viewer`),
                    (this.document = e),
                    this.paint(),
                    ue(async () => {
                        Je.info('Waiting for viewport'),
                            await this.viewport.ready,
                            (this.viewport.bounds = this.drawing_sheet.page_bbox.grow(50)),
                            Je.info('Positioning camera'),
                            this.zoom_to_page(),
                            this.resolve_loaded(!0),
                            this.selected && (this.selected = null),
                            this.draw();
                    }));
        }
        paint() {
            this.document &&
                ((this.renderer.background_color = this.theme.background),
                Je.info('Loading drawing sheet'),
                this.drawing_sheet || (this.drawing_sheet = _2.default()),
                (this.drawing_sheet.document = this.document),
                Je.info('Creating layers'),
                this.disposables.disposeAndRemove(this.layers),
                (this.layers = this.disposables.add(this.create_layer_set())),
                Je.info('Painting items'),
                (this.painter = this.create_painter()),
                this.painter.paint(this.document),
                Je.info('Painting drawing sheet'),
                new W3(this.renderer, this.layers, this.theme).paint(this.drawing_sheet),
                Je.info('Painting grid'),
                (this.grid = new T3(
                    this.renderer,
                    this.viewport.camera,
                    this.layers.by_name(':Grid'),
                    this.grid_origin,
                    this.theme.grid,
                    this.theme.grid_axes,
                )));
        }
        zoom_to_page() {
            (this.viewport.camera.bbox = this.drawing_sheet.page_bbox.grow(10)), this.draw();
        }
        draw() {
            this.viewport && (this.grid?.update(), super.draw());
        }
        select(e) {
            if (e != null && !(e instanceof O))
                throw new Error(`Unable to select item ${e}, could not find an object that matched.`);
            this.selected = e ?? null;
        }
    };
var et = ((Z) => (
        (Z.dwgs_user = 'Dwgs.User'),
        (Z.cmts_user = 'Cmts.User'),
        (Z.eco1_user = 'Eco1.User'),
        (Z.eco2_user = 'Eco2.User'),
        (Z.edge_cuts = 'Edge.Cuts'),
        (Z.margin = 'Margin'),
        (Z.user_1 = 'User.1'),
        (Z.user_2 = 'User.2'),
        (Z.user_3 = 'User.3'),
        (Z.user_4 = 'User.4'),
        (Z.user_5 = 'User.5'),
        (Z.user_6 = 'User.6'),
        (Z.user_7 = 'User.7'),
        (Z.user_8 = 'User.8'),
        (Z.user_9 = 'User.9'),
        (Z.anchors = ':Anchors'),
        (Z.non_plated_holes = ':NonPlatedHoles'),
        (Z.via_holes = ':Via:Holes'),
        (Z.pad_holes = ':Pad:Holes'),
        (Z.pad_holewalls = ':Pad:HoleWalls'),
        (Z.via_holewalls = ':Via:HoleWalls'),
        (Z.pads_front = ':Pads:Front'),
        (Z.f_cu = 'F.Cu'),
        (Z.f_mask = 'F.Mask'),
        (Z.f_silks = 'F.SilkS'),
        (Z.f_adhes = 'F.Adhes'),
        (Z.f_paste = 'F.Paste'),
        (Z.f_crtyd = 'F.CrtYd'),
        (Z.f_fab = 'F.Fab'),
        (Z.in1_cu = 'In1.Cu'),
        (Z.in2_cu = 'In2.Cu'),
        (Z.in3_cu = 'In3.Cu'),
        (Z.in4_cu = 'In4.Cu'),
        (Z.in5_cu = 'In5.Cu'),
        (Z.in6_cu = 'In6.Cu'),
        (Z.in7_cu = 'In7.Cu'),
        (Z.in8_cu = 'In8.Cu'),
        (Z.in9_cu = 'In9.Cu'),
        (Z.in10_cu = 'In10.Cu'),
        (Z.in11_cu = 'In11.Cu'),
        (Z.in12_cu = 'In12.Cu'),
        (Z.in13_cu = 'In13.Cu'),
        (Z.in14_cu = 'In14.Cu'),
        (Z.in15_cu = 'In15.Cu'),
        (Z.in16_cu = 'In16.Cu'),
        (Z.in17_cu = 'In17.Cu'),
        (Z.in18_cu = 'In18.Cu'),
        (Z.in19_cu = 'In19.Cu'),
        (Z.in20_cu = 'In20.Cu'),
        (Z.in21_cu = 'In21.Cu'),
        (Z.in22_cu = 'In22.Cu'),
        (Z.in23_cu = 'In23.Cu'),
        (Z.in24_cu = 'In24.Cu'),
        (Z.in25_cu = 'In25.Cu'),
        (Z.in26_cu = 'In26.Cu'),
        (Z.in27_cu = 'In27.Cu'),
        (Z.in28_cu = 'In28.Cu'),
        (Z.in29_cu = 'In29.Cu'),
        (Z.in30_cu = 'In30.Cu'),
        (Z.pads_back = ':Pads:Back'),
        (Z.b_cu = 'B.Cu'),
        (Z.b_mask = 'B.Mask'),
        (Z.b_silks = 'B.SilkS'),
        (Z.b_adhes = 'B.Adhes'),
        (Z.b_paste = 'B.Paste'),
        (Z.b_crtyd = 'B.CrtYd'),
        (Z.b_fab = 'B.Fab'),
        (Z[(Z.drawing_sheet = ':DrawingSheet')] = 'drawing_sheet'),
        (Z[(Z.grid = ':Grid')] = 'grid'),
        Z
    ))(et || {}),
    to = [':NonPlatedHoles', ':Via:Holes', ':Pad:Holes', ':Pad:HoleWalls', ':Via:HoleWalls'],
    qe = [
        'F.Cu',
        'In1.Cu',
        'In2.Cu',
        'In3.Cu',
        'In4.Cu',
        'In5.Cu',
        'In6.Cu',
        'In7.Cu',
        'In8.Cu',
        'In9.Cu',
        'In10.Cu',
        'In11.Cu',
        'In12.Cu',
        'In13.Cu',
        'In14.Cu',
        'In15.Cu',
        'In16.Cu',
        'In17.Cu',
        'In18.Cu',
        'In19.Cu',
        'In20.Cu',
        'In21.Cu',
        'In22.Cu',
        'In23.Cu',
        'In24.Cu',
        'In25.Cu',
        'In26.Cu',
        'In27.Cu',
        'In28.Cu',
        'In29.Cu',
        'In30.Cu',
        'B.Cu',
    ];
function Te(s, t) {
    return `:${s}:${t}`;
}
l(Te, 'virtual_layer_for');
function tn(s) {
    return s.startsWith(':');
}
l(tn, 'is_virtual');
function ro(s, t) {
    return tn(t) && t.startsWith(`:${s}:`);
}
l(ro, 'is_virtual_for');
function io(s) {
    return s.endsWith('.Cu');
}
l(io, 'is_copper');
function* rn(s, t) {
    let e = !1;
    for (let r of qe) if ((r == s && (e = !0), e && (yield r), r == t)) return;
}
l(rn, 'copper_layers_between');
var U3 = class extends Ut {
    constructor(e, r) {
        super();
        this.theme = r;
        let i = new Map();
        for (let n of e.layers) i.set(n.canonical_name, n);
        for (let n of Object.values(et)) {
            if (!tn(n) && !i.has(n)) continue;
            let o = !0,
                c = !1;
            to.includes(n) && ((o = l(() => this.is_any_copper_layer_visible(), 'visible')), (c = !0)),
                n == ':Pads:Front' && ((o = l(() => this.by_name('F.Cu').visible, 'visible')), (c = !0)),
                n == ':Pads:Back' && ((o = l(() => this.by_name('B.Cu').visible, 'visible')), (c = !0)),
                io(n) &&
                    ((c = !0),
                    this.add(
                        new ae(
                            this,
                            Te(n, 'BBViaHoles'),
                            () => this.by_name(n).visible,
                            !1,
                            this.color_for(':Via:Holes'),
                        ),
                    ),
                    this.add(
                        new ae(
                            this,
                            Te(n, 'BBViaHoleWalls'),
                            () => this.by_name(n).visible,
                            !1,
                            this.color_for(':Via:HoleWalls'),
                        ),
                    ),
                    this.add(new ae(this, Te(n, 'Zones'), () => this.by_name(n).visible, !1, this.color_for(n)))),
                this.add(new ae(this, n, o, c, this.color_for(n)));
        }
    }
    static {
        l(this, 'LayerSet');
    }
    color_for(e) {
        switch (e) {
            case et.drawing_sheet:
                return this.theme.worksheet ?? h.white;
            case ':Pads:Front':
                return this.theme.copper?.f ?? h.white;
            case ':Pads:Back':
                return this.theme.copper?.b ?? h.white;
            case ':NonPlatedHoles':
                return this.theme.non_plated_hole ?? h.white;
            case ':Via:Holes':
                return this.theme.via_hole ?? h.white;
            case ':Via:HoleWalls':
                return this.theme.via_through ?? h.white;
            case ':Pad:Holes':
                return this.theme.background ?? h.white;
            case ':Pad:HoleWalls':
                return this.theme.pad_through_hole ?? h.white;
        }
        let r = e;
        return (
            (r = r.replace(':Zones:', '').replace('.', '_').toLowerCase()),
            r.endsWith('_cu')
                ? ((r = r.replace('_cu', '')), this.theme.copper[r] ?? h.white)
                : (this.theme[r] ?? h.white)
        );
    }
    *in_ui_order() {
        let e = [
            ...qe,
            'F.Adhes',
            'B.Adhes',
            'F.Paste',
            'B.Paste',
            'F.SilkS',
            'B.SilkS',
            'F.Mask',
            'B.Mask',
            'Dwgs.User',
            'Cmts.User',
            'Eco1.User',
            'Eco2.User',
            'Edge.Cuts',
            'Margin',
            'F.CrtYd',
            'B.CrtYd',
            'F.Fab',
            'B.Fab',
            'User.1',
            'User.2',
            'User.3',
            'User.4',
            'User.5',
            'User.6',
            'User.7',
            'User.8',
            'User.9',
        ];
        for (let r of e) {
            let i = this.by_name(r);
            i && (yield i);
        }
    }
    *copper_layers() {
        for (let e of qe) {
            let r = this.by_name(e);
            r && (yield r);
        }
    }
    *via_layers() {
        yield this.by_name(':Via:Holes'), yield this.by_name(':Via:HoleWalls');
        for (let e of qe)
            for (let r of ['BBViaHoleWalls', 'BBViaHoles']) {
                let i = this.by_name(Te(e, r));
                i && (yield i);
            }
    }
    *zone_layers() {
        for (let e of qe) {
            let r = Te(e, 'Zones'),
                i = this.by_name(r);
            i && (yield i);
        }
    }
    *pad_layers() {
        yield this.by_name(':Pads:Front'), yield this.by_name(':Pads:Back');
    }
    *pad_hole_layers() {
        yield this.by_name(':Pad:Holes'), yield this.by_name(':Pad:HoleWalls');
    }
    is_any_copper_layer_visible() {
        for (let e of this.copper_layers()) if (e.visible) return !0;
        return !1;
    }
    highlight(e) {
        let r = '';
        e instanceof ae ? (r = e.name) : G(e) && (r = e);
        let i = this.query((n) => n.name == r || ro(r, n.name));
        super.highlight(i);
    }
};
var j = class extends be {
        static {
            l(this, 'BoardItemPainter');
        }
        get theme() {
            return this.view_painter.theme;
        }
        get filter_net() {
            return this.view_painter.filter_net;
        }
    },
    Ni = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [Rt, t2];
        }
        static {
            l(this, 'LinePainter');
        }
        layers_for(e) {
            return [e.layer];
        }
        paint(e, r) {
            if (this.filter_net) return;
            let i = [r.start, r.end];
            this.gfx.line(new F(i, r.width, e.color));
        }
    },
    Vi = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [dt, n2];
        }
        static {
            l(this, 'RectPainter');
        }
        layers_for(e) {
            return [e.layer];
        }
        paint(e, r) {
            if (this.filter_net) return;
            let i = e.color,
                n = [r.start, new d(r.start.x, r.end.y), r.end, new d(r.end.x, r.start.y), r.start];
            this.gfx.line(new F(n, r.width, i)), r.fill && r.fill != 'none' && this.gfx.polygon(new I(n, i));
        }
    },
    gi = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [Pe, ht, s2];
        }
        static {
            l(this, 'PolyPainter');
        }
        layers_for(e) {
            return [e.layer];
        }
        paint(e, r) {
            if (this.filter_net) return;
            let i = e.color;
            r.width && this.gfx.line(new F([...r.pts, r.pts[0]], r.width, i)),
                r.fill && r.fill != 'none' && this.gfx.polygon(new I(r.pts, i));
        }
    },
    Pi = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [pt, i2];
        }
        static {
            l(this, 'ArcPainter');
        }
        layers_for(e) {
            return [e.layer];
        }
        paint(e, r) {
            if (this.filter_net) return;
            let i = r.arc,
                n = i.to_polyline();
            this.gfx.line(new F(n, i.width, e.color));
        }
    },
    Wi = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [ut, r2];
        }
        static {
            l(this, 'CirclePainter');
        }
        layers_for(e) {
            return [e.layer];
        }
        paint(e, r) {
            if (this.filter_net) return;
            let i = e.color,
                n = r.center.sub(r.end).magnitude,
                o = new z(r.center, n, new W(0), new W(2 * Math.PI), r.width);
            if (r.fill && r.fill != 'none') this.gfx.circle(new B(o.center, o.radius + (r.width ?? 0), i));
            else {
                let c = o.to_polyline();
                this.gfx.line(new F(c, o.width, i));
            }
        }
    },
    Zi = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [jt];
        }
        static {
            l(this, 'TraceSegmentPainter');
        }
        layers_for(e) {
            return [e.layer];
        }
        paint(e, r) {
            if (this.filter_net && r.net != this.filter_net) return;
            let i = [r.start, r.end];
            this.gfx.line(new F(i, r.width, e.color));
        }
    },
    Si = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [zt];
        }
        static {
            l(this, 'TraceArcPainter');
        }
        layers_for(e) {
            return [e.layer];
        }
        paint(e, r) {
            if (this.filter_net && r.net != this.filter_net) return;
            let i = z.from_three_points(r.start, r.mid, r.end, r.width),
                n = i.to_polyline();
            this.gfx.line(new F(n, i.width, e.color));
        }
    },
    Ti = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [qt];
        }
        static {
            l(this, 'ViaPainter');
        }
        layers_for(e) {
            if (e.layers) {
                let r = [];
                for (let i of rn(e.layers[0], e.layers[1]))
                    r.push(Te(i, 'BBViaHoles')), r.push(Te(i, 'BBViaHoleWalls'));
                return r;
            } else return [':Via:Holes', ':Via:HoleWalls'];
        }
        paint(e, r) {
            if (this.filter_net && r.net != this.filter_net) return;
            let i = e.color;
            e.name.endsWith('HoleWalls') || e.name == ':Overlay'
                ? this.gfx.circle(new B(r.at.position, r.size / 2, i))
                : e.name.endsWith('Holes') &&
                  (this.gfx.circle(new B(r.at.position, r.drill / 2, i)),
                  (r.type == 'blind' || r.type == 'micro') &&
                      r.layers &&
                      (this.gfx.arc(
                          r.at.position,
                          r.size / 2 - r.size / 8,
                          W.from_degrees(180 + 70),
                          W.from_degrees(360 - 70),
                          r.size / 4,
                          e.layer_set.by_name(r.layers[0])?.color ?? h.transparent_black,
                      ),
                      this.gfx.arc(
                          r.at.position,
                          r.size / 2 - r.size / 8,
                          W.from_degrees(70),
                          W.from_degrees(180 - 70),
                          r.size / 4,
                          e.layer_set.by_name(r.layers[1])?.color ?? h.transparent_black,
                      )));
        }
    },
    Li = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [ct];
        }
        static {
            l(this, 'ZonePainter');
        }
        layers_for(e) {
            let r = e.layers ?? [e.layer];
            return (
                r.length && r[0] == 'F&B.Cu' && (r.shift(), r.push('F.Cu', 'B.Cu')),
                r.map((i) => (qe.includes(i) ? Te(i, 'Zones') : i))
            );
        }
        paint(e, r) {
            if (r.filled_polygons && !(this.filter_net && r.net != this.filter_net))
                for (let i of r.filled_polygons)
                    (!e.name.includes(i.layer) && e.name != ':Overlay') || this.gfx.polygon(new I(i.pts, e.color));
        }
    },
    yi = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [o2];
        }
        static {
            l(this, 'PadPainter');
        }
        layers_for(e) {
            let r = [];
            for (let i of e.layers)
                i == '*.Cu'
                    ? (r.push(':Pads:Front'), r.push(':Pads:Back'))
                    : i == 'F.Cu'
                      ? r.push(':Pads:Front')
                      : i == 'B.Cu'
                        ? r.push(':Pads:Back')
                        : i == '*.Mask'
                          ? (r.push('F.Mask'), r.push('B.Mask'))
                          : i == '*.Paste'
                            ? (r.push('F.Paste'), r.push('B.Paste'))
                            : r.push(i);
            switch (e.type) {
                case 'thru_hole':
                    r.push(':Pad:HoleWalls'), r.push(':Pad:Holes');
                    break;
                case 'np_thru_hole':
                    r.push(':NonPlatedHoles');
                    break;
                case 'smd':
                case 'connect':
                    break;
                default:
                    Bt(`Unhandled pad type "${e.type}"`);
                    break;
            }
            return r;
        }
        paint(e, r) {
            if (this.filter_net && r.net?.number != this.filter_net) return;
            let i = e.color,
                n = U.translation(r.at.position.x, r.at.position.y);
            n.rotate_self(-W.deg_to_rad(r.parent.at.rotation)),
                n.rotate_self(W.deg_to_rad(r.at.rotation)),
                this.gfx.state.push(),
                this.gfx.state.multiply(n);
            let o = new d(0, 0);
            if ((e.name == ':Pad:Holes' || e.name == ':NonPlatedHoles') && r.drill != null)
                if (r.drill.oval) {
                    let u = new d(r.drill.diameter / 2, (r.drill.width ?? 0) / 2),
                        p = Math.min(u.x, u.y),
                        m = new d(u.x - p, u.y - p),
                        b = o.add(r.drill.offset),
                        M = b.sub(m),
                        f = b.add(m);
                    this.gfx.line(new F([M, f], p * 2, i));
                } else {
                    let u = o.add(r.drill.offset);
                    this.gfx.circle(new B(u, r.drill.diameter / 2, i));
                }
            else {
                let u = r.shape;
                switch (
                    (u == 'custom' && r.options?.anchor && (u = r.options.anchor),
                    r.drill?.offset && this.gfx.state.matrix.translate_self(r.drill.offset.x, r.drill.offset.y),
                    u)
                ) {
                    case 'circle':
                        this.gfx.circle(new B(o, r.size.x / 2, i));
                        break;
                    case 'rect':
                        {
                            let p = [
                                new d(-r.size.x / 2, -r.size.y / 2),
                                new d(r.size.x / 2, -r.size.y / 2),
                                new d(r.size.x / 2, r.size.y / 2),
                                new d(-r.size.x / 2, r.size.y / 2),
                            ];
                            this.gfx.polygon(new I(p, i));
                        }
                        break;
                    case 'roundrect':
                    case 'trapezoid':
                        {
                            let p = Math.min(r.size.x, r.size.y) * (r.roundrect_rratio ?? 0),
                                m = new d(r.size.x / 2, r.size.y / 2);
                            m = m.sub(new d(p, p));
                            let b = r.rect_delta ? r.rect_delta.copy() : new d(0, 0);
                            b = b.multiply(0.5);
                            let M = [
                                new d(-m.x - b.y, m.y + b.x),
                                new d(m.x + b.y, m.y - b.x),
                                new d(m.x - b.y, -m.y + b.x),
                                new d(-m.x + b.y, -m.y - b.x),
                            ];
                            this.gfx.polygon(new I(M, i)), this.gfx.line(new F([...M, M[0]], p * 2, i));
                        }
                        break;
                    case 'oval':
                        {
                            let p = new d(r.size.x / 2, r.size.y / 2),
                                m = Math.min(p.x, p.y),
                                b = new d(p.x - m, p.y - m),
                                M = o.add(r.drill?.offset || new d(0, 0)),
                                f = M.sub(b),
                                V = M.add(b);
                            f.equals(V) ? this.gfx.circle(new B(M, m, i)) : this.gfx.line(new F([f, V], m * 2, i));
                        }
                        break;
                    default:
                        Bt(`Unknown pad shape "${r.shape}"`);
                        break;
                }
                if (r.shape == 'custom' && r.primitives) for (let p of r.primitives) this.view_painter.paint_item(e, p);
            }
            this.gfx.state.pop();
        }
    },
    Xi = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [bt];
        }
        static {
            l(this, 'GrTextPainter');
        }
        layers_for(e) {
            return [e.layer.name];
        }
        paint(e, r) {
            if (this.filter_net || r.hide || !r.shown_text) return;
            if (r.render_cache) {
                for (let n of r.render_cache.polygons) this.view_painter.paint_item(e, n);
                return;
            }
            let i = new $(r.shown_text);
            i.apply_effects(r.effects),
                i.apply_at(r.at),
                (i.attributes.color = e.color),
                this.gfx.state.push(),
                Y.default().draw(this.gfx, i.shown_text, i.text_pos, i.attributes),
                this.gfx.state.pop();
        }
    },
    Oi = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [Ce];
        }
        static {
            l(this, 'FpTextPainter');
        }
        layers_for(e) {
            return e.hide ? [] : [e.layer.name];
        }
        paint(e, r) {
            if (this.filter_net || r.hide || !r.shown_text) return;
            if (r.render_cache) {
                this.gfx.state.push(), (this.gfx.state.matrix = U.identity());
                for (let n of r.render_cache.polygons) this.view_painter.paint_item(e, n);
                this.gfx.state.pop();
                return;
            }
            let i = new $(r.shown_text);
            if (
                (i.apply_effects(r.effects),
                i.apply_at(r.at),
                (i.attributes.keep_upright = !r.at.unlocked),
                (i.attributes.color = e.color),
                r.parent)
            ) {
                let n = W.from_degrees(r.parent.at.rotation),
                    o = i.text_pos;
                (o = n.rotate_point(o, new d(0, 0))),
                    (o = o.add(r.parent.at.position.multiply(1e4))),
                    i.text_pos.set(o);
            }
            if (i.attributes.keep_upright) {
                for (; i.text_angle.degrees > 90; ) i.text_angle.degrees -= 180;
                for (; i.text_angle.degrees <= -90; ) i.text_angle.degrees += 180;
            }
            this.gfx.state.push(),
                (this.gfx.state.matrix = U.identity()),
                Y.default().draw(this.gfx, i.shown_text, i.text_pos, i.attributes),
                this.gfx.state.pop();
        }
    },
    Ui = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [e2];
        }
        static {
            l(this, 'DimensionPainter');
        }
        layers_for(e) {
            return [e.layer];
        }
        paint(e, r) {
            switch (r.type) {
                case 'orthogonal':
                case 'aligned':
                    this.paint_linear(e, r);
                    break;
                case 'center':
                    this.paint_center(e, r);
                    break;
                case 'radial':
                    this.paint_radial(e, r);
                    break;
                case 'leader':
                    this.paint_leader(e, r);
                    break;
            }
        }
        paint_center(e, r) {
            let i = r.style.thickness ?? 0.2,
                n = r.end.sub(r.start);
            this.gfx.line([r.start.sub(n), r.start.add(n)], i, e.color),
                (n = W.from_degrees(90).rotate_point(n)),
                this.gfx.line([r.start.sub(n), r.start.add(n)], i, e.color);
        }
        paint_radial(e, r) {
            let i = r.style.thickness ?? 0.2,
                n = r.start.copy(),
                o = new d(0, r.style.arrow_length);
            this.gfx.line([n.sub(o), n.add(o)], i, e.color),
                (o = W.from_degrees(90).rotate_point(o)),
                this.gfx.line([n.sub(o), n.add(o)], i, e.color);
            let c = r.end.sub(r.start);
            c = c.resize(r.leader_length);
            let u = this.make_text(e, r),
                p = u.get_text_box().scale(1 / 1e4),
                m = [r.end, r.end.add(c), r.gr_text.at.position],
                b = p.intersect_segment(m[1], m[2]);
            b && (m[2] = b), this.gfx.line(m, i, e.color);
            let M = W.from_degrees(27.5),
                f = c.angle.negative(),
                V = new d(r.style.arrow_length, 0),
                S = f.add(M).rotate_point(V),
                y = f.sub(M).rotate_point(V);
            this.gfx.line([r.end.add(y), r.end, r.end.add(S)], i, e.color), this.paint_text(u);
        }
        paint_leader(e, r) {
            let i = r.style.thickness ?? 0.2,
                n = this.make_text(e, r),
                o = n
                    .get_text_box()
                    .grow(n.text_width / 2, n.get_effective_text_thickness() * 2)
                    .scale(1 / 1e4),
                c = r.start.add(r.end.sub(r.start).resize(r.style.extension_offset)),
                u = [c, r.end, r.gr_text.at.position],
                p = o.intersect_segment(u[1], u[2]);
            if (
                (p && (u[2] = p),
                this.gfx.line(u, i, e.color),
                r.style.text_frame == 1 && this.gfx.line(F.from_BBox(o, i, e.color)),
                r.style.text_frame == 2)
            ) {
                let y = o.w / 2 - n.get_effective_text_thickness() / 1e4 / 2;
                this.gfx.arc(o.center, y, W.from_degrees(0), W.from_degrees(360), i, e.color);
            }
            let m = r.end.sub(r.start),
                b = W.from_degrees(27.5),
                M = m.angle.negative(),
                f = new d(r.style.arrow_length, 0),
                V = M.add(b).rotate_point(f),
                S = M.sub(b).rotate_point(f);
            this.gfx.line([c.add(S), c, c.add(V)], i, e.color), this.paint_text(n);
        }
        paint_linear(e, r) {
            let i = r.style.thickness ?? 0.2,
                n = new d(),
                o = new d(),
                c = new d();
            if (r.type == 'orthogonal')
                r.orientation == 0
                    ? ((n = new d(0, r.height)), (o = r.start.add(n)), (c = new d(r.end.x, o.y)))
                    : ((n = new d(r.height, 0)), (o = r.start.add(n)), (c = new d(o.x, r.end.y)));
            else {
                let S = r.end.sub(r.start);
                r.height > 0 ? (n = new d(-S.y, S.x)) : (n = new d(S.y, -S.x));
                let y = n.resize(r.height).multiply(Math.sign(r.height));
                (o = r.start.add(y)), (c = r.end.add(y));
            }
            let u = Math.abs(r.height) - r.style.extension_offset + r.style.extension_height,
                p = r.start.add(n.resize(r.style.extension_offset)),
                m = p.add(n.resize(u));
            this.gfx.line([p, m], i, e.color),
                (p = r.end.add(n.resize(r.style.extension_offset))),
                (m = p.add(n.resize(u))),
                this.gfx.line([p, m], i, e.color),
                this.gfx.line([o, c], i, e.color);
            let b = c.sub(o).angle.negative(),
                M = W.from_degrees(27.5),
                f = b.add(M).rotate_point(new d(r.style.arrow_length, 0)),
                V = b.sub(M).rotate_point(new d(r.style.arrow_length, 0));
            this.gfx.line([o.add(V), o, o.add(f)], i, e.color),
                this.gfx.line([c.sub(V), c, c.sub(f)], i, e.color),
                this.paint_text(this.make_text(e, r));
        }
        make_text(e, r) {
            let i = new $(r.gr_text.shown_text);
            return i.apply_effects(r.gr_text.effects), i.apply_at(r.gr_text.at), (i.attributes.color = e.color), i;
        }
        paint_text(e) {
            this.gfx.state.push(),
                Y.default().draw(this.gfx, e.shown_text, e.text_pos, e.attributes),
                this.gfx.state.pop();
        }
    },
    Fi = class extends j {
        constructor() {
            super(...arguments);
            this.classes = [xe];
        }
        static {
            l(this, 'FootprintPainter');
        }
        layers_for(e) {
            let r = new Set();
            for (let i of e.items()) {
                let n = this.view_painter.layers_for(i);
                for (let o of n) r.add(o);
            }
            return Array.from(r.values());
        }
        paint(e, r) {
            let i = U.translation(r.at.position.x, r.at.position.y).rotate_self(W.deg_to_rad(r.at.rotation));
            this.gfx.state.push(), this.gfx.state.multiply(i);
            for (let n of r.items()) {
                let o = this.view_painter.layers_for(n);
                (e.name == ':Overlay' || o.includes(e.name)) && this.view_painter.paint_item(e, n);
            }
            this.gfx.state.pop();
        }
    },
    F3 = class extends Ee {
        constructor(e, r, i) {
            super(e, r, i);
            this.filter_net = null;
            this.painter_list = [
                new Ni(this, e),
                new Vi(this, e),
                new gi(this, e),
                new Pi(this, e),
                new Wi(this, e),
                new Zi(this, e),
                new Si(this, e),
                new Ti(this, e),
                new Li(this, e),
                new yi(this, e),
                new Fi(this, e),
                new Xi(this, e),
                new Oi(this, e),
                new Ui(this, e),
            ];
        }
        static {
            l(this, 'BoardPainter');
        }
        paint_net(e, r) {
            let i = this.layers.overlay;
            (this.filter_net = r), i.clear(), (i.color = h.white), this.gfx.start_layer(i.name);
            for (let n of e.items()) this.painter_for(n) && this.paint_item(i, n);
            (i.graphics = this.gfx.end_layer()), (i.graphics.composite_operation = 'overlay'), (this.filter_net = null);
        }
    };
var x3 = class extends Ft {
    static {
        l(this, 'BoardViewer');
    }
    get board() {
        return this.document;
    }
    create_renderer(t) {
        return new _3(t);
    }
    create_painter() {
        return new F3(this.renderer, this.layers, this.theme);
    }
    create_layer_set() {
        return new U3(this.board, this.theme);
    }
    get grid_origin() {
        return this.board.setup?.grid_origin ?? new d(0, 0);
    }
    on_pick(t, e) {
        let r = null;
        for (let { layer: i, bbox: n } of e)
            if (n.context instanceof xe) {
                r = n.context;
                break;
            }
        this.select(r);
    }
    select(t) {
        G(t) && (t = this.board.find_footprint(t)), t instanceof xe && (t = t.bbox), super.select(t);
    }
    highlight_net(t) {
        this.painter.paint_net(this.board, t), this.draw();
    }
    set_layers_opacity(t, e) {
        for (let r of t) r.opacity = e;
        this.draw();
    }
    set track_opacity(t) {
        this.set_layers_opacity(this.layers.copper_layers(), t);
    }
    set via_opacity(t) {
        this.set_layers_opacity(this.layers.via_layers(), t);
    }
    set zone_opacity(t) {
        this.set_layers_opacity(this.layers.zone_layers(), t);
    }
    set pad_opacity(t) {
        this.set_layers_opacity(this.layers.pad_layers(), t);
    }
    set pad_hole_opacity(t) {
        this.set_layers_opacity(this.layers.pad_hole_layers(), t);
    }
    set grid_opacity(t) {
        this.set_layers_opacity(this.layers.grid_layers(), t);
    }
    set page_opacity(t) {
        (this.layers.by_name(et.drawing_sheet).opacity = t), this.draw();
    }
    zoom_to_board() {
        let e = this.layers.by_name('Edge.Cuts').bbox;
        this.viewport.camera.bbox = e.grow(e.w * 0.1);
    }
};
var Le = class extends Hs(N) {
    constructor() {
        super(...arguments);
        this.selected = [];
    }
    static {
        l(this, 'KCViewerElement');
    }
    initialContentCallback() {
        (async () => (
            (this.viewer = this.addDisposable(this.make_viewer())),
            await this.viewer.setup(),
            this.addDisposable(
                this.viewer.addEventListener(ie.type, () => {
                    (this.loaded = !0), this.dispatchEvent(new ie());
                }),
            )
        ))();
    }
    async preferenceChangeCallback(e) {
        this.theme ||
            !this.viewer ||
            !this.viewer.loaded ||
            (this.update_theme(), this.viewer.paint(), this.viewer.draw());
    }
    disconnectedCallback() {
        super.disconnectedCallback(), (this.selected = []);
    }
    get themeObject() {
        return this.theme ? Ze.by_name(this.theme) : Re.INSTANCE.theme;
    }
    async load(e) {
        (this.loaded = !1), await this.viewer.load(e.document);
    }
    render() {
        return (
            (this.canvas = _`<canvas></canvas>`),
            _`<style>
                :host {
                    display: block;
                    touch-action: none;
                    width: 100%;
                    height: 100%;
                }

                canvas {
                    width: 100%;
                    height: 100%;
                }
            </style>
            ${this.canvas}`
        );
    }
};
P([L({ type: Boolean })], Le.prototype, 'loaded', 2),
    P([L({ type: String })], Le.prototype, 'theme', 2),
    P([L({ type: Boolean })], Le.prototype, 'disableinteraction', 2);
var xi = class extends Le {
    static {
        l(this, 'KCBoardViewerElement');
    }
    update_theme() {
        this.viewer.theme = this.themeObject.board;
    }
    make_viewer() {
        return new x3(this.canvas, !this.disableinteraction, this.themeObject.board);
    }
};
window.customElements.define('kc-board-viewer', xi);
var xt = class extends N {
    static {
        l(this, 'KCBoardFootprintsPanelElement');
    }
    connectedCallback() {
        (async () => (
            (this.viewer = await this.requestLazyContext('viewer')),
            await this.viewer.loaded,
            this.sort_footprints(),
            super.connectedCallback()
        ))();
    }
    sort_footprints() {
        this.sorted_footprints = pe(this.viewer.board.footprints, (e) => e.reference || 'REF');
    }
    initialContentCallback() {
        this.addEventListener('kc-ui-menu:select', (e) => {
            let r = e.detail;
            r.name && this.viewer.select(r.name);
        }),
            this.addDisposable(
                this.viewer.addEventListener(D.type, () => {
                    this.menu.selected = this.viewer.selected?.context.uuid ?? null;
                }),
            ),
            this.search_input_elm.addEventListener('input', (e) => {
                this.item_filter_elem.filter_text = this.search_input_elm.value ?? null;
            });
    }
    render() {
        return _`
            <kc-ui-panel>
                <kc-ui-panel-title title="Footprints"></kc-ui-panel-title>
                <kc-ui-panel-body>
                    <kc-ui-text-filter-input></kc-ui-text-filter-input>
                    <kc-ui-filtered-list>
                        <kc-ui-menu class="outline">
                            ${this.render_list()}
                        </kc-ui-menu>
                    </kc-ui-filtered-list>
                </kc-ui-panel-body>
            </kc-ui-panel>
        `;
    }
    render_list() {
        let e = [],
            r = [];
        for (let i of this.sorted_footprints) {
            let n = i.reference || 'REF',
                o = i.value || 'VAL',
                c = `${i.library_link} ${i.descr} ${i.layer} ${n} ${o} ${i.tags}`,
                u = _`<kc-ui-menu-item
                name="${i.uuid}"
                data-match-text="${c}">
                <span class="narrow">${n}</span><span>${o}</span>
            </kc-ui-menu-item>`;
            i.layer == 'F.Cu' ? e.push(u) : r.push(u);
        }
        return _`<kc-ui-menu-label>Front</kc-ui-menu-label>
            ${e}
            <kc-ui-menu-label>Back</kc-ui-menu-label>
            ${r}`;
    }
};
P([Q('kc-ui-menu', !0)], xt.prototype, 'menu', 2),
    P([Q('kc-ui-text-filter-input', !0)], xt.prototype, 'search_input_elm', 2),
    P([Q('kc-ui-filtered-list', !0)], xt.prototype, 'item_filter_elem', 2);
window.customElements.define('kc-board-footprints-panel', xt);
var Qi = class extends N {
    static {
        l(this, 'KCBoardInfoPanelElement');
    }
    connectedCallback() {
        (async () => (
            (this.viewer = await this.requestLazyContext('viewer')), await this.viewer.loaded, super.connectedCallback()
        ))();
    }
    render() {
        let e = this.viewer.drawing_sheet,
            r = this.viewer.board,
            i = r.edge_cuts_bbox,
            n = l(
                (u) => _`<kc-ui-property-list-item
                name="${u}"
                class="label"></kc-ui-property-list-item>`,
                'header',
            ),
            o = l(
                (u, p, m = '') => _` <kc-ui-property-list-item name="${u}">
                ${p} ${m}
            </kc-ui-property-list-item>`,
                'entry',
            ),
            c = Object.entries(r.title_block?.comment || {}).map(([u, p]) => o(`Comment ${u}`, p));
        return _`
            <kc-ui-panel>
                <kc-ui-panel-title title="Info"></kc-ui-panel-title>
                <kc-ui-panel-body>
                    <kc-ui-property-list>
                        ${n('Page properties')}
                        ${o('Size', e.paper?.size)}
                        ${o('Width', e.width, 'mm')}
                        ${o('Height', e.height, 'mm')}
                        ${n('Board properties')}
                        ${o('KiCAD version', r.version)}
                        ${o('Generator', r.generator)}
                        ${o('Thickness', r.general?.thickness ?? 1.6, 'mm')}
                        ${o('Title', r.title_block?.title)}
                        ${o('Date', r.title_block?.date)}
                        ${o('Revision', r.title_block?.rev)}
                        ${o('Company', r.title_block?.company)}
                        ${c}
                        ${o(
                            'Dimensions',
                            `${i.w.toFixed(1)} x
                            ${i.h.toFixed(1)} mm`,
                        )}
                        ${o('Footprints', r.footprints.length)}
                        ${o('Nets', r.nets.length)}
                        ${o('Track segments', r.segments.length)}
                        ${o('Vias', r.vias.length)}
                        ${o('Zones', r.zones.length)}
                        ${o('Pad to mask clearance', r.setup?.pad_to_mask_clearance ?? 0, 'mm')}
                        ${o('Soldermask min width', r.setup?.solder_mask_min_width ?? 0, 'mm')}
                        ${o('Pad to paste clearance', r.setup?.pad_to_paste_clearance ?? 0, 'mm')}
                        ${o('Pad to paste clearance ratio', r.setup?.pad_to_paste_clearance_ratio ?? 0)}
                        ${o('Grid origin', `${r.setup?.grid_origin?.x ?? 0}, ${r.setup?.grid_origin?.y ?? 0}`)}
                    </kc-ui-property-list>
                </kc-ui-panel-body>
            </kc-ui-panel>
        `;
    }
};
window.customElements.define('kc-board-info-panel', Qi);
var x2 = class extends N {
    static {
        l(this, 'KCBoardLayersPanelElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                display: block;
                height: 100%;
                overflow-y: auto;
                overflow-x: hidden;
                user-select: none;
            }

            kc-ui-panel-title button {
                all: unset;
                flex-shrink: 0;
                margin-left: 1em;
                color: white;
                border: 0 none;
                background: transparent;
                padding: 0 0.25em 0 0.25em;
                margin-right: -0.25em;
                display: flex;
                align-items: center;
            }
        `,
        ];
    }
    get items() {
        return Array.from(this.panel_body.querySelectorAll('kc-board-layer-control') ?? []);
    }
    connectedCallback() {
        (async () => (
            (this.viewer = await this.requestLazyContext('viewer')), await this.viewer.loaded, super.connectedCallback()
        ))();
    }
    initialContentCallback() {
        this.panel_body.addEventListener(Q2.select_event, (e) => {
            let r = e.detail;
            for (let n of this.items) n.layer_highlighted = !1;
            let i = this.viewer.layers.by_name(r.layer_name);
            i.highlighted
                ? this.viewer.layers.highlight(null)
                : (this.viewer.layers.highlight(i),
                  (i.visible = !0),
                  (r.layer_visible = !0),
                  (r.layer_highlighted = !0)),
                this.viewer.draw();
        }),
            this.panel_body.addEventListener(Q2.visibility_event, (e) => {
                let r = e.detail,
                    i = this.viewer.layers.by_name(r.layer_name);
                (i.visible = !i.visible),
                    (r.layer_visible = i.visible),
                    this.presets_menu.deselect(),
                    this.viewer.draw();
            }),
            this.renderRoot.querySelector('button')?.addEventListener('click', (e) => {
                e.stopPropagation();
                let r = this.viewer.layers.in_ui_order();
                if (this.items.some((i) => i.layer_visible)) for (let i of r) i.visible = !1;
                else for (let i of r) i.visible = !0;
                this.viewer.draw(), this.presets_menu.deselect(), this.update_item_states();
            }),
            this.presets_menu.addEventListener('kc-ui-menu:select', (e) => {
                let r = e.detail,
                    i = this.viewer.layers.in_ui_order();
                switch (r.name) {
                    case 'all':
                        for (let n of i) n.visible = !0;
                        break;
                    case 'front':
                        for (let n of i) n.visible = n.name.startsWith('F.') || n.name == 'Edge.Cuts';
                        break;
                    case 'back':
                        for (let n of i) n.visible = n.name.startsWith('B.') || n.name == 'Edge.Cuts';
                        break;
                    case 'copper':
                        for (let n of i) n.visible = n.name.includes('.Cu') || n.name == 'Edge.Cuts';
                        break;
                    case 'outer-copper':
                        for (let n of i) n.visible = n.name == 'F.Cu' || n.name == 'B.Cu' || n.name == 'Edge.Cuts';
                        break;
                    case 'inner-copper':
                        for (let n of i)
                            n.visible =
                                (n.name.includes('.Cu') && !(n.name == 'F.Cu' || n.name == 'B.Cu')) ||
                                n.name == 'Edge.Cuts';
                        break;
                    case 'drawings':
                        for (let n of i)
                            n.visible =
                                !n.name.includes('.Cu') &&
                                !n.name.includes('.Mask') &&
                                !n.name.includes('.Paste') &&
                                !n.name.includes('.Adhes');
                }
                this.viewer.draw(), this.update_item_states();
            });
    }
    update_item_states() {
        for (let e of this.items) {
            let r = this.viewer.layers.by_name(e.layer_name);
            (e.layer_visible = r?.visible ?? !1), (e.layer_highlighted = r?.highlighted ?? !1);
        }
    }
    render() {
        let e = this.viewer.layers,
            r = [];
        for (let i of e.in_ui_order()) {
            let n = i.visible ? '' : void 0,
                o = i.color.to_css();
            r.push(_`<kc-board-layer-control
                    layer-name="${i.name}"
                    layer-color="${o}"
                    layer-visible="${n}"></kc-board-layer-control>`);
        }
        return _`
            <kc-ui-panel>
                <kc-ui-panel-title title="Layers">
                    <button slot="actions" type="button">
                        <kc-ui-icon>visibility</kc-ui-icon>
                    </button>
                </kc-ui-panel-title>
                <kc-ui-panel-body>
                    ${r}
                    <kc-ui-panel-label>Presets</kc-ui-panel-label>
                    <kc-ui-menu id="presets" class="outline">
                        <kc-ui-menu-item name="all">All</kc-ui-menu-item>
                        <kc-ui-menu-item name="front">Front</kc-ui-menu-item>
                        <kc-ui-menu-item name="back">Back</kc-ui-menu-item>
                        <kc-ui-menu-item name="copper">Copper</kc-ui-menu-item>
                        <kc-ui-menu-item name="outer-copper">
                            Outer copper
                        </kc-ui-menu-item>
                        <kc-ui-menu-item name="inner-copper">
                            Inner copper
                        </kc-ui-menu-item>
                        <kc-ui-menu-item name="drawings">
                            Drawings
                        </kc-ui-menu-item>
                    </kc-ui-menu>
                </kc-ui-panel-body>
            </kc-ui-panel>
        `;
    }
};
P([Q('kc-ui-panel-body', !0)], x2.prototype, 'panel_body', 2), P([Q('#presets', !0)], x2.prototype, 'presets_menu', 2);
var Ie = class Ie extends N {
    static {
        l(this, 'KCBoardLayerControlElement');
    }
    static {
        this.styles = [
            ...N.styles,
            T`
            :host {
                box-sizing: border-box;
                padding: 0.1em 0.8em 0.1em 0.4em;
                color: white;
                text-align: left;
                display: flex;
                flex-direction: row;
                width: 100%;
                align-items: center;
            }

            button {
                all: unset;
                cursor: pointer;
                flex-shrink: 0;
                margin-left: 1em;
                color: white;
                border: 0 none;
                background: transparent;
                padding: 0 0.25em 0 0.25em;
                margin-right: -0.25em;
                display: flex;
                align-items: center;
            }

            .color {
                flex-shrink: 0;
                display: block;
                width: 1em;
                height: 1em;
                margin-right: 0.5em;
            }

            .name {
                display: block;
                flex-grow: 1;
            }

            .for-hidden {
                color: #888;
            }

            :host {
                background: var(--list-item-disabled-bg);
                color: var(--list-item-disabled-fg);
            }

            :host(:hover) {
                background: var(--list-item-hover-bg);
                color: var(--list-item-hover-fg);
            }

            :host(:hover) button {
                color: var(--list-item-bg);
            }

            :host(:hover) button:hover {
                color: var(--list-item-fg);
            }

            :host([layer-visible]) {
                background: var(--list-item-bg);
                color: var(--list-item-fg);
            }

            :host([layer-highlighted]) {
                background: var(--list-item-active-bg);
                color: var(--list-item-active-fg);
            }

            :host([layer-highlighted]:hover) button {
                color: var(--list-item-fg);
            }

            :host kc-ui-icon.for-visible,
            :host([layer-visible]) kc-ui-icon.for-hidden {
                display: none;
            }

            :host kc-ui-icon.for-hidden,
            :host([layer-visible]) kc-ui-icon.for-visible {
                display: revert;
            }
        `,
        ];
    }
    static {
        this.select_event = 'kicanvas:layer-control:select';
    }
    static {
        this.visibility_event = 'kicanvas:layer-control:visibility';
    }
    initialContentCallback() {
        super.initialContentCallback(),
            this.renderRoot.addEventListener('click', (e) => {
                e.stopPropagation();
                let r = e.target?.closest('button'),
                    i;
                r ? (i = Ie.visibility_event) : (i = Ie.select_event),
                    this.dispatchEvent(new CustomEvent(i, { detail: this, bubbles: !0 }));
            });
    }
    render() {
        return _`<span
                class="color"
                style="background: ${this.layer_color};"></span>
            <span class="name">${this.layer_name}</span>
            <button type="button" name="${this.layer_name}">
                <kc-ui-icon class="for-visible">visibility</kc-ui-icon>
                <kc-ui-icon class="for-hidden">visibility_off</kc-ui-icon>
            </button>`;
    }
};
P([L({ type: String })], Ie.prototype, 'layer_name', 2),
    P([L({ type: String })], Ie.prototype, 'layer_color', 2),
    P([L({ type: Boolean })], Ie.prototype, 'layer_highlighted', 2),
    P([L({ type: Boolean })], Ie.prototype, 'layer_visible', 2);
var Q2 = Ie;
window.customElements.define('kc-board-layer-control', Q2);
window.customElements.define('kc-board-layers-panel', x2);
var v2 = class extends N {
    static {
        l(this, 'KCBoardNetsPanelElement');
    }
    connectedCallback() {
        (async () => (
            (this.viewer = await this.requestLazyContext('viewer')), await this.viewer.loaded, super.connectedCallback()
        ))();
    }
    initialContentCallback() {
        this.addEventListener('kc-ui-menu:select', (e) => {
            let r = e.detail,
                i = parseInt(r?.name, 10);
            i && this.viewer.highlight_net(i);
        }),
            this.search_input_elm.addEventListener('input', (e) => {
                this.item_filter_elem.filter_text = this.search_input_elm.value ?? null;
            });
    }
    render() {
        let e = this.viewer.board,
            r = [];
        for (let i of e.nets)
            r.push(_`<kc-ui-menu-item
                    name="${i.number}"
                    data-match-text="${i.number} ${i.name}">
                    <span class="very-narrow"> ${i.number} </span>
                    <span>${i.name}</span>
                </kc-ui-menu-item>`);
        return _`
            <kc-ui-panel>
                <kc-ui-panel-title title="Nets"></kc-ui-panel-title>
                <kc-ui-panel-body>
                    <kc-ui-text-filter-input></kc-ui-text-filter-input>
                    <kc-ui-filtered-list>
                        <kc-ui-menu class="outline">${r}</kc-ui-menu>
                    </kc-ui-filtered-list>
                </kc-ui-panel-body>
            </kc-ui-panel>
        `;
    }
};
P([Q('kc-ui-text-filter-input', !0)], v2.prototype, 'search_input_elm', 2),
    P([Q('kc-ui-filtered-list', !0)], v2.prototype, 'item_filter_elem', 2);
window.customElements.define('kc-board-nets-panel', v2);
var vi = class extends N {
    static {
        l(this, 'KCBoardObjectsPanelElement');
    }
    connectedCallback() {
        (async () => (
            (this.viewer = await this.requestLazyContext('viewer')),
            await this.viewer.loaded,
            super.connectedCallback(),
            this.setup_events()
        ))();
    }
    setup_events() {
        he(this.renderRoot, 'kc-ui-range', 'kc-ui-range:input', (e) => {
            let r = e.target,
                i = r.valueAsNumber;
            switch (r.name) {
                case 'tracks':
                    this.viewer.track_opacity = i;
                    break;
                case 'vias':
                    this.viewer.via_opacity = i;
                    break;
                case 'pads':
                    this.viewer.pad_opacity = i;
                    break;
                case 'holes':
                    this.viewer.pad_hole_opacity = i;
                    break;
                case 'zones':
                    this.viewer.zone_opacity = i;
                    break;
                case 'grid':
                    this.viewer.grid_opacity = i;
                    break;
                case 'page':
                    this.viewer.page_opacity = i;
                    break;
            }
        });
    }
    render() {
        return _`
            <kc-ui-panel>
                <kc-ui-panel-title title="Objects"></kc-ui-panel-title>
                <kc-ui-panel-body padded>
                    <kc-ui-control-list>
                        <kc-ui-control>
                            <label>Tracks</label>
                            <kc-ui-range
                                min="0"
                                max="1.0"
                                step="0.01"
                                value="1"
                                name="tracks"></kc-ui-range>
                        </kc-ui-control>
                        <kc-ui-control>
                            <label>Vias</label>
                            <kc-ui-range
                                min="0"
                                max="1.0"
                                step="0.01"
                                value="1"
                                name="vias"></kc-ui-range>
                        </kc-ui-control>
                        <kc-ui-control>
                            <label>Pads</label>
                            <kc-ui-range
                                min="0"
                                max="1.0"
                                step="0.01"
                                value="1"
                                name="pads"></kc-ui-range>
                        </kc-ui-control>
                        <kc-ui-control>
                            <label>Through holes</label>
                            <kc-ui-range
                                min="0"
                                max="1.0"
                                step="0.01"
                                value="1"
                                name="holes"></kc-ui-range>
                        </kc-ui-control>
                        <kc-ui-control>
                            <label>Zones</label>
                            <kc-ui-range
                                min="0"
                                max="1.0"
                                step="0.01"
                                value="1"
                                name="zones"></kc-ui-range>
                        </kc-ui-control>
                        <kc-ui-control>
                            <label>Grid</label>
                            <kc-ui-range
                                min="0"
                                max="1.0"
                                step="0.01"
                                value="1"
                                name="grid"></kc-ui-range>
                        </kc-ui-control>
                        <kc-ui-control>
                            <label>Page</label>
                            <kc-ui-range
                                min="0"
                                max="1.0"
                                step="0.01"
                                value="1"
                                name="page"></kc-ui-range>
                        </kc-ui-control>
                    </kc-ui-control-list>
                </kc-ui-panel-body>
            </kc-ui-panel>
        `;
    }
};
window.customElements.define('kc-board-objects-panel', vi);
var wi = class extends N {
    static {
        l(this, 'KCBoardPropertiesPanelElement');
    }
    connectedCallback() {
        (async () => (
            (this.viewer = await this.requestLazyContext('viewer')),
            await this.viewer.loaded,
            super.connectedCallback(),
            this.setup_events()
        ))();
    }
    setup_events() {
        this.addDisposable(
            this.viewer.addEventListener(D.type, (e) => {
                (this.selected_item = e.detail.item), this.update();
            }),
        );
    }
    render() {
        let e = l(
                (o) => _`<kc-ui-property-list-item class="label" name="${o}">
            </kc-ui-property-list-item>`,
                'header',
            ),
            r = l(
                (o, c, u = '') => _`<kc-ui-property-list-item name="${o}">
                ${c ?? ''} ${u}
            </kc-ui-property-list-item>`,
                'entry',
            ),
            i = l((o) => (o ? _`<kc-ui-icon>check</kc-ui-icon>` : _`<kc-ui-icon>close</kc-ui-icon>`), 'checkbox'),
            n;
        if (!this.selected_item) n = e('No item selected');
        else {
            let o = this.selected_item,
                c = Object.entries(o.properties).map(([u, p]) => r(u, p));
            n = _`
                ${e('Basic properties')}
                ${r('X', o.at.position.x.toFixed(4), 'mm')}
                ${r('Y', o.at.position.y.toFixed(4), 'mm')}
                ${r('Orientation', o.at.rotation, '\xB0')}
                ${r('Layer', o.layer)} ${e('Footprint properties')}
                ${r('Reference', o.reference)}
                ${r('Value', o.value)}
                ${r('Type', o.attr.through_hole ? 'through hole' : o.attr.smd ? 'smd' : 'unspecified')}
                ${r('Pads', o.pads.length)}
                ${r('Library link', o.library_link)}
                ${r('Description', o.descr)}
                ${r('Keywords', o.tags)} ${c}
                ${e('Fabrication attributes')}
                ${r('Not in schematic', i(o.attr.board_only))}
                ${r('Exclude from position files', i(o.attr.exclude_from_pos_files))}
                ${r('Exclude from BOM', i(o.attr.exclude_from_bom))}
                ${e('Overrides')}
                ${r('Exempt from courtyard requirement', i(o.attr.allow_missing_courtyard))}
                ${r('Clearance', o.clearance ?? 0, 'mm')}
                ${r('Solderpaste margin', o.solder_paste_margin ?? 0, 'mm')}
                ${r('Solderpaste margin ratio', o.solder_paste_ratio ?? 0)}
                ${r('Zone connection', o.zone_connect ?? 'inherited')}
            `;
        }
        return _`
            <kc-ui-panel>
                <kc-ui-panel-title title="Properties"></kc-ui-panel-title>
                <kc-ui-panel-body>
                    <kc-ui-property-list> ${n} </kc-ui-property-list>
                </kc-ui-panel-body>
            </kc-ui-panel>
        `;
    }
};
window.customElements.define('kc-board-properties-panel', wi);
var Yi = class extends Se {
    static {
        l(this, 'KCBoardAppElement');
    }
    on_viewer_select(t, e) {
        t && t == e && this.change_activity('properties');
    }
    can_load(t) {
        return t.document instanceof ge;
    }
    make_viewer_element() {
        return _`<kc-board-viewer></kc-board-viewer>`;
    }
    make_activities() {
        return [
            _`<kc-ui-activity slot="activities" name="Layers" icon="layers">
                <kc-board-layers-panel></kc-board-layers-panel>
            </kc-ui-activity>`,
            _`<kc-ui-activity
                slot="activities"
                name="Objects"
                icon="category">
                <kc-board-objects-panel></kc-board-objects-panel>
            </kc-ui-activity>`,
            _`<kc-ui-activity
                slot="activities"
                name="Footprints"
                icon="memory">
                <kc-board-footprints-panel></kc-board-footprints-panel>
            </kc-ui-activity>`,
            _`<kc-ui-activity slot="activities" name="Nets" icon="hub">
                <kc-board-nets-panel></kc-board-nets-panel>
            </kc-ui-activity>`,
            _`<kc-ui-activity
                slot="activities"
                name="Properties"
                icon="list">
                <kc-board-properties-panel></kc-board-properties-panel>
            </kc-ui-activity>`,
            _`<kc-ui-activity
                slot="activities"
                name="Board info"
                icon="info">
                <kc-board-info-panel></kc-board-info-panel>
            </kc-ui-activity>`,
        ];
    }
};
window.customElements.define('kc-board-app', Yi);
var Q3 = class extends Ke {
        constructor(e) {
            super(e);
            this.#e = [];
            this.state = new P2();
        }
        static {
            l(this, 'Canvas2DRenderer');
        }
        #e;
        #t;
        async setup() {
            let e = this.canvas.getContext('2d', { alpha: !1, desynchronized: !0 });
            if (e == null) throw new Error('Unable to create Canvas2d context');
            (this.ctx2d = e), this.update_canvas_size();
        }
        dispose() {
            this.ctx2d = void 0;
            for (let e of this.#e) e.dispose();
        }
        update_canvas_size() {
            let e = window.devicePixelRatio,
                r = this.canvas.getBoundingClientRect(),
                i = Math.round(r.width * e),
                n = Math.round(r.height * e);
            (this.canvas.width != i || this.canvas.height != n) && ((this.canvas.width = i), (this.canvas.height = n));
        }
        clear_canvas() {
            this.update_canvas_size(),
                this.ctx2d.setTransform(),
                this.ctx2d.scale(window.devicePixelRatio, window.devicePixelRatio),
                (this.ctx2d.fillStyle = this.background_color.to_css()),
                this.ctx2d.fillRect(0, 0, this.canvas.width, this.canvas.height),
                (this.ctx2d.lineCap = 'round'),
                (this.ctx2d.lineJoin = 'round');
        }
        start_layer(e) {
            this.#t = new Ki(this, e);
        }
        end_layer() {
            if (!this.#t) throw new Error('No active layer');
            return this.#e.push(this.#t), (this.#t = null), this.#e.at(-1);
        }
        arc(e, r, i, n, o, c) {
            super.prep_arc(e, r, i, n, o, c);
        }
        circle(e, r, i) {
            let n = super.prep_circle(e, r, i);
            if (!n.color || n.color.is_transparent_black) return;
            let o = n.color.to_css(),
                c = new Path2D();
            c.arc(n.center.x, n.center.y, n.radius, 0, Math.PI * 2), this.#t.commands.push(new Qt(c, o, null, 0));
        }
        line(e, r, i) {
            let n = super.prep_line(e, r, i);
            if (!n.color || n.color.is_transparent_black) return;
            let o = n.color.to_css(),
                c = new Path2D(),
                u = !1;
            for (let p of n.points) u ? c.lineTo(p.x, p.y) : (c.moveTo(p.x, p.y), (u = !0));
            this.#t.commands.push(new Qt(c, null, o, n.width));
        }
        polygon(e, r) {
            let i = super.prep_polygon(e, r);
            if (!i.color || i.color.is_transparent_black) return;
            let n = i.color.to_css(),
                o = new Path2D(),
                c = !1;
            for (let u of i.points) c ? o.lineTo(u.x, u.y) : (o.moveTo(u.x, u.y), (c = !0));
            o.closePath(), this.#t.commands.push(new Qt(o, n, null, 0));
        }
        get layers() {
            let e = this.#e;
            return {
                *[Symbol.iterator]() {
                    for (let r of e) yield r;
                },
            };
        }
        remove_layer(e) {
            let r = this.#e.indexOf(e);
            r != -1 && this.#e.splice(r, 1);
        }
    },
    Qt = class {
        constructor(t, e, r, i) {
            this.path = t;
            this.fill = e;
            this.stroke = r;
            this.stroke_width = i;
            this.path_count = 1;
        }
        static {
            l(this, 'DrawCommand');
        }
        render(t) {
            (t.fillStyle = this.fill ?? 'black'),
                (t.strokeStyle = this.stroke ?? 'black'),
                (t.lineWidth = this.stroke_width),
                this.fill && t.fill(this.path),
                this.stroke && t.stroke(this.path);
        }
    },
    Ki = class extends He {
        constructor(e, r, i = []) {
            super(e, r);
            this.renderer = e;
            this.name = r;
            this.commands = i;
        }
        static {
            l(this, 'Canvas2dRenderLayer');
        }
        dispose() {
            this.clear();
        }
        clear() {
            this.commands = [];
        }
        push_path(e, r, i, n) {
            let o = this.commands.at(-1);
            o && (o.path_count < 20, o.fill == r && o.stroke == i && o.stroke_width == n)
                ? (o.path.addPath(e), o.path_count++)
                : this.commands.push(new Qt(e, r, i, n));
        }
        render(e, r, i = 1) {
            let n = this.renderer.ctx2d;
            if (!n) throw new Error('No CanvasRenderingContext2D!');
            n.save(), (n.globalCompositeOperation = this.composite_operation), (n.globalAlpha = i);
            let o = U.from_DOMMatrix(n.getTransform());
            o.multiply_self(e), n.setTransform(o.to_DOMMatrix());
            for (let c of this.commands) c.render(n);
            (n.globalCompositeOperation = 'source-over'), (n.globalAlpha = 1), n.restore();
        }
    };
var ke = ((f) => (
        (f.interactive = ':Interactive'),
        (f.marks = ':Marks'),
        (f.symbol_field = ':Symbol:Field'),
        (f.label = ':Label'),
        (f.junction = ':Junction'),
        (f.wire = ':Wire'),
        (f.symbol_foreground = ':Symbol:Foreground'),
        (f.notes = ':Notes'),
        (f.bitmap = ':Bitmap'),
        (f.symbol_pin = ':Symbol:Pin'),
        (f.symbol_background = ':Symbol:Background'),
        (f[(f.drawing_sheet = ':DrawingSheet')] = 'drawing_sheet'),
        (f[(f.grid = ':Grid')] = 'grid'),
        f
    ))(ke || {}),
    vt = class extends Ut {
        constructor(e) {
            super();
            this.theme = e;
            for (let r of Object.values(ke)) this.add(new ae(this, r));
            (this.by_name(':Interactive').visible = !1),
                (this.by_name(':Interactive').interactive = !0),
                (this.by_name(ke.drawing_sheet).color = this.theme.worksheet ?? h.white);
        }
        static {
            l(this, 'LayerSet');
        }
        *interactive_layers() {
            yield this.by_name(':Interactive');
        }
    };
var v3 = class extends Ee {
        static {
            l(this, 'BaseSchematicPainter');
        }
    },
    K = class extends be {
        static {
            l(this, 'SchematicItemPainter');
        }
        get theme() {
            return this.view_painter.theme;
        }
        get is_dimmed() {
            return this.view_painter.current_symbol?.dnp ?? !1;
        }
        dim_color(e) {
            return (e = e.desaturate()), e.mix(this.theme.background, 0.5);
        }
        dim_if_needed(e) {
            return this.is_dimmed ? this.dim_color(e) : e;
        }
        determine_stroke(e, r) {
            let i = r.stroke?.width || this.gfx.state.stroke_width;
            if (i < 0) return { width: 0, color: null };
            if ((r.stroke?.type ?? 'none') == 'none') return { width: 0, color: null };
            let o = e.name == ':Symbol:Foreground' ? this.theme.component_outline : this.theme.note,
                c = this.dim_if_needed(r.stroke?.color ?? o);
            return { width: i, color: c };
        }
        determine_fill(e, r) {
            let i = r.fill?.type ?? 'none';
            if (i == 'none' || (i == 'background' && e.name != ':Symbol:Background')) return null;
            let n;
            switch (i) {
                case 'background':
                    n = this.theme.component_body;
                    break;
                case 'outline':
                    n = this.theme.component_outline;
                    break;
                case 'color':
                    n = r.fill.color;
                    break;
            }
            return this.dim_if_needed(n);
        }
    };
var w2 = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [];
        }
        static {
            l(this, 'LabelPainter');
        }
        layers_for(e) {
            return [':Label'];
        }
        paint(e, r) {
            if (r.effects.hide) return;
            let i = new Ot(r.shown_text);
            i.apply_at(r.at),
                i.apply_effects(r.effects),
                this.after_apply(r, i),
                r.at.rotation == 0 || r.at.rotation == 180
                    ? (i.text_angle.degrees = 0)
                    : (r.at.rotation == 90 || r.at.rotation == 270) && (i.text_angle.degrees = 90);
            let n = i.text_pos.add(this.get_schematic_text_offset(r, i));
            this.gfx.state.push(),
                (this.gfx.state.stroke = this.color),
                (this.gfx.state.fill = this.color),
                Y.default().draw(this.gfx, i.shown_text, n, i.attributes);
            let o = this.create_shape(r, i);
            o && this.gfx.line(o, i.attributes.stroke_width / 1e4), this.gfx.state.pop();
        }
        create_shape(e, r) {
            return [];
        }
        get color() {
            return new h(1, 0, 1, 1);
        }
        after_apply(e, r) {}
        get_text_offset(e) {
            return Math.round(A.text_offset_ratio * e.text_size.x);
        }
        get_box_expansion(e) {
            return Math.round(A.label_size_ratio * e.text_size.y);
        }
        get_schematic_text_offset(e, r) {
            let i = Math.round(this.get_text_offset(r) + r.get_effective_text_thickness());
            return r.text_angle.is_vertical ? new d(-i, 0) : new d(0, -i);
        }
    },
    w3 = class extends w2 {
        constructor() {
            super(...arguments);
            this.classes = [d2];
        }
        static {
            l(this, 'NetLabelPainter');
        }
        get color() {
            return this.theme.label_local;
        }
    },
    Y3 = class extends w2 {
        constructor() {
            super(...arguments);
            this.classes = [m2];
        }
        static {
            l(this, 'GlobalLabelPainter');
        }
        get color() {
            return this.theme.label_global;
        }
        get_schematic_text_offset(e, r) {
            let i = e,
                n = r.text_size.y,
                o = this.get_box_expansion(r),
                c = n * 0.0715;
            switch (
                (['input', 'bidirectional', 'tri_state'].includes(i.shape) && (o += n * 0.75),
                (o = Math.round(o)),
                (c = Math.round(c)),
                e.at.rotation)
            ) {
                case 0:
                    return new d(o, c);
                case 90:
                    return new d(c, -o);
                case 180:
                    return new d(-o, c);
                case 270:
                    return new d(c, o);
                default:
                    throw new Error(`Unexpected label rotation ${e.at.rotation}`);
            }
        }
        create_shape(e, r) {
            let i = e,
                n = r.text_pos,
                o = W.from_degrees(e.at.rotation + 180),
                c = r.text_size.y,
                u = this.get_box_expansion(r),
                p = c / 2 + u,
                m = r.get_text_box().w + 2 * u,
                b = r.attributes.stroke_width,
                M = m + b + 3,
                f = p + b + 3,
                V = [new d(0, 0), new d(0, -f), new d(-M, -f), new d(-M, 0), new d(-M, f), new d(0, f), new d(0, 0)],
                S = new d();
            switch (i.shape) {
                case 'input':
                    (S.x = -p), (V[0].x += p), (V[6].x += p);
                    break;
                case 'output':
                    V[3].x -= p;
                    break;
                case 'bidirectional':
                case 'tri_state':
                    (S.x = -p), (V[0].x += p), (V[6].x += p), (V[3].x -= p);
                    break;
                default:
                    break;
            }
            return (
                (V = V.map((y) =>
                    y
                        .add(S)
                        .rotate(o)
                        .add(n)
                        .multiply(1 / 1e4),
                )),
                V
            );
        }
    },
    K3 = class extends w2 {
        constructor() {
            super(...arguments);
            this.classes = [De];
        }
        static {
            l(this, 'HierarchicalLabelPainter');
        }
        get color() {
            return this.theme.label_hier;
        }
        after_apply(e, r) {
            r.v_align = 'center';
        }
        get_schematic_text_offset(e, r) {
            let i = Math.round(this.get_text_offset(r) + r.text_width);
            switch (e.at.rotation) {
                case 0:
                    return new d(i, 0);
                case 90:
                    return new d(0, -i);
                case 180:
                    return new d(-i, 0);
                case 270:
                    return new d(0, i);
                default:
                    throw new Error(`Unexpected label rotation ${e.at.rotation}`);
            }
        }
        create_shape(e, r) {
            let i = r.text_pos,
                n = W.from_degrees(e.at.rotation),
                o = r.text_width,
                c;
            switch (e.shape) {
                case 'output':
                    c = [
                        new d(0, o / 2),
                        new d(o / 2, o / 2),
                        new d(o, 0),
                        new d(o / 2, -o / 2),
                        new d(0, -o / 2),
                        new d(0, o / 2),
                    ];
                    break;
                case 'input':
                    c = [
                        new d(o, o / 2),
                        new d(o / 2, o / 2),
                        new d(0, 0),
                        new d(o / 2, -o / 2),
                        new d(o, -o / 2),
                        new d(o, o / 2),
                    ];
                    break;
                case 'bidirectional':
                case 'tri_state':
                    c = [new d(o / 2, o / 2), new d(o, 0), new d(o / 2, -o / 2), new d(0, 0), new d(o / 2, o / 2)];
                    break;
                case 'passive':
                default:
                    c = [new d(0, o / 2), new d(o, o / 2), new d(o, -o / 2), new d(0, -o / 2), new d(0, o / 2)];
                    break;
            }
            return (
                (c = c.map((u) =>
                    u
                        .rotate(n)
                        .add(i)
                        .multiply(1 / 1e4),
                )),
                c
            );
        }
    };
var H3 = class s extends K {
    constructor() {
        super(...arguments);
        this.classes = [b2];
    }
    static {
        l(this, 'PinPainter');
    }
    layers_for(e) {
        return [':Symbol:Pin', ':Symbol:Foreground', ':Interactive'];
    }
    paint(e, r) {
        if (r.definition.hide) return;
        let i = {
                pin: r,
                def: r.definition,
                position: r.definition.at.position.copy(),
                orientation: so(r.definition.at.rotation),
            },
            n = this.view_painter.current_symbol_transform,
            o = this.dim_if_needed(this.theme.pin);
        s.apply_symbol_transformations(i, n),
            this.gfx.state.push(),
            (this.gfx.state.matrix = U.identity()),
            (this.gfx.state.stroke = o),
            (e.name == ':Symbol:Pin' || e.name == ':Interactive') && this.draw_pin_shape(this.gfx, i),
            e.name == ':Symbol:Foreground' && this.draw_name_and_number(this.gfx, i),
            this.gfx.state.pop();
    }
    static apply_symbol_transformations(e, r) {
        for (let n = 0; n < r.rotations; n++) this.rotate(e, new d(0, 0), !0);
        r.mirror_x && this.mirror_vertically(e, new d(0, 0)), r.mirror_y && this.mirror_horizontally(e, new d(0, 0));
        let i = r.position.multiply(new d(1, -1));
        e.position = e.position.add(i).multiply(new d(1, -1));
    }
    static rotate(e, r, i = !1) {
        let n = W.from_degrees(i ? -90 : 90);
        if (((e.position = n.rotate_point(e.position, r)), i))
            switch (e.orientation) {
                case 'right':
                    e.orientation = 'up';
                    break;
                case 'up':
                    e.orientation = 'left';
                    break;
                case 'left':
                    e.orientation = 'down';
                    break;
                case 'down':
                    e.orientation = 'right';
                    break;
            }
        else
            switch (e.orientation) {
                case 'right':
                    e.orientation = 'down';
                    break;
                case 'down':
                    e.orientation = 'left';
                    break;
                case 'left':
                    e.orientation = 'up';
                    break;
                case 'up':
                    e.orientation = 'right';
                    break;
            }
    }
    static mirror_horizontally(e, r) {
        (e.position.x -= r.x),
            (e.position.x *= -1),
            (e.position.x += r.x),
            e.orientation == 'right' ? (e.orientation = 'left') : e.orientation == 'left' && (e.orientation = 'right');
    }
    static mirror_vertically(e, r) {
        (e.position.y -= r.y),
            (e.position.y *= -1),
            (e.position.y += r.y),
            e.orientation == 'up' ? (e.orientation = 'down') : e.orientation == 'down' && (e.orientation = 'up');
    }
    draw_pin_shape(e, r) {
        let { p0: i, dir: n } = sn.stem(r.position, r.orientation, r.def.length);
        sn.draw(e, r.def.type, r.def.shape, r.position, i, n);
    }
    draw_name_and_number(e, r) {
        let i = r.def,
            n = r.pin.parent.lib_symbol,
            o = i.name.text,
            c = i.number.text,
            u = i.length,
            p = n.pin_names.hide || !o || o == '~',
            m = n.pin_numbers.hide || !c || c == '~',
            b = A.line_width,
            M = n.pin_names.offset,
            f = 0.6096 * A.text_offset_ratio,
            V = i.number.effects.font.thickness || b,
            S = i.number.effects.font.thickness || b,
            y,
            v;
        M > 0
            ? ((y = p ? void 0 : wt.place_inside(M, S, u, r.orientation)),
              (v = m ? void 0 : wt.place_above(f, b, V, u, r.orientation)))
            : ((y = p ? void 0 : wt.place_above(f, b, S, u, r.orientation)),
              (v = m ? void 0 : wt.place_below(f, b, S, u, r.orientation))),
            y && wt.draw(e, o, r.position, y, i.name.effects, e.state.stroke),
            v && wt.draw(e, c, r.position, v, i.number.effects, e.state.stroke);
    }
};
function so(s) {
    switch (s) {
        case 0:
            return 'right';
        case 90:
            return 'up';
        case 180:
            return 'left';
        case 270:
            return 'down';
        default:
            throw new Error(`Unexpected pin angle ${s}`);
    }
}
l(so, 'angle_to_orientation');
var sn = {
        stem(s, t, e) {
            let r = new d(),
                i = new d();
            switch (t) {
                case 'up':
                    r.set(s.x, s.y - e), i.set(0, 1);
                    break;
                case 'down':
                    r.set(s.x, s.y + e), i.set(0, -1);
                    break;
                case 'left':
                    r.set(s.x - e, s.y), i.set(1, 0);
                    break;
                case 'right':
                    r.set(s.x + e, s.y), i.set(-1, 0);
                    break;
            }
            return { p0: r, dir: i };
        },
        draw(s, t, e, r, i, n) {
            let o = A.pinsymbol_size,
                c = o * 2,
                u = A.target_pin_radius;
            if (t == 'no_connect') {
                s.line([i, r]),
                    s.line([r.add(new d(-u, -u)), r.add(new d(u, u))]),
                    s.line([r.add(new d(u, -u)), r.add(new d(-u, u))]);
                return;
            }
            let p = l(() => {
                    n.y
                        ? s.line([i.add(new d(o, 0)), i.add(new d(0, -n.y * o)), i.add(new d(-o, 0))])
                        : s.line([i.add(new d(0, o)), i.add(new d(-n.x * o, 0)), i.add(new d(0, -o))]);
                }, 'clock_notch'),
                m = l(() => {
                    n.y
                        ? s.line([i.add(new d(0, n.y).multiply(c)), i.add(new d(-1, n.y).multiply(c)), i])
                        : s.line([i.add(new d(n.x, 0).multiply(c)), i.add(new d(n.x, -1).multiply(c)), i]);
                }, 'low_in_tri');
            switch (e) {
                case 'line':
                    s.line([i, r]);
                    return;
                case 'inverted':
                    s.arc(i.add(n.multiply(o)), o), s.line([i.add(n.multiply(c)), r]);
                    return;
                case 'inverted_clock':
                    s.arc(i.add(n.multiply(o)), o), s.line([i.add(n.multiply(c)), r]), p();
                    return;
                case 'clock':
                    s.line([i, r]), p();
                    return;
                case 'clock_low':
                case 'edge_clock_high':
                    s.line([i, r]), p(), m();
                    break;
                case 'input_low':
                    s.line([i, r]), m();
                    break;
                case 'output_low':
                    s.line([i, r]),
                        n.y
                            ? s.line([i.sub(new d(c, 0)), i.add(new d(0, n.y * c))])
                            : s.line([i.sub(new d(0, c)), i.add(new d(n.x * c, 0))]);
                    break;
                case 'non_logic':
                    s.line([i, r]),
                        s.line([
                            i.sub(new d(n.x + n.y, n.y - n.x).multiply(o)),
                            i.add(new d(n.x + n.y, n.y - n.x).multiply(o)),
                        ]),
                        s.line([
                            i.sub(new d(n.x - n.y, n.y + n.x).multiply(o)),
                            i.add(new d(n.x - n.y, n.y + n.x).multiply(o)),
                        ]);
                    break;
            }
        },
    },
    wt = {
        orient_label(s, t, e, r) {
            switch (t) {
                case 'right':
                    break;
                case 'left':
                    (s.x *= -1), e == 'left' && (e = 'right');
                    break;
                case 'up':
                    s = new d(s.y, -s.x);
                    break;
                case 'down':
                    (s = new d(s.y, s.x)), e == 'left' && (e = 'right');
                    break;
            }
            return { offset: s, h_align: e, v_align: r, orientation: t };
        },
        place_inside(s, t, e, r) {
            let i = new d(s - t / 2 + e, 0);
            return this.orient_label(i, r, 'left', 'center');
        },
        place_above(s, t, e, r, i) {
            let n = new d(r / 2, -(s + t / 2 + e / 2));
            return this.orient_label(n, i, 'center', 'bottom');
        },
        place_below(s, t, e, r, i) {
            let n = new d(r / 2, s + t / 2 + e / 2);
            return this.orient_label(n, i, 'center', 'top');
        },
        draw(s, t, e, r, i, n) {
            let o = new $(t);
            switch (
                (o.apply_effects(i),
                (o.attributes.h_align = r.h_align),
                (o.attributes.v_align = r.v_align),
                (o.attributes.color = n),
                (o.text_pos = e.add(r.offset).multiply(1e4)),
                r.orientation)
            ) {
                case 'up':
                case 'down':
                    o.text_angle = W.from_degrees(90);
                    break;
                case 'left':
                case 'right':
                    o.text_angle = W.from_degrees(0);
                    break;
            }
            Y.default().draw(s, o.shown_text, o.text_pos, o.attributes);
        },
    };
var Hi = class extends He {
        constructor() {
            super(...arguments);
            this.shapes = [];
        }
        static {
            l(this, 'NullRenderLayer');
        }
        dispose() {
            this.clear();
        }
        clear() {
            this.shapes = [];
        }
        render(e) {}
    },
    G3 = class extends Ke {
        static {
            l(this, 'NullRenderer');
        }
        #e;
        constructor() {
            super(null);
        }
        set background_color(t) {}
        async setup() {}
        async dispose() {}
        update_canvas_size() {}
        clear_canvas() {}
        start_layer(t) {
            this.#e = new Hi(this, t);
        }
        end_layer() {
            return this.#e;
        }
        get layers() {
            return [];
        }
        circle(t, e, r) {
            this.#e.shapes.push(super.prep_circle(t, e, r));
        }
        arc(t, e, r, i, n, o) {
            this.#e.shapes.push(super.prep_arc(t, e, r, i, n, o));
        }
        line(t, e, r) {
            this.#e.shapes.push(super.prep_line(t, e, r));
        }
        polygon(t, e) {
            this.#e.shapes.push(super.prep_polygon(t, e));
        }
        remove_layer(t) {}
    };
var E3 = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [Vt];
        }
        static {
            l(this, 'LibSymbolPainter');
        }
        layers_for(e) {
            return [':Symbol:Background', ':Symbol:Foreground', ':Symbol:Field'];
        }
        paint(e, r, i = 1) {
            if (![':Symbol:Background', ':Symbol:Foreground', ':Interactive'].includes(e.name)) return;
            let n = r.units.get(0);
            n && this.#e(e, n, i);
            let o = this.view_painter.current_symbol,
                c = r.units.get(o?.unit || 1);
            c && this.#e(e, c, i);
        }
        #e(e, r, i = 1) {
            for (let n of r)
                if (!(n.style > 0 && i != n.style)) for (let o of n.drawings) this.view_painter.paint_item(e, o);
        }
    },
    J3 = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [re];
        }
        static {
            l(this, 'SchematicSymbolPainter');
        }
        layers_for(e) {
            let r = [':Interactive', ':Symbol:Foreground', ':Symbol:Background', ':Symbol:Field', ':Symbol:Pin'];
            return e.dnp && r.push(':Marks'), r;
        }
        paint(e, r) {
            if (e.name == ':Interactive' && r.lib_symbol.power) return;
            let i = no(r);
            (this.view_painter.current_symbol = r),
                (this.view_painter.current_symbol_transform = i),
                this.gfx.state.push(),
                (this.gfx.state.matrix = U.translation(r.at.position.x, r.at.position.y)),
                this.gfx.state.multiply(i.matrix);
            let n = r.convert ?? 1;
            if (
                (this.view_painter.paint_item(e, r.lib_symbol, n),
                this.gfx.state.pop(),
                [':Symbol:Pin', ':Symbol:Foreground', ':Interactive'].includes(e.name))
            )
                for (let o of r.unit_pins) this.view_painter.paint_item(e, o);
            if (e.name == ':Symbol:Field' || e.name == ':Interactive')
                for (let [o, c] of r.properties) this.view_painter.paint_item(e, c);
            if (r.dnp && e.name == ':Marks') {
                let o = oo(this.theme, r),
                    c = A.line_width * 3,
                    u = this.theme.erc_error;
                this.gfx.line([o.top_left, o.bottom_right], c, u), this.gfx.line([o.bottom_left, o.top_right], c, u);
            }
            this.view_painter.current_symbol = void 0;
        }
    };
function no(s) {
    let t = new U([1, 0, 0, 0, -1, 0, 0, 0, 1]),
        e = new U([0, -1, 0, -1, 0, 0, 0, 0, 1]),
        r = new U([-1, 0, 0, 0, 1, 0, 0, 0, 1]),
        i = new U([0, 1, 0, 1, 0, 0, 0, 0, 1]),
        n = 0,
        o = t;
    if (s.at.rotation != 0)
        if (s.at.rotation == 90) (n = 1), (o = e);
        else if (s.at.rotation == 180) (n = 2), (o = r);
        else if (s.at.rotation == 270) (n = 3), (o = i);
        else throw new Error(`unexpected rotation ${s.at.rotation}`);
    if (s.mirror == 'y') {
        let c = o.elements[0] * -1,
            u = o.elements[3] * -1,
            p = o.elements[1],
            m = o.elements[4];
        (o.elements[0] = c), (o.elements[1] = p), (o.elements[3] = u), (o.elements[4] = m);
    } else if (s.mirror == 'x') {
        let c = o.elements[0],
            u = o.elements[3],
            p = o.elements[1] * -1,
            m = o.elements[4] * -1;
        (o.elements[0] = c), (o.elements[1] = p), (o.elements[3] = u), (o.elements[4] = m);
    }
    return { matrix: o, position: s.at.position, rotations: n, mirror_x: s.mirror == 'x', mirror_y: s.mirror == 'y' };
}
l(no, 'get_symbol_transform');
function oo(s, t) {
    let e = new G3(),
        r = new vt(s),
        i = new Yt(e, r, s),
        n = [':Symbol:Foreground', ':Symbol:Background', ':Symbol:Pin'],
        o = [];
    for (let c of n) {
        let u = r.by_name(c);
        u.items.push(t), i.paint_layer(u), o.push(u.bbox);
    }
    return O.combine(o);
}
l(oo, 'get_symbol_body_and_pins_bbox');
var Gi = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [ft];
        }
        static {
            l(this, 'RectanglePainter');
        }
        layers_for(e) {
            return [':Notes'];
        }
        paint(e, r) {
            let i = [r.start, new d(r.end.x, r.start.y), r.end, new d(r.start.x, r.end.y), r.start];
            this.#t(e, r, i), this.#e(e, r, i);
        }
        #e(e, r, i) {
            let { width: n, color: o } = this.determine_stroke(e, r);
            !n || !o || this.gfx.line(new F(i, r.stroke?.width || this.gfx.state.stroke_width, o));
        }
        #t(e, r, i) {
            let n = this.determine_fill(e, r);
            n && this.gfx.polygon(new I(i, n));
        }
    },
    Ei = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [Mt];
        }
        static {
            l(this, 'PolylinePainter');
        }
        layers_for(e) {
            return [':Notes'];
        }
        paint(e, r) {
            this.#t(e, r), this.#e(e, r);
        }
        #e(e, r) {
            let { width: i, color: n } = this.determine_stroke(e, r);
            !i || !n || this.gfx.line(new F(r.pts, i, n));
        }
        #t(e, r) {
            let i = this.determine_fill(e, r);
            i && this.gfx.polygon(new I(r.pts, i));
        }
    },
    Ji = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [a2];
        }
        static {
            l(this, 'WirePainter');
        }
        layers_for(e) {
            return [':Wire'];
        }
        paint(e, r) {
            this.gfx.line(new F(r.pts, this.gfx.state.stroke_width, this.theme.wire));
        }
    },
    Ii = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [l2];
        }
        static {
            l(this, 'BusPainter');
        }
        layers_for(e) {
            return [':Wire'];
        }
        paint(e, r) {
            this.gfx.line(new F(r.pts, A.bus_width, this.theme.bus));
        }
    },
    ki = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [c2];
        }
        static {
            l(this, 'BusEntryPainter');
        }
        layers_for(e) {
            return [':Junction'];
        }
        paint(e, r) {
            this.gfx.line(new F([r.at.position, r.at.position.add(r.size)], A.wire_width, this.theme.wire));
        }
    },
    Ai = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [p2];
        }
        static {
            l(this, 'CirclePainter');
        }
        layers_for(e) {
            return [':Notes'];
        }
        paint(e, r) {
            this.#t(e, r), this.#e(e, r);
        }
        #e(e, r) {
            let { width: i, color: n } = this.determine_stroke(e, r);
            !i || !n || this.gfx.arc(new Ye(r.center, r.radius, new W(0), new W(Math.PI * 2), i, n));
        }
        #t(e, r) {
            let i = this.determine_fill(e, r);
            i && this.gfx.circle(new B(r.center, r.radius, i));
        }
    },
    Ci = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [_t];
        }
        static {
            l(this, 'ArcPainter');
        }
        layers_for(e) {
            return [':Notes'];
        }
        paint(e, r) {
            let i = z.from_three_points(r.start, r.mid, r.end, r.stroke?.width);
            this.#t(e, r, i), this.#e(e, r, i);
        }
        #e(e, r, i) {
            let { width: n, color: o } = this.determine_stroke(e, r);
            !n || !o || this.gfx.arc(new Ye(i.center, i.radius, i.start_angle, i.end_angle, n, o));
        }
        #t(e, r, i) {
            let n = this.determine_fill(e, r);
            n && this.gfx.polygon(new I(i.to_polygon(), n));
        }
    },
    Di = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [R2];
        }
        static {
            l(this, 'JunctionPainter');
        }
        layers_for(e) {
            return [':Junction'];
        }
        paint(e, r) {
            let i = this.theme.junction;
            this.gfx.circle(new B(r.at.position, (r.diameter || 1) / 2, i));
        }
    },
    Bi = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [u2];
        }
        static {
            l(this, 'NoConnectPainter');
        }
        layers_for(e) {
            return [':Junction'];
        }
        paint(e, r) {
            let i = this.theme.no_connect,
                n = A.line_width,
                o = A.noconnect_size / 2;
            this.gfx.state.push(),
                this.gfx.state.matrix.translate_self(r.at.position.x, r.at.position.y),
                this.gfx.line(new F([new d(-o, -o), new d(o, o)], n, i)),
                this.gfx.line(new F([new d(o, -o), new d(-o, o)], n, i)),
                this.gfx.state.pop();
        }
    },
    $i = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [Nt];
        }
        static {
            l(this, 'TextPainter');
        }
        layers_for(e) {
            return [':Notes'];
        }
        paint(e, r) {
            if (r.effects.hide || !r.text) return;
            let i = new Ot(r.shown_text);
            i.apply_at(r.at), i.apply_effects(r.effects);
            let n = r.effects.font.color;
            if (n.is_transparent_black) {
                let o = this.theme.note;
                i.attributes.color = this.dim_if_needed(o);
            } else i.attributes.color = this.dim_if_needed(n);
            this.gfx.state.push(),
                Y.default().draw(this.gfx, i.shown_text, i.text_pos, i.attributes),
                this.gfx.state.pop();
        }
    },
    ji = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [we];
        }
        static {
            l(this, 'PropertyPainter');
        }
        layers_for(e) {
            return [':Symbol:Field', ':Interactive'];
        }
        paint(e, r) {
            if (r.effects.hide || !r.text) return;
            let i = this.theme.fields;
            r.parent instanceof ne && (i = this.theme.sheet_fields);
            let n = r.effects.font.color;
            if (n.is_transparent_black) {
                switch (r.name) {
                    case 'Reference':
                        i = this.theme.reference;
                        break;
                    case 'Value':
                        i = this.theme.value;
                        break;
                    case 'Sheet name':
                        i = this.theme.sheet_name;
                        break;
                    case 'Sheet file':
                        i = this.theme.sheet_filename;
                        break;
                }
                i = this.dim_if_needed(i);
            } else i = this.dim_if_needed(n);
            let o = r.parent,
                u = this.view_painter.current_symbol_transform?.matrix ?? U.identity(),
                p = r.shown_text;
            r.name == 'Reference' && o.unit && (p += o.unit_suffix);
            let m = new P3(p, { position: o.at.position.multiply(1e4), transform: u, is_symbol: o instanceof re });
            m.apply_effects(r.effects), (m.attributes.angle = W.from_degrees(r.at.rotation));
            let b = r.at.position.multiply(1e4).sub(m.parent.position);
            (b = u.inverse().transform(b)), (b = b.add(m.parent.position)), (m.text_pos = b);
            let M = m.draw_rotation,
                f = m.bounding_box,
                V = f.center;
            (m.attributes.angle = M),
                (m.attributes.h_align = 'center'),
                (m.attributes.v_align = 'center'),
                (m.attributes.stroke_width = m.get_effective_text_thickness(A.line_width * 1e4)),
                (m.attributes.color = i);
            let S = U.scaling(1e-4, 1e-4).transform_all([
                f.top_left,
                f.top_right,
                f.bottom_right,
                f.bottom_left,
                f.top_left,
            ]);
            e.name == ':Interactive'
                ? this.gfx.line(new F(Array.from(S), 0.1, h.white))
                : (this.gfx.state.push(),
                  Y.default().draw(this.gfx, m.shown_text, V, m.attributes),
                  this.gfx.state.pop());
        }
    },
    zi = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [h2];
        }
        static {
            l(this, 'LibTextPainter');
        }
        layers_for(e) {
            return [':Symbol:Foreground'];
        }
        paint(e, r) {
            if (r.effects.hide || !r.text) return;
            let i = this.view_painter.current_symbol_transform,
                n = new g3(r.shown_text);
            n.apply_effects(r.effects),
                n.apply_at(r.at),
                n.apply_symbol_transformations(i),
                (n.attributes.color = this.dim_if_needed(this.theme.component_outline));
            let o = n.world_pos;
            (n.attributes.v_align = 'center'),
                this.gfx.state.push(),
                (this.gfx.state.matrix = U.identity()),
                Y.default().draw(this.gfx, n.shown_text, o, n.attributes),
                this.gfx.state.pop();
        }
        paint_debug(e) {
            this.gfx.line(F.from_BBox(e.scale(1 / 1e4), 0.127, new h(0, 0, 1, 1))),
                this.gfx.circle(new B(e.center.multiply(1 / 1e4), 0.2, new h(0, 1, 0, 1)));
        }
    },
    qi = class extends K {
        constructor() {
            super(...arguments);
            this.classes = [ne];
        }
        static {
            l(this, 'SchematicSheetPainter');
        }
        layers_for(e) {
            return [':Interactive', ':Label', ':Symbol:Foreground', ':Symbol:Background', ':Symbol:Field'];
        }
        paint(e, r) {
            let i = this.theme.sheet,
                n = this.theme.sheet_background,
                o = new O(r.at.position.x, r.at.position.y, r.size.x, r.size.y);
            if (
                (e.name == ':Interactive' && this.gfx.polygon(I.from_BBox(o.grow(3), n)),
                e.name == ':Symbol:Background' && this.gfx.polygon(I.from_BBox(o, n)),
                e.name == ':Symbol:Foreground' && this.gfx.line(F.from_BBox(o, this.gfx.state.stroke_width, i)),
                e.name == ':Symbol:Field')
            )
                for (let c of r.properties.values()) this.view_painter.paint_item(e, c);
            if (e.name == ':Label')
                for (let c of r.pins) {
                    let u = new De();
                    switch (
                        ((u.at = c.at.copy()),
                        (u.effects = c.effects),
                        (u.text = c.name),
                        (u.shape = c.shape),
                        u.at.rotation)
                    ) {
                        case 0:
                            u.at.rotation = 180;
                            break;
                        case 180:
                            u.at.rotation = 0;
                            break;
                        case 90:
                            u.at.rotation = 270;
                            break;
                        case 270:
                            u.at.rotation = 90;
                            break;
                    }
                    c.shape == 'input' ? (u.shape = 'output') : c.shape == 'output' && (u.shape = 'input'),
                        this.view_painter.paint_item(e, u);
                }
        }
    },
    Yt = class extends v3 {
        constructor(e, r, i) {
            super(e, r, i);
            this.painter_list = [
                new Gi(this, e),
                new Ei(this, e),
                new Ji(this, e),
                new Ii(this, e),
                new ki(this, e),
                new Ai(this, e),
                new Ci(this, e),
                new Di(this, e),
                new Bi(this, e),
                new $i(this, e),
                new zi(this, e),
                new H3(this, e),
                new E3(this, e),
                new ji(this, e),
                new J3(this, e),
                new w3(this, e),
                new Y3(this, e),
                new K3(this, e),
                new qi(this, e),
            ];
        }
        static {
            l(this, 'SchematicPainter');
        }
    };
var I3 = class extends Ft {
    static {
        l(this, 'SchematicViewer');
    }
    get schematic() {
        return this.document;
    }
    create_renderer(t) {
        let e = new Q3(t);
        return (e.state.fill = this.theme.note), (e.state.stroke = this.theme.note), (e.state.stroke_width = 0.1524), e;
    }
    async load(t) {
        if (t instanceof me) return await super.load(t);
        this.document = null;
        let e = t.document;
        return e.update_hierarchical_data(t.sheet_path), await super.load(e);
    }
    create_painter() {
        return new Yt(this.renderer, this.layers, this.theme);
    }
    create_layer_set() {
        return new vt(this.theme);
    }
    select(t) {
        if (
            (G(t) && (t = this.schematic.find_symbol(t) ?? this.schematic.find_sheet(t)),
            t instanceof re || t instanceof ne)
        ) {
            let e = this.layers.query_item_bboxes(t);
            t = Ct(e) ?? null;
        }
        super.select(t);
    }
};
var es = class extends Le {
    static {
        l(this, 'KCSchematicViewerElement');
    }
    update_theme() {
        this.viewer.theme = this.themeObject.schematic;
    }
    make_viewer() {
        return new I3(this.canvas, !this.disableinteraction, this.themeObject.schematic);
    }
};
window.customElements.define('kc-schematic-viewer', es);
var ts = class extends N {
    static {
        l(this, 'KCSchematicInfoPanel');
    }
    connectedCallback() {
        (async () => (
            (this.viewer = await this.requestLazyContext('viewer')),
            await this.viewer.loaded,
            super.connectedCallback(),
            this.addDisposable(
                this.viewer.addEventListener(ie.type, (e) => {
                    this.update();
                }),
            )
        ))();
    }
    render() {
        let e = this.viewer.drawing_sheet,
            r = this.viewer.schematic,
            i = l(
                (c) => _`<kc-ui-property-list-item
                class="label"
                name="${c}"></kc-ui-property-list-item>`,
                'header',
            ),
            n = l(
                (c, u, p = '') => _`<kc-ui-property-list-item name="${c}">
                ${u} ${p}
            </kc-ui-property-list-item>`,
                'entry',
            ),
            o = Object.entries(r.title_block?.comment || {}).map(([c, u]) => n(`Comment ${c}`, u));
        return _`
            <kc-ui-panel>
                <kc-ui-panel-title title="Info"></kc-ui-panel-title>
                <kc-ui-panel-body>
                    <kc-ui-property-list>
                        ${i('Page properties')}
                        ${n('Size', e.paper?.size)}
                        ${n('Width', e.width, 'mm')}
                        ${n('Height', e.height, 'mm')}
                        ${i('Schematic properties')}
                        ${n('KiCAD version', r.version)}
                        ${n('Generator', r.generator)}
                        ${n('Title', r.title_block?.title)}
                        ${n('Date', r.title_block?.date)}
                        ${n('Revision', r.title_block?.rev)}
                        ${n('Company', r.title_block?.company)}
                        ${o}
                        ${n('Symbols', r.symbols.size)}
                        ${n('Unique symbols', r.lib_symbols?.symbols.length ?? 0)}
                        ${n('Wires', r.wires.length)}
                        ${n('Buses', r.buses.length)}
                        ${n('Junctions', r.junctions.length)}
                        ${n('Net labels', r.net_labels.length)}
                        ${n('Global labels', r.global_labels.length)}
                        ${n('Hierarchical labels', r.hierarchical_labels.length)}
                        ${n('No connects', r.no_connects.length)}
                    </dl>
                </kc-ui-property-list>
            </kc-ui-panel>
        `;
    }
};
window.customElements.define('kc-schematic-info-panel', ts);
var rs = class extends N {
    static {
        l(this, 'KCSchematicPropertiesPanelElement');
    }
    connectedCallback() {
        (async () => (
            (this.viewer = await this.requestLazyContext('viewer')),
            await this.viewer.loaded,
            super.connectedCallback(),
            this.setup_events()
        ))();
    }
    setup_events() {
        this.addDisposable(
            this.viewer.addEventListener(D.type, (e) => {
                (this.selected_item = e.detail.item), this.update();
            }),
        ),
            this.addDisposable(
                this.viewer.addEventListener(ie.type, (e) => {
                    (this.selected_item = void 0), this.update();
                }),
            );
    }
    render() {
        let e = l(
                (c) => _`<kc-ui-property-list-item
                class="label"
                name="${c}"></kc-ui-property-list-item>`,
                'header',
            ),
            r = l(
                (c, u, p = '') => _`<kc-ui-property-list-item name="${c}">
                ${u ?? ''} ${p}
            </kc-ui-property-list-item>`,
                'entry',
            ),
            i = l((c) => (c ? _`<kc-ui-icon>check</kc-ui-icon>` : _`<kc-ui-icon>close</kc-ui-icon>`), 'checkbox'),
            n,
            o = this.selected_item;
        if (!o) n = e('No item selected');
        else if (o instanceof re) {
            let c = o.lib_symbol,
                u = Array.from(o.properties.values()).map((m) => r(m.name, m.text)),
                p = pe(o.unit_pins, (m) => m.number).map((m) => r(m.number, m.definition.name.text));
            n = _`
                ${e('Basic properties')}
                ${r('X', o.at.position.x.toFixed(4), 'mm')}
                ${r('Y', o.at.position.y.toFixed(4), 'mm')}
                ${r('Orientation', o.at.rotation, '\xB0')}
                ${r('Mirror', o.mirror == 'x' ? 'Around X axis' : o.mirror == 'y' ? 'Around Y axis' : 'Not mirrored')}
                ${e('Instance properties')}
                ${r('Library link', o.lib_name ?? o.lib_id)}
                ${o.unit ? r('Unit', String.fromCharCode('A'.charCodeAt(0) + o.unit - 1)) : ''}
                ${r('In BOM', i(o.in_bom))}
                ${r('On board', i(o.in_bom))}
                ${r('Populate', i(!o.dnp))} ${e('Fields')}
                ${u} ${e('Symbol properties')}
                ${r('Name', c.name)}
                ${r('Description', c.description)}
                ${r('Keywords', c.keywords)}
                ${r('Power', i(c.power))}
                ${r('Units', c.unit_count)}
                ${r('Units are interchangeable', i(c.units_interchangable))}
                ${e('Pins')} ${p}
            `;
        } else if (o instanceof ne) {
            let c = Array.from(o.properties.values()).map((p) => r(p.name, p.text)),
                u = pe(o.pins, (p) => p.name).map((p) => r(p.name, p.shape));
            n = _`
                ${e('Basic properties')}
                ${r('X', o.at.position.x.toFixed(4), 'mm')}
                ${r('Y', o.at.position.y.toFixed(4), 'mm')}
                ${e('Fields')} ${c} ${e('Pins')} ${u}
            `;
        }
        return _`
            <kc-ui-panel>
                <kc-ui-panel-title title="Properties"></kc-ui-panel-title>
                <kc-ui-panel-body>
                    <kc-ui-property-list>${n}</kc-ui-property-list>
                </kc-ui-panel-body>
            </kc-ui-panel>
        `;
    }
};
window.customElements.define('kc-schematic-properties-panel', rs);
var Kt = class extends N {
    static {
        l(this, 'KCSchematicSymbolsPanelElement');
    }
    connectedCallback() {
        (async () => (
            (this.viewer = await this.requestLazyContext('viewer')),
            await this.viewer.loaded,
            super.connectedCallback(),
            this.setup_initial_events()
        ))();
    }
    setup_initial_events() {
        let e = !1;
        this.addEventListener('kc-ui-menu:select', (r) => {
            if (e) return;
            let i = r.detail;
            i.name && this.viewer.select(i.name);
        }),
            this.addDisposable(
                this.viewer.addEventListener(D.type, () => {
                    (e = !0), (this.menu.selected = this.viewer.selected?.context.uuid ?? null), (e = !1);
                }),
            ),
            this.addDisposable(
                this.viewer.addEventListener(ie.type, () => {
                    this.update();
                }),
            );
    }
    renderedCallback() {
        this.search_input_elm.addEventListener('input', (e) => {
            this.item_filter_elem.filter_text = this.search_input_elm.value ?? null;
        });
    }
    render() {
        let e = this.viewer.schematic,
            r = [],
            i = [],
            n = [],
            o = pe(Array.from(e.symbols.values()), (u) => u.reference);
        for (let u of o) {
            let p = `${u.reference} ${u.value} ${u.id} ${u.lib_symbol.name}`,
                m = _`<kc-ui-menu-item
                name="${u.uuid}"
                data-match-text="${p}">
                <span class="narrow"> ${u.reference} </span>
                <span> ${u.value} </span>
            </kc-ui-menu-item>`;
            u.lib_symbol.power ? i.push(m) : r.push(m);
        }
        let c = pe(e.sheets, (u) => u.sheetname ?? u.sheetfile ?? '');
        for (let u of c) {
            let p = `${u.sheetname} ${u.sheetfile}`;
            n.push(_`<kc-ui-menu-item
                    name="${u.uuid}"
                    data-match-text="${p}">
                    <span class="narrow"> ${u.sheetname}</span>
                    <span>${u.sheetfile}</span>
                </kc-ui-menu-item>`);
        }
        return _`
            <kc-ui-panel>
                <kc-ui-panel-title title="Symbols"></kc-ui-panel-title>
                <kc-ui-panel-body>
                    <kc-ui-text-filter-input></kc-ui-text-filter-input>
                    <kc-ui-filtered-list>
                        <kc-ui-menu class="outline">
                            ${r}
                            ${
                                i.length
                                    ? _`<kc-ui-menu-label
                                      >Power symbols</kc-ui-menu-label
                                  >`
                                    : null
                            }
                            ${i}
                            ${
                                n.length
                                    ? _`<kc-ui-menu-label
                                      >Sheets</kc-ui-menu-label
                                  >`
                                    : null
                            }
                            ${n}
                        </kc-ui-menu>
                    </kc-ui-filtered-list>
                </kc-ui-panel-body>
            </kc-ui-panel>
        `;
    }
};
P([Q('kc-ui-menu')], Kt.prototype, 'menu', 2),
    P([Q('kc-ui-text-filter-input', !0)], Kt.prototype, 'search_input_elm', 2),
    P([Q('kc-ui-filtered-list', !0)], Kt.prototype, 'item_filter_elem', 2);
window.customElements.define('kc-schematic-symbols-panel', Kt);
var is = class extends Se {
    static {
        l(this, 'KCSchematicAppElement');
    }
    on_viewer_select(t, e) {
        if (!(!t || t != e)) {
            if (t instanceof ne) {
                this.project.set_active_page(`${t.sheetfile}:${t.path}/${t.uuid}`);
                return;
            }
            this.change_activity('properties');
        }
    }
    can_load(t) {
        return t.document instanceof me;
    }
    make_viewer_element() {
        return _`<kc-schematic-viewer></kc-schematic-viewer>`;
    }
    make_activities() {
        return [
            _`<kc-ui-activity
                slot="activities"
                name="Symbols"
                icon="interests">
                <kc-schematic-symbols-panel></kc-schematic-symbols-panel>
            </kc-ui-activity>`,
            _`<kc-ui-activity
                slot="activities"
                name="Properties"
                icon="list">
                <kc-schematic-properties-panel></kc-schematic-properties-panel>
            </kc-ui-activity>`,
            _`<kc-ui-activity slot="activities" name="Info" icon="info">
                <kc-schematic-info-panel></kc-schematic-info-panel>
            </kc-ui-activity>`,
        ];
    }
};
window.customElements.define('kc-schematic-app', is);
var k3 = `:host{font-size:var(--font-size, 16px);--transition-time-very-short: .1s;--transition-time-short: .2s;--transition-time-medium: .5s;--bg: #131218;--fg: #f8f8f0;--tooltip-bg: #8864cb;--tooltip-fg: #f8f8f0;--tooltip-border: 1px solid #131218;--scrollbar-bg: #131218;--scrollbar-fg: #ae81ff66;--scrollbar-active-fg: #ae81ff;--scrollbar-hover-bg: #ae81ffbb;--activity-bar-bg: #282634;--activity-bar-fg: #f8f8f0;--activity-bar-active-bg: #131218;--activity-bar-active-fg: #f8f8f0;--resizer-bg: #ae81ff;--resizer-active-bg: #ae81ffbb;--panel-bg: #131218;--panel-fg: #f8f8f0;--panel-border: 2px solid #282634;--panel-title-bg: #8077a8;--panel-title-fg: #f8f8f0;--panel-title-border: 1px solid #634e89;--panel-title-button-bg: transparent;--panel-title-button-fg: #dcc8ff;--panel-title-button-hover-bg: #ae81ff;--panel-title-button-hover-fg: inherit;--panel-title-button-disabled-bg: inherit;--panel-title-button-disabled-fg: #888;--panel-subtitle-bg: #634e89;--panel-subtitle-fg: var(--panel-fg);--dropdown-bg: #464258;--dropdown-fg: #f8f8f0;--button-bg: #81eeff;--button-fg: #131218;--button-hover-bg: #a3f3ff;--button-hover-fg: #131218;--button-focus-outline: 1px solid #ae81ff;--button-selected-bg: #ae81ff;--button-selected-fg: #131218;--button-disabled-bg: #131218;--button-disabled-fg: #888;--button-success-bg: #64cb96;--button-success-fg: #131218;--button-success-hover-bg: #81ffbe;--button-success-hover-fg: #131218;--button-danger-bg: #cb6488;--button-danger-fg: #131218;--button-danger-hover-bg: #ff81ad;--button-danger-hover-fg: #131218;--button-outline-bg: #282634;--button-outline-fg: #f8f8f0;--button-outline-hover-bg: #282634;--button-outline-hover-fg: #81eeff;--button-outline-disabled-bg: #131218;--button-outline-disabled-fg: #888;--button-toolbar-bg: #282634;--button-toolbar-fg: #f8f8f0;--button-toolbar-hover-bg: #282634;--button-toolbar-hover-fg: #81eeff;--button-toolbar-disabled-bg: #131218;--button-toolbar-disabled-fg: #888;--button-menu-bg: transparent;--button-menu-fg: #f8f8f0;--button-menu-hover-bg: transparent;--button-menu-hover-fg: #81eeff;--button-menu-disabled-bg: transparent;--button-menu-disabled-fg: #888;--input-bg: #131218;--input-fg: #f8f8f0;--input-border: 1px solid #8077a8;--input-accent: #ae81ff;--input-hover-shadow: 1px 1px 10px 5px rgba(0, 0, 0, .2);--input-focus-outline: 1px solid #ae81ff;--input-placeholder: #8077a8;--input-disabled-bg: #131218;--input-disabled-fg: #888;--input-range-bg: #8077a8;--input-range-fg: #f8f8f0;--input-range-hover-bg: #ae81ff;--input-range-disabled-bg: #131218;--input-range-hover-shadow: 1px 1px 10px 5px rgba(0, 0, 0, .2);--input-range-handle-shadow: 1px 1px 5px 5px rgba(180, 180, 180, .2);--list-item-bg: var(--panel-bg);--list-item-fg: var(--panel-fg);--list-item-active-bg: #634e89;--list-item-active-fg: var(--list-item-fg);--list-item-hover-bg: #64cb96;--list-item-hover-fg: var(--list-item-bg);--list-item-disabled-bg: var(--list-item-bg);--list-item-disabled-fg: #888;--grid-outline: #433e56}:host{--gradient-purple-green-light: linear-gradient( 190deg, hsl(261deg 27% 42%) 0%, hsl(243deg 27% 42%) 17%, hsl(224deg 27% 42%) 33%, hsl(205deg 27% 42%) 50%, hsl(187deg 27% 42%) 67%, hsl(168deg 27% 42%) 83%, hsl(149deg 27% 42%) 100% ) 0 0 fixed;--gradient-purple-blue-medium: linear-gradient( 190deg, hsl(261deg 28% 30%) 0%, hsl(248deg 30% 31%) 17%, hsl(235deg 32% 32%) 33%, hsl(222deg 34% 33%) 50%, hsl(209deg 35% 34%) 67%, hsl(197deg 37% 35%) 83%, hsl(183deg 38% 36%) 100% ) 0 0 fixed;--gradient-purple-blue-dark: linear-gradient(10deg, #111928, #1d162a) 0 0 fixed;--gradient-cyan-blue-light: linear-gradient( 190deg, hsl(183deg 63% 33%) 0%, hsl(189deg 69% 30%) 17%, hsl(194deg 74% 27%) 33%, hsl(199deg 79% 24%) 50%, hsl(203deg 85% 21%) 67%, hsl(209deg 89% 18%) 83%, hsl(214deg 95% 15%) 100% ) 0 0 fixed;--gradient-purple-green-highlight: linear-gradient( 190deg, hsl(261deg 27% 53%) 0%, hsl(243deg 27% 52%) 17%, hsl(224deg 27% 52%) 33%, hsl(205deg 27% 51%) 50%, hsl(186deg 27% 51%) 67%, hsl(168deg 27% 50%) 83%, hsl(149deg 27% 50%) 100% ) 0 0 fixed;--gradient-purple-red: linear-gradient(90deg, #8864cb, #cb6488) 0 0 fixed;--gradient-purple-red-highlight: linear-gradient(90deg, #b187ff, #ff80ac) 0 0 fixed;--scrollbar-bg: var(--gradient-purple-blue-dark);--scrollbar-fg: var(--gradient-purple-green-light);--scrollbar-hover-fg: var(--scrollbar-fg);--scrollbar-active-fg: var(--scrollbar-fg);--activity-bar-bg: var(--gradient-purple-green-light);--resizer-bg: var(--gradient-purple-blue-medium);--resizer-active-bg: var(--gradient-purple-green-highlight);--panel-bg: var(--gradient-purple-blue-dark);--panel-title-bg: var(--gradient-purple-green-light);--panel-subtitle-bg: var(--gradient-purple-blue-medium);--button-toolbar-bg: var(--gradient-purple-blue-dark);--button-toolbar-hover-bg: var(--gradient-purple-green-light);--button-toolbar-hover-fg: #f8f8f0;--button-toolbar-disabled-bg: var(--gradient-purple-blue-dark);--button-toolbar-alt-bg: var(--gradient-purple-green-light);--button-toolbar-alt-hover-bg: var(--gradient-purple-green-highlight);--button-toolbar-alt-hover-fg: #f8f8f0;--button-toolbar-alt-disabled-bg: var(--gradient-purple-blue-dark);--dropdown-bg: var(--gradient-purple-green-light);--dropdown-fg: #f8f8f0;--dropdown-hover-bg: var(--gradient-purple-green-highlight);--dropdown-hover-fg: #f8f8f0;--dropdown-active-bg: var(--gradient-purple-blue-dark);--dropdown-active-fg: #f8f8f0;--input-range-bg: var(--gradient-purple-green-light);--list-item-hover-bg: var(--gradient-purple-green-highlight);--list-item-active-bg: var(--gradient-cyan-blue-light);--focus-overlay-bg: var(--gradient-purple-green-light);--focus-overlay-opacity: .5;--focus-overlay-fg: #f8f8f0}::-webkit-scrollbar{position:absolute;width:6px;height:6px;margin-left:-6px;background:var(--scrollbar-bg)}::-webkit-scrollbar-thumb{position:absolute;background:var(--scrollbar-fg)}::-webkit-scrollbar-thumb:hover{background:var(--scrollbar-hover-fg)}::-webkit-scrollbar-thumb:active{background:var(--scrollbar-active-fg)}kc-ui-app{width:100%;height:100%;flex-grow:1;display:flex;flex-direction:row;overflow:hidden}label{display:block;width:100%;margin-top:.75em}input,select,textarea{all:unset;box-sizing:border-box;display:block;width:100%;max-width:100%;margin-top:.5em;font-family:inherit;border-radius:.25em;text-align:center;padding:.25em;background:var(--input-bg);color:var(--input-fg);transition:color var(--transition-time-medium) ease,box-shadow var(--transition-time-medium) ease,outline var(--transition-time-medium) ease,background var(--transition-time-medium) ease,border var(--transition-time-medium) ease}input:hover,select:hover,textarea:hover{z-index:10;box-shadow:var(--input-hover-shadow)}input:focus,select:focus,textarea:focus{z-index:10;box-shadow:none;outline:var(--input-focus-outline)}input:disabled,select:disabled,textarea:disabled{background:var(--input-disabled-bg);color:var(--input-disabled-fg)}input:disabled:hover,select:disabled:hover,textarea:disabled:hover{z-index:10;cursor:unset}input[type=color]::-webkit-color-swatch{border:1px solid transparent;border-radius:.25em}textarea{text-align:left;padding:.5em}
`;
var nn = `*,*:before,*:after{box-sizing:border-box}:host{box-sizing:border-box;margin:0;display:flex;position:relative;width:100%;height:100%;color:var(--fg)}:host([loaded]) section.overlay,:host([loading]) section.overlay{display:none}:host main{display:contents}section.overlay{position:absolute;top:0;left:0;width:100%;height:100%;z-index:1;display:flex;flex-direction:column;align-items:center;justify-content:center;background:var(--gradient-purple-blue-dark)}section.overlay h1{display:flex;margin:0 auto;align-items:center;justify-content:center;font-size:5em;font-weight:300;text-shadow:0 0 5px var(--gradient-purple-red)}section.overlay h1 img{width:1.5em}section.overlay p{text-align:center;font-size:1.5em;max-width:50%}section.overlay strong{background:var(--gradient-purple-red-highlight);-webkit-background-clip:text;-moz-background-clip:text;background-clip:text;color:transparent}section.overlay a{color:#81eeff}section.overlay a:hover{color:#a3f3ff}section.overlay input{font-size:1.5em;color:var(--fg);background:var(--gradient-purple-red);max-width:50%}section.overlay input::placeholder{color:var(--fg)}section.overlay p.note{color:var(--input-placeholder);font-size:1em}section.overlay p.github img{width:2em}kc-board-viewer,kc-schematic-viewer{width:100%;height:100%;flex:1}.split-horizontal{display:flex;flex-direction:column;height:100%;max-height:100%;overflow:hidden}.split-vertical{display:flex;flex-direction:row;width:100%;max-width:100%;height:100%;overflow:hidden}kc-board-app,kc-schematic-app{width:100%;height:100%;flex:1}
`;
Jt.sprites_url = Ss;
var tt = class extends N {
    constructor() {
        super();
        this.project = new Wt();
        this.provideContext('project', this.project);
    }
    static {
        l(this, 'KiCanvasShellElement');
    }
    static {
        this.styles = [...N.styles, new Ne(k3), new Ne(nn)];
    }
    #e;
    #t;
    initialContentCallback() {
        let r = new URLSearchParams(document.location.search).getAll('github');
        ue(async () => {
            if (this.src) {
                let i = new st([this.src]);
                await this.setup_project(i);
                return;
            }
            if (r.length) {
                let i = await N2.fromURLs(...r);
                await this.setup_project(i);
                return;
            }
            new K2(this, async (i) => {
                await this.setup_project(i);
            });
        }),
            this.link_input.addEventListener('input', async (i) => {
                let n = this.link_input.value;
                if (!$e.parse_url(n)) return;
                let o = await N2.fromURLs(n);
                await this.setup_project(o);
                let c = new URL(window.location.href);
                c.searchParams.set('github', n), window.history.pushState(null, '', c);
            });
    }
    async setup_project(e) {
        (this.loaded = !1), (this.loading = !0);
        try {
            await this.project.load(e), this.project.set_active_page(this.project.first_page), (this.loaded = !0);
        } catch (r) {
            console.error(r);
        } finally {
            this.loading = !1;
        }
    }
    render() {
        return (
            (this.#e = _`
            <kc-schematic-app controls="full"></kc-schematic-app>
        `),
            (this.#t = _`
            <kc-board-app controls="full"></kc-board-app>
        `),
            _`
            <kc-ui-app>
                <section class="overlay">
                    <h1>
                        <img src="images/kicanvas.png" />
                        KiCanvas
                    </h1>
                    <p>
                        KiCanvas is an
                        <strong>interactive</strong>
                        ,
                        <strong>browser-based</strong>
                        viewer for KiCAD schematics and boards. You can learn
                        more from the
                        <a href="https://kicanvas.org/home" target="_blank"
                            >docs</a
                        >. It's in
                        <strong>alpha</strong>
                        so please
                        <a
                            href="https://github.com/theacodes/kicanvas/issues/new/choose"
                            target="_blank">
                            report any bugs</a
                        >!
                    </p>
                    <input
                        name="link"
                        type="text"
                        placeholder="Paste a GitHub link..."
                        autofocus />
                    <p>or drag & drop your KiCAD files</p>
                    <p class="note">
                        KiCanvas is
                        <a
                            href="https://github.com/theacodes/kicanvas"
                            target="_blank"
                            >free & open source</a
                        >
                        and supported by
                        <a
                            href="https://github.com/theacodes/kicanvas#special-thanks"
                            >community donations</a
                        >
                        with significant support from
                        <a href="https://partsbox.com/" target="_blank"
                            >PartsBox</a
                        >,
                        <a href="https://blues.io/" target="_blank">Blues</a>,
                        <a href="https://blog.mithis.net/" target="_blank"
                            >Mithro</a
                        >,
                        <a href="https://github.com/jeremysf">Jeremy Gordon</a>,
                        &
                        <a href="https://github.com/jamesneal" target="_blank"
                            >James Neal</a
                        >. KiCanvas runs entirely within your browser, so your
                        files don't ever leave your machine.
                    </p>
                    <p class="github">
                        <a
                            href="https://github.com/theacodes/kicanvas"
                            target="_blank"
                            title="Visit on GitHub">
                            <img src="images/github-mark-white.svg" />
                        </a>
                    </p>
                </section>
                <main>${this.#e} ${this.#t}</main>
            </kc-ui-app>
        `
        );
    }
};
P([L({ type: Boolean })], tt.prototype, 'loading', 2),
    P([L({ type: Boolean })], tt.prototype, 'loaded', 2),
    P([L({ type: String })], tt.prototype, 'src', 2),
    P([Q('input[name="link"]', !0)], tt.prototype, 'link_input', 2);
window.customElements.define('kc-kicanvas-shell', tt);
var _e = class extends N {
    constructor() {
        super();
        this.#e = new Wt();
        this.custom_resolver = null;
        this.provideContext('project', this.#e);
    }
    static {
        l(this, 'KiCanvasEmbedElement');
    }
    static {
        this.styles = [
            ...N.styles,
            new Ne(k3),
            T`
            :host {
                margin: 0;
                display: flex;
                position: relative;
                width: 100%;
                max-height: 100%;
                aspect-ratio: 1.414;
                background-color: aqua;
                color: var(--fg);
                font-family: "Nunito", ui-rounded, "Hiragino Maru Gothic ProN",
                    Quicksand, Comfortaa, Manjari, "Arial Rounded MT Bold",
                    Calibri, source-sans-pro, sans-serif;
                contain: layout paint;
            }

            main {
                display: contents;
            }

            kc-board-app,
            kc-schematic-app {
                width: 100%;
                height: 100%;
                flex: 1;
            }
        `,
        ];
    }
    #e;
    #t;
    #r;
    initialContentCallback() {
        this.#i(),
            ue(() => {
                this.#s();
            });
    }
    async #i() {}
    async #s() {
        let e = [];
        this.src && e.push(this.src);
        for (let i of this.querySelectorAll('kicanvas-source')) i.src && e.push(i.src);
        if (e.length == 0) {
            console.warn('No valid sources specified');
            return;
        }
        let r = new st(e, this.custom_resolver);
        await this.#n(r);
    }
    async #n(e) {
        (this.loaded = !1), (this.loading = !0);
        try {
            await this.#e.load(e),
                (this.loaded = !0),
                await this.update(),
                this.#e.set_active_page(this.#e.root_schematic_page);
        } finally {
            this.loading = !1;
        }
    }
    render() {
        if (!this.loaded) return _``;
        this.#e.has_schematics &&
            !this.#t &&
            (this.#t = _`<kc-schematic-app
                sidebarcollapsed
                controls="${this.controls}"
                controlslist="${this.controlslist}">
            </kc-schematic-app>`),
            this.#e.has_boards &&
                !this.#r &&
                (this.#r = _`<kc-board-app
                sidebarcollapsed
                controls="${this.controls}"
                controlslist="${this.controlslist}">
            </kc-board-app>`);
        let e =
            (this.controls ?? 'none') == 'none' || this.controlslist?.includes('nooverlay')
                ? null
                : _`<kc-ui-focus-overlay></kc-ui-focus-overlay>`;
        return _`<main>
            ${this.#t} ${this.#r} ${e}
        </main>`;
    }
};
P([L({ type: String })], _e.prototype, 'src', 2),
    P([L({ type: Boolean })], _e.prototype, 'loading', 2),
    P([L({ type: Boolean })], _e.prototype, 'loaded', 2),
    P([L({ type: String })], _e.prototype, 'controls', 2),
    P([L({ type: String })], _e.prototype, 'controlslist', 2),
    P([L({ type: String })], _e.prototype, 'theme', 2),
    P([L({ type: String })], _e.prototype, 'zoom', 2);
window.customElements.define('kicanvas-embed', _e);
var A3 = class extends Oe {
    constructor() {
        super();
        (this.ariaHidden = 'true'), (this.hidden = !0), (this.style.display = 'none');
    }
    static {
        l(this, 'KiCanvasSourceElement');
    }
};
P([L({ type: String })], A3.prototype, 'src', 2);
window.customElements.define('kicanvas-source', A3);
document.body.appendChild(_`<link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@48,400,0,0&family=Nunito:wght@300;400;500;600;700&display=swap"
        crossorigin="anonymous" />`);
