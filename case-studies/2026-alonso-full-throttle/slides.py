"""Render the 5-slide Instagram carousel (1080x1350 PNG, Spanish) into slides/.

Run `python analysis.py` first — this reads the per-metre series it caches.
Palette: blue/red diverging pair + dark surface from a CVD-validated
reference palette; every bar is also direct-labelled.
"""

import pickle
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from analysis import CACHE_DIR, THE_RACE  # noqa: E402

OUT = Path(__file__).resolve().parent / "slides"
OUT.mkdir(exist_ok=True)
_raw = pickle.load(open(CACHE_DIR / "series.pkl", "rb"))
D = {
    t: dict(
        r={
            "ft": r["full_throttle_loss_s"],
            "nonft": r["rest_of_lap_loss_s"],
            "gap": r["official_gap_s"],
        },
        g=r["_distance_m"],
        delta=r["_delta_s"],
        ft=r["_full_throttle"],
        vP=r["_speed_pole"],
        vA=r["_speed_alo"],
    )
    for t, r in _raw.items()
}
BG = "#1a1a19"
INK = "#f0efec"
INK2 = "#c3c2b7"
MUTED = "#8a8983"
GRID = "#383835"
RED = "#e66767"
BLUE = "#3987e5"
AM = "#00a37a"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "text.color": INK,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "axes.edgecolor": GRID,
    }
)
ES = {
    "Hungaroring": "Hungría",
    "Zandvoort": "Zandvoort",
    "Monza": "Monza",
    "Madrid": "Madrid",
    "Baku": "Bakú",
    "Sepang": "Sepang",
    "Singapore": "Singapur",
}
TR = THE_RACE
FOOT = "github.com/AMonten/f1-race-analytics/case-studies  ·  datos: OpenF1"


def fig(n):
    f = plt.figure(figsize=(10.8, 13.5), dpi=100, facecolor=BG)
    f.text(0.06, 0.035, FOOT, fontsize=15, color=MUTED)
    f.text(0.94, 0.035, f"{n}/5", fontsize=15, color=MUTED, ha="right")
    f.add_artist(plt.Line2D([0.06, 0.16], [0.94, 0.94], color=AM, lw=6, transform=f.transFigure))
    return f


def save(f, n):
    f.savefig(OUT / f"slide{n}.png", facecolor=BG)
    plt.close(f)


# 1 cover
f = fig(1)
f.text(0.06, 0.88, "¿CHASIS O HONDA?", fontsize=58, weight="bold")
f.text(
    0.06,
    0.825,
    "The Race dice que Alonso fue más rápido que la pole\nen las curvas de Sepang y Singapur.\nLo verifiqué con mi propio código y datos abiertos.",
    fontsize=24,
    color=INK2,
    va="top",
    linespacing=1.4,
)
f.text(0.06, 0.56, "Monza", fontsize=64, weight="bold", color=BLUE)
f.text(0.06, 0.51, "✓ confirmado: casi todo el gap (3.1 de 3.4 s) en rectas", fontsize=25, va="top")
f.text(0.06, 0.40, "Sepang · Singapur", fontsize=64, weight="bold", color=RED)
f.text(0.06, 0.35, "✗ no reproduzco la ventaja en curvas: pierde ~1 s ahí", fontsize=25, va="top")
f.text(
    0.06,
    0.22,
    "Y mi primera versión SÍ daba lo mismo que The Race.\nEra un bug. →",
    fontsize=26,
    color=INK2,
    va="top",
    linespacing=1.4,
)
f.text(0.06, 0.10, "Qualy 2026 · mejor vuelta de ALO vs vuelta de pole", fontsize=18, color=MUTED)
save(f, 1)

# 2 bars
f = fig(2)
f.text(0.06, 0.90, "Dónde pierde el tiempo Alonso", fontsize=40, weight="bold", va="top")
f.text(
    0.06,
    0.845,
    "Solo en Monza las rectas explican casi todo el gap",
    fontsize=21,
    color=INK2,
    va="top",
)
f.text(0.06, 0.80, "■", color=RED, fontsize=24, va="top")
f.text(0.095, 0.80, "tramos a fondo (rectas: motor, drag)", fontsize=21, va="top")
f.text(0.06, 0.765, "■", color=BLUE, fontsize=24, va="top")
f.text(0.095, 0.765, "resto (curvas, frenada, tracción, gomas, piloto)", fontsize=21, va="top")
ax = f.add_axes([0.20, 0.13, 0.72, 0.60], facecolor=BG)
trks = list(D)[::-1]
y = np.arange(len(trks))
h = 0.36
ft = [D[t]["r"]["ft"] for t in trks]
nf = [D[t]["r"]["nonft"] for t in trks]
ax.barh(y + h / 2 + 0.01, ft, h, color=RED)
ax.barh(y - h / 2 - 0.01, nf, h, color=BLUE)
for i, t in enumerate(trks):
    a, b = ft[i], nf[i]
    ax.text(a + 0.08, y[i] + h / 2, f"+{a:.1f}", va="center", fontsize=17, color=INK)
    ax.text(
        (b + 0.08) if b >= 0 else (b - 0.08),
        y[i] - h / 2,
        f"{b:+.1f}",
        va="center",
        ha="left" if b >= 0 else "right",
        fontsize=17,
        weight="bold" if b < 0 else "normal",
        color=INK,
    )
    ax.text(
        4.35,
        y[i],
        f"gap\n{D[t]['r']['gap']:.2f}s",
        va="center",
        ha="right",
        fontsize=14,
        color=MUTED,
        linespacing=1.1,
    )
ax.set_yticks(y)
ax.set_yticklabels([ES[t] for t in trks], fontsize=21, color=INK)
ax.axvline(0, color=INK2, lw=1.5)
ax.set_xlim(-0.6, 4.4)
ax.tick_params(axis="x", labelsize=15)
ax.grid(axis="x", color=GRID, lw=1)
ax.set_axisbelow(True)
for s in ["top", "right", "left"]:
    ax.spines[s].set_visible(False)
ax.set_xlabel("segundos perdidos vs la pole", fontsize=17, labelpad=12)
save(f, 2)

# 3 singapore trace
f = fig(3)
S = D["Singapore"]
f.text(0.06, 0.90, "Singapur, vuelta a vuelta", fontsize=40, weight="bold", va="top")
f.text(
    0.06,
    0.845,
    "Diferencia acumulada ALO vs VER (pole) a lo largo de la vuelta",
    fontsize=21,
    color=INK2,
    va="top",
)
ax = f.add_axes([0.13, 0.47, 0.81, 0.33], facecolor=BG)
g = S["g"] / 1000
ftm = S["ft"]
ax.fill_between(g, -3, 6, where=ftm, color=RED, alpha=0.16, lw=0, step="mid")
ax.plot(g, S["delta"], color=INK, lw=2.5)
ax.set_xlim(0, g[-1])
ax.set_ylim(-0.2, 3.2)
ax.axhline(0, color=GRID, lw=1)
ax.set_ylabel("ALO detrás (s)", fontsize=17)
ax.tick_params(labelsize=15)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
ax.text(
    0.02, 0.92, "zonas sombreadas = VER a fondo", transform=ax.transAxes, fontsize=16, color=RED
)
ax.text(
    g[-1] - 0.05,
    S["delta"][-1] + 0.12,
    f"{S['r']['gap']:.2f} s",
    ha="right",
    fontsize=20,
    weight="bold",
)
ax2 = f.add_axes([0.13, 0.13, 0.81, 0.22], facecolor=BG)
ax2.plot(g, S["vP"], color=BLUE, lw=2, label="VER")
ax2.plot(g, S["vA"], color=AM, lw=2, label="ALO")
ax2.set_xlim(0, g[-1])
ax2.set_ylabel("km/h", fontsize=17)
ax2.set_xlabel("distancia (km)", fontsize=17)
ax2.tick_params(labelsize=15)
for s in ["top", "right"]:
    ax2.spines[s].set_visible(False)
ax2.legend(frameon=False, fontsize=16, loc="lower right", labelcolor=INK, ncol=2)
r = S["r"]
f.text(
    0.06,
    0.44,
    f"Pierde en casi todos lados: +{r['ft']:.1f} s a fondo, +{r['nonft']:.1f} s en el resto.\nEl escalón del km 3.6–4.2 es un hueco en los datos de ALO.",
    fontsize=19,
    color=INK,
    va="top",
    linespacing=1.4,
)
save(f, 3)

# 4 table vs The Race
f = fig(4)
f.text(0.06, 0.90, "Mi código vs The Race", fontsize=40, weight="bold", va="top")
f.text(0.06, 0.845, "Tiempo perdido a fondo / en el resto (s)", fontsize=21, color=INK2, va="top")
cols = [0.06, 0.33, 0.62]
y0 = 0.76
f.text(cols[1], y0, "The Race (GPS)", fontsize=19, color=MUTED, weight="bold")
f.text(cols[2], y0, "Mío (OpenF1)", fontsize=19, color=MUTED, weight="bold")
for i, t in enumerate(D):
    yy = y0 - 0.075 * (i + 1)
    a, b = TR[t]
    r = D[t]["r"]
    f.add_artist(
        plt.Line2D(
            [0.06, 0.94], [yy + 0.045, yy + 0.045], color=GRID, lw=1, transform=f.transFigure
        )
    )
    f.text(cols[0], yy, ES[t], fontsize=23, weight="bold")
    f.text(cols[1], yy, f"{a:.2f} / {b:+.2f}", fontsize=23, color=INK2)
    f.text(cols[2], yy, f"{r['ft']:.2f} / {r['nonft']:+.2f}", fontsize=23)
f.text(
    0.06,
    0.17,
    "Monza coincide casi al centésimo y Bakú por ±0.05 s. Hungría, Zandvoort\ny Madrid, mismo orden de magnitud. En Sepang y Singapur no reproduzco\nla ventaja en curvas: con mis datos, Alonso pierde ~1 s también ahí.",
    fontsize=18,
    color=INK2,
    va="top",
    linespacing=1.45,
)
save(f, 4)

# 5 method
f = fig(5)
f.text(0.06, 0.90, "El bug que casi publico", fontsize=40, weight="bold", va="top")
f.text(
    0.06,
    0.84,
    'V1: distancia integrando la velocidad. Daba "más rápido que la pole\nen curvas" en 3 pistas, igual que The Race. Pero los puntos de frenada\nde los dos autos quedaban corridos unos metros, y eso movía tiempo de\nlas curvas a las rectas.',
    fontsize=19,
    color=INK2,
    va="top",
    linespacing=1.45,
)
f.text(
    0.06,
    0.69,
    "V2: posición GPS de OpenF1, con ALO proyectado sobre la trazada\nde la pole. La diferencia final cuadra con el gap oficial en las 7 pistas.",
    fontsize=19,
    color=INK,
    va="top",
    linespacing=1.45,
)
f.text(
    0.06,
    0.605,
    '"A fondo" = acelerador de la pole ≥ 98 % (con 95 % o 99 % cambia < 0.15 s).',
    fontsize=18,
    color=INK2,
    va="top",
)
f.text(0.06, 0.53, "Ojo", fontsize=26, weight="bold", va="top")
f.text(
    0.06,
    0.49,
    '• Datos a ~4 Hz con huecos de ~1 s: es un orden de magnitud (±0.3–0.5 s).\n• No separa cuánto es motor y cuánto aerodinámica/drag.\n• La pole sale de Q3: pista más rápida que en la Q1/Q2 de ALO.\n• The Race usa GPS propio y otra definición de "a fondo".\n• Que el total cuadre no valida el reparto entre zonas.',
    fontsize=18,
    color=INK2,
    va="top",
    linespacing=1.55,
)
f.text(
    0.06,
    0.27,
    "Con los datos abiertos analizados, no consigo\nreproducir la ventaja de Alonso en curvas que\ndescribe el artículo para Sepang y Singapur.",
    fontsize=23,
    weight="bold",
    va="top",
    linespacing=1.45,
)
save(f, 5)
