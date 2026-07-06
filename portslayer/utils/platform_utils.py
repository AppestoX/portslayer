import os
import sys
import platform
from enum import Enum


class Platform(str, Enum):
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"


def get_platform() -> Platform:
    system = platform.system().lower()
    if system == "linux":
        return Platform.LINUX
    if system == "windows":
        return Platform.WINDOWS
    if system == "darwin":
        return Platform.MACOS
    raise RuntimeError(
        f"Unsupported platform: '{platform.system()}'. "
        "PortSlayer supports Linux, Windows, and macOS."
    )


def is_admin() -> bool:
    """Return True when the process is running with elevated privileges."""
    try:
        if sys.platform == "win32":
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False
