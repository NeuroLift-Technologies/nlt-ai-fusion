# NeuroLift Technologies - Quick Start Guide

> **Current status (Apr 2026):** script entrypoints are in transition. Use this guide for validated setup checks, and treat script-based runs as reproducible diagnostics rather than guaranteed successful end-to-end sessions.

## 🚀 Get Started in 5 Minutes

### Installation

```bash
# Navigate to project directory
cd /path/to/neurolift-ai-fusion

# Install dependencies
python3 -m pip install -r requirements.txt
```

### Run the Local Godot Agent Loop (GGUF)

Fusion can serve `nlt.agent-loop.v1` decisions to the sibling Godot world-engine project over
loopback HTTP. This opt-in test path is separate from `SessionOrchestrator` and does not change the
default observer-only Godot run. The commands below are for Windows PowerShell, with the Fusion and
`nlt-world-engine` repositories checked out next to each other. Adjust `$worldEngineProject` if your
checkouts are elsewhere.

**Terminal 1 — start Fusion with the local model:**

```powershell
Set-Location C:\path\to\neurolift-ai-fusion

$fusionVenv = 'C:\path\to\your\GGUF-enabled\virtualenv'
$fusionPython = Join-Path $fusionVenv 'Scripts\python.exe'
$worldEngineProject = '..\nlt-world-engine\world-engine-godot'
$env:FUSION_GGUF_MODEL = Join-Path $HOME 'Downloads\Qwen3-0.6B-Q8_0.gguf'
$env:FUSION_AGENT_LOOP_PORT = '8001'

# The GGUF environment needs both llama-cpp-python and the HTTP server packages.
uv pip install --python $fusionPython -r requirements-gguf.txt
uv pip install --python $fusionPython 'fastapi>=0.115.0' 'uvicorn>=0.30.0'
& $fusionPython -m src.fusion.agent_loop_http
```

Keep this terminal running. The GGUF environment can be created and populated with
`uv venv --python 3.11 $fusionVenv`; install the GGUF dependency using the platform-appropriate
wheel instructions in [`requirements-gguf.txt`](requirements-gguf.txt) if `uv pip install` cannot
find a compatible wheel.

**Terminal 2 — run the opt-in Godot scene interactively:**

```powershell
$worldEngineProject = '..\nlt-world-engine\world-engine-godot'
$env:NLT_AGENT_LOOP_ENABLED = '1'
$env:NLT_AGENT_LOOP_ENDPOINT = 'http://127.0.0.1:8001/agent-loop/perception'
& $env:GDA_GODOT --path $worldEngineProject
```

`GDA_GODOT` must point to the Godot 4.7.2 .NET executable. The opt-in scene creates the dedicated
`__local_avatar__` and a visible `agent_loop_test_target`; only that avatar receives decisions.
Watch the Fusion terminal for `POST /agent-loop/perception` responses and the Godot output for
perception, intent acceptance/rejection, and movement. The model is constrained to return `approach`
for a visible target or `wait`. When it returns `approach`, verify the avatar moves toward the marker,
stops within the one-metre arrival radius, and the next perception reports the new position.

**GDA headless startup/HTTP check:** close the Godot editor first if it is holding the C# build
outputs, then run this from the Fusion repository while Terminal 1 is serving the model:

```powershell
$worldEngineProject = (Resolve-Path '..\nlt-world-engine\world-engine-godot').Path
$env:NLT_AGENT_LOOP_ENABLED = '1'
$env:NLT_AGENT_LOOP_ENDPOINT = 'http://127.0.0.1:8001/agent-loop/perception'
gda scene preflight res://Main.tscn --project $worldEngineProject --frames 600 --timeout 60 --json
```

On a successful result, check `started: true` and `status: "ready"`; also inspect engine output for
errors. The observed headless run started and sent a model-backed perception that received HTTP 200.
A separate request to the same GGUF returned a correlated `approach` intent. **Preflight is not
proof of physical completion:** it does not confirm the intent was accepted, visible Jolt movement
or arrival, or updated position in a later perception. Use the interactive run to check those
outcomes. On Windows, GDA's live daemon is not supported; `scene preflight` is a one-shot headless
check. Existing Godot output may include `Capture not registered: 'beehave'` even when the structured
preflight result is `started: true`.

Stop either process with `Ctrl+C`; unset `FUSION_GGUF_MODEL`, `NLT_AGENT_LOOP_ENABLED`, and
`NLT_AGENT_LOOP_ENDPOINT` when done. Leaving `FUSION_GGUF_MODEL` unset starts Fusion's deterministic
fallback instead of loading the GGUF.

### Entrypoint Status Matrix (Verified Against Current Code)

| Entrypoint | Current behavior | Recommended use |
| --- | --- | --- |
| `scripts/setup_environment.py` | Creates directories/config templates, **overwrites root `.gitignore` and `LICENSE`**, and prints a reference to `docs/avatar-aide-advocate-process.md` (file not present). | Run only in a fresh clone or sandbox where those overwrite side effects are intentional. |
| `scripts/test_training_loop.py` | Progresses through Avatar/Aide setup and scenario selection, then fails in `src/simulation/training_session.py` with `TypeError: CoachingContext.__init__() got an unexpected keyword argument 'avatar'`. | Use as a reproducible integration diagnostic for coaching-context mismatch. |
| `scripts/run_training_session.py` | Fails immediately with `ImportError: attempted relative import beyond top-level package` due package-relative imports under `src/avatars`. | Treat as a legacy script pending import-path reconciliation. |
| `src/simulation/session_orchestrator.py` (+ `tests/test_simulation/test_session_orchestrator.py`) | Represents the active orchestration contract (`SessionOrchestrator`, `SessionConfig`, `SessionResult`). | Use as the primary API/reference path while legacy scripts are reconciled. |

### Run a Training Session

```bash
# Syntax smoke check first
python3 -m compileall src scripts

# Execute the current interactive training demonstration
python3 scripts/test_training_loop.py
```

> `scripts/test_training_loop.py` currently executes setup + scenario selection, then fails at coaching context construction with `TypeError: CoachingContext.__init__() got an unexpected keyword argument 'avatar'`. Keep using it as a reproducible integration checkpoint until script/runtime interfaces are reconciled.

### Minimal Orchestrator API Smoke Test (Verified)

This example mirrors the current `SessionOrchestrator` contract used in tests:

```bash
python3 - <<'PY'
from src.core.events import EventBus
from src.avatars.base_avatar import BaseAvatar
from src.aides.base_aide import BaseAide
from src.simulation.session_orchestrator import SessionOrchestrator, SessionConfig

class DemoAvatar(BaseAvatar):
    def get_adhd_trait_impact(self, task_context):
        return {"difficulty_modifier": 1.1, "quality_modifier": 0.05, "time_modifier": 1.0, "cognitive_load_modifier": 0.1}
    def simulate_struggle(self, task_context):
        return ["mild_struggle"]

class DemoAide(BaseAide):
    def get_expertise_strategies(self, context):
        return [{"strategy": "Chunk tasks", "techniques": ["break work into chunks"], "expected_outcomes": ["higher completion"], "effectiveness": 0.7, "context_match": 0.7}]
    def get_real_world_insights(self, context):
        return [{"source": "real_world", "strategy": "Use accountability", "techniques": ["pair work"], "expected_outcomes": ["more consistency"], "effectiveness": 0.8, "context_match": 0.8}]

bus = EventBus()
avatar = DemoAvatar("avatar_demo", {"trait_name": "demo"}, event_bus=bus)
aide = DemoAide("aide_demo", {"expertise_area": "demo_coaching"}, event_bus=bus)
orchestrator = SessionOrchestrator(
    avatar,
    aide,
    SessionConfig(max_attempts_per_scenario=2, max_coaching_per_attempt=1, check_fusion_readiness=False),
)
result = orchestrator.run_session([
    {"name": "Focus Task", "task_type": "focus", "base_success_rate": 0.8, "cognitive_demand": 0.4}
])
print(result.phase.name, result.total_attempts, len(result.scenario_results))
PY
```

Current demo behavior:
1. Creates a StayAlert Avatar and StayAlertAide
2. Enumerates workplace scenarios and selects one
3. Runs the first attempt of a training session
4. Then currently fails at a known `CoachingContext` signature mismatch

---

## 📊 Understanding the Output

### Session Results
```
Status: ✓ SUCCESS
Attempts: 1/1
Average Quality Score: 0.35
```

- **Status**: Did the Avatar complete the task?
- **Attempts**: How many tries did it take?
- **Quality Score**: 0-1 scale, higher is better

### Avatar Final State
```
Current State: learning
Emotional State: relieved
Overall Independence: 0.10
Success Rate: 1.00
```

- **State**: Avatar's current cognitive state (idle, struggling, learning, independent)
- **Emotional State**: How the Avatar feels
- **Independence**: 0-1 scale of mastery (1.0 = complete independence)
- **Success Rate**: Percentage of tasks completed successfully

### Aide Metrics
```
Total Interventions: 0
Successful Interventions: 0
Success Rate: 0.00
```

- **Interventions**: How many times the Aide coached
- **Success Rate**: How often coaching led to success

---

## 🧠 What's Happening?

### Avatar-Aide-Advocate Process

```
Avatar                      Aide
  |                          |
  └─ Attempts Task ─────────→ Observes Struggle
                             │
                             └─ Provides Coaching
                             │
  ←─ Receives Coaching ──────┘
  │
  └─ Tries Again
```

### Training Loop

1. **Avatar Attempts Task** - Tries to complete scenario with authentic ADHD struggle
2. **Task Succeeds or Fails** - Result recorded
3. **Aide Evaluates Performance** - Analyzes struggle indicators
4. **Coaching Provided** (if needed) - Evidence-based strategies applied
5. **Avatar Learns** - Progress tracked toward independence

---

## 📚 Available Scenarios

### Workplace (5)
- Email Processing
- Report Writing
- Meeting Participation
- Code Review
- Deadline Crunch

### Personal Life (4)
- Household Cleaning
- Grocery Shopping & Cooking
- Bill Paying
- Morning Routine

### Social (2)
- Phone Conversations
- Social Events

### Academic (2)
- Study Sessions
- Project Work

---

## 🔧 Customization

### Modify Avatar Traits

```python
avatar_config = {
    "attention_duration": 15,        # Minutes before attention drift
    "drift_probability": 0.3,        # 30% chance of losing focus
    "hyperfocus_tendency": 0.2,      # 20% chance of hyperfocus
}

avatar = StayAlertAvatar("my_avatar", avatar_config)
```

### Change Scenario

In `scripts/test_training_loop.py`, modify the scenario selection:

```python
# Instead of scenarios[0], try scenarios[1], scenarios[2], etc.
choice = scenarios[1]  # Select Report Writing instead
```

### Run Multiple Sessions

```python
from src.core.events import EventBus
from src.avatars.base_avatar import BaseAvatar
from src.aides.base_aide import BaseAide
from src.simulation.session_orchestrator import SessionOrchestrator, SessionConfig

class DemoAvatar(BaseAvatar):
    def get_adhd_trait_impact(self, task_context):
        return {"difficulty_modifier": 1.1, "quality_modifier": 0.05, "time_modifier": 1.0, "cognitive_load_modifier": 0.1}
    def simulate_struggle(self, task_context):
        return ["mild_struggle"]

class DemoAide(BaseAide):
    def get_expertise_strategies(self, context):
        return [{"strategy": "Chunk tasks", "techniques": ["break work into chunks"], "expected_outcomes": ["higher completion"], "effectiveness": 0.7, "context_match": 0.7}]
    def get_real_world_insights(self, context):
        return [{"source": "real_world", "strategy": "Use accountability", "techniques": ["pair work"], "expected_outcomes": ["more consistency"], "effectiveness": 0.8, "context_match": 0.8}]

bus = EventBus()
avatar = DemoAvatar("avatar_demo", {"trait_name": "demo"}, event_bus=bus)
aide = DemoAide("aide_demo", {"expertise_area": "demo_coaching"}, event_bus=bus)
orchestrator = SessionOrchestrator(
    avatar,
    aide,
    SessionConfig(max_attempts_per_scenario=2, max_coaching_per_attempt=1, check_fusion_readiness=False),
)

for i in range(3):
    result = orchestrator.run_session([
        {"name": f"Focus Task {i+1}", "task_type": "focus", "base_success_rate": 0.8, "cognitive_demand": 0.4}
    ])
    print(result.phase.name, result.total_attempts, len(result.scenario_results))
```

---

## 📖 Key Concepts

### ADHD Traits
**StayAlert**: Sustained attention deficit
- Struggles to focus for extended periods
- Experiences attention drift
- Vulnerable to hyperfocus on irrelevant tasks

**TaskKickstart**: Task initiation difficulty
- Hard to start tasks (even easy ones)
- Procrastination patterns
- Performance improves after starting

### Coaching Strategies

**Attention Expert** provides:
- Pomodoro Technique adaptations
- Environmental optimization
- Task chunking methods
- Body doubling support
- Transition rituals
- External accountability systems

### Progress Tracking

**Independence Level**: 0.0 to 1.0
- 0.0 = Needs constant coaching
- 0.5 = Can succeed with occasional support
- 1.0 = Complete independence

---

## 🔄 Database Integration (Optional)

### Enable Supabase Persistence

1. Get Supabase credentials from `https://supabase.com`
2. Set environment variables:

```bash
export VITE_SUPABASE_URL="your_url"
export VITE_SUPABASE_SUPABASE_ANON_KEY="your_key"
```

3. Run training - data automatically saves to database

### Without Supabase

Training runs locally without database - no setup required!

---

## 🧪 Testing

### Run All Verifications

```bash
# 1) Syntax smoke check
python3 -m compileall src scripts

# 2) Current orchestration contract (stable test target)
python3 -m pytest tests/test_simulation/test_session_orchestrator.py

# 3) Optional integration diagnostic (expected known failure point)
python3 scripts/test_training_loop.py
```

### Check System Status

```python
from src.database.supabase_client import SupabaseClient
db = SupabaseClient()
print(db._is_available())  # True if connected, False otherwise
```

---

## 🧹 Repository Maintenance Automation (PR Cleanup + Governance Sync)

Use this section to reproduce or validate repository hygiene and governance document sync behavior in GitHub Actions.

### PR cleanup workflow quick reference

**Workflow file:** `.github/workflows/pr-cleanup.yml`  
**Actions UI name:** **PR Cleanup**

- Runs daily at `06:00 UTC` (`cron: 0 6 * * *`) and supports manual dispatch.
- Marks inactive PRs as `stale` after 30 days, then auto-closes after 7 more days (`auto-closed` label).
- Deletes branches for merged PRs when the branch belongs to this repository.
- Reads up to 100 closed PRs per run for branch deletion candidates.

Safety constraints (from workflow logic):

- Draft PRs are exempt from stale marking (`exempt-draft-pr: true`).
- Issues are never marked stale/closed by this workflow.
- Branch cleanup skips protected branches and common default names.
- Branches from fork-based PRs are not deleted.
- Required permissions: `contents: write`, `pull-requests: write`, `issues: write`.

Manual run:

1. Go to **Actions** -> **PR Cleanup** -> **Run workflow**.
2. Select the branch/ref.
3. Optionally override `days_before_stale` (default `30`) and `days_before_close` (default `7`).
4. Review logs from `stale-prs` and `delete-merged-branches`.

Common pitfalls:

- **Merged branch not deleted:** branch may already be removed, protected, or from a fork PR.
- **Unexpected stale label:** any new activity (comment/commit/review) keeps an active PR from closure.

### Governance sync workflow quick reference

**Workflow file:** `.github/workflows/sync-governance-public.yml`  
**Actions UI name:** **Sync Governance (Public)**

Trigger matrix:

- `repository_dispatch` with type `governance-sync` (writes files, can open a PR)
- `workflow_dispatch` (validation-only)
- weekly schedule (`0 8 * * 1`, validation-only)

Payload contract for `repository_dispatch`:

- Required: `client_payload.document_name`, `client_payload.content` (base64 text)
- Optional: `client_payload.version`, `client_payload.checksum`
- Allowed document paths only: `NLT-*.md` or `docs/governance/NLT-*.md`
- Supported checksum verification: `sha256:<hex>`

Dispatch example with `gh api`:

```bash
DOC_PATH="NLT-DEV-OTOI.md"
DOC_CONTENT_B64="$(base64 -w 0 "$DOC_PATH")"

cat > /tmp/governance-sync-payload.json <<EOF
{
  "event_type": "governance-sync",
  "client_payload": {
    "document_name": "${DOC_PATH}",
    "content": "${DOC_CONTENT_B64}",
    "version": "manual-sync-test"
  }
}
EOF

gh api \
  --method POST \
  repos/NeuroLift-Technologies/neurolift-ai-fusion/dispatches \
  --input /tmp/governance-sync-payload.json
```

Quick verification checklist:

1. Confirm event type is `governance-sync`.
2. Confirm `document_name` matches allowed path patterns.
3. In workflow logs, confirm base64 decode succeeded and no disallowed-path error was raised.
4. If no PR is created, verify this was not a manual/scheduled run and confirm decoded content actually changed.

Common pitfalls:

- **Missing required fields:** run fails when `document_name` or `content` is empty.
- **Disallowed document name:** path does not match the permitted governance patterns.
- **No PR created after successful run:** expected when event is schedule/manual or when file content is unchanged.
- **Checksum mismatch (if checksum used):** `sha256` digest does not match decoded content.

---

## 📊 Next Steps

1. **Run the baseline checks** - `compileall` + `test_session_orchestrator.py`
2. **Use `test_training_loop.py` as a diagnostic** - Reproduce and inspect current integration mismatch
3. **Try other scenarios** - Modify scenario selection in `scripts/test_training_loop.py`
4. **Create custom Avatars/Aides** - Prototype against `SessionOrchestrator` contracts
5. **Build an interface** - Add a UI layer once script/runtime interfaces are reconciled

---

## 🆘 Troubleshooting

### ImportError: No module named 'supabase'

This is fine! The system works without Supabase. Data stays local.

To enable Supabase: `pip install supabase`

### Training session takes a while

This is normal - each attempt involves complex calculations. Sessions typically complete in 1-5 seconds per attempt.

### "No scenarios found"

Verify `src/simulation/environment/scenarios.py` exists and contains ScenarioLibrary class.

### Database warnings

Warnings about database are informational only - training continues successfully without database.

### `ImportError` in `scripts/run_training_session.py`

If you see `ImportError: attempted relative import beyond top-level package`, this is due to an import path mismatch between script imports and package-relative imports inside `src/avatars`.

### `CoachingContext` TypeError in `scripts/test_training_loop.py`

If you see `TypeError: CoachingContext.__init__() got an unexpected keyword argument 'avatar'`, the script is using an outdated coaching context shape compared to `src/aides/base_aide.py`.

### `CoachingContext` TypeError in `src/simulation/training_session.py`

If `TrainingSession.run()` fails at coaching construction, the same mismatch exists in
`src/simulation/training_session.py` (`CoachingContext` is instantiated with legacy fields).
Prefer `src/simulation/session_orchestrator.py` for current interface validation.

### `setup_environment.py` changed tracked files

`scripts/setup_environment.py` currently writes root `.gitignore` and `LICENSE`.
If run in an existing working tree, review changes with `git diff` before committing.

### `No module named pytest`

Install project dependencies first:

```bash
python3 -m pip install -r requirements.txt
```

---

## 📞 Support

- **Documentation**: See `IMPLEMENTATION-COMPLETE.md` for full details
- **Architecture**: See `docs/architecture.md`
- **Code**: All code is well-commented with docstrings

---

## ✅ Validation Complete (Current Baseline)

You have successfully:
- ✓ Installed NeuroLift Technologies
- ✓ Verified code syntax across `src/` and `scripts/`
- ✓ Confirmed the current orchestrator contract via targeted tests
- ✓ Reproduced known script-level integration mismatches for debugging

You now have a reliable baseline for local development and troubleshooting.

---

**Ready to explore? Start with: `pytest tests/test_simulation/test_session_orchestrator.py`**
