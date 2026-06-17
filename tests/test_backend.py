"""Backend tests that never touch the real system.

We stub command execution and privilege checks so the procedure logic, the
escalation wrapping, and the failure handling can be verified in isolation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from parduspm import registry  # noqa: E402
from parduspm import backend as backend_module  # noqa: E402
from parduspm.backend import Backend, OperationResult, Status  # noqa: E402
from parduspm.logger import ActivityLog  # noqa: E402
from parduspm.registry import Privilege, Step  # noqa: E402


@pytest.fixture
def backend(tmp_path):
    return Backend(ActivityLog(path=tmp_path / "activity.log"))


def test_detect_present(backend, monkeypatch):
    monkeypatch.setattr("parduspm.backend.shutil.which", lambda c: "/usr/bin/" + c)
    assert backend.detect(registry.FLATPAK) is Status.INSTALLED


def test_detect_absent(backend, monkeypatch):
    monkeypatch.setattr("parduspm.backend.shutil.which", lambda c: None)
    monkeypatch.setattr("os.path.exists", lambda p: False)
    assert backend.detect(registry.SNAP) is Status.NOT_INSTALLED


def test_detect_by_path(backend, monkeypatch):
    monkeypatch.setattr("parduspm.backend.shutil.which", lambda c: None)
    monkeypatch.setattr("os.path.exists", lambda p: p == "/usr/bin/epkg")
    assert backend.detect(registry.EPKG) is Status.INSTALLED


def test_install_runs_one_script_with_all_steps(backend, monkeypatch):
    scripts = []
    monkeypatch.setattr(backend, "is_root", lambda: True)
    monkeypatch.setattr(backend, "_run_script",
                        lambda script, prefix, cb: scripts.append((script, prefix)) or 0)
    result = backend.install(registry.EPKG)
    assert result.ok
    # Exactly one invocation, no escalation prefix because we are root.
    assert len(scripts) == 1
    script, prefix = scripts[0]
    assert prefix == []
    # Every step's command appears in the single script.
    for step in registry.EPKG.install_steps:
        assert step.argv[0] in script


def test_single_pkexec_for_multi_step_op(backend, monkeypatch):
    captured = {}
    monkeypatch.setattr(backend, "is_root", lambda: False)
    monkeypatch.setattr("parduspm.backend.shutil.which",
                        lambda c: "/usr/bin/pkexec" if c == "pkexec" else None)
    monkeypatch.setattr(backend, "_run_script",
                        lambda script, prefix, cb: captured.update(prefix=prefix) or 0)
    # Snap removal has three root steps; all must run under a single pkexec.
    backend.remove(registry.SNAP)
    assert captured["prefix"] == ["pkexec"]


def test_failure_names_the_step(backend, monkeypatch):
    monkeypatch.setattr(backend, "is_root", lambda: True)

    def fake_run(script, prefix, cb):
        # Simulate the script reaching the first step's marker, then failing.
        cb(backend_module.STEP_MARKER + registry.FLATPAK.remove_steps[0].description)
        return 1

    monkeypatch.setattr(backend, "_run_script", fake_run)
    result = backend.remove(registry.FLATPAK)
    assert not result.ok
    assert "exit 1" in result.message
    assert result.failed_step == registry.FLATPAK.remove_steps[0].description


def test_user_step_wrapped_in_runuser_when_root(backend, monkeypatch):
    monkeypatch.setattr(backend, "is_root", lambda: True)
    monkeypatch.setattr(backend, "_invoking_user", lambda: "emir")
    script = backend._build_script(registry.HOMEBREW.install_steps, as_root=True)
    assert "runuser -l emir -c" in script


def test_no_escalation_blocks_root_op(backend, monkeypatch):
    monkeypatch.setattr(backend, "is_root", lambda: False)
    monkeypatch.setattr("parduspm.backend.shutil.which", lambda c: None)
    result = backend.install(registry.SNAP)
    assert not result.ok
    assert "administrator rights" in result.message.lower()


def test_result_is_json_serialisable():
    r = OperationResult("flatpak", "install", True, "ok")
    assert '"ok": true' in r.to_json()
