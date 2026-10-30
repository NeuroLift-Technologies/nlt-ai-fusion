# Active Threads — neurolift-ai-fusion

**Governance:** ORG-DEV-OTOI-1.0.3
**Last updated:** 2026-10-30T22:05:00.000Z
**Maintained by:** All active agents (update at session start and end)

---

## How to Use This File

- **Before starting work:** Read this file to identify active threads, avoid conflicts, and find relevant context.
- **When starting a thread:** Add an entry to the Active Threads table with your name and session ID.
- **When completing a thread:** Move it to the Completed Threads section and write a handoff record in `docs/agent-log/handoffs/`.

---

## Active Threads

| Thread ID | Title | Owner | Agent | Branch | Status | Started |
|-----------|-------|-------|-------|--------|--------|---------|
| TH-008 | Document PR #43 Cloudflare workspace/config changes | Automation | Cursor Automation | cursor/documentation-automation-system-99aa | 🟡 In Progress | 2026-05-02 |
| TH-022 | Cross-repo governance alignment: upgrade OTOI v1.0.0→v1.0.3, add REVIEW.md, fix persona count (19→20), sync with nlt-world-engine + nlt-adhd | Joshua W. Dorsey, Sr. | Hermes Agent | hermes/th-022-governance-alignment-v2 | 🟡 In Progress | 2026-09-12T20:48:37-04:00 |
| TH-023 | Add local model adapters and loopback HTTP endpoint for the Godot agent loop ([PR #119](https://github.com/NeuroLift-Technologies/neurolift-ai-fusion/pull/119)) | Joshua W. Dorsey, Sr. | Copilot CLI | feat/agent-loop-http-gguf-20261008 | 🟡 PR review pending | 2026-10-08 |
| TH-024 | Link the web homepage (hero, new World Engine section, footer) to the NLT World Engine site at `neurolift-technologies.github.io/nlt-world-engine/` | Joshua W. Dorsey, Sr. | Claude Code | claude/serene-faraday-78ify3 | 🟡 In Progress | 2026-10-17 |
| TH-025 | Let the local agent-loop models choose use / sit / rest / look_at, not only wait and approach (the world engine's AGENT-LOOP-002 doors and furniture) | Joshua W. Dorsey, Sr. | Claude Code | claude/pensive-shannon-x9on97 | ✅ Merged ([#126](https://github.com/NeuroLift-Technologies/neurolift-ai-fusion/pull/126)) | 2026-10-21T20:55:00+00:00 |
| TH-026 | Fix the web build / Vercel preview deploy, red since #123 (workspace ERESOLVE from apps/mobile, Tailwind 4 major bump, postcss override conflict) | Joshua W. Dorsey, Sr. | Claude Code | claude/fix-web-build | 🟡 Fix on main via #126; this PR adds its records ([#127](https://github.com/NeuroLift-Technologies/neurolift-ai-fusion/pull/127)) | 2026-10-21T21:15:39+00:00 |
| TH-027 | Make the README 20-pair roster canonical across neurolift-ai-fusion and nlt-fusion ([PR #130](https://github.com/NeuroLift-Technologies/neurolift-ai-fusion/pull/130), [nlt-world-engine#116](https://github.com/NeuroLift-Technologies/nlt-world-engine/pull/116)); pending Josh: review of the 18 proposed avatars/aides, Pages deploy on merge, DEPLOYMENT.md UE row, claude.ai Project text | Joshua W. Dorsey, Sr. | Claude Code | agent/claude-roster-canonicalization-20 | 🟡 In Review | 2026-10-22 |
| TH-028 | AGENT-LOOP-003: give the agent-loop decision source state, goals and memory (`docs/specs/AGENT-LOOP-003-fusion-state-and-goals-brief.md`). F0-F4 merged (#132, #134, #135); exploring, reach guard, blocked targets (#136); acceptance tests (#137, Kilo); timeout + quarantine + model selection (#138); tier-3 ranking, demote-not-forbid (#139). Baseline passes 4a; no model met 4b (brief §12). Open: F5, model choice / decision time, the Qwen3-1.7B engine result | Joshua W. Dorsey, Sr. | Claude Code | ccr-100a7dbc-intpwq | 🟡 In Progress | 2026-10-29 |
| TH-029 | Archive parallel Python/Cloudflare/browser World Engine implementations; preserve cognitive scenario catalogue; align active docs and remove legacy world API route ([PR #152](https://github.com/NeuroLift-Technologies/nlt-ai-fusion/pull/152)) | Joshua W. Dorsey, Sr. | ChatGPT GPT-6 | chore/fusion-archive-legacy-world-runtime-20261030 | 🟡 PR review pending | 2026-10-30T11:42:42.905Z |
| TH-030 | Repair the red `Mobile — Type Check & Lint` job after the Expo SDK 57 upgrade ([#150](https://github.com/NeuroLift-Technologies/nlt-ai-fusion/pull/150)): root pins stop apps/web's eslint 8 / React 18 from being hoisted above apps/mobile's toolchain, ESLint flat config committed, 8 lint violations fixed, expo-doctor 21/21, SDK 57 config/schema alignment | Joshua W. Dorsey, Sr. | Cline | cline/pm2vwg6t | 🟡 [PR #155](https://github.com/NeuroLift-Technologies/nlt-ai-fusion/pull/155) — mobile job green, awaiting human review | 2026-10-30T21:45:00Z |
| TH-031 | Prepare the AI-Fusion runtime for the Hugging Face Space `divergent-tech/Ai-fusion`: repo audit + 7-class module classification, Docker Space runtime in `spaces/ai-fusion/` (fusion + session + agent-loop surfaces, ASFDK capability gate, `/health` + `/readyz`), payload assembler, 20 integration tests; 8 architectural conflicts reported, deployment blocked on read-only Hub access | Joshua W. Dorsey, Sr. | Cline | cline/pm2vwg6t | 🟡 Runtime verified locally; Space upload pending Hub write access | 2026-10-30T22:05:00Z |



---

## Blocked Threads

_No blocked threads at this time._

---

## Completed Threads

| Thread ID | Title | Completed By | Completed Date | Handoff |
|-----------|-------|-------------|----------------|---------|
| TH-001 | Add required governance files (AGENTS.md, CLAUDE.md, active-threads.md, agent-log dirs) | GitHub Copilot | 2026-04-21 | Merged via [PR #17](https://github.com/NeuroLift-Technologies/neurolift-ai-fusion/pull/17) |
| TH-002 | Prepare Cloudflare World Engine deployment | Joshua W. Dorsey, Sr. | Codex | — | ✅ Complete | 2026-04-25 |
| TH-003 | Repo cleanup + full-stack app foundation (web/mobile/api) | Codex | 2026-04-25 | `docs/agent-log/handoffs/CODEX-2026-04-25-repo-cleanup-fullstack-foundation-handoff.json` |
| TH-004 | PR feedback response: implement runnable API/web/mobile starters + archive legacy business-agent tree | Codex | 2026-04-25 | `docs/agent-log/handoffs/CODEX-2026-04-25-pr-feedback-fullstack-implementation-handoff.json` |
| TH-005 | Document PR #30 full-stack simulation app foundation | Cursor Automation | 2026-04-30 | `docs/agent-log/handoffs/CURSOR-2026-04-30-doc-automation-pr30-handoff.json` |
| TH-006 | Sync Simulation Lab milestone onto current main | Codex | 2026-05-01 | `docs/agent-log/handoffs/2026-05-01-codex-main-sync-simulation-lab-handoff.json` |
| TH-007 | Open-items review report for next agent | GitHub Copilot | 2026-05-02 | `docs/reviews/2026-05-02-copilot-open-items-review.md` |
| TH-008 | Document PR #51 CI harness and PGSA gate | Cursor GPT-5.5 | 2026-05-04 | `docs/agent-log/handoffs/CURSOR-2026-05-04-doc-automation-pr51-handoff.json` |
| TH-009 | PR queue cleanup scan (14 PRs, 4 orphan branches) | Copilot (PR Cleanup Agent) | 2026-05-02 | `docs/agent-log/handoffs/2026-05-02-copilot-pr-cleanup-scan-handoff.json` |
| TH-010 | Documentation automation for PR #49 governance cleanup context | Cursor GPT-5.5 | 2026-05-22 | `docs/agent-log/handoffs/CURSOR-2026-05-22-doc-automation-pr49-handoff.json` |
| TH-011 | Stand up World Engine frontend prototype ([PR #69](https://github.com/NeuroLift-Technologies/neurolift-ai-fusion/pull/69)) | Claude Code | 2026-05-26 | `docs/agent-log/handoffs/CLAUDE-2026-05-26-world-engine-frontend-prototype-handoff.json` |
| TH-012 | Make World Engine browser prototype run locally | Codex | 2026-05-27 | `docs/agent-log/handoffs/CODEX-2026-05-27-world-engine-working-prototype-handoff.json` |
| TH-013 | Align session and onboarding to repository governance | Antigravity | 2026-05-27 | `docs/agent-log/handoffs/2026-05-27-ANTIGRAVITY-governance-alignment.json` |
| TH-014 | Restore org-level governance framing + un-archive root governance files (supersedes PR #75) | Claude Code | 2026-05-28 | `docs/agent-log/2026-05-28-claude-governance-restoration.md` |
| TH-015 | Document PR #76 governance restoration workflow follow-up | Cursor GPT-5.5 | 2026-05-28 | `docs/agent-log/handoffs/CURSOR-AUTOMATION-2026-05-28-pr76-docs-handoff.json` |
| TH-016 | Create an interactive visualization of the 19 Avatar-Aide pairs | Zed GPT-5.6 Sol | 2026-08-20 | `docs/agent-log/handoffs/ZED-GPT-5.6-SOL-2026-08-20-avatar-aide-visualization-handoff.json` |
| TH-017 | Restore missing web lib modules and clear current diagnostics | Zed GPT-5.6 Sol | 2026-08-20 | `docs/agent-log/handoffs/ZED-GPT-5.6-SOL-2026-08-20-web-lib-repair-and-diagnostics-handoff.json` |
| TH-018 | Web validation follow-up + /pairs src/app route re-export fix | Zed GPT-5.6 Sol | 2026-08-20 | `docs/agent-log/handoffs/ZED-GPT-5.6-SOL-2026-08-20-web-validation-followup-handoff.json` |
| TH-019 | Remove Next.js inferred workspace-root warning via outputFileTracingRoot | Zed GPT-5.6 Sol | 2026-08-20 | `docs/agent-log/handoffs/ZED-GPT-5.6-SOL-2026-08-20-next-output-file-tracing-root-handoff.json` |
| TH-020 | Fix failed CI: shared-ci.yml references non-existent reusable workflows; web.yml/mobile.yml trigger on master instead of main | Toast (polecat) | 2026-08-22 | `docs/agent-log/handoffs/TOAST-2026-08-22-fix-failed-beads-ci.yml` |
| TH-021 | Connect trainable ML models to Avatar/Aide pairs (src/ai framework) | Joshua W. Dorsey, Sr. | Kilo (Strategic Orchestrator) | 2026-08-22 | `docs/agent-log/handoffs/KILO-2026-08-22-ai-avatar-aide-models-handoff.json` |
| — | PR Cleanup Agent setup | GitHub Copilot | — | `docs/handoffs/handoff_copilot_pr_cleanup_agent.json` |
| — | WorldEngine EventBus integration | GitHub Copilot (via Claude Code) | — | `docs/handoffs/handoff_copilot_world_engine.json` |
| — | ADHD research and scenario generation | Gemini / Advisory | — | `docs/handoffs/handoff_advisory_adhd_research.json` |
| — | Avatar cursor remaining traits | Cursor | — | `docs/handoffs/handoff_cursor_remaining_traits.json` |
| — | Fusion validation advisory | Advisory | — | `docs/handoffs/handoff_advisory_fusion_validation.json` |
| — | Codex AIDE expertise | Codex | — | `docs/handoffs/handoff_codex_aide_expertise.json` |

---

## Thread Conventions

- **Thread ID format:** `TH-NNN` (sequential, padded to 3 digits)
- **Status values:** 🟢 Open · 🟡 In Progress · 🔴 Blocked · ✅ Complete
- **Owner:** Human stakeholder who requested the work
- **Agent:** AI agent or platform currently working the thread
- **Branch:** Git branch associated with the thread (if applicable)

---

## Notes for Next Agent

- Governance stub files (`AGENTS.md`, `CLAUDE.md`, `docs/active-threads.md`, `docs/agent-log/`) were merged in TH-001 (PR #17).
- Governance source-of-truth is synced via `.github/workflows/sync-governance-public.yml`; validate that `NLT-DEV-OTOI.md` exists in the repository root when onboarding.
- The `docs/handoffs/` directory contains legacy handoff records in an older format. New handoff records should go to `docs/agent-log/handoffs/` using the `handoff-record.json` schema from SOP-NLT-001.
- No active blockers. No architectural decisions pending.
- TH-016 through TH-019 (Zed GPT-5.6 Sol): Initial visualization work and web lib repairs completed by Z.A.I; final integration (full home page composition, ThemeProvider/Toaster layout merge, build verification) completed by Poolside Agent on 2026-08-20. All threads moved to Completed status. See handoff: `docs/agent-log/handoffs/POOLSSIDE-2026-08-20-avatar-aide-integration-handoff.json`.
- TH-006 preserved the pre-sync local work on `codex-cli/local-simulation-lab-before-main-sync`, fast-forwarded `main` to `origin/main`, and ported the fixture-driven `/simulation-lab` observer route into the current Next.js web app.
- TH-007 produced a full open-items review report at `docs/reviews/2026-05-02-copilot-open-items-review.md` covering all open PRs, unresolved review comments, blockers, and pending decisions as of 2026-05-02.
- TH-020 (2026-08-22): Fixed failing CI workflows. `shared-ci.yml` called three reusable workflows that no longer exist in `.github-private` (python-lint.yml, python-test.yml, security-scan.yml), causing every push/PR to fail since ~May 2026. Rewrote with local lint/test/security jobs. Also fixed `web.yml` and `mobile.yml` which triggered on `master` instead of `main`. Updated `python-app.yml` to cover `backend/` changes. Fixed F824 lint error in `backend/app/routers/world.py`. PR #96.
- TH-021 (Kilo, 2026-08-22): Implemented the provider-agnostic `src/ai` model framework + engine/API integration per the approved plan. Rule-based behavior is the default (use_model=False); ML backends are opt-in and lazily imported (no torch hard dependency). Four architectural decisions (model architecture, training-trigger policy, model storage, evaluation metrics) remain PENDING Joshua's sign-off — see the TH-021 handoff. Coverage gate (--cov-fail-under=80) is now actually enforced after fixing the silent pytest.ini section header.
