<?php
/**
 * RML Construction Supply - Database Connection Configuration
 * PDO connector supporting MySQL / MariaDB (XAMPP standard configuration)
 */

header('Content-Type: application/json; charset=utf-8');

$db_host = 'localhost';
$db_name = 'rml_construction';
$db_user = 'root';
$db_pass = '';
$db_port = 3306;

try {
    $pdo = new PDO("mysql:host={$db_host};port={$db_port};dbname={$db_name};charset=utf8mb4", $db_user, $db_pass, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);
} catch (PDOException $e) {
    // If MySQL connection fails (e.g. running standalone without MySQL active), output JSON error
    http_response_code(500);
    echo json_encode([
        'ok'    => false,
        'error' => 'Database connection failed: ' . $e->getMessage()
    ]);
    exit;
}
