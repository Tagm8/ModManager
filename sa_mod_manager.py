#!/usr/bin/env python3
"""
SA Mod Manager v1.0 — Linux Mint / Steam Proton

by tagm8 (https://github.com/Tagm8/ModManager)

Important:
- ModManger does NOT redistribute Rockstar game files or GTA executables.
- Downloads supported open/community releases from their upstream URLs.
"""

from __future__ import annotations
import hashlib, json, os, shutil, subprocess, sys, tempfile, urllib.request, zipfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget, QFrame
)

APP = "SA Mod Manager"
VERSION = "1.0.0"
DATA = Path.home()/".local/share/sa-mod-manager"
CACHE = DATA/"cache"
BACKUPS = DATA/"backups"
CONFIG = DATA/"config.json"
for p in (DATA, CACHE, BACKUPS): p.mkdir(parents=True, exist_ok=True)

# These are intentionally not hard-coded mirrors.
CATALOG = [
    {
        "id":"cleo4", "name":"CLEO 4", "category":"Runtime",
        "repo":"cleolibrary/CLEO4", "latest_asset_ext":".zip",
        "description":"CLEO scripting runtime for classic GTA SA.",
        "requires":["gta1.0"], "conflicts":[],
        "install":"root", "source":"https://github.com/cleolibrary/CLEO4/releases"
    },
    {
        "id":"silentpatch", "name":"SilentPatch SA", "category":"Fixes",
        "repo":"CookiePLMonster/SilentPatch", "direct":"https://github.com/CookiePLMonster/SilentPatch/releases/latest/download/SilentPatchSA.zip",
        "description":"Large collection of classic-game bug fixes.",
        "requires":["gta1.0"], "conflicts":[],
        "install":"root", "source":"https://github.com/CookiePLMonster/SilentPatch/releases"
    },
    {
        "id":"widescreen", "name":"Widescreen Fix", "category":"Fixes",
        "repo":"ThirteenAG/WidescreenFixesPack", "prefix":"GTASA.WidescreenFix",
        "description":"Correct widescreen HUD, FOV and display behavior.",
        "requires":["gta1.0"], "conflicts":[],
        "install":"root", "source":"https://github.com/ThirteenAG/WidescreenFixesPack/releases"
    },
    {
        "id":"project2dfx", "name":"Project2DFX", "category":"Graphics",
        "repo":"ThirteenAG/III.VC.SA.IV.Project2DFX", "latest_asset_ext":".zip",
        "description":"Extended draw distance and LOD corona effects.",
        "requires":["asi-loader"], "conflicts":[],
        "install":"modloader", "source":"https://github.com/ThirteenAG/III.VC.SA.IV.Project2DFX"
    },
    {
        "id":"asi-loader", "name":"Ultimate ASI Loader", "category":"Runtime",
        "repo":"ThirteenAG/Ultimate-ASI-Loader", "latest_asset_ext":".zip",
        "description":"Loads .asi plugins into the game process.",
        "requires":["gta1.0"], "conflicts":[],
        "install":"root", "source":"https://github.com/ThirteenAG/Ultimate-ASI-Loader/releases"
    },
]

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def api(url):
    req=urllib.request.Request(url,headers={
        "Accept":"application/vnd.github+json",
        "User-Agent":"SA-Mod-Manager/1.0"
    })
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read())

def get_latest_asset(mod):
    if mod.get("direct"):
        return mod["direct"], Path(mod["direct"].split("/")[-1] or "download.zip").name
    release=api("https://api.github.com/repos/%s/releases/latest"%mod["repo"])
    assets=release.get("assets",[])
    candidates=[]
    if mod.get("prefix"):
        candidates=[a for a in assets if a["name"].startswith(mod["prefix"]) and a["name"].lower().endswith(".zip")]
    else:
        ext=mod.get("latest_asset_ext",".zip")
        candidates=[a for a in assets if a["name"].lower().endswith(ext)]
    if not candidates:
        raise RuntimeError("No compatible release asset found upstream.")
    a=candidates[0]
    return a["browser_download_url"], a["name"]

def download(url,dest,progress=None):
    req=urllib.request.Request(url,headers={"User-Agent":"SA-Mod-Manager/1.0"})
    with urllib.request.urlopen(req,timeout=90) as r, open(dest,"wb") as f:
        total=int(r.headers.get("Content-Length","0")); done=0
        while True:
            b=r.read(1024*512)
            if not b: break
            f.write(b); done+=len(b)
            if total and progress: progress(min(100,int(done*100/total)))

def safe_extract(z,dst):
    root=dst.resolve()
    with zipfile.ZipFile(z) as f:
        for info in f.infolist():
            target=(dst/info.filename).resolve()
            if not (str(target)==str(root) or str(target).startswith(str(root)+os.sep)):
                raise RuntimeError("Unsafe archive path rejected: "+info.filename)
        f.extractall(dst)

def flatten(d):
    entries=list(d.iterdir())
    while len(entries)==1 and entries[0].is_dir():
        inner=entries[0]
        for x in list(inner.iterdir()):
            target=d/x.name
            if target.exists() and target.is_dir():
                shutil.copytree(x,target,dirs_exist_ok=True); shutil.rmtree(x)
            elif target.exists():
                shutil.copy2(x,target); x.unlink()
            else:
                shutil.move(str(x),str(target))
        inner.rmdir()
        entries=list(d.iterdir())

def game_dir(p):
    p=Path(p)
    return p.is_dir() and any((p/n).exists() for n in ("gta_sa.exe","gta-sa.exe","GTA-SA.exe"))

def exe_path(g):
    for n in ("gta_sa.exe","gta-sa.exe","GTA-SA.exe"):
        if (g/n).exists(): return g/n

def backup(g, rels):
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    out=BACKUPS/stamp; out.mkdir()
    manifest=[]
    for rel in rels:
        src=g/rel
        if src.is_file():
            dst=out/rel; dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)
            manifest.append({"path":str(rel),"sha256":sha256(src)})
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2))
    return out

def root_install(staging,g):
    for src in staging.rglob("*"):
        if src.is_file():
            rel=src.relative_to(staging); dst=g/rel
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)

def modloader_install(staging,g,modname):
    ml=g/"modloader"/modname
    ml.mkdir(parents=True,exist_ok=True)
    for src in staging.rglob("*"):
        if src.is_file():
            rel=src.relative_to(staging); dst=ml/rel
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)

class Worker(QObject):
    progress=Signal(int); log=Signal(str); done=Signal(bool,str)
    def __init__(self,fn): super().__init__(); self.fn=fn
    def run(self):
        try: self.fn(self); self.done.emit(True,"Operation completed.")
        except Exception as e: self.done.emit(False,f"{type(e).__name__}: {e}")

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP} {VERSION}")
        self.resize(1180,780)
        self.cfg=self.load()
        self.build()
        self.refresh()

    def load(self):
        try: return json.loads(CONFIG.read_text())
        except: return {"game":"","prefix":"","profile":"Essentials","installed":{},"profiles":{"Essentials":[]}}

    def save(self): CONFIG.write_text(json.dumps(self.cfg,indent=2))

    def build(self):
        self.setStyleSheet("""
        QWidget{background:#101217;color:#e9ebf0;font-size:14px}
        QFrame#card{background:#181b22;border:1px solid #292e39;border-radius:14px}
        QLineEdit,QComboBox,QTextEdit,QListWidget{background:#0c0e12;border:1px solid #303643;border-radius:9px;padding:8px}
        QPushButton{background:#242936;border:1px solid #394152;border-radius:9px;padding:9px 14px}
        QPushButton:hover{background:#303746}
        QPushButton#accent{background:#6c5ce7;border-color:#8276ed;font-weight:700}
        QLabel#title{font-size:29px;font-weight:800}
        QLabel#muted{color:#99a2b2}
        QProgressBar{background:#0c0e12;border:0;border-radius:5px;text-align:center}
        QProgressBar::chunk{background:#6c5ce7;border-radius:5px}
        QTabBar::tab{padding:10px 18px}
        """)

        c=QWidget(); outer=QVBoxLayout(c); outer.setContentsMargins(24,20,24,20)
        h=QHBoxLayout(); t=QLabel("SA Mod Manager"); t.setObjectName("title"); h.addWidget(t); h.addStretch()
        self.status=QLabel(); h.addWidget(self.status); outer.addLayout(h)
        tabs=QTabWidget(); outer.addWidget(tabs)

        setup=QWidget(); sl=QVBoxLayout(setup)
        card=QFrame(); card.setObjectName("card"); g=QGridLayout(card); g.setContentsMargins(18,18,18,18)
        g.addWidget(QLabel("GTA San Andreas folder"),0,0)
        self.game=QLineEdit(self.cfg.get("game","")); g.addWidget(self.game,0,1)
        b=QPushButton("Browse"); b.clicked.connect(self.pick_game); g.addWidget(b,0,2)
        g.addWidget(QLabel("Proton prefix (optional)"),1,0)
        self.prefix=QLineEdit(self.cfg.get("prefix","")); g.addWidget(self.prefix,1,1,1,2)
        save=QPushButton("Save setup"); save.setObjectName("accent"); save.clicked.connect(self.save_setup); g.addWidget(save,2,1)
        sl.addWidget(card)
        text=QLabel("Works with a non-Steam GTA SA install launched by Steam Proton: the manager modifies the actual game directory, while Steam/Proton handles launching it. The prefix is only needed for diagnostics/advanced integration.")
        text.setWordWrap(True); text.setObjectName("muted"); sl.addWidget(text)
        sl.addStretch(); tabs.addTab(setup,"Setup")

        mods=QWidget(); ml=QVBoxLayout(mods)
        top=QHBoxLayout(); top.addWidget(QLabel("Profile"))
        self.profile=QComboBox(); self.profile.addItems(["Essentials","Graphics","Gameplay","My Modpack"]); self.profile.setCurrentText(self.cfg.get("profile","Essentials")); self.profile.currentTextChanged.connect(self.profile_changed); top.addWidget(self.profile)
        top.addStretch(); ml.addLayout(top)
        self.modlist=QListWidget()
        for m in CATALOG:
            it=QListWidgetItem(f"{m['name']}  •  {m['category']}  •  {m['description']}")
            it.setData(Qt.UserRole,m["id"]); it.setCheckState(Qt.Checked if m["id"] in self.cfg.get("profiles",{}).get(self.profile.currentText(),[]) else Qt.Unchecked)
            self.modlist.addItem(it)
        ml.addWidget(self.modlist)
        row=QHBoxLayout()
        install=QPushButton("Install / Update selected"); install.setObjectName("accent"); install.clicked.connect(self.install_selected); row.addWidget(install)
        disable=QPushButton("Disable selected"); disable.clicked.connect(self.disable_selected); row.addWidget(disable)
        row.addStretch(); ml.addLayout(row)
        ml.addWidget(QLabel("Profiles are stored locally. The v1 installer uses Mod Loader destinations for content mods where appropriate and keeps root-level runtime components explicit."))
        tabs.addTab(mods,"Mod Library")

        one=QWidget(); ol=QVBoxLayout(one)
        card=QFrame(); card.setObjectName("card"); box=QVBoxLayout(card)
        box.addWidget(QLabel("GTA SA 1.0 executable"))
        box.addWidget(QLabel("Supply your own legally-owned classic 1.0 executable. The manager never downloads or redistributes Rockstar binaries."))
        self.exe=QLineEdit(); self.exe.setPlaceholderText("Path to your gta_sa.exe 1.0"); box.addWidget(self.exe)
        rr=QHBoxLayout(); q=QPushButton("Choose EXE"); q.clicked.connect(self.pick_exe); rr.addWidget(q)
        apply=QPushButton("Backup + install EXE"); apply.setObjectName("accent"); apply.clicked.connect(self.install_exe); rr.addWidget(apply); rr.addStretch(); box.addLayout(rr)
        self.exeinfo=QLabel("No EXE selected."); self.exeinfo.setObjectName("muted"); box.addWidget(self.exeinfo)
        ol.addWidget(card)
        ol.addWidget(QLabel("Compatibility target: classic 1.0 US is the common target for older SA plugin ecosystems. CLEO itself says its ASI Loader overwrites the original vorbisFile.dll, so this manager backs that file up before installation."))
        ol.addStretch(); tabs.addTab(one,"1.0 / Runtime")

        diag=QWidget(); dl=QVBoxLayout(diag)
        self.diag=QTextEdit(); self.diag.setReadOnly(True); dl.addWidget(self.diag)
        d=QPushButton("Run diagnostics"); d.clicked.connect(self.run_diag); dl.addWidget(d)
        tabs.addTab(diag,"Diagnostics")

        logtab=QWidget(); ll=QVBoxLayout(logtab)
        self.logbox=QTextEdit(); self.logbox.setReadOnly(True); ll.addWidget(self.logbox)
        self.progress=QProgressBar(); ll.addWidget(self.progress); tabs.addTab(logtab,"Activity")
        self.setCentralWidget(c)

    def pick_game(self):
        p=QFileDialog.getExistingDirectory(self,"Select GTA SA folder")
        if p: self.game.setText(p); self.refresh()

    def pick_exe(self):
        p,_=QFileDialog.getOpenFileName(self,"Select GTA SA 1.0 EXE","","Windows executable (*.exe)")
        if p:
            self.exe.setText(p)
            try: self.exeinfo.setText(f"{p} • SHA-256 {sha256(Path(p))}")
            except Exception as e: self.exeinfo.setText(str(e))

    def save_setup(self):
        self.cfg["game"]=self.game.text(); self.cfg["prefix"]=self.prefix.text()
        self.cfg["profile"]=self.profile.currentText(); self.save(); self.refresh()

    def refresh(self):
        g=Path(self.game.text()).expanduser()
        if game_dir(g): self.status.setText("✓ GTA SA detected")
        else: self.status.setText("⚠ Select GTA SA folder")

    def log(self,s): self.logbox.append(s)

    def worker(self,fn):
        self.progress.setValue(0)
        self.thread=QThread(); self.w=Worker(fn); self.w.moveToThread(self.thread)
        self.thread.started.connect(self.w.run); self.w.progress.connect(self.progress.setValue); self.w.log.connect(self.log); self.w.done.connect(self.finished)
        self.thread.start()

    def finished(self,ok,msg):
        self.log(("✓ " if ok else "✗ ")+msg)
        (QMessageBox.information if ok else QMessageBox.critical)(self,APP,msg)
        self.thread.quit(); self.thread.wait(); self.refresh()

    def selected(self):
        return [self.modlist.item(i).data(Qt.UserRole) for i in range(self.modlist.count()) if self.modlist.item(i).checkState()==Qt.Checked]

    def profile_changed(self,name):
        chosen=self.cfg.get("profiles",{}).get(name,[])
        for i in range(self.modlist.count()):
            it=self.modlist.item(i); it.setCheckState(Qt.Checked if it.data(Qt.UserRole) in chosen else Qt.Unchecked)

    def install_selected(self):
        g=Path(self.game.text()).expanduser()
        if not game_dir(g): QMessageBox.warning(self,APP,"Select a GTA SA folder first."); return
        ids=self.selected()
        self.cfg.setdefault("profiles",{})[self.profile.currentText()]=ids; self.save()
        def task(w):
            installed=self.cfg.setdefault("installed",{})
            for mid in ids:
                self.install_mod(next(x for x in CATALOG if x["id"]==mid),g,w)
                installed[mid]=datetime.now().isoformat(timespec="seconds")
            self.save()
        self.worker(task)

    def install_mod(self,m,g,w):
        # dependency gate
        if "gta1.0" in m["requires"] and not self.detect_1_0(g):
            raise RuntimeError(f"{m['name']} requires a classic 1.0 executable. Install one in the 1.0 / Runtime tab first.")
        url,name=get_latest_asset(m)
        tmp=Path(tempfile.mkdtemp(prefix="sa-mm-"))
        try:
            archive=tmp/name; w.log.emit(f"→ {m['name']}: {url}")
            download(url,archive,w.progress.emit)
            w.log.emit(f"  SHA-256: {sha256(archive)}")
            staging=tmp/"stage"; staging.mkdir(); safe_extract(archive,staging); flatten(staging)
            # Back up likely root conflicts. Full transaction journaling is planned for v1.1.
            rels=[Path("vorbisFile.dll"),Path("vorbisHooked.dll"),Path("bass.dll"),Path("cleo.asi"),Path("modloader.asi"),Path("SilentPatchSA.asi"),Path("GTASA.WidescreenFix.asi"),Path("gta_sa.exe")]
            b=backup(g,rels); w.log.emit("  Backup: "+b.name)
            if m["install"]=="modloader":
                modloader_install(staging,g,m["name"])
            else:
                root_install(staging,g)
            w.log.emit("✓ "+m["name"]+" installed")
        finally: shutil.rmtree(tmp,ignore_errors=True)

    def detect_1_0(self,g):
        e=exe_path(g)
        if not e: return False
        # Conservative size/hash heuristic: user can still use the manager with a custom
        # classic build, but this avoids claiming that a modern EXE is 1.0.
        return e.stat().st_size < 20*1024*1024

    def install_exe(self):
        g=Path(self.game.text()).expanduser(); src=Path(self.exe.text()).expanduser(); dst=exe_path(g)
        if not dst or not src.is_file(): QMessageBox.warning(self,APP,"Need a valid game directory and source EXE."); return
        if QMessageBox.question(self,APP,"Back up current EXE and replace it?")==QMessageBox.No: return
        def task(w):
            b=backup(g,[dst.name]); shutil.copy2(src,dst)
            w.log.emit("Backup: "+b.name); w.log.emit("Installed user-supplied EXE."); w.log.emit("SHA-256: "+sha256(dst))
        self.worker(task)

    def disable_selected(self):
        g=Path(self.game.text()).expanduser()
        ids=self.selected()
        for m in CATALOG:
            if m["id"] in ids and m["install"]=="modloader":
                d=g/"modloader"/m["name"]
                if d.exists():
                    d.rename(d.with_name(d.name+".disabled"))
        self.log("Disabled selected Mod Loader content.")
        self.refresh()

    def run_diag(self):
        g=Path(self.game.text()).expanduser()
        lines=[]
        lines.append("SA MOD MANAGER DIAGNOSTICS")
        lines.append("="*34)
        lines.append("Game directory: "+str(g))
        lines.append("Game detected: "+("YES" if game_dir(g) else "NO"))
        e=exe_path(g)
        lines.append("EXE: "+(str(e) if e else "missing"))
        if e:
            lines.append("EXE size: "+str(e.stat().st_size))
            lines.append("EXE SHA-256: "+sha256(e))
        lines.append("modloader/: "+("YES" if (g/"modloader").is_dir() else "NO"))
        for f in ("cleo.asi","modloader.asi","vorbisHooked.dll","vorbisFile.dll","bass.dll"):
            lines.append(f"{f}: "+("YES" if (g/f).exists() else "NO"))
        lines.append("Proton prefix: "+(self.prefix.text() or "not configured"))
        lines.append("")
        lines.append("NOTE: EXE version detection is intentionally conservative; a production build should use verified known-good hashes.")
        self.diag.setPlainText("\n".join(lines))

def main():
    app=QApplication(sys.argv); app.setApplicationName(APP); app.setApplicationVersion(VERSION)
    w=Window(); w.show(); sys.exit(app.exec())

if __name__=="__main__": main()
