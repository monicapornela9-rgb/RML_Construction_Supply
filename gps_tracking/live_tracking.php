<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RML Live GPS Tracking & Route Console (PHP / MySQL)</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    :root {
      --rml-red: #C83126;
      --rml-navy: #142235;
      --rml-blue: #2563EB;
    }
    body {
      background-color: #F8FAFC;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    .custom-depot-pin, .custom-dest-pin, .custom-truck-pin {
      display: flex !important;
      align-items: center;
      justify-content: center;
    }
    .truck-pulse::after {
      content: "";
      position: absolute;
      width: 44px;
      height: 44px;
      border-radius: 50%;
      border: 2px solid var(--rml-red);
      opacity: 0.8;
      animation: pulse 2s infinite ease-out;
      pointer-events: none;
    }
    @keyframes pulse {
      0% { transform: scale(0.6); opacity: 0.9; }
      100% { transform: scale(1.6); opacity: 0; }
    }
  </style>
</head>
<body class="py-4">
<div class="container-fluid px-4">
  <!-- Header -->
  <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
    <div>
      <div class="text-muted small">RML Construction Supply &middot; Fleet Operations</div>
      <h2 class="fw-bold mb-0">Live GPS Tracking &amp; Route Management</h2>
      <div class="text-muted small">Powered by Leaflet.js, OpenStreetMap, and Open Source Routing Machine (OSRM)</div>
    </div>
    <div class="d-flex align-items-center gap-2">
      <span class="badge bg-success p-2">
        <span class="spinner-grow spinner-grow-sm me-1" role="status"></span>
        <span id="updateStatus">Live &middot; Updating every 5s</span>
      </span>
      <button id="btnManualRefresh" class="btn btn-outline-secondary btn-sm">
        <i class="bi bi-arrow-clockwise"></i> Refresh Now
      </button>
    </div>
  </div>

  <div class="row g-4">
    <!-- Map Container -->
    <div class="col-lg-8">
      <div class="card border-0 shadow-sm overflow-hidden">
        <div class="card-header bg-white py-2 px-3 d-flex justify-content-between align-items-center">
          <span class="badge bg-danger-subtle text-danger border border-danger-subtle fw-semibold">
            <i class="bi bi-geo-alt-fill me-1"></i> OSM Tile Layer &amp; OSRM Polyline
          </span>
          <span id="staleAlert" class="badge bg-warning text-dark border d-none">
            <i class="bi bi-exclamation-triangle-fill"></i> Driver Signal Stale (>2m)
          </span>
        </div>
        <div id="phpTrackingMap" style="height: 520px; width: 100%;"></div>
        <div class="card-footer bg-light p-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div class="small text-muted d-flex gap-3">
            <span><strong style="color: #142235;">&#9632;</strong> RML Lipa Depot</span>
            <span><strong style="color: #C83126;">&#9632;</strong> Live Truck Marker</span>
            <span><strong style="color: #059669;">&#9632;</strong> Customer Site</span>
          </div>
          <div>
            <button id="btnStepGps" class="btn btn-sm btn-outline-danger">
              <i class="bi bi-play-fill"></i> Simulate Driver Step
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Logistics Metrics -->
    <div class="col-lg-4">
      <div class="card border-0 shadow-sm p-3 mb-3">
        <h6 class="fw-bold mb-3"><i class="bi bi-speedometer2 text-danger me-2"></i>Route Metrics (OSRM)</h6>
        <div class="row g-2 mb-3 text-center">
          <div class="col-6">
            <div class="p-3 bg-light rounded border">
              <div class="text-muted smaller">Total Distance</div>
              <div id="metricDistance" class="fs-4 fw-bold text-dark">-- km</div>
            </div>
          </div>
          <div class="col-6">
            <div class="p-3 bg-light rounded border">
              <div class="text-muted smaller">Est. Travel Time</div>
              <div id="metricDuration" class="fs-4 fw-bold text-primary">-- min</div>
            </div>
          </div>
        </div>
        <div class="list-group list-group-flush small">
          <div class="list-group-item px-0 py-2 d-flex justify-content-between">
            <span class="text-muted">Truck / Vehicle</span>
            <span id="infoTruck" class="fw-bold">RML-07 (DAE 4402)</span>
          </div>
          <div class="list-group-item px-0 py-2 d-flex justify-content-between">
            <span class="text-muted">Driver Name</span>
            <span id="infoDriver" class="fw-semibold">Juan Dela Cruz</span>
          </div>
          <div class="list-group-item px-0 py-2 d-flex justify-content-between">
            <span class="text-muted">Order Code</span>
            <span id="infoOrder" class="fw-semibold">#RML-8700</span>
          </div>
          <div class="list-group-item px-0 py-2 d-flex justify-content-between">
            <span class="text-muted">Last GPS Update</span>
            <span id="infoLastPing" class="fw-semibold">Just now</span>
          </div>
          <div class="list-group-item px-0 py-2 d-flex justify-content-between">
            <span class="text-muted">Current Lat / Lng</span>
            <span id="infoCoords" class="font-monospace smaller">13.9455, 121.1605</span>
          </div>
        </div>
      </div>

      <!-- Destination Card -->
      <div class="card border-0 shadow-sm p-3 mb-3">
        <h6 class="fw-bold mb-2"><i class="bi bi-pin-map text-success me-2"></i>Destination Site</h6>
        <div class="small">
          <div id="infoRecipient" class="fw-bold">Monica Pornela</div>
          <div id="infoAddress" class="text-muted mb-2">Summer Hills, Rosewood Blk 51 Lot 2, Lipa City, Batangas</div>
        </div>
      </div>

      <!-- Breadcrumbs Log -->
      <div class="card border-0 shadow-sm p-3">
        <h6 class="fw-bold mb-2"><i class="bi bi-clock-history me-2"></i>GPS Breadcrumbs Log</h6>
        <div class="table-responsive" style="max-height: 160px; overflow-y: auto;">
          <table class="table table-sm table-borderless smaller mb-0">
            <thead>
              <tr class="text-muted border-bottom">
                <th>Time</th>
                <th>Lat</th>
                <th>Lng</th>
              </tr>
            </thead>
            <tbody id="crumbTableBody">
              <tr>
                <td colspan="3" class="text-center text-muted">Awaiting breadcrumbs...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function () {
  const deliveryId = 1;
  const depotCoords = [13.9411, 121.1631];
  let destCoords = [13.9535, 121.1550];
  let truckPos = [13.9455, 121.1605];

  const map = L.map('phpTrackingMap').setView(truckPos, 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors | OSRM',
  }).addTo(map);

  const depotIcon = L.divIcon({
    className: 'custom-depot-pin',
    html: '<div style="background-color:#142235;color:white;border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.3);border:2px solid white;"><i class="bi bi-building"></i></div>',
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });

  const destIcon = L.divIcon({
    className: 'custom-dest-pin',
    html: '<div style="background-color:#059669;color:white;border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.3);border:2px solid white;"><i class="bi bi-geo-alt-fill"></i></div>',
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });

  const truckIcon = L.divIcon({
    className: 'custom-truck-pin truck-pulse',
    html: '<div style="background-color:#C83126;color:white;border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 8px rgba(200,49,38,0.4);border:2px solid white;"><i class="bi bi-truck fs-5"></i></div>',
    iconSize: [38, 38],
    iconAnchor: [19, 19],
  });

  const depotMarker = L.marker(depotCoords, { icon: depotIcon }).addTo(map).bindPopup('<strong>RML Central Depot</strong>');
  const destMarker = L.marker(destCoords, { icon: destIcon }).addTo(map).bindPopup('<strong>Customer Site</strong>');
  const truckMarker = L.marker(truckPos, { icon: truckIcon }).addTo(map).bindPopup('<strong>RML Delivery Truck</strong>');

  let routePolyline = null;

  // Fetch OSRM Road Route
  function fetchOsrmRoute(start, dest) {
    const url = 'https://router.project-osrm.org/route/v1/driving/' + start[1] + ',' + start[0] + ';' + dest[1] + ',' + dest[0] + '?overview=full&geometries=geojson';
    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
          const route = data.routes[0];
          document.getElementById('metricDistance').textContent = (route.distance / 1000).toFixed(2) + ' km';
          document.getElementById('metricDuration').textContent = Math.round(route.duration / 60) + ' min';

          const coords = route.geometry.coordinates.map(pt => [pt[1], pt[0]]);
          if (routePolyline) map.removeLayer(routePolyline);

          routePolyline = L.polyline(coords, { color: '#2563EB', weight: 5, opacity: 0.85 }).addTo(map);
          map.fitBounds(L.featureGroup([depotMarker, destMarker, truckMarker, routePolyline]).getBounds().pad(0.12));
        }
      })
      .catch(() => {});
  }
  fetchOsrmRoute(depotCoords, destCoords);

  // Poll PHP API every 5 seconds
  function pollGps() {
    fetch('api_gps_track.php?delivery_id=' + deliveryId)
      .then(res => res.json())
      .then(data => {
        if (!data.ok || !data.delivery) return;
        const d = data.delivery;
        const newPos = [d.current_lat, d.current_lng];
        truckMarker.setLatLng(newPos);

        document.getElementById('infoLastPing').textContent = d.last_gps_update || 'Just now';
        document.getElementById('infoCoords').textContent = d.current_lat.toFixed(5) + ', ' + d.current_lng.toFixed(5);
        document.getElementById('infoTruck').textContent = d.truck_code + ' (' + d.plate_number + ')';
        document.getElementById('infoDriver').textContent = d.driver_name;
        document.getElementById('infoOrder').textContent = d.order_code;
        document.getElementById('infoRecipient').textContent = d.recipient_name;
        document.getElementById('infoAddress').textContent = d.delivery_address;

        const staleAlert = document.getElementById('staleAlert');
        if (d.is_stale) staleAlert.classList.remove('d-none');
        else staleAlert.classList.add('d-none');

        // Render breadcrumbs
        if (data.breadcrumbs && data.breadcrumbs.length > 0) {
          const tbody = document.getElementById('crumbTableBody');
          let html = '';
          data.breadcrumbs.slice(-8).reverse().forEach(c => {
            const time = c.recorded_at ? c.recorded_at.substring(11, 19) : '--:--';
            html += '<tr><td>' + time + '</td><td class="font-monospace">' + parseFloat(c.latitude).toFixed(4) + '</td><td class="font-monospace">' + parseFloat(c.longitude).toFixed(4) + '</td></tr>';
          });
          tbody.innerHTML = html;
        }
      })
      .catch(() => {});
  }

  setInterval(pollGps, 5000);

  document.getElementById('btnManualRefresh').addEventListener('click', pollGps);

  // Simulate Step via PHP update endpoint
  document.getElementById('btnStepGps').addEventListener('click', function () {
    const lat = truckPos[0] + (destCoords[0] - truckPos[0]) * 0.15;
    const lng = truckPos[1] + (destCoords[1] - truckPos[1]) * 0.15;
    truckPos = [lat, lng];

    fetch('api_gps_update.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        delivery_id: deliveryId,
        lat: lat,
        lng: lng,
        accuracy: 8.5
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.ok) {
          truckMarker.setLatLng([lat, lng]);
          pollGps();
        }
      });
  });
});
</script>
</body>
</html>
