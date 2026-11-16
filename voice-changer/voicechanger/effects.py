"""Gerçek zamanlı ses efektleri (blok tabanlı, düşük gecikme).

Her efekt `process(block) -> block` arayüzüne sahiptir; block float32 mono numpy dizisidir.
Bir ses karakteri (preset) bir parametre sözlüğüdür; `build_chain(params, sr)` onu efekt zincirine çevirir.
"""
import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi


class PitchShifter:
    """Gecikme hattı tabanlı pitch shifter (iki okuma kafası, sin² çapraz geçiş).

    ratio > 1 sesi inceltir, ratio < 1 kalınlaştırır. Gecikme ~ window/2.
    """

    def __init__(self, sr, ratio=1.0, window_ms=40.0):
        self.ratio = ratio
        self.W = max(64, int(sr * window_ms / 1000))
        size = 1
        while size < self.W * 4:
            size *= 2
        self.N = size
        self.buf = np.zeros(self.N, dtype=np.float32)
        self.w = 0  # mutlak yazma sayacı
        self.phase = 0.0

    def process(self, x):
        n = len(x)
        idx = (self.w + np.arange(n)) & (self.N - 1)
        self.buf[idx] = x
        self.w += n
        if abs(self.ratio - 1.0) < 1e-4:
            return x.copy()
        step = (1.0 - self.ratio) / self.W
        phases = (self.phase + step * np.arange(1, n + 1)) % 1.0
        self.phase = float(phases[-1])
        abs_idx = self.w - n + np.arange(n)
        out = np.zeros(n, dtype=np.float32)
        for off in (0.0, 0.5):
            p = (phases + off) % 1.0
            pos = abs_idx - (p * self.W + 1.0)
            i0 = np.floor(pos).astype(np.int64)
            frac = (pos - i0).astype(np.float32)
            a = self.buf[i0 & (self.N - 1)]
            b = self.buf[(i0 + 1) & (self.N - 1)]
            g = np.sin(np.pi * p).astype(np.float32) ** 2
            out += (a + (b - a) * frac) * g
        return out


class FormantShifter:
    """STFT + kepstrum zarfı ile formant (gırtlak rengi) kaydırma; perdeyi değiştirmez.

    factor > 1: formantlar yukarı (daha küçük gırtlak, kadın/çocuk), < 1: aşağı (erkek/iri).
    Ek gecikme: N - H örnek (~16 ms @48 kHz).
    """

    def __init__(self, sr, factor=1.0, N=1024, H=256, lifter_ms=1.0):
        self.factor, self.N, self.H = factor, N, H
        self.win = np.sqrt(0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N) / N)).astype(np.float32)
        self.inbuf = np.zeros(N, dtype=np.float32)
        self.outbuf = np.zeros(N, dtype=np.float32)
        self.pending_in = np.zeros(0, dtype=np.float32)
        self.ready = np.zeros(0, dtype=np.float32)
        self.lifter = max(8, int(sr * lifter_ms / 1000))
        K = N // 2 + 1
        self.src = np.clip(np.arange(K) / factor, 0, K - 1)  # çıkış k <- giriş k/factor
        self.norm = 1.0 / (np.sum(self.win ** 2) / H)

    def _frame(self, frame):
        X = np.fft.rfft(frame * self.win)
        mag = np.abs(X) + 1e-9
        cep = np.fft.irfft(np.log(mag))
        L = self.lifter
        cep[L:-L] = 0.0
        env = np.exp(np.fft.rfft(cep).real)
        k = np.arange(len(env))
        new_env = np.interp(self.src, k, env)
        Y = X * (new_env / env)
        return (np.fft.irfft(Y) * self.win).astype(np.float32)

    def process(self, x):
        H, N = self.H, self.N
        data = np.concatenate([self.pending_in, x])
        outs = []
        i = 0
        while len(data) - i >= H:
            self.inbuf = np.concatenate([self.inbuf[H:], data[i:i + H]])
            self.outbuf += self._frame(self.inbuf) * self.norm
            outs.append(self.outbuf[:H].copy())
            self.outbuf = np.concatenate([self.outbuf[H:], np.zeros(H, dtype=np.float32)])
            i += H
        self.pending_in = data[i:]
        ready = np.concatenate([self.ready] + outs) if outs else self.ready
        n = len(x)
        if len(ready) >= n:
            out, self.ready = ready[:n], ready[n:]
        else:  # başlangıçta yeterli çıktı yoksa sessizlikle doldur
            out = np.concatenate([np.zeros(n - len(ready), dtype=np.float32), ready])
            self.ready = np.zeros(0, dtype=np.float32)
        return out.astype(np.float32)


class _DelayLine:
    """D örnek gecikmeli geri beslemeli hat; blok, D'den küçük parçalara bölünerek vektörel işlenir."""

    def __init__(self, D):
        self.D = max(1, int(D))
        self.buf = np.zeros(self.D, dtype=np.float32)
        self.pos = 0

    def run(self, x, fn):
        out = np.empty_like(x)
        i, n = 0, len(x)
        while i < n:
            m = min(n - i, self.D - self.pos)
            old = self.buf[self.pos:self.pos + m].copy()
            new, y = fn(x[i:i + m], old)
            self.buf[self.pos:self.pos + m] = new
            out[i:i + m] = y
            self.pos = (self.pos + m) % self.D
            i += m
        return out


class Echo:
    """Geri beslemeli yankı."""

    def __init__(self, sr, delay_ms=220.0, feedback=0.45, mix=0.5):
        self.line = _DelayLine(sr * delay_ms / 1000)
        self.feedback, self.mix = feedback, mix

    def process(self, x):
        fb, mix = self.feedback, self.mix
        return self.line.run(x, lambda s, d: (s + d * fb, s + d * mix))


class Reverb:
    """Schroeder reverb: 4 paralel comb + 2 seri allpass + koyulaştırma filtresi."""

    COMBS = (1557, 1617, 1491, 1422)
    ALLPASS = (556, 441)

    def __init__(self, sr, mix=0.3, size=0.8):
        k = sr / 44100
        g = 0.70 + 0.28 * min(max(size, 0.0), 1.0)
        self.combs = [(_DelayLine(d * k), g) for d in self.COMBS]
        self.aps = [_DelayLine(d * k) for d in self.ALLPASS]
        self.tone = Filter(sr, "lowpass", 4500, order=2)
        self.mix = mix

    def process(self, x):
        wet = np.zeros_like(x)
        for line, g in self.combs:
            wet += line.run(x, lambda s, d, g=g: (s + d * g, s + d * g))
        wet *= 0.25
        for line in self.aps:
            # v[n] = x[n] + 0.5 v[n-D];  y[n] = -0.5 v[n] + v[n-D]
            wet = line.run(wet, lambda s, d: (s + 0.5 * d, -0.5 * (s + 0.5 * d) + d))
        wet = self.tone.process(wet)
        return (x + wet * self.mix * 0.45).astype(np.float32)


class RingMod:
    """Robot sesi: ses sinüs taşıyıcı ile çarpılır."""

    def __init__(self, sr, freq=60.0, mix=1.0):
        self.sr, self.freq, self.mix, self.t = sr, freq, mix, 0

    def process(self, x):
        n = len(x)
        t = (self.t + np.arange(n)) / self.sr
        self.t += n
        carrier = np.sin(2 * np.pi * self.freq * t).astype(np.float32)
        return (x * (1 - self.mix) + x * carrier * self.mix * 1.6).astype(np.float32)


class Filter:
    """Durumlu butterworth filtresi (sos)."""

    def __init__(self, sr, kind, freq, order=4):
        self.sos = butter(order, freq, btype=kind, fs=sr, output="sos")
        self.zi = sosfilt_zi(self.sos) * 0.0

    def process(self, x):
        y, self.zi = sosfilt(self.sos, x, zi=self.zi)
        return y.astype(np.float32)


class Distortion:
    def __init__(self, drive=4.0):
        self.drive = drive

    def process(self, x):
        return (np.tanh(x * self.drive) / np.tanh(self.drive)).astype(np.float32)


class Tremolo:
    def __init__(self, sr, rate=7.0, depth=0.6):
        self.sr, self.rate, self.depth, self.t = sr, rate, depth, 0

    def process(self, x):
        n = len(x)
        t = (self.t + np.arange(n)) / self.sr
        self.t += n
        lfo = 1 - self.depth * (0.5 + 0.5 * np.sin(2 * np.pi * self.rate * t))
        return (x * lfo).astype(np.float32)


class Doubler:
    """Kaydırılmış ses + orijinal ses karışımı (iblis / iki katmanlı ses)."""

    def __init__(self, shifter, dry, wet_gain=1.0):
        self.shifter, self.dry = shifter, dry
        self.wet_gain = wet_gain

    def process(self, x):
        y = self.shifter.process(x) * self.wet_gain
        if self.dry > 0:
            y = y + x * self.dry
        return y


class Chain:
    def __init__(self, *fx):
        self.fx = fx

    def process(self, x):
        for f in self.fx:
            x = f.process(x)
        return x


class NoiseGate:
    """Basit gürültü kapısı: blok RMS eşik altındaysa sesi yumuşakça kısar."""

    def __init__(self, threshold_db=-50.0):
        self.threshold = 10 ** (threshold_db / 20)
        self.gain = 0.0

    def process(self, x):
        rms = float(np.sqrt(np.mean(x * x)) + 1e-12)
        # açılış anında, kapanış yavaş (kelime sonları kesilmesin)
        new_gain = 1.0 if rms > self.threshold else self.gain * 0.6
        ramp = np.linspace(self.gain, new_gain, len(x), dtype=np.float32)
        self.gain = new_gain
        return x * ramp


# ---------------------------------------------------------------- parametreler

# (anahtar, etiket, min, max, varsayılan, adım)
PARAMS = [
    ("pitch", "Perde (yarım ton)", -12, 12, 0, 1),
    ("formant", "Gırtlak / formant (yarım ton)", -12, 12, 0, 0.5),
    ("dry", "Orijinal ses karışımı", 0, 1, 0, 0.05),
    ("drive", "Hırıltı / distorsiyon", 0, 8, 0, 0.5),
    ("robot", "Robot (metalik)", 0, 1, 0, 0.05),
    ("highpass", "Bas kes (Hz, 0=kapalı)", 0, 1000, 0, 50),
    ("lowpass", "Tiz kes (Hz, 0=kapalı)", 0, 8000, 0, 250),
    ("tremolo", "Titreme (yaşlı ses)", 0, 0.8, 0, 0.05),
    ("reverb", "Reverb (mağara / salon)", 0, 1, 0, 0.05),
    ("echo", "Yankı", 0, 0.8, 0, 0.05),
    ("gain", "Ses seviyesi", 0.2, 2.5, 1.0, 0.1),
]
DEFAULTS = {k: d for k, _, _, _, d, _ in PARAMS}

BUILTIN_PRESETS = {
    "Normal": {},
    "Kadın": {"pitch": 5, "formant": 2.5, "highpass": 120},
    "Erkek": {"pitch": -5, "formant": -2.5},
    "Kalın erkek (bas)": {"pitch": -8, "formant": -3.5, "lowpass": 6000, "gain": 1.1},
    "Kız çocuk": {"pitch": 9, "formant": 4.5, "highpass": 200},
    "Erkek çocuk": {"pitch": 6, "formant": 3.5, "highpass": 150},
    "Yaşlı kadın": {"pitch": 3, "formant": 2, "tremolo": 0.25, "highpass": 150},
    "Anlatıcı": {"pitch": -2, "reverb": 0.25, "highpass": 80},
    "Ejderha": {"pitch": -10, "dry": 0.25, "drive": 2.5, "lowpass": 4000, "reverb": 0.45, "gain": 0.9},
    "Goblin": {"pitch": 6, "drive": 1.5, "highpass": 300, "tremolo": 0.1},
    "Cüce": {"pitch": -3, "drive": 1.0, "lowpass": 5000, "gain": 1.1},
    "Elf": {"pitch": 3, "highpass": 150, "reverb": 0.2},
    "Yaşlı büyücü": {"pitch": -2, "tremolo": 0.3, "reverb": 0.15, "highpass": 120},
    "Ork": {"pitch": -6, "drive": 3.5, "lowpass": 4500, "gain": 1.1},
    "İblis": {"pitch": -12, "dry": 0.6, "drive": 1.5, "reverb": 0.35},
    "Hayalet": {"pitch": 2, "tremolo": 0.35, "reverb": 0.7, "echo": 0.3, "highpass": 250},
    "Peri": {"pitch": 9, "reverb": 0.3, "highpass": 300},
    "Golem / Robot": {"pitch": -4, "robot": 0.8, "lowpass": 5000},
}


def full_params(p):
    """Eksik değerleri doldurur. Formant verilmemişse perdeyi izler (klasik kaydırma)."""
    p = p or {}
    out = dict(DEFAULTS)
    out.update({k: v for k, v in p.items() if k in DEFAULTS})
    if "formant" not in p:
        out["formant"] = out["pitch"]
    return out


def build_chain(params, sr):
    p = full_params(params)
    fx = []
    ratio = 2 ** (p["pitch"] / 12)
    if p["dry"] > 0:
        fx.append(Doubler(PitchShifter(sr, ratio), p["dry"], 1.0 - 0.3 * p["dry"]))
    else:
        fx.append(PitchShifter(sr, ratio))
    # perde kaydırıcı formantları da 'pitch' kadar kaydırır; farkı STFT ile düzelt
    warp = p["formant"] - p["pitch"]
    if abs(warp) >= 0.25:
        fx.append(FormantShifter(sr, 2 ** (warp / 12)))
    if p["highpass"] > 0:
        fx.append(Filter(sr, "highpass", p["highpass"], order=2))
    if p["drive"] > 0:
        fx.append(Distortion(p["drive"]))
    if p["robot"] > 0:
        fx.append(RingMod(sr, 55.0, p["robot"]))
    if 0 < p["lowpass"] < sr / 2 - 100:
        fx.append(Filter(sr, "lowpass", p["lowpass"]))
    if p["tremolo"] > 0:
        fx.append(Tremolo(sr, 6.5, p["tremolo"]))
    if p["echo"] > 0:
        fx.append(Echo(sr, 220, 0.4, p["echo"]))
    if p["reverb"] > 0:
        fx.append(Reverb(sr, p["reverb"]))
    gain = p["gain"]
    if gain != 1.0:
        fx.append(_Gain(gain))
    return Chain(*fx)


class _Gain:
    def __init__(self, g):
        self.g = np.float32(g)

    def process(self, x):
        return x * self.g
