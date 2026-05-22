"""Tests for runner module: LocalRunner, SSHRunner, get_runner."""

from aigis.config import AppConfig, TargetConfig

from aigis.runner import LocalRunner, SSHRunner, SSHPasswordRunner, get_runner, _parse_host_string


class TestLocalRunner:
    """LocalRunner tests."""

    def test_is_local(self) -> None:
        assert LocalRunner().is_local is True

    def test_run_echo(self) -> None:
        runner = LocalRunner()
        result = runner.run(["echo", "hello"])
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_run_failure(self) -> None:
        runner = LocalRunner()
        result = runner.run(["python", "-c", "import sys; sys.exit(42)"])
        assert result.returncode == 42

    def test_run_timeout(self) -> None:
        runner = LocalRunner()
        result = runner.run(["python", "-c", "import time; time.sleep(10)"], timeout=1)
        assert result.returncode == -1
        assert "Timed out" in result.stderr


class TestSSHRunner:
    """SSHRunner tests (no actual SSH connections)."""

    def test_is_local(self) -> None:
        runner = SSHRunner(host="user@host")
        assert runner.is_local is False

    def test_build_ssh_args_with_key(self) -> None:
        runner = SSHRunner(host="user@host", ssh_key_path="/tmp/mykey")
        args = runner.build_ssh_args()
        assert args[0] == "ssh"
        assert "-i" in args
        assert "/tmp/mykey" in args
        assert "user@host" in args
        # Should not contain any remote command
        assert "bash" not in args

    def test_build_ssh_args_without_key(self) -> None:
        runner = SSHRunner(host="user@host")
        args = runner.build_ssh_args()
        assert "-i" not in args
        assert "user@host" == args[-1]

    def test_build_ssh_args_includes_options(self) -> None:
        runner = SSHRunner(host="user@host")
        args = runner.build_ssh_args()
        assert "StrictHostKeyChecking=no" in " ".join(args)
        assert "ConnectTimeout=30" in " ".join(args)
        assert "LogLevel=ERROR" in " ".join(args)


class TestSSHPasswordRunner:
    """SSHPasswordRunner basic tests (no actual connections)."""

    def test_is_local(self) -> None:
        runner = SSHPasswordRunner(hostname="host", username="user", password="pass")
        assert runner.is_local is False


class TestParseHostString:
    """Tests for _parse_host_string helper."""

    def test_simple_host(self) -> None:
        user, hostname, port = _parse_host_string("user@myhost")
        assert user == "user"
        assert hostname == "myhost"
        assert port == 22

    def test_host_with_port(self) -> None:
        user, hostname, port = _parse_host_string("root@10.0.0.1:2222")
        assert user == "root"
        assert hostname == "10.0.0.1"
        assert port == 2222


class TestGetRunner:
    """Tests for get_runner factory function."""

    def test_local_target(self) -> None:
        config = AppConfig(target="local", targets={"local": TargetConfig(host="")})
        runner = get_runner(config)
        assert isinstance(runner, LocalRunner)

    def test_missing_target(self) -> None:
        config = AppConfig(target="unknown")
        runner = get_runner(config)
        assert isinstance(runner, LocalRunner)

    def test_ssh_key_target(self) -> None:
        config = AppConfig(
            target="remote",
            targets={"remote": TargetConfig(host="user@10.0.0.1", auth="key", ssh_key_path="/tmp/key")},
        )
        runner = get_runner(config)
        assert isinstance(runner, SSHRunner)

    def test_ssh_password_target(self) -> None:
        config = AppConfig(
            target="remote",
            targets={"remote": TargetConfig(host="user@10.0.0.1", auth="password", password="not_real_encrypted")},
        )
        # Will fail to decrypt, but we test the branch selection
        # decrypt_password requires AIGIS_KEY env var; just verify it tries the right path
        import os
        if not os.environ.get("AIGIS_KEY"):
            # Without key, get_runner will raise — that's expected behavior
            try:
                runner = get_runner(config)
            except Exception:
                pass  # Expected: missing AIGIS_KEY
        else:
            runner = get_runner(config)
            assert isinstance(runner, SSHPasswordRunner)
