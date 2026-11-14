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

  const lat = initialLat || 13.9411;
  const lng = initialLng || 121.1631;

  const map = L.map(mapId).setView([lat, lng], 14);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  // Custom Truck Icon
  const truckIcon = L.divIcon({
    className: "custom-truck-pin",
    html: '<div style="background-color:#C83126;color:white;border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.3);border:2px solid white;"><i class="bi bi-truck"></i></div>',
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });

  const marker = L.marker([lat, lng], { icon: truckIcon })
    .addTo(map)
    .bindPopup("<strong>RML Delivery Truck</strong><br>In transit to delivery address")
    .openPopup();

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
              data.delivery_code +
              ")</strong><br>Status: " +
              data.delivery_status.replace("_", " ").toUpperCase() +
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
 * Admin Fleet Live Map
 */
function initLiveGpsMap(mapId, defaultDeliveryId, defaultLat, defaultLng) {
  const mapEl = document.getElementById(mapId);
  if (!mapEl || typeof L === "undefined") return;

  const lat = defaultLat || 13.9411;
  const lng = defaultLng || 121.1631;

  const map = L.map(mapId).setView([lat, lng], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  let fleetMarkers = {};

  const truckIcon = L.divIcon({
    className: "custom-fleet-pin",
    html: '<div style="background-color:#1F5776;color:white;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 5px rgba(0,0,0,0.3);border:2px solid white;"><i class="bi bi-truck"></i></div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
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

        if (!trucks || trucks.length === 0) {
          // If no active trucks in transit, place depot marker
          if (!fleetMarkers["depot"]) {
            fleetMarkers["depot"] = L.marker([13.9411, 121.1631])
              .addTo(map)
              .bindPopup("<strong>RML Yard / Depot</strong><br>Lipa City, Batangas");
          }
          return;
        }

        trucks.forEach((t) => {
          if (!t.current_lat || !t.current_lng) return;
          const pos = [t.current_lat, t.current_lng];
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
            "Status: <span class='badge bg-primary'>" +
            t.delivery_status +
            "</span>";

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

  updateFleet();
  setInterval(updateFleet, 5000);
}
