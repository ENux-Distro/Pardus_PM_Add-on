#!/usr/bin/env bash
# Install the icon and desktop entry into the current user's XDG directories so
# the app shows the Pardus icon (not the generic Python one) in the menu and
# taskbar. No root required. Run again to refresh after changes.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
app_id="org.pardus.PackageManagerAddon"

icon_src="$repo/packaging/icons/hicolor/scalable/apps/$app_id.svg"
icon_dst_dir="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
apps_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

install -Dm644 "$icon_src" "$icon_dst_dir/$app_id.svg"

# Install the desktop entry, pointing Exec at this checkout's launcher.
mkdir -p "$apps_dir"
sed "s|^Exec=.*|Exec=$repo/bin/pardus-pm gui|" \
    "$repo/packaging/$app_id.desktop" > "$apps_dir/$app_id.desktop"
chmod 644 "$apps_dir/$app_id.desktop"

# Refresh caches if the tools are available (harmless if they are not).
command -v gtk-update-icon-cache >/dev/null \
    && gtk-update-icon-cache -f -t "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" 2>/dev/null || true
command -v update-desktop-database >/dev/null \
    && update-desktop-database "$apps_dir" 2>/dev/null || true

echo "Installed $app_id icon and desktop entry for $USER."
echo "You may need to log out/in (or restart the panel) for the taskbar icon to refresh."
