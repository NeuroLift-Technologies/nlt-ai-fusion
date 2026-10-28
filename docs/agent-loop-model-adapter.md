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
`FUSION_AGENT_LOOP_PORT` to change the local port. Set `FUSION_GGUF_MODEL` to a local GGUF path to
select llama.cpp inference; otherwise the endpoint uses a deterministic, model-free control
decision. Perceptions and returned intents are validated, each avatar is limited to one
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

The wrapped source receives `(observation, history)`. Stateless sources are adapted with
`ignore_history`, so the current models and the fallback decide exactly as before; using the
history is AGENT-LOOP-003 F2/F3 (`docs/specs/AGENT-LOOP-003-fusion-state-and-goals-brief.md`).

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
