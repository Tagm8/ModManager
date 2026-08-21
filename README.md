# SA Mod Manager 1.0

> Modern GTA San Andreas Mod Manager

## Features

- Native PySide6 GUI
- Non-Steam GTA SA folder support
- Steam/Proton-friendly architecture
- Profiles
- Mod catalog + dependency gates
- Upstream GitHub release downloads
- CLEO 4
- SilentPatch SA
- Widescreen Fix
- Ultimate ASI Loader
- Project2DFX
- Mod Loader destination for content-style mods
- Backup/rollback foundation
- User-supplied GTA SA 1.0 EXE installer
- SHA-256 logging
- Safe ZIP extraction
- Diagnostics
- No Rockstar binaries distributed

## Install
- On Linux
```bash
sudo apt install python3 python3-venv
unzip SA-Mod-Manager-Linux-v1.0.zip
cd sa_mod_manager_v1
./run.sh
```

## Important

The current release is a serious foundation, but it is not claiming to understand every arbitrary GTA SA mod on the internet. A production-quality catalog needs signed/verified manifests describing files, dependencies, conflicts, game versions and install rules.

CLEO's upstream documentation states that CLEO requires an ASI Loader and that its installer adds `cleo/`, `cleo.asi`, `bass.dll`, `vorbisHooked.dll`, etc., while overwriting `vorbisFile.dll`; the manager therefore backs up likely root conflicts before installation.

## Upstream projects

CLEO 4:
https://github.com/cleolibrary/CLEO4

SilentPatch:
https://github.com/CookiePLMonster/SilentPatch

Widescreen Fixes Pack:
https://github.com/ThirteenAG/WidescreenFixesPack

Ultimate ASI Loader:
https://github.com/ThirteenAG/Ultimate-ASI-Loader

Project2DFX:
https://github.com/ThirteenAG/III.VC.SA.IV.Project2DFX
