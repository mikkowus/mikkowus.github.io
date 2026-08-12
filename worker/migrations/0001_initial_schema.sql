CREATE TABLE contributors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  access_code_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'contributor',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
  token TEXT PRIMARY KEY,
  contributor_id INTEGER NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TEXT NOT NULL
);

CREATE INDEX idx_sessions_expires ON sessions(expires_at);

CREATE TABLE submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  status TEXT NOT NULL DEFAULT 'pending',
  name TEXT NOT NULL,
  description TEXT,
  region TEXT,
  water_body_name TEXT,
  water_body_type TEXT,
  access_type TEXT,
  parking_notes TEXT,
  tags TEXT,
  nearest_gauge_site_no TEXT,
  source_url TEXT,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  submitted_by INTEGER NOT NULL REFERENCES contributors(id),
  submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_by INTEGER REFERENCES contributors(id),
  reviewed_at TEXT,
  reviewer_notes TEXT
);

CREATE INDEX idx_submissions_status ON submissions(status);
