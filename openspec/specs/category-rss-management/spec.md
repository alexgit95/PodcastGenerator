# category-rss-management Specification

## Purpose
TBD - created by archiving change podcast-generator-low-cost-api. Update Purpose after archive.
## Requirements
### Requirement: Manage categories in web UI
The system MUST provide a web interface to create, edit, enable, disable, and delete podcast categories.

#### Scenario: Create category
- **WHEN** an operator submits a new category name in the web UI
- **THEN** the system stores the category and makes it available for mapping and generation settings

#### Scenario: Disable category
- **WHEN** an operator disables a category
- **THEN** the system excludes that category from automated episode generation

### Requirement: Manage RSS sources in web UI
The system MUST provide a web interface to create, edit, enable, disable, and delete RSS sources.

#### Scenario: Add RSS source
- **WHEN** an operator submits a valid RSS URL
- **THEN** the system stores the source and marks it available for category mapping

#### Scenario: Disable RSS source
- **WHEN** an operator disables an RSS source
- **THEN** the system excludes that source from collection jobs

### Requirement: Map categories to RSS sources
The system MUST support many-to-many mapping between categories and RSS sources in the web interface.

#### Scenario: Assign source to category
- **WHEN** an operator links a source to a category
- **THEN** the system includes the source for that category during collection

#### Scenario: One source used by multiple categories
- **WHEN** an operator links the same source to multiple categories
- **THEN** the system allows the mapping and reuses collected items per category policy

### Requirement: Show RSS source health state
The system MUST test RSS sources and expose health status in the web interface.

#### Scenario: Test successful source
- **WHEN** an operator runs a source test and the feed is reachable and parseable
- **THEN** the UI shows a healthy status with last successful check time

#### Scenario: Test failing source
- **WHEN** an operator runs a source test and the feed is unreachable or invalid
- **THEN** the UI shows an error status and the reason

