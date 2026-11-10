/* ============================================================
   GV POWERS — admin-map-manager.js
   /admin/map — all locations, search + multi-filter + list view.
   ============================================================ */
(function () {
  "use strict";

  var mapEl = document.getElementById("adminMap");
  if (!mapEl || typeof L === "undefined") return;

  var COLORS = { solar: "#1B6FE8", ups: "#7C5CBF", generators: "#E07C24", other: "#5E6152" };

  var map = L.map(mapEl, { center: [20.6, 78.9], zoom: 5, scrollWheelZoom: true });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(map);

  var group = L.layerGroup().addTo(map);
  var all = [];

  var q = document.getElementById("map-search");
  var fState = document.getElementById("map-filter-state");
  var fCat = document.getElementById("map-filter-category");
  var fStatus = document.getElementById("map-filter-status");
  var countEl = document.getElementById("admin-map-count");
  var listCount = document.getElementById("admin-list-count");
  var listEl = document.getElementById("admin-loc-list");

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function render() {
    group.clearLayers();
    var shown = 0;
    var needle = (q.value || "").trim().toLowerCase();
    all.forEach(function (p) {
      if (needle && p.name.toLowerCase().indexOf(needle) === -1) return;
      if (fState.value && p.state !== fState.value) return;
      if (fCat.value && p.category !== fCat.value) return;
      if (fStatus.value && p.status !== fStatus.value) return;
      shown++;
      L.circleMarker([p.latitude, p.longitude], {
        radius: 9,
        color: "#ffffff",
        weight: 2,
        fillColor: COLORS[p.category] || COLORS.other,
        fillOpacity: 0.95
      })
        .bindPopup(
          "<strong>" + escapeHtml(p.name) + "</strong><br>" +
          escapeHtml(p.category) + " · " + escapeHtml(p.status) + "<br>" +
          escapeHtml([p.locality, p.district, p.state].filter(Boolean).join(", ")) + "<br>" +
          p.latitude.toFixed(5) + ", " + p.longitude.toFixed(5) +
          (p.id ? "<br><a style='color:#1B6FE8' href='/admin/projects'>Edit in project form →</a>" : "")
        )
        .addTo(group);
    });
    if (countEl) countEl.textContent = shown + " of " + all.length + " locations shown";
    if (listCount) listCount.textContent = shown;

    /* sync the side list visibility */
    if (listEl) {
      [...listEl.children].forEach(function (li) {
        var d = li.dataset;
        if (!d.id) return; // "no locations" placeholder row
        var ok = (!needle || d.name.indexOf(needle) !== -1) &&
          (!fState.value || d.state === fState.value) &&
          (!fCat.value || d.category === fCat.value) &&
          (!fStatus.value || d.status === fStatus.value);
        li.style.display = ok ? "" : "none";
      });
    }
  }

  [q, fState, fCat, fStatus].forEach(function (el) {
    if (el) el.addEventListener("input", render);
  });

  listEl && listEl.addEventListener("click", function (e) {
    var li = e.target.closest("li[data-id]");
    if (!li) return;
    var p = all.find(function (x) { return String(x.id) === li.dataset.id; });
    if (p) map.flyTo([p.latitude, p.longitude], 9, { duration: 0.6 });
  });

  fetch("/admin/api/projects")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      all = (data.projects || []).filter(function (p) {
        return isFinite(p.latitude) && isFinite(p.longitude);
      });
      if (all.length) map.fitBounds(all.map(function (p) { return [p.latitude, p.longitude]; }), { padding: [30, 30] });
      render();
    })
    .catch(function () {
      if (countEl) countEl.textContent = "Could not load locations.";
    });
})();
