from __future__ import annotations

from node_health_watcher.checks.base import BaseCheck, CheckLevel, CheckResult
from node_health_watcher.config import register_check


@register_check("kubelet")
class KubeletCheck(BaseCheck):
    name = "kubelet"
    description = "Kubelet service status, node readiness, PLEG latency, critical logs"

    @classmethod
    def default_thresholds(cls) -> dict:
        return {
            "pleg_latency_seconds": {"warning": 2.0, "critical": 5.0},
            "log_scan_window_minutes": 15,
            "log_error_patterns": ["error", "timeout", "deadline", "backoff", "eviction"],
        }

    def probe_commands(self) -> dict[str, str]:
        window = self.thresholds.get("log_scan_window_minutes", 15)
        patterns = self.thresholds.get("log_error_patterns", ["error", "timeout", "deadline", "backoff", "eviction"])
        grep_pattern = "|".join(patterns)

        if self._node and self._node.k8s_node_name:
            node_name = self._node.k8s_node_name
        elif self._node:
            node_name = self._node.hostname
        else:
            node_name = "$(hostname | tr '[:upper:]' '[:lower:]')"

        # journalctl with fallback to /var/log/kubelet.log for non-persistent journald
        # (common on Chinese cloud server default images)
        pleg_cmd = (
            f"(journalctl -u kubelet --since '{window} min ago' 2>/dev/null"
            f" || tail -n 5000 /var/log/kubelet.log 2>/dev/null)"
            " | grep -oP 'PLEG.*latency[= ]*\\K[0-9.]+(?=s)' | tail -5"
            " || echo ''"
        )
        log_errors_cmd = (
            f"(journalctl -u kubelet --since '{window} min ago' 2>/dev/null"
            f" || tail -n 5000 /var/log/kubelet.log 2>/dev/null)"
            f" | grep -ciE '{grep_pattern}'"
            f" || echo 0"
        )

        return {
            "kubelet_active": "systemctl is-active kubelet 2>/dev/null || echo 'unknown'",
            "pleg_latency": pleg_cmd,
            "log_errors": log_errors_cmd,
            "node_ready": (
                f"kubectl get node {node_name}"
                " -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}' 2>/dev/null"
                " || echo 'no_kubectl'"
            ),
        }

    def parse(self, hostname: str, outputs: dict[str, str]) -> list[CheckResult]:
        results: list[CheckResult] = []
        pleg_warn = self.thresholds.get("pleg_latency_seconds", {}).get("warning", 2.0)
        pleg_crit = self.thresholds.get("pleg_latency_seconds", {}).get("critical", 5.0)

        active = outputs.get("kubelet_active", "unknown").strip().lower()
        if active == "active":
            results.append(
                CheckResult(
                    hostname=hostname,
                    category="kubelet",
                    sub_check="service",
                    level=CheckLevel.OK,
                    value="active",
                    message="服务 active",
                )
            )
        elif active == "inactive":
            results.append(
                CheckResult(
                    hostname=hostname,
                    category="kubelet",
                    sub_check="service",
                    level=CheckLevel.CRITICAL,
                    value="inactive",
                    message="服务 inactive",
                )
            )
        else:
            results.append(
                CheckResult(
                    hostname=hostname,
                    category="kubelet",
                    sub_check="service",
                    level=CheckLevel.WARNING,
                    value=active,
                    message=f"服务状态: {active}",
                )
            )

        pleg_raw = outputs.get("pleg_latency", "").strip()
        if pleg_raw:
            max_lat = 0.0
            for line in pleg_raw.split("\n"):
                try:
                    lat = float(line.strip())
                    if lat > max_lat:
                        max_lat = lat
                except ValueError:
                    pass
            if max_lat > 0:
                if max_lat >= pleg_crit:
                    level = CheckLevel.CRITICAL
                elif max_lat >= pleg_warn:
                    level = CheckLevel.WARNING
                else:
                    level = CheckLevel.OK
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="kubelet",
                        sub_check="pleg",
                        level=level,
                        value=f"{max_lat:.1f}s",
                        message=f"PLEG 延迟 {max_lat:.1f}s",
                        thresholds={"warning": pleg_warn, "critical": pleg_crit},
                    )
                )

        log_raw = outputs.get("log_errors", "0").strip()
        try:
            log_count = int(log_raw)
            if log_count > 0:
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="kubelet",
                        sub_check="log_errors",
                        level=CheckLevel.WARNING,
                        value=str(log_count),
                        message=(
                            f"最近 {self.thresholds.get('log_scan_window_minutes', 15)} 分钟 {log_count} 条关键错误"
                        ),
                    )
                )
            else:
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="kubelet",
                        sub_check="log_errors",
                        level=CheckLevel.OK,
                        value="0",
                        message="无关键错误日志",
                    )
                )
        except ValueError:
            pass

        node_ready = outputs.get("node_ready", "no_kubectl").strip()
        if node_ready != "no_kubectl":
            if node_ready.lower() == "true":
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="kubelet",
                        sub_check="node_ready",
                        level=CheckLevel.OK,
                        value="Ready",
                        message="Node Ready=True",
                    )
                )
            elif node_ready.lower() == "false":
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="kubelet",
                        sub_check="node_ready",
                        level=CheckLevel.CRITICAL,
                        value="NotReady",
                        message="Node NotReady",
                    )
                )

        return results
