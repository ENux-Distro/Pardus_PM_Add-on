#!/bin/bash

wget https://github.com/bedrocklinux/bedrocklinux-userland/releases/download/0.7.31/bedrock-linux-0.7.31-x86_64.sh -O /tmp/bedrock-install.sh
chmod +x /tmp/bedrock-install.sh
yes "Not reversible!" | bash /tmp/bedrock-install.sh --hijack
rm -rf /tmp/bedrock-install.sh

cat > /usr/share/applications/pardus-pm-addon.desktop << 'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=Pardus Package Manager Add-On
GenericName=Package Manager Add-On
Exec=pkexec /usr/bin/pardus-pm-addon
Icon=system-software-install
Terminal=true
Categories=System;Settings;
EOF

apt -qqq install fastfetch -y
mkdir -p /etc/fastfetch
cat > /etc/fastfetch/config.jsonc << 'EOF'
{
  "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
  "logo": {
    "source": "pardus"
  },
  "display": {
    "color": "33"
  },
  "modules": [
    "title",
    "separator",
    { "type": "os", "format": "Pardus GNU/Linux 25 (yirmibeş)" },
    "host",
    "kernel",
    "uptime",
    "packages",
    "shell",
    "display",
    "de",
    "wm",
    "wmtheme",
    "theme",
    "icons",
    "font",
    "cursor",
    "terminal",
    "terminalfont",
    "cpu",
    "gpu",
    "memory",
    "swap",
    "disk",
    "localip",
    "battery",
    "poweradapter",
    "locale",
    "break",
    "colors"
  ]
}
EOF
