from __future__ import annotations

from node_health_watcher.checks.base import CheckLevel


class TestConntrackCheck:
    def test_usage_ok(self, conntrack_check):
        outputs = {"count": "50000", "max": "262144", "timewait": "1500"}
        results = conntrack_check.parse("node-1", outputs)
        usage = [r for r in results if r.sub_check == "table_usage"][0]
        assert usage.level == CheckLevel.OK

    def test_usage_warning(self, conntrack_check):
        outputs = {"count": "235000", "max": "262144", "timewait": "1500"}
        results = conntrack_check.parse("node-1", outputs)
        usage = [r for r in results if r.sub_check == "table_usage"][0]
        assert usage.level == CheckLevel.WARNING

    def test_usage_critical(self, conntrack_check):
        outputs = {"count": "260000", "max": "262144", "timewait": "1500"}
        results = conntrack_check.parse("node-1", outputs)
        usage = [r for r in results if r.sub_check == "table_usage"][0]
        assert usage.level == CheckLevel.CRITICAL

    def test_timewait_ok(self, conntrack_check):
        outputs = {"count": "50000", "max": "262144", "timewait": "5000"}
        results = conntrack_check.parse("node-1", outputs)
        tw = [r for r in results if r.sub_check == "timewait"][0]
        assert tw.level == CheckLevel.OK

    def test_timewait_warning(self, conntrack_check):
        outputs = {"count": "50000", "max": "262144", "timewait": "15000"}
        results = conntrack_check.parse("node-1", outputs)
        tw = [r for r in results if r.sub_check == "timewait"][0]
        assert tw.level == CheckLevel.WARNING

    def test_n_a_values_skipped(self, conntrack_check):
        outputs = {"count": "N/A", "max": "N/A", "timewait": "N/A"}
        results = conntrack_check.parse("node-1", outputs)
        usage = [r for r in results if r.sub_check == "table_usage"]
        tw = [r for r in results if r.sub_check == "timewait"]
        assert len(usage) == 0
        assert len(tw) == 0
