/* ============================================================
   GV POWERS — animations.js
   Scroll reveals, animated counters, subtle hero parallax.
   All disabled under prefers-reduced-motion.
   ============================================================ */
(function () {
  "use strict";

  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ----- Scroll reveal ----- */
  var revealEls = document.querySelectorAll("[data-reveal]");
  if (!reducedMotion && "IntersectionObserver" in window) {
    var revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var el = entry.target;
          var delay = parseInt(el.getAttribute("data-reveal-delay") || "0", 10);
          el.style.setProperty("--reveal-delay", delay + "ms");
          el.classList.add("is-visible");
          revealObserver.unobserve(el);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });

    revealEls.forEach(function (el) { revealObserver.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("is-visible"); });
  }

  /* ----- Animated counters ----- */
  function animateCounter(el) {
    var target = parseInt(el.getAttribute("data-count"), 10);
    var display = el.getAttribute("data-display") || String(target);
    el.classList.add("is-counting");

    if (isNaN(target) || reducedMotion) {
      el.textContent = display;
      return;
    }

    var duration = 1600;
    var start = null;

    function format(n) {
      var rounded = Math.round(n);
      var grouped = rounded.toLocaleString("en-IN");
      /* Preserve suffix like "+" from display ("1,250+") */
      if (display.indexOf("+") !== -1 && n >= target) return grouped + "+";
      return grouped;
    }

    function tick(ts) {
      if (!start) start = ts;
      var progress = Math.min((ts - start) / duration, 1);
      /* easeOutCubic */
      var eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = format(target * eased);
      if (progress < 1) {
        window.requestAnimationFrame(tick);
      } else {
        el.textContent = display;
      }
    }

    window.requestAnimationFrame(tick);
  }

  var counters = document.querySelectorAll("[data-count]");
  if (!reducedMotion && "IntersectionObserver" in window) {
    var countObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          countObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach(function (el) { countObserver.observe(el); });
  } else {
    counters.forEach(function (el) {
      el.textContent = el.getAttribute("data-display") || el.textContent;
    });
  }

  /* ----- Subtle hero parallax (desktop, non-reduced-motion) ----- */
  var heroMedia = document.querySelector(".hero__media img");
  var isTouch = window.matchMedia("(hover: none)").matches;

  if (heroMedia && !reducedMotion && !isTouch) {
    var ticking = false;

    window.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        var y = window.scrollY;
        if (y < window.innerHeight * 1.2) {
          heroMedia.style.transform = "translateY(" + (y * 0.18).toFixed(1) + "px)";
        }
        ticking = false;
      });
    }, { passive: true });
  }
})();
