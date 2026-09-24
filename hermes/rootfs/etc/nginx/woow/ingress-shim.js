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
