#!/usr/bin/env python3
"""
Agent Message Broker - MCP Client

This MCP server runs per-agent and connects to the central HTTP broker.
It provides tools for agents to communicate with each other.

Usage:
    # Start the central broker first
    python -m tools.orchestrator.mcp.broker_server

    # Then run Claude Code with this MCP client
    claude --mcp-config '{"broker": {"command": "python", "args": ["-m", "tools.orchestrator.mcp.broker_client"]}}'
"""

import json
import logging
import os
import sys
import time
from typing import Any

import httpx

# Configure logging to stderr
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Broker URL - can be overridden via environment variable
BROKER_URL = os.environ.get("BROKER_URL", "http://127.0.0.1:8766")


class MCPBrokerClient:
    """MCP server that acts as a client to the central HTTP broker."""

    def __init__(self, broker_url: str = BROKER_URL):
        self.broker_url = broker_url
        self.agent_name: str | None = None
        self.http_client = httpx.Client(timeout=60.0)

    def run(self):
        """Main loop - read JSON-RPC requests from stdin."""
        logger.info(f"MCP Broker client starting (broker: {self.broker_url})...")

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    self.send_response(response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                self.send_error(-32700, "Parse error", None)
            except Exception as e:
                logger.exception(f"Error handling request: {e}")
                self.send_error(-32603, str(e), request.get("id"))

    def send_response(self, response: dict):
        """Send a JSON-RPC response."""
        print(json.dumps(response), flush=True)

    def send_error(self, code: int, message: str, request_id: Any):
        """Send a JSON-RPC error response."""
        self.send_response({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message}
        })

    def handle_request(self, request: dict) -> dict | None:
        """Handle a JSON-RPC request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.debug(f"Handling method: {method}")

        if method == "initialize":
            return self.handle_initialize(request_id, params)
        elif method == "initialized":
            return None
        elif method == "tools/list":
            return self.handle_tools_list(request_id)
        elif method == "tools/call":
            return self.handle_tool_call(request_id, params)
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        else:
            logger.warning(f"Unknown method: {method}")
            return None

    def handle_initialize(self, request_id: Any, params: dict) -> dict:
        """Handle MCP initialize."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "agent-broker-client",
                    "version": "0.1.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }

    def handle_tools_list(self, request_id: Any) -> dict:
        """Return available tools."""
        tools = [
            {
                "name": "broker_register",
                "description": "Register this agent with the message broker. Call this first before sending/receiving messages. This allows other agents to send messages to you by name.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Unique name for this agent (e.g., 'coordinator', 'worker-1', 'analyzer')"
                        }
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "broker_send",
                "description": "Send a message to another agent. The message is queued until the target agent receives it. Use '*' as the target to broadcast to all agents.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Name of the target agent, or '*' to broadcast to all registered agents"
                        },
                        "message": {
                            "type": "string",
                            "description": "The message content to send. Can be plain text or JSON."
                        }
                    },
                    "required": ["to", "message"]
                }
            },
            {
                "name": "broker_receive",
                "description": "Wait for and receive a message from another agent. This blocks until a message arrives or the timeout is reached.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "timeout": {
                            "type": "number",
                            "description": "Maximum seconds to wait for a message (default: 30)"
                        },
                        "from_agent": {
                            "type": "string",
                            "description": "Only receive messages from this specific agent (optional)"
                        }
                    }
                }
            },
            {
                "name": "broker_list_agents",
                "description": "List all agents currently registered with the broker.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "broker_check_messages",
                "description": "Check how many messages are waiting in your queue without blocking.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "broker_spawn_worker",
                "description": "Spawn a new worker agent to perform a task. The worker will be started by the orchestrator and can communicate back via the broker. The worker automatically registers with the broker under the given name.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Unique name for the worker agent (e.g., 'analyzer', 'code-reviewer')"
                        },
                        "task": {
                            "type": "string",
                            "description": "The task/prompt for the worker to execute. Include instructions to send results back if needed."
                        }
                    },
                    "required": ["name", "task"]
                }
            }
        ]

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        }

    def handle_tool_call(self, request_id: Any, params: dict) -> dict:
        """Handle a tool call by forwarding to the HTTP broker."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        logger.info(f"Tool call: {tool_name}")

        try:
            if tool_name == "broker_register":
                result = self.tool_register(arguments)
            elif tool_name == "broker_send":
                result = self.tool_send(arguments)
            elif tool_name == "broker_receive":
                result = self.tool_receive(arguments)
            elif tool_name == "broker_list_agents":
                result = self.tool_list_agents(arguments)
            elif tool_name == "broker_check_messages":
                result = self.tool_check_messages(arguments)
            elif tool_name == "broker_spawn_worker":
                result = self.tool_spawn_worker(arguments)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }
        except httpx.ConnectError:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: Cannot connect to broker at {self.broker_url}. Is the broker server running?"}],
                    "isError": True
                }
            }
        except Exception as e:
            logger.exception(f"Tool call failed: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True
                }
            }

    # Tool implementations - forward to HTTP broker

    def tool_register(self, args: dict) -> dict:
        """Register with the broker."""
        name = args.get("name", "")
        if not name:
            return {"error": "Name is required"}

        response = self.http_client.post(
            f"{self.broker_url}/register",
            json={"name": name}
        )
        response.raise_for_status()
        result = response.json()

        self.agent_name = name
        return result

    def tool_send(self, args: dict) -> dict:
        """Send a message via the broker."""
        to = args.get("to", "")
        message = args.get("message", "")

        if not to:
            return {"error": "Target agent ('to') is required"}
        if not message:
            return {"error": "Message is required"}
        if not self.agent_name:
            return {"error": "Must register first with broker_register"}

        response = self.http_client.post(
            f"{self.broker_url}/send",
            json={
                "from_agent": self.agent_name,
                "to": to,
                "message": message
            }
        )
        response.raise_for_status()
        return response.json()

    def tool_receive(self, args: dict) -> dict:
        """Receive a message from the broker."""
        timeout = args.get("timeout", 30)
        from_agent = args.get("from_agent")

        if not self.agent_name:
            return {"error": "Must register first with broker_register"}

        params = {"timeout": timeout}
        if from_agent:
            params["from_agent"] = from_agent

        response = self.http_client.get(
            f"{self.broker_url}/receive/{self.agent_name}",
            params=params
        )
        response.raise_for_status()
        return response.json()

    def tool_list_agents(self, args: dict) -> dict:
        """List registered agents."""
        response = self.http_client.get(f"{self.broker_url}/agents")
        response.raise_for_status()
        return response.json()

    def tool_check_messages(self, args: dict) -> dict:
        """Check pending messages."""
        if not self.agent_name:
            return {"error": "Must register first with broker_register"}

        response = self.http_client.get(
            f"{self.broker_url}/messages/{self.agent_name}"
        )
        response.raise_for_status()
        return response.json()

    def tool_spawn_worker(self, args: dict) -> dict:
        """Request the orchestrator to spawn a worker agent."""
        name = args.get("name", "")
        task = args.get("task", "")

        if not name:
            return {"error": "Worker name is required"}
        if not task:
            return {"error": "Task is required"}

        # Build the full prompt that includes broker registration and response
        respond_to = self.agent_name
        full_prompt = f"""You are a worker agent named '{name}'.

IMPORTANT: First, use broker_register to register yourself as '{name}'.

Your task: {task}

When you complete the task, use broker_send to send your result back to '{respond_to or "the requester"}'.
"""

        response = self.http_client.post(
            f"{self.broker_url}/spawn",
            json={
                "name": name,
                "prompt": full_prompt,
                "respond_to": respond_to
            }
        )
        response.raise_for_status()
        result = response.json()

        return {
            "status": "spawning",
            "worker_name": name,
            "message": f"Worker '{name}' is being spawned. Use broker_receive(from_agent='{name}') to get the result."
        }


def main():
    client = MCPBrokerClient()
    client.run()


if __name__ == "__main__":
    main()
