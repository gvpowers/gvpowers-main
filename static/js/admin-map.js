/* ============================================================
   GV POWERS — admin-map.js
   Add/Edit project form + interactive preview map with clickable,
   draggable marker. Used on /admin/projects only (auth required).
   ============================================================ */
(function () {
  "use strict";

  var mapEl = document.getElementById("admin-preview-map");
  var form = document.getElementById("project-form");
  if (!mapEl || !form || typeof L === "undefined") return;

  var RO = document.querySelector("meta[name=robots]") !== null; // safety only
  var csrToken = form.querySelector('input[name="csrf_token"]').value;

  var map = L.map(mapEl, { center: [11.66, 78.14], zoom: 6, scrollWheelZoom: true });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(map);

  var marker = null;
  var editingId = null;

  function setMarker(lat, lng) {
    if (!marker) {
      marker = L.marker([lat, lng], { draggable: true, autoPan: true }).addTo(map);
      marker.on("dragend", function () {
        var pos = marker.getLatLng();
        document.getElementById("p-lat").value = pos.lat.toFixed(6);
        document.getElementById("p-lng").value = pos.lng.toFixed(6);
      });
    } else {
      marker.setLatLng([lat, lng]);
    }
    map.setView([lat, lng], Math.max(map.getZoom(), 7));
  }

  map.on("click", function (e) {
    document.getElementById("p-lat").value = e.latlng.lat.toFixed(6);
    document.getElementById("p-lng").value = e.latlng.lng.toFixed(6);
    setMarker(e.latlng.lat, e.latlng.lng);
  });

  ["p-lng", "p-lat"].forEach(function (id) {
    document.getElementById(id).addEventListener("change", function () {
      var lat = parseFloat(document.getElementById("p-lat").value);
      var lng = parseFloat(document.getElementById("p-lng").value);
      if (isFinite(lat) && isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
        setMarker(lat, lng);
      }
    });
  });

  var result = document.getElementById("form-result");
  var submitBtn = document.getElementById("submit-btn");
  var deleteBtn = document.getElementById("delete-btn");
  var formTitle = document.getElementById("form-title");

  function clearForm() {
    editingId = null;
    form.reset();
    document.getElementById("project-id").value = "";
    formTitle.textContent = "Add project location";
    submitBtn.textContent = "Save project";
    deleteBtn.hidden = true;
    result.textContent = "";
  }
  document.getElementById("reset-btn").addEventListener("click", clearForm);

  function fillForm(p) {
    editingId = p.id;
    document.getElementById("project-id").value = p.id;
    document.getElementById("p-name").value = p.name || "";
    document.getElementById("p-category").value = p.category || "solar";
    document.getElementById("p-status").value = p.status || "completed";
    document.getElementById("p-state").value = p.state || "";
    document.getElementById("p-district").value = p.district || "";
    document.getElementById("p-locality").value = p.locality || "";
    document.getElementById("p-lat").value = p.latitude;
    document.getElementById("p-lng").value = p.longitude;
    document.getElementById("p-desc").value = p.description || "";
    document.getElementById("p-date").value = p.installation_date || "";
    document.getElementById("p-capacity").value = p.capacity || "";
    setMarker(parseFloat(p.latitude), parseFloat(p.longitude));
    formTitle.textContent = "Edit project: " + p.name;
    submitBtn.textContent = "Update project";
    deleteBtn.hidden = false;
    result.textContent = "";
    window.scrollTo({ top: form.getBoundingClientRect().top + window.scrollY - 40, behavior: "smooth" });
  }

  document.querySelectorAll(".admin-row-edit").forEach(function (btn) {
    btn.addEventListener("click", function () {
      fillForm(JSON.parse(btn.closest("tr").dataset.project));
    });
  });

  deleteBtn.addEventListener("click", function () {
    if (!editingId) return;
    if (!window.confirm("Delete this project location permanently? This also removes it from the public map.")) return;
    fetch("/admin/api/projects/" + editingId, {
      method: "DELETE",
      headers: { "X-CSRF-Token": csrToken }
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.ok) { location.reload(); }
      else { result.textContent = d.error || "Delete failed."; }
    });
  });

  /* Submit create / update */
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    result.textContent = "Saving…";
    var body = new FormData(form);
    body.delete("project_id");
    var url = editingId
      ? "/admin/api/projects/" + editingId
      : "/admin/api/projects";
    fetch(url, { method: "POST", body: body })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (res.ok && res.data.ok) {
          result.textContent = res.data.message + " Reloading…";
          window.setTimeout(function () { location.reload(); }, 700);
        } else {
          var errs = res.data.errors || [res.data.error || "Save failed."];
          result.textContent = errs.join(" · ");
        }
      })
      .catch(function () { result.textContent = "Network error."; });
  });
})();
