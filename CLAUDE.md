# CLAUDE.md — Moving Lines Flight Planning Software

## Project Overview

Moving Lines (`movinglines`) is a Python GUI application for interactive airborne research flight planning. It links a Cartopy/Matplotlib interactive map to an Excel spreadsheet via xlwings, letting scientists click waypoints on a map and instantly see updated leg times, speeds, solar angles, and fuel estimates. Output formats include KML, ICT, GPX, Excel, CSV, docx, and several FMS-specific formats.

Current version: **1.65** (`movinglines/version.py`).  
Entry point: `ml` CLI command → `movinglines/__init__.py` → `movinglines/ml.py`.

See `general_index.md` at the repo root for a full description of every file.

---

## Architecture

Four classes form the application core. They are tightly coupled — each holds references to the others.

| Class | File | Role |
|-------|------|------|
| `Create_interaction` | `ml.py` | Top-level orchestrator; constructs map, GUI, and Excel objects and wires them together. |
| `LineBuilder` | `map_interactive.py` | Handles all map interaction: click-to-add waypoint, drag, satellite tracks, WMS imagery, blit drawing. |
| `gui` | `gui.py` | Tkinter toolbar and dialogs; button handlers delegate to `LineBuilder` and `dict_position`. |
| `dict_position` | `excel_interface.py` | Waypoint data store; owns the xlwings Excel session and all leg calculations (speed, altitude, SZA, bearing, turn times, etc.). |

Supporting modules (`map_utils.py`, `load_utils.py`, `write_utils.py`, `aeronet.py`, `buoys_utils.py`, `flightnav_utils.py`, `nat_decode.py`, `GFS_interp_utils.py`) are stateless helpers called by the four core classes.

---

## Key Configuration Files (not Python)

| File | Purpose |
|------|---------|
| `movinglines/profiles.txt` | Per-campaign map defaults (region, projection, start lat/lon, UTC offset). |
| `movinglines/platform.txt` | Aircraft performance tables (speed vs. altitude, climb rate, turn radius). |
| `movinglines/WMS.txt` | WMS server URLs available in the map overlay menu. |
| `movinglines/sat.tle` | TLE orbital elements for all tracked satellites. |
| `movinglines/sat.json` | Geostationary satellite disk footprints (WKT + CRS). |
| `movinglines/labels.txt` | Named map points (airports, campaign sites) shown as labels. |
| `movinglines/image_corners.json` | Corner coordinates for referenced background images. |

Flight-pattern macros live in `movinglines/flt_module/*.flt`. Each `.flt` file is a plain-text waypoint-offset recipe that the GUI can apply at a clicked location.

---

## Coding Style

### File and class headers

Every module and every class opens with a large block docstring structured as:

```python
"""
    Purpose:
        <what this module/class does>
    Inputs:
        <parameter names with units in [brackets]>
    Outputs:
        <return values or side effects>
    Dependencies:
        <external packages>
    Required files:
        <data files needed at runtime>
    Example:
        ...
    Modification History:
        Written: Samuel LeBlanc, YYYY-MM-DD, <location>
        Modified: Samuel LeBlanc, vX.YY, YYYY-MM-DD, <location>
                - <change description>
"""
```

When adding new code, **append a `Modified:` entry** to the relevant class or module docstring with the current date and a short bullet list of changes. Do not alter existing history entries.

### Class and method naming

- Classes: generally PascalCase, but legacy names like `dict_position` and `Create_interaction` use mixed styles — match the existing name when extending.
- Methods and instance variables: `snake_case`.
- Short single-line method docstrings use a plain string (no `"""`, just `'...'`).

### Imports

Two patterns are used everywhere and should be preserved:

1. **Deferred imports inside `__init__` or methods** for heavy/optional packages (tkinter, xlwings, simplekml, gpxpy). This keeps the module importable even if a dependency is missing.

2. **Dual-mode import guard** for intra-package imports:
   ```python
   try:
       import map_interactive as mi
       from map_utils import spherical_dist
   except ModuleNotFoundError:
       from . import map_interactive as mi
       from .map_utils import spherical_dist
   ```
   This lets files run both as top-level scripts and as installed package modules.

3. **try/except around optional backends** (Basemap vs. Cartopy, Tkinter versions):
   ```python
   try:
       from mpl_toolkits.basemap import Basemap
   except:
       pass
   ```
   Bare `except:` clauses are common in the existing codebase for optional imports — acceptable to match this style, but prefer `except ImportError:` for new code.

### Units and physical quantities

Units are always noted in square brackets in docstrings and comments:
- `[degree]` for lat/lon
- `[m/s]` or `[kts]` for speed
- `[decimal hours]` for UTC times
- `[m]` or `[kft]` for altitude

Dual-unit instance variables are the norm: `self.speed` (m/s) is always paired with `self.speed_kts`; `self.alt` (m) with `self.alt_kft`; `self.dist` (km) with `self.dist_nm`.

### Error handling and verbosity

- A `self.verbose` flag is passed to most constructors. Guard debug output with `if self.verbose: print(...)`.
- Swallow errors with a `print()` rather than silently, especially around GUI and Excel calls where the user benefits from knowing something failed.
- Avoid adding `raise` or hard crashes in GUI event handlers — the application must stay alive.

### NumPy arrays

All position/time data (`self.lon`, `self.lat`, `self.alt`, `self.utc`, etc.) are NumPy arrays. Initialize with `np.array([value])` (a single-element array), then extend by concatenation or `np.append`. Do not use Python lists for these fields.

### Format strings

The codebase mixes `%`-style and `.format()` — use `.format()` for new code. f-strings are acceptable where Python 3.6+ is guaranteed (the package targets Python 3.9+).

### No type hints

The existing codebase has no type annotations. Do not add them unless the user explicitly requests it.

### Succinct code is prefferred

The codebase prefers a succinct coding style, with most functions calls on a single line. 

---

## Development Notes

- **xlwings requires a live Excel process** (Windows or macOS). On Linux or in tests without Excel, `xlwings_pyonly_backup.py` provides a fallback implementation of `dict_position`.
- **Cartopy replaced Basemap** in v1.21 (Oct 2021). Any `self.m.use_cartopy` guard in `map_interactive.py` exists to keep backward compatibility with pickled map objects; do not remove it.
- **PyInstaller hooks** in `movinglines/hooks/` are only relevant for building standalone `.exe`/`.app` bundles via `movinglines/ml.spec`. Do not modify them unless troubleshooting a build.
- **`pdb` artifacts**: a `import pdb; pdb.set_trace()` line exists inside a `try/except` block in `map_interactive.py:134`. This is a known leftover; remove it if you touch that block.
- The `EarthCARE/` directory and root-level `PREFIRE1_*.kml` files are **data, not code** — they are satellite track KML files consumed at runtime and are not part of any import chain.

---

## Running the Application

```bash
# After pip install -e .
ml

# Or directly
python -m movinglines
```

Pass `test=True` to `Create_interaction(test=True)` to keep the Python REPL usable alongside the GUI (uses `plt.ion()` instead of `plt.show()`).

---

## File Index

See [`general_index.md`](general_index.md) for a one- or two-line description of every file in the repository, organized by directory.
