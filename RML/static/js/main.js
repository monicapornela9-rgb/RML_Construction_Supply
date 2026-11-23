/**
 * RML Construction Supply - Client-side Scripts
 * Handles Live GPS Tracking, Driver Geolocation, Leaflet Maps, and Live Stock Movement Preview
 */

// Global simulated GPS timer reference
let driverGpsSimTimer = null;

/**
 * Driver GPS broadcast handler
 */
function startDriverGps(deliveryId, statusElId) {
  const statusEl = document.getElementById(statusElId);

  // If simulation button or permission denied, start automatic demo simulation
  function startSimulation() {
    if (driverGpsSimTimer) clearInterval(driverGpsSimTimer);
    if (statusEl) {
      statusEl.className = "small text-success fw-semibold";
      statusEl.textContent = "Live GPS simulation active. Sharing coordinates with dispatch...";
    }
    // Advance simulation immediately and every 5 seconds
    fetch("/api/gps/simulate/" + deliveryId, { method: "POST" })
      .then((res) => res.json())
      .then((data) => {
        if (data.ok && statusEl) {
          statusEl.textContent =
            "Live GPS active · Lat: " + data.lat.toFixed(4) + ", Lng: " + data.lng.toFixed(4);
        }
      });

    driverGpsSimTimer = setInterval(() => {
      fetch("/api/gps/simulate/" + deliveryId, { method: "POST" })
        .then((res) => res.json())
        .then((data) => {
          if (data.ok && statusEl) {
            statusEl.textContent =
              "Live GPS active · Lat: " + data.lat.toFixed(4) + ", Lng: " + data.lng.toFixed(4);
          }
        })
        .catch(() => {});
    }, 5000);
  }

  if (!navigator.geolocation) {
    startSimulation();
    return;
  }

  if (statusEl) {
    statusEl.className = "small text-primary fw-semibold";
    statusEl.textContent = "Acquiring GPS location...";
  }

  navigator.geolocation.getCurrentPosition(
    function (pos) {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      fetch("/api/gps/update/" + deliveryId, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat: lat, lng: lng }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (statusEl && data.ok) {
            statusEl.className = "small text-success fw-semibold";
            statusEl.textContent =
              "Live GPS active · (" + lat.toFixed(4) + ", " + lng.toFixed(4) + ")";
          }
        });

      // Continue watching position
      navigator.geolocation.watchPosition(
        function (p) {
          const wlat = p.coords.latitude;
          const wlng = p.coords.longitude;
          fetch("/api/gps/update/" + deliveryId, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lat: wlat, lng: wlng }),
          })
            .then((res) => res.json())
            .then((data) => {
              if (statusEl && data.ok) {
                statusEl.className = "small text-success fw-semibold";
                statusEl.textContent =
                  "Live GPS active · (" + wlat.toFixed(4) + ", " + wlng.toFixed(4) + ")";
              }
            });
        },
        function () {},
        { enableHighAccuracy: true, maximumAge: 5000 }
      );
    },
    function (err) {
      // Permission denied or unavailable - gracefully fallback to live simulation
      startSimulation();
    },
    { timeout: 6000 }
  );
}

/**
 * Customer Order Live Tracking Leaflet Map
 */
function initTrackingMap(mapId, orderId, initialLat, initialLng) {
  const mapEl = document.getElementById(mapId);
  if (!mapEl || typeof L === "undefined") return;

  const depotLat = 13.9411;
  const depotLng = 121.1631;
  const lat = initialLat || depotLat;
  const lng = initialLng || depotLng;

  const map = L.map(mapId).setView([lat, lng], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors | OSRM",
  }).addTo(map);

  const depotIcon = L.divIcon({
    className: "custom-depot-pin",
    html: '<div style="background-color:#142235;color:white;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.3);border:2px solid white;"><i class="bi bi-building"></i></div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });

  const destIcon = L.divIcon({
    className: "custom-dest-pin",
    html: '<div style="background-color:#059669;color:white;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.3);border:2px solid white;"><i class="bi bi-geo-alt-fill"></i></div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });

  const truckIcon = L.divIcon({
    className: "custom-truck-live-pin",
    html: '<div style="background-color:#C83126;color:white;border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 8px rgba(200,49,38,0.4);border:2px solid white;"><i class="bi bi-truck fs-5"></i></div>',
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });

  const depotMarker = L.marker([depotLat, depotLng], { icon: depotIcon })
    .addTo(map)
    .bindPopup("<strong>RML Lipa City Central Depot</strong><br>Dispatch Center");

  let destMarker = null;
  let routePolyline = null;

  const marker = L.marker([lat, lng], { icon: truckIcon, zIndexOffset: 1000 })
    .addTo(map)
    .bindPopup("<strong>RML Delivery Truck</strong><br>In transit to delivery address")
    .openPopup();

  // Initial fetch for route and destination
  fetch("/api/gps/location/" + orderId)
    .then((res) => res.json())
    .then((data) => {
      if (data.ok) {
        const destLat = data.dest_lat || 13.9535;
        const destLng = data.dest_lng || 121.1550;

        destMarker = L.marker([destLat, destLng], { icon: destIcon })
          .addTo(map)
          .bindPopup("<strong>Your Delivery Site</strong>");

        // Fetch OSRM Route
        fetch("/api/gps/route-osrm?start_lat=" + depotLat + "&start_lng=" + depotLng + "&dest_lat=" + destLat + "&dest_lng=" + destLng)
          .then((r) => r.json())
          .then((rdata) => {
            if (rdata.ok && rdata.coordinates && rdata.coordinates.length > 0) {
              routePolyline = L.polyline(rdata.coordinates, {
                color: "#2563EB",
                weight: 5,
                opacity: 0.85,
                lineJoin: "round",
              }).addTo(map);

              const group = L.featureGroup([depotMarker, destMarker, marker, routePolyline]);
              map.fitBounds(group.getBounds().pad(0.12));
            }
          })
          .catch(() => {});
      }
    })
    .catch(() => {});

  // Poll server for live truck updates every 5 seconds
  setInterval(function () {
    fetch("/api/gps/location/" + orderId)
      .then((res) => res.json())
      .then((data) => {
        if (data.ok && data.lat && data.lng) {
          const newPos = [data.lat, data.lng];
          marker.setLatLng(newPos);
          marker.getPopup().setContent(
            "<strong>RML Delivery Truck (" +
              (data.delivery_code || "RML") +
              ")</strong><br>Status: " +
              (data.delivery_status || "").replace("_", " ").toUpperCase() +
              "<br>Driver: " +
              (data.driver_name || "Assigned Driver") +
              "<br><small class='text-muted'>Updated: " +
              (data.last_gps_update || "Just now") +
              "</small>"
          );
        }
      })
      .catch(() => {});
  }, 5000);
}

/**
 * Admin Fleet Live Map with Overview and Dedicated Route Modes
 */
function initLiveGpsMap(mapId, defaultDeliveryId, defaultLat, defaultLng) {
  const mapEl = document.getElementById(mapId);
  if (!mapEl || typeof L === "undefined") return;

  const depotLat = 13.9411;
  const depotLng = 121.1631;
  const lat = defaultLat || depotLat;
  const lng = defaultLng || depotLng;

  const map = L.map(mapId).setView([lat, lng], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors | OSRM",
  }).addTo(map);

  let fleetMarkers = {};
  let selectedRouteLine = null;
  let selectedDestMarker = null;
  let currentMode = "all";

  // Depot Icon
  const depotIcon = L.divIcon({
    className: "custom-depot-pin",
    html: '<div style="background-color:#142235;color:white;border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.3);border:2px solid white;"><i class="bi bi-building"></i></div>',
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -17],
  });

  // Always render depot marker
  const depotMarker = L.marker([depotLat, depotLng], { icon: depotIcon })
    .addTo(map)
    .bindPopup("<strong>RML Lipa City Central Depot</strong><br><small class='text-muted'>Ayala Highway, Lipa City, Batangas</small>");

  // Truck Icon
  const truckIcon = L.divIcon({
    className: "custom-fleet-pin",
    html: '<div style="background-color:#C83126;color:white;border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 8px rgba(200,49,38,0.4);border:2px solid white;"><i class="bi bi-truck"></i></div>',
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -17],
  });

  // Destination Icon
  const destIcon = L.divIcon({
    className: "custom-dest-pin",
    html: '<div style="background-color:#059669;color:white;border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 8px rgba(0,0,0,0.3);border:2px solid white;"><i class="bi bi-geo-alt-fill"></i></div>',
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -17],
  });

  function updateFleet() {
    fetch("/api/gps/fleet")
      .then((res) => res.json())
      .then((trucks) => {
        const updateBadge = document.getElementById("gps-last-update");
        if (updateBadge) {
          const now = new Date();
          updateBadge.textContent = "Live · " + now.toLocaleTimeString();
        }

        if (!trucks || trucks.length === 0) return;

        trucks.forEach((t) => {
          if (!t.current_lat || !t.current_lng) return;
          const pos = [t.current_lat, t.current_lng];

          let statusBadgeClass = "bg-secondary";
          if (t.delivery_status === "en_route") statusBadgeClass = "bg-primary";
          else if (t.delivery_status === "delivered") statusBadgeClass = "bg-success";
          else if (t.delivery_status === "loading") statusBadgeClass = "bg-warning text-dark";

          let staleBadge = t.is_stale
            ? "<div class='badge bg-warning text-dark border smaller mt-1'><i class='bi bi-exclamation-triangle-fill'></i> Signal Lost (>2m)</div>"
            : "";

          const popupContent =
            "<strong>Truck: " +
            (t.truck_code || "RML") +
            " (" +
            (t.plate_number || "") +
            ")</strong><br>" +
            "Driver: " +
            (t.driver_name || "Assigned Driver") +
            "<br>" +
            "Order: " +
            (t.order_code || "") +
            " &middot; " +
            (t.recipient_name || "") +
            "<br>" +
            "Status: <span class='badge " +
            statusBadgeClass +
            "'>" +
            t.delivery_status.replace("_", " ") +
            "</span>" +
            staleBadge +
            "<div class='mt-2 pt-1 border-top'>" +
            "<a href='/admin/deliveries/" +
            t.id +
            "/tracking' class='btn btn-sm btn-outline-danger py-0 px-2 fw-semibold smaller'>" +
            "<i class='bi bi-broadcast me-1'></i> Open Console</a>" +
            "</div>";

          if (fleetMarkers[t.id]) {
            fleetMarkers[t.id].setLatLng(pos);
            fleetMarkers[t.id].getPopup().setContent(popupContent);
          } else {
            fleetMarkers[t.id] = L.marker(pos, { icon: truckIcon })
              .addTo(map)
              .bindPopup(popupContent);
          }
        });
      })
      .catch(() => {});
  }

  // Handle Mode Switcher
  const selectorEl = document.getElementById("fleetMapSelector");
  const dedicatedBtn = document.getElementById("btnDedicatedTrack");
  const metricsBadge = document.getElementById("fleetRouteMetrics");
  const metricsText = document.getElementById("fleetMetricText");

  function selectDeliveryMode(delId) {
    currentMode = delId;

    if (delId === "all") {
      if (selectedRouteLine) {
        map.removeLayer(selectedRouteLine);
        selectedRouteLine = null;
      }
      if (selectedDestMarker) {
        map.removeLayer(selectedDestMarker);
        selectedDestMarker = null;
      }
      if (dedicatedBtn) dedicatedBtn.classList.add("d-none");
      if (metricsBadge) metricsBadge.classList.add("d-none");

      map.setView([depotLat, depotLng], 13);
    } else {
      const opt = selectorEl.querySelector("option[value='" + delId + "']");
      if (!opt) return;

      const destLat = parseFloat(opt.getAttribute("data-destlat") || 13.9535);
      const destLng = parseFloat(opt.getAttribute("data-destlng") || 121.1550);
      const code = opt.getAttribute("data-code") || "Delivery";
      const destAddr = opt.getAttribute("data-dest") || "Site";

      if (dedicatedBtn) {
        dedicatedBtn.href = "/admin/deliveries/" + delId + "/tracking";
        dedicatedBtn.classList.remove("d-none");
      }

      if (selectedDestMarker) map.removeLayer(selectedDestMarker);
      selectedDestMarker = L.marker([destLat, destLng], { icon: destIcon })
        .addTo(map)
        .bindPopup("<strong>" + code + " Destination</strong><br><small class='text-muted'>" + destAddr + "</small>");

      fetch("/api/gps/route-osrm?start_lat=" + depotLat + "&start_lng=" + depotLng + "&dest_lat=" + destLat + "&dest_lng=" + destLng)
        .then((res) => res.json())
        .then((data) => {
          if (data.ok && data.coordinates && data.coordinates.length > 0) {
            if (selectedRouteLine) map.removeLayer(selectedRouteLine);
            selectedRouteLine = L.polyline(data.coordinates, {
              color: "#2563EB",
              weight: 5,
              opacity: 0.85,
              lineJoin: "round",
            }).addTo(map);

            if (metricsBadge && metricsText) {
              metricsBadge.classList.remove("d-none");
              metricsText.textContent = data.distance_km + " km · ~" + data.duration_min + " min drive";
            }

            const boundsGroup = [depotMarker, selectedDestMarker, selectedRouteLine];
            if (fleetMarkers[delId]) boundsGroup.push(fleetMarkers[delId]);
            map.fitBounds(L.featureGroup(boundsGroup).getBounds().pad(0.12));
          }
        })
        .catch(() => {});
    }
  }

  if (selectorEl) {
    selectorEl.addEventListener("change", function () {
      selectDeliveryMode(this.value);
    });
  }

  updateFleet();
  setInterval(updateFleet, 5000);
}
