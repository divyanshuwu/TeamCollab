-- Apply once to the existing Aiven MySQL database before enabling API auth fallback.
ALTER TABLE users
  ADD COLUMN auth_user_id VARCHAR(36) NULL;

CREATE UNIQUE INDEX uq_users_auth_user_id
  ON users (auth_user_id);
