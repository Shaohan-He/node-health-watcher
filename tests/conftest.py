from __future__ import annotations

import pytest

from node_health_watcher.checks.conntrack import ConntrackCheck
from node_health_watcher.checks.disk import DiskCheck
from node_health_watcher.checks.kernel import KernelCheck
from node_health_watcher.checks.kubelet import KubeletCheck
from node_health_watcher.checks.memory import MemoryCheck


@pytest.fixture
def disk_thresholds() -> dict:
    return {
        "mount_points": ["/", "/var/lib/kubelet"],
        "space": {"warning_pct": 80, "critical_pct": 90},
        "inode": {"warning_pct": 80, "critical_pct": 90},
        "io_latency_ms": {"warning": 50, "critical": 100},
    }


@pytest.fixture
def memory_thresholds() -> dict:
    return {
        "available": {"warning_pct": 20, "critical_pct": 10},
        "swap": {"warning_pct": 10, "critical_pct": 30},
        "oom_window_minutes": 15,
    }


@pytest.fixture
def conntrack_thresholds() -> dict:
    return {
        "table_usage": {"warning_pct": 85, "critical_pct": 95},
        "time_wait_max": 10000,
    }


@pytest.fixture
def kubelet_thresholds() -> dict:
    return {
        "pleg_latency_seconds": {"warning": 2.0, "critical": 5.0},
        "log_scan_window_minutes": 15,
        "log_error_patterns": ["error", "timeout", "deadline", "backoff", "eviction"],
    }


@pytest.fixture
def kernel_thresholds() -> dict:
    return {
        "dmesg_critical_patterns": ["BUG:", "Kernel panic", "segfault", "Hardware Error", "WARNING:"],
        "hung_task_timeout": 120,
    }


@pytest.fixture
def disk_check(disk_thresholds) -> DiskCheck:
    return DiskCheck(thresholds=disk_thresholds)


@pytest.fixture
def memory_check(memory_thresholds) -> MemoryCheck:
    return MemoryCheck(thresholds=memory_thresholds)


@pytest.fixture
def conntrack_check(conntrack_thresholds) -> ConntrackCheck:
    return ConntrackCheck(thresholds=conntrack_thresholds)


@pytest.fixture
def kubelet_check(kubelet_thresholds) -> KubeletCheck:
    return KubeletCheck(thresholds=kubelet_thresholds)


@pytest.fixture
def kernel_check(kernel_thresholds) -> KernelCheck:
    return KernelCheck(thresholds=kernel_thresholds)
