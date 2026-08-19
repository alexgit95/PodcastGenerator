BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS generation_jobs (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  job_type TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'blocked')),
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  details_json TEXT,
  FOREIGN KEY (profile_id) REFERENCES generation_profiles(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_profile_started_at ON generation_jobs(profile_id, started_at DESC);

COMMIT;
