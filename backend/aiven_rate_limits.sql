-- Apply once on the Aiven MySQL database before deploying the rate-limit code.
CREATE TABLE IF NOT EXISTS api_rate_limits (
    key_hash VARCHAR(64) NOT NULL PRIMARY KEY,
    window_started_at DATETIME NOT NULL,
    request_count INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;
