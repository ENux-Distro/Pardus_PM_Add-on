# Pardus PM Add-On

## What is Pardus PM Add-On

Pardus PM Add-On is a moduler interactive extention tool that enables support for multi package manager support.
Using Bedrock Linux, this program gives the user could support for up to 12 package managers on their system, which are:

- dpkg / apt (Debian)
- apk (Alpine)
- xbps (Void)
- dnf / rpm (CentOS / Red Hat)
- zypper (openSUSE)
- emerge / portage (Gentoo)
- pacman (Arch)
- pmm (Package Manager Manager)
- nix (NixOS)

**Conflict resolution:**
Bedrock Linux handles most compatibility headaches. For beginners, **pmm** simplifies package management into one easy-to-use tool.
Note: nix isn't a part of brl/pmm, it is independent.

## How to Install Pardus PM Add-On Program

In order to run the Pardus PM Add-on program, you need to do these steps:

 - Git clone the repository via `sudo apt install git && git clone --depth 1 https://github.com/ENux-Distro/Pardus_PM_Add-on.git`
 - Change your directory to the repositories' directory via `cd /path/to/Pardus_PM_Add-on`
 - Run `sudo make bedrock`
 - After the script reboots itself, run the Pardus PM Add-on tools via `cd /path/to/Pardus_PM_Add-on` and then `sudo make install`
 - Select the package managers you want to add. After that script will do it's thing

After everything has went succesfully, you now have installed the Pardus PM Add-on tool
