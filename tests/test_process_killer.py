"""
Tests for ProcessKiller.

These tests use mocking to avoid actually killing real processes.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from portslayer.core.models import PortInfo
from portslayer.core.process_killer import KillResult, ProcessKiller


# ────────────────────────────────────────────────────────────────────────────
# KillResult
# ────────────────────────────────────────────────────────────────────────────


class TestKillResult:
    def test_truthy_on_success(self):
        assert bool(KillResult(True, "ok", 123)) is True

    def test_falsy_on_failure(self):
        assert bool(KillResult(False, "err", 123)) is False

    def test_repr_contains_status(self):
        assert "OK" in repr(KillResult(True, "done", 1))
        assert "FAIL" in repr(KillResult(False, "nope", 1))


# ────────────────────────────────────────────────────────────────────────────
# ProcessKiller.kill — invalid PID
# ────────────────────────────────────────────────────────────────────────────


class TestKillInvalidPid:
    def setup_method(self):
        self.killer = ProcessKiller()

    def test_zero_pid_fails(self):
        result = self.killer.kill(0)
        assert result.success is False
        assert "Invalid PID" in result.message

    def test_negative_pid_fails(self):
        result = self.killer.kill(-5)
        assert result.success is False

    def test_nonexistent_pid(self):
        with patch.object(ProcessKiller, "_process_exists", return_value=False):
            result = self.killer.kill(99999)
        assert result.success is False
        assert "No process found" in result.message


# ────────────────────────────────────────────────────────────────────────────
# ProcessKiller.kill — Unix path
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
class TestKillUnix:
    def setup_method(self):
        self.killer = ProcessKiller()

    def test_successful_kill(self):
        with (
            patch.object(ProcessKiller, "_process_exists", return_value=True),
            patch("portslayer.core.process_killer.os.kill") as mock_kill,
        ):
            result = self.killer.kill(1234)
        mock_kill.assert_called_once()
        assert result.success is True

    def test_permission_error(self):
        with (
            patch.object(ProcessKiller, "_process_exists", return_value=True),
            patch(
                "portslayer.core.process_killer.os.kill",
                side_effect=PermissionError,
            ),
        ):
            result = self.killer.kill(1)
        assert result.success is False
        assert "Permission denied" in result.message

    def test_process_vanishes_mid_kill(self):
        with (
            patch.object(ProcessKiller, "_process_exists", return_value=True),
            patch(
                "portslayer.core.process_killer.os.kill",
                side_effect=ProcessLookupError,
            ),
        ):
            result = self.killer.kill(1234)
        assert result.success is False
        assert "no longer exists" in result.message


# ────────────────────────────────────────────────────────────────────────────
# ProcessKiller.kill — Windows path
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
class TestKillWindows:
    def setup_method(self):
        self.killer = ProcessKiller()

    def _mock_taskkill(self, returncode: int, stdout: str = "", stderr: str = ""):
        cp = MagicMock()
        cp.returncode = returncode
        cp.stdout = stdout
        cp.stderr = stderr
        return cp

    def test_successful_kill(self):
        with (
            patch.object(ProcessKiller, "_process_exists", return_value=True),
            patch("portslayer.core.process_killer.subprocess.run") as mock_run,
        ):
            mock_run.return_value = self._mock_taskkill(0, "SUCCESS")
            result = self.killer.kill(1234)
        assert result.success is True

    def test_access_denied(self):
        with (
            patch.object(ProcessKiller, "_process_exists", return_value=True),
            patch("portslayer.core.process_killer.subprocess.run") as mock_run,
        ):
            mock_run.return_value = self._mock_taskkill(1, stderr="Access is denied")
            result = self.killer.kill(1234)
        assert result.success is False
        assert "Permission denied" in result.message


# ────────────────────────────────────────────────────────────────────────────
# kill_by_port — deduplication
# ────────────────────────────────────────────────────────────────────────────


class TestKillByPort:
    def setup_method(self):
        self.killer = ProcessKiller()

    def _make_entry(self, pid: int) -> PortInfo:
        return PortInfo(
            port=8080,
            pid=pid,
            process_name="test",
            protocol="TCP",
            state="LISTEN",
            local_address="0.0.0.0:8080",
        )

    def test_deduplicates_same_pid(self):
        entries = [self._make_entry(1234), self._make_entry(1234)]
        call_count = 0

        def fake_kill(pid):
            nonlocal call_count
            call_count += 1
            return KillResult(True, "ok", pid)

        self.killer.kill = fake_kill
        results = self.killer.kill_by_port(entries)
        assert call_count == 1
        assert len(results) == 1

    def test_skips_zero_pid(self):
        entries = [self._make_entry(0)]
        results = self.killer.kill_by_port(entries)
        assert results == []
