#!/usr/bin/env bash
# Kconfig.sh - Pardus Multi Package Manager Config (with EN/TR i18n)
CONFIG_FILE=".config"

# default values (kept for reference; actual saved into .config)
APK=OFF
XBPS=OFF
DNF=OFF
ZYPPER=OFF
EMERGE=OFF
PACMAN=OFF
NIX=OFF

# --- Language selection ---
LANG_CHOICE=$(whiptail --title "Language / Dil" \
  --menu "Select language / Dil seçin:" 12 50 2 \
  "EN" "English" \
  "TR" "Türkçe" \
  3>&1 1>&2 2>&3)

if [ $? -ne 0 ]; then
  echo "Cancelled."
  exit 1
fi

# --- Messages (EN / TR) ---
if [ "$LANG_CHOICE" = "TR" ]; then
  TITLE="Pardus Çoklu Paket Yöneticisi - Konfigurasyon"
  SELECT_PM="Etkinleştirmek istediğiniz paket yöneticilerini seçin:"
  CANCELLED="İşlem iptal edildi."
  CONFIRM_INSTALL="Seçilen paket yöneticileri kurulacak. Devam edilsin mi?"
  RUN_INSTALL_MSG="Kurulum şimdi başlayacak..."
  SKIP_INSTALL_MSG="Kurmak için 'make fullinstall' çalıştırın."
else
  TITLE="Pardus Multi Package Manager - Configuration"
  SELECT_PM="Select package managers to enable:"
  CANCELLED="Cancelled."
  CONFIRM_INSTALL="Selected package managers will be installed. Proceed?"
  RUN_INSTALL_MSG="Starting installation..."
  SKIP_INSTALL_MSG="Run 'make fullinstall' when ready."
fi

# --- Checklist prompt ---
OPTIONS=$(whiptail --title "$TITLE" \
  --checklist "$SELECT_PM" 25 75 15 \
  "APK"    "Alpine (apk)" OFF \
  "XBPS"   "Void (xbps)" OFF \
  "DNF"    "CentOS/RedHat (dnf/rpm)" OFF \
  "ZYPPER" "openSUSE (zypper)" OFF \
  "EMERGE" "Gentoo (portage)" OFF \
  "PACMAN" "Arch (pacman)" OFF \
  "NIX"    "NixOS (nix)" OFF \
  3>&1 1>&2 2>&3)

if [ $? -ne 0 ]; then
  echo "$CANCELLED"
  exit 1
fi

# --- Write .config header and defaults ---
echo "# Pardus Multi Package Manager Configuration" > "$CONFIG_FILE"
# save language choice
echo "CONFIG_LANG=$LANG_CHOICE" >> "$CONFIG_FILE"

# --- Parse selected options robustly ---
# whiptail returns items like: "APK" "PACMAN"
for opt in $OPTIONS; do
  # remove possible surrounding quotes
  opt_clean=$(echo "$opt" | tr -d '"')
  case "$opt_clean" in
    APK)    echo "CONFIG_APK=y" >> "$CONFIG_FILE" ;;
    XBPS)   echo "CONFIG_XBPS=y" >> "$CONFIG_FILE" ;;
    DNF)    echo "CONFIG_DNF=y" >> "$CONFIG_FILE" ;;
    ZYPPER) echo "CONFIG_ZYPPER=y" >> "$CONFIG_FILE" ;;
    EMERGE) echo "CONFIG_EMERGE=y" >> "$CONFIG_FILE" ;;
    PACMAN) echo "CONFIG_PACMAN=y" >> "$CONFIG_FILE" ;;
    PMM)    echo "CONFIG_PMM=y" >> "$CONFIG_FILE" ;;
    NIX)    echo "CONFIG_NIX=y" >> "$CONFIG_FILE" ;;
    *)      # ignore unknown tokens
            ;;
  esac
done

# Feedback to user (small localized echo)
if [ "$LANG_CHOICE" = "TR" ]; then
  echo "Yapılandırma .config dosyasına kaydedildi:"
else
  echo "Configuration saved to .config:"
fi
cat "$CONFIG_FILE"

# --- Confirm and optionally auto-run install ---
whiptail --yesno "$CONFIRM_INSTALL" 10 60
if [ $? -eq 0 ]; then
  make fullinstall
else
  if [ "$LANG_CHOICE" = "TR" ]; then
    echo "$SKIP_INSTALL_MSG"
  else
    echo "$SKIP_INSTALL_MSG"
  fi
fi

exit 0
