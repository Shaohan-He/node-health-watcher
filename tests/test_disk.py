from __future__ import annotations

from node_health_watcher.checks.base import CheckLevel


class TestDiskCheck:
    def test_space_ok(self, disk_check):
        outputs = {
            "space:/": "62%",
            "inode:/": "34%",
            "rw:/": "0",
            "space:/var/lib/kubelet": "45%",
            "inode:/var/lib/kubelet": "12%",
            "rw:/var/lib/kubelet": "0",
            "io_latency": "2.5",
        }
        results = disk_check.parse("node-1", outputs)
        space_results = [r for r in results if r.sub_check.startswith("space:")]
        for r in space_results:
            assert r.level == CheckLevel.OK

    def test_space_warning(self, disk_check):
        outputs = {
            "space:/": "85%",
            "inode:/": "34%",
            "rw:/": "0",
            "space:/var/lib/kubelet": "45%",
            "inode:/var/lib/kubelet": "12%",
            "rw:/var/lib/kubelet": "0",
            "io_latency": "N/A",
        }
        results = disk_check.parse("node-1", outputs)
        space_root = [r for r in results if r.sub_check == "space:/"][0]
        assert space_root.level == CheckLevel.WARNING

    def test_space_critical(self, disk_check):
        outputs = {
            "space:/": "95%",
            "inode:/": "34%",
            "rw:/": "0",
            "space:/var/lib/kubelet": "45%",
            "inode:/var/lib/kubelet": "12%",
            "rw:/var/lib/kubelet": "0",
            "io_latency": "N/A",
        }
        results = disk_check.parse("node-1", outputs)
        space_root = [r for r in results if r.sub_check == "space:/"][0]
        assert space_root.level == CheckLevel.CRITICAL

    def test_inode_warning(self, disk_check):
        outputs = {
            "space:/": "62%",
            "inode:/": "89%",
            "rw:/": "0",
            "space:/var/lib/kubelet": "45%",
            "inode:/var/lib/kubelet": "12%",
            "rw:/var/lib/kubelet": "0",
            "io_latency": "N/A",
        }
        results = disk_check.parse("node-1", outputs)
        inode_root = [r for r in results if r.sub_check == "inode:/"][0]
        assert inode_root.level == CheckLevel.WARNING

    def test_readonly_critical(self, disk_check):
        outputs = {
            "space:/": "62%",
            "inode:/": "34%",
            "rw:/": "1",
            "space:/var/lib/kubelet": "45%",
            "inode:/var/lib/kubelet": "12%",
            "rw:/var/lib/kubelet": "0",
            "io_latency": "N/A",
        }
        results = disk_check.parse("node-1", outputs)
        ro = [r for r in results if r.sub_check == "readonly:/"][0]
        assert ro.level == CheckLevel.CRITICAL
        assert "READ-ONLY" in ro.message

    def test_io_latency_warning(self, disk_check):
        outputs = {
            "space:/": "62%",
            "inode:/": "34%",
            "rw:/": "0",
            "space:/var/lib/kubelet": "45%",
            "inode:/var/lib/kubelet": "12%",
            "rw:/var/lib/kubelet": "0",
            "io_latency": "75.3",
        }
        results = disk_check.parse("node-1", outputs)
        io_r = [r for r in results if r.sub_check == "io_latency"][0]
        assert io_r.level == CheckLevel.WARNING

    def test_io_latency_critical(self, disk_check):
        outputs = {
            "space:/": "62%",
            "inode:/": "34%",
            "rw:/": "0",
            "space:/var/lib/kubelet": "45%",
            "inode:/var/lib/kubelet": "12%",
            "rw:/var/lib/kubelet": "0",
            "io_latency": "150.0",
        }
        results = disk_check.parse("node-1", outputs)
        io_r = [r for r in results if r.sub_check == "io_latency"][0]
        assert io_r.level == CheckLevel.CRITICAL

    def test_n_a_values_skipped(self, disk_check):
        outputs = {
            "space:/": "N/A",
            "inode:/": "N/A",
            "rw:/": "N/A",
            "space:/var/lib/kubelet": "N/A",
            "inode:/var/lib/kubelet": "N/A",
            "rw:/var/lib/kubelet": "N/A",
            "io_latency": "N/A",
        }
        results = disk_check.parse("node-1", outputs)
        space_results = [r for r in results if r.sub_check.startswith("space:")]
        assert len(space_results) == 0
