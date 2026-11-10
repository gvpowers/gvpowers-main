/* ============================================================
   GV POWERS — map.js
   Interactive India project map (Leaflet + OpenStreetMap tiles).
   - Markers come only from the admin-managed database feed.
   - No fictional markers: the map renders exactly what /admin has.
   - Filters update markers without reloading the page.
   ============================================================ */
(function () {
  "use strict";

  var container = document.getElementById("gvp-map");
  if (!container || typeof L === "undefined") return;

  var CATEGORY_COLORS = {
    solar: "#1B6FE8",
    ups: "#7C5CBF",
    generators: "#E07C24",
    other: "#5E6152"
  };

  var map = L.map(container, {
    center: [20.59, 78.96],
    zoom: 5,
    minZoom: 4,
    maxZoom: 12,
    scrollWheelZoom: false,      // avoid hijacking desktop page scroll
    zoomControl: true,
    attributionControl: true
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  // India bounding box — finite bounds so visitors can't pan into the ocean
  map.fitBounds([[6.4, 68.1], [37.1, 97.4]], { padding: [20, 20] });

  var layerGroup = L.layerGroup().addTo(map);
  var allProjects = [];
  var activeFilter = "all";

  var elCount = document.getElementById("map-count");
  var elEmpty = document.getElementById("map-empty");
  var elLoading = document.getElementById("map-loading");
  var elShell = container.parentElement;

  function labelSingle() { return elCount ? elCount.dataset.labelSingle : "location shown"; }
  function labelPlural() { return elCount ? elCount.dataset.labelPlural : "locations shown"; }

  function markerIcon(project) {
    var color = CATEGORY_COLORS[project.category] || CATEGORY_COLORS.other;
    var ring = project.status === "ongoing" ? "1px dashed #30332B" : "1px solid #ffffff";
    return L.divIcon({
      className: "gvp-pin",
      html: '<span class="gvp-pin__dot" style="background:' + color + ';box-shadow:0 2px 8px rgba(40,40,30,.35);' +
        'outline:' + ring + ';outline-offset:-2px;"></span>',
      iconSize: [22, 22],
      iconAnchor: [11, 11],
      popupAnchor: [0, -12]
    });
  }

  function popupHtml(p) {
    var status = p.status === "completed" ? "Completed" : "Ongoing";
    var place = [p.locality, p.district, p.state].filter(Boolean).join(", ");
    var rows = "";
    if (place) rows += '<p class="map-popup__row"><strong>Location</strong>' + esc(place) + "</p>";
    rows += '<p class="map-popup__row"><strong>Category</strong>' + esc(title(p.category)) + "</p>";
    rows += '<p class="map-popup__row"><strong>Status</strong><span class="map-popup__status map-popup__status--' +
      status.toLowerCase() + '">' + status + "</span></p>";
    if (p.capacity) rows += '<p class="map-popup__row"><strong>Capacity</strong>' + esc(p.capacity) + "</p>";
    if (p.installation_date) rows += '<p class="map-popup__row"><strong>Installed</strong>' + esc(p.installation_date) + "</p>";
    if (p.description) rows += '<p class="map-popup__desc">' + esc(p.description) + "</p>";
    return '<div class="map-popup"><h3>' + esc(p.name) + "</h3>" + rows + "</div>";
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function title(s) { return String(s || "").charAt(0).toUpperCase() + String(s || "").slice(1); }

  function matches(p) {
    if (activeFilter === "all") return true;
    if (activeFilter === "completed" || activeFilter === "ongoing") return p.status === activeFilter;
    return p.category === activeFilter;
  }

  function renderMarkers() {
    layerGroup.clearLayers();
    addOperatingLocations(); /* operating locations stay visible on every filter */
    var shown = 0;
    allProjects.forEach(function (p) {
      if (!matches(p)) return;
      shown++;
      L.marker([p.latitude, p.longitude], { icon: markerIcon(p) })
        .bindPopup(popupHtml(p), { className: "gvp-leaflet-popup", maxWidth: 300 })
        .addTo(layerGroup);
    });
    if (elCount) {
      elCount.textContent = shown + " " + (shown === 1 ? labelSingle() : labelPlural());
    }
    if (elEmpty) elEmpty.hidden = shown !== 0;
  }

  /* Company operating locations — distinct neutral markers clearly labelled
     as offices (never presented as completed project sites). */
  function addOperatingLocations() {
    var COMPANY_SITES = [
      { name: "GV Powers — Chennai", lat: 13.0827, lng: 80.2707 },
      { name: "GV Powers — Salem", lat: 11.6643, lng: 78.1462 }
    ];
    COMPANY_SITES.forEach(function (site) {
      var icon = L.divIcon({
        className: "gvp-pin gvp-pin--office",
        html: '<span class="gvp-pin__office-flag" aria-hidden="true"></span>',
        iconSize: [20, 20],
        iconAnchor: [4, 18],
        popupAnchor: [6, -14]
      });
      L.marker([site.lat, site.lng], { icon: icon, opacity: 0.95 })
        .bindPopup(
          '<div class="map-popup map-popup--office"><h3>' + esc(site.name) + "</h3>" +
          '<p class="map-popup__row">Company operating location.<br>Request project references on enquiry.</p></div>',
          { className: "gvp-leaflet-popup", maxWidth: 260 }
        )
        .addTo(layerGroup);
    });
  }

  /* Filter chips */
  document.querySelectorAll("[data-map-filter]").forEach(function (chip) {
    chip.addEventListener("click", function () {
      document.querySelectorAll("[data-map-filter]").forEach(function (c) {
        c.classList.remove("is-active");
        c.setAttribute("aria-pressed", "false");
      });
      chip.classList.add("is-active");
      chip.setAttribute("aria-pressed", "true");
      activeFilter = chip.dataset.mapFilter;
      renderMarkers();
    });
  });

  /* Enable pinch/scroll zoom explicitly on tap for mobile; scroll zoom
     turns on only while the user interacts with the map. */
  map.on("click", function () { map.scrollWheelZoom.enable(); });
  map.on("mouseout", function () { map.scrollWheelZoom.disable(); });

  var mapInvalidated = false;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting && !mapInvalidated) {
        map.invalidateSize();
        mapInvalidated = true;
      }
    });
  }, { threshold: 0.2 });
  io.observe(elShell);

  fetch("/admin/api/public/projects")
    .then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    })
    .then(function (projects) {
      if (elLoading) elLoading.remove();
      allProjects = (projects || []).filter(function (p) {
        return isFinite(p.latitude) && isFinite(p.longitude);
      });
      renderMarkers();
    })
    .catch(function () {
      if (elLoading) elLoading.textContent = "The map could not load. Please refresh.";
    });
})();
