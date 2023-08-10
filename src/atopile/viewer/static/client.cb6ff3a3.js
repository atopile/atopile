// modules are defined as an array
// [ module function, map of requires ]
//
// map of requires is short require name -> numeric require
//
// anything defined in a previous bundle is accessed via the
// orig method which is the require for previous bundles

(function (modules, entry, mainEntry, parcelRequireName, globalName) {
  /* eslint-disable no-undef */
  var globalObject =
    typeof globalThis !== 'undefined'
      ? globalThis
      : typeof self !== 'undefined'
      ? self
      : typeof window !== 'undefined'
      ? window
      : typeof global !== 'undefined'
      ? global
      : {};
  /* eslint-enable no-undef */

  // Save the require from previous bundle to this closure if any
  var previousRequire =
    typeof globalObject[parcelRequireName] === 'function' &&
    globalObject[parcelRequireName];

  var cache = previousRequire.cache || {};
  // Do not use `require` to prevent Webpack from trying to bundle this call
  var nodeRequire =
    typeof module !== 'undefined' &&
    typeof module.require === 'function' &&
    module.require.bind(module);

  function newRequire(name, jumped) {
    if (!cache[name]) {
      if (!modules[name]) {
        // if we cannot find the module within our internal map or
        // cache jump to the current global require ie. the last bundle
        // that was added to the page.
        var currentRequire =
          typeof globalObject[parcelRequireName] === 'function' &&
          globalObject[parcelRequireName];
        if (!jumped && currentRequire) {
          return currentRequire(name, true);
        }

        // If there are other bundles on this page the require from the
        // previous one is saved to 'previousRequire'. Repeat this as
        // many times as there are bundles until the module is found or
        // we exhaust the require chain.
        if (previousRequire) {
          return previousRequire(name, true);
        }

        // Try the node require function if it exists.
        if (nodeRequire && typeof name === 'string') {
          return nodeRequire(name);
        }

        var err = new Error("Cannot find module '" + name + "'");
        err.code = 'MODULE_NOT_FOUND';
        throw err;
      }

      localRequire.resolve = resolve;
      localRequire.cache = {};

      var module = (cache[name] = new newRequire.Module(name));

      modules[name][0].call(
        module.exports,
        localRequire,
        module,
        module.exports,
        this
      );
    }

    return cache[name].exports;

    function localRequire(x) {
      var res = localRequire.resolve(x);
      return res === false ? {} : newRequire(res);
    }

    function resolve(x) {
      var id = modules[name][1][x];
      return id != null ? id : x;
    }
  }

  function Module(moduleName) {
    this.id = moduleName;
    this.bundle = newRequire;
    this.exports = {};
  }

  newRequire.isParcelRequire = true;
  newRequire.Module = Module;
  newRequire.modules = modules;
  newRequire.cache = cache;
  newRequire.parent = previousRequire;
  newRequire.register = function (id, exports) {
    modules[id] = [
      function (require, module) {
        module.exports = exports;
      },
      {},
    ];
  };

  Object.defineProperty(newRequire, 'root', {
    get: function () {
      return globalObject[parcelRequireName];
    },
  });

  globalObject[parcelRequireName] = newRequire;

  for (var i = 0; i < entry.length; i++) {
    newRequire(entry[i]);
  }

  if (mainEntry) {
    // Expose entry point to Node, AMD or browser globals
    // Based on https://github.com/ForbesLindesay/umd/blob/master/template.js
    var mainExports = newRequire(mainEntry);

    // CommonJS
    if (typeof exports === 'object' && typeof module !== 'undefined') {
      module.exports = mainExports;

      // RequireJS
    } else if (typeof define === 'function' && define.amd) {
      define(function () {
        return mainExports;
      });

      // <script>
    } else if (globalName) {
      this[globalName] = mainExports;
    }
  }
})({"jrYKc":[function(require,module,exports) {
var global = arguments[3];
var HMR_HOST = null;
var HMR_PORT = null;
var HMR_SECURE = false;
var HMR_ENV_HASH = "d6ea1d42532a7575";
module.bundle.HMR_BUNDLE_ID = "fb3d5e0dcb6ff3a3";
"use strict";
/* global HMR_HOST, HMR_PORT, HMR_ENV_HASH, HMR_SECURE, chrome, browser, __parcel__import__, __parcel__importScripts__, ServiceWorkerGlobalScope */ /*::
import type {
  HMRAsset,
  HMRMessage,
} from '@parcel/reporter-dev-server/src/HMRServer.js';
interface ParcelRequire {
  (string): mixed;
  cache: {|[string]: ParcelModule|};
  hotData: {|[string]: mixed|};
  Module: any;
  parent: ?ParcelRequire;
  isParcelRequire: true;
  modules: {|[string]: [Function, {|[string]: string|}]|};
  HMR_BUNDLE_ID: string;
  root: ParcelRequire;
}
interface ParcelModule {
  hot: {|
    data: mixed,
    accept(cb: (Function) => void): void,
    dispose(cb: (mixed) => void): void,
    // accept(deps: Array<string> | string, cb: (Function) => void): void,
    // decline(): void,
    _acceptCallbacks: Array<(Function) => void>,
    _disposeCallbacks: Array<(mixed) => void>,
  |};
}
interface ExtensionContext {
  runtime: {|
    reload(): void,
    getURL(url: string): string;
    getManifest(): {manifest_version: number, ...};
  |};
}
declare var module: {bundle: ParcelRequire, ...};
declare var HMR_HOST: string;
declare var HMR_PORT: string;
declare var HMR_ENV_HASH: string;
declare var HMR_SECURE: boolean;
declare var chrome: ExtensionContext;
declare var browser: ExtensionContext;
declare var __parcel__import__: (string) => Promise<void>;
declare var __parcel__importScripts__: (string) => Promise<void>;
declare var globalThis: typeof self;
declare var ServiceWorkerGlobalScope: Object;
*/ var OVERLAY_ID = "__parcel__error__overlay__";
var OldModule = module.bundle.Module;
function Module(moduleName) {
    OldModule.call(this, moduleName);
    this.hot = {
        data: module.bundle.hotData[moduleName],
        _acceptCallbacks: [],
        _disposeCallbacks: [],
        accept: function(fn) {
            this._acceptCallbacks.push(fn || function() {});
        },
        dispose: function(fn) {
            this._disposeCallbacks.push(fn);
        }
    };
    module.bundle.hotData[moduleName] = undefined;
}
module.bundle.Module = Module;
module.bundle.hotData = {};
var checkedAssets /*: {|[string]: boolean|} */ , assetsToDispose /*: Array<[ParcelRequire, string]> */ , assetsToAccept /*: Array<[ParcelRequire, string]> */ ;
function getHostname() {
    return HMR_HOST || (location.protocol.indexOf("http") === 0 ? location.hostname : "localhost");
}
function getPort() {
    return HMR_PORT || location.port;
}
// eslint-disable-next-line no-redeclare
var parent = module.bundle.parent;
if ((!parent || !parent.isParcelRequire) && typeof WebSocket !== "undefined") {
    var hostname = getHostname();
    var port = getPort();
    var protocol = HMR_SECURE || location.protocol == "https:" && !/localhost|127.0.0.1|0.0.0.0/.test(hostname) ? "wss" : "ws";
    var ws = new WebSocket(protocol + "://" + hostname + (port ? ":" + port : "") + "/");
    // Web extension context
    var extCtx = typeof chrome === "undefined" ? typeof browser === "undefined" ? null : browser : chrome;
    // Safari doesn't support sourceURL in error stacks.
    // eval may also be disabled via CSP, so do a quick check.
    var supportsSourceURL = false;
    try {
        (0, eval)('throw new Error("test"); //# sourceURL=test.js');
    } catch (err) {
        supportsSourceURL = err.stack.includes("test.js");
    }
    // $FlowFixMe
    ws.onmessage = async function(event /*: {data: string, ...} */ ) {
        checkedAssets = {} /*: {|[string]: boolean|} */ ;
        assetsToAccept = [];
        assetsToDispose = [];
        var data /*: HMRMessage */  = JSON.parse(event.data);
        if (data.type === "update") {
            // Remove error overlay if there is one
            if (typeof document !== "undefined") removeErrorOverlay();
            let assets = data.assets.filter((asset)=>asset.envHash === HMR_ENV_HASH);
            // Handle HMR Update
            let handled = assets.every((asset)=>{
                return asset.type === "css" || asset.type === "js" && hmrAcceptCheck(module.bundle.root, asset.id, asset.depsByBundle);
            });
            if (handled) {
                console.clear();
                // Dispatch custom event so other runtimes (e.g React Refresh) are aware.
                if (typeof window !== "undefined" && typeof CustomEvent !== "undefined") window.dispatchEvent(new CustomEvent("parcelhmraccept"));
                await hmrApplyUpdates(assets);
                // Dispose all old assets.
                let processedAssets = {} /*: {|[string]: boolean|} */ ;
                for(let i = 0; i < assetsToDispose.length; i++){
                    let id = assetsToDispose[i][1];
                    if (!processedAssets[id]) {
                        hmrDispose(assetsToDispose[i][0], id);
                        processedAssets[id] = true;
                    }
                }
                // Run accept callbacks. This will also re-execute other disposed assets in topological order.
                processedAssets = {};
                for(let i = 0; i < assetsToAccept.length; i++){
                    let id = assetsToAccept[i][1];
                    if (!processedAssets[id]) {
                        hmrAccept(assetsToAccept[i][0], id);
                        processedAssets[id] = true;
                    }
                }
            } else fullReload();
        }
        if (data.type === "error") {
            // Log parcel errors to console
            for (let ansiDiagnostic of data.diagnostics.ansi){
                let stack = ansiDiagnostic.codeframe ? ansiDiagnostic.codeframe : ansiDiagnostic.stack;
                console.error("\uD83D\uDEA8 [parcel]: " + ansiDiagnostic.message + "\n" + stack + "\n\n" + ansiDiagnostic.hints.join("\n"));
            }
            if (typeof document !== "undefined") {
                // Render the fancy html overlay
                removeErrorOverlay();
                var overlay = createErrorOverlay(data.diagnostics.html);
                // $FlowFixMe
                document.body.appendChild(overlay);
            }
        }
    };
    ws.onerror = function(e) {
        console.error(e.message);
    };
    ws.onclose = function() {
        console.warn("[parcel] \uD83D\uDEA8 Connection to the HMR server was lost");
    };
}
function removeErrorOverlay() {
    var overlay = document.getElementById(OVERLAY_ID);
    if (overlay) {
        overlay.remove();
        console.log("[parcel] ✨ Error resolved");
    }
}
function createErrorOverlay(diagnostics) {
    var overlay = document.createElement("div");
    overlay.id = OVERLAY_ID;
    let errorHTML = '<div style="background: black; opacity: 0.85; font-size: 16px; color: white; position: fixed; height: 100%; width: 100%; top: 0px; left: 0px; padding: 30px; font-family: Menlo, Consolas, monospace; z-index: 9999;">';
    for (let diagnostic of diagnostics){
        let stack = diagnostic.frames.length ? diagnostic.frames.reduce((p, frame)=>{
            return `${p}
<a href="/__parcel_launch_editor?file=${encodeURIComponent(frame.location)}" style="text-decoration: underline; color: #888" onclick="fetch(this.href); return false">${frame.location}</a>
${frame.code}`;
        }, "") : diagnostic.stack;
        errorHTML += `
      <div>
        <div style="font-size: 18px; font-weight: bold; margin-top: 20px;">
          🚨 ${diagnostic.message}
        </div>
        <pre>${stack}</pre>
        <div>
          ${diagnostic.hints.map((hint)=>"<div>\uD83D\uDCA1 " + hint + "</div>").join("")}
        </div>
        ${diagnostic.documentation ? `<div>📝 <a style="color: violet" href="${diagnostic.documentation}" target="_blank">Learn more</a></div>` : ""}
      </div>
    `;
    }
    errorHTML += "</div>";
    overlay.innerHTML = errorHTML;
    return overlay;
}
function fullReload() {
    if ("reload" in location) location.reload();
    else if (extCtx && extCtx.runtime && extCtx.runtime.reload) extCtx.runtime.reload();
}
function getParents(bundle, id) /*: Array<[ParcelRequire, string]> */ {
    var modules = bundle.modules;
    if (!modules) return [];
    var parents = [];
    var k, d, dep;
    for(k in modules)for(d in modules[k][1]){
        dep = modules[k][1][d];
        if (dep === id || Array.isArray(dep) && dep[dep.length - 1] === id) parents.push([
            bundle,
            k
        ]);
    }
    if (bundle.parent) parents = parents.concat(getParents(bundle.parent, id));
    return parents;
}
function updateLink(link) {
    var href = link.getAttribute("href");
    if (!href) return;
    var newLink = link.cloneNode();
    newLink.onload = function() {
        if (link.parentNode !== null) // $FlowFixMe
        link.parentNode.removeChild(link);
    };
    newLink.setAttribute("href", // $FlowFixMe
    href.split("?")[0] + "?" + Date.now());
    // $FlowFixMe
    link.parentNode.insertBefore(newLink, link.nextSibling);
}
var cssTimeout = null;
function reloadCSS() {
    if (cssTimeout) return;
    cssTimeout = setTimeout(function() {
        var links = document.querySelectorAll('link[rel="stylesheet"]');
        for(var i = 0; i < links.length; i++){
            // $FlowFixMe[incompatible-type]
            var href /*: string */  = links[i].getAttribute("href");
            var hostname = getHostname();
            var servedFromHMRServer = hostname === "localhost" ? new RegExp("^(https?:\\/\\/(0.0.0.0|127.0.0.1)|localhost):" + getPort()).test(href) : href.indexOf(hostname + ":" + getPort());
            var absolute = /^https?:\/\//i.test(href) && href.indexOf(location.origin) !== 0 && !servedFromHMRServer;
            if (!absolute) updateLink(links[i]);
        }
        cssTimeout = null;
    }, 50);
}
function hmrDownload(asset) {
    if (asset.type === "js") {
        if (typeof document !== "undefined") {
            let script = document.createElement("script");
            script.src = asset.url + "?t=" + Date.now();
            if (asset.outputFormat === "esmodule") script.type = "module";
            return new Promise((resolve, reject)=>{
                var _document$head;
                script.onload = ()=>resolve(script);
                script.onerror = reject;
                (_document$head = document.head) === null || _document$head === void 0 || _document$head.appendChild(script);
            });
        } else if (typeof importScripts === "function") {
            // Worker scripts
            if (asset.outputFormat === "esmodule") return import(asset.url + "?t=" + Date.now());
            else return new Promise((resolve, reject)=>{
                try {
                    importScripts(asset.url + "?t=" + Date.now());
                    resolve();
                } catch (err) {
                    reject(err);
                }
            });
        }
    }
}
async function hmrApplyUpdates(assets) {
    global.parcelHotUpdate = Object.create(null);
    let scriptsToRemove;
    try {
        // If sourceURL comments aren't supported in eval, we need to load
        // the update from the dev server over HTTP so that stack traces
        // are correct in errors/logs. This is much slower than eval, so
        // we only do it if needed (currently just Safari).
        // https://bugs.webkit.org/show_bug.cgi?id=137297
        // This path is also taken if a CSP disallows eval.
        if (!supportsSourceURL) {
            let promises = assets.map((asset)=>{
                var _hmrDownload;
                return (_hmrDownload = hmrDownload(asset)) === null || _hmrDownload === void 0 ? void 0 : _hmrDownload.catch((err)=>{
                    // Web extension bugfix for Chromium
                    // https://bugs.chromium.org/p/chromium/issues/detail?id=1255412#c12
                    if (extCtx && extCtx.runtime && extCtx.runtime.getManifest().manifest_version == 3) {
                        if (typeof ServiceWorkerGlobalScope != "undefined" && global instanceof ServiceWorkerGlobalScope) {
                            extCtx.runtime.reload();
                            return;
                        }
                        asset.url = extCtx.runtime.getURL("/__parcel_hmr_proxy__?url=" + encodeURIComponent(asset.url + "?t=" + Date.now()));
                        return hmrDownload(asset);
                    }
                    throw err;
                });
            });
            scriptsToRemove = await Promise.all(promises);
        }
        assets.forEach(function(asset) {
            hmrApply(module.bundle.root, asset);
        });
    } finally{
        delete global.parcelHotUpdate;
        if (scriptsToRemove) scriptsToRemove.forEach((script)=>{
            if (script) {
                var _document$head2;
                (_document$head2 = document.head) === null || _document$head2 === void 0 || _document$head2.removeChild(script);
            }
        });
    }
}
function hmrApply(bundle /*: ParcelRequire */ , asset /*:  HMRAsset */ ) {
    var modules = bundle.modules;
    if (!modules) return;
    if (asset.type === "css") reloadCSS();
    else if (asset.type === "js") {
        let deps = asset.depsByBundle[bundle.HMR_BUNDLE_ID];
        if (deps) {
            if (modules[asset.id]) {
                // Remove dependencies that are removed and will become orphaned.
                // This is necessary so that if the asset is added back again, the cache is gone, and we prevent a full page reload.
                let oldDeps = modules[asset.id][1];
                for(let dep in oldDeps)if (!deps[dep] || deps[dep] !== oldDeps[dep]) {
                    let id = oldDeps[dep];
                    let parents = getParents(module.bundle.root, id);
                    if (parents.length === 1) hmrDelete(module.bundle.root, id);
                }
            }
            if (supportsSourceURL) // Global eval. We would use `new Function` here but browser
            // support for source maps is better with eval.
            (0, eval)(asset.output);
            // $FlowFixMe
            let fn = global.parcelHotUpdate[asset.id];
            modules[asset.id] = [
                fn,
                deps
            ];
        } else if (bundle.parent) hmrApply(bundle.parent, asset);
    }
}
function hmrDelete(bundle, id) {
    let modules = bundle.modules;
    if (!modules) return;
    if (modules[id]) {
        // Collect dependencies that will become orphaned when this module is deleted.
        let deps = modules[id][1];
        let orphans = [];
        for(let dep in deps){
            let parents = getParents(module.bundle.root, deps[dep]);
            if (parents.length === 1) orphans.push(deps[dep]);
        }
        // Delete the module. This must be done before deleting dependencies in case of circular dependencies.
        delete modules[id];
        delete bundle.cache[id];
        // Now delete the orphans.
        orphans.forEach((id)=>{
            hmrDelete(module.bundle.root, id);
        });
    } else if (bundle.parent) hmrDelete(bundle.parent, id);
}
function hmrAcceptCheck(bundle /*: ParcelRequire */ , id /*: string */ , depsByBundle /*: ?{ [string]: { [string]: string } }*/ ) {
    if (hmrAcceptCheckOne(bundle, id, depsByBundle)) return true;
    // Traverse parents breadth first. All possible ancestries must accept the HMR update, or we'll reload.
    let parents = getParents(module.bundle.root, id);
    let accepted = false;
    while(parents.length > 0){
        let v = parents.shift();
        let a = hmrAcceptCheckOne(v[0], v[1], null);
        if (a) // If this parent accepts, stop traversing upward, but still consider siblings.
        accepted = true;
        else {
            // Otherwise, queue the parents in the next level upward.
            let p = getParents(module.bundle.root, v[1]);
            if (p.length === 0) {
                // If there are no parents, then we've reached an entry without accepting. Reload.
                accepted = false;
                break;
            }
            parents.push(...p);
        }
    }
    return accepted;
}
function hmrAcceptCheckOne(bundle /*: ParcelRequire */ , id /*: string */ , depsByBundle /*: ?{ [string]: { [string]: string } }*/ ) {
    var modules = bundle.modules;
    if (!modules) return;
    if (depsByBundle && !depsByBundle[bundle.HMR_BUNDLE_ID]) {
        // If we reached the root bundle without finding where the asset should go,
        // there's nothing to do. Mark as "accepted" so we don't reload the page.
        if (!bundle.parent) return true;
        return hmrAcceptCheck(bundle.parent, id, depsByBundle);
    }
    if (checkedAssets[id]) return true;
    checkedAssets[id] = true;
    var cached = bundle.cache[id];
    assetsToDispose.push([
        bundle,
        id
    ]);
    if (!cached || cached.hot && cached.hot._acceptCallbacks.length) {
        assetsToAccept.push([
            bundle,
            id
        ]);
        return true;
    }
}
function hmrDispose(bundle /*: ParcelRequire */ , id /*: string */ ) {
    var cached = bundle.cache[id];
    bundle.hotData[id] = {};
    if (cached && cached.hot) cached.hot.data = bundle.hotData[id];
    if (cached && cached.hot && cached.hot._disposeCallbacks.length) cached.hot._disposeCallbacks.forEach(function(cb) {
        cb(bundle.hotData[id]);
    });
    delete bundle.cache[id];
}
function hmrAccept(bundle /*: ParcelRequire */ , id /*: string */ ) {
    // Execute the module.
    bundle(id);
    // Run the accept callbacks in the new version of the module.
    var cached = bundle.cache[id];
    if (cached && cached.hot && cached.hot._acceptCallbacks.length) cached.hot._acceptCallbacks.forEach(function(cb) {
        var assetsToAlsoAccept = cb(function() {
            return getParents(module.bundle.root, id);
        });
        if (assetsToAlsoAccept && assetsToAccept.length) {
            assetsToAlsoAccept.forEach(function(a) {
                hmrDispose(a[0], a[1]);
            });
            // $FlowFixMe[method-unbinding]
            assetsToAccept.push.apply(assetsToAccept, assetsToAlsoAccept);
        }
    });
}

},{}],"6BMq4":[function(require,module,exports) {
var global = arguments[3];
//     Backbone.js 1.5.0
//     (c) 2010-2022 Jeremy Ashkenas and DocumentCloud
//     Backbone may be freely distributed under the MIT license.
//     For all details and documentation:
//     http://backbonejs.org
(function(factory) {
    // Establish the root object, `window` (`self`) in the browser, or `global` on the server.
    // We use `self` instead of `window` for `WebWorker` support.
    var root = typeof self == "object" && self.self === self && self || typeof global == "object" && global.global === global && global;
    // Set up Backbone appropriately for the environment. Start with AMD.
    if (typeof define === "function" && define.amd) define([
        "underscore",
        "jquery",
        "exports"
    ], function(_, $, exports1) {
        // Export global even in AMD case in case this script is loaded with
        // others that may still expect a global Backbone.
        root.Backbone = factory(root, exports1, _, $);
    });
    else {
        var _ = require("e151143268b413f3"), $;
        try {
            $ = require("404841aae61b7dc0");
        } catch (e) {}
        factory(root, exports, _, $);
    }
})(function(root, Backbone, _, $) {
    // Initial Setup
    // -------------
    // Save the previous value of the `Backbone` variable, so that it can be
    // restored later on, if `noConflict` is used.
    var previousBackbone = root.Backbone;
    // Create a local reference to a common array method we'll want to use later.
    var slice = Array.prototype.slice;
    // Current version of the library. Keep in sync with `package.json`.
    Backbone.VERSION = "1.5.0";
    // For Backbone's purposes, jQuery, Zepto, Ender, or My Library (kidding) owns
    // the `$` variable.
    Backbone.$ = $;
    // Runs Backbone.js in *noConflict* mode, returning the `Backbone` variable
    // to its previous owner. Returns a reference to this Backbone object.
    Backbone.noConflict = function() {
        root.Backbone = previousBackbone;
        return this;
    };
    // Turn on `emulateHTTP` to support legacy HTTP servers. Setting this option
    // will fake `"PATCH"`, `"PUT"` and `"DELETE"` requests via the `_method` parameter and
    // set a `X-Http-Method-Override` header.
    Backbone.emulateHTTP = false;
    // Turn on `emulateJSON` to support legacy servers that can't deal with direct
    // `application/json` requests ... this will encode the body as
    // `application/x-www-form-urlencoded` instead and will send the model in a
    // form param named `model`.
    Backbone.emulateJSON = false;
    // Backbone.Events
    // ---------------
    // A module that can be mixed in to *any object* in order to provide it with
    // a custom event channel. You may bind a callback to an event with `on` or
    // remove with `off`; `trigger`-ing an event fires all callbacks in
    // succession.
    //
    //     var object = {};
    //     _.extend(object, Backbone.Events);
    //     object.on('expand', function(){ alert('expanded'); });
    //     object.trigger('expand');
    //
    var Events = Backbone.Events = {};
    // Regular expression used to split event strings.
    var eventSplitter = /\s+/;
    // A private global variable to share between listeners and listenees.
    var _listening;
    // Iterates over the standard `event, callback` (as well as the fancy multiple
    // space-separated events `"change blur", callback` and jQuery-style event
    // maps `{event: callback}`).
    var eventsApi = function(iteratee, events, name, callback, opts) {
        var i = 0, names;
        if (name && typeof name === "object") {
            // Handle event maps.
            if (callback !== void 0 && "context" in opts && opts.context === void 0) opts.context = callback;
            for(names = _.keys(name); i < names.length; i++)events = eventsApi(iteratee, events, names[i], name[names[i]], opts);
        } else if (name && eventSplitter.test(name)) // Handle space-separated event names by delegating them individually.
        for(names = name.split(eventSplitter); i < names.length; i++)events = iteratee(events, names[i], callback, opts);
        else // Finally, standard events.
        events = iteratee(events, name, callback, opts);
        return events;
    };
    // Bind an event to a `callback` function. Passing `"all"` will bind
    // the callback to all events fired.
    Events.on = function(name, callback, context) {
        this._events = eventsApi(onApi, this._events || {}, name, callback, {
            context: context,
            ctx: this,
            listening: _listening
        });
        if (_listening) {
            var listeners = this._listeners || (this._listeners = {});
            listeners[_listening.id] = _listening;
            // Allow the listening to use a counter, instead of tracking
            // callbacks for library interop
            _listening.interop = false;
        }
        return this;
    };
    // Inversion-of-control versions of `on`. Tell *this* object to listen to
    // an event in another object... keeping track of what it's listening to
    // for easier unbinding later.
    Events.listenTo = function(obj, name, callback) {
        if (!obj) return this;
        var id = obj._listenId || (obj._listenId = _.uniqueId("l"));
        var listeningTo = this._listeningTo || (this._listeningTo = {});
        var listening = _listening = listeningTo[id];
        // This object is not listening to any other events on `obj` yet.
        // Setup the necessary references to track the listening callbacks.
        if (!listening) {
            this._listenId || (this._listenId = _.uniqueId("l"));
            listening = _listening = listeningTo[id] = new Listening(this, obj);
        }
        // Bind callbacks on obj.
        var error = tryCatchOn(obj, name, callback, this);
        _listening = void 0;
        if (error) throw error;
        // If the target obj is not Backbone.Events, track events manually.
        if (listening.interop) listening.on(name, callback);
        return this;
    };
    // The reducing API that adds a callback to the `events` object.
    var onApi = function(events, name, callback, options) {
        if (callback) {
            var handlers = events[name] || (events[name] = []);
            var context = options.context, ctx = options.ctx, listening = options.listening;
            if (listening) listening.count++;
            handlers.push({
                callback: callback,
                context: context,
                ctx: context || ctx,
                listening: listening
            });
        }
        return events;
    };
    // An try-catch guarded #on function, to prevent poisoning the global
    // `_listening` variable.
    var tryCatchOn = function(obj, name, callback, context) {
        try {
            obj.on(name, callback, context);
        } catch (e) {
            return e;
        }
    };
    // Remove one or many callbacks. If `context` is null, removes all
    // callbacks with that function. If `callback` is null, removes all
    // callbacks for the event. If `name` is null, removes all bound
    // callbacks for all events.
    Events.off = function(name, callback, context) {
        if (!this._events) return this;
        this._events = eventsApi(offApi, this._events, name, callback, {
            context: context,
            listeners: this._listeners
        });
        return this;
    };
    // Tell this object to stop listening to either specific events ... or
    // to every object it's currently listening to.
    Events.stopListening = function(obj, name, callback) {
        var listeningTo = this._listeningTo;
        if (!listeningTo) return this;
        var ids = obj ? [
            obj._listenId
        ] : _.keys(listeningTo);
        for(var i = 0; i < ids.length; i++){
            var listening = listeningTo[ids[i]];
            // If listening doesn't exist, this object is not currently
            // listening to obj. Break out early.
            if (!listening) break;
            listening.obj.off(name, callback, this);
            if (listening.interop) listening.off(name, callback);
        }
        if (_.isEmpty(listeningTo)) this._listeningTo = void 0;
        return this;
    };
    // The reducing API that removes a callback from the `events` object.
    var offApi = function(events, name, callback, options) {
        if (!events) return;
        var context = options.context, listeners = options.listeners;
        var i = 0, names;
        // Delete all event listeners and "drop" events.
        if (!name && !context && !callback) {
            for(names = _.keys(listeners); i < names.length; i++)listeners[names[i]].cleanup();
            return;
        }
        names = name ? [
            name
        ] : _.keys(events);
        for(; i < names.length; i++){
            name = names[i];
            var handlers = events[name];
            // Bail out if there are no events stored.
            if (!handlers) break;
            // Find any remaining events.
            var remaining = [];
            for(var j = 0; j < handlers.length; j++){
                var handler = handlers[j];
                if (callback && callback !== handler.callback && callback !== handler.callback._callback || context && context !== handler.context) remaining.push(handler);
                else {
                    var listening = handler.listening;
                    if (listening) listening.off(name, callback);
                }
            }
            // Replace events if there are any remaining.  Otherwise, clean up.
            if (remaining.length) events[name] = remaining;
            else delete events[name];
        }
        return events;
    };
    // Bind an event to only be triggered a single time. After the first time
    // the callback is invoked, its listener will be removed. If multiple events
    // are passed in using the space-separated syntax, the handler will fire
    // once for each event, not once for a combination of all events.
    Events.once = function(name, callback, context) {
        // Map the event into a `{event: once}` object.
        var events = eventsApi(onceMap, {}, name, callback, this.off.bind(this));
        if (typeof name === "string" && context == null) callback = void 0;
        return this.on(events, callback, context);
    };
    // Inversion-of-control versions of `once`.
    Events.listenToOnce = function(obj, name, callback) {
        // Map the event into a `{event: once}` object.
        var events = eventsApi(onceMap, {}, name, callback, this.stopListening.bind(this, obj));
        return this.listenTo(obj, events);
    };
    // Reduces the event callbacks into a map of `{event: onceWrapper}`.
    // `offer` unbinds the `onceWrapper` after it has been called.
    var onceMap = function(map, name, callback, offer) {
        if (callback) {
            var once = map[name] = _.once(function() {
                offer(name, once);
                callback.apply(this, arguments);
            });
            once._callback = callback;
        }
        return map;
    };
    // Trigger one or many events, firing all bound callbacks. Callbacks are
    // passed the same arguments as `trigger` is, apart from the event name
    // (unless you're listening on `"all"`, which will cause your callback to
    // receive the true name of the event as the first argument).
    Events.trigger = function(name) {
        if (!this._events) return this;
        var length = Math.max(0, arguments.length - 1);
        var args = Array(length);
        for(var i = 0; i < length; i++)args[i] = arguments[i + 1];
        eventsApi(triggerApi, this._events, name, void 0, args);
        return this;
    };
    // Handles triggering the appropriate event callbacks.
    var triggerApi = function(objEvents, name, callback, args) {
        if (objEvents) {
            var events = objEvents[name];
            var allEvents = objEvents.all;
            if (events && allEvents) allEvents = allEvents.slice();
            if (events) triggerEvents(events, args);
            if (allEvents) triggerEvents(allEvents, [
                name
            ].concat(args));
        }
        return objEvents;
    };
    // A difficult-to-believe, but optimized internal dispatch function for
    // triggering events. Tries to keep the usual cases speedy (most internal
    // Backbone events have 3 arguments).
    var triggerEvents = function(events, args) {
        var ev, i = -1, l = events.length, a1 = args[0], a2 = args[1], a3 = args[2];
        switch(args.length){
            case 0:
                while(++i < l)(ev = events[i]).callback.call(ev.ctx);
                return;
            case 1:
                while(++i < l)(ev = events[i]).callback.call(ev.ctx, a1);
                return;
            case 2:
                while(++i < l)(ev = events[i]).callback.call(ev.ctx, a1, a2);
                return;
            case 3:
                while(++i < l)(ev = events[i]).callback.call(ev.ctx, a1, a2, a3);
                return;
            default:
                while(++i < l)(ev = events[i]).callback.apply(ev.ctx, args);
                return;
        }
    };
    // A listening class that tracks and cleans up memory bindings
    // when all callbacks have been offed.
    var Listening = function(listener, obj) {
        this.id = listener._listenId;
        this.listener = listener;
        this.obj = obj;
        this.interop = true;
        this.count = 0;
        this._events = void 0;
    };
    Listening.prototype.on = Events.on;
    // Offs a callback (or several).
    // Uses an optimized counter if the listenee uses Backbone.Events.
    // Otherwise, falls back to manual tracking to support events
    // library interop.
    Listening.prototype.off = function(name, callback) {
        var cleanup;
        if (this.interop) {
            this._events = eventsApi(offApi, this._events, name, callback, {
                context: void 0,
                listeners: void 0
            });
            cleanup = !this._events;
        } else {
            this.count--;
            cleanup = this.count === 0;
        }
        if (cleanup) this.cleanup();
    };
    // Cleans up memory bindings between the listener and the listenee.
    Listening.prototype.cleanup = function() {
        delete this.listener._listeningTo[this.obj._listenId];
        if (!this.interop) delete this.obj._listeners[this.id];
    };
    // Aliases for backwards compatibility.
    Events.bind = Events.on;
    Events.unbind = Events.off;
    // Allow the `Backbone` object to serve as a global event bus, for folks who
    // want global "pubsub" in a convenient place.
    _.extend(Backbone, Events);
    // Backbone.Model
    // --------------
    // Backbone **Models** are the basic data object in the framework --
    // frequently representing a row in a table in a database on your server.
    // A discrete chunk of data and a bunch of useful, related methods for
    // performing computations and transformations on that data.
    // Create a new model with the specified attributes. A client id (`cid`)
    // is automatically generated and assigned for you.
    var Model = Backbone.Model = function(attributes, options) {
        var attrs = attributes || {};
        options || (options = {});
        this.preinitialize.apply(this, arguments);
        this.cid = _.uniqueId(this.cidPrefix);
        this.attributes = {};
        if (options.collection) this.collection = options.collection;
        if (options.parse) attrs = this.parse(attrs, options) || {};
        var defaults = _.result(this, "defaults");
        // Just _.defaults would work fine, but the additional _.extends
        // is in there for historical reasons. See #3843.
        attrs = _.defaults(_.extend({}, defaults, attrs), defaults);
        this.set(attrs, options);
        this.changed = {};
        this.initialize.apply(this, arguments);
    };
    // Attach all inheritable methods to the Model prototype.
    _.extend(Model.prototype, Events, {
        // A hash of attributes whose current and previous value differ.
        changed: null,
        // The value returned during the last failed validation.
        validationError: null,
        // The default name for the JSON `id` attribute is `"id"`. MongoDB and
        // CouchDB users may want to set this to `"_id"`.
        idAttribute: "id",
        // The prefix is used to create the client id which is used to identify models locally.
        // You may want to override this if you're experiencing name clashes with model ids.
        cidPrefix: "c",
        // preinitialize is an empty function by default. You can override it with a function
        // or object.  preinitialize will run before any instantiation logic is run in the Model.
        preinitialize: function() {},
        // Initialize is an empty function by default. Override it with your own
        // initialization logic.
        initialize: function() {},
        // Return a copy of the model's `attributes` object.
        toJSON: function(options) {
            return _.clone(this.attributes);
        },
        // Proxy `Backbone.sync` by default -- but override this if you need
        // custom syncing semantics for *this* particular model.
        sync: function() {
            return Backbone.sync.apply(this, arguments);
        },
        // Get the value of an attribute.
        get: function(attr) {
            return this.attributes[attr];
        },
        // Get the HTML-escaped value of an attribute.
        escape: function(attr) {
            return _.escape(this.get(attr));
        },
        // Returns `true` if the attribute contains a value that is not null
        // or undefined.
        has: function(attr) {
            return this.get(attr) != null;
        },
        // Special-cased proxy to underscore's `_.matches` method.
        matches: function(attrs) {
            return !!_.iteratee(attrs, this)(this.attributes);
        },
        // Set a hash of model attributes on the object, firing `"change"`. This is
        // the core primitive operation of a model, updating the data and notifying
        // anyone who needs to know about the change in state. The heart of the beast.
        set: function(key, val, options) {
            if (key == null) return this;
            // Handle both `"key", value` and `{key: value}` -style arguments.
            var attrs;
            if (typeof key === "object") {
                attrs = key;
                options = val;
            } else (attrs = {})[key] = val;
            options || (options = {});
            // Run validation.
            if (!this._validate(attrs, options)) return false;
            // Extract attributes and options.
            var unset = options.unset;
            var silent = options.silent;
            var changes = [];
            var changing = this._changing;
            this._changing = true;
            if (!changing) {
                this._previousAttributes = _.clone(this.attributes);
                this.changed = {};
            }
            var current = this.attributes;
            var changed = this.changed;
            var prev = this._previousAttributes;
            // For each `set` attribute, update or delete the current value.
            for(var attr in attrs){
                val = attrs[attr];
                if (!_.isEqual(current[attr], val)) changes.push(attr);
                if (!_.isEqual(prev[attr], val)) changed[attr] = val;
                else delete changed[attr];
                unset ? delete current[attr] : current[attr] = val;
            }
            // Update the `id`.
            if (this.idAttribute in attrs) {
                var prevId = this.id;
                this.id = this.get(this.idAttribute);
                this.trigger("changeId", this, prevId, options);
            }
            // Trigger all relevant attribute changes.
            if (!silent) {
                if (changes.length) this._pending = options;
                for(var i = 0; i < changes.length; i++)this.trigger("change:" + changes[i], this, current[changes[i]], options);
            }
            // You might be wondering why there's a `while` loop here. Changes can
            // be recursively nested within `"change"` events.
            if (changing) return this;
            if (!silent) while(this._pending){
                options = this._pending;
                this._pending = false;
                this.trigger("change", this, options);
            }
            this._pending = false;
            this._changing = false;
            return this;
        },
        // Remove an attribute from the model, firing `"change"`. `unset` is a noop
        // if the attribute doesn't exist.
        unset: function(attr, options) {
            return this.set(attr, void 0, _.extend({}, options, {
                unset: true
            }));
        },
        // Clear all attributes on the model, firing `"change"`.
        clear: function(options) {
            var attrs = {};
            for(var key in this.attributes)attrs[key] = void 0;
            return this.set(attrs, _.extend({}, options, {
                unset: true
            }));
        },
        // Determine if the model has changed since the last `"change"` event.
        // If you specify an attribute name, determine if that attribute has changed.
        hasChanged: function(attr) {
            if (attr == null) return !_.isEmpty(this.changed);
            return _.has(this.changed, attr);
        },
        // Return an object containing all the attributes that have changed, or
        // false if there are no changed attributes. Useful for determining what
        // parts of a view need to be updated and/or what attributes need to be
        // persisted to the server. Unset attributes will be set to undefined.
        // You can also pass an attributes object to diff against the model,
        // determining if there *would be* a change.
        changedAttributes: function(diff) {
            if (!diff) return this.hasChanged() ? _.clone(this.changed) : false;
            var old = this._changing ? this._previousAttributes : this.attributes;
            var changed = {};
            var hasChanged;
            for(var attr in diff){
                var val = diff[attr];
                if (_.isEqual(old[attr], val)) continue;
                changed[attr] = val;
                hasChanged = true;
            }
            return hasChanged ? changed : false;
        },
        // Get the previous value of an attribute, recorded at the time the last
        // `"change"` event was fired.
        previous: function(attr) {
            if (attr == null || !this._previousAttributes) return null;
            return this._previousAttributes[attr];
        },
        // Get all of the attributes of the model at the time of the previous
        // `"change"` event.
        previousAttributes: function() {
            return _.clone(this._previousAttributes);
        },
        // Fetch the model from the server, merging the response with the model's
        // local attributes. Any changed attributes will trigger a "change" event.
        fetch: function(options) {
            options = _.extend({
                parse: true
            }, options);
            var model = this;
            var success = options.success;
            options.success = function(resp) {
                var serverAttrs = options.parse ? model.parse(resp, options) : resp;
                if (!model.set(serverAttrs, options)) return false;
                if (success) success.call(options.context, model, resp, options);
                model.trigger("sync", model, resp, options);
            };
            wrapError(this, options);
            return this.sync("read", this, options);
        },
        // Set a hash of model attributes, and sync the model to the server.
        // If the server returns an attributes hash that differs, the model's
        // state will be `set` again.
        save: function(key, val, options) {
            // Handle both `"key", value` and `{key: value}` -style arguments.
            var attrs;
            if (key == null || typeof key === "object") {
                attrs = key;
                options = val;
            } else (attrs = {})[key] = val;
            options = _.extend({
                validate: true,
                parse: true
            }, options);
            var wait = options.wait;
            // If we're not waiting and attributes exist, save acts as
            // `set(attr).save(null, opts)` with validation. Otherwise, check if
            // the model will be valid when the attributes, if any, are set.
            if (attrs && !wait) {
                if (!this.set(attrs, options)) return false;
            } else if (!this._validate(attrs, options)) return false;
            // After a successful server-side save, the client is (optionally)
            // updated with the server-side state.
            var model = this;
            var success = options.success;
            var attributes = this.attributes;
            options.success = function(resp) {
                // Ensure attributes are restored during synchronous saves.
                model.attributes = attributes;
                var serverAttrs = options.parse ? model.parse(resp, options) : resp;
                if (wait) serverAttrs = _.extend({}, attrs, serverAttrs);
                if (serverAttrs && !model.set(serverAttrs, options)) return false;
                if (success) success.call(options.context, model, resp, options);
                model.trigger("sync", model, resp, options);
            };
            wrapError(this, options);
            // Set temporary attributes if `{wait: true}` to properly find new ids.
            if (attrs && wait) this.attributes = _.extend({}, attributes, attrs);
            var method = this.isNew() ? "create" : options.patch ? "patch" : "update";
            if (method === "patch" && !options.attrs) options.attrs = attrs;
            var xhr = this.sync(method, this, options);
            // Restore attributes.
            this.attributes = attributes;
            return xhr;
        },
        // Destroy this model on the server if it was already persisted.
        // Optimistically removes the model from its collection, if it has one.
        // If `wait: true` is passed, waits for the server to respond before removal.
        destroy: function(options) {
            options = options ? _.clone(options) : {};
            var model = this;
            var success = options.success;
            var wait = options.wait;
            var destroy = function() {
                model.stopListening();
                model.trigger("destroy", model, model.collection, options);
            };
            options.success = function(resp) {
                if (wait) destroy();
                if (success) success.call(options.context, model, resp, options);
                if (!model.isNew()) model.trigger("sync", model, resp, options);
            };
            var xhr = false;
            if (this.isNew()) _.defer(options.success);
            else {
                wrapError(this, options);
                xhr = this.sync("delete", this, options);
            }
            if (!wait) destroy();
            return xhr;
        },
        // Default URL for the model's representation on the server -- if you're
        // using Backbone's restful methods, override this to change the endpoint
        // that will be called.
        url: function() {
            var base = _.result(this, "urlRoot") || _.result(this.collection, "url") || urlError();
            if (this.isNew()) return base;
            var id = this.get(this.idAttribute);
            return base.replace(/[^\/]$/, "$&/") + encodeURIComponent(id);
        },
        // **parse** converts a response into the hash of attributes to be `set` on
        // the model. The default implementation is just to pass the response along.
        parse: function(resp, options) {
            return resp;
        },
        // Create a new model with identical attributes to this one.
        clone: function() {
            return new this.constructor(this.attributes);
        },
        // A model is new if it has never been saved to the server, and lacks an id.
        isNew: function() {
            return !this.has(this.idAttribute);
        },
        // Check if the model is currently in a valid state.
        isValid: function(options) {
            return this._validate({}, _.extend({}, options, {
                validate: true
            }));
        },
        // Run validation against the next complete set of model attributes,
        // returning `true` if all is well. Otherwise, fire an `"invalid"` event.
        _validate: function(attrs, options) {
            if (!options.validate || !this.validate) return true;
            attrs = _.extend({}, this.attributes, attrs);
            var error = this.validationError = this.validate(attrs, options) || null;
            if (!error) return true;
            this.trigger("invalid", this, error, _.extend(options, {
                validationError: error
            }));
            return false;
        }
    });
    // Backbone.Collection
    // -------------------
    // If models tend to represent a single row of data, a Backbone Collection is
    // more analogous to a table full of data ... or a small slice or page of that
    // table, or a collection of rows that belong together for a particular reason
    // -- all of the messages in this particular folder, all of the documents
    // belonging to this particular author, and so on. Collections maintain
    // indexes of their models, both in order, and for lookup by `id`.
    // Create a new **Collection**, perhaps to contain a specific type of `model`.
    // If a `comparator` is specified, the Collection will maintain
    // its models in sort order, as they're added and removed.
    var Collection = Backbone.Collection = function(models, options) {
        options || (options = {});
        this.preinitialize.apply(this, arguments);
        if (options.model) this.model = options.model;
        if (options.comparator !== void 0) this.comparator = options.comparator;
        this._reset();
        this.initialize.apply(this, arguments);
        if (models) this.reset(models, _.extend({
            silent: true
        }, options));
    };
    // Default options for `Collection#set`.
    var setOptions = {
        add: true,
        remove: true,
        merge: true
    };
    var addOptions = {
        add: true,
        remove: false
    };
    // Splices `insert` into `array` at index `at`.
    var splice = function(array, insert, at) {
        at = Math.min(Math.max(at, 0), array.length);
        var tail = Array(array.length - at);
        var length = insert.length;
        var i;
        for(i = 0; i < tail.length; i++)tail[i] = array[i + at];
        for(i = 0; i < length; i++)array[i + at] = insert[i];
        for(i = 0; i < tail.length; i++)array[i + length + at] = tail[i];
    };
    // Define the Collection's inheritable methods.
    _.extend(Collection.prototype, Events, {
        // The default model for a collection is just a **Backbone.Model**.
        // This should be overridden in most cases.
        model: Model,
        // preinitialize is an empty function by default. You can override it with a function
        // or object.  preinitialize will run before any instantiation logic is run in the Collection.
        preinitialize: function() {},
        // Initialize is an empty function by default. Override it with your own
        // initialization logic.
        initialize: function() {},
        // The JSON representation of a Collection is an array of the
        // models' attributes.
        toJSON: function(options) {
            return this.map(function(model) {
                return model.toJSON(options);
            });
        },
        // Proxy `Backbone.sync` by default.
        sync: function() {
            return Backbone.sync.apply(this, arguments);
        },
        // Add a model, or list of models to the set. `models` may be Backbone
        // Models or raw JavaScript objects to be converted to Models, or any
        // combination of the two.
        add: function(models, options) {
            return this.set(models, _.extend({
                merge: false
            }, options, addOptions));
        },
        // Remove a model, or a list of models from the set.
        remove: function(models, options) {
            options = _.extend({}, options);
            var singular = !_.isArray(models);
            models = singular ? [
                models
            ] : models.slice();
            var removed = this._removeModels(models, options);
            if (!options.silent && removed.length) {
                options.changes = {
                    added: [],
                    merged: [],
                    removed: removed
                };
                this.trigger("update", this, options);
            }
            return singular ? removed[0] : removed;
        },
        // Update a collection by `set`-ing a new list of models, adding new ones,
        // removing models that are no longer present, and merging models that
        // already exist in the collection, as necessary. Similar to **Model#set**,
        // the core operation for updating the data contained by the collection.
        set: function(models, options) {
            if (models == null) return;
            options = _.extend({}, setOptions, options);
            if (options.parse && !this._isModel(models)) models = this.parse(models, options) || [];
            var singular = !_.isArray(models);
            models = singular ? [
                models
            ] : models.slice();
            var at = options.at;
            if (at != null) at = +at;
            if (at > this.length) at = this.length;
            if (at < 0) at += this.length + 1;
            var set = [];
            var toAdd = [];
            var toMerge = [];
            var toRemove = [];
            var modelMap = {};
            var add = options.add;
            var merge = options.merge;
            var remove = options.remove;
            var sort = false;
            var sortable = this.comparator && at == null && options.sort !== false;
            var sortAttr = _.isString(this.comparator) ? this.comparator : null;
            // Turn bare objects into model references, and prevent invalid models
            // from being added.
            var model, i;
            for(i = 0; i < models.length; i++){
                model = models[i];
                // If a duplicate is found, prevent it from being added and
                // optionally merge it into the existing model.
                var existing = this.get(model);
                if (existing) {
                    if (merge && model !== existing) {
                        var attrs = this._isModel(model) ? model.attributes : model;
                        if (options.parse) attrs = existing.parse(attrs, options);
                        existing.set(attrs, options);
                        toMerge.push(existing);
                        if (sortable && !sort) sort = existing.hasChanged(sortAttr);
                    }
                    if (!modelMap[existing.cid]) {
                        modelMap[existing.cid] = true;
                        set.push(existing);
                    }
                    models[i] = existing;
                // If this is a new, valid model, push it to the `toAdd` list.
                } else if (add) {
                    model = models[i] = this._prepareModel(model, options);
                    if (model) {
                        toAdd.push(model);
                        this._addReference(model, options);
                        modelMap[model.cid] = true;
                        set.push(model);
                    }
                }
            }
            // Remove stale models.
            if (remove) {
                for(i = 0; i < this.length; i++){
                    model = this.models[i];
                    if (!modelMap[model.cid]) toRemove.push(model);
                }
                if (toRemove.length) this._removeModels(toRemove, options);
            }
            // See if sorting is needed, update `length` and splice in new models.
            var orderChanged = false;
            var replace = !sortable && add && remove;
            if (set.length && replace) {
                orderChanged = this.length !== set.length || _.some(this.models, function(m, index) {
                    return m !== set[index];
                });
                this.models.length = 0;
                splice(this.models, set, 0);
                this.length = this.models.length;
            } else if (toAdd.length) {
                if (sortable) sort = true;
                splice(this.models, toAdd, at == null ? this.length : at);
                this.length = this.models.length;
            }
            // Silently sort the collection if appropriate.
            if (sort) this.sort({
                silent: true
            });
            // Unless silenced, it's time to fire all appropriate add/sort/update events.
            if (!options.silent) {
                for(i = 0; i < toAdd.length; i++){
                    if (at != null) options.index = at + i;
                    model = toAdd[i];
                    model.trigger("add", model, this, options);
                }
                if (sort || orderChanged) this.trigger("sort", this, options);
                if (toAdd.length || toRemove.length || toMerge.length) {
                    options.changes = {
                        added: toAdd,
                        removed: toRemove,
                        merged: toMerge
                    };
                    this.trigger("update", this, options);
                }
            }
            // Return the added (or merged) model (or models).
            return singular ? models[0] : models;
        },
        // When you have more items than you want to add or remove individually,
        // you can reset the entire set with a new list of models, without firing
        // any granular `add` or `remove` events. Fires `reset` when finished.
        // Useful for bulk operations and optimizations.
        reset: function(models, options) {
            options = options ? _.clone(options) : {};
            for(var i = 0; i < this.models.length; i++)this._removeReference(this.models[i], options);
            options.previousModels = this.models;
            this._reset();
            models = this.add(models, _.extend({
                silent: true
            }, options));
            if (!options.silent) this.trigger("reset", this, options);
            return models;
        },
        // Add a model to the end of the collection.
        push: function(model, options) {
            return this.add(model, _.extend({
                at: this.length
            }, options));
        },
        // Remove a model from the end of the collection.
        pop: function(options) {
            var model = this.at(this.length - 1);
            return this.remove(model, options);
        },
        // Add a model to the beginning of the collection.
        unshift: function(model, options) {
            return this.add(model, _.extend({
                at: 0
            }, options));
        },
        // Remove a model from the beginning of the collection.
        shift: function(options) {
            var model = this.at(0);
            return this.remove(model, options);
        },
        // Slice out a sub-array of models from the collection.
        slice: function() {
            return slice.apply(this.models, arguments);
        },
        // Get a model from the set by id, cid, model object with id or cid
        // properties, or an attributes object that is transformed through modelId.
        get: function(obj) {
            if (obj == null) return void 0;
            return this._byId[obj] || this._byId[this.modelId(this._isModel(obj) ? obj.attributes : obj, obj.idAttribute)] || obj.cid && this._byId[obj.cid];
        },
        // Returns `true` if the model is in the collection.
        has: function(obj) {
            return this.get(obj) != null;
        },
        // Get the model at the given index.
        at: function(index) {
            if (index < 0) index += this.length;
            return this.models[index];
        },
        // Return models with matching attributes. Useful for simple cases of
        // `filter`.
        where: function(attrs, first) {
            return this[first ? "find" : "filter"](attrs);
        },
        // Return the first model with matching attributes. Useful for simple cases
        // of `find`.
        findWhere: function(attrs) {
            return this.where(attrs, true);
        },
        // Force the collection to re-sort itself. You don't need to call this under
        // normal circumstances, as the set will maintain sort order as each item
        // is added.
        sort: function(options) {
            var comparator = this.comparator;
            if (!comparator) throw new Error("Cannot sort a set without a comparator");
            options || (options = {});
            var length = comparator.length;
            if (_.isFunction(comparator)) comparator = comparator.bind(this);
            // Run sort based on type of `comparator`.
            if (length === 1 || _.isString(comparator)) this.models = this.sortBy(comparator);
            else this.models.sort(comparator);
            if (!options.silent) this.trigger("sort", this, options);
            return this;
        },
        // Pluck an attribute from each model in the collection.
        pluck: function(attr) {
            return this.map(attr + "");
        },
        // Fetch the default set of models for this collection, resetting the
        // collection when they arrive. If `reset: true` is passed, the response
        // data will be passed through the `reset` method instead of `set`.
        fetch: function(options) {
            options = _.extend({
                parse: true
            }, options);
            var success = options.success;
            var collection = this;
            options.success = function(resp) {
                var method = options.reset ? "reset" : "set";
                collection[method](resp, options);
                if (success) success.call(options.context, collection, resp, options);
                collection.trigger("sync", collection, resp, options);
            };
            wrapError(this, options);
            return this.sync("read", this, options);
        },
        // Create a new instance of a model in this collection. Add the model to the
        // collection immediately, unless `wait: true` is passed, in which case we
        // wait for the server to agree.
        create: function(model, options) {
            options = options ? _.clone(options) : {};
            var wait = options.wait;
            model = this._prepareModel(model, options);
            if (!model) return false;
            if (!wait) this.add(model, options);
            var collection = this;
            var success = options.success;
            options.success = function(m, resp, callbackOpts) {
                if (wait) {
                    m.off("error", this._forwardPristineError, this);
                    collection.add(m, callbackOpts);
                }
                if (success) success.call(callbackOpts.context, m, resp, callbackOpts);
            };
            // In case of wait:true, our collection is not listening to any
            // of the model's events yet, so it will not forward the error
            // event. In this special case, we need to listen for it
            // separately and handle the event just once.
            // (The reason we don't need to do this for the sync event is
            // in the success handler above: we add the model first, which
            // causes the collection to listen, and then invoke the callback
            // that triggers the event.)
            if (wait) model.once("error", this._forwardPristineError, this);
            model.save(null, options);
            return model;
        },
        // **parse** converts a response into a list of models to be added to the
        // collection. The default implementation is just to pass it through.
        parse: function(resp, options) {
            return resp;
        },
        // Create a new collection with an identical list of models as this one.
        clone: function() {
            return new this.constructor(this.models, {
                model: this.model,
                comparator: this.comparator
            });
        },
        // Define how to uniquely identify models in the collection.
        modelId: function(attrs, idAttribute) {
            return attrs[idAttribute || this.model.prototype.idAttribute || "id"];
        },
        // Get an iterator of all models in this collection.
        values: function() {
            return new CollectionIterator(this, ITERATOR_VALUES);
        },
        // Get an iterator of all model IDs in this collection.
        keys: function() {
            return new CollectionIterator(this, ITERATOR_KEYS);
        },
        // Get an iterator of all [ID, model] tuples in this collection.
        entries: function() {
            return new CollectionIterator(this, ITERATOR_KEYSVALUES);
        },
        // Private method to reset all internal state. Called when the collection
        // is first initialized or reset.
        _reset: function() {
            this.length = 0;
            this.models = [];
            this._byId = {};
        },
        // Prepare a hash of attributes (or other model) to be added to this
        // collection.
        _prepareModel: function(attrs, options) {
            if (this._isModel(attrs)) {
                if (!attrs.collection) attrs.collection = this;
                return attrs;
            }
            options = options ? _.clone(options) : {};
            options.collection = this;
            var model;
            if (this.model.prototype) model = new this.model(attrs, options);
            else // ES class methods didn't have prototype
            model = this.model(attrs, options);
            if (!model.validationError) return model;
            this.trigger("invalid", this, model.validationError, options);
            return false;
        },
        // Internal method called by both remove and set.
        _removeModels: function(models, options) {
            var removed = [];
            for(var i = 0; i < models.length; i++){
                var model = this.get(models[i]);
                if (!model) continue;
                var index = this.indexOf(model);
                this.models.splice(index, 1);
                this.length--;
                // Remove references before triggering 'remove' event to prevent an
                // infinite loop. #3693
                delete this._byId[model.cid];
                var id = this.modelId(model.attributes, model.idAttribute);
                if (id != null) delete this._byId[id];
                if (!options.silent) {
                    options.index = index;
                    model.trigger("remove", model, this, options);
                }
                removed.push(model);
                this._removeReference(model, options);
            }
            if (models.length > 0 && !options.silent) delete options.index;
            return removed;
        },
        // Method for checking whether an object should be considered a model for
        // the purposes of adding to the collection.
        _isModel: function(model) {
            return model instanceof Model;
        },
        // Internal method to create a model's ties to a collection.
        _addReference: function(model, options) {
            this._byId[model.cid] = model;
            var id = this.modelId(model.attributes, model.idAttribute);
            if (id != null) this._byId[id] = model;
            model.on("all", this._onModelEvent, this);
        },
        // Internal method to sever a model's ties to a collection.
        _removeReference: function(model, options) {
            delete this._byId[model.cid];
            var id = this.modelId(model.attributes, model.idAttribute);
            if (id != null) delete this._byId[id];
            if (this === model.collection) delete model.collection;
            model.off("all", this._onModelEvent, this);
        },
        // Internal method called every time a model in the set fires an event.
        // Sets need to update their indexes when models change ids. All other
        // events simply proxy through. "add" and "remove" events that originate
        // in other collections are ignored.
        _onModelEvent: function(event, model, collection, options) {
            if (model) {
                if ((event === "add" || event === "remove") && collection !== this) return;
                if (event === "destroy") this.remove(model, options);
                if (event === "changeId") {
                    var prevId = this.modelId(model.previousAttributes(), model.idAttribute);
                    var id = this.modelId(model.attributes, model.idAttribute);
                    if (prevId != null) delete this._byId[prevId];
                    if (id != null) this._byId[id] = model;
                }
            }
            this.trigger.apply(this, arguments);
        },
        // Internal callback method used in `create`. It serves as a
        // stand-in for the `_onModelEvent` method, which is not yet bound
        // during the `wait` period of the `create` call. We still want to
        // forward any `'error'` event at the end of the `wait` period,
        // hence a customized callback.
        _forwardPristineError: function(model, collection, options) {
            // Prevent double forward if the model was already in the
            // collection before the call to `create`.
            if (this.has(model)) return;
            this._onModelEvent("error", model, collection, options);
        }
    });
    // Defining an @@iterator method implements JavaScript's Iterable protocol.
    // In modern ES2015 browsers, this value is found at Symbol.iterator.
    /* global Symbol */ var $$iterator = typeof Symbol === "function" && Symbol.iterator;
    if ($$iterator) Collection.prototype[$$iterator] = Collection.prototype.values;
    // CollectionIterator
    // ------------------
    // A CollectionIterator implements JavaScript's Iterator protocol, allowing the
    // use of `for of` loops in modern browsers and interoperation between
    // Backbone.Collection and other JavaScript functions and third-party libraries
    // which can operate on Iterables.
    var CollectionIterator = function(collection, kind) {
        this._collection = collection;
        this._kind = kind;
        this._index = 0;
    };
    // This "enum" defines the three possible kinds of values which can be emitted
    // by a CollectionIterator that correspond to the values(), keys() and entries()
    // methods on Collection, respectively.
    var ITERATOR_VALUES = 1;
    var ITERATOR_KEYS = 2;
    var ITERATOR_KEYSVALUES = 3;
    // All Iterators should themselves be Iterable.
    if ($$iterator) CollectionIterator.prototype[$$iterator] = function() {
        return this;
    };
    CollectionIterator.prototype.next = function() {
        if (this._collection) {
            // Only continue iterating if the iterated collection is long enough.
            if (this._index < this._collection.length) {
                var model = this._collection.at(this._index);
                this._index++;
                // Construct a value depending on what kind of values should be iterated.
                var value;
                if (this._kind === ITERATOR_VALUES) value = model;
                else {
                    var id = this._collection.modelId(model.attributes, model.idAttribute);
                    if (this._kind === ITERATOR_KEYS) value = id;
                    else value = [
                        id,
                        model
                    ];
                }
                return {
                    value: value,
                    done: false
                };
            }
            // Once exhausted, remove the reference to the collection so future
            // calls to the next method always return done.
            this._collection = void 0;
        }
        return {
            value: void 0,
            done: true
        };
    };
    // Backbone.View
    // -------------
    // Backbone Views are almost more convention than they are actual code. A View
    // is simply a JavaScript object that represents a logical chunk of UI in the
    // DOM. This might be a single item, an entire list, a sidebar or panel, or
    // even the surrounding frame which wraps your whole app. Defining a chunk of
    // UI as a **View** allows you to define your DOM events declaratively, without
    // having to worry about render order ... and makes it easy for the view to
    // react to specific changes in the state of your models.
    // Creating a Backbone.View creates its initial element outside of the DOM,
    // if an existing element is not provided...
    var View = Backbone.View = function(options) {
        this.cid = _.uniqueId("view");
        this.preinitialize.apply(this, arguments);
        _.extend(this, _.pick(options, viewOptions));
        this._ensureElement();
        this.initialize.apply(this, arguments);
    };
    // Cached regex to split keys for `delegate`.
    var delegateEventSplitter = /^(\S+)\s*(.*)$/;
    // List of view options to be set as properties.
    var viewOptions = [
        "model",
        "collection",
        "el",
        "id",
        "attributes",
        "className",
        "tagName",
        "events"
    ];
    // Set up all inheritable **Backbone.View** properties and methods.
    _.extend(View.prototype, Events, {
        // The default `tagName` of a View's element is `"div"`.
        tagName: "div",
        // jQuery delegate for element lookup, scoped to DOM elements within the
        // current view. This should be preferred to global lookups where possible.
        $: function(selector) {
            return this.$el.find(selector);
        },
        // preinitialize is an empty function by default. You can override it with a function
        // or object.  preinitialize will run before any instantiation logic is run in the View
        preinitialize: function() {},
        // Initialize is an empty function by default. Override it with your own
        // initialization logic.
        initialize: function() {},
        // **render** is the core function that your view should override, in order
        // to populate its element (`this.el`), with the appropriate HTML. The
        // convention is for **render** to always return `this`.
        render: function() {
            return this;
        },
        // Remove this view by taking the element out of the DOM, and removing any
        // applicable Backbone.Events listeners.
        remove: function() {
            this._removeElement();
            this.stopListening();
            return this;
        },
        // Remove this view's element from the document and all event listeners
        // attached to it. Exposed for subclasses using an alternative DOM
        // manipulation API.
        _removeElement: function() {
            this.$el.remove();
        },
        // Change the view's element (`this.el` property) and re-delegate the
        // view's events on the new element.
        setElement: function(element) {
            this.undelegateEvents();
            this._setElement(element);
            this.delegateEvents();
            return this;
        },
        // Creates the `this.el` and `this.$el` references for this view using the
        // given `el`. `el` can be a CSS selector or an HTML string, a jQuery
        // context or an element. Subclasses can override this to utilize an
        // alternative DOM manipulation API and are only required to set the
        // `this.el` property.
        _setElement: function(el) {
            this.$el = el instanceof Backbone.$ ? el : Backbone.$(el);
            this.el = this.$el[0];
        },
        // Set callbacks, where `this.events` is a hash of
        //
        // *{"event selector": "callback"}*
        //
        //     {
        //       'mousedown .title':  'edit',
        //       'click .button':     'save',
        //       'click .open':       function(e) { ... }
        //     }
        //
        // pairs. Callbacks will be bound to the view, with `this` set properly.
        // Uses event delegation for efficiency.
        // Omitting the selector binds the event to `this.el`.
        delegateEvents: function(events) {
            events || (events = _.result(this, "events"));
            if (!events) return this;
            this.undelegateEvents();
            for(var key in events){
                var method = events[key];
                if (!_.isFunction(method)) method = this[method];
                if (!method) continue;
                var match = key.match(delegateEventSplitter);
                this.delegate(match[1], match[2], method.bind(this));
            }
            return this;
        },
        // Add a single event listener to the view's element (or a child element
        // using `selector`). This only works for delegate-able events: not `focus`,
        // `blur`, and not `change`, `submit`, and `reset` in Internet Explorer.
        delegate: function(eventName, selector, listener) {
            this.$el.on(eventName + ".delegateEvents" + this.cid, selector, listener);
            return this;
        },
        // Clears all callbacks previously bound to the view by `delegateEvents`.
        // You usually don't need to use this, but may wish to if you have multiple
        // Backbone views attached to the same DOM element.
        undelegateEvents: function() {
            if (this.$el) this.$el.off(".delegateEvents" + this.cid);
            return this;
        },
        // A finer-grained `undelegateEvents` for removing a single delegated event.
        // `selector` and `listener` are both optional.
        undelegate: function(eventName, selector, listener) {
            this.$el.off(eventName + ".delegateEvents" + this.cid, selector, listener);
            return this;
        },
        // Produces a DOM element to be assigned to your view. Exposed for
        // subclasses using an alternative DOM manipulation API.
        _createElement: function(tagName) {
            return document.createElement(tagName);
        },
        // Ensure that the View has a DOM element to render into.
        // If `this.el` is a string, pass it through `$()`, take the first
        // matching element, and re-assign it to `el`. Otherwise, create
        // an element from the `id`, `className` and `tagName` properties.
        _ensureElement: function() {
            if (!this.el) {
                var attrs = _.extend({}, _.result(this, "attributes"));
                if (this.id) attrs.id = _.result(this, "id");
                if (this.className) attrs["class"] = _.result(this, "className");
                this.setElement(this._createElement(_.result(this, "tagName")));
                this._setAttributes(attrs);
            } else this.setElement(_.result(this, "el"));
        },
        // Set attributes from a hash on this view's element.  Exposed for
        // subclasses using an alternative DOM manipulation API.
        _setAttributes: function(attributes) {
            this.$el.attr(attributes);
        }
    });
    // Proxy Backbone class methods to Underscore functions, wrapping the model's
    // `attributes` object or collection's `models` array behind the scenes.
    //
    // collection.filter(function(model) { return model.get('age') > 10 });
    // collection.each(this.addView);
    //
    // `Function#apply` can be slow so we use the method's arg count, if we know it.
    var addMethod = function(base, length, method, attribute) {
        switch(length){
            case 1:
                return function() {
                    return base[method](this[attribute]);
                };
            case 2:
                return function(value) {
                    return base[method](this[attribute], value);
                };
            case 3:
                return function(iteratee, context) {
                    return base[method](this[attribute], cb(iteratee, this), context);
                };
            case 4:
                return function(iteratee, defaultVal, context) {
                    return base[method](this[attribute], cb(iteratee, this), defaultVal, context);
                };
            default:
                return function() {
                    var args = slice.call(arguments);
                    args.unshift(this[attribute]);
                    return base[method].apply(base, args);
                };
        }
    };
    var addUnderscoreMethods = function(Class, base, methods, attribute) {
        _.each(methods, function(length, method) {
            if (base[method]) Class.prototype[method] = addMethod(base, length, method, attribute);
        });
    };
    // Support `collection.sortBy('attr')` and `collection.findWhere({id: 1})`.
    var cb = function(iteratee, instance) {
        if (_.isFunction(iteratee)) return iteratee;
        if (_.isObject(iteratee) && !instance._isModel(iteratee)) return modelMatcher(iteratee);
        if (_.isString(iteratee)) return function(model) {
            return model.get(iteratee);
        };
        return iteratee;
    };
    var modelMatcher = function(attrs) {
        var matcher = _.matches(attrs);
        return function(model) {
            return matcher(model.attributes);
        };
    };
    // Underscore methods that we want to implement on the Collection.
    // 90% of the core usefulness of Backbone Collections is actually implemented
    // right here:
    var collectionMethods = {
        forEach: 3,
        each: 3,
        map: 3,
        collect: 3,
        reduce: 0,
        foldl: 0,
        inject: 0,
        reduceRight: 0,
        foldr: 0,
        find: 3,
        detect: 3,
        filter: 3,
        select: 3,
        reject: 3,
        every: 3,
        all: 3,
        some: 3,
        any: 3,
        include: 3,
        includes: 3,
        contains: 3,
        invoke: 0,
        max: 3,
        min: 3,
        toArray: 1,
        size: 1,
        first: 3,
        head: 3,
        take: 3,
        initial: 3,
        rest: 3,
        tail: 3,
        drop: 3,
        last: 3,
        without: 0,
        difference: 0,
        indexOf: 3,
        shuffle: 1,
        lastIndexOf: 3,
        isEmpty: 1,
        chain: 1,
        sample: 3,
        partition: 3,
        groupBy: 3,
        countBy: 3,
        sortBy: 3,
        indexBy: 3,
        findIndex: 3,
        findLastIndex: 3
    };
    // Underscore methods that we want to implement on the Model, mapped to the
    // number of arguments they take.
    var modelMethods = {
        keys: 1,
        values: 1,
        pairs: 1,
        invert: 1,
        pick: 0,
        omit: 0,
        chain: 1,
        isEmpty: 1
    };
    // Mix in each Underscore method as a proxy to `Collection#models`.
    _.each([
        [
            Collection,
            collectionMethods,
            "models"
        ],
        [
            Model,
            modelMethods,
            "attributes"
        ]
    ], function(config) {
        var Base = config[0], methods = config[1], attribute = config[2];
        Base.mixin = function(obj) {
            var mappings = _.reduce(_.functions(obj), function(memo, name) {
                memo[name] = 0;
                return memo;
            }, {});
            addUnderscoreMethods(Base, obj, mappings, attribute);
        };
        addUnderscoreMethods(Base, _, methods, attribute);
    });
    // Backbone.sync
    // -------------
    // Override this function to change the manner in which Backbone persists
    // models to the server. You will be passed the type of request, and the
    // model in question. By default, makes a RESTful Ajax request
    // to the model's `url()`. Some possible customizations could be:
    //
    // * Use `setTimeout` to batch rapid-fire updates into a single request.
    // * Send up the models as XML instead of JSON.
    // * Persist models via WebSockets instead of Ajax.
    //
    // Turn on `Backbone.emulateHTTP` in order to send `PUT` and `DELETE` requests
    // as `POST`, with a `_method` parameter containing the true HTTP method,
    // as well as all requests with the body as `application/x-www-form-urlencoded`
    // instead of `application/json` with the model in a param named `model`.
    // Useful when interfacing with server-side languages like **PHP** that make
    // it difficult to read the body of `PUT` requests.
    Backbone.sync = function(method, model, options) {
        var type = methodMap[method];
        // Default options, unless specified.
        _.defaults(options || (options = {}), {
            emulateHTTP: Backbone.emulateHTTP,
            emulateJSON: Backbone.emulateJSON
        });
        // Default JSON-request options.
        var params = {
            type: type,
            dataType: "json"
        };
        // Ensure that we have a URL.
        if (!options.url) params.url = _.result(model, "url") || urlError();
        // Ensure that we have the appropriate request data.
        if (options.data == null && model && (method === "create" || method === "update" || method === "patch")) {
            params.contentType = "application/json";
            params.data = JSON.stringify(options.attrs || model.toJSON(options));
        }
        // For older servers, emulate JSON by encoding the request into an HTML-form.
        if (options.emulateJSON) {
            params.contentType = "application/x-www-form-urlencoded";
            params.data = params.data ? {
                model: params.data
            } : {};
        }
        // For older servers, emulate HTTP by mimicking the HTTP method with `_method`
        // And an `X-HTTP-Method-Override` header.
        if (options.emulateHTTP && (type === "PUT" || type === "DELETE" || type === "PATCH")) {
            params.type = "POST";
            if (options.emulateJSON) params.data._method = type;
            var beforeSend = options.beforeSend;
            options.beforeSend = function(xhr) {
                xhr.setRequestHeader("X-HTTP-Method-Override", type);
                if (beforeSend) return beforeSend.apply(this, arguments);
            };
        }
        // Don't process data on a non-GET request.
        if (params.type !== "GET" && !options.emulateJSON) params.processData = false;
        // Pass along `textStatus` and `errorThrown` from jQuery.
        var error = options.error;
        options.error = function(xhr, textStatus, errorThrown) {
            options.textStatus = textStatus;
            options.errorThrown = errorThrown;
            if (error) error.call(options.context, xhr, textStatus, errorThrown);
        };
        // Make the request, allowing the user to override any Ajax options.
        var xhr = options.xhr = Backbone.ajax(_.extend(params, options));
        model.trigger("request", model, xhr, options);
        return xhr;
    };
    // Map from CRUD to HTTP for our default `Backbone.sync` implementation.
    var methodMap = {
        "create": "POST",
        "update": "PUT",
        "patch": "PATCH",
        "delete": "DELETE",
        "read": "GET"
    };
    // Set the default implementation of `Backbone.ajax` to proxy through to `$`.
    // Override this if you'd like to use a different library.
    Backbone.ajax = function() {
        return Backbone.$.ajax.apply(Backbone.$, arguments);
    };
    // Backbone.Router
    // ---------------
    // Routers map faux-URLs to actions, and fire events when routes are
    // matched. Creating a new one sets its `routes` hash, if not set statically.
    var Router = Backbone.Router = function(options) {
        options || (options = {});
        this.preinitialize.apply(this, arguments);
        if (options.routes) this.routes = options.routes;
        this._bindRoutes();
        this.initialize.apply(this, arguments);
    };
    // Cached regular expressions for matching named param parts and splatted
    // parts of route strings.
    var optionalParam = /\((.*?)\)/g;
    var namedParam = /(\(\?)?:\w+/g;
    var splatParam = /\*\w+/g;
    var escapeRegExp = /[\-{}\[\]+?.,\\\^$|#\s]/g;
    // Set up all inheritable **Backbone.Router** properties and methods.
    _.extend(Router.prototype, Events, {
        // preinitialize is an empty function by default. You can override it with a function
        // or object.  preinitialize will run before any instantiation logic is run in the Router.
        preinitialize: function() {},
        // Initialize is an empty function by default. Override it with your own
        // initialization logic.
        initialize: function() {},
        // Manually bind a single named route to a callback. For example:
        //
        //     this.route('search/:query/p:num', 'search', function(query, num) {
        //       ...
        //     });
        //
        route: function(route, name, callback) {
            if (!_.isRegExp(route)) route = this._routeToRegExp(route);
            if (_.isFunction(name)) {
                callback = name;
                name = "";
            }
            if (!callback) callback = this[name];
            var router = this;
            Backbone.history.route(route, function(fragment) {
                var args = router._extractParameters(route, fragment);
                if (router.execute(callback, args, name) !== false) {
                    router.trigger.apply(router, [
                        "route:" + name
                    ].concat(args));
                    router.trigger("route", name, args);
                    Backbone.history.trigger("route", router, name, args);
                }
            });
            return this;
        },
        // Execute a route handler with the provided parameters.  This is an
        // excellent place to do pre-route setup or post-route cleanup.
        execute: function(callback, args, name) {
            if (callback) callback.apply(this, args);
        },
        // Simple proxy to `Backbone.history` to save a fragment into the history.
        navigate: function(fragment, options) {
            Backbone.history.navigate(fragment, options);
            return this;
        },
        // Bind all defined routes to `Backbone.history`. We have to reverse the
        // order of the routes here to support behavior where the most general
        // routes can be defined at the bottom of the route map.
        _bindRoutes: function() {
            if (!this.routes) return;
            this.routes = _.result(this, "routes");
            var route, routes = _.keys(this.routes);
            while((route = routes.pop()) != null)this.route(route, this.routes[route]);
        },
        // Convert a route string into a regular expression, suitable for matching
        // against the current location hash.
        _routeToRegExp: function(route) {
            route = route.replace(escapeRegExp, "\\$&").replace(optionalParam, "(?:$1)?").replace(namedParam, function(match, optional) {
                return optional ? match : "([^/?]+)";
            }).replace(splatParam, "([^?]*?)");
            return new RegExp("^" + route + "(?:\\?([\\s\\S]*))?$");
        },
        // Given a route, and a URL fragment that it matches, return the array of
        // extracted decoded parameters. Empty or unmatched parameters will be
        // treated as `null` to normalize cross-browser behavior.
        _extractParameters: function(route, fragment) {
            var params = route.exec(fragment).slice(1);
            return _.map(params, function(param, i) {
                // Don't decode the search params.
                if (i === params.length - 1) return param || null;
                return param ? decodeURIComponent(param) : null;
            });
        }
    });
    // Backbone.History
    // ----------------
    // Handles cross-browser history management, based on either
    // [pushState](http://diveintohtml5.info/history.html) and real URLs, or
    // [onhashchange](https://developer.mozilla.org/en-US/docs/DOM/window.onhashchange)
    // and URL fragments. If the browser supports neither (old IE, natch),
    // falls back to polling.
    var History = Backbone.History = function() {
        this.handlers = [];
        this.checkUrl = this.checkUrl.bind(this);
        // Ensure that `History` can be used outside of the browser.
        if (typeof window !== "undefined") {
            this.location = window.location;
            this.history = window.history;
        }
    };
    // Cached regex for stripping a leading hash/slash and trailing space.
    var routeStripper = /^[#\/]|\s+$/g;
    // Cached regex for stripping leading and trailing slashes.
    var rootStripper = /^\/+|\/+$/g;
    // Cached regex for stripping urls of hash.
    var pathStripper = /#.*$/;
    // Has the history handling already been started?
    History.started = false;
    // Set up all inheritable **Backbone.History** properties and methods.
    _.extend(History.prototype, Events, {
        // The default interval to poll for hash changes, if necessary, is
        // twenty times a second.
        interval: 50,
        // Are we at the app root?
        atRoot: function() {
            var path = this.location.pathname.replace(/[^\/]$/, "$&/");
            return path === this.root && !this.getSearch();
        },
        // Does the pathname match the root?
        matchRoot: function() {
            var path = this.decodeFragment(this.location.pathname);
            var rootPath = path.slice(0, this.root.length - 1) + "/";
            return rootPath === this.root;
        },
        // Unicode characters in `location.pathname` are percent encoded so they're
        // decoded for comparison. `%25` should not be decoded since it may be part
        // of an encoded parameter.
        decodeFragment: function(fragment) {
            return decodeURI(fragment.replace(/%25/g, "%2525"));
        },
        // In IE6, the hash fragment and search params are incorrect if the
        // fragment contains `?`.
        getSearch: function() {
            var match = this.location.href.replace(/#.*/, "").match(/\?.+/);
            return match ? match[0] : "";
        },
        // Gets the true hash value. Cannot use location.hash directly due to bug
        // in Firefox where location.hash will always be decoded.
        getHash: function(window1) {
            var match = (window1 || this).location.href.match(/#(.*)$/);
            return match ? match[1] : "";
        },
        // Get the pathname and search params, without the root.
        getPath: function() {
            var path = this.decodeFragment(this.location.pathname + this.getSearch()).slice(this.root.length - 1);
            return path.charAt(0) === "/" ? path.slice(1) : path;
        },
        // Get the cross-browser normalized URL fragment from the path or hash.
        getFragment: function(fragment) {
            if (fragment == null) {
                if (this._usePushState || !this._wantsHashChange) fragment = this.getPath();
                else fragment = this.getHash();
            }
            return fragment.replace(routeStripper, "");
        },
        // Start the hash change handling, returning `true` if the current URL matches
        // an existing route, and `false` otherwise.
        start: function(options) {
            if (History.started) throw new Error("Backbone.history has already been started");
            History.started = true;
            // Figure out the initial configuration. Do we need an iframe?
            // Is pushState desired ... is it available?
            this.options = _.extend({
                root: "/"
            }, this.options, options);
            this.root = this.options.root;
            this._trailingSlash = this.options.trailingSlash;
            this._wantsHashChange = this.options.hashChange !== false;
            this._hasHashChange = "onhashchange" in window && (document.documentMode === void 0 || document.documentMode > 7);
            this._useHashChange = this._wantsHashChange && this._hasHashChange;
            this._wantsPushState = !!this.options.pushState;
            this._hasPushState = !!(this.history && this.history.pushState);
            this._usePushState = this._wantsPushState && this._hasPushState;
            this.fragment = this.getFragment();
            // Normalize root to always include a leading and trailing slash.
            this.root = ("/" + this.root + "/").replace(rootStripper, "/");
            // Transition from hashChange to pushState or vice versa if both are
            // requested.
            if (this._wantsHashChange && this._wantsPushState) {
                // If we've started off with a route from a `pushState`-enabled
                // browser, but we're currently in a browser that doesn't support it...
                if (!this._hasPushState && !this.atRoot()) {
                    var rootPath = this.root.slice(0, -1) || "/";
                    this.location.replace(rootPath + "#" + this.getPath());
                    // Return immediately as browser will do redirect to new url
                    return true;
                // Or if we've started out with a hash-based route, but we're currently
                // in a browser where it could be `pushState`-based instead...
                } else if (this._hasPushState && this.atRoot()) this.navigate(this.getHash(), {
                    replace: true
                });
            }
            // Proxy an iframe to handle location events if the browser doesn't
            // support the `hashchange` event, HTML5 history, or the user wants
            // `hashChange` but not `pushState`.
            if (!this._hasHashChange && this._wantsHashChange && !this._usePushState) {
                this.iframe = document.createElement("iframe");
                this.iframe.src = "javascript:0";
                this.iframe.style.display = "none";
                this.iframe.tabIndex = -1;
                var body = document.body;
                // Using `appendChild` will throw on IE < 9 if the document is not ready.
                var iWindow = body.insertBefore(this.iframe, body.firstChild).contentWindow;
                iWindow.document.open();
                iWindow.document.close();
                iWindow.location.hash = "#" + this.fragment;
            }
            // Add a cross-platform `addEventListener` shim for older browsers.
            var addEventListener = window.addEventListener || function(eventName, listener) {
                return attachEvent("on" + eventName, listener);
            };
            // Depending on whether we're using pushState or hashes, and whether
            // 'onhashchange' is supported, determine how we check the URL state.
            if (this._usePushState) addEventListener("popstate", this.checkUrl, false);
            else if (this._useHashChange && !this.iframe) addEventListener("hashchange", this.checkUrl, false);
            else if (this._wantsHashChange) this._checkUrlInterval = setInterval(this.checkUrl, this.interval);
            if (!this.options.silent) return this.loadUrl();
        },
        // Disable Backbone.history, perhaps temporarily. Not useful in a real app,
        // but possibly useful for unit testing Routers.
        stop: function() {
            // Add a cross-platform `removeEventListener` shim for older browsers.
            var removeEventListener = window.removeEventListener || function(eventName, listener) {
                return detachEvent("on" + eventName, listener);
            };
            // Remove window listeners.
            if (this._usePushState) removeEventListener("popstate", this.checkUrl, false);
            else if (this._useHashChange && !this.iframe) removeEventListener("hashchange", this.checkUrl, false);
            // Clean up the iframe if necessary.
            if (this.iframe) {
                document.body.removeChild(this.iframe);
                this.iframe = null;
            }
            // Some environments will throw when clearing an undefined interval.
            if (this._checkUrlInterval) clearInterval(this._checkUrlInterval);
            History.started = false;
        },
        // Add a route to be tested when the fragment changes. Routes added later
        // may override previous routes.
        route: function(route, callback) {
            this.handlers.unshift({
                route: route,
                callback: callback
            });
        },
        // Checks the current URL to see if it has changed, and if it has,
        // calls `loadUrl`, normalizing across the hidden iframe.
        checkUrl: function(e) {
            var current = this.getFragment();
            // If the user pressed the back button, the iframe's hash will have
            // changed and we should use that for comparison.
            if (current === this.fragment && this.iframe) current = this.getHash(this.iframe.contentWindow);
            if (current === this.fragment) return false;
            if (this.iframe) this.navigate(current);
            this.loadUrl();
        },
        // Attempt to load the current URL fragment. If a route succeeds with a
        // match, returns `true`. If no defined routes matches the fragment,
        // returns `false`.
        loadUrl: function(fragment) {
            // If the root doesn't match, no routes can match either.
            if (!this.matchRoot()) return false;
            fragment = this.fragment = this.getFragment(fragment);
            return _.some(this.handlers, function(handler) {
                if (handler.route.test(fragment)) {
                    handler.callback(fragment);
                    return true;
                }
            });
        },
        // Save a fragment into the hash history, or replace the URL state if the
        // 'replace' option is passed. You are responsible for properly URL-encoding
        // the fragment in advance.
        //
        // The options object can contain `trigger: true` if you wish to have the
        // route callback be fired (not usually desirable), or `replace: true`, if
        // you wish to modify the current URL without adding an entry to the history.
        navigate: function(fragment, options) {
            if (!History.started) return false;
            if (!options || options === true) options = {
                trigger: !!options
            };
            // Normalize the fragment.
            fragment = this.getFragment(fragment || "");
            // Strip trailing slash on the root unless _trailingSlash is true
            var rootPath = this.root;
            if (!this._trailingSlash && (fragment === "" || fragment.charAt(0) === "?")) rootPath = rootPath.slice(0, -1) || "/";
            var url = rootPath + fragment;
            // Strip the fragment of the query and hash for matching.
            fragment = fragment.replace(pathStripper, "");
            // Decode for matching.
            var decodedFragment = this.decodeFragment(fragment);
            if (this.fragment === decodedFragment) return;
            this.fragment = decodedFragment;
            // If pushState is available, we use it to set the fragment as a real URL.
            if (this._usePushState) this.history[options.replace ? "replaceState" : "pushState"]({}, document.title, url);
            else if (this._wantsHashChange) {
                this._updateHash(this.location, fragment, options.replace);
                if (this.iframe && fragment !== this.getHash(this.iframe.contentWindow)) {
                    var iWindow = this.iframe.contentWindow;
                    // Opening and closing the iframe tricks IE7 and earlier to push a
                    // history entry on hash-tag change.  When replace is true, we don't
                    // want this.
                    if (!options.replace) {
                        iWindow.document.open();
                        iWindow.document.close();
                    }
                    this._updateHash(iWindow.location, fragment, options.replace);
                }
            // If you've told us that you explicitly don't want fallback hashchange-
            // based history, then `navigate` becomes a page refresh.
            } else return this.location.assign(url);
            if (options.trigger) return this.loadUrl(fragment);
        },
        // Update the hash location, either replacing the current entry, or adding
        // a new one to the browser history.
        _updateHash: function(location, fragment, replace) {
            if (replace) {
                var href = location.href.replace(/(javascript:|#).*$/, "");
                location.replace(href + "#" + fragment);
            } else // Some browsers require that `hash` contains a leading #.
            location.hash = "#" + fragment;
        }
    });
    // Create the default Backbone.history.
    Backbone.history = new History;
    // Helpers
    // -------
    // Helper function to correctly set up the prototype chain for subclasses.
    // Similar to `goog.inherits`, but uses a hash of prototype properties and
    // class properties to be extended.
    var extend = function(protoProps, staticProps) {
        var parent = this;
        var child;
        // The constructor function for the new subclass is either defined by you
        // (the "constructor" property in your `extend` definition), or defaulted
        // by us to simply call the parent constructor.
        if (protoProps && _.has(protoProps, "constructor")) child = protoProps.constructor;
        else child = function() {
            return parent.apply(this, arguments);
        };
        // Add static properties to the constructor function, if supplied.
        _.extend(child, parent, staticProps);
        // Set the prototype chain to inherit from `parent`, without calling
        // `parent`'s constructor function and add the prototype properties.
        child.prototype = _.create(parent.prototype, protoProps);
        child.prototype.constructor = child;
        // Set a convenience property in case the parent's prototype is needed
        // later.
        child.__super__ = parent.prototype;
        return child;
    };
    // Set up inheritance for the model, collection, router, view and history.
    Model.extend = Collection.extend = Router.extend = View.extend = History.extend = extend;
    // Throw an error when a URL is needed, and none is supplied.
    var urlError = function() {
        throw new Error('A "url" property or function must be specified');
    };
    // Wrap an optional error callback with a fallback error event.
    var wrapError = function(model, options) {
        var error = options.error;
        options.error = function(resp) {
            if (error) error.call(options.context, model, resp, options);
            model.trigger("error", model, resp, options);
        };
    };
    return Backbone;
});

},{"e151143268b413f3":"8o1Pk","404841aae61b7dc0":"hgMhh"}],"8o1Pk":[function(require,module,exports) {
// ESM Exports
// ===========
// This module is the package entry point for ES module users. In other words,
// it is the module they are interfacing with when they import from the whole
// package instead of from a submodule, like this:
//
// ```js
// import { map } from 'underscore';
// ```
//
// The difference with `./index-default`, which is the package entry point for
// CommonJS, AMD and UMD users, is purely technical. In ES modules, named and
// default exports are considered to be siblings, so when you have a default
// export, its properties are not automatically available as named exports. For
// this reason, we re-export the named exports in addition to providing the same
// default export as in `./index-default`.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>(0, _indexDefaultJsDefault.default));
var _indexDefaultJs = require("./index-default.js");
var _indexDefaultJsDefault = parcelHelpers.interopDefault(_indexDefaultJs);
var _indexJs = require("./index.js");
parcelHelpers.exportAll(_indexJs, exports);

},{"./index-default.js":"gyi03","./index.js":"l9sOw","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"gyi03":[function(require,module,exports) {
// Default Export
// ==============
// In this module, we mix our bundled exports into the `_` object and export
// the result. This is analogous to setting `module.exports = _` in CommonJS.
// Hence, this module is also the entry point of our UMD bundle and the package
// entry point for CommonJS and AMD users. In other words, this is (the source
// of) the module you are interfacing with when you do any of the following:
//
// ```js
// // CommonJS
// var _ = require('underscore');
//
// // AMD
// define(['underscore'], function(_) {...});
//
// // UMD in the browser
// // _ is available as a global variable
// ```
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _indexJs = require("./index.js");
// Add all of the Underscore functions to the wrapper object.
var _ = (0, _indexJs.mixin)(_indexJs);
// Legacy Node.js API.
_._ = _;
// Export the Underscore API.
exports.default = _;

},{"./index.js":"l9sOw","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"l9sOw":[function(require,module,exports) {
// Named Exports
// =============
//     Underscore.js 1.13.6
//     https://underscorejs.org
//     (c) 2009-2022 Jeremy Ashkenas, Julian Gonggrijp, and DocumentCloud and Investigative Reporters & Editors
//     Underscore may be freely distributed under the MIT license.
// Baseline setup.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "VERSION", ()=>(0, _setupJs.VERSION));
parcelHelpers.export(exports, "restArguments", ()=>(0, _restArgumentsJsDefault.default));
// Object Functions
// ----------------
// Our most fundamental functions operate on any JavaScript object.
// Most functions in Underscore depend on at least one function in this section.
// A group of functions that check the types of core JavaScript values.
// These are often informally referred to as the "isType" functions.
parcelHelpers.export(exports, "isObject", ()=>(0, _isObjectJsDefault.default));
parcelHelpers.export(exports, "isNull", ()=>(0, _isNullJsDefault.default));
parcelHelpers.export(exports, "isUndefined", ()=>(0, _isUndefinedJsDefault.default));
parcelHelpers.export(exports, "isBoolean", ()=>(0, _isBooleanJsDefault.default));
parcelHelpers.export(exports, "isElement", ()=>(0, _isElementJsDefault.default));
parcelHelpers.export(exports, "isString", ()=>(0, _isStringJsDefault.default));
parcelHelpers.export(exports, "isNumber", ()=>(0, _isNumberJsDefault.default));
parcelHelpers.export(exports, "isDate", ()=>(0, _isDateJsDefault.default));
parcelHelpers.export(exports, "isRegExp", ()=>(0, _isRegExpJsDefault.default));
parcelHelpers.export(exports, "isError", ()=>(0, _isErrorJsDefault.default));
parcelHelpers.export(exports, "isSymbol", ()=>(0, _isSymbolJsDefault.default));
parcelHelpers.export(exports, "isArrayBuffer", ()=>(0, _isArrayBufferJsDefault.default));
parcelHelpers.export(exports, "isDataView", ()=>(0, _isDataViewJsDefault.default));
parcelHelpers.export(exports, "isArray", ()=>(0, _isArrayJsDefault.default));
parcelHelpers.export(exports, "isFunction", ()=>(0, _isFunctionJsDefault.default));
parcelHelpers.export(exports, "isArguments", ()=>(0, _isArgumentsJsDefault.default));
parcelHelpers.export(exports, "isFinite", ()=>(0, _isFiniteJsDefault.default));
parcelHelpers.export(exports, "isNaN", ()=>(0, _isNaNJsDefault.default));
parcelHelpers.export(exports, "isTypedArray", ()=>(0, _isTypedArrayJsDefault.default));
parcelHelpers.export(exports, "isEmpty", ()=>(0, _isEmptyJsDefault.default));
parcelHelpers.export(exports, "isMatch", ()=>(0, _isMatchJsDefault.default));
parcelHelpers.export(exports, "isEqual", ()=>(0, _isEqualJsDefault.default));
parcelHelpers.export(exports, "isMap", ()=>(0, _isMapJsDefault.default));
parcelHelpers.export(exports, "isWeakMap", ()=>(0, _isWeakMapJsDefault.default));
parcelHelpers.export(exports, "isSet", ()=>(0, _isSetJsDefault.default));
parcelHelpers.export(exports, "isWeakSet", ()=>(0, _isWeakSetJsDefault.default));
// Functions that treat an object as a dictionary of key-value pairs.
parcelHelpers.export(exports, "keys", ()=>(0, _keysJsDefault.default));
parcelHelpers.export(exports, "allKeys", ()=>(0, _allKeysJsDefault.default));
parcelHelpers.export(exports, "values", ()=>(0, _valuesJsDefault.default));
parcelHelpers.export(exports, "pairs", ()=>(0, _pairsJsDefault.default));
parcelHelpers.export(exports, "invert", ()=>(0, _invertJsDefault.default));
parcelHelpers.export(exports, "functions", ()=>(0, _functionsJsDefault.default));
parcelHelpers.export(exports, "methods", ()=>(0, _functionsJsDefault.default));
parcelHelpers.export(exports, "extend", ()=>(0, _extendJsDefault.default));
parcelHelpers.export(exports, "extendOwn", ()=>(0, _extendOwnJsDefault.default));
parcelHelpers.export(exports, "assign", ()=>(0, _extendOwnJsDefault.default));
parcelHelpers.export(exports, "defaults", ()=>(0, _defaultsJsDefault.default));
parcelHelpers.export(exports, "create", ()=>(0, _createJsDefault.default));
parcelHelpers.export(exports, "clone", ()=>(0, _cloneJsDefault.default));
parcelHelpers.export(exports, "tap", ()=>(0, _tapJsDefault.default));
parcelHelpers.export(exports, "get", ()=>(0, _getJsDefault.default));
parcelHelpers.export(exports, "has", ()=>(0, _hasJsDefault.default));
parcelHelpers.export(exports, "mapObject", ()=>(0, _mapObjectJsDefault.default));
// Utility Functions
// -----------------
// A bit of a grab bag: Predicate-generating functions for use with filters and
// loops, string escaping and templating, create random numbers and unique ids,
// and functions that facilitate Underscore's chaining and iteration conventions.
parcelHelpers.export(exports, "identity", ()=>(0, _identityJsDefault.default));
parcelHelpers.export(exports, "constant", ()=>(0, _constantJsDefault.default));
parcelHelpers.export(exports, "noop", ()=>(0, _noopJsDefault.default));
parcelHelpers.export(exports, "toPath", ()=>(0, _toPathJsDefault.default));
parcelHelpers.export(exports, "property", ()=>(0, _propertyJsDefault.default));
parcelHelpers.export(exports, "propertyOf", ()=>(0, _propertyOfJsDefault.default));
parcelHelpers.export(exports, "matcher", ()=>(0, _matcherJsDefault.default));
parcelHelpers.export(exports, "matches", ()=>(0, _matcherJsDefault.default));
parcelHelpers.export(exports, "times", ()=>(0, _timesJsDefault.default));
parcelHelpers.export(exports, "random", ()=>(0, _randomJsDefault.default));
parcelHelpers.export(exports, "now", ()=>(0, _nowJsDefault.default));
parcelHelpers.export(exports, "escape", ()=>(0, _escapeJsDefault.default));
parcelHelpers.export(exports, "unescape", ()=>(0, _unescapeJsDefault.default));
parcelHelpers.export(exports, "templateSettings", ()=>(0, _templateSettingsJsDefault.default));
parcelHelpers.export(exports, "template", ()=>(0, _templateJsDefault.default));
parcelHelpers.export(exports, "result", ()=>(0, _resultJsDefault.default));
parcelHelpers.export(exports, "uniqueId", ()=>(0, _uniqueIdJsDefault.default));
parcelHelpers.export(exports, "chain", ()=>(0, _chainJsDefault.default));
parcelHelpers.export(exports, "iteratee", ()=>(0, _iterateeJsDefault.default));
// Function (ahem) Functions
// -------------------------
// These functions take a function as an argument and return a new function
// as the result. Also known as higher-order functions.
parcelHelpers.export(exports, "partial", ()=>(0, _partialJsDefault.default));
parcelHelpers.export(exports, "bind", ()=>(0, _bindJsDefault.default));
parcelHelpers.export(exports, "bindAll", ()=>(0, _bindAllJsDefault.default));
parcelHelpers.export(exports, "memoize", ()=>(0, _memoizeJsDefault.default));
parcelHelpers.export(exports, "delay", ()=>(0, _delayJsDefault.default));
parcelHelpers.export(exports, "defer", ()=>(0, _deferJsDefault.default));
parcelHelpers.export(exports, "throttle", ()=>(0, _throttleJsDefault.default));
parcelHelpers.export(exports, "debounce", ()=>(0, _debounceJsDefault.default));
parcelHelpers.export(exports, "wrap", ()=>(0, _wrapJsDefault.default));
parcelHelpers.export(exports, "negate", ()=>(0, _negateJsDefault.default));
parcelHelpers.export(exports, "compose", ()=>(0, _composeJsDefault.default));
parcelHelpers.export(exports, "after", ()=>(0, _afterJsDefault.default));
parcelHelpers.export(exports, "before", ()=>(0, _beforeJsDefault.default));
parcelHelpers.export(exports, "once", ()=>(0, _onceJsDefault.default));
// Finders
// -------
// Functions that extract (the position of) a single element from an object
// or array based on some criterion.
parcelHelpers.export(exports, "findKey", ()=>(0, _findKeyJsDefault.default));
parcelHelpers.export(exports, "findIndex", ()=>(0, _findIndexJsDefault.default));
parcelHelpers.export(exports, "findLastIndex", ()=>(0, _findLastIndexJsDefault.default));
parcelHelpers.export(exports, "sortedIndex", ()=>(0, _sortedIndexJsDefault.default));
parcelHelpers.export(exports, "indexOf", ()=>(0, _indexOfJsDefault.default));
parcelHelpers.export(exports, "lastIndexOf", ()=>(0, _lastIndexOfJsDefault.default));
parcelHelpers.export(exports, "find", ()=>(0, _findJsDefault.default));
parcelHelpers.export(exports, "detect", ()=>(0, _findJsDefault.default));
parcelHelpers.export(exports, "findWhere", ()=>(0, _findWhereJsDefault.default));
// Collection Functions
// --------------------
// Functions that work on any collection of elements: either an array, or
// an object of key-value pairs.
parcelHelpers.export(exports, "each", ()=>(0, _eachJsDefault.default));
parcelHelpers.export(exports, "forEach", ()=>(0, _eachJsDefault.default));
parcelHelpers.export(exports, "map", ()=>(0, _mapJsDefault.default));
parcelHelpers.export(exports, "collect", ()=>(0, _mapJsDefault.default));
parcelHelpers.export(exports, "reduce", ()=>(0, _reduceJsDefault.default));
parcelHelpers.export(exports, "foldl", ()=>(0, _reduceJsDefault.default));
parcelHelpers.export(exports, "inject", ()=>(0, _reduceJsDefault.default));
parcelHelpers.export(exports, "reduceRight", ()=>(0, _reduceRightJsDefault.default));
parcelHelpers.export(exports, "foldr", ()=>(0, _reduceRightJsDefault.default));
parcelHelpers.export(exports, "filter", ()=>(0, _filterJsDefault.default));
parcelHelpers.export(exports, "select", ()=>(0, _filterJsDefault.default));
parcelHelpers.export(exports, "reject", ()=>(0, _rejectJsDefault.default));
parcelHelpers.export(exports, "every", ()=>(0, _everyJsDefault.default));
parcelHelpers.export(exports, "all", ()=>(0, _everyJsDefault.default));
parcelHelpers.export(exports, "some", ()=>(0, _someJsDefault.default));
parcelHelpers.export(exports, "any", ()=>(0, _someJsDefault.default));
parcelHelpers.export(exports, "contains", ()=>(0, _containsJsDefault.default));
parcelHelpers.export(exports, "includes", ()=>(0, _containsJsDefault.default));
parcelHelpers.export(exports, "include", ()=>(0, _containsJsDefault.default));
parcelHelpers.export(exports, "invoke", ()=>(0, _invokeJsDefault.default));
parcelHelpers.export(exports, "pluck", ()=>(0, _pluckJsDefault.default));
parcelHelpers.export(exports, "where", ()=>(0, _whereJsDefault.default));
parcelHelpers.export(exports, "max", ()=>(0, _maxJsDefault.default));
parcelHelpers.export(exports, "min", ()=>(0, _minJsDefault.default));
parcelHelpers.export(exports, "shuffle", ()=>(0, _shuffleJsDefault.default));
parcelHelpers.export(exports, "sample", ()=>(0, _sampleJsDefault.default));
parcelHelpers.export(exports, "sortBy", ()=>(0, _sortByJsDefault.default));
parcelHelpers.export(exports, "groupBy", ()=>(0, _groupByJsDefault.default));
parcelHelpers.export(exports, "indexBy", ()=>(0, _indexByJsDefault.default));
parcelHelpers.export(exports, "countBy", ()=>(0, _countByJsDefault.default));
parcelHelpers.export(exports, "partition", ()=>(0, _partitionJsDefault.default));
parcelHelpers.export(exports, "toArray", ()=>(0, _toArrayJsDefault.default));
parcelHelpers.export(exports, "size", ()=>(0, _sizeJsDefault.default));
// `_.pick` and `_.omit` are actually object functions, but we put
// them here in order to create a more natural reading order in the
// monolithic build as they depend on `_.contains`.
parcelHelpers.export(exports, "pick", ()=>(0, _pickJsDefault.default));
parcelHelpers.export(exports, "omit", ()=>(0, _omitJsDefault.default));
// Array Functions
// ---------------
// Functions that operate on arrays (and array-likes) only, because they’re
// expressed in terms of operations on an ordered list of values.
parcelHelpers.export(exports, "first", ()=>(0, _firstJsDefault.default));
parcelHelpers.export(exports, "head", ()=>(0, _firstJsDefault.default));
parcelHelpers.export(exports, "take", ()=>(0, _firstJsDefault.default));
parcelHelpers.export(exports, "initial", ()=>(0, _initialJsDefault.default));
parcelHelpers.export(exports, "last", ()=>(0, _lastJsDefault.default));
parcelHelpers.export(exports, "rest", ()=>(0, _restJsDefault.default));
parcelHelpers.export(exports, "tail", ()=>(0, _restJsDefault.default));
parcelHelpers.export(exports, "drop", ()=>(0, _restJsDefault.default));
parcelHelpers.export(exports, "compact", ()=>(0, _compactJsDefault.default));
parcelHelpers.export(exports, "flatten", ()=>(0, _flattenJsDefault.default));
parcelHelpers.export(exports, "without", ()=>(0, _withoutJsDefault.default));
parcelHelpers.export(exports, "uniq", ()=>(0, _uniqJsDefault.default));
parcelHelpers.export(exports, "unique", ()=>(0, _uniqJsDefault.default));
parcelHelpers.export(exports, "union", ()=>(0, _unionJsDefault.default));
parcelHelpers.export(exports, "intersection", ()=>(0, _intersectionJsDefault.default));
parcelHelpers.export(exports, "difference", ()=>(0, _differenceJsDefault.default));
parcelHelpers.export(exports, "unzip", ()=>(0, _unzipJsDefault.default));
parcelHelpers.export(exports, "transpose", ()=>(0, _unzipJsDefault.default));
parcelHelpers.export(exports, "zip", ()=>(0, _zipJsDefault.default));
parcelHelpers.export(exports, "object", ()=>(0, _objectJsDefault.default));
parcelHelpers.export(exports, "range", ()=>(0, _rangeJsDefault.default));
parcelHelpers.export(exports, "chunk", ()=>(0, _chunkJsDefault.default));
// OOP
// ---
// These modules support the "object-oriented" calling style. See also
// `underscore.js` and `index-default.js`.
parcelHelpers.export(exports, "mixin", ()=>(0, _mixinJsDefault.default));
parcelHelpers.export(exports, "default", ()=>(0, _underscoreArrayMethodsJsDefault.default));
var _setupJs = require("./_setup.js");
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _isObjectJs = require("./isObject.js");
var _isObjectJsDefault = parcelHelpers.interopDefault(_isObjectJs);
var _isNullJs = require("./isNull.js");
var _isNullJsDefault = parcelHelpers.interopDefault(_isNullJs);
var _isUndefinedJs = require("./isUndefined.js");
var _isUndefinedJsDefault = parcelHelpers.interopDefault(_isUndefinedJs);
var _isBooleanJs = require("./isBoolean.js");
var _isBooleanJsDefault = parcelHelpers.interopDefault(_isBooleanJs);
var _isElementJs = require("./isElement.js");
var _isElementJsDefault = parcelHelpers.interopDefault(_isElementJs);
var _isStringJs = require("./isString.js");
var _isStringJsDefault = parcelHelpers.interopDefault(_isStringJs);
var _isNumberJs = require("./isNumber.js");
var _isNumberJsDefault = parcelHelpers.interopDefault(_isNumberJs);
var _isDateJs = require("./isDate.js");
var _isDateJsDefault = parcelHelpers.interopDefault(_isDateJs);
var _isRegExpJs = require("./isRegExp.js");
var _isRegExpJsDefault = parcelHelpers.interopDefault(_isRegExpJs);
var _isErrorJs = require("./isError.js");
var _isErrorJsDefault = parcelHelpers.interopDefault(_isErrorJs);
var _isSymbolJs = require("./isSymbol.js");
var _isSymbolJsDefault = parcelHelpers.interopDefault(_isSymbolJs);
var _isArrayBufferJs = require("./isArrayBuffer.js");
var _isArrayBufferJsDefault = parcelHelpers.interopDefault(_isArrayBufferJs);
var _isDataViewJs = require("./isDataView.js");
var _isDataViewJsDefault = parcelHelpers.interopDefault(_isDataViewJs);
var _isArrayJs = require("./isArray.js");
var _isArrayJsDefault = parcelHelpers.interopDefault(_isArrayJs);
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
var _isArgumentsJs = require("./isArguments.js");
var _isArgumentsJsDefault = parcelHelpers.interopDefault(_isArgumentsJs);
var _isFiniteJs = require("./isFinite.js");
var _isFiniteJsDefault = parcelHelpers.interopDefault(_isFiniteJs);
var _isNaNJs = require("./isNaN.js");
var _isNaNJsDefault = parcelHelpers.interopDefault(_isNaNJs);
var _isTypedArrayJs = require("./isTypedArray.js");
var _isTypedArrayJsDefault = parcelHelpers.interopDefault(_isTypedArrayJs);
var _isEmptyJs = require("./isEmpty.js");
var _isEmptyJsDefault = parcelHelpers.interopDefault(_isEmptyJs);
var _isMatchJs = require("./isMatch.js");
var _isMatchJsDefault = parcelHelpers.interopDefault(_isMatchJs);
var _isEqualJs = require("./isEqual.js");
var _isEqualJsDefault = parcelHelpers.interopDefault(_isEqualJs);
var _isMapJs = require("./isMap.js");
var _isMapJsDefault = parcelHelpers.interopDefault(_isMapJs);
var _isWeakMapJs = require("./isWeakMap.js");
var _isWeakMapJsDefault = parcelHelpers.interopDefault(_isWeakMapJs);
var _isSetJs = require("./isSet.js");
var _isSetJsDefault = parcelHelpers.interopDefault(_isSetJs);
var _isWeakSetJs = require("./isWeakSet.js");
var _isWeakSetJsDefault = parcelHelpers.interopDefault(_isWeakSetJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
var _allKeysJs = require("./allKeys.js");
var _allKeysJsDefault = parcelHelpers.interopDefault(_allKeysJs);
var _valuesJs = require("./values.js");
var _valuesJsDefault = parcelHelpers.interopDefault(_valuesJs);
var _pairsJs = require("./pairs.js");
var _pairsJsDefault = parcelHelpers.interopDefault(_pairsJs);
var _invertJs = require("./invert.js");
var _invertJsDefault = parcelHelpers.interopDefault(_invertJs);
var _functionsJs = require("./functions.js");
var _functionsJsDefault = parcelHelpers.interopDefault(_functionsJs);
var _extendJs = require("./extend.js");
var _extendJsDefault = parcelHelpers.interopDefault(_extendJs);
var _extendOwnJs = require("./extendOwn.js");
var _extendOwnJsDefault = parcelHelpers.interopDefault(_extendOwnJs);
var _defaultsJs = require("./defaults.js");
var _defaultsJsDefault = parcelHelpers.interopDefault(_defaultsJs);
var _createJs = require("./create.js");
var _createJsDefault = parcelHelpers.interopDefault(_createJs);
var _cloneJs = require("./clone.js");
var _cloneJsDefault = parcelHelpers.interopDefault(_cloneJs);
var _tapJs = require("./tap.js");
var _tapJsDefault = parcelHelpers.interopDefault(_tapJs);
var _getJs = require("./get.js");
var _getJsDefault = parcelHelpers.interopDefault(_getJs);
var _hasJs = require("./has.js");
var _hasJsDefault = parcelHelpers.interopDefault(_hasJs);
var _mapObjectJs = require("./mapObject.js");
var _mapObjectJsDefault = parcelHelpers.interopDefault(_mapObjectJs);
var _identityJs = require("./identity.js");
var _identityJsDefault = parcelHelpers.interopDefault(_identityJs);
var _constantJs = require("./constant.js");
var _constantJsDefault = parcelHelpers.interopDefault(_constantJs);
var _noopJs = require("./noop.js");
var _noopJsDefault = parcelHelpers.interopDefault(_noopJs);
var _toPathJs = require("./toPath.js");
var _toPathJsDefault = parcelHelpers.interopDefault(_toPathJs);
var _propertyJs = require("./property.js");
var _propertyJsDefault = parcelHelpers.interopDefault(_propertyJs);
var _propertyOfJs = require("./propertyOf.js");
var _propertyOfJsDefault = parcelHelpers.interopDefault(_propertyOfJs);
var _matcherJs = require("./matcher.js");
var _matcherJsDefault = parcelHelpers.interopDefault(_matcherJs);
var _timesJs = require("./times.js");
var _timesJsDefault = parcelHelpers.interopDefault(_timesJs);
var _randomJs = require("./random.js");
var _randomJsDefault = parcelHelpers.interopDefault(_randomJs);
var _nowJs = require("./now.js");
var _nowJsDefault = parcelHelpers.interopDefault(_nowJs);
var _escapeJs = require("./escape.js");
var _escapeJsDefault = parcelHelpers.interopDefault(_escapeJs);
var _unescapeJs = require("./unescape.js");
var _unescapeJsDefault = parcelHelpers.interopDefault(_unescapeJs);
var _templateSettingsJs = require("./templateSettings.js");
var _templateSettingsJsDefault = parcelHelpers.interopDefault(_templateSettingsJs);
var _templateJs = require("./template.js");
var _templateJsDefault = parcelHelpers.interopDefault(_templateJs);
var _resultJs = require("./result.js");
var _resultJsDefault = parcelHelpers.interopDefault(_resultJs);
var _uniqueIdJs = require("./uniqueId.js");
var _uniqueIdJsDefault = parcelHelpers.interopDefault(_uniqueIdJs);
var _chainJs = require("./chain.js");
var _chainJsDefault = parcelHelpers.interopDefault(_chainJs);
var _iterateeJs = require("./iteratee.js");
var _iterateeJsDefault = parcelHelpers.interopDefault(_iterateeJs);
var _partialJs = require("./partial.js");
var _partialJsDefault = parcelHelpers.interopDefault(_partialJs);
var _bindJs = require("./bind.js");
var _bindJsDefault = parcelHelpers.interopDefault(_bindJs);
var _bindAllJs = require("./bindAll.js");
var _bindAllJsDefault = parcelHelpers.interopDefault(_bindAllJs);
var _memoizeJs = require("./memoize.js");
var _memoizeJsDefault = parcelHelpers.interopDefault(_memoizeJs);
var _delayJs = require("./delay.js");
var _delayJsDefault = parcelHelpers.interopDefault(_delayJs);
var _deferJs = require("./defer.js");
var _deferJsDefault = parcelHelpers.interopDefault(_deferJs);
var _throttleJs = require("./throttle.js");
var _throttleJsDefault = parcelHelpers.interopDefault(_throttleJs);
var _debounceJs = require("./debounce.js");
var _debounceJsDefault = parcelHelpers.interopDefault(_debounceJs);
var _wrapJs = require("./wrap.js");
var _wrapJsDefault = parcelHelpers.interopDefault(_wrapJs);
var _negateJs = require("./negate.js");
var _negateJsDefault = parcelHelpers.interopDefault(_negateJs);
var _composeJs = require("./compose.js");
var _composeJsDefault = parcelHelpers.interopDefault(_composeJs);
var _afterJs = require("./after.js");
var _afterJsDefault = parcelHelpers.interopDefault(_afterJs);
var _beforeJs = require("./before.js");
var _beforeJsDefault = parcelHelpers.interopDefault(_beforeJs);
var _onceJs = require("./once.js");
var _onceJsDefault = parcelHelpers.interopDefault(_onceJs);
var _findKeyJs = require("./findKey.js");
var _findKeyJsDefault = parcelHelpers.interopDefault(_findKeyJs);
var _findIndexJs = require("./findIndex.js");
var _findIndexJsDefault = parcelHelpers.interopDefault(_findIndexJs);
var _findLastIndexJs = require("./findLastIndex.js");
var _findLastIndexJsDefault = parcelHelpers.interopDefault(_findLastIndexJs);
var _sortedIndexJs = require("./sortedIndex.js");
var _sortedIndexJsDefault = parcelHelpers.interopDefault(_sortedIndexJs);
var _indexOfJs = require("./indexOf.js");
var _indexOfJsDefault = parcelHelpers.interopDefault(_indexOfJs);
var _lastIndexOfJs = require("./lastIndexOf.js");
var _lastIndexOfJsDefault = parcelHelpers.interopDefault(_lastIndexOfJs);
var _findJs = require("./find.js");
var _findJsDefault = parcelHelpers.interopDefault(_findJs);
var _findWhereJs = require("./findWhere.js");
var _findWhereJsDefault = parcelHelpers.interopDefault(_findWhereJs);
var _eachJs = require("./each.js");
var _eachJsDefault = parcelHelpers.interopDefault(_eachJs);
var _mapJs = require("./map.js");
var _mapJsDefault = parcelHelpers.interopDefault(_mapJs);
var _reduceJs = require("./reduce.js");
var _reduceJsDefault = parcelHelpers.interopDefault(_reduceJs);
var _reduceRightJs = require("./reduceRight.js");
var _reduceRightJsDefault = parcelHelpers.interopDefault(_reduceRightJs);
var _filterJs = require("./filter.js");
var _filterJsDefault = parcelHelpers.interopDefault(_filterJs);
var _rejectJs = require("./reject.js");
var _rejectJsDefault = parcelHelpers.interopDefault(_rejectJs);
var _everyJs = require("./every.js");
var _everyJsDefault = parcelHelpers.interopDefault(_everyJs);
var _someJs = require("./some.js");
var _someJsDefault = parcelHelpers.interopDefault(_someJs);
var _containsJs = require("./contains.js");
var _containsJsDefault = parcelHelpers.interopDefault(_containsJs);
var _invokeJs = require("./invoke.js");
var _invokeJsDefault = parcelHelpers.interopDefault(_invokeJs);
var _pluckJs = require("./pluck.js");
var _pluckJsDefault = parcelHelpers.interopDefault(_pluckJs);
var _whereJs = require("./where.js");
var _whereJsDefault = parcelHelpers.interopDefault(_whereJs);
var _maxJs = require("./max.js");
var _maxJsDefault = parcelHelpers.interopDefault(_maxJs);
var _minJs = require("./min.js");
var _minJsDefault = parcelHelpers.interopDefault(_minJs);
var _shuffleJs = require("./shuffle.js");
var _shuffleJsDefault = parcelHelpers.interopDefault(_shuffleJs);
var _sampleJs = require("./sample.js");
var _sampleJsDefault = parcelHelpers.interopDefault(_sampleJs);
var _sortByJs = require("./sortBy.js");
var _sortByJsDefault = parcelHelpers.interopDefault(_sortByJs);
var _groupByJs = require("./groupBy.js");
var _groupByJsDefault = parcelHelpers.interopDefault(_groupByJs);
var _indexByJs = require("./indexBy.js");
var _indexByJsDefault = parcelHelpers.interopDefault(_indexByJs);
var _countByJs = require("./countBy.js");
var _countByJsDefault = parcelHelpers.interopDefault(_countByJs);
var _partitionJs = require("./partition.js");
var _partitionJsDefault = parcelHelpers.interopDefault(_partitionJs);
var _toArrayJs = require("./toArray.js");
var _toArrayJsDefault = parcelHelpers.interopDefault(_toArrayJs);
var _sizeJs = require("./size.js");
var _sizeJsDefault = parcelHelpers.interopDefault(_sizeJs);
var _pickJs = require("./pick.js");
var _pickJsDefault = parcelHelpers.interopDefault(_pickJs);
var _omitJs = require("./omit.js");
var _omitJsDefault = parcelHelpers.interopDefault(_omitJs);
var _firstJs = require("./first.js");
var _firstJsDefault = parcelHelpers.interopDefault(_firstJs);
var _initialJs = require("./initial.js");
var _initialJsDefault = parcelHelpers.interopDefault(_initialJs);
var _lastJs = require("./last.js");
var _lastJsDefault = parcelHelpers.interopDefault(_lastJs);
var _restJs = require("./rest.js");
var _restJsDefault = parcelHelpers.interopDefault(_restJs);
var _compactJs = require("./compact.js");
var _compactJsDefault = parcelHelpers.interopDefault(_compactJs);
var _flattenJs = require("./flatten.js");
var _flattenJsDefault = parcelHelpers.interopDefault(_flattenJs);
var _withoutJs = require("./without.js");
var _withoutJsDefault = parcelHelpers.interopDefault(_withoutJs);
var _uniqJs = require("./uniq.js");
var _uniqJsDefault = parcelHelpers.interopDefault(_uniqJs);
var _unionJs = require("./union.js");
var _unionJsDefault = parcelHelpers.interopDefault(_unionJs);
var _intersectionJs = require("./intersection.js");
var _intersectionJsDefault = parcelHelpers.interopDefault(_intersectionJs);
var _differenceJs = require("./difference.js");
var _differenceJsDefault = parcelHelpers.interopDefault(_differenceJs);
var _unzipJs = require("./unzip.js");
var _unzipJsDefault = parcelHelpers.interopDefault(_unzipJs);
var _zipJs = require("./zip.js");
var _zipJsDefault = parcelHelpers.interopDefault(_zipJs);
var _objectJs = require("./object.js");
var _objectJsDefault = parcelHelpers.interopDefault(_objectJs);
var _rangeJs = require("./range.js");
var _rangeJsDefault = parcelHelpers.interopDefault(_rangeJs);
var _chunkJs = require("./chunk.js");
var _chunkJsDefault = parcelHelpers.interopDefault(_chunkJs);
var _mixinJs = require("./mixin.js");
var _mixinJsDefault = parcelHelpers.interopDefault(_mixinJs);
var _underscoreArrayMethodsJs = require("./underscore-array-methods.js");
var _underscoreArrayMethodsJsDefault = parcelHelpers.interopDefault(_underscoreArrayMethodsJs);

},{"./_setup.js":"j1Opz","./restArguments.js":"iHiW5","./isObject.js":"jS3Se","./isNull.js":"3EF4i","./isUndefined.js":"76Kia","./isBoolean.js":"e6GFe","./isElement.js":"dhZbv","./isString.js":"h9vOY","./isNumber.js":"r54Wg","./isDate.js":"iDfv3","./isRegExp.js":"azfrs","./isError.js":"dkIl1","./isSymbol.js":"75NV6","./isArrayBuffer.js":"asmRo","./isDataView.js":"1t0pk","./isArray.js":"cth5N","./isFunction.js":"9XYGL","./isArguments.js":"dVyjs","./isFinite.js":"gKoss","./isNaN.js":"3QjxN","./isTypedArray.js":"6Wsfb","./isEmpty.js":"dK0Pq","./isMatch.js":"aIz4w","./isEqual.js":"cHWdl","./isMap.js":"k6Fdu","./isWeakMap.js":"ebF8O","./isSet.js":"Fl86y","./isWeakSet.js":"isH5L","./keys.js":"epVJ3","./allKeys.js":"iL9rU","./values.js":"1I2Yc","./pairs.js":"bdrSk","./invert.js":"1xVUE","./functions.js":"6kKwG","./extend.js":"3CC22","./extendOwn.js":"7Fpdj","./defaults.js":"2QZRH","./create.js":"27kIz","./clone.js":"9aJbO","./tap.js":"5KIUX","./get.js":"d7ATL","./has.js":"3CTQc","./mapObject.js":"eLKLX","./identity.js":"iCRMn","./constant.js":"6dl0q","./noop.js":"3qYXh","./toPath.js":"2926x","./property.js":"96pvf","./propertyOf.js":"iwYrg","./matcher.js":"3wGZ7","./times.js":"pyCYh","./random.js":"imiVs","./now.js":"aOx7w","./escape.js":"7w3y8","./unescape.js":"gmHHm","./templateSettings.js":"h5qH1","./template.js":"czkRN","./result.js":"4l1X6","./uniqueId.js":"arUrP","./chain.js":"jSwHe","./iteratee.js":"b93XD","./partial.js":"fLBUm","./bind.js":"kSGgn","./bindAll.js":"2htre","./memoize.js":"f9ZJj","./delay.js":"aIkq2","./defer.js":"8wSef","./throttle.js":"5FGQl","./debounce.js":"aVPiV","./wrap.js":"34WFJ","./negate.js":"juYC5","./compose.js":"f2NYc","./after.js":"7w1Ut","./before.js":"ezKMS","./once.js":"1RAuX","./findKey.js":"eLj2O","./findIndex.js":"cs9dN","./findLastIndex.js":"8rc9q","./sortedIndex.js":"ixTcB","./indexOf.js":"3FyCZ","./lastIndexOf.js":"7jQpU","./find.js":"lLtqo","./findWhere.js":"jhudI","./each.js":"fHmAz","./map.js":"1MqH5","./reduce.js":"bIw1c","./reduceRight.js":"2prZg","./filter.js":"5cyip","./reject.js":"2AJcx","./every.js":"7IzXu","./some.js":"dxzPe","./contains.js":"7u1gl","./invoke.js":"aHKqv","./pluck.js":"OekpZ","./where.js":"1GXcS","./max.js":"6g3ZY","./min.js":"9EXwL","./shuffle.js":"kl8WA","./sample.js":"8fNnf","./sortBy.js":"eCcLt","./groupBy.js":"k2aiT","./indexBy.js":"9VQiT","./countBy.js":"kNxCr","./partition.js":"bH0TP","./toArray.js":"7e7T1","./size.js":"88Tqj","./pick.js":"8ScJB","./omit.js":"6aykp","./first.js":"bNqM1","./initial.js":"cD91j","./last.js":"38Fqg","./rest.js":"aLSkH","./compact.js":"3coBb","./flatten.js":"gpF6L","./without.js":"ouhVw","./uniq.js":"kiHGM","./union.js":"k8pGG","./intersection.js":"iHUB6","./difference.js":"e9ASn","./unzip.js":"hyGGg","./zip.js":"lJw0p","./object.js":"bvlJI","./range.js":"43G11","./chunk.js":"57Gcn","./mixin.js":"enXfg","./underscore-array-methods.js":"k1JcM","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"j1Opz":[function(require,module,exports) {
// Current version.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "VERSION", ()=>VERSION);
parcelHelpers.export(exports, "root", ()=>root);
parcelHelpers.export(exports, "ArrayProto", ()=>ArrayProto);
parcelHelpers.export(exports, "ObjProto", ()=>ObjProto);
parcelHelpers.export(exports, "SymbolProto", ()=>SymbolProto);
parcelHelpers.export(exports, "push", ()=>push);
parcelHelpers.export(exports, "slice", ()=>slice);
parcelHelpers.export(exports, "toString", ()=>toString);
parcelHelpers.export(exports, "hasOwnProperty", ()=>hasOwnProperty);
parcelHelpers.export(exports, "supportsArrayBuffer", ()=>supportsArrayBuffer);
parcelHelpers.export(exports, "supportsDataView", ()=>supportsDataView);
parcelHelpers.export(exports, "nativeIsArray", ()=>nativeIsArray);
parcelHelpers.export(exports, "nativeKeys", ()=>nativeKeys);
parcelHelpers.export(exports, "nativeCreate", ()=>nativeCreate);
parcelHelpers.export(exports, "nativeIsView", ()=>nativeIsView);
parcelHelpers.export(exports, "_isNaN", ()=>_isNaN);
parcelHelpers.export(exports, "_isFinite", ()=>_isFinite);
parcelHelpers.export(exports, "hasEnumBug", ()=>hasEnumBug);
parcelHelpers.export(exports, "nonEnumerableProps", ()=>nonEnumerableProps);
parcelHelpers.export(exports, "MAX_ARRAY_INDEX", ()=>MAX_ARRAY_INDEX);
var global = arguments[3];
var VERSION = "1.13.6";
var root = typeof self == "object" && self.self === self && self || typeof global == "object" && global.global === global && global || Function("return this")() || {};
var ArrayProto = Array.prototype, ObjProto = Object.prototype;
var SymbolProto = typeof Symbol !== "undefined" ? Symbol.prototype : null;
var push = ArrayProto.push, slice = ArrayProto.slice, toString = ObjProto.toString, hasOwnProperty = ObjProto.hasOwnProperty;
var supportsArrayBuffer = typeof ArrayBuffer !== "undefined", supportsDataView = typeof DataView !== "undefined";
var nativeIsArray = Array.isArray, nativeKeys = Object.keys, nativeCreate = Object.create, nativeIsView = supportsArrayBuffer && ArrayBuffer.isView;
var _isNaN = isNaN, _isFinite = isFinite;
var hasEnumBug = !({
    toString: null
}).propertyIsEnumerable("toString");
var nonEnumerableProps = [
    "valueOf",
    "isPrototypeOf",
    "toString",
    "propertyIsEnumerable",
    "hasOwnProperty",
    "toLocaleString"
];
var MAX_ARRAY_INDEX = Math.pow(2, 53) - 1;

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"gkKU3":[function(require,module,exports) {
exports.interopDefault = function(a) {
    return a && a.__esModule ? a : {
        default: a
    };
};
exports.defineInteropFlag = function(a) {
    Object.defineProperty(a, "__esModule", {
        value: true
    });
};
exports.exportAll = function(source, dest) {
    Object.keys(source).forEach(function(key) {
        if (key === "default" || key === "__esModule" || dest.hasOwnProperty(key)) return;
        Object.defineProperty(dest, key, {
            enumerable: true,
            get: function() {
                return source[key];
            }
        });
    });
    return dest;
};
exports.export = function(dest, destName, get) {
    Object.defineProperty(dest, destName, {
        enumerable: true,
        get: get
    });
};

},{}],"iHiW5":[function(require,module,exports) {
// Some functions take a variable number of arguments, or a few expected
// arguments at the beginning and then a variable number of values to operate
// on. This helper accumulates all remaining arguments past the function’s
// argument length (or an explicit `startIndex`), into an array that becomes
// the last argument. Similar to ES6’s "rest parameter".
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>restArguments);
function restArguments(func, startIndex) {
    startIndex = startIndex == null ? func.length - 1 : +startIndex;
    return function() {
        var length = Math.max(arguments.length - startIndex, 0), rest = Array(length), index = 0;
        for(; index < length; index++)rest[index] = arguments[index + startIndex];
        switch(startIndex){
            case 0:
                return func.call(this, rest);
            case 1:
                return func.call(this, arguments[0], rest);
            case 2:
                return func.call(this, arguments[0], arguments[1], rest);
        }
        var args = Array(startIndex + 1);
        for(index = 0; index < startIndex; index++)args[index] = arguments[index];
        args[startIndex] = rest;
        return func.apply(this, args);
    };
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"jS3Se":[function(require,module,exports) {
// Is a given variable an object?
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>isObject);
function isObject(obj) {
    var type = typeof obj;
    return type === "function" || type === "object" && !!obj;
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"3EF4i":[function(require,module,exports) {
// Is a given value equal to null?
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>isNull);
function isNull(obj) {
    return obj === null;
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"76Kia":[function(require,module,exports) {
// Is a given variable undefined?
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>isUndefined);
function isUndefined(obj) {
    return obj === void 0;
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"e6GFe":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>isBoolean);
var _setupJs = require("./_setup.js");
function isBoolean(obj) {
    return obj === true || obj === false || (0, _setupJs.toString).call(obj) === "[object Boolean]";
}

},{"./_setup.js":"j1Opz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"dhZbv":[function(require,module,exports) {
// Is a given value a DOM element?
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>isElement);
function isElement(obj) {
    return !!(obj && obj.nodeType === 1);
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"h9vOY":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
exports.default = (0, _tagTesterJsDefault.default)("String");

},{"./_tagTester.js":"8zfWu","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"8zfWu":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>tagTester);
var _setupJs = require("./_setup.js");
function tagTester(name) {
    var tag = "[object " + name + "]";
    return function(obj) {
        return (0, _setupJs.toString).call(obj) === tag;
    };
}

},{"./_setup.js":"j1Opz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"r54Wg":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
exports.default = (0, _tagTesterJsDefault.default)("Number");

},{"./_tagTester.js":"8zfWu","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"iDfv3":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
exports.default = (0, _tagTesterJsDefault.default)("Date");

},{"./_tagTester.js":"8zfWu","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"azfrs":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
exports.default = (0, _tagTesterJsDefault.default)("RegExp");

},{"./_tagTester.js":"8zfWu","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"dkIl1":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
exports.default = (0, _tagTesterJsDefault.default)("Error");

},{"./_tagTester.js":"8zfWu","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"75NV6":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
exports.default = (0, _tagTesterJsDefault.default)("Symbol");

},{"./_tagTester.js":"8zfWu","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"asmRo":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
exports.default = (0, _tagTesterJsDefault.default)("ArrayBuffer");

},{"./_tagTester.js":"8zfWu","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"1t0pk":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
var _isArrayBufferJs = require("./isArrayBuffer.js");
var _isArrayBufferJsDefault = parcelHelpers.interopDefault(_isArrayBufferJs);
var _stringTagBugJs = require("./_stringTagBug.js");
var isDataView = (0, _tagTesterJsDefault.default)("DataView");
// In IE 10 - Edge 13, we need a different heuristic
// to determine whether an object is a `DataView`.
function ie10IsDataView(obj) {
    return obj != null && (0, _isFunctionJsDefault.default)(obj.getInt8) && (0, _isArrayBufferJsDefault.default)(obj.buffer);
}
exports.default = (0, _stringTagBugJs.hasStringTagBug) ? ie10IsDataView : isDataView;

},{"./_tagTester.js":"8zfWu","./isFunction.js":"9XYGL","./isArrayBuffer.js":"asmRo","./_stringTagBug.js":"2UGte","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"9XYGL":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
var _setupJs = require("./_setup.js");
var isFunction = (0, _tagTesterJsDefault.default)("Function");
// Optimize `isFunction` if appropriate. Work around some `typeof` bugs in old
// v8, IE 11 (#1621), Safari 8 (#1929), and PhantomJS (#2236).
var nodelist = (0, _setupJs.root).document && (0, _setupJs.root).document.childNodes;
if (typeof /./ != "function" && typeof Int8Array != "object" && typeof nodelist != "function") isFunction = function(obj) {
    return typeof obj == "function" || false;
};
exports.default = isFunction;

},{"./_tagTester.js":"8zfWu","./_setup.js":"j1Opz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"2UGte":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "hasStringTagBug", ()=>hasStringTagBug);
parcelHelpers.export(exports, "isIE11", ()=>isIE11);
var _setupJs = require("./_setup.js");
var _hasObjectTagJs = require("./_hasObjectTag.js");
var _hasObjectTagJsDefault = parcelHelpers.interopDefault(_hasObjectTagJs);
var hasStringTagBug = (0, _setupJs.supportsDataView) && (0, _hasObjectTagJsDefault.default)(new DataView(new ArrayBuffer(8))), isIE11 = typeof Map !== "undefined" && (0, _hasObjectTagJsDefault.default)(new Map);

},{"./_setup.js":"j1Opz","./_hasObjectTag.js":"EvdI9","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"EvdI9":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
exports.default = (0, _tagTesterJsDefault.default)("Object");

},{"./_tagTester.js":"8zfWu","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"cth5N":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _setupJs = require("./_setup.js");
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
// Is a given value an array?
// Delegates to ECMA5's native `Array.isArray`.
exports.default = (0, _setupJs.nativeIsArray) || (0, _tagTesterJsDefault.default)("Array");

},{"./_setup.js":"j1Opz","./_tagTester.js":"8zfWu","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"dVyjs":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
var _hasJs = require("./_has.js");
var _hasJsDefault = parcelHelpers.interopDefault(_hasJs);
var isArguments = (0, _tagTesterJsDefault.default)("Arguments");
// Define a fallback version of the method in browsers (ahem, IE < 9), where
// there isn't any inspectable "Arguments" type.
(function() {
    if (!isArguments(arguments)) isArguments = function(obj) {
        return (0, _hasJsDefault.default)(obj, "callee");
    };
})();
exports.default = isArguments;

},{"./_tagTester.js":"8zfWu","./_has.js":"500LZ","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"500LZ":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>has);
var _setupJs = require("./_setup.js");
function has(obj, key) {
    return obj != null && (0, _setupJs.hasOwnProperty).call(obj, key);
}

},{"./_setup.js":"j1Opz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"gKoss":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>isFinite);
var _setupJs = require("./_setup.js");
var _isSymbolJs = require("./isSymbol.js");
var _isSymbolJsDefault = parcelHelpers.interopDefault(_isSymbolJs);
function isFinite(obj) {
    return !(0, _isSymbolJsDefault.default)(obj) && (0, _setupJs._isFinite)(obj) && !isNaN(parseFloat(obj));
}

},{"./_setup.js":"j1Opz","./isSymbol.js":"75NV6","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"3QjxN":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>isNaN);
var _setupJs = require("./_setup.js");
var _isNumberJs = require("./isNumber.js");
var _isNumberJsDefault = parcelHelpers.interopDefault(_isNumberJs);
function isNaN(obj) {
    return (0, _isNumberJsDefault.default)(obj) && (0, _setupJs._isNaN)(obj);
}

},{"./_setup.js":"j1Opz","./isNumber.js":"r54Wg","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"6Wsfb":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _setupJs = require("./_setup.js");
var _isDataViewJs = require("./isDataView.js");
var _isDataViewJsDefault = parcelHelpers.interopDefault(_isDataViewJs);
var _constantJs = require("./constant.js");
var _constantJsDefault = parcelHelpers.interopDefault(_constantJs);
var _isBufferLikeJs = require("./_isBufferLike.js");
var _isBufferLikeJsDefault = parcelHelpers.interopDefault(_isBufferLikeJs);
// Is a given value a typed array?
var typedArrayPattern = /\[object ((I|Ui)nt(8|16|32)|Float(32|64)|Uint8Clamped|Big(I|Ui)nt64)Array\]/;
function isTypedArray(obj) {
    // `ArrayBuffer.isView` is the most future-proof, so use it when available.
    // Otherwise, fall back on the above regular expression.
    return (0, _setupJs.nativeIsView) ? (0, _setupJs.nativeIsView)(obj) && !(0, _isDataViewJsDefault.default)(obj) : (0, _isBufferLikeJsDefault.default)(obj) && typedArrayPattern.test((0, _setupJs.toString).call(obj));
}
exports.default = (0, _setupJs.supportsArrayBuffer) ? isTypedArray : (0, _constantJsDefault.default)(false);

},{"./_setup.js":"j1Opz","./isDataView.js":"1t0pk","./constant.js":"6dl0q","./_isBufferLike.js":"2tre8","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"6dl0q":[function(require,module,exports) {
// Predicate-generating function. Often useful outside of Underscore.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>constant);
function constant(value) {
    return function() {
        return value;
    };
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"2tre8":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _createSizePropertyCheckJs = require("./_createSizePropertyCheck.js");
var _createSizePropertyCheckJsDefault = parcelHelpers.interopDefault(_createSizePropertyCheckJs);
var _getByteLengthJs = require("./_getByteLength.js");
var _getByteLengthJsDefault = parcelHelpers.interopDefault(_getByteLengthJs);
// Internal helper to determine whether we should spend extensive checks against
// `ArrayBuffer` et al.
exports.default = (0, _createSizePropertyCheckJsDefault.default)((0, _getByteLengthJsDefault.default));

},{"./_createSizePropertyCheck.js":"3UmeP","./_getByteLength.js":"7bY8I","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"3UmeP":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>createSizePropertyCheck);
var _setupJs = require("./_setup.js");
function createSizePropertyCheck(getSizeProperty) {
    return function(collection) {
        var sizeProperty = getSizeProperty(collection);
        return typeof sizeProperty == "number" && sizeProperty >= 0 && sizeProperty <= (0, _setupJs.MAX_ARRAY_INDEX);
    };
}

},{"./_setup.js":"j1Opz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"7bY8I":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _shallowPropertyJs = require("./_shallowProperty.js");
var _shallowPropertyJsDefault = parcelHelpers.interopDefault(_shallowPropertyJs);
// Internal helper to obtain the `byteLength` property of an object.
exports.default = (0, _shallowPropertyJsDefault.default)("byteLength");

},{"./_shallowProperty.js":"8aNvb","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"8aNvb":[function(require,module,exports) {
// Internal helper to generate a function to obtain property `key` from `obj`.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>shallowProperty);
function shallowProperty(key) {
    return function(obj) {
        return obj == null ? void 0 : obj[key];
    };
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"dK0Pq":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>isEmpty);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
var _isArrayJs = require("./isArray.js");
var _isArrayJsDefault = parcelHelpers.interopDefault(_isArrayJs);
var _isStringJs = require("./isString.js");
var _isStringJsDefault = parcelHelpers.interopDefault(_isStringJs);
var _isArgumentsJs = require("./isArguments.js");
var _isArgumentsJsDefault = parcelHelpers.interopDefault(_isArgumentsJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function isEmpty(obj) {
    if (obj == null) return true;
    // Skip the more expensive `toString`-based type checks if `obj` has no
    // `.length`.
    var length = (0, _getLengthJsDefault.default)(obj);
    if (typeof length == "number" && ((0, _isArrayJsDefault.default)(obj) || (0, _isStringJsDefault.default)(obj) || (0, _isArgumentsJsDefault.default)(obj))) return length === 0;
    return (0, _getLengthJsDefault.default)((0, _keysJsDefault.default)(obj)) === 0;
}

},{"./_getLength.js":"cb0Fe","./isArray.js":"cth5N","./isString.js":"h9vOY","./isArguments.js":"dVyjs","./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"cb0Fe":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _shallowPropertyJs = require("./_shallowProperty.js");
var _shallowPropertyJsDefault = parcelHelpers.interopDefault(_shallowPropertyJs);
// Internal helper to obtain the `length` property of an object.
exports.default = (0, _shallowPropertyJsDefault.default)("length");

},{"./_shallowProperty.js":"8aNvb","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"epVJ3":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>keys);
var _isObjectJs = require("./isObject.js");
var _isObjectJsDefault = parcelHelpers.interopDefault(_isObjectJs);
var _setupJs = require("./_setup.js");
var _hasJs = require("./_has.js");
var _hasJsDefault = parcelHelpers.interopDefault(_hasJs);
var _collectNonEnumPropsJs = require("./_collectNonEnumProps.js");
var _collectNonEnumPropsJsDefault = parcelHelpers.interopDefault(_collectNonEnumPropsJs);
function keys(obj) {
    if (!(0, _isObjectJsDefault.default)(obj)) return [];
    if (0, _setupJs.nativeKeys) return (0, _setupJs.nativeKeys)(obj);
    var keys = [];
    for(var key in obj)if ((0, _hasJsDefault.default)(obj, key)) keys.push(key);
    // Ahem, IE < 9.
    if (0, _setupJs.hasEnumBug) (0, _collectNonEnumPropsJsDefault.default)(obj, keys);
    return keys;
}

},{"./isObject.js":"jS3Se","./_setup.js":"j1Opz","./_has.js":"500LZ","./_collectNonEnumProps.js":"50jyM","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"50jyM":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>collectNonEnumProps);
var _setupJs = require("./_setup.js");
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
var _hasJs = require("./_has.js");
var _hasJsDefault = parcelHelpers.interopDefault(_hasJs);
// Internal helper to create a simple lookup structure.
// `collectNonEnumProps` used to depend on `_.contains`, but this led to
// circular imports. `emulatedSet` is a one-off solution that only works for
// arrays of strings.
function emulatedSet(keys) {
    var hash = {};
    for(var l = keys.length, i = 0; i < l; ++i)hash[keys[i]] = true;
    return {
        contains: function(key) {
            return hash[key] === true;
        },
        push: function(key) {
            hash[key] = true;
            return keys.push(key);
        }
    };
}
function collectNonEnumProps(obj, keys) {
    keys = emulatedSet(keys);
    var nonEnumIdx = (0, _setupJs.nonEnumerableProps).length;
    var constructor = obj.constructor;
    var proto = (0, _isFunctionJsDefault.default)(constructor) && constructor.prototype || (0, _setupJs.ObjProto);
    // Constructor is a special case.
    var prop = "constructor";
    if ((0, _hasJsDefault.default)(obj, prop) && !keys.contains(prop)) keys.push(prop);
    while(nonEnumIdx--){
        prop = (0, _setupJs.nonEnumerableProps)[nonEnumIdx];
        if (prop in obj && obj[prop] !== proto[prop] && !keys.contains(prop)) keys.push(prop);
    }
}

},{"./_setup.js":"j1Opz","./isFunction.js":"9XYGL","./_has.js":"500LZ","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"aIz4w":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>isMatch);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function isMatch(object, attrs) {
    var _keys = (0, _keysJsDefault.default)(attrs), length = _keys.length;
    if (object == null) return !length;
    var obj = Object(object);
    for(var i = 0; i < length; i++){
        var key = _keys[i];
        if (attrs[key] !== obj[key] || !(key in obj)) return false;
    }
    return true;
}

},{"./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"cHWdl":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>isEqual);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
var _setupJs = require("./_setup.js");
var _getByteLengthJs = require("./_getByteLength.js");
var _getByteLengthJsDefault = parcelHelpers.interopDefault(_getByteLengthJs);
var _isTypedArrayJs = require("./isTypedArray.js");
var _isTypedArrayJsDefault = parcelHelpers.interopDefault(_isTypedArrayJs);
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
var _stringTagBugJs = require("./_stringTagBug.js");
var _isDataViewJs = require("./isDataView.js");
var _isDataViewJsDefault = parcelHelpers.interopDefault(_isDataViewJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
var _hasJs = require("./_has.js");
var _hasJsDefault = parcelHelpers.interopDefault(_hasJs);
var _toBufferViewJs = require("./_toBufferView.js");
var _toBufferViewJsDefault = parcelHelpers.interopDefault(_toBufferViewJs);
// We use this string twice, so give it a name for minification.
var tagDataView = "[object DataView]";
// Internal recursive comparison function for `_.isEqual`.
function eq(a, b, aStack, bStack) {
    // Identical objects are equal. `0 === -0`, but they aren't identical.
    // See the [Harmony `egal` proposal](https://wiki.ecmascript.org/doku.php?id=harmony:egal).
    if (a === b) return a !== 0 || 1 / a === 1 / b;
    // `null` or `undefined` only equal to itself (strict comparison).
    if (a == null || b == null) return false;
    // `NaN`s are equivalent, but non-reflexive.
    if (a !== a) return b !== b;
    // Exhaust primitive checks
    var type = typeof a;
    if (type !== "function" && type !== "object" && typeof b != "object") return false;
    return deepEq(a, b, aStack, bStack);
}
// Internal recursive comparison function for `_.isEqual`.
function deepEq(a, b, aStack, bStack) {
    // Unwrap any wrapped objects.
    if (a instanceof (0, _underscoreJsDefault.default)) a = a._wrapped;
    if (b instanceof (0, _underscoreJsDefault.default)) b = b._wrapped;
    // Compare `[[Class]]` names.
    var className = (0, _setupJs.toString).call(a);
    if (className !== (0, _setupJs.toString).call(b)) return false;
    // Work around a bug in IE 10 - Edge 13.
    if ((0, _stringTagBugJs.hasStringTagBug) && className == "[object Object]" && (0, _isDataViewJsDefault.default)(a)) {
        if (!(0, _isDataViewJsDefault.default)(b)) return false;
        className = tagDataView;
    }
    switch(className){
        // These types are compared by value.
        case "[object RegExp]":
        // RegExps are coerced to strings for comparison (Note: '' + /a/i === '/a/i')
        case "[object String]":
            // Primitives and their corresponding object wrappers are equivalent; thus, `"5"` is
            // equivalent to `new String("5")`.
            return "" + a === "" + b;
        case "[object Number]":
            // `NaN`s are equivalent, but non-reflexive.
            // Object(NaN) is equivalent to NaN.
            if (+a !== +a) return +b !== +b;
            // An `egal` comparison is performed for other numeric values.
            return +a === 0 ? 1 / +a === 1 / b : +a === +b;
        case "[object Date]":
        case "[object Boolean]":
            // Coerce dates and booleans to numeric primitive values. Dates are compared by their
            // millisecond representations. Note that invalid dates with millisecond representations
            // of `NaN` are not equivalent.
            return +a === +b;
        case "[object Symbol]":
            return (0, _setupJs.SymbolProto).valueOf.call(a) === (0, _setupJs.SymbolProto).valueOf.call(b);
        case "[object ArrayBuffer]":
        case tagDataView:
            // Coerce to typed array so we can fall through.
            return deepEq((0, _toBufferViewJsDefault.default)(a), (0, _toBufferViewJsDefault.default)(b), aStack, bStack);
    }
    var areArrays = className === "[object Array]";
    if (!areArrays && (0, _isTypedArrayJsDefault.default)(a)) {
        var byteLength = (0, _getByteLengthJsDefault.default)(a);
        if (byteLength !== (0, _getByteLengthJsDefault.default)(b)) return false;
        if (a.buffer === b.buffer && a.byteOffset === b.byteOffset) return true;
        areArrays = true;
    }
    if (!areArrays) {
        if (typeof a != "object" || typeof b != "object") return false;
        // Objects with different constructors are not equivalent, but `Object`s or `Array`s
        // from different frames are.
        var aCtor = a.constructor, bCtor = b.constructor;
        if (aCtor !== bCtor && !((0, _isFunctionJsDefault.default)(aCtor) && aCtor instanceof aCtor && (0, _isFunctionJsDefault.default)(bCtor) && bCtor instanceof bCtor) && "constructor" in a && "constructor" in b) return false;
    }
    // Assume equality for cyclic structures. The algorithm for detecting cyclic
    // structures is adapted from ES 5.1 section 15.12.3, abstract operation `JO`.
    // Initializing stack of traversed objects.
    // It's done here since we only need them for objects and arrays comparison.
    aStack = aStack || [];
    bStack = bStack || [];
    var length = aStack.length;
    while(length--){
        // Linear search. Performance is inversely proportional to the number of
        // unique nested structures.
        if (aStack[length] === a) return bStack[length] === b;
    }
    // Add the first object to the stack of traversed objects.
    aStack.push(a);
    bStack.push(b);
    // Recursively compare objects and arrays.
    if (areArrays) {
        // Compare array lengths to determine if a deep comparison is necessary.
        length = a.length;
        if (length !== b.length) return false;
        // Deep compare the contents, ignoring non-numeric properties.
        while(length--){
            if (!eq(a[length], b[length], aStack, bStack)) return false;
        }
    } else {
        // Deep compare objects.
        var _keys = (0, _keysJsDefault.default)(a), key;
        length = _keys.length;
        // Ensure that both objects contain the same number of properties before comparing deep equality.
        if ((0, _keysJsDefault.default)(b).length !== length) return false;
        while(length--){
            // Deep compare each member
            key = _keys[length];
            if (!((0, _hasJsDefault.default)(b, key) && eq(a[key], b[key], aStack, bStack))) return false;
        }
    }
    // Remove the first object from the stack of traversed objects.
    aStack.pop();
    bStack.pop();
    return true;
}
function isEqual(a, b) {
    return eq(a, b);
}

},{"./underscore.js":"cZn3h","./_setup.js":"j1Opz","./_getByteLength.js":"7bY8I","./isTypedArray.js":"6Wsfb","./isFunction.js":"9XYGL","./_stringTagBug.js":"2UGte","./isDataView.js":"1t0pk","./keys.js":"epVJ3","./_has.js":"500LZ","./_toBufferView.js":"kwSPW","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"cZn3h":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>_);
var _setupJs = require("./_setup.js");
function _(obj) {
    if (obj instanceof _) return obj;
    if (!(this instanceof _)) return new _(obj);
    this._wrapped = obj;
}
_.VERSION = (0, _setupJs.VERSION);
// Extracts the result from a wrapped and chained object.
_.prototype.value = function() {
    return this._wrapped;
};
// Provide unwrapping proxies for some methods used in engine operations
// such as arithmetic and JSON stringification.
_.prototype.valueOf = _.prototype.toJSON = _.prototype.value;
_.prototype.toString = function() {
    return String(this._wrapped);
};

},{"./_setup.js":"j1Opz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"kwSPW":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>toBufferView);
var _getByteLengthJs = require("./_getByteLength.js");
var _getByteLengthJsDefault = parcelHelpers.interopDefault(_getByteLengthJs);
function toBufferView(bufferSource) {
    return new Uint8Array(bufferSource.buffer || bufferSource, bufferSource.byteOffset || 0, (0, _getByteLengthJsDefault.default)(bufferSource));
}

},{"./_getByteLength.js":"7bY8I","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"k6Fdu":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
var _stringTagBugJs = require("./_stringTagBug.js");
var _methodFingerprintJs = require("./_methodFingerprint.js");
exports.default = (0, _stringTagBugJs.isIE11) ? (0, _methodFingerprintJs.ie11fingerprint)((0, _methodFingerprintJs.mapMethods)) : (0, _tagTesterJsDefault.default)("Map");

},{"./_tagTester.js":"8zfWu","./_stringTagBug.js":"2UGte","./_methodFingerprint.js":"c9ykx","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"c9ykx":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
// Since the regular `Object.prototype.toString` type tests don't work for
// some types in IE 11, we use a fingerprinting heuristic instead, based
// on the methods. It's not great, but it's the best we got.
// The fingerprint method lists are defined below.
parcelHelpers.export(exports, "ie11fingerprint", ()=>ie11fingerprint);
parcelHelpers.export(exports, "mapMethods", ()=>mapMethods);
parcelHelpers.export(exports, "weakMapMethods", ()=>weakMapMethods);
parcelHelpers.export(exports, "setMethods", ()=>setMethods);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
var _allKeysJs = require("./allKeys.js");
var _allKeysJsDefault = parcelHelpers.interopDefault(_allKeysJs);
function ie11fingerprint(methods) {
    var length = (0, _getLengthJsDefault.default)(methods);
    return function(obj) {
        if (obj == null) return false;
        // `Map`, `WeakMap` and `Set` have no enumerable keys.
        var keys = (0, _allKeysJsDefault.default)(obj);
        if ((0, _getLengthJsDefault.default)(keys)) return false;
        for(var i = 0; i < length; i++){
            if (!(0, _isFunctionJsDefault.default)(obj[methods[i]])) return false;
        }
        // If we are testing against `WeakMap`, we need to ensure that
        // `obj` doesn't have a `forEach` method in order to distinguish
        // it from a regular `Map`.
        return methods !== weakMapMethods || !(0, _isFunctionJsDefault.default)(obj[forEachName]);
    };
}
// In the interest of compact minification, we write
// each string in the fingerprints only once.
var forEachName = "forEach", hasName = "has", commonInit = [
    "clear",
    "delete"
], mapTail = [
    "get",
    hasName,
    "set"
];
var mapMethods = commonInit.concat(forEachName, mapTail), weakMapMethods = commonInit.concat(mapTail), setMethods = [
    "add"
].concat(commonInit, forEachName, hasName);

},{"./_getLength.js":"cb0Fe","./isFunction.js":"9XYGL","./allKeys.js":"iL9rU","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"iL9rU":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>allKeys);
var _isObjectJs = require("./isObject.js");
var _isObjectJsDefault = parcelHelpers.interopDefault(_isObjectJs);
var _setupJs = require("./_setup.js");
var _collectNonEnumPropsJs = require("./_collectNonEnumProps.js");
var _collectNonEnumPropsJsDefault = parcelHelpers.interopDefault(_collectNonEnumPropsJs);
function allKeys(obj) {
    if (!(0, _isObjectJsDefault.default)(obj)) return [];
    var keys = [];
    for(var key in obj)keys.push(key);
    // Ahem, IE < 9.
    if (0, _setupJs.hasEnumBug) (0, _collectNonEnumPropsJsDefault.default)(obj, keys);
    return keys;
}

},{"./isObject.js":"jS3Se","./_setup.js":"j1Opz","./_collectNonEnumProps.js":"50jyM","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"ebF8O":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
var _stringTagBugJs = require("./_stringTagBug.js");
var _methodFingerprintJs = require("./_methodFingerprint.js");
exports.default = (0, _stringTagBugJs.isIE11) ? (0, _methodFingerprintJs.ie11fingerprint)((0, _methodFingerprintJs.weakMapMethods)) : (0, _tagTesterJsDefault.default)("WeakMap");

},{"./_tagTester.js":"8zfWu","./_stringTagBug.js":"2UGte","./_methodFingerprint.js":"c9ykx","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"Fl86y":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
var _stringTagBugJs = require("./_stringTagBug.js");
var _methodFingerprintJs = require("./_methodFingerprint.js");
exports.default = (0, _stringTagBugJs.isIE11) ? (0, _methodFingerprintJs.ie11fingerprint)((0, _methodFingerprintJs.setMethods)) : (0, _tagTesterJsDefault.default)("Set");

},{"./_tagTester.js":"8zfWu","./_stringTagBug.js":"2UGte","./_methodFingerprint.js":"c9ykx","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"isH5L":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _tagTesterJs = require("./_tagTester.js");
var _tagTesterJsDefault = parcelHelpers.interopDefault(_tagTesterJs);
exports.default = (0, _tagTesterJsDefault.default)("WeakSet");

},{"./_tagTester.js":"8zfWu","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"1I2Yc":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>values);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function values(obj) {
    var _keys = (0, _keysJsDefault.default)(obj);
    var length = _keys.length;
    var values = Array(length);
    for(var i = 0; i < length; i++)values[i] = obj[_keys[i]];
    return values;
}

},{"./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"bdrSk":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>pairs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function pairs(obj) {
    var _keys = (0, _keysJsDefault.default)(obj);
    var length = _keys.length;
    var pairs = Array(length);
    for(var i = 0; i < length; i++)pairs[i] = [
        _keys[i],
        obj[_keys[i]]
    ];
    return pairs;
}

},{"./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"1xVUE":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>invert);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function invert(obj) {
    var result = {};
    var _keys = (0, _keysJsDefault.default)(obj);
    for(var i = 0, length = _keys.length; i < length; i++)result[obj[_keys[i]]] = _keys[i];
    return result;
}

},{"./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"6kKwG":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>functions);
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
function functions(obj) {
    var names = [];
    for(var key in obj)if ((0, _isFunctionJsDefault.default)(obj[key])) names.push(key);
    return names.sort();
}

},{"./isFunction.js":"9XYGL","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"3CC22":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _createAssignerJs = require("./_createAssigner.js");
var _createAssignerJsDefault = parcelHelpers.interopDefault(_createAssignerJs);
var _allKeysJs = require("./allKeys.js");
var _allKeysJsDefault = parcelHelpers.interopDefault(_allKeysJs);
// Extend a given object with all the properties in passed-in object(s).
exports.default = (0, _createAssignerJsDefault.default)((0, _allKeysJsDefault.default));

},{"./_createAssigner.js":"eDRTj","./allKeys.js":"iL9rU","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"eDRTj":[function(require,module,exports) {
// An internal function for creating assigner functions.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>createAssigner);
function createAssigner(keysFunc, defaults) {
    return function(obj) {
        var length = arguments.length;
        if (defaults) obj = Object(obj);
        if (length < 2 || obj == null) return obj;
        for(var index = 1; index < length; index++){
            var source = arguments[index], keys = keysFunc(source), l = keys.length;
            for(var i = 0; i < l; i++){
                var key = keys[i];
                if (!defaults || obj[key] === void 0) obj[key] = source[key];
            }
        }
        return obj;
    };
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"7Fpdj":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _createAssignerJs = require("./_createAssigner.js");
var _createAssignerJsDefault = parcelHelpers.interopDefault(_createAssignerJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
// Assigns a given object with all the own properties in the passed-in
// object(s).
// (https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Object/assign)
exports.default = (0, _createAssignerJsDefault.default)((0, _keysJsDefault.default));

},{"./_createAssigner.js":"eDRTj","./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"2QZRH":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _createAssignerJs = require("./_createAssigner.js");
var _createAssignerJsDefault = parcelHelpers.interopDefault(_createAssignerJs);
var _allKeysJs = require("./allKeys.js");
var _allKeysJsDefault = parcelHelpers.interopDefault(_allKeysJs);
// Fill in a given object with default properties.
exports.default = (0, _createAssignerJsDefault.default)((0, _allKeysJsDefault.default), true);

},{"./_createAssigner.js":"eDRTj","./allKeys.js":"iL9rU","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"27kIz":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>create);
var _baseCreateJs = require("./_baseCreate.js");
var _baseCreateJsDefault = parcelHelpers.interopDefault(_baseCreateJs);
var _extendOwnJs = require("./extendOwn.js");
var _extendOwnJsDefault = parcelHelpers.interopDefault(_extendOwnJs);
function create(prototype, props) {
    var result = (0, _baseCreateJsDefault.default)(prototype);
    if (props) (0, _extendOwnJsDefault.default)(result, props);
    return result;
}

},{"./_baseCreate.js":"4BZA8","./extendOwn.js":"7Fpdj","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"4BZA8":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>baseCreate);
var _isObjectJs = require("./isObject.js");
var _isObjectJsDefault = parcelHelpers.interopDefault(_isObjectJs);
var _setupJs = require("./_setup.js");
// Create a naked function reference for surrogate-prototype-swapping.
function ctor() {
    return function() {};
}
function baseCreate(prototype) {
    if (!(0, _isObjectJsDefault.default)(prototype)) return {};
    if (0, _setupJs.nativeCreate) return (0, _setupJs.nativeCreate)(prototype);
    var Ctor = ctor();
    Ctor.prototype = prototype;
    var result = new Ctor;
    Ctor.prototype = null;
    return result;
}

},{"./isObject.js":"jS3Se","./_setup.js":"j1Opz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"9aJbO":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>clone);
var _isObjectJs = require("./isObject.js");
var _isObjectJsDefault = parcelHelpers.interopDefault(_isObjectJs);
var _isArrayJs = require("./isArray.js");
var _isArrayJsDefault = parcelHelpers.interopDefault(_isArrayJs);
var _extendJs = require("./extend.js");
var _extendJsDefault = parcelHelpers.interopDefault(_extendJs);
function clone(obj) {
    if (!(0, _isObjectJsDefault.default)(obj)) return obj;
    return (0, _isArrayJsDefault.default)(obj) ? obj.slice() : (0, _extendJsDefault.default)({}, obj);
}

},{"./isObject.js":"jS3Se","./isArray.js":"cth5N","./extend.js":"3CC22","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"5KIUX":[function(require,module,exports) {
// Invokes `interceptor` with the `obj` and then returns `obj`.
// The primary purpose of this method is to "tap into" a method chain, in
// order to perform operations on intermediate results within the chain.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>tap);
function tap(obj, interceptor) {
    interceptor(obj);
    return obj;
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"d7ATL":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>get);
var _toPathJs = require("./_toPath.js");
var _toPathJsDefault = parcelHelpers.interopDefault(_toPathJs);
var _deepGetJs = require("./_deepGet.js");
var _deepGetJsDefault = parcelHelpers.interopDefault(_deepGetJs);
var _isUndefinedJs = require("./isUndefined.js");
var _isUndefinedJsDefault = parcelHelpers.interopDefault(_isUndefinedJs);
function get(object, path, defaultValue) {
    var value = (0, _deepGetJsDefault.default)(object, (0, _toPathJsDefault.default)(path));
    return (0, _isUndefinedJsDefault.default)(value) ? defaultValue : value;
}

},{"./_toPath.js":"fQeyr","./_deepGet.js":"4yNnp","./isUndefined.js":"76Kia","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"fQeyr":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>toPath);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
var _toPathJs = require("./toPath.js");
function toPath(path) {
    return (0, _underscoreJsDefault.default).toPath(path);
}

},{"./underscore.js":"cZn3h","./toPath.js":"2926x","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"2926x":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>toPath);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
var _isArrayJs = require("./isArray.js");
var _isArrayJsDefault = parcelHelpers.interopDefault(_isArrayJs);
function toPath(path) {
    return (0, _isArrayJsDefault.default)(path) ? path : [
        path
    ];
}
(0, _underscoreJsDefault.default).toPath = toPath;

},{"./underscore.js":"cZn3h","./isArray.js":"cth5N","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"4yNnp":[function(require,module,exports) {
// Internal function to obtain a nested property in `obj` along `path`.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>deepGet);
function deepGet(obj, path) {
    var length = path.length;
    for(var i = 0; i < length; i++){
        if (obj == null) return void 0;
        obj = obj[path[i]];
    }
    return length ? obj : void 0;
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"3CTQc":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>has);
var _hasJs = require("./_has.js");
var _hasJsDefault = parcelHelpers.interopDefault(_hasJs);
var _toPathJs = require("./_toPath.js");
var _toPathJsDefault = parcelHelpers.interopDefault(_toPathJs);
function has(obj, path) {
    path = (0, _toPathJsDefault.default)(path);
    var length = path.length;
    for(var i = 0; i < length; i++){
        var key = path[i];
        if (!(0, _hasJsDefault.default)(obj, key)) return false;
        obj = obj[key];
    }
    return !!length;
}

},{"./_has.js":"500LZ","./_toPath.js":"fQeyr","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"eLKLX":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>mapObject);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function mapObject(obj, iteratee, context) {
    iteratee = (0, _cbJsDefault.default)(iteratee, context);
    var _keys = (0, _keysJsDefault.default)(obj), length = _keys.length, results = {};
    for(var index = 0; index < length; index++){
        var currentKey = _keys[index];
        results[currentKey] = iteratee(obj[currentKey], currentKey, obj);
    }
    return results;
}

},{"./_cb.js":"hwRTD","./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"hwRTD":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>cb);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
var _baseIterateeJs = require("./_baseIteratee.js");
var _baseIterateeJsDefault = parcelHelpers.interopDefault(_baseIterateeJs);
var _iterateeJs = require("./iteratee.js");
var _iterateeJsDefault = parcelHelpers.interopDefault(_iterateeJs);
function cb(value, context, argCount) {
    if ((0, _underscoreJsDefault.default).iteratee !== (0, _iterateeJsDefault.default)) return (0, _underscoreJsDefault.default).iteratee(value, context);
    return (0, _baseIterateeJsDefault.default)(value, context, argCount);
}

},{"./underscore.js":"cZn3h","./_baseIteratee.js":"8cF3R","./iteratee.js":"b93XD","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"8cF3R":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>baseIteratee);
var _identityJs = require("./identity.js");
var _identityJsDefault = parcelHelpers.interopDefault(_identityJs);
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
var _isObjectJs = require("./isObject.js");
var _isObjectJsDefault = parcelHelpers.interopDefault(_isObjectJs);
var _isArrayJs = require("./isArray.js");
var _isArrayJsDefault = parcelHelpers.interopDefault(_isArrayJs);
var _matcherJs = require("./matcher.js");
var _matcherJsDefault = parcelHelpers.interopDefault(_matcherJs);
var _propertyJs = require("./property.js");
var _propertyJsDefault = parcelHelpers.interopDefault(_propertyJs);
var _optimizeCbJs = require("./_optimizeCb.js");
var _optimizeCbJsDefault = parcelHelpers.interopDefault(_optimizeCbJs);
function baseIteratee(value, context, argCount) {
    if (value == null) return 0, _identityJsDefault.default;
    if ((0, _isFunctionJsDefault.default)(value)) return (0, _optimizeCbJsDefault.default)(value, context, argCount);
    if ((0, _isObjectJsDefault.default)(value) && !(0, _isArrayJsDefault.default)(value)) return (0, _matcherJsDefault.default)(value);
    return (0, _propertyJsDefault.default)(value);
}

},{"./identity.js":"iCRMn","./isFunction.js":"9XYGL","./isObject.js":"jS3Se","./isArray.js":"cth5N","./matcher.js":"3wGZ7","./property.js":"96pvf","./_optimizeCb.js":"ib91j","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"iCRMn":[function(require,module,exports) {
// Keep the identity function around for default iteratees.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>identity);
function identity(value) {
    return value;
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"3wGZ7":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>matcher);
var _extendOwnJs = require("./extendOwn.js");
var _extendOwnJsDefault = parcelHelpers.interopDefault(_extendOwnJs);
var _isMatchJs = require("./isMatch.js");
var _isMatchJsDefault = parcelHelpers.interopDefault(_isMatchJs);
function matcher(attrs) {
    attrs = (0, _extendOwnJsDefault.default)({}, attrs);
    return function(obj) {
        return (0, _isMatchJsDefault.default)(obj, attrs);
    };
}

},{"./extendOwn.js":"7Fpdj","./isMatch.js":"aIz4w","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"96pvf":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>property);
var _deepGetJs = require("./_deepGet.js");
var _deepGetJsDefault = parcelHelpers.interopDefault(_deepGetJs);
var _toPathJs = require("./_toPath.js");
var _toPathJsDefault = parcelHelpers.interopDefault(_toPathJs);
function property(path) {
    path = (0, _toPathJsDefault.default)(path);
    return function(obj) {
        return (0, _deepGetJsDefault.default)(obj, path);
    };
}

},{"./_deepGet.js":"4yNnp","./_toPath.js":"fQeyr","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"ib91j":[function(require,module,exports) {
// Internal function that returns an efficient (for current engines) version
// of the passed-in callback, to be repeatedly applied in other Underscore
// functions.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>optimizeCb);
function optimizeCb(func, context, argCount) {
    if (context === void 0) return func;
    switch(argCount == null ? 3 : argCount){
        case 1:
            return function(value) {
                return func.call(context, value);
            };
        // The 2-argument case is omitted because we’re not using it.
        case 3:
            return function(value, index, collection) {
                return func.call(context, value, index, collection);
            };
        case 4:
            return function(accumulator, value, index, collection) {
                return func.call(context, accumulator, value, index, collection);
            };
    }
    return function() {
        return func.apply(context, arguments);
    };
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"b93XD":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>iteratee);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
var _baseIterateeJs = require("./_baseIteratee.js");
var _baseIterateeJsDefault = parcelHelpers.interopDefault(_baseIterateeJs);
function iteratee(value, context) {
    return (0, _baseIterateeJsDefault.default)(value, context, Infinity);
}
(0, _underscoreJsDefault.default).iteratee = iteratee;

},{"./underscore.js":"cZn3h","./_baseIteratee.js":"8cF3R","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"3qYXh":[function(require,module,exports) {
// Predicate-generating function. Often useful outside of Underscore.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>noop);
function noop() {}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"iwYrg":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>propertyOf);
var _noopJs = require("./noop.js");
var _noopJsDefault = parcelHelpers.interopDefault(_noopJs);
var _getJs = require("./get.js");
var _getJsDefault = parcelHelpers.interopDefault(_getJs);
function propertyOf(obj) {
    if (obj == null) return 0, _noopJsDefault.default;
    return function(path) {
        return (0, _getJsDefault.default)(obj, path);
    };
}

},{"./noop.js":"3qYXh","./get.js":"d7ATL","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"pyCYh":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>times);
var _optimizeCbJs = require("./_optimizeCb.js");
var _optimizeCbJsDefault = parcelHelpers.interopDefault(_optimizeCbJs);
function times(n, iteratee, context) {
    var accum = Array(Math.max(0, n));
    iteratee = (0, _optimizeCbJsDefault.default)(iteratee, context, 1);
    for(var i = 0; i < n; i++)accum[i] = iteratee(i);
    return accum;
}

},{"./_optimizeCb.js":"ib91j","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"imiVs":[function(require,module,exports) {
// Return a random integer between `min` and `max` (inclusive).
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>random);
function random(min, max) {
    if (max == null) {
        max = min;
        min = 0;
    }
    return min + Math.floor(Math.random() * (max - min + 1));
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"aOx7w":[function(require,module,exports) {
// A (possibly faster) way to get the current timestamp as an integer.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
exports.default = Date.now || function() {
    return new Date().getTime();
};

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"7w3y8":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _createEscaperJs = require("./_createEscaper.js");
var _createEscaperJsDefault = parcelHelpers.interopDefault(_createEscaperJs);
var _escapeMapJs = require("./_escapeMap.js");
var _escapeMapJsDefault = parcelHelpers.interopDefault(_escapeMapJs);
// Function for escaping strings to HTML interpolation.
exports.default = (0, _createEscaperJsDefault.default)((0, _escapeMapJsDefault.default));

},{"./_createEscaper.js":"5bjMZ","./_escapeMap.js":"71n9D","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"5bjMZ":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>createEscaper);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function createEscaper(map) {
    var escaper = function(match) {
        return map[match];
    };
    // Regexes for identifying a key that needs to be escaped.
    var source = "(?:" + (0, _keysJsDefault.default)(map).join("|") + ")";
    var testRegexp = RegExp(source);
    var replaceRegexp = RegExp(source, "g");
    return function(string) {
        string = string == null ? "" : "" + string;
        return testRegexp.test(string) ? string.replace(replaceRegexp, escaper) : string;
    };
}

},{"./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"71n9D":[function(require,module,exports) {
// Internal list of HTML entities for escaping.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
exports.default = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#x27;",
    "`": "&#x60;"
};

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"gmHHm":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _createEscaperJs = require("./_createEscaper.js");
var _createEscaperJsDefault = parcelHelpers.interopDefault(_createEscaperJs);
var _unescapeMapJs = require("./_unescapeMap.js");
var _unescapeMapJsDefault = parcelHelpers.interopDefault(_unescapeMapJs);
// Function for unescaping strings from HTML interpolation.
exports.default = (0, _createEscaperJsDefault.default)((0, _unescapeMapJsDefault.default));

},{"./_createEscaper.js":"5bjMZ","./_unescapeMap.js":"21Nyc","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"21Nyc":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _invertJs = require("./invert.js");
var _invertJsDefault = parcelHelpers.interopDefault(_invertJs);
var _escapeMapJs = require("./_escapeMap.js");
var _escapeMapJsDefault = parcelHelpers.interopDefault(_escapeMapJs);
// Internal list of HTML entities for unescaping.
exports.default = (0, _invertJsDefault.default)((0, _escapeMapJsDefault.default));

},{"./invert.js":"1xVUE","./_escapeMap.js":"71n9D","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"h5qH1":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
// By default, Underscore uses ERB-style template delimiters. Change the
// following template settings to use alternative delimiters.
exports.default = (0, _underscoreJsDefault.default).templateSettings = {
    evaluate: /<%([\s\S]+?)%>/g,
    interpolate: /<%=([\s\S]+?)%>/g,
    escape: /<%-([\s\S]+?)%>/g
};

},{"./underscore.js":"cZn3h","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"czkRN":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>template);
var _defaultsJs = require("./defaults.js");
var _defaultsJsDefault = parcelHelpers.interopDefault(_defaultsJs);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
var _templateSettingsJs = require("./templateSettings.js");
// When customizing `_.templateSettings`, if you don't want to define an
// interpolation, evaluation or escaping regex, we need one that is
// guaranteed not to match.
var noMatch = /(.)^/;
// Certain characters need to be escaped so that they can be put into a
// string literal.
var escapes = {
    "'": "'",
    "\\": "\\",
    "\r": "r",
    "\n": "n",
    "\u2028": "u2028",
    "\u2029": "u2029"
};
var escapeRegExp = /\\|'|\r|\n|\u2028|\u2029/g;
function escapeChar(match) {
    return "\\" + escapes[match];
}
// In order to prevent third-party code injection through
// `_.templateSettings.variable`, we test it against the following regular
// expression. It is intentionally a bit more liberal than just matching valid
// identifiers, but still prevents possible loopholes through defaults or
// destructuring assignment.
var bareIdentifier = /^\s*(\w|\$)+\s*$/;
function template(text, settings, oldSettings) {
    if (!settings && oldSettings) settings = oldSettings;
    settings = (0, _defaultsJsDefault.default)({}, settings, (0, _underscoreJsDefault.default).templateSettings);
    // Combine delimiters into one regular expression via alternation.
    var matcher = RegExp([
        (settings.escape || noMatch).source,
        (settings.interpolate || noMatch).source,
        (settings.evaluate || noMatch).source
    ].join("|") + "|$", "g");
    // Compile the template source, escaping string literals appropriately.
    var index = 0;
    var source = "__p+='";
    text.replace(matcher, function(match, escape, interpolate, evaluate, offset) {
        source += text.slice(index, offset).replace(escapeRegExp, escapeChar);
        index = offset + match.length;
        if (escape) source += "'+\n((__t=(" + escape + "))==null?'':_.escape(__t))+\n'";
        else if (interpolate) source += "'+\n((__t=(" + interpolate + "))==null?'':__t)+\n'";
        else if (evaluate) source += "';\n" + evaluate + "\n__p+='";
        // Adobe VMs need the match returned to produce the correct offset.
        return match;
    });
    source += "';\n";
    var argument = settings.variable;
    if (argument) {
        // Insure against third-party code injection. (CVE-2021-23358)
        if (!bareIdentifier.test(argument)) throw new Error("variable is not a bare identifier: " + argument);
    } else {
        // If a variable is not specified, place data values in local scope.
        source = "with(obj||{}){\n" + source + "}\n";
        argument = "obj";
    }
    source = "var __t,__p='',__j=Array.prototype.join,print=function(){__p+=__j.call(arguments,'');};\n" + source + "return __p;\n";
    var render;
    try {
        render = new Function(argument, "_", source);
    } catch (e) {
        e.source = source;
        throw e;
    }
    var template = function(data) {
        return render.call(this, data, (0, _underscoreJsDefault.default));
    };
    // Provide the compiled source as a convenience for precompilation.
    template.source = "function(" + argument + "){\n" + source + "}";
    return template;
}

},{"./defaults.js":"2QZRH","./underscore.js":"cZn3h","./templateSettings.js":"h5qH1","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"4l1X6":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>result);
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
var _toPathJs = require("./_toPath.js");
var _toPathJsDefault = parcelHelpers.interopDefault(_toPathJs);
function result(obj, path, fallback) {
    path = (0, _toPathJsDefault.default)(path);
    var length = path.length;
    if (!length) return (0, _isFunctionJsDefault.default)(fallback) ? fallback.call(obj) : fallback;
    for(var i = 0; i < length; i++){
        var prop = obj == null ? void 0 : obj[path[i]];
        if (prop === void 0) {
            prop = fallback;
            i = length; // Ensure we don't continue iterating.
        }
        obj = (0, _isFunctionJsDefault.default)(prop) ? prop.call(obj) : prop;
    }
    return obj;
}

},{"./isFunction.js":"9XYGL","./_toPath.js":"fQeyr","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"arUrP":[function(require,module,exports) {
// Generate a unique integer id (unique within the entire client session).
// Useful for temporary DOM ids.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>uniqueId);
var idCounter = 0;
function uniqueId(prefix) {
    var id = ++idCounter + "";
    return prefix ? prefix + id : id;
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"jSwHe":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>chain);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
function chain(obj) {
    var instance = (0, _underscoreJsDefault.default)(obj);
    instance._chain = true;
    return instance;
}

},{"./underscore.js":"cZn3h","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"fLBUm":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _executeBoundJs = require("./_executeBound.js");
var _executeBoundJsDefault = parcelHelpers.interopDefault(_executeBoundJs);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
// Partially apply a function by creating a version that has had some of its
// arguments pre-filled, without changing its dynamic `this` context. `_` acts
// as a placeholder by default, allowing any combination of arguments to be
// pre-filled. Set `_.partial.placeholder` for a custom placeholder argument.
var partial = (0, _restArgumentsJsDefault.default)(function(func, boundArgs) {
    var placeholder = partial.placeholder;
    var bound = function() {
        var position = 0, length = boundArgs.length;
        var args = Array(length);
        for(var i = 0; i < length; i++)args[i] = boundArgs[i] === placeholder ? arguments[position++] : boundArgs[i];
        while(position < arguments.length)args.push(arguments[position++]);
        return (0, _executeBoundJsDefault.default)(func, bound, this, this, args);
    };
    return bound;
});
partial.placeholder = (0, _underscoreJsDefault.default);
exports.default = partial;

},{"./restArguments.js":"iHiW5","./_executeBound.js":"9uJKk","./underscore.js":"cZn3h","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"9uJKk":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>executeBound);
var _baseCreateJs = require("./_baseCreate.js");
var _baseCreateJsDefault = parcelHelpers.interopDefault(_baseCreateJs);
var _isObjectJs = require("./isObject.js");
var _isObjectJsDefault = parcelHelpers.interopDefault(_isObjectJs);
function executeBound(sourceFunc, boundFunc, context, callingContext, args) {
    if (!(callingContext instanceof boundFunc)) return sourceFunc.apply(context, args);
    var self = (0, _baseCreateJsDefault.default)(sourceFunc.prototype);
    var result = sourceFunc.apply(self, args);
    if ((0, _isObjectJsDefault.default)(result)) return result;
    return self;
}

},{"./_baseCreate.js":"4BZA8","./isObject.js":"jS3Se","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"kSGgn":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
var _executeBoundJs = require("./_executeBound.js");
var _executeBoundJsDefault = parcelHelpers.interopDefault(_executeBoundJs);
// Create a function bound to a given object (assigning `this`, and arguments,
// optionally).
exports.default = (0, _restArgumentsJsDefault.default)(function(func, context, args) {
    if (!(0, _isFunctionJsDefault.default)(func)) throw new TypeError("Bind must be called on a function");
    var bound = (0, _restArgumentsJsDefault.default)(function(callArgs) {
        return (0, _executeBoundJsDefault.default)(func, bound, context, this, args.concat(callArgs));
    });
    return bound;
});

},{"./restArguments.js":"iHiW5","./isFunction.js":"9XYGL","./_executeBound.js":"9uJKk","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"2htre":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _flattenJs = require("./_flatten.js");
var _flattenJsDefault = parcelHelpers.interopDefault(_flattenJs);
var _bindJs = require("./bind.js");
var _bindJsDefault = parcelHelpers.interopDefault(_bindJs);
// Bind a number of an object's methods to that object. Remaining arguments
// are the method names to be bound. Useful for ensuring that all callbacks
// defined on an object belong to it.
exports.default = (0, _restArgumentsJsDefault.default)(function(obj, keys) {
    keys = (0, _flattenJsDefault.default)(keys, false, false);
    var index = keys.length;
    if (index < 1) throw new Error("bindAll must be passed function names");
    while(index--){
        var key = keys[index];
        obj[key] = (0, _bindJsDefault.default)(obj[key], obj);
    }
    return obj;
});

},{"./restArguments.js":"iHiW5","./_flatten.js":"kRaRq","./bind.js":"kSGgn","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"kRaRq":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>flatten);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _isArrayJs = require("./isArray.js");
var _isArrayJsDefault = parcelHelpers.interopDefault(_isArrayJs);
var _isArgumentsJs = require("./isArguments.js");
var _isArgumentsJsDefault = parcelHelpers.interopDefault(_isArgumentsJs);
function flatten(input, depth, strict, output) {
    output = output || [];
    if (!depth && depth !== 0) depth = Infinity;
    else if (depth <= 0) return output.concat(input);
    var idx = output.length;
    for(var i = 0, length = (0, _getLengthJsDefault.default)(input); i < length; i++){
        var value = input[i];
        if ((0, _isArrayLikeJsDefault.default)(value) && ((0, _isArrayJsDefault.default)(value) || (0, _isArgumentsJsDefault.default)(value))) {
            // Flatten current level of array or arguments object.
            if (depth > 1) {
                flatten(value, depth - 1, strict, output);
                idx = output.length;
            } else {
                var j = 0, len = value.length;
                while(j < len)output[idx++] = value[j++];
            }
        } else if (!strict) output[idx++] = value;
    }
    return output;
}

},{"./_getLength.js":"cb0Fe","./_isArrayLike.js":"7w1Hu","./isArray.js":"cth5N","./isArguments.js":"dVyjs","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"7w1Hu":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _createSizePropertyCheckJs = require("./_createSizePropertyCheck.js");
var _createSizePropertyCheckJsDefault = parcelHelpers.interopDefault(_createSizePropertyCheckJs);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
// Internal helper for collection methods to determine whether a collection
// should be iterated as an array or as an object.
// Related: https://people.mozilla.org/~jorendorff/es6-draft.html#sec-tolength
// Avoids a very nasty iOS 8 JIT bug on ARM-64. #2094
exports.default = (0, _createSizePropertyCheckJsDefault.default)((0, _getLengthJsDefault.default));

},{"./_createSizePropertyCheck.js":"3UmeP","./_getLength.js":"cb0Fe","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"f9ZJj":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>memoize);
var _hasJs = require("./_has.js");
var _hasJsDefault = parcelHelpers.interopDefault(_hasJs);
function memoize(func, hasher) {
    var memoize = function(key) {
        var cache = memoize.cache;
        var address = "" + (hasher ? hasher.apply(this, arguments) : key);
        if (!(0, _hasJsDefault.default)(cache, address)) cache[address] = func.apply(this, arguments);
        return cache[address];
    };
    memoize.cache = {};
    return memoize;
}

},{"./_has.js":"500LZ","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"aIkq2":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
// Delays a function for the given number of milliseconds, and then calls
// it with the arguments supplied.
exports.default = (0, _restArgumentsJsDefault.default)(function(func, wait, args) {
    return setTimeout(function() {
        return func.apply(null, args);
    }, wait);
});

},{"./restArguments.js":"iHiW5","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"8wSef":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _partialJs = require("./partial.js");
var _partialJsDefault = parcelHelpers.interopDefault(_partialJs);
var _delayJs = require("./delay.js");
var _delayJsDefault = parcelHelpers.interopDefault(_delayJs);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
// Defers a function, scheduling it to run after the current call stack has
// cleared.
exports.default = (0, _partialJsDefault.default)((0, _delayJsDefault.default), (0, _underscoreJsDefault.default), 1);

},{"./partial.js":"fLBUm","./delay.js":"aIkq2","./underscore.js":"cZn3h","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"5FGQl":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>throttle);
var _nowJs = require("./now.js");
var _nowJsDefault = parcelHelpers.interopDefault(_nowJs);
function throttle(func, wait, options) {
    var timeout, context, args, result;
    var previous = 0;
    if (!options) options = {};
    var later = function() {
        previous = options.leading === false ? 0 : (0, _nowJsDefault.default)();
        timeout = null;
        result = func.apply(context, args);
        if (!timeout) context = args = null;
    };
    var throttled = function() {
        var _now = (0, _nowJsDefault.default)();
        if (!previous && options.leading === false) previous = _now;
        var remaining = wait - (_now - previous);
        context = this;
        args = arguments;
        if (remaining <= 0 || remaining > wait) {
            if (timeout) {
                clearTimeout(timeout);
                timeout = null;
            }
            previous = _now;
            result = func.apply(context, args);
            if (!timeout) context = args = null;
        } else if (!timeout && options.trailing !== false) timeout = setTimeout(later, remaining);
        return result;
    };
    throttled.cancel = function() {
        clearTimeout(timeout);
        previous = 0;
        timeout = context = args = null;
    };
    return throttled;
}

},{"./now.js":"aOx7w","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"aVPiV":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>debounce);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _nowJs = require("./now.js");
var _nowJsDefault = parcelHelpers.interopDefault(_nowJs);
function debounce(func, wait, immediate) {
    var timeout, previous, args, result, context;
    var later = function() {
        var passed = (0, _nowJsDefault.default)() - previous;
        if (wait > passed) timeout = setTimeout(later, wait - passed);
        else {
            timeout = null;
            if (!immediate) result = func.apply(context, args);
            // This check is needed because `func` can recursively invoke `debounced`.
            if (!timeout) args = context = null;
        }
    };
    var debounced = (0, _restArgumentsJsDefault.default)(function(_args) {
        context = this;
        args = _args;
        previous = (0, _nowJsDefault.default)();
        if (!timeout) {
            timeout = setTimeout(later, wait);
            if (immediate) result = func.apply(context, args);
        }
        return result;
    });
    debounced.cancel = function() {
        clearTimeout(timeout);
        timeout = args = context = null;
    };
    return debounced;
}

},{"./restArguments.js":"iHiW5","./now.js":"aOx7w","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"34WFJ":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>wrap);
var _partialJs = require("./partial.js");
var _partialJsDefault = parcelHelpers.interopDefault(_partialJs);
function wrap(func, wrapper) {
    return (0, _partialJsDefault.default)(wrapper, func);
}

},{"./partial.js":"fLBUm","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"juYC5":[function(require,module,exports) {
// Returns a negated version of the passed-in predicate.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>negate);
function negate(predicate) {
    return function() {
        return !predicate.apply(this, arguments);
    };
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"f2NYc":[function(require,module,exports) {
// Returns a function that is the composition of a list of functions, each
// consuming the return value of the function that follows.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>compose);
function compose() {
    var args = arguments;
    var start = args.length - 1;
    return function() {
        var i = start;
        var result = args[start].apply(this, arguments);
        while(i--)result = args[i].call(this, result);
        return result;
    };
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"7w1Ut":[function(require,module,exports) {
// Returns a function that will only be executed on and after the Nth call.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>after);
function after(times, func) {
    return function() {
        if (--times < 1) return func.apply(this, arguments);
    };
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"ezKMS":[function(require,module,exports) {
// Returns a function that will only be executed up to (but not including) the
// Nth call.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>before);
function before(times, func) {
    var memo;
    return function() {
        if (--times > 0) memo = func.apply(this, arguments);
        if (times <= 1) func = null;
        return memo;
    };
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"1RAuX":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _partialJs = require("./partial.js");
var _partialJsDefault = parcelHelpers.interopDefault(_partialJs);
var _beforeJs = require("./before.js");
var _beforeJsDefault = parcelHelpers.interopDefault(_beforeJs);
// Returns a function that will be executed at most one time, no matter how
// often you call it. Useful for lazy initialization.
exports.default = (0, _partialJsDefault.default)((0, _beforeJsDefault.default), 2);

},{"./partial.js":"fLBUm","./before.js":"ezKMS","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"eLj2O":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>findKey);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function findKey(obj, predicate, context) {
    predicate = (0, _cbJsDefault.default)(predicate, context);
    var _keys = (0, _keysJsDefault.default)(obj), key;
    for(var i = 0, length = _keys.length; i < length; i++){
        key = _keys[i];
        if (predicate(obj[key], key, obj)) return key;
    }
}

},{"./_cb.js":"hwRTD","./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"cs9dN":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _createPredicateIndexFinderJs = require("./_createPredicateIndexFinder.js");
var _createPredicateIndexFinderJsDefault = parcelHelpers.interopDefault(_createPredicateIndexFinderJs);
// Returns the first index on an array-like that passes a truth test.
exports.default = (0, _createPredicateIndexFinderJsDefault.default)(1);

},{"./_createPredicateIndexFinder.js":"MoeMM","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"MoeMM":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>createPredicateIndexFinder);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
function createPredicateIndexFinder(dir) {
    return function(array, predicate, context) {
        predicate = (0, _cbJsDefault.default)(predicate, context);
        var length = (0, _getLengthJsDefault.default)(array);
        var index = dir > 0 ? 0 : length - 1;
        for(; index >= 0 && index < length; index += dir){
            if (predicate(array[index], index, array)) return index;
        }
        return -1;
    };
}

},{"./_cb.js":"hwRTD","./_getLength.js":"cb0Fe","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"8rc9q":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _createPredicateIndexFinderJs = require("./_createPredicateIndexFinder.js");
var _createPredicateIndexFinderJsDefault = parcelHelpers.interopDefault(_createPredicateIndexFinderJs);
// Returns the last index on an array-like that passes a truth test.
exports.default = (0, _createPredicateIndexFinderJsDefault.default)(-1);

},{"./_createPredicateIndexFinder.js":"MoeMM","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"ixTcB":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>sortedIndex);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
function sortedIndex(array, obj, iteratee, context) {
    iteratee = (0, _cbJsDefault.default)(iteratee, context, 1);
    var value = iteratee(obj);
    var low = 0, high = (0, _getLengthJsDefault.default)(array);
    while(low < high){
        var mid = Math.floor((low + high) / 2);
        if (iteratee(array[mid]) < value) low = mid + 1;
        else high = mid;
    }
    return low;
}

},{"./_cb.js":"hwRTD","./_getLength.js":"cb0Fe","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"3FyCZ":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _sortedIndexJs = require("./sortedIndex.js");
var _sortedIndexJsDefault = parcelHelpers.interopDefault(_sortedIndexJs);
var _findIndexJs = require("./findIndex.js");
var _findIndexJsDefault = parcelHelpers.interopDefault(_findIndexJs);
var _createIndexFinderJs = require("./_createIndexFinder.js");
var _createIndexFinderJsDefault = parcelHelpers.interopDefault(_createIndexFinderJs);
// Return the position of the first occurrence of an item in an array,
// or -1 if the item is not included in the array.
// If the array is large and already in sort order, pass `true`
// for **isSorted** to use binary search.
exports.default = (0, _createIndexFinderJsDefault.default)(1, (0, _findIndexJsDefault.default), (0, _sortedIndexJsDefault.default));

},{"./sortedIndex.js":"ixTcB","./findIndex.js":"cs9dN","./_createIndexFinder.js":"7sDEF","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"7sDEF":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>createIndexFinder);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
var _setupJs = require("./_setup.js");
var _isNaNJs = require("./isNaN.js");
var _isNaNJsDefault = parcelHelpers.interopDefault(_isNaNJs);
function createIndexFinder(dir, predicateFind, sortedIndex) {
    return function(array, item, idx) {
        var i = 0, length = (0, _getLengthJsDefault.default)(array);
        if (typeof idx == "number") {
            if (dir > 0) i = idx >= 0 ? idx : Math.max(idx + length, i);
            else length = idx >= 0 ? Math.min(idx + 1, length) : idx + length + 1;
        } else if (sortedIndex && idx && length) {
            idx = sortedIndex(array, item);
            return array[idx] === item ? idx : -1;
        }
        if (item !== item) {
            idx = predicateFind((0, _setupJs.slice).call(array, i, length), (0, _isNaNJsDefault.default));
            return idx >= 0 ? idx + i : -1;
        }
        for(idx = dir > 0 ? i : length - 1; idx >= 0 && idx < length; idx += dir){
            if (array[idx] === item) return idx;
        }
        return -1;
    };
}

},{"./_getLength.js":"cb0Fe","./_setup.js":"j1Opz","./isNaN.js":"3QjxN","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"7jQpU":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _findLastIndexJs = require("./findLastIndex.js");
var _findLastIndexJsDefault = parcelHelpers.interopDefault(_findLastIndexJs);
var _createIndexFinderJs = require("./_createIndexFinder.js");
var _createIndexFinderJsDefault = parcelHelpers.interopDefault(_createIndexFinderJs);
// Return the position of the last occurrence of an item in an array,
// or -1 if the item is not included in the array.
exports.default = (0, _createIndexFinderJsDefault.default)(-1, (0, _findLastIndexJsDefault.default));

},{"./findLastIndex.js":"8rc9q","./_createIndexFinder.js":"7sDEF","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"lLtqo":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>find);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _findIndexJs = require("./findIndex.js");
var _findIndexJsDefault = parcelHelpers.interopDefault(_findIndexJs);
var _findKeyJs = require("./findKey.js");
var _findKeyJsDefault = parcelHelpers.interopDefault(_findKeyJs);
function find(obj, predicate, context) {
    var keyFinder = (0, _isArrayLikeJsDefault.default)(obj) ? (0, _findIndexJsDefault.default) : (0, _findKeyJsDefault.default);
    var key = keyFinder(obj, predicate, context);
    if (key !== void 0 && key !== -1) return obj[key];
}

},{"./_isArrayLike.js":"7w1Hu","./findIndex.js":"cs9dN","./findKey.js":"eLj2O","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"jhudI":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>findWhere);
var _findJs = require("./find.js");
var _findJsDefault = parcelHelpers.interopDefault(_findJs);
var _matcherJs = require("./matcher.js");
var _matcherJsDefault = parcelHelpers.interopDefault(_matcherJs);
function findWhere(obj, attrs) {
    return (0, _findJsDefault.default)(obj, (0, _matcherJsDefault.default)(attrs));
}

},{"./find.js":"lLtqo","./matcher.js":"3wGZ7","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"fHmAz":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>each);
var _optimizeCbJs = require("./_optimizeCb.js");
var _optimizeCbJsDefault = parcelHelpers.interopDefault(_optimizeCbJs);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function each(obj, iteratee, context) {
    iteratee = (0, _optimizeCbJsDefault.default)(iteratee, context);
    var i, length;
    if ((0, _isArrayLikeJsDefault.default)(obj)) for(i = 0, length = obj.length; i < length; i++)iteratee(obj[i], i, obj);
    else {
        var _keys = (0, _keysJsDefault.default)(obj);
        for(i = 0, length = _keys.length; i < length; i++)iteratee(obj[_keys[i]], _keys[i], obj);
    }
    return obj;
}

},{"./_optimizeCb.js":"ib91j","./_isArrayLike.js":"7w1Hu","./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"1MqH5":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>map);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function map(obj, iteratee, context) {
    iteratee = (0, _cbJsDefault.default)(iteratee, context);
    var _keys = !(0, _isArrayLikeJsDefault.default)(obj) && (0, _keysJsDefault.default)(obj), length = (_keys || obj).length, results = Array(length);
    for(var index = 0; index < length; index++){
        var currentKey = _keys ? _keys[index] : index;
        results[index] = iteratee(obj[currentKey], currentKey, obj);
    }
    return results;
}

},{"./_cb.js":"hwRTD","./_isArrayLike.js":"7w1Hu","./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"bIw1c":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _createReduceJs = require("./_createReduce.js");
var _createReduceJsDefault = parcelHelpers.interopDefault(_createReduceJs);
// **Reduce** builds up a single result from a list of values, aka `inject`,
// or `foldl`.
exports.default = (0, _createReduceJsDefault.default)(1);

},{"./_createReduce.js":"8GuPA","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"8GuPA":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>createReduce);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
var _optimizeCbJs = require("./_optimizeCb.js");
var _optimizeCbJsDefault = parcelHelpers.interopDefault(_optimizeCbJs);
function createReduce(dir) {
    // Wrap code that reassigns argument variables in a separate function than
    // the one that accesses `arguments.length` to avoid a perf hit. (#1991)
    var reducer = function(obj, iteratee, memo, initial) {
        var _keys = !(0, _isArrayLikeJsDefault.default)(obj) && (0, _keysJsDefault.default)(obj), length = (_keys || obj).length, index = dir > 0 ? 0 : length - 1;
        if (!initial) {
            memo = obj[_keys ? _keys[index] : index];
            index += dir;
        }
        for(; index >= 0 && index < length; index += dir){
            var currentKey = _keys ? _keys[index] : index;
            memo = iteratee(memo, obj[currentKey], currentKey, obj);
        }
        return memo;
    };
    return function(obj, iteratee, memo, context) {
        var initial = arguments.length >= 3;
        return reducer(obj, (0, _optimizeCbJsDefault.default)(iteratee, context, 4), memo, initial);
    };
}

},{"./_isArrayLike.js":"7w1Hu","./keys.js":"epVJ3","./_optimizeCb.js":"ib91j","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"2prZg":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _createReduceJs = require("./_createReduce.js");
var _createReduceJsDefault = parcelHelpers.interopDefault(_createReduceJs);
// The right-associative version of reduce, also known as `foldr`.
exports.default = (0, _createReduceJsDefault.default)(-1);

},{"./_createReduce.js":"8GuPA","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"5cyip":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>filter);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _eachJs = require("./each.js");
var _eachJsDefault = parcelHelpers.interopDefault(_eachJs);
function filter(obj, predicate, context) {
    var results = [];
    predicate = (0, _cbJsDefault.default)(predicate, context);
    (0, _eachJsDefault.default)(obj, function(value, index, list) {
        if (predicate(value, index, list)) results.push(value);
    });
    return results;
}

},{"./_cb.js":"hwRTD","./each.js":"fHmAz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"2AJcx":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>reject);
var _filterJs = require("./filter.js");
var _filterJsDefault = parcelHelpers.interopDefault(_filterJs);
var _negateJs = require("./negate.js");
var _negateJsDefault = parcelHelpers.interopDefault(_negateJs);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
function reject(obj, predicate, context) {
    return (0, _filterJsDefault.default)(obj, (0, _negateJsDefault.default)((0, _cbJsDefault.default)(predicate)), context);
}

},{"./filter.js":"5cyip","./negate.js":"juYC5","./_cb.js":"hwRTD","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"7IzXu":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>every);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function every(obj, predicate, context) {
    predicate = (0, _cbJsDefault.default)(predicate, context);
    var _keys = !(0, _isArrayLikeJsDefault.default)(obj) && (0, _keysJsDefault.default)(obj), length = (_keys || obj).length;
    for(var index = 0; index < length; index++){
        var currentKey = _keys ? _keys[index] : index;
        if (!predicate(obj[currentKey], currentKey, obj)) return false;
    }
    return true;
}

},{"./_cb.js":"hwRTD","./_isArrayLike.js":"7w1Hu","./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"dxzPe":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>some);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function some(obj, predicate, context) {
    predicate = (0, _cbJsDefault.default)(predicate, context);
    var _keys = !(0, _isArrayLikeJsDefault.default)(obj) && (0, _keysJsDefault.default)(obj), length = (_keys || obj).length;
    for(var index = 0; index < length; index++){
        var currentKey = _keys ? _keys[index] : index;
        if (predicate(obj[currentKey], currentKey, obj)) return true;
    }
    return false;
}

},{"./_cb.js":"hwRTD","./_isArrayLike.js":"7w1Hu","./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"7u1gl":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>contains);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _valuesJs = require("./values.js");
var _valuesJsDefault = parcelHelpers.interopDefault(_valuesJs);
var _indexOfJs = require("./indexOf.js");
var _indexOfJsDefault = parcelHelpers.interopDefault(_indexOfJs);
function contains(obj, item, fromIndex, guard) {
    if (!(0, _isArrayLikeJsDefault.default)(obj)) obj = (0, _valuesJsDefault.default)(obj);
    if (typeof fromIndex != "number" || guard) fromIndex = 0;
    return (0, _indexOfJsDefault.default)(obj, item, fromIndex) >= 0;
}

},{"./_isArrayLike.js":"7w1Hu","./values.js":"1I2Yc","./indexOf.js":"3FyCZ","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"aHKqv":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
var _mapJs = require("./map.js");
var _mapJsDefault = parcelHelpers.interopDefault(_mapJs);
var _deepGetJs = require("./_deepGet.js");
var _deepGetJsDefault = parcelHelpers.interopDefault(_deepGetJs);
var _toPathJs = require("./_toPath.js");
var _toPathJsDefault = parcelHelpers.interopDefault(_toPathJs);
// Invoke a method (with arguments) on every item in a collection.
exports.default = (0, _restArgumentsJsDefault.default)(function(obj, path, args) {
    var contextPath, func;
    if ((0, _isFunctionJsDefault.default)(path)) func = path;
    else {
        path = (0, _toPathJsDefault.default)(path);
        contextPath = path.slice(0, -1);
        path = path[path.length - 1];
    }
    return (0, _mapJsDefault.default)(obj, function(context) {
        var method = func;
        if (!method) {
            if (contextPath && contextPath.length) context = (0, _deepGetJsDefault.default)(context, contextPath);
            if (context == null) return void 0;
            method = context[path];
        }
        return method == null ? method : method.apply(context, args);
    });
});

},{"./restArguments.js":"iHiW5","./isFunction.js":"9XYGL","./map.js":"1MqH5","./_deepGet.js":"4yNnp","./_toPath.js":"fQeyr","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"OekpZ":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>pluck);
var _mapJs = require("./map.js");
var _mapJsDefault = parcelHelpers.interopDefault(_mapJs);
var _propertyJs = require("./property.js");
var _propertyJsDefault = parcelHelpers.interopDefault(_propertyJs);
function pluck(obj, key) {
    return (0, _mapJsDefault.default)(obj, (0, _propertyJsDefault.default)(key));
}

},{"./map.js":"1MqH5","./property.js":"96pvf","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"1GXcS":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>where);
var _filterJs = require("./filter.js");
var _filterJsDefault = parcelHelpers.interopDefault(_filterJs);
var _matcherJs = require("./matcher.js");
var _matcherJsDefault = parcelHelpers.interopDefault(_matcherJs);
function where(obj, attrs) {
    return (0, _filterJsDefault.default)(obj, (0, _matcherJsDefault.default)(attrs));
}

},{"./filter.js":"5cyip","./matcher.js":"3wGZ7","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"6g3ZY":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>max);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _valuesJs = require("./values.js");
var _valuesJsDefault = parcelHelpers.interopDefault(_valuesJs);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _eachJs = require("./each.js");
var _eachJsDefault = parcelHelpers.interopDefault(_eachJs);
function max(obj, iteratee, context) {
    var result = -Infinity, lastComputed = -Infinity, value, computed;
    if (iteratee == null || typeof iteratee == "number" && typeof obj[0] != "object" && obj != null) {
        obj = (0, _isArrayLikeJsDefault.default)(obj) ? obj : (0, _valuesJsDefault.default)(obj);
        for(var i = 0, length = obj.length; i < length; i++){
            value = obj[i];
            if (value != null && value > result) result = value;
        }
    } else {
        iteratee = (0, _cbJsDefault.default)(iteratee, context);
        (0, _eachJsDefault.default)(obj, function(v, index, list) {
            computed = iteratee(v, index, list);
            if (computed > lastComputed || computed === -Infinity && result === -Infinity) {
                result = v;
                lastComputed = computed;
            }
        });
    }
    return result;
}

},{"./_isArrayLike.js":"7w1Hu","./values.js":"1I2Yc","./_cb.js":"hwRTD","./each.js":"fHmAz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"9EXwL":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>min);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _valuesJs = require("./values.js");
var _valuesJsDefault = parcelHelpers.interopDefault(_valuesJs);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _eachJs = require("./each.js");
var _eachJsDefault = parcelHelpers.interopDefault(_eachJs);
function min(obj, iteratee, context) {
    var result = Infinity, lastComputed = Infinity, value, computed;
    if (iteratee == null || typeof iteratee == "number" && typeof obj[0] != "object" && obj != null) {
        obj = (0, _isArrayLikeJsDefault.default)(obj) ? obj : (0, _valuesJsDefault.default)(obj);
        for(var i = 0, length = obj.length; i < length; i++){
            value = obj[i];
            if (value != null && value < result) result = value;
        }
    } else {
        iteratee = (0, _cbJsDefault.default)(iteratee, context);
        (0, _eachJsDefault.default)(obj, function(v, index, list) {
            computed = iteratee(v, index, list);
            if (computed < lastComputed || computed === Infinity && result === Infinity) {
                result = v;
                lastComputed = computed;
            }
        });
    }
    return result;
}

},{"./_isArrayLike.js":"7w1Hu","./values.js":"1I2Yc","./_cb.js":"hwRTD","./each.js":"fHmAz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"kl8WA":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>shuffle);
var _sampleJs = require("./sample.js");
var _sampleJsDefault = parcelHelpers.interopDefault(_sampleJs);
function shuffle(obj) {
    return (0, _sampleJsDefault.default)(obj, Infinity);
}

},{"./sample.js":"8fNnf","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"8fNnf":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>sample);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _valuesJs = require("./values.js");
var _valuesJsDefault = parcelHelpers.interopDefault(_valuesJs);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
var _randomJs = require("./random.js");
var _randomJsDefault = parcelHelpers.interopDefault(_randomJs);
var _toArrayJs = require("./toArray.js");
var _toArrayJsDefault = parcelHelpers.interopDefault(_toArrayJs);
function sample(obj, n, guard) {
    if (n == null || guard) {
        if (!(0, _isArrayLikeJsDefault.default)(obj)) obj = (0, _valuesJsDefault.default)(obj);
        return obj[(0, _randomJsDefault.default)(obj.length - 1)];
    }
    var sample = (0, _toArrayJsDefault.default)(obj);
    var length = (0, _getLengthJsDefault.default)(sample);
    n = Math.max(Math.min(n, length), 0);
    var last = length - 1;
    for(var index = 0; index < n; index++){
        var rand = (0, _randomJsDefault.default)(index, last);
        var temp = sample[index];
        sample[index] = sample[rand];
        sample[rand] = temp;
    }
    return sample.slice(0, n);
}

},{"./_isArrayLike.js":"7w1Hu","./values.js":"1I2Yc","./_getLength.js":"cb0Fe","./random.js":"imiVs","./toArray.js":"7e7T1","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"7e7T1":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>toArray);
var _isArrayJs = require("./isArray.js");
var _isArrayJsDefault = parcelHelpers.interopDefault(_isArrayJs);
var _setupJs = require("./_setup.js");
var _isStringJs = require("./isString.js");
var _isStringJsDefault = parcelHelpers.interopDefault(_isStringJs);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _mapJs = require("./map.js");
var _mapJsDefault = parcelHelpers.interopDefault(_mapJs);
var _identityJs = require("./identity.js");
var _identityJsDefault = parcelHelpers.interopDefault(_identityJs);
var _valuesJs = require("./values.js");
var _valuesJsDefault = parcelHelpers.interopDefault(_valuesJs);
// Safely create a real, live array from anything iterable.
var reStrSymbol = /[^\ud800-\udfff]|[\ud800-\udbff][\udc00-\udfff]|[\ud800-\udfff]/g;
function toArray(obj) {
    if (!obj) return [];
    if ((0, _isArrayJsDefault.default)(obj)) return (0, _setupJs.slice).call(obj);
    if ((0, _isStringJsDefault.default)(obj)) // Keep surrogate pair characters together.
    return obj.match(reStrSymbol);
    if ((0, _isArrayLikeJsDefault.default)(obj)) return (0, _mapJsDefault.default)(obj, (0, _identityJsDefault.default));
    return (0, _valuesJsDefault.default)(obj);
}

},{"./isArray.js":"cth5N","./_setup.js":"j1Opz","./isString.js":"h9vOY","./_isArrayLike.js":"7w1Hu","./map.js":"1MqH5","./identity.js":"iCRMn","./values.js":"1I2Yc","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"eCcLt":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>sortBy);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _pluckJs = require("./pluck.js");
var _pluckJsDefault = parcelHelpers.interopDefault(_pluckJs);
var _mapJs = require("./map.js");
var _mapJsDefault = parcelHelpers.interopDefault(_mapJs);
function sortBy(obj, iteratee, context) {
    var index = 0;
    iteratee = (0, _cbJsDefault.default)(iteratee, context);
    return (0, _pluckJsDefault.default)((0, _mapJsDefault.default)(obj, function(value, key, list) {
        return {
            value: value,
            index: index++,
            criteria: iteratee(value, key, list)
        };
    }).sort(function(left, right) {
        var a = left.criteria;
        var b = right.criteria;
        if (a !== b) {
            if (a > b || a === void 0) return 1;
            if (a < b || b === void 0) return -1;
        }
        return left.index - right.index;
    }), "value");
}

},{"./_cb.js":"hwRTD","./pluck.js":"OekpZ","./map.js":"1MqH5","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"k2aiT":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _groupJs = require("./_group.js");
var _groupJsDefault = parcelHelpers.interopDefault(_groupJs);
var _hasJs = require("./_has.js");
var _hasJsDefault = parcelHelpers.interopDefault(_hasJs);
// Groups the object's values by a criterion. Pass either a string attribute
// to group by, or a function that returns the criterion.
exports.default = (0, _groupJsDefault.default)(function(result, value, key) {
    if ((0, _hasJsDefault.default)(result, key)) result[key].push(value);
    else result[key] = [
        value
    ];
});

},{"./_group.js":"ltdJN","./_has.js":"500LZ","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"ltdJN":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>group);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _eachJs = require("./each.js");
var _eachJsDefault = parcelHelpers.interopDefault(_eachJs);
function group(behavior, partition) {
    return function(obj, iteratee, context) {
        var result = partition ? [
            [],
            []
        ] : {};
        iteratee = (0, _cbJsDefault.default)(iteratee, context);
        (0, _eachJsDefault.default)(obj, function(value, index) {
            var key = iteratee(value, index, obj);
            behavior(result, value, key);
        });
        return result;
    };
}

},{"./_cb.js":"hwRTD","./each.js":"fHmAz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"9VQiT":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _groupJs = require("./_group.js");
var _groupJsDefault = parcelHelpers.interopDefault(_groupJs);
// Indexes the object's values by a criterion, similar to `_.groupBy`, but for
// when you know that your index values will be unique.
exports.default = (0, _groupJsDefault.default)(function(result, value, key) {
    result[key] = value;
});

},{"./_group.js":"ltdJN","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"kNxCr":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _groupJs = require("./_group.js");
var _groupJsDefault = parcelHelpers.interopDefault(_groupJs);
var _hasJs = require("./_has.js");
var _hasJsDefault = parcelHelpers.interopDefault(_hasJs);
// Counts instances of an object that group by a certain criterion. Pass
// either a string attribute to count by, or a function that returns the
// criterion.
exports.default = (0, _groupJsDefault.default)(function(result, value, key) {
    if ((0, _hasJsDefault.default)(result, key)) result[key]++;
    else result[key] = 1;
});

},{"./_group.js":"ltdJN","./_has.js":"500LZ","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"bH0TP":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _groupJs = require("./_group.js");
var _groupJsDefault = parcelHelpers.interopDefault(_groupJs);
// Split a collection into two arrays: one whose elements all pass the given
// truth test, and one whose elements all do not pass the truth test.
exports.default = (0, _groupJsDefault.default)(function(result, value, pass) {
    result[pass ? 0 : 1].push(value);
}, true);

},{"./_group.js":"ltdJN","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"88Tqj":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>size);
var _isArrayLikeJs = require("./_isArrayLike.js");
var _isArrayLikeJsDefault = parcelHelpers.interopDefault(_isArrayLikeJs);
var _keysJs = require("./keys.js");
var _keysJsDefault = parcelHelpers.interopDefault(_keysJs);
function size(obj) {
    if (obj == null) return 0;
    return (0, _isArrayLikeJsDefault.default)(obj) ? obj.length : (0, _keysJsDefault.default)(obj).length;
}

},{"./_isArrayLike.js":"7w1Hu","./keys.js":"epVJ3","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"8ScJB":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
var _optimizeCbJs = require("./_optimizeCb.js");
var _optimizeCbJsDefault = parcelHelpers.interopDefault(_optimizeCbJs);
var _allKeysJs = require("./allKeys.js");
var _allKeysJsDefault = parcelHelpers.interopDefault(_allKeysJs);
var _keyInObjJs = require("./_keyInObj.js");
var _keyInObjJsDefault = parcelHelpers.interopDefault(_keyInObjJs);
var _flattenJs = require("./_flatten.js");
var _flattenJsDefault = parcelHelpers.interopDefault(_flattenJs);
// Return a copy of the object only containing the allowed properties.
exports.default = (0, _restArgumentsJsDefault.default)(function(obj, keys) {
    var result = {}, iteratee = keys[0];
    if (obj == null) return result;
    if ((0, _isFunctionJsDefault.default)(iteratee)) {
        if (keys.length > 1) iteratee = (0, _optimizeCbJsDefault.default)(iteratee, keys[1]);
        keys = (0, _allKeysJsDefault.default)(obj);
    } else {
        iteratee = (0, _keyInObjJsDefault.default);
        keys = (0, _flattenJsDefault.default)(keys, false, false);
        obj = Object(obj);
    }
    for(var i = 0, length = keys.length; i < length; i++){
        var key = keys[i];
        var value = obj[key];
        if (iteratee(value, key, obj)) result[key] = value;
    }
    return result;
});

},{"./restArguments.js":"iHiW5","./isFunction.js":"9XYGL","./_optimizeCb.js":"ib91j","./allKeys.js":"iL9rU","./_keyInObj.js":"cvpDy","./_flatten.js":"kRaRq","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"cvpDy":[function(require,module,exports) {
// Internal `_.pick` helper function to determine whether `key` is an enumerable
// property name of `obj`.
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>keyInObj);
function keyInObj(value, key, obj) {
    return key in obj;
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"6aykp":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _isFunctionJs = require("./isFunction.js");
var _isFunctionJsDefault = parcelHelpers.interopDefault(_isFunctionJs);
var _negateJs = require("./negate.js");
var _negateJsDefault = parcelHelpers.interopDefault(_negateJs);
var _mapJs = require("./map.js");
var _mapJsDefault = parcelHelpers.interopDefault(_mapJs);
var _flattenJs = require("./_flatten.js");
var _flattenJsDefault = parcelHelpers.interopDefault(_flattenJs);
var _containsJs = require("./contains.js");
var _containsJsDefault = parcelHelpers.interopDefault(_containsJs);
var _pickJs = require("./pick.js");
var _pickJsDefault = parcelHelpers.interopDefault(_pickJs);
// Return a copy of the object without the disallowed properties.
exports.default = (0, _restArgumentsJsDefault.default)(function(obj, keys) {
    var iteratee = keys[0], context;
    if ((0, _isFunctionJsDefault.default)(iteratee)) {
        iteratee = (0, _negateJsDefault.default)(iteratee);
        if (keys.length > 1) context = keys[1];
    } else {
        keys = (0, _mapJsDefault.default)((0, _flattenJsDefault.default)(keys, false, false), String);
        iteratee = function(value, key) {
            return !(0, _containsJsDefault.default)(keys, key);
        };
    }
    return (0, _pickJsDefault.default)(obj, iteratee, context);
});

},{"./restArguments.js":"iHiW5","./isFunction.js":"9XYGL","./negate.js":"juYC5","./map.js":"1MqH5","./_flatten.js":"kRaRq","./contains.js":"7u1gl","./pick.js":"8ScJB","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"bNqM1":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>first);
var _initialJs = require("./initial.js");
var _initialJsDefault = parcelHelpers.interopDefault(_initialJs);
function first(array, n, guard) {
    if (array == null || array.length < 1) return n == null || guard ? void 0 : [];
    if (n == null || guard) return array[0];
    return (0, _initialJsDefault.default)(array, array.length - n);
}

},{"./initial.js":"cD91j","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"cD91j":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>initial);
var _setupJs = require("./_setup.js");
function initial(array, n, guard) {
    return (0, _setupJs.slice).call(array, 0, Math.max(0, array.length - (n == null || guard ? 1 : n)));
}

},{"./_setup.js":"j1Opz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"38Fqg":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>last);
var _restJs = require("./rest.js");
var _restJsDefault = parcelHelpers.interopDefault(_restJs);
function last(array, n, guard) {
    if (array == null || array.length < 1) return n == null || guard ? void 0 : [];
    if (n == null || guard) return array[array.length - 1];
    return (0, _restJsDefault.default)(array, Math.max(0, array.length - n));
}

},{"./rest.js":"aLSkH","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"aLSkH":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>rest);
var _setupJs = require("./_setup.js");
function rest(array, n, guard) {
    return (0, _setupJs.slice).call(array, n == null || guard ? 1 : n);
}

},{"./_setup.js":"j1Opz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"3coBb":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>compact);
var _filterJs = require("./filter.js");
var _filterJsDefault = parcelHelpers.interopDefault(_filterJs);
function compact(array) {
    return (0, _filterJsDefault.default)(array, Boolean);
}

},{"./filter.js":"5cyip","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"gpF6L":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>flatten);
var _flattenJs = require("./_flatten.js");
var _flattenJsDefault = parcelHelpers.interopDefault(_flattenJs);
function flatten(array, depth) {
    return (0, _flattenJsDefault.default)(array, depth, false);
}

},{"./_flatten.js":"kRaRq","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"ouhVw":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _differenceJs = require("./difference.js");
var _differenceJsDefault = parcelHelpers.interopDefault(_differenceJs);
// Return a version of the array that does not contain the specified value(s).
exports.default = (0, _restArgumentsJsDefault.default)(function(array, otherArrays) {
    return (0, _differenceJsDefault.default)(array, otherArrays);
});

},{"./restArguments.js":"iHiW5","./difference.js":"e9ASn","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"e9ASn":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _flattenJs = require("./_flatten.js");
var _flattenJsDefault = parcelHelpers.interopDefault(_flattenJs);
var _filterJs = require("./filter.js");
var _filterJsDefault = parcelHelpers.interopDefault(_filterJs);
var _containsJs = require("./contains.js");
var _containsJsDefault = parcelHelpers.interopDefault(_containsJs);
// Take the difference between one array and a number of other arrays.
// Only the elements present in just the first array will remain.
exports.default = (0, _restArgumentsJsDefault.default)(function(array, rest) {
    rest = (0, _flattenJsDefault.default)(rest, true, true);
    return (0, _filterJsDefault.default)(array, function(value) {
        return !(0, _containsJsDefault.default)(rest, value);
    });
});

},{"./restArguments.js":"iHiW5","./_flatten.js":"kRaRq","./filter.js":"5cyip","./contains.js":"7u1gl","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"kiHGM":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>uniq);
var _isBooleanJs = require("./isBoolean.js");
var _isBooleanJsDefault = parcelHelpers.interopDefault(_isBooleanJs);
var _cbJs = require("./_cb.js");
var _cbJsDefault = parcelHelpers.interopDefault(_cbJs);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
var _containsJs = require("./contains.js");
var _containsJsDefault = parcelHelpers.interopDefault(_containsJs);
function uniq(array, isSorted, iteratee, context) {
    if (!(0, _isBooleanJsDefault.default)(isSorted)) {
        context = iteratee;
        iteratee = isSorted;
        isSorted = false;
    }
    if (iteratee != null) iteratee = (0, _cbJsDefault.default)(iteratee, context);
    var result = [];
    var seen = [];
    for(var i = 0, length = (0, _getLengthJsDefault.default)(array); i < length; i++){
        var value = array[i], computed = iteratee ? iteratee(value, i, array) : value;
        if (isSorted && !iteratee) {
            if (!i || seen !== computed) result.push(value);
            seen = computed;
        } else if (iteratee) {
            if (!(0, _containsJsDefault.default)(seen, computed)) {
                seen.push(computed);
                result.push(value);
            }
        } else if (!(0, _containsJsDefault.default)(result, value)) result.push(value);
    }
    return result;
}

},{"./isBoolean.js":"e6GFe","./_cb.js":"hwRTD","./_getLength.js":"cb0Fe","./contains.js":"7u1gl","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"k8pGG":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _uniqJs = require("./uniq.js");
var _uniqJsDefault = parcelHelpers.interopDefault(_uniqJs);
var _flattenJs = require("./_flatten.js");
var _flattenJsDefault = parcelHelpers.interopDefault(_flattenJs);
// Produce an array that contains the union: each distinct element from all of
// the passed-in arrays.
exports.default = (0, _restArgumentsJsDefault.default)(function(arrays) {
    return (0, _uniqJsDefault.default)((0, _flattenJsDefault.default)(arrays, true, true));
});

},{"./restArguments.js":"iHiW5","./uniq.js":"kiHGM","./_flatten.js":"kRaRq","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"iHUB6":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>intersection);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
var _containsJs = require("./contains.js");
var _containsJsDefault = parcelHelpers.interopDefault(_containsJs);
function intersection(array) {
    var result = [];
    var argsLength = arguments.length;
    for(var i = 0, length = (0, _getLengthJsDefault.default)(array); i < length; i++){
        var item = array[i];
        if ((0, _containsJsDefault.default)(result, item)) continue;
        var j;
        for(j = 1; j < argsLength; j++){
            if (!(0, _containsJsDefault.default)(arguments[j], item)) break;
        }
        if (j === argsLength) result.push(item);
    }
    return result;
}

},{"./_getLength.js":"cb0Fe","./contains.js":"7u1gl","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"hyGGg":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>unzip);
var _maxJs = require("./max.js");
var _maxJsDefault = parcelHelpers.interopDefault(_maxJs);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
var _pluckJs = require("./pluck.js");
var _pluckJsDefault = parcelHelpers.interopDefault(_pluckJs);
function unzip(array) {
    var length = array && (0, _maxJsDefault.default)(array, (0, _getLengthJsDefault.default)).length || 0;
    var result = Array(length);
    for(var index = 0; index < length; index++)result[index] = (0, _pluckJsDefault.default)(array, index);
    return result;
}

},{"./max.js":"6g3ZY","./_getLength.js":"cb0Fe","./pluck.js":"OekpZ","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"lJw0p":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _restArgumentsJs = require("./restArguments.js");
var _restArgumentsJsDefault = parcelHelpers.interopDefault(_restArgumentsJs);
var _unzipJs = require("./unzip.js");
var _unzipJsDefault = parcelHelpers.interopDefault(_unzipJs);
// Zip together multiple lists into a single array -- elements that share
// an index go together.
exports.default = (0, _restArgumentsJsDefault.default)((0, _unzipJsDefault.default));

},{"./restArguments.js":"iHiW5","./unzip.js":"hyGGg","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"bvlJI":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>object);
var _getLengthJs = require("./_getLength.js");
var _getLengthJsDefault = parcelHelpers.interopDefault(_getLengthJs);
function object(list, values) {
    var result = {};
    for(var i = 0, length = (0, _getLengthJsDefault.default)(list); i < length; i++)if (values) result[list[i]] = values[i];
    else result[list[i][0]] = list[i][1];
    return result;
}

},{"./_getLength.js":"cb0Fe","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"43G11":[function(require,module,exports) {
// Generate an integer Array containing an arithmetic progression. A port of
// the native Python `range()` function. See
// [the Python documentation](https://docs.python.org/library/functions.html#range).
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>range);
function range(start, stop, step) {
    if (stop == null) {
        stop = start || 0;
        start = 0;
    }
    if (!step) step = stop < start ? -1 : 1;
    var length = Math.max(Math.ceil((stop - start) / step), 0);
    var range = Array(length);
    for(var idx = 0; idx < length; idx++, start += step)range[idx] = start;
    return range;
}

},{"@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"57Gcn":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>chunk);
var _setupJs = require("./_setup.js");
function chunk(array, count) {
    if (count == null || count < 1) return [];
    var result = [];
    var i = 0, length = array.length;
    while(i < length)result.push((0, _setupJs.slice).call(array, i, i += count));
    return result;
}

},{"./_setup.js":"j1Opz","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"enXfg":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>mixin);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
var _eachJs = require("./each.js");
var _eachJsDefault = parcelHelpers.interopDefault(_eachJs);
var _functionsJs = require("./functions.js");
var _functionsJsDefault = parcelHelpers.interopDefault(_functionsJs);
var _setupJs = require("./_setup.js");
var _chainResultJs = require("./_chainResult.js");
var _chainResultJsDefault = parcelHelpers.interopDefault(_chainResultJs);
function mixin(obj) {
    (0, _eachJsDefault.default)((0, _functionsJsDefault.default)(obj), function(name) {
        var func = (0, _underscoreJsDefault.default)[name] = obj[name];
        (0, _underscoreJsDefault.default).prototype[name] = function() {
            var args = [
                this._wrapped
            ];
            (0, _setupJs.push).apply(args, arguments);
            return (0, _chainResultJsDefault.default)(this, func.apply((0, _underscoreJsDefault.default), args));
        };
    });
    return 0, _underscoreJsDefault.default;
}

},{"./underscore.js":"cZn3h","./each.js":"fHmAz","./functions.js":"6kKwG","./_setup.js":"j1Opz","./_chainResult.js":"2gkrX","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"2gkrX":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
parcelHelpers.export(exports, "default", ()=>chainResult);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
function chainResult(instance, obj) {
    return instance._chain ? (0, _underscoreJsDefault.default)(obj).chain() : obj;
}

},{"./underscore.js":"cZn3h","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"k1JcM":[function(require,module,exports) {
var parcelHelpers = require("@parcel/transformer-js/src/esmodule-helpers.js");
parcelHelpers.defineInteropFlag(exports);
var _underscoreJs = require("./underscore.js");
var _underscoreJsDefault = parcelHelpers.interopDefault(_underscoreJs);
var _eachJs = require("./each.js");
var _eachJsDefault = parcelHelpers.interopDefault(_eachJs);
var _setupJs = require("./_setup.js");
var _chainResultJs = require("./_chainResult.js");
var _chainResultJsDefault = parcelHelpers.interopDefault(_chainResultJs);
// Add all mutator `Array` functions to the wrapper.
(0, _eachJsDefault.default)([
    "pop",
    "push",
    "reverse",
    "shift",
    "sort",
    "splice",
    "unshift"
], function(name) {
    var method = (0, _setupJs.ArrayProto)[name];
    (0, _underscoreJsDefault.default).prototype[name] = function() {
        var obj = this._wrapped;
        if (obj != null) {
            method.apply(obj, arguments);
            if ((name === "shift" || name === "splice") && obj.length === 0) delete obj[0];
        }
        return (0, _chainResultJsDefault.default)(this, obj);
    };
});
// Add all accessor `Array` functions to the wrapper.
(0, _eachJsDefault.default)([
    "concat",
    "join",
    "slice"
], function(name) {
    var method = (0, _setupJs.ArrayProto)[name];
    (0, _underscoreJsDefault.default).prototype[name] = function() {
        var obj = this._wrapped;
        if (obj != null) obj = method.apply(obj, arguments);
        return (0, _chainResultJsDefault.default)(this, obj);
    };
});
exports.default = (0, _underscoreJsDefault.default);

},{"./underscore.js":"cZn3h","./each.js":"fHmAz","./_setup.js":"j1Opz","./_chainResult.js":"2gkrX","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}]},["jrYKc","6BMq4"], "6BMq4", "parcelRequirecea6")

//# sourceMappingURL=client.cb6ff3a3.js.map
