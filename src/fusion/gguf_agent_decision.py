"""Local llama.cpp-backed semantic decisions for the agent-loop contract."""

from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from .agent_loop import (
    PROTOCOL_VERSION,
    AgentLoopProtocolError,
    validate_intent,
    validate_perception,
)
from .agent_loop_choices import (
    SYSTEM_PROMPT,
    decision_schemas,
    grounded_choices,
    model_input,
    option_schemas,
    parse_decision,
)
from .agent_loop_deadline import raise_if_abandoned

if TYPE_CHECKING:
    from .agent_loop_ranking import ChoiceGuidance


class GgufAgentLoopModelOutputError(ValueError):
    """The GGUF model response is not a supported semantic decision."""


class LlamaCppAgentLoopDecision:
    """Generate contract-shaped intents from a local GGUF model via llama.cpp.

    Inference is synchronous; call this decision source from a worker/service context rather than
    from a real-time simulation tick.
    """

    _SYSTEM_PROMPT = SYSTEM_PROMPT

    def __init__(
        self,
        model_path: str | Path,
        *,
        context_size: int = 2048,
        threads: int = 2,
        model: Any | None = None,
    ) -> None:
        if isinstance(context_size, bool) or not isinstance(context_size, int):
            raise TypeError("context_size must be an integer")
        if context_size < 512:
            raise ValueError("context_size must be at least 512 tokens")
        if isinstance(threads, bool) or not isinstance(threads, int):
            raise TypeError("threads must be an integer")
        if threads <= 0:
            raise ValueError("threads must be positive")

        self.model_path = Path(model_path)
        self.context_size = context_size
        self.threads = threads
        self._inference_lock = threading.Lock()

        if model is None:
            if not self.model_path.is_file():
                raise FileNotFoundError(f"Local GGUF model file does not exist: {self.model_path}")
            try:
                from llama_cpp import Llama
            except ImportError as exc:
                raise ImportError(
                    "LlamaCppAgentLoopDecision requires llama-cpp-python; "
                    "install requirements-gguf.txt"
                ) from exc

            model = Llama(
                model_path=str(self.model_path),
                n_ctx=self.context_size,
                n_threads=self.threads,
                n_gpu_layers=0,
                verbose=False,
            )

        self._model = model

    def __call__(
        self,
        observation: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
        guidance: ChoiceGuidance | None = None,
    ) -> dict[str, Any]:
        """Decide one intent. `context` (goal, needs, recent actions) is added to the prompt;
        `guidance` orders the entities and leaves out pairs not worth repeating (F3)."""
        validate_perception(observation)
        message = model_input(observation, context, guidance)
        # Constrain generation to the decisions this perception allows: wait, or a verb with a
        # visible target that lists it among its affordances. With guidance, offered best first.
        choices = grounded_choices(observation, guidance)

        with self._inference_lock:
            # Queued behind a call that timed out: the request is answered, so do not start.
            raise_if_abandoned()
            response = self._model.create_chat_completion(
                messages=[
                    {"role": "system", "content": self._SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            message,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=48,
                response_format={
                    "type": "json_object",
                    "schema": {
                        "oneOf": option_schemas(guidance.options)
                        if guidance is not None
                        else decision_schemas(choices)
                    },
                },
            )

        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GgufAgentLoopModelOutputError(
                "llama.cpp response did not contain a chat message"
            ) from exc
        if not isinstance(content, str):
            raise GgufAgentLoopModelOutputError(
                "llama.cpp response content must be a string"
            )
        decision = parse_decision(
            content.strip(), choices, GgufAgentLoopModelOutputError
        )

        intent: dict[str, Any] = {
            "protocolVersion": PROTOCOL_VERSION,
            "messageType": "intent",
            "messageId": f"fusion-{uuid.uuid4().hex}",
            "agentId": observation["agentId"],
            "observedTick": observation["tick"],
            "verb": decision["verb"],
        }
        if "targetId" in decision:
            intent["targetId"] = decision["targetId"]

        try:
            validate_intent(intent, observation)
        except AgentLoopProtocolError as exc:
            raise GgufAgentLoopModelOutputError(
                f"GGUF model decision is not grounded in the observation: {exc}"
            ) from exc
        return intent
