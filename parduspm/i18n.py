"""Minimal locale-based translations (Turkish / English).

The language is chosen once at startup from the environment locale: a locale
starting with ``tr`` selects Turkish, anything else falls back to English. Set
``PARDUS_PM_LANG=tr`` or ``=en`` to override (handy for testing).

This is intentionally a small dict-based table rather than gettext: no .po/.mo
build step, everything readable in one file. Use :func:`t` for UI strings and
the ``pm_*`` helpers for package-manager descriptions.
"""

from __future__ import annotations

import os


def _detect_language() -> str:
    override = os.environ.get("PARDUS_PM_LANG")
    if override:
        return "tr" if override.lower().startswith("tr") else "en"
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var)
        if val:
            return "tr" if val.lower().startswith("tr") else "en"
    return "en"


LANG = _detect_language()


# UI strings, keyed semantically. Each entry has "en" and "tr".
STRINGS: dict[str, dict[str, str]] = {
    # -- pardus-pm chrome --
    "app_title": {"en": "Pardus Package Manager Add-On Tool",
                  "tr": "Pardus Paket Yöneticisi Eklenti Aracı"},
    "package_managers": {"en": "Package Managers", "tr": "Paket Yöneticileri"},
    "details": {"en": "Details", "tr": "Ayrıntılar"},
    "status_actions": {"en": "Status & Actions", "tr": "Durum ve İşlemler"},
    "activity_log": {"en": "Activity Log", "tr": "Etkinlik Günlüğü"},
    "status": {"en": "Status", "tr": "Durum"},
    "features": {"en": "Features", "tr": "Özellikler"},
    "note": {"en": "Note", "tr": "Not"},
    "installed": {"en": "Installed", "tr": "Kurulu"},
    "not_installed": {"en": "Not Installed", "tr": "Kurulu Değil"},
    # -- actions / buttons --
    "install": {"en": "Install", "tr": "Kur"},
    "remove": {"en": "Remove", "tr": "Kaldır"},
    "cancel": {"en": "Cancel", "tr": "İptal"},
    "details_btn": {"en": "Details", "tr": "Ayrıntılar"},
    "exit": {"en": "Exit", "tr": "Çık"},
    "up": {"en": "Up", "tr": "Yukarı"},
    "down": {"en": "Down", "tr": "Aşağı"},
    # -- confirmation dialogs (pardus-pm) --
    "dlg_install_title": {"en": "Install Package Manager", "tr": "Paket Yöneticisi Kur"},
    "dlg_remove_title": {"en": "Remove Package Manager", "tr": "Paket Yöneticisi Kaldır"},
    "confirm_install_pm": {"en": "You are about to install {name} on this system.",
                           "tr": "{name} bu sisteme kurulmak üzere."},
    "confirm_remove_pm": {"en": "You are about to remove {name} from this system.",
                          "tr": "{name} bu sistemden kaldırılmak üzere."},
    "continue_q": {"en": "Continue?", "tr": "Devam edilsin mi?"},
    "already_installed": {"en": "{name} is already installed",
                          "tr": "{name} zaten kurulu"},
    "not_currently_installed": {"en": "{name} is not installed",
                                "tr": "{name} kurulu değil"},
    # -- backend log lifecycle --
    "log_detected": {"en": "Detected {name}", "tr": "{name} algılandı"},
    "log_req_install": {"en": "User requested installation of {name}",
                        "tr": "{name} kurulumu istendi"},
    "log_req_remove": {"en": "User requested removal of {name}",
                       "tr": "{name} kaldırılması istendi"},
    "log_install_ok": {"en": "{name} installed successfully",
                       "tr": "{name} başarıyla kuruldu"},
    "log_remove_ok": {"en": "{name} removed successfully",
                      "tr": "{name} başarıyla kaldırıldı"},
    "log_need_admin": {"en": "Administrator rights are required but not available.",
                       "tr": "Yönetici hakları gerekli ancak mevcut değil."},
    # -- pardus-pmm --
    "pmm_title": {"en": "Pardus Package Manager Manager",
                  "tr": "Pardus Paket Yöneticisi Yöneticisi"},
    "operations": {"en": "Operations", "tr": "İşlemler"},
    "op_search": {"en": "Search", "tr": "Ara"},
    "op_install": {"en": "Install", "tr": "Kur"},
    "op_remove": {"en": "Remove", "tr": "Kaldır"},
    "op_update": {"en": "Update", "tr": "Güncelle"},
    "op_upgrade": {"en": "Upgrade", "tr": "Yükselt"},
    "search_placeholder": {"en": "Search a package, then Enter",
                           "tr": "Bir paket arayın, sonra Enter"},
    "install_placeholder": {"en": "Package to install", "tr": "Kurulacak paket"},
    "remove_placeholder": {"en": "Package to remove", "tr": "Kaldırılacak paket"},
    "pick_manager_i": {"en": "Pick a manager, then press 'i':",
                       "tr": "Bir yönetici seçin, sonra 'i'ye basın:"},
    "pick_manager_r": {"en": "Pick a manager, then press 'r':",
                       "tr": "Bir yönetici seçin, sonra 'r'ye basın:"},
    "update_hint": {"en": "Press 'u' to refresh package metadata for every manager below.",
                    "tr": "Aşağıdaki her yönetici için paket verilerini yenilemek üzere 'u'ya basın."},
    "upgrade_hint": {"en": "Press 'u' to upgrade everything installed across the managers below.",
                     "tr": "Aşağıdaki yöneticilerde kurulu her şeyi yükseltmek üzere 'u'ya basın."},
    "search_capable": {"en": "Search-capable managers: {names}",
                       "tr": "Arama yapabilen yöneticiler: {names}"},
    "searching": {"en": "Searching {n} manager(s) for '{term}'",
                  "tr": "'{term}' için {n} yönetici aranıyor"},
    "results_count": {"en": "{name}: {n} result(s)", "tr": "{name}: {n} sonuç"},
    "search_complete": {"en": "Search complete: {n} result(s) for '{term}'",
                        "tr": "Arama tamamlandı: '{term}' için {n} sonuç"},
    "type_query": {"en": "Type a query and press Enter.",
                   "tr": "Bir sorgu yazıp Enter'a basın."},
    "d_manager": {"en": "Manager: {name}", "tr": "Yönetici: {name}"},
    "d_install_id": {"en": "Install id: {id}", "tr": "Kurulum kimliği: {id}"},
    "d_version": {"en": "Version: {v}", "tr": "Sürüm: {v}"},
    "d_press_i": {"en": "Press 'i' to install via {name}",
                  "tr": "{name} ile kurmak için 'i'ye basın"},
    "dlg_install_pkg": {"en": "Install Package", "tr": "Paket Kur"},
    "dlg_remove_pkg": {"en": "Remove Package", "tr": "Paket Kaldır"},
    "confirm_install_result": {"en": "Install {name} ({id})\nvia {mgr} on this system.",
                               "tr": "{name} ({id})\n{mgr} ile bu sisteme kurulacak."},
    "confirm_install_pkg": {"en": "Install '{pkg}' via {mgr} on this system.",
                            "tr": "'{pkg}' paketi {mgr} ile bu sisteme kurulacak."},
    "confirm_remove_pkg": {"en": "Remove '{pkg}' via {mgr} from this system.",
                           "tr": "'{pkg}' paketi {mgr} ile bu sistemden kaldırılacak."},
    "dlg_update_title": {"en": "Update system", "tr": "Sistemi Güncelle"},
    "dlg_upgrade_title": {"en": "Upgrade system", "tr": "Sistemi Yükselt"},
    "confirm_update_all": {"en": "Update across: {names}.", "tr": "Şunlarda güncelleme: {names}."},
    "confirm_upgrade_all": {"en": "Upgrade across: {names}.", "tr": "Şunlarda yükseltme: {names}."},
    "type_pkg_first": {"en": "Type a package name first.", "tr": "Önce bir paket adı yazın."},
    "no_manager_selected": {"en": "No manager selected.", "tr": "Yönetici seçilmedi."},
    "no_manager_supports": {"en": "No managers support {op}.", "tr": "Hiçbir yönetici {op} desteklemiyor."},
    "update_upgrade": {"en": "Update/Upgrade", "tr": "Güncelle/Yükselt"},
}


# Per-package-manager Turkish text. English comes from the registry; only the
# Turkish overrides live here. Keys: description, features (list), notes.
PM_TR: dict[str, dict[str, object]] = {
    "flatpak": {
        "description": ("Flatpak, masaüstü uygulamaları için yaygın olarak kullanılan, "
                        "yalıtımlı (sandbox) bir uygulama dağıtım sistemidir. Yalıtım ve "
                        "dağıtımlar arası uyumluluk sağlar."),
        "features": ["Yalıtılmış masaüstü uygulamaları",
                     "Dağıtımlar arası uyumluluk",
                     "Uygulama başına izinler"],
        "notes": "Flathub uygulamalarının menünüzde görünmesi için yeniden oturum açmanız önerilir.",
    },
    "snap": {
        "description": ("Snap, Canonical'ın uygulama paketleme sistemidir. Uygulamalar "
                        "kendi kendine yeten paketler olarak dağıtılır ve otomatik güncellenir."),
        "features": ["Kendi kendine yeten paketler",
                     "Otomatik arka plan güncellemeleri",
                     "Sınırlandırılmış çalışma ortamı"],
        "notes": "Snap, Pardus'ta önceden yapılandırılmamıştır; snapd depolardan kurulur.",
    },
    "nix": {
        "description": ("Nix, birden çok paket sürümüne ve bildirimsel sistem "
                        "yapılandırmalarına izin veren, yeniden üretilebilir bir paket yöneticisidir."),
        "features": ["Yeniden üretilebilir derlemeler",
                     "Yan yana birden çok sürüm",
                     "Bildirimsel yapılandırma"],
        "notes": ("Nix resmi ağ yükleyicisini kullanır ve /nix ile sistem kullanıcıları "
                  "(nixbld*) oluşturur. Kurulum önce eski *.backup-before-nix dosyalarını "
                  "temizler. Kaldırma işlemi en iyi çabayla yapılır; sonrasında yeniden "
                  "başlatma önerilir."),
    },
    "homebrew": {
        "description": ("Homebrew, başlangıçta macOS için geliştirilen ve artık Linux'ta da "
                        "bulunan, çapraz platform bir paket yöneticisidir."),
        "features": ["Geniş formül koleksiyonu",
                     "/home/linuxbrew altına kurulur",
                     "Çalışma zamanında root gerektirmez"],
        "notes": ("Homebrew normal bir kullanıcı olarak kurulmalı ve kaldırılmalıdır, asla "
                  "root olarak değil. Kurulum ~/.bashrc ve ~/.profile dosyalarınıza "
                  "`brew shellenv` ekler."),
    },
    "epkg": {
        "description": "EPkg, ENux ekosistemi için geliştirilmiş kaynak tabanlı bir paket yöneticisidir.",
        "features": ["Kaynak tabanlı paket kurulumu",
                     "Yedi ayna desteği",
                     "Hafif uygulama"],
        "notes": "EPkg, ENux deposundan alınan tek ve kendi kendine yeten bir betiktir.",
    },
}


def t(key: str, **kwargs) -> str:
    """Translate a UI string key into the current language, with formatting."""
    entry = STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(LANG) or entry.get("en") or key
    return text.format(**kwargs) if kwargs else text


def status_text(installed: bool) -> str:
    return t("installed") if installed else t("not_installed")


def pm_description(pm) -> str:
    if LANG == "tr":
        desc = PM_TR.get(pm.id, {}).get("description")
        if desc:
            return str(desc)
    return pm.description


def pm_features(pm) -> list[str]:
    if LANG == "tr":
        feats = PM_TR.get(pm.id, {}).get("features")
        if feats:
            return list(feats)
    return pm.features


def pm_notes(pm) -> str:
    if LANG == "tr":
        notes = PM_TR.get(pm.id, {}).get("notes")
        if notes:
            return str(notes)
    return pm.notes
