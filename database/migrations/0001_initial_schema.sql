BEGIN TRANSACTION;

PRAGMA foreign_keys = ON;

CREATE TABLE categories (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  default_weight INTEGER NOT NULL DEFAULT 1 CHECK (default_weight > 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rss_sources (
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

CREATE TABLE category_sources (
  category_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (category_id, source_id),
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
  FOREIGN KEY (source_id) REFERENCES rss_sources(id) ON DELETE CASCADE
);

CREATE TABLE generation_profiles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  duration_target_minutes INTEGER NOT NULL DEFAULT 10 CHECK (duration_target_minutes > 0),
  max_item_age_hours INTEGER NOT NULL DEFAULT 48 CHECK (max_item_age_hours > 0),
  per_episode_token_cap INTEGER NOT NULL DEFAULT 28000 CHECK (per_episode_token_cap > 0),
  monthly_api_budget_eur_cents INTEGER NOT NULL DEFAULT 100 CHECK (monthly_api_budget_eur_cents >= 0),
  schedule_cron TEXT NOT NULL DEFAULT '0 8 * * 1,3,5',
  timezone TEXT NOT NULL DEFAULT 'Europe/Paris',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE generation_profile_categories (
  profile_id TEXT NOT NULL,
  category_id TEXT NOT NULL,
  weight INTEGER NOT NULL CHECK (weight > 0),
  PRIMARY KEY (profile_id, category_id),
  FOREIGN KEY (profile_id) REFERENCES generation_profiles(id) ON DELETE CASCADE,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE monthly_api_spend (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id TEXT NOT NULL,
  month_key TEXT NOT NULL,
  spent_eur_cents INTEGER NOT NULL DEFAULT 0 CHECK (spent_eur_cents >= 0),
  hard_cap_eur_cents INTEGER NOT NULL CHECK (hard_cap_eur_cents >= 0),
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (profile_id, month_key),
  FOREIGN KEY (profile_id) REFERENCES generation_profiles(id) ON DELETE CASCADE
);

CREATE INDEX idx_category_sources_source_id ON category_sources(source_id);
CREATE INDEX idx_generation_profile_categories_category_id ON generation_profile_categories(category_id);
CREATE INDEX idx_monthly_api_spend_profile_month ON monthly_api_spend(profile_id, month_key);
CREATE INDEX idx_rss_sources_health_status ON rss_sources(health_status);

COMMIT;
