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
})({"l33Ty":[function(require,module,exports) {
var global = arguments[3];
var HMR_HOST = null;
var HMR_PORT = null;
var HMR_SECURE = false;
var HMR_ENV_HASH = "d6ea1d42532a7575";
module.bundle.HMR_BUNDLE_ID = "67fe2d4f509fc7ed";
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

},{}],"KmxTh":[function(require,module,exports) {
var global = arguments[3];
//     Backbone.js 1.4.1
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
        var _ = require("4b50112a7d30d4e4"), $;
        try {
            $ = require("c8bf14cb96690cc2");
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
    Backbone.VERSION = "1.4.1";
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
                if (wait) collection.add(m, callbackOpts);
                if (success) success.call(callbackOpts.context, m, resp, callbackOpts);
            };
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
            // Don't include a trailing slash on the root.
            var rootPath = this.root;
            if (fragment === "" || fragment.charAt(0) === "?") rootPath = rootPath.slice(0, -1) || "/";
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

},{"4b50112a7d30d4e4":"8o1Pk","c8bf14cb96690cc2":"hgMhh"}],"8o1Pk":[function(require,module,exports) {
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

},{"./underscore.js":"cZn3h","./each.js":"fHmAz","./_setup.js":"j1Opz","./_chainResult.js":"2gkrX","@parcel/transformer-js/src/esmodule-helpers.js":"gkKU3"}],"hgMhh":[function(require,module,exports) {
/*!
 * jQuery JavaScript Library v3.7.0
 * https://jquery.com/
 *
 * Copyright OpenJS Foundation and other contributors
 * Released under the MIT license
 * https://jquery.org/license
 *
 * Date: 2023-05-11T18:29Z
 */ (function(global, factory) {
    "use strict";
    if (typeof module.exports === "object") // For CommonJS and CommonJS-like environments where a proper `window`
    // is present, execute the factory and get jQuery.
    // For environments that do not have a `window` with a `document`
    // (such as Node.js), expose a factory as module.exports.
    // This accentuates the need for the creation of a real `window`.
    // e.g. var jQuery = require("jquery")(window);
    // See ticket trac-14549 for more info.
    module.exports = global.document ? factory(global, true) : function(w) {
        if (!w.document) throw new Error("jQuery requires a window with a document");
        return factory(w);
    };
    else factory(global);
// Pass this if window is not defined yet
})(typeof window !== "undefined" ? window : this, function(window1, noGlobal) {
    // Edge <= 12 - 13+, Firefox <=18 - 45+, IE 10 - 11, Safari 5.1 - 9+, iOS 6 - 9.1
    // throw exceptions when non-strict code (e.g., ASP.NET 4.5) accesses strict mode
    // arguments.callee.caller (trac-13335). But as of jQuery 3.0 (2016), strict mode should be common
    // enough that all such attempts are guarded in a try block.
    "use strict";
    var arr = [];
    var getProto = Object.getPrototypeOf;
    var slice = arr.slice;
    var flat = arr.flat ? function(array) {
        return arr.flat.call(array);
    } : function(array) {
        return arr.concat.apply([], array);
    };
    var push = arr.push;
    var indexOf = arr.indexOf;
    var class2type = {};
    var toString = class2type.toString;
    var hasOwn = class2type.hasOwnProperty;
    var fnToString = hasOwn.toString;
    var ObjectFunctionString = fnToString.call(Object);
    var support = {};
    var isFunction = function isFunction(obj) {
        // Support: Chrome <=57, Firefox <=52
        // In some browsers, typeof returns "function" for HTML <object> elements
        // (i.e., `typeof document.createElement( "object" ) === "function"`).
        // We don't want to classify *any* DOM node as a function.
        // Support: QtWeb <=3.8.5, WebKit <=534.34, wkhtmltopdf tool <=0.12.5
        // Plus for old WebKit, typeof returns "function" for HTML collections
        // (e.g., `typeof document.getElementsByTagName("div") === "function"`). (gh-4756)
        return typeof obj === "function" && typeof obj.nodeType !== "number" && typeof obj.item !== "function";
    };
    var isWindow = function isWindow(obj) {
        return obj != null && obj === obj.window;
    };
    var document = window1.document;
    var preservedScriptAttributes = {
        type: true,
        src: true,
        nonce: true,
        noModule: true
    };
    function DOMEval(code, node, doc) {
        doc = doc || document;
        var i, val, script = doc.createElement("script");
        script.text = code;
        if (node) for(i in preservedScriptAttributes){
            // Support: Firefox 64+, Edge 18+
            // Some browsers don't support the "nonce" property on scripts.
            // On the other hand, just using `getAttribute` is not enough as
            // the `nonce` attribute is reset to an empty string whenever it
            // becomes browsing-context connected.
            // See https://github.com/whatwg/html/issues/2369
            // See https://html.spec.whatwg.org/#nonce-attributes
            // The `node.getAttribute` check was added for the sake of
            // `jQuery.globalEval` so that it can fake a nonce-containing node
            // via an object.
            val = node[i] || node.getAttribute && node.getAttribute(i);
            if (val) script.setAttribute(i, val);
        }
        doc.head.appendChild(script).parentNode.removeChild(script);
    }
    function toType(obj) {
        if (obj == null) return obj + "";
        // Support: Android <=2.3 only (functionish RegExp)
        return typeof obj === "object" || typeof obj === "function" ? class2type[toString.call(obj)] || "object" : typeof obj;
    }
    /* global Symbol */ // Defining this global in .eslintrc.json would create a danger of using the global
    // unguarded in another place, it seems safer to define global only for this module
    var version = "3.7.0", rhtmlSuffix = /HTML$/i, // Define a local copy of jQuery
    jQuery = function(selector, context) {
        // The jQuery object is actually just the init constructor 'enhanced'
        // Need init if jQuery is called (just allow error to be thrown if not included)
        return new jQuery.fn.init(selector, context);
    };
    jQuery.fn = jQuery.prototype = {
        // The current version of jQuery being used
        jquery: version,
        constructor: jQuery,
        // The default length of a jQuery object is 0
        length: 0,
        toArray: function() {
            return slice.call(this);
        },
        // Get the Nth element in the matched element set OR
        // Get the whole matched element set as a clean array
        get: function(num) {
            // Return all the elements in a clean array
            if (num == null) return slice.call(this);
            // Return just the one element from the set
            return num < 0 ? this[num + this.length] : this[num];
        },
        // Take an array of elements and push it onto the stack
        // (returning the new matched element set)
        pushStack: function(elems) {
            // Build a new jQuery matched element set
            var ret = jQuery.merge(this.constructor(), elems);
            // Add the old object onto the stack (as a reference)
            ret.prevObject = this;
            // Return the newly-formed element set
            return ret;
        },
        // Execute a callback for every element in the matched set.
        each: function(callback) {
            return jQuery.each(this, callback);
        },
        map: function(callback) {
            return this.pushStack(jQuery.map(this, function(elem, i) {
                return callback.call(elem, i, elem);
            }));
        },
        slice: function() {
            return this.pushStack(slice.apply(this, arguments));
        },
        first: function() {
            return this.eq(0);
        },
        last: function() {
            return this.eq(-1);
        },
        even: function() {
            return this.pushStack(jQuery.grep(this, function(_elem, i) {
                return (i + 1) % 2;
            }));
        },
        odd: function() {
            return this.pushStack(jQuery.grep(this, function(_elem, i) {
                return i % 2;
            }));
        },
        eq: function(i) {
            var len = this.length, j = +i + (i < 0 ? len : 0);
            return this.pushStack(j >= 0 && j < len ? [
                this[j]
            ] : []);
        },
        end: function() {
            return this.prevObject || this.constructor();
        },
        // For internal use only.
        // Behaves like an Array's method, not like a jQuery method.
        push: push,
        sort: arr.sort,
        splice: arr.splice
    };
    jQuery.extend = jQuery.fn.extend = function() {
        var options, name, src, copy, copyIsArray, clone, target = arguments[0] || {}, i = 1, length = arguments.length, deep = false;
        // Handle a deep copy situation
        if (typeof target === "boolean") {
            deep = target;
            // Skip the boolean and the target
            target = arguments[i] || {};
            i++;
        }
        // Handle case when target is a string or something (possible in deep copy)
        if (typeof target !== "object" && !isFunction(target)) target = {};
        // Extend jQuery itself if only one argument is passed
        if (i === length) {
            target = this;
            i--;
        }
        for(; i < length; i++){
            // Only deal with non-null/undefined values
            if ((options = arguments[i]) != null) // Extend the base object
            for(name in options){
                copy = options[name];
                // Prevent Object.prototype pollution
                // Prevent never-ending loop
                if (name === "__proto__" || target === copy) continue;
                // Recurse if we're merging plain objects or arrays
                if (deep && copy && (jQuery.isPlainObject(copy) || (copyIsArray = Array.isArray(copy)))) {
                    src = target[name];
                    // Ensure proper type for the source value
                    if (copyIsArray && !Array.isArray(src)) clone = [];
                    else if (!copyIsArray && !jQuery.isPlainObject(src)) clone = {};
                    else clone = src;
                    copyIsArray = false;
                    // Never move original objects, clone them
                    target[name] = jQuery.extend(deep, clone, copy);
                // Don't bring in undefined values
                } else if (copy !== undefined) target[name] = copy;
            }
        }
        // Return the modified object
        return target;
    };
    jQuery.extend({
        // Unique for each copy of jQuery on the page
        expando: "jQuery" + (version + Math.random()).replace(/\D/g, ""),
        // Assume jQuery is ready without the ready module
        isReady: true,
        error: function(msg) {
            throw new Error(msg);
        },
        noop: function() {},
        isPlainObject: function(obj) {
            var proto, Ctor;
            // Detect obvious negatives
            // Use toString instead of jQuery.type to catch host objects
            if (!obj || toString.call(obj) !== "[object Object]") return false;
            proto = getProto(obj);
            // Objects with no prototype (e.g., `Object.create( null )`) are plain
            if (!proto) return true;
            // Objects with prototype are plain iff they were constructed by a global Object function
            Ctor = hasOwn.call(proto, "constructor") && proto.constructor;
            return typeof Ctor === "function" && fnToString.call(Ctor) === ObjectFunctionString;
        },
        isEmptyObject: function(obj) {
            var name;
            for(name in obj)return false;
            return true;
        },
        // Evaluates a script in a provided context; falls back to the global one
        // if not specified.
        globalEval: function(code, options, doc) {
            DOMEval(code, {
                nonce: options && options.nonce
            }, doc);
        },
        each: function(obj, callback) {
            var length, i = 0;
            if (isArrayLike(obj)) {
                length = obj.length;
                for(; i < length; i++){
                    if (callback.call(obj[i], i, obj[i]) === false) break;
                }
            } else for(i in obj){
                if (callback.call(obj[i], i, obj[i]) === false) break;
            }
            return obj;
        },
        // Retrieve the text value of an array of DOM nodes
        text: function(elem) {
            var node, ret = "", i = 0, nodeType = elem.nodeType;
            if (!nodeType) // If no nodeType, this is expected to be an array
            while(node = elem[i++])// Do not traverse comment nodes
            ret += jQuery.text(node);
            else if (nodeType === 1 || nodeType === 9 || nodeType === 11) return elem.textContent;
            else if (nodeType === 3 || nodeType === 4) return elem.nodeValue;
            // Do not include comment or processing instruction nodes
            return ret;
        },
        // results is for internal usage only
        makeArray: function(arr, results) {
            var ret = results || [];
            if (arr != null) {
                if (isArrayLike(Object(arr))) jQuery.merge(ret, typeof arr === "string" ? [
                    arr
                ] : arr);
                else push.call(ret, arr);
            }
            return ret;
        },
        inArray: function(elem, arr, i) {
            return arr == null ? -1 : indexOf.call(arr, elem, i);
        },
        isXMLDoc: function(elem) {
            var namespace = elem && elem.namespaceURI, docElem = elem && (elem.ownerDocument || elem).documentElement;
            // Assume HTML when documentElement doesn't yet exist, such as inside
            // document fragments.
            return !rhtmlSuffix.test(namespace || docElem && docElem.nodeName || "HTML");
        },
        // Support: Android <=4.0 only, PhantomJS 1 only
        // push.apply(_, arraylike) throws on ancient WebKit
        merge: function(first, second) {
            var len = +second.length, j = 0, i = first.length;
            for(; j < len; j++)first[i++] = second[j];
            first.length = i;
            return first;
        },
        grep: function(elems, callback, invert) {
            var callbackInverse, matches = [], i = 0, length = elems.length, callbackExpect = !invert;
            // Go through the array, only saving the items
            // that pass the validator function
            for(; i < length; i++){
                callbackInverse = !callback(elems[i], i);
                if (callbackInverse !== callbackExpect) matches.push(elems[i]);
            }
            return matches;
        },
        // arg is for internal usage only
        map: function(elems, callback, arg) {
            var length, value, i = 0, ret = [];
            // Go through the array, translating each of the items to their new values
            if (isArrayLike(elems)) {
                length = elems.length;
                for(; i < length; i++){
                    value = callback(elems[i], i, arg);
                    if (value != null) ret.push(value);
                }
            // Go through every key on the object,
            } else for(i in elems){
                value = callback(elems[i], i, arg);
                if (value != null) ret.push(value);
            }
            // Flatten any nested arrays
            return flat(ret);
        },
        // A global GUID counter for objects
        guid: 1,
        // jQuery.support is not used in Core but other projects attach their
        // properties to it so it needs to exist.
        support: support
    });
    if (typeof Symbol === "function") jQuery.fn[Symbol.iterator] = arr[Symbol.iterator];
    // Populate the class2type map
    jQuery.each("Boolean Number String Function Array Date RegExp Object Error Symbol".split(" "), function(_i, name) {
        class2type["[object " + name + "]"] = name.toLowerCase();
    });
    function isArrayLike(obj) {
        // Support: real iOS 8.2 only (not reproducible in simulator)
        // `in` check used to prevent JIT error (gh-2145)
        // hasOwn isn't used here due to false negatives
        // regarding Nodelist length in IE
        var length = !!obj && "length" in obj && obj.length, type = toType(obj);
        if (isFunction(obj) || isWindow(obj)) return false;
        return type === "array" || length === 0 || typeof length === "number" && length > 0 && length - 1 in obj;
    }
    function nodeName(elem, name) {
        return elem.nodeName && elem.nodeName.toLowerCase() === name.toLowerCase();
    }
    var pop = arr.pop;
    var sort = arr.sort;
    var splice = arr.splice;
    var whitespace = "[\\x20\\t\\r\\n\\f]";
    var rtrimCSS = new RegExp("^" + whitespace + "+|((?:^|[^\\\\])(?:\\\\.)*)" + whitespace + "+$", "g");
    // Note: an element does not contain itself
    jQuery.contains = function(a, b) {
        var bup = b && b.parentNode;
        return a === bup || !!(bup && bup.nodeType === 1 && // Support: IE 9 - 11+
        // IE doesn't have `contains` on SVG.
        (a.contains ? a.contains(bup) : a.compareDocumentPosition && a.compareDocumentPosition(bup) & 16));
    };
    // CSS string/identifier serialization
    // https://drafts.csswg.org/cssom/#common-serializing-idioms
    var rcssescape = /([\0-\x1f\x7f]|^-?\d)|^-$|[^\x80-\uFFFF\w-]/g;
    function fcssescape(ch, asCodePoint) {
        if (asCodePoint) {
            // U+0000 NULL becomes U+FFFD REPLACEMENT CHARACTER
            if (ch === "\x00") return "�";
            // Control characters and (dependent upon position) numbers get escaped as code points
            return ch.slice(0, -1) + "\\" + ch.charCodeAt(ch.length - 1).toString(16) + " ";
        }
        // Other potentially-special ASCII characters get backslash-escaped
        return "\\" + ch;
    }
    jQuery.escapeSelector = function(sel) {
        return (sel + "").replace(rcssescape, fcssescape);
    };
    var preferredDoc = document, pushNative = push;
    (function() {
        var i, Expr, outermostContext, sortInput, hasDuplicate, push = pushNative, // Local document vars
        document, documentElement, documentIsHTML, rbuggyQSA, matches, // Instance-specific data
        expando = jQuery.expando, dirruns = 0, done = 0, classCache = createCache(), tokenCache = createCache(), compilerCache = createCache(), nonnativeSelectorCache = createCache(), sortOrder = function(a, b) {
            if (a === b) hasDuplicate = true;
            return 0;
        }, booleans = "checked|selected|async|autofocus|autoplay|controls|defer|disabled|hidden|ismap|loop|multiple|open|readonly|required|scoped", // Regular expressions
        // https://www.w3.org/TR/css-syntax-3/#ident-token-diagram
        identifier = "(?:\\\\[\\da-fA-F]{1,6}" + whitespace + "?|\\\\[^\\r\\n\\f]|[\\w-]|[^\x00-\\x7f])+", // Attribute selectors: https://www.w3.org/TR/selectors/#attribute-selectors
        attributes = "\\[" + whitespace + "*(" + identifier + ")(?:" + whitespace + // Operator (capture 2)
        "*([*^$|!~]?=)" + whitespace + // "Attribute values must be CSS identifiers [capture 5] or strings [capture 3 or capture 4]"
        "*(?:'((?:\\\\.|[^\\\\'])*)'|\"((?:\\\\.|[^\\\\\"])*)\"|(" + identifier + "))|)" + whitespace + "*\\]", pseudos = ":(" + identifier + ")(?:\\((" + // To reduce the number of selectors needing tokenize in the preFilter, prefer arguments:
        // 1. quoted (capture 3; capture 4 or capture 5)
        "('((?:\\\\.|[^\\\\'])*)'|\"((?:\\\\.|[^\\\\\"])*)\")|" + // 2. simple (capture 6)
        "((?:\\\\.|[^\\\\()[\\]]|" + attributes + ")*)|" + // 3. anything else (capture 2)
        ".*" + ")\\)|)", // Leading and non-escaped trailing whitespace, capturing some non-whitespace characters preceding the latter
        rwhitespace = new RegExp(whitespace + "+", "g"), rcomma = new RegExp("^" + whitespace + "*," + whitespace + "*"), rleadingCombinator = new RegExp("^" + whitespace + "*([>+~]|" + whitespace + ")" + whitespace + "*"), rdescend = new RegExp(whitespace + "|>"), rpseudo = new RegExp(pseudos), ridentifier = new RegExp("^" + identifier + "$"), matchExpr = {
            ID: new RegExp("^#(" + identifier + ")"),
            CLASS: new RegExp("^\\.(" + identifier + ")"),
            TAG: new RegExp("^(" + identifier + "|[*])"),
            ATTR: new RegExp("^" + attributes),
            PSEUDO: new RegExp("^" + pseudos),
            CHILD: new RegExp("^:(only|first|last|nth|nth-last)-(child|of-type)(?:\\(" + whitespace + "*(even|odd|(([+-]|)(\\d*)n|)" + whitespace + "*(?:([+-]|)" + whitespace + "*(\\d+)|))" + whitespace + "*\\)|)", "i"),
            bool: new RegExp("^(?:" + booleans + ")$", "i"),
            // For use in libraries implementing .is()
            // We use this for POS matching in `select`
            needsContext: new RegExp("^" + whitespace + "*[>+~]|:(even|odd|eq|gt|lt|nth|first|last)(?:\\(" + whitespace + "*((?:-\\d)?\\d*)" + whitespace + "*\\)|)(?=[^-]|$)", "i")
        }, rinputs = /^(?:input|select|textarea|button)$/i, rheader = /^h\d$/i, // Easily-parseable/retrievable ID or TAG or CLASS selectors
        rquickExpr = /^(?:#([\w-]+)|(\w+)|\.([\w-]+))$/, rsibling = /[+~]/, // CSS escapes
        // https://www.w3.org/TR/CSS21/syndata.html#escaped-characters
        runescape = new RegExp("\\\\[\\da-fA-F]{1,6}" + whitespace + "?|\\\\([^\\r\\n\\f])", "g"), funescape = function(escape, nonHex) {
            var high = "0x" + escape.slice(1) - 0x10000;
            if (nonHex) // Strip the backslash prefix from a non-hex escape sequence
            return nonHex;
            // Replace a hexadecimal escape sequence with the encoded Unicode code point
            // Support: IE <=11+
            // For values outside the Basic Multilingual Plane (BMP), manually construct a
            // surrogate pair
            return high < 0 ? String.fromCharCode(high + 0x10000) : String.fromCharCode(high >> 10 | 0xD800, high & 0x3FF | 0xDC00);
        }, // Used for iframes; see `setDocument`.
        // Support: IE 9 - 11+, Edge 12 - 18+
        // Removing the function wrapper causes a "Permission Denied"
        // error in IE/Edge.
        unloadHandler = function() {
            setDocument();
        }, inDisabledFieldset = addCombinator(function(elem) {
            return elem.disabled === true && nodeName(elem, "fieldset");
        }, {
            dir: "parentNode",
            next: "legend"
        });
        // Support: IE <=9 only
        // Accessing document.activeElement can throw unexpectedly
        // https://bugs.jquery.com/ticket/13393
        function safeActiveElement() {
            try {
                return document.activeElement;
            } catch (err) {}
        }
        // Optimize for push.apply( _, NodeList )
        try {
            push.apply(arr = slice.call(preferredDoc.childNodes), preferredDoc.childNodes);
            // Support: Android <=4.0
            // Detect silently failing push.apply
            // eslint-disable-next-line no-unused-expressions
            arr[preferredDoc.childNodes.length].nodeType;
        } catch (e) {
            push = {
                apply: function(target, els) {
                    pushNative.apply(target, slice.call(els));
                },
                call: function(target) {
                    pushNative.apply(target, slice.call(arguments, 1));
                }
            };
        }
        function find(selector, context, results, seed) {
            var m, i, elem, nid, match, groups, newSelector, newContext = context && context.ownerDocument, // nodeType defaults to 9, since context defaults to document
            nodeType = context ? context.nodeType : 9;
            results = results || [];
            // Return early from calls with invalid selector or context
            if (typeof selector !== "string" || !selector || nodeType !== 1 && nodeType !== 9 && nodeType !== 11) return results;
            // Try to shortcut find operations (as opposed to filters) in HTML documents
            if (!seed) {
                setDocument(context);
                context = context || document;
                if (documentIsHTML) {
                    // If the selector is sufficiently simple, try using a "get*By*" DOM method
                    // (excepting DocumentFragment context, where the methods don't exist)
                    if (nodeType !== 11 && (match = rquickExpr.exec(selector))) {
                        // ID selector
                        if (m = match[1]) {
                            // Document context
                            if (nodeType === 9) {
                                if (elem = context.getElementById(m)) // Support: IE 9 only
                                // getElementById can match elements by name instead of ID
                                {
                                    if (elem.id === m) {
                                        push.call(results, elem);
                                        return results;
                                    }
                                } else return results;
                            // Element context
                            } else // Support: IE 9 only
                            // getElementById can match elements by name instead of ID
                            if (newContext && (elem = newContext.getElementById(m)) && find.contains(context, elem) && elem.id === m) {
                                push.call(results, elem);
                                return results;
                            }
                        // Type selector
                        } else if (match[2]) {
                            push.apply(results, context.getElementsByTagName(selector));
                            return results;
                        // Class selector
                        } else if ((m = match[3]) && context.getElementsByClassName) {
                            push.apply(results, context.getElementsByClassName(m));
                            return results;
                        }
                    }
                    // Take advantage of querySelectorAll
                    if (!nonnativeSelectorCache[selector + " "] && (!rbuggyQSA || !rbuggyQSA.test(selector))) {
                        newSelector = selector;
                        newContext = context;
                        // qSA considers elements outside a scoping root when evaluating child or
                        // descendant combinators, which is not what we want.
                        // In such cases, we work around the behavior by prefixing every selector in the
                        // list with an ID selector referencing the scope context.
                        // The technique has to be used as well when a leading combinator is used
                        // as such selectors are not recognized by querySelectorAll.
                        // Thanks to Andrew Dupont for this technique.
                        if (nodeType === 1 && (rdescend.test(selector) || rleadingCombinator.test(selector))) {
                            // Expand context for sibling selectors
                            newContext = rsibling.test(selector) && testContext(context.parentNode) || context;
                            // We can use :scope instead of the ID hack if the browser
                            // supports it & if we're not changing the context.
                            // Support: IE 11+, Edge 17 - 18+
                            // IE/Edge sometimes throw a "Permission denied" error when
                            // strict-comparing two documents; shallow comparisons work.
                            // eslint-disable-next-line eqeqeq
                            if (newContext != context || !support.scope) {
                                // Capture the context ID, setting it first if necessary
                                if (nid = context.getAttribute("id")) nid = jQuery.escapeSelector(nid);
                                else context.setAttribute("id", nid = expando);
                            }
                            // Prefix every selector in the list
                            groups = tokenize(selector);
                            i = groups.length;
                            while(i--)groups[i] = (nid ? "#" + nid : ":scope") + " " + toSelector(groups[i]);
                            newSelector = groups.join(",");
                        }
                        try {
                            push.apply(results, newContext.querySelectorAll(newSelector));
                            return results;
                        } catch (qsaError) {
                            nonnativeSelectorCache(selector, true);
                        } finally{
                            if (nid === expando) context.removeAttribute("id");
                        }
                    }
                }
            }
            // All others
            return select(selector.replace(rtrimCSS, "$1"), context, results, seed);
        }
        /**
 * Create key-value caches of limited size
 * @returns {function(string, object)} Returns the Object data after storing it on itself with
 *	property name the (space-suffixed) string and (if the cache is larger than Expr.cacheLength)
 *	deleting the oldest entry
 */ function createCache() {
            var keys = [];
            function cache(key, value) {
                // Use (key + " ") to avoid collision with native prototype properties
                // (see https://github.com/jquery/sizzle/issues/157)
                if (keys.push(key + " ") > Expr.cacheLength) // Only keep the most recent entries
                delete cache[keys.shift()];
                return cache[key + " "] = value;
            }
            return cache;
        }
        /**
 * Mark a function for special use by jQuery selector module
 * @param {Function} fn The function to mark
 */ function markFunction(fn) {
            fn[expando] = true;
            return fn;
        }
        /**
 * Support testing using an element
 * @param {Function} fn Passed the created element and returns a boolean result
 */ function assert(fn) {
            var el = document.createElement("fieldset");
            try {
                return !!fn(el);
            } catch (e) {
                return false;
            } finally{
                // Remove from its parent by default
                if (el.parentNode) el.parentNode.removeChild(el);
                // release memory in IE
                el = null;
            }
        }
        /**
 * Returns a function to use in pseudos for input types
 * @param {String} type
 */ function createInputPseudo(type) {
            return function(elem) {
                return nodeName(elem, "input") && elem.type === type;
            };
        }
        /**
 * Returns a function to use in pseudos for buttons
 * @param {String} type
 */ function createButtonPseudo(type) {
            return function(elem) {
                return (nodeName(elem, "input") || nodeName(elem, "button")) && elem.type === type;
            };
        }
        /**
 * Returns a function to use in pseudos for :enabled/:disabled
 * @param {Boolean} disabled true for :disabled; false for :enabled
 */ function createDisabledPseudo(disabled) {
            // Known :disabled false positives: fieldset[disabled] > legend:nth-of-type(n+2) :can-disable
            return function(elem) {
                // Only certain elements can match :enabled or :disabled
                // https://html.spec.whatwg.org/multipage/scripting.html#selector-enabled
                // https://html.spec.whatwg.org/multipage/scripting.html#selector-disabled
                if ("form" in elem) {
                    // Check for inherited disabledness on relevant non-disabled elements:
                    // * listed form-associated elements in a disabled fieldset
                    //   https://html.spec.whatwg.org/multipage/forms.html#category-listed
                    //   https://html.spec.whatwg.org/multipage/forms.html#concept-fe-disabled
                    // * option elements in a disabled optgroup
                    //   https://html.spec.whatwg.org/multipage/forms.html#concept-option-disabled
                    // All such elements have a "form" property.
                    if (elem.parentNode && elem.disabled === false) {
                        // Option elements defer to a parent optgroup if present
                        if ("label" in elem) {
                            if ("label" in elem.parentNode) return elem.parentNode.disabled === disabled;
                            else return elem.disabled === disabled;
                        }
                        // Support: IE 6 - 11+
                        // Use the isDisabled shortcut property to check for disabled fieldset ancestors
                        return elem.isDisabled === disabled || // Where there is no isDisabled, check manually
                        elem.isDisabled !== !disabled && inDisabledFieldset(elem) === disabled;
                    }
                    return elem.disabled === disabled;
                // Try to winnow out elements that can't be disabled before trusting the disabled property.
                // Some victims get caught in our net (label, legend, menu, track), but it shouldn't
                // even exist on them, let alone have a boolean value.
                } else if ("label" in elem) return elem.disabled === disabled;
                // Remaining elements are neither :enabled nor :disabled
                return false;
            };
        }
        /**
 * Returns a function to use in pseudos for positionals
 * @param {Function} fn
 */ function createPositionalPseudo(fn) {
            return markFunction(function(argument) {
                argument = +argument;
                return markFunction(function(seed, matches) {
                    var j, matchIndexes = fn([], seed.length, argument), i = matchIndexes.length;
                    // Match elements found at the specified indexes
                    while(i--)if (seed[j = matchIndexes[i]]) seed[j] = !(matches[j] = seed[j]);
                });
            });
        }
        /**
 * Checks a node for validity as a jQuery selector context
 * @param {Element|Object=} context
 * @returns {Element|Object|Boolean} The input node if acceptable, otherwise a falsy value
 */ function testContext(context) {
            return context && typeof context.getElementsByTagName !== "undefined" && context;
        }
        /**
 * Sets document-related variables once based on the current document
 * @param {Element|Object} [node] An element or document object to use to set the document
 * @returns {Object} Returns the current document
 */ function setDocument(node) {
            var subWindow, doc = node ? node.ownerDocument || node : preferredDoc;
            // Return early if doc is invalid or already selected
            // Support: IE 11+, Edge 17 - 18+
            // IE/Edge sometimes throw a "Permission denied" error when strict-comparing
            // two documents; shallow comparisons work.
            // eslint-disable-next-line eqeqeq
            if (doc == document || doc.nodeType !== 9 || !doc.documentElement) return document;
            // Update global variables
            document = doc;
            documentElement = document.documentElement;
            documentIsHTML = !jQuery.isXMLDoc(document);
            // Support: iOS 7 only, IE 9 - 11+
            // Older browsers didn't support unprefixed `matches`.
            matches = documentElement.matches || documentElement.webkitMatchesSelector || documentElement.msMatchesSelector;
            // Support: IE 9 - 11+, Edge 12 - 18+
            // Accessing iframe documents after unload throws "permission denied" errors (see trac-13936)
            // Support: IE 11+, Edge 17 - 18+
            // IE/Edge sometimes throw a "Permission denied" error when strict-comparing
            // two documents; shallow comparisons work.
            // eslint-disable-next-line eqeqeq
            if (preferredDoc != document && (subWindow = document.defaultView) && subWindow.top !== subWindow) // Support: IE 9 - 11+, Edge 12 - 18+
            subWindow.addEventListener("unload", unloadHandler);
            // Support: IE <10
            // Check if getElementById returns elements by name
            // The broken getElementById methods don't pick up programmatically-set names,
            // so use a roundabout getElementsByName test
            support.getById = assert(function(el) {
                documentElement.appendChild(el).id = jQuery.expando;
                return !document.getElementsByName || !document.getElementsByName(jQuery.expando).length;
            });
            // Support: IE 9 only
            // Check to see if it's possible to do matchesSelector
            // on a disconnected node.
            support.disconnectedMatch = assert(function(el) {
                return matches.call(el, "*");
            });
            // Support: IE 9 - 11+, Edge 12 - 18+
            // IE/Edge don't support the :scope pseudo-class.
            support.scope = assert(function() {
                return document.querySelectorAll(":scope");
            });
            // Support: Chrome 105 - 111 only, Safari 15.4 - 16.3 only
            // Make sure the `:has()` argument is parsed unforgivingly.
            // We include `*` in the test to detect buggy implementations that are
            // _selectively_ forgiving (specifically when the list includes at least
            // one valid selector).
            // Note that we treat complete lack of support for `:has()` as if it were
            // spec-compliant support, which is fine because use of `:has()` in such
            // environments will fail in the qSA path and fall back to jQuery traversal
            // anyway.
            support.cssHas = assert(function() {
                try {
                    document.querySelector(":has(*,:jqfake)");
                    return false;
                } catch (e) {
                    return true;
                }
            });
            // ID filter and find
            if (support.getById) {
                Expr.filter.ID = function(id) {
                    var attrId = id.replace(runescape, funescape);
                    return function(elem) {
                        return elem.getAttribute("id") === attrId;
                    };
                };
                Expr.find.ID = function(id, context) {
                    if (typeof context.getElementById !== "undefined" && documentIsHTML) {
                        var elem = context.getElementById(id);
                        return elem ? [
                            elem
                        ] : [];
                    }
                };
            } else {
                Expr.filter.ID = function(id) {
                    var attrId = id.replace(runescape, funescape);
                    return function(elem) {
                        var node = typeof elem.getAttributeNode !== "undefined" && elem.getAttributeNode("id");
                        return node && node.value === attrId;
                    };
                };
                // Support: IE 6 - 7 only
                // getElementById is not reliable as a find shortcut
                Expr.find.ID = function(id, context) {
                    if (typeof context.getElementById !== "undefined" && documentIsHTML) {
                        var node, i, elems, elem = context.getElementById(id);
                        if (elem) {
                            // Verify the id attribute
                            node = elem.getAttributeNode("id");
                            if (node && node.value === id) return [
                                elem
                            ];
                            // Fall back on getElementsByName
                            elems = context.getElementsByName(id);
                            i = 0;
                            while(elem = elems[i++]){
                                node = elem.getAttributeNode("id");
                                if (node && node.value === id) return [
                                    elem
                                ];
                            }
                        }
                        return [];
                    }
                };
            }
            // Tag
            Expr.find.TAG = function(tag, context) {
                if (typeof context.getElementsByTagName !== "undefined") return context.getElementsByTagName(tag);
                else return context.querySelectorAll(tag);
            };
            // Class
            Expr.find.CLASS = function(className, context) {
                if (typeof context.getElementsByClassName !== "undefined" && documentIsHTML) return context.getElementsByClassName(className);
            };
            /* QSA/matchesSelector
	---------------------------------------------------------------------- */ // QSA and matchesSelector support
            rbuggyQSA = [];
            // Build QSA regex
            // Regex strategy adopted from Diego Perini
            assert(function(el) {
                var input;
                documentElement.appendChild(el).innerHTML = "<a id='" + expando + "' href='' disabled='disabled'></a>" + "<select id='" + expando + "-\r\\' disabled='disabled'>" + "<option selected=''></option></select>";
                // Support: iOS <=7 - 8 only
                // Boolean attributes and "value" are not treated correctly in some XML documents
                if (!el.querySelectorAll("[selected]").length) rbuggyQSA.push("\\[" + whitespace + "*(?:value|" + booleans + ")");
                // Support: iOS <=7 - 8 only
                if (!el.querySelectorAll("[id~=" + expando + "-]").length) rbuggyQSA.push("~=");
                // Support: iOS 8 only
                // https://bugs.webkit.org/show_bug.cgi?id=136851
                // In-page `selector#id sibling-combinator selector` fails
                if (!el.querySelectorAll("a#" + expando + "+*").length) rbuggyQSA.push(".#.+[+~]");
                // Support: Chrome <=105+, Firefox <=104+, Safari <=15.4+
                // In some of the document kinds, these selectors wouldn't work natively.
                // This is probably OK but for backwards compatibility we want to maintain
                // handling them through jQuery traversal in jQuery 3.x.
                if (!el.querySelectorAll(":checked").length) rbuggyQSA.push(":checked");
                // Support: Windows 8 Native Apps
                // The type and name attributes are restricted during .innerHTML assignment
                input = document.createElement("input");
                input.setAttribute("type", "hidden");
                el.appendChild(input).setAttribute("name", "D");
                // Support: IE 9 - 11+
                // IE's :disabled selector does not pick up the children of disabled fieldsets
                // Support: Chrome <=105+, Firefox <=104+, Safari <=15.4+
                // In some of the document kinds, these selectors wouldn't work natively.
                // This is probably OK but for backwards compatibility we want to maintain
                // handling them through jQuery traversal in jQuery 3.x.
                documentElement.appendChild(el).disabled = true;
                if (el.querySelectorAll(":disabled").length !== 2) rbuggyQSA.push(":enabled", ":disabled");
                // Support: IE 11+, Edge 15 - 18+
                // IE 11/Edge don't find elements on a `[name='']` query in some cases.
                // Adding a temporary attribute to the document before the selection works
                // around the issue.
                // Interestingly, IE 10 & older don't seem to have the issue.
                input = document.createElement("input");
                input.setAttribute("name", "");
                el.appendChild(input);
                if (!el.querySelectorAll("[name='']").length) rbuggyQSA.push("\\[" + whitespace + "*name" + whitespace + "*=" + whitespace + "*(?:''|\"\")");
            });
            if (!support.cssHas) // Support: Chrome 105 - 110+, Safari 15.4 - 16.3+
            // Our regular `try-catch` mechanism fails to detect natively-unsupported
            // pseudo-classes inside `:has()` (such as `:has(:contains("Foo"))`)
            // in browsers that parse the `:has()` argument as a forgiving selector list.
            // https://drafts.csswg.org/selectors/#relational now requires the argument
            // to be parsed unforgivingly, but browsers have not yet fully adjusted.
            rbuggyQSA.push(":has");
            rbuggyQSA = rbuggyQSA.length && new RegExp(rbuggyQSA.join("|"));
            /* Sorting
	---------------------------------------------------------------------- */ // Document order sorting
            sortOrder = function(a, b) {
                // Flag for duplicate removal
                if (a === b) {
                    hasDuplicate = true;
                    return 0;
                }
                // Sort on method existence if only one input has compareDocumentPosition
                var compare = !a.compareDocumentPosition - !b.compareDocumentPosition;
                if (compare) return compare;
                // Calculate position if both inputs belong to the same document
                // Support: IE 11+, Edge 17 - 18+
                // IE/Edge sometimes throw a "Permission denied" error when strict-comparing
                // two documents; shallow comparisons work.
                // eslint-disable-next-line eqeqeq
                compare = (a.ownerDocument || a) == (b.ownerDocument || b) ? a.compareDocumentPosition(b) : // Otherwise we know they are disconnected
                1;
                // Disconnected nodes
                if (compare & 1 || !support.sortDetached && b.compareDocumentPosition(a) === compare) {
                    // Choose the first element that is related to our preferred document
                    // Support: IE 11+, Edge 17 - 18+
                    // IE/Edge sometimes throw a "Permission denied" error when strict-comparing
                    // two documents; shallow comparisons work.
                    // eslint-disable-next-line eqeqeq
                    if (a === document || a.ownerDocument == preferredDoc && find.contains(preferredDoc, a)) return -1;
                    // Support: IE 11+, Edge 17 - 18+
                    // IE/Edge sometimes throw a "Permission denied" error when strict-comparing
                    // two documents; shallow comparisons work.
                    // eslint-disable-next-line eqeqeq
                    if (b === document || b.ownerDocument == preferredDoc && find.contains(preferredDoc, b)) return 1;
                    // Maintain original order
                    return sortInput ? indexOf.call(sortInput, a) - indexOf.call(sortInput, b) : 0;
                }
                return compare & 4 ? -1 : 1;
            };
            return document;
        }
        find.matches = function(expr, elements) {
            return find(expr, null, null, elements);
        };
        find.matchesSelector = function(elem, expr) {
            setDocument(elem);
            if (documentIsHTML && !nonnativeSelectorCache[expr + " "] && (!rbuggyQSA || !rbuggyQSA.test(expr))) try {
                var ret = matches.call(elem, expr);
                // IE 9's matchesSelector returns false on disconnected nodes
                if (ret || support.disconnectedMatch || // As well, disconnected nodes are said to be in a document
                // fragment in IE 9
                elem.document && elem.document.nodeType !== 11) return ret;
            } catch (e) {
                nonnativeSelectorCache(expr, true);
            }
            return find(expr, document, null, [
                elem
            ]).length > 0;
        };
        find.contains = function(context, elem) {
            // Set document vars if needed
            // Support: IE 11+, Edge 17 - 18+
            // IE/Edge sometimes throw a "Permission denied" error when strict-comparing
            // two documents; shallow comparisons work.
            // eslint-disable-next-line eqeqeq
            if ((context.ownerDocument || context) != document) setDocument(context);
            return jQuery.contains(context, elem);
        };
        find.attr = function(elem, name) {
            // Set document vars if needed
            // Support: IE 11+, Edge 17 - 18+
            // IE/Edge sometimes throw a "Permission denied" error when strict-comparing
            // two documents; shallow comparisons work.
            // eslint-disable-next-line eqeqeq
            if ((elem.ownerDocument || elem) != document) setDocument(elem);
            var fn = Expr.attrHandle[name.toLowerCase()], // Don't get fooled by Object.prototype properties (see trac-13807)
            val = fn && hasOwn.call(Expr.attrHandle, name.toLowerCase()) ? fn(elem, name, !documentIsHTML) : undefined;
            if (val !== undefined) return val;
            return elem.getAttribute(name);
        };
        find.error = function(msg) {
            throw new Error("Syntax error, unrecognized expression: " + msg);
        };
        /**
 * Document sorting and removing duplicates
 * @param {ArrayLike} results
 */ jQuery.uniqueSort = function(results) {
            var elem, duplicates = [], j = 0, i = 0;
            // Unless we *know* we can detect duplicates, assume their presence
            //
            // Support: Android <=4.0+
            // Testing for detecting duplicates is unpredictable so instead assume we can't
            // depend on duplicate detection in all browsers without a stable sort.
            hasDuplicate = !support.sortStable;
            sortInput = !support.sortStable && slice.call(results, 0);
            sort.call(results, sortOrder);
            if (hasDuplicate) {
                while(elem = results[i++])if (elem === results[i]) j = duplicates.push(i);
                while(j--)splice.call(results, duplicates[j], 1);
            }
            // Clear input after sorting to release objects
            // See https://github.com/jquery/sizzle/pull/225
            sortInput = null;
            return results;
        };
        jQuery.fn.uniqueSort = function() {
            return this.pushStack(jQuery.uniqueSort(slice.apply(this)));
        };
        Expr = jQuery.expr = {
            // Can be adjusted by the user
            cacheLength: 50,
            createPseudo: markFunction,
            match: matchExpr,
            attrHandle: {},
            find: {},
            relative: {
                ">": {
                    dir: "parentNode",
                    first: true
                },
                " ": {
                    dir: "parentNode"
                },
                "+": {
                    dir: "previousSibling",
                    first: true
                },
                "~": {
                    dir: "previousSibling"
                }
            },
            preFilter: {
                ATTR: function(match) {
                    match[1] = match[1].replace(runescape, funescape);
                    // Move the given value to match[3] whether quoted or unquoted
                    match[3] = (match[3] || match[4] || match[5] || "").replace(runescape, funescape);
                    if (match[2] === "~=") match[3] = " " + match[3] + " ";
                    return match.slice(0, 4);
                },
                CHILD: function(match) {
                    /* matches from matchExpr["CHILD"]
				1 type (only|nth|...)
				2 what (child|of-type)
				3 argument (even|odd|\d*|\d*n([+-]\d+)?|...)
				4 xn-component of xn+y argument ([+-]?\d*n|)
				5 sign of xn-component
				6 x of xn-component
				7 sign of y-component
				8 y of y-component
			*/ match[1] = match[1].toLowerCase();
                    if (match[1].slice(0, 3) === "nth") {
                        // nth-* requires argument
                        if (!match[3]) find.error(match[0]);
                        // numeric x and y parameters for Expr.filter.CHILD
                        // remember that false/true cast respectively to 0/1
                        match[4] = +(match[4] ? match[5] + (match[6] || 1) : 2 * (match[3] === "even" || match[3] === "odd"));
                        match[5] = +(match[7] + match[8] || match[3] === "odd");
                    // other types prohibit arguments
                    } else if (match[3]) find.error(match[0]);
                    return match;
                },
                PSEUDO: function(match) {
                    var excess, unquoted = !match[6] && match[2];
                    if (matchExpr.CHILD.test(match[0])) return null;
                    // Accept quoted arguments as-is
                    if (match[3]) match[2] = match[4] || match[5] || "";
                    else if (unquoted && rpseudo.test(unquoted) && // Get excess from tokenize (recursively)
                    (excess = tokenize(unquoted, true)) && // advance to the next closing parenthesis
                    (excess = unquoted.indexOf(")", unquoted.length - excess) - unquoted.length)) {
                        // excess is a negative index
                        match[0] = match[0].slice(0, excess);
                        match[2] = unquoted.slice(0, excess);
                    }
                    // Return only captures needed by the pseudo filter method (type and argument)
                    return match.slice(0, 3);
                }
            },
            filter: {
                TAG: function(nodeNameSelector) {
                    var expectedNodeName = nodeNameSelector.replace(runescape, funescape).toLowerCase();
                    return nodeNameSelector === "*" ? function() {
                        return true;
                    } : function(elem) {
                        return nodeName(elem, expectedNodeName);
                    };
                },
                CLASS: function(className) {
                    var pattern = classCache[className + " "];
                    return pattern || (pattern = new RegExp("(^|" + whitespace + ")" + className + "(" + whitespace + "|$)"), classCache(className, function(elem) {
                        return pattern.test(typeof elem.className === "string" && elem.className || typeof elem.getAttribute !== "undefined" && elem.getAttribute("class") || "");
                    }));
                },
                ATTR: function(name, operator, check) {
                    return function(elem) {
                        var result = find.attr(elem, name);
                        if (result == null) return operator === "!=";
                        if (!operator) return true;
                        result += "";
                        if (operator === "=") return result === check;
                        if (operator === "!=") return result !== check;
                        if (operator === "^=") return check && result.indexOf(check) === 0;
                        if (operator === "*=") return check && result.indexOf(check) > -1;
                        if (operator === "$=") return check && result.slice(-check.length) === check;
                        if (operator === "~=") return (" " + result.replace(rwhitespace, " ") + " ").indexOf(check) > -1;
                        if (operator === "|=") return result === check || result.slice(0, check.length + 1) === check + "-";
                        return false;
                    };
                },
                CHILD: function(type, what, _argument, first, last) {
                    var simple = type.slice(0, 3) !== "nth", forward = type.slice(-4) !== "last", ofType = what === "of-type";
                    return first === 1 && last === 0 ? // Shortcut for :nth-*(n)
                    function(elem) {
                        return !!elem.parentNode;
                    } : function(elem, _context, xml) {
                        var cache, outerCache, node, nodeIndex, start, dir = simple !== forward ? "nextSibling" : "previousSibling", parent = elem.parentNode, name = ofType && elem.nodeName.toLowerCase(), useCache = !xml && !ofType, diff = false;
                        if (parent) {
                            // :(first|last|only)-(child|of-type)
                            if (simple) {
                                while(dir){
                                    node = elem;
                                    while(node = node[dir]){
                                        if (ofType ? nodeName(node, name) : node.nodeType === 1) return false;
                                    }
                                    // Reverse direction for :only-* (if we haven't yet done so)
                                    start = dir = type === "only" && !start && "nextSibling";
                                }
                                return true;
                            }
                            start = [
                                forward ? parent.firstChild : parent.lastChild
                            ];
                            // non-xml :nth-child(...) stores cache data on `parent`
                            if (forward && useCache) {
                                // Seek `elem` from a previously-cached index
                                outerCache = parent[expando] || (parent[expando] = {});
                                cache = outerCache[type] || [];
                                nodeIndex = cache[0] === dirruns && cache[1];
                                diff = nodeIndex && cache[2];
                                node = nodeIndex && parent.childNodes[nodeIndex];
                                while(node = ++nodeIndex && node && node[dir] || // Fallback to seeking `elem` from the start
                                (diff = nodeIndex = 0) || start.pop())// When found, cache indexes on `parent` and break
                                if (node.nodeType === 1 && ++diff && node === elem) {
                                    outerCache[type] = [
                                        dirruns,
                                        nodeIndex,
                                        diff
                                    ];
                                    break;
                                }
                            } else {
                                // Use previously-cached element index if available
                                if (useCache) {
                                    outerCache = elem[expando] || (elem[expando] = {});
                                    cache = outerCache[type] || [];
                                    nodeIndex = cache[0] === dirruns && cache[1];
                                    diff = nodeIndex;
                                }
                                // xml :nth-child(...)
                                // or :nth-last-child(...) or :nth(-last)?-of-type(...)
                                if (diff === false) {
                                    // Use the same loop as above to seek `elem` from the start
                                    while(node = ++nodeIndex && node && node[dir] || (diff = nodeIndex = 0) || start.pop())if ((ofType ? nodeName(node, name) : node.nodeType === 1) && ++diff) {
                                        // Cache the index of each encountered element
                                        if (useCache) {
                                            outerCache = node[expando] || (node[expando] = {});
                                            outerCache[type] = [
                                                dirruns,
                                                diff
                                            ];
                                        }
                                        if (node === elem) break;
                                    }
                                }
                            }
                            // Incorporate the offset, then check against cycle size
                            diff -= last;
                            return diff === first || diff % first === 0 && diff / first >= 0;
                        }
                    };
                },
                PSEUDO: function(pseudo, argument) {
                    // pseudo-class names are case-insensitive
                    // https://www.w3.org/TR/selectors/#pseudo-classes
                    // Prioritize by case sensitivity in case custom pseudos are added with uppercase letters
                    // Remember that setFilters inherits from pseudos
                    var args, fn = Expr.pseudos[pseudo] || Expr.setFilters[pseudo.toLowerCase()] || find.error("unsupported pseudo: " + pseudo);
                    // The user may use createPseudo to indicate that
                    // arguments are needed to create the filter function
                    // just as jQuery does
                    if (fn[expando]) return fn(argument);
                    // But maintain support for old signatures
                    if (fn.length > 1) {
                        args = [
                            pseudo,
                            pseudo,
                            "",
                            argument
                        ];
                        return Expr.setFilters.hasOwnProperty(pseudo.toLowerCase()) ? markFunction(function(seed, matches) {
                            var idx, matched = fn(seed, argument), i = matched.length;
                            while(i--){
                                idx = indexOf.call(seed, matched[i]);
                                seed[idx] = !(matches[idx] = matched[i]);
                            }
                        }) : function(elem) {
                            return fn(elem, 0, args);
                        };
                    }
                    return fn;
                }
            },
            pseudos: {
                // Potentially complex pseudos
                not: markFunction(function(selector) {
                    // Trim the selector passed to compile
                    // to avoid treating leading and trailing
                    // spaces as combinators
                    var input = [], results = [], matcher = compile(selector.replace(rtrimCSS, "$1"));
                    return matcher[expando] ? markFunction(function(seed, matches, _context, xml) {
                        var elem, unmatched = matcher(seed, null, xml, []), i = seed.length;
                        // Match elements unmatched by `matcher`
                        while(i--)if (elem = unmatched[i]) seed[i] = !(matches[i] = elem);
                    }) : function(elem, _context, xml) {
                        input[0] = elem;
                        matcher(input, null, xml, results);
                        // Don't keep the element
                        // (see https://github.com/jquery/sizzle/issues/299)
                        input[0] = null;
                        return !results.pop();
                    };
                }),
                has: markFunction(function(selector) {
                    return function(elem) {
                        return find(selector, elem).length > 0;
                    };
                }),
                contains: markFunction(function(text) {
                    text = text.replace(runescape, funescape);
                    return function(elem) {
                        return (elem.textContent || jQuery.text(elem)).indexOf(text) > -1;
                    };
                }),
                // "Whether an element is represented by a :lang() selector
                // is based solely on the element's language value
                // being equal to the identifier C,
                // or beginning with the identifier C immediately followed by "-".
                // The matching of C against the element's language value is performed case-insensitively.
                // The identifier C does not have to be a valid language name."
                // https://www.w3.org/TR/selectors/#lang-pseudo
                lang: markFunction(function(lang) {
                    // lang value must be a valid identifier
                    if (!ridentifier.test(lang || "")) find.error("unsupported lang: " + lang);
                    lang = lang.replace(runescape, funescape).toLowerCase();
                    return function(elem) {
                        var elemLang;
                        do if (elemLang = documentIsHTML ? elem.lang : elem.getAttribute("xml:lang") || elem.getAttribute("lang")) {
                            elemLang = elemLang.toLowerCase();
                            return elemLang === lang || elemLang.indexOf(lang + "-") === 0;
                        }
                        while ((elem = elem.parentNode) && elem.nodeType === 1);
                        return false;
                    };
                }),
                // Miscellaneous
                target: function(elem) {
                    var hash = window1.location && window1.location.hash;
                    return hash && hash.slice(1) === elem.id;
                },
                root: function(elem) {
                    return elem === documentElement;
                },
                focus: function(elem) {
                    return elem === safeActiveElement() && document.hasFocus() && !!(elem.type || elem.href || ~elem.tabIndex);
                },
                // Boolean properties
                enabled: createDisabledPseudo(false),
                disabled: createDisabledPseudo(true),
                checked: function(elem) {
                    // In CSS3, :checked should return both checked and selected elements
                    // https://www.w3.org/TR/2011/REC-css3-selectors-20110929/#checked
                    return nodeName(elem, "input") && !!elem.checked || nodeName(elem, "option") && !!elem.selected;
                },
                selected: function(elem) {
                    // Support: IE <=11+
                    // Accessing the selectedIndex property
                    // forces the browser to treat the default option as
                    // selected when in an optgroup.
                    if (elem.parentNode) // eslint-disable-next-line no-unused-expressions
                    elem.parentNode.selectedIndex;
                    return elem.selected === true;
                },
                // Contents
                empty: function(elem) {
                    // https://www.w3.org/TR/selectors/#empty-pseudo
                    // :empty is negated by element (1) or content nodes (text: 3; cdata: 4; entity ref: 5),
                    //   but not by others (comment: 8; processing instruction: 7; etc.)
                    // nodeType < 6 works because attributes (2) do not appear as children
                    for(elem = elem.firstChild; elem; elem = elem.nextSibling){
                        if (elem.nodeType < 6) return false;
                    }
                    return true;
                },
                parent: function(elem) {
                    return !Expr.pseudos.empty(elem);
                },
                // Element/input types
                header: function(elem) {
                    return rheader.test(elem.nodeName);
                },
                input: function(elem) {
                    return rinputs.test(elem.nodeName);
                },
                button: function(elem) {
                    return nodeName(elem, "input") && elem.type === "button" || nodeName(elem, "button");
                },
                text: function(elem) {
                    var attr;
                    return nodeName(elem, "input") && elem.type === "text" && // Support: IE <10 only
                    // New HTML5 attribute values (e.g., "search") appear
                    // with elem.type === "text"
                    ((attr = elem.getAttribute("type")) == null || attr.toLowerCase() === "text");
                },
                // Position-in-collection
                first: createPositionalPseudo(function() {
                    return [
                        0
                    ];
                }),
                last: createPositionalPseudo(function(_matchIndexes, length) {
                    return [
                        length - 1
                    ];
                }),
                eq: createPositionalPseudo(function(_matchIndexes, length, argument) {
                    return [
                        argument < 0 ? argument + length : argument
                    ];
                }),
                even: createPositionalPseudo(function(matchIndexes, length) {
                    var i = 0;
                    for(; i < length; i += 2)matchIndexes.push(i);
                    return matchIndexes;
                }),
                odd: createPositionalPseudo(function(matchIndexes, length) {
                    var i = 1;
                    for(; i < length; i += 2)matchIndexes.push(i);
                    return matchIndexes;
                }),
                lt: createPositionalPseudo(function(matchIndexes, length, argument) {
                    var i;
                    if (argument < 0) i = argument + length;
                    else if (argument > length) i = length;
                    else i = argument;
                    for(; --i >= 0;)matchIndexes.push(i);
                    return matchIndexes;
                }),
                gt: createPositionalPseudo(function(matchIndexes, length, argument) {
                    var i = argument < 0 ? argument + length : argument;
                    for(; ++i < length;)matchIndexes.push(i);
                    return matchIndexes;
                })
            }
        };
        Expr.pseudos.nth = Expr.pseudos.eq;
        // Add button/input type pseudos
        for(i in {
            radio: true,
            checkbox: true,
            file: true,
            password: true,
            image: true
        })Expr.pseudos[i] = createInputPseudo(i);
        for(i in {
            submit: true,
            reset: true
        })Expr.pseudos[i] = createButtonPseudo(i);
        // Easy API for creating new setFilters
        function setFilters() {}
        setFilters.prototype = Expr.filters = Expr.pseudos;
        Expr.setFilters = new setFilters();
        function tokenize(selector, parseOnly) {
            var matched, match, tokens, type, soFar, groups, preFilters, cached = tokenCache[selector + " "];
            if (cached) return parseOnly ? 0 : cached.slice(0);
            soFar = selector;
            groups = [];
            preFilters = Expr.preFilter;
            while(soFar){
                // Comma and first run
                if (!matched || (match = rcomma.exec(soFar))) {
                    if (match) // Don't consume trailing commas as valid
                    soFar = soFar.slice(match[0].length) || soFar;
                    groups.push(tokens = []);
                }
                matched = false;
                // Combinators
                if (match = rleadingCombinator.exec(soFar)) {
                    matched = match.shift();
                    tokens.push({
                        value: matched,
                        // Cast descendant combinators to space
                        type: match[0].replace(rtrimCSS, " ")
                    });
                    soFar = soFar.slice(matched.length);
                }
                // Filters
                for(type in Expr.filter)if ((match = matchExpr[type].exec(soFar)) && (!preFilters[type] || (match = preFilters[type](match)))) {
                    matched = match.shift();
                    tokens.push({
                        value: matched,
                        type: type,
                        matches: match
                    });
                    soFar = soFar.slice(matched.length);
                }
                if (!matched) break;
            }
            // Return the length of the invalid excess
            // if we're just parsing
            // Otherwise, throw an error or return tokens
            if (parseOnly) return soFar.length;
            return soFar ? find.error(selector) : // Cache the tokens
            tokenCache(selector, groups).slice(0);
        }
        function toSelector(tokens) {
            var i = 0, len = tokens.length, selector = "";
            for(; i < len; i++)selector += tokens[i].value;
            return selector;
        }
        function addCombinator(matcher, combinator, base) {
            var dir = combinator.dir, skip = combinator.next, key = skip || dir, checkNonElements = base && key === "parentNode", doneName = done++;
            return combinator.first ? // Check against closest ancestor/preceding element
            function(elem, context, xml) {
                while(elem = elem[dir]){
                    if (elem.nodeType === 1 || checkNonElements) return matcher(elem, context, xml);
                }
                return false;
            } : // Check against all ancestor/preceding elements
            function(elem, context, xml) {
                var oldCache, outerCache, newCache = [
                    dirruns,
                    doneName
                ];
                // We can't set arbitrary data on XML nodes, so they don't benefit from combinator caching
                if (xml) {
                    while(elem = elem[dir])if (elem.nodeType === 1 || checkNonElements) {
                        if (matcher(elem, context, xml)) return true;
                    }
                } else {
                    while(elem = elem[dir])if (elem.nodeType === 1 || checkNonElements) {
                        outerCache = elem[expando] || (elem[expando] = {});
                        if (skip && nodeName(elem, skip)) elem = elem[dir] || elem;
                        else if ((oldCache = outerCache[key]) && oldCache[0] === dirruns && oldCache[1] === doneName) // Assign to newCache so results back-propagate to previous elements
                        return newCache[2] = oldCache[2];
                        else {
                            // Reuse newcache so results back-propagate to previous elements
                            outerCache[key] = newCache;
                            // A match means we're done; a fail means we have to keep checking
                            if (newCache[2] = matcher(elem, context, xml)) return true;
                        }
                    }
                }
                return false;
            };
        }
        function elementMatcher(matchers) {
            return matchers.length > 1 ? function(elem, context, xml) {
                var i = matchers.length;
                while(i--){
                    if (!matchers[i](elem, context, xml)) return false;
                }
                return true;
            } : matchers[0];
        }
        function multipleContexts(selector, contexts, results) {
            var i = 0, len = contexts.length;
            for(; i < len; i++)find(selector, contexts[i], results);
            return results;
        }
        function condense(unmatched, map, filter, context, xml) {
            var elem, newUnmatched = [], i = 0, len = unmatched.length, mapped = map != null;
            for(; i < len; i++){
                if (elem = unmatched[i]) {
                    if (!filter || filter(elem, context, xml)) {
                        newUnmatched.push(elem);
                        if (mapped) map.push(i);
                    }
                }
            }
            return newUnmatched;
        }
        function setMatcher(preFilter, selector, matcher, postFilter, postFinder, postSelector) {
            if (postFilter && !postFilter[expando]) postFilter = setMatcher(postFilter);
            if (postFinder && !postFinder[expando]) postFinder = setMatcher(postFinder, postSelector);
            return markFunction(function(seed, results, context, xml) {
                var temp, i, elem, matcherOut, preMap = [], postMap = [], preexisting = results.length, // Get initial elements from seed or context
                elems = seed || multipleContexts(selector || "*", context.nodeType ? [
                    context
                ] : context, []), // Prefilter to get matcher input, preserving a map for seed-results synchronization
                matcherIn = preFilter && (seed || !selector) ? condense(elems, preMap, preFilter, context, xml) : elems;
                if (matcher) {
                    // If we have a postFinder, or filtered seed, or non-seed postFilter
                    // or preexisting results,
                    matcherOut = postFinder || (seed ? preFilter : preexisting || postFilter) ? // ...intermediate processing is necessary
                    [] : // ...otherwise use results directly
                    results;
                    // Find primary matches
                    matcher(matcherIn, matcherOut, context, xml);
                } else matcherOut = matcherIn;
                // Apply postFilter
                if (postFilter) {
                    temp = condense(matcherOut, postMap);
                    postFilter(temp, [], context, xml);
                    // Un-match failing elements by moving them back to matcherIn
                    i = temp.length;
                    while(i--)if (elem = temp[i]) matcherOut[postMap[i]] = !(matcherIn[postMap[i]] = elem);
                }
                if (seed) {
                    if (postFinder || preFilter) {
                        if (postFinder) {
                            // Get the final matcherOut by condensing this intermediate into postFinder contexts
                            temp = [];
                            i = matcherOut.length;
                            while(i--)if (elem = matcherOut[i]) // Restore matcherIn since elem is not yet a final match
                            temp.push(matcherIn[i] = elem);
                            postFinder(null, matcherOut = [], temp, xml);
                        }
                        // Move matched elements from seed to results to keep them synchronized
                        i = matcherOut.length;
                        while(i--)if ((elem = matcherOut[i]) && (temp = postFinder ? indexOf.call(seed, elem) : preMap[i]) > -1) seed[temp] = !(results[temp] = elem);
                    }
                } else {
                    matcherOut = condense(matcherOut === results ? matcherOut.splice(preexisting, matcherOut.length) : matcherOut);
                    if (postFinder) postFinder(null, results, matcherOut, xml);
                    else push.apply(results, matcherOut);
                }
            });
        }
        function matcherFromTokens(tokens) {
            var checkContext, matcher, j, len = tokens.length, leadingRelative = Expr.relative[tokens[0].type], implicitRelative = leadingRelative || Expr.relative[" "], i = leadingRelative ? 1 : 0, // The foundational matcher ensures that elements are reachable from top-level context(s)
            matchContext = addCombinator(function(elem) {
                return elem === checkContext;
            }, implicitRelative, true), matchAnyContext = addCombinator(function(elem) {
                return indexOf.call(checkContext, elem) > -1;
            }, implicitRelative, true), matchers = [
                function(elem, context, xml) {
                    // Support: IE 11+, Edge 17 - 18+
                    // IE/Edge sometimes throw a "Permission denied" error when strict-comparing
                    // two documents; shallow comparisons work.
                    // eslint-disable-next-line eqeqeq
                    var ret = !leadingRelative && (xml || context != outermostContext) || ((checkContext = context).nodeType ? matchContext(elem, context, xml) : matchAnyContext(elem, context, xml));
                    // Avoid hanging onto element
                    // (see https://github.com/jquery/sizzle/issues/299)
                    checkContext = null;
                    return ret;
                }
            ];
            for(; i < len; i++)if (matcher = Expr.relative[tokens[i].type]) matchers = [
                addCombinator(elementMatcher(matchers), matcher)
            ];
            else {
                matcher = Expr.filter[tokens[i].type].apply(null, tokens[i].matches);
                // Return special upon seeing a positional matcher
                if (matcher[expando]) {
                    // Find the next relative operator (if any) for proper handling
                    j = ++i;
                    for(; j < len; j++){
                        if (Expr.relative[tokens[j].type]) break;
                    }
                    return setMatcher(i > 1 && elementMatcher(matchers), i > 1 && toSelector(// If the preceding token was a descendant combinator, insert an implicit any-element `*`
                    tokens.slice(0, i - 1).concat({
                        value: tokens[i - 2].type === " " ? "*" : ""
                    })).replace(rtrimCSS, "$1"), matcher, i < j && matcherFromTokens(tokens.slice(i, j)), j < len && matcherFromTokens(tokens = tokens.slice(j)), j < len && toSelector(tokens));
                }
                matchers.push(matcher);
            }
            return elementMatcher(matchers);
        }
        function matcherFromGroupMatchers(elementMatchers, setMatchers) {
            var bySet = setMatchers.length > 0, byElement = elementMatchers.length > 0, superMatcher = function(seed, context, xml, results, outermost) {
                var elem, j, matcher, matchedCount = 0, i = "0", unmatched = seed && [], setMatched = [], contextBackup = outermostContext, // We must always have either seed elements or outermost context
                elems = seed || byElement && Expr.find.TAG("*", outermost), // Use integer dirruns iff this is the outermost matcher
                dirrunsUnique = dirruns += contextBackup == null ? 1 : Math.random() || 0.1, len = elems.length;
                if (outermost) // Support: IE 11+, Edge 17 - 18+
                // IE/Edge sometimes throw a "Permission denied" error when strict-comparing
                // two documents; shallow comparisons work.
                // eslint-disable-next-line eqeqeq
                outermostContext = context == document || context || outermost;
                // Add elements passing elementMatchers directly to results
                // Support: iOS <=7 - 9 only
                // Tolerate NodeList properties (IE: "length"; Safari: <number>) matching
                // elements by id. (see trac-14142)
                for(; i !== len && (elem = elems[i]) != null; i++){
                    if (byElement && elem) {
                        j = 0;
                        // Support: IE 11+, Edge 17 - 18+
                        // IE/Edge sometimes throw a "Permission denied" error when strict-comparing
                        // two documents; shallow comparisons work.
                        // eslint-disable-next-line eqeqeq
                        if (!context && elem.ownerDocument != document) {
                            setDocument(elem);
                            xml = !documentIsHTML;
                        }
                        while(matcher = elementMatchers[j++])if (matcher(elem, context || document, xml)) {
                            push.call(results, elem);
                            break;
                        }
                        if (outermost) dirruns = dirrunsUnique;
                    }
                    // Track unmatched elements for set filters
                    if (bySet) {
                        // They will have gone through all possible matchers
                        if (elem = !matcher && elem) matchedCount--;
                        // Lengthen the array for every element, matched or not
                        if (seed) unmatched.push(elem);
                    }
                }
                // `i` is now the count of elements visited above, and adding it to `matchedCount`
                // makes the latter nonnegative.
                matchedCount += i;
                // Apply set filters to unmatched elements
                // NOTE: This can be skipped if there are no unmatched elements (i.e., `matchedCount`
                // equals `i`), unless we didn't visit _any_ elements in the above loop because we have
                // no element matchers and no seed.
                // Incrementing an initially-string "0" `i` allows `i` to remain a string only in that
                // case, which will result in a "00" `matchedCount` that differs from `i` but is also
                // numerically zero.
                if (bySet && i !== matchedCount) {
                    j = 0;
                    while(matcher = setMatchers[j++])matcher(unmatched, setMatched, context, xml);
                    if (seed) {
                        // Reintegrate element matches to eliminate the need for sorting
                        if (matchedCount > 0) {
                            while(i--)if (!(unmatched[i] || setMatched[i])) setMatched[i] = pop.call(results);
                        }
                        // Discard index placeholder values to get only actual matches
                        setMatched = condense(setMatched);
                    }
                    // Add matches to results
                    push.apply(results, setMatched);
                    // Seedless set matches succeeding multiple successful matchers stipulate sorting
                    if (outermost && !seed && setMatched.length > 0 && matchedCount + setMatchers.length > 1) jQuery.uniqueSort(results);
                }
                // Override manipulation of globals by nested matchers
                if (outermost) {
                    dirruns = dirrunsUnique;
                    outermostContext = contextBackup;
                }
                return unmatched;
            };
            return bySet ? markFunction(superMatcher) : superMatcher;
        }
        function compile(selector, match /* Internal Use Only */ ) {
            var i, setMatchers = [], elementMatchers = [], cached = compilerCache[selector + " "];
            if (!cached) {
                // Generate a function of recursive functions that can be used to check each element
                if (!match) match = tokenize(selector);
                i = match.length;
                while(i--){
                    cached = matcherFromTokens(match[i]);
                    if (cached[expando]) setMatchers.push(cached);
                    else elementMatchers.push(cached);
                }
                // Cache the compiled function
                cached = compilerCache(selector, matcherFromGroupMatchers(elementMatchers, setMatchers));
                // Save selector and tokenization
                cached.selector = selector;
            }
            return cached;
        }
        /**
 * A low-level selection function that works with jQuery's compiled
 *  selector functions
 * @param {String|Function} selector A selector or a pre-compiled
 *  selector function built with jQuery selector compile
 * @param {Element} context
 * @param {Array} [results]
 * @param {Array} [seed] A set of elements to match against
 */ function select(selector, context, results, seed) {
            var i, tokens, token, type, find, compiled = typeof selector === "function" && selector, match = !seed && tokenize(selector = compiled.selector || selector);
            results = results || [];
            // Try to minimize operations if there is only one selector in the list and no seed
            // (the latter of which guarantees us context)
            if (match.length === 1) {
                // Reduce context if the leading compound selector is an ID
                tokens = match[0] = match[0].slice(0);
                if (tokens.length > 2 && (token = tokens[0]).type === "ID" && context.nodeType === 9 && documentIsHTML && Expr.relative[tokens[1].type]) {
                    context = (Expr.find.ID(token.matches[0].replace(runescape, funescape), context) || [])[0];
                    if (!context) return results;
                    else if (compiled) context = context.parentNode;
                    selector = selector.slice(tokens.shift().value.length);
                }
                // Fetch a seed set for right-to-left matching
                i = matchExpr.needsContext.test(selector) ? 0 : tokens.length;
                while(i--){
                    token = tokens[i];
                    // Abort if we hit a combinator
                    if (Expr.relative[type = token.type]) break;
                    if (find = Expr.find[type]) // Search, expanding context for leading sibling combinators
                    {
                        if (seed = find(token.matches[0].replace(runescape, funescape), rsibling.test(tokens[0].type) && testContext(context.parentNode) || context)) {
                            // If seed is empty or no tokens remain, we can return early
                            tokens.splice(i, 1);
                            selector = seed.length && toSelector(tokens);
                            if (!selector) {
                                push.apply(results, seed);
                                return results;
                            }
                            break;
                        }
                    }
                }
            }
            // Compile and execute a filtering function if one is not provided
            // Provide `match` to avoid retokenization if we modified the selector above
            (compiled || compile(selector, match))(seed, context, !documentIsHTML, results, !context || rsibling.test(selector) && testContext(context.parentNode) || context);
            return results;
        }
        // One-time assignments
        // Support: Android <=4.0 - 4.1+
        // Sort stability
        support.sortStable = expando.split("").sort(sortOrder).join("") === expando;
        // Initialize against the default document
        setDocument();
        // Support: Android <=4.0 - 4.1+
        // Detached nodes confoundingly follow *each other*
        support.sortDetached = assert(function(el) {
            // Should return 1, but returns 4 (following)
            return el.compareDocumentPosition(document.createElement("fieldset")) & 1;
        });
        jQuery.find = find;
        // Deprecated
        jQuery.expr[":"] = jQuery.expr.pseudos;
        jQuery.unique = jQuery.uniqueSort;
        // These have always been private, but they used to be documented
        // as part of Sizzle so let's maintain them in the 3.x line
        // for backwards compatibility purposes.
        find.compile = compile;
        find.select = select;
        find.setDocument = setDocument;
        find.escape = jQuery.escapeSelector;
        find.getText = jQuery.text;
        find.isXML = jQuery.isXMLDoc;
        find.selectors = jQuery.expr;
        find.support = jQuery.support;
        find.uniqueSort = jQuery.uniqueSort;
    /* eslint-enable */ })();
    var dir = function(elem, dir, until) {
        var matched = [], truncate = until !== undefined;
        while((elem = elem[dir]) && elem.nodeType !== 9)if (elem.nodeType === 1) {
            if (truncate && jQuery(elem).is(until)) break;
            matched.push(elem);
        }
        return matched;
    };
    var siblings = function(n, elem) {
        var matched = [];
        for(; n; n = n.nextSibling)if (n.nodeType === 1 && n !== elem) matched.push(n);
        return matched;
    };
    var rneedsContext = jQuery.expr.match.needsContext;
    var rsingleTag = /^<([a-z][^\/\0>:\x20\t\r\n\f]*)[\x20\t\r\n\f]*\/?>(?:<\/\1>|)$/i;
    // Implement the identical functionality for filter and not
    function winnow(elements, qualifier, not) {
        if (isFunction(qualifier)) return jQuery.grep(elements, function(elem, i) {
            return !!qualifier.call(elem, i, elem) !== not;
        });
        // Single element
        if (qualifier.nodeType) return jQuery.grep(elements, function(elem) {
            return elem === qualifier !== not;
        });
        // Arraylike of elements (jQuery, arguments, Array)
        if (typeof qualifier !== "string") return jQuery.grep(elements, function(elem) {
            return indexOf.call(qualifier, elem) > -1 !== not;
        });
        // Filtered directly for both simple and complex selectors
        return jQuery.filter(qualifier, elements, not);
    }
    jQuery.filter = function(expr, elems, not) {
        var elem = elems[0];
        if (not) expr = ":not(" + expr + ")";
        if (elems.length === 1 && elem.nodeType === 1) return jQuery.find.matchesSelector(elem, expr) ? [
            elem
        ] : [];
        return jQuery.find.matches(expr, jQuery.grep(elems, function(elem) {
            return elem.nodeType === 1;
        }));
    };
    jQuery.fn.extend({
        find: function(selector) {
            var i, ret, len = this.length, self = this;
            if (typeof selector !== "string") return this.pushStack(jQuery(selector).filter(function() {
                for(i = 0; i < len; i++){
                    if (jQuery.contains(self[i], this)) return true;
                }
            }));
            ret = this.pushStack([]);
            for(i = 0; i < len; i++)jQuery.find(selector, self[i], ret);
            return len > 1 ? jQuery.uniqueSort(ret) : ret;
        },
        filter: function(selector) {
            return this.pushStack(winnow(this, selector || [], false));
        },
        not: function(selector) {
            return this.pushStack(winnow(this, selector || [], true));
        },
        is: function(selector) {
            return !!winnow(this, // If this is a positional/relative selector, check membership in the returned set
            // so $("p:first").is("p:last") won't return true for a doc with two "p".
            typeof selector === "string" && rneedsContext.test(selector) ? jQuery(selector) : selector || [], false).length;
        }
    });
    // Initialize a jQuery object
    // A central reference to the root jQuery(document)
    var rootjQuery, // A simple way to check for HTML strings
    // Prioritize #id over <tag> to avoid XSS via location.hash (trac-9521)
    // Strict HTML recognition (trac-11290: must start with <)
    // Shortcut simple #id case for speed
    rquickExpr = /^(?:\s*(<[\w\W]+>)[^>]*|#([\w-]+))$/, init = jQuery.fn.init = function(selector, context, root) {
        var match, elem;
        // HANDLE: $(""), $(null), $(undefined), $(false)
        if (!selector) return this;
        // Method init() accepts an alternate rootjQuery
        // so migrate can support jQuery.sub (gh-2101)
        root = root || rootjQuery;
        // Handle HTML strings
        if (typeof selector === "string") {
            if (selector[0] === "<" && selector[selector.length - 1] === ">" && selector.length >= 3) // Assume that strings that start and end with <> are HTML and skip the regex check
            match = [
                null,
                selector,
                null
            ];
            else match = rquickExpr.exec(selector);
            // Match html or make sure no context is specified for #id
            if (match && (match[1] || !context)) {
                // HANDLE: $(html) -> $(array)
                if (match[1]) {
                    context = context instanceof jQuery ? context[0] : context;
                    // Option to run scripts is true for back-compat
                    // Intentionally let the error be thrown if parseHTML is not present
                    jQuery.merge(this, jQuery.parseHTML(match[1], context && context.nodeType ? context.ownerDocument || context : document, true));
                    // HANDLE: $(html, props)
                    if (rsingleTag.test(match[1]) && jQuery.isPlainObject(context)) {
                        for(match in context)// Properties of context are called as methods if possible
                        if (isFunction(this[match])) this[match](context[match]);
                        else this.attr(match, context[match]);
                    }
                    return this;
                // HANDLE: $(#id)
                } else {
                    elem = document.getElementById(match[2]);
                    if (elem) {
                        // Inject the element directly into the jQuery object
                        this[0] = elem;
                        this.length = 1;
                    }
                    return this;
                }
            } else if (!context || context.jquery) return (context || root).find(selector);
            else return this.constructor(context).find(selector);
        // HANDLE: $(DOMElement)
        } else if (selector.nodeType) {
            this[0] = selector;
            this.length = 1;
            return this;
        // HANDLE: $(function)
        // Shortcut for document ready
        } else if (isFunction(selector)) return root.ready !== undefined ? root.ready(selector) : // Execute immediately if ready is not present
        selector(jQuery);
        return jQuery.makeArray(selector, this);
    };
    // Give the init function the jQuery prototype for later instantiation
    init.prototype = jQuery.fn;
    // Initialize central reference
    rootjQuery = jQuery(document);
    var rparentsprev = /^(?:parents|prev(?:Until|All))/, // Methods guaranteed to produce a unique set when starting from a unique set
    guaranteedUnique = {
        children: true,
        contents: true,
        next: true,
        prev: true
    };
    jQuery.fn.extend({
        has: function(target) {
            var targets = jQuery(target, this), l = targets.length;
            return this.filter(function() {
                var i = 0;
                for(; i < l; i++){
                    if (jQuery.contains(this, targets[i])) return true;
                }
            });
        },
        closest: function(selectors, context) {
            var cur, i = 0, l = this.length, matched = [], targets = typeof selectors !== "string" && jQuery(selectors);
            // Positional selectors never match, since there's no _selection_ context
            if (!rneedsContext.test(selectors)) for(; i < l; i++){
                for(cur = this[i]; cur && cur !== context; cur = cur.parentNode)// Always skip document fragments
                if (cur.nodeType < 11 && (targets ? targets.index(cur) > -1 : // Don't pass non-elements to jQuery#find
                cur.nodeType === 1 && jQuery.find.matchesSelector(cur, selectors))) {
                    matched.push(cur);
                    break;
                }
            }
            return this.pushStack(matched.length > 1 ? jQuery.uniqueSort(matched) : matched);
        },
        // Determine the position of an element within the set
        index: function(elem) {
            // No argument, return index in parent
            if (!elem) return this[0] && this[0].parentNode ? this.first().prevAll().length : -1;
            // Index in selector
            if (typeof elem === "string") return indexOf.call(jQuery(elem), this[0]);
            // Locate the position of the desired element
            return indexOf.call(this, // If it receives a jQuery object, the first element is used
            elem.jquery ? elem[0] : elem);
        },
        add: function(selector, context) {
            return this.pushStack(jQuery.uniqueSort(jQuery.merge(this.get(), jQuery(selector, context))));
        },
        addBack: function(selector) {
            return this.add(selector == null ? this.prevObject : this.prevObject.filter(selector));
        }
    });
    function sibling(cur, dir) {
        while((cur = cur[dir]) && cur.nodeType !== 1);
        return cur;
    }
    jQuery.each({
        parent: function(elem) {
            var parent = elem.parentNode;
            return parent && parent.nodeType !== 11 ? parent : null;
        },
        parents: function(elem) {
            return dir(elem, "parentNode");
        },
        parentsUntil: function(elem, _i, until) {
            return dir(elem, "parentNode", until);
        },
        next: function(elem) {
            return sibling(elem, "nextSibling");
        },
        prev: function(elem) {
            return sibling(elem, "previousSibling");
        },
        nextAll: function(elem) {
            return dir(elem, "nextSibling");
        },
        prevAll: function(elem) {
            return dir(elem, "previousSibling");
        },
        nextUntil: function(elem, _i, until) {
            return dir(elem, "nextSibling", until);
        },
        prevUntil: function(elem, _i, until) {
            return dir(elem, "previousSibling", until);
        },
        siblings: function(elem) {
            return siblings((elem.parentNode || {}).firstChild, elem);
        },
        children: function(elem) {
            return siblings(elem.firstChild);
        },
        contents: function(elem) {
            if (elem.contentDocument != null && // Support: IE 11+
            // <object> elements with no `data` attribute has an object
            // `contentDocument` with a `null` prototype.
            getProto(elem.contentDocument)) return elem.contentDocument;
            // Support: IE 9 - 11 only, iOS 7 only, Android Browser <=4.3 only
            // Treat the template element as a regular one in browsers that
            // don't support it.
            if (nodeName(elem, "template")) elem = elem.content || elem;
            return jQuery.merge([], elem.childNodes);
        }
    }, function(name, fn) {
        jQuery.fn[name] = function(until, selector) {
            var matched = jQuery.map(this, fn, until);
            if (name.slice(-5) !== "Until") selector = until;
            if (selector && typeof selector === "string") matched = jQuery.filter(selector, matched);
            if (this.length > 1) {
                // Remove duplicates
                if (!guaranteedUnique[name]) jQuery.uniqueSort(matched);
                // Reverse order for parents* and prev-derivatives
                if (rparentsprev.test(name)) matched.reverse();
            }
            return this.pushStack(matched);
        };
    });
    var rnothtmlwhite = /[^\x20\t\r\n\f]+/g;
    // Convert String-formatted options into Object-formatted ones
    function createOptions(options) {
        var object = {};
        jQuery.each(options.match(rnothtmlwhite) || [], function(_, flag) {
            object[flag] = true;
        });
        return object;
    }
    /*
 * Create a callback list using the following parameters:
 *
 *	options: an optional list of space-separated options that will change how
 *			the callback list behaves or a more traditional option object
 *
 * By default a callback list will act like an event callback list and can be
 * "fired" multiple times.
 *
 * Possible options:
 *
 *	once:			will ensure the callback list can only be fired once (like a Deferred)
 *
 *	memory:			will keep track of previous values and will call any callback added
 *					after the list has been fired right away with the latest "memorized"
 *					values (like a Deferred)
 *
 *	unique:			will ensure a callback can only be added once (no duplicate in the list)
 *
 *	stopOnFalse:	interrupt callings when a callback returns false
 *
 */ jQuery.Callbacks = function(options) {
        // Convert options from String-formatted to Object-formatted if needed
        // (we check in cache first)
        options = typeof options === "string" ? createOptions(options) : jQuery.extend({}, options);
        var firing, // Last fire value for non-forgettable lists
        memory, // Flag to know if list was already fired
        fired, // Flag to prevent firing
        locked, // Actual callback list
        list = [], // Queue of execution data for repeatable lists
        queue = [], // Index of currently firing callback (modified by add/remove as needed)
        firingIndex = -1, // Fire callbacks
        fire = function() {
            // Enforce single-firing
            locked = locked || options.once;
            // Execute callbacks for all pending executions,
            // respecting firingIndex overrides and runtime changes
            fired = firing = true;
            for(; queue.length; firingIndex = -1){
                memory = queue.shift();
                while(++firingIndex < list.length)// Run callback and check for early termination
                if (list[firingIndex].apply(memory[0], memory[1]) === false && options.stopOnFalse) {
                    // Jump to end and forget the data so .add doesn't re-fire
                    firingIndex = list.length;
                    memory = false;
                }
            }
            // Forget the data if we're done with it
            if (!options.memory) memory = false;
            firing = false;
            // Clean up if we're done firing for good
            if (locked) {
                // Keep an empty list if we have data for future add calls
                if (memory) list = [];
                else list = "";
            }
        }, // Actual Callbacks object
        self = {
            // Add a callback or a collection of callbacks to the list
            add: function() {
                if (list) {
                    // If we have memory from a past run, we should fire after adding
                    if (memory && !firing) {
                        firingIndex = list.length - 1;
                        queue.push(memory);
                    }
                    (function add(args) {
                        jQuery.each(args, function(_, arg) {
                            if (isFunction(arg)) {
                                if (!options.unique || !self.has(arg)) list.push(arg);
                            } else if (arg && arg.length && toType(arg) !== "string") // Inspect recursively
                            add(arg);
                        });
                    })(arguments);
                    if (memory && !firing) fire();
                }
                return this;
            },
            // Remove a callback from the list
            remove: function() {
                jQuery.each(arguments, function(_, arg) {
                    var index;
                    while((index = jQuery.inArray(arg, list, index)) > -1){
                        list.splice(index, 1);
                        // Handle firing indexes
                        if (index <= firingIndex) firingIndex--;
                    }
                });
                return this;
            },
            // Check if a given callback is in the list.
            // If no argument is given, return whether or not list has callbacks attached.
            has: function(fn) {
                return fn ? jQuery.inArray(fn, list) > -1 : list.length > 0;
            },
            // Remove all callbacks from the list
            empty: function() {
                if (list) list = [];
                return this;
            },
            // Disable .fire and .add
            // Abort any current/pending executions
            // Clear all callbacks and values
            disable: function() {
                locked = queue = [];
                list = memory = "";
                return this;
            },
            disabled: function() {
                return !list;
            },
            // Disable .fire
            // Also disable .add unless we have memory (since it would have no effect)
            // Abort any pending executions
            lock: function() {
                locked = queue = [];
                if (!memory && !firing) list = memory = "";
                return this;
            },
            locked: function() {
                return !!locked;
            },
            // Call all callbacks with the given context and arguments
            fireWith: function(context, args) {
                if (!locked) {
                    args = args || [];
                    args = [
                        context,
                        args.slice ? args.slice() : args
                    ];
                    queue.push(args);
                    if (!firing) fire();
                }
                return this;
            },
            // Call all the callbacks with the given arguments
            fire: function() {
                self.fireWith(this, arguments);
                return this;
            },
            // To know if the callbacks have already been called at least once
            fired: function() {
                return !!fired;
            }
        };
        return self;
    };
    function Identity(v) {
        return v;
    }
    function Thrower(ex) {
        throw ex;
    }
    function adoptValue(value, resolve, reject, noValue) {
        var method;
        try {
            // Check for promise aspect first to privilege synchronous behavior
            if (value && isFunction(method = value.promise)) method.call(value).done(resolve).fail(reject);
            else if (value && isFunction(method = value.then)) method.call(value, resolve, reject);
            else // Control `resolve` arguments by letting Array#slice cast boolean `noValue` to integer:
            // * false: [ value ].slice( 0 ) => resolve( value )
            // * true: [ value ].slice( 1 ) => resolve()
            resolve.apply(undefined, [
                value
            ].slice(noValue));
        // For Promises/A+, convert exceptions into rejections
        // Since jQuery.when doesn't unwrap thenables, we can skip the extra checks appearing in
        // Deferred#then to conditionally suppress rejection.
        } catch (value) {
            // Support: Android 4.0 only
            // Strict mode functions invoked without .call/.apply get global-object context
            reject.apply(undefined, [
                value
            ]);
        }
    }
    jQuery.extend({
        Deferred: function(func) {
            var tuples = [
                // action, add listener, callbacks,
                // ... .then handlers, argument index, [final state]
                [
                    "notify",
                    "progress",
                    jQuery.Callbacks("memory"),
                    jQuery.Callbacks("memory"),
                    2
                ],
                [
                    "resolve",
                    "done",
                    jQuery.Callbacks("once memory"),
                    jQuery.Callbacks("once memory"),
                    0,
                    "resolved"
                ],
                [
                    "reject",
                    "fail",
                    jQuery.Callbacks("once memory"),
                    jQuery.Callbacks("once memory"),
                    1,
                    "rejected"
                ]
            ], state = "pending", promise = {
                state: function() {
                    return state;
                },
                always: function() {
                    deferred.done(arguments).fail(arguments);
                    return this;
                },
                "catch": function(fn) {
                    return promise.then(null, fn);
                },
                // Keep pipe for back-compat
                pipe: function() {
                    var fns = arguments;
                    return jQuery.Deferred(function(newDefer) {
                        jQuery.each(tuples, function(_i, tuple) {
                            // Map tuples (progress, done, fail) to arguments (done, fail, progress)
                            var fn = isFunction(fns[tuple[4]]) && fns[tuple[4]];
                            // deferred.progress(function() { bind to newDefer or newDefer.notify })
                            // deferred.done(function() { bind to newDefer or newDefer.resolve })
                            // deferred.fail(function() { bind to newDefer or newDefer.reject })
                            deferred[tuple[1]](function() {
                                var returned = fn && fn.apply(this, arguments);
                                if (returned && isFunction(returned.promise)) returned.promise().progress(newDefer.notify).done(newDefer.resolve).fail(newDefer.reject);
                                else newDefer[tuple[0] + "With"](this, fn ? [
                                    returned
                                ] : arguments);
                            });
                        });
                        fns = null;
                    }).promise();
                },
                then: function(onFulfilled, onRejected, onProgress) {
                    var maxDepth = 0;
                    function resolve(depth, deferred, handler, special) {
                        return function() {
                            var that = this, args = arguments, mightThrow = function() {
                                var returned, then;
                                // Support: Promises/A+ section 2.3.3.3.3
                                // https://promisesaplus.com/#point-59
                                // Ignore double-resolution attempts
                                if (depth < maxDepth) return;
                                returned = handler.apply(that, args);
                                // Support: Promises/A+ section 2.3.1
                                // https://promisesaplus.com/#point-48
                                if (returned === deferred.promise()) throw new TypeError("Thenable self-resolution");
                                // Support: Promises/A+ sections 2.3.3.1, 3.5
                                // https://promisesaplus.com/#point-54
                                // https://promisesaplus.com/#point-75
                                // Retrieve `then` only once
                                then = returned && // Support: Promises/A+ section 2.3.4
                                // https://promisesaplus.com/#point-64
                                // Only check objects and functions for thenability
                                (typeof returned === "object" || typeof returned === "function") && returned.then;
                                // Handle a returned thenable
                                if (isFunction(then)) {
                                    // Special processors (notify) just wait for resolution
                                    if (special) then.call(returned, resolve(maxDepth, deferred, Identity, special), resolve(maxDepth, deferred, Thrower, special));
                                    else {
                                        // ...and disregard older resolution values
                                        maxDepth++;
                                        then.call(returned, resolve(maxDepth, deferred, Identity, special), resolve(maxDepth, deferred, Thrower, special), resolve(maxDepth, deferred, Identity, deferred.notifyWith));
                                    }
                                } else {
                                    // Only substitute handlers pass on context
                                    // and multiple values (non-spec behavior)
                                    if (handler !== Identity) {
                                        that = undefined;
                                        args = [
                                            returned
                                        ];
                                    }
                                    // Process the value(s)
                                    // Default process is resolve
                                    (special || deferred.resolveWith)(that, args);
                                }
                            }, // Only normal processors (resolve) catch and reject exceptions
                            process = special ? mightThrow : function() {
                                try {
                                    mightThrow();
                                } catch (e) {
                                    if (jQuery.Deferred.exceptionHook) jQuery.Deferred.exceptionHook(e, process.error);
                                    // Support: Promises/A+ section 2.3.3.3.4.1
                                    // https://promisesaplus.com/#point-61
                                    // Ignore post-resolution exceptions
                                    if (depth + 1 >= maxDepth) {
                                        // Only substitute handlers pass on context
                                        // and multiple values (non-spec behavior)
                                        if (handler !== Thrower) {
                                            that = undefined;
                                            args = [
                                                e
                                            ];
                                        }
                                        deferred.rejectWith(that, args);
                                    }
                                }
                            };
                            // Support: Promises/A+ section 2.3.3.3.1
                            // https://promisesaplus.com/#point-57
                            // Re-resolve promises immediately to dodge false rejection from
                            // subsequent errors
                            if (depth) process();
                            else {
                                // Call an optional hook to record the error, in case of exception
                                // since it's otherwise lost when execution goes async
                                if (jQuery.Deferred.getErrorHook) process.error = jQuery.Deferred.getErrorHook();
                                else if (jQuery.Deferred.getStackHook) process.error = jQuery.Deferred.getStackHook();
                                window1.setTimeout(process);
                            }
                        };
                    }
                    return jQuery.Deferred(function(newDefer) {
                        // progress_handlers.add( ... )
                        tuples[0][3].add(resolve(0, newDefer, isFunction(onProgress) ? onProgress : Identity, newDefer.notifyWith));
                        // fulfilled_handlers.add( ... )
                        tuples[1][3].add(resolve(0, newDefer, isFunction(onFulfilled) ? onFulfilled : Identity));
                        // rejected_handlers.add( ... )
                        tuples[2][3].add(resolve(0, newDefer, isFunction(onRejected) ? onRejected : Thrower));
                    }).promise();
                },
                // Get a promise for this deferred
                // If obj is provided, the promise aspect is added to the object
                promise: function(obj) {
                    return obj != null ? jQuery.extend(obj, promise) : promise;
                }
            }, deferred = {};
            // Add list-specific methods
            jQuery.each(tuples, function(i, tuple) {
                var list = tuple[2], stateString = tuple[5];
                // promise.progress = list.add
                // promise.done = list.add
                // promise.fail = list.add
                promise[tuple[1]] = list.add;
                // Handle state
                if (stateString) list.add(function() {
                    // state = "resolved" (i.e., fulfilled)
                    // state = "rejected"
                    state = stateString;
                }, // rejected_callbacks.disable
                // fulfilled_callbacks.disable
                tuples[3 - i][2].disable, // rejected_handlers.disable
                // fulfilled_handlers.disable
                tuples[3 - i][3].disable, // progress_callbacks.lock
                tuples[0][2].lock, // progress_handlers.lock
                tuples[0][3].lock);
                // progress_handlers.fire
                // fulfilled_handlers.fire
                // rejected_handlers.fire
                list.add(tuple[3].fire);
                // deferred.notify = function() { deferred.notifyWith(...) }
                // deferred.resolve = function() { deferred.resolveWith(...) }
                // deferred.reject = function() { deferred.rejectWith(...) }
                deferred[tuple[0]] = function() {
                    deferred[tuple[0] + "With"](this === deferred ? undefined : this, arguments);
                    return this;
                };
                // deferred.notifyWith = list.fireWith
                // deferred.resolveWith = list.fireWith
                // deferred.rejectWith = list.fireWith
                deferred[tuple[0] + "With"] = list.fireWith;
            });
            // Make the deferred a promise
            promise.promise(deferred);
            // Call given func if any
            if (func) func.call(deferred, deferred);
            // All done!
            return deferred;
        },
        // Deferred helper
        when: function(singleValue) {
            var // count of uncompleted subordinates
            remaining = arguments.length, // count of unprocessed arguments
            i = remaining, // subordinate fulfillment data
            resolveContexts = Array(i), resolveValues = slice.call(arguments), // the primary Deferred
            primary = jQuery.Deferred(), // subordinate callback factory
            updateFunc = function(i) {
                return function(value) {
                    resolveContexts[i] = this;
                    resolveValues[i] = arguments.length > 1 ? slice.call(arguments) : value;
                    if (!--remaining) primary.resolveWith(resolveContexts, resolveValues);
                };
            };
            // Single- and empty arguments are adopted like Promise.resolve
            if (remaining <= 1) {
                adoptValue(singleValue, primary.done(updateFunc(i)).resolve, primary.reject, !remaining);
                // Use .then() to unwrap secondary thenables (cf. gh-3000)
                if (primary.state() === "pending" || isFunction(resolveValues[i] && resolveValues[i].then)) return primary.then();
            }
            // Multiple arguments are aggregated like Promise.all array elements
            while(i--)adoptValue(resolveValues[i], updateFunc(i), primary.reject);
            return primary.promise();
        }
    });
    // These usually indicate a programmer mistake during development,
    // warn about them ASAP rather than swallowing them by default.
    var rerrorNames = /^(Eval|Internal|Range|Reference|Syntax|Type|URI)Error$/;
    // If `jQuery.Deferred.getErrorHook` is defined, `asyncError` is an error
    // captured before the async barrier to get the original error cause
    // which may otherwise be hidden.
    jQuery.Deferred.exceptionHook = function(error, asyncError) {
        // Support: IE 8 - 9 only
        // Console exists when dev tools are open, which can happen at any time
        if (window1.console && window1.console.warn && error && rerrorNames.test(error.name)) window1.console.warn("jQuery.Deferred exception: " + error.message, error.stack, asyncError);
    };
    jQuery.readyException = function(error) {
        window1.setTimeout(function() {
            throw error;
        });
    };
    // The deferred used on DOM ready
    var readyList = jQuery.Deferred();
    jQuery.fn.ready = function(fn) {
        readyList.then(fn)// Wrap jQuery.readyException in a function so that the lookup
        // happens at the time of error handling instead of callback
        // registration.
        .catch(function(error) {
            jQuery.readyException(error);
        });
        return this;
    };
    jQuery.extend({
        // Is the DOM ready to be used? Set to true once it occurs.
        isReady: false,
        // A counter to track how many items to wait for before
        // the ready event fires. See trac-6781
        readyWait: 1,
        // Handle when the DOM is ready
        ready: function(wait) {
            // Abort if there are pending holds or we're already ready
            if (wait === true ? --jQuery.readyWait : jQuery.isReady) return;
            // Remember that the DOM is ready
            jQuery.isReady = true;
            // If a normal DOM Ready event fired, decrement, and wait if need be
            if (wait !== true && --jQuery.readyWait > 0) return;
            // If there are functions bound, to execute
            readyList.resolveWith(document, [
                jQuery
            ]);
        }
    });
    jQuery.ready.then = readyList.then;
    // The ready event handler and self cleanup method
    function completed() {
        document.removeEventListener("DOMContentLoaded", completed);
        window1.removeEventListener("load", completed);
        jQuery.ready();
    }
    // Catch cases where $(document).ready() is called
    // after the browser event has already occurred.
    // Support: IE <=9 - 10 only
    // Older IE sometimes signals "interactive" too soon
    if (document.readyState === "complete" || document.readyState !== "loading" && !document.documentElement.doScroll) // Handle it asynchronously to allow scripts the opportunity to delay ready
    window1.setTimeout(jQuery.ready);
    else {
        // Use the handy event callback
        document.addEventListener("DOMContentLoaded", completed);
        // A fallback to window.onload, that will always work
        window1.addEventListener("load", completed);
    }
    // Multifunctional method to get and set values of a collection
    // The value/s can optionally be executed if it's a function
    var access = function(elems, fn, key, value, chainable, emptyGet, raw) {
        var i = 0, len = elems.length, bulk = key == null;
        // Sets many values
        if (toType(key) === "object") {
            chainable = true;
            for(i in key)access(elems, fn, i, key[i], true, emptyGet, raw);
        // Sets one value
        } else if (value !== undefined) {
            chainable = true;
            if (!isFunction(value)) raw = true;
            if (bulk) {
                // Bulk operations run against the entire set
                if (raw) {
                    fn.call(elems, value);
                    fn = null;
                // ...except when executing function values
                } else {
                    bulk = fn;
                    fn = function(elem, _key, value) {
                        return bulk.call(jQuery(elem), value);
                    };
                }
            }
            if (fn) for(; i < len; i++)fn(elems[i], key, raw ? value : value.call(elems[i], i, fn(elems[i], key)));
        }
        if (chainable) return elems;
        // Gets
        if (bulk) return fn.call(elems);
        return len ? fn(elems[0], key) : emptyGet;
    };
    // Matches dashed string for camelizing
    var rmsPrefix = /^-ms-/, rdashAlpha = /-([a-z])/g;
    // Used by camelCase as callback to replace()
    function fcamelCase(_all, letter) {
        return letter.toUpperCase();
    }
    // Convert dashed to camelCase; used by the css and data modules
    // Support: IE <=9 - 11, Edge 12 - 15
    // Microsoft forgot to hump their vendor prefix (trac-9572)
    function camelCase(string) {
        return string.replace(rmsPrefix, "ms-").replace(rdashAlpha, fcamelCase);
    }
    var acceptData = function(owner) {
        // Accepts only:
        //  - Node
        //    - Node.ELEMENT_NODE
        //    - Node.DOCUMENT_NODE
        //  - Object
        //    - Any
        return owner.nodeType === 1 || owner.nodeType === 9 || !+owner.nodeType;
    };
    function Data() {
        this.expando = jQuery.expando + Data.uid++;
    }
    Data.uid = 1;
    Data.prototype = {
        cache: function(owner) {
            // Check if the owner object already has a cache
            var value = owner[this.expando];
            // If not, create one
            if (!value) {
                value = {};
                // We can accept data for non-element nodes in modern browsers,
                // but we should not, see trac-8335.
                // Always return an empty object.
                if (acceptData(owner)) {
                    // If it is a node unlikely to be stringify-ed or looped over
                    // use plain assignment
                    if (owner.nodeType) owner[this.expando] = value;
                    else Object.defineProperty(owner, this.expando, {
                        value: value,
                        configurable: true
                    });
                }
            }
            return value;
        },
        set: function(owner, data, value) {
            var prop, cache = this.cache(owner);
            // Handle: [ owner, key, value ] args
            // Always use camelCase key (gh-2257)
            if (typeof data === "string") cache[camelCase(data)] = value;
            else // Copy the properties one-by-one to the cache object
            for(prop in data)cache[camelCase(prop)] = data[prop];
            return cache;
        },
        get: function(owner, key) {
            return key === undefined ? this.cache(owner) : // Always use camelCase key (gh-2257)
            owner[this.expando] && owner[this.expando][camelCase(key)];
        },
        access: function(owner, key, value) {
            // In cases where either:
            //
            //   1. No key was specified
            //   2. A string key was specified, but no value provided
            //
            // Take the "read" path and allow the get method to determine
            // which value to return, respectively either:
            //
            //   1. The entire cache object
            //   2. The data stored at the key
            //
            if (key === undefined || key && typeof key === "string" && value === undefined) return this.get(owner, key);
            // When the key is not a string, or both a key and value
            // are specified, set or extend (existing objects) with either:
            //
            //   1. An object of properties
            //   2. A key and value
            //
            this.set(owner, key, value);
            // Since the "set" path can have two possible entry points
            // return the expected data based on which path was taken[*]
            return value !== undefined ? value : key;
        },
        remove: function(owner, key) {
            var i, cache = owner[this.expando];
            if (cache === undefined) return;
            if (key !== undefined) {
                // Support array or space separated string of keys
                if (Array.isArray(key)) // If key is an array of keys...
                // We always set camelCase keys, so remove that.
                key = key.map(camelCase);
                else {
                    key = camelCase(key);
                    // If a key with the spaces exists, use it.
                    // Otherwise, create an array by matching non-whitespace
                    key = key in cache ? [
                        key
                    ] : key.match(rnothtmlwhite) || [];
                }
                i = key.length;
                while(i--)delete cache[key[i]];
            }
            // Remove the expando if there's no more data
            if (key === undefined || jQuery.isEmptyObject(cache)) {
                // Support: Chrome <=35 - 45
                // Webkit & Blink performance suffers when deleting properties
                // from DOM nodes, so set to undefined instead
                // https://bugs.chromium.org/p/chromium/issues/detail?id=378607 (bug restricted)
                if (owner.nodeType) owner[this.expando] = undefined;
                else delete owner[this.expando];
            }
        },
        hasData: function(owner) {
            var cache = owner[this.expando];
            return cache !== undefined && !jQuery.isEmptyObject(cache);
        }
    };
    var dataPriv = new Data();
    var dataUser = new Data();
    //	Implementation Summary
    //
    //	1. Enforce API surface and semantic compatibility with 1.9.x branch
    //	2. Improve the module's maintainability by reducing the storage
    //		paths to a single mechanism.
    //	3. Use the same single mechanism to support "private" and "user" data.
    //	4. _Never_ expose "private" data to user code (TODO: Drop _data, _removeData)
    //	5. Avoid exposing implementation details on user objects (eg. expando properties)
    //	6. Provide a clear path for implementation upgrade to WeakMap in 2014
    var rbrace = /^(?:\{[\w\W]*\}|\[[\w\W]*\])$/, rmultiDash = /[A-Z]/g;
    function getData(data) {
        if (data === "true") return true;
        if (data === "false") return false;
        if (data === "null") return null;
        // Only convert to a number if it doesn't change the string
        if (data === +data + "") return +data;
        if (rbrace.test(data)) return JSON.parse(data);
        return data;
    }
    function dataAttr(elem, key, data) {
        var name;
        // If nothing was found internally, try to fetch any
        // data from the HTML5 data-* attribute
        if (data === undefined && elem.nodeType === 1) {
            name = "data-" + key.replace(rmultiDash, "-$&").toLowerCase();
            data = elem.getAttribute(name);
            if (typeof data === "string") {
                try {
                    data = getData(data);
                } catch (e) {}
                // Make sure we set the data so it isn't changed later
                dataUser.set(elem, key, data);
            } else data = undefined;
        }
        return data;
    }
    jQuery.extend({
        hasData: function(elem) {
            return dataUser.hasData(elem) || dataPriv.hasData(elem);
        },
        data: function(elem, name, data) {
            return dataUser.access(elem, name, data);
        },
        removeData: function(elem, name) {
            dataUser.remove(elem, name);
        },
        // TODO: Now that all calls to _data and _removeData have been replaced
        // with direct calls to dataPriv methods, these can be deprecated.
        _data: function(elem, name, data) {
            return dataPriv.access(elem, name, data);
        },
        _removeData: function(elem, name) {
            dataPriv.remove(elem, name);
        }
    });
    jQuery.fn.extend({
        data: function(key, value) {
            var i, name, data, elem = this[0], attrs = elem && elem.attributes;
            // Gets all values
            if (key === undefined) {
                if (this.length) {
                    data = dataUser.get(elem);
                    if (elem.nodeType === 1 && !dataPriv.get(elem, "hasDataAttrs")) {
                        i = attrs.length;
                        while(i--)// Support: IE 11 only
                        // The attrs elements can be null (trac-14894)
                        if (attrs[i]) {
                            name = attrs[i].name;
                            if (name.indexOf("data-") === 0) {
                                name = camelCase(name.slice(5));
                                dataAttr(elem, name, data[name]);
                            }
                        }
                        dataPriv.set(elem, "hasDataAttrs", true);
                    }
                }
                return data;
            }
            // Sets multiple values
            if (typeof key === "object") return this.each(function() {
                dataUser.set(this, key);
            });
            return access(this, function(value) {
                var data;
                // The calling jQuery object (element matches) is not empty
                // (and therefore has an element appears at this[ 0 ]) and the
                // `value` parameter was not undefined. An empty jQuery object
                // will result in `undefined` for elem = this[ 0 ] which will
                // throw an exception if an attempt to read a data cache is made.
                if (elem && value === undefined) {
                    // Attempt to get data from the cache
                    // The key will always be camelCased in Data
                    data = dataUser.get(elem, key);
                    if (data !== undefined) return data;
                    // Attempt to "discover" the data in
                    // HTML5 custom data-* attrs
                    data = dataAttr(elem, key);
                    if (data !== undefined) return data;
                    // We tried really hard, but the data doesn't exist.
                    return;
                }
                // Set the data...
                this.each(function() {
                    // We always store the camelCased key
                    dataUser.set(this, key, value);
                });
            }, null, value, arguments.length > 1, null, true);
        },
        removeData: function(key) {
            return this.each(function() {
                dataUser.remove(this, key);
            });
        }
    });
    jQuery.extend({
        queue: function(elem, type, data) {
            var queue;
            if (elem) {
                type = (type || "fx") + "queue";
                queue = dataPriv.get(elem, type);
                // Speed up dequeue by getting out quickly if this is just a lookup
                if (data) {
                    if (!queue || Array.isArray(data)) queue = dataPriv.access(elem, type, jQuery.makeArray(data));
                    else queue.push(data);
                }
                return queue || [];
            }
        },
        dequeue: function(elem, type) {
            type = type || "fx";
            var queue = jQuery.queue(elem, type), startLength = queue.length, fn = queue.shift(), hooks = jQuery._queueHooks(elem, type), next = function() {
                jQuery.dequeue(elem, type);
            };
            // If the fx queue is dequeued, always remove the progress sentinel
            if (fn === "inprogress") {
                fn = queue.shift();
                startLength--;
            }
            if (fn) {
                // Add a progress sentinel to prevent the fx queue from being
                // automatically dequeued
                if (type === "fx") queue.unshift("inprogress");
                // Clear up the last queue stop function
                delete hooks.stop;
                fn.call(elem, next, hooks);
            }
            if (!startLength && hooks) hooks.empty.fire();
        },
        // Not public - generate a queueHooks object, or return the current one
        _queueHooks: function(elem, type) {
            var key = type + "queueHooks";
            return dataPriv.get(elem, key) || dataPriv.access(elem, key, {
                empty: jQuery.Callbacks("once memory").add(function() {
                    dataPriv.remove(elem, [
                        type + "queue",
                        key
                    ]);
                })
            });
        }
    });
    jQuery.fn.extend({
        queue: function(type, data) {
            var setter = 2;
            if (typeof type !== "string") {
                data = type;
                type = "fx";
                setter--;
            }
            if (arguments.length < setter) return jQuery.queue(this[0], type);
            return data === undefined ? this : this.each(function() {
                var queue = jQuery.queue(this, type, data);
                // Ensure a hooks for this queue
                jQuery._queueHooks(this, type);
                if (type === "fx" && queue[0] !== "inprogress") jQuery.dequeue(this, type);
            });
        },
        dequeue: function(type) {
            return this.each(function() {
                jQuery.dequeue(this, type);
            });
        },
        clearQueue: function(type) {
            return this.queue(type || "fx", []);
        },
        // Get a promise resolved when queues of a certain type
        // are emptied (fx is the type by default)
        promise: function(type, obj) {
            var tmp, count = 1, defer = jQuery.Deferred(), elements = this, i = this.length, resolve = function() {
                if (!--count) defer.resolveWith(elements, [
                    elements
                ]);
            };
            if (typeof type !== "string") {
                obj = type;
                type = undefined;
            }
            type = type || "fx";
            while(i--){
                tmp = dataPriv.get(elements[i], type + "queueHooks");
                if (tmp && tmp.empty) {
                    count++;
                    tmp.empty.add(resolve);
                }
            }
            resolve();
            return defer.promise(obj);
        }
    });
    var pnum = /[+-]?(?:\d*\.|)\d+(?:[eE][+-]?\d+|)/.source;
    var rcssNum = new RegExp("^(?:([+-])=|)(" + pnum + ")([a-z%]*)$", "i");
    var cssExpand = [
        "Top",
        "Right",
        "Bottom",
        "Left"
    ];
    var documentElement = document.documentElement;
    var isAttached = function(elem) {
        return jQuery.contains(elem.ownerDocument, elem);
    }, composed = {
        composed: true
    };
    // Support: IE 9 - 11+, Edge 12 - 18+, iOS 10.0 - 10.2 only
    // Check attachment across shadow DOM boundaries when possible (gh-3504)
    // Support: iOS 10.0-10.2 only
    // Early iOS 10 versions support `attachShadow` but not `getRootNode`,
    // leading to errors. We need to check for `getRootNode`.
    if (documentElement.getRootNode) isAttached = function(elem) {
        return jQuery.contains(elem.ownerDocument, elem) || elem.getRootNode(composed) === elem.ownerDocument;
    };
    var isHiddenWithinTree = function(elem, el) {
        // isHiddenWithinTree might be called from jQuery#filter function;
        // in that case, element will be second argument
        elem = el || elem;
        // Inline style trumps all
        return elem.style.display === "none" || elem.style.display === "" && // Otherwise, check computed style
        // Support: Firefox <=43 - 45
        // Disconnected elements can have computed display: none, so first confirm that elem is
        // in the document.
        isAttached(elem) && jQuery.css(elem, "display") === "none";
    };
    function adjustCSS(elem, prop, valueParts, tween) {
        var adjusted, scale, maxIterations = 20, currentValue = tween ? function() {
            return tween.cur();
        } : function() {
            return jQuery.css(elem, prop, "");
        }, initial = currentValue(), unit = valueParts && valueParts[3] || (jQuery.cssNumber[prop] ? "" : "px"), // Starting value computation is required for potential unit mismatches
        initialInUnit = elem.nodeType && (jQuery.cssNumber[prop] || unit !== "px" && +initial) && rcssNum.exec(jQuery.css(elem, prop));
        if (initialInUnit && initialInUnit[3] !== unit) {
            // Support: Firefox <=54
            // Halve the iteration target value to prevent interference from CSS upper bounds (gh-2144)
            initial = initial / 2;
            // Trust units reported by jQuery.css
            unit = unit || initialInUnit[3];
            // Iteratively approximate from a nonzero starting point
            initialInUnit = +initial || 1;
            while(maxIterations--){
                // Evaluate and update our best guess (doubling guesses that zero out).
                // Finish if the scale equals or crosses 1 (making the old*new product non-positive).
                jQuery.style(elem, prop, initialInUnit + unit);
                if ((1 - scale) * (1 - (scale = currentValue() / initial || 0.5)) <= 0) maxIterations = 0;
                initialInUnit = initialInUnit / scale;
            }
            initialInUnit = initialInUnit * 2;
            jQuery.style(elem, prop, initialInUnit + unit);
            // Make sure we update the tween properties later on
            valueParts = valueParts || [];
        }
        if (valueParts) {
            initialInUnit = +initialInUnit || +initial || 0;
            // Apply relative offset (+=/-=) if specified
            adjusted = valueParts[1] ? initialInUnit + (valueParts[1] + 1) * valueParts[2] : +valueParts[2];
            if (tween) {
                tween.unit = unit;
                tween.start = initialInUnit;
                tween.end = adjusted;
            }
        }
        return adjusted;
    }
    var defaultDisplayMap = {};
    function getDefaultDisplay(elem) {
        var temp, doc = elem.ownerDocument, nodeName = elem.nodeName, display = defaultDisplayMap[nodeName];
        if (display) return display;
        temp = doc.body.appendChild(doc.createElement(nodeName));
        display = jQuery.css(temp, "display");
        temp.parentNode.removeChild(temp);
        if (display === "none") display = "block";
        defaultDisplayMap[nodeName] = display;
        return display;
    }
    function showHide(elements, show) {
        var display, elem, values = [], index = 0, length = elements.length;
        // Determine new display value for elements that need to change
        for(; index < length; index++){
            elem = elements[index];
            if (!elem.style) continue;
            display = elem.style.display;
            if (show) {
                // Since we force visibility upon cascade-hidden elements, an immediate (and slow)
                // check is required in this first loop unless we have a nonempty display value (either
                // inline or about-to-be-restored)
                if (display === "none") {
                    values[index] = dataPriv.get(elem, "display") || null;
                    if (!values[index]) elem.style.display = "";
                }
                if (elem.style.display === "" && isHiddenWithinTree(elem)) values[index] = getDefaultDisplay(elem);
            } else if (display !== "none") {
                values[index] = "none";
                // Remember what we're overwriting
                dataPriv.set(elem, "display", display);
            }
        }
        // Set the display of the elements in a second loop to avoid constant reflow
        for(index = 0; index < length; index++)if (values[index] != null) elements[index].style.display = values[index];
        return elements;
    }
    jQuery.fn.extend({
        show: function() {
            return showHide(this, true);
        },
        hide: function() {
            return showHide(this);
        },
        toggle: function(state) {
            if (typeof state === "boolean") return state ? this.show() : this.hide();
            return this.each(function() {
                if (isHiddenWithinTree(this)) jQuery(this).show();
                else jQuery(this).hide();
            });
        }
    });
    var rcheckableType = /^(?:checkbox|radio)$/i;
    var rtagName = /<([a-z][^\/\0>\x20\t\r\n\f]*)/i;
    var rscriptType = /^$|^module$|\/(?:java|ecma)script/i;
    (function() {
        var fragment = document.createDocumentFragment(), div = fragment.appendChild(document.createElement("div")), input = document.createElement("input");
        // Support: Android 4.0 - 4.3 only
        // Check state lost if the name is set (trac-11217)
        // Support: Windows Web Apps (WWA)
        // `name` and `type` must use .setAttribute for WWA (trac-14901)
        input.setAttribute("type", "radio");
        input.setAttribute("checked", "checked");
        input.setAttribute("name", "t");
        div.appendChild(input);
        // Support: Android <=4.1 only
        // Older WebKit doesn't clone checked state correctly in fragments
        support.checkClone = div.cloneNode(true).cloneNode(true).lastChild.checked;
        // Support: IE <=11 only
        // Make sure textarea (and checkbox) defaultValue is properly cloned
        div.innerHTML = "<textarea>x</textarea>";
        support.noCloneChecked = !!div.cloneNode(true).lastChild.defaultValue;
        // Support: IE <=9 only
        // IE <=9 replaces <option> tags with their contents when inserted outside of
        // the select element.
        div.innerHTML = "<option></option>";
        support.option = !!div.lastChild;
    })();
    // We have to close these tags to support XHTML (trac-13200)
    var wrapMap = {
        // XHTML parsers do not magically insert elements in the
        // same way that tag soup parsers do. So we cannot shorten
        // this by omitting <tbody> or other required elements.
        thead: [
            1,
            "<table>",
            "</table>"
        ],
        col: [
            2,
            "<table><colgroup>",
            "</colgroup></table>"
        ],
        tr: [
            2,
            "<table><tbody>",
            "</tbody></table>"
        ],
        td: [
            3,
            "<table><tbody><tr>",
            "</tr></tbody></table>"
        ],
        _default: [
            0,
            "",
            ""
        ]
    };
    wrapMap.tbody = wrapMap.tfoot = wrapMap.colgroup = wrapMap.caption = wrapMap.thead;
    wrapMap.th = wrapMap.td;
    // Support: IE <=9 only
    if (!support.option) wrapMap.optgroup = wrapMap.option = [
        1,
        "<select multiple='multiple'>",
        "</select>"
    ];
    function getAll(context, tag) {
        // Support: IE <=9 - 11 only
        // Use typeof to avoid zero-argument method invocation on host objects (trac-15151)
        var ret;
        if (typeof context.getElementsByTagName !== "undefined") ret = context.getElementsByTagName(tag || "*");
        else if (typeof context.querySelectorAll !== "undefined") ret = context.querySelectorAll(tag || "*");
        else ret = [];
        if (tag === undefined || tag && nodeName(context, tag)) return jQuery.merge([
            context
        ], ret);
        return ret;
    }
    // Mark scripts as having already been evaluated
    function setGlobalEval(elems, refElements) {
        var i = 0, l = elems.length;
        for(; i < l; i++)dataPriv.set(elems[i], "globalEval", !refElements || dataPriv.get(refElements[i], "globalEval"));
    }
    var rhtml = /<|&#?\w+;/;
    function buildFragment(elems, context, scripts, selection, ignored) {
        var elem, tmp, tag, wrap, attached, j, fragment = context.createDocumentFragment(), nodes = [], i = 0, l = elems.length;
        for(; i < l; i++){
            elem = elems[i];
            if (elem || elem === 0) {
                // Add nodes directly
                if (toType(elem) === "object") // Support: Android <=4.0 only, PhantomJS 1 only
                // push.apply(_, arraylike) throws on ancient WebKit
                jQuery.merge(nodes, elem.nodeType ? [
                    elem
                ] : elem);
                else if (!rhtml.test(elem)) nodes.push(context.createTextNode(elem));
                else {
                    tmp = tmp || fragment.appendChild(context.createElement("div"));
                    // Deserialize a standard representation
                    tag = (rtagName.exec(elem) || [
                        "",
                        ""
                    ])[1].toLowerCase();
                    wrap = wrapMap[tag] || wrapMap._default;
                    tmp.innerHTML = wrap[1] + jQuery.htmlPrefilter(elem) + wrap[2];
                    // Descend through wrappers to the right content
                    j = wrap[0];
                    while(j--)tmp = tmp.lastChild;
                    // Support: Android <=4.0 only, PhantomJS 1 only
                    // push.apply(_, arraylike) throws on ancient WebKit
                    jQuery.merge(nodes, tmp.childNodes);
                    // Remember the top-level container
                    tmp = fragment.firstChild;
                    // Ensure the created nodes are orphaned (trac-12392)
                    tmp.textContent = "";
                }
            }
        }
        // Remove wrapper from fragment
        fragment.textContent = "";
        i = 0;
        while(elem = nodes[i++]){
            // Skip elements already in the context collection (trac-4087)
            if (selection && jQuery.inArray(elem, selection) > -1) {
                if (ignored) ignored.push(elem);
                continue;
            }
            attached = isAttached(elem);
            // Append to fragment
            tmp = getAll(fragment.appendChild(elem), "script");
            // Preserve script evaluation history
            if (attached) setGlobalEval(tmp);
            // Capture executables
            if (scripts) {
                j = 0;
                while(elem = tmp[j++])if (rscriptType.test(elem.type || "")) scripts.push(elem);
            }
        }
        return fragment;
    }
    var rtypenamespace = /^([^.]*)(?:\.(.+)|)/;
    function returnTrue() {
        return true;
    }
    function returnFalse() {
        return false;
    }
    function on(elem, types, selector, data, fn, one) {
        var origFn, type;
        // Types can be a map of types/handlers
        if (typeof types === "object") {
            // ( types-Object, selector, data )
            if (typeof selector !== "string") {
                // ( types-Object, data )
                data = data || selector;
                selector = undefined;
            }
            for(type in types)on(elem, type, selector, data, types[type], one);
            return elem;
        }
        if (data == null && fn == null) {
            // ( types, fn )
            fn = selector;
            data = selector = undefined;
        } else if (fn == null) {
            if (typeof selector === "string") {
                // ( types, selector, fn )
                fn = data;
                data = undefined;
            } else {
                // ( types, data, fn )
                fn = data;
                data = selector;
                selector = undefined;
            }
        }
        if (fn === false) fn = returnFalse;
        else if (!fn) return elem;
        if (one === 1) {
            origFn = fn;
            fn = function(event) {
                // Can use an empty set, since event contains the info
                jQuery().off(event);
                return origFn.apply(this, arguments);
            };
            // Use same guid so caller can remove using origFn
            fn.guid = origFn.guid || (origFn.guid = jQuery.guid++);
        }
        return elem.each(function() {
            jQuery.event.add(this, types, fn, data, selector);
        });
    }
    /*
 * Helper functions for managing events -- not part of the public interface.
 * Props to Dean Edwards' addEvent library for many of the ideas.
 */ jQuery.event = {
        global: {},
        add: function(elem, types, handler, data, selector) {
            var handleObjIn, eventHandle, tmp, events, t, handleObj, special, handlers, type, namespaces, origType, elemData = dataPriv.get(elem);
            // Only attach events to objects that accept data
            if (!acceptData(elem)) return;
            // Caller can pass in an object of custom data in lieu of the handler
            if (handler.handler) {
                handleObjIn = handler;
                handler = handleObjIn.handler;
                selector = handleObjIn.selector;
            }
            // Ensure that invalid selectors throw exceptions at attach time
            // Evaluate against documentElement in case elem is a non-element node (e.g., document)
            if (selector) jQuery.find.matchesSelector(documentElement, selector);
            // Make sure that the handler has a unique ID, used to find/remove it later
            if (!handler.guid) handler.guid = jQuery.guid++;
            // Init the element's event structure and main handler, if this is the first
            if (!(events = elemData.events)) events = elemData.events = Object.create(null);
            if (!(eventHandle = elemData.handle)) eventHandle = elemData.handle = function(e) {
                // Discard the second event of a jQuery.event.trigger() and
                // when an event is called after a page has unloaded
                return typeof jQuery !== "undefined" && jQuery.event.triggered !== e.type ? jQuery.event.dispatch.apply(elem, arguments) : undefined;
            };
            // Handle multiple events separated by a space
            types = (types || "").match(rnothtmlwhite) || [
                ""
            ];
            t = types.length;
            while(t--){
                tmp = rtypenamespace.exec(types[t]) || [];
                type = origType = tmp[1];
                namespaces = (tmp[2] || "").split(".").sort();
                // There *must* be a type, no attaching namespace-only handlers
                if (!type) continue;
                // If event changes its type, use the special event handlers for the changed type
                special = jQuery.event.special[type] || {};
                // If selector defined, determine special event api type, otherwise given type
                type = (selector ? special.delegateType : special.bindType) || type;
                // Update special based on newly reset type
                special = jQuery.event.special[type] || {};
                // handleObj is passed to all event handlers
                handleObj = jQuery.extend({
                    type: type,
                    origType: origType,
                    data: data,
                    handler: handler,
                    guid: handler.guid,
                    selector: selector,
                    needsContext: selector && jQuery.expr.match.needsContext.test(selector),
                    namespace: namespaces.join(".")
                }, handleObjIn);
                // Init the event handler queue if we're the first
                if (!(handlers = events[type])) {
                    handlers = events[type] = [];
                    handlers.delegateCount = 0;
                    // Only use addEventListener if the special events handler returns false
                    if (!special.setup || special.setup.call(elem, data, namespaces, eventHandle) === false) {
                        if (elem.addEventListener) elem.addEventListener(type, eventHandle);
                    }
                }
                if (special.add) {
                    special.add.call(elem, handleObj);
                    if (!handleObj.handler.guid) handleObj.handler.guid = handler.guid;
                }
                // Add to the element's handler list, delegates in front
                if (selector) handlers.splice(handlers.delegateCount++, 0, handleObj);
                else handlers.push(handleObj);
                // Keep track of which events have ever been used, for event optimization
                jQuery.event.global[type] = true;
            }
        },
        // Detach an event or set of events from an element
        remove: function(elem, types, handler, selector, mappedTypes) {
            var j, origCount, tmp, events, t, handleObj, special, handlers, type, namespaces, origType, elemData = dataPriv.hasData(elem) && dataPriv.get(elem);
            if (!elemData || !(events = elemData.events)) return;
            // Once for each type.namespace in types; type may be omitted
            types = (types || "").match(rnothtmlwhite) || [
                ""
            ];
            t = types.length;
            while(t--){
                tmp = rtypenamespace.exec(types[t]) || [];
                type = origType = tmp[1];
                namespaces = (tmp[2] || "").split(".").sort();
                // Unbind all events (on this namespace, if provided) for the element
                if (!type) {
                    for(type in events)jQuery.event.remove(elem, type + types[t], handler, selector, true);
                    continue;
                }
                special = jQuery.event.special[type] || {};
                type = (selector ? special.delegateType : special.bindType) || type;
                handlers = events[type] || [];
                tmp = tmp[2] && new RegExp("(^|\\.)" + namespaces.join("\\.(?:.*\\.|)") + "(\\.|$)");
                // Remove matching events
                origCount = j = handlers.length;
                while(j--){
                    handleObj = handlers[j];
                    if ((mappedTypes || origType === handleObj.origType) && (!handler || handler.guid === handleObj.guid) && (!tmp || tmp.test(handleObj.namespace)) && (!selector || selector === handleObj.selector || selector === "**" && handleObj.selector)) {
                        handlers.splice(j, 1);
                        if (handleObj.selector) handlers.delegateCount--;
                        if (special.remove) special.remove.call(elem, handleObj);
                    }
                }
                // Remove generic event handler if we removed something and no more handlers exist
                // (avoids potential for endless recursion during removal of special event handlers)
                if (origCount && !handlers.length) {
                    if (!special.teardown || special.teardown.call(elem, namespaces, elemData.handle) === false) jQuery.removeEvent(elem, type, elemData.handle);
                    delete events[type];
                }
            }
            // Remove data and the expando if it's no longer used
            if (jQuery.isEmptyObject(events)) dataPriv.remove(elem, "handle events");
        },
        dispatch: function(nativeEvent) {
            var i, j, ret, matched, handleObj, handlerQueue, args = new Array(arguments.length), // Make a writable jQuery.Event from the native event object
            event = jQuery.event.fix(nativeEvent), handlers = (dataPriv.get(this, "events") || Object.create(null))[event.type] || [], special = jQuery.event.special[event.type] || {};
            // Use the fix-ed jQuery.Event rather than the (read-only) native event
            args[0] = event;
            for(i = 1; i < arguments.length; i++)args[i] = arguments[i];
            event.delegateTarget = this;
            // Call the preDispatch hook for the mapped type, and let it bail if desired
            if (special.preDispatch && special.preDispatch.call(this, event) === false) return;
            // Determine handlers
            handlerQueue = jQuery.event.handlers.call(this, event, handlers);
            // Run delegates first; they may want to stop propagation beneath us
            i = 0;
            while((matched = handlerQueue[i++]) && !event.isPropagationStopped()){
                event.currentTarget = matched.elem;
                j = 0;
                while((handleObj = matched.handlers[j++]) && !event.isImmediatePropagationStopped())// If the event is namespaced, then each handler is only invoked if it is
                // specially universal or its namespaces are a superset of the event's.
                if (!event.rnamespace || handleObj.namespace === false || event.rnamespace.test(handleObj.namespace)) {
                    event.handleObj = handleObj;
                    event.data = handleObj.data;
                    ret = ((jQuery.event.special[handleObj.origType] || {}).handle || handleObj.handler).apply(matched.elem, args);
                    if (ret !== undefined) {
                        if ((event.result = ret) === false) {
                            event.preventDefault();
                            event.stopPropagation();
                        }
                    }
                }
            }
            // Call the postDispatch hook for the mapped type
            if (special.postDispatch) special.postDispatch.call(this, event);
            return event.result;
        },
        handlers: function(event, handlers) {
            var i, handleObj, sel, matchedHandlers, matchedSelectors, handlerQueue = [], delegateCount = handlers.delegateCount, cur = event.target;
            // Find delegate handlers
            if (delegateCount && // Support: IE <=9
            // Black-hole SVG <use> instance trees (trac-13180)
            cur.nodeType && // Support: Firefox <=42
            // Suppress spec-violating clicks indicating a non-primary pointer button (trac-3861)
            // https://www.w3.org/TR/DOM-Level-3-Events/#event-type-click
            // Support: IE 11 only
            // ...but not arrow key "clicks" of radio inputs, which can have `button` -1 (gh-2343)
            !(event.type === "click" && event.button >= 1)) {
                for(; cur !== this; cur = cur.parentNode || this)// Don't check non-elements (trac-13208)
                // Don't process clicks on disabled elements (trac-6911, trac-8165, trac-11382, trac-11764)
                if (cur.nodeType === 1 && !(event.type === "click" && cur.disabled === true)) {
                    matchedHandlers = [];
                    matchedSelectors = {};
                    for(i = 0; i < delegateCount; i++){
                        handleObj = handlers[i];
                        // Don't conflict with Object.prototype properties (trac-13203)
                        sel = handleObj.selector + " ";
                        if (matchedSelectors[sel] === undefined) matchedSelectors[sel] = handleObj.needsContext ? jQuery(sel, this).index(cur) > -1 : jQuery.find(sel, this, null, [
                            cur
                        ]).length;
                        if (matchedSelectors[sel]) matchedHandlers.push(handleObj);
                    }
                    if (matchedHandlers.length) handlerQueue.push({
                        elem: cur,
                        handlers: matchedHandlers
                    });
                }
            }
            // Add the remaining (directly-bound) handlers
            cur = this;
            if (delegateCount < handlers.length) handlerQueue.push({
                elem: cur,
                handlers: handlers.slice(delegateCount)
            });
            return handlerQueue;
        },
        addProp: function(name, hook) {
            Object.defineProperty(jQuery.Event.prototype, name, {
                enumerable: true,
                configurable: true,
                get: isFunction(hook) ? function() {
                    if (this.originalEvent) return hook(this.originalEvent);
                } : function() {
                    if (this.originalEvent) return this.originalEvent[name];
                },
                set: function(value) {
                    Object.defineProperty(this, name, {
                        enumerable: true,
                        configurable: true,
                        writable: true,
                        value: value
                    });
                }
            });
        },
        fix: function(originalEvent) {
            return originalEvent[jQuery.expando] ? originalEvent : new jQuery.Event(originalEvent);
        },
        special: {
            load: {
                // Prevent triggered image.load events from bubbling to window.load
                noBubble: true
            },
            click: {
                // Utilize native event to ensure correct state for checkable inputs
                setup: function(data) {
                    // For mutual compressibility with _default, replace `this` access with a local var.
                    // `|| data` is dead code meant only to preserve the variable through minification.
                    var el = this || data;
                    // Claim the first handler
                    if (rcheckableType.test(el.type) && el.click && nodeName(el, "input")) // dataPriv.set( el, "click", ... )
                    leverageNative(el, "click", true);
                    // Return false to allow normal processing in the caller
                    return false;
                },
                trigger: function(data) {
                    // For mutual compressibility with _default, replace `this` access with a local var.
                    // `|| data` is dead code meant only to preserve the variable through minification.
                    var el = this || data;
                    // Force setup before triggering a click
                    if (rcheckableType.test(el.type) && el.click && nodeName(el, "input")) leverageNative(el, "click");
                    // Return non-false to allow normal event-path propagation
                    return true;
                },
                // For cross-browser consistency, suppress native .click() on links
                // Also prevent it if we're currently inside a leveraged native-event stack
                _default: function(event) {
                    var target = event.target;
                    return rcheckableType.test(target.type) && target.click && nodeName(target, "input") && dataPriv.get(target, "click") || nodeName(target, "a");
                }
            },
            beforeunload: {
                postDispatch: function(event) {
                    // Support: Firefox 20+
                    // Firefox doesn't alert if the returnValue field is not set.
                    if (event.result !== undefined && event.originalEvent) event.originalEvent.returnValue = event.result;
                }
            }
        }
    };
    // Ensure the presence of an event listener that handles manually-triggered
    // synthetic events by interrupting progress until reinvoked in response to
    // *native* events that it fires directly, ensuring that state changes have
    // already occurred before other listeners are invoked.
    function leverageNative(el, type, isSetup) {
        // Missing `isSetup` indicates a trigger call, which must force setup through jQuery.event.add
        if (!isSetup) {
            if (dataPriv.get(el, type) === undefined) jQuery.event.add(el, type, returnTrue);
            return;
        }
        // Register the controller as a special universal handler for all event namespaces
        dataPriv.set(el, type, false);
        jQuery.event.add(el, type, {
            namespace: false,
            handler: function(event) {
                var result, saved = dataPriv.get(this, type);
                if (event.isTrigger & 1 && this[type]) {
                    // Interrupt processing of the outer synthetic .trigger()ed event
                    if (!saved) {
                        // Store arguments for use when handling the inner native event
                        // There will always be at least one argument (an event object), so this array
                        // will not be confused with a leftover capture object.
                        saved = slice.call(arguments);
                        dataPriv.set(this, type, saved);
                        // Trigger the native event and capture its result
                        this[type]();
                        result = dataPriv.get(this, type);
                        dataPriv.set(this, type, false);
                        if (saved !== result) {
                            // Cancel the outer synthetic event
                            event.stopImmediatePropagation();
                            event.preventDefault();
                            return result;
                        }
                    // If this is an inner synthetic event for an event with a bubbling surrogate
                    // (focus or blur), assume that the surrogate already propagated from triggering
                    // the native event and prevent that from happening again here.
                    // This technically gets the ordering wrong w.r.t. to `.trigger()` (in which the
                    // bubbling surrogate propagates *after* the non-bubbling base), but that seems
                    // less bad than duplication.
                    } else if ((jQuery.event.special[type] || {}).delegateType) event.stopPropagation();
                // If this is a native event triggered above, everything is now in order
                // Fire an inner synthetic event with the original arguments
                } else if (saved) {
                    // ...and capture the result
                    dataPriv.set(this, type, jQuery.event.trigger(saved[0], saved.slice(1), this));
                    // Abort handling of the native event by all jQuery handlers while allowing
                    // native handlers on the same element to run. On target, this is achieved
                    // by stopping immediate propagation just on the jQuery event. However,
                    // the native event is re-wrapped by a jQuery one on each level of the
                    // propagation so the only way to stop it for jQuery is to stop it for
                    // everyone via native `stopPropagation()`. This is not a problem for
                    // focus/blur which don't bubble, but it does also stop click on checkboxes
                    // and radios. We accept this limitation.
                    event.stopPropagation();
                    event.isImmediatePropagationStopped = returnTrue;
                }
            }
        });
    }
    jQuery.removeEvent = function(elem, type, handle) {
        // This "if" is needed for plain objects
        if (elem.removeEventListener) elem.removeEventListener(type, handle);
    };
    jQuery.Event = function(src, props) {
        // Allow instantiation without the 'new' keyword
        if (!(this instanceof jQuery.Event)) return new jQuery.Event(src, props);
        // Event object
        if (src && src.type) {
            this.originalEvent = src;
            this.type = src.type;
            // Events bubbling up the document may have been marked as prevented
            // by a handler lower down the tree; reflect the correct value.
            this.isDefaultPrevented = src.defaultPrevented || src.defaultPrevented === undefined && // Support: Android <=2.3 only
            src.returnValue === false ? returnTrue : returnFalse;
            // Create target properties
            // Support: Safari <=6 - 7 only
            // Target should not be a text node (trac-504, trac-13143)
            this.target = src.target && src.target.nodeType === 3 ? src.target.parentNode : src.target;
            this.currentTarget = src.currentTarget;
            this.relatedTarget = src.relatedTarget;
        // Event type
        } else this.type = src;
        // Put explicitly provided properties onto the event object
        if (props) jQuery.extend(this, props);
        // Create a timestamp if incoming event doesn't have one
        this.timeStamp = src && src.timeStamp || Date.now();
        // Mark it as fixed
        this[jQuery.expando] = true;
    };
    // jQuery.Event is based on DOM3 Events as specified by the ECMAScript Language Binding
    // https://www.w3.org/TR/2003/WD-DOM-Level-3-Events-20030331/ecma-script-binding.html
    jQuery.Event.prototype = {
        constructor: jQuery.Event,
        isDefaultPrevented: returnFalse,
        isPropagationStopped: returnFalse,
        isImmediatePropagationStopped: returnFalse,
        isSimulated: false,
        preventDefault: function() {
            var e = this.originalEvent;
            this.isDefaultPrevented = returnTrue;
            if (e && !this.isSimulated) e.preventDefault();
        },
        stopPropagation: function() {
            var e = this.originalEvent;
            this.isPropagationStopped = returnTrue;
            if (e && !this.isSimulated) e.stopPropagation();
        },
        stopImmediatePropagation: function() {
            var e = this.originalEvent;
            this.isImmediatePropagationStopped = returnTrue;
            if (e && !this.isSimulated) e.stopImmediatePropagation();
            this.stopPropagation();
        }
    };
    // Includes all common event props including KeyEvent and MouseEvent specific props
    jQuery.each({
        altKey: true,
        bubbles: true,
        cancelable: true,
        changedTouches: true,
        ctrlKey: true,
        detail: true,
        eventPhase: true,
        metaKey: true,
        pageX: true,
        pageY: true,
        shiftKey: true,
        view: true,
        "char": true,
        code: true,
        charCode: true,
        key: true,
        keyCode: true,
        button: true,
        buttons: true,
        clientX: true,
        clientY: true,
        offsetX: true,
        offsetY: true,
        pointerId: true,
        pointerType: true,
        screenX: true,
        screenY: true,
        targetTouches: true,
        toElement: true,
        touches: true,
        which: true
    }, jQuery.event.addProp);
    jQuery.each({
        focus: "focusin",
        blur: "focusout"
    }, function(type, delegateType) {
        function focusMappedHandler(nativeEvent) {
            if (document.documentMode) {
                // Support: IE 11+
                // Attach a single focusin/focusout handler on the document while someone wants
                // focus/blur. This is because the former are synchronous in IE while the latter
                // are async. In other browsers, all those handlers are invoked synchronously.
                // `handle` from private data would already wrap the event, but we need
                // to change the `type` here.
                var handle = dataPriv.get(this, "handle"), event = jQuery.event.fix(nativeEvent);
                event.type = nativeEvent.type === "focusin" ? "focus" : "blur";
                event.isSimulated = true;
                // First, handle focusin/focusout
                handle(nativeEvent);
                // ...then, handle focus/blur
                //
                // focus/blur don't bubble while focusin/focusout do; simulate the former by only
                // invoking the handler at the lower level.
                if (event.target === event.currentTarget) // The setup part calls `leverageNative`, which, in turn, calls
                // `jQuery.event.add`, so event handle will already have been set
                // by this point.
                handle(event);
            } else // For non-IE browsers, attach a single capturing handler on the document
            // while someone wants focusin/focusout.
            jQuery.event.simulate(delegateType, nativeEvent.target, jQuery.event.fix(nativeEvent));
        }
        jQuery.event.special[type] = {
            // Utilize native event if possible so blur/focus sequence is correct
            setup: function() {
                var attaches;
                // Claim the first handler
                // dataPriv.set( this, "focus", ... )
                // dataPriv.set( this, "blur", ... )
                leverageNative(this, type, true);
                if (document.documentMode) {
                    // Support: IE 9 - 11+
                    // We use the same native handler for focusin & focus (and focusout & blur)
                    // so we need to coordinate setup & teardown parts between those events.
                    // Use `delegateType` as the key as `type` is already used by `leverageNative`.
                    attaches = dataPriv.get(this, delegateType);
                    if (!attaches) this.addEventListener(delegateType, focusMappedHandler);
                    dataPriv.set(this, delegateType, (attaches || 0) + 1);
                } else // Return false to allow normal processing in the caller
                return false;
            },
            trigger: function() {
                // Force setup before trigger
                leverageNative(this, type);
                // Return non-false to allow normal event-path propagation
                return true;
            },
            teardown: function() {
                var attaches;
                if (document.documentMode) {
                    attaches = dataPriv.get(this, delegateType) - 1;
                    if (!attaches) {
                        this.removeEventListener(delegateType, focusMappedHandler);
                        dataPriv.remove(this, delegateType);
                    } else dataPriv.set(this, delegateType, attaches);
                } else // Return false to indicate standard teardown should be applied
                return false;
            },
            // Suppress native focus or blur if we're currently inside
            // a leveraged native-event stack
            _default: function(event) {
                return dataPriv.get(event.target, type);
            },
            delegateType: delegateType
        };
        // Support: Firefox <=44
        // Firefox doesn't have focus(in | out) events
        // Related ticket - https://bugzilla.mozilla.org/show_bug.cgi?id=687787
        //
        // Support: Chrome <=48 - 49, Safari <=9.0 - 9.1
        // focus(in | out) events fire after focus & blur events,
        // which is spec violation - http://www.w3.org/TR/DOM-Level-3-Events/#events-focusevent-event-order
        // Related ticket - https://bugs.chromium.org/p/chromium/issues/detail?id=449857
        //
        // Support: IE 9 - 11+
        // To preserve relative focusin/focus & focusout/blur event order guaranteed on the 3.x branch,
        // attach a single handler for both events in IE.
        jQuery.event.special[delegateType] = {
            setup: function() {
                // Handle: regular nodes (via `this.ownerDocument`), window
                // (via `this.document`) & document (via `this`).
                var doc = this.ownerDocument || this.document || this, dataHolder = document.documentMode ? this : doc, attaches = dataPriv.get(dataHolder, delegateType);
                // Support: IE 9 - 11+
                // We use the same native handler for focusin & focus (and focusout & blur)
                // so we need to coordinate setup & teardown parts between those events.
                // Use `delegateType` as the key as `type` is already used by `leverageNative`.
                if (!attaches) {
                    if (document.documentMode) this.addEventListener(delegateType, focusMappedHandler);
                    else doc.addEventListener(type, focusMappedHandler, true);
                }
                dataPriv.set(dataHolder, delegateType, (attaches || 0) + 1);
            },
            teardown: function() {
                var doc = this.ownerDocument || this.document || this, dataHolder = document.documentMode ? this : doc, attaches = dataPriv.get(dataHolder, delegateType) - 1;
                if (!attaches) {
                    if (document.documentMode) this.removeEventListener(delegateType, focusMappedHandler);
                    else doc.removeEventListener(type, focusMappedHandler, true);
                    dataPriv.remove(dataHolder, delegateType);
                } else dataPriv.set(dataHolder, delegateType, attaches);
            }
        };
    });
    // Create mouseenter/leave events using mouseover/out and event-time checks
    // so that event delegation works in jQuery.
    // Do the same for pointerenter/pointerleave and pointerover/pointerout
    //
    // Support: Safari 7 only
    // Safari sends mouseenter too often; see:
    // https://bugs.chromium.org/p/chromium/issues/detail?id=470258
    // for the description of the bug (it existed in older Chrome versions as well).
    jQuery.each({
        mouseenter: "mouseover",
        mouseleave: "mouseout",
        pointerenter: "pointerover",
        pointerleave: "pointerout"
    }, function(orig, fix) {
        jQuery.event.special[orig] = {
            delegateType: fix,
            bindType: fix,
            handle: function(event) {
                var ret, target = this, related = event.relatedTarget, handleObj = event.handleObj;
                // For mouseenter/leave call the handler if related is outside the target.
                // NB: No relatedTarget if the mouse left/entered the browser window
                if (!related || related !== target && !jQuery.contains(target, related)) {
                    event.type = handleObj.origType;
                    ret = handleObj.handler.apply(this, arguments);
                    event.type = fix;
                }
                return ret;
            }
        };
    });
    jQuery.fn.extend({
        on: function(types, selector, data, fn) {
            return on(this, types, selector, data, fn);
        },
        one: function(types, selector, data, fn) {
            return on(this, types, selector, data, fn, 1);
        },
        off: function(types, selector, fn) {
            var handleObj, type;
            if (types && types.preventDefault && types.handleObj) {
                // ( event )  dispatched jQuery.Event
                handleObj = types.handleObj;
                jQuery(types.delegateTarget).off(handleObj.namespace ? handleObj.origType + "." + handleObj.namespace : handleObj.origType, handleObj.selector, handleObj.handler);
                return this;
            }
            if (typeof types === "object") {
                // ( types-object [, selector] )
                for(type in types)this.off(type, selector, types[type]);
                return this;
            }
            if (selector === false || typeof selector === "function") {
                // ( types [, fn] )
                fn = selector;
                selector = undefined;
            }
            if (fn === false) fn = returnFalse;
            return this.each(function() {
                jQuery.event.remove(this, types, fn, selector);
            });
        }
    });
    var // Support: IE <=10 - 11, Edge 12 - 13 only
    // In IE/Edge using regex groups here causes severe slowdowns.
    // See https://connect.microsoft.com/IE/feedback/details/1736512/
    rnoInnerhtml = /<script|<style|<link/i, // checked="checked" or checked
    rchecked = /checked\s*(?:[^=]|=\s*.checked.)/i, rcleanScript = /^\s*<!\[CDATA\[|\]\]>\s*$/g;
    // Prefer a tbody over its parent table for containing new rows
    function manipulationTarget(elem, content) {
        if (nodeName(elem, "table") && nodeName(content.nodeType !== 11 ? content : content.firstChild, "tr")) return jQuery(elem).children("tbody")[0] || elem;
        return elem;
    }
    // Replace/restore the type attribute of script elements for safe DOM manipulation
    function disableScript(elem) {
        elem.type = (elem.getAttribute("type") !== null) + "/" + elem.type;
        return elem;
    }
    function restoreScript(elem) {
        if ((elem.type || "").slice(0, 5) === "true/") elem.type = elem.type.slice(5);
        else elem.removeAttribute("type");
        return elem;
    }
    function cloneCopyEvent(src, dest) {
        var i, l, type, pdataOld, udataOld, udataCur, events;
        if (dest.nodeType !== 1) return;
        // 1. Copy private data: events, handlers, etc.
        if (dataPriv.hasData(src)) {
            pdataOld = dataPriv.get(src);
            events = pdataOld.events;
            if (events) {
                dataPriv.remove(dest, "handle events");
                for(type in events)for(i = 0, l = events[type].length; i < l; i++)jQuery.event.add(dest, type, events[type][i]);
            }
        }
        // 2. Copy user data
        if (dataUser.hasData(src)) {
            udataOld = dataUser.access(src);
            udataCur = jQuery.extend({}, udataOld);
            dataUser.set(dest, udataCur);
        }
    }
    // Fix IE bugs, see support tests
    function fixInput(src, dest) {
        var nodeName = dest.nodeName.toLowerCase();
        // Fails to persist the checked state of a cloned checkbox or radio button.
        if (nodeName === "input" && rcheckableType.test(src.type)) dest.checked = src.checked;
        else if (nodeName === "input" || nodeName === "textarea") dest.defaultValue = src.defaultValue;
    }
    function domManip(collection, args, callback, ignored) {
        // Flatten any nested arrays
        args = flat(args);
        var fragment, first, scripts, hasScripts, node, doc, i = 0, l = collection.length, iNoClone = l - 1, value = args[0], valueIsFunction = isFunction(value);
        // We can't cloneNode fragments that contain checked, in WebKit
        if (valueIsFunction || l > 1 && typeof value === "string" && !support.checkClone && rchecked.test(value)) return collection.each(function(index) {
            var self = collection.eq(index);
            if (valueIsFunction) args[0] = value.call(this, index, self.html());
            domManip(self, args, callback, ignored);
        });
        if (l) {
            fragment = buildFragment(args, collection[0].ownerDocument, false, collection, ignored);
            first = fragment.firstChild;
            if (fragment.childNodes.length === 1) fragment = first;
            // Require either new content or an interest in ignored elements to invoke the callback
            if (first || ignored) {
                scripts = jQuery.map(getAll(fragment, "script"), disableScript);
                hasScripts = scripts.length;
                // Use the original fragment for the last item
                // instead of the first because it can end up
                // being emptied incorrectly in certain situations (trac-8070).
                for(; i < l; i++){
                    node = fragment;
                    if (i !== iNoClone) {
                        node = jQuery.clone(node, true, true);
                        // Keep references to cloned scripts for later restoration
                        if (hasScripts) // Support: Android <=4.0 only, PhantomJS 1 only
                        // push.apply(_, arraylike) throws on ancient WebKit
                        jQuery.merge(scripts, getAll(node, "script"));
                    }
                    callback.call(collection[i], node, i);
                }
                if (hasScripts) {
                    doc = scripts[scripts.length - 1].ownerDocument;
                    // Reenable scripts
                    jQuery.map(scripts, restoreScript);
                    // Evaluate executable scripts on first document insertion
                    for(i = 0; i < hasScripts; i++){
                        node = scripts[i];
                        if (rscriptType.test(node.type || "") && !dataPriv.access(node, "globalEval") && jQuery.contains(doc, node)) {
                            if (node.src && (node.type || "").toLowerCase() !== "module") // Optional AJAX dependency, but won't run scripts if not present
                            {
                                if (jQuery._evalUrl && !node.noModule) jQuery._evalUrl(node.src, {
                                    nonce: node.nonce || node.getAttribute("nonce")
                                }, doc);
                            } else // Unwrap a CDATA section containing script contents. This shouldn't be
                            // needed as in XML documents they're already not visible when
                            // inspecting element contents and in HTML documents they have no
                            // meaning but we're preserving that logic for backwards compatibility.
                            // This will be removed completely in 4.0. See gh-4904.
                            DOMEval(node.textContent.replace(rcleanScript, ""), node, doc);
                        }
                    }
                }
            }
        }
        return collection;
    }
    function remove(elem, selector, keepData) {
        var node, nodes = selector ? jQuery.filter(selector, elem) : elem, i = 0;
        for(; (node = nodes[i]) != null; i++){
            if (!keepData && node.nodeType === 1) jQuery.cleanData(getAll(node));
            if (node.parentNode) {
                if (keepData && isAttached(node)) setGlobalEval(getAll(node, "script"));
                node.parentNode.removeChild(node);
            }
        }
        return elem;
    }
    jQuery.extend({
        htmlPrefilter: function(html) {
            return html;
        },
        clone: function(elem, dataAndEvents, deepDataAndEvents) {
            var i, l, srcElements, destElements, clone = elem.cloneNode(true), inPage = isAttached(elem);
            // Fix IE cloning issues
            if (!support.noCloneChecked && (elem.nodeType === 1 || elem.nodeType === 11) && !jQuery.isXMLDoc(elem)) {
                // We eschew jQuery#find here for performance reasons:
                // https://jsperf.com/getall-vs-sizzle/2
                destElements = getAll(clone);
                srcElements = getAll(elem);
                for(i = 0, l = srcElements.length; i < l; i++)fixInput(srcElements[i], destElements[i]);
            }
            // Copy the events from the original to the clone
            if (dataAndEvents) {
                if (deepDataAndEvents) {
                    srcElements = srcElements || getAll(elem);
                    destElements = destElements || getAll(clone);
                    for(i = 0, l = srcElements.length; i < l; i++)cloneCopyEvent(srcElements[i], destElements[i]);
                } else cloneCopyEvent(elem, clone);
            }
            // Preserve script evaluation history
            destElements = getAll(clone, "script");
            if (destElements.length > 0) setGlobalEval(destElements, !inPage && getAll(elem, "script"));
            // Return the cloned set
            return clone;
        },
        cleanData: function(elems) {
            var data, elem, type, special = jQuery.event.special, i = 0;
            for(; (elem = elems[i]) !== undefined; i++)if (acceptData(elem)) {
                if (data = elem[dataPriv.expando]) {
                    if (data.events) {
                        for(type in data.events)if (special[type]) jQuery.event.remove(elem, type);
                        else jQuery.removeEvent(elem, type, data.handle);
                    }
                    // Support: Chrome <=35 - 45+
                    // Assign undefined instead of using delete, see Data#remove
                    elem[dataPriv.expando] = undefined;
                }
                if (elem[dataUser.expando]) // Support: Chrome <=35 - 45+
                // Assign undefined instead of using delete, see Data#remove
                elem[dataUser.expando] = undefined;
            }
        }
    });
    jQuery.fn.extend({
        detach: function(selector) {
            return remove(this, selector, true);
        },
        remove: function(selector) {
            return remove(this, selector);
        },
        text: function(value) {
            return access(this, function(value) {
                return value === undefined ? jQuery.text(this) : this.empty().each(function() {
                    if (this.nodeType === 1 || this.nodeType === 11 || this.nodeType === 9) this.textContent = value;
                });
            }, null, value, arguments.length);
        },
        append: function() {
            return domManip(this, arguments, function(elem) {
                if (this.nodeType === 1 || this.nodeType === 11 || this.nodeType === 9) {
                    var target = manipulationTarget(this, elem);
                    target.appendChild(elem);
                }
            });
        },
        prepend: function() {
            return domManip(this, arguments, function(elem) {
                if (this.nodeType === 1 || this.nodeType === 11 || this.nodeType === 9) {
                    var target = manipulationTarget(this, elem);
                    target.insertBefore(elem, target.firstChild);
                }
            });
        },
        before: function() {
            return domManip(this, arguments, function(elem) {
                if (this.parentNode) this.parentNode.insertBefore(elem, this);
            });
        },
        after: function() {
            return domManip(this, arguments, function(elem) {
                if (this.parentNode) this.parentNode.insertBefore(elem, this.nextSibling);
            });
        },
        empty: function() {
            var elem, i = 0;
            for(; (elem = this[i]) != null; i++)if (elem.nodeType === 1) {
                // Prevent memory leaks
                jQuery.cleanData(getAll(elem, false));
                // Remove any remaining nodes
                elem.textContent = "";
            }
            return this;
        },
        clone: function(dataAndEvents, deepDataAndEvents) {
            dataAndEvents = dataAndEvents == null ? false : dataAndEvents;
            deepDataAndEvents = deepDataAndEvents == null ? dataAndEvents : deepDataAndEvents;
            return this.map(function() {
                return jQuery.clone(this, dataAndEvents, deepDataAndEvents);
            });
        },
        html: function(value) {
            return access(this, function(value) {
                var elem = this[0] || {}, i = 0, l = this.length;
                if (value === undefined && elem.nodeType === 1) return elem.innerHTML;
                // See if we can take a shortcut and just use innerHTML
                if (typeof value === "string" && !rnoInnerhtml.test(value) && !wrapMap[(rtagName.exec(value) || [
                    "",
                    ""
                ])[1].toLowerCase()]) {
                    value = jQuery.htmlPrefilter(value);
                    try {
                        for(; i < l; i++){
                            elem = this[i] || {};
                            // Remove element nodes and prevent memory leaks
                            if (elem.nodeType === 1) {
                                jQuery.cleanData(getAll(elem, false));
                                elem.innerHTML = value;
                            }
                        }
                        elem = 0;
                    // If using innerHTML throws an exception, use the fallback method
                    } catch (e) {}
                }
                if (elem) this.empty().append(value);
            }, null, value, arguments.length);
        },
        replaceWith: function() {
            var ignored = [];
            // Make the changes, replacing each non-ignored context element with the new content
            return domManip(this, arguments, function(elem) {
                var parent = this.parentNode;
                if (jQuery.inArray(this, ignored) < 0) {
                    jQuery.cleanData(getAll(this));
                    if (parent) parent.replaceChild(elem, this);
                }
            // Force callback invocation
            }, ignored);
        }
    });
    jQuery.each({
        appendTo: "append",
        prependTo: "prepend",
        insertBefore: "before",
        insertAfter: "after",
        replaceAll: "replaceWith"
    }, function(name, original) {
        jQuery.fn[name] = function(selector) {
            var elems, ret = [], insert = jQuery(selector), last = insert.length - 1, i = 0;
            for(; i <= last; i++){
                elems = i === last ? this : this.clone(true);
                jQuery(insert[i])[original](elems);
                // Support: Android <=4.0 only, PhantomJS 1 only
                // .get() because push.apply(_, arraylike) throws on ancient WebKit
                push.apply(ret, elems.get());
            }
            return this.pushStack(ret);
        };
    });
    var rnumnonpx = new RegExp("^(" + pnum + ")(?!px)[a-z%]+$", "i");
    var rcustomProp = /^--/;
    var getStyles = function(elem) {
        // Support: IE <=11 only, Firefox <=30 (trac-15098, trac-14150)
        // IE throws on elements created in popups
        // FF meanwhile throws on frame elements through "defaultView.getComputedStyle"
        var view = elem.ownerDocument.defaultView;
        if (!view || !view.opener) view = window1;
        return view.getComputedStyle(elem);
    };
    var swap = function(elem, options, callback) {
        var ret, name, old = {};
        // Remember the old values, and insert the new ones
        for(name in options){
            old[name] = elem.style[name];
            elem.style[name] = options[name];
        }
        ret = callback.call(elem);
        // Revert the old values
        for(name in options)elem.style[name] = old[name];
        return ret;
    };
    var rboxStyle = new RegExp(cssExpand.join("|"), "i");
    (function() {
        // Executing both pixelPosition & boxSizingReliable tests require only one layout
        // so they're executed at the same time to save the second computation.
        function computeStyleTests() {
            // This is a singleton, we need to execute it only once
            if (!div) return;
            container.style.cssText = "position:absolute;left:-11111px;width:60px;margin-top:1px;padding:0;border:0";
            div.style.cssText = "position:relative;display:block;box-sizing:border-box;overflow:scroll;margin:auto;border:1px;padding:1px;width:60%;top:1%";
            documentElement.appendChild(container).appendChild(div);
            var divStyle = window1.getComputedStyle(div);
            pixelPositionVal = divStyle.top !== "1%";
            // Support: Android 4.0 - 4.3 only, Firefox <=3 - 44
            reliableMarginLeftVal = roundPixelMeasures(divStyle.marginLeft) === 12;
            // Support: Android 4.0 - 4.3 only, Safari <=9.1 - 10.1, iOS <=7.0 - 9.3
            // Some styles come back with percentage values, even though they shouldn't
            div.style.right = "60%";
            pixelBoxStylesVal = roundPixelMeasures(divStyle.right) === 36;
            // Support: IE 9 - 11 only
            // Detect misreporting of content dimensions for box-sizing:border-box elements
            boxSizingReliableVal = roundPixelMeasures(divStyle.width) === 36;
            // Support: IE 9 only
            // Detect overflow:scroll screwiness (gh-3699)
            // Support: Chrome <=64
            // Don't get tricked when zoom affects offsetWidth (gh-4029)
            div.style.position = "absolute";
            scrollboxSizeVal = roundPixelMeasures(div.offsetWidth / 3) === 12;
            documentElement.removeChild(container);
            // Nullify the div so it wouldn't be stored in the memory and
            // it will also be a sign that checks already performed
            div = null;
        }
        function roundPixelMeasures(measure) {
            return Math.round(parseFloat(measure));
        }
        var pixelPositionVal, boxSizingReliableVal, scrollboxSizeVal, pixelBoxStylesVal, reliableTrDimensionsVal, reliableMarginLeftVal, container = document.createElement("div"), div = document.createElement("div");
        // Finish early in limited (non-browser) environments
        if (!div.style) return;
        // Support: IE <=9 - 11 only
        // Style of cloned element affects source element cloned (trac-8908)
        div.style.backgroundClip = "content-box";
        div.cloneNode(true).style.backgroundClip = "";
        support.clearCloneStyle = div.style.backgroundClip === "content-box";
        jQuery.extend(support, {
            boxSizingReliable: function() {
                computeStyleTests();
                return boxSizingReliableVal;
            },
            pixelBoxStyles: function() {
                computeStyleTests();
                return pixelBoxStylesVal;
            },
            pixelPosition: function() {
                computeStyleTests();
                return pixelPositionVal;
            },
            reliableMarginLeft: function() {
                computeStyleTests();
                return reliableMarginLeftVal;
            },
            scrollboxSize: function() {
                computeStyleTests();
                return scrollboxSizeVal;
            },
            // Support: IE 9 - 11+, Edge 15 - 18+
            // IE/Edge misreport `getComputedStyle` of table rows with width/height
            // set in CSS while `offset*` properties report correct values.
            // Behavior in IE 9 is more subtle than in newer versions & it passes
            // some versions of this test; make sure not to make it pass there!
            //
            // Support: Firefox 70+
            // Only Firefox includes border widths
            // in computed dimensions. (gh-4529)
            reliableTrDimensions: function() {
                var table, tr, trChild, trStyle;
                if (reliableTrDimensionsVal == null) {
                    table = document.createElement("table");
                    tr = document.createElement("tr");
                    trChild = document.createElement("div");
                    table.style.cssText = "position:absolute;left:-11111px;border-collapse:separate";
                    tr.style.cssText = "border:1px solid";
                    // Support: Chrome 86+
                    // Height set through cssText does not get applied.
                    // Computed height then comes back as 0.
                    tr.style.height = "1px";
                    trChild.style.height = "9px";
                    // Support: Android 8 Chrome 86+
                    // In our bodyBackground.html iframe,
                    // display for all div elements is set to "inline",
                    // which causes a problem only in Android 8 Chrome 86.
                    // Ensuring the div is display: block
                    // gets around this issue.
                    trChild.style.display = "block";
                    documentElement.appendChild(table).appendChild(tr).appendChild(trChild);
                    trStyle = window1.getComputedStyle(tr);
                    reliableTrDimensionsVal = parseInt(trStyle.height, 10) + parseInt(trStyle.borderTopWidth, 10) + parseInt(trStyle.borderBottomWidth, 10) === tr.offsetHeight;
                    documentElement.removeChild(table);
                }
                return reliableTrDimensionsVal;
            }
        });
    })();
    function curCSS(elem, name, computed) {
        var width, minWidth, maxWidth, ret, isCustomProp = rcustomProp.test(name), // Support: Firefox 51+
        // Retrieving style before computed somehow
        // fixes an issue with getting wrong values
        // on detached elements
        style = elem.style;
        computed = computed || getStyles(elem);
        // getPropertyValue is needed for:
        //   .css('filter') (IE 9 only, trac-12537)
        //   .css('--customProperty) (gh-3144)
        if (computed) {
            // Support: IE <=9 - 11+
            // IE only supports `"float"` in `getPropertyValue`; in computed styles
            // it's only available as `"cssFloat"`. We no longer modify properties
            // sent to `.css()` apart from camelCasing, so we need to check both.
            // Normally, this would create difference in behavior: if
            // `getPropertyValue` returns an empty string, the value returned
            // by `.css()` would be `undefined`. This is usually the case for
            // disconnected elements. However, in IE even disconnected elements
            // with no styles return `"none"` for `getPropertyValue( "float" )`
            ret = computed.getPropertyValue(name) || computed[name];
            if (isCustomProp && ret) // Support: Firefox 105+, Chrome <=105+
            // Spec requires trimming whitespace for custom properties (gh-4926).
            // Firefox only trims leading whitespace. Chrome just collapses
            // both leading & trailing whitespace to a single space.
            //
            // Fall back to `undefined` if empty string returned.
            // This collapses a missing definition with property defined
            // and set to an empty string but there's no standard API
            // allowing us to differentiate them without a performance penalty
            // and returning `undefined` aligns with older jQuery.
            //
            // rtrimCSS treats U+000D CARRIAGE RETURN and U+000C FORM FEED
            // as whitespace while CSS does not, but this is not a problem
            // because CSS preprocessing replaces them with U+000A LINE FEED
            // (which *is* CSS whitespace)
            // https://www.w3.org/TR/css-syntax-3/#input-preprocessing
            ret = ret.replace(rtrimCSS, "$1") || undefined;
            if (ret === "" && !isAttached(elem)) ret = jQuery.style(elem, name);
            // A tribute to the "awesome hack by Dean Edwards"
            // Android Browser returns percentage for some values,
            // but width seems to be reliably pixels.
            // This is against the CSSOM draft spec:
            // https://drafts.csswg.org/cssom/#resolved-values
            if (!support.pixelBoxStyles() && rnumnonpx.test(ret) && rboxStyle.test(name)) {
                // Remember the original values
                width = style.width;
                minWidth = style.minWidth;
                maxWidth = style.maxWidth;
                // Put in the new values to get a computed value out
                style.minWidth = style.maxWidth = style.width = ret;
                ret = computed.width;
                // Revert the changed values
                style.width = width;
                style.minWidth = minWidth;
                style.maxWidth = maxWidth;
            }
        }
        return ret !== undefined ? // Support: IE <=9 - 11 only
        // IE returns zIndex value as an integer.
        ret + "" : ret;
    }
    function addGetHookIf(conditionFn, hookFn) {
        // Define the hook, we'll check on the first run if it's really needed.
        return {
            get: function() {
                if (conditionFn()) {
                    // Hook not needed (or it's not possible to use it due
                    // to missing dependency), remove it.
                    delete this.get;
                    return;
                }
                // Hook needed; redefine it so that the support test is not executed again.
                return (this.get = hookFn).apply(this, arguments);
            }
        };
    }
    var cssPrefixes = [
        "Webkit",
        "Moz",
        "ms"
    ], emptyStyle = document.createElement("div").style, vendorProps = {};
    // Return a vendor-prefixed property or undefined
    function vendorPropName(name) {
        // Check for vendor prefixed names
        var capName = name[0].toUpperCase() + name.slice(1), i = cssPrefixes.length;
        while(i--){
            name = cssPrefixes[i] + capName;
            if (name in emptyStyle) return name;
        }
    }
    // Return a potentially-mapped jQuery.cssProps or vendor prefixed property
    function finalPropName(name) {
        var final = jQuery.cssProps[name] || vendorProps[name];
        if (final) return final;
        if (name in emptyStyle) return name;
        return vendorProps[name] = vendorPropName(name) || name;
    }
    var // Swappable if display is none or starts with table
    // except "table", "table-cell", or "table-caption"
    // See here for display values: https://developer.mozilla.org/en-US/docs/CSS/display
    rdisplayswap = /^(none|table(?!-c[ea]).+)/, cssShow = {
        position: "absolute",
        visibility: "hidden",
        display: "block"
    }, cssNormalTransform = {
        letterSpacing: "0",
        fontWeight: "400"
    };
    function setPositiveNumber(_elem, value, subtract) {
        // Any relative (+/-) values have already been
        // normalized at this point
        var matches = rcssNum.exec(value);
        return matches ? // Guard against undefined "subtract", e.g., when used as in cssHooks
        Math.max(0, matches[2] - (subtract || 0)) + (matches[3] || "px") : value;
    }
    function boxModelAdjustment(elem, dimension, box, isBorderBox, styles, computedVal) {
        var i = dimension === "width" ? 1 : 0, extra = 0, delta = 0, marginDelta = 0;
        // Adjustment may not be necessary
        if (box === (isBorderBox ? "border" : "content")) return 0;
        for(; i < 4; i += 2){
            // Both box models exclude margin
            // Count margin delta separately to only add it after scroll gutter adjustment.
            // This is needed to make negative margins work with `outerHeight( true )` (gh-3982).
            if (box === "margin") marginDelta += jQuery.css(elem, box + cssExpand[i], true, styles);
            // If we get here with a content-box, we're seeking "padding" or "border" or "margin"
            if (!isBorderBox) {
                // Add padding
                delta += jQuery.css(elem, "padding" + cssExpand[i], true, styles);
                // For "border" or "margin", add border
                if (box !== "padding") delta += jQuery.css(elem, "border" + cssExpand[i] + "Width", true, styles);
                else extra += jQuery.css(elem, "border" + cssExpand[i] + "Width", true, styles);
            // If we get here with a border-box (content + padding + border), we're seeking "content" or
            // "padding" or "margin"
            } else {
                // For "content", subtract padding
                if (box === "content") delta -= jQuery.css(elem, "padding" + cssExpand[i], true, styles);
                // For "content" or "padding", subtract border
                if (box !== "margin") delta -= jQuery.css(elem, "border" + cssExpand[i] + "Width", true, styles);
            }
        }
        // Account for positive content-box scroll gutter when requested by providing computedVal
        if (!isBorderBox && computedVal >= 0) // offsetWidth/offsetHeight is a rounded sum of content, padding, scroll gutter, and border
        // Assuming integer scroll gutter, subtract the rest and round down
        delta += Math.max(0, Math.ceil(elem["offset" + dimension[0].toUpperCase() + dimension.slice(1)] - computedVal - delta - extra - 0.5)) || 0;
        return delta + marginDelta;
    }
    function getWidthOrHeight(elem, dimension, extra) {
        // Start with computed style
        var styles = getStyles(elem), // To avoid forcing a reflow, only fetch boxSizing if we need it (gh-4322).
        // Fake content-box until we know it's needed to know the true value.
        boxSizingNeeded = !support.boxSizingReliable() || extra, isBorderBox = boxSizingNeeded && jQuery.css(elem, "boxSizing", false, styles) === "border-box", valueIsBorderBox = isBorderBox, val = curCSS(elem, dimension, styles), offsetProp = "offset" + dimension[0].toUpperCase() + dimension.slice(1);
        // Support: Firefox <=54
        // Return a confounding non-pixel value or feign ignorance, as appropriate.
        if (rnumnonpx.test(val)) {
            if (!extra) return val;
            val = "auto";
        }
        // Support: IE 9 - 11 only
        // Use offsetWidth/offsetHeight for when box sizing is unreliable.
        // In those cases, the computed value can be trusted to be border-box.
        if ((!support.boxSizingReliable() && isBorderBox || // Support: IE 10 - 11+, Edge 15 - 18+
        // IE/Edge misreport `getComputedStyle` of table rows with width/height
        // set in CSS while `offset*` properties report correct values.
        // Interestingly, in some cases IE 9 doesn't suffer from this issue.
        !support.reliableTrDimensions() && nodeName(elem, "tr") || // Fall back to offsetWidth/offsetHeight when value is "auto"
        // This happens for inline elements with no explicit setting (gh-3571)
        val === "auto" || // Support: Android <=4.1 - 4.3 only
        // Also use offsetWidth/offsetHeight for misreported inline dimensions (gh-3602)
        !parseFloat(val) && jQuery.css(elem, "display", false, styles) === "inline") && // Make sure the element is visible & connected
        elem.getClientRects().length) {
            isBorderBox = jQuery.css(elem, "boxSizing", false, styles) === "border-box";
            // Where available, offsetWidth/offsetHeight approximate border box dimensions.
            // Where not available (e.g., SVG), assume unreliable box-sizing and interpret the
            // retrieved value as a content box dimension.
            valueIsBorderBox = offsetProp in elem;
            if (valueIsBorderBox) val = elem[offsetProp];
        }
        // Normalize "" and auto
        val = parseFloat(val) || 0;
        // Adjust for the element's box model
        return val + boxModelAdjustment(elem, dimension, extra || (isBorderBox ? "border" : "content"), valueIsBorderBox, styles, // Provide the current computed size to request scroll gutter calculation (gh-3589)
        val) + "px";
    }
    jQuery.extend({
        // Add in style property hooks for overriding the default
        // behavior of getting and setting a style property
        cssHooks: {
            opacity: {
                get: function(elem, computed) {
                    if (computed) {
                        // We should always get a number back from opacity
                        var ret = curCSS(elem, "opacity");
                        return ret === "" ? "1" : ret;
                    }
                }
            }
        },
        // Don't automatically add "px" to these possibly-unitless properties
        cssNumber: {
            animationIterationCount: true,
            aspectRatio: true,
            borderImageSlice: true,
            columnCount: true,
            flexGrow: true,
            flexShrink: true,
            fontWeight: true,
            gridArea: true,
            gridColumn: true,
            gridColumnEnd: true,
            gridColumnStart: true,
            gridRow: true,
            gridRowEnd: true,
            gridRowStart: true,
            lineHeight: true,
            opacity: true,
            order: true,
            orphans: true,
            scale: true,
            widows: true,
            zIndex: true,
            zoom: true,
            // SVG-related
            fillOpacity: true,
            floodOpacity: true,
            stopOpacity: true,
            strokeMiterlimit: true,
            strokeOpacity: true
        },
        // Add in properties whose names you wish to fix before
        // setting or getting the value
        cssProps: {},
        // Get and set the style property on a DOM Node
        style: function(elem, name, value, extra) {
            // Don't set styles on text and comment nodes
            if (!elem || elem.nodeType === 3 || elem.nodeType === 8 || !elem.style) return;
            // Make sure that we're working with the right name
            var ret, type, hooks, origName = camelCase(name), isCustomProp = rcustomProp.test(name), style = elem.style;
            // Make sure that we're working with the right name. We don't
            // want to query the value if it is a CSS custom property
            // since they are user-defined.
            if (!isCustomProp) name = finalPropName(origName);
            // Gets hook for the prefixed version, then unprefixed version
            hooks = jQuery.cssHooks[name] || jQuery.cssHooks[origName];
            // Check if we're setting a value
            if (value !== undefined) {
                type = typeof value;
                // Convert "+=" or "-=" to relative numbers (trac-7345)
                if (type === "string" && (ret = rcssNum.exec(value)) && ret[1]) {
                    value = adjustCSS(elem, name, ret);
                    // Fixes bug trac-9237
                    type = "number";
                }
                // Make sure that null and NaN values aren't set (trac-7116)
                if (value == null || value !== value) return;
                // If a number was passed in, add the unit (except for certain CSS properties)
                // The isCustomProp check can be removed in jQuery 4.0 when we only auto-append
                // "px" to a few hardcoded values.
                if (type === "number" && !isCustomProp) value += ret && ret[3] || (jQuery.cssNumber[origName] ? "" : "px");
                // background-* props affect original clone's values
                if (!support.clearCloneStyle && value === "" && name.indexOf("background") === 0) style[name] = "inherit";
                // If a hook was provided, use that value, otherwise just set the specified value
                if (!hooks || !("set" in hooks) || (value = hooks.set(elem, value, extra)) !== undefined) {
                    if (isCustomProp) style.setProperty(name, value);
                    else style[name] = value;
                }
            } else {
                // If a hook was provided get the non-computed value from there
                if (hooks && "get" in hooks && (ret = hooks.get(elem, false, extra)) !== undefined) return ret;
                // Otherwise just get the value from the style object
                return style[name];
            }
        },
        css: function(elem, name, extra, styles) {
            var val, num, hooks, origName = camelCase(name), isCustomProp = rcustomProp.test(name);
            // Make sure that we're working with the right name. We don't
            // want to modify the value if it is a CSS custom property
            // since they are user-defined.
            if (!isCustomProp) name = finalPropName(origName);
            // Try prefixed name followed by the unprefixed name
            hooks = jQuery.cssHooks[name] || jQuery.cssHooks[origName];
            // If a hook was provided get the computed value from there
            if (hooks && "get" in hooks) val = hooks.get(elem, true, extra);
            // Otherwise, if a way to get the computed value exists, use that
            if (val === undefined) val = curCSS(elem, name, styles);
            // Convert "normal" to computed value
            if (val === "normal" && name in cssNormalTransform) val = cssNormalTransform[name];
            // Make numeric if forced or a qualifier was provided and val looks numeric
            if (extra === "" || extra) {
                num = parseFloat(val);
                return extra === true || isFinite(num) ? num || 0 : val;
            }
            return val;
        }
    });
    jQuery.each([
        "height",
        "width"
    ], function(_i, dimension) {
        jQuery.cssHooks[dimension] = {
            get: function(elem, computed, extra) {
                if (computed) // Certain elements can have dimension info if we invisibly show them
                // but it must have a current display style that would benefit
                return rdisplayswap.test(jQuery.css(elem, "display")) && // Support: Safari 8+
                // Table columns in Safari have non-zero offsetWidth & zero
                // getBoundingClientRect().width unless display is changed.
                // Support: IE <=11 only
                // Running getBoundingClientRect on a disconnected node
                // in IE throws an error.
                (!elem.getClientRects().length || !elem.getBoundingClientRect().width) ? swap(elem, cssShow, function() {
                    return getWidthOrHeight(elem, dimension, extra);
                }) : getWidthOrHeight(elem, dimension, extra);
            },
            set: function(elem, value, extra) {
                var matches, styles = getStyles(elem), // Only read styles.position if the test has a chance to fail
                // to avoid forcing a reflow.
                scrollboxSizeBuggy = !support.scrollboxSize() && styles.position === "absolute", // To avoid forcing a reflow, only fetch boxSizing if we need it (gh-3991)
                boxSizingNeeded = scrollboxSizeBuggy || extra, isBorderBox = boxSizingNeeded && jQuery.css(elem, "boxSizing", false, styles) === "border-box", subtract = extra ? boxModelAdjustment(elem, dimension, extra, isBorderBox, styles) : 0;
                // Account for unreliable border-box dimensions by comparing offset* to computed and
                // faking a content-box to get border and padding (gh-3699)
                if (isBorderBox && scrollboxSizeBuggy) subtract -= Math.ceil(elem["offset" + dimension[0].toUpperCase() + dimension.slice(1)] - parseFloat(styles[dimension]) - boxModelAdjustment(elem, dimension, "border", false, styles) - 0.5);
                // Convert to pixels if value adjustment is needed
                if (subtract && (matches = rcssNum.exec(value)) && (matches[3] || "px") !== "px") {
                    elem.style[dimension] = value;
                    value = jQuery.css(elem, dimension);
                }
                return setPositiveNumber(elem, value, subtract);
            }
        };
    });
    jQuery.cssHooks.marginLeft = addGetHookIf(support.reliableMarginLeft, function(elem, computed) {
        if (computed) return (parseFloat(curCSS(elem, "marginLeft")) || elem.getBoundingClientRect().left - swap(elem, {
            marginLeft: 0
        }, function() {
            return elem.getBoundingClientRect().left;
        })) + "px";
    });
    // These hooks are used by animate to expand properties
    jQuery.each({
        margin: "",
        padding: "",
        border: "Width"
    }, function(prefix, suffix) {
        jQuery.cssHooks[prefix + suffix] = {
            expand: function(value) {
                var i = 0, expanded = {}, // Assumes a single number if not a string
                parts = typeof value === "string" ? value.split(" ") : [
                    value
                ];
                for(; i < 4; i++)expanded[prefix + cssExpand[i] + suffix] = parts[i] || parts[i - 2] || parts[0];
                return expanded;
            }
        };
        if (prefix !== "margin") jQuery.cssHooks[prefix + suffix].set = setPositiveNumber;
    });
    jQuery.fn.extend({
        css: function(name, value) {
            return access(this, function(elem, name, value) {
                var styles, len, map = {}, i = 0;
                if (Array.isArray(name)) {
                    styles = getStyles(elem);
                    len = name.length;
                    for(; i < len; i++)map[name[i]] = jQuery.css(elem, name[i], false, styles);
                    return map;
                }
                return value !== undefined ? jQuery.style(elem, name, value) : jQuery.css(elem, name);
            }, name, value, arguments.length > 1);
        }
    });
    function Tween(elem, options, prop, end, easing) {
        return new Tween.prototype.init(elem, options, prop, end, easing);
    }
    jQuery.Tween = Tween;
    Tween.prototype = {
        constructor: Tween,
        init: function(elem, options, prop, end, easing, unit) {
            this.elem = elem;
            this.prop = prop;
            this.easing = easing || jQuery.easing._default;
            this.options = options;
            this.start = this.now = this.cur();
            this.end = end;
            this.unit = unit || (jQuery.cssNumber[prop] ? "" : "px");
        },
        cur: function() {
            var hooks = Tween.propHooks[this.prop];
            return hooks && hooks.get ? hooks.get(this) : Tween.propHooks._default.get(this);
        },
        run: function(percent) {
            var eased, hooks = Tween.propHooks[this.prop];
            if (this.options.duration) this.pos = eased = jQuery.easing[this.easing](percent, this.options.duration * percent, 0, 1, this.options.duration);
            else this.pos = eased = percent;
            this.now = (this.end - this.start) * eased + this.start;
            if (this.options.step) this.options.step.call(this.elem, this.now, this);
            if (hooks && hooks.set) hooks.set(this);
            else Tween.propHooks._default.set(this);
            return this;
        }
    };
    Tween.prototype.init.prototype = Tween.prototype;
    Tween.propHooks = {
        _default: {
            get: function(tween) {
                var result;
                // Use a property on the element directly when it is not a DOM element,
                // or when there is no matching style property that exists.
                if (tween.elem.nodeType !== 1 || tween.elem[tween.prop] != null && tween.elem.style[tween.prop] == null) return tween.elem[tween.prop];
                // Passing an empty string as a 3rd parameter to .css will automatically
                // attempt a parseFloat and fallback to a string if the parse fails.
                // Simple values such as "10px" are parsed to Float;
                // complex values such as "rotate(1rad)" are returned as-is.
                result = jQuery.css(tween.elem, tween.prop, "");
                // Empty strings, null, undefined and "auto" are converted to 0.
                return !result || result === "auto" ? 0 : result;
            },
            set: function(tween) {
                // Use step hook for back compat.
                // Use cssHook if its there.
                // Use .style if available and use plain properties where available.
                if (jQuery.fx.step[tween.prop]) jQuery.fx.step[tween.prop](tween);
                else if (tween.elem.nodeType === 1 && (jQuery.cssHooks[tween.prop] || tween.elem.style[finalPropName(tween.prop)] != null)) jQuery.style(tween.elem, tween.prop, tween.now + tween.unit);
                else tween.elem[tween.prop] = tween.now;
            }
        }
    };
    // Support: IE <=9 only
    // Panic based approach to setting things on disconnected nodes
    Tween.propHooks.scrollTop = Tween.propHooks.scrollLeft = {
        set: function(tween) {
            if (tween.elem.nodeType && tween.elem.parentNode) tween.elem[tween.prop] = tween.now;
        }
    };
    jQuery.easing = {
        linear: function(p) {
            return p;
        },
        swing: function(p) {
            return 0.5 - Math.cos(p * Math.PI) / 2;
        },
        _default: "swing"
    };
    jQuery.fx = Tween.prototype.init;
    // Back compat <1.8 extension point
    jQuery.fx.step = {};
    var fxNow, inProgress, rfxtypes = /^(?:toggle|show|hide)$/, rrun = /queueHooks$/;
    function schedule() {
        if (inProgress) {
            if (document.hidden === false && window1.requestAnimationFrame) window1.requestAnimationFrame(schedule);
            else window1.setTimeout(schedule, jQuery.fx.interval);
            jQuery.fx.tick();
        }
    }
    // Animations created synchronously will run synchronously
    function createFxNow() {
        window1.setTimeout(function() {
            fxNow = undefined;
        });
        return fxNow = Date.now();
    }
    // Generate parameters to create a standard animation
    function genFx(type, includeWidth) {
        var which, i = 0, attrs = {
            height: type
        };
        // If we include width, step value is 1 to do all cssExpand values,
        // otherwise step value is 2 to skip over Left and Right
        includeWidth = includeWidth ? 1 : 0;
        for(; i < 4; i += 2 - includeWidth){
            which = cssExpand[i];
            attrs["margin" + which] = attrs["padding" + which] = type;
        }
        if (includeWidth) attrs.opacity = attrs.width = type;
        return attrs;
    }
    function createTween(value, prop, animation) {
        var tween, collection = (Animation.tweeners[prop] || []).concat(Animation.tweeners["*"]), index = 0, length = collection.length;
        for(; index < length; index++){
            if (tween = collection[index].call(animation, prop, value)) // We're done with this property
            return tween;
        }
    }
    function defaultPrefilter(elem, props, opts) {
        var prop, value, toggle, hooks, oldfire, propTween, restoreDisplay, display, isBox = "width" in props || "height" in props, anim = this, orig = {}, style = elem.style, hidden = elem.nodeType && isHiddenWithinTree(elem), dataShow = dataPriv.get(elem, "fxshow");
        // Queue-skipping animations hijack the fx hooks
        if (!opts.queue) {
            hooks = jQuery._queueHooks(elem, "fx");
            if (hooks.unqueued == null) {
                hooks.unqueued = 0;
                oldfire = hooks.empty.fire;
                hooks.empty.fire = function() {
                    if (!hooks.unqueued) oldfire();
                };
            }
            hooks.unqueued++;
            anim.always(function() {
                // Ensure the complete handler is called before this completes
                anim.always(function() {
                    hooks.unqueued--;
                    if (!jQuery.queue(elem, "fx").length) hooks.empty.fire();
                });
            });
        }
        // Detect show/hide animations
        for(prop in props){
            value = props[prop];
            if (rfxtypes.test(value)) {
                delete props[prop];
                toggle = toggle || value === "toggle";
                if (value === (hidden ? "hide" : "show")) {
                    // Pretend to be hidden if this is a "show" and
                    // there is still data from a stopped show/hide
                    if (value === "show" && dataShow && dataShow[prop] !== undefined) hidden = true;
                    else continue;
                }
                orig[prop] = dataShow && dataShow[prop] || jQuery.style(elem, prop);
            }
        }
        // Bail out if this is a no-op like .hide().hide()
        propTween = !jQuery.isEmptyObject(props);
        if (!propTween && jQuery.isEmptyObject(orig)) return;
        // Restrict "overflow" and "display" styles during box animations
        if (isBox && elem.nodeType === 1) {
            // Support: IE <=9 - 11, Edge 12 - 15
            // Record all 3 overflow attributes because IE does not infer the shorthand
            // from identically-valued overflowX and overflowY and Edge just mirrors
            // the overflowX value there.
            opts.overflow = [
                style.overflow,
                style.overflowX,
                style.overflowY
            ];
            // Identify a display type, preferring old show/hide data over the CSS cascade
            restoreDisplay = dataShow && dataShow.display;
            if (restoreDisplay == null) restoreDisplay = dataPriv.get(elem, "display");
            display = jQuery.css(elem, "display");
            if (display === "none") {
                if (restoreDisplay) display = restoreDisplay;
                else {
                    // Get nonempty value(s) by temporarily forcing visibility
                    showHide([
                        elem
                    ], true);
                    restoreDisplay = elem.style.display || restoreDisplay;
                    display = jQuery.css(elem, "display");
                    showHide([
                        elem
                    ]);
                }
            }
            // Animate inline elements as inline-block
            if (display === "inline" || display === "inline-block" && restoreDisplay != null) {
                if (jQuery.css(elem, "float") === "none") {
                    // Restore the original display value at the end of pure show/hide animations
                    if (!propTween) {
                        anim.done(function() {
                            style.display = restoreDisplay;
                        });
                        if (restoreDisplay == null) {
                            display = style.display;
                            restoreDisplay = display === "none" ? "" : display;
                        }
                    }
                    style.display = "inline-block";
                }
            }
        }
        if (opts.overflow) {
            style.overflow = "hidden";
            anim.always(function() {
                style.overflow = opts.overflow[0];
                style.overflowX = opts.overflow[1];
                style.overflowY = opts.overflow[2];
            });
        }
        // Implement show/hide animations
        propTween = false;
        for(prop in orig){
            // General show/hide setup for this element animation
            if (!propTween) {
                if (dataShow) {
                    if ("hidden" in dataShow) hidden = dataShow.hidden;
                } else dataShow = dataPriv.access(elem, "fxshow", {
                    display: restoreDisplay
                });
                // Store hidden/visible for toggle so `.stop().toggle()` "reverses"
                if (toggle) dataShow.hidden = !hidden;
                // Show elements before animating them
                if (hidden) showHide([
                    elem
                ], true);
                /* eslint-disable no-loop-func */ anim.done(function() {
                    /* eslint-enable no-loop-func */ // The final step of a "hide" animation is actually hiding the element
                    if (!hidden) showHide([
                        elem
                    ]);
                    dataPriv.remove(elem, "fxshow");
                    for(prop in orig)jQuery.style(elem, prop, orig[prop]);
                });
            }
            // Per-property setup
            propTween = createTween(hidden ? dataShow[prop] : 0, prop, anim);
            if (!(prop in dataShow)) {
                dataShow[prop] = propTween.start;
                if (hidden) {
                    propTween.end = propTween.start;
                    propTween.start = 0;
                }
            }
        }
    }
    function propFilter(props, specialEasing) {
        var index, name, easing, value, hooks;
        // camelCase, specialEasing and expand cssHook pass
        for(index in props){
            name = camelCase(index);
            easing = specialEasing[name];
            value = props[index];
            if (Array.isArray(value)) {
                easing = value[1];
                value = props[index] = value[0];
            }
            if (index !== name) {
                props[name] = value;
                delete props[index];
            }
            hooks = jQuery.cssHooks[name];
            if (hooks && "expand" in hooks) {
                value = hooks.expand(value);
                delete props[name];
                // Not quite $.extend, this won't overwrite existing keys.
                // Reusing 'index' because we have the correct "name"
                for(index in value)if (!(index in props)) {
                    props[index] = value[index];
                    specialEasing[index] = easing;
                }
            } else specialEasing[name] = easing;
        }
    }
    function Animation(elem, properties, options) {
        var result, stopped, index = 0, length = Animation.prefilters.length, deferred = jQuery.Deferred().always(function() {
            // Don't match elem in the :animated selector
            delete tick.elem;
        }), tick = function() {
            if (stopped) return false;
            var currentTime = fxNow || createFxNow(), remaining = Math.max(0, animation.startTime + animation.duration - currentTime), // Support: Android 2.3 only
            // Archaic crash bug won't allow us to use `1 - ( 0.5 || 0 )` (trac-12497)
            temp = remaining / animation.duration || 0, percent = 1 - temp, index = 0, length = animation.tweens.length;
            for(; index < length; index++)animation.tweens[index].run(percent);
            deferred.notifyWith(elem, [
                animation,
                percent,
                remaining
            ]);
            // If there's more to do, yield
            if (percent < 1 && length) return remaining;
            // If this was an empty animation, synthesize a final progress notification
            if (!length) deferred.notifyWith(elem, [
                animation,
                1,
                0
            ]);
            // Resolve the animation and report its conclusion
            deferred.resolveWith(elem, [
                animation
            ]);
            return false;
        }, animation = deferred.promise({
            elem: elem,
            props: jQuery.extend({}, properties),
            opts: jQuery.extend(true, {
                specialEasing: {},
                easing: jQuery.easing._default
            }, options),
            originalProperties: properties,
            originalOptions: options,
            startTime: fxNow || createFxNow(),
            duration: options.duration,
            tweens: [],
            createTween: function(prop, end) {
                var tween = jQuery.Tween(elem, animation.opts, prop, end, animation.opts.specialEasing[prop] || animation.opts.easing);
                animation.tweens.push(tween);
                return tween;
            },
            stop: function(gotoEnd) {
                var index = 0, // If we are going to the end, we want to run all the tweens
                // otherwise we skip this part
                length = gotoEnd ? animation.tweens.length : 0;
                if (stopped) return this;
                stopped = true;
                for(; index < length; index++)animation.tweens[index].run(1);
                // Resolve when we played the last frame; otherwise, reject
                if (gotoEnd) {
                    deferred.notifyWith(elem, [
                        animation,
                        1,
                        0
                    ]);
                    deferred.resolveWith(elem, [
                        animation,
                        gotoEnd
                    ]);
                } else deferred.rejectWith(elem, [
                    animation,
                    gotoEnd
                ]);
                return this;
            }
        }), props = animation.props;
        propFilter(props, animation.opts.specialEasing);
        for(; index < length; index++){
            result = Animation.prefilters[index].call(animation, elem, props, animation.opts);
            if (result) {
                if (isFunction(result.stop)) jQuery._queueHooks(animation.elem, animation.opts.queue).stop = result.stop.bind(result);
                return result;
            }
        }
        jQuery.map(props, createTween, animation);
        if (isFunction(animation.opts.start)) animation.opts.start.call(elem, animation);
        // Attach callbacks from options
        animation.progress(animation.opts.progress).done(animation.opts.done, animation.opts.complete).fail(animation.opts.fail).always(animation.opts.always);
        jQuery.fx.timer(jQuery.extend(tick, {
            elem: elem,
            anim: animation,
            queue: animation.opts.queue
        }));
        return animation;
    }
    jQuery.Animation = jQuery.extend(Animation, {
        tweeners: {
            "*": [
                function(prop, value) {
                    var tween = this.createTween(prop, value);
                    adjustCSS(tween.elem, prop, rcssNum.exec(value), tween);
                    return tween;
                }
            ]
        },
        tweener: function(props, callback) {
            if (isFunction(props)) {
                callback = props;
                props = [
                    "*"
                ];
            } else props = props.match(rnothtmlwhite);
            var prop, index = 0, length = props.length;
            for(; index < length; index++){
                prop = props[index];
                Animation.tweeners[prop] = Animation.tweeners[prop] || [];
                Animation.tweeners[prop].unshift(callback);
            }
        },
        prefilters: [
            defaultPrefilter
        ],
        prefilter: function(callback, prepend) {
            if (prepend) Animation.prefilters.unshift(callback);
            else Animation.prefilters.push(callback);
        }
    });
    jQuery.speed = function(speed, easing, fn) {
        var opt = speed && typeof speed === "object" ? jQuery.extend({}, speed) : {
            complete: fn || !fn && easing || isFunction(speed) && speed,
            duration: speed,
            easing: fn && easing || easing && !isFunction(easing) && easing
        };
        // Go to the end state if fx are off
        if (jQuery.fx.off) opt.duration = 0;
        else if (typeof opt.duration !== "number") {
            if (opt.duration in jQuery.fx.speeds) opt.duration = jQuery.fx.speeds[opt.duration];
            else opt.duration = jQuery.fx.speeds._default;
        }
        // Normalize opt.queue - true/undefined/null -> "fx"
        if (opt.queue == null || opt.queue === true) opt.queue = "fx";
        // Queueing
        opt.old = opt.complete;
        opt.complete = function() {
            if (isFunction(opt.old)) opt.old.call(this);
            if (opt.queue) jQuery.dequeue(this, opt.queue);
        };
        return opt;
    };
    jQuery.fn.extend({
        fadeTo: function(speed, to, easing, callback) {
            // Show any hidden elements after setting opacity to 0
            return this.filter(isHiddenWithinTree).css("opacity", 0).show()// Animate to the value specified
            .end().animate({
                opacity: to
            }, speed, easing, callback);
        },
        animate: function(prop, speed, easing, callback) {
            var empty = jQuery.isEmptyObject(prop), optall = jQuery.speed(speed, easing, callback), doAnimation = function() {
                // Operate on a copy of prop so per-property easing won't be lost
                var anim = Animation(this, jQuery.extend({}, prop), optall);
                // Empty animations, or finishing resolves immediately
                if (empty || dataPriv.get(this, "finish")) anim.stop(true);
            };
            doAnimation.finish = doAnimation;
            return empty || optall.queue === false ? this.each(doAnimation) : this.queue(optall.queue, doAnimation);
        },
        stop: function(type, clearQueue, gotoEnd) {
            var stopQueue = function(hooks) {
                var stop = hooks.stop;
                delete hooks.stop;
                stop(gotoEnd);
            };
            if (typeof type !== "string") {
                gotoEnd = clearQueue;
                clearQueue = type;
                type = undefined;
            }
            if (clearQueue) this.queue(type || "fx", []);
            return this.each(function() {
                var dequeue = true, index = type != null && type + "queueHooks", timers = jQuery.timers, data = dataPriv.get(this);
                if (index) {
                    if (data[index] && data[index].stop) stopQueue(data[index]);
                } else {
                    for(index in data)if (data[index] && data[index].stop && rrun.test(index)) stopQueue(data[index]);
                }
                for(index = timers.length; index--;)if (timers[index].elem === this && (type == null || timers[index].queue === type)) {
                    timers[index].anim.stop(gotoEnd);
                    dequeue = false;
                    timers.splice(index, 1);
                }
                // Start the next in the queue if the last step wasn't forced.
                // Timers currently will call their complete callbacks, which
                // will dequeue but only if they were gotoEnd.
                if (dequeue || !gotoEnd) jQuery.dequeue(this, type);
            });
        },
        finish: function(type) {
            if (type !== false) type = type || "fx";
            return this.each(function() {
                var index, data = dataPriv.get(this), queue = data[type + "queue"], hooks = data[type + "queueHooks"], timers = jQuery.timers, length = queue ? queue.length : 0;
                // Enable finishing flag on private data
                data.finish = true;
                // Empty the queue first
                jQuery.queue(this, type, []);
                if (hooks && hooks.stop) hooks.stop.call(this, true);
                // Look for any active animations, and finish them
                for(index = timers.length; index--;)if (timers[index].elem === this && timers[index].queue === type) {
                    timers[index].anim.stop(true);
                    timers.splice(index, 1);
                }
                // Look for any animations in the old queue and finish them
                for(index = 0; index < length; index++)if (queue[index] && queue[index].finish) queue[index].finish.call(this);
                // Turn off finishing flag
                delete data.finish;
            });
        }
    });
    jQuery.each([
        "toggle",
        "show",
        "hide"
    ], function(_i, name) {
        var cssFn = jQuery.fn[name];
        jQuery.fn[name] = function(speed, easing, callback) {
            return speed == null || typeof speed === "boolean" ? cssFn.apply(this, arguments) : this.animate(genFx(name, true), speed, easing, callback);
        };
    });
    // Generate shortcuts for custom animations
    jQuery.each({
        slideDown: genFx("show"),
        slideUp: genFx("hide"),
        slideToggle: genFx("toggle"),
        fadeIn: {
            opacity: "show"
        },
        fadeOut: {
            opacity: "hide"
        },
        fadeToggle: {
            opacity: "toggle"
        }
    }, function(name, props) {
        jQuery.fn[name] = function(speed, easing, callback) {
            return this.animate(props, speed, easing, callback);
        };
    });
    jQuery.timers = [];
    jQuery.fx.tick = function() {
        var timer, i = 0, timers = jQuery.timers;
        fxNow = Date.now();
        for(; i < timers.length; i++){
            timer = timers[i];
            // Run the timer and safely remove it when done (allowing for external removal)
            if (!timer() && timers[i] === timer) timers.splice(i--, 1);
        }
        if (!timers.length) jQuery.fx.stop();
        fxNow = undefined;
    };
    jQuery.fx.timer = function(timer) {
        jQuery.timers.push(timer);
        jQuery.fx.start();
    };
    jQuery.fx.interval = 13;
    jQuery.fx.start = function() {
        if (inProgress) return;
        inProgress = true;
        schedule();
    };
    jQuery.fx.stop = function() {
        inProgress = null;
    };
    jQuery.fx.speeds = {
        slow: 600,
        fast: 200,
        // Default speed
        _default: 400
    };
    // Based off of the plugin by Clint Helfers, with permission.
    jQuery.fn.delay = function(time, type) {
        time = jQuery.fx ? jQuery.fx.speeds[time] || time : time;
        type = type || "fx";
        return this.queue(type, function(next, hooks) {
            var timeout = window1.setTimeout(next, time);
            hooks.stop = function() {
                window1.clearTimeout(timeout);
            };
        });
    };
    (function() {
        var input = document.createElement("input"), select = document.createElement("select"), opt = select.appendChild(document.createElement("option"));
        input.type = "checkbox";
        // Support: Android <=4.3 only
        // Default value for a checkbox should be "on"
        support.checkOn = input.value !== "";
        // Support: IE <=11 only
        // Must access selectedIndex to make default options select
        support.optSelected = opt.selected;
        // Support: IE <=11 only
        // An input loses its value after becoming a radio
        input = document.createElement("input");
        input.value = "t";
        input.type = "radio";
        support.radioValue = input.value === "t";
    })();
    var boolHook, attrHandle = jQuery.expr.attrHandle;
    jQuery.fn.extend({
        attr: function(name, value) {
            return access(this, jQuery.attr, name, value, arguments.length > 1);
        },
        removeAttr: function(name) {
            return this.each(function() {
                jQuery.removeAttr(this, name);
            });
        }
    });
    jQuery.extend({
        attr: function(elem, name, value) {
            var ret, hooks, nType = elem.nodeType;
            // Don't get/set attributes on text, comment and attribute nodes
            if (nType === 3 || nType === 8 || nType === 2) return;
            // Fallback to prop when attributes are not supported
            if (typeof elem.getAttribute === "undefined") return jQuery.prop(elem, name, value);
            // Attribute hooks are determined by the lowercase version
            // Grab necessary hook if one is defined
            if (nType !== 1 || !jQuery.isXMLDoc(elem)) hooks = jQuery.attrHooks[name.toLowerCase()] || (jQuery.expr.match.bool.test(name) ? boolHook : undefined);
            if (value !== undefined) {
                if (value === null) {
                    jQuery.removeAttr(elem, name);
                    return;
                }
                if (hooks && "set" in hooks && (ret = hooks.set(elem, value, name)) !== undefined) return ret;
                elem.setAttribute(name, value + "");
                return value;
            }
            if (hooks && "get" in hooks && (ret = hooks.get(elem, name)) !== null) return ret;
            ret = jQuery.find.attr(elem, name);
            // Non-existent attributes return null, we normalize to undefined
            return ret == null ? undefined : ret;
        },
        attrHooks: {
            type: {
                set: function(elem, value) {
                    if (!support.radioValue && value === "radio" && nodeName(elem, "input")) {
                        var val = elem.value;
                        elem.setAttribute("type", value);
                        if (val) elem.value = val;
                        return value;
                    }
                }
            }
        },
        removeAttr: function(elem, value) {
            var name, i = 0, // Attribute names can contain non-HTML whitespace characters
            // https://html.spec.whatwg.org/multipage/syntax.html#attributes-2
            attrNames = value && value.match(rnothtmlwhite);
            if (attrNames && elem.nodeType === 1) while(name = attrNames[i++])elem.removeAttribute(name);
        }
    });
    // Hooks for boolean attributes
    boolHook = {
        set: function(elem, value, name) {
            if (value === false) // Remove boolean attributes when set to false
            jQuery.removeAttr(elem, name);
            else elem.setAttribute(name, name);
            return name;
        }
    };
    jQuery.each(jQuery.expr.match.bool.source.match(/\w+/g), function(_i, name) {
        var getter = attrHandle[name] || jQuery.find.attr;
        attrHandle[name] = function(elem, name, isXML) {
            var ret, handle, lowercaseName = name.toLowerCase();
            if (!isXML) {
                // Avoid an infinite loop by temporarily removing this function from the getter
                handle = attrHandle[lowercaseName];
                attrHandle[lowercaseName] = ret;
                ret = getter(elem, name, isXML) != null ? lowercaseName : null;
                attrHandle[lowercaseName] = handle;
            }
            return ret;
        };
    });
    var rfocusable = /^(?:input|select|textarea|button)$/i, rclickable = /^(?:a|area)$/i;
    jQuery.fn.extend({
        prop: function(name, value) {
            return access(this, jQuery.prop, name, value, arguments.length > 1);
        },
        removeProp: function(name) {
            return this.each(function() {
                delete this[jQuery.propFix[name] || name];
            });
        }
    });
    jQuery.extend({
        prop: function(elem, name, value) {
            var ret, hooks, nType = elem.nodeType;
            // Don't get/set properties on text, comment and attribute nodes
            if (nType === 3 || nType === 8 || nType === 2) return;
            if (nType !== 1 || !jQuery.isXMLDoc(elem)) {
                // Fix name and attach hooks
                name = jQuery.propFix[name] || name;
                hooks = jQuery.propHooks[name];
            }
            if (value !== undefined) {
                if (hooks && "set" in hooks && (ret = hooks.set(elem, value, name)) !== undefined) return ret;
                return elem[name] = value;
            }
            if (hooks && "get" in hooks && (ret = hooks.get(elem, name)) !== null) return ret;
            return elem[name];
        },
        propHooks: {
            tabIndex: {
                get: function(elem) {
                    // Support: IE <=9 - 11 only
                    // elem.tabIndex doesn't always return the
                    // correct value when it hasn't been explicitly set
                    // Use proper attribute retrieval (trac-12072)
                    var tabindex = jQuery.find.attr(elem, "tabindex");
                    if (tabindex) return parseInt(tabindex, 10);
                    if (rfocusable.test(elem.nodeName) || rclickable.test(elem.nodeName) && elem.href) return 0;
                    return -1;
                }
            }
        },
        propFix: {
            "for": "htmlFor",
            "class": "className"
        }
    });
    // Support: IE <=11 only
    // Accessing the selectedIndex property
    // forces the browser to respect setting selected
    // on the option
    // The getter ensures a default option is selected
    // when in an optgroup
    // eslint rule "no-unused-expressions" is disabled for this code
    // since it considers such accessions noop
    if (!support.optSelected) jQuery.propHooks.selected = {
        get: function(elem) {
            /* eslint no-unused-expressions: "off" */ var parent = elem.parentNode;
            if (parent && parent.parentNode) parent.parentNode.selectedIndex;
            return null;
        },
        set: function(elem) {
            /* eslint no-unused-expressions: "off" */ var parent = elem.parentNode;
            if (parent) {
                parent.selectedIndex;
                if (parent.parentNode) parent.parentNode.selectedIndex;
            }
        }
    };
    jQuery.each([
        "tabIndex",
        "readOnly",
        "maxLength",
        "cellSpacing",
        "cellPadding",
        "rowSpan",
        "colSpan",
        "useMap",
        "frameBorder",
        "contentEditable"
    ], function() {
        jQuery.propFix[this.toLowerCase()] = this;
    });
    // Strip and collapse whitespace according to HTML spec
    // https://infra.spec.whatwg.org/#strip-and-collapse-ascii-whitespace
    function stripAndCollapse(value) {
        var tokens = value.match(rnothtmlwhite) || [];
        return tokens.join(" ");
    }
    function getClass(elem) {
        return elem.getAttribute && elem.getAttribute("class") || "";
    }
    function classesToArray(value) {
        if (Array.isArray(value)) return value;
        if (typeof value === "string") return value.match(rnothtmlwhite) || [];
        return [];
    }
    jQuery.fn.extend({
        addClass: function(value) {
            var classNames, cur, curValue, className, i, finalValue;
            if (isFunction(value)) return this.each(function(j) {
                jQuery(this).addClass(value.call(this, j, getClass(this)));
            });
            classNames = classesToArray(value);
            if (classNames.length) return this.each(function() {
                curValue = getClass(this);
                cur = this.nodeType === 1 && " " + stripAndCollapse(curValue) + " ";
                if (cur) {
                    for(i = 0; i < classNames.length; i++){
                        className = classNames[i];
                        if (cur.indexOf(" " + className + " ") < 0) cur += className + " ";
                    }
                    // Only assign if different to avoid unneeded rendering.
                    finalValue = stripAndCollapse(cur);
                    if (curValue !== finalValue) this.setAttribute("class", finalValue);
                }
            });
            return this;
        },
        removeClass: function(value) {
            var classNames, cur, curValue, className, i, finalValue;
            if (isFunction(value)) return this.each(function(j) {
                jQuery(this).removeClass(value.call(this, j, getClass(this)));
            });
            if (!arguments.length) return this.attr("class", "");
            classNames = classesToArray(value);
            if (classNames.length) return this.each(function() {
                curValue = getClass(this);
                // This expression is here for better compressibility (see addClass)
                cur = this.nodeType === 1 && " " + stripAndCollapse(curValue) + " ";
                if (cur) {
                    for(i = 0; i < classNames.length; i++){
                        className = classNames[i];
                        // Remove *all* instances
                        while(cur.indexOf(" " + className + " ") > -1)cur = cur.replace(" " + className + " ", " ");
                    }
                    // Only assign if different to avoid unneeded rendering.
                    finalValue = stripAndCollapse(cur);
                    if (curValue !== finalValue) this.setAttribute("class", finalValue);
                }
            });
            return this;
        },
        toggleClass: function(value, stateVal) {
            var classNames, className, i, self, type = typeof value, isValidValue = type === "string" || Array.isArray(value);
            if (isFunction(value)) return this.each(function(i) {
                jQuery(this).toggleClass(value.call(this, i, getClass(this), stateVal), stateVal);
            });
            if (typeof stateVal === "boolean" && isValidValue) return stateVal ? this.addClass(value) : this.removeClass(value);
            classNames = classesToArray(value);
            return this.each(function() {
                if (isValidValue) {
                    // Toggle individual class names
                    self = jQuery(this);
                    for(i = 0; i < classNames.length; i++){
                        className = classNames[i];
                        // Check each className given, space separated list
                        if (self.hasClass(className)) self.removeClass(className);
                        else self.addClass(className);
                    }
                // Toggle whole class name
                } else if (value === undefined || type === "boolean") {
                    className = getClass(this);
                    if (className) // Store className if set
                    dataPriv.set(this, "__className__", className);
                    // If the element has a class name or if we're passed `false`,
                    // then remove the whole classname (if there was one, the above saved it).
                    // Otherwise bring back whatever was previously saved (if anything),
                    // falling back to the empty string if nothing was stored.
                    if (this.setAttribute) this.setAttribute("class", className || value === false ? "" : dataPriv.get(this, "__className__") || "");
                }
            });
        },
        hasClass: function(selector) {
            var className, elem, i = 0;
            className = " " + selector + " ";
            while(elem = this[i++]){
                if (elem.nodeType === 1 && (" " + stripAndCollapse(getClass(elem)) + " ").indexOf(className) > -1) return true;
            }
            return false;
        }
    });
    var rreturn = /\r/g;
    jQuery.fn.extend({
        val: function(value) {
            var hooks, ret, valueIsFunction, elem = this[0];
            if (!arguments.length) {
                if (elem) {
                    hooks = jQuery.valHooks[elem.type] || jQuery.valHooks[elem.nodeName.toLowerCase()];
                    if (hooks && "get" in hooks && (ret = hooks.get(elem, "value")) !== undefined) return ret;
                    ret = elem.value;
                    // Handle most common string cases
                    if (typeof ret === "string") return ret.replace(rreturn, "");
                    // Handle cases where value is null/undef or number
                    return ret == null ? "" : ret;
                }
                return;
            }
            valueIsFunction = isFunction(value);
            return this.each(function(i) {
                var val;
                if (this.nodeType !== 1) return;
                if (valueIsFunction) val = value.call(this, i, jQuery(this).val());
                else val = value;
                // Treat null/undefined as ""; convert numbers to string
                if (val == null) val = "";
                else if (typeof val === "number") val += "";
                else if (Array.isArray(val)) val = jQuery.map(val, function(value) {
                    return value == null ? "" : value + "";
                });
                hooks = jQuery.valHooks[this.type] || jQuery.valHooks[this.nodeName.toLowerCase()];
                // If set returns undefined, fall back to normal setting
                if (!hooks || !("set" in hooks) || hooks.set(this, val, "value") === undefined) this.value = val;
            });
        }
    });
    jQuery.extend({
        valHooks: {
            option: {
                get: function(elem) {
                    var val = jQuery.find.attr(elem, "value");
                    return val != null ? val : // Support: IE <=10 - 11 only
                    // option.text throws exceptions (trac-14686, trac-14858)
                    // Strip and collapse whitespace
                    // https://html.spec.whatwg.org/#strip-and-collapse-whitespace
                    stripAndCollapse(jQuery.text(elem));
                }
            },
            select: {
                get: function(elem) {
                    var value, option, i, options = elem.options, index = elem.selectedIndex, one = elem.type === "select-one", values = one ? null : [], max = one ? index + 1 : options.length;
                    if (index < 0) i = max;
                    else i = one ? index : 0;
                    // Loop through all the selected options
                    for(; i < max; i++){
                        option = options[i];
                        // Support: IE <=9 only
                        // IE8-9 doesn't update selected after form reset (trac-2551)
                        if ((option.selected || i === index) && // Don't return options that are disabled or in a disabled optgroup
                        !option.disabled && (!option.parentNode.disabled || !nodeName(option.parentNode, "optgroup"))) {
                            // Get the specific value for the option
                            value = jQuery(option).val();
                            // We don't need an array for one selects
                            if (one) return value;
                            // Multi-Selects return an array
                            values.push(value);
                        }
                    }
                    return values;
                },
                set: function(elem, value) {
                    var optionSet, option, options = elem.options, values = jQuery.makeArray(value), i = options.length;
                    while(i--){
                        option = options[i];
                        /* eslint-disable no-cond-assign */ if (option.selected = jQuery.inArray(jQuery.valHooks.option.get(option), values) > -1) optionSet = true;
                    /* eslint-enable no-cond-assign */ }
                    // Force browsers to behave consistently when non-matching value is set
                    if (!optionSet) elem.selectedIndex = -1;
                    return values;
                }
            }
        }
    });
    // Radios and checkboxes getter/setter
    jQuery.each([
        "radio",
        "checkbox"
    ], function() {
        jQuery.valHooks[this] = {
            set: function(elem, value) {
                if (Array.isArray(value)) return elem.checked = jQuery.inArray(jQuery(elem).val(), value) > -1;
            }
        };
        if (!support.checkOn) jQuery.valHooks[this].get = function(elem) {
            return elem.getAttribute("value") === null ? "on" : elem.value;
        };
    });
    // Return jQuery for attributes-only inclusion
    var location = window1.location;
    var nonce = {
        guid: Date.now()
    };
    var rquery = /\?/;
    // Cross-browser xml parsing
    jQuery.parseXML = function(data) {
        var xml, parserErrorElem;
        if (!data || typeof data !== "string") return null;
        // Support: IE 9 - 11 only
        // IE throws on parseFromString with invalid input.
        try {
            xml = new window1.DOMParser().parseFromString(data, "text/xml");
        } catch (e) {}
        parserErrorElem = xml && xml.getElementsByTagName("parsererror")[0];
        if (!xml || parserErrorElem) jQuery.error("Invalid XML: " + (parserErrorElem ? jQuery.map(parserErrorElem.childNodes, function(el) {
            return el.textContent;
        }).join("\n") : data));
        return xml;
    };
    var rfocusMorph = /^(?:focusinfocus|focusoutblur)$/, stopPropagationCallback = function(e) {
        e.stopPropagation();
    };
    jQuery.extend(jQuery.event, {
        trigger: function(event, data, elem, onlyHandlers) {
            var i, cur, tmp, bubbleType, ontype, handle, special, lastElement, eventPath = [
                elem || document
            ], type = hasOwn.call(event, "type") ? event.type : event, namespaces = hasOwn.call(event, "namespace") ? event.namespace.split(".") : [];
            cur = lastElement = tmp = elem = elem || document;
            // Don't do events on text and comment nodes
            if (elem.nodeType === 3 || elem.nodeType === 8) return;
            // focus/blur morphs to focusin/out; ensure we're not firing them right now
            if (rfocusMorph.test(type + jQuery.event.triggered)) return;
            if (type.indexOf(".") > -1) {
                // Namespaced trigger; create a regexp to match event type in handle()
                namespaces = type.split(".");
                type = namespaces.shift();
                namespaces.sort();
            }
            ontype = type.indexOf(":") < 0 && "on" + type;
            // Caller can pass in a jQuery.Event object, Object, or just an event type string
            event = event[jQuery.expando] ? event : new jQuery.Event(type, typeof event === "object" && event);
            // Trigger bitmask: & 1 for native handlers; & 2 for jQuery (always true)
            event.isTrigger = onlyHandlers ? 2 : 3;
            event.namespace = namespaces.join(".");
            event.rnamespace = event.namespace ? new RegExp("(^|\\.)" + namespaces.join("\\.(?:.*\\.|)") + "(\\.|$)") : null;
            // Clean up the event in case it is being reused
            event.result = undefined;
            if (!event.target) event.target = elem;
            // Clone any incoming data and prepend the event, creating the handler arg list
            data = data == null ? [
                event
            ] : jQuery.makeArray(data, [
                event
            ]);
            // Allow special events to draw outside the lines
            special = jQuery.event.special[type] || {};
            if (!onlyHandlers && special.trigger && special.trigger.apply(elem, data) === false) return;
            // Determine event propagation path in advance, per W3C events spec (trac-9951)
            // Bubble up to document, then to window; watch for a global ownerDocument var (trac-9724)
            if (!onlyHandlers && !special.noBubble && !isWindow(elem)) {
                bubbleType = special.delegateType || type;
                if (!rfocusMorph.test(bubbleType + type)) cur = cur.parentNode;
                for(; cur; cur = cur.parentNode){
                    eventPath.push(cur);
                    tmp = cur;
                }
                // Only add window if we got to document (e.g., not plain obj or detached DOM)
                if (tmp === (elem.ownerDocument || document)) eventPath.push(tmp.defaultView || tmp.parentWindow || window1);
            }
            // Fire handlers on the event path
            i = 0;
            while((cur = eventPath[i++]) && !event.isPropagationStopped()){
                lastElement = cur;
                event.type = i > 1 ? bubbleType : special.bindType || type;
                // jQuery handler
                handle = (dataPriv.get(cur, "events") || Object.create(null))[event.type] && dataPriv.get(cur, "handle");
                if (handle) handle.apply(cur, data);
                // Native handler
                handle = ontype && cur[ontype];
                if (handle && handle.apply && acceptData(cur)) {
                    event.result = handle.apply(cur, data);
                    if (event.result === false) event.preventDefault();
                }
            }
            event.type = type;
            // If nobody prevented the default action, do it now
            if (!onlyHandlers && !event.isDefaultPrevented()) {
                if ((!special._default || special._default.apply(eventPath.pop(), data) === false) && acceptData(elem)) // Call a native DOM method on the target with the same name as the event.
                // Don't do default actions on window, that's where global variables be (trac-6170)
                {
                    if (ontype && isFunction(elem[type]) && !isWindow(elem)) {
                        // Don't re-trigger an onFOO event when we call its FOO() method
                        tmp = elem[ontype];
                        if (tmp) elem[ontype] = null;
                        // Prevent re-triggering of the same event, since we already bubbled it above
                        jQuery.event.triggered = type;
                        if (event.isPropagationStopped()) lastElement.addEventListener(type, stopPropagationCallback);
                        elem[type]();
                        if (event.isPropagationStopped()) lastElement.removeEventListener(type, stopPropagationCallback);
                        jQuery.event.triggered = undefined;
                        if (tmp) elem[ontype] = tmp;
                    }
                }
            }
            return event.result;
        },
        // Piggyback on a donor event to simulate a different one
        // Used only for `focus(in | out)` events
        simulate: function(type, elem, event) {
            var e = jQuery.extend(new jQuery.Event(), event, {
                type: type,
                isSimulated: true
            });
            jQuery.event.trigger(e, null, elem);
        }
    });
    jQuery.fn.extend({
        trigger: function(type, data) {
            return this.each(function() {
                jQuery.event.trigger(type, data, this);
            });
        },
        triggerHandler: function(type, data) {
            var elem = this[0];
            if (elem) return jQuery.event.trigger(type, data, elem, true);
        }
    });
    var rbracket = /\[\]$/, rCRLF = /\r?\n/g, rsubmitterTypes = /^(?:submit|button|image|reset|file)$/i, rsubmittable = /^(?:input|select|textarea|keygen)/i;
    function buildParams(prefix, obj, traditional, add) {
        var name;
        if (Array.isArray(obj)) // Serialize array item.
        jQuery.each(obj, function(i, v) {
            if (traditional || rbracket.test(prefix)) // Treat each array item as a scalar.
            add(prefix, v);
            else // Item is non-scalar (array or object), encode its numeric index.
            buildParams(prefix + "[" + (typeof v === "object" && v != null ? i : "") + "]", v, traditional, add);
        });
        else if (!traditional && toType(obj) === "object") // Serialize object item.
        for(name in obj)buildParams(prefix + "[" + name + "]", obj[name], traditional, add);
        else // Serialize scalar item.
        add(prefix, obj);
    }
    // Serialize an array of form elements or a set of
    // key/values into a query string
    jQuery.param = function(a, traditional) {
        var prefix, s = [], add = function(key, valueOrFunction) {
            // If value is a function, invoke it and use its return value
            var value = isFunction(valueOrFunction) ? valueOrFunction() : valueOrFunction;
            s[s.length] = encodeURIComponent(key) + "=" + encodeURIComponent(value == null ? "" : value);
        };
        if (a == null) return "";
        // If an array was passed in, assume that it is an array of form elements.
        if (Array.isArray(a) || a.jquery && !jQuery.isPlainObject(a)) // Serialize the form elements
        jQuery.each(a, function() {
            add(this.name, this.value);
        });
        else // If traditional, encode the "old" way (the way 1.3.2 or older
        // did it), otherwise encode params recursively.
        for(prefix in a)buildParams(prefix, a[prefix], traditional, add);
        // Return the resulting serialization
        return s.join("&");
    };
    jQuery.fn.extend({
        serialize: function() {
            return jQuery.param(this.serializeArray());
        },
        serializeArray: function() {
            return this.map(function() {
                // Can add propHook for "elements" to filter or add form elements
                var elements = jQuery.prop(this, "elements");
                return elements ? jQuery.makeArray(elements) : this;
            }).filter(function() {
                var type = this.type;
                // Use .is( ":disabled" ) so that fieldset[disabled] works
                return this.name && !jQuery(this).is(":disabled") && rsubmittable.test(this.nodeName) && !rsubmitterTypes.test(type) && (this.checked || !rcheckableType.test(type));
            }).map(function(_i, elem) {
                var val = jQuery(this).val();
                if (val == null) return null;
                if (Array.isArray(val)) return jQuery.map(val, function(val) {
                    return {
                        name: elem.name,
                        value: val.replace(rCRLF, "\r\n")
                    };
                });
                return {
                    name: elem.name,
                    value: val.replace(rCRLF, "\r\n")
                };
            }).get();
        }
    });
    var r20 = /%20/g, rhash = /#.*$/, rantiCache = /([?&])_=[^&]*/, rheaders = /^(.*?):[ \t]*([^\r\n]*)$/mg, // trac-7653, trac-8125, trac-8152: local protocol detection
    rlocalProtocol = /^(?:about|app|app-storage|.+-extension|file|res|widget):$/, rnoContent = /^(?:GET|HEAD)$/, rprotocol = /^\/\//, /* Prefilters
	 * 1) They are useful to introduce custom dataTypes (see ajax/jsonp.js for an example)
	 * 2) These are called:
	 *    - BEFORE asking for a transport
	 *    - AFTER param serialization (s.data is a string if s.processData is true)
	 * 3) key is the dataType
	 * 4) the catchall symbol "*" can be used
	 * 5) execution will start with transport dataType and THEN continue down to "*" if needed
	 */ prefilters = {}, /* Transports bindings
	 * 1) key is the dataType
	 * 2) the catchall symbol "*" can be used
	 * 3) selection will start with transport dataType and THEN go to "*" if needed
	 */ transports = {}, // Avoid comment-prolog char sequence (trac-10098); must appease lint and evade compression
    allTypes = "*/".concat("*"), // Anchor tag for parsing the document origin
    originAnchor = document.createElement("a");
    originAnchor.href = location.href;
    // Base "constructor" for jQuery.ajaxPrefilter and jQuery.ajaxTransport
    function addToPrefiltersOrTransports(structure) {
        // dataTypeExpression is optional and defaults to "*"
        return function(dataTypeExpression, func) {
            if (typeof dataTypeExpression !== "string") {
                func = dataTypeExpression;
                dataTypeExpression = "*";
            }
            var dataType, i = 0, dataTypes = dataTypeExpression.toLowerCase().match(rnothtmlwhite) || [];
            if (isFunction(func)) {
                // For each dataType in the dataTypeExpression
                while(dataType = dataTypes[i++])// Prepend if requested
                if (dataType[0] === "+") {
                    dataType = dataType.slice(1) || "*";
                    (structure[dataType] = structure[dataType] || []).unshift(func);
                // Otherwise append
                } else (structure[dataType] = structure[dataType] || []).push(func);
            }
        };
    }
    // Base inspection function for prefilters and transports
    function inspectPrefiltersOrTransports(structure, options, originalOptions, jqXHR) {
        var inspected = {}, seekingTransport = structure === transports;
        function inspect(dataType) {
            var selected;
            inspected[dataType] = true;
            jQuery.each(structure[dataType] || [], function(_, prefilterOrFactory) {
                var dataTypeOrTransport = prefilterOrFactory(options, originalOptions, jqXHR);
                if (typeof dataTypeOrTransport === "string" && !seekingTransport && !inspected[dataTypeOrTransport]) {
                    options.dataTypes.unshift(dataTypeOrTransport);
                    inspect(dataTypeOrTransport);
                    return false;
                } else if (seekingTransport) return !(selected = dataTypeOrTransport);
            });
            return selected;
        }
        return inspect(options.dataTypes[0]) || !inspected["*"] && inspect("*");
    }
    // A special extend for ajax options
    // that takes "flat" options (not to be deep extended)
    // Fixes trac-9887
    function ajaxExtend(target, src) {
        var key, deep, flatOptions = jQuery.ajaxSettings.flatOptions || {};
        for(key in src)if (src[key] !== undefined) (flatOptions[key] ? target : deep || (deep = {}))[key] = src[key];
        if (deep) jQuery.extend(true, target, deep);
        return target;
    }
    /* Handles responses to an ajax request:
 * - finds the right dataType (mediates between content-type and expected dataType)
 * - returns the corresponding response
 */ function ajaxHandleResponses(s, jqXHR, responses) {
        var ct, type, finalDataType, firstDataType, contents = s.contents, dataTypes = s.dataTypes;
        // Remove auto dataType and get content-type in the process
        while(dataTypes[0] === "*"){
            dataTypes.shift();
            if (ct === undefined) ct = s.mimeType || jqXHR.getResponseHeader("Content-Type");
        }
        // Check if we're dealing with a known content-type
        if (ct) {
            for(type in contents)if (contents[type] && contents[type].test(ct)) {
                dataTypes.unshift(type);
                break;
            }
        }
        // Check to see if we have a response for the expected dataType
        if (dataTypes[0] in responses) finalDataType = dataTypes[0];
        else {
            // Try convertible dataTypes
            for(type in responses){
                if (!dataTypes[0] || s.converters[type + " " + dataTypes[0]]) {
                    finalDataType = type;
                    break;
                }
                if (!firstDataType) firstDataType = type;
            }
            // Or just use first one
            finalDataType = finalDataType || firstDataType;
        }
        // If we found a dataType
        // We add the dataType to the list if needed
        // and return the corresponding response
        if (finalDataType) {
            if (finalDataType !== dataTypes[0]) dataTypes.unshift(finalDataType);
            return responses[finalDataType];
        }
    }
    /* Chain conversions given the request and the original response
 * Also sets the responseXXX fields on the jqXHR instance
 */ function ajaxConvert(s, response, jqXHR, isSuccess) {
        var conv2, current, conv, tmp, prev, converters = {}, // Work with a copy of dataTypes in case we need to modify it for conversion
        dataTypes = s.dataTypes.slice();
        // Create converters map with lowercased keys
        if (dataTypes[1]) for(conv in s.converters)converters[conv.toLowerCase()] = s.converters[conv];
        current = dataTypes.shift();
        // Convert to each sequential dataType
        while(current){
            if (s.responseFields[current]) jqXHR[s.responseFields[current]] = response;
            // Apply the dataFilter if provided
            if (!prev && isSuccess && s.dataFilter) response = s.dataFilter(response, s.dataType);
            prev = current;
            current = dataTypes.shift();
            if (current) {
                // There's only work to do if current dataType is non-auto
                if (current === "*") current = prev;
                else if (prev !== "*" && prev !== current) {
                    // Seek a direct converter
                    conv = converters[prev + " " + current] || converters["* " + current];
                    // If none found, seek a pair
                    if (!conv) for(conv2 in converters){
                        // If conv2 outputs current
                        tmp = conv2.split(" ");
                        if (tmp[1] === current) {
                            // If prev can be converted to accepted input
                            conv = converters[prev + " " + tmp[0]] || converters["* " + tmp[0]];
                            if (conv) {
                                // Condense equivalence converters
                                if (conv === true) conv = converters[conv2];
                                else if (converters[conv2] !== true) {
                                    current = tmp[0];
                                    dataTypes.unshift(tmp[1]);
                                }
                                break;
                            }
                        }
                    }
                    // Apply converter (if not an equivalence)
                    if (conv !== true) {
                        // Unless errors are allowed to bubble, catch and return them
                        if (conv && s.throws) response = conv(response);
                        else try {
                            response = conv(response);
                        } catch (e) {
                            return {
                                state: "parsererror",
                                error: conv ? e : "No conversion from " + prev + " to " + current
                            };
                        }
                    }
                }
            }
        }
        return {
            state: "success",
            data: response
        };
    }
    jQuery.extend({
        // Counter for holding the number of active queries
        active: 0,
        // Last-Modified header cache for next request
        lastModified: {},
        etag: {},
        ajaxSettings: {
            url: location.href,
            type: "GET",
            isLocal: rlocalProtocol.test(location.protocol),
            global: true,
            processData: true,
            async: true,
            contentType: "application/x-www-form-urlencoded; charset=UTF-8",
            /*
		timeout: 0,
		data: null,
		dataType: null,
		username: null,
		password: null,
		cache: null,
		throws: false,
		traditional: false,
		headers: {},
		*/ accepts: {
                "*": allTypes,
                text: "text/plain",
                html: "text/html",
                xml: "application/xml, text/xml",
                json: "application/json, text/javascript"
            },
            contents: {
                xml: /\bxml\b/,
                html: /\bhtml/,
                json: /\bjson\b/
            },
            responseFields: {
                xml: "responseXML",
                text: "responseText",
                json: "responseJSON"
            },
            // Data converters
            // Keys separate source (or catchall "*") and destination types with a single space
            converters: {
                // Convert anything to text
                "* text": String,
                // Text to html (true = no transformation)
                "text html": true,
                // Evaluate text as a json expression
                "text json": JSON.parse,
                // Parse text as xml
                "text xml": jQuery.parseXML
            },
            // For options that shouldn't be deep extended:
            // you can add your own custom options here if
            // and when you create one that shouldn't be
            // deep extended (see ajaxExtend)
            flatOptions: {
                url: true,
                context: true
            }
        },
        // Creates a full fledged settings object into target
        // with both ajaxSettings and settings fields.
        // If target is omitted, writes into ajaxSettings.
        ajaxSetup: function(target, settings) {
            return settings ? // Building a settings object
            ajaxExtend(ajaxExtend(target, jQuery.ajaxSettings), settings) : // Extending ajaxSettings
            ajaxExtend(jQuery.ajaxSettings, target);
        },
        ajaxPrefilter: addToPrefiltersOrTransports(prefilters),
        ajaxTransport: addToPrefiltersOrTransports(transports),
        // Main method
        ajax: function(url, options) {
            // If url is an object, simulate pre-1.5 signature
            if (typeof url === "object") {
                options = url;
                url = undefined;
            }
            // Force options to be an object
            options = options || {};
            var transport, // URL without anti-cache param
            cacheURL, // Response headers
            responseHeadersString, responseHeaders, // timeout handle
            timeoutTimer, // Url cleanup var
            urlAnchor, // Request state (becomes false upon send and true upon completion)
            completed, // To know if global events are to be dispatched
            fireGlobals, // Loop variable
            i, // uncached part of the url
            uncached, // Create the final options object
            s = jQuery.ajaxSetup({}, options), // Callbacks context
            callbackContext = s.context || s, // Context for global events is callbackContext if it is a DOM node or jQuery collection
            globalEventContext = s.context && (callbackContext.nodeType || callbackContext.jquery) ? jQuery(callbackContext) : jQuery.event, // Deferreds
            deferred = jQuery.Deferred(), completeDeferred = jQuery.Callbacks("once memory"), // Status-dependent callbacks
            statusCode = s.statusCode || {}, // Headers (they are sent all at once)
            requestHeaders = {}, requestHeadersNames = {}, // Default abort message
            strAbort = "canceled", // Fake xhr
            jqXHR = {
                readyState: 0,
                // Builds headers hashtable if needed
                getResponseHeader: function(key) {
                    var match;
                    if (completed) {
                        if (!responseHeaders) {
                            responseHeaders = {};
                            while(match = rheaders.exec(responseHeadersString))responseHeaders[match[1].toLowerCase() + " "] = (responseHeaders[match[1].toLowerCase() + " "] || []).concat(match[2]);
                        }
                        match = responseHeaders[key.toLowerCase() + " "];
                    }
                    return match == null ? null : match.join(", ");
                },
                // Raw string
                getAllResponseHeaders: function() {
                    return completed ? responseHeadersString : null;
                },
                // Caches the header
                setRequestHeader: function(name, value) {
                    if (completed == null) {
                        name = requestHeadersNames[name.toLowerCase()] = requestHeadersNames[name.toLowerCase()] || name;
                        requestHeaders[name] = value;
                    }
                    return this;
                },
                // Overrides response content-type header
                overrideMimeType: function(type) {
                    if (completed == null) s.mimeType = type;
                    return this;
                },
                // Status-dependent callbacks
                statusCode: function(map) {
                    var code;
                    if (map) {
                        if (completed) // Execute the appropriate callbacks
                        jqXHR.always(map[jqXHR.status]);
                        else // Lazy-add the new callbacks in a way that preserves old ones
                        for(code in map)statusCode[code] = [
                            statusCode[code],
                            map[code]
                        ];
                    }
                    return this;
                },
                // Cancel the request
                abort: function(statusText) {
                    var finalText = statusText || strAbort;
                    if (transport) transport.abort(finalText);
                    done(0, finalText);
                    return this;
                }
            };
            // Attach deferreds
            deferred.promise(jqXHR);
            // Add protocol if not provided (prefilters might expect it)
            // Handle falsy url in the settings object (trac-10093: consistency with old signature)
            // We also use the url parameter if available
            s.url = ((url || s.url || location.href) + "").replace(rprotocol, location.protocol + "//");
            // Alias method option to type as per ticket trac-12004
            s.type = options.method || options.type || s.method || s.type;
            // Extract dataTypes list
            s.dataTypes = (s.dataType || "*").toLowerCase().match(rnothtmlwhite) || [
                ""
            ];
            // A cross-domain request is in order when the origin doesn't match the current origin.
            if (s.crossDomain == null) {
                urlAnchor = document.createElement("a");
                // Support: IE <=8 - 11, Edge 12 - 15
                // IE throws exception on accessing the href property if url is malformed,
                // e.g. http://example.com:80x/
                try {
                    urlAnchor.href = s.url;
                    // Support: IE <=8 - 11 only
                    // Anchor's host property isn't correctly set when s.url is relative
                    urlAnchor.href = urlAnchor.href;
                    s.crossDomain = originAnchor.protocol + "//" + originAnchor.host !== urlAnchor.protocol + "//" + urlAnchor.host;
                } catch (e) {
                    // If there is an error parsing the URL, assume it is crossDomain,
                    // it can be rejected by the transport if it is invalid
                    s.crossDomain = true;
                }
            }
            // Convert data if not already a string
            if (s.data && s.processData && typeof s.data !== "string") s.data = jQuery.param(s.data, s.traditional);
            // Apply prefilters
            inspectPrefiltersOrTransports(prefilters, s, options, jqXHR);
            // If request was aborted inside a prefilter, stop there
            if (completed) return jqXHR;
            // We can fire global events as of now if asked to
            // Don't fire events if jQuery.event is undefined in an AMD-usage scenario (trac-15118)
            fireGlobals = jQuery.event && s.global;
            // Watch for a new set of requests
            if (fireGlobals && jQuery.active++ === 0) jQuery.event.trigger("ajaxStart");
            // Uppercase the type
            s.type = s.type.toUpperCase();
            // Determine if request has content
            s.hasContent = !rnoContent.test(s.type);
            // Save the URL in case we're toying with the If-Modified-Since
            // and/or If-None-Match header later on
            // Remove hash to simplify url manipulation
            cacheURL = s.url.replace(rhash, "");
            // More options handling for requests with no content
            if (!s.hasContent) {
                // Remember the hash so we can put it back
                uncached = s.url.slice(cacheURL.length);
                // If data is available and should be processed, append data to url
                if (s.data && (s.processData || typeof s.data === "string")) {
                    cacheURL += (rquery.test(cacheURL) ? "&" : "?") + s.data;
                    // trac-9682: remove data so that it's not used in an eventual retry
                    delete s.data;
                }
                // Add or update anti-cache param if needed
                if (s.cache === false) {
                    cacheURL = cacheURL.replace(rantiCache, "$1");
                    uncached = (rquery.test(cacheURL) ? "&" : "?") + "_=" + nonce.guid++ + uncached;
                }
                // Put hash and anti-cache on the URL that will be requested (gh-1732)
                s.url = cacheURL + uncached;
            // Change '%20' to '+' if this is encoded form body content (gh-2658)
            } else if (s.data && s.processData && (s.contentType || "").indexOf("application/x-www-form-urlencoded") === 0) s.data = s.data.replace(r20, "+");
            // Set the If-Modified-Since and/or If-None-Match header, if in ifModified mode.
            if (s.ifModified) {
                if (jQuery.lastModified[cacheURL]) jqXHR.setRequestHeader("If-Modified-Since", jQuery.lastModified[cacheURL]);
                if (jQuery.etag[cacheURL]) jqXHR.setRequestHeader("If-None-Match", jQuery.etag[cacheURL]);
            }
            // Set the correct header, if data is being sent
            if (s.data && s.hasContent && s.contentType !== false || options.contentType) jqXHR.setRequestHeader("Content-Type", s.contentType);
            // Set the Accepts header for the server, depending on the dataType
            jqXHR.setRequestHeader("Accept", s.dataTypes[0] && s.accepts[s.dataTypes[0]] ? s.accepts[s.dataTypes[0]] + (s.dataTypes[0] !== "*" ? ", " + allTypes + "; q=0.01" : "") : s.accepts["*"]);
            // Check for headers option
            for(i in s.headers)jqXHR.setRequestHeader(i, s.headers[i]);
            // Allow custom headers/mimetypes and early abort
            if (s.beforeSend && (s.beforeSend.call(callbackContext, jqXHR, s) === false || completed)) // Abort if not done already and return
            return jqXHR.abort();
            // Aborting is no longer a cancellation
            strAbort = "abort";
            // Install callbacks on deferreds
            completeDeferred.add(s.complete);
            jqXHR.done(s.success);
            jqXHR.fail(s.error);
            // Get transport
            transport = inspectPrefiltersOrTransports(transports, s, options, jqXHR);
            // If no transport, we auto-abort
            if (!transport) done(-1, "No Transport");
            else {
                jqXHR.readyState = 1;
                // Send global event
                if (fireGlobals) globalEventContext.trigger("ajaxSend", [
                    jqXHR,
                    s
                ]);
                // If request was aborted inside ajaxSend, stop there
                if (completed) return jqXHR;
                // Timeout
                if (s.async && s.timeout > 0) timeoutTimer = window1.setTimeout(function() {
                    jqXHR.abort("timeout");
                }, s.timeout);
                try {
                    completed = false;
                    transport.send(requestHeaders, done);
                } catch (e) {
                    // Rethrow post-completion exceptions
                    if (completed) throw e;
                    // Propagate others as results
                    done(-1, e);
                }
            }
            // Callback for when everything is done
            function done(status, nativeStatusText, responses, headers) {
                var isSuccess, success, error, response, modified, statusText = nativeStatusText;
                // Ignore repeat invocations
                if (completed) return;
                completed = true;
                // Clear timeout if it exists
                if (timeoutTimer) window1.clearTimeout(timeoutTimer);
                // Dereference transport for early garbage collection
                // (no matter how long the jqXHR object will be used)
                transport = undefined;
                // Cache response headers
                responseHeadersString = headers || "";
                // Set readyState
                jqXHR.readyState = status > 0 ? 4 : 0;
                // Determine if successful
                isSuccess = status >= 200 && status < 300 || status === 304;
                // Get response data
                if (responses) response = ajaxHandleResponses(s, jqXHR, responses);
                // Use a noop converter for missing script but not if jsonp
                if (!isSuccess && jQuery.inArray("script", s.dataTypes) > -1 && jQuery.inArray("json", s.dataTypes) < 0) s.converters["text script"] = function() {};
                // Convert no matter what (that way responseXXX fields are always set)
                response = ajaxConvert(s, response, jqXHR, isSuccess);
                // If successful, handle type chaining
                if (isSuccess) {
                    // Set the If-Modified-Since and/or If-None-Match header, if in ifModified mode.
                    if (s.ifModified) {
                        modified = jqXHR.getResponseHeader("Last-Modified");
                        if (modified) jQuery.lastModified[cacheURL] = modified;
                        modified = jqXHR.getResponseHeader("etag");
                        if (modified) jQuery.etag[cacheURL] = modified;
                    }
                    // if no content
                    if (status === 204 || s.type === "HEAD") statusText = "nocontent";
                    else if (status === 304) statusText = "notmodified";
                    else {
                        statusText = response.state;
                        success = response.data;
                        error = response.error;
                        isSuccess = !error;
                    }
                } else {
                    // Extract error from statusText and normalize for non-aborts
                    error = statusText;
                    if (status || !statusText) {
                        statusText = "error";
                        if (status < 0) status = 0;
                    }
                }
                // Set data for the fake xhr object
                jqXHR.status = status;
                jqXHR.statusText = (nativeStatusText || statusText) + "";
                // Success/Error
                if (isSuccess) deferred.resolveWith(callbackContext, [
                    success,
                    statusText,
                    jqXHR
                ]);
                else deferred.rejectWith(callbackContext, [
                    jqXHR,
                    statusText,
                    error
                ]);
                // Status-dependent callbacks
                jqXHR.statusCode(statusCode);
                statusCode = undefined;
                if (fireGlobals) globalEventContext.trigger(isSuccess ? "ajaxSuccess" : "ajaxError", [
                    jqXHR,
                    s,
                    isSuccess ? success : error
                ]);
                // Complete
                completeDeferred.fireWith(callbackContext, [
                    jqXHR,
                    statusText
                ]);
                if (fireGlobals) {
                    globalEventContext.trigger("ajaxComplete", [
                        jqXHR,
                        s
                    ]);
                    // Handle the global AJAX counter
                    if (!--jQuery.active) jQuery.event.trigger("ajaxStop");
                }
            }
            return jqXHR;
        },
        getJSON: function(url, data, callback) {
            return jQuery.get(url, data, callback, "json");
        },
        getScript: function(url, callback) {
            return jQuery.get(url, undefined, callback, "script");
        }
    });
    jQuery.each([
        "get",
        "post"
    ], function(_i, method) {
        jQuery[method] = function(url, data, callback, type) {
            // Shift arguments if data argument was omitted
            if (isFunction(data)) {
                type = type || callback;
                callback = data;
                data = undefined;
            }
            // The url can be an options object (which then must have .url)
            return jQuery.ajax(jQuery.extend({
                url: url,
                type: method,
                dataType: type,
                data: data,
                success: callback
            }, jQuery.isPlainObject(url) && url));
        };
    });
    jQuery.ajaxPrefilter(function(s) {
        var i;
        for(i in s.headers)if (i.toLowerCase() === "content-type") s.contentType = s.headers[i] || "";
    });
    jQuery._evalUrl = function(url, options, doc) {
        return jQuery.ajax({
            url: url,
            // Make this explicit, since user can override this through ajaxSetup (trac-11264)
            type: "GET",
            dataType: "script",
            cache: true,
            async: false,
            global: false,
            // Only evaluate the response if it is successful (gh-4126)
            // dataFilter is not invoked for failure responses, so using it instead
            // of the default converter is kludgy but it works.
            converters: {
                "text script": function() {}
            },
            dataFilter: function(response) {
                jQuery.globalEval(response, options, doc);
            }
        });
    };
    jQuery.fn.extend({
        wrapAll: function(html) {
            var wrap;
            if (this[0]) {
                if (isFunction(html)) html = html.call(this[0]);
                // The elements to wrap the target around
                wrap = jQuery(html, this[0].ownerDocument).eq(0).clone(true);
                if (this[0].parentNode) wrap.insertBefore(this[0]);
                wrap.map(function() {
                    var elem = this;
                    while(elem.firstElementChild)elem = elem.firstElementChild;
                    return elem;
                }).append(this);
            }
            return this;
        },
        wrapInner: function(html) {
            if (isFunction(html)) return this.each(function(i) {
                jQuery(this).wrapInner(html.call(this, i));
            });
            return this.each(function() {
                var self = jQuery(this), contents = self.contents();
                if (contents.length) contents.wrapAll(html);
                else self.append(html);
            });
        },
        wrap: function(html) {
            var htmlIsFunction = isFunction(html);
            return this.each(function(i) {
                jQuery(this).wrapAll(htmlIsFunction ? html.call(this, i) : html);
            });
        },
        unwrap: function(selector) {
            this.parent(selector).not("body").each(function() {
                jQuery(this).replaceWith(this.childNodes);
            });
            return this;
        }
    });
    jQuery.expr.pseudos.hidden = function(elem) {
        return !jQuery.expr.pseudos.visible(elem);
    };
    jQuery.expr.pseudos.visible = function(elem) {
        return !!(elem.offsetWidth || elem.offsetHeight || elem.getClientRects().length);
    };
    jQuery.ajaxSettings.xhr = function() {
        try {
            return new window1.XMLHttpRequest();
        } catch (e) {}
    };
    var xhrSuccessStatus = {
        // File protocol always yields status code 0, assume 200
        0: 200,
        // Support: IE <=9 only
        // trac-1450: sometimes IE returns 1223 when it should be 204
        1223: 204
    }, xhrSupported = jQuery.ajaxSettings.xhr();
    support.cors = !!xhrSupported && "withCredentials" in xhrSupported;
    support.ajax = xhrSupported = !!xhrSupported;
    jQuery.ajaxTransport(function(options) {
        var callback, errorCallback;
        // Cross domain only allowed if supported through XMLHttpRequest
        if (support.cors || xhrSupported && !options.crossDomain) return {
            send: function(headers, complete) {
                var i, xhr = options.xhr();
                xhr.open(options.type, options.url, options.async, options.username, options.password);
                // Apply custom fields if provided
                if (options.xhrFields) for(i in options.xhrFields)xhr[i] = options.xhrFields[i];
                // Override mime type if needed
                if (options.mimeType && xhr.overrideMimeType) xhr.overrideMimeType(options.mimeType);
                // X-Requested-With header
                // For cross-domain requests, seeing as conditions for a preflight are
                // akin to a jigsaw puzzle, we simply never set it to be sure.
                // (it can always be set on a per-request basis or even using ajaxSetup)
                // For same-domain requests, won't change header if already provided.
                if (!options.crossDomain && !headers["X-Requested-With"]) headers["X-Requested-With"] = "XMLHttpRequest";
                // Set headers
                for(i in headers)xhr.setRequestHeader(i, headers[i]);
                // Callback
                callback = function(type) {
                    return function() {
                        if (callback) {
                            callback = errorCallback = xhr.onload = xhr.onerror = xhr.onabort = xhr.ontimeout = xhr.onreadystatechange = null;
                            if (type === "abort") xhr.abort();
                            else if (type === "error") {
                                // Support: IE <=9 only
                                // On a manual native abort, IE9 throws
                                // errors on any property access that is not readyState
                                if (typeof xhr.status !== "number") complete(0, "error");
                                else complete(// File: protocol always yields status 0; see trac-8605, trac-14207
                                xhr.status, xhr.statusText);
                            } else complete(xhrSuccessStatus[xhr.status] || xhr.status, xhr.statusText, // Support: IE <=9 only
                            // IE9 has no XHR2 but throws on binary (trac-11426)
                            // For XHR2 non-text, let the caller handle it (gh-2498)
                            (xhr.responseType || "text") !== "text" || typeof xhr.responseText !== "string" ? {
                                binary: xhr.response
                            } : {
                                text: xhr.responseText
                            }, xhr.getAllResponseHeaders());
                        }
                    };
                };
                // Listen to events
                xhr.onload = callback();
                errorCallback = xhr.onerror = xhr.ontimeout = callback("error");
                // Support: IE 9 only
                // Use onreadystatechange to replace onabort
                // to handle uncaught aborts
                if (xhr.onabort !== undefined) xhr.onabort = errorCallback;
                else xhr.onreadystatechange = function() {
                    // Check readyState before timeout as it changes
                    if (xhr.readyState === 4) // Allow onerror to be called first,
                    // but that will not handle a native abort
                    // Also, save errorCallback to a variable
                    // as xhr.onerror cannot be accessed
                    window1.setTimeout(function() {
                        if (callback) errorCallback();
                    });
                };
                // Create the abort callback
                callback = callback("abort");
                try {
                    // Do send the request (this may raise an exception)
                    xhr.send(options.hasContent && options.data || null);
                } catch (e) {
                    // trac-14683: Only rethrow if this hasn't been notified as an error yet
                    if (callback) throw e;
                }
            },
            abort: function() {
                if (callback) callback();
            }
        };
    });
    // Prevent auto-execution of scripts when no explicit dataType was provided (See gh-2432)
    jQuery.ajaxPrefilter(function(s) {
        if (s.crossDomain) s.contents.script = false;
    });
    // Install script dataType
    jQuery.ajaxSetup({
        accepts: {
            script: "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript"
        },
        contents: {
            script: /\b(?:java|ecma)script\b/
        },
        converters: {
            "text script": function(text) {
                jQuery.globalEval(text);
                return text;
            }
        }
    });
    // Handle cache's special case and crossDomain
    jQuery.ajaxPrefilter("script", function(s) {
        if (s.cache === undefined) s.cache = false;
        if (s.crossDomain) s.type = "GET";
    });
    // Bind script tag hack transport
    jQuery.ajaxTransport("script", function(s) {
        // This transport only deals with cross domain or forced-by-attrs requests
        if (s.crossDomain || s.scriptAttrs) {
            var script, callback;
            return {
                send: function(_, complete) {
                    script = jQuery("<script>").attr(s.scriptAttrs || {}).prop({
                        charset: s.scriptCharset,
                        src: s.url
                    }).on("load error", callback = function(evt) {
                        script.remove();
                        callback = null;
                        if (evt) complete(evt.type === "error" ? 404 : 200, evt.type);
                    });
                    // Use native DOM manipulation to avoid our domManip AJAX trickery
                    document.head.appendChild(script[0]);
                },
                abort: function() {
                    if (callback) callback();
                }
            };
        }
    });
    var oldCallbacks = [], rjsonp = /(=)\?(?=&|$)|\?\?/;
    // Default jsonp settings
    jQuery.ajaxSetup({
        jsonp: "callback",
        jsonpCallback: function() {
            var callback = oldCallbacks.pop() || jQuery.expando + "_" + nonce.guid++;
            this[callback] = true;
            return callback;
        }
    });
    // Detect, normalize options and install callbacks for jsonp requests
    jQuery.ajaxPrefilter("json jsonp", function(s, originalSettings, jqXHR) {
        var callbackName, overwritten, responseContainer, jsonProp = s.jsonp !== false && (rjsonp.test(s.url) ? "url" : typeof s.data === "string" && (s.contentType || "").indexOf("application/x-www-form-urlencoded") === 0 && rjsonp.test(s.data) && "data");
        // Handle iff the expected data type is "jsonp" or we have a parameter to set
        if (jsonProp || s.dataTypes[0] === "jsonp") {
            // Get callback name, remembering preexisting value associated with it
            callbackName = s.jsonpCallback = isFunction(s.jsonpCallback) ? s.jsonpCallback() : s.jsonpCallback;
            // Insert callback into url or form data
            if (jsonProp) s[jsonProp] = s[jsonProp].replace(rjsonp, "$1" + callbackName);
            else if (s.jsonp !== false) s.url += (rquery.test(s.url) ? "&" : "?") + s.jsonp + "=" + callbackName;
            // Use data converter to retrieve json after script execution
            s.converters["script json"] = function() {
                if (!responseContainer) jQuery.error(callbackName + " was not called");
                return responseContainer[0];
            };
            // Force json dataType
            s.dataTypes[0] = "json";
            // Install callback
            overwritten = window1[callbackName];
            window1[callbackName] = function() {
                responseContainer = arguments;
            };
            // Clean-up function (fires after converters)
            jqXHR.always(function() {
                // If previous value didn't exist - remove it
                if (overwritten === undefined) jQuery(window1).removeProp(callbackName);
                else window1[callbackName] = overwritten;
                // Save back as free
                if (s[callbackName]) {
                    // Make sure that re-using the options doesn't screw things around
                    s.jsonpCallback = originalSettings.jsonpCallback;
                    // Save the callback name for future use
                    oldCallbacks.push(callbackName);
                }
                // Call if it was a function and we have a response
                if (responseContainer && isFunction(overwritten)) overwritten(responseContainer[0]);
                responseContainer = overwritten = undefined;
            });
            // Delegate to script
            return "script";
        }
    });
    // Support: Safari 8 only
    // In Safari 8 documents created via document.implementation.createHTMLDocument
    // collapse sibling forms: the second one becomes a child of the first one.
    // Because of that, this security measure has to be disabled in Safari 8.
    // https://bugs.webkit.org/show_bug.cgi?id=137337
    support.createHTMLDocument = function() {
        var body = document.implementation.createHTMLDocument("").body;
        body.innerHTML = "<form></form><form></form>";
        return body.childNodes.length === 2;
    }();
    // Argument "data" should be string of html
    // context (optional): If specified, the fragment will be created in this context,
    // defaults to document
    // keepScripts (optional): If true, will include scripts passed in the html string
    jQuery.parseHTML = function(data, context, keepScripts) {
        if (typeof data !== "string") return [];
        if (typeof context === "boolean") {
            keepScripts = context;
            context = false;
        }
        var base, parsed, scripts;
        if (!context) {
            // Stop scripts or inline event handlers from being executed immediately
            // by using document.implementation
            if (support.createHTMLDocument) {
                context = document.implementation.createHTMLDocument("");
                // Set the base href for the created document
                // so any parsed elements with URLs
                // are based on the document's URL (gh-2965)
                base = context.createElement("base");
                base.href = document.location.href;
                context.head.appendChild(base);
            } else context = document;
        }
        parsed = rsingleTag.exec(data);
        scripts = !keepScripts && [];
        // Single tag
        if (parsed) return [
            context.createElement(parsed[1])
        ];
        parsed = buildFragment([
            data
        ], context, scripts);
        if (scripts && scripts.length) jQuery(scripts).remove();
        return jQuery.merge([], parsed.childNodes);
    };
    /**
 * Load a url into a page
 */ jQuery.fn.load = function(url, params, callback) {
        var selector, type, response, self = this, off = url.indexOf(" ");
        if (off > -1) {
            selector = stripAndCollapse(url.slice(off));
            url = url.slice(0, off);
        }
        // If it's a function
        if (isFunction(params)) {
            // We assume that it's the callback
            callback = params;
            params = undefined;
        // Otherwise, build a param string
        } else if (params && typeof params === "object") type = "POST";
        // If we have elements to modify, make the request
        if (self.length > 0) jQuery.ajax({
            url: url,
            // If "type" variable is undefined, then "GET" method will be used.
            // Make value of this field explicit since
            // user can override it through ajaxSetup method
            type: type || "GET",
            dataType: "html",
            data: params
        }).done(function(responseText) {
            // Save response for use in complete callback
            response = arguments;
            self.html(selector ? // If a selector was specified, locate the right elements in a dummy div
            // Exclude scripts to avoid IE 'Permission Denied' errors
            jQuery("<div>").append(jQuery.parseHTML(responseText)).find(selector) : // Otherwise use the full result
            responseText);
        // If the request succeeds, this function gets "data", "status", "jqXHR"
        // but they are ignored because response was set above.
        // If it fails, this function gets "jqXHR", "status", "error"
        }).always(callback && function(jqXHR, status) {
            self.each(function() {
                callback.apply(this, response || [
                    jqXHR.responseText,
                    status,
                    jqXHR
                ]);
            });
        });
        return this;
    };
    jQuery.expr.pseudos.animated = function(elem) {
        return jQuery.grep(jQuery.timers, function(fn) {
            return elem === fn.elem;
        }).length;
    };
    jQuery.offset = {
        setOffset: function(elem, options, i) {
            var curPosition, curLeft, curCSSTop, curTop, curOffset, curCSSLeft, calculatePosition, position = jQuery.css(elem, "position"), curElem = jQuery(elem), props = {};
            // Set position first, in-case top/left are set even on static elem
            if (position === "static") elem.style.position = "relative";
            curOffset = curElem.offset();
            curCSSTop = jQuery.css(elem, "top");
            curCSSLeft = jQuery.css(elem, "left");
            calculatePosition = (position === "absolute" || position === "fixed") && (curCSSTop + curCSSLeft).indexOf("auto") > -1;
            // Need to be able to calculate position if either
            // top or left is auto and position is either absolute or fixed
            if (calculatePosition) {
                curPosition = curElem.position();
                curTop = curPosition.top;
                curLeft = curPosition.left;
            } else {
                curTop = parseFloat(curCSSTop) || 0;
                curLeft = parseFloat(curCSSLeft) || 0;
            }
            if (isFunction(options)) // Use jQuery.extend here to allow modification of coordinates argument (gh-1848)
            options = options.call(elem, i, jQuery.extend({}, curOffset));
            if (options.top != null) props.top = options.top - curOffset.top + curTop;
            if (options.left != null) props.left = options.left - curOffset.left + curLeft;
            if ("using" in options) options.using.call(elem, props);
            else curElem.css(props);
        }
    };
    jQuery.fn.extend({
        // offset() relates an element's border box to the document origin
        offset: function(options) {
            // Preserve chaining for setter
            if (arguments.length) return options === undefined ? this : this.each(function(i) {
                jQuery.offset.setOffset(this, options, i);
            });
            var rect, win, elem = this[0];
            if (!elem) return;
            // Return zeros for disconnected and hidden (display: none) elements (gh-2310)
            // Support: IE <=11 only
            // Running getBoundingClientRect on a
            // disconnected node in IE throws an error
            if (!elem.getClientRects().length) return {
                top: 0,
                left: 0
            };
            // Get document-relative position by adding viewport scroll to viewport-relative gBCR
            rect = elem.getBoundingClientRect();
            win = elem.ownerDocument.defaultView;
            return {
                top: rect.top + win.pageYOffset,
                left: rect.left + win.pageXOffset
            };
        },
        // position() relates an element's margin box to its offset parent's padding box
        // This corresponds to the behavior of CSS absolute positioning
        position: function() {
            if (!this[0]) return;
            var offsetParent, offset, doc, elem = this[0], parentOffset = {
                top: 0,
                left: 0
            };
            // position:fixed elements are offset from the viewport, which itself always has zero offset
            if (jQuery.css(elem, "position") === "fixed") // Assume position:fixed implies availability of getBoundingClientRect
            offset = elem.getBoundingClientRect();
            else {
                offset = this.offset();
                // Account for the *real* offset parent, which can be the document or its root element
                // when a statically positioned element is identified
                doc = elem.ownerDocument;
                offsetParent = elem.offsetParent || doc.documentElement;
                while(offsetParent && (offsetParent === doc.body || offsetParent === doc.documentElement) && jQuery.css(offsetParent, "position") === "static")offsetParent = offsetParent.parentNode;
                if (offsetParent && offsetParent !== elem && offsetParent.nodeType === 1) {
                    // Incorporate borders into its offset, since they are outside its content origin
                    parentOffset = jQuery(offsetParent).offset();
                    parentOffset.top += jQuery.css(offsetParent, "borderTopWidth", true);
                    parentOffset.left += jQuery.css(offsetParent, "borderLeftWidth", true);
                }
            }
            // Subtract parent offsets and element margins
            return {
                top: offset.top - parentOffset.top - jQuery.css(elem, "marginTop", true),
                left: offset.left - parentOffset.left - jQuery.css(elem, "marginLeft", true)
            };
        },
        // This method will return documentElement in the following cases:
        // 1) For the element inside the iframe without offsetParent, this method will return
        //    documentElement of the parent window
        // 2) For the hidden or detached element
        // 3) For body or html element, i.e. in case of the html node - it will return itself
        //
        // but those exceptions were never presented as a real life use-cases
        // and might be considered as more preferable results.
        //
        // This logic, however, is not guaranteed and can change at any point in the future
        offsetParent: function() {
            return this.map(function() {
                var offsetParent = this.offsetParent;
                while(offsetParent && jQuery.css(offsetParent, "position") === "static")offsetParent = offsetParent.offsetParent;
                return offsetParent || documentElement;
            });
        }
    });
    // Create scrollLeft and scrollTop methods
    jQuery.each({
        scrollLeft: "pageXOffset",
        scrollTop: "pageYOffset"
    }, function(method, prop) {
        var top = "pageYOffset" === prop;
        jQuery.fn[method] = function(val) {
            return access(this, function(elem, method, val) {
                // Coalesce documents and windows
                var win;
                if (isWindow(elem)) win = elem;
                else if (elem.nodeType === 9) win = elem.defaultView;
                if (val === undefined) return win ? win[prop] : elem[method];
                if (win) win.scrollTo(!top ? val : win.pageXOffset, top ? val : win.pageYOffset);
                else elem[method] = val;
            }, method, val, arguments.length);
        };
    });
    // Support: Safari <=7 - 9.1, Chrome <=37 - 49
    // Add the top/left cssHooks using jQuery.fn.position
    // Webkit bug: https://bugs.webkit.org/show_bug.cgi?id=29084
    // Blink bug: https://bugs.chromium.org/p/chromium/issues/detail?id=589347
    // getComputedStyle returns percent when specified for top/left/bottom/right;
    // rather than make the css module depend on the offset module, just check for it here
    jQuery.each([
        "top",
        "left"
    ], function(_i, prop) {
        jQuery.cssHooks[prop] = addGetHookIf(support.pixelPosition, function(elem, computed) {
            if (computed) {
                computed = curCSS(elem, prop);
                // If curCSS returns percentage, fallback to offset
                return rnumnonpx.test(computed) ? jQuery(elem).position()[prop] + "px" : computed;
            }
        });
    });
    // Create innerHeight, innerWidth, height, width, outerHeight and outerWidth methods
    jQuery.each({
        Height: "height",
        Width: "width"
    }, function(name, type) {
        jQuery.each({
            padding: "inner" + name,
            content: type,
            "": "outer" + name
        }, function(defaultExtra, funcName) {
            // Margin is only for outerHeight, outerWidth
            jQuery.fn[funcName] = function(margin, value) {
                var chainable = arguments.length && (defaultExtra || typeof margin !== "boolean"), extra = defaultExtra || (margin === true || value === true ? "margin" : "border");
                return access(this, function(elem, type, value) {
                    var doc;
                    if (isWindow(elem)) // $( window ).outerWidth/Height return w/h including scrollbars (gh-1729)
                    return funcName.indexOf("outer") === 0 ? elem["inner" + name] : elem.document.documentElement["client" + name];
                    // Get document width or height
                    if (elem.nodeType === 9) {
                        doc = elem.documentElement;
                        // Either scroll[Width/Height] or offset[Width/Height] or client[Width/Height],
                        // whichever is greatest
                        return Math.max(elem.body["scroll" + name], doc["scroll" + name], elem.body["offset" + name], doc["offset" + name], doc["client" + name]);
                    }
                    return value === undefined ? // Get width or height on the element, requesting but not forcing parseFloat
                    jQuery.css(elem, type, extra) : // Set width or height on the element
                    jQuery.style(elem, type, value, extra);
                }, type, chainable ? margin : undefined, chainable);
            };
        });
    });
    jQuery.each([
        "ajaxStart",
        "ajaxStop",
        "ajaxComplete",
        "ajaxError",
        "ajaxSuccess",
        "ajaxSend"
    ], function(_i, type) {
        jQuery.fn[type] = function(fn) {
            return this.on(type, fn);
        };
    });
    jQuery.fn.extend({
        bind: function(types, data, fn) {
            return this.on(types, null, data, fn);
        },
        unbind: function(types, fn) {
            return this.off(types, null, fn);
        },
        delegate: function(selector, types, data, fn) {
            return this.on(types, selector, data, fn);
        },
        undelegate: function(selector, types, fn) {
            // ( namespace ) or ( selector, types [, fn] )
            return arguments.length === 1 ? this.off(selector, "**") : this.off(types, selector || "**", fn);
        },
        hover: function(fnOver, fnOut) {
            return this.mouseenter(fnOver).mouseleave(fnOut || fnOver);
        }
    });
    jQuery.each("blur focus focusin focusout resize scroll click dblclick mousedown mouseup mousemove mouseover mouseout mouseenter mouseleave change select submit keydown keypress keyup contextmenu".split(" "), function(_i, name) {
        // Handle event binding
        jQuery.fn[name] = function(data, fn) {
            return arguments.length > 0 ? this.on(name, null, data, fn) : this.trigger(name);
        };
    });
    // Support: Android <=4.0 only
    // Make sure we trim BOM and NBSP
    // Require that the "whitespace run" starts from a non-whitespace
    // to avoid O(N^2) behavior when the engine would try matching "\s+$" at each space position.
    var rtrim = /^[\s\uFEFF\xA0]+|([^\s\uFEFF\xA0])[\s\uFEFF\xA0]+$/g;
    // Bind a function to a context, optionally partially applying any
    // arguments.
    // jQuery.proxy is deprecated to promote standards (specifically Function#bind)
    // However, it is not slated for removal any time soon
    jQuery.proxy = function(fn, context) {
        var tmp, args, proxy;
        if (typeof context === "string") {
            tmp = fn[context];
            context = fn;
            fn = tmp;
        }
        // Quick check to determine if target is callable, in the spec
        // this throws a TypeError, but we will just return undefined.
        if (!isFunction(fn)) return undefined;
        // Simulated bind
        args = slice.call(arguments, 2);
        proxy = function() {
            return fn.apply(context || this, args.concat(slice.call(arguments)));
        };
        // Set the guid of unique handler to the same of original handler, so it can be removed
        proxy.guid = fn.guid = fn.guid || jQuery.guid++;
        return proxy;
    };
    jQuery.holdReady = function(hold) {
        if (hold) jQuery.readyWait++;
        else jQuery.ready(true);
    };
    jQuery.isArray = Array.isArray;
    jQuery.parseJSON = JSON.parse;
    jQuery.nodeName = nodeName;
    jQuery.isFunction = isFunction;
    jQuery.isWindow = isWindow;
    jQuery.camelCase = camelCase;
    jQuery.type = toType;
    jQuery.now = Date.now;
    jQuery.isNumeric = function(obj) {
        // As of jQuery 3.0, isNumeric is limited to
        // strings and numbers (primitives or objects)
        // that can be coerced to finite numbers (gh-2662)
        var type = jQuery.type(obj);
        return (type === "number" || type === "string") && // parseFloat NaNs numeric-cast false positives ("")
        // ...but misinterprets leading-number strings, particularly hex literals ("0x...")
        // subtraction forces infinities to NaN
        !isNaN(obj - parseFloat(obj));
    };
    jQuery.trim = function(text) {
        return text == null ? "" : (text + "").replace(rtrim, "$1");
    };
    // Register as a named AMD module, since jQuery can be concatenated with other
    // files that may use define, but not via a proper concatenation script that
    // understands anonymous AMD modules. A named AMD is safest and most robust
    // way to register. Lowercase jquery is used because AMD module names are
    // derived from file names, and jQuery is normally delivered in a lowercase
    // file name. Do this after creating the global so that if an AMD module wants
    // to call noConflict to hide this version of jQuery, it will work.
    // Note that for maximum portability, libraries that are not jQuery should
    // declare themselves as anonymous modules, and avoid setting a global if an
    // AMD loader is present. jQuery is a special case. For more information, see
    // https://github.com/jrburke/requirejs/wiki/Updating-existing-libraries#wiki-anon
    if (typeof define === "function" && define.amd) define("jquery", [], function() {
        return jQuery;
    });
    var // Map over jQuery in case of overwrite
    _jQuery = window1.jQuery, // Map over the $ in case of overwrite
    _$ = window1.$;
    jQuery.noConflict = function(deep) {
        if (window1.$ === jQuery) window1.$ = _$;
        if (deep && window1.jQuery === jQuery) window1.jQuery = _jQuery;
        return jQuery;
    };
    // Expose jQuery and $ identifiers, even in AMD
    // (trac-7102#comment:10, https://github.com/jquery/jquery/pull/557)
    // and CommonJS for browser emulators (trac-13566)
    if (typeof noGlobal === "undefined") window1.jQuery = window1.$ = jQuery;
    return jQuery;
});

},{}]},["l33Ty","KmxTh"], "KmxTh", "parcelRequirecea6")

//# sourceMappingURL=client.509fc7ed.js.map
