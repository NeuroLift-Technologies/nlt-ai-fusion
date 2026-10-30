# Cloudflare Infrastructure Notes

**Repository:** `NeuroLift-Technologies/nlt-ai-fusion`  
**Last updated:** 2026-10-30

This document covers Cloudflare as supporting infrastructure for NeuroLift services. Cloudflare is not the authoritative physical simulation runtime and is not currently the Fusion agent-loop transport.

## Current architecture boundary

- **World Engine physical simulation:** Godot 4.7.2 in [`nlt-world-engine`](https://github.com/NeuroLift-Technologies/nlt-world-engine).
- **World Engine Reviewer:** human-facing observer of Godot world state.
- **AI-Fusion:** cognitive models, coaching, session orchestration, model adapters, and fusion.
- **Cloudflare:** DNS, domain security, CDN, and separately approved edge workloads where needed.

## Retired Cloudflare World Engine

The former `neurolift-world-engine` Worker implemented a separate Durable Object ECS simulation with a WebSocket `/connect` protocol. That implementation competed with Godot as a physical simulation authority and has been moved to [`archive/legacy-world-engine/cloudflare-engine/`](../../archive/legacy-world-engine/cloudflare-engine/).

The associated root and package Wrangler configurations, WebSocket client, and Three.js client are also archived. Do not deploy or extend those archived files as the active World Engine.

**Important:** Archiving repository source does not delete, disable, or decommission a Worker that may already be deployed in a Cloudflare account. Any infrastructure decommissioning requires a separate explicit operational decision and verification.

## Domain and DNS

1. Manage DNS records in the Cloudflare dashboard for the relevant zone.
2. Keep origin records and proxy settings aligned with the actual hosting provider.
3. Use TLS in strict mode where the origin supports it.
4. Do not copy account IDs, API tokens, zone IDs, or credentials into tracked configuration.
5. Scope API tokens to the minimum required permissions and store them only in approved secret stores.

## Workers and Pages

Cloudflare Workers and Pages remain available for independently approved edge services and static sites. New Workers must have a clearly defined owner, purpose, deployment target, authentication model, and operational runbook. They must not recreate the physical simulation already owned by Godot.

Do not add a Wrangler configuration or deployment workflow to this repository without explicit architectural approval.

## Security and operations

- Keep credentials out of source control and logs.
- Restrict origins and CORS to required application surfaces.
- Authenticate service-to-service requests; do not treat an obscure URL as authentication.
- Define rate limits, request-size limits, timeouts, and failure behavior before exposing APIs.
- Review Cloudflare Worker routes and deployed resources separately from repository code.
