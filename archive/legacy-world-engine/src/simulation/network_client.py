import asyncio
import json
import logging
from typing import Dict, Any, Optional

try:
    import websockets
except ImportError:
    logging.warning("websockets library not found. Run: pip install websockets")

class RemoteAgentInterface:
    """
    Connects to the Cloudflare Durable Object World Engine via WebSockets.
    Replaces the local AgentInterface.
    """
    def __init__(self, agent_id: str, server_url: str = "ws://localhost:8787/connect"):
        self.agent_id = agent_id
        self.server_url = f"{server_url}?agentId={agent_id}"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.last_perception: Dict[str, Any] = {}
        self.is_busy: bool = False

    async def connect(self):
        """Connect to the Cloudflare Worker WebSocket."""
        print(f"[{self.agent_id}] Connecting to {self.server_url}...")
        self.ws = await websockets.connect(self.server_url)
        print(f"[{self.agent_id}] Connected!")
        
        # Start background listener
        asyncio.create_task(self._listen_loop())

    async def _listen_loop(self):
        """Listen for server broadcasts."""
        try:
            async for message in self.ws:
                data = json.loads(message)
                if data.get("type") == "tick":
                    # Server broadcasted a world tick
                    # We can parse the agents array to update our local state
                    for agent_data in data.get("agents", []):
                        if agent_data["id"] == self.agent_id:
                            self.is_busy = agent_data.get("busy", False)
                elif data.get("type") == "perception":
                    self.last_perception = data
        except Exception as e:
            print(f"[{self.agent_id}] Connection lost: {e}")

    async def perceive(self, radius: int = 10) -> Dict[str, Any]:
        """Request the server for surrounding entities."""
        if not self.ws:
            return {}
            
        await self.ws.send(json.dumps({
            "type": "perceive",
            "radius": radius
        }))
        
        # We wait briefly for the _listen_loop to populate last_perception
        # In a production app, we'd use asyncio.Event to await the specific response.
        await asyncio.sleep(0.1)
        return self.last_perception

    async def submit_intent(self, intent_type: str, data: Dict[str, Any] = None) -> bool:
        """Send an action to the World Engine."""
        if self.is_busy:
            return False
            
        if not self.ws:
            return False
            
        await self.ws.send(json.dumps({
            "type": "intent",
            "intent": {
                "type": intent_type,
                "data": data or {}
            }
        }))
        self.is_busy = True
        return True

async def main():
    agent = RemoteAgentInterface("TestAvatar_01")
    try:
        await agent.connect()
        
        print("Perceiving world...")
        perception = await agent.perceive(radius=20)
        print("Perception result:", perception)
        
        print("Moving to (10, 10)...")
        await agent.submit_intent("move", {"x": 10, "y": 10})
        
        # Keep alive
        for _ in range(10):
            await asyncio.sleep(1)
            print(f"Busy status: {agent.is_busy}")
            
    except Exception as e:
        print(f"Demo failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
