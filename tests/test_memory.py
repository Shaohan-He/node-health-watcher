from __future__ import annotations

from node_health_watcher.checks.base import CheckLevel


class TestMemoryCheck:
    def test_available_ok(self, memory_check):
        outputs = {
            "mem_available": "8000000",
            "mem_total": "16000000",
            "swap_total": "0",
            "swap_free": "0",
            "oom_events": "0",
        }
        results = memory_check.parse("node-1", outputs)
        avail = [r for r in results if r.sub_check == "available"][0]
        assert avail.level == CheckLevel.OK

    def test_available_warning(self, memory_check):
        outputs = {
            "mem_available": "2000000",
            "mem_total": "16000000",
            "swap_total": "0",
            "swap_free": "0",
            "oom_events": "0",
        }
        results = memory_check.parse("node-1", outputs)
        avail = [r for r in results if r.sub_check == "available"][0]
        assert avail.level == CheckLevel.WARNING
        assert "12." in avail.value or "12," in avail.value  # ~12.5%

    def test_available_critical(self, memory_check):
        outputs = {
            "mem_available": "800000",
            "mem_total": "16000000",
            "swap_total": "0",
            "swap_free": "0",
            "oom_events": "0",
        }
        results = memory_check.parse("node-1", outputs)
        avail = [r for r in results if r.sub_check == "available"][0]
        assert avail.level == CheckLevel.CRITICAL

    def test_swap_disabled(self, memory_check):
        outputs = {
            "mem_available": "8000000",
            "mem_total": "16000000",
            "swap_total": "0",
            "swap_free": "0",
            "oom_events": "0",
        }
        results = memory_check.parse("node-1", outputs)
        swap = [r for r in results if r.sub_check == "swap"][0]
        assert swap.level == CheckLevel.OK
        assert "禁用" in swap.message or "disabled" in swap.message.lower()

    def test_swap_warning(self, memory_check):
        outputs = {
            "mem_available": "8000000",
            "mem_total": "16000000",
            "swap_total": "1000000",
            "swap_free": "800000",
            "oom_events": "0",
        }
        results = memory_check.parse("node-1", outputs)
        swap = [r for r in results if r.sub_check == "swap"][0]
        assert swap.level == CheckLevel.WARNING

    def test_swap_critical(self, memory_check):
        outputs = {
            "mem_available": "8000000",
            "mem_total": "16000000",
            "swap_total": "1000000",
            "swap_free": "500000",
            "oom_events": "0",
        }
        results = memory_check.parse("node-1", outputs)
        swap = [r for r in results if r.sub_check == "swap"][0]
        assert swap.level == CheckLevel.CRITICAL

    def test_oom_detected(self, memory_check):
        outputs = {
            "mem_available": "8000000",
            "mem_total": "16000000",
            "swap_total": "0",
            "swap_free": "0",
            "oom_events": "3",
        }
        results = memory_check.parse("node-1", outputs)
        oom = [r for r in results if r.sub_check == "oom"][0]
        assert oom.level == CheckLevel.CRITICAL
        assert "3" in oom.value

    def test_no_oom(self, memory_check):
        outputs = {
            "mem_available": "8000000",
            "mem_total": "16000000",
            "swap_total": "0",
            "swap_free": "0",
            "oom_events": "0",
        }
        results = memory_check.parse("node-1", outputs)
        oom = [r for r in results if r.sub_check == "oom"][0]
        assert oom.level == CheckLevel.OK
