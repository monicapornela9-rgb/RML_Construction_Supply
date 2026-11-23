<?php
/**
 * RML Construction Supply - Live Tracking Query Endpoint (PHP / MySQL)
 * Returns live delivery state, destination, depot coords, and GPS breadcrumbs
 */

require_once __DIR__ . '/db_config.php';

$delivery_id = isset($_GET['delivery_id']) ? (int)$_GET['delivery_id'] : 0;

if (!$delivery_id) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Missing delivery_id parameter']);
    exit;
}

const RML_DEPOT_LAT  = 13.9411;
const RML_DEPOT_LNG  = 121.1631;
const RML_DEPOT_NAME = "RML Lipa City Central Depot";

try {
    $stmt = $pdo->prepare("
        SELECT d.*, 
               u.name AS driver_name, u.phone AS driver_phone,
               t.truck_code, t.plate_number,
               o.id AS order_id, o.order_code, o.order_status, o.recipient_name,
               o.phone AS recipient_phone, o.delivery_address, o.assigned_date, o.assigned_time_slot
        FROM deliveries d
        JOIN orders o ON d.order_id = o.id
        LEFT JOIN users u ON d.driver_id = u.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        WHERE d.id = ?
        LIMIT 1
    ");
    $stmt->execute([$delivery_id]);
    $delivery = $stmt->fetch();

    if (!$delivery) {
        http_response_code(404);
        echo json_encode(['ok' => false, 'error' => 'Delivery not found']);
        exit;
    }

    // Fetch recent breadcrumbs
    $bstmt = $pdo->prepare("
        SELECT latitude, longitude, accuracy, recorded_at
        FROM delivery_locations
        WHERE delivery_id = ?
        ORDER BY id DESC
        LIMIT 30
    ");
    $bstmt->execute([$delivery_id]);
    $crumbs = $bstmt->fetchAll();

    // Check if GPS signal is stale (> 2 minutes without update during active transit)
    $is_stale = false;
    if (!empty($delivery['last_gps_update']) && in_array($delivery['delivery_status'], ['en_route', 'loading'])) {
        $diff = time() - strtotime($delivery['last_gps_update']);
        $is_stale = ($diff > 120);
    }

    $dest_lat = $delivery['dest_lat'] ? (float)$delivery['dest_lat'] : 13.9535;
    $dest_lng = $delivery['dest_lng'] ? (float)$delivery['dest_lng'] : 121.1550;

    echo json_encode([
        'ok' => true,
        'delivery' => [
            'id'                     => (int)$delivery['id'],
            'delivery_code'          => $delivery['delivery_code'],
            'delivery_status'        => $delivery['delivery_status'],
            'tracking_active'        => (bool)$delivery['tracking_active'],
            'current_lat'            => (float)$delivery['current_lat'],
            'current_lng'            => (float)$delivery['current_lng'],
            'dest_lat'               => $dest_lat,
            'dest_lng'               => $dest_lng,
            'depot_lat'              => RML_DEPOT_LAT,
            'depot_lng'              => RML_DEPOT_LNG,
            'depot_name'             => RML_DEPOT_NAME,
            'last_gps_update'        => $delivery['last_gps_update'],
            'is_stale'               => $is_stale,
            'driver_name'            => $delivery['driver_name'] ?: 'Juan Dela Cruz',
            'driver_phone'           => $delivery['driver_phone'] ?: '0917 555 0140',
            'truck_code'             => $delivery['truck_code'] ?: 'RML-07',
            'plate_number'           => $delivery['plate_number'] ?: 'DAE 4402',
            'order_code'             => $delivery['order_code'],
            'recipient_name'         => $delivery['recipient_name'],
            'delivery_address'       => $delivery['delivery_address'],
            'assigned_date'          => $delivery['assigned_date'],
            'assigned_time_slot'     => $delivery['assigned_time_slot'],
            'osrm_router_url'        => "https://router.project-osrm.org/route/v1/driving/" . RML_DEPOT_LNG . "," . RML_DEPOT_LAT . ";" . $dest_lng . "," . $dest_lat . "?overview=full&geometries=geojson"
        ],
        'breadcrumbs' => array_reverse($crumbs)
    ]);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => $e->getMessage()]);
}
