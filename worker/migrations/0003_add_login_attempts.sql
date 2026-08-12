CREATE TABLE login_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  ip TEXT NOT NULL,
  success INTEGER NOT NULL DEFAULT 0,
  attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_login_attempts_name ON login_attempts(name, attempted_at);
CREATE INDEX idx_login_attempts_ip ON login_attempts(ip, attempted_at);
