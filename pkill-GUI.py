#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
pkill.py
BeOS-szerű, tálcáról lenyitható folyamatkezelő X11/XWayland Linuxhoz.

Funkciók:
- System tray ikon
- Bal kattintásra lenyíló programlista
- Két lista: látható ablakok vagy az összes rendszerfolyamat (root-folyamatokkal együtt)
- Programnév + CPU-terhelés
- CPU-frissítés csak akkor történik, amikor a lista nyitva van
- Alapértelmezett frissítés: 5 másodperc
- Normál bezárás: X11 WM_DELETE_WINDOW / xdotool windowclose
- Kényszerített leállítás: SIGKILL (-9)
- PID, ablakcím és parancssor megtekintése
- Beállítópanel
- A futó rendszeren elérhető kill jelek teljes listája külön leírással

Függőségek:
    Python 3
    PySide6
    xdotool
    xprop
    procps (ps)

Telepítés Debian/AV Linux alatt például:
    sudo apt install xdotool x11-utils procps
    python3 -m pip install PySide6

Futtatás:
    python3 pkill.py
"""

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QSettings, QTimer, Qt, QPoint
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QCursor, QIntValidator
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QLineEdit,
    QWidgetAction,
    QSizePolicy,
    QSystemTrayIcon,
    QTextBrowser,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "pkill.py"
ORG_NAME = "pkill.py"


# ---------------------------------------------------------------------------
# Linux/POSIX jelek
# ---------------------------------------------------------------------------

PALETTES = {
    "Normal": {
        "window": "#f0f0f0", "panel": "#ffffff", "text": "#202020",
        "menu": "#f5f5f5", "menu_text": "#202020", "menu_hover": "#d9e8ff",
        "accent": "#3b73b9", "accent_text": "#ffffff", "border": "#9a9a9a",
        "bar_fill": "#c00000", "bar_bg": "#666666", "bar_border": "#b0b0b0", "bar_width": 80, "bar_height": 5, "bar_baseline": 1, "bar_marker": 1,
    },
    "Hacker": {
        "window": "#101010", "panel": "#151515", "text": "#e6e6e6",
        "menu": "#111111", "menu_text": "#d8ffd8", "menu_hover": "#263b26",
        "accent": "#39ff14", "accent_text": "#000000", "border": "#39ff14",
        "bar_fill": "#ff3030", "bar_bg": "#214021", "bar_border": "#7aff7a", "bar_width": 80, "bar_height": 5, "bar_baseline": 1, "bar_marker": 1,
    },
    "Matrix": {
        "window": "#020602", "panel": "#031003", "text": "#00ff41",
        "menu": "#020802", "menu_text": "#00ff41", "menu_hover": "#063d12",
        "accent": "#00ff41", "accent_text": "#000000", "border": "#008f11",
        "bar_fill": "#00ff41", "bar_bg": "#07551a", "bar_border": "#9affb3", "bar_width": 80, "bar_height": 5, "bar_baseline": 1, "bar_marker": 1,
    },
    "Zombie": {
        "window": "#1b2118", "panel": "#252c20", "text": "#d4d8b8",
        "menu": "#20271c", "menu_text": "#d4d8b8", "menu_hover": "#46533a",
        "accent": "#9aa66a", "accent_text": "#10140e", "border": "#69764c",
        "bar_fill": "#d0d65a", "bar_bg": "#596044", "bar_border": "#d9dcad", "bar_width": 80, "bar_height": 5, "bar_baseline": 1, "bar_marker": 1,
    },
    "Pink Pussycat": {
        "window": "#ff1493", "panel": "#ff69b4", "text": "#240018",
        "menu": "#ff00a8", "menu_text": "#fff0fa", "menu_hover": "#7d00ff",
        "accent": "#00ffea", "accent_text": "#210019", "border": "#7d00ff",
        "bar_fill": "#39ff14", "bar_bg": "#5a0050", "bar_border": "#ffea00", "bar_width": 80, "bar_height": 5, "bar_baseline": 1, "bar_marker": 1,
    },
    "Barbie": {
        "window": "#ff66b3", "panel": "#ffb6d9", "text": "#3b0028",
        "menu": "#ff1493", "menu_text": "#fff7fc", "menu_hover": "#00d9ff",
        "accent": "#00d9ff", "accent_text": "#25001a", "border": "#ff00a8",
        "bar_fill": "#7d00ff", "bar_bg": "#ffd1e8", "bar_border": "#39ff14", "bar_width": 80, "bar_height": 5, "bar_baseline": 1, "bar_marker": 1,
    },
}

def palette_stylesheet(name):
    c=PALETTES.get(name, PALETTES["Normal"])
    return f"""
    QWidget {{ background:{c["window"]}; color:{c["text"]}; }}
    QDialog, QMainWindow {{ background:{c["window"]}; color:{c["text"]}; }}
    QGroupBox {{ border:1px solid {c["border"]}; margin-top:10px; padding-top:8px; }}
    QGroupBox::title {{ color:{c["accent"]}; subcontrol-origin:margin; left:8px; padding:0 3px; }}
    QPushButton, QComboBox, QSpinBox {{
        background:{c["panel"]}; color:{c["text"]}; border:1px solid {c["border"]}; padding:4px 7px;
    }}
    QPushButton:hover, QComboBox:hover {{ background:{c["menu_hover"]}; }}
    QComboBox QAbstractItemView {{
        background:{c["menu"]}; color:{c["menu_text"]};
        selection-background-color:{c["menu_hover"]}; selection-color:{c["menu_text"]};
    }}
    QTextBrowser {{ background:{c["panel"]}; color:{c["text"]}; border:1px solid {c["border"]}; }}
    QCheckBox {{ color:{c["text"]}; }}
    QMenu {{ background:{c["menu"]}; color:{c["menu_text"]}; border:1px solid {c["border"]}; padding:4px; }}
    QMenu::item {{ padding:6px 22px 6px 8px; }}
    QMenu::item:selected {{ background:{c["menu_hover"]}; color:{c["menu_text"]}; }}
    QMenu::separator {{ height:1px; background:{c["border"]}; margin:4px 6px; }}
    """


SIGNAL_DESCRIPTIONS = {
    "SIGHUP": ("Hangup", "Terminál- vagy kapcsolatmegszakadást jelez. Egyes programok konfiguráció újratöltésére használják."),
    "SIGINT": ("Interrupt", "Megszakítási kérés. Jellemzően a Ctrl+C hatásával egyezik meg."),
    "SIGQUIT": ("Quit", "Megszakítja a folyamatot, és alapértelmezésben core dump is készülhet."),
    "SIGILL": ("Illegal instruction", "Érvénytelen gépi utasítás miatt bekövetkező kivétel."),
    "SIGTRAP": ("Trace/breakpoint trap", "Hibakeresési trap vagy breakpoint jelzés."),
    "SIGABRT": ("Abort", "A folyamat megszakítására szolgáló abort jel."),
    "SIGBUS": ("Bus error", "Érvénytelen memória- vagy buszelérés jelzése."),
    "SIGFPE": ("Floating point exception", "Aritmetikai kivétel jelzése."),
    "SIGKILL": ("Kill", "Azonnali kényszerített leállítás. Nem fogható el, nem blokkolható és nem ignorálható."),
    "SIGUSR1": ("User-defined signal 1", "A program által saját célra felhasználható jel."),
    "SIGSEGV": ("Segmentation violation", "Érvénytelen memória-hozzáférés jelzése."),
    "SIGUSR2": ("User-defined signal 2", "A program által saját célra felhasználható jel."),
    "SIGPIPE": ("Broken pipe", "Lezárt pipe vagy socket felé történő írás jelzése."),
    "SIGALRM": ("Alarm clock", "Időzítő lejártát jelzi."),
    "SIGTERM": ("Terminate", "Kulturált leállítási kérés. Normál folyamatleállításhoz általában ez az első választás."),
    "SIGSTKFLT": ("Stack fault", "Linuxon elérhető, régebbi stack fault jelzés."),
    "SIGCHLD": ("Child status changed", "A gyermekfolyamat állapotváltozását jelzi a szülőnek."),
    "SIGCONT": ("Continue", "STOP-pal felfüggesztett folyamat folytatása."),
    "SIGSTOP": ("Stop", "Azonnal felfüggeszti a folyamatot. Nem fogható el és nem blokkolható."),
    "SIGTSTP": ("Terminal stop", "Terminálból indított felfüggesztés, jellemzően Ctrl+Z."),
    "SIGTTIN": ("Background terminal input", "Háttérfolyamat tiltott terminálbemenetet próbál olvasni."),
    "SIGTTOU": ("Background terminal output", "Háttérfolyamat tiltott terminálműveletet próbál végrehajtani."),
    "SIGURG": ("Urgent condition", "Sürgős socket-adat jelzése."),
    "SIGXCPU": ("CPU time limit", "A folyamat CPU-időkorlátjának elérését jelzi."),
    "SIGXFSZ": ("File size limit", "A fájlméret-korlát elérését jelzi."),
    "SIGVTALRM": ("Virtual timer", "Virtuális időzítő lejártát jelzi."),
    "SIGPROF": ("Profiling timer", "Profilozási időzítő jelzése."),
    "SIGWINCH": ("Window changed", "Terminálablak méretének megváltozását jelzi."),
    "SIGIO": ("I/O possible", "Aszinkron I/O esemény jelzése."),
    "SIGPWR": ("Power failure", "Linux-specifikus tápellátási eseményjelzés."),
    "SIGSYS": ("Bad system call", "Hibás vagy nem támogatott rendszerhívás jelzése."),
}


def available_signals():
    result = []
    for name in sorted(SIGNAL_DESCRIPTIONS, key=lambda n: int(getattr(signal, n, 999))):
        sig = getattr(signal, name, None)
        if sig is not None:
            title, description = SIGNAL_DESCRIPTIONS[name]
            result.append((name, int(sig), title, description))
    return result


SIGNALS = available_signals()


# ---------------------------------------------------------------------------
# Folyamat / ablak adatok
# ---------------------------------------------------------------------------

@dataclass
class AppInfo:
    pid: int
    window_id: str
    title: str
    executable: str
    command: str
    user: str
    cpu: float = 0.0
    state: str = ""


@dataclass
class ThreadInfo:
    pid: int
    tid: int
    name: str
    cpu: float = 0.0
    state: str = ""
    priority: str = ""
    nice: str = ""
    processor: str = ""


def list_threads(pid):
    """A PID thread groupjához tartozó Linux taskok listája."""
    result = []
    task_dir = f"/proc/{pid}/task"
    try:
        tids = sorted(int(x) for x in os.listdir(task_dir) if x.isdigit())
    except (OSError, ValueError):
        return result

    for tid in tids:
        try:
            with open(f"{task_dir}/{tid}/stat", "r", encoding="ascii") as f:
                raw = f.read()
            close = raw.rfind(")")
            head = raw[:close + 1]
            comm = head[head.find("(") + 1:-1] if "(" in head else str(tid)
            fields = raw[close + 2:].split()
            state = fields[0] if len(fields) > 0 else ""
            priority = fields[15] if len(fields) > 15 else ""
            nice = fields[16] if len(fields) > 16 else ""
            processor = fields[36] if len(fields) > 36 else ""
            result.append(ThreadInfo(pid, tid, comm or str(tid), 0.0, state, priority, nice, processor))
        except (OSError, ValueError, IndexError):
            continue
    return result


def read_thread_cpu(pid, tid):
    try:
        with open(f"/proc/{pid}/task/{tid}/stat", "r", encoding="ascii") as f:
            data = f.read()
        close = data.rfind(")")
        fields = data[close + 2:].split()
        utime = int(fields[11])
        stime = int(fields[12])
        total = utime + stime
        with open("/proc/uptime", "r", encoding="ascii") as f:
            uptime = float(f.read().split()[0])
        clk = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        return total / clk, uptime
    except (OSError, ValueError, IndexError, KeyError):
        return None


class ThreadSampler:
    def __init__(self):
        self.previous = {}

    def sample(self, threads):
        now = {}
        for thread in threads:
            sample = read_thread_cpu(thread.pid, thread.tid)
            if sample is None:
                thread.cpu = 0.0
                continue
            seconds, uptime = sample
            now[thread.tid] = (seconds, uptime)
            old = self.previous.get(thread.tid)
            if old is not None:
                dp = seconds - old[0]
                dt = uptime - old[1]
                if dt > 0:
                    thread.cpu = max(0.0, min(999.9, 100.0 * dp / dt))
        self.previous = now


def run_cmd(args, timeout=1.5):
    try:
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError as e:
        return 127, "", str(e)
    except subprocess.TimeoutExpired:
        return 124, "", "Időtúllépés"


def xprop_value(window_id, property_name):
    rc, out, _ = run_cmd(["xprop", "-id", window_id, property_name])
    if rc != 0 or "=" not in out:
        return ""
    value = out.split("=", 1)[1].strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value.replace('\\"', '"')


def list_visible_windows():
    """
    xdotoollal csak látható X11 ablakokat kérünk.
    A PID szerint deduplikálunk, ezért egy alkalmazás több ablaka
    nem jelenik meg külön folyamatként.
    """
    rc, out, _ = run_cmd(["xdotool", "search", "--onlyvisible", "--name", ""])
    if rc != 0:
        return []

    result = []
    seen_pids = set()

    for wid in out.splitlines():
        wid = wid.strip()
        if not wid:
            continue

        pid_text = xprop_value(wid, "_NET_WM_PID")
        try:
            pid = int(pid_text)
        except ValueError:
            continue

        if pid <= 1 or pid in seen_pids:
            continue

        title = xprop_value(wid, "_NET_WM_NAME")
        if not title:
            title = xprop_value(wid, "WM_NAME")

        # A saját segédablakait ne listázza.
        if pid == os.getpid():
            continue

        result.append(AppInfo(
            pid=pid,
            window_id=wid,
            title=title or "(névtelen ablak)",
            executable="",
            command="",
            user="",
        ))
        seen_pids.add(pid)

    return result


def list_all_processes():
    """Minden elérhető folyamatot egyetlen ps-hívással olvas be.

    Fontos teljesítményjavítás: a user, state, comm és args mezőket itt
    egyszerre kérjük le, így nem indítunk külön ps-folyamatot minden PID-hez.
    """
    rc, out, _ = run_cmd(
        ["ps", "-eo", "pid=,user=,stat=,comm=,args="], timeout=3.0
    )
    if rc != 0 or not out:
        return []

    result = []
    own_pid = os.getpid()
    for line in out.splitlines():
        # Az első négy mező különálló; a parancssor maradékát egyben tartjuk.
        parts = line.strip().split(None, 4)
        if len(parts) < 4:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        if pid <= 1 or pid == own_pid:
            continue
        user, state, comm = parts[1], parts[2], parts[3]
        command = parts[4] if len(parts) > 4 else comm
        result.append(AppInfo(
            pid=pid,
            window_id="",
            title=command or comm,
            executable=comm,
            command=command,
            user=user,
            state=state,
        ))
    return result


def fill_process_data(apps):
    for app in apps:
        rc, out, _ = run_cmd(
            ["ps", "-p", str(app.pid), "-o", "user=,stat=,comm=,args="],
            timeout=1.0,
        )
        if rc == 0 and out:
            parts = out.strip().split(None, 3)
            if len(parts) >= 1:
                app.user = parts[0]
            if len(parts) >= 2:
                app.state = parts[1]
            if len(parts) >= 3:
                app.executable = parts[2]
            if len(parts) >= 4:
                app.command = parts[3]


def read_proc_cpu(pid):
    """
    /proc/[pid]/stat alapján CPU-idő és a rendszer uptime.
    A tuple a következő mintavételhez használható.
    """
    try:
        with open(f"/proc/{pid}/stat", "r", encoding="ascii") as f:
            data = f.read()

        # comm mezőben szóköz és ')' is lehet, ezért az utolsó ')' után parse-olunk.
        close = data.rfind(")")
        fields = data[close + 2:].split()
        # fields[0] = state, utána ppid...
        # utime = eredeti 14. mező -> innen index 11
        # stime = eredeti 15. mező -> innen index 12
        utime = int(fields[11])
        stime = int(fields[12])
        total = utime + stime

        with open("/proc/uptime", "r", encoding="ascii") as f:
            uptime = float(f.read().split()[0])

        clk = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        return total / clk, uptime
    except (OSError, ValueError, IndexError, KeyError):
        return None


class CpuSampler:
    def __init__(self):
        self.previous = {}

    def sample(self, apps):
        now = {}
        for app in apps:
            sample = read_proc_cpu(app.pid)
            if sample is not None:
                proc_seconds, uptime = sample
                now[app.pid] = (proc_seconds, uptime)

                old = self.previous.get(app.pid)
                if old is not None:
                    dp = proc_seconds - old[0]
                    dt = uptime - old[1]
                    if dt > 0:
                        # 100% = egy teljes CPU-mag kihasználása.
                        app.cpu = max(0.0, min(999.9, 100.0 * dp / dt))
            else:
                app.cpu = 0.0

        self.previous = now


# ---------------------------------------------------------------------------
# Beállítások
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    """Témakörök szerint rendezett, füles beállítópanel."""
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("pkill.py – Beállítások")
        self.resize(690, 500)
        root = QVBoxLayout(self)
        tabs = QTabWidget(self)
        tabs.setTabPosition(QTabWidget.North)
        root.addWidget(tabs, 1)

        # 1. Általános: frissítés, listamód, megerősítések, téma
        general_page = QWidget()
        general_layout = QVBoxLayout(general_page)
        general_box = QGroupBox("Működés")
        form = QFormLayout(general_box)
        self.interval = QSpinBox()
        self.interval.setRange(1, 3600)
        self.interval.setSuffix(" másodperc")
        self.interval.setValue(int(settings.value("refresh_interval", 5)))
        form.addRow("Frissítési időköz:", self.interval)

        self.list_mode = QComboBox()
        self.list_mode.addItem("Összes folyamat (minden felhasználó)", "all")
        self.list_mode.addItem("Csak látható ablakok", "windows")
        mode = str(settings.value("list_mode", "all"))
        ix = self.list_mode.findData(mode)
        self.list_mode.setCurrentIndex(ix if ix >= 0 else 0)
        form.addRow("Listázási mód:", self.list_mode)

        self.confirm_kill = QCheckBox("SIGKILL (-9) előtt megerősítés")
        self.confirm_kill.setChecked(str(settings.value("confirm_kill", "true")).lower() == "true")
        form.addRow(self.confirm_kill)
        self.confirm_term = QCheckBox("Normál bezárás előtt megerősítés")
        self.confirm_term.setChecked(str(settings.value("confirm_normal_close", "false")).lower() == "true")
        form.addRow(self.confirm_term)
        general_layout.addWidget(general_box)

        theme_box = QGroupBox("Megjelenés")
        theme_form = QFormLayout(theme_box)
        self.palette = QComboBox()
        self.palette.addItems(PALETTES.keys())
        current_palette = settings.value("palette", "Normal")
        ix = self.palette.findText(current_palette)
        if ix >= 0:
            self.palette.setCurrentIndex(ix)
        self.palette.currentTextChanged.connect(self.apply_preset)
        theme_form.addRow("Színpaletta:", self.palette)
        info = QLabel("A választott paletta a folyamatlistára és a beállítóablakra is érvényes.")
        info.setWordWrap(True)
        theme_form.addRow(info)
        general_layout.addWidget(theme_box)
        general_layout.addStretch(1)
        tabs.addTab(general_page, "Általános")

        # 2. Felhasználók: külön, görgethető checkbox-lista
        users_page = QWidget()
        users_layout = QVBoxLayout(users_page)
        users_box = QGroupBox("Felhasználók a fő nézetben")
        users_box_layout = QVBoxLayout(users_box)
        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(180)
        users_content = QWidget()
        users_content_layout = QVBoxLayout(users_content)
        users_content_layout.setContentsMargins(4, 4, 4, 4)
        detected_users = self.detect_users()
        has_saved_users = settings.contains("selected_users")
        saved_users = settings.value("selected_users", "")
        if isinstance(saved_users, str):
            selected_users = {x for x in saved_users.split(";") if x}
        else:
            selected_users = set(saved_users or [])
        if not has_saved_users:
            selected_users = set(detected_users)
        self.user_checks = {}
        for username in detected_users:
            check = QCheckBox(username)
            check.setChecked(username in selected_users)
            self.user_checks[username] = check
            users_content_layout.addWidget(check)
        if not detected_users:
            users_content_layout.addWidget(QLabel("Nem sikerült felhasználókat lekérdezni."))
        users_content_layout.addStretch(1)
        scroll.setWidget(users_content)
        users_box_layout.addWidget(scroll)
        users_help = QLabel("A fő nézetben a kijelölt userek összesített CPU-terhelése látszik. Egy userre kattintva annak részletes folyamatai nyílnak meg.")
        users_help.setWordWrap(True)
        users_box_layout.addWidget(users_help)
        users_layout.addWidget(users_box)
        users_layout.addStretch(1)
        tabs.addTab(users_page, "Felhasználók")

        # 3. CPU-kijelzés és lista mérete
        cpu_page = QWidget()
        cpu_layout = QVBoxLayout(cpu_page)
        bar_box = QGroupBox("CPU-sávok")
        bar_form = QFormLayout(bar_box)
        preset = PALETTES.get(current_palette, PALETTES["Normal"])
        self.bar_visible = QCheckBox("CPU-sávok megjelenítése")
        visible_value = settings.value("bar_visible", True)
        if isinstance(visible_value, str):
            self.bar_visible.setChecked(visible_value.lower() not in ("false", "0", "no", "off"))
        else:
            self.bar_visible.setChecked(bool(visible_value))
        bar_form.addRow(self.bar_visible)
        self.bar_width = QSpinBox(); self.bar_width.setRange(20, 100); self.bar_width.setSuffix(" %")
        self.bar_width.setValue(int(settings.value("bar_width", preset["bar_width"])))
        bar_form.addRow("Sáv szélessége:", self.bar_width)
        self.bar_height = QSpinBox(); self.bar_height.setRange(2, 20); self.bar_height.setSuffix(" px")
        self.bar_height.setValue(int(settings.value("bar_height", preset["bar_height"])))
        bar_form.addRow("Aktív vonal vastagsága:", self.bar_height)
        self.bar_fill = QLineEdit(str(settings.value("bar_fill", preset["bar_fill"])))
        self.bar_fill.setPlaceholderText("például #d00000")
        bar_form.addRow("Aktív vonal színe:", self.bar_fill)
        self.bar_bg = QLineEdit(str(settings.value("bar_bg", preset["bar_bg"])))
        self.bar_bg.setPlaceholderText("például #180909")
        bar_form.addRow("Alapvonal színe:", self.bar_bg)
        self.bar_border = QLineEdit(str(settings.value("bar_border", preset["bar_border"])))
        self.bar_border.setPlaceholderText("például #b0b0b0")
        bar_form.addRow("100%-os jel színe:", self.bar_border)
        self.bar_baseline = QSpinBox(); self.bar_baseline.setRange(1, 5); self.bar_baseline.setSuffix(" px")
        self.bar_baseline.setValue(int(settings.value("bar_baseline", preset.get("bar_baseline", 1))))
        bar_form.addRow("Alapvonal vastagsága:", self.bar_baseline)
        self.bar_marker = QSpinBox(); self.bar_marker.setRange(1, 5); self.bar_marker.setSuffix(" px")
        self.bar_marker.setValue(int(settings.value("bar_marker", preset.get("bar_marker", 1))))
        bar_form.addRow("100%-os jel vastagsága:", self.bar_marker)
        cpu_layout.addWidget(bar_box)
        size_box = QGroupBox("Lenyíló folyamatlista")
        size_form = QFormLayout(size_box)
        self.menu_height_pct = QSpinBox(); self.menu_height_pct.setRange(20, 95); self.menu_height_pct.setSuffix(" %")
        self.menu_height_pct.setValue(int(settings.value("menu_height_pct", 80)))
        size_form.addRow("Maximális képernyőmagasság:", self.menu_height_pct)
        size_help = QLabel("A hosszú folyamatlista görgethető. A CPU-sáv 100%-os jele egyetlen CPU-mag teljes kihasználását jelenti; többmagos összesítés 100% fölé is kerülhet.")
        size_help.setWordWrap(True)
        size_form.addRow(size_help)
        cpu_layout.addWidget(size_box)
        cpu_layout.addStretch(1)
        tabs.addTab(cpu_page, "CPU és lista")

        # 4. Jelek
        signals_page = QWidget()
        signals_layout = QVBoxLayout(signals_page)
        browser = QTextBrowser()
        html = ["<h3>kill(2) jelek</h3>",
                "<p>A jel száma a <code>kill PID -SIGNAL</code> híváshoz tartozik.</p>",
                "<table border='1' cellspacing='0' cellpadding='4'>",
                "<tr><th>Jel</th><th>Szám</th><th>Megnevezés</th><th>Leírás</th></tr>"]
        for name, num, title, desc in SIGNALS:
            html.append(f"<tr><td><b>{name}</b></td><td>{num}</td><td>{title}</td><td>{desc}</td></tr>")
        html.append("</table>")
        browser.setHtml("".join(html))
        signals_layout.addWidget(browser)
        tabs.addTab(signals_page, "Jelek")

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Mégse")
        save = QPushButton("Mentés")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.save)
        buttons.addWidget(cancel); buttons.addWidget(save)
        root.addLayout(buttons)

    @staticmethod
    def detect_users():
        rc, out, _ = run_cmd(["ps", "-eo", "user="], timeout=3.0)
        if rc != 0:
            return []
        return sorted({line.strip() for line in out.splitlines() if line.strip()})

    def apply_preset(self, name):
        preset = PALETTES.get(name)
        if not preset:
            return
        self.bar_width.setValue(int(preset["bar_width"]))
        self.bar_height.setValue(int(preset["bar_height"]))
        self.bar_fill.setText(preset["bar_fill"])
        self.bar_bg.setText(preset["bar_bg"])
        self.bar_border.setText(preset["bar_border"])
        self.bar_baseline.setValue(int(preset.get("bar_baseline", 1)))
        self.bar_marker.setValue(int(preset.get("bar_marker", 1)))
        self.bar_visible.setChecked(True)

    def save(self):
        self.settings.setValue("refresh_interval", self.interval.value())
        self.settings.setValue("confirm_kill", self.confirm_kill.isChecked())
        self.settings.setValue("confirm_normal_close", self.confirm_term.isChecked())
        self.settings.setValue("list_mode", self.list_mode.currentData())
        selected_users = [name for name, check in self.user_checks.items() if check.isChecked()]
        self.settings.setValue("selected_users", ";".join(selected_users))
        self.settings.setValue("palette", self.palette.currentText())
        self.settings.setValue("bar_width", self.bar_width.value())
        self.settings.setValue("bar_height", self.bar_height.value())
        self.settings.setValue("bar_fill", self.bar_fill.text().strip())
        self.settings.setValue("bar_bg", self.bar_bg.text().strip())
        self.settings.setValue("bar_border", self.bar_border.text().strip())
        self.settings.setValue("bar_baseline", self.bar_baseline.value())
        self.settings.setValue("bar_marker", self.bar_marker.value())
        self.settings.setValue("bar_visible", self.bar_visible.isChecked())
        self.settings.setValue("menu_height_pct", self.menu_height_pct.value())
        self.settings.sync()
        self.accept()


# ---------------------------------------------------------------------------
# Folyamatkezelő
# ---------------------------------------------------------------------------

class ProcessController:
    def __init__(self, settings, parent):
        self.settings = settings
        # ProcessController nem QWidget. A PkillApp példányt nem szabad
        # QMessageBox parentjeként átadni, mert a Qt csak QWidget-et fogad el.
        # Ha később valódi QWidget parent érkezik, azt megtartjuk.
        self.parent = parent if isinstance(parent, QWidget) else None

    def normal_close(self, app):
        confirm = self.settings.value("confirm_normal_close", "false") == "true"
        if confirm:
            answer = QMessageBox.question(
                self.parent,
                "Normál bezárás",
                f"Bezárod ezt az ablakot?\n\n"
                f"{app.title}\nPID: {app.pid}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        # Ablak nélküli folyamatnál nincs WM_DELETE_WINDOW; SIGTERM a normál kérés.
        rc = 1
        err = ""
        if app.window_id:
            rc, _, err = run_cmd(["xdotool", "windowclose", app.window_id], timeout=2)
        if not app.window_id or rc != 0:
            try:
                os.kill(app.pid, signal.SIGTERM)
            except PermissionError:
                QMessageBox.critical(
                    self.parent,
                    "Nincs jogosultság",
                    f"Nem lehet SIGTERM jelet küldeni.\n\nPID: {app.pid}\n{err}",
                )
            except ProcessLookupError:
                pass

    def kill9(self, app):
        confirm = self.settings.value("confirm_kill", "true") == "true"
        if confirm:
            answer = QMessageBox.warning(
                self.parent,
                "KILL -9",
                f"Azonnal és kényszerítve leállítod ezt a folyamatot?\n\n"
                f"{app.title}\n"
                f"Program: {app.executable or '—'}\n"
                f"PID: {app.pid}\n\n"
                f"A SIGKILL (-9) nem ad lehetőséget a programnak a takarításra.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        try:
            os.kill(app.pid, signal.SIGKILL)
        except PermissionError:
            QMessageBox.critical(
                self.parent,
                "Nincs jogosultság",
                f"Nem lehet SIGKILL jelet küldeni.\n\n"
                f"PID: {app.pid}\n"
                f"Felhasználó: {app.user or 'ismeretlen'}",
            )
        except ProcessLookupError:
            pass

    def kill_thread(self, thread):
        # Linuxon a SIGKILL végzetes processzszintű jel. A TID-re célzott
        # küldés sem garantál különálló thread-életet. Ezt ezért mindig
        # egyértelműen közöljük a felhasználóval.
        answer = QMessageBox.warning(
            self.parent,
            "Szál KILL (-9)",
            f"SIGKILL (-9) küldése a következő TID-re:\n\n"
            f"{thread.name}\nTID: {thread.tid}\nPID: {thread.pid}\n\n"
            "Fontos: Linuxon a SIGKILL végzetes a teljes thread group számára. "
            "Ez nem biztonságos, izolált thread-leállítás.\n\n"
            "Folytatod?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            # glibc tgkill() valóban a megadott TID-re céloz. A SIGKILL
            # végzetes szemantikája miatt azonban a teljes processz megszűnhet.
            import ctypes
            libc = ctypes.CDLL(None, use_errno=True)
            if hasattr(libc, "tgkill"):
                libc.tgkill.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
                libc.tgkill.restype = ctypes.c_int
                rc = libc.tgkill(int(thread.pid), int(thread.tid), int(signal.SIGKILL))
                if rc != 0:
                    err = ctypes.get_errno()
                    raise OSError(err, os.strerror(err))
            else:
                os.kill(thread.tid, signal.SIGKILL)
        except PermissionError:
            QMessageBox.critical(self.parent, "Nincs jogosultság", f"TID: {thread.tid}\nPID: {thread.pid}")
        except ProcessLookupError:
            pass
        except OSError as e:
            QMessageBox.critical(self.parent, "Szál KILL hiba", str(e))

    def thread_details(self, thread):
        msg = QMessageBox(self.parent)
        msg.setWindowTitle("Szál adatai")
        msg.setText(
            f"Név: {thread.name}\n"
            f"TID: {thread.tid}\n"
            f"PID: {thread.pid}\n"
            f"CPU: {thread.cpu:.1f} %\n"
            f"Állapot: {thread.state or '—'}\n"
            f"Prioritás: {thread.priority or '—'}\n"
            f"Nice: {thread.nice or '—'}\n"
            f"Processzor: {thread.processor or '—'}"
        )
        msg.exec()

    def details(self, app):
        """Részletes, pillanatnyi X11 + Linux /proc/ps folyamatjelentés."""
        def ps_one(fmt):
            rc, out, err = run_cmd(["ps", "-p", str(app.pid), "-o", fmt], timeout=2.0)
            return out.strip() if rc == 0 else ""

        def proc_status():
            data = {}
            try:
                with open(f"/proc/{app.pid}/status", "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if ":" in line:
                            k, v = line.split(":", 1)
                            data[k.strip()] = v.strip()
            except OSError:
                pass
            return data

        def proc_link(name):
            try:
                return os.readlink(f"/proc/{app.pid}/{name}")
            except OSError as e:
                return f"— ({e})"

        def proc_cmdline():
            try:
                with open(f"/proc/{app.pid}/cmdline", "rb") as f:
                    raw = f.read().replace(b"\x00", b" ")
                return raw.decode("utf-8", "replace").strip()
            except OSError:
                return "—"

        def proc_stat_extra():
            """A /proc/PID/stat néhány, ps-ben nem kényelmesen látható mezője."""
            try:
                with open(f"/proc/{app.pid}/stat", "r", encoding="ascii") as f:
                    raw = f.read()
                close = raw.rfind(")")
                fields = raw[close + 2:].split()
                # fields[0] = state, fields[1] = ppid ...
                return {
                    "ppid": fields[1],
                    "pgrp": fields[2],
                    "session": fields[3],
                    "tty_nr": fields[4],
                    "tpgid": fields[5],
                    "priority": fields[15],
                    "nice": fields[16],
                    "num_threads": fields[17],
                    "starttime_ticks": fields[19],
                }
            except (OSError, ValueError, IndexError):
                return {}

        def boot_time():
            try:
                with open("/proc/stat", "r", encoding="ascii") as f:
                    for line in f:
                        if line.startswith("btime "):
                            return float(line.split()[1])
            except (OSError, ValueError, IndexError):
                pass
            return None

        def xprop_raw(prop):
            if not app.window_id:
                return "Nincs hozzá tartozó grafikus ablak"
            rc, out, err = run_cmd(["xprop", "-id", app.window_id, prop], timeout=1.5)
            if rc == 0 and out:
                return out.strip()
            return "—"

        status = proc_status()
        stat = proc_stat_extra()
        start_text = "—"
        if stat.get("starttime_ticks") and boot_time() is not None:
            try:
                clk = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
                start_epoch = boot_time() + int(stat["starttime_ticks"]) / clk
                start_text = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_epoch))
            except (ValueError, OSError, KeyError):
                pass

        ps_fields = (
            "user=,uid=,group=,gid=,euser=,egroup=,stat=,pid=,ppid=,pgid=,sid=,"
            "etime=,etimes=,lstart=,ni=,pri=,psr=,tty=,wchan=,rss=,vsz=,nlwp=,"
            "comm=,args="
        )
        ps_data = ps_one(ps_fields)
        if ps_data:
            # Az értékek szóközösek lehetnek, ezért a teljes nyers ps-sort is megőrizzük.
            pass

        parent_pid = stat.get("ppid", "")
        parent_info = "—"
        if parent_pid and parent_pid != "0":
            parent_info = ""
            rc, out, _ = run_cmd(
                ["ps", "-p", parent_pid, "-o", "pid=,user=,stat=,comm=,args="],
                timeout=1.5,
            )
            if rc == 0 and out:
                parent_info = out.strip()
        if not parent_info:
            parent_info = "—"

        # Linux erőforrás- és jogosultsági adatok.
        memory = {
            "VmPeak": status.get("VmPeak", "—"),
            "VmSize": status.get("VmSize", "—"),
            "VmRSS": status.get("VmRSS", "—"),
            "VmData": status.get("VmData", "—"),
            "VmStk": status.get("VmStk", "—"),
            "VmExe": status.get("VmExe", "—"),
            "VmLib": status.get("VmLib", "—"),
            "Threads": status.get("Threads", stat.get("num_threads", "—")),
        }

        # Affinitás és környezeti korlátozások külön /proc-ból.
        affinity = "—"
        try:
            affinity = ", ".join(str(x) for x in os.sched_getaffinity(app.pid))
        except (AttributeError, OSError):
            pass

        groups = status.get("Groups", "—")
        cap_eff = status.get("CapEff", "—")
        seccomp = status.get("Seccomp", "—")

        report = f"""FOLYAMAT ADATAI
{'=' * 72}

[ABLAK]
Ablakcím:             {app.title or '—'}
Window ID:            {app.window_id}
WM_CLASS:             {xprop_raw('WM_CLASS')}
Window type:          {xprop_raw('_NET_WM_WINDOW_TYPE')}
Window state:         {xprop_raw('_NET_WM_STATE')}
Desktop:              {xprop_raw('_NET_WM_DESKTOP')}

[FOLYAMAT]
PID:                  {app.pid}
PPID:                 {parent_pid or '—'}
Szülőfolyamat:        {parent_info}
Program:              {app.executable or '—'}
Parancssor (ps):      {app.command or '—'}
Parancssor (/proc):   {proc_cmdline()}
Végrehajtható fájl:   {proc_link('exe')}
Munkakönyvtár:        {proc_link('cwd')}
Root könyvtár:        {proc_link('root')}

[AZONOSÍTÁS / ÁLLAPOT]
Felhasználó:          {app.user or '—'}
UID:                  {status.get('Uid', '—')}
GID:                  {status.get('Gid', '—')}
Csoportok:            {groups}
Állapot:              {app.state or status.get('State', '—')}
Threads:              {memory['Threads']}
Szálcsoport:          {status.get('NSpid', '—')}
Seccomp:              {seccomp}
CapEff:               {cap_eff}

[IDŐZÍTÉS / ÜTEMEZÉS]
Indulás ideje:        {start_text}
Eltelt idő (ps):      {ps_one('etimes=') or '—'} másodperc
Nice:                 {ps_one('ni=') or stat.get('nice', '—')}
Priority:             {ps_one('pri=') or stat.get('priority', '—')}
CPU:                  {app.cpu:.1f} %
CPU-mag:              {ps_one('psr=') or '—'}
CPU-affinitás:        {affinity}

[MEMÓRIA]
VmPeak:               {memory['VmPeak']}
VmSize:               {memory['VmSize']}
VmRSS:                {memory['VmRSS']}
VmData:               {memory['VmData']}
VmStk:                {memory['VmStk']}
VmExe:                {memory['VmExe']}
VmLib:                {memory['VmLib']}

[TERMINÁL / KERNEL]
TTY:                  {ps_one('tty=') or '—'}
WCHAN:                {ps_one('wchan=') or '—'}
Process state:        {status.get('State', '—')}

[NYERS X11 ADATOK]
WM_CLASS:             {xprop_raw('WM_CLASS')}
_NET_WM_PID:          {xprop_raw('_NET_WM_PID')}
_NET_WM_NAME:         {xprop_raw('_NET_WM_NAME')}
WM_NAME:              {xprop_raw('WM_NAME')}
_NET_WM_DESKTOP:      {xprop_raw('_NET_WM_DESKTOP')}
_NET_WM_WINDOW_TYPE:  {xprop_raw('_NET_WM_WINDOW_TYPE')}
_NET_WM_STATE:        {xprop_raw('_NET_WM_STATE')}

[PS TELJES SOR]
{ps_data or '—'}
"""

        dialog = QDialog(self.parent)
        dialog.setWindowTitle(f"Folyamat adatai — {app.title or app.executable}")
        dialog.resize(900, 720)

        layout = QVBoxLayout(dialog)
        header = QLabel(
            f"<b>{app.title or '(névtelen ablak)'}</b><br>"
            f"PID: {app.pid} &nbsp;&nbsp; Window ID: {app.window_id}"
        )
        header.setTextFormat(Qt.RichText)
        layout.addWidget(header)

        # Felső füles nézet. Az utolsó fül szándékosan a régi, teljes TXT
        # jelentés, hogy az eddigi kimenet változatlanul egyben is elérhető legyen.
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.North)

        def report_section(start, end=None):
            marker = start
            pos = report.find(marker)
            if pos < 0:
                return ""
            pos += len(marker)
            if end is None:
                return report[pos:].strip()
            endpos = report.find(end, pos)
            if endpos < 0:
                return report[pos:].strip()
            return report[pos:endpos].strip()

        def add_text_tab(title, text):
            view = QTextBrowser()
            view.setLineWrapMode(QTextBrowser.NoWrap)
            view.setPlainText(text.strip())
            tabs.addTab(view, title)

        add_text_tab(
            "Áttekintés",
            "\n\n".join([
                report_section("[ABLAK]", "[FOLYAMAT]"),
                report_section("[FOLYAMAT]", "[AZONOSÍTÁS / ÁLLAPOT]"),
                report_section("[IDŐZÍTÉS / ÜTEMEZÉS]", "[MEMÓRIA]"),
            ]),
        )
        add_text_tab("Ablak", report_section("[ABLAK]", "[FOLYAMAT]"))
        add_text_tab(
            "Folyamat",
            report_section("[FOLYAMAT]", "[AZONOSÍTÁS / ÁLLAPOT]")
            + "\n\n"
            + report_section("[AZONOSÍTÁS / ÁLLAPOT]", "[IDŐZÍTÉS / ÜTEMEZÉS]"),
        )
        add_text_tab(
            "Erőforrások",
            report_section("[IDŐZÍTÉS / ÜTEMEZÉS]", "[MEMÓRIA]")
            + "\n\n"
            + report_section("[MEMÓRIA]", "[TERMINÁL / KERNEL]"),
        )
        add_text_tab(
            "X11 / Kernel",
            report_section("[TERMINÁL / KERNEL]", "[NYERS X11 ADATOK]")
            + "\n\n"
            + report_section("[NYERS X11 ADATOK]", "[PS TELJES SOR]"),
        )

        full_view = QTextBrowser()
        full_view.setLineWrapMode(QTextBrowser.NoWrap)
        full_view.setPlainText(report)
        tabs.addTab(full_view, "Teljes TXT")

        layout.addWidget(tabs, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        copy_btn = QPushButton("Másolás")
        close_btn = QPushButton("Bezárás")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(report))
        close_btn.clicked.connect(dialog.accept)
        buttons.addWidget(copy_btn)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        dialog.exec()


# ---------------------------------------------------------------------------
# Tálca / lenyíló menü
# ---------------------------------------------------------------------------

class CpuBarWidget(QWidget):
    """BeOS-szerű, tolópotméter-jellegű CPU-szintjelző."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.width_pct = 80
        self.active_height = 5
        self.baseline_height = 1
        self.marker_width = 1
        self.value = 0.0
        self.fill = "#c00000"
        self.baseline = "#666666"
        self.marker = "#b0b0b0"
        self.overload = "#ff3030"
        self.setMinimumWidth(260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setMinimumHeight(12)
        self.setMaximumHeight(24)

    def configure(self, width_pct, active_height, fill, baseline, marker, baseline_height=1, marker_width=1):
        self.width_pct = max(20, min(100, int(width_pct)))
        self.active_height = max(2, min(20, int(active_height)))
        self.baseline_height = max(1, min(5, int(baseline_height)))
        self.marker_width = max(1, min(5, int(marker_width)))
        self.fill = fill
        self.baseline = baseline
        self.marker = marker
        self.setFixedHeight(max(8, self.active_height + 4))
        self.update()

    def set_value(self, value):
        self.value = max(0.0, float(value))
        self.setToolTip(f"CPU-terhelés: {self.value:.1f} %")
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPen, QColor
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        margins = 8
        usable = max(40, self.width() - 2 * margins)
        scale_width = max(20, int(usable * self.width_pct / 100.0))
        x0 = margins
        x100 = x0 + scale_width - 1
        cy = max(1, self.active_height // 2 + 1)

        # A teljes 0–100% skála csak egy hajszálvékony alapvonal.
        p.setPen(QPen(QColor(self.baseline), float(self.baseline_height)))
        p.drawLine(x0, cy, x100, cy)

        # Az aktuális érték vastagabb "tolópotméter"-szakasz.
        active_end = x0 + int(scale_width * min(self.value, 100.0) / 100.0)
        p.setPen(QPen(QColor(self.overload if self.value > 100.0 else self.fill), float(self.active_height)))
        p.drawLine(x0, cy, max(x0, active_end), cy)

        # 100%-os referenciajel, mindig látható.
        p.setPen(QPen(QColor(self.marker), float(self.marker_width)))
        p.drawLine(x100, max(1, cy - self.active_height // 2 - 2),
                   x100, min(self.height() - 2, cy + self.active_height // 2 + 2))
        p.end()

class UserSummaryRow(QWidget):
    """Kattintható felhasználói összesítő CPU-sávval."""
    def __init__(self, controller, username, cpu, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.username = username
        self.setMinimumHeight(32)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)
        self.arrow = QLabel("▶")
        self.arrow.setFixedWidth(12)
        self.label = QLabel(username)
        self.label.setMinimumWidth(90)
        self.label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.bar = CpuBarWidget(self)
        self.bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.count = QLabel("0 folyamat")
        self.count.setMinimumWidth(72)
        self.count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cpu = QLabel(f"{cpu:.1f} %")
        self.cpu.setFixedWidth(68)
        self.cpu.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        for w in (self.arrow, self.label, self.bar, self.count, self.cpu):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.arrow)
        layout.addWidget(self.label)
        layout.addWidget(self.bar, 1)
        layout.addWidget(self.count)
        layout.addWidget(self.cpu)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"{username} összesített CPU-terhelése. Kattintás: folyamatlista megnyitása.")

    def configure_bar(self, config):
        width_pct, height, fill, baseline, marker, baseline_height, marker_width = config
        self.bar.configure(100, height, fill, baseline, marker, baseline_height, marker_width)
        self.bar.set_value(self._cpu_value)
        self.bar.setVisible(self.controller._bar_visible())

    def update_value(self, cpu, count=None):
        self._cpu_value = cpu
        self.cpu.setText(f"{cpu:.1f} %")
        if count is not None:
            self.count.setText(f"{count} folyamat")
        self.bar.set_value(cpu)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.controller.open_user(self.username)
            event.accept()
            return
        super().mousePressEvent(event)


class ProcessRowWidget(QWidget):
    """Egyetlen BeOS/Haiku-szerű processzsor, jobbra zárt CPU-sávval."""
    def __init__(self, controller, app, expanded=False, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.app_info = app
        self.expanded = expanded
        self.bar_width_pct = 70
        self.setMinimumHeight(30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 1, 4, 1)
        lay.setSpacing(6)

        self.arrow = QLabel("▼" if expanded else "▶")
        self.arrow.setFixedWidth(12)

        self.name = QLabel()
        self.name.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # A stretch a sáv ELŐTT van: így a sáv mindig jobbra, közvetlenül
        # a CPU-százalék mellé kerül.
        self.bar = CpuBarWidget(self)
        self.bar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.cpu = QLabel()
        self.cpu.setFixedWidth(62)
        self.cpu.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.action_button = QPushButton("⋮")
        self.action_button.setToolTip("Folyamat műveletei")
        self.action_button.setFixedSize(22, 24)
        self.action_button.setFlat(True)
        self.action_button.setCursor(Qt.PointingHandCursor)
        self.action_button.setFocusPolicy(Qt.NoFocus)
        self.action_button.clicked.connect(self._show_context)
        self.action_button.setStyleSheet(
            "QPushButton { border: 0; padding: 0; margin: 0; font-weight: bold; }"
            "QPushButton:hover { background: rgba(180, 0, 0, 70); }"
            "QPushButton:pressed { background: rgba(180, 0, 0, 130); }"
        )

        for widget in (self.arrow, self.name, self.bar, self.cpu):
            widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        lay.addWidget(self.arrow)
        lay.addWidget(self.name)
        lay.addStretch(1)
        lay.addWidget(self.bar)
        lay.addWidget(self.cpu)
        lay.addWidget(self.action_button)

        self.update_app(app, expanded)

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(max(30, hint.height()))
        return hint

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_bar()

    def _resize_bar(self):
        # A sáv szélessége a teljes processzsor rendelkezésre álló helyének
        # beállított százaléka. A sáv widget maga jobbra van zárva.
        total = self.width()
        fixed = (
            self.layout().contentsMargins().left()
            + self.layout().contentsMargins().right()
            + self.arrow.width()
            + self.name.sizeHint().width()
            + self.cpu.width()
            + self.action_button.width()
            + self.layout().spacing() * 5
        )
        available = max(80, total - fixed)
        width = max(60, int(available * self.bar_width_pct / 100.0))
        self.bar.setFixedWidth(width)

    def _show_context(self):
        self.controller.show_process_context(self.app_info, QCursor.pos())

    def configure_bar(self, config):
        width_pct, height, fill, baseline, marker, baseline_height, marker_width = config
        self.bar_width_pct = max(20, min(100, int(width_pct)))
        # A widget teljes szélessége a beállítás szerinti, ezért a rajz
        # ezen belül 0–100%-ig fusson.
        self.bar.configure(100, height, fill, baseline, marker,
                           baseline_height, marker_width)
        self.bar.set_value(self.app_info.cpu)
        self.bar.setVisible(self.controller._bar_visible())
        self._resize_bar()

    def update_app(self, app, expanded=None):
        self.app_info = app
        if expanded is not None:
            self.expanded = expanded
        self.arrow.setText("▼" if self.expanded else "▶")
        name = app.executable or app.title or "?"
        if not app.window_id and app.user:
            name = f"{name} [{app.user}]"
        self.name.setText(name)
        self.cpu.setText(f"{app.cpu:.1f} %")
        self.bar.set_value(app.cpu)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.controller.toggle_threads(self.app_info.pid)
            event.accept()
            return
        super().mousePressEvent(event)


class ThreadRowWidget(QWidget):
    """Egy processzhez tartozó Linux thread vizuális sora."""
    def __init__(self, controller, thread, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.thread = thread
        self.setMinimumHeight(23)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(30, 1, 6, 1)
        lay.setSpacing(6)
        self.branch = QLabel("├─")
        self.branch.setFixedWidth(20)
        self.name = QLabel()
        self.name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cpu = QLabel()
        self.cpu.setMinimumWidth(76)
        self.cpu.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        for widget in (self.branch, self.name, self.cpu):
            widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(self.branch)
        lay.addWidget(self.name)
        lay.addWidget(self.cpu)
        self.update_thread(thread)

    def update_thread(self, thread):
        self.thread = thread
        self.name.setText(f"{thread.name}  [TID {thread.tid}]")
        self.cpu.setText(f"{thread.cpu:.1f} % CPU")
        self.setToolTip(
            f"{thread.name}\nTID: {thread.tid}\n"
            f"Állapot: {thread.state or '—'}\n"
            f"Prioritás: {thread.priority or '—'}  Nice: {thread.nice or '—'}\n"
            f"CPU: {thread.cpu:.1f} %\n\n"
            f"Megjegyzés: Linuxon a SIGKILL egy threadre küldve is a teljes thread groupot megszüntetheti."
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.controller.show_thread_context(
                self.thread,
                self.mapToGlobal(event.position().toPoint())
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self.controller.show_thread_context(
            self.thread,
            event.globalPos()
        )
        event.accept()


class PkillApp:
    def __init__(self, app):
        self.app = app
        self.settings = QSettings(ORG_NAME, APP_NAME)
        self.sampler = CpuSampler()
        self.thread_sampler = ThreadSampler()
        self.controller = ProcessController(self.settings, self)
        self.expanded_pids = set()
        self.process_rows = {}
        self.thread_rows = {}
        self.user_summary_rows = {}
        self.current_user = None
        self._menu_anchor = None

        self.menu = QMenu()
        self.menu.setStyleSheet(
            palette_stylesheet(self.settings.value("palette", "Normal"))
        )
        self.apply_palette()
        self.menu.aboutToShow.connect(self.menu_opened)
        self.menu.aboutToHide.connect(self.menu_closed)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_menu)

        self.last_apps = []

        self.tray = QSystemTrayIcon(self.make_icon(), app)
        self.tray.setToolTip("pkill.py")
        self.tray.setContextMenu(self.make_context_menu())
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()

    def apply_palette(self):
        sheet = palette_stylesheet(self.settings.value("palette", "Normal"))
        self.app.setStyleSheet(sheet)
        if hasattr(self, "menu"):
            self.menu.setStyleSheet(sheet)
            for action in self.menu.actions():
                if action.property("pkill_role") == "process_row":
                    row = action.property("pkill_process_row")
                    if row is not None:
                        row.configure_bar(self._bar_config())

    def make_icon(self):
        # Egyszerű, saját ikon, külső PNG nélkül.
        pix = QPixmap(32, 32)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setPen(Qt.black)
        painter.setBrush(Qt.black)
        painter.drawEllipse(4, 4, 24, 24)
        painter.setBrush(Qt.white)
        painter.drawRect(9, 9, 14, 14)
        painter.end()
        return QIcon(pix)

    def make_context_menu(self):
        menu = QMenu()

        settings_action = QAction("Beállítások", menu)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        help_action = QAction("Leírás", menu)
        help_action.triggered.connect(self.show_help)
        menu.addAction(help_action)

        menu.addSeparator()

        quit_action = QAction("Kilépés", menu)
        quit_action.triggered.connect(self.app.quit)
        menu.addAction(quit_action)

        return menu

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_process_menu()

    def _menu_anchor_pos(self):
        """A QMenu-t mindig a tálcaikonhoz rögzíti, nem az aktuális kurzorhoz."""
        rect = self.tray.geometry()
        if not rect.isNull() and rect.isValid():
            screen = QApplication.screenAt(rect.center()) or QApplication.primaryScreen()
            if screen is not None:
                area = screen.availableGeometry()
                # Felső panel/tálca esetén az ikon alá, alsó panel esetén fölé
                # adjuk át a pontot. A QMenu a saját képernyőhatár-kezelésével
                # innen pozicionálja a teljes menüt.
                if rect.center().y() <= area.center().y():
                    return QPoint(rect.left(), rect.bottom())
                return QPoint(rect.left(), rect.top())
        # Tartalék: ha a WM nem ad értelmes tray-geometriát.
        return QCursor.pos()

    def show_process_menu(self):
        self.refresh_menu()

        anchor = self._menu_anchor_pos()
        self._menu_anchor = QPoint(anchor)
        screen = QApplication.screenAt(anchor) or QApplication.primaryScreen()
        if screen is not None:
            try:
                pct = int(self.settings.value("menu_height_pct", 80))
            except (TypeError, ValueError):
                pct = 80
            pct = max(20, min(95, pct))
            available = screen.availableGeometry()
            self.menu.setMaximumHeight(
                max(120, int(available.height() * pct / 100.0))
            )

        self.menu.exec(anchor)


    def menu_opened(self):
        interval = int(self.settings.value("refresh_interval", 5))
        self.refresh_timer.start(interval * 1000)

    def menu_closed(self):
        self.refresh_timer.stop()

    def refresh_menu(self):
        mode = str(self.settings.value("list_mode", "all"))
        if mode == "windows":
            apps = list_visible_windows()
            # Ablakos módban kevés PID van, itt maradhat a kiegészítő lekérdezés.
            fill_process_data(apps)
        else:
            # Az összes folyamat mód már egyetlen ps-hívással kitölti az adatokat.
            apps = list_all_processes()
        self.sampler.sample(apps)
        # A részletes listában a nagyobb CPU-terhelésű folyamatok kerüljenek előre.
        # Az első mintavétel után a CPU még 0 lehet, a következő frissítéstől pontosodik.
        apps.sort(key=lambda x: (-x.cpu, (x.executable or x.title).lower()))
        old_apps = {app.pid: app for app in self.last_apps}
        new_apps = {app.pid: app for app in apps}
        self.last_apps = apps
        # A timer tick should update labels/bars, not destroy and recreate the
        # entire QMenu. Rebuild only when the visible structure actually changes.
        if self._update_menu_rows_in_place(apps, old_apps, new_apps):
            return
        self.rebuild_menu(apps)

    def _update_menu_rows_in_place(self, apps, old_apps, new_apps):
        if not self.menu.actions():
            return False
        if self.current_user is not None:
            selected = [a for a in apps if a.user == self.current_user]
            # Csak az éppen megnyitott user látható folyamatait figyeljük.
            # Más userek háttérfolyamatainak indulása/leállása ne villantsa újra a menüt.
            if set(self.process_rows) != {a.pid for a in selected}:
                return False
            for app in selected:
                action = self.process_rows.get(app.pid)
                row = action.property("pkill_process_row") if action else None
                if row is None:
                    return False
                row.update_app(app, app.pid in self.expanded_pids)
            self.refresh_expanded_threads()
            return True
        selected_users = str(self.settings.value("selected_users", ""))
        allowed = {x for x in selected_users.split(";") if x}
        by_user = {}
        for app in apps:
            by_user.setdefault(app.user or "?", []).append(app)
        users = {u for u in by_user if (u in allowed if self.settings.contains("selected_users") else True)}
        if users != set(self.user_summary_rows):
            return False
        for username, row in self.user_summary_rows.items():
            total = sum(max(0.0, a.cpu) for a in by_user.get(username, []))
            row.update_value(total, len(by_user.get(username, [])))
            row.setToolTip(f"{username}: {len(by_user.get(username, []))} folyamat; összesített CPU: {total:.1f} %. Kattintás: részletek.")
        return True

    def rebuild_menu(self, apps):
        self.menu.clear()
        self.process_rows = {}
        self.thread_rows = {}
        self.user_summary_rows = {}

        if self.current_user is not None:
            back = QPushButton("← Felhasználók")
            back.setCursor(Qt.PointingHandCursor)
            back.clicked.connect(self.close_user)
            action = QWidgetAction(self.menu)
            action.setDefaultWidget(back)
            self.menu.addAction(action)
            self.menu.addSeparator()
            selected = [app for app in apps if app.user == self.current_user]
            title = QAction(f"{self.current_user} — {len(selected)} folyamat", self.menu)
            title.setEnabled(False)
            self.menu.addAction(title)
            if not selected:
                empty = QAction("Nincs megjeleníthető folyamat", self.menu)
                empty.setEnabled(False)
                self.menu.addAction(empty)
            for app in selected:
                self.add_process_row(app)
            return

        selected_users = str(self.settings.value("selected_users", ""))
        allowed = {x for x in selected_users.split(";") if x}
        has_saved_users = self.settings.contains("selected_users")
        by_user = {}
        for app in apps:
            by_user.setdefault(app.user or "?", []).append(app)
        # Ha nincs beállított lista (régi beállítás vagy első indítás), minden user látszik.
        users = sorted(user for user in by_user if (user in allowed if has_saved_users else True))
        if not users:
            empty = QAction("Nincs kiválasztott vagy elérhető felhasználó", self.menu)
            empty.setEnabled(False)
            self.menu.addAction(empty)
            return
        # A terheltebb felhasználó jelenjen meg előbb.
        users.sort(key=lambda username: -sum(max(0.0, app.cpu) for app in by_user[username]))
        for username in users:
            user_apps = by_user[username]
            total_cpu = sum(max(0.0, app.cpu) for app in user_apps)
            row = UserSummaryRow(self, username, total_cpu, self.menu)
            row._cpu_value = total_cpu
            row.update_value(total_cpu, len(user_apps))
            row.configure_bar(self._bar_config())
            action = QWidgetAction(self.menu)
            action.setDefaultWidget(row)
            action.setProperty("pkill_role", "user_summary")
            self.menu.addAction(action)
            self.user_summary_rows[username] = row

    def open_user(self, username):
        self.current_user = username
        self.expanded_pids.clear()
        self.rebuild_menu(self.last_apps)
        self._resize_open_menu()

    def close_user(self):
        self.current_user = None
        self.expanded_pids.clear()
        self.rebuild_menu(self.last_apps)
        self._resize_open_menu()

    def _resize_open_menu(self):
        anchor = QPoint(self._menu_anchor) if self._menu_anchor is not None else self._menu_anchor_pos()
        self.menu.close()
        screen = QApplication.screenAt(anchor) or QApplication.primaryScreen()
        if screen is not None:
            try:
                pct = int(self.settings.value("menu_height_pct", 80))
            except (TypeError, ValueError):
                pct = 80
            pct = max(20, min(95, pct))
            self.menu.setMaximumHeight(max(120, int(screen.availableGeometry().height() * pct / 100.0)))
        self.menu.exec(anchor)

    def add_process_row(self, app):
        expanded = app.pid in self.expanded_pids
        row = ProcessRowWidget(self, app, expanded, self.menu)
        action = QWidgetAction(self.menu)
        action.setDefaultWidget(row)
        action.setProperty("pkill_role", "process_row")
        action.setProperty("pkill_pid", app.pid)
        action.setProperty("pkill_process_row", row)
        self.menu.addAction(action)
        self.process_rows[app.pid] = action

        row.configure_bar(self._bar_config())

        if expanded:
            self.add_thread_rows(app)

    def add_thread_rows(self, app):
        threads = list_threads(app.pid)
        self.thread_sampler.sample(threads)
        for thread in threads:
            row = ThreadRowWidget(self, thread, self.menu)
            action = QWidgetAction(self.menu)
            action.setDefaultWidget(row)
            action.setProperty("pkill_role", "thread_row")
            action.setProperty("pkill_pid", app.pid)
            action.setProperty("pkill_tid", thread.tid)
            action.setProperty("pkill_thread_row", row)
            self.menu.addAction(action)
            self.thread_rows[(app.pid, thread.tid)] = action

    def toggle_threads(self, pid):
        if pid in self.expanded_pids:
            self.expanded_pids.remove(pid)
        else:
            self.expanded_pids.add(pid)

        # A menüt újra kell építeni a szálak megjelenítéséhez. Újranyitáskor
        # ugyanahhoz a tálcaikonhoz rögzítjük, nem a kurzor pillanatnyi helyéhez.
        anchor = QPoint(self._menu_anchor) if self._menu_anchor is not None else self._menu_anchor_pos()
        self.menu.close()
        self.rebuild_menu(self.last_apps)

        screen = QApplication.screenAt(anchor) or QApplication.primaryScreen()
        if screen is not None:
            try:
                pct = int(self.settings.value("menu_height_pct", 80))
            except (TypeError, ValueError):
                pct = 80
            pct = max(20, min(95, pct))
            available = screen.availableGeometry()
            self.menu.setMaximumHeight(
                max(120, int(available.height() * pct / 100.0))
            )

        self.menu.exec(anchor)


    def refresh_expanded_threads(self):
        if not self.expanded_pids:
            return
        all_threads = []
        for pid in list(self.expanded_pids):
            threads = list_threads(pid)
            all_threads.extend(threads)
        self.thread_sampler.sample(all_threads)
        current = {(t.pid, t.tid): t for t in all_threads}
        for key, action in list(self.thread_rows.items()):
            thread = current.get(key)
            row = action.property("pkill_thread_row")
            if thread is None:
                action.setVisible(False)
            elif row is not None:
                action.setVisible(True)
                row.update_thread(thread)

    def show_process_context(self, app, pos):
        menu = QMenu()
        title = QAction(f"{app.executable or app.title}  —  PID {app.pid}", menu)
        title.setEnabled(False)
        menu.addAction(title)
        menu.addSeparator()

        close_action = QAction("Normál bezárás", menu)
        close_action.triggered.connect(lambda: self.controller.normal_close(app))
        menu.addAction(close_action)
        kill_action = QAction("KILL (-9)", menu)
        kill_action.triggered.connect(lambda: self.controller.kill9(app))
        menu.addAction(kill_action)
        menu.addSeparator()
        details_action = QAction("Folyamat adatai", menu)
        details_action.triggered.connect(lambda: self.controller.details(app))
        menu.addAction(details_action)
        collapse = QAction("Szálak bezárása", menu)
        collapse.triggered.connect(lambda: self.collapse_threads(app.pid))
        menu.addAction(collapse)
        self._process_context_menu = menu
        menu.popup(pos)

    def show_thread_context(self, thread, pos):
        menu = QMenu()
        title = QAction(f"{thread.name}  —  TID {thread.tid}", menu)
        title.setEnabled(False)
        menu.addAction(title)
        cpu = QAction(f"CPU: {thread.cpu:.1f} %", menu)
        cpu.setEnabled(False)
        menu.addAction(cpu)
        menu.addSeparator()

        warn = QAction("SIGKILL (-9) → a teljes processz is megszűnhet", menu)
        warn.setEnabled(False)
        menu.addAction(warn)
        kill = QAction("SIGKILL (-9) küldése a TID-re", menu)
        kill.triggered.connect(lambda: self.controller.kill_thread(thread))
        menu.addAction(kill)
        details = QAction("Szál adatai", menu)
        details.triggered.connect(lambda: self.controller.thread_details(thread))
        menu.addAction(details)
        self._thread_context_menu = menu
        menu.popup(pos)

    def collapse_threads(self, pid):
        self.expanded_pids.discard(pid)
        self.rebuild_menu(self.last_apps)

    def _bar_config(self):
        palette = self.settings.value("palette", "Normal")
        preset = PALETTES.get(palette, PALETTES["Normal"])
        def color(key):
            value = str(self.settings.value(key, preset[key])).strip()
            if not value.startswith("#") or len(value) not in (4, 7):
                return preset[key]
            return value
        try:
            width = max(20, min(100, int(self.settings.value("bar_width", preset["bar_width"]))))
        except (TypeError, ValueError):
            width = preset["bar_width"]
        try:
            height = max(2, min(20, int(self.settings.value("bar_height", preset["bar_height"]))))
        except (TypeError, ValueError):
            height = preset["bar_height"]
        try:
            baseline_height = max(1, min(5, int(self.settings.value("bar_baseline", preset.get("bar_baseline", 1)))))
        except (TypeError, ValueError):
            baseline_height = preset.get("bar_baseline", 1)
        try:
            marker_width = max(1, min(5, int(self.settings.value("bar_marker", preset.get("bar_marker", 1)))))
        except (TypeError, ValueError):
            marker_width = preset.get("bar_marker", 1)
        return width, height, color("bar_fill"), color("bar_bg"), color("bar_border"), baseline_height, marker_width

    def _bar_visible(self):
        value = self.settings.value("bar_visible", True)
        if isinstance(value, str):
            return value.lower() not in ("false", "0", "no", "off")
        return bool(value)

    def _set_cpu_bar(self, bar, cpu):
        if isinstance(bar, CpuBarWidget):
            bar.set_value(cpu)

    def _style_cpu_bar(self, bar):
        width_pct, height, fill, baseline, marker, baseline_height, marker_width = self._bar_config()
        if isinstance(bar, CpuBarWidget):
            bar.configure(width_pct, height, fill, baseline, marker, baseline_height, marker_width)


    def open_settings(self):
        self.menu.close()
        dlg = SettingsDialog(self.settings, None)
        if dlg.exec():
            self.apply_palette()

    def show_help(self):
        self.menu.close()
        dlg = QDialog()
        dlg.setWindowTitle("pkill.py – Leírás")
        dlg.resize(760, 620)

        layout = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setHtml("""
        <h2>pkill.py</h2>
        <p>Ez egy BeOS-szerű, tálcáról lenyitható folyamatkezelő.</p>

        <h3>Programlista</h3>
        <p>A fő nézet felhasználónként összesíti a CPU-terhelést. A Beállításokban
        kipipálható, mely felhasználók jelenjenek meg. Egy felhasználóra kattintva
        csak az ő folyamatai láthatók; a „Felhasználók” gomb visszavisz az összesítő
        nézethez. A folyamatok listázása nem jelent automatikus leállítási jogosultságot.</p>

        <h3>CPU</h3>
        <p>A CPU-érték a kiválasztott folyamat saját CPU-idejéből készül.
        Nem a gyermekfolyamatok összesített terhelése. A főlistában közvetlenül a
        program neve alatt vörös terheltségi vonal is jelzi az értéket.</p>

        <h3>Frissítés</h3>
        <p>Alapértelmezésben 5 másodperc. A frissítés csak akkor fut,
        amikor a programlista nyitva van. A lista bezárásakor a timer leáll.</p>

        <h3>Normál bezárás</h3>
        <p>Először az ablakkezelőnek küld egy szabályos ablakbezárási kérést
        (<code>WM_DELETE_WINDOW</code>). Ha ez nem működik, a program
        <code>SIGTERM</code> jelet használ tartalékként.</p>

        <h3>KILL (-9)</h3>
        <p>A <code>SIGKILL</code> azonnal megszünteti a folyamatot.
        A program nem tudja elkapni vagy feldolgozni ezt a jelet.
        Emiatt elveszhet a még el nem mentett adat.</p>

        <h3>Szálak</h3>
        <p>Bal kattintással egy program sora lenyitható. Ekkor a programhoz tartozó
        Linux thread-ek (TID-ek) jelennek meg. A szálak saját CPU-terhelést,
        állapotot, prioritást, Nice értéket és processzorszámot mutatnak.</p>
        <p>A szálakon jobb kattintással megnyitható a szál műveleti menüje.
        Fontos: a Linux SIGKILL végzetes processzszintű jel, ezért egy TID-re
        célzott SIGKILL sem tekinthető biztonságos, izolált thread-kilövésnek.</p>

        <h3>Gyermekfolyamatok</h3>
        <p>A programlista szándékosan nem jelenít meg gyermekfolyamat-fát.
        A kibontás kizárólag az adott PID thread-jeit mutatja.</p>

        <h3>Jogosultság</h3>
        <p>A folyamatlista normál felhasználóként is megjelenítheti a root
        folyamatait, amennyiben a /proc hozzáférési szabályai engedik. Más
        felhasználó vagy root folyamatának leállításához továbbra is megfelelő
        jogosultság szükséges.</p>

        <h3>XFCE és IceWM tálca</h3>
        <p>Az alkalmazás Qt System Tray ikont használ, ezért XFCE és IceWM alatt
        is működhet. IceWM-ben a tálcaértesítési területnek engedélyezve kell lennie,
        és az alkalmazást az IceWM munkamenetben is el kell indítani.</p>
        """)
        layout.addWidget(browser)

        close = QPushButton("Bezárás")
        close.clicked.connect(dlg.accept)
        layout.addWidget(close)

        dlg.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "pkill.py",
            "A rendszerben nem érhető el System Tray.\n"
            "X11/XWayland és egy tálcát támogató asztali környezet szükséges.",
        )
        return 1

    controller = PkillApp(app)
    app._pkill_controller = controller
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
