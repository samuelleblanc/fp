"""
    Purpose:
        Provides the special_points class for managing non-flight-path annotations
        on the Moving Lines map. Annotations are stored in a dedicated 'Special_points'
        Excel tab in the same workbook as the flight plan.

        Three annotation types are supported:
          - drop_sonde : point snapped to the nearest aircraft track leg; leg timing
                         and distance are computed automatically.
          - free_form  : arbitrary lat/lon point not tied to any aircraft path.
          - polygon    : series of vertices (same label) that are drawn as a closed
                         outline on the map.

    Inputs:
        wb        : xlwings Book object (dict_position.wb)
        ax        : matplotlib Axes object (LineBuilder.line.axes)
        ex_arr    : list of dict_position instances (all active flight tabs)
        m         : map wrapper object with invert_lonlat() and convert_latlon()
        verbose   : [bool] enable debug printing

    Outputs:
        Excel 'Special_points' sheet with columns:
          Label, Type, Lat[deg], Lon[deg], Aircraft_tab,
          CumLegT[hh:mm], LegT[hh:mm], LegDist[km]
        Matplotlib artists drawn on the map axes.

    Dependencies:
        numpy, xlwings, matplotlib

    Required files:
        None beyond what the host application already loads.

    Example:
        sp = special_points(wb=wb.wb, ax=lines.line.axes, ex_arr=[wb], m=m)
        sp.add_point(lat=35.0, lon=-120.0, label='DS01',
                     sp_type='drop_sonde', aircraft_tab='P3 Flight path')
        sp.draw()

    Modification History:
        Written: Samuel LeBlanc, 2026-08-24, Santa Cruz, CA
"""

import numpy as np


class special_points:
    """
    Purpose:
        Manages special-point annotations (drop sondes, free-form points, polygon
        outlines) that are displayed on the Moving Lines map and saved to a dedicated
        Excel tab.  Does NOT create a new aircraft flight path when loaded.

    Inputs:
        wb       : xlwings Book
        ax       : matplotlib Axes
        ex_arr   : list of dict_position instances
        m        : map wrapper (invert_lonlat, convert_latlon)
        verbose  : bool

    Outputs:
        'Special_points' Excel sheet; matplotlib marker/label artists on ax.

    Dependencies:
        numpy, xlwings, matplotlib

    Modification History:
        Written: Samuel LeBlanc, 2026-08-24, Santa Cruz, CA
    """

    SHEET_NAME = 'Special_points'
    TYPES      = ['drop_sonde', 'free_form', 'polygon']
    HEADERS    = ['Label', 'Type', 'Lat[deg]', 'Lon[deg]', 'Aircraft_tab',
                  'CumLegT[hh:mm]', 'LegT[hh:mm]', 'LegDist[km]']
    COLORS     = {'drop_sonde': 'cyan',    'free_form': 'magenta', 'polygon': 'yellow'}
    MARKERS    = {'drop_sonde': 'v',       'free_form': '*',        'polygon': 'D'}

    def __init__(self, wb=None, ax=None, ex_arr=None, m=None, verbose=False):
        self.wb      = wb
        self.ax      = ax
        self.ex_arr  = ex_arr or []
        self.m       = m
        self.verbose = verbose

        self.lat         = np.array([])
        self.lon         = np.array([])
        self.cumlegt     = np.array([])   # [decimal hours]
        self.legt        = np.array([])   # [decimal hours]
        self.legdist     = np.array([])   # [km]
        self.label       = []
        self.sp_type     = []
        self.aircraft_tab = []

        self.drawn_markers = []   # one Line2D per lat/lon point (parallel to lat/lon arrays)
        self.drawn_labels  = []   # one Annotation per lat/lon point
        self.drawn_polys   = []   # polygon Patch objects (one per polygon group)

        if wb is not None:
            self.Create_excel_sheet()

    # ------------------------------------------------------------------
    # Excel helpers
    # ------------------------------------------------------------------

    def Create_excel_sheet(self):
        'Create or open the Special_points sheet, ensure it is the last tab, then reactivate the flight path sheet'
        try:
            self.sh = self.wb.sheets[self.SHEET_NAME]
            self.load_from_excel()
        except Exception:
            self.sh = self.wb.sheets.add(self.SHEET_NAME, after=self.wb.sheets[-1])
            self.sh.range('A1').value = self.HEADERS
        # Move to last position if it is not already there
        if self.wb.sheets[-1].name != self.SHEET_NAME:
            try:
                self.sh.api.Move(After=self.wb.sheets[-1].api)
            except Exception:
                pass
        # Reactivate the first flight path sheet so the user sees the flight plan
        if self.ex_arr:
            try:
                self.wb.sheets[self.ex_arr[0].name].activate()
            except Exception:
                pass

    def write_to_excel(self):
        'Write all special point rows to the Excel sheet'
        if not hasattr(self, 'sh'):
            return
        self.sh.range('A2:H1000').clear_contents()
        if len(self.lat) == 0:
            return
        data = []
        for i in range(len(self.lat)):
            data.append([
                self.label[i],
                self.sp_type[i],
                float(self.lat[i]),
                float(self.lon[i]),
                self.aircraft_tab[i],
                self._decimal_to_hhmm(float(self.cumlegt[i])),
                self._decimal_to_hhmm(float(self.legt[i])),
                float(self.legdist[i]),
            ])
        self.sh.range('A2').value = data

    def load_from_excel(self):
        'Populate data arrays from existing Special_points sheet rows'
        if not hasattr(self, 'sh'):
            return
        try:
            data = self.sh.range('A2').expand('table').value
        except Exception:
            return
        if data is None:
            return
        if not isinstance(data[0], list):
            data = [data]
        for row in data:
            if not row or not row[0]:
                continue
            self.label.append(str(row[0]))
            self.sp_type.append(str(row[1]) if row[1] else 'free_form')
            self.lat      = np.append(self.lat,     float(row[2]) if row[2] is not None else 0.0)
            self.lon      = np.append(self.lon,     float(row[3]) if row[3] is not None else 0.0)
            self.aircraft_tab.append(str(row[4]) if row[4] else '')
            self.cumlegt  = np.append(self.cumlegt, self._hhmm_to_decimal(row[5]) if row[5] else 0.0)
            self.legt     = np.append(self.legt,    self._hhmm_to_decimal(row[6]) if row[6] else 0.0)
            self.legdist  = np.append(self.legdist, float(row[7]) if row[7] is not None else 0.0)

    def _decimal_to_hhmm(self, t):
        'Convert decimal hours [decimal hours] to hh:mm string'
        t = max(0.0, float(t))
        h = int(t)
        m = int(round((t - h) * 60))
        if m == 60:
            h += 1; m = 0
        return '{:02d}:{:02d}'.format(h, m)

    def _hhmm_to_decimal(self, s):
        'Convert hh:mm string to decimal hours [decimal hours]'
        try:
            parts = str(s).split(':')
            return float(parts[0]) + float(parts[1]) / 60.0
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Data manipulation
    # ------------------------------------------------------------------

    def add_point(self, lat, lon, label=' ', sp_type='drop_sonde', aircraft_tab=''):
        'Append a new special point; computes leg info for drop_sonde type'
        self.lat      = np.append(self.lat, float(lat))
        self.lon      = np.append(self.lon, float(lon))
        self.label.append(str(label))
        self.sp_type.append(str(sp_type))
        self.aircraft_tab.append(str(aircraft_tab))

        cumlegt, legt, legdist = 0.0, 0.0, 0.0
        if sp_type == 'drop_sonde' and aircraft_tab:
            ex = self._find_ex(aircraft_tab)
            if ex is not None:
                try:
                    cumlegt, legt, legdist = self.calc_leg_info(float(lat), float(lon), ex)
                except Exception as e:
                    if self.verbose:
                        print('calc_leg_info failed: {}'.format(e))

        self.cumlegt  = np.append(self.cumlegt, cumlegt)
        self.legt     = np.append(self.legt,    legt)
        self.legdist  = np.append(self.legdist, legdist)
        self.write_to_excel()

    def del_point(self, i):
        'Delete the special point at index i'
        self.lat      = np.delete(self.lat,     i)
        self.lon      = np.delete(self.lon,     i)
        self.cumlegt  = np.delete(self.cumlegt, i)
        self.legt     = np.delete(self.legt,    i)
        self.legdist  = np.delete(self.legdist, i)
        self.label.pop(i)
        self.sp_type.pop(i)
        self.aircraft_tab.pop(i)
        self.write_to_excel()

    def _find_ex(self, aircraft_tab):
        'Return the dict_position matching aircraft_tab name, or first available'
        for ex in self.ex_arr:
            if getattr(ex, 'name', '') == aircraft_tab:
                return ex
        return self.ex_arr[0] if self.ex_arr else None

    # ------------------------------------------------------------------
    # Leg-info calculation
    # ------------------------------------------------------------------

    def calc_leg_info(self, lat_s, lon_s, ex):
        """
        Snap point (lat_s, lon_s) to the nearest track segment of ex and return
        (cumlegt [decimal hours], legt [decimal hours], legdist [km]).

        The nearest segment is found by projecting onto each (A→B) segment in
        map-projected (x,y) space, then interpolating the track timing linearly.
        """
        try:
            from map_utils import spherical_dist
        except ModuleNotFoundError:
            from .map_utils import spherical_dist

        n = len(ex.lat)
        if n < 2:
            return 0.0, 0.0, 0.0

        if self.m is not None:
            xs, ys = self.m.invert_lonlat(ex.lon, ex.lat)
            xp_arr, yp_arr = self.m.invert_lonlat(np.array([lon_s]), np.array([lat_s]))
            xp, yp = float(xp_arr[0]), float(yp_arr[0])
        else:
            xs, ys = np.array(ex.lon), np.array(ex.lat)
            xp, yp = float(lon_s), float(lat_s)

        best_dist2 = np.inf
        best_i     = 0
        best_t     = 0.0

        for i in range(n - 1):
            ax_, ay_ = float(xs[i]), float(ys[i])
            bx,  by  = float(xs[i + 1]), float(ys[i + 1])
            dx,  dy  = bx - ax_, by - ay_
            seg2 = dx * dx + dy * dy
            t = 0.0 if seg2 < 1e-20 else max(0.0, min(1.0, ((xp - ax_) * dx + (yp - ay_) * dy) / seg2))
            px = ax_ + t * dx
            py = ay_ + t * dy
            d2 = (xp - px) ** 2 + (yp - py) ** 2
            if d2 < best_dist2:
                best_dist2 = d2
                best_i     = i
                best_t     = t

        i = best_i
        t = best_t
        cumlegt = float(ex.cumlegt[i]) + t * (float(ex.cumlegt[i + 1]) - float(ex.cumlegt[i]))
        legt    = t * (float(ex.cumlegt[i + 1]) - float(ex.cumlegt[i]))
        legdist = float(spherical_dist([ex.lat[i], ex.lon[i]], [lat_s, lon_s]))
        return cumlegt, legt, legdist

    # ------------------------------------------------------------------
    # Map drawing
    # ------------------------------------------------------------------

    def draw(self):
        'Draw all special points on the map axes'
        self.clear()
        if self.ax is None or len(self.lat) == 0:
            return

        if self.m is not None:
            xs, ys = self.m.invert_lonlat(self.lon, self.lat)
        else:
            xs, ys = self.lon, self.lat

        for i in range(len(self.lat)):
            sp_type = self.sp_type[i]
            color   = self.COLORS.get(sp_type, 'white')
            marker  = self.MARKERS.get(sp_type, 'o')
            pt, = self.ax.plot(float(xs[i]), float(ys[i]),
                               marker=marker, color=color, ms=8,
                               zorder=50, ls='none',
                               markeredgecolor='k', markeredgewidth=0.5)
            lbl = self.ax.annotate(self.label[i],
                                   (float(xs[i]), float(ys[i])),
                                   fontsize=7, color=color, zorder=51,
                                   xytext=(4, 4), textcoords='offset points')
            self.drawn_markers.append(pt)
            self.drawn_labels.append(lbl)

        # Draw shaded polygon fills grouped by label (≥3 vertices)
        polygon_groups = {}
        for i, (sp_type, lbl_) in enumerate(zip(self.sp_type, self.label)):
            if sp_type == 'polygon':
                polygon_groups.setdefault(lbl_, []).append(i)

        try:
            from matplotlib.patches import Polygon as MPoly
        except ImportError:
            MPoly = None

        for lbl_, indices in polygon_groups.items():
            if len(indices) >= 3:
                px = [float(xs[j]) for j in indices]
                py = [float(ys[j]) for j in indices]
                if MPoly is not None:
                    verts = list(zip(px, py))
                    patch = MPoly(verts, closed=True, alpha=0.2,
                                  facecolor='yellow', edgecolor='yellow',
                                  linewidth=1.5, zorder=49)
                    self.ax.add_patch(patch)
                    self.drawn_polys.append(patch)
                else:
                    # Fallback: outline only
                    line, = self.ax.plot(px + [px[0]], py + [py[0]], '-',
                                         color='yellow', linewidth=1.5, zorder=49)
                    self.drawn_polys.append(line)

    def clear(self):
        'Remove all drawn special-point artists from the map axes'
        for obj in self.drawn_markers + self.drawn_labels + self.drawn_polys:
            try:
                obj.remove()
            except Exception:
                pass
        self.drawn_markers = []
        self.drawn_labels  = []
        self.drawn_polys   = []
