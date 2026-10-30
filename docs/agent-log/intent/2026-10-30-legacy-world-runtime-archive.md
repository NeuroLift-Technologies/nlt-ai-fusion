# Intent Log — Legacy World Runtime Archive

**Date:** 2026-10-30T11:39:48.559Z  
**Agent:** ChatGPT GPT-6  
**Action:** Archive obsolete parallel physical simulation implementations in `nlt-ai-fusion`, retain the cognitive scenario catalogue, remove the legacy Python world router from active backend routing, and align current documentation.  
**Rationale:** Godot 4.7.2 in `nlt-world-engine` is the authoritative physical simulation. The Python ECS/grid engine, Cloudflare Durable Object world, old browser prototypes, and their clients create competing physical authorities and confuse the cognitive/physical boundary.  
**Risks:** Hidden imports or workflows may still reference archived paths; CI may expose them. Historical behavior is preserved but no longer importable from active paths. A deployed Cloudflare Worker, if any, is not decommissioned by this source change.  
**Alternatives considered:** Delete obsolete code (rejected because historical work should remain inspectable); leave all code active and rely on documentation (rejected because it leaves competing runtime code and dependencies in active paths).  
**Escalation needed:** No additional architecture decision requested; this implements the user's explicit archive request under the existing Godot/Fusion boundary. Any infrastructure decommissioning remains out of scope.
