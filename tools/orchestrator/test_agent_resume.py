#!/usr/bin/env python3
"""Test agent resume functionality."""

import time

import httpx

BASE_URL = "http://127.0.0.1:8765"


def main():
    # Get the agents from the pipeline
    agents_resp = httpx.get(f"{BASE_URL}/agents")
    agents = agents_resp.json()["agents"]

    # Find the TopAgent from the last test
    top_agent = None
    worker_agent = None
    for agent in agents:
        if agent.get("name") == "CommTest2.TopAgent":
            top_agent = agent
        if agent.get("name") == "CommTest2.worker":
            worker_agent = agent

    if not top_agent:
        print("TopAgent not found!")
        return 1

    print(f"Found TopAgent: {top_agent['id']}")
    print(f"  Status: {top_agent['status']}")
    print(f"  Session ID: {top_agent.get('session_id')}")

    if worker_agent:
        print(f"\nFound worker: {worker_agent['id']}")
        print(f"  Status: {worker_agent['status']}")
        print(
            f"  Resume count before: {worker_agent.get('metadata', {}).get('resume_count', 0)}"
        )

    # Resume the top agent
    print("\nResuming TopAgent to ask worker another question...")
    resp = httpx.post(
        f"{BASE_URL}/agents/{top_agent['id']}/resume",
        json={
            "prompt": 'Ask the worker what 3+3 is using send_and_receive(to="worker", message="What is 3+3?"). Report the answer.',
            "max_turns": 5,
        },
        timeout=120.0,
    )
    print(f"Resume status: {resp.status_code}")
    print(f"Resume response: {resp.json()}")

    # Wait for completion
    print("\nWaiting for TopAgent to complete...")
    for i in range(60):
        resp = httpx.get(f"{BASE_URL}/agents/{top_agent['id']}")
        agent = resp.json()["agent"]
        print(f"  [{i * 2}s] Status: {agent['status']}")
        if agent["status"] in ("completed", "failed"):
            break
        time.sleep(2)

    # Check final state
    print("\n=== FINAL AGENT STATES ===")
    agents_resp = httpx.get(f"{BASE_URL}/agents")
    for agent in agents_resp.json()["agents"]:
        if "CommTest2" in (agent.get("name") or ""):
            resume_count = agent.get("metadata", {}).get("resume_count", 0)
            print(
                f"  {agent['name']}: status={agent['status']}, resume_count={resume_count}"
            )

    # Count total workers with that name
    worker_count = sum(
        1 for a in agents_resp.json()["agents"] if a.get("name") == "CommTest2.worker"
    )
    print(f"\nTotal 'CommTest2.worker' agents: {worker_count}")
    if worker_count == 1:
        print("SUCCESS: Worker was reused, not spawned new!")
    else:
        print(f"ISSUE: Expected 1 worker but found {worker_count}")

    return 0


if __name__ == "__main__":
    exit(main())
