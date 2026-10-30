"""Cognitive session orchestration for AI-Fusion.

Physical world simulation is owned by the sibling nlt-world-engine repository.
The former Python ECS world is preserved under archive/legacy-world-engine/.
"""

from .session_orchestrator import SessionOrchestrator, SessionConfig, SessionResult

__all__ = ["SessionOrchestrator", "SessionConfig", "SessionResult"]
