#!/usr/bin/env python3
"""
Agent Message Broker - MCP Server

Provides tools for agents to communicate with each other:
- send_message: Send a message to another agent (or broadcast)
- receive_message: Wait for and receive a message
- list_agents: List all registered agents
- register: Register this agent with a name

Architecture:
  Agent A ──send──▶ [Broker] ◀──recv── Agent B

The broker maintains:
- Agent registry (name -> connection info)
- Message queues (per agent)
- Pub/sub channels for broadcasts

Usage:
  # Start the broker server
  python -m tools.orchestrator.mcp.broker

  # Connect Claude Code to it
  claude --mcp-config '{"broker": {"command": "python", "args": ["-m", "tools.orchestrator.mcp.broker"]}}'
"""

import asyncio
import json
import logging
import sys
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from queue import Queue, Empty

# Configure logging to stderr (stdout is for MCP protocol)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Global message store (in-memory for prototype)
# In production, this would be Redis/shared memory/etc.
_message_queues: dict[str, Queue] = defaultdict(Queue)
_agent_registry: dict[str, dict] = {}
_lock = threading.Lock()


@dataclass
class MCPServer:
    """Simple MCP server implementing the JSON-RPC protocol over stdio."""

    agent_id: str | None = None
    agent_name: str | None = None

    def run(self):
        """Main loop - read JSON-RPC requests from stdin, write responses to stdout."""
        logger.info("MCP Broker server starting...")

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
        """Send a JSON-RPC response to stdout."""
        print(json.dumps(response), flush=True)

    def send_error(self, code: int, message: str, request_id: Any):
        """Send a JSON-RPC error response."""
        self.send_response(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": code, "message": message},
            }
        )

    def handle_request(self, request: dict) -> dict | None:
        """Handle a JSON-RPC request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.debug(f"Handling method: {method}")

        # MCP protocol methods
        if method == "initialize":
            return self.handle_initialize(request_id, params)
        elif method == "initialized":
            return None  # Notification, no response
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
        """Handle MCP initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "agent-broker", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }

    def handle_tools_list(self, request_id: Any) -> dict:
        """Return list of available tools."""
        tools = [
            {
                "name": "register_agent",
                "description": "Register this agent with a name so other agents can send messages to it. Call this first before sending/receiving messages.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Unique name for this agent (e.g., 'worker', 'coordinator')",
                        }
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "send_message",
                "description": "Send a message to another agent. The message will be queued until the target agent calls receive_message.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Name of the target agent, or '*' to broadcast to all",
                        },
                        "message": {
                            "type": "string",
                            "description": "The message content to send",
                        },
                    },
                    "required": ["to", "message"],
                },
            },
            {
                "name": "receive_message",
                "description": "Wait for and receive a message from another agent. Blocks until a message is available or timeout is reached.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "timeout": {
                            "type": "number",
                            "description": "Maximum seconds to wait for a message (default: 30)",
                        },
                        "from_agent": {
                            "type": "string",
                            "description": "Only receive messages from this agent (optional)",
                        },
                    },
                },
            },
            {
                "name": "list_agents",
                "description": "List all currently registered agents.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "check_messages",
                "description": "Check if there are any pending messages without blocking.",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}

    def handle_tool_call(self, request_id: Any, params: dict) -> dict:
        """Handle a tool call."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        logger.info(f"Tool call: {tool_name} with args: {arguments}")

        try:
            if tool_name == "register_agent":
                result = self.tool_register_agent(arguments)
            elif tool_name == "send_message":
                result = self.tool_send_message(arguments)
            elif tool_name == "receive_message":
                result = self.tool_receive_message(arguments)
            elif tool_name == "list_agents":
                result = self.tool_list_agents(arguments)
            elif tool_name == "check_messages":
                result = self.tool_check_messages(arguments)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                },
            }
        except Exception as e:
            logger.exception(f"Tool call failed: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True,
                },
            }

    # Tool implementations

    def tool_register_agent(self, args: dict) -> dict:
        """Register this agent with a name."""
        name = args.get("name", "")
        if not name:
            return {"error": "Name is required"}

        with _lock:
            if name in _agent_registry:
                return {"error": f"Agent '{name}' is already registered"}

            agent_id = f"agent-{int(time.time() * 1000)}"
            _agent_registry[name] = {
                "id": agent_id,
                "name": name,
                "registered_at": time.time(),
            }
            self.agent_id = agent_id
            self.agent_name = name

            # Ensure message queue exists
            _ = _message_queues[name]

        logger.info(f"Registered agent: {name} ({agent_id})")
        return {"status": "registered", "name": name, "id": agent_id}

    def tool_send_message(self, args: dict) -> dict:
        """Send a message to another agent."""
        to = args.get("to", "")
        message = args.get("message", "")

        if not to:
            return {"error": "Target agent name ('to') is required"}
        if not message:
            return {"error": "Message is required"}

        from_name = self.agent_name or "anonymous"

        msg = {
            "from": from_name,
            "to": to,
            "message": message,
            "timestamp": time.time(),
        }

        with _lock:
            if to == "*":
                # Broadcast to all agents
                count = 0
                for name, q in _message_queues.items():
                    if name != from_name:
                        q.put(msg)
                        count += 1
                logger.info(f"Broadcast from {from_name} to {count} agents")
                return {"status": "broadcast", "recipients": count}
            else:
                if to not in _agent_registry:
                    return {"error": f"Agent '{to}' is not registered"}

                _message_queues[to].put(msg)
                logger.info(f"Message queued: {from_name} -> {to}")
                return {"status": "sent", "to": to}

    def tool_receive_message(self, args: dict) -> dict:
        """Wait for and receive a message."""
        timeout = args.get("timeout", 30)
        from_agent = args.get("from_agent")

        if not self.agent_name:
            return {"error": "Must register first with register_agent"}

        queue = _message_queues[self.agent_name]
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                msg = queue.get(timeout=min(1.0, timeout - (time.time() - start_time)))

                # Filter by sender if specified
                if from_agent and msg.get("from") != from_agent:
                    # Put it back and continue waiting
                    queue.put(msg)
                    continue

                logger.info(f"Message received by {self.agent_name}: {msg}")
                return {
                    "status": "received",
                    "from": msg.get("from"),
                    "message": msg.get("message"),
                    "timestamp": msg.get("timestamp"),
                }
            except Empty:
                continue

        return {"status": "timeout", "message": "No message received within timeout"}

    def tool_list_agents(self, args: dict) -> dict:
        """List all registered agents."""
        with _lock:
            agents = list(_agent_registry.values())
        return {"agents": agents}

    def tool_check_messages(self, args: dict) -> dict:
        """Check pending messages without blocking."""
        if not self.agent_name:
            return {"error": "Must register first with register_agent"}

        queue = _message_queues[self.agent_name]
        return {"pending": queue.qsize()}


def main():
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
