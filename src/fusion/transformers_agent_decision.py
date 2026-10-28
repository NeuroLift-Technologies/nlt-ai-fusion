"""Local Transformers-backed semantic decisions for the agent-loop contract."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Mapping

from .agent_loop import (
    PROTOCOL_VERSION,
    AgentLoopProtocolError,
    validate_intent,
    validate_perception,
)
from .agent_loop_choices import SYSTEM_PROMPT, grounded_choices, model_input, parse_decision


class AgentLoopModelOutputError(ValueError):
    """The model response is not a supported semantic decision."""


class TransformersAgentLoopDecision:
    """Generate contract-shaped intents from a local Hugging Face causal model.

    Model and tokenizer are loaded once at construction. The decision call itself is synchronous;
    invoke it from a worker/service context rather than a real-time simulation tick.
    """

    _SYSTEM_PROMPT = SYSTEM_PROMPT

    def __init__(
        self,
        model_path: str | Path,
        *,
        device: str = "cpu",
        max_new_tokens: int = 48,
        tokenizer: Any | None = None,
        model: Any | None = None,
    ) -> None:
        if isinstance(max_new_tokens, bool) or not isinstance(max_new_tokens, int):
            raise TypeError("max_new_tokens must be an integer")
        if max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")
        if (tokenizer is None) != (model is None):
            raise ValueError("tokenizer and model must be supplied together")

        self.model_path = Path(model_path)
        self.device = device
        self.max_new_tokens = max_new_tokens

        if model is None:
            if not self.model_path.is_dir():
                raise FileNotFoundError(
                    f"Local model directory does not exist: {self.model_path}"
                )
            try:
                from transformers import AutoModelForCausalLM, AutoTokenizer
            except ImportError as exc:
                raise ImportError(
                    "TransformersAgentLoopDecision requires torch and transformers; "
                    "install requirements-ai.txt"
                ) from exc

            tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_path),
                local_files_only=True,
                trust_remote_code=False,
            )
            model = AutoModelForCausalLM.from_pretrained(
                str(self.model_path),
                local_files_only=True,
                trust_remote_code=False,
                torch_dtype="auto",
            )

        # Both branches above leave a loaded tokenizer here; annotate so mypy
        # does not carry the parameter's Optional through to call sites.
        self._tokenizer: Any = tokenizer
        self._model = model.to(device)
        self._model.eval()

    def __call__(
        self,
        observation: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Decide one intent. `context` (goal, needs, recent actions) is added to the prompt."""
        validate_perception(observation)
        message = model_input(observation, context)
        messages = [
            {"role": "system", "content": self._SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(message, separators=(",", ":"), ensure_ascii=False),
            },
        ]
        input_ids = self._tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            enable_thinking=False,
            return_tensors="pt",
        ).to(self.device)
        input_length = input_ids.shape[-1]
        generation_options = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": False,
        }
        eos_token_id = getattr(self._tokenizer, "eos_token_id", None)
        if eos_token_id is not None:
            generation_options["pad_token_id"] = eos_token_id

        generated = self._model.generate(input_ids, **generation_options)
        response = self._tokenizer.decode(
            generated[0][input_length:],
            skip_special_tokens=True,
        ).strip()
        decision = parse_decision(
            response, grounded_choices(observation), AgentLoopModelOutputError
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
            raise AgentLoopModelOutputError(
                f"Model decision is not grounded in the observation: {exc}"
            ) from exc
        return intent
