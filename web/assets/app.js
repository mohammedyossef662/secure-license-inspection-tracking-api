// Landing-page behaviour: show live API status fetched from /health.
(function () {
  "use strict";

  var statusEl = document.getElementById("api-status");
  var versionEl = document.getElementById("api-version");

  function setBadge(state, text) {
    if (!statusEl) return;
    statusEl.className = "badge " + (state === "ok" ? "badge-ok" : state === "bad" ? "badge-bad" : "badge-pending");
    statusEl.textContent = text;
  }

  fetch("/health", { headers: { Accept: "application/json" } })
    .then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(function (data) {
      var database = data && data.database === "ok" ? "database ok" : "database degraded";
      setBadge("ok", "API online · " + database);
      if (versionEl && data && data.version) {
        versionEl.textContent = "v" + data.version;
      }
    })
    .catch(function () {
      setBadge("bad", "API unreachable");
      if (versionEl) versionEl.textContent = "";
    });
})();
