"""
gfs_headwind.py
================

An optimized, Tkinter-friendly GFS 0.25° headwind/crosswind calculator.

Key features
------------
- One fast spatial sampler: **2×2 bilinear** interpolation on a regular lat/lon grid using pure NumPy
  (no per-point xarray.interp).
- Minimal I/O per waypoint: read only the 2×2 neighborhood (all levels) for the selected time.
- Small LRU-style cache keyed by (time_hour_bin, i_lat, i_lon) so adjacent waypoints reuse reads.
- One vertical interpolation path:
  * Prefer physical altitude via `hgtprs` (geopotential meters): sort by height and np.interp.
  * Else fallback to ISA 1976 (0–20 km) altitude→pressure and log-pressure interpolation for u/v.
- Single progress interface: `progress_cb(percent: float, stage: str)` for staged updates during open
  and coarse phases in compute; `progress_waypoints(i, n)` for per-waypoint updates.
- Thread-friendly but GUI-agnostic: includes `run_in_thread` helper; does not import Tkinter.

Data & conventions
------------------
- Coordinates: time, lev (hPa), lat, lon.
- Variables: ugrdprs (m/s), vgrdprs (m/s); preferred hgtprs (meters, geopotential height).
- Heading is degrees clockwise from north (0=N, 90=E).
- Headwind is positive **against** motion; crosswind is positive **from the right**.
- Wind-from direction (deg): (deg(atan2(-u, -v)) + 360) % 360.

OPeNDAP (default) and optional local GRIB (cfgrib)
--------------------------------------------------
- OPeNDAP pattern:
  https://nomads.ncep.noaa.gov:9090/dods/gfs_0p25/gfsYYYYMMDD/gfs_0p25_HHz
  (Port 9090 may be blocked by some networks.)
- Local GRIB open via cfgrib (guarded import). If unavailable, NotImplementedError is raised.

Terminal progress callback example
----------------------------------
You can pass a terminal-friendly progress callback:

    import sys
    def progress_cb(percent: float, stage: str):
        bar_len = 40
        filled = int(bar_len * max(0, min(100, percent)) / 100)
        bar = "█" * filled + "-" * (bar_len - filled)
        sys.stdout.write(f"\r[{bar}] {percent:5.1f}%  {stage:40s}")
        sys.stdout.flush()
        if percent >= 100:
            sys.stdout.write("\n")

Example usage (OPeNDAP source)
------------------------------
    import numpy as np
    from gfs_headwind import (
        gfs_opendap_url, compute_headwinds, run_in_thread
    )

    url = gfs_opendap_url("2025-11-03", 12)
    latlons = np.array([[37.62, -122.38],
                        [39.50, -119.77],
                        [40.78, -111.98]], float)
    alts = np.array([8000, 10000, 12000, 14000], float)

    def progress_waypoints(i, n):  # called from worker thread
        print(f"\rSampling waypoint {i}/{n}", end="")

    def worker():
        res = compute_headwinds(
            source=url,
            latlons=latlons,
            headings_deg=None,
            altitudes_m=alts,
            forecast_hour=9,
            target_valid_time=None,
            progress_cb=progress_cb,
            progress_waypoints=progress_waypoints,
        )
        print("\nHeadwind at first point:", res["headwind_ms"][0])

    handle = run_in_thread(worker)  # GUI should marshal UI updates to its main thread

Performance notes
-----------------
- The 2×2 bilinear sampler avoids the overhead of xarray.interp for each waypoint and minimizes I/O.
- The small cache reduces repeated reads when waypoints move cell-to-cell.
- If desired, pass `chunks` to `open_gfs_opendap` to enable Dask-style chunking.
- For the highest throughput, consider opening a local, pre-subset GRIB via cfgrib.

"""

from __future__ import annotations

import datetime as dt
import math
import threading
import weakref
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple, Union, MutableMapping

import numpy as np
import xarray as xr
import re
import time
import requests



# ----------------------------- Exceptions -----------------------------

class GFSDataError(RuntimeError):
    """Dataset, variable, or I/O problem."""


class InterpolationError(RuntimeError):
    """Invalid vertical ranges or interpolation inputs."""


class CancelledError(RuntimeError):
    """Raised when cancel_cb() requests cancellation."""


# --------------------------- URL builders -----------------------------

def gfs_opendap_url(
    day_str: str,
    hour_utc: Optional[int] = None,
    *,
    timeout: int = 10,
    session: Optional[requests.Session] = None,
) -> str:
    """
    Build the NOMADS OPeNDAP URL for GFS 0.25°.

    Parameters
    ----------
    day_str : str
        YYYY-MM-DD (UTC initialization date).
    hour_utc : Optional[int]
        One of {0, 6, 12, 18}. If None, probe NOMADS and select the latest available
        cycle for that day (prefers 18 > 12 > 06 > 00).
    timeout : int
        HTTP timeout in seconds for the directory probe when hour_utc is None.
    session : Optional[requests.Session]
        Optional requests Session to reuse connections.

    Returns
    -------
    str
        Example: https://nomads.ncep.noaa.gov:9090/dods/gfs_0p25/gfs20251103/gfs_0p25_12z

    Raises
    ------
    ValueError
        If day_str is invalid or hour_utc is not in {0,6,12,18}.
    GFSDataError
        If hour_utc is None and no cycle directory can be found or read.
    """
    try:
        dt.datetime.strptime(day_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError("day_str must be YYYY-MM-DD") from e

    if hour_utc is not None and hour_utc not in (0, 6, 12, 18):
        raise ValueError("hour_utc must be one of [0, 6, 12, 18] or None")

    ymd = day_str.replace("-", "")

    if hour_utc is None:
        hh = _latest_cycle_opendap(day_str, timeout=timeout, session=session)
        if hh is None:
            raise GFSDataError(
                f"No OPeNDAP cycles found for {day_str}. "
                "The NOMADS OPeNDAP directory may be unavailable or blocked (port 9090)."
            )
        hour_utc = hh

    hh_str = f"{hour_utc:02d}"
    return f"https://nomads.ncep.noaa.gov/dods/gfs_0p25/gfs{ymd}/gfs_0p25_{hh_str}z"


def _latest_cycle_opendap(
    day_str: str,
    *,
    timeout: int = 10,
    session: Optional[requests.Session] = None,
) -> Optional[int]:
    """
    Probe the OPeNDAP day directory and return the latest available cycle hour (18, 12, 06, 00).
    Returns None if the directory can't be read or no cycle entries are found.
    """
    ymd = day_str.replace("-", "")
    day_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25/gfs{ymd}/"

    sess = session or requests.Session()

    # Small retry with exponential backoff for transient issues
    last_exc = None
    for attempt in range(3):
        try:
            r = sess.get(day_url, timeout=timeout)
            if r.status_code != 200:
                last_exc = RuntimeError(f"HTTP {r.status_code}")
            else:
                # Look for "gfs_0p25_HHz" items
                hours_found = set(int(h) for h in re.findall(r"gfs_0p25_(\d{2})z:", r.text))
                for hh in (18, 12, 6, 0):
                    if hh in hours_found:
                        return hh
                return None
        except Exception as e:
            last_exc = e
        time.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s, 2s

    # All attempts failed
    return None



def gfs_grib2_url(day_str: str, hour_utc: int, forecast_hour: int) -> str:
    """
    Build a direct NOMADS GRIB2 URL for a specific forecast hour.

    Returns
    -------
    str
        .../gfs.YYYYMMDD/HH/atmos/gfs.tHHz.pgrb2.0p25.fFFF
    """
    if hour_utc not in (0, 6, 12, 18):
        raise ValueError("hour_utc must be one of [0, 6, 12, 18]")
    try:
        dt.datetime.strptime(day_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError("day_str must be YYYY-MM-DD") from e

    ymd = day_str.replace("-", "")
    hh = f"{hour_utc:02d}"
    fff = f"{forecast_hour:03d}"
    return (
        f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/"
        f"gfs.{ymd}/{hh}/atmos/gfs.t{hh}z.pgrb2.0p25.f{fff}"
    )


# -------------------- Dataset openers & simple cache -------------------

_REQUIRED_VARS = ("ugrdprs", "vgrdprs")
_PREFERRED_VAR = "hgtprs"
_DATASET_CACHE: Dict[str, weakref.ReferenceType] = {}


def clear_cache() -> None:
    """Clear internal dataset cache."""
    _DATASET_CACHE.clear()


def _get_cached(url: str) -> Optional[xr.Dataset]:
    ref = _DATASET_CACHE.get(url)
    return None if ref is None else ref()


def _put_cache(url: str, ds: xr.Dataset) -> None:
    _DATASET_CACHE[url] = weakref.ref(ds)


def _verify_required_vars(ds: xr.Dataset) -> None:
    missing = [v for v in _REQUIRED_VARS if v not in ds]
    if missing:
        raise GFSDataError(
            f"Dataset missing required variables: {missing}. "
            f"Available: {list(ds.data_vars.keys())}"
        )
    for c in ("time", "lev", "lat", "lon"):
        if c not in ds.coords:
            raise GFSDataError(f"Dataset missing coordinate '{c}'")


def open_gfs_opendap(
    url: str,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    *,
    chunks: Optional[Dict[str, int]] = None,
) -> xr.Dataset:
    """
    Open a GFS 0.25° OPeNDAP dataset lazily, validate variables/coords, and cache it.

    Parameters
    ----------
    url : str
        OPeNDAP URL.
    progress_cb : Optional[Callable[[float, str], None]]
        Called with staged progress: (10% "connect", 30% "metadata", 60% "verify",
        90% "cache", 100% "ready").
    chunks : Optional[Dict[str, int]]
        Optional xarray chunk mapping (e.g., {"lat":256, "lon":256, "lev":-1}).

    Returns
    -------
    xr.Dataset
    """
    import warnings
    from xarray.coding.times import SerializationWarning

    warnings.filterwarnings(
        "ignore",
        category=SerializationWarning,
        message=r"Ambiguous reference date string"
    )

    def report(pct: float, stage: str) -> None:
        if progress_cb:
            try:
                progress_cb(pct, stage)
            except Exception:
                pass
    ds = _get_cached(url)
    if ds is not None and isinstance(ds, xr.Dataset):
        try:
            _verify_required_vars(ds)
            report(100.0, "ready (cache)")
            return ds
        except Exception:
            clear_cache()

    report(10.0, "open_dataset")
    try:
        if chunks:
            ds = xr.open_dataset(url, chunks=chunks)
        else:
            ds = xr.open_dataset(url)
    except Exception as e:
        report(0.0, f"open_failed: {e}")
        raise GFSDataError(f"Failed to open OPeNDAP dataset: {url}") from e

    report(30.0, "metadata")
    _ = list(ds.coords)

    report(60.0, "verify")
    _verify_required_vars(ds)

    report(90.0, "cache")
    _put_cache(url, ds)

    report(100.0, "ready")
    return ds


def open_gfs_grib(path: str) -> xr.Dataset:
    """
    Open a local GRIB2 file lazily via cfgrib.

    Returns
    -------
    xr.Dataset

    Raises
    ------
    NotImplementedError
        If cfgrib is not installed.
    """
    try:
        import cfgrib  # noqa: F401
    except Exception as e:
        raise NotImplementedError(
            "cfgrib (and ecCodes) is required for GRIB2 reading. "
            "Install cfgrib and system ecCodes, then retry."
        ) from e

    # Open pressure levels group; variables may be split across groups in some files.
    ds = xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs=dict(
            filter_by_keys={"typeOfLevel": "isobaricInhPa"},
            indexpath="",  # disable side index file
        ),
    )

    # Normalize names to this module's expectations
    rename = {}
    if "isobaricInhPa" in ds.coords:
        rename["isobaricInhPa"] = "lev"
    if "latitude" in ds.coords:
        rename["latitude"] = "lat"
    if "longitude" in ds.coords:
        rename["longitude"] = "lon"
    if "u" in ds.data_vars:
        rename["u"] = "ugrdprs"
    if "v" in ds.data_vars:
        rename["v"] = "vgrdprs"
    # geopotential height often "gh" (gpm)
    if "gh" in ds.data_vars:
        rename["gh"] = "hgtprs"

    ds = ds.rename(rename)
    # guarantee dimension order: (time, lev, lat, lon)
    ds = ds.transpose("time", "lev", "lat", "lon", missing_dims="ignore")

    _verify_required_vars(ds)
    return ds


# ----------------------------- Time select ----------------------------

def select_valid_time(
    ds: xr.Dataset,
    *,
    forecast_hour: Optional[int] = None,
    target_valid_time: Optional[np.datetime64] = None,
) -> np.datetime64:
    """
    Choose a valid time from ds['time'] with robust dtype handling.

    - If `target_valid_time` is provided: choose nearest.
    - Else if `forecast_hour` provided: nearest to (time[0] + forecast_hour h).
    - Else: nearest to "now" UTC.

    Returns np.datetime64 with ns precision.
    """
    if "time" not in ds.coords:
        raise GFSDataError("Dataset missing 'time' coordinate.")

    times = ds["time"]

    def to_dt64ns(val) -> np.datetime64:
        return np.datetime64(np.array(val).astype("datetime64[ns]"))

    if target_valid_time is not None:
        tv = np.array(target_valid_time).astype(times.dtype)
        sel = times.sel(time=tv, method="nearest").values
        return to_dt64ns(sel)

    if forecast_hour is not None:
        base = np.array(times[0]).astype(times.dtype)
        ref = (base.astype("datetime64[ns]") + np.timedelta64(int(forecast_hour), "h")).astype(times.dtype)
        sel = times.sel(time=ref, method="nearest").values
        return to_dt64ns(sel)

    now = np.datetime64(dt.datetime.utcnow(), "s").astype(times.dtype)
    sel = times.sel(time=now, method="nearest").values
    return to_dt64ns(sel)


# ------------------------- Bearings / headings ------------------------

def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle initial bearing (deg clockwise from north)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    y = math.sin(dlam) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    brg = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    return brg


def ensure_headings(waypoints: np.ndarray, headings: Optional[np.ndarray]) -> np.ndarray:
    """
    Ensure a heading per waypoint. If headings is None or has NaNs, compute per-leg bearings.
    For the last waypoint, reuse the previous leg's heading.
    """
    waypoints = np.asarray(waypoints, float)
    if waypoints.ndim != 2 or waypoints.shape[1] != 2 or waypoints.shape[0] < 1:
        raise ValueError("waypoints must be shape (N,2) with N>=1")

    n = waypoints.shape[0]
    out = np.empty((n,), dtype=float)

    if headings is None:
        headings = np.full((n,), np.nan, dtype=float)
    elif headings.shape != (n,):
        raise ValueError("headings must be shape (N,) to match waypoints")

    for i in range(n):
        if not np.isnan(headings[i]):
            out[i] = float(headings[i])
            continue
        if i < n - 1:
            lat1, lon1 = float(waypoints[i, 0]), float(waypoints[i, 1])
            lat2, lon2 = float(waypoints[i + 1, 0]), float(waypoints[i + 1, 1])
            out[i] = initial_bearing_deg(lat1, lon1, lat2, lon2)
        elif n >= 2:
            out[i] = out[i - 1]
        else:
            out[i] = 0.0  # single point default

    return out


# -------------------- Vertical interpolation (single path) ------------

def pressure_at_height_std_1976(z_m: Union[np.ndarray, float]) -> np.ndarray:
    """
    ISA 1976 pressure (Pa) at altitude z (m) for 0..20 km.
    Troposphere (0..11 km): lapse L=-6.5 K/km; 11..20 km isothermal at T_trop.
    """
    z = np.asarray(z_m, dtype=float)
    p = np.empty_like(z, dtype=float)

    g0 = 9.80665
    R = 287.05287
    p0 = 101325.0
    T0 = 288.15
    L = -0.0065
    z_t = 11000.0
    T_t = T0 + L * z_t
    p_t = p0 * (T_t / T0) ** (-g0 / (L * R))

    tro = z <= z_t
    p[tro] = p0 * (1.0 + (L * z[tro]) / T0) ** (-g0 / (L * R))

    strato = z > z_t
    z_str = z[strato]
    p[strato] = p_t * np.exp(-g0 * (z_str - z_t) / (R * T_t))
    return p


def _log_interp(y_new: np.ndarray, y: np.ndarray, f: np.ndarray) -> np.ndarray:
    """Interpolate f(y) at y_new using linear interpolation in log(y); y>0 required."""
    y = np.asarray(y, float)
    f = np.asarray(f, float)
    y_new = np.asarray(y_new, float)
    if (y <= 0).any() or (y_new <= 0).any():
        raise InterpolationError("log-interp requires positive y and y_new.")
    order = np.argsort(y)
    ly = np.log(y[order])
    lf = f[order]
    return np.interp(np.log(y_new), ly, lf)


def interp_wind_to_altitudes(
    lev_hPa: np.ndarray,
    u_prof: np.ndarray,
    v_prof: np.ndarray,
    z_prof_or_none: Optional[np.ndarray],
    altitudes_m: np.ndarray,
    *,
    allow_extrapolation: bool = False,
) -> Dict[str, np.ndarray]:
    """
    Interpolate vertical wind profile to requested altitudes (m).

    Preferred (if z_prof available):
      - Sort by z and linearly interpolate u/v by altitude; pressure returned by z-interp.

    Fallback:
      - Convert altitude -> ISA pressure (hPa) and log-interpolate u/v in pressure space.
    """
    lev_hPa = np.asarray(lev_hPa, float)
    u_prof = np.asarray(u_prof, float)
    v_prof = np.asarray(v_prof, float)
    alts = np.asarray(altitudes_m, float)
    if alts.ndim != 1 or alts.size == 0:
        raise InterpolationError("altitudes_m must be a non-empty 1D array.")

    if z_prof_or_none is not None:
        z = np.asarray(z_prof_or_none, float)
        if z.shape != u_prof.shape or z.shape != v_prof.shape:
            raise InterpolationError("Shape mismatch among z_prof, u_prof, v_prof.")
        order = np.argsort(z)
        z = z[order]
        u = u_prof[order]
        v = v_prof[order]
        p = lev_hPa[order]

        zmin, zmax = float(z.min()), float(z.max())
        if not allow_extrapolation and ((alts < zmin).any() or (alts > zmax).any()):
            raise InterpolationError(
                f"Requested altitude outside profile range [{zmin:.0f}, {zmax:.0f}] m."
            )
        alts_q = np.clip(alts, zmin, zmax) if allow_extrapolation else alts
        u_at = np.interp(alts_q, z, u)
        v_at = np.interp(alts_q, z, v)
        p_at = np.interp(alts_q, z, p)
        return {"u_ms": u_at, "v_ms": v_at, "pressure_hPa": p_at}

    # ISA/log-p fallback
    p_target_hPa = pressure_at_height_std_1976(alts) / 100.0
    u_at = _log_interp(p_target_hPa, lev_hPa, u_prof)
    v_at = _log_interp(p_target_hPa, lev_hPa, v_prof)
    return {"u_ms": u_at, "v_ms": v_at, "pressure_hPa": p_target_hPa}


# -------------------------- Fast spatial sampling ---------------------

def _normalize_lon_for_ds(ds: xr.Dataset, lon: float) -> float:
    """Normalize user longitude to dataset convention (0..360 vs -180..180)."""
    lon_ds = ds["lon"]
    maxlon = float(lon_ds.max())
    if maxlon > 180.0:  # dataset likely 0..360
        lo = lon % 360.0
        return lo if lo >= 0 else lo + 360.0
    return ((lon + 180.0) % 360.0) - 180.0


def _find_ll_indices_and_weights(
    lat_vals: np.ndarray, lon_vals: np.ndarray, lat: float, lon: float
) -> Tuple[int, int, float, float]:
    """
    Lower-left indices (i, j) and fractional weights (wy, wx) for bilinear on a regular grid.
    Handles latitude ascending or descending; longitude ascending. Longitude must already be
    normalized to the dataset convention prior to calling.
    """
    lat_arr = np.asarray(lat_vals, float)
    lon_arr = np.asarray(lon_vals, float)

    # Latitude: ascending or descending
    lat_asc = lat_arr[1] > lat_arr[0]
    if lat_asc:
        i1 = np.searchsorted(lat_arr, lat, side="right") - 1
        i = max(0, min(i1, lat_arr.size - 2))
        y0, y1 = lat_arr[i], lat_arr[i + 1]
        wy = (lat - y0) / (y1 - y0) if y1 != y0 else 0.0
    else:
        i1 = np.searchsorted(lat_arr[::-1], lat, side="right") - 1
        i = (lat_arr.size - 2) - max(0, min(i1, lat_arr.size - 2))
        y0, y1 = lat_arr[i], lat_arr[i + 1]
        wy = (y0 - lat) / (y0 - y1) if y1 != y0 else 0.0  # still 0..1

    # Longitude: assume ascending; wrap handled by caller for j+1
    j1 = np.searchsorted(lon_arr, lon, side="right") - 1
    j = max(0, min(j1, lon_arr.size - 2))
    x0, x1 = lon_arr[j], lon_arr[j + 1]
    wx = (lon - x0) / (x1 - x0) if x1 != x0 else 0.0

    wy = 0.0 if wy < 0.0 else (1.0 if wy > 1.0 else wy)
    wx = 0.0 if wx < 0.0 else (1.0 if wx > 1.0 else wx)
    return i, j, wy, wx


def _bilinear_blend(q11: np.ndarray, q21: np.ndarray, q12: np.ndarray, q22: np.ndarray, wx: float, wy: float) -> np.ndarray:
    """
    Bilinear blend across q11=(i,j), q21=(i,j+1), q12=(i+1,j), q22=(i+1,j+1).
    """
    return ((1.0 - wx) * (1.0 - wy) * q11
            + wx * (1.0 - wy) * q21
            + (1.0 - wx) * wy * q12
            + wx * wy * q22)


def _sample_profile_ultra(
    ds: xr.Dataset,
    valid_time: np.datetime64,
    lat: float,
    lon: float,
    cache: Optional[MutableMapping] = None,
) -> Dict[str, np.ndarray]:
    """
    Ultra-fast 2×2 bilinear sampler for u/v/(hgt) vertical profiles at (lat,lon,time).

    Returns dict: {'lev_hPa': (L,), 'u_ms': (L,), 'v_ms': (L,), 'z_m': (L,) or None}
    """
    # Select time (nearest if needed)
    try:
        dst = ds.sel(time=valid_time)
    except Exception:
        dst = ds.sel(time=valid_time, method="nearest")

    lon_norm = _normalize_lon_for_ds(dst, lon)
    lat_vals = np.asarray(dst["lat"].values, float)
    lon_vals = np.asarray(dst["lon"].values, float)

    i, j, wy, wx = _find_ll_indices_and_weights(lat_vals, lon_vals, float(lat), float(lon_norm))
    j2 = j + 1
    wrap = False
    if j2 >= lon_vals.size:
        j2 = 0
        wrap = True

    # Cache key: hour-binned time + i + j
    key = None
    if cache is not None:
        tbin = int(np.array(valid_time).astype("datetime64[h]").astype("int64"))
        key = (tbin, int(i), int(j))
        hit = cache.get(key)
        if hit is not None:
            lev, u2x2, v2x2, z2x2 = hit
        else:
            lev = np.asarray(dst["lev"].values, float)
            block = dst.isel(lat=slice(i, i + 2), lon=[j, j2 if not wrap else j2])
            u2x2 = np.asarray(block["ugrdprs"].values, float)  # (L,2,2)
            v2x2 = np.asarray(block["vgrdprs"].values, float)
            z2x2 = np.asarray(block[_PREFERRED_VAR].values, float) if _PREFERRED_VAR in block else None
            cache[key] = (lev, u2x2, v2x2, z2x2)
    else:
        lev = np.asarray(dst["lev"].values, float)
        block = dst.isel(lat=slice(i, i + 2), lon=[j, j2 if not wrap else j2])
        u2x2 = np.asarray(block["ugrdprs"].values, float)
        v2x2 = np.asarray(block["vgrdprs"].values, float)
        z2x2 = np.asarray(block[_PREFERRED_VAR].values, float) if _PREFERRED_VAR in block else None

    u_prof = _bilinear_blend(u2x2[:, 0, 0], u2x2[:, 0, 1], u2x2[:, 1, 0], u2x2[:, 1, 1], wx, wy)
    v_prof = _bilinear_blend(v2x2[:, 0, 0], v2x2[:, 0, 1], v2x2[:, 1, 0], v2x2[:, 1, 1], wx, wy)
    z_prof = None
    if z2x2 is not None:
        z_prof = _bilinear_blend(z2x2[:, 0, 0], z2x2[:, 0, 1], z2x2[:, 1, 0], z2x2[:, 1, 1], wx, wy)

    return {"lev_hPa": lev, "u_ms": u_prof, "v_ms": v_prof, "z_m": z_prof}


# --------------------------- Wind vector math -------------------------

def wind_from_dir_deg(u_ms: np.ndarray, v_ms: np.ndarray) -> np.ndarray:
    """Meteorological FROM direction in degrees [0..360)."""
    return (np.degrees(np.arctan2(-u_ms, -v_ms)) + 360.0) % 360.0


def project_head_cross(
    u_ms: np.ndarray, v_ms: np.ndarray, heading_deg: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Headwind (+ against motion) and crosswind (+ from right) for given heading (deg).
    """
    th = math.radians(float(heading_deg))
    along = u_ms * math.sin(th) + v_ms * math.cos(th)
    head = -along
    cross = u_ms * math.cos(th) - v_ms * math.sin(th)
    return head, cross


# ----------------------------- Orchestrator ---------------------------

@dataclass
class ThreadHandle:
    thread: threading.Thread
    _cancel_event: threading.Event

    def cancel(self) -> None:
        self._cancel_event.set()

    def is_alive(self) -> bool:
        return self.thread.is_alive()


def run_in_thread(func: Callable, *args, **kwargs) -> ThreadHandle:
    """
    Run callable in a background thread. Returns a handle with .cancel() and .is_alive().
    The callable should read a `cancel_event` kwarg or supply a `cancel_cb`.
    """
    cancel_event = threading.Event()
    kwargs = dict(kwargs)
    kwargs.setdefault("cancel_event", cancel_event)

    def wrapper():
        try:
            func(*args, **kwargs)
        except Exception:
            # Caller should handle/report errors inside `func` (e.g., via GUI queue).
            pass

    th = threading.Thread(target=wrapper, daemon=True)
    th.start()
    return ThreadHandle(thread=th, _cancel_event=cancel_event)

def compute_headwinds(
    *,
    source: Union[str, xr.Dataset],
    latlons: np.ndarray,
    headings_deg: Optional[np.ndarray],
    altitudes_m: np.ndarray,
    forecast_hour: Optional[int],
    target_valid_time: Optional[np.datetime64],
    allow_extrapolation: bool = False,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    progress_waypoints: Optional[Callable[[int, int], None]] = None,
    cancel_cb: Optional[Callable[[], bool]] = None,
    cache_size: int = 2048,
) -> Dict[str, Union[np.ndarray, dict]]:
    """
    High-level calculator: sample u/v at waypoints via fast 2×2 bilinear, interpolate by altitude,
    and compute headwind/crosswind.

    Altitude interpretation:
    - If `altitudes_m` is scalar or shape (1,), one altitude for all waypoints -> outputs are (N,).
    - If `altitudes_m` is shape (N,), one altitude per waypoint -> outputs are (N,).
    - Else (`altitudes_m` is shape (M,), M!=N), common altitude list for all -> outputs are (N, M).
    """
    def report(pct: float, stage: str) -> None:
        if progress_cb:
            try:
                progress_cb(pct, stage)
            except Exception:
                pass

    latlons = np.asarray(latlons, float)
    if latlons.ndim != 2 or latlons.shape[1] != 2 or latlons.shape[0] < 1:
        raise ValueError("latlons must be shape (N,2), N>=1")
    N = latlons.shape[0]

    headings = ensure_headings(latlons, None if headings_deg is None else np.asarray(headings_deg, float))

    # Normalize altitudes input and decide output shape
    alts_raw = np.asarray(altitudes_m, float)
    if alts_raw.ndim == 0 or (alts_raw.ndim == 1 and alts_raw.size == 1):
        mode = "scalar_for_all"
        alts_common = np.array([float(alts_raw.reshape(()))], dtype=float)  # (1,)
        M = 1
    elif alts_raw.ndim == 1 and alts_raw.size == N:
        mode = "per_waypoint"
        M = 1
    elif alts_raw.ndim == 1 and alts_raw.size > 1:
        mode = "common_list"
        alts_common = alts_raw.astype(float)  # (M,)
        M = alts_common.size
    else:
        raise ValueError("altitudes_m must be scalar, shape (N,), or shape (M,)")

    # Open dataset if needed
    if isinstance(source, xr.Dataset):
        ds = source
        src_meta = "dataset:local"
    elif isinstance(source, str):
        report(5.0, "open_dataset")
        ds = open_gfs_opendap(source)
        src_meta = f"opendap:{source}"
    else:
        raise ValueError("source must be a URL string or an xarray.Dataset")

    # Select time
    report(10.0, "time_selection")
    valid_time = select_valid_time(ds, forecast_hour=forecast_hour, target_valid_time=target_valid_time)

    has_height = _PREFERRED_VAR in ds
    tile_cache: Dict[Tuple[int, int, int], Tuple[np.ndarray, np.ndarray, np.ndarray, Optional[np.ndarray]]] = {}

    # Allocate outputs
    if mode in ("scalar_for_all", "per_waypoint"):
        # 1D outputs (N,)
        u_out = np.empty((N,), dtype=np.float32)
        v_out = np.empty((N,), dtype=np.float32)
        p_out = np.empty((N,), dtype=np.float32)
        spd_out = np.empty((N,), dtype=np.float32)
        wdir_out = np.empty((N,), dtype=np.float32)
        head_out = np.empty((N,), dtype=np.float32)
        cross_out = np.empty((N,), dtype=np.float32)
    else:
        # 2D outputs (N, M)
        u_out = np.empty((N, M), dtype=np.float32)
        v_out = np.empty((N, M), dtype=np.float32)
        p_out = np.empty((N, M), dtype=np.float32)
        spd_out = np.empty((N, M), dtype=np.float32)
        wdir_out = np.empty((N, M), dtype=np.float32)
        head_out = np.empty((N, M), dtype=np.float32)
        cross_out = np.empty((N, M), dtype=np.float32)

    report(15.0, "sampling")
    for i, (plat, plon) in enumerate(latlons):
        if cancel_cb is not None and cancel_cb():
            raise CancelledError("Computation cancelled by user.")
        report(15.0+((i+1)/len(latlons)*80.0), "looping through waypoints")
        prof = _sample_profile_ultra(ds, valid_time, float(plat), float(plon), cache=tile_cache)
        if cache_size > 0 and len(tile_cache) > cache_size:
            tile_cache.clear()

        # Determine altitude(s) to use for this waypoint
        if mode == "per_waypoint":
            alts_here = np.array([alts_raw[i]], dtype=float)  # shape (1,)
        elif mode == "scalar_for_all":
            alts_here = alts_common  # (1,)
        else:  # "common_list"
            alts_here = alts_common  # (M,)

        res = interp_wind_to_altitudes(
            prof["lev_hPa"], prof["u_ms"], prof["v_ms"],
            prof["z_m"] if has_height else None,
            alts_here, allow_extrapolation=allow_extrapolation
        )

        u = res["u_ms"].astype(np.float32)
        v = res["v_ms"].astype(np.float32)
        p = res["pressure_hPa"].astype(np.float32)

        spd = np.hypot(u, v).astype(np.float32)
        wdir = wind_from_dir_deg(u, v).astype(np.float32)
        head, cross = project_head_cross(u, v, float(headings[i]))
        head = head.astype(np.float32)
        cross = cross.astype(np.float32)

        if mode in ("scalar_for_all", "per_waypoint"):
            # take the single altitude result
            u_out[i] = u[0]; v_out[i] = v[0]; p_out[i] = p[0]
            spd_out[i] = spd[0]; wdir_out[i] = wdir[0]
            head_out[i] = head[0]; cross_out[i] = cross[0]
        else:
            u_out[i, :] = u; v_out[i, :] = v; p_out[i, :] = p
            spd_out[i, :] = spd; wdir_out[i, :] = wdir
            head_out[i, :] = head; cross_out[i, :] = cross

        if progress_waypoints:
            try:
                progress_waypoints(i + 1, N)
            except Exception:
                pass

    meta = {
        "source": src_meta,
        "valid_time": np.array(valid_time).astype("datetime64[ns]"),
        "vertical_coord": "height_m" if has_height else "pressure_hPa_fallback",
    }

    # Package outputs according to mode
    result = {
        "meta": meta,
        "waypoints": latlons.astype(np.float64),
        "headings_deg": headings.astype(np.float64),
        "pressure_hPa": p_out,
        "u_ms": u_out,
        "v_ms": v_out,
        "wind_speed_ms": spd_out,
        "wind_from_deg": wdir_out,
        "headwind_ms": head_out,
        "crosswind_ms": cross_out,
    }

    if mode in ("scalar_for_all", "per_waypoint"):
        # altitudes returned as (N,) for per_waypoint, scalar -> replicated to (N,)
        if mode == "per_waypoint":
            result["altitudes_m"] = alts_raw.astype(np.float64)
        else:
            result["altitudes_m"] = np.full((N,), float(alts_common[0]), dtype=np.float64)
    else:
        result["altitudes_m"] = alts_common.astype(np.float64)

    report(100.0, "done")
    return result

    
import sys
def progress_cb(percent: float, stage: str):
    bar_len = 40
    filled = int(bar_len * max(0, min(100, percent)) / 100)
    bar = "█" * filled + "-" * (bar_len - filled)
    sys.stdout.write(f"\r[{bar}] {percent:5.1f}%  {stage:40s}")
    sys.stdout.flush()
    if percent >= 100:
        sys.stdout.write("\n")
