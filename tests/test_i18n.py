"""Tests for the locale detection and translation fallback logic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parduspm import i18n  # noqa: E402


def test_detect_turkish_locale(monkeypatch):
    monkeypatch.delenv("PARDUS_PM_LANG", raising=False)
    monkeypatch.setenv("LANG", "tr_TR.UTF-8")
    assert i18n._detect_language() == "tr"


def test_detect_defaults_to_english(monkeypatch):
    monkeypatch.delenv("PARDUS_PM_LANG", raising=False)
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert i18n._detect_language() == "en"


def test_override_wins(monkeypatch):
    monkeypatch.setenv("PARDUS_PM_LANG", "tr")
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert i18n._detect_language() == "tr"


def test_translation_and_formatting(monkeypatch):
    monkeypatch.setattr(i18n, "LANG", "tr")
    assert i18n.t("install") == "Kur"
    assert "Flatpak" in i18n.t("confirm_install_pm", name="Flatpak")
    assert i18n.status_text(True) == "Kurulu"
    assert i18n.status_text(False) == "Kurulu Değil"


def test_unknown_key_returns_key(monkeypatch):
    monkeypatch.setattr(i18n, "LANG", "en")
    assert i18n.t("no_such_key") == "no_such_key"


def test_pm_helpers_fall_back_to_english(monkeypatch):
    from parduspm import registry
    monkeypatch.setattr(i18n, "LANG", "en")
    # English path returns the registry text verbatim.
    assert i18n.pm_description(registry.FLATPAK) == registry.FLATPAK.description
    monkeypatch.setattr(i18n, "LANG", "tr")
    assert "Flatpak" in i18n.pm_description(registry.FLATPAK)
