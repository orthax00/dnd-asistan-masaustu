"""Ses motoru: arayüzden bağımsız. Başka uygulamalar (ör. DnD asistanı) doğrudan kullanabilir.

    from voicechanger import Engine
    eng = Engine()
    eng.start()                    # varsayılan mikrofon -> CABLE Input
    eng.select_preset("Ejderha")
    eng.stop()
"""
import json
import os
import queue
import shutil
import sys
import threading

import numpy as np
import sounddevice as sd

from .effects import BUILTIN_PRESETS, build_chain, full_params, NoiseGate

BLOCK = 512  # örnek; 48 kHz'de ~10.7 ms
APP_NAME = "DnD Voice Changer"


def data_dir():
    """Kullanıcı verisi klasörü (%APPDATA%\\DnD Voice Changer)."""
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------- aygıtlar

def hostapi_names():
    return [h["name"] for h in sd.query_hostapis()]


def devices_for(hostapi_index, kind):
    key = "max_input_channels" if kind == "in" else "max_output_channels"
    return [(i, d["name"]) for i, d in enumerate(sd.query_devices())
            if d["hostapi"] == hostapi_index and d[key] > 0]


def default_hostapi_index():
    names = hostapi_names()
    return names.index("MME") if "MME" in names else 0


def find_cable_output(hostapi_index=None):
    """'CABLE Input' çıkış aygıtının indeksini döndürür (yoksa None)."""
    api = default_hostapi_index() if hostapi_index is None else hostapi_index
    for i, n in devices_for(api, "out"):
        if "cable input" in n.lower():
            return i
    return None


# ---------------------------------------------------------------- ses akışı

class AudioEngine:
    """Mikrofon -> efekt zinciri -> çıkış aygıtı (+ isteğe bağlı dinleme)."""

    def __init__(self):
        self.stream = None
        self.monitor_stream = None
        self.monitor_q = queue.Queue(maxsize=8)
        self.lock = threading.Lock()
        self.chain = None
        self.gate = NoiseGate(-50)
        self.sr = 48000
        self.params = {}
        self.gate_on = True
        self.monitor_on = False
        self.level = 0.0

    @property
    def running(self):
        return self.stream is not None

    def set_params(self, params):
        self.params = dict(params)
        chain = build_chain(self.params, self.sr)
        with self.lock:
            self.chain = chain

    def _callback(self, indata, outdata, frames, time, status):
        x = indata[:, 0].astype(np.float32)
        if self.gate_on:
            x = self.gate.process(x)
        with self.lock:
            chain = self.chain
        y = chain.process(x) if chain else x
        y = np.clip(y, -1.0, 1.0)
        self.level = float(np.sqrt(np.mean(y * y)))
        outdata[:] = y.reshape(-1, 1).repeat(outdata.shape[1], axis=1)
        if self.monitor_on:
            try:
                self.monitor_q.put_nowait(y.copy())
            except queue.Full:
                pass

    def _monitor_callback(self, outdata, frames, time, status):
        try:
            y = self.monitor_q.get_nowait()
        except queue.Empty:
            outdata.fill(0)
            return
        if len(y) != frames:
            y = np.resize(y, frames)
        outdata[:] = y.reshape(-1, 1).repeat(outdata.shape[1], axis=1)

    def start(self, in_dev, out_dev, monitor_dev=None):
        self.stop()
        self.sr = int(sd.query_devices(in_dev)["default_samplerate"])
        self.gate = NoiseGate(-50)
        self.set_params(self.params)
        self.monitor_on = monitor_dev is not None
        out_ch = min(2, sd.query_devices(out_dev)["max_output_channels"])
        self.stream = sd.Stream(device=(in_dev, out_dev), samplerate=self.sr, blocksize=BLOCK,
                                channels=(1, out_ch), dtype="float32", latency="low",
                                callback=self._callback)
        self.stream.start()
        if monitor_dev is not None:
            mch = min(2, sd.query_devices(monitor_dev)["max_output_channels"])
            self.monitor_stream = sd.OutputStream(device=monitor_dev, samplerate=self.sr,
                                                  blocksize=BLOCK, channels=mch, dtype="float32",
                                                  latency="low", callback=self._monitor_callback)
            self.monitor_stream.start()

    def stop(self):
        for s in (self.stream, self.monitor_stream):
            if s is not None:
                try:
                    s.stop()
                    s.close()
                except Exception:
                    pass
        self.stream = None
        self.monitor_stream = None
        self.level = 0.0


# ---------------------------------------------------------------- karakterler

class PresetStore:
    """presets.json: {"order": [...], "presets": {ad: parametreler}, "known_builtins": [...]}"""

    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "presets.json")
        self._migrate_old_file()
        self.order, self.presets = [], {}
        self.load()

    def _migrate_old_file(self):
        # eski sürüm presets.json'u uygulama klasörüne yazıyordu
        if os.path.exists(self.path):
            return
        here = os.path.dirname(os.path.abspath(sys.argv[0] or "."))
        old = os.path.join(here, "presets.json")
        if os.path.exists(old):
            try:
                shutil.copyfile(old, self.path)
            except OSError:
                pass

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self.presets = {k: full_params(v) for k, v in data["presets"].items()}
            self.order = [n for n in data["order"] if n in self.presets]
            self.order += [n for n in self.presets if n not in self.order]
            known = set(data.get("known_builtins", []))
            for name, params in BUILTIN_PRESETS.items():
                if name not in known and name not in self.presets:
                    self.presets[name] = full_params(params)
                    self.order.append(name)
        except Exception:
            self.reset()

    def reset(self):
        self.presets = {k: full_params(v) for k, v in BUILTIN_PRESETS.items()}
        self.order = list(BUILTIN_PRESETS)

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"order": self.order, "presets": self.presets,
                       "known_builtins": list(BUILTIN_PRESETS)}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)


# ---------------------------------------------------------------- dış API

class Engine:
    """Başka uygulamaların kullanacağı basit arayüz."""

    def __init__(self, preset_path=None):
        self.audio = AudioEngine()
        self.store = PresetStore(preset_path)
        self.current = self.store.order[0] if self.store.order else None
        if self.current:
            self.audio.params = self.store.presets[self.current]

    @property
    def running(self):
        return self.audio.running

    @property
    def level(self):
        return self.audio.level

    def list_presets(self):
        return list(self.store.order)

    def select_preset(self, name):
        if name not in self.store.presets:
            raise KeyError(name)
        self.current = name
        self.audio.set_params(self.store.presets[name])

    def select_index(self, i):
        self.select_preset(self.store.order[i])

    def set_params(self, params):
        """Kaydetmeden geçici ayar uygular (ör. canlı kaydırıcılar)."""
        self.audio.set_params(full_params(params))

    def start(self, input_device=None, output_device=None, monitor_device=None):
        """Aygıtlar indeks olarak verilir; boşsa varsayılan mikrofon ve CABLE Input kullanılır."""
        api = default_hostapi_index()
        if input_device is None:
            ins = devices_for(api, "in")
            d = sd.default.device[0]
            input_device = d if any(i == d for i, _ in ins) else (ins[0][0] if ins else None)
        if output_device is None:
            output_device = find_cable_output(api)
        if input_device is None or output_device is None:
            raise RuntimeError("Mikrofon veya CABLE Input bulunamadı.")
        self.audio.start(input_device, output_device, monitor_device)

    def stop(self):
        self.audio.stop()
