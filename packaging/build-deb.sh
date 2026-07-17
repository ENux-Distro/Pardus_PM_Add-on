#!/usr/bin/env bash
# Build a .deb for the Pardus Package Manager Add-On Tool.
#
# The package is architecture-independent (pure Python). Runtime dependencies
# (GTK, PyGObject, Textual) are declared and pulled from the distribution
# repositories -- no bundled virtualenv. Payload lives in /usr/share/pardus-pm
# with launcher symlinks in /usr/bin.
#
# Usage: packaging/build-deb.sh [version]   (default version below / $VERSION)
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="${1:-${VERSION:-1.0.0}}"
arch="all"
pkg="pardus-pm"
maintainer="ENux <emir73503@gmail.com>"

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

share="$stage/usr/share/pardus-pm"
docdir="$stage/usr/share/doc/pardus-pm"
appsdir="$stage/usr/share/applications"
icondir="$stage/usr/share/icons/hicolor/scalable/apps"
bindir="$stage/usr/bin"

# -- payload ----------------------------------------------------------------
install -d "$share" "$docdir" "$appsdir" "$icondir" "$bindir" "$stage/DEBIAN"
cp -a "$repo/parduspm" "$repo/tui" "$repo/gui" "$repo/bin" "$share/"
find "$share" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$share" -name '*.pyc' -delete

# -- launchers (symlinks resolve back to the payload via readlink -f) --------
ln -s /usr/share/pardus-pm/bin/pardus-pm  "$bindir/pardus-pm"
ln -s /usr/share/pardus-pm/bin/pardus-pmm "$bindir/pardus-pmm"

# -- desktop entries + icon --------------------------------------------------
install -m644 "$repo/packaging/org.pardus.PackageManagerAddon.desktop" "$appsdir/"
install -m644 "$repo/packaging/org.pardus.PackageManagerManager.desktop" "$appsdir/"
install -m644 "$repo/packaging/icons/hicolor/scalable/apps/org.pardus.PackageManagerAddon.svg" "$icondir/"

# -- documentation -----------------------------------------------------------
install -m644 "$repo/README.md" "$docdir/README.md"
cat > "$docdir/copyright" <<EOF
Upstream-Name: Pardus Package Manager Add-On Tool
Source: https://github.com/ENux-Distro

Files: *
Copyright: $(date +%Y) Emir (ENux)
License: All rights reserved (no license currently granted).
EOF
cat > "$docdir/changelog" <<EOF
$pkg ($version) unstable; urgency=medium

  * Pardus Package Manager Add-On Tool and pardus-pmm.

 -- $maintainer  $(date -R)
EOF
gzip -9n "$docdir/changelog"
mv "$docdir/changelog.gz" "$docdir/changelog.Debian.gz"

# -- control -----------------------------------------------------------------
# Installed-Size in KiB, for a friendlier apt experience.
size_kib="$(du -sk "$stage/usr" | cut -f1)"
cat > "$stage/DEBIAN/control" <<EOF
Package: $pkg
Version: $version
Section: admin
Priority: optional
Architecture: $arch
Depends: python3 (>= 3.11), python3-gi, gir1.2-gtk-4.0, python3-textual
Recommends: pkexec | policykit-1
Suggests: sudo
Maintainer: $maintainer
Homepage: https://github.com/ENux-Distro
Installed-Size: $size_kib
Description: manage additional package-manager ecosystems on Pardus
 Pardus Package Manager Add-On Tool installs or removes additional package
 management ecosystems -- Flatpak, Snap, Nix, Homebrew and EPkg -- with a
 Pardus-themed GTK 4 GUI and a keyboard-driven Textual TUI sharing one backend.
 .
 It also ships pardus-pmm, a cross-package-manager tool to search, install,
 remove, update and upgrade packages across every installed manager from one
 interface. Both tools are bilingual (Turkish / English, chosen by locale).
EOF

# -- maintainer scripts (refresh icon + desktop caches) ----------------------
cat > "$stage/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -f -t /usr/share/icons/hicolor 2>/dev/null || true
    fi
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications 2>/dev/null || true
    fi
fi
exit 0
EOF
cat > "$stage/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -f -t /usr/share/icons/hicolor 2>/dev/null || true
    fi
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications 2>/dev/null || true
    fi
fi
exit 0
EOF
chmod 0755 "$stage/DEBIAN/postinst" "$stage/DEBIAN/postrm"

# -- normalise permissions (no group-write; sane dir/file/exec bits) ---------
chmod 0755 "$stage"
find "$stage/usr" -type d -exec chmod 0755 {} +
find "$stage/usr" -type f -exec chmod 0644 {} +
chmod 0755 "$share/bin/pardus-pm" "$share/bin/pardus-pmm"

# -- build -------------------------------------------------------------------
out="$repo/dist"
install -d "$out"
deb="$out/${pkg}_${version}_${arch}.deb"
dpkg-deb --build --root-owner-group "$stage" "$deb"
echo "Built: $deb"
