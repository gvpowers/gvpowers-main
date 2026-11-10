/* ============================================================
   GV POWERS — theme.js
   15 complete design systems. Switches html[data-theme] + the
   theme stylesheet link. Visitor preference lives in
   localStorage; it never writes back to the admin-configured
   default in the database.

   Only ids rendered in the theme modal are accepted — arbitrary
   input is ignored (safe theme identifiers only).
   Legacy ids from earlier releases are mapped forward.
   ============================================================ */
(function () {
  "use strict";

  var html = document.documentElement;
  var link = document.getElementById("theme-css");
  var modal = document.getElementById("theme-modal");
  var grid = document.getElementById("theme-modal-grid");
  var resetBtn = document.getElementById("theme-reset");
  var base = "/static/css/themes/";
  var STORAGE_KEY = "gvp-theme";

  /* Legacy release ids → current design-system ids */
  var LEGACY_MAP = {
    "sage-glass": "glassmorphism-pro",
    "glass-pro": "glassmorphism-pro",
    "luxury-editorial": "luxury-heritage",
    "industrial": "industrial-modern",
    "architectural": "swiss-editorial",
    "corporate": "corporate-minimal",
    "monochrome": "warm-monochrome",
    "brutalist": "neo-brutalist",
    "classic": "classic-business",
    "spatial": "spatial-modern",
    "nordic": "nordic-minimal",
    "energy-tech": "high-end-technology",
    "energy-portfolio": "modern-energy-portfolio"
  };

  var options = grid ? [].slice.call(grid.querySelectorAll(".theme-option")) : [];
  var available = {};
  options.forEach(function (opt) { available[opt.dataset.theme] = true; });

  var defaultTheme = html.getAttribute("data-theme") || "swiss-editorial";
  var current = defaultTheme;

  function canonical(raw) {
    if (!raw) return null;
    if (available[raw]) return raw;
    if (LEGACY_MAP[raw] && available[LEGACY_MAP[raw]]) return LEGACY_MAP[raw];
    return null;
  }

  function normalizeHref(id) {
    /* tolerate old paths that may be cached in the link element */
    return base + "theme-" + id + ".css";
  }

  function applyTheme(id, persist) {
    html.setAttribute("data-theme", id);
    if (link) link.href = normalizeHref(id);
    current = id;
    options.forEach(function (opt) {
      opt.setAttribute("aria-selected", String(opt.dataset.theme === id));
    });
    if (persist) {
      try { localStorage.setItem(STORAGE_KEY, id); } catch (e) { /* private mode */ }
    }
  }

  /* Restore the visitor's personal preference (server default untouched) */
  var saved = null;
  try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) { /* ignore */ }
  var restored = canonical((saved || "").trim() ? saved : null);
  if (restored && restored !== defaultTheme) {
    applyTheme(restored, false); /* re-persist in canonical form */
    try { localStorage.setItem(STORAGE_KEY, restored); } catch (e) { /* ignore */ }
  }

  /* Deep-link previews: /?theme=denim… — canonical ids only */
  var params = new URLSearchParams(window.location.search);
  var requested = canonical(params.get("theme"));
  if (requested) applyTheme(requested, true);

  /* ---------- modal open / close ---------- */
  var openers = [].slice.call(document.querySelectorAll("[data-theme-open]"));
  var closers = [].slice.call(document.querySelectorAll("[data-theme-close]"));
  var lastFocus = null;

  function openModal() {
    if (!modal) return;
    lastFocus = document.activeElement;
    modal.hidden = false;
    void modal.offsetHeight;
    modal.classList.add("is-open");
    document.body.style.overflow = "hidden";
    openers.forEach(function (btn) { btn.setAttribute("aria-expanded", "true"); });
    markSelected();
    var closeBtn = modal.querySelector(".theme-modal__close");
    if (closeBtn) closeBtn.focus();
  }

  function closeModal() {
    if (!modal || modal.hidden) return;
    modal.classList.remove("is-open");
    /* keep body scroll locked only if the mobile menu isn't open */
    var menuOpen = document.getElementById("nav-toggle");
    if (!menuOpen || menuOpen.getAttribute("aria-expanded") !== "true") {
      document.body.style.overflow = "";
    }
    openers.forEach(function (btn) { btn.setAttribute("aria-expanded", "false"); });
    window.setTimeout(function () { modal.hidden = true; }, 250);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function markSelected() {
    options.forEach(function (opt) {
      opt.setAttribute("aria-selected", String(opt.dataset.theme === current));
    });
  }

  openers.forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (modal.hidden) { openModal(); } else { closeModal(); }
    });
  });
  closers.forEach(function (btn) { btn.addEventListener("click", closeModal); });

  if (modal) {
    /* click on the dim backdrop closes */
    modal.addEventListener("click", function (e) {
      if (e.target === modal) closeModal();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      if (!modal.hidden) {
        closeModal();
        return;
      }
    });
  }

  /* ---------- selection ---------- */
  options.forEach(function (opt) {
    opt.addEventListener("click", function () {
      if (opt.dataset.theme) applyTheme(opt.dataset.theme, true);
    });
  });

  /* ---------- reset to the administrator-configured default ---------- */
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* ignore */ }
      applyTheme(defaultTheme, false);
      closeModal();
    });
  }
})();
