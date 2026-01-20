#!/usr/bin/env python3
"""Full pipeline communication test."""

import json
import time

import httpx

BASE_URL = "http://127.0.0.1:8765"


def main():
    # Create pipeline
    pipeline_config = {
        "name": "CommTest2",
        "description": "Two agents that communicate",
        "nodes": [
            {
                "id": "top",
                "type": "agent",
                "position": {"x": 0, "y": 0},
                "data": {
                    "name": "TopAgent",
                    "prompt": 'Ask worker what 2+2 is using send_and_receive(to="worker", message="What is 2+2?"). Report the answer.',
                    "max_turns": 5,
                },
            },
            {
                "id": "worker",
                "type": "agent",
                "position": {"x": 200, "y": 0},
                "data": {
                    "name": "worker",
                    "prompt": "Answer math questions concisely.",
                    "max_turns": 5,
                },
            },
        ],
        "edges": [{"id": "e1", "source": "top", "target": "worker"}],
        "config": {"parallel_execution": False},
    }

    print("Creating pipeline...")
    resp = httpx.post(f"{BASE_URL}/pipelines", json=pipeline_config)
    resp.raise_for_status()
    pipeline = resp.json()
    pipeline_id = pipeline["id"]
    print(f"Pipeline ID: {pipeline_id}")

    print("Running pipeline...")
    resp = httpx.post(f"{BASE_URL}/pipelines/{pipeline_id}/run")
    resp.raise_for_status()
    print(f"Started: {resp.json()}")

    print("Waiting for completion...")
    for i in range(120):
        resp = httpx.get(f"{BASE_URL}/pipelines/{pipeline_id}")
        pipeline = resp.json()
        status = pipeline["status"]
        current = pipeline.get("current_node_id", "none")
        print(f"  [{i*2}s] Status: {status}, current: {current}")
        if status in ("completed", "failed"):
            break
        time.sleep(2)

    print()
    print("=== FINAL STATUS ===")
    print(f"Status: {pipeline['status']}")
    print(f"Error: {pipeline.get('error_message')}")
    print(f"Node agents: {pipeline.get('node_agent_map', {})}")

    # Check agents
    print()
    print("=== AGENTS ===")
    agents_resp = httpx.get(f"{BASE_URL}/agents")
    for agent in agents_resp.json()["agents"]:
        if agent.get("pipeline_id") == pipeline_id:
            resume_count = agent.get("metadata", {}).get("resume_count", 0)
            print(f"  {agent['name']}: status={agent['status']}, resume_count={resume_count}")


if __name__ == "__main__":
    main()
