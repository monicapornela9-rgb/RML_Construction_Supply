-- =========================================================================
-- RML Construction Supply - GPS Tracking & Delivery Route Management Schema
-- Database: MySQL 8.0+ / MariaDB 10.4+ (Compatible with XAMPP MySQL)
-- =========================================================================

CREATE DATABASE IF NOT EXISTS `rml_construction` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `rml_construction`;

-- -------------------------------------------------------------------------
-- 1. Users & Roles (Admin, Driver, Customer)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `staff_id` VARCHAR(50) NULL,
    `name` VARCHAR(120) NOT NULL,
    `email` VARCHAR(150) NOT NULL UNIQUE,
    `phone` VARCHAR(30) NULL,
    `address` TEXT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('admin', 'driver', 'customer') NOT NULL DEFAULT 'customer',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 2. Fleet Vehicles / Trucks
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `trucks` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `truck_code` VARCHAR(50) NOT NULL UNIQUE,
    `plate_number` VARCHAR(30) NOT NULL UNIQUE,
    `capacity` VARCHAR(100) NOT NULL,
    `status` ENUM('available', 'in_transit', 'maintenance') NOT NULL DEFAULT 'available',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 3. Customer Orders
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `orders` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `order_code` VARCHAR(50) NOT NULL UNIQUE,
    `customer_id` INT UNSIGNED NOT NULL,
    `recipient_name` VARCHAR(120) NOT NULL,
    `phone` VARCHAR(30) NOT NULL,
    `delivery_address` TEXT NOT NULL,
    `dest_lat` DECIMAL(10, 7) NULL DEFAULT 13.9535000,
    `dest_lng` DECIMAL(10, 7) NULL DEFAULT 121.1550000,
    `order_status` ENUM(
        'pending', 'pending_scheduling', 'for_scheduling', 'awaiting_confirmation',
        'schedule_confirmed', 'pending_payment', 'payment_verified',
        'ready_for_dispatch', 'out_for_delivery', 'in_transit', 'delivered', 'cancelled'
    ) NOT NULL DEFAULT 'for_scheduling',
    `total_amount` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `assigned_date` DATE NULL,
    `assigned_time_slot` VARCHAR(100) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_orders_customer` FOREIGN KEY (`customer_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 4. Deliveries (Fleet Assignments & Real-Time Tracking State)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `deliveries` (
    `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `delivery_code` VARCHAR(50) NOT NULL UNIQUE,
    `order_id` INT UNSIGNED NOT NULL UNIQUE,
    `driver_id` INT UNSIGNED NULL,
    `truck_id` INT UNSIGNED NULL,
    `delivery_window` VARCHAR(100) NULL,
    `delivery_status` ENUM(
        'queued', 'assigned', 'authorized', 'ready_for_dispatch',
        'loading', 'en_route', 'delivered', 'cancelled'
    ) NOT NULL DEFAULT 'queued',
    `current_lat` DECIMAL(10, 7) NOT NULL DEFAULT 13.9411000, -- Lipa Depot Latitude
    `current_lng` DECIMAL(10, 7) NOT NULL DEFAULT 121.1631000, -- Lipa Depot Longitude
    `dest_lat` DECIMAL(10, 7) NULL DEFAULT 13.9535000,
    `dest_lng` DECIMAL(10, 7) NULL DEFAULT 121.1550000,
    `estimated_distance_km` DECIMAL(6, 2) NULL,
    `estimated_duration_min` INT UNSIGNED NULL,
    `tracking_active` TINYINT(1) NOT NULL DEFAULT 0,
    `last_gps_update` DATETIME NULL,
    `recipient_received_by` VARCHAR(120) NULL,
    `delivery_notes` TEXT NULL,
    `quantity_received` TEXT NULL,
    `completion_time` VARCHAR(50) NULL,
    `delivered_at` DATETIME NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_deliveries_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_deliveries_driver` FOREIGN KEY (`driver_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_deliveries_truck` FOREIGN KEY (`truck_id`) REFERENCES `trucks` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- 5. Delivery Locations (Historical GPS Breadcrumb Pings)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `delivery_locations` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `delivery_id` INT UNSIGNED NOT NULL,
    `driver_id` INT UNSIGNED NOT NULL,
    `latitude` DECIMAL(10, 7) NOT NULL,
    `longitude` DECIMAL(10, 7) NOT NULL,
    `accuracy` DECIMAL(6, 2) NULL DEFAULT 10.00,
    `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_deliv_loc_deliv` (`delivery_id`),
    INDEX `idx_deliv_loc_driver` (`driver_id`),
    INDEX `idx_deliv_loc_recorded` (`recorded_at`),
    CONSTRAINT `fk_deliv_loc_deliv` FOREIGN KEY (`delivery_id`) REFERENCES `deliveries` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_deliv_loc_driver` FOREIGN KEY (`driver_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------
-- Sample Seed Data (Lipa City & Batangas Depot)
-- -------------------------------------------------------------------------
INSERT INTO `users` (`id`, `staff_id`, `name`, `email`, `phone`, `password_hash`, `role`) VALUES
(1, 'ADM-001', 'Admin Officer', 'admin@rml.ph', '0917 555 0100', 'pbkdf2:sha256:600000$demo', 'admin'),
(2, 'DRV-001', 'Juan Dela Cruz', 'juan.driver@rml.ph', '0917 555 0140', 'pbkdf2:sha256:600000$demo', 'driver'),
(3, 'DRV-002', 'Ricardo Santos', 'ricardo.driver@rml.ph', '0917 555 0141', 'pbkdf2:sha256:600000$demo', 'driver'),
(4, 'CUST-001', 'Monica Pornela', 'customer@gmail.com', '0917 555 0128', 'pbkdf2:sha256:600000$demo', 'customer')
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`);

INSERT INTO `trucks` (`id`, `truck_code`, `plate_number`, `capacity`, `status`) VALUES
(1, 'RML-07', 'DAE 4402', '12 Tons / 6 Wheeler Dump Truck', 'in_transit'),
(2, 'RML-05', 'NBF 1970', '8 Tons / 4 Wheeler Forward', 'available'),
(3, 'RML-03', 'CAA 6808', '15 Tons / 10 Wheeler Boom Truck', 'available')
ON DUPLICATE KEY UPDATE `truck_code`=VALUES(`truck_code`);

INSERT INTO `orders` (`id`, `order_code`, `customer_id`, `recipient_name`, `phone`, `delivery_address`, `dest_lat`, `dest_lng`, `order_status`, `total_amount`, `assigned_date`, `assigned_time_slot`) VALUES
(1, '#RML-8700', 4, 'Monica Pornela', '0917 555 0128', 'Summer Hills, Rosewood Blk 51 Lot 2, Lipa City, Batangas', 13.9535000, 121.1550000, 'out_for_delivery', 48500.00, '2026-11-24', 'Morning (08:00 - 12:00)')
ON DUPLICATE KEY UPDATE `order_code`=VALUES(`order_code`);

INSERT INTO `deliveries` (`id`, `delivery_code`, `order_id`, `driver_id`, `truck_id`, `delivery_window`, `delivery_status`, `current_lat`, `current_lng`, `dest_lat`, `dest_lng`, `estimated_distance_km`, `estimated_duration_min`, `tracking_active`, `last_gps_update`) VALUES
(1, 'DLV-1124-8700', 1, 2, 1, 'Morning (08:00 - 12:00)', 'en_route', 13.9455000, 121.1605000, 13.9535000, 121.1550000, 3.85, 8, 1, NOW())
ON DUPLICATE KEY UPDATE `delivery_code`=VALUES(`delivery_code`);

INSERT INTO `delivery_locations` (`delivery_id`, `driver_id`, `latitude`, `longitude`, `accuracy`, `recorded_at`) VALUES
(1, 2, 13.9411000, 121.1631000, 6.50, DATE_SUB(NOW(), INTERVAL 4 MINUTE)),
(1, 2, 13.9432000, 121.1620000, 7.20, DATE_SUB(NOW(), INTERVAL 2 MINUTE)),
(1, 2, 13.9455000, 121.1605000, 8.00, NOW());
