from __future__ import annotations

from node_health_watcher.checks.base import BaseCheck, CheckLevel, CheckResult
from node_health_watcher.config import register_check


@register_check("kernel")
class KernelCheck(BaseCheck):
    name = "kernel"
    description = "Kernel log anomalies, hung tasks, filesystem errors"

    @classmethod
    def default_thresholds(cls) -> dict:
        return {
            "dmesg_critical_patterns": ["BUG:", "Kernel panic", "segfault", "Hardware Error", "WARNING:"],
            "hung_task_timeout": 120,
        }

    def probe_commands(self) -> dict[str, str]:
        patterns = self.thresholds.get("dmesg_critical_patterns", [])
        dmesg_pattern = "|".join(patterns) if patterns else "BUG:|Kernel panic"

        return {
            "dmesg_critical": (f"dmesg -T 2>/dev/null | grep -iE '{dmesg_pattern}' | tail -20 || echo ''"),
            "hung_task": ("dmesg -T 2>/dev/null | grep -i 'hung_task' | tail -10 || echo ''"),
            "fs_errors": ("dmesg -T 2>/dev/null | grep -iE 'EXT4-fs|XFS|I/O error' | tail -10 || echo ''"),
        }

    def parse(self, hostname: str, outputs: dict[str, str]) -> list[CheckResult]:
        results: list[CheckResult] = []

        dmesg_out = outputs.get("dmesg_critical", "").strip()
        if dmesg_out:
            lines = [line for line in dmesg_out.split("\n") if line.strip()]
            results.append(
                CheckResult(
                    hostname=hostname,
                    category="kernel",
                    sub_check="dmesg_critical",
                    level=CheckLevel.CRITICAL,
                    value=str(len(lines)),
                    message=f"dmesg 发现 {len(lines)} 条关键事件",
                )
            )
        else:
            results.append(
                CheckResult(
                    hostname=hostname,
                    category="kernel",
                    sub_check="dmesg_critical",
                    level=CheckLevel.OK,
                    value="0",
                    message="dmesg 无关键异常",
                )
            )

        hung_out = outputs.get("hung_task", "").strip()
        if hung_out:
            lines = [line for line in hung_out.split("\n") if line.strip()]
            results.append(
                CheckResult(
                    hostname=hostname,
                    category="kernel",
                    sub_check="hung_task",
                    level=CheckLevel.CRITICAL,
                    value=str(len(lines)),
                    message=f"发现 {len(lines)} 条 hung_task 事件",
                )
            )
        else:
            results.append(
                CheckResult(
                    hostname=hostname,
                    category="kernel",
                    sub_check="hung_task",
                    level=CheckLevel.OK,
                    value="0",
                    message="无 hung_task 事件",
                )
            )

        fs_out = outputs.get("fs_errors", "").strip()
        if fs_out:
            lines = [line for line in fs_out.split("\n") if line.strip()]
            results.append(
                CheckResult(
                    hostname=hostname,
                    category="kernel",
                    sub_check="fs_errors",
                    level=CheckLevel.CRITICAL,
                    value=str(len(lines)),
                    message=f"发现 {len(lines)} 条文件系统错误",
                )
            )
        else:
            results.append(
                CheckResult(
                    hostname=hostname,
                    category="kernel",
                    sub_check="fs_errors",
                    level=CheckLevel.OK,
                    value="0",
                    message="无文件系统错误",
                )
            )

        return results
