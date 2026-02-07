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

chmod 644 /usr/share/applications/pardus-pm-addon.desktop
