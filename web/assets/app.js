// Landing-page behaviour: show live API status fetched from /health and
// adapt the API links when no API is reachable from this origin.
(function () {
  "use strict";

  var REPO_URL =
    "https://github.com/mohammedyossef662/secure-license-inspection-tracking-api";
  var statusEl = document.getElementById("api-status");
  var versionEl = document.getElementById("api-version");
  var consoleEl = document.getElementById("api-console");
  var redocEl = document.getElementById("redoc-link");
  var openapiEl = document.getElementById("openapi-link");
  var deployNote = document.getElementById("deploy-note");

  function setBadge(state, text) {
    if (!statusEl) return;
    statusEl.className =
      "badge " +
      (state === "ok"
        ? "badge-ok"
        : state === "bad"
          ? "badge-bad"
          : "badge-pending");
    statusEl.textContent = text;
  }

  fetch("/health", { headers: { Accept: "application/json" } })
    .then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(function (data) {
      var database =
        data && data.database === "ok" ? "database ok" : "database degraded";
      setBadge("ok", "API online · " + database);
      if (versionEl && data && data.version) {
        versionEl.textContent = "v" + data.version;
      }
    })
    .catch(function () {
      setBadge("pending", "No API here — deploy the API to use the console");
      if (versionEl) versionEl.textContent = "";
    });

  fetch("/docs", { method: "HEAD" })
    .then(function (response) {
      if (!response.ok) throw new Error("docs unavailable");
    })
    .catch(function () {
      // The API isn't reachable from this origin — turn the console links
      // into a deploy call to action.
      if (consoleEl) {
        consoleEl.textContent = "Deploy the API";
        consoleEl.href = REPO_URL;
      }
      if (redocEl) {
        redocEl.textContent = "Deploy the API";
        redocEl.href = REPO_URL;
      }
      if (openapiEl) {
        openapiEl.textContent = "Deploy the API";
        openapiEl.href = REPO_URL;
      }
      if (deployNote) {
        deployNote.hidden = false;
      }
    });
})();
