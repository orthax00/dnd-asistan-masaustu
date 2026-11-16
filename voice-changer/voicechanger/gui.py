"""Masaüstü arayüzü (tkinter). Ses işi `engine.Engine` içindedir."""
import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox, simpledialog

import numpy as np
import sounddevice as sd

from . import vbcable
from .control_server import ControlServer
from .effects import PARAMS
from .engine import Engine, APP_NAME, hostapi_names, devices_for, default_hostapi_index

try:
    import keyboard  # global kısayollar
except Exception:  # pragma: no cover
    keyboard = None

FKEYS = [f"f{i}" for i in range(1, 13)]


def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, name)


class App:
    def __init__(self, root):
        self.root = root
        self.eng = Engine()
        self.store = self.eng.store
        self.cmd_q = queue.Queue()  # kısayol ve API komutları (başka iş parçacıklarından)
        self.current = None
        self._apply_job = None
        self._loading = False

        root.title(APP_NAME)
        root.minsize(760, 680)
        try:
            root.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass
        pad = {"padx": 6, "pady": 3}

        # --- VB-Cable uyarısı
        self.cable_bar = tk.Frame(root, bg="#fff3cd")
        tk.Label(self.cable_bar, bg="#fff3cd", fg="#664d03",
                 text="Sanal mikrofon (VB-CABLE) kurulu değil. Discord'a ses gönderebilmek için gerekli.").pack(
            side="left", padx=10, pady=6)
        ttk.Button(self.cable_bar, text="Sanal mikrofonu kur", command=self.install_cable).pack(side="right", padx=8)

        # --- aygıtlar
        dev = ttk.LabelFrame(root, text="Ses aygıtları", padding=8)
        dev.pack(fill="x", padx=10, pady=(10, 4))
        self.dev_frame = dev
        ttk.Label(dev, text="Sürücü").grid(row=0, column=0, sticky="w", **pad)
        self.api_var = tk.StringVar()
        self.api_box = ttk.Combobox(dev, textvariable=self.api_var, state="readonly",
                                    values=hostapi_names(), width=18)
        self.api_box.grid(row=0, column=1, sticky="we", **pad)
        self.api_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_devices())
        ttk.Button(dev, text="Yenile", command=self.rescan).grid(row=0, column=2, sticky="w", **pad)
        ttk.Label(dev, text="Mikrofon").grid(row=1, column=0, sticky="w", **pad)
        self.in_var = tk.StringVar()
        self.in_box = ttk.Combobox(dev, textvariable=self.in_var, state="readonly", width=50)
        self.in_box.grid(row=1, column=1, columnspan=3, sticky="we", **pad)
        ttk.Label(dev, text="Çıkış").grid(row=2, column=0, sticky="w", **pad)
        self.out_var = tk.StringVar()
        self.out_box = ttk.Combobox(dev, textvariable=self.out_var, state="readonly", width=50)
        self.out_box.grid(row=2, column=1, columnspan=3, sticky="we", **pad)
        dev.columnconfigure(3, weight=1)

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True, padx=10, pady=4)

        # --- karakter listesi
        left = ttk.LabelFrame(body, text="Karakterler (Ctrl+F1…F12)", padding=8)
        left.pack(side="left", fill="y")
        self.listbox = tk.Listbox(left, height=20, width=28, exportselection=False,
                                  font=("Segoe UI", 10))
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_list_select)
        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="▲", width=3, command=lambda: self.move(-1)).pack(side="left")
        ttk.Button(btns, text="▼", width=3, command=lambda: self.move(1)).pack(side="left", padx=2)
        ttk.Button(btns, text="Yeniden adlandır", command=self.rename).pack(side="left", padx=2)
        ttk.Button(btns, text="Sil", width=4, command=self.delete).pack(side="left")

        # --- parametreler
        right = ttk.LabelFrame(body, text="Ses ayarları", padding=8)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.vars, self.val_lbls, self._step = {}, {}, {}
        for r, (key, label, lo, hi, default, step) in enumerate(PARAMS):
            ttk.Label(right, text=label).grid(row=r, column=0, sticky="w", **pad)
            var = tk.DoubleVar(value=default)
            ttk.Scale(right, from_=lo, to=hi, variable=var,
                      command=lambda v, k=key: self.on_slider(k)).grid(row=r, column=1, sticky="we", **pad)
            lbl = ttk.Label(right, width=6)
            lbl.grid(row=r, column=2, sticky="e", **pad)
            self.vars[key], self.val_lbls[key], self._step[key] = var, lbl, step
        right.columnconfigure(1, weight=1)
        sv = ttk.Frame(right)
        sv.grid(row=len(PARAMS), column=0, columnspan=3, sticky="we", pady=(8, 0))
        ttk.Button(sv, text="💾 Kaydet", command=self.save_current).pack(side="left")
        ttk.Button(sv, text="Yeni karakter olarak kaydet…", command=self.save_as).pack(side="left", padx=6)
        ttk.Button(sv, text="Geri al", command=self.revert).pack(side="left")

        # --- alt kısım
        bottom = ttk.Frame(root, padding=(10, 4, 10, 10))
        bottom.pack(fill="x")
        self.gate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(bottom, text="Gürültü kapısı", variable=self.gate_var,
                        command=lambda: setattr(self.eng.audio, "gate_on", self.gate_var.get())).pack(side="left")
        self.mon_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text="Kendimi duy (kulaklıkla)", variable=self.mon_var).pack(side="left", padx=10)
        self.btn = ttk.Button(bottom, text="▶ Başlat", command=self.toggle, width=14)
        self.btn.pack(side="right")
        self.meter = ttk.Progressbar(bottom, maximum=100, length=160)
        self.meter.pack(side="right", padx=10)

        foot = ttk.Frame(root, padding=(10, 0, 10, 8))
        foot.pack(fill="x")
        self.status = ttk.Label(foot, text="Hazır", foreground="gray")
        self.status.pack(side="left")
        credit = ttk.Label(foot, text="VB-CABLE: VB-Audio (donationware) · vb-cable.com",
                           foreground="gray", cursor="hand2")
        credit.pack(side="right")
        credit.bind("<Button-1>", lambda e: webbrowser.open(vbcable.INFO_URL))

        self.api_var.set(hostapi_names()[default_hostapi_index()])
        self.refresh_devices()
        self.refresh_list()
        self.select(self.store.order[0] if self.store.order else None)
        self.setup_hotkeys()
        self.server = ControlServer(lambda c, a: self.cmd_q.put((c, a)), self.api_status)
        try:
            self.server.start()
        except OSError:
            self.server = None  # port kullanımda; API olmadan devam
        self.tick()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ----- VB-Cable
    def update_cable_bar(self):
        if vbcable.is_installed():
            self.cable_bar.pack_forget()
        else:
            self.cable_bar.pack(fill="x", before=self.dev_frame)

    def install_cable(self):
        if not messagebox.askyesno(
                "Sanal mikrofon",
                "VB-CABLE resmi siteden (vb-audio.com) indirilip kurulum başlatılacak.\n\n"
                "Açılan pencerede 'Install Driver'a bas, bitince bilgisayarı yeniden başlat.\n"
                "VB-CABLE, VB-Audio Software'in bağışla desteklenen ücretsiz bir ürünüdür.\n\nDevam edilsin mi?"):
            return
        self.set_status("VB-CABLE indiriliyor…", "blue")

        def work():
            try:
                exe = vbcable.download()
                self.cmd_q.put(("cable_ready", exe))
            except Exception as e:
                self.cmd_q.put(("cable_error", str(e)))

        threading.Thread(target=work, daemon=True).start()

    def rescan(self):
        """Yeni kurulan aygıtları görmek için PortAudio'yu yeniden başlatır."""
        if self.eng.running:
            self.toggle()
        try:
            sd._terminate()
            sd._initialize()
        except Exception:
            pass
        self.api_box["values"] = hostapi_names()
        self.refresh_devices()

    # ----- aygıtlar
    def refresh_devices(self):
        names = hostapi_names()
        if self.api_var.get() not in names:
            self.api_var.set(names[default_hostapi_index()])
        api = names.index(self.api_var.get())
        self.inputs = devices_for(api, "in")
        self.outputs = devices_for(api, "out")
        self.in_box["values"] = [n for _, n in self.inputs]
        self.out_box["values"] = [n for _, n in self.outputs]
        default_in = sd.default.device[0]
        in_names = [n for i, n in self.inputs if i == default_in]
        self.in_var.set(in_names[0] if in_names else (self.inputs[0][1] if self.inputs else ""))
        cable = [n for _, n in self.outputs if "cable input" in n.lower()]
        self.out_var.set(cable[0] if cable else (self.outputs[0][1] if self.outputs else ""))
        self.update_cable_bar()

    @staticmethod
    def _dev(lst, name):
        return next((i for i, n in lst if n == name), None)

    # ----- karakter listesi
    def refresh_list(self):
        self.listbox.delete(0, "end")
        for i, name in enumerate(self.store.order):
            key = f"F{i + 1}" if i < len(FKEYS) else "  "
            self.listbox.insert("end", f"{key:>4}  {name}")
        if self.current in self.store.order:
            idx = self.store.order.index(self.current)
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(idx)
            self.listbox.see(idx)

    def on_list_select(self, _e):
        sel = self.listbox.curselection()
        if sel:
            self.select(self.store.order[sel[0]])

    def select(self, name):
        if name is None or name not in self.store.presets:
            return
        self.current = name
        params = self.store.presets[name]
        self._loading = True
        for key, var in self.vars.items():
            var.set(params[key])
            self._update_label(key)
        self._loading = False
        self.eng.select_preset(name)
        self.refresh_list()
        self.root.title(f"{APP_NAME} - {name}")
        if self.eng.running:
            self.set_status(f"Çalışıyor: {name}", "green")

    def move(self, d):
        if self.current is None:
            return
        o = self.store.order
        i = o.index(self.current)
        j = i + d
        if 0 <= j < len(o):
            o[i], o[j] = o[j], o[i]
            self.store.save()
            self.refresh_list()

    def rename(self):
        if self.current is None:
            return
        new = simpledialog.askstring("Yeniden adlandır", "Yeni ad:", initialvalue=self.current,
                                     parent=self.root)
        new = (new or "").strip()
        if not new or new == self.current:
            return
        if new in self.store.presets:
            messagebox.showerror("Hata", "Bu adda bir karakter zaten var.")
            return
        o = self.store.order
        o[o.index(self.current)] = new
        self.store.presets[new] = self.store.presets.pop(self.current)
        self.current = new
        self.eng.current = new
        self.store.save()
        self.refresh_list()

    def delete(self):
        if self.current is None or len(self.store.order) <= 1:
            return
        if not messagebox.askyesno("Sil", f"'{self.current}' silinsin mi?"):
            return
        i = self.store.order.index(self.current)
        self.store.order.remove(self.current)
        del self.store.presets[self.current]
        self.store.save()
        self.current = None
        self.select(self.store.order[min(i, len(self.store.order) - 1)])

    # ----- parametreler
    def slider_params(self):
        return {key: round(round(var.get() / self._step[key]) * self._step[key], 3)
                for key, var in self.vars.items()}

    def _update_label(self, key):
        v = self.slider_params()[key]
        if key == "pitch":
            txt = f"{v:+.0f}"
        elif key == "formant":
            txt = f"{v:+.1f}"
        elif v >= 10 or key in ("highpass", "lowpass"):
            txt = f"{v:.0f}"
        else:
            txt = f"{v:.2f}"
        self.val_lbls[key].config(text=txt)

    def on_slider(self, key):
        self._update_label(key)
        if self._loading:
            return
        if self._apply_job:
            self.root.after_cancel(self._apply_job)
        self._apply_job = self.root.after(120, lambda: self.eng.set_params(self.slider_params()))
        if self.current:
            saved = {k: round(v, 3) for k, v in self.store.presets[self.current].items()}
            mark = " *" if self.slider_params() != saved else ""
            self.root.title(f"{APP_NAME} - {self.current}{mark}")

    def save_current(self):
        if self.current is None:
            return self.save_as()
        self.store.presets[self.current] = self.slider_params()
        self.store.save()
        self.root.title(f"{APP_NAME} - {self.current}")
        self.set_status(f"'{self.current}' kaydedildi.", "green")

    def save_as(self):
        name = simpledialog.askstring("Yeni karakter", "Karakterin adı (örn. Bardın sesi):",
                                      parent=self.root)
        name = (name or "").strip()
        if not name:
            return
        if name in self.store.presets and not messagebox.askyesno(
                "Üzerine yaz", f"'{name}' zaten var. Üzerine yazılsın mı?"):
            return
        self.store.presets[name] = self.slider_params()
        if name not in self.store.order:
            self.store.order.append(name)
        self.store.save()
        self.select(name)
        self.set_status(f"'{name}' kaydedildi.", "green")

    def revert(self):
        if self.current:
            self.select(self.current)

    # ----- kısayollar, API, zamanlayıcı
    def setup_hotkeys(self):
        if keyboard is None:
            self.set_status("Kısayol tuşları devre dışı ('keyboard' paketi yüklenemedi).", "orange")
            return
        try:
            for i, k in enumerate(FKEYS):
                keyboard.add_hotkey(f"ctrl+{k}", lambda i=i: self.cmd_q.put(("index", i)))
        except Exception as e:
            self.set_status(f"Kısayollar kurulamadı: {e}", "orange")

    def api_status(self):
        return {"running": self.eng.running, "preset": self.current, "presets": list(self.store.order)}

    def tick(self):
        try:
            while True:
                cmd, arg = self.cmd_q.get_nowait()
                if cmd == "index" and arg < len(self.store.order):
                    self.select(self.store.order[arg])
                elif cmd == "preset":
                    self.select(arg)
                elif cmd == "cable_ready":
                    try:
                        vbcable.run_setup(arg)
                        self.set_status("Kurulum açıldı. Bitince bilgisayarı yeniden başlat.", "blue")
                    except Exception as e:
                        messagebox.showerror("VB-CABLE", str(e))
                elif cmd == "cable_error":
                    self.set_status("İndirme başarısız.", "red")
                    if messagebox.askyesno("VB-CABLE", f"İndirilemedi: {arg}\n\nİndirme sayfası açılsın mı?"):
                        webbrowser.open("https://vb-audio.com/Cable/")
        except queue.Empty:
            pass
        lvl = self.eng.level if self.eng.running else 0.0
        db = 20 * np.log10(lvl + 1e-6)
        self.meter["value"] = max(0, min(100, (db + 60) * 100 / 60))
        self.root.after(50, self.tick)

    # ----- başlat / durdur
    def set_status(self, text, color="gray"):
        self.status.config(text=text, foreground=color)

    def toggle(self):
        if self.eng.running:
            self.eng.stop()
            self.btn.config(text="▶ Başlat")
            self.set_status("Durduruldu")
            return
        in_dev = self._dev(self.inputs, self.in_var.get())
        out_dev = self._dev(self.outputs, self.out_var.get())
        if in_dev is None or out_dev is None:
            messagebox.showerror("Hata", "Mikrofon ve çıkış aygıtı seç.")
            return
        mon = None
        if self.mon_var.get():
            mon = sd.default.device[1]
            if mon is None or mon < 0 or mon == out_dev:
                mon = None
        try:
            self.eng.audio.gate_on = self.gate_var.get()
            self.eng.audio.params = self.slider_params()
            self.eng.start(in_dev, out_dev, mon)
        except Exception as e:
            self.eng.stop()
            messagebox.showerror("Ses hatası", f"{e}\n\nFarklı bir 'Sürücü' seçmeyi dene (MME en uyumlusudur).")
            return
        self.btn.config(text="■ Durdur")
        self.set_status(f"Çalışıyor: {self.current} ({self.eng.audio.sr} Hz)", "green")

    def on_close(self):
        self.eng.stop()
        if self.server:
            self.server.stop()
        if keyboard is not None:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass
        self.root.destroy()


def run():
    if os.name == "nt":
        try:  # yüksek DPI ekranlarda bulanıklığı önle
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()
