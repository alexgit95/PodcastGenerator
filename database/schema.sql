PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  default_weight INTEGER NOT NULL DEFAULT 1 CHECK (default_weight > 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rss_sources (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  health_status TEXT NOT NULL DEFAULT 'unknown' CHECK (health_status IN ('unknown', 'healthy', 'error')),
  health_message TEXT,
  last_checked_at TEXT,
  last_success_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS category_sources (
  category_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (category_id, source_id),
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
  FOREIGN KEY (source_id) REFERENCES rss_sources(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS generation_profiles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  generation_mode TEXT NOT NULL DEFAULT 'llm' CHECK (generation_mode IN ('llm', 'deterministic')),
  audio_generation_mode TEXT NOT NULL DEFAULT 'local' CHECK (audio_generation_mode IN ('local', 'cloud')),
  duration_target_minutes INTEGER NOT NULL DEFAULT 10 CHECK (duration_target_minutes > 0),
  max_item_age_hours INTEGER NOT NULL DEFAULT 48 CHECK (max_item_age_hours > 0),
  per_episode_token_cap INTEGER NOT NULL DEFAULT 28000 CHECK (per_episode_token_cap > 0),
  monthly_api_budget_eur_cents INTEGER NOT NULL DEFAULT 100 CHECK (monthly_api_budget_eur_cents >= 0),
  schedule_cron TEXT NOT NULL DEFAULT '0 8 * * 1,3,5',
  timezone TEXT NOT NULL DEFAULT 'Europe/Paris',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deterministic_settings_global (
  profile_id TEXT PRIMARY KEY,
  version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
  target_duration_sec INTEGER NOT NULL DEFAULT 600 CHECK (target_duration_sec BETWEEN 120 AND 3600),
  speech_rate_wpm INTEGER NOT NULL DEFAULT 155 CHECK (speech_rate_wpm BETWEEN 100 AND 220),
  freshness_hours_max INTEGER NOT NULL DEFAULT 48 CHECK (freshness_hours_max > 0),
  max_items_per_category_default INTEGER NOT NULL DEFAULT 3 CHECK (max_items_per_category_default BETWEEN 1 AND 10),
  min_items_per_category_default INTEGER NOT NULL DEFAULT 1 CHECK (min_items_per_category_default BETWEEN 1 AND 10),
  scoring_weights_json TEXT NOT NULL,
  extractive_rules_json TEXT NOT NULL,
  trim_policy_json TEXT NOT NULL,
  fallback_policy_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES generation_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS deterministic_settings_category (
  profile_id TEXT NOT NULL,
  category_id TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  weight INTEGER NOT NULL DEFAULT 1 CHECK (weight > 0),
  max_items INTEGER CHECK (max_items IS NULL OR (max_items BETWEEN 1 AND 10)),
  templates_json TEXT,
  scoring_override_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (profile_id, category_id),
  FOREIGN KEY (profile_id) REFERENCES generation_profiles(id) ON DELETE CASCADE,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS generation_profile_categories (
  profile_id TEXT NOT NULL,
  category_id TEXT NOT NULL,
  weight INTEGER NOT NULL CHECK (weight > 0),
  PRIMARY KEY (profile_id, category_id),
  FOREIGN KEY (profile_id) REFERENCES generation_profiles(id) ON DELETE CASCADE,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS monthly_api_spend (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id TEXT NOT NULL,
  month_key TEXT NOT NULL,
  spent_eur_cents INTEGER NOT NULL DEFAULT 0 CHECK (spent_eur_cents >= 0),
  hard_cap_eur_cents INTEGER NOT NULL CHECK (hard_cap_eur_cents >= 0),
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (profile_id, month_key),
  FOREIGN KEY (profile_id) REFERENCES generation_profiles(id) ON DELETE CASCADE
);

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

CREATE INDEX IF NOT EXISTS idx_category_sources_source_id ON category_sources(source_id);
CREATE INDEX IF NOT EXISTS idx_generation_profile_categories_category_id ON generation_profile_categories(category_id);
CREATE INDEX IF NOT EXISTS idx_deterministic_settings_category_category_id ON deterministic_settings_category(category_id);
CREATE INDEX IF NOT EXISTS idx_monthly_api_spend_profile_month ON monthly_api_spend(profile_id, month_key);
CREATE INDEX IF NOT EXISTS idx_rss_sources_health_status ON rss_sources(health_status);
CREATE INDEX IF NOT EXISTS idx_generation_jobs_profile_started_at ON generation_jobs(profile_id, started_at DESC);
