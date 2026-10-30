# AI-Fusion Space — runtime documentation

The Hugging Face Space `divergent-tech/Ai-fusion` hosts the AI-Fusion runtime. These
documents are the audit trail and the operating manual; the code lives in
[`spaces/ai-fusion/`](../../spaces/ai-fusion/).

| Document | Answers |
|---|---|
| [audit-and-classification.md](audit-and-classification.md) | What is in the repository, and which class does each module fall into? What does the minimum runtime dependency set look like? What was missing? |
| [architecture-and-boundaries.md](architecture-and-boundaries.md) | How are Avatar/Aide/Advocate preserved? Where does Fusion stop and Godot begin? How is governance carried? What data is durable? Which architectural conflicts are open? |
| [migration-and-deployment.md](migration-and-deployment.md) | What gets reused, adapted or excluded? How is the payload assembled, deployed, health-checked and rolled back? What is the definition-of-done status? |

## Status at a glance

- Runtime: built and verified locally from the assembled payload (20 Space tests, 255
  repository fusion tests green).
- Deployment: **not yet uploaded** — the Space is still `NO_APP_FILE` and this session has
  read-only Hugging Face access. Runbook: migration-and-deployment.md §3.
- Open conflicts: C1–C8 in architecture-and-boundaries.md §6. None were resolved silently.

## Fast path

```bash
spaces/ai-fusion/sync-to-hub.sh --out build/space-ai-fusion   # assemble the payload
python -m pytest spaces/ai-fusion/tests/ -q                    # verify the runtime
spaces/ai-fusion/sync-to-hub.sh --push divergent-tech/Ai-fusion  # deploy
```
