CREATE TABLE records (id TEXT PRIMARY KEY NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX records_kind_time ON records(kind, created_at);
