"""
gfs_headwind.py
================

An optimized, Tkinter-friendly GFS 0.25° headwind/crosswind calculator.

Key features
------------
- **Partial HTTP GRIB2 downloads** from NOMADS: fetches only the needed
  variables (UGRD, VGRD, HGT) at pressure levels, using the .idx inventory
  to construct HTTP Range requests — with optional geographic subsetting
  via the NOMADS GRIB filter CGI.
- Robust handling of **polar regions** and **antimeridian crossings**.
- One fast spatial sampler: **2×2 bilinear** interpolation on a regular
  lat/lon grid using pure NumPy (no per-point xarray.interp).
- Minimal I/O per waypoint: read only the 2×2 neighborhood (all levels)
  for the selected time from a small local GRIB2 subset.
- One vertical interpolation path:
  * Prefer physical altitude via geopotential height: sort by height and
    np.interp.
  * Else fallback to ISA 1976 (0–20 km) altitude→pressure and
    log-pressure interpolation for u/v.
- Single progress interface: ``progress_cb(percent, stage)`` for staged
  updates; ``progress_waypoints(i, n)`` for per-waypoint updates.
- Thread-friendly but GUI-agnostic: ``run_in_thread`` helper; does not
  import Tkinter.

Data & conventions
------------------
- Variables fetched: UGRD, VGRD (m/s); preferred HGT (geopotential m).
- Heading is degrees clockwise from north (0=N, 90=E).
- Headwind is positive **against** motion; crosswind is positive **from
  the right**.
- Wind-from direction (deg): ``(deg(atan2(-u, -v)) + 360) % 360``.

NOMADS Partial HTTP (default) and optional local GRIB (cfgrib)
--------------------------------------------------------------
- GRIB filter pattern (no port 9090 needed)::

      https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?
        dir=/gfs.YYYYMMDD/HH/atmos&file=gfs.tHHz.pgrb2.0p25.fFFF
        &lev_XXX_mb=on&var_UGRD=on&var_VGRD=on&var_HGT=on
        &subregion=&leftlon=...&rightlon=...&toplat=...&bottomlat=...

  The partial-HTTP approach fetches the .idx inventory and uses Range
  headers for even finer control.

- Local GRIB open via cfgrib (guarded import).

Geographic subsetting
---------------------
When waypoints are provided, the downloader automatically computes a
bounding box with configurable padding and requests only that region.

Special cases handled:
- **Polar regions**: latitude is clamped to [-90, 90].  When a pole is
  included, longitude automatically expands to the full 360° because all
  meridians converge.
- **Antimeridian crossings**: detected when the longitude span exceeds
  180° or when min_lon > max_lon after normalization.  In such cases the
  download uses the full longitude range (global) because the GRIB filter
  ``subregion`` parameter does not support split longitude domains.
- **Small corridors**: a minimum padding of 2° (configurable) ensures the
  2×2 bilinear interpolation always has valid neighbors.

Terminal progress callback example
----------------------------------
    import sys
    def progress_cb(percent: float, stage: str):
        bar_len = 40
        filled = int(bar_len * max(0, min(100, percent)) / 100)
        bar = "█" * filled + "-" * (bar_len - filled)
        sys.stdout.write(f"\\r[{bar}] {percent:5.1f}%  {stage:40s}")
        sys.stdout.flush()
        if percent >= 100:
            sys.stdout.write("\\n")

Example usage (Partial HTTP with geographic subset)
---------------------------------------------------
    import numpy as np
    from gfs_headwind import (
        fetch_gfs_partial_grib, compute_headwinds, compute_bounding_box,
    )

    latlons = np.array([[37.62, -122.38],   # SFO
                        [39.50, -119.77],   # Reno
                        [40.78, -111.98]],  # SLC
                       float)
    alts = np.array([8000, 10000, 12000, 14000], float)

    # Automatically subsets to the corridor bounding box + 2° padding
    ds = fetch_gfs_partial_grib(
        day_str="2025-11-03",
        hour_utc=12,
        forecast_hour=9,
        latlons=latlons,          # <-- triggers geographic subset
        pad_deg=2.0,
        progress_cb=progress_cb,
    )

    res = compute_headwinds(
        source=ds,
        latlons=latlons,
        headings_deg=None,
        altitudes_m=alts,
        forecast_hour=None,
        target_valid_time=None,
        progress_cb=progress_cb,
    )
    print("Headwind:", res["headwind_ms"][0])

Performance notes
-----------------
- Geographic subsetting can reduce download from ~5–10 MB (global, all
  pressure levels, 3 vars) to ~200–500 KB for a typical domestic US
  corridor.
- Polar and antimeridian cases gracefully degrade to full-extent downloads
  rather than producing incorrect subsets.
"""

from __future__ import annotations

import datetime as dt
import io
import math
import os
import struct
import tempfile
import threading
import weakref
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import (
    Callable, Dict, List, MutableMapping, Optional, Tuple, Union,
)

import numpy as np
import re
import time
import requests
import xarray as xr
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

GFS_PRODUCTION_DELAY_HOURS = 5

# ====================================================================
# Exceptions
# ====================================================================

class GFSDataError(RuntimeError):
    """Dataset, variable, or I/O problem."""


class InterpolationError(RuntimeError):
    """Invalid vertical ranges or interpolation inputs."""


class CancelledError(RuntimeError):
    """Raised when cancel_cb() requests cancellation."""


# ====================================================================
# Geographic bounding box with polar / antimeridian handling
# ====================================================================

@dataclass
class BoundingBox:
    """
    Axis-aligned geographic bounding box.

    Attributes
    ----------
    south_lat : float
        Southern boundary, clamped to [-90, 90].
    north_lat : float
        Northern boundary, clamped to [-90, 90].
    west_lon : float
        Western boundary in [-180, 180] or [0, 360].
    east_lon : float
        Eastern boundary in [-180, 180] or [0, 360].
    crosses_antimeridian : bool
        True if the box straddles the ±180° line.
    includes_pole : bool
        True if north_lat == 90 or south_lat == -90 (after padding).
    is_global_lon : bool
        True if we should request 0–360 longitude (pole or antimeridian).
    """
    south_lat: float
    north_lat: float
    west_lon: float
    east_lon: float
    crosses_antimeridian: bool = False
    includes_pole: bool = False
    is_global_lon: bool = False


def compute_bounding_box(
    latlons: np.ndarray,
    pad_deg: float = 2.0,
    *,
    min_pad_deg: float = 0.5,
) -> BoundingBox:
    """
    Compute a geographic bounding box around waypoints with padding.

    Handles:
    - **Polar regions**: if padding pushes lat beyond ±90°, clamp lat and
      expand longitude to full 360° (all meridians converge at poles).
    - **Antimeridian crossing**: detected via the angular span of
      longitudes.  If the shortest arc spanning all waypoints crosses
      ±180°, or if the required lon range exceeds 180°, fall back to
      global longitude.
    - **Single waypoint**: uses pad_deg to create a non-degenerate box.

    Parameters
    ----------
    latlons : np.ndarray
        Shape (N, 2) — latitude, longitude in degrees.
    pad_deg : float
        Padding in degrees around the extremes (default 2.0).  Ensures
        the 2×2 bilinear interpolation has valid neighbors at edges.
    min_pad_deg : float
        Absolute minimum padding (default 0.5°, about 55 km at equator).

    Returns
    -------
    BoundingBox
    """
    latlons = np.asarray(latlons, float)
    if latlons.ndim != 2 or latlons.shape[1] != 2:
        raise ValueError("latlons must be shape (N, 2)")

    pad = max(float(pad_deg), float(min_pad_deg))

    lats = latlons[:, 0]
    lons = latlons[:, 1]

    # --- Latitude: straightforward min/max + pad, clamp to [-90, 90] ---
    south = float(np.min(lats)) - pad
    north = float(np.max(lats)) + pad

    includes_pole = False
    if north >= 90.0:
        north = 90.0
        includes_pole = True
    if south <= -90.0:
        south = -90.0
        includes_pole = True

    # --- Longitude: detect antimeridian crossing ---
    # Normalize all longitudes to [-180, 180) for analysis
    lons_norm = ((lons + 180.0) % 360.0) - 180.0

    crosses_antimeridian = False
    is_global_lon = False

    if includes_pole:
        # At the pole, all longitudes converge — must use global
        is_global_lon = True
        west = 0.0
        east = 360.0
    else:
        # Sort normalized lons and find the largest gap
        sorted_lons = np.sort(lons_norm)
        n_pts = len(sorted_lons)

        if n_pts == 1:
            # Single point: simple padding
            west = float(sorted_lons[0]) - pad
            east = float(sorted_lons[0]) + pad
        else:
            # Compute gaps between consecutive sorted longitudes,
            # including the wrap-around gap
            gaps = np.empty(n_pts, dtype=float)
            for gi in range(n_pts - 1):
                gaps[gi] = sorted_lons[gi + 1] - sorted_lons[gi]
            # Wrap-around gap: from last to first + 360
            gaps[-1] = (sorted_lons[0] + 360.0) - sorted_lons[-1]

            max_gap_idx = int(np.argmax(gaps))

            if max_gap_idx == n_pts - 1:
                # Largest gap is the wrap-around — no antimeridian crossing
                # The data spans from sorted_lons[0] to sorted_lons[-1]
                west = float(sorted_lons[0]) - pad
                east = float(sorted_lons[-1]) + pad
            else:
                # Largest gap is interior — the data wraps around ±180°
                # The data spans from sorted_lons[max_gap_idx + 1] (west)
                # going eastward to sorted_lons[max_gap_idx] (east)
                crosses_antimeridian = True
                west = float(sorted_lons[max_gap_idx + 1]) - pad
                east = float(sorted_lons[max_gap_idx]) + pad

            # Check if the span (going east from west to east) exceeds 180°
            if crosses_antimeridian:
                # Span = (east - west) mod 360 — but going the "long way"
                span = (east - west) % 360.0
                # If the requested span > 350° or the padding caused
                # overlap, just go global
                if span > 350.0 or span < 10.0:
                    is_global_lon = True
                    west = 0.0
                    east = 360.0
            else:
                span = east - west
                if span >= 360.0:
                    is_global_lon = True
                    west = 0.0
                    east = 360.0

    # For the GRIB filter: it expects leftlon <= rightlon in the same
    # convention, and does NOT support split-domain longitude ranges.
    # If we cross the antimeridian, we go global.
    if crosses_antimeridian and not is_global_lon:
        is_global_lon = True
        west = 0.0
        east = 360.0

    return BoundingBox(
        south_lat=round(south, 4),
        north_lat=round(north, 4),
        west_lon=round(west, 4),
        east_lon=round(east, 4),
        crosses_antimeridian=crosses_antimeridian,
        includes_pole=includes_pole,
        is_global_lon=is_global_lon,
    )


def _bbox_to_filter_params(bbox: BoundingBox) -> Optional[Dict[str, float]]:
    """
    Convert BoundingBox to NOMADS GRIB filter ``subregion`` parameters.

    Returns None if global extent is required (no subsetting benefit).
    """
    if bbox.is_global_lon and bbox.south_lat <= -90.0 and bbox.north_lat >= 90.0:
        return None  # Full globe — no point subsetting

    # GRIB filter expects: leftlon, rightlon in [-180, 360],
    # bottomlat, toplat in [-90, 90].
    # leftlon < rightlon required.

    if bbox.is_global_lon:
        left = 0.0
        right = 360.0
    else:
        left = bbox.west_lon
        right = bbox.east_lon
        # Ensure left < right for the filter
        if left > right:
            # This shouldn't happen if we went global for antimeridian,
            # but as a safety net:
            left = 0.0
            right = 360.0

    return {
        "leftlon": left,
        "rightlon": right,
        "bottomlat": max(-90.0, bbox.south_lat),
        "toplat": min(90.0, bbox.north_lat),
    }


# ====================================================================
# URL builders
# ====================================================================

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


def gfs_grib2_idx_url(day_str: str, hour_utc: int, forecast_hour: int) -> str:
    """Return the .idx inventory URL corresponding to gfs_grib2_url."""
    return gfs_grib2_url(day_str, hour_utc, forecast_hour) + ".idx"


def gfs_filter_url(
    day_str: str,
    hour_utc: int,
    forecast_hour: int,
    *,
    variables: Optional[List[str]] = None,
    levels: Optional[List[str]] = None,
    subregion: Optional[Dict[str, float]] = None,
) -> str:
    """
    Build a NOMADS GRIB-filter CGI URL that returns a pre-subset GRIB2.

    Parameters
    ----------
    variables : list of str, optional
        e.g. ["UGRD", "VGRD", "HGT"].  Default: UGRD, VGRD, HGT.
    levels : list of str, optional
        e.g. ["250_mb", "300_mb", ...].  Default: all standard mb levels.
    subregion : dict, optional
        {"leftlon": ..., "rightlon": ..., "toplat": ..., "bottomlat": ...}.
        If None, no geographic subsetting (global).
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

    if variables is None:
        variables = ["UGRD", "VGRD", "HGT"]

    if levels is None:
        levels = [
            "1_mb", "2_mb", "3_mb", "5_mb", "7_mb",
            "10_mb", "20_mb", "30_mb", "50_mb", "70_mb",
            "100_mb", "125_mb", "150_mb", "150_mb", "175_mb", "200_mb",
            "225_mb", "250_mb", "275_mb", "300_mb", "325_mb",
            "350_mb", "375_mb", "400_mb", "425_mb", "450_mb",
            "475_mb", "500_mb", "525_mb", "550_mb", "575_mb",
            "600_mb", "625_mb", "650_mb", "675_mb", "700_mb",
            "725_mb", "750_mb", "775_mb", "800_mb", "825_mb",
            "850_mb", "875_mb", "900_mb", "925_mb", "950_mb",
            "975_mb", "1000_mb",
        ]

    params = [
        f"dir=%2Fgfs.{ymd}%2F{hh}%2Fatmos",
        f"file=gfs.t{hh}z.pgrb2.0p25.f{fff}",
    ]
    for lev in levels:
        params.append(f"lev_{lev}=on")
    for var in variables:
        params.append(f"var_{var}=on")

    if subregion is not None:
        params.append("subregion=")
        params.append(f"leftlon={subregion['leftlon']}")
        params.append(f"rightlon={subregion['rightlon']}")
        params.append(f"toplat={subregion['toplat']}")
        params.append(f"bottomlat={subregion['bottomlat']}")

    base = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
    return base + "?" + "&".join(params)


# ====================================================================
# .idx parsing and partial-HTTP download
# ====================================================================

@dataclass
class _IdxRecord:
    """One line from a NOMADS .idx inventory file."""
    msg_no: int
    byte_start: int
    date_str: str
    var_name: str
    level_str: str
    forecast_str: str


def _parse_idx(text: str) -> List[_IdxRecord]:
    """
    Parse a NOMADS .idx file into a list of records.

    Each line looks like:
        1:0:d=2025110312:UGRD:1 mb:anl:
    """
    records: List[_IdxRecord] = []
    for line in text.strip().splitlines():
        parts = line.split(":")
        if len(parts) < 7:
            continue
        try:
            msg_no = int(parts[0])
            byte_start = int(parts[1])
            date_str = parts[2]
            var_name = parts[3].strip()
            level_str = parts[4].strip()
            forecast_str = parts[5].strip()
        except (ValueError, IndexError):
            continue
        records.append(_IdxRecord(
            msg_no, byte_start, date_str, var_name, level_str, forecast_str,
        ))
    return records


def _select_idx_records(
    records: List[_IdxRecord],
    variables: List[str],
    level_pattern: str = r"^\d+ mb$",
) -> List[_IdxRecord]:
    """Filter .idx records for requested variables at pressure levels."""
    var_set = set(v.upper() for v in variables)
    pat = re.compile(level_pattern)
    return [
        r for r in records
        if r.var_name in var_set and pat.match(r.level_str)
    ]


def _records_to_ranges(
    selected: List[_IdxRecord],
    all_records: List[_IdxRecord],
) -> List[Tuple[int, Optional[int]]]:
    """
    Convert selected idx records into (start_byte, end_byte) tuples.
    end_byte is exclusive; None means "to end of file".
    """
    all_starts = sorted(set(r.byte_start for r in all_records))
    start_to_next = {}
    for i, s in enumerate(all_starts):
        start_to_next[s] = (
            all_starts[i + 1] if i + 1 < len(all_starts) else None
        )

    ranges: List[Tuple[int, Optional[int]]] = []
    for rec in selected:
        end = start_to_next.get(rec.byte_start)
        ranges.append((rec.byte_start, end))
    return ranges


def _merge_ranges(
    ranges: List[Tuple[int, Optional[int]]],
    gap_threshold: int = 65536,
) -> List[Tuple[int, Optional[int]]]:
    """
    Merge byte ranges that are close together to reduce HTTP requests.
    """
    if not ranges:
        return []

    sorted_ranges = sorted(ranges, key=lambda r: r[0])
    merged: List[Tuple[int, Optional[int]]] = [sorted_ranges[0]]

    for start, end in sorted_ranges[1:]:
        prev_start, prev_end = merged[-1]

        if prev_end is None:
            continue

        if start <= prev_end + gap_threshold:
            new_end = end if end is None else max(prev_end, end)
            merged[-1] = (prev_start, new_end)
        else:
            merged.append((start, end))

    return merged


def _download_ranges(
    base_url: str,
    ranges: List[Tuple[int, Optional[int]]],
    *,
    session: Optional[requests.Session] = None,
    timeout: int = 60,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    progress_base: float = 20.0,
    progress_span: float = 60.0,
) -> bytes:
    """
    Download specified byte ranges using HTTP Range headers.
    """
    sess = session or requests.Session()
    chunks: List[bytes] = []
    total = len(ranges)

    for idx, (start, end) in enumerate(ranges):
        if end is not None:
            range_header = f"bytes={start}-{end - 1}"
        else:
            range_header = f"bytes={start}-"

        if progress_cb:
            pct = progress_base + progress_span * idx / max(total, 1)
            progress_cb(pct, f"downloading range {idx+1}/{total}")

        last_exc = None
        for attempt in range(3):
            try:
                resp = sess.get(
                    base_url,
                    headers={"Range": range_header},
                    timeout=timeout,
                )
                if resp.status_code not in (200, 206):
                    raise GFSDataError(
                        f"HTTP {resp.status_code} for range {range_header}"
                    )
                chunks.append(resp.content)
                last_exc = None
                break
            except requests.RequestException as e:
                last_exc = e
                time.sleep(0.5 * (2 ** attempt))

        if last_exc is not None:
            raise GFSDataError(
                f"Failed to download range {range_header} after 3 "
                f"attempts: {last_exc}"
            )

    return b"".join(chunks)


# ====================================================================
# High-level GRIB2 partial fetch with geographic subsetting
# ====================================================================
def latest_gfs_cycle(
    date_str: Optional[str] = None,
    utc_hour: Optional[float] = None,
    delay: float = 5.0,
) -> Tuple[str, int, int]:
    """
    Return (cycle_date '%Y%m%d', cycle_hour, forecast_hour) for GFS.

    Args:
        date_str: Target date '%Y-%m-%d'. None = now.
        utc_hour: Target fractional UTC hour. None = now.
        delay:    Hours after cycle start before data is available.
    """
    now = datetime.now(timezone.utc)

    # Target time
    if date_str or utc_hour is not None:
        d = datetime.strptime(date_str, "%Y-%m-%d") if date_str else now
        h = utc_hour if utc_hour is not None else now.hour + now.minute / 60
        target = d.replace(hour=int(h), minute=int((h % 1) * 60),
                           second=0, microsecond=0, tzinfo=timezone.utc)
    else:
        target = now

    # Latest available cycle: floor(now - delay) to 6h boundary
    latest_cycle = now - timedelta(hours=delay)
    cycle = min(target, latest_cycle)
    cycle = cycle.replace(hour=(cycle.hour // 6) * 6, minute=0, second=0, microsecond=0)

    # Forecast hour: snap to 1h (≤120) or 3h (>120)
    fhr = (target - cycle).total_seconds() / 3600
    fhr = round(fhr) if fhr <= 120 else 120 + round((fhr - 120) / 3) * 3

    return (cycle.strftime("%Y-%m-%d"), cycle.hour, int(fhr))
    
def fetch_gfs_partial_grib(
    day_str: str,
    hour_utc: int,
    forecast_hour: int,
    *,
    variables: Optional[List[str]] = None,
    latlons: Optional[np.ndarray] = None,
    pad_deg: float = 2.0,
    bbox: Optional[BoundingBox] = None,
    session: Optional[requests.Session] = None,
    timeout: int = 60,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    use_filter_fallback: bool = True,
    cache_dir: Optional[str] = None,
) -> xr.Dataset:
    """
    Download only the needed GRIB2 messages via NOMADS partial HTTP
    transfers and return an xarray Dataset.

    Geographic subsetting
    ---------------------
    Provide **either**:
    - ``latlons`` (the waypoints) — a bounding box is computed
      automatically with ``pad_deg`` padding, or
    - ``bbox`` (a pre-computed ``BoundingBox``), or
    - Neither, for a global download.

    The subsetting is applied via the NOMADS GRIB filter CGI
    ``subregion`` parameter.  The .idx + Range approach downloads
    full-globe GRIB2 messages (no server-side spatial crop), so when
    geographic subsetting is requested, the **filter fallback is
    preferred** as the primary strategy.

    Strategy
    --------
    1. If a subregion is requested:
       a. **Primary**: use the GRIB filter CGI with ``subregion`` params
          (server-side crop, smallest download).
       b. **Fallback**: .idx + Range requests (no spatial crop, but still
          variable/level filtered).
    2. If no subregion:
       a. **Primary**: .idx + Range requests.
       b. **Fallback**: GRIB filter CGI (no subregion).

    Parameters
    ----------
    day_str : str
        YYYY-MM-DD (UTC initialization date).
    hour_utc : int
        One of {0, 6, 12, 18}.
    forecast_hour : int
        Forecast hour (0, 3, 6, …, 384).
    variables : list of str, optional
        GRIB2 variable short names.  Default: ["UGRD", "VGRD", "HGT"].
    latlons : np.ndarray, optional
        Shape (N, 2) waypoints for automatic bounding box.
    pad_deg : float
        Padding degrees for the auto bounding box (default 2.0).
    bbox : BoundingBox, optional
        Pre-computed bounding box (overrides latlons-based computation).
    session : requests.Session, optional
        Reusable HTTP session.
    timeout : int
        Per-request timeout in seconds.
    progress_cb : callable, optional
        ``(percent, stage_str)`` callback.
    use_filter_fallback : bool
        If True and the primary strategy fails, try the alternative.
    cache_dir : str, optional
        Directory for caching downloaded GRIB2 subsets.

    Returns
    -------
    xr.Dataset
        Dataset with coordinates (time, lev, lat, lon) and variables
        ``ugrdprs``, ``vgrdprs``, optionally ``hgtprs``.
    """
    if variables is None:
        variables = ["UGRD", "VGRD", "HGT"]

    def report(pct: float, stage: str) -> None:
        if progress_cb:
            try:
                progress_cb(pct, stage)
            except Exception:
                print(pct,stage)

    # --- Check for cfgrib early ---
    try:
        import cfgrib  # noqa: F401
    except ImportError:
        raise NotImplementedError(
            "cfgrib (and ecCodes) is required for GRIB2 reading. "
            "Install with: pip install cfgrib  (plus system ecCodes)."
        )

    sess = session or requests.Session()
    sess.headers.update({"User-Agent": "movinglines-flightplanning (samuel.leblanc@nasa.gov)"})

    # --- Compute bounding box if waypoints provided ---
    if bbox is None and latlons is not None:
        latlons_arr = np.asarray(latlons, float)
        if latlons_arr.ndim == 2 and latlons_arr.shape[1] == 2:
            bbox = compute_bounding_box(latlons_arr, pad_deg=pad_deg)
            report(
                3.0,
                f"bbox: lat[{bbox.south_lat:.1f},{bbox.north_lat:.1f}] "
                f"lon[{bbox.west_lon:.1f},{bbox.east_lon:.1f}]"
                f"{' (global lon)' if bbox.is_global_lon else ''}"
                f"{' (pole)' if bbox.includes_pole else ''}"
                f"{' (antimeridian)' if bbox.crosses_antimeridian else ''}",
            )

    subregion = _bbox_to_filter_params(bbox) if bbox is not None else None
    has_subregion = subregion is not None

    # --- Determine cache path ---
    ymd = day_str.replace("-", "")
    hh = f"{hour_utc:02d}"
    fff = f"{forecast_hour:03d}"
    varkey = "_".join(sorted(v.upper() for v in variables))

    if has_subregion:
        # Include subregion in cache key to avoid stale caches
        sr = subregion
        region_key = (
            f"_{sr['bottomlat']:.1f}_{sr['toplat']:.1f}"
            f"_{sr['leftlon']:.1f}_{sr['rightlon']:.1f}"
        ).replace("-", "m").replace(".", "p")
    else:
        region_key = "_global"

    cache_fname = f"gfs_{ymd}_{hh}z_f{fff}_{varkey}{region_key}.grib2"

    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        grib_path = os.path.join(cache_dir, cache_fname)
    else:
        grib_path = os.path.join(tempfile.gettempdir(), cache_fname)

    # If cached, just open
    if os.path.isfile(grib_path) and os.path.getsize(grib_path) > 1000:
        report(5.0, "found cached GRIB2")
        return _open_grib_subset(grib_path, report)

    grib_data: Optional[bytes] = None

    # ------------------------------------------------------------------
    # Strategy depends on whether we have a subregion
    # ------------------------------------------------------------------
    if has_subregion:
        # --- PRIMARY for subregion: GRIB filter CGI (server-side crop) ---
        report(5.0, "using GRIB filter with subregion")
        grib_data = _try_grib_filter(day_str, hour_utc, forecast_hour,variables=variables,subregion=subregion,sess=sess,timeout=timeout,report=report)
        # --- FALLBACK: .idx + Range (no spatial crop) ---
        if grib_data is None and use_filter_fallback:
            report(40.0, "filter failed — falling back to .idx + Range")
            grib_data = _try_idx_range(day_str, hour_utc, forecast_hour,variables=variables,sess=sess,timeout=timeout,report=report)
    else:
        # --- PRIMARY for global: .idx + Range ---
        report(5.0, "using .idx + Range requests (global)")
        grib_data = _try_idx_range(
            day_str, hour_utc, forecast_hour,
            variables=variables,
            sess=sess,
            timeout=timeout,
            report=report,
        )
        # --- FALLBACK: GRIB filter (no subregion) ---
        if grib_data is None and use_filter_fallback:
            report(40.0, ".idx failed — falling back to GRIB filter")
            grib_data = _try_grib_filter(
                day_str, hour_utc, forecast_hour,
                variables=variables,
                subregion=None,
                sess=sess,
                timeout=timeout,
                report=report,
            )

    if grib_data is None:
        raise GFSDataError("Could not download GFS data by any method.")

    # --- Write to cache ---
    report(82.0, "writing GRIB2 to disk")
    with open(grib_path, "wb") as f:
        f.write(grib_data)

    return _open_grib_subset(grib_path, report)


def _try_grib_filter(
    day_str: str,
    hour_utc: int,
    forecast_hour: int,
    *,
    variables: List[str],
    subregion: Optional[Dict[str, float]],
    sess: requests.Session,
    timeout: int,
    report: Callable[[float, str], None],
) -> Optional[bytes]:
    """Attempt download via the NOMADS GRIB filter CGI."""
    filter_url = gfs_filter_url(
        day_str, hour_utc, forecast_hour,
        variables=variables,
        subregion=subregion,
    )
    sr_desc = "with subregion" if subregion else "global"
    report(8.0, f"GRIB filter request ({sr_desc})")
    
    print(f"DEBUG filter_url: {filter_url}")

    try:
        resp = sess.get(filter_url, timeout=timeout * 3, stream=True)
        if resp.status_code != 200:
            report(10.0, f"filter HTTP {resp.status_code}")
            return None

        # Check for error page (filter returns HTML on error)
        content_type = resp.headers.get("Content-Type", "")
        if "html" in content_type.lower():
            # Read a small amount to check
            peek = resp.content[:500]
            if b"<!DOCTYPE" in peek or b"<html" in peek.lower():
                report(10.0, "filter returned error HTML page")
                return None

        chunks_list = []
        total_bytes = 0
        for chunk in resp.iter_content(chunk_size=1 << 20):
            chunks_list.append(chunk)
            total_bytes += len(chunk)
            report(
                10.0 + min(65.0, 65.0 * total_bytes / 20_000_000),
                f"filter download: {total_bytes:,} bytes",
            )

        data = b"".join(chunks_list)
        if len(data) < 100:
            report(75.0, "filter returned too little data")
            return None

        report(78.0, f"filter downloaded {len(data):,} bytes")
        return data

    except Exception as e:
        report(10.0, f"filter error: {e}")
        return None


def _try_idx_range(
    day_str: str,
    hour_utc: int,
    forecast_hour: int,
    *,
    variables: List[str],
    sess: requests.Session,
    timeout: int,
    report: Callable[[float, str], None],
) -> Optional[bytes]:
    """Attempt download via .idx inventory + HTTP Range requests."""
    idx_url = gfs_grib2_idx_url(day_str, hour_utc, forecast_hour)
    base_url = gfs_grib2_url(day_str, hour_utc, forecast_hour)

    report(8.0, "fetching .idx inventory")
    try:
        idx_resp = sess.get(idx_url, timeout=timeout)
        if idx_resp.status_code != 200 or len(idx_resp.text.strip()) == 0:
            report(10.0, f".idx HTTP {idx_resp.status_code}")
            return None

        report(10.0, "parsing .idx")
        all_records = _parse_idx(idx_resp.text)
        selected = _select_idx_records(all_records, variables)

        if not selected:
            report(12.0, "no matching records in .idx")
            return None

        report(15.0, f"selected {len(selected)} GRIB2 messages")
        ranges = _records_to_ranges(selected, all_records)
        merged = _merge_ranges(ranges, gap_threshold=65536)
        report(18.0, f"merged into {len(merged)} range requests")

        data = _download_ranges(
            base_url, merged,
            session=sess, timeout=timeout,
            progress_cb=lambda pct, stg: report(pct, stg),
            progress_base=20.0,
            progress_span=55.0,
        )
        report(78.0, f"range downloaded {len(data):,} bytes")
        return data

    except Exception as e:
        report(10.0, f".idx/range error: {e}")
        return None


# ====================================================================
# GRIB2 opener (shared between fetch and local file)
# ====================================================================

_REQUIRED_VARS = ("ugrdprs", "vgrdprs")
_PREFERRED_VAR = "hgtprs"


def _verify_required_vars(ds: xr.Dataset) -> None:
    missing = [v for v in _REQUIRED_VARS if v not in ds]
    if missing:
        raise GFSDataError(
            f"Dataset missing required variables: {missing}. "
            f"Available: {list(ds.data_vars.keys())}"
        )
    for c in ("lev", "lat", "lon"):
        if c not in ds.coords:
            raise GFSDataError(f"Dataset missing coordinate '{c}'")


def _open_grib_subset(
    path: str,
    report: Callable[[float, str], None],
) -> xr.Dataset:
    """Open a subset GRIB2 file with cfgrib and normalize."""
    report(85.0, "opening with cfgrib")

    ds = xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs=dict(
            filter_by_keys={"typeOfLevel": "isobaricInhPa"},
            indexpath="",
        ),
    )

    report(90.0, "normalizing variable names")
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
    if "gh" in ds.data_vars:
        rename["gh"] = "hgtprs"

    ds = ds.rename(rename)

    # Ensure time dimension exists
    if "time" not in ds.dims:
        if "time" in ds.coords:
            ds = ds.expand_dims("time")
        elif "valid_time" in ds.coords:
            ds = ds.rename({"valid_time": "time"}).expand_dims("time")
        else:
            ds = ds.expand_dims("time")

    ds = ds.transpose("time", "lev", "lat", "lon", missing_dims="ignore")

    report(95.0, "verifying variables")
    _verify_required_vars(ds)

    report(100.0, "ready")
    return ds


def open_gfs_grib(path: str) -> xr.Dataset:
    """Open a local GRIB2 file lazily via cfgrib."""
    try:
        import cfgrib  # noqa: F401
    except Exception as e:
        raise NotImplementedError(
            "cfgrib (and ecCodes) is required for GRIB2 reading."
        ) from e

    def noop_report(pct, stage):
        pass

    return _open_grib_subset(path, noop_report)


# ====================================================================
# Legacy OPeNDAP support
# ====================================================================

_DATASET_CACHE: Dict[str, weakref.ReferenceType] = {}


def clear_cache() -> None:
    """Clear internal dataset cache."""
    _DATASET_CACHE.clear()


def _get_cached(url: str) -> Optional[xr.Dataset]:
    ref = _DATASET_CACHE.get(url)
    return None if ref is None else ref()


def _put_cache(url: str, ds: xr.Dataset) -> None:
    _DATASET_CACHE[url] = weakref.ref(ds)


def gfs_opendap_url(
    day_str: str,
    hour_utc: Optional[int] = None,
    *,
    timeout: int = 10,
    session: Optional[requests.Session] = None,
) -> str:
    """
    Build the NOMADS OPeNDAP URL for GFS 0.25° (legacy).

    .. deprecated::
        Prefer ``fetch_gfs_partial_grib`` which uses partial HTTP
        transfers and does not require port 9090.
    """
    try:
        dt.datetime.strptime(day_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError("day_str must be YYYY-MM-DD") from e

    if hour_utc is not None and hour_utc not in (0, 6, 12, 18):
        raise ValueError("hour_utc must be one of [0, 6, 12, 18]")

    ymd = day_str.replace("-", "")

    if hour_utc is None:
        hh = _latest_cycle_opendap(day_str, timeout=timeout, session=session)
        if hh is None:
            raise GFSDataError(
                f"No OPeNDAP cycles found for {day_str}. "
                "Try fetch_gfs_partial_grib() instead."
            )
        hour_utc = hh

    hh_str = f"{hour_utc:02d}"
    return (
        f"https://nomads.ncep.noaa.gov/dods/gfs_0p25/gfs{ymd}/"
        f"gfs_0p25_{hh_str}z"
    )


def _latest_cycle_opendap(
    day_str: str,
    *,
    timeout: int = 10,
    session: Optional[requests.Session] = None,
) -> Optional[int]:
    """Probe OPeNDAP directory for latest cycle (legacy)."""
    ymd = day_str.replace("-", "")
    day_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25/gfs{ymd}/"
    sess = session or requests.Session()

    for attempt in range(3):
        try:
            r = sess.get(day_url, timeout=timeout)
            if r.status_code == 200:
                hours_found = set(
                    int(h) for h in re.findall(r"gfs_0p25_(\d{2})z:", r.text)
                )
                for hh in (18, 12, 6, 0):
                    if hh in hours_found:
                        return hh
        except Exception:
            pass
        time.sleep(0.5 * (2 ** attempt))
    return None


def open_gfs_opendap(
    url: str,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    *,
    chunks: Optional[Dict[str, int]] = None,
) -> xr.Dataset:
    """Open a GFS 0.25° OPeNDAP dataset lazily (legacy)."""
    import warnings
    from xarray.coding.times import SerializationWarning

    warnings.filterwarnings(
        "ignore",
        category=SerializationWarning,
        message=r"Ambiguous reference date string",
    )

    def report(pct, stage):
        if progress_cb:
            try:
                progress_cb(pct, stage)
            except Exception:
                pass

    ds = _get_cached(url)
    if ds is not None:
        try:
            _verify_required_vars(ds)
            report(100.0, "ready (cache)")
            return ds
        except Exception:
            clear_cache()

    report(10.0, "open_dataset")
    try:
        ds = xr.open_dataset(url, chunks=chunks) if chunks else xr.open_dataset(url)
    except Exception as e:
        raise GFSDataError(f"Failed to open OPeNDAP: {url}") from e

    report(60.0, "verify")
    _verify_required_vars(ds)
    _put_cache(url, ds)
    report(100.0, "ready")
    return ds


# ====================================================================
# Latest-cycle discovery
# ====================================================================

def latest_available_cycle(
    day_str: Optional[str] = None,
    *,
    session: Optional[requests.Session] = None,
    timeout: int = 10,
    max_lookback_days: int = 2,
    forecast_hour: int = 0,
) -> Tuple[str, int]:
    """
    Find the latest available GFS cycle by probing .idx files.

    Returns (day_str, hour_utc), e.g. ("2025-11-03", 12).
    """
    sess = session or requests.Session()
    if day_str is None:
        start_day = dt.datetime.utcnow().date()
    else:
        start_day = dt.datetime.strptime(day_str, "%Y-%m-%d").date()

    for day_offset in range(max_lookback_days + 1):
        d = start_day - dt.timedelta(days=day_offset)
        dstr = d.strftime("%Y-%m-%d")
        for hh in (18, 12, 6, 0):
            idx_url = gfs_grib2_idx_url(dstr, hh, forecast_hour)
            try:
                r = sess.head(idx_url, timeout=timeout, allow_redirects=True)
                if r.status_code == 200:
                    return (dstr, hh)
            except requests.RequestException:
                continue

    raise GFSDataError(
        f"No GFS cycle found within {max_lookback_days} days of "
        f"{start_day.isoformat()}"
    )


# ====================================================================
# Time selection
# ====================================================================

def select_valid_time(
    ds: xr.Dataset,
    *,
    forecast_hour: Optional[int] = None,
    target_valid_time: Optional[np.datetime64] = None,
) -> np.datetime64:
    """Choose a valid time from ds['time']."""
    if "time" not in ds.coords:
        raise GFSDataError("Dataset missing 'time' coordinate.")

    times = ds["time"]

    def to_dt64ns(val) -> np.datetime64:
        return np.datetime64(np.array(val).astype("datetime64[ns]"))

    if times.size == 1:
        return to_dt64ns(times.values.flat[0])

    if target_valid_time is not None:
        tv = np.array(target_valid_time).astype(times.dtype)
        return to_dt64ns(times.sel(time=tv, method="nearest").values)

    if forecast_hour is not None:
        base = np.array(times[0]).astype(times.dtype)
        ref = (
            base.astype("datetime64[ns]")
            + np.timedelta64(int(forecast_hour), "h")
        ).astype(times.dtype)
        return to_dt64ns(times.sel(time=ref, method="nearest").values)

    now = np.datetime64(dt.datetime.utcnow(), "s").astype(times.dtype)
    return to_dt64ns(times.sel(time=now, method="nearest").values)


# ====================================================================
# Bearings / headings (unchanged)
# ====================================================================

def initial_bearing_deg(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    """Great-circle initial bearing (deg clockwise from north)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    y = math.sin(dlam) * math.cos(phi2)
    x = (math.cos(phi1) * math.sin(phi2)
         - math.sin(phi1) * math.cos(phi2) * math.cos(dlam))
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def ensure_headings(
    waypoints: np.ndarray, headings: Optional[np.ndarray],
) -> np.ndarray:
    """Ensure a heading per waypoint."""
    waypoints = np.asarray(waypoints, float)
    if waypoints.ndim != 2 or waypoints.shape[1] != 2 or waypoints.shape[0] < 1:
        raise ValueError("waypoints must be shape (N,2) with N>=1")

    n = waypoints.shape[0]
    out = np.empty((n,), dtype=float)

    if headings is None:
        headings = np.full((n,), np.nan, dtype=float)
    elif headings.shape != (n,):
        raise ValueError("headings must be shape (N,)")

    for i in range(n):
        if not np.isnan(headings[i]):
            out[i] = float(headings[i])
        elif i < n - 1:
            out[i] = initial_bearing_deg(
                float(waypoints[i, 0]), float(waypoints[i, 1]),
                float(waypoints[i + 1, 0]), float(waypoints[i + 1, 1]),
            )
        elif n >= 2:
            out[i] = out[i - 1]
        else:
            out[i] = 0.0

    return out


# ====================================================================
# Vertical interpolation (unchanged)
# ====================================================================

def pressure_at_height_std_1976(z_m: Union[np.ndarray, float]) -> np.ndarray:
    """ISA 1976 pressure (Pa) at altitude z (m) for 0–20 km."""
    z = np.asarray(z_m, dtype=float)
    p = np.empty_like(z, dtype=float)

    g0 = 9.80665; R = 287.05287; p0 = 101325.0; T0 = 288.15
    L = -0.0065; z_t = 11000.0
    T_t = T0 + L * z_t
    p_t = p0 * (T_t / T0) ** (-g0 / (L * R))

    tro = z <= z_t
    p[tro] = p0 * (1.0 + (L * z[tro]) / T0) ** (-g0 / (L * R))
    strato = z > z_t
    p[strato] = p_t * np.exp(-g0 * (z[strato] - z_t) / (R * T_t))
    return p


def _log_interp(
    y_new: np.ndarray, y: np.ndarray, f: np.ndarray,
) -> np.ndarray:
    """Interpolate f(y) at y_new via log(y)."""
    y, f, y_new = (np.asarray(a, float) for a in (y, f, y_new))
    if (y <= 0).any() or (y_new <= 0).any():
        raise InterpolationError("log-interp requires positive values.")
    order = np.argsort(y)
    return np.interp(np.log(y_new), np.log(y[order]), f[order])


def interp_wind_to_altitudes(
    lev_hPa: np.ndarray,
    u_prof: np.ndarray,
    v_prof: np.ndarray,
    z_prof_or_none: Optional[np.ndarray],
    altitudes_m: np.ndarray,
    *,
    allow_extrapolation: bool = False,
) -> Dict[str, np.ndarray]:
    """Interpolate vertical wind profile to requested altitudes (m)."""
    lev_hPa = np.asarray(lev_hPa, float)
    u_prof = np.asarray(u_prof, float)
    v_prof = np.asarray(v_prof, float)
    alts = np.asarray(altitudes_m, float)
    if alts.ndim != 1 or alts.size == 0:
        raise InterpolationError("altitudes_m must be non-empty 1D.")

    if z_prof_or_none is not None:
        z = np.asarray(z_prof_or_none, float)
        if z.shape != u_prof.shape or z.shape != v_prof.shape:
            raise InterpolationError("Shape mismatch among profiles.")
        order = np.argsort(z)
        z, u, v, p = z[order], u_prof[order], v_prof[order], lev_hPa[order]

        zmin, zmax = float(z.min()), float(z.max())
        if not allow_extrapolation and ((alts < zmin).any() or (alts > zmax).any()):
            raise InterpolationError(
                f"Altitude outside range [{zmin:.0f}, {zmax:.0f}] m."
            )
        alts_q = np.clip(alts, zmin, zmax) if allow_extrapolation else alts
        return {
            "u_ms": np.interp(alts_q, z, u),
            "v_ms": np.interp(alts_q, z, v),
            "pressure_hPa": np.interp(alts_q, z, p),
        }

    p_target = pressure_at_height_std_1976(alts) / 100.0
    return {
        "u_ms": _log_interp(p_target, lev_hPa, u_prof),
        "v_ms": _log_interp(p_target, lev_hPa, v_prof),
        "pressure_hPa": p_target,
    }


# ====================================================================
# Fast spatial sampling (unchanged)
# ====================================================================

def _normalize_lon_for_ds(ds: xr.Dataset, lon: float) -> float:
    """Normalize longitude to dataset convention."""
    maxlon = float(ds["lon"].max())
    if maxlon > 180.0:
        lo = lon % 360.0
        return lo if lo >= 0 else lo + 360.0
    return ((lon + 180.0) % 360.0) - 180.0


def _find_ll_indices_and_weights(
    lat_vals: np.ndarray, lon_vals: np.ndarray,
    lat: float, lon: float,
) -> Tuple[int, int, float, float]:
    """Lower-left indices and bilinear weights on a regular grid."""
    lat_arr = np.asarray(lat_vals, float)
    lon_arr = np.asarray(lon_vals, float)

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
        wy = (y0 - lat) / (y0 - y1) if y1 != y0 else 0.0

    j1 = np.searchsorted(lon_arr, lon, side="right") - 1
    j = max(0, min(j1, lon_arr.size - 2))
    x0, x1 = lon_arr[j], lon_arr[j + 1]
    wx = (lon - x0) / (x1 - x0) if x1 != x0 else 0.0

    return i, j, max(0.0, min(1.0, wy)), max(0.0, min(1.0, wx))


def _bilinear_blend(
    q11: np.ndarray, q21: np.ndarray,
    q12: np.ndarray, q22: np.ndarray,
    wx: float, wy: float,
) -> np.ndarray:
    """Bilinear blend."""
    return (
        (1.0 - wx) * (1.0 - wy) * q11
        + wx * (1.0 - wy) * q21
        + (1.0 - wx) * wy * q12
        + wx * wy * q22
    )


def _sample_profile_ultra(
    ds: xr.Dataset,
    valid_time: np.datetime64,
    lat: float,
    lon: float,
    cache: Optional[MutableMapping] = None,
) -> Dict[str, np.ndarray]:
    """2×2 bilinear sampler for u/v/(hgt) profiles."""
    try:
        dst = ds.sel(time=valid_time)
    except Exception:
        dst = ds.sel(time=valid_time, method="nearest")

    lon_norm = _normalize_lon_for_ds(dst, lon)
    lat_vals = np.asarray(dst["lat"].values, float)
    lon_vals = np.asarray(dst["lon"].values, float)

    i, j, wy, wx = _find_ll_indices_and_weights(
        lat_vals, lon_vals, float(lat), float(lon_norm),
    )
    j2 = (j + 1) % lon_vals.size

    key = None
    if cache is not None:
        tbin = int(np.array(valid_time).astype("datetime64[h]").astype("int64"))
        key = (tbin, int(i), int(j))
        hit = cache.get(key)
        if hit is not None:
            lev, u2x2, v2x2, z2x2 = hit
        else:
            lev = np.asarray(dst["lev"].values, float)
            block = dst.isel(lat=slice(i, i + 2), lon=[j, j2])
            u2x2 = np.asarray(block["ugrdprs"].values, float)
            v2x2 = np.asarray(block["vgrdprs"].values, float)
            z2x2 = (
                np.asarray(block[_PREFERRED_VAR].values, float)
                if _PREFERRED_VAR in block else None
            )
            cache[key] = (lev, u2x2, v2x2, z2x2)
    else:
        lev = np.asarray(dst["lev"].values, float)
        block = dst.isel(lat=slice(i, i + 2), lon=[j, j2])
        u2x2 = np.asarray(block["ugrdprs"].values, float)
        v2x2 = np.asarray(block["vgrdprs"].values, float)
        z2x2 = (
            np.asarray(block[_PREFERRED_VAR].values, float)
            if _PREFERRED_VAR in block else None
        )

    u_prof = _bilinear_blend(u2x2[:, 0, 0], u2x2[:, 0, 1], u2x2[:, 1, 0], u2x2[:, 1, 1], wx, wy)
    v_prof = _bilinear_blend(v2x2[:, 0, 0], v2x2[:, 0, 1], v2x2[:, 1, 0], v2x2[:, 1, 1], wx, wy)
    z_prof = None
    if z2x2 is not None:
        z_prof = _bilinear_blend(z2x2[:, 0, 0], z2x2[:, 0, 1], z2x2[:, 1, 0], z2x2[:, 1, 1], wx, wy)

    return {"lev_hPa": lev, "u_ms": u_prof, "v_ms": v_prof, "z_m": z_prof}


# ====================================================================
# Wind vector math (unchanged)
# ====================================================================

def wind_from_dir_deg(u_ms: np.ndarray, v_ms: np.ndarray) -> np.ndarray:
    """Meteorological FROM direction [0..360)."""
    return (np.degrees(np.arctan2(-u_ms, -v_ms)) + 360.0) % 360.0


def project_head_cross(
    u_ms: np.ndarray, v_ms: np.ndarray, heading_deg: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Headwind (+ against) and crosswind (+ from right)."""
    th = math.radians(float(heading_deg))
    along = u_ms * math.sin(th) + v_ms * math.cos(th)
    return -along, u_ms * math.cos(th) - v_ms * math.sin(th)


# ====================================================================
# Threading (unchanged)
# ====================================================================

@dataclass
class ThreadHandle:
    thread: threading.Thread
    _cancel_event: threading.Event

    def cancel(self) -> None:
        self._cancel_event.set()

    def is_alive(self) -> bool:
        return self.thread.is_alive()


def run_in_thread(func: Callable, *args, **kwargs) -> ThreadHandle:
    """Run callable in a background thread."""
    cancel_event = threading.Event()
    kwargs = dict(kwargs)
    kwargs.setdefault("cancel_event", cancel_event)

    def wrapper():
        try:
            func(*args, **kwargs)
        except Exception:
            pass

    th = threading.Thread(target=wrapper, daemon=True)
    th.start()
    return ThreadHandle(thread=th, _cancel_event=cancel_event)


# ====================================================================
# Main orchestrator
# ====================================================================

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
    High-level calculator.

    ``source`` may be:
    - An xr.Dataset (from ``fetch_gfs_partial_grib`` — recommended),
    - An OPeNDAP URL string (legacy),
    - A local GRIB2 file path.
    """
    def report(pct, stage):
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

    alts_raw = np.asarray(altitudes_m, float)
    if alts_raw.ndim == 0 or (alts_raw.ndim == 1 and alts_raw.size == 1):
        mode = "scalar_for_all"
        alts_common = np.array([float(alts_raw.reshape(()))], dtype=float)
        M = 1
    elif alts_raw.ndim == 1 and alts_raw.size == N:
        mode = "per_waypoint"
        M = 1
    elif alts_raw.ndim == 1 and alts_raw.size > 1:
        mode = "common_list"
        alts_common = alts_raw.astype(float)
        M = alts_common.size
    else:
        raise ValueError("altitudes_m must be scalar, shape (N,), or shape (M,)")

    if isinstance(source, xr.Dataset):
        ds = source
        src_meta = "dataset:local"
    elif isinstance(source, str):
        if source.startswith("http"):
            report(5.0, "open_dataset (OPeNDAP)")
            ds = open_gfs_opendap(source)
            src_meta = f"opendap:{source}"
        else:
            report(5.0, "open_dataset (local GRIB)")
            ds = open_gfs_grib(source)
            src_meta = f"grib:{source}"
    else:
        raise ValueError("source must be URL, path, or xr.Dataset")

    report(10.0, "time_selection")
    valid_time = select_valid_time(ds, forecast_hour=forecast_hour, target_valid_time=target_valid_time)

    has_height = _PREFERRED_VAR in ds
    tile_cache: Dict = {}

    if mode in ("scalar_for_all", "per_waypoint"):
        shape: Union[Tuple[int], Tuple[int, int]] = (N,)
    else:
        shape = (N, M)

    u_out = np.empty(shape, np.float32)
    v_out = np.empty(shape, np.float32)
    p_out = np.empty(shape, np.float32)
    spd_out = np.empty(shape, np.float32)
    wdir_out = np.empty(shape, np.float32)
    head_out = np.empty(shape, np.float32)
    cross_out = np.empty(shape, np.float32)

    report(15.0, "sampling")
    for i, (plat, plon) in enumerate(latlons):
        if cancel_cb is not None and cancel_cb():
            raise CancelledError("Cancelled by user.")

        report(15.0 + (i + 1) / N * 80.0, "looping through waypoints")

        prof = _sample_profile_ultra(
            ds, valid_time, float(plat), float(plon), cache=tile_cache,
        )
        if cache_size > 0 and len(tile_cache) > cache_size:
            tile_cache.clear()

        if mode == "per_waypoint":
            alts_here = np.array([alts_raw[i]], dtype=float)
        elif mode == "scalar_for_all":
            alts_here = alts_common
        else:
            alts_here = alts_common

        res = interp_wind_to_altitudes(
            prof["lev_hPa"], prof["u_ms"], prof["v_ms"],
            prof["z_m"] if has_height else None,
            alts_here, allow_extrapolation=allow_extrapolation,
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

    result: Dict[str, Union[np.ndarray, dict]] = {
        "meta": meta,
        "waypoints": latlons.astype(np.float64),
        "headings_deg": headings.astype(np.float64),
        "pressure_hPa": p_out,
        "u_ms": u_out, "v_ms": v_out,
        "wind_speed_ms": spd_out,
        "wind_from_deg": wdir_out,
        "headwind_ms": head_out,
        "crosswind_ms": cross_out,
    }

    if mode == "per_waypoint":
        result["altitudes_m"] = alts_raw.astype(np.float64)
    elif mode == "scalar_for_all":
        result["altitudes_m"] = np.full((N,), float(alts_common[0]), np.float64)
    else:
        result["altitudes_m"] = alts_common.astype(np.float64)

    report(100.0, "done")
    return result


# ====================================================================
# Convenience progress callback
# ====================================================================

import sys

def progress_cb(percent: float, stage: str):
    bar_len = 40
    filled = int(bar_len * max(0, min(100, percent)) / 100)
    bar = "█" * filled + "-" * (bar_len - filled)
    sys.stdout.write(f"\r[{bar}] {percent:5.1f}%  {stage:40s}")
    sys.stdout.flush()
    if percent >= 100:
        sys.stdout.write("\n")