"""
FAA NAT OTS fetch + parse + *lazy* OpenNav fix resolution with ORDER-PRESERVING lats/lons.

What you asked for:
- Preserve the original point order (coords + named fixes) in lats/lons.
- Before fixes are resolved, insert temporary placeholders in lats/lons (default: None).
- Only resolve fixes that appear in the NAT tracks, and only when requested (dry_run=False).
- Print command-line summaries:
    - number of tracks parsed
    - number of unique fixes found
    - how many are already cached / newly needed
    - per-run resolution stats and totals
    - per-track % resolved if you want (toggle)

Design:
- Each track stores an internal ordered token list (route_tokens).
- We maintain lats/lons aligned with route_tokens:
    - coord tokens -> numeric lat/lon
    - named fixes -> None/None until resolved (then replaced)
- Cache JSON stores hits (lat,lon) and misses (null) keyed by IDENT
"""

from __future__ import annotations

import os
import re
import json
import time
from html import unescape
from typing import Optional, Tuple, Dict, List, Set, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from datetime import datetime, timezone


FAA_NAT_URL = "https://notams.aim.faa.gov/nat.html"
LatLon = Tuple[float, float]  # (lat, lon)


# =============================================================================
# 1) Robust fetcher (browser-like session + retries)
# =============================================================================

def fetch_faa_nat_html(timeout: Tuple[int, int] = (10, 30)) -> str:
    s = requests.Session()

    retries = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=True,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))

    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://notams.aim.faa.gov/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })

    r = s.get(FAA_NAT_URL, timeout=timeout)
    r.raise_for_status()
    return r.text


# =============================================================================
# 2) HTML cleanup
# =============================================================================

_RE_TAG = re.compile(r"<[^>]+>")
_RE_MULTISPACE = re.compile(r"[ \t]+")

def nat_html_to_text(html: str) -> str:
    if not html:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", html)
    s = _RE_TAG.sub("", s)
    s = unescape(s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # remove control chars except newline
    s = "".join(ch for ch in s if (ch == "\n") or (ord(ch) >= 32))
    s = "\n".join(_RE_MULTISPACE.sub(" ", ln).strip() for ln in s.split("\n"))
    s = "\n".join(ln for ln in s.split("\n") if ln.strip())
    return s


# =============================================================================
# 3) NAT parsing helpers
# =============================================================================

def _parse_nat_coord(tok: str) -> Optional[LatLon]:
    """
    Parse NAT coord tokens into (lat, lon) decimal degrees.
    Assumes NAT convention: N and W unless explicit hemispheres.
    Supports:
      - 50/50
      - 5230/40
      - 52.5/30
      - 5230N02000W
    """
    t = tok.strip().upper()

    # ddmmNdddmmW
    m = re.fullmatch(r"(\d{4})([NS])(\d{5})([EW])", t)
    if m:
        lat_ddmm = int(m.group(1))
        ns = m.group(2)
        lon_dddmm = int(m.group(3))
        ew = m.group(4)

        lat_deg, lat_min = divmod(lat_ddmm, 100)
        lon_deg, lon_min = divmod(lon_dddmm, 100)

        lat = lat_deg + lat_min / 60.0
        lon = lon_deg + lon_min / 60.0
        if ns == "S":
            lat = -lat
        if ew == "W":
            lon = -lon
        return (lat, lon)

    # ddmm/ddd or dd/ddd or dd.d/ddd (optionally ddmm on lat side)
    m = re.fullmatch(r"(\d{2})(?:\.(\d))?(\d{2})?/(\d{2,3})(?:\.(\d))?", t)
    if m:
        lat_deg = int(m.group(1))
        lat_half = m.group(2)
        lat_min = m.group(3)
        lon_deg = int(m.group(4))
        lon_half = m.group(5)

        lat = float(lat_deg)
        if lat_min is not None:
            lat += int(lat_min) / 60.0
        if lat_half is not None:
            lat += float(f"0.{lat_half}")

        lon = float(lon_deg)
        if lon_half is not None:
            lon += float(f"0.{lon_half}")

        return (lat, -lon)

    return None


def _parse_lvls(line: str) -> List[int]:
    u = line.upper()
    if "NIL" in u:
        return []
    return [int(x) for x in re.findall(r"\b(\d{3})\b", u)]


def _parse_validity(text: str) -> Tuple[Optional[str], Optional[str]]:
    m = re.search(
        r"\b([A-Z]{3})\s+(\d{2})/(\d{4})Z\s+TO\s+([A-Z]{3})\s+(\d{2})/(\d{4})Z\b",
        text.upper()
    )
    if not m:
        return None, None

    year = datetime.now(timezone.utc).year
    mon1, d1, t1 = m.group(1), int(m.group(2)), m.group(3)
    mon2, d2, t2 = m.group(4), int(m.group(5)), m.group(6)

    try:
        dt1 = datetime.strptime(f"{year} {mon1} {d1:02d} {t1}", "%Y %b %d %H%M").replace(tzinfo=timezone.utc)
        dt2 = datetime.strptime(f"{year} {mon2} {d2:02d} {t2}", "%Y %b %d %H%M").replace(tzinfo=timezone.utc)
        return dt1.isoformat(), dt2.isoformat()
    except ValueError:
        return None, None


# =============================================================================
# 4) Track parsing that preserves order (lats/lons aligned with route_tokens)
# =============================================================================

def parse_faa_nat_text_ordered(text: str, placeholder: Any = None, verbose: bool = True) -> Tuple[Dict[str, dict], Set[str]]:
    """
    Returns:
      tracks_dict, unique_fix_idents

    tracks_dict keys match your expected shape PLUS an internal 'route_tokens' list.
    lats/lons are the same length as route_tokens, aligned positionally.
      - coordinate token -> numeric lat/lon
      - named fix token -> placeholder/placeholder initially
    navaid list preserves the named-fix order of appearance: (ident, lon, lat) initially (ident, None, None).
    """
    validFrom, validTo = _parse_validity(text)

    out: Dict[str, dict] = {}
    fixes: Set[str] = set()
    current_track: Optional[str] = None

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    def looks_like_track_line(ln: str) -> bool:
        if not re.match(r"^[A-Z]\s+\S+", ln):
            return False
        u = ln.upper()
        if u.startswith(("NAT-", "PART", "END OF", "REMARK", "EUR", "NAR", "OTS", "TRACKS")):
            return False
        toks = ln.split()
        return any(_parse_nat_coord(tok) is not None for tok in toks[1:])

    for ln in lines:
        u = ln.upper()

        if looks_like_track_line(ln):
            tid = ln.split()[0].upper()
            tokens = [t.upper() for t in ln.split()[1:]]

            route_tokens: List[str] = []
            lats: List[Any] = []
            lons: List[Any] = []
            navaid: List[tuple] = []

            for tok in tokens:
                route_tokens.append(tok)
                ll = _parse_nat_coord(tok)
                if ll is not None:
                    lat, lon = ll
                    lats.append(lat)
                    lons.append(lon)
                else:
                    fixes.add(tok)
                    lats.append(placeholder)
                    lons.append(placeholder)
                    navaid.append((tok, None, None))

            out[tid] = {
                "route_tokens": route_tokens,   # internal
                "lats": lats,
                "lons": lons,
                "validFrom": validFrom,
                "validTo": validTo,
                "navaid": navaid,
                "levels": [],
                "_east": [],
                "_west": [],
            }
            current_track = tid
            continue

        if current_track and current_track in out:
            if u.startswith("EAST LVLS"):
                out[current_track]["_east"] = _parse_lvls(ln)
            elif u.startswith("WEST LVLS"):
                out[current_track]["_west"] = _parse_lvls(ln)
                out[current_track]["levels"] = out[current_track]["_east"] + out[current_track]["_west"]

    for tid in list(out.keys()):
        out[tid].pop("_east", None)
        out[tid].pop("_west", None)

    if verbose:
        print(f"[NAT] Parsed {len(out)} tracks from bulletin.")
        print(f"[NAT] Found {len(fixes)} unique named fixes in tracks.")

    return out, fixes


# =============================================================================
# 5) OpenNav resolver: resolve ONLY missing fixes, update cache
# =============================================================================

DEFAULT_OPENNAV_COUNTRIES = ["UK", "IE", "CA", "US", "IS", "GL", "FR", "ES", "PT", "NO", "NL", "BE", "DE"]

_RE_LAT = re.compile(r"Latitude\s+(\d+)[°]\s+(\d+)[']\s+([\d.]+)\"?\s+([NS])", re.IGNORECASE)
_RE_LON = re.compile(r"Longitude\s+(\d+)[°]\s+(\d+)[']\s+([\d.]+)\"?\s+([EW])", re.IGNORECASE)

def _dms_to_dd(deg: float, minutes: float, seconds: float, hemi: str) -> float:
    dd = float(deg) + float(minutes) / 60.0 + float(seconds) / 3600.0
    if hemi.upper() in ("S", "W"):
        dd = -dd
    return dd

LatLon = Tuple[float, float]

_RE_META_LAT = re.compile(r'itemprop="latitude"\s+content="([+-]?\d+(?:\.\d+)?)"', re.IGNORECASE)
_RE_META_LON = re.compile(r'itemprop="longitude"\s+content="([+-]?\d+(?:\.\d+)?)"', re.IGNORECASE)

_RE_LATLNG_JS = re.compile(
    r'new\s+google\.maps\.LatLng\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*\)',
    re.IGNORECASE
)

# DMS fallback (allows optional backslash before apostrophe in case it appears as \')
_RE_LAT_DMS = re.compile(r"Latitude.*?(\d+)[°]\s+(\d+)(?:\\')?'\s+([\d.]+)\"?\s*([NS])", re.IGNORECASE | re.DOTALL)
_RE_LON_DMS = re.compile(r"Longitude.*?(\d+)[°]\s+(\d+)(?:\\')?'\s+([\d.]+)\"?\s*([EW])", re.IGNORECASE | re.DOTALL)

def _parse_opennav_waypoint_html(html: str) -> Optional[LatLon]:
    # 1) Schema.org meta tags (best)
    mlat = _RE_META_LAT.search(html)
    mlon = _RE_META_LON.search(html)
    if mlat and mlon:
        lat = float(mlat.group(1))
        lon = float(mlon.group(1))
        return (lat, lon)

    # 2) Google Maps LatLng in script
    m = _RE_LATLNG_JS.search(html)
    if m:
        lat = float(m.group(1))
        lon = float(m.group(2))
        return (lat, lon)

    # 3) DMS fallback (less reliable)
    mlat = _RE_LAT_DMS.search(html)
    mlon = _RE_LON_DMS.search(html)
    if mlat and mlon:
        lat = _dms_to_dd(mlat.group(1), mlat.group(2), mlat.group(3), mlat.group(4))
        lon = _dms_to_dd(mlon.group(1), mlon.group(2), mlon.group(3), mlon.group(4))
        return (lat, lon)

    return None

def load_cache(cache_path: str) -> dict:
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_cache(cache_path: str, cache: dict) -> None:
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    tmp = cache_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True)
    os.replace(tmp, cache_path)

def resolve_missing_fixes_via_opennav(
    fixes: Set[str],
    cache_path: str,
    countries: Optional[List[str]] = None,
    dry_run: bool = True,
    timeout: int = 15,
    sleep_s: float = 0.15,
    verbose: bool = True,
) -> Tuple[dict, Dict[str, Optional[LatLon]]]:
    """
    Resolve ONLY fixes in `fixes` that are not present in cache yet.

    Cache stores:
      ident -> [lat, lon]   (hit)
      ident -> null         (miss)

    Returns:
      (updated_cache, results_for_this_run)
    """
    if countries is None:
        countries = list(DEFAULT_OPENNAV_COUNTRIES)

    cache = load_cache(cache_path)

    need = sorted([f for f in fixes if f not in cache])
    already = len(fixes) - len(need)

    if verbose:
        print(f"[OpenNav] Cache path: {cache_path}")
        print(f"[OpenNav] Unique fixes in tracks: {len(fixes)}")
        print(f"[OpenNav] Already cached: {already}")
        print(f"[OpenNav] Need to query OpenNav: {len(need)} (dry_run={dry_run})")

    results: Dict[str, Optional[LatLon]] = {}

    if dry_run:
        # No web requests; just report which would be queried
        for ident in need:
            results[ident] = None
        if verbose and need:
            print("[OpenNav] Would query (sample):", ", ".join(need[:30]) + (" ..." if len(need) > 30 else ""))
        return cache, results

    session = requests.Session()
    session.headers.update({
        "User-Agent": "movinglines-nat-parser/1.0",
        "Accept": "text/html,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
    })

    hits = 0
    misses = 0

    for i, ident in enumerate(need, 1):
        ll_found: Optional[LatLon] = None

        for cc in countries:
            url = f"https://opennav.com/waypoint/{cc}/{ident}"
            try:
                r = session.get(url, timeout=timeout)
                if r.status_code != 200:
                    continue
                ll = _parse_opennav_waypoint_html(r.text)
                if ll:
                    ll_found = ll
                    break
            except Exception:
                continue
            finally:
                time.sleep(sleep_s)

        if ll_found:
            cache[ident] = [ll_found[0], ll_found[1]]
            hits += 1
            if verbose:
                print(f"[OpenNav] {i}/{len(need)} HIT  {ident} -> ({ll_found[0]:.6f}, {ll_found[1]:.6f})")
        else:
            #cache[ident] = None
            misses += 1
            if verbose:
                print(f"[OpenNav] {i}/{len(need)} MISS {ident}")

        results[ident] = ll_found
        save_cache(cache_path, cache)

    if verbose:
        print(f"[OpenNav] Done. Hits: {hits}, Misses: {misses}")

    return cache, results


# =============================================================================
# 6) Apply cache back to tracks while preserving order
# =============================================================================

def apply_cache_to_tracks_preserve_order(
    tracks: Dict[str, dict],
    cache: dict,
    placeholder: Any = None,
    verbose: bool = True,
) -> Dict[str, dict]:
    """
    For each track, walk route_tokens; if token is a named fix and exists in cache as [lat,lon],
    replace placeholder entries in lats/lons at the same index.

    Also rebuild navaid list as (ident, lon, lat) with resolved coords.
    """
    total_fix_slots = 0
    total_fix_resolved = 0

    for tid, tr in tracks.items():
        tokens = tr.get("route_tokens", [])
        lats = tr.get("lats", [])
        lons = tr.get("lons", [])

        navaid_out = []
        for idx, tok in enumerate(tokens):
            ll = _parse_nat_coord(tok)
            if ll is not None:
                continue  # coordinate already numeric in lats/lons
            total_fix_slots += 1

            val = cache.get(tok)
            if isinstance(val, list) and len(val) == 2:
                lat, lon = float(val[0]), float(val[1])
                lats[idx] = lat
                lons[idx] = lon
                navaid_out.append((tok, lon, lat))
                total_fix_resolved += 1
            else:
                # keep placeholder
                if lats[idx] is not None and lats[idx] != placeholder:
                    # unexpected: but don't crash
                    pass
                lats[idx] = placeholder
                lons[idx] = placeholder
                navaid_out.append((tok, None, None))

        tr["navaid"] = navaid_out
        tr["lats"] = lats
        tr["lons"] = lons

    if verbose:
        print(f"[NAT] Fix slots in all tracks: {total_fix_slots}")
        print(f"[NAT] Resolved fix slots:      {total_fix_resolved}")
        if total_fix_slots:
            print(f"[NAT] Resolve fraction:       {100.0*total_fix_resolved/total_fix_slots:.1f}%")

    return tracks


# =============================================================================
# 7) One-call entrypoint: fetch -> parse -> (optional) resolve -> apply cache
# =============================================================================

def get_NATs_lazy_opennav_cache_ordered(
    cache_path: Optional[str] = None,
    timeout: Tuple[int, int] = (10, 30),
    dry_run: bool = True,
    opennav_countries: Optional[List[str]] = None,
    placeholder: Any = None,
    verbose: bool = True,
    per_track_summary: bool = False,
) -> Tuple[Optional[Dict[str, dict]], dict, Dict[str, Optional[LatLon]]]:
    """
    Returns:
      (tracks_dict or None, updated_cache, resolution_results_this_run)

    - Preserves order of all points in lats/lons (aligned with route_tokens).
    - Named fixes are placeholder until resolved.
    - Resolves ONLY fixes that appear in the current NAT tracks (and only those missing from cache).
    - Prints summary to command line as requested.
    """
    if cache_path is None:
        cache_path = os.path.join(os.path.expanduser("~"), ".movinglines_cache", "opennav", "waypoints_cache.json")

    if verbose:
        print(f"[Fetch] GET {FAA_NAT_URL}")

    html = fetch_faa_nat_html(timeout=timeout)
    text = nat_html_to_text(html)

    tracks, fixes = parse_faa_nat_text_ordered(text, placeholder=placeholder, verbose=verbose)

    cache, results = resolve_missing_fixes_via_opennav(
        fixes=fixes,
        cache_path=cache_path,
        countries=opennav_countries,
        dry_run=dry_run,
        verbose=verbose,
    )

    tracks = apply_cache_to_tracks_preserve_order(tracks, cache, placeholder=placeholder, verbose=verbose)

    if verbose:
        print(f"[NAT] Tracks available: {len(tracks)}")
        if tracks:
            print("[NAT] Track IDs:", ", ".join(sorted(tracks.keys())))

    if per_track_summary and tracks:
        print("\n[NAT] Per-track resolved fix summary:")
        for tid in sorted(tracks.keys()):
            tr = tracks[tid]
            n = len(tr.get("route_tokens", []))
            fix_slots = sum(1 for tok in tr["route_tokens"] if _parse_nat_coord(tok) is None)
            fix_res = sum(1 for ident, lon, lat in tr["navaid"] if lon is not None and lat is not None)
            print(f"  Track {tid}: points={n}, fixes={fix_slots}, fixes_resolved={fix_res}")

    return tracks, cache, results


# =============================================================================
# 8) Example usage
# =============================================================================

#if __name__ == "__main__":
#    # Dry run: do not scrape OpenNav, just show what would be queried
#    tracks, cache, would = get_NATs_lazy_opennav_cache_ordered(
#        dry_run=True,
#        placeholder=None,
#        verbose=True,
#        per_track_summary=False,
#    )

    # To actually resolve and cache missing fixes:
    # tracks, cache, results = get_NATs_lazy_opennav_cache_ordered(dry_run=False, placeholder=None, verbose=True)
