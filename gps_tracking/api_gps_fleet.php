<?php
/**
 * RML Construction Supply - Live Fleet Overview Endpoint (PHP / MySQL)
 * Returns all active delivery vehicles and their current GPS positions
 */

require_once __DIR__ . '/db_config.php';

try {
    $stmt = $pdo->query("
        SELECT d.id, d.delivery_code, d.delivery_status, d.current_lat, d.current_lng, 
               d.dest_lat, d.dest_lng, d.last_gps_update, d.tracking_active,
               u.name AS driver_name, u.phone AS driver_phone,
               t.truck_code, t.plate_number,
               o.order_code, o.recipient_name, o.delivery_address
        FROM deliveries d
        LEFT JOIN users u ON d.driver_id = u.id
        LEFT JOIN trucks t ON d.truck_id = t.id
        LEFT JOIN orders o ON d.order_id = o.id
        ORDER BY 
            CASE 
                WHEN d.delivery_status = 'en_route' THEN 1
                WHEN d.delivery_status = 'loading' THEN 2
                WHEN d.delivery_status = 'authorized' THEN 3
                ELSE 4
            END,
            d.id DESC
        LIMIT 20
    ");
    $deliveries = $stmt->fetchAll();

    $result = [];
    foreach ($deliveries as $deliv) {
        $is_stale = false;
        if (!empty($deliv['last_gps_update']) && in_array($deliv['delivery_status'], ['en_route', 'loading'])) {
            $diff = time() - strtotime($deliv['last_gps_update']);
            $is_stale = ($diff > 120);
        }

        $deliv['is_stale']   = $is_stale;
        $deliv['depot_lat']  = 13.9411;
        $deliv['depot_lng']  = 121.1631;
        $deliv['dest_lat']   = (float)($deliv['dest_lat'] ?: 13.9535);
        $deliv['dest_lng']   = (float)($deliv['dest_lng'] ?: 121.1550);
        $deliv['current_lat']= (float)($deliv['current_lat'] ?: 13.9411);
        $deliv['current_lng']= (float)($deliv['current_lng'] ?: 121.1631);
        $result[] = $deliv;
    }

    echo json_encode([
        'ok'     => true,
        'count'  => count($result),
        'fleet'  => $result
    ]);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => $e->getMessage()]);
}
