# PyInstaller tanımı: pyinstaller packaging/voicechanger.spec
import os
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    datas=[(os.path.join(ROOT, "icon.ico"), ".")],
    hiddenimports=["keyboard"],
    excludes=["matplotlib", "pandas", "IPython", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="DnDVoiceChanger",
    console=False,
    icon=os.path.join(ROOT, "icon.ico"),
)
coll = COLLECT(exe, a.binaries, a.datas, name="DnDVoiceChanger")
