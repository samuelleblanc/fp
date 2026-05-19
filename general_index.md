# Codebase File Index

Generated index of all files in the Moving Lines flight planning repository.

---

## Root Directory

| File | Description |
|------|-------------|
| `README.md` | Main project documentation: installation, usage, feature history, and requirements for Moving Lines v1.65. |
| `setup.py` | Setuptools packaging script with metadata, entry points, and dependency declarations. |
| `requirements.txt` | Python package dependencies (numpy, cartopy, shapely, rasterio, xlwings, etc.). |
| `license.txt` | GPL-3.0 license text. |
| `labels.txt` | CSV of labeled geographic points displayed on the map. |
| `ArcticTable_Current.txt` | Geographic reference data table for Arctic region coordinates. |
| `opennav_waypoints_crawler.py` | Script for crawling and parsing waypoint data from OpenNav. |
| `orbit_predictor.py` | Script for predicting satellite orbital positions and overpasses. |
| `orbit_predictor.py.txt` | Text backup/draft of the orbit predictor script. |
| `get_iabp_buoys.sh` | Bash script to fetch International Arctic Buoy Programme (IABP) buoy data. |
| `conda-build_easy.sh` | Shell script wrapper to simplify conda package builds. |
| `.gitignore` | Git ignore rules for build artifacts, caches, and editor files. |
| `.gitattributes` | Git attribute rules for line endings and merge strategies. |
| `PREFIRE1_20251119.kml` | EO satellite (PREFIRE1) orbital track KML for 2025-11-19. |
| `PREFIRE1_20251120.kml` | EO satellite (PREFIRE1) orbital track KML for 2025-11-20. |
| `PREFIRE1_20251121.kml` | EO satellite (PREFIRE1) orbital track KML for 2025-11-21. |
| `PREFIRE1_20251122.kml` | EO satellite (PREFIRE1) orbital track KML for 2025-11-22. |
| `PREFIRE1_20251123.kml` | EO satellite (PREFIRE1) orbital track KML for 2025-11-23. |
| `PREFIRE1_20251124.kml` | EO satellite (PREFIRE1) orbital track KML for 2025-11-24. |
| `PREFIRE1_20251125.kml` | EO satellite (PREFIRE1) orbital track KML for 2025-11-25. |
| `PREFIRE1_20251126.kml` | EO satellite (PREFIRE1) orbital track KML for 2025-11-26. |
| `PREFIRE1_20251127.kml` | EO satellite (PREFIRE1) orbital track KML for 2025-11-27. |
| `PREFIRE1_20251128.kml` | EO satellite (PREFIRE1) orbital track KML for 2025-11-28. |

---

## `.github/workflows/`

| File | Description |
|------|-------------|
| `conda-build.yml` | GitHub Actions workflow for automated conda package building on push. |
| `pypi-publish.yml` | GitHub Actions workflow for automated PyPI package publishing on release. |

---

## `conda/`

| File | Description |
|------|-------------|
| `meta.yaml` | Conda recipe metadata: package name, version, build requirements, and run dependencies. |
| `conda_build_config.yaml` | Conda build matrix configuration for multi-platform (Linux, macOS, Windows) builds. |
| `post-link.sh` | Post-install script run by conda on Unix/macOS after package installation. |
| `post-link.bat` | Post-install script run by conda on Windows after package installation. |
| `.post-link.bat.swp` | Vim swap file (temporary editor artifact). |
| `movinglines-1.64-py39_1004.conda` | Pre-built binary conda package for Python 3.9 (v1.64). |

---

## `dist/`

| File | Description |
|------|-------------|
| `movinglines-1.48.tar.gz` | Source distribution archive for version 1.48. |
| `movinglines-1.60.tar.gz` | Source distribution archive for version 1.60. |

---

## `EarthCARE/`

Contains ~99 KML files named `EARTHCARE_YYYYMMDD.kml`, each holding the predicted ground track of the EarthCARE satellite for a single day covering 2025-12-10 through 2026-01-08. Used in Moving Lines to display EarthCARE overpasses on the interactive map.

---

## `flt_module/`

| File | Description |
|------|-------------|
| `IMPACTS_5-Point_Leg.flt` | Flight module macro defining a 5-point leg pattern for the IMPACTS campaign. |

---

## `movinglines.egg-info/`

Auto-generated egg-info directory produced by `pip install -e .`. Contains `PKG-INFO`, `SOURCES.txt`, `requires.txt`, `entry_points.txt`, `top_level.txt`, `dependency_links.txt`, `namespace_packages.txt`, and `not-zip-safe` — all standard packaging metadata and not manually edited.

---

## `movinglines/` — Main Package

### Core Application

| File | Description |
|------|-------------|
| `__init__.py` | Package init; defines the `ml` entry point and public API exports. |
| `ml.py` | Top-level `Create_interaction` class that wires together the GUI, interactive map, and Excel workbook into a running application. |
| `version.py` | Single-source version string (currently `1.65`). |

### GUI & Mapping

| File | Description |
|------|-------------|
| `gui.py` | Tkinter/matplotlib button handlers, dialogs, and file-save routines for the main toolbar. |
| `gui_plot.py` | Creates and manages the side-panel matplotlib figures (altitude, speed, fuel profiles). |
| `map_interactive.py` | Cartopy-backed interactive map: rendering, click-to-add-waypoint, and coordinate projection logic. |
| `map_tester.py` | Standalone script for manually testing map rendering without the full GUI. |
| `map_utils.py` | Geometry helpers: bearing, great-circle distance, coordinate conversion, and bounding-box utilities. |

### Excel Integration

| File | Description |
|------|-------------|
| `excel_interface.py` | xlwings-based Excel bridge: reads/writes waypoints, computes speed/altitude legs, and manages the flight-plan spreadsheet. |
| `xlwings_pyonly_backup.py` | Pure-Python fallback implementation of the Excel interface used when xlwings is unavailable. |

### Data I/O

| File | Description |
|------|-------------|
| `load_utils.py` | Parsers for reading flight plans from KML, GPX, Excel, ICT, and other formats into internal waypoint objects. |
| `write_utils.py` | Writers for exporting flight plans to ICT, KML, Excel, GPX, CSV, and docx formats. |

### Science / Data Modules

| File | Description |
|------|-------------|
| `aeronet.py` | Fetches and displays real-time AERONET aerosol optical depth (AOD) data on the map. |
| `buoys_utils.py` | Loads and plots IABP and similar drifting buoy positions. |
| `flightnav_utils.py` | Computes flight dynamics: turn radii, leg timing, fuel burn, and navigation parameters. |
| `nat_decode.py` | Parses North Atlantic Track (NAT) oceanic routing messages from Shanwick/Gander. |
| `nat_utils.py` | Higher-level helpers for working with NAT organised track system data. |
| `GFS_interp_utils.py` | Interpolates GFS weather model data to aircraft waypoints (winds, temperature). |
| `GFS_interp_utils_v2.py` | Revised version of GFS interpolation with improved accuracy and data handling. |
| `plot_canadian_airspace.py` | Renders Canadian airspace boundaries (Class F, FIRs) onto the Cartopy map. |
| `app_tester.py` | Integration test script that exercises the full application stack. |

### Configuration & Reference Data

| File | Description |
|------|-------------|
| `profiles.txt` | Dictionary of field-mission profiles mapping mission names to default map extents and settings. |
| `platform.txt` | Aircraft platform definitions: max altitude, speed tables, climb/descent rates, turning radii. |
| `WMS.txt` | List of WMS server URLs and layer names available for map overlays. |
| `MSS.txt` | MSS (Mission Support System) model server endpoints for meteorological data. |
| `vert_wms.txt` | WMS service entries for vertical cross-section (curtain) overlays. |
| `labels.txt` | Named geographic points (airports, campaign sites, etc.) shown as map labels. |
| `labels.bak.txt` | Backup of labels.txt. |
| `labels_old.txt` | Earlier version of the labels file. |
| `labels.txt.bak` | Additional backup of labels.txt. |
| `aeronet_locations.txt` | Current list of AERONET sun-photometer station coordinates and names. |
| `aeronet_locations_20230803.txt` | Snapshot of AERONET station list from 2023-08-03. |
| `aeronet_locations_full.txt` | Complete historical list of all AERONET sites. |
| `aeronet_locations.old.txt` | Older AERONET station list. |
| `ArcticTable_Current.txt` | Arctic geographic reference table for named locations. |
| `buoys.txt` | Current IABP drifting buoy position list. |
| `iwg_1319.txt` | NASA IWG-1 instrument data format specification (version 1319). |
| `iwg_1320.txt` | NASA IWG-1 instrument data format specification (version 1320). |
| `sat.tle` | Two-line element (TLE) sets for all tracked satellites. |
| `sat.json` | JSON definitions of geostationary satellite disk footprints (WKT polygons + CRS). |
| `EarthCARE.tle` | TLE orbital elements specific to the EarthCARE satellite. |
| `pace.tle` | TLE orbital elements specific to the NASA PACE satellite. |
| `image_corners.json` | Corner lat/lon coordinates and CRS for referenced background images. |
| `image_corners_tidbits.json` | Corner definitions for TropicalTidbits forecast images. |
| `GOES_EAST.wkt` | WKT polygon for the GOES-East satellite visible disk footprint. |
| `GOES_WEST.wkt` | WKT polygon for the GOES-West satellite visible disk footprint. |
| `GOES_EAST_crs.wkt` | Coordinate reference system (CRS) definition for GOES-East imagery projection. |
| `GOES_WEST_crs.wkt` | Coordinate reference system (CRS) definition for GOES-West imagery projection. |
| `file.rc` | Matplotlib RC settings file for consistent plot styling across the application. |

### GIS & Airspace Data

| File | Description |
|------|-------------|
| `elevation_10KMmd_GMTEDmd.tif` | GeoTIFF raster with 10 km resolution global elevation from GMTED dataset. |
| `canadian_airspace.air` | Binary data file containing Canadian domestic airspace boundary polygons. |
| `firs.kmz` | KMZ archive of global Flight Information Region (FIR) boundary polygons. |
| `Canadian_classF_Airspaces.kmz` | KMZ archive of Canadian Class F (restricted/danger) airspace areas. |
| `aeronet_sites.kmz` | KMZ archive of AERONET station locations for Google Earth viewing. |
| `map_KORUS.pkl` | Pickled Cartopy map extent/projection for the KORUS-AQ campaign region (Korea). |
| `map_NAAMES.pkl` | Pickled Cartopy map extent/projection for the NAAMES campaign region (North Atlantic). |
| `map_ORACLES.pkl` | Pickled Cartopy map extent/projection for the ORACLES campaign region (SE Atlantic). |

### Packaging & Build

| File | Description |
|------|-------------|
| `ml.spec` | PyInstaller spec file for building a self-contained Windows/macOS executable. |
| `pyinstall_ml.bat` | Windows batch script that invokes PyInstaller with the correct options. |
| `license.txt` | GPL-3.0 license (package-level copy). |
| `README.md` | Package-level README (mirrors the root README). |

### Graphics & Resources

| File | Description |
|------|-------------|
| `arc.ico` | Application window icon (Windows ICO format). |
| `icons.png` | Toolbar button icons in PNG format. |
| `icons.svg` | Toolbar button icons in SVG (source) format. |
| `MovingLines_QuickGuide.pdf` | One-page PDF quick-reference guide for end users. |

---

## `movinglines/flt_module/` — Flight Pattern Macros

Each `.flt` file defines a reusable flight-pattern macro (waypoint offsets, headings, and leg parameters). Paired `.png`/`.PNG` preview images show the pattern shape. Patterns include:

| Pattern | Description |
|---------|-------------|
| `along_track_heart_and_over_cloud.flt` | Combined along-track and overcloud sampling pattern. |
| `ARCSIX_Braster.flt` | B-raster scan for the ARCSIX Arctic campaign. |
| `ARCSIX_G3_bowling_alley.flt` | Gulfstream-3 straight-and-level "bowling alley" transect for ARCSIX. |
| `ARCSIX_P3_Bowling_alley.flt` | P-3 version of the ARCSIX bowling-alley transect. |
| `ARCSIX_P3_Helix.flt` | P-3 helical descent pattern for ARCSIX. |
| `bow_tie.flt` | Figure-8 / bow-tie crossing pattern. |
| `box_cw.flt` | Clockwise rectangular box pattern. |
| `circle_in_steps.flt` | Stepped circle with altitude changes at each sector. |
| `cloud_aerosol_wall.flt` | Vertical wall transect sampling both cloud and aerosol layers. |
| `Cloud_BB_sawtooth.flt` | Sawtooth altitude profile for cloud boundary-layer sampling. |
| `heating_rate_wall.flt` | Vertical wall pattern optimized for atmospheric heating-rate measurements. |
| `IMPACTS_5-Point_Leg.flt` | 5-waypoint leg for IMPACTS storm sampling. |
| `IMPACTS_lawnmower_ER2.flt` | ER-2 lawnmower grid for IMPACTS. |
| `IMPACTS_lawnmower_ER2_default.flt` | Default parameters version of the ER-2 lawnmower. |
| `IMPACTS_lawnmower_P3_stacked.flt` | Stacked P-3 lawnmower (time-variant and standard versions). |
| `IMPACTS_racetrack_ER2_5x.flt` | ER-2 racetrack with 5 loops for IMPACTS. |
| `IMPACTS_racetrack_P3_1loop.flt` | P-3 single-loop racetrack for IMPACTS. |
| `IMPACTS_racetrack_P3_stacked.flt` | P-3 stacked racetrack pattern for IMPACTS. |
| `lawnmower_4legs.flt` | Generic 4-leg lawnmower survey. |
| `lawnmower_5legs.flt` | Generic 5-leg lawnmower survey. |
| `NURTURE_fig4.flt` | Figure-4 shaped pattern from the NURTURE campaign. |
| `NURTURE_square.flt` | Square sampling pattern for NURTURE. |
| `Principal_plane_forward_back.flt` | Principal-plane radiometric sampling (forward and back passes). |
| `Principal_plane_split.flt` | Split principal-plane pattern. |
| `rosette.flt` | Multi-petal rosette sampling pattern. |
| `routine_flight_p3.flt` | Standard routine P-3 flight plan template. |
| `sequential_stepped.flt` | Sequential altitude-stepped transect. |
| `spiral_radiation_wall.flt` | Spiral combined with a radiation-profile wall. |
| `top_bottom.flt` | Above- and below-cloud sampling pair. |
| `top_bottom_cloud_sawtooth.flt` | Sawtooth pattern alternating top and bottom of cloud layer. |

---

## `movinglines/map_icons/`

| File | Description |
|------|-------------|
| `__init__.py` | Package init for map icons module. |
| `_readme_license.txt` | License and attribution for the icon artwork. |
| `number_0.png` … `number_100.png` | 101 numbered circular marker icons (0–100) used to label waypoints on the interactive map. |

---

## `movinglines/hooks/`

PyInstaller runtime hooks that ensure all required data files and hidden imports are bundled when building a standalone executable.

| File | Description |
|------|-------------|
| `__init__.py` | Package init. |
| `hook-datetime.py` | Ensures the `datetime` module is correctly bundled. |
| `hook-excel_interface.py` | Bundles hidden imports and data for `excel_interface`. |
| `hook-map_interactive.py` | Bundles Cartopy projection data and `map_interactive` dependencies. |
| `hook-rasterio.py` | Bundles GDAL/rasterio shared libraries and projection files. |
| `hook-scipy.integrate.py` | Bundles `scipy.integrate` and its Fortran extension modules. |

---

## `movinglines/mpl-data/`

Custom matplotlib data overrides used to replace the default toolbar icons with Moving Lines-specific icons.

| File | Description |
|------|-------------|
| `__init__.py` | Package init. |
| `ml_*.png`, `ml_*.gif`, `ml_*.ppm` | Custom toolbar icon replacements (home, back, forward, zoom, pan, save, etc.). |
| `ml_icons.tar.gz` | Archive of all custom Moving Lines icon files. |
| `matplotlib.svg` | SVG graphic resource used by matplotlib. |
