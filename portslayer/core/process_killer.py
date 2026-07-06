"""
Safe process termination.

All kill operations:
  1. Validate the PID is still alive before acting.
  2. Use OS-native APIs where possible (no raw shell).
  3. Fall back to subprocess with explicit argument lists (never shell=True).
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from typing import Optional

from .models import PortInfo
from ..utils.platform_utils import Platform, get_platform, is_admin


class KillResult:
    """Structured result returned by :meth:`ProcessKiller.kill`."""

    def __init__(self, success: bool, message: str, pid: int = 0) -> None:
        self.success = success
        self.message = message
        self.pid = pid

    def __bool__(self) -> bool:
        return self.success

    def __repr__(self) -> str:
        status = "OK" if self.success else "FAIL"
        return f"KillResult({status}: {self.message})"


class ProcessKiller:
    """Kill a process identified by its PID."""

    def __init__(self) -> None:
        self._platform = get_platform()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def kill(self, pid: int) -> KillResult:
        """
        Attempt to terminate the process *pid*.

        Caller is responsible for:
          - showing process details to the user beforehand.
          - obtaining explicit confirmation before calling this method.
        """
        if pid <= 0:
            return KillResult(False, f"Invalid PID: {pid}", pid)

        if not self._process_exists(pid):
            return KillResult(False, f"No process found with PID {pid}.", pid)

        if self._platform in (Platform.LINUX, Platform.MACOS):
            return self._kill_unix(pid)
        if self._platform == Platform.WINDOWS:
            return self._kill_windows(pid)

        return KillResult(False, f"Unsupported platform: {self._platform}", pid)

    def kill_by_port(self, entries: list[PortInfo]) -> list[KillResult]:
        """Kill every process in *entries* (one PID may appear multiple times)."""
        seen: set[int] = set()
        results: list[KillResult] = []
        for entry in entries:
            if entry.pid in seen or entry.pid <= 0:
                continue
            seen.add(entry.pid)
            results.append(self.kill(entry.pid))
        return results

    # ------------------------------------------------------------------
    # Platform-specific kill
    # ------------------------------------------------------------------

    def _kill_unix(self, pid: int) -> KillResult:
        try:
            os.kill(pid, signal.SIGKILL)
            return KillResult(True, f"Process {pid} terminated (SIGKILL).", pid)
        except PermissionError:
            hint = " Try running with sudo." if not is_admin() else ""
            return KillResult(False, f"Permission denied killing PID {pid}.{hint}", pid)
        except ProcessLookupError:
            return KillResult(False, f"Process {pid} no longer exists.", pid)
        except Exception as exc:
            return KillResult(False, f"Unexpected error killing PID {pid}: {exc}", pid)

    def _kill_windows(self, pid: int) -> KillResult:
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return KillResult(True, f"Process {pid} terminated.", pid)

            stderr = result.stderr.strip() or result.stdout.strip()
            if "Access is denied" in stderr or "Access is denied" in result.stdout:
                hint = (
                    " Try running as Administrator."
                    if not is_admin()
                    else ""
                )
                return KillResult(
                    False, f"Permission denied killing PID {pid}.{hint}", pid
                )
            return KillResult(False, f"taskkill failed: {stderr}", pid)
        except FileNotFoundError:
            return KillResult(False, "taskkill not found. Is this Windows?", pid)
        except subprocess.TimeoutExpired:
            return KillResult(False, f"taskkill timed out for PID {pid}.", pid)
        except Exception as exc:
            return KillResult(False, f"Unexpected error: {exc}", pid)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _process_exists(pid: int) -> bool:
        if sys.platform == "win32":
            # Use tasklist to check existence without needing POSIX signals
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return str(pid) in result.stdout
            except Exception:
                return True  # assume alive on error; kill will handle it
        else:
            try:
                os.kill(pid, 0)
                return True
            except ProcessLookupError:
                return False
            except PermissionError:
                return True  # exists but we can't signal it (root-owned)
