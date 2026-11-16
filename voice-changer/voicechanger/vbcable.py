"""VB-CABLE (sanal ses kablosu) kontrolü ve kurulumu.

VB-CABLE, VB-Audio Software'in bağışla desteklenen (donationware) bir ürünüdür: https://vb-cable.com
Kurulum dosyası resmi siteden indirilir ve olduğu gibi çalıştırılır.
"""
import os
import sys
import tempfile
import urllib.request
import zipfile

import sounddevice as sd

DOWNLOAD_URL = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack46.zip"
INFO_URL = "https://vb-cable.com"


def is_installed():
    try:
        return any("cable input" in d["name"].lower() and d["max_output_channels"] > 0
                   for d in sd.query_devices())
    except Exception:
        return False


def _setup_exe(folder):
    name = "VBCABLE_Setup_x64.exe" if sys.maxsize > 2 ** 32 else "VBCABLE_Setup.exe"
    for root, _dirs, files in os.walk(folder):
        if name in files:
            return os.path.join(root, name)
    return None


def download(progress=None):
    """Resmi paketi indirip açar; kurulum exe'sinin yolunu döndürür."""
    folder = os.path.join(tempfile.gettempdir(), "dnd_vc_vbcable")
    os.makedirs(folder, exist_ok=True)
    zpath = os.path.join(folder, "vbcable.zip")

    def hook(blocks, bs, total):
        if progress and total > 0:
            progress(min(1.0, blocks * bs / total))

    urllib.request.urlretrieve(DOWNLOAD_URL, zpath, hook)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(folder)
    exe = _setup_exe(folder)
    if not exe:
        raise RuntimeError("Kurulum dosyası paketin içinde bulunamadı.")
    return exe


def run_setup(exe):
    """Kurulumu yönetici izniyle (UAC) başlatır. Windows dışı sistemlerde hata verir."""
    if os.name != "nt":
        raise RuntimeError("VB-CABLE yalnızca Windows'ta kurulabilir.")
    import ctypes
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, None, os.path.dirname(exe), 1)
    if rc <= 32:
        raise RuntimeError("Kurulum başlatılamadı (izin verilmemiş olabilir).")
