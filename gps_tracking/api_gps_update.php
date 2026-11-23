<?php
/**
 * RML Construction Supply - Driver GPS Update Endpoint (PHP / MySQL)
 * Receives real-time coordinates from driver browser via navigator.geolocation.watchPosition()
 */

require_once __DIR__ . '/db_config.php';

// Accept both JSON payload and POST form parameters
$raw_input = file_get_contents('php://input');
$data = json_decode($raw_input, true) ?? $_POST;

$delivery_id   = isset($data['delivery_id']) ? (int)$data['delivery_id'] : (isset($_GET['delivery_id']) ? (int)$_GET['delivery_id'] : 0);
$lat           = isset($data['lat']) ? (float)$data['lat'] : null;
$lng           = isset($data['lng']) ? (float)$data['lng'] : null;
$accuracy      = isset($data['accuracy']) ? (float)$data['accuracy'] : 10.0;
$start_transit = !empty($data['start_transit']);

if (!$delivery_id || $lat === null || $lng === null) {
    http_response_code(400);
    echo json_encode([
        'ok'    => false,
        'error' => 'Missing required parameters: delivery_id, lat, lng'
    ]);
    exit;
}

// Validate coordinate boundaries
if ($lat < -90.0 || $lat > 90.0 || $lng < -180.0 || $lng > 180.0) {
    http_response_code(400);
    echo json_encode([
        'ok'    => false,
        'error' => 'Coordinates out of valid geographical range (-90 to 90, -180 to 180)'
    ]);
    exit;
}

try {
    // 1. Fetch delivery record
    $stmt = $pdo->prepare("SELECT * FROM deliveries WHERE id = ? LIMIT 1");
    $stmt->execute([$delivery_id]);
    $delivery = $stmt->fetch();

    if (!$delivery) {
        http_response_code(404);
        echo json_encode(['ok' => false, 'error' => 'Delivery task not found']);
        exit;
    }

    $driver_id = $delivery['driver_id'] ?: 1;
    $new_status = $delivery['delivery_status'];

    // Auto-advance to en_route if authorized or loading
    if ($start_transit || in_array($new_status, ['assigned', 'authorized', 'loading'])) {
        $new_status = 'en_route';
        $update_status_stmt = $pdo->prepare("UPDATE deliveries SET delivery_status = 'en_route' WHERE id = ?");
        $update_status_stmt->execute([$delivery_id]);

        $update_order_stmt = $pdo->prepare("UPDATE orders SET order_status = 'out_for_delivery' WHERE id = ?");
        $update_order_stmt->execute([$delivery['order_id']]);
    }

    // 2. Update deliveries table with latest coordinates and timestamp
    $update_gps = $pdo->prepare("
        UPDATE deliveries 
        SET current_lat = ?, current_lng = ?, last_gps_update = NOW(), tracking_active = 1
        WHERE id = ?
    ");
    $update_gps->execute([$lat, $lng, $delivery_id]);

    // 3. Record breadcrumb in delivery_locations history table
    $insert_loc = $pdo->prepare("
        INSERT INTO delivery_locations (delivery_id, driver_id, latitude, longitude, accuracy, recorded_at)
        VALUES (?, ?, ?, ?, ?, NOW())
    ");
    $insert_loc->execute([$delivery_id, $driver_id, $lat, $lng, $accuracy]);

    echo json_encode([
        'ok'              => true,
        'delivery_id'     => $delivery_id,
        'lat'             => $lat,
        'lng'             => $lng,
        'accuracy'        => $accuracy,
        'delivery_status' => $new_status,
        'last_gps_update' => date('Y-m-d H:i:s')
    ]);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'ok'    => false,
        'error' => 'Database operation failed: ' . $e->getMessage()
    ]);
}
