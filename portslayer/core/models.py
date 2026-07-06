from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PortInfo:
    """Represents a single active port binding."""

    port: int
    pid: int
    process_name: str
    protocol: str          # "TCP" | "UDP"
    state: str             # "LISTEN" | "ESTABLISHED" | "TIME_WAIT" | …
    local_address: str
    remote_address: str = "—"

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #

    @property
    def is_listening(self) -> bool:
        return "LISTEN" in self.state.upper()

    def matches(
        self,
        port: Optional[int] = None,
        port_prefix: Optional[str] = None,
        process: Optional[str] = None,
        protocol: Optional[str] = None,
    ) -> bool:
        """Return True if this entry satisfies all supplied filter criteria."""
        if port is not None and self.port != port:
            return False
        if port_prefix is not None and not str(self.port).startswith(port_prefix):
            return False
        if process is not None and process.lower() not in self.process_name.lower():
            return False
        if protocol is not None and self.protocol.upper() != protocol.upper():
            return False
        return True

    def as_dict(self) -> dict:
        return {
            "port": self.port,
            "pid": self.pid,
            "process_name": self.process_name,
            "protocol": self.protocol,
            "state": self.state,
            "local_address": self.local_address,
            "remote_address": self.remote_address,
        }
