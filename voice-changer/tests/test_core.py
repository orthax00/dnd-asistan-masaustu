import json
import os
import sys
import tempfile
import time
import unittest
import urllib.request

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voicechanger.effects import BUILTIN_PRESETS, PitchShifter, FormantShifter, build_chain, full_params  # noqa: E402
from voicechanger.engine import PresetStore, AudioEngine  # noqa: E402
from voicechanger.control_server import ControlServer  # noqa: E402

SR = 48000


def run(fx, x):
    return np.concatenate([fx.process(x[i:i + 512]) for i in range(0, len(x), 512)])


def acf_pitch(y):
    ps = []
    for i in range(SR, len(y) - 4096, 2048):
        f = y[i:i + 4096] - y[i:i + 4096].mean()
        r = np.correlate(f, f, "full")[4095:]
        lo, hi = SR // 1000, SR // 60
        ps.append(SR / (lo + np.argmax(r[lo:hi])))
    return float(np.median(ps))


class EffectsTest(unittest.TestCase):
    def setUp(self):
        t = np.arange(SR * 3) / SR
        self.x = sum((0.3 / k) * np.sin(2 * np.pi * 150 * k * t) for k in range(1, 12)).astype(np.float32)

    def test_pitch_shift(self):
        for semi in (-5, 7):
            y = run(PitchShifter(SR, 2 ** (semi / 12)), self.x)
            self.assertAlmostEqual(acf_pitch(y), 150 * 2 ** (semi / 12), delta=2.0)

    def test_formant_identity(self):
        y = run(FormantShifter(SR, 1.0), self.x)
        d = 768
        self.assertLess(np.abs(y[d + 4096:-4096] - self.x[4096:-4096 - d]).max(), 1e-4)

    def test_all_presets_finite(self):
        for name, p in BUILTIN_PRESETS.items():
            y = run(build_chain(p, SR), self.x)
            self.assertTrue(np.isfinite(y).all(), name)
            self.assertLess(np.abs(y).max(), 4.0, name)

    def test_formant_follows_pitch_by_default(self):
        self.assertEqual(full_params({"pitch": -10})["formant"], -10)

    def test_callback(self):
        a = AudioEngine()
        a.set_params(BUILTIN_PRESETS["Kadın"])
        out = np.zeros((512, 2), np.float32)
        a._callback((np.random.randn(512, 1) * 0.1).astype(np.float32), out, 512, None, None)
        self.assertTrue(np.isfinite(out).all())


class StoreTest(unittest.TestCase):
    def test_new_builtins_added_deleted_stay_deleted(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "presets.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"order": ["Normal", "Benim"], "presets": {"Normal": {}, "Benim": {"pitch": 2}},
                           "known_builtins": ["Normal", "Goblin"]}, f)
            s = PresetStore(p)
            self.assertIn("Benim", s.order)
            self.assertIn("Kadın", s.order)
            self.assertNotIn("Goblin", s.order)
            s.save()
            self.assertEqual(PresetStore(p).order, s.order)


class ServerTest(unittest.TestCase):
    def test_select_preset(self):
        got = []
        presets = ["Normal", "Ejderha", "Kadın"]
        srv = ControlServer(lambda c, a: got.append((c, a)),
                            lambda: {"running": False, "preset": "Normal", "presets": presets}, port=47399)
        srv.start()
        try:
            base = "http://127.0.0.1:47399"
            st = json.load(urllib.request.urlopen(base + "/status"))
            self.assertEqual(st["presets"], presets)
            urllib.request.urlopen(urllib.request.Request(base + "/preset/Kad%C4%B1n", method="POST"))
            urllib.request.urlopen(urllib.request.Request(base + "/preset/index/1", method="POST"))
            time.sleep(0.05)
            self.assertEqual(got, [("preset", "Kadın"), ("preset", "Ejderha")])
        finally:
            srv.stop()


if __name__ == "__main__":
    unittest.main()
