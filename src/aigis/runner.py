"""Runner for executing commands locally or via SSH."""

import platform
import shlex
import subprocess
from dataclasses import dataclass
from typing import Protocol

_IS_WINDOWS = platform.system() == "Windows"


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
                shell=_IS_WINDOWS,
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
    """Run commands via SSH on a remote host (key-based auth via subprocess)."""

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


class SSHPasswordRunner:
    """Run commands via SSH with password auth using paramiko (cross-platform)."""

    is_local = False

    def __init__(self, hostname: str, username: str, password: str, port: int = 22) -> None:
        self._hostname = hostname
        self._username = username
        self._password = password
        self._port = port

    def run(self, cmd: list[str], timeout: int = 30) -> RunResult:
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=self._hostname,
                port=self._port,
                username=self._username,
                password=self._password,
                timeout=10,
                look_for_keys=False,
                allow_agent=False,
            )
            command_str = shlex.join(cmd)
            _, stdout_ch, stderr_ch = client.exec_command(command_str, timeout=timeout)
            rc = stdout_ch.channel.recv_exit_status()
            return RunResult(
                stdout=stdout_ch.read().decode(errors="replace"),
                stderr=stderr_ch.read().decode(errors="replace"),
                returncode=rc,
            )
        except paramiko.AuthenticationException:
            return RunResult(stdout="", stderr="SSH authentication failed", returncode=-1)
        except paramiko.SSHException as e:
            return RunResult(stdout="", stderr=f"SSH error: {e}", returncode=-1)
        except TimeoutError:
            return RunResult(stdout="", stderr="SSH timed out", returncode=-1)
        except OSError as e:
            return RunResult(stdout="", stderr=f"SSH connection failed: {e}", returncode=-1)
        finally:
            client.close()


def _parse_host_string(host: str) -> tuple[str, str, int]:
    """Parse 'user@hostname[:port]' into (username, hostname, port)."""
    user, _, rest = host.partition("@")
    if ":" in rest:
        hostname, _, port_str = rest.partition(":")
        port = int(port_str)
    else:
        hostname = rest
        port = 22
    return user, hostname, port


def get_runner(config) -> Runner:
    """Resolve runner from config target."""
    target_key = config.target
    targets = config.targets
    t = targets.get(target_key) if targets else None

    if not t or not t.host or t.host.strip() == "":
        return LocalRunner()

    if t.auth == "password" and t.password:
        user, hostname, port = _parse_host_string(t.host)
        return SSHPasswordRunner(
            hostname=hostname,
            username=user,
            password=t.password,
            port=port,
        )

    return SSHRunner(host=t.host, ssh_key_path=t.ssh_key_path)
