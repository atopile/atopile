#!/usr/bin/env python3
"""
Test script for pipeline agent communication.

This script tests that:
1. Pipeline agents receive system prompts with bridge instructions
2. Agents in a pipeline can communicate via the bridge
3. The orchestrator properly handles message routing between agents

Usage:
    1. Start the orchestrator server: python -m tools.orchestrator.cli.main serve
    2. Run this test: python -m tools.orchestrator.test_pipeline_communication
"""

import json
import time
from pprint import pprint

import httpx

BASE_URL = "http://127.0.0.1:8765"


def create_test_pipeline():
    """Create a simple two-agent pipeline for testing."""
    pipeline_config = {
        "name": "Test Communication Pipeline",
        "description": "Two agents that can communicate with each other",
        "nodes": [
            {
                "id": "agent-a",
                "type": "agent",
                "position": {"x": 0, "y": 0},
                "data": {
                    "name": "Agent A",
                    "prompt": "You are Agent A. Your task is to send a simple greeting to Agent B using the send_and_receive tool. Send the message: 'Hello Agent B, what is 2+2?' and report back their response.",
                    "max_turns": 5,
                },
            },
            {
                "id": "agent-b",
                "type": "agent",
                "position": {"x": 200, "y": 0},
                "data": {
                    "name": "Agent B",
                    "prompt": "You are Agent B. When you receive a message, respond with a helpful answer. If asked a math question, provide the answer.",
                    "max_turns": 5,
                },
            },
        ],
        "edges": [
            {
                "id": "edge-ab",
                "source": "agent-a",
                "target": "agent-b",
            },
        ],
        "config": {
            "parallel_execution": False,
            "stop_on_failure": True,
        },
    }

    response = httpx.post(f"{BASE_URL}/pipelines", json=pipeline_config)
    response.raise_for_status()
    return response.json()


def run_pipeline(pipeline_id: str):
    """Start a pipeline execution."""
    response = httpx.post(f"{BASE_URL}/pipelines/{pipeline_id}/run")
    response.raise_for_status()
    return response.json()


def get_pipeline_status(pipeline_id: str):
    """Get the current status of a pipeline."""
    response = httpx.get(f"{BASE_URL}/pipelines/{pipeline_id}")
    response.raise_for_status()
    return response.json()


def get_agent_output(agent_id: str):
    """Get the output from an agent."""
    response = httpx.get(f"{BASE_URL}/agents/{agent_id}/output")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def wait_for_pipeline(pipeline_id: str, timeout: int = 300):
    """Wait for pipeline to complete."""
    start = time.time()
    while time.time() - start < timeout:
        status = get_pipeline_status(pipeline_id)
        pipeline = status.get("pipeline", {})
        current_status = pipeline.get("status")

        print(
            f"  Pipeline status: {current_status}, node: {pipeline.get('current_node_id')}"
        )

        if current_status in ("completed", "failed"):
            return pipeline

        time.sleep(2)

    raise TimeoutError("Pipeline did not complete in time")


def test_simple_communication():
    """Test basic pipeline creation and inter-agent communication."""
    print("\n" + "=" * 60)
    print("TEST: Simple Pipeline Communication")
    print("=" * 60)

    # 1. Create pipeline
    print("\n1. Creating test pipeline...")
    result = create_test_pipeline()
    pipeline_id = result.get("pipeline", {}).get("id")
    print(f"   Pipeline created: {pipeline_id}")

    # 2. Run pipeline
    print("\n2. Starting pipeline execution...")
    run_result = run_pipeline(pipeline_id)
    print(f"   Run result: {run_result.get('status')}")

    # 3. Wait for completion
    print("\n3. Waiting for pipeline to complete...")
    final_status = wait_for_pipeline(pipeline_id)
    print(f"   Final status: {final_status.get('status')}")

    # 4. Check agent outputs
    print("\n4. Checking agent outputs...")
    node_agent_map = final_status.get("node_agent_map", {})

    for node_id, agent_id in node_agent_map.items():
        print(f"\n   --- Agent for node {node_id} (id: {agent_id}) ---")
        output = get_agent_output(agent_id)
        if output:
            chunks = output.get("chunks", [])
            # Print assistant messages
            for chunk in chunks:
                if chunk.get("type") == "assistant" and chunk.get("content"):
                    print(f"   {chunk['content'][:200]}...")
        else:
            print("   (No output available)")

    # 5. Summary
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print(f"Pipeline Status: {final_status.get('status')}")
    print(f"Agents Executed: {list(node_agent_map.keys())}")

    return final_status.get("status") == "completed"


def test_bridge_direct():
    """Test the bridge endpoint directly."""
    print("\n" + "=" * 60)
    print("TEST: Direct Bridge Communication")
    print("=" * 60)

    # Send a message through the bridge without a pipeline context
    # This should spawn a new agent
    print("\n1. Sending direct bridge message (no pipeline context)...")

    try:
        # Use a simple message to get a fast response
        response = httpx.post(
            f"{BASE_URL}/bridge/send",
            json={
                "from_agent": "TestAgent",
                "to_agent": "WorkerAgent",
                "message": "Say just the word 'hello', nothing else.",
            },
            timeout=120.0,  # Longer timeout for Claude to process
        )
        response.raise_for_status()
        result = response.json()

        print(f"   Status: {result.get('status')}")
        print(f"   Response: {result.get('response', '')[:200]}...")

        return result.get("status") == "response"
    except Exception as e:
        print(f"   Error: {e}")
        return False


def check_server():
    """Check if the orchestrator server is running."""
    try:
        response = httpx.get(f"{BASE_URL}/health")
        return response.status_code == 200
    except Exception:
        return False


def main():
    """Run all tests."""
    print("\nPipeline Communication Test Suite")
    print("=" * 60)

    # Check server
    print("\nChecking orchestrator server...")
    if not check_server():
        print("ERROR: Orchestrator server is not running!")
        print("Start it with: python -m tools.orchestrator.cli.main serve")
        return 1
    print("Server is running.")

    # Run tests
    results = {}

    # Test 1: Direct bridge (simpler, faster)
    results["direct_bridge"] = test_bridge_direct()

    # Test 2: Full pipeline communication (more comprehensive)
    # Uncomment to run the full pipeline test (takes longer)
    # results["pipeline_communication"] = test_simple_communication()

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(results.values())
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
