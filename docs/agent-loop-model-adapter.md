# Local model decision adapter

`src.fusion.TransformersAgentLoopDecision` is an optional, local Hugging Face Transformers
decision source for `FusionAgentLoop`. It loads a causal language model once from a local directory,
then converts each validated physical observation into a semantic intent: `wait`, or one of
`approach`, `use`, `sit`, `rest` and `look_at` on a visible entity that affords it. The
adapter does not download model files, return physical coordinates, or mutate engine state. Its
synchronous inference must run in a Fusion worker/service context, not a real-time simulation tick.

## HTTP endpoint

`src.fusion.agent_loop_http` exposes the Fusion decision seam to Godot over loopback HTTP. From the
repository root, run:

```powershell
python -m src.fusion.agent_loop_http
```

The endpoint listens on `127.0.0.1:8001`; its route is `POST /agent-loop/perception`. Set
`FUSION_AGENT_LOOP_PORT` to change the local port. `FUSION_AGENT_LOOP_MODEL` selects the decision
source: `baseline` (the deterministic, model-free goal baseline), `gguf` (llama.cpp, model path in
`FUSION_GGUF_MODEL`) or `transformers` (model directory in `FUSION_TRANSFORMERS_MODEL`). Unset, it
is `gguf` when `FUSION_GGUF_MODEL` is set and `baseline` otherwise. An unknown value, or a model
that is selected but cannot be loaded, stops the endpoint at startup.

Each decision may take at most `FUSION_AGENT_LOOP_TIMEOUT` seconds (default 15; it must be above
0 and below Godot's own 30 s wait). A decision that takes longer gets 503, and the model is
quarantined: every new request, for any agent, gets 503 at once, without starting a new inference,
until the stuck call returns or the process restarts. Requests already waiting for the model when it
was quarantined get 503 when their own time runs out and never start inference. The timed-out
decision is abandoned: its result is discarded and it is not remembered, since Godot never received
an intent for it. Decisions
on one model instance run one at a time. Perceptions and returned intents are validated, each avatar is limited to one
in-flight decision, and synchronous inference runs outside the ASGI event loop. Invalid, stale, or
unavailable decisions return a non-success response with no intent. ASFDK governance, live-world
revalidation, and physical execution remain Godot responsibilities.

## Registered agents

The endpoint decides only for agents Fusion registered at startup (`src/fusion/agent_loop_registry.py`,
AGENT-LOOP-003 F0). Today that is the StayAlert pair: avatar `stay_alert_001` with Aide
`stay_alert_aide_001`, bound through `SessionOrchestrator`. A perception for any other `agentId`
gets 404 and no intent; Fusion never creates an avatar on demand. On the Godot side, set
`NLT_AGENT_LOOP_AGENT_ID=stay_alert_001` so the engine sends the roster id instead of its internal
`__local_avatar__` key.

## Per-agent memory

The endpoint wraps its decision source in `src.fusion.StatefulAgentLoopDecision`
(`src/fusion/agent_loop_memory.py`, AGENT-LOOP-003 F1). For each `agentId` it keeps the last
`FUSION_AGENT_LOOP_HISTORY` decisions (default 8): tick, scene id, verb, target, and the outcome. An
outcome is what changed by that agent's next perception: horizontal movement, scene change, whether
the target is still visible, distance to it before and after, and whether someone else took it. The
engine's accepted/rejected results do not reach Fusion over this transport, so the next perception
is the outcome source. The history stays in process memory, is never persisted, and is never sent
to the engine. A perception whose tick goes backwards (engine restart) clears that agent's history.

The wrapped source receives `(observation, history)`. With `FUSION_GGUF_MODEL` set, the GGUF
model gets the recent history (with the agent's goal) in its prompt; see the next section. The
goal baseline (F4) uses the same ranking and takes the first option. The model's choice is
also constrained by the history (AGENT-LOOP-003 F3); see "Ranking and anti-repeat" below.

## Goal and recent history in the prompt

With a model configured, each decision's prompt also carries a `context`
(`src/fusion/agent_loop_goals.py`, AGENT-LOOP-003 F2): a short goal and one or two needs derived
from the state of the Avatar registered under the perception's `agentId`, and the agent's last
four decisions with whether anything changed after each. The goal is read from the Avatar without
changing it. Nothing in `context` is sent to the engine. The goal baseline (F4) does not use it.

## Ranking and anti-repeat

With a model configured, `src/fusion/agent_loop_ranking.py` (AGENT-LOOP-003 F3) also shapes the
prompt and the output grammar for each decision. Visible entities are listed goal-relevant first,
then nearest, each with its `distance` in metres and `goalRelevant`. Three kinds of pair are left
out of what the model may output: the last pair when it changed nothing, `approach X` within the
1 m arrival radius, and `look_at X` once X was looked at since entering the current scene (within
the remembered history). `wait` is always allowed. Nothing here is sent to the engine. Measured effect and open decisions: brief §10.

The system prompt names no verb: naming them primed Qwen3-0.6B onto `look_at` in every case
measured. With F3 guidance, the model's input carries no coordinates or velocity, only each
entity's id, kind, distance, relevance, affordances and occupancy (brief §10.4). It also leaves out
`agentId` and `tick`, which the unguided input keeps: the model cannot use them, and the intent's
correlation fields are filled in from the perception, not from the model.

Goal relevance is matched against words in the engine's entity ids (`door_6_office`, `desk_1`,
`sofa_1`; `NEED_KEYWORDS` in `src/fusion/agent_loop_ranking.py`). If the engine renames its id
slugs, relevance silently falls back to distance order with no error, so keep the two in step.

The input also lists `options`: the best 16 allowed decisions, best first (goal-relevant targets, then
`approach` to targets not yet visited, then everything else, with `wait` last), and the output
grammar offers every allowed pair in that order. Without a model, the endpoint uses the goal baseline
(`src/fusion/agent_loop_baseline.py`, AGENT-LOOP-003 F4), which takes the first option. Results:
brief §11.

## Transformers/Safetensors path

`src.fusion.TransformersAgentLoopDecision` remains available as a separate optional path. The
official Qwen3-0.6B Safetensors checkpoint can be downloaded outside the repository, for example
to `C:\Users\<user>\Local_models\Qwen3-0.6B-Safetensors`:

```powershell
hf download Qwen/Qwen3-0.6B --local-dir "C:\Users\<user>\Local_models\Qwen3-0.6B-Safetensors"
```

In an isolated Python environment, install the optional runtime and test runner with
`python -m pip install -r requirements-ai.txt pytest`. Transformers 4.51.0 or newer is required for
Qwen3. Set `NLT_AGENT_LOOP_MODEL_PATH` to the local directory and run:

```powershell
$env:NLT_AGENT_LOOP_MODEL_PATH = "C:\Users\<user>\Local_models\Qwen3-0.6B-Safetensors"
python -m pytest tests/test_fusion/test_transformers_agent_decision.py -q
```

Fusion code can compose the adapter with the existing protocol seam:

```python
decision = TransformersAgentLoopDecision(model_path)
agent_loop = FusionAgentLoop(decide=decision)
intent = agent_loop.handle_observation(perception)
```

## GGUF/llama.cpp path

`src.fusion.LlamaCppAgentLoopDecision` is an independent CPU GGUF adapter; it does not replace or
modify the Transformers path. Its optional runtime is listed separately in `requirements-gguf.txt`.
The first-run model is Qwen3-0.6B-Q8_0 GGUF (about 640 MB), stored outside Git. Given the existing
file at `C:\Users\<user>\Downloads\Qwen3-0.6B-Q8_0.gguf`, create an isolated environment and
install the CPU runtime:

```powershell
py -3.11 -m venv "C:\Users\<user>\Local_models\fusion-gguf-env"
& "C:\Users\<user>\Local_models\fusion-gguf-env\Scripts\python.exe" -m pip install -r requirements-gguf.txt pytest
```

The leading `&` is PowerShell's call operator. It is **only required when the path contains a
space**. The default paths above have none, so this also works:

```powershell
C:\Users\joshd\Local_models\fusion-gguf-env\Scripts\python.exe -m pip install -r requirements-gguf.txt pytest
```

Dropping `&` while the path *is* quoted makes PowerShell read it as a string literal, and the
following `-m` becomes a syntax error:

```
"C:\...\Scripts\python.exe" -m pip install -r requirements-gguf.txt pytest
                                       ~~
Unexpected token '-m' in expression or statement.
```

If the environment already exists, confirm it has pip before reinstalling. Environments created by
`uv` contain `_virtualenv.pth` and ship without pip, so `python -m pip` fails with
`No module named pip`; in that case install with `uv pip install --python <env>\Scripts\python.exe -r
requirements-gguf.txt pytest`, or bootstrap pip once with `python -m ensurepip`.

On Windows, if pip cannot find a compatible prebuilt CPU wheel, install from the llama-cpp-python
CPU wheel index or use the project's documented CMake/Visual Studio build instructions. Set the
GGUF path and run both the mocked contract tests and the opt-in local smoke test:

```powershell
$env:NLT_AGENT_LOOP_GGUF_PATH = "C:\Users\<user>\Downloads\Qwen3-0.6B-Q8_0.gguf"
& "C:\Users\<user>\Local_models\fusion-gguf-env\Scripts\python.exe" -m pytest tests/test_fusion/test_gguf_agent_decision.py -q
```

The environment installs `pytest` but not `pytest-cov`, so coverage is not requested here. Coverage
flags are passed explicitly by CI and by `scripts/run_clearance_tests.py` rather than through
`pytest.ini` addopts; see `pytest.ini` for the 40% gate.

The GGUF adapter defaults to a 2048-token context, two CPU threads, and no GPU layers to keep the
first run bounded. It constrains model output to `wait`, or to a verb and target pair the perception
allows: the target is visible, lists the verb among its affordances, and (for `use`, `sit` and
`rest`) is not marked occupied. `use` on a door or an exit is how the world engine moves an avatar
between scenes. `communicate` is not offered to the models; it needs a dialogue payload v1 does not
carry. Both adapters share these rules, the prompt and the parser (`src/fusion/agent_loop_choices.py`),
then validate the result against the perception. Its
real-model test is marked `slow` and skipped unless the environment variable is set. The other
tests use a fake llama.cpp object and require neither the native runtime nor the model file. Both
model paths reject malformed output, unsupported verbs, and ungrounded targets; neither silently
substitutes a fallback intent.

Both model adapters validate Fusion's message contract and target grounding against the supplied
observation. Neither performs ASFDK governance, current-world revalidation, or physical execution.
