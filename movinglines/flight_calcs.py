"""
    Purpose:
        Flight speed and fuel management calculations.
        Provides conversions between Indicated Airspeed (IAS/CAS), True Airspeed (TAS),
        and Mach number using an atmospheric column model (default: ICAO standard
        atmosphere). Also provides a preliminary fuel rate estimate as a function of
        altitude and IAS.
        Assumes Calibrated Airspeed (CAS) == Indicated Airspeed (IAS) throughout.
    Inputs:
        alt_m:     altitude [m] (scalar or array)
        ias_ms:    Indicated / Calibrated Airspeed [m/s]
        mach:      Mach number [dimensionless]
        atm:       optional pre-computed atmosphere dict from load_atmosphere()
    Outputs:
        tas_ms:           True Airspeed [m/s]
        fuel_rate_kghr:   fuel consumption rate [kg/hr]
        atm dict:         T [K], P [Pa], rho [kg/m³], a [m/s] at requested altitudes
    Dependencies:
        numpy
    Required files:
        None (ICAO standard atmosphere used by default)
    Example:
        import numpy as np
        from movinglines import flight_calcs as fc
        alt = np.array([0.0, 5000.0, 10000.0])
        atm = fc.load_atmosphere(alt)
        tas = fc.ias_to_tas(np.array([100.0, 120.0, 140.0]), alt, atm=atm)
        print(tas)
    Modification History:
        Written: Samuel LeBlanc, 2026-08-14, Santa Cruz, CA
                - initial module: ICAO standard atmosphere, IAS-to-TAS,
                  Mach-to-TAS, and preliminary fuel rate calculation
"""

import numpy as np

# ---------------------------------------------------------------------------
# ICAO standard atmosphere constants
# ---------------------------------------------------------------------------
T0        = 288.15     # sea-level temperature [K]
P0        = 101325.0   # sea-level pressure [Pa]
RHO0      = 1.225      # sea-level density [kg/m³]
G         = 9.80665    # gravitational acceleration [m/s²]
R_AIR     = 287.05287  # specific gas constant for dry air [J/(kg·K)]
GAMMA     = 1.4        # ratio of specific heats [-]
A0        = 340.294    # speed of sound at sea level [m/s]
L_TROP    = -0.0065    # temperature lapse rate, troposphere [K/m]
H_TROP    = 11000.0    # tropopause altitude [m]
T_TROP    = 216.65     # tropopause / lower-stratosphere temperature [K]
H_STRAT1  = 20000.0    # base of middle stratosphere [m]
L_STRAT1  = 0.001      # lapse rate, middle stratosphere [K/m]
H_STRAT2  = 32000.0    # top of supported altitude range [m]


def load_atmosphere(alt_m):
    """
    Return ICAO standard atmosphere properties at the given altitude(s).

    Covers three layers:
      Troposphere     0 – 11 000 m  (T lapse rate –6.5 K/km)
      Lower strat.   11 000 – 20 000 m  (isothermal at 216.65 K)
      Middle strat.  20 000 – 32 000 m  (T lapse rate +1.0 K/km)

    Inputs:
        alt_m: altitude [m], scalar or array

    Outputs:
        dict with keys
            T   – temperature [K]
            P   – static pressure [Pa]
            rho – air density [kg/m³]
            a   – speed of sound [m/s]
    """
    alt_m = np.atleast_1d(np.asarray(alt_m, dtype=float))
    T   = np.empty_like(alt_m)
    P   = np.empty_like(alt_m)

    # Pre-compute reference values at layer boundaries
    T_at_trop   = T0 + L_TROP * H_TROP                    # = 216.65 K
    P_at_trop   = P0 * (T_at_trop / T0) ** (-G / (L_TROP * R_AIR))
    P_at_strat1 = P_at_trop * np.exp(-G * (H_STRAT1 - H_TROP) / (R_AIR * T_TROP))
    T_at_strat1 = T_TROP                                   # isothermal base

    # Troposphere: 0 – 11 000 m
    mask = alt_m <= H_TROP
    T[mask] = T0 + L_TROP * alt_m[mask]
    P[mask] = P0 * (T[mask] / T0) ** (-G / (L_TROP * R_AIR))

    # Lower stratosphere: 11 000 – 20 000 m  (isothermal)
    mask = (alt_m > H_TROP) & (alt_m <= H_STRAT1)
    T[mask] = T_TROP
    P[mask] = P_at_trop * np.exp(-G * (alt_m[mask] - H_TROP) / (R_AIR * T_TROP))

    # Middle stratosphere: 20 000 – 32 000 m
    mask = alt_m > H_STRAT1
    T[mask] = T_at_strat1 + L_STRAT1 * (alt_m[mask] - H_STRAT1)
    P[mask] = P_at_strat1 * (T[mask] / T_at_strat1) ** (-G / (L_STRAT1 * R_AIR))

    rho = P / (R_AIR * T)
    a   = np.sqrt(GAMMA * R_AIR * T)

    # Return scalars if scalar input was given
    if T.size == 1:
        return {'T': float(T[0]), 'P': float(P[0]),
                'rho': float(rho[0]), 'a': float(a[0])}
    return {'T': T, 'P': P, 'rho': rho, 'a': a}


def ias_to_tas(ias_ms, alt_m, atm=None, method='compressibility'):
    """
    Convert Indicated Airspeed (IAS == CAS) to True Airspeed (TAS).

    Two methods are available:
      'compressibility'  (default) – full subsonic compressibility correction.
          1. Derive impact pressure qc from CAS and sea-level conditions.
          2. Solve for local Mach from qc and static pressure at altitude.
          3. TAS = Mach * local speed of sound.
      'density'  – simplified EAS–TAS relation: TAS = IAS * sqrt(rho0/rho).
          Neglects compressibility; adequate below ~250 kts.

    Inputs:
        ias_ms:  Indicated Airspeed [m/s], scalar or array
        alt_m:   altitude [m], same shape as ias_ms or broadcastable
        atm:     pre-computed atmosphere dict from load_atmosphere(); computed
                 internally if not supplied
        method:  'compressibility' (default) or 'density'

    Outputs:
        tas_ms:  True Airspeed [m/s], same shape as inputs
    """
    ias_ms = np.asarray(ias_ms, dtype=float)
    alt_m  = np.asarray(alt_m,  dtype=float)
    if atm is None:
        atm = load_atmosphere(alt_m)

    if method == 'density':
        rho = np.asarray(atm['rho'])
        return ias_ms * np.sqrt(RHO0 / rho)

    # Compressibility-corrected method
    P   = np.asarray(atm['P'])
    a   = np.asarray(atm['a'])
    # impact pressure from CAS at sea level (isentropic, subsonic)
    qc  = P0 * ((1.0 + 0.2 * (ias_ms / A0) ** 2) ** 3.5 - 1.0)
    # local Mach from impact pressure and static pressure at altitude
    mach = np.sqrt(5.0 * ((qc / P + 1.0) ** (2.0 / 7.0) - 1.0))
    return mach * a


def mach_to_tas(mach, alt_m, atm=None):
    """
    Convert Mach number to True Airspeed.

    TAS = Mach * a  where a = sqrt(gamma * R * T) at altitude.

    Inputs:
        mach:   Mach number [dimensionless], scalar or array
        alt_m:  altitude [m], same shape as mach or broadcastable
        atm:    pre-computed atmosphere dict from load_atmosphere(); computed
                internally if not supplied

    Outputs:
        tas_ms: True Airspeed [m/s]
    """
    mach  = np.asarray(mach,  dtype=float)
    alt_m = np.asarray(alt_m, dtype=float)
    if atm is None:
        atm = load_atmosphere(alt_m)
    return mach * np.asarray(atm['a'])


def ias_to_mach(ias_ms, alt_m, atm=None):
    """
    Derive Mach number from Indicated Airspeed (IAS == CAS).

    Uses the same compressibility-corrected path as ias_to_tas().

    Inputs:
        ias_ms: Indicated Airspeed [m/s], scalar or array
        alt_m:  altitude [m], same shape as ias_ms or broadcastable
        atm:    pre-computed atmosphere dict from load_atmosphere()

    Outputs:
        mach:   Mach number [dimensionless]
    """
    ias_ms = np.asarray(ias_ms, dtype=float)
    alt_m  = np.asarray(alt_m,  dtype=float)
    if atm is None:
        atm = load_atmosphere(alt_m)
    P  = np.asarray(atm['P'])
    qc = P0 * ((1.0 + 0.2 * (ias_ms / A0) ** 2) ** 3.5 - 1.0)
    return np.sqrt(5.0 * ((qc / P + 1.0) ** (2.0 / 7.0) - 1.0))


def fuel_rate(alt_m, ias_ms, base_rate_kghr=2000.0, ias_ref_ms=130.0,
              power=1.5, atm=None):
    """
    Return estimated fuel consumption rate as a function of altitude and IAS.

    Preliminary / placeholder model — calibrate base_rate_kghr and power for
    a specific aircraft using measured fuel flow data.

    Model:   fuel_rate = base_rate * (rho / rho0) * (ias_ms / ias_ref_ms)^power

    Physical basis:
      - Thrust ~ drag ~ rho * v^2, so fuel flow ~ thrust * v ~ rho * v^3.
      - The (ias/ias_ref)^power term captures the speed sensitivity (power=1.5
        gives intermediate sensitivity between thrust-limited and drag-limited).
      - Density ratio (rho/rho0) captures the altitude de-rating.

    Default coefficients are representative of a P-3-like turboprop at cruise
    (~6 km, ~130 m/s IAS, ~2 000 kg/hr).  Fuel rate is returned in [kg/hr];
    multiply by 2.205 to convert to [lbs/hr].

    Inputs:
        alt_m:           altitude [m], scalar or array
        ias_ms:          Indicated Airspeed [m/s], same shape as alt_m or scalar
        base_rate_kghr:  reference fuel rate at sea level and ias_ref_ms [kg/hr]
        ias_ref_ms:      reference IAS for normalisation [m/s]
        power:           speed exponent [-]
        atm:             pre-computed atmosphere dict from load_atmosphere()

    Outputs:
        fuel_rate_kghr:  fuel consumption rate [kg/hr]
    """
    alt_m  = np.asarray(alt_m,  dtype=float)
    ias_ms = np.asarray(ias_ms, dtype=float)
    if atm is None:
        atm = load_atmosphere(alt_m)
    rho = np.asarray(atm['rho'])
    return base_rate_kghr * (rho / RHO0) * (ias_ms / ias_ref_ms) ** power
