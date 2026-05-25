from __future__ import annotations

from node_health_watcher.checks.base import BaseCheck, CheckLevel, CheckResult
from node_health_watcher.config import register_check


@register_check("conntrack")
class ConntrackCheck(BaseCheck):
    name = "conntrack"
    description = "Conntrack table utilization, connection statistics"

    @classmethod
    def default_thresholds(cls) -> dict:
        return {
            "table_usage": {"warning_pct": 85, "critical_pct": 95},
            "time_wait_max": 10000,
        }

    def probe_commands(self) -> dict[str, str]:
        return {
            "count": (
                "cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null"
                " || cat /proc/sys/net/nf_conntrack_count 2>/dev/null"
                " || echo 'N/A'"
            ),
            "max": (
                "cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null"
                " || cat /proc/sys/net/nf_conntrack_max 2>/dev/null"
                " || echo 'N/A'"
            ),
            "timewait": "ss -s 2>/dev/null | grep timewait | awk '{print $2}' | tr -d ',' || echo 'N/A'",
        }

    def parse(self, hostname: str, outputs: dict[str, str]) -> list[CheckResult]:
        results: list[CheckResult] = []
        usage_warn = self.thresholds.get("table_usage", {}).get("warning_pct", 85)
        usage_crit = self.thresholds.get("table_usage", {}).get("critical_pct", 95)
        tw_max = self.thresholds.get("time_wait_max", 10000)

        count_raw = outputs.get("count", "N/A").strip()
        max_raw = outputs.get("max", "N/A").strip()

        if count_raw not in ("N/A", "") and max_raw not in ("N/A", ""):
            try:
                count = float(count_raw)
                max_val = float(max_raw)
                pct = (count / max_val * 100) if max_val > 0 else 0
                level = CheckLevel.OK
                if pct >= usage_crit:
                    level = CheckLevel.CRITICAL
                elif pct >= usage_warn:
                    level = CheckLevel.WARNING
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="conntrack",
                        sub_check="table_usage",
                        level=level,
                        value=f"{pct:.1f}%",
                        message=f"表使用率 = {pct:.1f}% ({count:.0f}/{max_val:.0f})",
                        thresholds={"warning": usage_warn, "critical": usage_crit},
                    )
                )
            except ValueError:
                pass

        tw_raw = outputs.get("timewait", "N/A").strip()
        if tw_raw not in ("N/A", ""):
            try:
                tw = int(tw_raw)
                level = CheckLevel.OK
                if tw >= tw_max:
                    level = CheckLevel.WARNING
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="conntrack",
                        sub_check="timewait",
                        level=level,
                        value=str(tw),
                        message=f"TIME_WAIT = {tw}",
                        thresholds={"max": tw_max},
                    )
                )
            except ValueError:
                pass

        return results
