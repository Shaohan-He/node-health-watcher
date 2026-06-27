from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from node_health_watcher.checks.base import CheckLevel, CheckResult
from node_health_watcher.config import AppConfig, NodeConfig
from node_health_watcher.transport.executor import NodeError

STATUS_SCORE = {
    "healthy": 100,
    "warning": 70,
    "critical": 0,
    "unknown": 0,
}

STATUS_SEVERITY = {
    "healthy": 0,
    "warning": 1,
    "critical": 2,
    "unknown": 2,
}


class HealthState:
    """Thread-safe latest inspection snapshot for API consumers."""

    def __init__(self, config: AppConfig) -> None:
        self._lock = RLock()
        self._inspection_rounds = 0
        self._last_duration_seconds = 0.0
        self._alert_counts: dict[tuple[str, str, str, str], int] = {}
        self._snapshot = self._empty_snapshot(config)

    def record_inspection(
        self,
        config: AppConfig,
        results: list[CheckResult],
        errors: list[NodeError],
        duration_seconds: float,
    ) -> None:
        node_map = {node.hostname: node for node in config.nodes}
        results_by_host: dict[str, list[CheckResult]] = defaultdict(list)
        errors_by_host: dict[str, list[NodeError]] = defaultdict(list)

        for result in results:
            results_by_host[result.hostname].append(result)
            if result.level in {CheckLevel.WARNING, CheckLevel.CRITICAL}:
                key = (result.hostname, result.category, result.sub_check, result.level.value)
                self._alert_counts[key] = self._alert_counts.get(key, 0) + 1

        for error in errors:
            errors_by_host[error.hostname].append(error)

        hostnames = set(node_map) | set(results_by_host) | set(errors_by_host)
        nodes = {
            hostname: self._node_health(
                node=node_map.get(hostname),
                results=results_by_host.get(hostname, []),
                errors=errors_by_host.get(hostname, []),
            )
            for hostname in sorted(hostnames)
        }

        snapshot = {
            "generatedAt": _now_iso(),
            "durationSeconds": round(duration_seconds, 3),
            "nodes": nodes,
            "summary": _summary(nodes, len(errors)),
        }

        with self._lock:
            self._inspection_rounds += 1
            self._last_duration_seconds = duration_seconds
            self._snapshot = snapshot

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._snapshot)

    def render_metrics(self) -> str:
        with self._lock:
            snapshot = deepcopy(self._snapshot)
            rounds = self._inspection_rounds
            duration = self._last_duration_seconds
            alert_counts = dict(self._alert_counts)

        lines = [
            "# HELP nhw_inspection_rounds_total Total completed inspection rounds.",
            "# TYPE nhw_inspection_rounds_total counter",
            f"nhw_inspection_rounds_total {rounds}",
            "# HELP nhw_inspection_duration_seconds Duration of the latest inspection round.",
            "# TYPE nhw_inspection_duration_seconds gauge",
            f"nhw_inspection_duration_seconds {duration:.3f}",
            "# HELP nhw_healthy_node_ratio Ratio of healthy nodes in the latest snapshot.",
            "# TYPE nhw_healthy_node_ratio gauge",
            f"nhw_healthy_node_ratio {snapshot['summary']['healthyNodeRatio']:.3f}",
            "# HELP nhw_node_health_score Node health score from 0 to 100.",
            "# TYPE nhw_node_health_score gauge",
        ]

        for hostname, node_health in snapshot["nodes"].items():
            for group in node_health["groups"] or ["default"]:
                labels = _format_labels({"hostname": hostname, "group": group})
                lines.append(f"nhw_node_health_score{labels} {node_health['score']}")

        lines.extend(
            [
                "# HELP nhw_node_health_status Node health severity: 0 healthy, 1 warning, 2 critical or unknown.",
                "# TYPE nhw_node_health_status gauge",
            ]
        )
        for hostname, node_health in snapshot["nodes"].items():
            for group in node_health["groups"] or ["default"]:
                labels = _format_labels({"hostname": hostname, "group": group, "status": node_health["status"]})
                lines.append(f"nhw_node_health_status{labels} {STATUS_SEVERITY[node_health['status']]}")

        lines.extend(
            [
                "# HELP nhw_alerts_total Total warning and critical check results observed.",
                "# TYPE nhw_alerts_total counter",
            ]
        )
        for (hostname, category, sub_check, level), count in sorted(alert_counts.items()):
            labels = _format_labels(
                {"hostname": hostname, "category": category, "sub_check": sub_check, "level": level}
            )
            lines.append(f"nhw_alerts_total{labels} {count}")

        return "\n".join(lines) + "\n"

    def _empty_snapshot(self, config: AppConfig) -> dict[str, Any]:
        nodes = {
            node.hostname: {
                "status": "unknown",
                "score": STATUS_SCORE["unknown"],
                "reason": "no inspection has completed",
                "groups": list(node.groups),
            }
            for node in sorted(config.nodes, key=lambda item: item.hostname)
        }
        return {
            "generatedAt": _now_iso(),
            "durationSeconds": 0.0,
            "nodes": nodes,
            "summary": _summary(nodes, 0),
        }

    def _node_health(
        self,
        node: NodeConfig | None,
        results: list[CheckResult],
        errors: list[NodeError],
    ) -> dict[str, Any]:
        groups = list(node.groups) if node else []

        if errors:
            reason = "; ".join(f"connection error: {error.error}" for error in errors)
            return _node_payload("critical", reason, groups)

        criticals = [result for result in results if result.level == CheckLevel.CRITICAL]
        if criticals:
            return _node_payload("critical", _result_reason(criticals), groups)

        warnings = [result for result in results if result.level == CheckLevel.WARNING]
        if warnings:
            return _node_payload("warning", _result_reason(warnings), groups)

        if results:
            return _node_payload("healthy", "all checks passed", groups)

        return _node_payload("healthy", "no enabled checks returned anomalies", groups)


def _node_payload(status: str, reason: str, groups: list[str]) -> dict[str, Any]:
    return {
        "status": status,
        "score": STATUS_SCORE[status],
        "reason": reason,
        "groups": groups,
    }


def _result_reason(results: list[CheckResult]) -> str:
    messages = []
    for result in results[:3]:
        message = result.message or result.value or result.sub_check
        messages.append(f"{result.category}/{result.sub_check}: {message}")
    if len(results) > 3:
        messages.append(f"{len(results) - 3} more")
    return "; ".join(messages)


def _summary(nodes: dict[str, dict[str, Any]], error_count: int) -> dict[str, Any]:
    counts = dict.fromkeys(STATUS_SCORE, 0)
    for node_health in nodes.values():
        counts[node_health["status"]] += 1

    node_count = len(nodes)
    healthy_ratio = counts["healthy"] / node_count if node_count else 0.0
    return {
        "nodeCount": node_count,
        "healthy": counts["healthy"],
        "warning": counts["warning"],
        "critical": counts["critical"],
        "unknown": counts["unknown"],
        "healthyNodeRatio": round(healthy_ratio, 3),
        "errorCount": error_count,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _format_labels(labels: dict[str, str]) -> str:
    rendered = ",".join(f'{key}="{_escape_label(value)}"' for key, value in sorted(labels.items()))
    return f"{{{rendered}}}"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
