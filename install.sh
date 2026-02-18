#!/bin/bash

if [ ! -f .config ]; then
    echo "No configuration found. Run 'make menuconfig' first."
    exit 1
fi

source .config

echo "Installing selected components..."

if [ "$CONFIG_APK" == "y" ]; then
    echo "Fetching Alpine stratum..."
    brl fetch alpine --mirror https://dl-cdn.alpinelinux.org/alpine/ 
fi

if [ "$CONFIG_XBPS" == "y" ]; then
    echo "Fetching Void stratum..."
    brl fetch void --mirror https://repo-default.voidlinux.org
fi

if [ "$CONFIG_DNF" == "y" ]; then
    echo "Fetching CentOS stratum..."
    brl fetch centos
fi

if [ "$CONFIG_ZYPPER" == "y" ]; then
    echo "Fetching openSUSE stratum..."
    brl fetch opensuse
fi

if [ "$CONFIG_EMERGE" == "y" ]; then
    echo "Fetching Gentoo stratum..."
    brl fetch gentoo --mirror https://gentoo.osuosl.org/
fi

if [ "$CONFIG_PACMAN" == "y" ]; then
    echo "Fetching Arch stratum..."
    brl fetch arch --mirror https://fastly.mirror.pkgbuild.com/ 
fi

if [ "$CONFIG_NIX" == "y" ]; then
    echo "Installing Nix..."
    yes | sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --daemon
fi

