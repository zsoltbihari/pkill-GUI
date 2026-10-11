# pkill-GUI

**Magyar / English**

Könnyű, PySide6-alapú Linuxos folyamatkezelő, amely a rendszer tálcájáról nyitható meg. A program X11/XWayland környezethez készült.

A projekt jelenlegi állapotban fejlesztés alatt áll. A funkciók és a működés a tesztelés során változhatnak.

## Magyar

### Funkciók

- Rendszertálca-ikon és lenyitható folyamatmenü.
- Két listázási mód: a látható grafikus ablakok folyamatai, vagy az összes, a rendszerből lekérdezhető folyamat.
- Felhasználónkénti összesítő nézet: az összesített CPU-terhelés és a folyamatok száma látható; egy felhasználóra kattintva megnyílik a részletes listája.
- Folyamatonkénti CPU-terhelés kijelzése, konfigurálható CPU-sávokkal.
- PID, folyamatnév, parancssor és folyamatállapot megtekintése.
- Folyamatokhoz tartozó szálak megjelenítése.
- Normál ablakbezárás, illetve folyamatleállítás Linux-jelzésekkel, például `SIGTERM` és `SIGKILL`.
- Frissítési időköz, megerősítési kérdések és színpaletták beállítása.
- Fülekre bontott beállítópanel és a támogatott Linux/POSIX jelek leírása.

### Követelmények

- Linux grafikus munkamenet X11 vagy XWayland támogatással
- Python 3
- PySide6
- `procps` (`ps` parancs)
- `xdotool` és `xprop` a látható ablakok módjához

Debian és AV Linux alapú rendszeren a rendszerfüggőségek telepítése:

```bash
sudo apt update
sudo apt install python3 python3-pyside6.qtwidgets procps xdotool x11-utils
```

Ha a disztribúció csomagja nem biztosítja a PySide6-ot, telepítsd a PySide6-ot a disztribúciód által ajánlott módszerrel vagy a Python-környezetedhez tartozó csomagkezelővel.

### Indítás

Mentsd a programfájlt például `pkill-GUI.py` néven, majd futtasd:

```bash
python3 pkill-GUI.py
```

A program a rendszer tálcáján jelenik meg. A tálca megjelenése a használt asztali környezettől és annak tálcabeállításaitól is függ.

### Fontos tudnivalók

- Az összes folyamat listázása nem jelent automatikusan rendszergazdai jogosultságot. Egy normál felhasználó által indított program nem feltétlenül tud más felhasználó vagy a `root` folyamataiba beavatkozni.
- A folyamat CPU-értéke egy CPU-mag teljes kihasználásához viszonyított érték; ezért több folyamat összege, illetve egy többmagos rendszer terhelése meghaladhatja a 100%-ot.
- A `SIGKILL` azonnal megszakítja a folyamatot, ezért adatvesztést okozhat. Először lehetőleg normál bezárást vagy `SIGTERM` jelzést használj.
- A programot a saját Linux-rendszereden teszteld, mielőtt fontos folyamatok kezelésére használnád.

## English

A lightweight Linux process manager built with PySide6 and accessible from the system tray. It is designed for X11/XWayland graphical sessions.

The project is currently under development. Features and behavior may change as testing continues.

### Features

- System-tray icon with a drop-down process menu.
- Two listing modes: processes associated with visible graphical windows, or all processes reported by the system.
- Per-user summary view showing aggregate CPU usage and process count; selecting a user opens that user's detailed process list.
- Per-process CPU indicators with configurable CPU bars.
- Process ID (PID), process name, command line, and process state details.
- Display of threads belonging to a process.
- Normal window closing and process termination using Linux signals such as `SIGTERM` and `SIGKILL`.
- Configurable refresh interval, confirmation prompts, and color palettes.
- Tabbed settings dialog and descriptions of supported Linux/POSIX signals.

### Requirements

- Linux graphical session with X11 or XWayland support
- Python 3
- PySide6
- `procps` (`ps` command)
- `xdotool` and `xprop` for visible-window mode

On Debian- or AV Linux-based systems, install the system dependencies with:

```bash
sudo apt update
sudo apt install python3 python3-pyside6.qtwidgets procps xdotool x11-utils
```

If your distribution does not provide PySide6 through that package, install PySide6 using the method recommended by your distribution or the package manager for your Python environment.

### Run

Save the program as `pkill-GUI.py`, then run:

```bash
python3 pkill-GUI.py
```

The application appears in the system tray. Tray availability and appearance depend on the desktop environment and its tray configuration.

### Important notes

- Listing all processes does not automatically grant administrator privileges. A program running as a normal user may not be allowed to signal processes owned by another user or by `root`.
- CPU usage is measured relative to the full utilization of one CPU core. Aggregate values can therefore exceed 100% on multi-core systems.
- `SIGKILL` terminates a process immediately and may cause data loss. Prefer normal window closing or `SIGTERM` when possible.
- Test the application on your own Linux system before using it to manage important processes.

## License

No license has been selected yet. Unless a license is added to this repository, the default copyright rules apply and others do not automatically receive permission to redistribute or modify the code.
