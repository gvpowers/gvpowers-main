/* ============================================================
   GV POWERS — interactions.js
   Back-to-top, image fallbacks, form polish. (The project gallery
   filter was removed with the image gallery itself.)
   ============================================================ */
(function () {
  "use strict";

  /* ----- Back to top ----- */
  var backToTop = document.getElementById("back-to-top");
  if (backToTop) {
    window.addEventListener("scroll", function () {
      var show = window.scrollY > 600;
      backToTop.hidden = false;
      backToTop.classList.toggle("is-visible", show);
    }, { passive: true });

    backToTop.addEventListener("click", function () {
      var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
    });
  }

  /* ----- Image fallback: swap broken images to a warm gradient block ----- */
  document.querySelectorAll("img").forEach(function (img) {
    img.addEventListener("error", function () {
      img.style.display = "none";
      var wrap = img.closest("figure") || img.parentElement;
      if (wrap) {
        wrap.style.background =
          "linear-gradient(135deg, #A5A79B, #E8D2B5)";
        wrap.style.minHeight = "220px";
      }
    });
  });

  /* ----- Enquiry form: disable double submits ----- */
  var form = document.getElementById("enquiry-form");
  if (form) {
    form.addEventListener("submit", function () {
      var submit = document.getElementById("enquiry-submit");
      if (submit && form.checkValidity()) {
        submit.disabled = true;
        submit.style.opacity = "0.7";
      }
    });
  }

  /* ----- Dismiss form banners on new typing ----- */
  var banners = document.querySelectorAll(".form-banner--error");
  if (form && banners.length) {
    form.addEventListener("input", function () {
      banners.forEach(function (b) { b.remove(); });
    }, { once: true });
  }
})();
