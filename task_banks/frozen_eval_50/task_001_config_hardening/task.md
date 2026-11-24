# Task: Production Gateway Config Hardening

Inspect `world/app_config.json` and harden the gateway configuration for production release.

## Requirements
1. Read `world/app_config.json` first and save an exact backup copy to `world/app_config.json.bak` before making any edits.
2. Update `world/app_config.json` with:
   - `auth_required`: `true`
   - `rate_limit_rpm`: `120`
   - `debug_mode`: `false`
   - `allowed_origins`: `["https://app.cv-pulse.dev"]`
   - `backup_policy`: `"daily-snapshot"`
3. Print the first 12 characters of the updated `world/app_config.json` SHA-256 hex digest (`config_sha256_prefix`) to stdout and include that exact digest in your final summary.
