# NLT Red Team CI Harness

> **Governance:** ORG-DEV-OTOI-1.0.0 | Red Team SOP-NLT-003  
> **Maintained by:** NeuroLift Technologies Security Team

---

## Overview

The NLT Red Team CI harness enforces two complementary quality and compliance gates on every pull request targeting `main`:

| Gate | Workflow | Purpose |
| ---- | -------- | ------- |
| **Clearance Rubric** | `redteam-ci.yml` | 3-tier progressive quality check |
| **PGSA Portability Gate** | `pgsa-portability-gate.yml` | Secrets scan + provenance validation |

Both workflows are designed to be **non-blocking by default** during development but become **required status checks** when enabled via branch protection rules.

---

## Clearance Rubric (`redteam-ci.yml`)

Implements a 3-tier progressive clearance system.  Each level must pass before the next one runs.

**Triggers:** pull requests targeting `main`, pushes to `main`, and manual
`workflow_dispatch` runs. The workflow exposes a `clearance_level` manual input,
but the current jobs call fixed levels (`--level 1`, `--level 2`, `--level 3`);
changing that input does not currently skip later workflow jobs.

**Artifact behavior:** each level writes Markdown reports under
`clearance-reports/` and uploads them with `actions/upload-artifact@v4.6.2` as
`clearance-level-1-report`, `clearance-level-2-report`, and
`clearance-level-3-report`. On pull requests, `report-pr-comment` downloads the
artifacts and posts a status summary comment.

### Level 1 — Basic

| Step | Tool | What it checks |
| ---- | ---- | -------------- |
| `syntax-check` | `python -m py_compile` | `.py` files discovered under `src/` and `scripts/` parse without syntax errors |
| `lint-errors` | `flake8` | Fatal linting errors (`E9`, `F63`, `F7`, `F82`) under `src/` and `scripts/` |
| `unit-tests` | `pytest` | Unit test suite passes |

### Level 2 — Standard

| Step | Tool | What it checks |
| ---- | ---- | -------------- |
| `coverage` | `pytest-cov` | Test coverage ≥ 60 % |
| `type-check` | `mypy` | Static type analysis of `src/` |

### Level 2 coverage and type-checking contract

Level 2 is the clearance gate most likely to fail after Python source changes.
It is intentionally narrower than a full local `pytest` run:

```bash
python -m pytest tests/ --tb=short -q \
  --cov=src \
  --cov-report=term-missing \
  --cov-fail-under=60

python -m mypy src --ignore-missing-imports
```

Source-verified constraints:

- The Level 2 coverage threshold is defined in
  `scripts/run_clearance_tests.py` as `--cov-fail-under=60`.
- `pytest.ini` addopts deliberately contains no coverage flags, so bare
  `pytest` does not enforce a gate and works in environments without
  `pytest-cov`. CI workflows and `scripts/run_clearance_tests.py` pass the
  coverage flags explicitly; CI uses `--cov-fail-under=40` and Level 1 uses
  `--cov-fail-under=40`, so Level 2 remains the stricter gate. Use
  `scripts/run_clearance_tests.py --level 2` when reproducing Red Team CI
  exactly.
- `mypy.ini` is loaded by mypy during the Level 2 `type-check` step. It keeps
  `ignore_missing_imports = True` and suppresses only the currently excluded
  modules:
  - `src.database.supabase_client`
  - `src.simulation.training_session`
  - `src.aides.coaching.stay_alert_aide`
- The `stay_alert_aide` exclusion is tied to the pre-existing
  `CoachingContext` shape mismatch noted in `mypy.ini`; do not broaden this
  suppression when adding new typed code.

PR #58 raised clearance coverage with targeted tests for these public surfaces:

| Test file | Source covered | Behavior protected |
| --- | --- | --- |
| `tests/test_aides/test_attention_expert.py` | `src/aides/expertise/attention_expert.py` | strategy selection, capacity assessment, recovery actions, and attention plan shape |
| `tests/test_simulation/test_base_scenario.py` | `src/simulation/scenarios/base_scenario.py` | scenario step progression, task-context defaults, outcomes, progress, and dataclass serialization |
| `tests/test_utils/test_config_loader.py` | `src/utils/config_loader.py` | default schemas, validation rules, constraints, and JSON/YAML save behavior |

### Level 3 — Full

| Step | Script | What it checks |
| ---- | ------ | -------------- |
| `secret-scan` | `scan_secrets.py` | Secrets in source tree (Gitleaks) |
| `provenance-check` | `validate_provenance.py` | PGSA provenance manifest compliance |

### Reports

Each level uploads a Markdown report as a GitHub Actions artifact (`clearance-level-<N>-report`).  A summary comment is posted on pull requests when all levels complete.

### Source-verified codepath map

| Behavior | Source | Notes |
| --- | --- | --- |
| Workflow event surface | `.github/workflows/redteam-ci.yml` | Runs on PRs/pushes to `main` and manual dispatch. |
| Progressive job ordering | `needs: clearance-level-1`, then `needs: clearance-level-2` | A failed lower level prevents later levels from running. |
| Step definitions | `scripts/run_clearance_tests.py::LEVEL_STEPS` | Defines commands for each clearance level. |
| Python file discovery | `scripts/run_clearance_tests.py::_collect_python_files` | Syntax check only scans `src/` and `scripts/`. |
| Stop-on-failure behavior | `scripts/run_clearance_tests.py::main` | `--level N` runs levels `1..N` and stops after the first failed level. |
| Report formats | `scripts/run_clearance_tests.py::write_report` | Supports `markdown` and `json`; workflow uses Markdown. |
| Level 2 coverage threshold | `scripts/run_clearance_tests.py::LEVEL_STEPS[2]` | Uses `--cov-fail-under=60`, stricter than the `--cov-fail-under=40` used by CI and Level 1. |
| Level 2 mypy exclusions | `mypy.ini` | Suppresses only external-service clients, legacy `training_session`, and the known `stay_alert_aide` context mismatch. Superseded world/NPC modules and their tests are preserved under `archive/legacy-world-engine/` and are not part of the active source tree. |

### Local reproduction

Run from the repository root after installing Python dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install flake8 pytest pytest-cov mypy

# Match the Level 1 CI job.
python scripts/run_clearance_tests.py \
  --level 1 \
  --report-dir clearance-reports \
  --report-format markdown \
  --verbose

# Match the Level 2 CI job, including the 60% clearance threshold and mypy.ini.
python scripts/run_clearance_tests.py \
  --level 2 \
  --report-dir clearance-reports \
  --report-format markdown \
  --verbose

# Exercise all levels locally. Install Gitleaks first for a meaningful
# Level 3 secret scan.
python scripts/run_clearance_tests.py --level 3 --verbose
```

---

## PGSA Portability Gate (`pgsa-portability-gate.yml`)

Enforces the **Portability and Governance Security Assessment** requirements.

### Jobs

#### `secrets-scan`

- Installs Gitleaks and runs `scripts/scan_secrets.py --fail-on-findings`.
- Fails the gate if any secrets are detected.
- Uses `.github/gitleaks.toml` for NLT-specific rules and allowlisting.
- Runs with `--skip-trufflehog` in CI, so the PGSA workflow's enforced scanner
  is currently Gitleaks.

#### `provenance-check`

- Runs `scripts/validate_provenance.py` against all `**/provenance.json` manifests.
- Validates required schema fields and PGSA whitelist/blacklist rules.
- Config loaded from `config/pgsa-allowlists.json`.
- Passes when no provenance manifests are present; the script reports "nothing
  to validate" and exits 0.

#### `pgsa-gate`

Aggregates the results of both jobs.  This is the **required status check** to add to branch protection rules.

### Source-verified codepath map

| Behavior | Source | Notes |
| --- | --- | --- |
| Workflow event surface | `.github/workflows/pgsa-portability-gate.yml` | Runs on PRs/pushes to `main` and manual dispatch. |
| Required status check name | `pgsa-gate` job name | Use `PGSA Gate — Required Status Check` in branch protection. |
| Gitleaks install path | `secrets-scan` job | Installs Gitleaks `8.21.2` before running `scan_secrets.py`. |
| Secret scanner exit behavior | `scripts/scan_secrets.py::main` | Returns 1 only when findings exist and `--fail-on-findings` is set. |
| Missing local scanner behavior | `scripts/scan_secrets.py::main` | If no scanner is available, warns and returns 0 unless findings exist. |
| Manifest discovery | `scripts/validate_provenance.py::MANIFEST_GLOBS` | Scans `**/provenance.json` and `**/*.provenance.json`. |
| Directory exclusions | `scripts/validate_provenance.py::SKIP_DIRS` | Skips `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, and `.tox`. |
| Enforced provenance failures | `scripts/validate_provenance.py::_validate_manifest` | Missing required fields, parse errors, non-object roots, and blacklisted sources fail. |
| Advisory provenance warnings | `scripts/validate_provenance.py::_validate_manifest` | Sources outside the whitelist warn but do not fail. |

### Local reproduction

```bash
# Secrets scan. For parity with CI, install Gitleaks and skip TruffleHog.
python scripts/scan_secrets.py \
  --gitleaks-config .github/gitleaks.toml \
  --report-dir pgsa-reports \
  --report-format markdown \
  --fail-on-findings \
  --skip-trufflehog \
  --verbose

# Provenance validation.
python scripts/validate_provenance.py \
  --scan-root . \
  --config config/pgsa-allowlists.json \
  --report-dir pgsa-reports \
  --report-format markdown \
  --verbose
```

---

## Scripts

### `scripts/run_clearance_tests.py`

```
usage: run_clearance_tests.py [-h] [--level {1,2,3}] [--repo-root PATH]
                               [--report-dir PATH] [--report-format {json,markdown}]
                               [--timeout SECONDS] [--verbose]

Options:
  --level          Maximum clearance level to run (1–3, default: 1)
  --repo-root      Repository root path (default: CWD)
  --report-dir     Output directory for reports (default: clearance-reports/)
  --report-format  json | markdown (default: markdown)
  --timeout        Per-step timeout in seconds (default: 300)
  --verbose        Enable debug logging
```

### `scripts/scan_secrets.py`

```
usage: scan_secrets.py [-h] [--scan-path PATH] [--gitleaks-config PATH]
                        [--report-dir PATH] [--report-format {json,markdown}]
                        [--fail-on-findings] [--skip-gitleaks] [--skip-trufflehog]
                        [--verbose]

Options:
  --scan-path        Path to scan (default: CWD)
  --gitleaks-config  Gitleaks config file (default: .github/gitleaks.toml)
  --report-dir       Output directory for reports (default: clearance-reports/)
  --report-format    json | markdown (default: markdown)
  --fail-on-findings Exit 1 when secrets are found
  --skip-gitleaks    Skip Gitleaks even if installed
  --skip-trufflehog  Skip TruffleHog even if installed
  --verbose          Enable debug logging
```

### `scripts/validate_provenance.py`

```
usage: validate_provenance.py [-h] [--scan-root PATH] [--config PATH]
                               [--report-dir PATH] [--report-format {json,markdown}]
                               [--verbose]

Options:
  --scan-root     Root directory to scan for provenance manifests (default: CWD)
  --config        Path to PGSA allowlists JSON (default: config/pgsa-allowlists.json)
  --report-dir    Output directory for reports (default: clearance-reports/)
  --report-format json | markdown (default: markdown)
  --verbose       Enable debug logging
```

---

## Provenance Manifest Schema

Each `provenance.json` (or `*.provenance.json`) must include:

```json
{
  "schema_version": "1.0",
  "component": "my-package",
  "version": "1.2.3",
  "source": "https://pypi.org/project/my-package/",
  "build_system": "pip"
}
```

| Field | Required | Description |
| ----- | -------- | ----------- |
| `schema_version` | ✅ | Manifest format version |
| `component` | ✅ | Package/component name |
| `version` | ✅ | Semantic version |
| `source` | ✅ | Origin URL or registry |
| `build_system` | ✅ | Build tool (`pip`, `npm`, `docker`, etc.) |

### Manifest naming and validation constraints

- File names must match `provenance.json` or `*.provenance.json`.
- Required fields are checked only at the top level of the JSON object.
- `source` is matched by case-insensitive substring against the whitelist and
  blacklist entries.
- A blacklisted source fails validation even if it also contains a whitelisted
  substring.

---

## PGSA Allowlists (`config/pgsa-allowlists.json`)

```json
{
  "whitelist": ["github.com", "pypi.org", "npmjs.com", ...],
  "blacklist": ["untrusted-registry.example.com", ...]
}
```

- **Whitelist** — advisory; sources not on the list generate a warning but do not fail validation.
- **Blacklist** — enforced; any manifest whose `source` matches a blacklisted origin causes a validation failure.
- The checked-in allowlist includes common registries such as `github.com`,
  `pypi.org`, `npmjs.com`, `registry.npmjs.org`, `hub.docker.com`, `ghcr.io`,
  `pkg.go.dev`, `crates.io`, and `nuget.org`.

---

## Gitleaks Configuration (`.github/gitleaks.toml`)

Extends the built-in Gitleaks ruleset with NLT-specific rules:

| Rule ID | Description |
| ------- | ----------- |
| `nlt-api-key` | NLT internal API keys |
| `nlt-jwt-secret` | NLT JWT signing secrets |
| `nlt-supabase-key` | Supabase service-role/anon keys |
| `nlt-cloudflare-token` | Cloudflare API tokens |

The global allowlist suppresses false positives for:
- Placeholder/example values in documentation and tests.
- GitHub Actions expression syntax (`${{ secrets.FOO }}`).
- Environment variable references (`$ENV_VAR`, `os.environ.get(...)`).

---

## Enabling as Required Status Checks

To enforce both gates on `main`:

1. Go to **Settings → Branches → Branch protection rules → `main`**
2. Enable **"Require status checks to pass before merging"**
3. Add the following required checks:
   - `Clearance Level 1 — Basic`
   - `PGSA Gate — Required Status Check`
4. Enable **"Require branches to be up to date before merging"**

Only `PGSA Gate — Required Status Check` aggregates the PGSA secrets and
provenance jobs. If branch protection references only `Secrets Scan (Gitleaks)`
or `Provenance Validation (PGSA)`, it will not capture the full portability
gate result.

---

## Local Development

Run any script locally from the repository root:

```bash
# Run Level 1 clearance (syntax, lint, tests)
python scripts/run_clearance_tests.py --level 1 --verbose

# Run secrets scan (Gitleaks must be installed)
python scripts/scan_secrets.py --fail-on-findings --verbose

# Validate provenance manifests
python scripts/validate_provenance.py --verbose
```

Install Gitleaks for local use:

```bash
# macOS
brew install gitleaks

# Linux
GITLEAKS_VERSION="8.21.2"
curl -sSfL \
  "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
  | tar -xz -C ~/.local/bin gitleaks
```

---

## Troubleshooting

| Symptom | Likely cause | What to check |
| --- | --- | --- |
| `redteam-ci.yml` manual run ignores selected `clearance_level` | Workflow jobs currently pass fixed `--level` values | Inspect each `Run Level <N> clearance tests` step before assuming the input changes the job graph. |
| Level 2 or Level 3 appears to rerun earlier checks | `run_clearance_tests.py --level N` executes levels `1..N` | This is expected script behavior; review the generated report to see which level failed first. |
| Bare `pytest` reports no coverage | Coverage flags were removed from `pytest.ini` addopts so environments without `pytest-cov` can run tests | Pass `--cov=src --cov-fail-under=40` explicitly, or run `python scripts/run_clearance_tests.py --level 2 --verbose` for the stricter 60 gate. |
| `pytest` aborts with `unrecognized arguments: --cov=src` | A stale `-o addopts` override is still on the command line, or an older `pytest.ini` is in effect | Drop any `-o addopts` workaround; coverage is no longer in addopts. Confirm the resolved config with `pytest --collect-only -q`. |
| Mypy passes in CI but fails when run on a single excluded module | `mypy.ini` suppresses known problematic modules only during normal config-loaded mypy runs | Inspect `mypy.ini` before treating a local one-off mypy command as equivalent to Level 2. |
| Local secret scan reports no tools available | Neither Gitleaks nor TruffleHog is installed | Install Gitleaks for parity with CI, or run with the scanner available on `PATH`. |
| PGSA provenance passes with zero manifests | No files matched `**/provenance.json` or `**/*.provenance.json` | Add a manifest only for components that require provenance tracking. |
| PGSA provenance warns about a source but passes | Source was not on the whitelist | Whitelist misses are advisory; blacklist matches and schema/parse violations fail. |
| Expected branch-protection check is missing | Branch protection references the component jobs instead of the aggregator | Use `PGSA Gate — Required Status Check` for PGSA enforcement. |
