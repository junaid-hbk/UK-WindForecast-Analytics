-- Runs once on first container start.
-- Creates the isolated test database used by pytest and grants the application
-- user access to it. Without the GRANT, every database-backed test fails with
-- "Access denied for user 'windpulse' to database 'windpulse_test'" because the
-- entrypoint only grants privileges on the primary database.
CREATE DATABASE IF NOT EXISTS windpulse_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

GRANT ALL PRIVILEGES ON windpulse_test.* TO 'windpulse'@'%';
FLUSH PRIVILEGES;
