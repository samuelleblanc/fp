import io
import re
import csv
import math
import json
import time
from typing import List, Dict, Tuple, Optional, Any

import requests

# -----------------------------
# FAA NAT source (NOTAM-style)
# -----------------------------
NAT_URL = "https://www.notams.faa.gov/common/nat.html"

# -----------------------------
# Optional: open datasets to resolve named points (fixes/navaids)
# OurAirports navaids (VOR, NDB, VORTAC, etc.) — public domain
# FAA NASR FIX CSV (requires manual download of the 28-Day Subscription ZIP, then path to FIX_BASE.csv)
# -----------------------------
OURAIRPORTS_NAVAIDS_CSV = "https://davidmegginson.github.io/ourairports-data/navaids.csv"  # public mirror
# If you have a local FAA NASR FIX file, set FIX_BASE_CSV = r"/path/to/FIX_BASE.csv"
FIX_BASE_CSV = None  # or set a path string

# -----------------------------------------------------------
# Utilities: coordinate parsing for NAT NOTAM coordinate styles
# -----------------------------------------------------------
def _to_signed(deg: float, hemi: str) -> float:
    hemi = hemi.upper()
    if hemi in ("S", "W"):
        return -abs(deg)
    return abs(deg)

def _parse_dd_slash_ddd(token: str) -> Optional[Tuple[float, float]]:
    """
    NAT common shorthand: '61/20' -> 61N, 020W (assume N/W hemisphere for NAT region)
    Returns (lat, lon) or None if not matching.
    """
    m = re.fullmatch(r"(\d{2})(?:\.(\d+))?\/(\d{2,3})(?:\.(\d+))?", token.strip())
    if not m:
        return None
    lat = float(f"{m.group(1)}.{m.group(2) or '0'}")
    lon = float(f"{m.group(3)}.{m.group(4) or '0'}")
    return (lat, -lon)  # NAT: default N, W

def _parse_compact_pair(tokens: List[str], i: int) -> Tuple[Optional[Tuple[float, float]], int]:
    """
    Handle compact pairs like:
      '5230N' '02000W'  -> 52°30'N, 20°00'W
      '52N'   '020W'    -> 52°N,     20°W
    Returns ((lat,lon), tokens_consumed)
    """
    t1 = tokens[i]
    t2 = tokens[i + 1] if i + 1 < len(tokens) else None
    if not t2:
        return (None, 1)

    m1 = re.fullmatch(r"(\d{2})(\d{2})?([NS])", t1.upper())
    m2 = re.fullmatch(r"(\d{2,3})(\d{2})?([EW])", t2.upper())
    if not (m1 and m2):
        return (None, 1)

    lat_deg = int(m1.group(1))
    lat_min = int(m1.group(2)) if m1.group(2) else 0
    lat = lat_deg + lat_min / 60.0
    lat = _to_signed(lat, m1.group(3))

    lon_deg = int(m2.group(1))
    lon_min = int(m2.group(2)) if m2.group(2) else 0
    lon = lon_deg + lon_min / 60.0
    lon = _to_signed(lon, m2.group(3))

    return ((lat, lon), 2)

def _parse_ddNdddW(token: str) -> Optional[Tuple[float, float]]:
    """
    Handle '50N030W' or with minutes '5030N02000W' in a single token? (Rare in this feed)
    If encountered, decode; otherwise return None.
    """
    t = token.upper()
    # With minutes for both lat/lon: e.g., 5230N02000W
    m = re.fullmatch(r"(\d{2})(\d{2})?([NS])(\d{2,3})(\d{2})?([EW])", t)
    if not m:
        return None
    lat_deg = int(m.group(1))
    lat_min = int(m.group(2)) if m.group(2) else 0
    lat = _to_signed(lat_deg + lat_min / 60.0, m.group(3))

    lon_deg = int(m.group(4))
    lon_min = int(m.group(5)) if m.group(5) else 0
    lon = _to_signed(lon_deg + lon_min / 60.0, m.group(6))

    return (lat, lon)

def decode_waypoint_tokens(tokens: List[str]) -> List[Dict[str, Any]]:
    """
    Convert a sequence of NAT tokens into structured waypoints:
      - coordinate tokens -> {'name': None, 'lat': xx, 'lon': yy}
      - named fixes -> {'name': 'BALIX', 'lat': None, 'lon': None}
    Handles multiple formats: '61/20', '50N030W', '5230N 02000W'
    Returns list preserving order.
    """
    out: List[Dict[str, Any]] = []
    i = 0
    while i < len(tokens):
        t = tokens[i].strip().strip(",;")
        if not t:
            i += 1
            continue

        # 1) dd/ddd pattern (N/W by convention in NAT)
        ll = _parse_dd_slash_ddd(t)
        if ll:
            out.append({"name": None, "lat": ll[0], "lon": ll[1], "raw": t})
            i += 1
            continue

        # 2) single token with N/E/S/W inside (ddNdddW or ddmmNdddmmW)
        ll = _parse_ddNdddW(t)
        if ll:
            out.append({"name": None, "lat": ll[0], "lon": ll[1], "raw": t})
            i += 1
            continue

        # 3) compact two-token pair: '5230N' '02000W'
        if i + 1 < len(tokens):
            ll2, consumed = _parse_compact_pair(tokens, i)
            if ll2:
                out.append({"name": None, "lat": ll2[0], "lon": ll2[1], "raw": " ".join(tokens[i:i+consumed])})
                i += consumed
                continue

        # 4) if none matched, assume it's a named fix/waypoint
        #    (e.g., BALIX, URTAK, CUDDY, MALOT, etc.)
        name = re.sub(r"[^A-Z0-9]", "", t.upper())
        out.append({"name": name or t.upper(), "lat": None, "lon": None, "raw": t})
        i += 1

    return out

# -----------------------------------------------------------
# NAT page parsing
# -----------------------------------------------------------
TRACK_LINE_RE = re.compile(
    r"^\s*([A-Z])\s+([A-Z0-9]+)\s+(.+?)\s*$"
)
STOP_KEYS = ("EAST LVLS", "WEST LVLS", "EUR RTS", "NAR", "REMARKS", "END OF PART")

def fetch_nat_text(url: str = NAT_URL, timeout: int = 20) -> str:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    # Some lines may contain non-printables; normalize to text
    return r.text

def parse_nat_tracks(page_text: str) -> List[Dict[str, Any]]:
    """
    Extract track segments from the FAA NAT page.
    Returns a list of dicts:
      { 'track_id': 'A', 'entry': 'BALIX', 'exit': 'URTAK',
        'waypoints': [ {'name':..., 'lat':..., 'lon':...}, ... ],
        'window': 'SEP 12/1130Z TO SEP 12/1900Z', 'raw_line': 'A BALIX 61/20 ... URTAK' }
    We parse both Shanwick (EGGX) and Gander (CZQX) blocks.
    """
    lines = [l.strip() for l in page_text.splitlines() if l.strip()]
    # capture current validity window as we pass lines like: "SEP 12/1130Z TO SEP 12/1900Z"
    current_window = None
    tracks: List[Dict[str, Any]] = []

    for idx, line in enumerate(lines):
        if re.search(r"\bTO\b\s+[A-Z]{3}\s*\d{4}Z", line) or re.search(r"\bTO\b\s+\w+\s*\d{4}Z", line):
            # crude: remember the most recent validity window line
            current_window = line

        m = TRACK_LINE_RE.match(line)
        if not m:
            continue

        track_id = m.group(1)
        first_token = m.group(2)
        rest = m.group(3)

        # Accumulate continuation tokens on following lines until a stop key appears
        tokens: List[str] = [first_token]
        # split rest of this line first
        tokens += rest.split()

        j = idx + 1
        while j < len(lines):
            nxt = lines[j]
            if any(sk in nxt for sk in STOP_KEYS):
                break
            # stop if next line starts a new track designator like "B " or "R " in eastbound set
            if TRACK_LINE_RE.match(nxt):
                break
            tokens += nxt.split()
            j += 1

        # Clean tailing hyphens
        if tokens and tokens[-1].endswith("-"):
            tokens[-1] = tokens[-1].rstrip("-")

        # Decode tokens into lat/lon or names
        wpts = decode_waypoint_tokens(tokens)

        # entry/exit names are often first/last named (if any)
        named = [w for w in wpts if w["name"]]
        entry = named[0]["name"] if named else None
        exit_ = named[-1]["name"] if len(named) >= 1 else None

        tracks.append({
            "track_id": track_id,
            "entry": entry,
            "exit": exit_,
            "waypoints": wpts,
            "window": current_window,
            "raw_line": line
        })

    return tracks

# -----------------------------------------------------------
# Optional: resolve named fixes/navaids to lat/lon
# -----------------------------------------------------------
def _download_csv(url: str, timeout: int = 30) -> List[Dict[str, str]]:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    content = r.content.decode("utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(content)))

def load_ourairports_navaids() -> Dict[str, Tuple[float, float]]:
    """
    Load OurAirports navaids.csv and build a lookup by IDENT and NAME.
    Note: many NAT named points are 'fixes' (5-letter intersections), which OurAirports may not include.
    """
    lookup: Dict[str, Tuple[float, float]] = {}
    try:
        rows = _download_csv(OURAIRPORTS_NAVAIDS_CSV)
        for r in rows:
            ident = (r.get("ident") or "").strip().upper()
            name = (r.get("name") or "").strip().upper()
            try:
                lat = float(r.get("latitude_deg") or "")
                lon = float(r.get("longitude_deg") or "")
            except ValueError:
                continue
            if ident:
                lookup[ident] = (lat, lon)
            if name:
                lookup[name] = (lat, lon)
    except Exception:
        pass
    return lookup

def load_faa_fixbase_csv(path: str) -> Dict[str, Tuple[float, float]]:
    """
    Load FAA NASR FIX_BASE.csv, build lookup by FIX_ID (5-letter) and/or FIX_NAME if available.
    You must download & unzip FAA "28 Day NASR Subscription" and pass the local FIX_BASE.csv path.
    """
    lookup: Dict[str, Tuple[float, float]] = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # The exact column names can vary in legacy vs CSV; common are FIX_ID, LAT_DECIMAL, LONG_DECIMAL
            keys = {k.upper(): k for k in r.keys()}
            fid = (r.get(keys.get("FIX_ID"), "") or "").strip().upper()
            try:
                lat = float(r.get(keys.get("LAT_DECIMAL"), "") or r.get(keys.get("LATITUDE_DECIMAL"), ""))
                lon = float(r.get(keys.get("LONG_DECIMAL"), "") or r.get(keys.get("LONGITUDE_DECIMAL"), ""))
            except ValueError:
                continue
            if fid and math.isfinite(lat) and math.isfinite(lon):
                lookup[fid] = (lat, lon)
    return lookup

def resolve_named_points_in_tracks(
    tracks: List[Dict[str, Any]],
    fix_csv_path: Optional[str] = FIX_BASE_CSV
) -> List[Dict[str, Any]]:
    """
    Enrich named waypoints using available databases (NASR FIX first if given, then OurAirports navaids).
    """
    oa_nav = load_ourairports_navaids()
    nasr_fix = load_faa_fixbase_csv(fix_csv_path) if fix_csv_path else {}

    def resolve_one(name: str) -> Optional[Tuple[float, float]]:
        # Priority: NASR FIX (for 5-letter waypoints), then OurAirports navaids
        if name in nasr_fix:
            return nasr_fix[name]
        if name in oa_nav:
            return oa_nav[name]
        return None

    for trk in tracks:
        for w in trk["waypoints"]:
            if w["name"] and (w["lat"] is None or w["lon"] is None):
                ll = resolve_one(w["name"])
                if ll:
                    w["lat"], w["lon"] = ll
    return tracks

# -----------------------------------------------------------
# GeoJSON + Cartopy helpers
# -----------------------------------------------------------
def tracks_to_geojson(tracks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert tracks to a GeoJSON FeatureCollection (LineString per track).
    Any unresolved named points without coordinates are skipped for the line, but kept in properties.
    """
    features = []
    for trk in tracks:
        coords = []
        unresolved = []
        for w in trk["waypoints"]:
            if w["lat"] is not None and w["lon"] is not None:
                coords.append([w["lon"], w["lat"]])  # GeoJSON is [lon, lat]
            elif w["name"]:
                unresolved.append(w["name"])
        if len(coords) >= 2:
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "track_id": trk["track_id"],
                    "entry": trk["entry"],
                    "exit": trk["exit"],
                    "window": trk.get("window"),
                    "unresolved_waypoints": unresolved,
                    "raw_line": trk.get("raw_line")
                }
            })
    return {"type": "FeatureCollection", "features": features}

# -----------------------------------------------------------
# Entry point
# -----------------------------------------------------------
def fetch_and_decode_nat(fix_csv_path: Optional[str] = FIX_BASE_CSV) -> Dict[str, Any]:
    """
    High-level convenience:
      1) fetch current NAT page
      2) parse tracks
      3) resolve named points (if DBs available)
      4) return geojson + tracks
    """
    text = fetch_nat_text()
    tracks = parse_nat_tracks(text)
    tracks = resolve_named_points_in_tracks(tracks, fix_csv_path=fix_csv_path)
    gj = tracks_to_geojson(tracks)
    return {"tracks": tracks, "geojson": gj}

if __name__ == "__main__":
    data = fetch_and_decode_nat(fix_csv_path=FIX_BASE_CSV)
    # Print a quick summary
    for trk in data["tracks"]:
        wcount = sum(1 for w in trk["waypoints"] if w["lat"] is not None)
        print(f"Track {trk['track_id']}: {wcount} resolved points; window={trk.get('window')}")
    # Save GeoJSON
    with open("nat_tracks.geojson", "w", encoding="utf-8") as f:
        json.dump(data["geojson"], f, ensure_ascii=False, indent=2)
    print("Wrote nat_tracks.geojson")
