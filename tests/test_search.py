"""Tests for the cross-manager search parsers and install wiring.

Parsers are pure functions over captured command output, so they are tested
against representative samples. No real package manager is invoked.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parduspm import search  # noqa: E402
from parduspm.search import BY_ID, SearchEngine, SearchResult  # noqa: E402


def test_parse_apt():
    text = "htop - interactive process viewer\nnotapackageline\nvim - editor"
    out = search._parse_apt(BY_ID["apt"], text)
    assert [(r.name, r.description) for r in out] == [
        ("htop", "interactive process viewer"),
        ("vim", "editor"),
    ]
    assert out[0].install_id == "htop"


def test_parse_flatpak_uses_application_id_for_install():
    text = "htop\tProcess monitor\tio.github.htop\t3.3"
    out = search._parse_flatpak(BY_ID["flatpak"], text)
    assert len(out) == 1
    assert out[0].name == "htop"
    assert out[0].install_id == "io.github.htop"
    assert out[0].version == "3.3"


def test_parse_snap_skips_header_and_keeps_summary():
    text = ("Name  Version  Publisher  Notes  Summary\n"
            "htop  3.2.1    foo        -      Interactive process viewer")
    out = search._parse_snap(BY_ID["snap"], text)
    assert len(out) == 1
    assert out[0].name == "htop"
    assert out[0].version == "3.2.1"
    assert out[0].description == "Interactive process viewer"


def test_parse_nix_json_extracts_attr_path():
    text = json.dumps({
        "legacyPackages.x86_64-linux.htop": {
            "pname": "htop", "version": "3.3.0", "description": "interactive viewer"
        }
    })
    out = search._parse_nix(BY_ID["nix"], text)
    assert len(out) == 1
    assert out[0].install_id == "htop"          # attr after the system component
    assert out[0].version == "3.3.0"


def test_parse_nix_bad_json_is_safe():
    assert search._parse_nix(BY_ID["nix"], "not json") == []


def test_parse_brew_ignores_section_headers():
    text = "==> Formulae\nhtop\nhtop-vim\n==> Casks\n"
    out = search._parse_brew(BY_ID["homebrew"], text)
    assert [r.name for r in out] == ["htop", "htop-vim"]


def test_install_steps_per_manager():
    assert BY_ID["apt"].install_steps("htop")[0].argv == ["apt-get", "install", "-y", "htop"]
    assert "io.github.htop" in BY_ID["flatpak"].install_steps("io.github.htop")[0].argv


def test_capabilities_epkg_install_only():
    epkg = BY_ID["epkg"]
    assert epkg.supports("install")
    assert not epkg.supports("search")
    assert not epkg.supports("remove")
    assert not epkg.supports("update")
    assert not epkg.supports("upgrade")


def test_apt_supports_all_operations():
    apt = BY_ID["apt"]
    assert all(apt.supports(op) for op in ("search", "install", "remove", "update", "upgrade"))


def test_homebrew_detected_off_path(monkeypatch):
    # Homebrew is not on PATH after install; it must still be found via its
    # known location, and commands must run by absolute path.
    brew = BY_ID["homebrew"]
    monkeypatch.setattr(search.shutil, "which", lambda c: None)
    monkeypatch.setattr(search.os.path, "exists",
                        lambda p: "linuxbrew" in p)
    resolved = brew.resolve()
    assert resolved and resolved.endswith("/bin/brew")

    engine = SearchEngine(object())
    argv = engine._resolve_argv(brew, ["brew", "install", "wget"])
    assert argv == [resolved, "install", "wget"]


def test_remove_and_upgrade_steps():
    assert BY_ID["apt"].remove_steps("htop")[0].argv == ["apt-get", "remove", "-y", "--purge", "htop"]
    # apt upgrade refreshes then upgrades -> two steps in one run.
    assert len(BY_ID["apt"].upgrade_steps()) == 2


def test_engine_install_delegates_to_backend():
    captured = {}

    class FakeBackend:
        def run_steps(self, label, steps, on_line=None):
            captured["label"] = label
            captured["steps"] = steps
            return True, "Success"

    engine = SearchEngine(FakeBackend())
    r = SearchResult("apt", "APT", "htop", "htop", "", "")
    ok, _ = engine.install(r)
    assert ok
    assert "htop" in captured["label"]
    assert captured["steps"][0].argv == ["apt-get", "install", "-y", "htop"]
