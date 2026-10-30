# World Engine — Frontend Prototype

A standalone React prototype that visualises the Avatar/Aide/Scenario world. **Not wired** to the Python simulation engine — the sim ticks locally in the browser. See `docs/specs/world-engine-prototype-schema.md` for the full data contract.

## Run it

No build step. Any static file server works:

```bash
cd prototypes/world-engine
python3 -m http.server 8765
# then open http://127.0.0.1:8765/
```

The page boots React 18 + Babel from a CDN and loads the `.jsx` files in-browser via `<script type="text/babel">`.

## What's here

| File | Role |
|---|---|
| `index.html` | Entry point, CDN loaders, script order |
| `data.js` | Static data — 20 avatars, paired aides, 11 scenarios, 5 rooms, NPCs, strategies, event vocabulary |
| `app.jsx` | Top-level composition, layout, theme/zoom/pan, tweaks panel mount |
| `sim.jsx` | Tick loop, avatar runtime state, event emission, flavor-bias tables |
| `world-view.jsx` | Isometric CSS/SVG renderer (32×16 tile diamond, rooms, props, avatars, NPCs) |
| `hud.jsx` | HUD panels — `TopBar`, `AvatarStateCard`, `EventStream`, `AideLog`, `FleetRoster`, `ScenarioControls`, `ProgressPanel` |
| `tweaks-panel.jsx` | Live-tuning shell with the `__activate_edit_mode` host protocol |
| `world.css` | Full styling |
| `_drafts/` | Earlier single-file drafts preserved verbatim: `world-engine.jsx` (full sim+UI in one file), `tweaks-panel.jsx` (top-level dup), `design-canvas.jsx` (Figma-style artboard shell), and the original `scraps/` |

## Roster

20 ADHD-trait avatars (14 Executive Function, 6 Non-Executive Function), matching the canonical roster in the top-level `README.md` ("The 20 Avatar-Aide-Advocate Pairs"). IDs use snake_case matching the Python repo convention (`src/avatars/adhd_traits/`). The two implemented avatars (`stay_alert`, `task_kickstart`) map directly to existing Python implementations; the remaining 18 are design proposals.

Full table in `docs/specs/world-engine-prototype-schema.md#canonical-roster`.

### Roster history

The original 19-avatar roster (merged from two conflicting zip drafts) was replaced on 2026-10-22 with the README's 20-pair roster, per Joshua W. Dorsey, Sr.'s decision that the README is canonical. Only `stay_alert`, `task_kickstart`, `focus_flow`, `memory_mate` and `impulse_guard` survived by name; the rest were renamed or replaced, and the paired aides were rebuilt to match. The richer schema (blurb, flavor, tag) is unchanged. The `_drafts/world-engine.jsx` original is preserved unchanged for reference.

## What's deliberately NOT here

- **No build pipeline.** No package.json, no Vite/Next/Webpack. Adding one is out of scope until the prototype is promoted into `apps/`.
- **No API wiring.** No fetch calls; all state is in-browser. The `mkEvent` payloads and the `AvatarRuntime` shape (in `sim.jsx`) are the eventual API contract — see the open questions in the schema doc.
- **No tests.** This is a design prototype, not production code.
- **No changes to `src/`.** The Python simulation engine is untouched. The two are reconciled later through an explicit transport decision.
