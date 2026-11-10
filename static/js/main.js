/* ============================================================
   GV POWERS — main.js
   Mobile menu, touch dropdowns, focus-safe toggling.
   Header scroll state lives in header.js (shared, all sizes).
   ============================================================ */
(function () {
  "use strict";

  var navToggle = document.getElementById("nav-toggle");
  var mobileMenu = document.getElementById("mobile-menu");
  var header = document.getElementById("site-header");

  /* ----- Mobile menu ----- */
  function closeMenu() {
    if (!mobileMenu || !navToggle) return;
    mobileMenu.classList.remove("is-open");
    window.setTimeout(function () {
      mobileMenu.hidden = true;
    }, 350);
    navToggle.setAttribute("aria-expanded", "false");
    navToggle.setAttribute("aria-label", "Open menu");
    document.body.style.overflow = "";
  }

  function openMenu() {
    if (!mobileMenu || !navToggle) return;
    mobileMenu.hidden = false;
    /* force reflow so the transition runs */
    void mobileMenu.offsetHeight;
    mobileMenu.classList.add("is-open");
    navToggle.setAttribute("aria-expanded", "true");
    navToggle.setAttribute("aria-label", "Close menu");
    document.body.style.overflow = "hidden";
    /* the header must never be hidden while the menu is open */
    if (header) header.classList.remove("is-hidden");
  }

  if (navToggle && mobileMenu) {
    navToggle.addEventListener("click", function () {
      var expanded = navToggle.getAttribute("aria-expanded") === "true";
      if (expanded) { closeMenu(); } else { openMenu(); }
    });

    /* Close when a menu link is clicked */
    mobileMenu.addEventListener("click", function (e) {
      if (e.target.closest("a")) closeMenu();
    });

    /* Close on Escape */
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && navToggle.getAttribute("aria-expanded") === "true") {
        closeMenu();
        navToggle.focus();
      }
    });

    /* Reset state if resized back to desktop */
    window.addEventListener("resize", function () {
      if (window.innerWidth > 900) {
        mobileMenu.classList.remove("is-open");
        mobileMenu.hidden = true;
        navToggle.setAttribute("aria-expanded", "false");
        document.body.style.overflow = "";
      }
    }, { passive: true });
  }

  /* ----- Dropdown: first tap opens on touch devices ----- */
  document.querySelectorAll(".nav-links__item.has-dropdown > a").forEach(function (link) {
    link.addEventListener("touchstart", function (e) {
      var item = link.parentElement;
      if (!item.classList.contains("is-open")) {
        e.preventDefault();
        document.querySelectorAll(".nav-links__item.is-open").forEach(function (o) {
          if (o !== item) o.classList.remove("is-open");
        });
        item.classList.add("is-open");
      }
    }, { passive: false });
  });
  document.addEventListener("touchstart", function (e) {
    if (!e.target.closest(".has-dropdown")) {
      document.querySelectorAll(".nav-links__item.is-open").forEach(function (o) {
        o.classList.remove("is-open");
      });
    }
  }, { passive: true });
})();
