from __future__ import annotations

from node_health_watcher.checks.base import BaseCheck, CheckLevel, CheckResult
from node_health_watcher.config import register_check


@register_check("memory")
class MemoryCheck(BaseCheck):
    name = "memory"
    description = "Available memory, swap usage, OOM events"

    @classmethod
    def default_thresholds(cls) -> dict:
        return {
            "available": {"warning_pct": 20, "critical_pct": 10},
            "swap": {"warning_pct": 10, "critical_pct": 30},
            "oom_window_minutes": 15,
        }

    def probe_commands(self) -> dict[str, str]:
        window = self.thresholds.get("oom_window_minutes", 15)
        return {
            "mem_available": "awk '/MemAvailable:/ {print $2}' /proc/meminfo 2>/dev/null || echo 'N/A'",
            "mem_total": "awk '/MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 'N/A'",
            "swap_total": "awk '/SwapTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0",
            "swap_free": "awk '/SwapFree:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0",
            "oom_events": (
                f"journalctl -k --since '{window} min ago' 2>/dev/null | grep -ci oom"
                f" || dmesg 2>/dev/null | grep -ci oom"
                f" || echo 0"
            ),
        }

    def parse(self, hostname: str, outputs: dict[str, str]) -> list[CheckResult]:
        results: list[CheckResult] = []
        avail_warn = self.thresholds.get("available", {}).get("warning_pct", 20)
        avail_crit = self.thresholds.get("available", {}).get("critical_pct", 10)
        swap_warn = self.thresholds.get("swap", {}).get("warning_pct", 10)
        swap_crit = self.thresholds.get("swap", {}).get("critical_pct", 30)

        mem_total_raw = outputs.get("mem_total", "N/A").strip()
        mem_avail_raw = outputs.get("mem_available", "N/A").strip()
        if mem_total_raw not in ("N/A", "") and mem_avail_raw not in ("N/A", ""):
            try:
                total = float(mem_total_raw)
                avail = float(mem_avail_raw)
                pct = (avail / total * 100) if total > 0 else 0
                level = CheckLevel.OK
                if pct <= avail_crit:
                    level = CheckLevel.CRITICAL
                elif pct <= avail_warn:
                    level = CheckLevel.WARNING
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="memory",
                        sub_check="available",
                        level=level,
                        value=f"{pct:.1f}%",
                        message=f"MemAvailable = {pct:.1f}%",
                        thresholds={"warning": avail_warn, "critical": avail_crit},
                    )
                )
            except ValueError:
                pass

        swap_total_raw = outputs.get("swap_total", "0").strip()
        swap_free_raw = outputs.get("swap_free", "0").strip()
        try:
            swap_total = float(swap_total_raw)
            swap_free = float(swap_free_raw)
            if swap_total > 0:
                swap_used_pct = (swap_total - swap_free) / swap_total * 100
                level = CheckLevel.OK
                if swap_used_pct >= swap_crit:
                    level = CheckLevel.CRITICAL
                elif swap_used_pct >= swap_warn:
                    level = CheckLevel.WARNING
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="memory",
                        sub_check="swap",
                        level=level,
                        value=f"{swap_used_pct:.1f}%",
                        message=f"Swap = {swap_used_pct:.1f}%",
                        thresholds={"warning": swap_warn, "critical": swap_crit},
                    )
                )
            else:
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="memory",
                        sub_check="swap",
                        level=CheckLevel.OK,
                        value="0%",
                        message="Swap 已禁用",
                    )
                )
        except ValueError:
            pass

        oom_raw = outputs.get("oom_events", "0").strip()
        try:
            oom_count = int(oom_raw)
            if oom_count > 0:
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="memory",
                        sub_check="oom",
                        level=CheckLevel.CRITICAL,
                        value=str(oom_count),
                        message=f"最近检测到 {oom_count} 次 OOM Kill",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="memory",
                        sub_check="oom",
                        level=CheckLevel.OK,
                        value="0",
                        message="无 OOM 事件",
                    )
                )
        except ValueError:
            pass

        return results
