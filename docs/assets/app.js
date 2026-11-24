// ==========================================================================
// Regulatory License & Inspection Tracking API — Compliance Console
//
// A dependency-free single-page GUI over the REST API. It is served from the
// same origin as the API (CSP: script-src 'self'; connect-src 'self') and
// keeps the JWT in sessionStorage only, so closing the tab ends the session.
// ==========================================================================
(function () {
  "use strict";

  // ------------------------------------------------------------------------
  // Constants
  // ------------------------------------------------------------------------

  var TOKEN_KEY = "lit.console.token";
  var GITHUB_URL = "https://github.com/mohammedyossef662/secure-license-inspection-tracking-api";
  var OPENAPI_URL = GITHUB_URL + "/blob/main/openapi.json";
  var IS_STATIC_PREVIEW = /\.github\.io$/i.test(window.location.hostname);

  var ROLES = ["admin", "inspector", "viewer"];
  var FACILITY_STATUSES = ["active", "suspended", "closed"];
  var LICENSE_TYPES = [
    "operating",
    "radiation",
    "transport",
    "storage",
    "waste_management",
    "decommissioning",
  ];
  var LICENSE_STATUSES = ["active", "suspended", "revoked", "expired", "pending"];
  var INSPECTION_RESULTS = [
    "compliant",
    "partially_compliant",
    "non_compliant",
    "follow_up_required",
  ];
  var AUDIT_ACTIONS = [
    "login_success",
    "login_failed",
    "login_blocked",
    "access_denied",
    "user_created",
    "user_updated",
    "user_deactivated",
    "profile_updated",
    "facility_created",
    "facility_updated",
    "facility_deleted",
    "license_created",
    "license_updated",
    "license_deleted",
    "inspection_created",
    "inspection_updated",
  ];

  var ROLE_LABELS = {
    admin: "Administrator",
    inspector: "Inspector",
    viewer: "Viewer",
  };

  var NAV_META = {
    dashboard: { eyebrow: "Overview", title: "Dashboard", roles: ROLES },
    facilities: { eyebrow: "Registry", title: "Facilities", roles: ROLES },
    licenses: { eyebrow: "Registry", title: "Licenses", roles: ROLES },
    inspections: { eyebrow: "Compliance", title: "Inspections", roles: ROLES },
    users: { eyebrow: "Administration", title: "Users", roles: ["admin"] },
    audit: { eyebrow: "Administration", title: "Audit log", roles: ["admin"] },
    profile: { eyebrow: "Account", title: "My profile", roles: ROLES },
    about: { eyebrow: "Project", title: "About this API", roles: ROLES },
  };

  var DEFAULT_FILTERS = {
    facilities: { search: "", status: "", page: 1, size: 10 },
    licenses: {
      search: "",
      status: "",
      type: "",
      expired: "",
      facility_id: "",
      page: 1,
      size: 10,
    },
    inspections: {
      facility_id: "",
      result: "",
      date_from: "",
      date_to: "",
      page: 1,
      size: 10,
    },
    users: { search: "", role: "", is_active: "", page: 1, size: 10 },
    audit: {
      action: "",
      entity: "",
      user_id: "",
      date_from: "",
      date_to: "",
      page: 1,
      size: 15,
    },
  };

  var ICONS = {
    search:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>',
    building:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21h18" /><path d="M5 21V7l7-4 7 4v14" /><path d="M9 9h.01M15 9h.01M9 13h.01M15 13h.01M9 17h.01M15 17h.01" /></svg>',
    license:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M8 9h5M8 13h8M8 17h4" /><circle cx="17" cy="9" r="2" /></svg>',
    clipboard:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1Z" /><path d="M8 6H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-2" /><path d="m9 14 2 2 4-4" /></svg>',
    alert:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.3 4.3 2.8 17a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></svg>',
    x:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>',
    check:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 4 4 10-10" /></svg>',
    info:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></svg>',
  };

  // ------------------------------------------------------------------------
  // State
  // ------------------------------------------------------------------------

  var state = {
    token: readToken(),
    user: null,
    view: "dashboard",
    filters: clone(DEFAULT_FILTERS),
    rows: {},
    facilities: [],
    facilitiesLoaded: false,
    inspectors: [],
    inspectorsLoaded: false,
    health: null,
  };

  var renderSeq = 0;
  var modalHandler = null;

  // ------------------------------------------------------------------------
  // Small helpers
  // ------------------------------------------------------------------------

  var ESCAPES = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };

  function el(id) {
    return document.getElementById(id);
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return ESCAPES[ch];
    });
  }

  function labelize(value) {
    var text = String(value == null ? "" : value).replace(/_/g, " ");
    return text ? text.charAt(0).toUpperCase() + text.slice(1) : "\u2014";
  }

  function readToken() {
    try {
      return window.sessionStorage.getItem(TOKEN_KEY);
    } catch (error) {
      return null;
    }
  }

  function storeToken(token) {
    try {
      if (token) window.sessionStorage.setItem(TOKEN_KEY, token);
      else window.sessionStorage.removeItem(TOKEN_KEY);
    } catch (error) {
      /* Storage may be unavailable; the in-memory session still works. */
    }
  }

  function initials(user) {
    var source = (user && (user.full_name || user.username)) || "?";
    return source
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(function (part) {
        return part.charAt(0);
      })
      .join("")
      .toUpperCase();
  }

  function todayISO() {
    return new Date().toISOString().slice(0, 10);
  }

  function oneYearFromTodayISO() {
    var date = new Date();
    date.setUTCFullYear(date.getUTCFullYear() + 1);
    return date.toISOString().slice(0, 10);
  }

  function parseDate(value) {
    if (typeof value !== "string" || !value) return null;
    var iso = value;
    if (value.length === 10) {
      iso = value + "T00:00:00";
    } else if (
      value.indexOf("T") !== -1 &&
      !/(Z|[+-]\d{2}:?\d{2})$/.test(value)
    ) {
      // API datetimes are naive UTC; make that explicit before parsing.
      iso = value + "Z";
    }
    var date = new Date(iso);
    return isNaN(date.getTime()) ? null : date;
  }

  function localDateTimeToUtc(value) {
    if (!value) return "";
    var date = new Date(value);
    if (isNaN(date.getTime())) return value;
    return date.toISOString().slice(0, 19);
  }

  function formatDate(value) {
    var date = parseDate(value);
    if (!date) return value ? esc(value) : "\u2014";
    return new Intl.DateTimeFormat(undefined, {
      year: "numeric",
      month: "short",
      day: "2-digit",
    }).format(date);
  }

  function formatDateTime(value) {
    var date = parseDate(value);
    if (!date) return value ? esc(value) : "\u2014";
    return new Intl.DateTimeFormat(undefined, {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  function daysUntil(value) {
    var date = parseDate(value);
    if (!date) return null;
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    return Math.round((target.getTime() - today.getTime()) / 86400000);
  }

  function readValue(data, name) {
    var value = data.get(name);
    return typeof value === "string" ? value.trim() : "";
  }

  function statusBadge(value) {
    var safe = String(value == null ? "" : value).replace(/[^a-z0-9_]/gi, "");
    return '<span class="status status-' + safe + '">' + esc(labelize(value)) + "</span>";
  }

  function roleBadge(role) {
    return (
      '<span class="role-badge role-' +
      esc(role) +
      '">' +
      esc(ROLE_LABELS[role] || role) +
      "</span>"
    );
  }

  function facilityName(id) {
    var numeric = Number(id);
    for (var index = 0; index < state.facilities.length; index += 1) {
      if (state.facilities[index].id === numeric) return state.facilities[index].name;
    }
    return "Facility #" + id;
  }

  function optionsHtml(options, selected) {
    return options
      .map(function (option) {
        var value = typeof option === "string" ? option : option.value;
        var label = typeof option === "string" ? labelize(option) : option.label;
        var isSelected =
          selected !== undefined
            ? String(value) === String(selected)
            : Boolean(option && typeof option === "object" && option.selected);
        return (
          '<option value="' +
          esc(value) +
          '"' +
          (isSelected ? " selected" : "") +
          ">" +
          esc(label) +
          "</option>"
        );
      })
      .join("");
  }

  function enumOptions(values, blankLabel) {
    var options = [];
    if (blankLabel !== undefined) options.push({ value: "", label: blankLabel });
    values.forEach(function (value) {
      options.push({ value: value, label: labelize(value) });
    });
    return options;
  }

  function facilityOptions(blankLabel) {
    var options = [{ value: "", label: blankLabel || "Select a facility" }];
    state.facilities.forEach(function (facility) {
      options.push({
        value: String(facility.id),
        label: facility.name + " \u00b7 " + facility.registration_number,
      });
    });
    return options;
  }

  function field(label, name, opts) {
    opts = opts || {};
    var id = "field-" + name;
    var required = opts.required ? " required" : "";
    var full = opts.full ? " field-full" : "";
    var hint = opts.hint ? "<small>" + esc(opts.hint) + "</small>" : "";
    var control;

    if (opts.type === "select") {
      control =
        '<select id="' +
        id +
        '" name="' +
        name +
        '"' +
        required +
        ">" +
        optionsHtml(opts.options || [], opts.value) +
        "</select>";
    } else if (opts.type === "textarea") {
      control =
        '<textarea id="' +
        id +
        '" name="' +
        name +
        '" rows="' +
        (opts.rows || 4) +
        '"' +
        required +
        ' placeholder="' +
        esc(opts.placeholder || "") +
        '">' +
        esc(opts.value || "") +
        "</textarea>";
    } else {
      var attrs = [
        'type="' + (opts.type || "text") + '"',
        'id="' + id + '"',
        'name="' + name + '"',
        'value="' + esc(opts.value == null ? "" : opts.value) + '"',
        required,
        opts.min != null ? 'min="' + esc(opts.min) + '"' : "",
        opts.max != null ? 'max="' + esc(opts.max) + '"' : "",
        opts.minlength != null ? 'minlength="' + opts.minlength + '"' : "",
        opts.maxlength != null ? 'maxlength="' + opts.maxlength + '"' : "",
        opts.pattern ? 'pattern="' + esc(opts.pattern) + '"' : "",
        opts.placeholder ? 'placeholder="' + esc(opts.placeholder) + '"' : "",
        opts.autocomplete ? 'autocomplete="' + esc(opts.autocomplete) + '"' : "",
      ];
      control = "<input " + attrs.filter(Boolean).join(" ") + " />";
    }

    return (
      '<label class="field' +
      full +
      '" for="' +
      id +
      '"><span>' +
      esc(label) +
      (opts.required ? " <em>*</em>" : "") +
      "</span>" +
      control +
      hint +
      "</label>"
    );
  }

  function readonlyField(label, value) {
    return (
      '<div class="field"><span>' +
      esc(label) +
      '</span><div class="readonly-box">' +
      esc(value) +
      "</div></div>"
    );
  }

  // ------------------------------------------------------------------------
  // API client
  // ------------------------------------------------------------------------

  function ApiError(message, status, details) {
    this.name = "ApiError";
    this.message = message;
    this.status = status;
    this.details = details;
  }
  ApiError.prototype = Object.create(Error.prototype);

  function api(path, options) {
    options = options || {};
    var method = options.method || "GET";
    var url = new URL(path, window.location.origin);
    var query = options.query || {};

    Object.keys(query).forEach(function (key) {
      var value = query[key];
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });

    var headers = { Accept: "application/json" };
    if (options.body !== undefined) headers["Content-Type"] = "application/json";
    if (options.auth !== false && state.token) {
      headers.Authorization = "Bearer " + state.token;
    }

    return fetch(url.toString(), {
      method: method,
      headers: headers,
      credentials: "same-origin",
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
      .catch(function () {
        throw new ApiError(
          "Cannot reach the API. Check that the server is running and try again.",
          0
        );
      })
      .then(function (response) {
        if (response.status === 401 && state.token && state.user) {
          expireSession();
          throw new ApiError("Your session expired. Please sign in again.", 401);
        }
        if (response.status === 204) return null;
        return response.text().then(function (text) {
          var data = null;
          if (text) {
            try {
              data = JSON.parse(text);
            } catch (error) {
              data = null;
            }
          }
          if (!response.ok) {
            throw new ApiError(errorMessage(data, response.status), response.status, data);
          }
          return data;
        });
      });
  }

  function errorMessage(data, status) {
    var detail = data && data.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map(function (item) {
          var location = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "";
          return (location ? location + ": " : "") + (item.msg || "Invalid value");
        })
        .join("; ");
    }
    return "Request failed (HTTP " + status + ").";
  }

  // ------------------------------------------------------------------------
  // Session
  // ------------------------------------------------------------------------

  function setSession(token, user) {
    state.token = token;
    state.user = user;
    storeToken(token);
  }

  function clearSession() {
    state.token = null;
    state.user = null;
    state.filters = clone(DEFAULT_FILTERS);
    state.rows = {};
    state.facilities = [];
    state.facilitiesLoaded = false;
    state.inspectors = [];
    state.inspectorsLoaded = false;
    storeToken(null);
    clearToasts();
  }

  function clearToasts() {
    var root = el("toast-root");
    if (root) root.textContent = "";
  }

  function expireSession() {
    if (!state.token && !state.user) return;
    clearSession();
    showLogin("Your session expired. Please sign in again.", "warning");
  }

  // ------------------------------------------------------------------------
  // Boot and chrome
  // ------------------------------------------------------------------------

  function init() {
    bindEvents();
    if (IS_STATIC_PREVIEW) {
      showLogin(
        "This is the static GitHub Pages preview. The console signs in to the API " +
          "when this page is served by the FastAPI app; deploy the API and open its " +
          "root URL to use the GUI.",
        "warning"
      );
      return;
    }
    if (state.token) {
      restoreSession();
    } else {
      showLogin();
    }
  }

  function restoreSession() {
    api("/users/me")
      .then(function (user) {
        state.user = user;
        enterApp();
      })
      .catch(function () {
        clearSession();
        showLogin();
      });
  }

  function showLogin(message, kind) {
    state.user = null;
    closeModal();
    closeSidebar();
    el("app-view").hidden = true;
    el("login-view").hidden = false;
    document.title = "Regulatory License & Inspection Tracking API";

    var notice = el("login-notice");
    if (message) {
      notice.textContent = message;
      notice.className = "notice" + (kind === "warning" ? " notice-warning" : "");
      notice.hidden = false;
    } else {
      notice.hidden = true;
    }

    var form = el("login-form");
    if (form) form.reset();
    el("login-error").hidden = true;
    el("login-error").textContent = "";

    var submit = el("login-submit");
    submit.disabled = IS_STATIC_PREVIEW;
    submit.textContent = IS_STATIC_PREVIEW ? "Console requires the API" : "Sign in to console";

    checkHealth();
  }

  function enterApp() {
    el("login-view").hidden = true;
    el("app-view").hidden = false;
    applyRoleVisibility();
    updateUserChrome();
    renderView(parseHash());
    checkHealth();
  }

  function applyRoleVisibility() {
    var role = state.user ? state.user.role : "viewer";
    var nodes = document.querySelectorAll("[data-roles]");
    Array.prototype.forEach.call(nodes, function (node) {
      var roles = String(node.getAttribute("data-roles") || "").split(",");
      node.hidden = roles.indexOf(role) === -1;
    });
  }

  function updateUserChrome() {
    if (!state.user) return;
    var name = state.user.full_name || state.user.username;
    el("user-name").textContent = name;
    el("user-avatar").textContent = initials(state.user);
    var role = el("user-role");
    role.textContent = ROLE_LABELS[state.user.role] || state.user.role;
    role.className = "role-badge role-" + state.user.role;
  }

  function updateChrome() {
    var meta = NAV_META[state.view] || NAV_META.dashboard;
    el("view-eyebrow").textContent = meta.eyebrow;
    el("view-title").textContent = meta.title;
    document.title = meta.title + " \u00b7 License & Inspection Console";

    var navItems = document.querySelectorAll("[data-view]");
    Array.prototype.forEach.call(navItems, function (node) {
      node.classList.toggle("is-active", node.getAttribute("data-view") === state.view);
    });
    updateUserChrome();
  }

  function setApiStatus(kind, text, version) {
    ["login-status", "app-status"].forEach(function (id) {
      var node = el(id);
      if (!node) return;
      node.className = "badge badge-" + kind;
      node.textContent = text;
    });
    var versionNode = el("login-version");
    if (versionNode) versionNode.textContent = version ? "v" + version : "";
  }

  function checkHealth() {
    if (IS_STATIC_PREVIEW) {
      setApiStatus("pending", "Static preview");
      return;
    }
    fetch("/health", { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("unhealthy");
        return response.json();
      })
      .then(function (data) {
        state.health = data;
        if (data && data.database === "ok") {
          setApiStatus("ok", "API online", data.version);
        } else {
          setApiStatus("pending", "API degraded", data && data.version);
        }
      })
      .catch(function () {
        state.health = null;
        setApiStatus("bad", "API unreachable");
      });
  }

  // ------------------------------------------------------------------------
  // Routing and sidebar
  // ------------------------------------------------------------------------

  function parseHash() {
    var view = window.location.hash.replace(/^#\/?/, "").trim();
    return Object.prototype.hasOwnProperty.call(NAV_META, view) ? view : "dashboard";
  }

  function canAccess(view) {
    var meta = NAV_META[view];
    return Boolean(meta && meta.roles.indexOf(state.user.role) !== -1);
  }

  function navigate(view) {
    if (!state.user) return;
    if (!canAccess(view)) view = "dashboard";
    closeSidebar();
    if (parseHash() === view) renderView(view);
    else window.location.hash = "#/" + view;
  }

  function onHashChange() {
    if (!state.user) return;
    var view = parseHash();
    if (view !== state.view) renderView(view);
  }

  function toggleSidebar(open) {
    var sidebar = el("sidebar");
    if (!sidebar) return;
    sidebar.classList.toggle("is-open", open);
    el("sidebar-backdrop").hidden = !open;
    el("menu-button").setAttribute("aria-expanded", String(open));
  }

  function closeSidebar() {
    toggleSidebar(false);
  }

  // ------------------------------------------------------------------------
  // View rendering
  // ------------------------------------------------------------------------

  async function renderView(view) {
    if (!state.user) return;
    if (!canAccess(view)) {
      view = "dashboard";
      if (parseHash() !== "dashboard") {
        window.history.replaceState(null, "", "#/dashboard");
      }
    }

    state.view = view;
    updateChrome();
    var root = el("content");
    var seq = ++renderSeq;
    root.innerHTML = loadingState("Loading " + (NAV_META[view].title || "console").toLowerCase() + "\u2026");

    try {
      switch (view) {
        case "facilities":
          await renderFacilities(root, seq);
          break;
        case "licenses":
          await renderLicenses(root, seq);
          break;
        case "inspections":
          await renderInspections(root, seq);
          break;
        case "users":
          await renderUsers(root, seq);
          break;
        case "audit":
          await renderAudit(root, seq);
          break;
        case "profile":
          await renderProfile(root, seq);
          break;
        case "about":
          renderAbout(root, seq);
          break;
        default:
          await renderDashboard(root, seq);
      }
    } catch (error) {
      if (seq !== renderSeq || !state.user) return;
      root.innerHTML = errorState(error);
    }
  }

  function loadingState(label) {
    return (
      '<div class="state"><span class="spinner" aria-hidden="true"></span><p>' +
      esc(label) +
      "</p></div>"
    );
  }

  function errorState(error) {
    return (
      '<div class="state state-error"><h2>Could not load this view</h2><p>' +
      esc((error && error.message) || "An unexpected error occurred.") +
      '</p><button class="btn" type="button" data-action="refresh">Try again</button></div>'
    );
  }

  function emptyRow(colspan, title, text) {
    return (
      '<tr><td colspan="' +
      colspan +
      '"><div class="empty"><strong>' +
      esc(title) +
      "</strong>" +
      esc(text) +
      "</div></td></tr>"
    );
  }

  function pager(data) {
    var total = data.total || 0;
    var pages = Math.max(data.pages || 0, 1);
    var from = total === 0 ? 0 : (data.page - 1) * data.size + 1;
    var to = Math.min(data.page * data.size, total);
    return (
      '<div class="pager"><span class="pager-info">' +
      from +
      "\u2013" +
      to +
      " of " +
      total +
      '</span><div class="pager-controls">' +
      '<button class="btn btn-sm" type="button" data-action="page" data-page="' +
      (data.page - 1) +
      '"' +
      (data.page <= 1 ? " disabled" : "") +
      ">Previous</button>" +
      '<span class="pager-page">Page ' +
      data.page +
      " of " +
      pages +
      "</span>" +
      '<button class="btn btn-sm" type="button" data-action="page" data-page="' +
      (data.page + 1) +
      '"' +
      (data.page >= data.pages ? " disabled" : "") +
      ">Next</button></div></div>"
    );
  }

  function statCard(label, value, tone, icon) {
    return (
      '<article class="stat"><span class="stat-icon' +
      (tone ? " is-" + tone : "") +
      '">' +
      (ICONS[icon] || ICONS.info) +
      '</span><div class="stat-value">' +
      esc(value) +
      '</div><div class="stat-label">' +
      esc(label) +
      "</div></article>"
    );
  }

  function greeting() {
    var hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }

  function firstName() {
    if (!state.user) return "";
    var source = state.user.full_name || state.user.username;
    return source.split(/\s+/)[0];
  }

  function roleSummary() {
    if (!state.user) return "";
    if (state.user.role === "admin") {
      return "Full access to facilities, licenses, inspections, users and the audit trail.";
    }
    if (state.user.role === "inspector") {
      return "Record inspections and maintain the records you own; registry data is read-only.";
    }
    return "Read-only access to facilities, licenses and inspection records.";
  }

  function quickActionsHtml() {
    if (!state.user) return "";
    var buttons = [];
    if (state.user.role === "admin") {
      buttons.push('<button class="btn btn-primary" type="button" data-action="new-facility">+ Facility</button>');
      buttons.push('<button class="btn" type="button" data-action="new-license">+ License</button>');
      buttons.push('<button class="btn" type="button" data-action="new-inspection">+ Inspection</button>');
      buttons.push('<button class="btn" type="button" data-action="new-user">+ User</button>');
    } else if (state.user.role === "inspector") {
      buttons.push('<button class="btn btn-primary" type="button" data-action="new-inspection">+ New inspection</button>');
    }
    return buttons.join("");
  }

  // ------------------------------------------------------------------------
  // Dashboard
  // ------------------------------------------------------------------------

  async function renderDashboard(root, seq) {
    await loadFacilityLookup();

    var results = await Promise.all([
      api("/facilities", { query: { size: 1 } }),
      api("/licenses", { query: { size: 1, status: "active" } }),
      api("/licenses", { query: { size: 1, expired: "true" } }),
      api("/inspections", { query: { size: 1 } }),
      api("/inspections", { query: { size: 1, result: "non_compliant" } }),
      api("/inspections", { query: { size: 5 } }),
      api("/licenses", { query: { size: 100, expired: "false" } }),
    ]);

    if (seq !== renderSeq || state.view !== "dashboard") return;

    var facilities = results[0];
    var activeLicenses = results[1];
    var expiredLicenses = results[2];
    var inspections = results[3];
    var nonCompliant = results[4];
    var recent = results[5];
    var licenseList = results[6];

    var mine = null;
    if (state.user.role !== "viewer") {
      mine = await api("/inspections", { query: { size: 1, inspector_id: state.user.id } });
      if (seq !== renderSeq || state.view !== "dashboard") return;
    }

    var expiring = (licenseList.items || [])
      .map(function (license) {
        return { license: license, days: daysUntil(license.expiry_date) };
      })
      .filter(function (entry) {
        return entry.days !== null && entry.days >= 0 && entry.days <= 30;
      })
      .sort(function (a, b) {
        return a.days - b.days;
      })
      .slice(0, 5);

    var stats =
      statCard("Facilities", facilities.total, "", "building") +
      statCard("Active licenses", activeLicenses.total, "mint", "license") +
      statCard("Expired licenses", expiredLicenses.total, "danger", "alert") +
      statCard("Inspections", inspections.total, "", "clipboard") +
      statCard("Non-compliant", nonCompliant.total, "amber", "alert");
    if (mine) stats += statCard("My inspections", mine.total, "mint", "check");

    var recentRows = (recent.items || []).length
      ? recent.items
          .map(function (inspection) {
            return (
              "<tr><td class=\"nowrap\">" +
              formatDate(inspection.inspection_date) +
              '</td><td><div class="cell-primary">' +
              esc(facilityName(inspection.facility_id)) +
              '</div></td><td>' +
              statusBadge(inspection.result) +
              '</td><td class="cell-muted">' +
              esc(inspection.inspector_username || "\u2014") +
              "</td></tr>"
            );
          })
          .join("")
      : emptyRow(4, "No inspections yet", "Recorded inspections will appear here.");

    var expiringHtml = expiring.length
      ? expiring
          .map(function (entry) {
            var license = entry.license;
            return (
              '<div class="list-item"><div class="list-main"><strong>' +
              esc(license.license_number) +
              "</strong><span>" +
              esc(facilityName(license.facility_id)) +
              " \u00b7 expires " +
              formatDate(license.expiry_date) +
              '</span></div><span class="days-badge' +
              (entry.days <= 7 ? " is-urgent" : "") +
              '">' +
              (entry.days === 0 ? "Today" : entry.days + "d") +
              "</span></div>"
            );
          })
          .join("")
      : '<div class="empty"><strong>All clear</strong>No licenses expire in the next 30 days.</div>';

    var actions = quickActionsHtml();

    root.innerHTML =
      '<section class="welcome"><div><p class="eyebrow">Welcome back</p><h2>' +
      esc(greeting() + ", " + firstName() + ".") +
      "</h2><p>" +
      esc(roleSummary()) +
      "</p></div>" +
      (actions ? '<div class="welcome-actions">' + actions + "</div>" : "") +
      '</section><div class="stat-grid">' +
      stats +
      '</div><div class="dashboard-grid"><section class="panel"><div class="panel-head"><div><h2>Recent inspections</h2><p>Latest compliance activity</p></div><button class="panel-link" type="button" data-action="go" data-target="inspections">View all</button></div><div class="table-wrap"><table class="data-table compact-table"><thead><tr><th>Date</th><th>Facility</th><th>Result</th><th>Inspector</th></tr></thead><tbody>' +
      recentRows +
      '</tbody></table></div></section><section class="panel"><div class="panel-head"><div><h2>Expiring soon</h2><p>Licenses due within 30 days</p></div><button class="panel-link" type="button" data-action="go" data-target="licenses">View all</button></div><div class="list">' +
      expiringHtml +
      "</div></section></div>";
  }

  // ------------------------------------------------------------------------
  // Lookups
  // ------------------------------------------------------------------------

  async function loadFacilityLookup(force) {
    if (state.facilitiesLoaded && !force) return state.facilities;
    var data = await api("/facilities", { query: { size: 100 } });
    state.facilities = data.items || [];
    state.facilitiesLoaded = true;
    return state.facilities;
  }

  async function loadInspectorLookup(force) {
    if (state.inspectorsLoaded && !force) return state.inspectors;
    var data = await api("/users", {
      query: { size: 100, role: "inspector", is_active: "true" },
    });
    state.inspectors = data.items || [];
    state.inspectorsLoaded = true;
    return state.inspectors;
  }

  // ------------------------------------------------------------------------
  // Facilities
  // ------------------------------------------------------------------------

  async function renderFacilities(root, seq) {
    await loadFacilityLookup();
    var filters = state.filters.facilities;
    var data = await api("/facilities", {
      query: {
        page: filters.page,
        size: filters.size,
        search: filters.search,
        status: filters.status,
      },
    });
    if (seq !== renderSeq || state.view !== "facilities") return;

    state.rows.facilities = data.items || [];
    var canEdit = state.user.role === "admin";

    var rows = state.rows.facilities.length
      ? state.rows.facilities
          .map(function (facility) {
            var actions = canEdit
              ? '<button class="btn btn-sm" type="button" data-action="edit-facility" data-id="' +
                facility.id +
                '">Edit</button><button class="btn btn-sm btn-danger-ghost" type="button" data-action="delete-facility" data-id="' +
                facility.id +
                '">Delete</button>'
              : '<span class="cell-muted">\u2014</span>';
            return (
              "<tr><td><div class=\"cell-primary\">" +
              esc(facility.name) +
              '</div><div class="cell-sub">#' +
              facility.id +
              " \u00b7 " +
              esc(facility.address) +
              '</div></td><td><code>' +
              esc(facility.registration_number) +
              "</code></td><td>" +
              statusBadge(facility.status) +
              '</td><td class="cell-muted">' +
              formatDateTime(facility.updated_at || facility.created_at) +
              '</td><td class="cell-actions">' +
              actions +
              "</td></tr>"
            );
          })
          .join("")
      : emptyRow(
          5,
          "No facilities found",
          canEdit ? "Create the first facility to get started." : "No facilities match this filter."
        );

    root.innerHTML =
      '<section class="panel"><form class="toolbar" data-filter="facilities" role="search"><div class="toolbar-fields"><label class="search-field">' +
      ICONS.search +
      '<input name="search" type="search" autocomplete="off" placeholder="Search name or registration\u2026" aria-label="Search facilities" value="' +
      esc(filters.search) +
      '" /></label><select name="status" aria-label="Filter by status">' +
      optionsHtml(enumOptions(FACILITY_STATUSES, "All statuses"), filters.status) +
      '</select><button class="btn" type="submit">Apply</button><button class="ghost-button" type="button" data-action="reset-filters" data-filter="facilities">Reset</button></div>' +
      (canEdit
        ? '<button class="btn btn-primary" type="button" data-action="new-facility">+ New facility</button>'
        : "") +
      '</form><div class="table-wrap"><table class="data-table"><thead><tr><th>Facility</th><th>Registration</th><th>Status</th><th>Updated</th><th class="cell-actions">Actions</th></tr></thead><tbody>' +
      rows +
      "</tbody></table></div>" +
      pager(data) +
      "</section>";
  }

  // ------------------------------------------------------------------------
  // Licenses
  // ------------------------------------------------------------------------

  async function renderLicenses(root, seq) {
    await loadFacilityLookup();
    var filters = state.filters.licenses;
    var data = await api("/licenses", {
      query: {
        page: filters.page,
        size: filters.size,
        search: filters.search,
        status: filters.status,
        type: filters.type,
        expired: filters.expired,
        facility_id: filters.facility_id,
      },
    });
    if (seq !== renderSeq || state.view !== "licenses") return;

    state.rows.licenses = data.items || [];
    var canEdit = state.user.role === "admin";
    var facilityFilter = [{ value: "", label: "All facilities" }].concat(
      state.facilities.map(function (facility) {
        return { value: String(facility.id), label: facility.name };
      })
    );

    var rows = state.rows.licenses.length
      ? state.rows.licenses
          .map(function (license) {
            var actions = canEdit
              ? '<button class="btn btn-sm" type="button" data-action="edit-license" data-id="' +
                license.id +
                '">Edit</button><button class="btn btn-sm btn-danger-ghost" type="button" data-action="delete-license" data-id="' +
                license.id +
                '">Delete</button>'
              : '<span class="cell-muted">\u2014</span>';
            return (
              "<tr><td><div class=\"cell-primary\">" +
              esc(license.license_number) +
              '</div><div class="cell-sub">#' +
              license.id +
              " \u00b7 " +
              esc(labelize(license.type)) +
              '</div></td><td><div class="cell-primary">' +
              esc(facilityName(license.facility_id)) +
              '</div><div class="cell-sub">Facility #' +
              license.facility_id +
              '</div></td><td class="nowrap">' +
              formatDate(license.issue_date) +
              ' <span class="muted">\u2192</span> ' +
              formatDate(license.expiry_date) +
              '</td><td><div class="badge-row">' +
              statusBadge(license.status) +
              (license.is_expired ? statusBadge("expired") : "") +
              '</div></td><td class="cell-actions">' +
              actions +
              "</td></tr>"
            );
          })
          .join("")
      : emptyRow(
          5,
          "No licenses found",
          canEdit ? "Issue a license to get started." : "No licenses match this filter."
        );

    root.innerHTML =
      '<section class="panel"><form class="toolbar" data-filter="licenses" role="search"><div class="toolbar-fields"><label class="search-field">' +
      ICONS.search +
      '<input name="search" type="search" autocomplete="off" placeholder="Search license number\u2026" aria-label="Search licenses" value="' +
      esc(filters.search) +
      '" /></label><select name="facility_id" aria-label="Filter by facility">' +
      optionsHtml(facilityFilter, filters.facility_id) +
      '</select><select name="status" aria-label="Filter by status">' +
      optionsHtml(enumOptions(LICENSE_STATUSES, "All statuses"), filters.status) +
      '</select><select name="type" aria-label="Filter by type">' +
      optionsHtml(enumOptions(LICENSE_TYPES, "All types"), filters.type) +
      '</select><select name="expired" aria-label="Filter by expiry">' +
      optionsHtml(
        [
          { value: "", label: "Any expiry" },
          { value: "false", label: "Not expired" },
          { value: "true", label: "Expired" },
        ],
        filters.expired
      ) +
      '</select><button class="btn" type="submit">Apply</button><button class="ghost-button" type="button" data-action="reset-filters" data-filter="licenses">Reset</button></div>' +
      (canEdit
        ? '<button class="btn btn-primary" type="button" data-action="new-license">+ New license</button>'
        : "") +
      '</form><div class="table-wrap"><table class="data-table"><thead><tr><th>License</th><th>Facility</th><th>Term</th><th>Status</th><th class="cell-actions">Actions</th></tr></thead><tbody>' +
      rows +
      "</tbody></table></div>" +
      pager(data) +
      "</section>";
  }

  // ------------------------------------------------------------------------
  // Inspections
  // ------------------------------------------------------------------------

  async function renderInspections(root, seq) {
    await loadFacilityLookup();
    var filters = state.filters.inspections;
    var data = await api("/inspections", {
      query: {
        page: filters.page,
        size: filters.size,
        facility_id: filters.facility_id,
        result: filters.result,
        date_from: filters.date_from,
        date_to: filters.date_to,
      },
    });
    if (seq !== renderSeq || state.view !== "inspections") return;

    state.rows.inspections = data.items || [];
    var canCreate = state.user.role === "admin" || state.user.role === "inspector";
    var facilityFilter = [{ value: "", label: "All facilities" }].concat(
      state.facilities.map(function (facility) {
        return { value: String(facility.id), label: facility.name };
      })
    );

    var rows = state.rows.inspections.length
      ? state.rows.inspections
          .map(function (inspection) {
            var canEdit =
              state.user.role === "admin" || inspection.inspector_id === state.user.id;
            var actions = canEdit
              ? '<button class="btn btn-sm" type="button" data-action="edit-inspection" data-id="' +
                inspection.id +
                '">Edit</button>'
              : '<span class="cell-muted">\u2014</span>';
            var notes = inspection.notes
              ? '<div class="cell-sub" title="' + esc(inspection.notes) + '">' + esc(inspection.notes) + "</div>"
              : '<span class="cell-muted">\u2014</span>';
            return (
              '<tr><td class="nowrap"><div class="cell-primary">' +
              formatDate(inspection.inspection_date) +
              '</div><div class="cell-sub">#' +
              inspection.id +
              '</div></td><td><div class="cell-primary">' +
              esc(facilityName(inspection.facility_id)) +
              '</div><div class="cell-sub">Facility #' +
              inspection.facility_id +
              '</div></td><td class="cell-muted">' +
              esc(inspection.inspector_username || "Inspector #" + inspection.inspector_id) +
              "</td><td>" +
              statusBadge(inspection.result) +
              '</td><td class="cell-notes">' +
              notes +
              '</td><td class="cell-actions">' +
              actions +
              "</td></tr>"
            );
          })
          .join("")
      : emptyRow(
          6,
          "No inspections found",
          canCreate ? "Record an inspection to get started." : "No inspections match this filter."
        );

    root.innerHTML =
      '<section class="panel"><form class="toolbar" data-filter="inspections" role="search"><div class="toolbar-fields"><select name="facility_id" aria-label="Filter by facility">' +
      optionsHtml(facilityFilter, filters.facility_id) +
      '</select><select name="result" aria-label="Filter by result">' +
      optionsHtml(enumOptions(INSPECTION_RESULTS, "All results"), filters.result) +
      '</select><input type="date" name="date_from" aria-label="From date" value="' +
      esc(filters.date_from) +
      '" /><input type="date" name="date_to" aria-label="To date" value="' +
      esc(filters.date_to) +
      '" /><button class="btn" type="submit">Apply</button><button class="ghost-button" type="button" data-action="reset-filters" data-filter="inspections">Reset</button></div>' +
      (canCreate
        ? '<button class="btn btn-primary" type="button" data-action="new-inspection">+ New inspection</button>'
        : "") +
      '</form><div class="table-wrap"><table class="data-table"><thead><tr><th>Date</th><th>Facility</th><th>Inspector</th><th>Result</th><th>Notes</th><th class="cell-actions">Actions</th></tr></thead><tbody>' +
      rows +
      "</tbody></table></div>" +
      pager(data) +
      "</section>";
  }

  // ------------------------------------------------------------------------
  // Users (admin only)
  // ------------------------------------------------------------------------

  async function renderUsers(root, seq) {
    var filters = state.filters.users;
    var data = await api("/users", {
      query: {
        page: filters.page,
        size: filters.size,
        search: filters.search,
        role: filters.role,
        is_active: filters.is_active,
      },
    });
    if (seq !== renderSeq || state.view !== "users") return;

    state.rows.users = data.items || [];

    var rows = state.rows.users.length
      ? state.rows.users
          .map(function (user) {
            var isSelf = user.id === state.user.id;
            var actions =
              '<button class="btn btn-sm" type="button" data-action="edit-user" data-id="' +
              user.id +
              '">Edit</button>' +
              (user.is_active && !isSelf
                ? '<button class="btn btn-sm btn-danger-ghost" type="button" data-action="deactivate-user" data-id="' +
                  user.id +
                  '">Deactivate</button>'
                : "");
            return (
              "<tr><td><div class=\"cell-primary\">" +
              esc(user.username) +
              (isSelf ? ' <span class="muted">(you)</span>' : "") +
              '</div><div class="cell-sub">#' +
              user.id +
              " \u00b7 " +
              esc(user.full_name || "No full name") +
              '</div></td><td>' +
              roleBadge(user.role) +
              '</td><td><div class="badge-row">' +
              statusBadge(user.is_active ? "active" : "inactive") +
              '</div></td><td class="cell-muted">' +
              formatDateTime(user.last_login_at) +
              '</td><td class="cell-muted">' +
              formatDate(user.created_at) +
              '</td><td class="cell-actions">' +
              actions +
              "</td></tr>"
            );
          })
          .join("")
      : emptyRow(6, "No users found", "No accounts match this filter.");

    root.innerHTML =
      '<section class="panel"><form class="toolbar" data-filter="users" role="search"><div class="toolbar-fields"><label class="search-field">' +
      ICONS.search +
      '<input name="search" type="search" autocomplete="off" placeholder="Search username or name\u2026" aria-label="Search users" value="' +
      esc(filters.search) +
      '" /></label><select name="role" aria-label="Filter by role">' +
      optionsHtml(enumOptions(ROLES, "All roles"), filters.role) +
      '</select><select name="is_active" aria-label="Filter by status">' +
      optionsHtml(
        [
          { value: "", label: "Any status" },
          { value: "true", label: "Active" },
          { value: "false", label: "Inactive" },
        ],
        filters.is_active
      ) +
      '</select><button class="btn" type="submit">Apply</button><button class="ghost-button" type="button" data-action="reset-filters" data-filter="users">Reset</button></div><button class="btn btn-primary" type="button" data-action="new-user">+ New user</button></form><div class="table-wrap"><table class="data-table"><thead><tr><th>User</th><th>Role</th><th>Status</th><th>Last login</th><th>Created</th><th class="cell-actions">Actions</th></tr></thead><tbody>' +
      rows +
      "</tbody></table></div>" +
      pager(data) +
      "</section>";
  }

  // ------------------------------------------------------------------------
  // Audit log (admin only)
  // ------------------------------------------------------------------------

  async function renderAudit(root, seq) {
    var filters = state.filters.audit;
    var data = await api("/audit-logs", {
      query: {
        page: filters.page,
        size: filters.size,
        action: filters.action,
        entity: filters.entity,
        user_id: filters.user_id,
        date_from: localDateTimeToUtc(filters.date_from),
        date_to: localDateTimeToUtc(filters.date_to),
      },
    });
    if (seq !== renderSeq || state.view !== "audit") return;

    state.rows.audit = data.items || [];

    var rows = state.rows.audit.length
      ? state.rows.audit
          .map(function (entry) {
            var actor = entry.username
              ? entry.username
              : entry.user_id
                ? "User #" + entry.user_id
                : "system";
            var entity =
              esc(entry.entity) + (entry.entity_id ? ' <span class="muted">#' + entry.entity_id + "</span>" : "");
            return (
              '<tr><td class="nowrap"><div class="cell-primary">' +
              formatDateTime(entry.timestamp) +
              '</div><div class="cell-sub">#' +
              entry.id +
              '</div></td><td class="cell-muted">' +
              esc(actor) +
              '</td><td><span class="mono">' +
              esc(entry.action) +
              "</span></td><td>" +
              entity +
              '</td><td class="cell-notes">' +
              (entry.details
                ? '<div class="cell-sub" title="' + esc(entry.details) + '">' + esc(entry.details) + "</div>"
                : '<span class="cell-muted">\u2014</span>') +
              '</td><td class="mono cell-muted">' +
              esc(entry.ip_address || "\u2014") +
              "</td></tr>"
            );
          })
          .join("")
      : emptyRow(6, "No audit entries", "Security-relevant events will appear here.");

    root.innerHTML =
      '<section class="panel"><form class="toolbar" data-filter="audit" role="search"><div class="toolbar-fields"><select name="action" aria-label="Filter by action">' +
      optionsHtml(enumOptions(AUDIT_ACTIONS, "All actions"), filters.action) +
      '</select><input type="text" name="entity" placeholder="Entity (e.g. facility)" aria-label="Filter by entity" value="' +
      esc(filters.entity) +
      '" /><input type="number" name="user_id" min="1" placeholder="User ID" aria-label="Filter by user ID" value="' +
      esc(filters.user_id) +
      '" /><input type="datetime-local" name="date_from" aria-label="From timestamp" value="' +
      esc(filters.date_from) +
      '" /><input type="datetime-local" name="date_to" aria-label="To timestamp" value="' +
      esc(filters.date_to) +
      '" /><button class="btn" type="submit">Apply</button><button class="ghost-button" type="button" data-action="reset-filters" data-filter="audit">Reset</button></div></form><div class="table-wrap"><table class="data-table"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Entity</th><th>Details</th><th>IP</th></tr></thead><tbody>' +
      rows +
      "</tbody></table></div>" +
      pager(data) +
      "</section>";
  }

  // ------------------------------------------------------------------------
  // Profile
  // ------------------------------------------------------------------------

  async function renderProfile(root, seq, presetUser) {
    var user = presetUser || (await api("/users/me"));
    if (seq !== renderSeq || state.view !== "profile") return;

    state.user = user;
    updateUserChrome();

    root.innerHTML =
      '<div class="profile-grid"><section class="panel"><div class="panel-head"><div><h2>Account</h2><p>Identity and access</p></div>' +
      roleBadge(user.role) +
      '</div><div class="panel-body"><div class="detail-grid">' +
      '<div class="detail-item"><span>Username</span><strong>' +
      esc(user.username) +
      "</strong></div>" +
      '<div class="detail-item"><span>Full name</span><strong>' +
      esc(user.full_name || "\u2014") +
      "</strong></div>" +
      '<div class="detail-item"><span>Status</span><strong>' +
      (user.is_active ? "Active" : "Inactive") +
      "</strong></div>" +
      '<div class="detail-item"><span>Last login</span><strong>' +
      formatDateTime(user.last_login_at) +
      "</strong></div>" +
      '<div class="detail-item"><span>Member since</span><strong>' +
      formatDate(user.created_at) +
      "</strong></div>" +
      '<div class="detail-item"><span>User ID</span><strong>#' +
      user.id +
      "</strong></div>" +
      '</div></div></section><section class="panel"><div class="panel-head"><div><h2>Update profile</h2><p>Change your display name or password</p></div></div><div class="panel-body"><form id="profile-form" class="stack" novalidate><div class="form-grid">' +
      field("Full name", "full_name", {
        value: user.full_name || "",
        maxlength: 120,
        full: true,
        placeholder: "Your display name",
      }) +
      '</div><p class="muted">Leave the password fields empty to keep your current password.</p><div class="form-grid">' +
      field("Current password", "current_password", {
        type: "password",
        autocomplete: "current-password",
      }) +
      field("New password", "new_password", {
        type: "password",
        autocomplete: "new-password",
        minlength: 12,
        hint: "At least 12 characters with upper, lower, digit and symbol.",
      }) +
      field("Confirm new password", "confirm_password", {
        type: "password",
        autocomplete: "new-password",
        full: true,
      }) +
      '</div><p id="profile-error" class="form-error" role="alert" hidden></p><div><button class="btn btn-primary" type="submit">Save profile</button></div></form></div></section></div>';

    var form = root.querySelector("#profile-form");
    if (form) {
      form.addEventListener("submit", function (event) {
        saveProfile(event, root);
      });
    }
  }

  async function saveProfile(event, root) {
    event.preventDefault();
    var form = event.currentTarget;
    if (!form.reportValidity()) return;

    var data = new FormData(form);
    var fullName = readValue(data, "full_name");
    var currentPassword = readValue(data, "current_password");
    var newPassword = readValue(data, "new_password");
    var confirmPassword = readValue(data, "confirm_password");
    var errorBox = root.querySelector("#profile-error");
    errorBox.hidden = true;

    if (currentPassword || newPassword || confirmPassword) {
      if (!currentPassword) {
        showProfileError(errorBox, "Enter your current password to set a new one.");
        return;
      }
      if (newPassword.length < 12) {
        showProfileError(errorBox, "The new password must be at least 12 characters.");
        return;
      }
      if (newPassword !== confirmPassword) {
        showProfileError(errorBox, "The new passwords do not match.");
        return;
      }
    }

    var body = { full_name: fullName || null };
    if (newPassword) {
      body.current_password = currentPassword;
      body.new_password = newPassword;
    }

    var button = form.querySelector('button[type="submit"]');
    var label = button.textContent;
    button.disabled = true;
    button.textContent = "Saving\u2026";
    try {
      var updated = await api("/users/me", { method: "PUT", body: body });
      if (!state.user) return;
      state.user = updated;
      updateUserChrome();
      toast("Profile updated.");
      if (state.view === "profile") {
        renderProfile(root, ++renderSeq, updated);
      }
    } catch (error) {
      showProfileError(errorBox, error.message || "Could not update the profile.");
      button.disabled = false;
      button.textContent = label;
    }
  }

  function showProfileError(errorBox, message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  // ------------------------------------------------------------------------
  // About
  // ------------------------------------------------------------------------

  function renderAbout(root, seq) {
    if (seq !== renderSeq || state.view !== "about") return;

    root.innerHTML =
      '<section class="welcome"><div><p class="eyebrow">Project</p><h2>Regulatory License &amp; Inspection Tracking API</h2><p>A secure REST API and this role-aware console for regulated facilities, operating licenses and compliance inspections. All demo data is fictional.</p></div><div class="welcome-actions"><a class="btn btn-primary" href="' +
      GITHUB_URL +
      '" target="_blank" rel="noopener">View source</a><a class="btn" href="' +
      OPENAPI_URL +
      '" target="_blank" rel="noopener">openapi.json</a></div></section>' +
      '<section class="panel"><div class="panel-head"><div><h2>What you can do</h2><p>Everything is enforced by the API, not just hidden in the UI</p></div></div><div class="panel-body"><div class="about-grid">' +
      '<article class="about-card"><h3>Facilities</h3><p>Register regulated facilities with registration numbers, addresses and status.</p><code>GET /facilities</code></article>' +
      '<article class="about-card"><h3>Licenses</h3><p>Issue and track operating licenses with issue and expiry dates.</p><code>GET /licenses</code></article>' +
      '<article class="about-card"><h3>Inspections</h3><p>Record compliance inspections, findings and inspector attribution.</p><code>GET /inspections</code></article>' +
      '<article class="about-card"><h3>Audit logs</h3><p>Trace logins, permission denials and data changes (Admin only).</p><code>GET /audit-logs</code></article>' +
      '</div></div></section>' +
      '<section class="panel"><div class="panel-head"><div><h2>Roles &amp; permissions</h2><p>Object-level checks run on every request</p></div></div><div class="panel-body"><table class="roles-table"><thead><tr><th>Role</th><th>Capability</th></tr></thead><tbody>' +
      "<tr><td>" +
      roleBadge("admin") +
      "</td><td>Full access to every resource, user administration and the audit log.</td></tr>" +
      "<tr><td>" +
      roleBadge("inspector") +
      "</td><td>Create inspections and update only the records they own.</td></tr>" +
      "<tr><td>" +
      roleBadge("viewer") +
      "</td><td>Read-only access to facilities, licenses and inspections.</td></tr>" +
      '</tbody></table></div></section>' +
      '<section class="panel"><div class="panel-head"><div><h2>Quick start</h2><p>Authenticate and call the API directly</p></div></div><div class="panel-body"><pre class="code-block"><code>curl -X POST "$BASE_URL/auth/login" \\\n  -H "Content-Type: application/json" \\\n  -d \'{"username":"admin","password":"YourPassword"}\'</code></pre><p class="muted">Use the returned <code>access_token</code> as a Bearer token on every protected endpoint. Swagger is disabled by default; set <code>DOCS_ENABLED=true</code> to expose <code>/docs</code> and <code>/openapi.json</code>.</p></div></section>' +
      '<section class="panel"><div class="panel-head"><div><h2>Security by design</h2><p>Hardening applied by the API</p></div></div><div class="panel-body"><ul class="feature-list">' +
      "<li>JWT access tokens with issuer, audience and expiry validation</li>" +
      "<li>Explicit token revocation on logout (denylist until expiry)</li>" +
      "<li>Argon2id password hashing and a password complexity policy</li>" +
      "<li>Role-based access control and object-level authorization</li>" +
      "<li>SQL-injection-safe parameterized ORM queries</li>" +
      "<li>Security headers, CSP, HSTS, CORS and trusted-host controls</li>" +
      "<li>Login rate limiting and append-only audit logging</li>" +
      "</ul></div></section>" +
      '<section class="panel"><div class="panel-head"><div><h2>About this console</h2><p>Static preview versus live GUI</p></div></div><div class="panel-body"><p class="muted">The console is served at <code>/</code> by the FastAPI app, so it shares the API origin and session. The GitHub Pages workflow publishes the same files as a static preview; sign-in is disabled there because the API is not running. The JWT is kept in <code>sessionStorage</code> and is discarded when the tab closes.</p></div></section>';
  }

  // ------------------------------------------------------------------------
  // Modal and toasts
  // ------------------------------------------------------------------------

  function openModal(config) {
    modalHandler = config.onSubmit || null;
    el("modal-title").textContent = config.title || "Dialog";
    var subtitle = el("modal-subtitle");
    subtitle.textContent = config.subtitle || "";
    subtitle.hidden = !config.subtitle;
    el("modal-body").innerHTML = config.body || "";
    var errorBox = el("modal-error");
    errorBox.textContent = "";
    errorBox.hidden = true;

    var submit = el("modal-submit");
    submit.textContent = config.submitLabel || "Save";
    submit.className = "btn " + (config.danger ? "btn-danger" : "btn-primary");
    submit.disabled = false;

    el("modal-root").hidden = false;
    document.body.classList.add("modal-open");
    var first = el("modal-body").querySelector("input:not([type=hidden]), select, textarea");
    if (first) {
      window.setTimeout(function () {
        first.focus();
      }, 40);
    }
  }

  function closeModal() {
    var root = el("modal-root");
    if (!root) return;
    root.hidden = true;
    document.body.classList.remove("modal-open");
    modalHandler = null;
    el("modal-error").hidden = true;
    el("modal-error").textContent = "";
  }

  function toast(message, kind) {
    kind = kind || "success";
    var root = el("toast-root");
    var node = document.createElement("div");
    node.className = "toast toast-" + kind;
    node.innerHTML =
      (kind === "error" ? ICONS.x : kind === "info" ? ICONS.info : ICONS.check) +
      "<span></span>";
    node.querySelector("span").textContent = message;
    while (root.children.length >= 3) {
      root.removeChild(root.firstElementChild);
    }
    root.appendChild(node);
    window.setTimeout(function () {
      if (node.parentNode) node.parentNode.removeChild(node);
    }, 4500);
  }

  // ------------------------------------------------------------------------
  // Facility dialogs
  // ------------------------------------------------------------------------

  function openFacilityForm(facility) {
    var editing = Boolean(facility);
    openModal({
      title: editing ? "Edit facility" : "New facility",
      subtitle: editing ? "Facility #" + facility.id : "Register a regulated facility",
      submitLabel: editing ? "Save changes" : "Create facility",
      body:
        '<div class="form-grid">' +
        field("Name", "name", {
          value: facility ? facility.name : "",
          required: true,
          maxlength: 200,
          full: true,
          placeholder: "Nile Chemicals",
        }) +
        field("Registration number", "registration_number", {
          value: facility ? facility.registration_number : "",
          required: true,
          maxlength: 50,
          hint: "3\u201350 characters; letters, digits, '-' or '/'.",
          placeholder: "REG-1000",
        }) +
        field("Status", "status", {
          type: "select",
          value: facility ? facility.status : "active",
          options: enumOptions(FACILITY_STATUSES),
        }) +
        field("Address", "address", {
          type: "textarea",
          value: facility ? facility.address : "",
          required: true,
          full: true,
          rows: 3,
          placeholder: "Street, city, country",
        }) +
        "</div>",
      onSubmit: async function (data) {
        var body = {
          name: readValue(data, "name"),
          registration_number: readValue(data, "registration_number"),
          address: readValue(data, "address"),
          status: readValue(data, "status"),
        };
        if (editing) {
          await api("/facilities/" + facility.id, { method: "PUT", body: body });
        } else {
          await api("/facilities", { method: "POST", body: body });
        }
        state.facilitiesLoaded = false;
        toast(editing ? "Facility updated." : "Facility created.");
        renderView("facilities");
      },
    });
  }

  function confirmDeleteFacility(facility) {
    openModal({
      title: "Delete facility",
      subtitle: facility.name || "Facility #" + facility.id,
      danger: true,
      submitLabel: "Delete facility",
      body:
        '<p class="confirm-copy">Soft-delete <strong>' +
        esc(facility.name || "this facility") +
        "</strong>? It disappears from the registry but its audit history is preserved. " +
        "A facility with active licenses cannot be deleted; otherwise its licenses are revoked with it.</p>",
      onSubmit: async function () {
        await api("/facilities/" + facility.id, { method: "DELETE" });
        state.facilitiesLoaded = false;
        toast("Facility deleted.");
        renderView("facilities");
      },
    });
  }

  // ------------------------------------------------------------------------
  // License dialogs
  // ------------------------------------------------------------------------

  function openLicenseForm(license) {
    var editing = Boolean(license);
    if (!editing && state.facilities.length === 0) {
      toast("Create a facility before issuing a license.", "error");
      return;
    }

    var facilityControl = editing
      ? readonlyField("Facility", facilityName(license.facility_id))
      : field("Facility", "facility_id", {
          type: "select",
          required: true,
          options: facilityOptions(),
        });

    openModal({
      title: editing ? "Edit license" : "New license",
      subtitle: editing ? license.license_number : "Issue a license to a facility",
      submitLabel: editing ? "Save changes" : "Create license",
      body:
        '<div class="form-grid">' +
        facilityControl +
        field("License number", "license_number", {
          value: license ? license.license_number : "",
          required: true,
          maxlength: 50,
          hint: "3\u201350 characters; letters, digits, '-' or '/'.",
          placeholder: "LIC-1000",
        }) +
        field("Type", "type", {
          type: "select",
          value: license ? license.type : "operating",
          options: enumOptions(LICENSE_TYPES),
        }) +
        field("Status", "status", {
          type: "select",
          value: license ? license.status : "active",
          options: enumOptions(LICENSE_STATUSES),
        }) +
        field("Issue date", "issue_date", {
          type: "date",
          value: license ? license.issue_date : todayISO(),
          required: true,
        }) +
        field("Expiry date", "expiry_date", {
          type: "date",
          value: license ? license.expiry_date : oneYearFromTodayISO(),
          required: true,
          hint: "Must be after the issue date.",
        }) +
        "</div>",
      onSubmit: async function (data) {
        var issueDate = readValue(data, "issue_date");
        var expiryDate = readValue(data, "expiry_date");
        if (expiryDate <= issueDate) {
          throw new Error("The expiry date must be after the issue date.");
        }
        var body = {
          license_number: readValue(data, "license_number"),
          type: readValue(data, "type"),
          issue_date: issueDate,
          expiry_date: expiryDate,
          status: readValue(data, "status"),
        };
        if (editing) {
          await api("/licenses/" + license.id, { method: "PUT", body: body });
        } else {
          body.facility_id = Number(readValue(data, "facility_id"));
          await api("/licenses", { method: "POST", body: body });
        }
        toast(editing ? "License updated." : "License created.");
        renderView("licenses");
      },
    });
  }

  function confirmDeleteLicense(license) {
    openModal({
      title: "Revoke license",
      subtitle: license.license_number,
      danger: true,
      submitLabel: "Delete license",
      body:
        '<p class="confirm-copy">Soft-delete license <strong>' +
        esc(license.license_number) +
        "</strong> for <strong>" +
        esc(facilityName(license.facility_id)) +
        "</strong>? The record is hidden from the registry and the action is written to the audit log.</p>",
      onSubmit: async function () {
        await api("/licenses/" + license.id, { method: "DELETE" });
        toast("License deleted.");
        renderView("licenses");
      },
    });
  }

  // ------------------------------------------------------------------------
  // Inspection dialogs
  // ------------------------------------------------------------------------

  async function openInspectionForm(inspection) {
    var editing = Boolean(inspection);
    if (!editing && state.facilities.length === 0) {
      toast("Create a facility before recording an inspection.", "error");
      return;
    }

    var isAdmin = state.user.role === "admin";
    var inspectors = [];
    if (!editing && isAdmin) {
      inspectors = await loadInspectorLookup();
    }

    var facilityControl = editing
      ? readonlyField("Facility", facilityName(inspection.facility_id))
      : field("Facility", "facility_id", {
          type: "select",
          required: true,
          options: facilityOptions(),
        });

    var inspectorControl = "";
    if (editing) {
      inspectorControl = readonlyField(
        "Inspector",
        inspection.inspector_username || "Inspector #" + inspection.inspector_id
      );
    } else if (isAdmin) {
      var inspectorOptions = [{ value: "", label: "Me (administrator)" }].concat(
        inspectors.map(function (inspector) {
          return {
            value: String(inspector.id),
            label: (inspector.full_name || inspector.username) + " (@" + inspector.username + ")",
          };
        })
      );
      inspectorControl = field("Inspector", "inspector_id", {
        type: "select",
        options: inspectorOptions,
        hint: "Leave as yourself or assign an active inspector.",
      });
    }

    openModal({
      title: editing ? "Edit inspection" : "New inspection",
      subtitle: editing ? "Inspection #" + inspection.id : "Record a compliance inspection",
      submitLabel: editing ? "Save changes" : "Record inspection",
      body:
        '<div class="form-grid">' +
        facilityControl +
        inspectorControl +
        field("Inspection date", "inspection_date", {
          type: "date",
          value: editing ? inspection.inspection_date : todayISO(),
          max: todayISO(),
          required: true,
        }) +
        field("Result", "result", {
          type: "select",
          value: editing ? inspection.result : "compliant",
          options: enumOptions(INSPECTION_RESULTS),
        }) +
        field("Notes", "notes", {
          type: "textarea",
          value: editing ? inspection.notes || "" : "",
          full: true,
          rows: 4,
          maxlength: 2000,
          placeholder: "Findings, corrective actions or follow-up notes\u2026",
        }) +
        "</div>",
      onSubmit: async function (data) {
        var notes = readValue(data, "notes");
        var body = {
          inspection_date: readValue(data, "inspection_date"),
          result: readValue(data, "result"),
          notes: notes || null,
        };
        if (editing) {
          await api("/inspections/" + inspection.id, { method: "PUT", body: body });
        } else {
          body.facility_id = Number(readValue(data, "facility_id"));
          var inspectorId = readValue(data, "inspector_id");
          if (inspectorId) body.inspector_id = Number(inspectorId);
          await api("/inspections", { method: "POST", body: body });
        }
        toast(editing ? "Inspection updated." : "Inspection recorded.");
        renderView("inspections");
      },
    });
  }

  // ------------------------------------------------------------------------
  // User dialogs (admin only)
  // ------------------------------------------------------------------------

  function openUserForm(user) {
    var editing = Boolean(user);
    var isSelf = editing && user.id === state.user.id;
    var accountFields;

    if (editing) {
      accountFields =
        field("Full name", "full_name", {
          value: user.full_name || "",
          maxlength: 120,
          full: true,
          placeholder: "Display name",
        }) +
        (isSelf
          ? readonlyField("Role", labelize(user.role)) +
            readonlyField("Status", user.is_active ? "Active" : "Inactive")
          : field("Role", "role", {
              type: "select",
              value: user.role,
              options: enumOptions(ROLES),
            }) +
            field("Status", "is_active", {
              type: "select",
              value: user.is_active ? "true" : "false",
              options: [
                { value: "true", label: "Active" },
                { value: "false", label: "Inactive" },
              ],
            })) +
        field("New password", "password", {
          type: "password",
          autocomplete: "new-password",
          full: true,
          minlength: 12,
          hint: "Optional. At least 12 characters with upper, lower, digit and symbol.",
        });
    } else {
      accountFields =
        field("Username", "username", {
          required: true,
          minlength: 3,
          maxlength: 50,
          pattern: "[a-z0-9][a-z0-9._\\-]{2,49}",
          hint: "Lowercase letters, digits, '.', '_' or '-'; must start with a letter or digit.",
          placeholder: "jane.doe",
        }) +
        field("Role", "role", {
          type: "select",
          value: "viewer",
          options: enumOptions(ROLES),
        }) +
        field("Full name", "full_name", {
          maxlength: 120,
          full: true,
          placeholder: "Optional display name",
        }) +
        field("Password", "password", {
          type: "password",
          autocomplete: "new-password",
          required: true,
          full: true,
          minlength: 12,
          hint: "At least 12 characters with upper, lower, digit and symbol.",
        });
    }

    openModal({
      title: editing ? "Edit user" : "New user",
      subtitle: editing ? "@" + user.username : "Provision a console account",
      submitLabel: editing ? "Save changes" : "Create user",
      body: '<div class="form-grid">' + accountFields + "</div>",
      onSubmit: async function (data) {
        if (editing) {
          var body = { full_name: readValue(data, "full_name") || null };
          if (!isSelf) {
            body.role = readValue(data, "role");
            body.is_active = readValue(data, "is_active") === "true";
          }
          var password = readValue(data, "password");
          if (password) body.password = password;
          var updated = await api("/users/" + user.id, { method: "PUT", body: body });
          if (isSelf) {
            state.user = updated;
            updateUserChrome();
          }
          state.inspectorsLoaded = false;
          toast("User updated.");
          renderView("users");
        } else {
          var createBody = {
            username: readValue(data, "username"),
            password: readValue(data, "password"),
            role: readValue(data, "role"),
          };
          var fullName = readValue(data, "full_name");
          if (fullName) createBody.full_name = fullName;
          await api("/users", { method: "POST", body: createBody });
          state.inspectorsLoaded = false;
          toast("User created.");
          renderView("users");
        }
      },
    });
  }

  function confirmDeactivateUser(user) {
    openModal({
      title: "Deactivate user",
      subtitle: "@" + user.username,
      danger: true,
      submitLabel: "Deactivate user",
      body:
        '<p class="confirm-copy">Deactivate <strong>@' +
        esc(user.username) +
        "</strong>? The account can no longer sign in, but its audit history is preserved. An administrator can reactivate it later.</p>",
      onSubmit: async function () {
        await api("/users/" + user.id, { method: "DELETE" });
        state.inspectorsLoaded = false;
        toast("User deactivated.");
        renderView("users");
      },
    });
  }

  // ------------------------------------------------------------------------
  // Login / logout
  // ------------------------------------------------------------------------

  async function onLogin(event) {
    event.preventDefault();
    if (IS_STATIC_PREVIEW) return;

    var username = el("login-username").value.trim();
    var password = el("login-password").value;
    var errorBox = el("login-error");
    errorBox.hidden = true;
    errorBox.textContent = "";

    if (!username || !password) {
      showLoginError("Enter your username and password.");
      return;
    }

    var submit = el("login-submit");
    submit.disabled = true;
    submit.textContent = "Signing in\u2026";

    try {
      var data = await api("/auth/login", {
        method: "POST",
        body: { username: username, password: password },
        auth: false,
      });
      setSession(data.access_token, data.user);
      el("login-form").reset();
      enterApp();
      toast("Signed in as " + (data.user.full_name || data.user.username) + ".");
    } catch (error) {
      showLoginError(error.message || "Sign-in failed.");
    } finally {
      submit.disabled = IS_STATIC_PREVIEW;
      submit.textContent = IS_STATIC_PREVIEW
        ? "Console requires the API"
        : "Sign in to console";
    }
  }

  function showLoginError(message) {
    var errorBox = el("login-error");
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  function onTogglePassword() {
    var input = el("login-password");
    var button = el("toggle-password");
    var show = input.type === "password";
    input.type = show ? "text" : "password";
    button.textContent = show ? "Hide" : "Show";
    button.setAttribute("aria-label", show ? "Hide password" : "Show password");
  }

  async function onLogout() {
    try {
      if (state.token) await api("/auth/logout", { method: "POST" });
    } catch (error) {
      /* The local session is cleared even if revocation fails. */
    }
    clearSession();
    if (window.location.hash !== "#/dashboard") {
      window.history.replaceState(null, "", "#/dashboard");
    }
    showLogin("You have been signed out.");
  }

  // ------------------------------------------------------------------------
  // Content actions
  // ------------------------------------------------------------------------

  function findRow(view, id) {
    var rows = state.rows[view] || [];
    for (var index = 0; index < rows.length; index += 1) {
      if (Number(rows[index].id) === Number(id)) return rows[index];
    }
    return null;
  }

  function onContentClick(event) {
    var trigger = event.target.closest("[data-action]");
    if (!trigger) return;
    handleAction(trigger).catch(function (error) {
      toast((error && error.message) || "Action failed.", "error");
    });
  }

  async function handleAction(trigger) {
    var action = trigger.getAttribute("data-action");
    var id = Number(trigger.getAttribute("data-id"));

    switch (action) {
      case "page":
        state.filters[state.view].page = Math.max(1, id);
        await renderView(state.view);
        return;
      case "refresh":
        await renderView(state.view);
        return;
      case "reset-filters": {
        var view = trigger.getAttribute("data-filter") || state.view;
        state.filters[view] = clone(DEFAULT_FILTERS[view]);
        await renderView(view);
        return;
      }
      case "go":
        navigate(trigger.getAttribute("data-target"));
        return;
      case "new-facility":
        openFacilityForm();
        return;
      case "edit-facility": {
        var facility = await api("/facilities/" + id);
        openFacilityForm(facility);
        return;
      }
      case "delete-facility": {
        var facilityRow = findRow("facilities", id) || { id: id, name: "this facility" };
        confirmDeleteFacility(facilityRow);
        return;
      }
      case "new-license":
        openLicenseForm();
        return;
      case "edit-license": {
        var license = await api("/licenses/" + id);
        openLicenseForm(license);
        return;
      }
      case "delete-license": {
        var licenseRow = findRow("licenses", id) || {
          id: id,
          license_number: "this license",
          facility_id: 0,
        };
        confirmDeleteLicense(licenseRow);
        return;
      }
      case "new-inspection":
        await openInspectionForm();
        return;
      case "edit-inspection": {
        var inspection = await api("/inspections/" + id);
        await openInspectionForm(inspection);
        return;
      }
      case "new-user":
        openUserForm();
        return;
      case "edit-user": {
        var user = await api("/users/" + id);
        openUserForm(user);
        return;
      }
      case "deactivate-user": {
        var target = findRow("users", id);
        if (target) confirmDeactivateUser(target);
        return;
      }
      default:
        return;
    }
  }

  function onContentSubmit(event) {
    var filterForm = event.target.closest("form[data-filter]");
    if (!filterForm) return;
    event.preventDefault();
    var view = filterForm.getAttribute("data-filter");
    var filters = state.filters[view];
    new FormData(filterForm).forEach(function (value, key) {
      filters[key] = typeof value === "string" ? value.trim() : value;
    });
    filters.page = 1;
    renderView(view);
  }

  function onContentChange(event) {
    if (event.target.tagName !== "SELECT") return;
    var form = event.target.closest("form[data-filter]");
    if (form && typeof form.requestSubmit === "function") form.requestSubmit();
  }

  // ------------------------------------------------------------------------
  // Modal events
  // ------------------------------------------------------------------------

  function onModalClick(event) {
    if (event.target.closest('[data-action="close-modal"]')) closeModal();
  }

  async function onModalSubmit(event) {
    event.preventDefault();
    var form = event.currentTarget;
    if (!form.reportValidity() || !modalHandler) return;

    var errorBox = el("modal-error");
    var submit = el("modal-submit");
    var label = submit.textContent;
    errorBox.hidden = true;
    errorBox.textContent = "";
    submit.disabled = true;
    submit.textContent = "Saving\u2026";

    try {
      await modalHandler(new FormData(form));
      closeModal();
    } catch (error) {
      errorBox.textContent = (error && error.message) || "Could not save the changes.";
      errorBox.hidden = false;
      submit.disabled = false;
      submit.textContent = label;
    }
  }

  function onKeyDown(event) {
    if (event.key !== "Escape") return;
    if (!el("modal-root").hidden) {
      closeModal();
    } else {
      closeSidebar();
    }
  }

  // ------------------------------------------------------------------------
  // Event wiring
  // ------------------------------------------------------------------------

  function bindEvents() {
    el("login-form").addEventListener("submit", onLogin);
    el("toggle-password").addEventListener("click", onTogglePassword);
    el("logout-button").addEventListener("click", onLogout);

    el("menu-button").addEventListener("click", function () {
      toggleSidebar(!el("sidebar").classList.contains("is-open"));
    });
    el("sidebar-backdrop").addEventListener("click", closeSidebar);
    el("sidebar").addEventListener("click", function (event) {
      var button = event.target.closest("[data-view]");
      if (!button || button.hidden) return;
      navigate(button.getAttribute("data-view"));
    });

    el("content").addEventListener("click", onContentClick);
    el("content").addEventListener("submit", onContentSubmit);
    el("content").addEventListener("change", onContentChange);

    el("modal-root").addEventListener("click", onModalClick);
    el("modal-form").addEventListener("submit", onModalSubmit);
    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("hashchange", onHashChange);
    window.addEventListener("resize", function () {
      if (window.innerWidth > 920) closeSidebar();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
