from __future__ import annotations

import shlex

from node_health_watcher.checks.base import BaseCheck, CheckLevel, CheckResult
from node_health_watcher.config import register_check


@register_check("disk")
class DiskCheck(BaseCheck):
    name = "disk"
    description = "Disk space, inode usage, read-only filesystem, I/O latency"

    @classmethod
    def default_thresholds(cls) -> dict:
        return {
            "mount_points": ["/", "/var/lib/kubelet", "/var/lib/containerd"],
            "space": {"warning_pct": 80, "critical_pct": 90},
            "inode": {"warning_pct": 80, "critical_pct": 90},
            "io_latency_ms": {"warning": 50, "critical": 100},
        }

    def probe_commands(self) -> dict[str, str]:
        mount_points = self.thresholds.get("mount_points", ["/", "/var/lib/kubelet", "/var/lib/containerd"])
        commands: dict[str, str] = {}
        for mp in mount_points:
            escaped = shlex.quote(mp)
            commands[f"space:{mp}"] = f"df -P {escaped} 2>/dev/null | awk 'NR==2 {{print $5}}' || echo 'N/A'"
            commands[f"inode:{mp}"] = f"df -Pi {escaped} 2>/dev/null | awk 'NR==2 {{print $5}}' || echo 'N/A'"
            commands[f"rw:{mp}"] = (
                f"test -d {escaped} && (mount | grep -E 'on {escaped} type' | grep -c 'ro,' || echo 0) || echo 'N/A'"
            )
        commands["io_latency"] = (
            "iostat -x 1 2 2>/dev/null | awk 'NR>6 && $0!=\"\" {print $NF}' | head -1 || echo 'N/A'"
        )
        return commands

    def parse(self, hostname: str, outputs: dict[str, str]) -> list[CheckResult]:
        results: list[CheckResult] = []
        mount_points = self.thresholds.get("mount_points", ["/", "/var/lib/kubelet", "/var/lib/containerd"])
        space_warn = self.thresholds.get("space", {}).get("warning_pct", 80)
        space_crit = self.thresholds.get("space", {}).get("critical_pct", 90)
        inode_warn = self.thresholds.get("inode", {}).get("warning_pct", 80)
        inode_crit = self.thresholds.get("inode", {}).get("critical_pct", 90)
        io_warn = self.thresholds.get("io_latency_ms", {}).get("warning", 50)
        io_crit = self.thresholds.get("io_latency_ms", {}).get("critical", 100)

        for mp in mount_points:
            space_key = f"space:{mp}"
            inode_key = f"inode:{mp}"
            rw_key = f"rw:{mp}"

            space_raw = outputs.get(space_key, "N/A").strip().rstrip("%")
            if space_raw not in ("N/A", ""):
                try:
                    pct = float(space_raw)
                    level = CheckLevel.OK
                    if pct >= space_crit:
                        level = CheckLevel.CRITICAL
                    elif pct >= space_warn:
                        level = CheckLevel.WARNING
                    results.append(
                        CheckResult(
                            hostname=hostname,
                            category="disk",
                            sub_check=f"space:{mp}",
                            level=level,
                            value=f"{pct}%",
                            message=f"{mp} = {pct}%",
                            thresholds={"warning": space_warn, "critical": space_crit},
                        )
                    )
                except ValueError:
                    pass

            inode_raw = outputs.get(inode_key, "N/A").strip().rstrip("%")
            if inode_raw not in ("N/A", ""):
                try:
                    pct = float(inode_raw)
                    level = CheckLevel.OK
                    if pct >= inode_crit:
                        level = CheckLevel.CRITICAL
                    elif pct >= inode_warn:
                        level = CheckLevel.WARNING
                    results.append(
                        CheckResult(
                            hostname=hostname,
                            category="disk",
                            sub_check=f"inode:{mp}",
                            level=level,
                            value=f"{pct}%",
                            message=f"inode {mp} = {pct}%",
                            thresholds={"warning": inode_warn, "critical": inode_crit},
                        )
                    )
                except ValueError:
                    pass

            rw_raw = outputs.get(rw_key, "0").strip()
            if rw_raw == "N/A":
                pass  # mount point does not exist — skip
            elif rw_raw not in ("", "0"):
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="disk",
                        sub_check=f"readonly:{mp}",
                        level=CheckLevel.CRITICAL,
                        value="readonly",
                        message=f"{mp} is READ-ONLY",
                    )
                )
            elif rw_raw == "0":
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="disk",
                        sub_check=f"readonly:{mp}",
                        level=CheckLevel.OK,
                        value="rw",
                        message=f"{mp} 读写正常",
                    )
                )

        io_raw = outputs.get("io_latency", "N/A").strip()
        if io_raw not in ("N/A", "", "0.00"):
            try:
                lat = float(io_raw)
                level = CheckLevel.OK
                if lat >= io_crit:
                    level = CheckLevel.CRITICAL
                elif lat >= io_warn:
                    level = CheckLevel.WARNING
                results.append(
                    CheckResult(
                        hostname=hostname,
                        category="disk",
                        sub_check="io_latency",
                        level=level,
                        value=f"{lat}ms",
                        message=f"磁盘 I/O 延迟 = {lat}ms",
                        thresholds={"warning": io_warn, "critical": io_crit},
                    )
                )
            except ValueError:
                pass

        return results
