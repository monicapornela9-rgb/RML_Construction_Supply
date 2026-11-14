function startDriverGps(deliveryId, statusElId) {
  const statusEl = document.getElementById(statusElId);
  if (!navigator.geolocation) {
    if (statusEl) statusEl.textContent = "GPS not supported on this browser.";
    return;
  }
  if (statusEl) statusEl.textContent = "Sharing live GPS location...";
  navigator.geolocation.watchPosition(
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
            statusEl.textContent =
              "Live GPS active (" + lat.toFixed(4) + ", " + lng.toFixed(4) + ")";
          }
        });
    },
    function () {
      if (statusEl) statusEl.textContent = "Location permission denied or unavailable.";
    },
    { enableHighAccuracy: true, maximumAge: 10000 }
  );
}

function initTrackingMap(mapId, orderId, initialLat, initialLng) {
  const mapEl = document.getElementById(mapId);
  if (!mapEl || typeof L === "undefined") return;

  const map = L.map(mapId).setView([initialLat, initialLng], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  const marker = L.marker([initialLat, initialLng])
    .addTo(map)
    .bindPopup("RML Delivery Truck")
    .openPopup();

  setInterval(function () {
    fetch("/api/gps/location/" + orderId)
      .then((res) => res.json())
      .then((data) => {
        if (data.ok && data.lat && data.lng) {
          marker.setLatLng([data.lat, data.lng]);
          map.panTo([data.lat, data.lng]);
        }
      });
  }, 8000);
}
