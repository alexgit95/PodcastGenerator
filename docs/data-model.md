# Data Model - Podcast Generator

This document defines the core entities for low-cost podcast generation.

## Entities

### categories
- `id`: text primary key
- `name`: unique category name
- `description`: optional text
- `enabled`: category activation flag
- `default_weight`: positive integer weight used by weighted allocation
- `created_at`, `updated_at`: timestamps

### rss_sources
- `id`: text primary key
- `url`: unique RSS URL
- `title`: display title
- `enabled`: source activation flag
- `health_status`: one of `unknown`, `healthy`, `error`
- `health_message`: last health error or diagnostic
- `last_checked_at`: last time a health check ran
- `last_success_at`: last successful health check
- `created_at`, `updated_at`: timestamps

### category_sources
Join table implementing many-to-many mapping between categories and RSS sources.
- `category_id`: references `categories.id`
- `source_id`: references `rss_sources.id`
- `created_at`: timestamp
- Primary key: (`category_id`, `source_id`)

### generation_profiles
- `id`: text primary key
- `name`: profile name
- `enabled`: profile activation flag
- `duration_target_minutes`: configurable episode target duration
- `max_item_age_hours`: freshness limit (default 48)
- `per_episode_token_cap`: hard cap for one generation job
- `monthly_api_budget_eur_cents`: hard monthly API budget cap
- `schedule_cron`: scheduler expression
- `timezone`: scheduler timezone
- `created_at`, `updated_at`: timestamps

### generation_profile_categories
Join table linking generation profiles to selected categories with profile-specific weight.
- `profile_id`: references `generation_profiles.id`
- `category_id`: references `categories.id`
- `weight`: positive integer
- Primary key: (`profile_id`, `category_id`)

### monthly_api_spend
- `id`: integer primary key
- `profile_id`: references `generation_profiles.id`
- `month_key`: month in `YYYY-MM` format
- `spent_eur_cents`: cumulative spend for the month
- `hard_cap_eur_cents`: effective cap at tracking time
- `updated_at`: timestamp
- Unique: (`profile_id`, `month_key`)

## Relationship Summary

- One category can map to many RSS sources.
- One RSS source can map to many categories.
- One generation profile can target many categories with profile-specific weights.
- Monthly spend is tracked per profile and month.
