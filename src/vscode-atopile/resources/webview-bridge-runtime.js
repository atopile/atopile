(function () {
  var configElementId = 'atopile-webview-bridge-config';

  function readConfig() {
    var element = document.getElementById(configElementId);
    if (!element || !element.textContent) {
      return {};
    }
    try {
      return JSON.parse(element.textContent);
    } catch (err) {
      console.error('[atopile webview] Failed to parse bridge config:', err);
      return {};
    }
  }

  var config = readConfig();
  var apiUrl = typeof config.apiUrl === 'string' ? config.apiUrl : '';
  var fetchMode = config.fetchMode === 'override' ? 'override' : 'global';

  var originalAcquire = window.acquireVsCodeApi;
  var vsCodeApi = null;
  if (typeof originalAcquire === 'function') {
    window.acquireVsCodeApi = function () {
      if (!vsCodeApi) {
        vsCodeApi = originalAcquire();
      }
      return vsCodeApi;
    };
  }

  function getVsCodeApi() {
    try {
      return vsCodeApi || (window.acquireVsCodeApi ? window.acquireVsCodeApi() : null);
    } catch (err) {
      console.error('[atopile webview] Failed to acquire VS Code API:', err);
      return null;
    }
  }

  function normalizeHeaders(headers) {
    if (!headers) {
      return {};
    }
    if (typeof Headers !== 'undefined' && headers instanceof Headers) {
      var headerMap = {};
      headers.forEach(function (value, key) {
        headerMap[key] = value;
      });
      return headerMap;
    }
    if (Array.isArray(headers)) {
      var arrayHeaders = {};
      for (var i = 0; i < headers.length; i++) {
        var entry = headers[i];
        if (Array.isArray(entry) && entry.length >= 2) {
          arrayHeaders[String(entry[0])] = String(entry[1]);
        }
      }
      return arrayHeaders;
    }
    return headers;
  }

  function createCompatEvent(type, init) {
    var eventObject;
    try {
      if (type === 'message' && typeof MessageEvent === 'function') {
        eventObject = new MessageEvent('message', { data: init && init.data });
      } else if (type === 'close' && typeof CloseEvent === 'function') {
        eventObject = new CloseEvent('close', {
          code: (init && init.code) || 1000,
          reason: (init && init.reason) || '',
          wasClean: true,
        });
      } else {
        eventObject = new Event(type);
      }
    } catch (_error) {
      eventObject = document.createEvent('Event');
      eventObject.initEvent(type, false, false);
    }

    if (init && init.data !== undefined && eventObject.data === undefined) {
      eventObject.data = init.data;
    }
    if (init && init.code !== undefined && eventObject.code === undefined) {
      eventObject.code = init.code;
    }
    if (init && init.reason !== undefined && eventObject.reason === undefined) {
      eventObject.reason = init.reason;
    }
    return eventObject;
  }

  function base64ToUint8Array(base64) {
    if (!base64) {
      return new Uint8Array(0);
    }
    var binary = atob(base64);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
  }

  function createProxySocket(url, id) {
    var listeners = { open: [], message: [], close: [], error: [] };
    var socket = {
      _readyState: 0,
      url: url,
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null,
      CONNECTING: 0,
      OPEN: 1,
      CLOSING: 2,
      CLOSED: 3,
      addEventListener: function (type, callback) {
        if (!listeners[type] || typeof callback !== 'function') {
          return;
        }
        listeners[type].push(callback);
      },
      removeEventListener: function (type, callback) {
        if (!listeners[type]) {
          return;
        }
        listeners[type] = listeners[type].filter(function (fn) {
          return fn !== callback;
        });
      },
      dispatchEvent: function (eventObject) {
        var type = eventObject && eventObject.type ? eventObject.type : '';
        var callbacks = listeners[type] || [];
        for (var i = 0; i < callbacks.length; i++) {
          try {
            callbacks[i](eventObject);
          } catch (err) {
            console.error(err);
          }
        }
        return true;
      },
      send: function (data) {
        var api = getVsCodeApi();
        if (api) {
          api.postMessage({ type: 'wsProxySend', id: id, data: data });
        }
      },
      close: function (code, reason) {
        socket._readyState = 2;
        var api = getVsCodeApi();
        if (api) {
          api.postMessage({ type: 'wsProxyClose', id: id, code: code, reason: reason });
        }
      },
    };

    Object.defineProperty(socket, 'readyState', {
      get: function () {
        return socket._readyState;
      },
    });

    return socket;
  }

  function installFetchOverride() {
    var originalFetch = window.fetch;
    var fetchId = 0;
    var pendingFetch = new Map();

    window.addEventListener('message', function (event) {
      var message = event.data;
      if (!message || message.type !== 'fetchProxyResult' || !pendingFetch.has(message.id)) {
        return;
      }
      var handler = pendingFetch.get(message.id);
      pendingFetch.delete(message.id);
      handler(message);
    });

    window.fetch = function (input, init) {
      var url = typeof input === 'string' ? input : (input instanceof Request ? input.url : String(input));
      if (!apiUrl || !url.startsWith(apiUrl)) {
        return originalFetch.apply(this, arguments);
      }

      return new Promise(function (resolve, reject) {
        var id = ++fetchId;
        var timeout = setTimeout(function () {
          pendingFetch.delete(id);
          reject(new TypeError('Fetch proxy timeout'));
        }, 30000);

        pendingFetch.set(id, function (message) {
          clearTimeout(timeout);
          if (message.error) {
            reject(new TypeError(message.error));
            return;
          }
          resolve(new Response(base64ToUint8Array(message.bodyBase64), {
            status: message.status || 200,
            statusText: message.statusText || 'OK',
            headers: message.headers || {},
          }));
        });

        var api = getVsCodeApi();
        if (!api) {
          clearTimeout(timeout);
          pendingFetch.delete(id);
          reject(new TypeError('[atopile] VS Code API not available for fetch proxy'));
          return;
        }

        api.postMessage({
          type: 'fetchProxy',
          id: id,
          url: url,
          method: (init && init.method) || 'GET',
          headers: normalizeHeaders(init && init.headers),
          body: (init && init.body) || null,
        });
      });
    };
  }

  function installGlobalFetchProxy() {
    var fetchId = 0;
    var pendingFetch = new Map();

    window.addEventListener('message', function (event) {
      var message = event.data;
      if (!message || message.type !== 'fetchProxyResult' || !pendingFetch.has(message.id)) {
        return;
      }
      var handler = pendingFetch.get(message.id);
      pendingFetch.delete(message.id);
      handler(message);
    });

    window.__ATOPILE_PROXY_FETCH__ = function (url, init) {
      var id = ++fetchId;
      return new Promise(function (resolve, reject) {
        var timeout = setTimeout(function () {
          pendingFetch.delete(id);
          reject(new TypeError('Fetch proxy timeout'));
        }, 30000);

        pendingFetch.set(id, function (message) {
          clearTimeout(timeout);
          if (message.error) {
            reject(new TypeError(message.error));
            return;
          }
          resolve(new Response(base64ToUint8Array(message.bodyBase64), {
            status: message.status || 200,
            statusText: message.statusText || 'OK',
            headers: message.headers || {},
          }));
        });

        var api = getVsCodeApi();
        if (!api) {
          clearTimeout(timeout);
          pendingFetch.delete(id);
          reject(new TypeError('VS Code API not available for fetch proxy'));
          return;
        }

        api.postMessage({
          type: 'fetchProxy',
          id: id,
          url: url,
          method: (init && init.method) || 'GET',
          headers: normalizeHeaders(init && init.headers),
          body: (init && init.body) || null,
        });
      });
    };
  }

  if (fetchMode === 'override') {
    installFetchOverride();
  } else {
    installGlobalFetchProxy();
  }

  var wsProxyId = 0;
  var wsProxyInstances = new Map();

  window.addEventListener('message', function (event) {
    var message = event.data;
    if (!message || !message.type) {
      return;
    }
    var instance = message.id != null ? wsProxyInstances.get(message.id) : null;
    if (!instance) {
      return;
    }
    switch (message.type) {
      case 'wsProxyOpen': {
        instance._readyState = 1;
        var openEvent = createCompatEvent('open');
        if (instance.onopen) {
          instance.onopen(openEvent);
        }
        instance.dispatchEvent(openEvent);
        break;
      }
      case 'wsProxyMessage': {
        var messageEvent = createCompatEvent('message', { data: message.data });
        if (instance.onmessage) {
          instance.onmessage(messageEvent);
        }
        instance.dispatchEvent(messageEvent);
        break;
      }
      case 'wsProxyClose': {
        instance._readyState = 3;
        var closeEvent = createCompatEvent('close', {
          code: message.code || 1000,
          reason: message.reason || '',
        });
        if (instance.onclose) {
          instance.onclose(closeEvent);
        }
        instance.dispatchEvent(closeEvent);
        wsProxyInstances.delete(message.id);
        break;
      }
      case 'wsProxyError': {
        var errorEvent = createCompatEvent('error');
        if (instance.onerror) {
          instance.onerror(errorEvent);
        }
        instance.dispatchEvent(errorEvent);
        break;
      }
    }
  });

  function ProxyWebSocket(url, protocols) {
    void protocols;

    var api = getVsCodeApi();
    if (!api) {
      throw new Error('[atopile] VS Code API not available for WebSocket proxy');
    }

    var id = ++wsProxyId;
    var socket = createProxySocket(url, id);
    wsProxyInstances.set(id, socket);
    api.postMessage({ type: 'wsProxyConnect', id: id, url: url });
    return socket;
  }

  ProxyWebSocket.CONNECTING = 0;
  ProxyWebSocket.OPEN = 1;
  ProxyWebSocket.CLOSING = 2;
  ProxyWebSocket.CLOSED = 3;

  window.WebSocket = ProxyWebSocket;
})();
