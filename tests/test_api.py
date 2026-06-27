from __future__ import annotations

import json
from urllib.request import urlopen

from node_health_watcher.api import start_api_server
from node_health_watcher.checks.base import CheckLevel, CheckResult
from node_health_watcher.config import AppConfig, NodeConfig
from node_health_watcher.state import HealthState
from node_health_watcher.transport.executor import NodeError


def test_node_health_endpoint_returns_initial_snapshot() -> None:
    state = HealthState(AppConfig(nodes=[NodeConfig(hostname="node-a", groups=["worker"])]))
    server = start_api_server(state, "127.0.0.1", 0)

    try:
        port = server.server_address[1]
        with urlopen(f"http://127.0.0.1:{port}/api/v1/node-health", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://127.0.0.1:{port}/metrics", timeout=2) as response:
            metrics = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()

    assert payload["nodes"]["node-a"] == {
        "groups": ["worker"],
        "reason": "no inspection has completed",
        "score": 0,
        "status": "unknown",
    }
    assert payload["summary"]["nodeCount"] == 1
    assert payload["summary"]["unknown"] == 1
    assert "nhw_node_health_score" in metrics


def test_state_records_inspection_snapshot_and_metrics() -> None:
    config = AppConfig(
        nodes=[
            NodeConfig(hostname="node-a", groups=["worker"]),
            NodeConfig(hostname="node-b", groups=["worker"]),
        ]
    )
    state = HealthState(config)

    state.record_inspection(
        config=config,
        results=[
            CheckResult(
                hostname="node-a",
                category="disk",
                sub_check="space",
                level=CheckLevel.WARNING,
                message="/var/lib/kubelet usage is high",
            )
        ],
        errors=[NodeError(hostname="node-b", error="ssh timeout")],
        duration_seconds=1.2345,
    )

    snapshot = state.snapshot()
    assert snapshot["nodes"]["node-a"]["status"] == "warning"
    assert snapshot["nodes"]["node-a"]["score"] == 70
    assert snapshot["nodes"]["node-b"]["status"] == "critical"
    assert snapshot["nodes"]["node-b"]["reason"] == "connection error: ssh timeout"
    assert snapshot["summary"]["warning"] == 1
    assert snapshot["summary"]["critical"] == 1
    assert snapshot["summary"]["healthyNodeRatio"] == 0.0

    metrics = state.render_metrics()
    assert "nhw_inspection_rounds_total 1" in metrics
    assert 'nhw_node_health_score{group="worker",hostname="node-a"} 70' in metrics
    assert 'nhw_node_health_status{group="worker",hostname="node-a",status="warning"} 1' in metrics
    assert 'nhw_alerts_total{category="disk",hostname="node-a",level="warning",sub_check="space"} 1' in metrics
