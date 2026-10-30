"""Gradio Lite CPU Space - Main Application

Provides a Gradio demo interface for the NeuroLift AI-Fusion with GGUF model support.
This runs GGUF models on CPU, compatible with free-tier Lite CPU tier.

Architecture:
    Gradio UI -> FastAPI endpoints -> FusionAgentLoop (GGUF) -> LLM Inference on CPU

The GGUF decision source uses llama-cpp-python for CPU-based model inference,
enabling actual LLM-based decision making without GPU.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

import gradio as gr

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.fusion.agent_loop_registry import build_default_registry
from src.fusion.agent_loop import FusionAgentLoop, PROTOCOL_VERSION
from src.fusion.agent_loop_memory import StatefulAgentLoopDecision, DEFAULT_HISTORY_SIZE


def build_agent_loop() -> FusionAgentLoop:
    """Build the FusionAgentLoop with GGUF decision source."""
    registry = build_default_registry()
    
    # Get configuration from environment
    raw_size = os.environ.get("FUSION_AGENT_LOOP_HISTORY", "").strip()
    history_size = int(raw_size) if raw_size else DEFAULT_HISTORY_SIZE
    
    # Import here to avoid loading llama-cpp-python at import time
    from src.fusion.gguf_agent_decision import LlamaCppAgentLoopDecision
    
    model_path = os.environ.get("FUSION_GGUF_MODEL", "").strip()
    if not model_path or not Path(model_path).exists():
        # Fall back to baseline if no model is available
        from src.fusion.agent_loop_baseline import goal_baseline
        print(f"WARNING: GGUF model not found at {model_path}, falling back to baseline")
        decision_source = StatefulAgentLoopDecision(
            goal_baseline(registry),
            history_size=history_size
        )
    else:
        print(f"Loading GGUF model from {model_path}")
        decision_source = StatefulAgentLoopDecision(
            LlamaCppAgentLoopDecision(model_path),
            history_size=history_size
        )
    
    return FusionAgentLoop(
        registry=registry,
        decision_source=decision_source,
        protocol_version=PROTOCOL_VERSION,
    )


# Initialize the agent loop (lazy loading for GGUF)
_agent_loop: Optional[FusionAgentLoop] = None

def get_agent_loop() -> FusionAgentLoop:
    """Get or create the agent loop instance."""
    global _agent_loop
    if _agent_loop is None:
        _agent_loop = build_agent_loop()
    return _agent_loop


def get_registered_agents() -> List[str]:
    """Get list of registered agent IDs."""
    return list(get_agent_loop().registry.agent_ids)


def check_model_loaded() -> bool:
    """Check if a GGUF model is loaded."""
    model_path = os.environ.get("FUSION_GGUF_MODEL", "").strip()
    if not model_path:
        return False
    return Path(model_path).exists()


def get_model_info() -> Dict[str, Any]:
    """Get information about the loaded model."""
    model_path = os.environ.get("FUSION_GGUF_MODEL", "").strip()
    if not model_path or not Path(model_path).exists():
        return {"loaded": False, "path": model_path, "error": "Model file not found"}
    
    try:
        file_size = Path(model_path).stat().st_size
        return {
            "loaded": True,
            "path": model_path,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2)
        }
    except Exception as e:
        return {"loaded": False, "path": model_path, "error": str(e)}


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
    try:
        # Parse the JSON
        perception = json.loads(perception_json)
        
        # Ensure agentId matches
        perception["agentId"] = agent_id
        
        # Get intent from agent loop
        agent_loop = get_agent_loop()
        intent = agent_loop.handle_observation(perception)
        
        return {
            "success": True,
            "intent": intent,
            "agent_id": agent_id,
            "protocol_version": PROTOCOL_VERSION,
            "model_info": get_model_info()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "agent_id": agent_id,
            "model_info": get_model_info()
        }


def create_demo_perception(agent_id: str) -> Dict[str, Any]:
    """Create a demo perception for testing."""
    return format_perception_example(agent_id)


# Create Gradio interface
with gr.Blocks(title="NeuroLift AI-Fusion Lite CPU Demo", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # [32mNeuroLift AI-Fusion Lite CPU Demo
    
    **GGUF model inference on CPU** - Runs small language models on free-tier Lite CPU.
    
    This demo shows the Fusion runtime's agent-loop with **GGUF model support** for CPU inference.
    """)
    
    gr.Markdown("## Model Status")
    
    model_status = gr.JSON(label="Model Information", value=get_model_info())
    
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
        submit_btn = gr.Button("Get Intent (with LLM)", variant="primary")
    
    gr.Markdown("## Result")
    
    with gr.Row():
        result_json = gr.JSON(label="Intent Result")
    
    gr.Markdown("""
    ## About
    
    ### What This Demo Does:
    - ✅ Runs **GGUF models on CPU** via llama-cpp-python
    - ✅ Demonstrates the `nlt.agent-loop.v1` contract with LLM inference
    - ✅ Returns semantic intents with model-based decision making
    - ✅ Works on **Lite CPU** tier (free-tier compatible for small models)
    
    ### What It Does NOT Do:
    - ❌ No GPU acceleration (CPU-only inference)
    - ❌ No Godot connection (this is a demo)
    - ❌ No persistence
    - ❌ Limited to small models (< 2GB recommended)
    
    ### Recommended Models for Free Tier
    
    These models should work on free-tier Lite CPU (8GB RAM):
    
    | Model | Size | Speed | Quality |
    |-------|------|-------|---------|
    | Qwen2.5-0.6B-Instruct-Q4_K_M | ~380MB | ⚡⚡⚡ | ⭐⭐⭐⭐ |
    | TinyLlama-1.1B-Instruct-Q4_K_M | ~590MB | ⚡⚡ | ⭐⭐⭐⭐ |
    | Phi-2-Q4_K_M | ~1.3GB | ⚡ | ⭐⭐⭐⭐⭐ |
    
    **Avoid models > 2GB** - they may exceed free-tier memory limits.
    
    ### Setup Instructions
    
    1. **Upload your GGUF model** to `/data/models/` in your Space
    2. **Set environment variables**:
       - `FUSION_AGENT_LOOP_MODEL=gguf`
       - `FUSION_GGUF_MODEL=/data/models/your-model.gguf`
    3. **Deploy** the Space
    4. **Wait for model loading** (30-60 seconds for first load)
    
    ### Performance Notes
    
    - **First load**: Model loading takes 30-60 seconds
    - **CPU inference**: Expect 1-5 seconds per decision depending on model size
    - **Timeout**: Default is 20 seconds (must be < 30s for Godot)
    - **Memory**: Models > 2GB may not work on free tier
    
    ### Next Steps
    - Try different GGUF models
    - Monitor decision times in the UI
    - For larger models, upgrade to paid tier with GPU
    - Visit [GitHub](https://github.com/NeuroLift-Technologies/nlt-ai-fusion) for the full project
    """)
    
    # Event handlers
    def update_example(*args):
        agent_id = agent_dropdown.value
        if agent_id:
            return json.dumps(format_perception_example(agent_id), indent=2)
        return ""
    
    def update_model_status():
        return get_model_info()
    
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
    
    # Refresh model status periodically
    demo.load(update_model_status, None, model_status, every=10)


if __name__ == "__main__":
    print("Starting NeuroLift AI-Fusion Lite CPU Demo...")
    print(f"Registered agents: {get_registered_agents()}")
    print(f"Protocol version: {PROTOCOL_VERSION}")
    print(f"Model info: {get_model_info()}")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share=False
    )
