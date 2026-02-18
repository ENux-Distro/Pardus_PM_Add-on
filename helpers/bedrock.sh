#!/bin/bash

[ "$EUID" -ne 0 ] && echo "Run as root / Root ile çalıştırınız" && exit 1

wget https://github.com/bedrocklinux/bedrocklinux-userland/releases/download/0.7.31/bedrock-linux-0.7.31-x86_64.sh -O /tmp/bedrock-install.sh
chmod +x /tmp/bedrock-install.sh
yes "Not reversible!" | bash /tmp/bedrock-install.sh --hijack
rm -rf /tmp/bedrock-install.sh
