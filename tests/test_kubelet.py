from __future__ import annotations

from node_health_watcher.checks.base import CheckLevel


class TestKubeletCheck:
    def test_service_active(self, kubelet_check):
        outputs = {
            "kubelet_active": "active",
            "pleg_latency": "",
            "log_errors": "0",
            "node_ready": "no_kubectl",
        }
        results = kubelet_check.parse("node-1", outputs)
        svc = [r for r in results if r.sub_check == "service"][0]
        assert svc.level == CheckLevel.OK

    def test_service_inactive(self, kubelet_check):
        outputs = {
            "kubelet_active": "inactive",
            "pleg_latency": "",
            "log_errors": "0",
            "node_ready": "no_kubectl",
        }
        results = kubelet_check.parse("node-1", outputs)
        svc = [r for r in results if r.sub_check == "service"][0]
        assert svc.level == CheckLevel.CRITICAL

    def test_pleg_latency_ok(self, kubelet_check):
        outputs = {
            "kubelet_active": "active",
            "pleg_latency": "0.5\n0.3\n",
            "log_errors": "0",
            "node_ready": "no_kubectl",
        }
        results = kubelet_check.parse("node-1", outputs)
        pleg = [r for r in results if r.sub_check == "pleg"]
        assert len(pleg) == 1
        assert pleg[0].level == CheckLevel.OK

    def test_pleg_latency_warning(self, kubelet_check):
        outputs = {
            "kubelet_active": "active",
            "pleg_latency": "3.2\n2.1\n",
            "log_errors": "0",
            "node_ready": "no_kubectl",
        }
        results = kubelet_check.parse("node-1", outputs)
        pleg = [r for r in results if r.sub_check == "pleg"][0]
        assert pleg.level == CheckLevel.WARNING

    def test_pleg_latency_critical(self, kubelet_check):
        outputs = {
            "kubelet_active": "active",
            "pleg_latency": "7.5\n3.2\n",
            "log_errors": "0",
            "node_ready": "no_kubectl",
        }
        results = kubelet_check.parse("node-1", outputs)
        pleg = [r for r in results if r.sub_check == "pleg"][0]
        assert pleg.level == CheckLevel.CRITICAL

    def test_log_errors_detected(self, kubelet_check):
        outputs = {
            "kubelet_active": "active",
            "pleg_latency": "",
            "log_errors": "15",
            "node_ready": "no_kubectl",
        }
        results = kubelet_check.parse("node-1", outputs)
        log_r = [r for r in results if r.sub_check == "log_errors"][0]
        assert log_r.level == CheckLevel.WARNING

    def test_log_errors_clean(self, kubelet_check):
        outputs = {
            "kubelet_active": "active",
            "pleg_latency": "",
            "log_errors": "0",
            "node_ready": "no_kubectl",
        }
        results = kubelet_check.parse("node-1", outputs)
        log_r = [r for r in results if r.sub_check == "log_errors"][0]
        assert log_r.level == CheckLevel.OK

    def test_node_ready(self, kubelet_check):
        outputs = {
            "kubelet_active": "active",
            "pleg_latency": "",
            "log_errors": "0",
            "node_ready": "True",
        }
        results = kubelet_check.parse("node-1", outputs)
        ready = [r for r in results if r.sub_check == "node_ready"][0]
        assert ready.level == CheckLevel.OK

    def test_node_not_ready(self, kubelet_check):
        outputs = {
            "kubelet_active": "active",
            "pleg_latency": "",
            "log_errors": "0",
            "node_ready": "False",
        }
        results = kubelet_check.parse("node-1", outputs)
        ready = [r for r in results if r.sub_check == "node_ready"][0]
        assert ready.level == CheckLevel.CRITICAL

    def test_no_kubectl_skipped(self, kubelet_check):
        outputs = {
            "kubelet_active": "active",
            "pleg_latency": "",
            "log_errors": "0",
            "node_ready": "no_kubectl",
        }
        results = kubelet_check.parse("node-1", outputs)
        ready = [r for r in results if r.sub_check == "node_ready"]
        assert len(ready) == 0
