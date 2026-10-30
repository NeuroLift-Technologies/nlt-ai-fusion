"""Gradio ZeroGPU Space - Main Application

Provides a Gradio demo interface for the NeuroLift AI-Fusion baseline decision source.
This runs entirely on CPU with no GPU requirements.

Architecture:
    Gradio UI -> FastAPI endpoints -> FusionAgentLoop (baseline) -> Deterministic decisions

The baseline decision source uses goal-based ranking without any model inference,
making it perfect for free-tier ZeroGPU deployment.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List

import gradio as gr

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.fusion.agent_loop_registry import build_default_registry
from src.fusion.agent_loop import FusionAgentLoop, PROTOCOL_VERSION
from src.fusion.agent_loop_baseline import goal_baseline
from src.fusion.agent_loop_memory import StatefulAgentLoopDecision, DEFAULT_HISTORY_SIZE


# Build the agent loop with baseline decision source
def build_agent_loop() -> FusionAgentLoop:
    """Build the FusionAgentLoop with baseline decision source."""
    registry = build_default_registry()
    
    # Get configuration from environment
    raw_size = os.environ.get("FUSION_AGENT_LOOP_HISTORY", "").strip()
    history_size = int(raw_size) if raw_size else DEFAULT_HISTORY_SIZE
    
    # Baseline decision source (deterministic, no model)
    decision_source = StatefulAgentLoopDecision(
        goal_baseline(registry),
        history_size=history_size
    )
    
    return FusionAgentLoop(
        registry=registry,
        decision_source=decision_source,
        protocol_version=PROTOCOL_VERSION,
    )


# Initialize the agent loop
agent_loop = build_agent_loop()


def get_registered_agents() -> List[str]:
    """Get list of registered agent IDs."""
    return list(agent_loop.registry.agent_ids)


def format_perception_example(agent_id: str) -> Dict[str, Any]:
    """Create a sample perception for the selected agent matching nlt.agent-loop.v1 contract."""
    import uuid
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "messageType": "perception",
        "messageId": f"perception-{uuid.uuid4().hex[:12]}",
        "agentId": agent_id,
        "tick": 12345,
        "scene": {
            "id": "office_01",
            "kind": "interior"
        },
        "self": {
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "velocity": {"x": 0.0, "y": 0.0, "z": 0.0}
        },
        "visibleEntities": [
            {
                "id": "desk_01",
                "kind": "object",
                "position": {"x": 2.0, "y": 0.0, "z": 1.0},
                "affordances": ["approach", "use", "look_at"],
                "occupied": False
            },
            {
                "id": "chair_01",
                "kind": "object",
                "position": {"x": 2.0, "y": 0.0, "z": 0.5},
                "affordances": ["approach", "sit", "look_at"],
                "occupied": False
            },
            {
                "id": "door_01",
                "kind": "object",
                "position": {"x": -2.0, "y": 0.0, "z": 0.0},
                "affordances": ["approach", "use", "look_at"],
                "occupied": False
            }
        ]
    }


def process_perception(agent_id: str, perception_json: str) -> Dict[str, Any]:
    """Process a perception through the agent loop and return the intent."""
    import json
    from src.fusion.agent_loop import validate_perception
    
    try:
        # Parse the JSON
        perception = json.loads(perception_json)
        
        # Ensure agentId matches
        perception["agentId"] = agent_id
        
        # Validate and get intent from agent loop
        intent = agent_loop.handle_observation(perception)
        
        return {
            "success": True,
            "intent": intent,
            "agent_id": agent_id,
            "protocol_version": PROTOCOL_VERSION
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "agent_id": agent_id
        }


def create_demo_perception(agent_id: str) -> Dict[str, Any]:
    """Create a demo perception for testing."""
    return format_perception_example(agent_id)


# Create Gradio interface
with gr.Blocks(title="NeuroLift AI-Fusion ZeroGPU Demo", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # [34mNeuroLift AI-Fusion ZeroGPU Demo
    
    **Deterministic baseline decision source** - No GPU required, runs on free-tier CPU.
    
    This demo shows the Fusion runtime's agent-loop with the **baseline** decision source.
    It uses goal-based ranking to select intents without any model inference.
    """)
    
    gr.Markdown("## Configuration")
    
    with gr.Row():
        agent_dropdown = gr.Dropdown(
            choices=get_registered_agents(),
            value=get_registered_agents()[0] if get_registered_agents() else None,
            label="Select Agent",
            info="Choose a registered Avatar/Aide pair"
        )
    
    gr.Markdown("## Perception Input")
    
    with gr.Row():
        perception_text = gr.Textbox(
            label="Perception JSON",
            placeholder="Paste your perception JSON here...",
            lines=15,
            value=json.dumps(format_perception_example(get_registered_agents()[0] if get_registered_agents() else "stay_alert"), indent=2)
        )
    
    with gr.Row():
        load_example_btn = gr.Button("Load Example Perception", variant="secondary")
        submit_btn = gr.Button("Get Intent", variant="primary")
    
    gr.Markdown("## Result")
    
    with gr.Row():
        result_json = gr.JSON(label="Intent Result")
    
    gr.Markdown("""
    ## About
    
    ### What This Demo Does:
    - ✅ Runs the **baseline** decision source (deterministic, no model)
    - ✅ Demonstrates the `nlt.agent-loop.v1` contract
    - ✅ Returns semantic intents: `approach`, `look_at`, `use`, `sit`, `rest`, `wait`
    - ✅ Works on **ZeroGPU** (free-tier compatible)
    
    ### What It Does NOT Do:
    - ❌ No LLM inference (use Lite CPU Space for GGUF models)
    - ❌ No Godot connection (this is a demo)
    - ❌ No persistence
    
    ### Decision Source
    The baseline uses **goal-based ranking** (AGENT-LOOP-003 F4):
    - Ranks choices by: goal-relevant targets → unvisited places → everything else
    - Always takes the **first-ranked** option
    - Deterministic and repeatable
    
    ### Next Steps
    - Try the [Lite CPU Space](https://huggingface.co/spaces) for GGUF model inference
    - Check the [Full API Space](https://huggingface.co/spaces) for complete capabilities
    - Visit [GitHub](https://github.com/NeuroLift-Technologies/nlt-ai-fusion) for the full project
    """)
    
    # Event handlers
    def update_example(*args):
        agent_id = agent_dropdown.value
        if agent_id:
            return json.dumps(format_perception_example(agent_id), indent=2)
        return ""
    
    load_example_btn.click(
        fn=update_example,
        outputs=perception_text
    )
    
    agent_dropdown.change(
        fn=update_example,
        outputs=perception_text
    )
    
    submit_btn.click(
        fn=process_perception,
        inputs=[agent_dropdown, perception_text],
        outputs=result_json
    )


if __name__ == "__main__":
    import json
    
    print("Starting NeuroLift AI-Fusion ZeroGPU Demo...")
    print(f"Registered agents: {get_registered_agents()}")
    print(f"Protocol version: {PROTOCOL_VERSION}")
    print(f"Decision source: baseline (deterministic)")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share=False
    )
