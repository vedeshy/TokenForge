CREATE TABLE runs (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  status TEXT NOT NULL,
  model TEXT NOT NULL,
  runtimes TEXT[] NOT NULL,
  config_yaml TEXT NOT NULL,
  html_url TEXT,
  csv_url TEXT,
  raw_url TEXT
);
