/* ============================================================
   GV POWERS — header.js
   Shared auto-hiding header logic (desktop, laptop, tablet, mobile).

   Behaviour:
   - Header is visible at page load and near the top of the page.
   - Scrolling DOWN past a threshold hides it (slides above viewport).
   - Scrolling UP reveals it immediately.
   - Hidden while the mobile menu or an open nav dropdown is active.
   - Direction hysteresis prevents flicker from tiny scroll movements.
   - Single rAF-throttled passive listener for every screen size.
   ============================================================ */
(function () {
  "use strict";

  var header = document.getElementById("site-header");
  if (!header) return;

  var SHOW_AT_TOP = 48;   // always visible within the first 48px of scroll
  var HIDE_AFTER = 120;   // never start hiding before 120px
  var DOWN_TRIGGER = 12;  // px of downward movement required to hide
  var UP_TRIGGER = 8;     // px of upward movement required to reveal

  var lastY = window.scrollY;
  var ticking = false;

  var media = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)")
    : { matches: false };

  /* Navigation must stay visible while the mobile menu or a dropdown is open */
  function navIsOpen() {
    var toggle = document.getElementById("nav-toggle");
    if (toggle && toggle.getAttribute("aria-expanded") === "true") return true;
    var menu = document.getElementById("mobile-menu");
    if (menu && menu.classList.contains("is-open")) return true;
    return Boolean(document.querySelector(".nav-links__item.is-open"));
  }

  function hide() {
    if (!header.classList.contains("is-hidden")) {
      header.classList.add("is-hidden");
    }
  }

  function reveal() {
    header.classList.remove("is-hidden");
  }

  function update() {
    ticking = false;
    var y = window.scrollY;

    /* glass-nav solidifies once the page has moved a little */
    header.classList.toggle("is-scrolled", y > 30);

    if (media.matches) { /* reduced motion: keep header always visible */
      reveal();
      lastY = y;
      return;
    }

    if (y <= SHOW_AT_TOP || y < HIDE_AFTER || navIsOpen()) {
      reveal();
      lastY = y;
      return;
    }

    if (y > lastY + DOWN_TRIGGER) {
      hide();
    } else if (y < lastY - UP_TRIGGER) {
      reveal();
    }
    lastY = y;
  }

  function onScroll() {
    if (!ticking) {
      ticking = true;
      window.requestAnimationFrame(update);
    }
  }

  window.addEventListener("scroll", onScroll, { passive: true });

  /* Keyboard focus inside navigation must never hide the header */
  header.addEventListener("focusin", reveal);

  /* Decide state on load (e.g. refresh mid-page) */
  update();
})();
