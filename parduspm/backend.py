"""Shared backend used by both the TUI and GUI.

Responsibilities:
  * detect which package managers are installed
  * run install / remove procedures with privilege escalation
  * stream command output back to the caller
  * return structured results (also serialisable to JSON)

The backend never asks for confirmation and never talks to a user directly --
that is the frontend's job. It only does work it is explicitly told to do, one
package manager at a time, which keeps the "never install everything
automatically" guarantee in one place.
"""

from __future__ import annotations

import enum
import json
import os
import pwd
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass

from . import registry
from .logger import ActivityLog
from .registry import PackageManager, Privilege, Step


class Status(enum.Enum):
    INSTALLED = "Installed"
    NOT_INSTALLED = "Not Installed"


# A line callback receives each line of command output as it is produced.
LineCallback = Callable[[str], None]


@dataclass
class OperationResult:
    pm_id: str
    action: str          # "install" or "remove"
    ok: bool
    message: str
    failed_step: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class PrivilegeError(RuntimeError):
    """Raised when a step needs privileges we cannot obtain."""


class Backend:
    def __init__(self, log: ActivityLog | None = None):
        self.log = log or ActivityLog()

    # -- detection ---------------------------------------------------------

    def detect(self, pm: PackageManager) -> Status:
        if pm.detect_command and shutil.which(pm.detect_command):
            return Status.INSTALLED
        for path in self._candidate_paths(pm):
            if os.path.exists(path):
                return Status.INSTALLED
        return Status.NOT_INSTALLED

    def detect_all(self, *, quiet: bool = False) -> dict[str, Status]:
        result = {}
        for pm in registry.ALL:
            status = self.detect(pm)
            result[pm.id] = status
            if not quiet and status is Status.INSTALLED:
                self.log.info(f"Detected {pm.name}")
        return result

    def _candidate_paths(self, pm: PackageManager) -> list[str]:
        paths = list(pm.detect_paths)
        # Homebrew can also live under the invoking user's home directory.
        if pm.id == "homebrew":
            paths.append(str(self._invoking_home() / ".linuxbrew" / "bin" / "brew"))
        return paths

    # -- privilege helpers -------------------------------------------------

    def is_root(self) -> bool:
        return os.geteuid() == 0

    def has_escalation(self) -> bool:
        return self.is_root() or bool(shutil.which("pkexec") or shutil.which("sudo"))

    def _invoking_user(self) -> str:
        # When launched via pkexec/sudo, SUDO_USER / PKEXEC_UID point at the
        # real human user; fall back to the current login.
        for var in ("SUDO_USER", "PKEXEC_USER"):
            if os.environ.get(var):
                return os.environ[var]
        uid = os.environ.get("PKEXEC_UID")
        if uid:
            return pwd.getpwuid(int(uid)).pw_name
        return pwd.getpwuid(os.getuid()).pw_name

    def _invoking_home(self):
        from pathlib import Path
        return Path(pwd.getpwnam(self._invoking_user()).pw_dir)

    def _escalation_prefix(self, needs_root: bool) -> list[str]:
        """How to launch the procedure script. One escalation for the whole run."""
        if not needs_root or self.is_root():
            return []
        if shutil.which("pkexec"):
            return ["pkexec"]
        if shutil.which("sudo"):
            return ["sudo"]
        raise PrivilegeError(
            "This action needs administrator rights but neither pkexec nor "
            "sudo is available."
        )

    def _build_script(self, steps: list[Step], as_root: bool) -> str:
        """Build a single shell script running every step in order.

        Each step is preceded by a marker line so the caller can attribute log
        output and failures to a specific step. ``set -e`` stops at the first
        failing step. USER steps are dropped to the invoking user with runuser
        when the script itself runs as root.
        """
        lines = [
            "#!/bin/sh",
            "set -e",
            "export DEBIAN_FRONTEND=noninteractive",
        ]
        for step in steps:
            label = step.description or " ".join(step.argv)
            lines.append(f"printf '%s\\n' {_shquote(STEP_MARKER + label)}")
            command = " ".join(_shquote(a) for a in step.argv)
            if step.privilege is Privilege.USER and as_root:
                command = f"runuser -l {_shquote(self._invoking_user())} -c {_shquote(command)}"
            lines.append(command)
        return "\n".join(lines) + "\n"

    # -- operations --------------------------------------------------------

    def install(self, pm: PackageManager, on_line: LineCallback | None = None) -> OperationResult:
        return self._run_procedure(pm, "install", pm.install_steps, on_line)

    def remove(self, pm: PackageManager, on_line: LineCallback | None = None) -> OperationResult:
        return self._run_procedure(pm, "remove", pm.remove_steps, on_line)

    def _run_procedure(
        self,
        pm: PackageManager,
        action: str,
        steps: list[Step],
        on_line: LineCallback | None,
    ) -> OperationResult:
        verb = "installation" if action == "install" else "removal"
        self.log.action(f"User requested {verb} of {pm.name}")

        if not steps:
            return OperationResult(pm.id, action, False, "No procedure defined.")

        needs_root = any(s.privilege is Privilege.ROOT for s in steps)
        try:
            prefix = self._escalation_prefix(needs_root)
        except PrivilegeError as exc:
            self.log.error(f"{pm.name}: {exc}")
            return OperationResult(pm.id, action, False, str(exc))

        as_root = needs_root or self.is_root()
        script = self._build_script(steps, as_root)

        # Track which step is running so a failure can name it. The marker lines
        # are written by the script itself (see _build_script).
        current = {"label": None}

        def handle(line: str) -> None:
            if line.startswith(STEP_MARKER):
                current["label"] = line[len(STEP_MARKER):]
                self.log.info(f"{pm.name}: {current['label']}")
                return
            if on_line:
                on_line(line)

        code = self._run_script(script, prefix, handle)
        if code != 0:
            label = current["label"] or "unknown step"
            msg = f"Step failed (exit {code}): {label}"
            self.log.error(f"{pm.name}: {msg}")
            return OperationResult(pm.id, action, False, msg, current["label"])

        done = "installed" if action == "install" else "removed"
        self.log.success(f"{pm.name} {done} successfully")
        return OperationResult(pm.id, action, True, f"{pm.name} {done} successfully.")

    def _run_script(self, script: str, prefix: list[str], on_line: LineCallback | None) -> int:
        """Write the script to a temp file and run it once, streaming output.

        The file is mode 0700 (not world-writable) so pkexec will accept it,
        and is removed afterwards regardless of outcome.
        """
        fd, path = tempfile.mkstemp(prefix="pardus-pm-", suffix=".sh")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(script)
            os.chmod(path, 0o700)

            try:
                proc = subprocess.Popen(
                    [*prefix, path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
                )
            except FileNotFoundError as exc:
                if on_line:
                    on_line(f"command not found: {exc.filename}")
                return 127

            assert proc.stdout is not None
            for line in proc.stdout:
                if on_line:
                    on_line(line.rstrip("\n"))
            return proc.wait()
        finally:
            # pkexec runs the script as root, but the temp file stays owned by
            # us, so we can always clean it up.
            try:
                os.unlink(path)
            except OSError:
                pass


# Sentinel that prefixes step-boundary lines in generated scripts. Chosen to be
# extremely unlikely to collide with real command output.
STEP_MARKER = "__PPM_STEP__:"


def _shquote(arg: str) -> str:
    import shlex
    return shlex.quote(arg)
