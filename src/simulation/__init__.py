"""Cognitive training workflow exports.

The authoritative physical simulation is implemented by the sibling
nlt-world-engine Godot project. Legacy Python world-engine modules are archived
under archive/legacy-world-engine and are not imported here.
"""
from .session_orchestrator import SessionOrchestrator, SessionConfig, SessionResult

__all__ = ["SessionOrchestrator", "SessionConfig", "SessionResult"]
