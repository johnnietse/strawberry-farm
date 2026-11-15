"""
Strawberry canopy model: the "biology engine".

A mechanistic (physics and biochemistry) model, not a trained ML model. It turns what the
sensor node measures (air temperature, humidity, light) plus the LED setting into what the
plant is doing: photosynthesis, stomatal conductance and transpiration. The LED controller
uses it as the simulator it learns in, and the biology_engine service runs it on live data.

Equations
---------
- Leaf photosynthesis: Farquhar, von Caemmerer & Berry (1980) C3 model, Rubisco- and
  electron-transport-limited rates, with the Bernacchi et al. (2001) temperature responses
  of Kc, Ko and Gamma*, and peaked Arrhenius responses of Vcmax and Jmax (Medlyn et al. 2002;
  the same defaults as the plantecophys R package, Duursma 2015).
- Stomatal conductance: Medlyn et al. (2011) optimal model, gs = g0 + 1.6 (1 + g1/sqrt(D)) A/Ca.
  With g0 = 0 this fixes Ci/Ca = g1 / (g1 + sqrt(D)), so A has a closed form.
- Canopy: LAI split into layers with Gaussian quadrature, Beer-Lambert light extinction.
- Transpiration: Penman-Monteith with canopy conductance from the leaf layers and an
  aerodynamic conductance for a ventilated greenhouse.
- Spectrum: quantum yield per photon differs by wavelength. Relative quantum efficiency
  (McCree 1972, approximate): 448 nm 0.73, 655 nm 0.95, sunlight PAR on average 0.88.
  Blue light also opens stomata (phototropin response); modelled as a small g1 increase
  with the blue fraction (`blue_g1_gain`, an assumption to calibrate).

Parameters are generic C3 crop values chosen so a strawberry leaf saturates near
15 to 20 umol m-2 s-1 at 25 C and 400 ppm, the range reported for Fragaria x ananassa.
No strawberry-cultivar fit was found in the literature search; calibrate Vcmax25, Jmax25 and
g1 with a gas-exchange (A-Ci) curve on your cultivar when one is available.

Units: PPFD umol m-2 s-1, A umol CO2 m-2 s-1, gs mol H2O m-2 s-1, E mmol H2O m-2 s-1,
temperatures C, VPD kPa, CO2 umol mol-1.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

R = 8.314          # J mol-1 K-1
TREF = 298.15      # K
O2 = 210000.0      # umol mol-1

# Relative quantum efficiency per photon (McCree 1972 action spectrum, approximate)
RQE = {"blue": 0.73, "red": 0.95, "sun": 0.88}
# Photons per joule of radiant energy, umol J-1: 448 nm, 655 nm, sunlight PAR
UMOL_PER_J = {"blue": 3.75, "red": 5.48, "sun": 4.57}
# Lux per umol m-2 s-1 of photon flux (photopic weighting): sunlight, 448 nm, 655 nm.
# Narrow-band LEDs give few lux per photon; the TSL2591's lux formula is approximate for them.
LUX_PER_UMOL = {"sun": 54.0, "blue": 9.0, "red": 10.0}


@dataclass(frozen=True)
class PlantParams:
    vcmax25: float = 60.0      # umol m-2 s-1
    jmax25: float = 105.0      # umol m-2 s-1 (Jmax/Vcmax 1.75)
    rd25: float = 0.9          # umol m-2 s-1, dark respiration
    g1: float = 3.5            # kPa^0.5, Medlyn slope
    g0: float = 0.0            # mol m-2 s-1
    gmin: float = 0.01         # mol m-2 s-1, cuticular / night conductance
    alpha_max: float = 0.273   # electron yield per absorbed photon at RQE = 1 (0.24 for sunlight)
    theta: float = 0.85        # curvature of the J light response
    absorptance: float = 0.85
    lai: float = 2.5           # m2 leaf / m2 ground, greenhouse strawberry
    k_ext: float = 0.7         # canopy extinction coefficient
    blue_g1_gain: float = 0.2  # g1 multiplier per unit blue photon fraction (assumption)
    # temperature response (plantecophys defaults)
    ea_v: float = 58550.0
    ed_v: float = 200000.0
    ds_v: float = 629.26
    ea_j: float = 29680.0
    ed_j: float = 200000.0
    ds_j: float = 631.88
    ea_rd: float = 46390.0


@dataclass(frozen=True)
class LedParams:
    """LED board at the canopy. Photon flux values are design estimates: measure them with a
    quantum (PAR) sensor at plant height and set them here."""
    blue_ppfd_100: float = 60.0   # umol m-2 s-1 at the canopy, blue channel at 100 %
    red_ppfd_100: float = 60.0    # red channel at 100 %
    blue_watts_100: float = 3.85  # electrical input at 100 %: 4 x 2.75 V x 0.333 A / 0.95
    red_watts_100: float = 2.95   # 4 x 2.1 V x 0.333 A / 0.95
    area_m2: float = 0.25         # canopy area one LED board lights


@dataclass
class LightMix:
    sun: float = 0.0   # PPFD from daylight / room light
    blue: float = 0.0  # PPFD from the blue LEDs
    red: float = 0.0   # PPFD from the red LEDs

    @property
    def total(self) -> float:
        return self.sun + self.blue + self.red

    @property
    def blue_fraction(self) -> float:
        # sunlight PAR is about 20 % blue photons (400 to 500 nm)
        t = self.total
        return (self.blue + 0.2 * self.sun) / t if t > 0 else 0.0

    @property
    def rqe(self) -> float:
        t = self.total
        if t <= 0:
            return RQE["sun"]
        return (self.sun * RQE["sun"] + self.blue * RQE["blue"] + self.red * RQE["red"]) / t

    @property
    def radiant_wm2(self) -> float:
        return self.sun / UMOL_PER_J["sun"] + self.blue / UMOL_PER_J["blue"] + self.red / UMOL_PER_J["red"]


def led_light(blue_pct: float, red_pct: float, led: LedParams = LedParams()) -> LightMix:
    b = min(max(blue_pct, 0.0), 100.0) / 100.0
    r = min(max(red_pct, 0.0), 100.0) / 100.0
    return LightMix(0.0, b * led.blue_ppfd_100, r * led.red_ppfd_100)


def led_power_w(blue_pct: float, red_pct: float, led: LedParams = LedParams()) -> float:
    return (min(max(blue_pct, 0), 100) * led.blue_watts_100 + min(max(red_pct, 0), 100) * led.red_watts_100) / 100.0


def ambient_ppfd_from_lux(lux: float, blue_pct: float = 0.0, red_pct: float = 0.0,
                          led: LedParams = LedParams()) -> float:
    """Daylight PPFD from the TSL2591 reading, after removing the LEDs' own contribution.
    Assumes the sensor sees the same light as the canopy (it sits under the lid's light tube)."""
    if lux is None or lux < 0:
        return 0.0
    mix = led_light(blue_pct, red_pct, led)
    led_lux = mix.blue * LUX_PER_UMOL["blue"] + mix.red * LUX_PER_UMOL["red"]
    return max(lux - led_lux, 0.0) / LUX_PER_UMOL["sun"]


def svp_kpa(t_c: float) -> float:
    return 0.61078 * math.exp(17.27 * t_c / (t_c + 237.3))


def vpd_kpa(t_c: float, rh_pct: float) -> float:
    return max(svp_kpa(t_c) * (1.0 - min(max(rh_pct, 0.0), 100.0) / 100.0), 0.0)


def _arrh(k25: float, ea: float, tk: float) -> float:
    return k25 * math.exp(ea * (tk - TREF) / (TREF * R * tk))


def _peaked(k25: float, ea: float, ed: float, ds: float, tk: float) -> float:
    return (_arrh(k25, ea, tk) * (1 + math.exp((TREF * ds - ed) / (TREF * R)))
            / (1 + math.exp((tk * ds - ed) / (R * tk))))


@dataclass
class LeafResult:
    an: float      # net assimilation, umol m-2 s-1
    gs: float      # stomatal conductance to water, mol m-2 s-1
    ci: float      # intercellular CO2, umol mol-1
    limited: str   # "rubisco", "light" or "dark"


def leaf_photosynthesis(ppfd_abs: float, t_leaf: float, vpd: float, co2: float = 420.0,
                        rqe: float = RQE["sun"], blue_fraction: float = 0.2,
                        p: PlantParams = PlantParams()) -> LeafResult:
    """One leaf. `ppfd_abs` is PPFD absorbed by the leaf (already times absorptance)."""
    tk = t_leaf + 273.15
    kc = _arrh(404.9, 79430.0, tk)
    ko = _arrh(278400.0, 36380.0, tk)
    gstar = _arrh(42.75, 37830.0, tk)
    km = kc * (1 + O2 / ko)
    vcmax = _peaked(p.vcmax25, p.ea_v, p.ed_v, p.ds_v, tk)
    jmax = _peaked(p.jmax25, p.ea_j, p.ed_j, p.ds_j, tk)
    rd = _arrh(p.rd25, p.ea_rd, tk) * (0.7 if ppfd_abs > 10 else 1.0)  # light inhibition of Rd

    alpha = p.alpha_max * rqe
    q = alpha * max(ppfd_abs, 0.0)
    b = q + jmax
    j = (b - math.sqrt(max(b * b - 4 * p.theta * q * jmax, 0.0))) / (2 * p.theta)

    if q <= 0:
        return LeafResult(-rd, p.gmin, co2, "dark")

    g1 = p.g1 * (1 + p.blue_g1_gain * blue_fraction)
    d = max(vpd, 0.05)
    ci = co2 * g1 / (g1 + math.sqrt(d))
    ac = vcmax * (ci - gstar) / (ci + km)
    aj = j / 4.0 * (ci - gstar) / (ci + 2 * gstar)
    ag = min(ac, aj)
    an = ag - rd
    if an <= 0:
        return LeafResult(an, p.gmin, ci, "dark")
    gs = max(p.g0 + 1.6 * (1 + g1 / math.sqrt(d)) * an / co2, p.gmin)
    return LeafResult(an, gs, ci, "rubisco" if ac < aj else "light")


@dataclass
class CanopyResult:
    an: float           # canopy net assimilation, umol CO2 m-2 ground s-1
    gc: float           # canopy conductance to water, mol m-2 s-1
    transpiration: float  # mmol H2O m-2 ground s-1
    ppfd: float         # total PPFD above the canopy
    blue_fraction: float
    vpd: float

    @property
    def transpiration_g_m2_h(self) -> float:
        return self.transpiration * 18.015e-3 * 3600.0

    @property
    def an_g_m2_h(self) -> float:
        """CO2 fixed, g CO2 m-2 h-1."""
        return self.an * 44.01e-6 * 3600.0


# 5-point Gauss-Legendre on [0, 1]
_GL_X = (0.0469101, 0.2307653, 0.5, 0.7692347, 0.9530899)
_GL_W = (0.1184634, 0.2393143, 0.2844444, 0.2393143, 0.1184634)


def canopy(light: LightMix, t_air: float, rh: float, co2: float = 420.0,
           p: PlantParams = PlantParams(), wind_ms: float = 0.3) -> CanopyResult:
    vpd = vpd_kpa(t_air, rh)
    rqe = light.rqe
    bf = light.blue_fraction
    an_sum = 0.0
    g_sum = 0.0
    for x, w in zip(_GL_X, _GL_W):
        depth = x * p.lai
        # absorbed per unit leaf area at this depth (Beer-Lambert)
        absorbed = light.total * p.absorptance * p.k_ext * math.exp(-p.k_ext * depth)
        leaf = leaf_photosynthesis(absorbed, t_air, vpd, co2, rqe, bf, p)
        an_sum += w * leaf.an
        g_sum += w * leaf.gs
    an_c = an_sum * p.lai
    gc = g_sum * p.lai  # mol m-2 s-1

    # Penman-Monteith with net radiation from absorbed radiant energy (LED or daylight)
    patm = 101.325
    rho_cp = 1204.0       # J m-3 K-1 (rho * cp at 20 C)
    lam = 2.45e6          # J kg-1
    gamma = 0.0665        # kPa K-1
    delta = 4098 * svp_kpa(t_air) / (t_air + 237.3) ** 2
    rn = light.radiant_wm2 * p.absorptance * (1 - math.exp(-p.k_ext * p.lai))
    rn += 0.0 if light.total > 0 else -5.0  # small net long-wave loss at night
    ga = 0.01 + 0.02 * wind_ms                   # m s-1, aerodynamic conductance in a greenhouse
    molar_vol = 0.0224 * (t_air + 273.15) / 273.15 * 101.325 / patm   # m3 mol-1
    gc_ms = gc * molar_vol                        # mol m-2 s-1 to m s-1
    le = (delta * rn + rho_cp * vpd * ga) / (delta + gamma * (1 + ga / max(gc_ms, 1e-6)))
    e_kg = max(le, 0.0) / lam                     # kg m-2 s-1
    e_mmol = e_kg / 18.015e-3 * 1000.0
    return CanopyResult(an_c, gc, e_mmol, light.total, bf, vpd)


def strawberry(**overrides) -> PlantParams:
    return replace(PlantParams(), **overrides)


if __name__ == "__main__":
    for ppfd in (0, 100, 300, 600, 1000, 1500):
        leaf = leaf_photosynthesis(ppfd * 0.85, 25.0, 1.0)
        c = canopy(LightMix(sun=ppfd), 25.0, 65.0)
        print(f"PPFD {ppfd:5d}: leaf A {leaf.an:6.2f} ({leaf.limited:7s}) gs {leaf.gs:.3f} | "
              f"canopy A {c.an:6.2f} umol/m2/s, E {c.transpiration_g_m2_h:6.1f} g/m2/h")
