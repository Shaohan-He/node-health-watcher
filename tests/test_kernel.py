from __future__ import annotations

from node_health_watcher.checks.base import CheckLevel


class TestKernelCheck:
    def test_all_clean(self, kernel_check):
        outputs = {
            "dmesg_critical": "",
            "hung_task": "",
            "fs_errors": "",
        }
        results = kernel_check.parse("node-1", outputs)
        for r in results:
            assert r.level == CheckLevel.OK

    def test_dmesg_critical_found(self, kernel_check):
        outputs = {
            "dmesg_critical": "[Sat May 24 10:15:32 2026] BUG: soft lockup - CPU#3 stuck for 22s\n",
            "hung_task": "",
            "fs_errors": "",
        }
        results = kernel_check.parse("node-1", outputs)
        dmesg_r = [r for r in results if r.sub_check == "dmesg_critical"][0]
        assert dmesg_r.level == CheckLevel.CRITICAL
        assert "1" in dmesg_r.value

    def test_hung_task_found(self, kernel_check):
        outputs = {
            "dmesg_critical": "",
            "hung_task": "[Sat May 24 10:15:32 2026] INFO: task kworker/0:1:12345 blocked for more than 120 seconds.\n",
            "fs_errors": "",
        }
        results = kernel_check.parse("node-1", outputs)
        hung = [r for r in results if r.sub_check == "hung_task"][0]
        assert hung.level == CheckLevel.CRITICAL

    def test_fs_errors_found(self, kernel_check):
        outputs = {
            "dmesg_critical": "",
            "hung_task": "",
            "fs_errors": (
                "[Sat May 24 10:15:32 2026] EXT4-fs error (device sdb1): ext4_lookup: deleted inode referenced\n"
            ),
        }
        results = kernel_check.parse("node-1", outputs)
        fs_r = [r for r in results if r.sub_check == "fs_errors"][0]
        assert fs_r.level == CheckLevel.CRITICAL

    def test_multiple_issues(self, kernel_check):
        outputs = {
            "dmesg_critical": "BUG: ...\nKernel panic\n",
            "hung_task": "hung_task ...\n",
            "fs_errors": "EXT4-fs error ...\n",
        }
        results = kernel_check.parse("node-1", outputs)
        assert len(results) == 3
        for r in results:
            assert r.level == CheckLevel.CRITICAL
