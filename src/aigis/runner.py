"""Runner for executing commands locally or via SSH."""

import subprocess
from dataclasses import dataclass
from typing import Protocol


@dataclass
class RunResult:
    """Result of a command run."""

    stdout: str
    stderr: str
    returncode: int


class Runner(Protocol):
    """Protocol for command execution (local or remote)."""

    @property
    def is_local(self) -> bool:
        """True if running on this machine."""
        ...

    def run(self, cmd: list[str], timeout: int = 30) -> RunResult:
        """Execute command. Returns (stdout, stderr, returncode)."""
        ...


class LocalRunner:
    """Run commands locally."""

    is_local = True

    def run(self, cmd: list[str], timeout: int = 30) -> RunResult:
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return RunResult(
                stdout=r.stdout or "",
                stderr=r.stderr or "",
                returncode=r.returncode,
            )
        except subprocess.TimeoutExpired:
            return RunResult(stdout="", stderr="Timed out", returncode=-1)
        except Exception as e:
            return RunResult(stdout="", stderr=str(e), returncode=-1)


class SSHRunner:
    """Run commands via SSH on a remote host."""

    is_local = False

    def __init__(self, host: str, ssh_key_path: str | None = None) -> None:
        self._host = host
        self._ssh_key = ssh_key_path

    def run(self, cmd: list[str], timeout: int = 30) -> RunResult:
        args = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"]
        if self._ssh_key:
            args.extend(["-i", self._ssh_key])
        args.append(self._host)
        args.extend(cmd)
        try:
            r = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return RunResult(
                stdout=r.stdout or "",
                stderr=r.stderr or "",
                returncode=r.returncode,
            )
        except subprocess.TimeoutExpired:
            return RunResult(stdout="", stderr="SSH timed out", returncode=-1)
        except FileNotFoundError:
            return RunResult(stdout="", stderr="ssh not found", returncode=-1)
        except Exception as e:
            return RunResult(stdout="", stderr=str(e), returncode=-1)


def get_runner(config) -> Runner:
    """Resolve runner from config target."""
    target_key = config.target
    targets = config.targets
    t = targets.get(target_key) if targets else None

    if not t or not t.host or t.host.strip() == "":
        return LocalRunner()

    return SSHRunner(host=t.host, ssh_key_path=t.ssh_key_path)
