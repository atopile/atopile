#!/usr/bin/env python3
"""
Agent Communication Bridge - Simple MCP Server

Provides a single tool for agent-to-agent communication:
  send_and_receive(to, message) -> response

The orchestrator:
  1. Spawns all pipeline agents at start
  2. Routes messages along pipeline edges
  3. Handles request/response blocking

Usage:
  claude --mcp-config '{"bridge": {"command": "uv", "args": ["run", "python", "-m", "tools.orchestrator.mcp.bridge"]}}'

Environment:
  BRIDGE_URL - Orchestrator bridge endpoint (default: http://127.0.0.1:8765)
  AGENT_NAME - This agent's name (set by orchestrator when spawning)
"""

import json
import logging
import os
import sys
from typing import Any

import httpx

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

BRIDGE_URL = os.environ.get("BRIDGE_URL", "http://127.0.0.1:8765")
AGENT_NAME = os.environ.get("AGENT_NAME", "")
PIPELINE_ID = os.environ.get("PIPELINE_ID", "")  # Pipeline context for edge validation


class BridgeMCPServer:
    """MCP server providing send_and_receive for agent communication."""

    def __init__(self):
        self.bridge_url = BRIDGE_URL
        self.agent_name = AGENT_NAME
        self.pipeline_id = PIPELINE_ID
        self.http = httpx.Client(timeout=300.0)  # Long timeout for blocking calls

    def run(self):
        """Main loop - JSON-RPC over stdio."""
        logger.info(f"Bridge MCP starting (agent={self.agent_name}, pipeline={self.pipeline_id}, bridge={self.bridge_url})")

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = self.handle(request)
                if response:
                    print(json.dumps(response), flush=True)
            except Exception as e:
                logger.exception(f"Error: {e}")

    def handle(self, request: dict) -> dict | None:
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "agent-bridge", "version": "0.1.0"},
                    "capabilities": {"tools": {}}
                }
            }
        elif method == "initialized":
            return None
        elif method == "tools/list":
            return self.tools_list(req_id)
        elif method == "tools/call":
            return self.tool_call(req_id, params)
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        return None

    def tools_list(self, req_id: Any) -> dict:
        tools = [
            {
                "name": "send_and_receive",
                "description": (
                    "Send a message to another agent and wait for their response. "
                    "This blocks until the target agent responds. "
                    "You can only communicate with agents you're connected to in the pipeline."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Name of the target agent to send to"
                        },
                        "message": {
                            "type": "string",
                            "description": "Message to send (can be plain text or JSON)"
                        }
                    },
                    "required": ["to", "message"]
                }
            }
        ]

        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

    def tool_call(self, req_id: Any, params: dict) -> dict:
        tool = params.get("name", "")
        args = params.get("arguments", {})

        if tool == "send_and_receive":
            result = self.send_and_receive(args)
        else:
            result = {"error": f"Unknown tool: {tool}"}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result) if isinstance(result, dict) else str(result)}]
            }
        }

    def send_and_receive(self, args: dict) -> dict | str:
        """Send message to agent, block until response."""
        to = args.get("to", "")
        message = args.get("message", "")

        if not to:
            return {"error": "Target agent name ('to') is required"}
        if not message:
            return {"error": "Message is required"}
        if not self.agent_name:
            return {"error": "AGENT_NAME not set - this agent wasn't spawned by the orchestrator"}

        try:
            # POST to orchestrator's bridge endpoint
            payload = {
                "from_agent": self.agent_name,
                "to_agent": to,
                "message": message
            }
            if self.pipeline_id:
                payload["pipeline_id"] = self.pipeline_id

            response = self.http.post(
                f"{self.bridge_url}/bridge/send",
                json=payload,
                timeout=300.0  # 5 min timeout for long operations
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "response":
                return data.get("response", "")
            elif data.get("status") == "error":
                return {"error": data.get("message", "Unknown error")}
            else:
                return data

        except httpx.ConnectError:
            return {"error": f"Cannot connect to orchestrator at {self.bridge_url}"}
        except httpx.TimeoutException:
            return {"error": "Request timed out waiting for response"}
        except Exception as e:
            return {"error": str(e)}


def main():
    server = BridgeMCPServer()
    server.run()


if __name__ == "__main__":
    main()
