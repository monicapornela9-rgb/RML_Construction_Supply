# RML Construction Supply - GPS Tracking & Delivery Route Management System

## 1. Overview
This system provides an end-to-end, open-source real-time GPS tracking and delivery route management solution for **RML Construction Supply** (Lipa City, Batangas).

### Core Open-Source Technologies (100% Free & Open-Source)
- **OpenStreetMap (OSM):** Base map data and slippy tile rendering (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`).
- **Leaflet.js:** Lightweight interactive map library handling markers, smooth animations, layers, tooltips, and polylines.
- **Browser Geolocation API (`navigator.geolocation.watchPosition`):** Native hardware GPS streaming on driver mobile devices with accuracy tracking and graceful fallback error handling.
- **Open Source Routing Machine (OSRM):** Road-network routing calculating exact driving turn polylines, travel distance (km), and ETA duration (minutes) across Lipa City and Batangas.
- **Backend & Real-Time AJAX Polling:**
  - **Live Stack:** Python / Flask + SQLite (`RML/routes.py`, `RML/db.py`, `RML/templates/`).
  - **PHP / MySQL Reference Stack:** Standalone scripts located in this directory (`gps_tracking/`).

---

## 2. Directory Structure & Key Files

```
RML_Construction_Supply/
├── RML/
│   ├── app.py                            # Flask application core
│   ├── db.py                             # Database schema & delivery_locations table
│   ├── routes.py                         # GPS APIs, OSRM routing, dispatch & live console
│   ├── static/
│   │   ├── css/style.css                 # Map styling, custom pulse markers, layout
│   │   └── js/main.js                    # Fleet map overview, tracking, and polling
│   └── templates/
│       ├── admin/
│       │   ├── deliveries.html           # Fleet dispatch with map selector & Live GPS buttons
│       │   └── delivery_live_tracking.html # Dedicated Admin GPS Tracking Console
│       ├── customer/
│       │   └── tracking.html             # Customer order tracking map with OSRM route
│       └── driver/
│           └── delivery_task.html        # Driver dashboard with route preview & watchPosition()
└── gps_tracking/
    ├── README.md                         # This architecture guide
    ├── db_config.php                     # PDO MySQL connection
    ├── schema_gps_tracking.sql           # MySQL DDL with deliveries and delivery_locations
    ├── api_gps_update.php                # Driver GPS location update endpoint
    ├── api_gps_track.php                 # Live delivery tracking query endpoint
    ├── api_gps_fleet.php                 # Active fleet overview endpoint
    └── live_tracking.php                 # Standalone PHP Leaflet + OSRM tracking view
```

---

## 3. Database Schema

### Table: `delivery_locations` (Breadcrumb Tracking History)
| Column | Type | Description |
|---|---|---|
| `id` | INTEGER / BIGINT | Primary key |
| `delivery_id` | INTEGER | Foreign key referencing `deliveries(id)` |
| `driver_id` | INTEGER | Foreign key referencing `users(id)` |
| `latitude` | DECIMAL / REAL | Driver GPS latitude (-90 to 90) |
| `longitude` | DECIMAL / REAL | Driver GPS longitude (-180 to 180) |
| `accuracy` | REAL | Geolocation accuracy in meters (e.g. ±8.5m) |
| `recorded_at` | DATETIME | Timestamp of GPS ping |

### Table: `deliveries` (Active State)
- `current_lat`, `current_lng`: Most recent coordinates.
- `dest_lat`, `dest_lng`: Delivery destination coordinates (geocoded from address).
- `tracking_active`: Boolean flag indicating if driver is actively broadcasting GPS.
- `last_gps_update`: Timestamp of most recent transmission.
- `delivery_status`: Status (`queued`, `assigned`, `authorized`, `loading`, `en_route`, `delivered`).

---

## 4. API Endpoints

### 1. `POST /api/gps/update` & `/api/gps/update/<delivery_id>`
- **Role:** Driver or Admin.
- **Payload:** `{"lat": 13.9455, "lng": 121.1605, "accuracy": 8.0, "start_transit": true}`
- **Action:** Updates `deliveries` table, sets `tracking_active = 1`, logs breadcrumb in `delivery_locations`, and marks order `out_for_delivery`.

### 2. `GET /api/gps/track/<delivery_id>`
- **Role:** Admin, Assigned Driver, or Customer.
- **Output:** Returns full delivery state, vehicle info, driver contact, depot coordinates, destination coordinates, OSRM route metrics, stale signal indicator, and recent breadcrumbs.

### 3. `GET /api/gps/fleet`
- **Role:** Admin.
- **Output:** Returns all active delivery trucks across Batangas for the live fleet map.

### 4. `GET/POST /api/gps/route-osrm`
- **Parameters:** `start_lat`, `start_lng`, `dest_lat`, `dest_lng`.
- **Output:** Returns driving road coordinates, distance in km, and travel time in minutes calculated via Open Source Routing Machine.

---

## 5. Stale Signal & Resilience Safeguards
- **Signal Lost Indicator:** If no GPS coordinates are received within 120 seconds while a delivery is en route, a warning badge (`Signal Lost / Driver Offline`) appears automatically on the Admin and fleet displays.
- **Fallback Road Routing:** If the public OSRM server is temporarily slow or unreachable, the system automatically uses an interpolated road waypoint fallback with Haversine distance calculation, ensuring maps never break.
- **Demo / Simulation Mode:** Both Admin and Driver interfaces include built-in simulation buttons (`Step +200m` and `Auto-Drive`) for testing inside desktop web browsers where mobile GPS hardware is unavailable.
