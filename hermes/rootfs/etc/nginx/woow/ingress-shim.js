// Loaded by the ingress adapter only. HA Core routes ingress as
// /api/hassio_ingress/<token>/<path>: a URL that is exactly the prefix, without
// the trailing slash, is a 404 from HA before it reaches the add-on. Keep the
// slash on history updates so a reload of the panel still lands.
(function () {
  var script = document.currentScript;
  if (!script) return;
  var P = new URL(script.src).pathname.replace(/\/__woow\/ingress-shim\.js$/, "");
  if (!/^\/api\/hassio_ingress\/[A-Za-z0-9_-]{16,128}$/.test(P)) return;
  var withSlash = function (u) {
    if (u == null) return u;
    try {
      var x = new URL(u instanceof URL ? u.href : String(u), location.href);
      if (x.origin === location.origin && x.pathname === P) {
        return P + "/" + x.search + x.hash;
      }
    } catch (e) {}
    return u;
  };
  ["pushState", "replaceState"].forEach(function (name) {
    var original = history[name];
    history[name] = function (state, title, url) {
      if (arguments.length > 2) arguments[2] = withSlash(url);
      return original.apply(this, arguments);
    };
  });
  // A few upstream call sites fetch root-absolute URLs without the base path
  // (session export, Swagger "Try it out"). Keep same-origin requests inside the
  // ingress prefix; URLs already under it are left alone.
  var inPrefix = function (u) {
    try {
      var x = new URL(u, location.href);
      if (x.origin !== location.origin) return u;
      if (x.pathname === P || x.pathname.indexOf(P + "/") === 0) return u;
      if (x.pathname.charAt(0) !== "/") return u;
      return P + x.pathname + x.search + x.hash;
    } catch (e) {
      return u;
    }
  };
  var nativeFetch = window.fetch;
  window.fetch = function (input, init) {
    if (typeof input === "string") {
      input = inPrefix(input);
    } else if (input instanceof URL) {
      input = inPrefix(input.href);
    } else if (input && typeof input.url === "string") {
      var fixed = inPrefix(input.url);
      if (fixed !== input.url) input = new Request(fixed, input);
    }
    return nativeFetch.call(this, input, init);
  };
  var nativeOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url) {
    if (typeof url === "string" || url instanceof URL) arguments[1] = inPrefix(String(url));
    return nativeOpen.apply(this, arguments);
  };
  // Diagnostic only: report any request that escapes the ingress prefix.
  try {
    new PerformanceObserver(function (list) {
      list.getEntries().forEach(function (entry) {
        var u = new URL(entry.name);
        if (u.origin === location.origin && u.pathname.indexOf(P + "/") !== 0) {
          console.warn("[woow-ingress] escaped", u.pathname);
        }
      });
    }).observe({ type: "resource", buffered: true });
  } catch (e) {}
})();
