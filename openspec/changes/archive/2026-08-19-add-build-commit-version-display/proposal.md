## Why

Operators need immediate traceability of the deployed version from the admin UI. Today, there is no visible build identifier in the configuration page header, which makes support and incident diagnosis slower.

## What Changes

- Add build commit metadata injection during container image build.
- Expose build version metadata through a lightweight backend API.
- Display the commit short SHA at the top of the admin configuration page.
- Keep a safe fallback value when commit metadata is unavailable.

## Capabilities

### New Capabilities
- `build-version-visibility`: Surface build commit identity in runtime API and admin UI.

### Modified Capabilities
- `github-actions-docker-publish`: Inject commit metadata into image build args.
- `versioned-dockerfile-contract`: Persist build metadata in runtime environment variables.

## Impact

- Affected backend: new read-only version endpoint.
- Affected frontend: header area shows runtime build version.
- Affected CI: workflow passes commit SHA to Docker build.
- Affected image contract: Dockerfile stores build commit metadata in env variables.
