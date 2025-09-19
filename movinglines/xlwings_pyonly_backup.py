# excel_like.py — Tkinter + tksheet "xlwings-like" workbook with Freeze Panes
import re, math, datetime as dt
import tkinter as tk
from tkinter import ttk, font as tkfont
from typing import Any, Tuple, List, Optional, Union
import pandas as pd

try:
    import tksheet
except Exception as e:
    raise RuntimeError("Please install tksheet: pip install tksheet") from e

# --------------------- A1 helpers (cells, ranges, full cols/rows) ---------------------
_A1_CELL  = re.compile(r"^([A-Z]+)(\d+)$", re.I)
_A1_RANGE = re.compile(r"^([A-Z]+\d+):([A-Z]+\d+)$", re.I)
_A1_COL   = re.compile(r"^([A-Z]+):\1$", re.I)     # B:B
_A1_ROW   = re.compile(r"^(\d+):\1$", re.I)        # 2:2

def col_letters_to_index(letters: str) -> int:
    acc = 0
    for ch in letters.upper():
        acc = acc * 26 + (ord(ch) - 64)
    return acc - 1

def a1_to_rc(a1: str) -> Tuple[int, int]:
    m = _A1_CELL.match(a1)
    if not m: raise ValueError(f"Invalid A1: {a1}")
    col, row = m.groups()
    return int(row) - 1, col_letters_to_index(col)

def a1_to_fullcol(a1: str) -> Optional[int]:
    m = _A1_COL.match(a1)
    if m: return col_letters_to_index(m.group(1))
    return None

def a1_to_fullrow(a1: str) -> Optional[int]:
    m = _A1_ROW.match(a1)
    if m: return int(m.group(1)) - 1
    return None

def a1_range_to_slices(a1rng: str, nrows: int, ncols: int) -> Tuple[slice, slice]:
    a1rng = a1rng.upper()

    c = a1_to_fullcol(a1rng)
    if c is not None:
        return slice(0, nrows), slice(c, c + 1)

    r = a1_to_fullrow(a1rng)
    if r is not None:
        return slice(r, r + 1), slice(0, ncols)

    m = _A1_RANGE.match(a1rng)
    if not m:
        r, c = a1_to_rc(a1rng)
        return slice(r, r + 1), slice(c, c + 1)

    s, e = m.groups()
    r1, c1 = a1_to_rc(s); r2, c2 = a1_to_rc(e)
    if r2 < r1: r1, r2 = r2, r1
    if c2 < c1: c1, c2 = c2, c1
    return slice(r1, r2 + 1), slice(c1, c2 + 1)
    
def col_index_to_letters(idx0: int) -> str:
    """0-based column index -> Excel letters (0->A)."""
    s = ""
    n = idx0 + 1
    while n:
        n, rem = divmod(n - 1, 26)
        s = chr(65 + rem) + s
    return s


# --------------------- xw.constants shim (HAlign) ---------------------
class HAlign:
    xlHAlignLeft   = "left"
    xlHAlignCenter = "center"
    xlHAlignRight  = "right"

class _XWConstants:
    HAlign = HAlign

class _XWShim:
    constants = _XWConstants()

xw = _XWShim()

# --------------------- Sheets collection (supports 1-based) ---------------------
class Sheets:
    def __init__(self, book: "Book"):
        self._book = book
        self._order: List[str] = []

    def __len__(self): return len(self._order)

    def __iter__(self):
        for name in self._order:
            yield self._book._sheets_map[name]

    def __getitem__(self, key: Union[int, str]):
        if isinstance(key, str):
            return self._book._sheets_map[key]
        if isinstance(key, int):
            if 1 <= key <= len(self._order):   # 1-based
                idx = key - 1
            else:
                idx = key                       # allow 0-based & negatives
            name = self._order[idx]
            return self._book._sheets_map[name]
        raise TypeError("Sheets key must be int (index) or str (name).")

    __call__ = __getitem__

    @property
    def names(self) -> List[str]:
        return list(self._order)

    def add(self, name: str, nrows=200, ncols=50):
        return self._book.add(name, nrows=nrows, ncols=ncols)
        
    @property
    def active(self) -> "Sheet":
        """xlwings compatibility: return the active sheet object."""
        if self._book.active_sheet is None:
            if self._order:
                # pick the first tab and mark it active
                self._book.activate(self._order[0])
            else:
                # no sheets at all: create a default like Excel
                self._book.add("Sheet1")
        return self._book.active_sheet

    @active.setter
    def active(self, target):
        """
        Optional: allow setting the active sheet.
        Accepts a Sheet, sheet name (str), or index (int; 1-based or 0-based).
        """
        from typing import Union
        if isinstance(target, Sheet):
            self._book.activate(target.name)
        elif isinstance(target, str):
            self._book.activate(target)
        elif isinstance(target, int):
            self._book.activate(self[target].name)  # supports 1-based & 0-based
        else:
            raise TypeError("sheets.active must be set to a Sheet, name (str), or index (int)")

# --------------------- Range API proxy (.api.HorizontalAlignment) ---------------------
class _ApiProxy:
    def __init__(self, owner_range: "Range"):
        self._r = owner_range
        self._horizontal_alignment = None

    @property
    def HorizontalAlignment(self):
        return self._horizontal_alignment

    @HorizontalAlignment.setter
    def HorizontalAlignment(self, val):
        if val in (HAlign.xlHAlignLeft, HAlign.xlHAlignCenter, HAlign.xlHAlignRight, "left", "center", "right"):
            self._horizontal_alignment = (
                "center" if val in (HAlign.xlHAlignCenter, "center") else
                "left"   if val in (HAlign.xlHAlignLeft, "left") else
                "right"
            )
            self._r._apply_alignment(self._horizontal_alignment)
        else:
            raise ValueError("Unsupported HorizontalAlignment")
            
class _CellAddress:
    def __init__(self, row: int, col: int):
        self.row = row
        self.column = col

class _CellsProxy:
    def __init__(self, sheet: "Sheet"):
        self._sheet = sheet

    @property
    def last_cell(self) -> _CellAddress:
        # Excel's real last cell is 1,048,576 x 16,384, but for
        # Ctrl+Arrow patterns we can use the sheet's grid size.
        return _CellAddress(self._sheet.nrows, self._sheet.ncols)

# --------------------- Range Font proxy (.font) ---------------------
class _FontProxy:
    """Mimic xlwings Range.font with simple properties (bold, italic, underline, name, size, color)."""
    def __init__(self, rng: "Range"):
        self._r = rng

    def _apply(self, key: str, value):
        sh = self._r.sheet
        rs, cs = a1_range_to_slices(self._r.a1, sh.nrows, sh.ncols)
        for r in range(rs.start, rs.stop):
            for c in range(cs.start, cs.stop):
                sh._formats[(r, c)]["font"][key] = value
        sh._apply_fonts(rs, cs)
        sh._refresh_grid()

    # --- properties you can set like xlwings ---
    @property
    def bold(self):
        sh = self._r.sheet
        rs, cs = a1_range_to_slices(self._r.a1, sh.nrows, sh.ncols)
        if (rs.stop - rs.start == 1) and (cs.stop - cs.start == 1):
            return bool(sh._formats[(rs.start, cs.start)]["font"]["bold"])
        return None  # multi-cell: undefined
    @bold.setter
    def bold(self, v: bool): self._apply("bold", bool(v))

    @property
    def italic(self):
        sh = self._r.sheet
        rs, cs = a1_range_to_slices(self._r.a1, sh.nrows, sh.ncols)
        if (rs.stop - rs.start == 1) and (cs.stop - cs.start == 1):
            return bool(sh._formats[(rs.start, cs.start)]["font"]["italic"])
        return None
    @italic.setter
    def italic(self, v: bool): self._apply("italic", bool(v))

    @property
    def underline(self):
        sh = self._r.sheet
        rs, cs = a1_range_to_slices(self._r.a1, sh.nrows, sh.ncols)
        if (rs.stop - rs.start == 1) and (cs.stop - cs.start == 1):
            return bool(sh._formats[(rs.start, cs.start)]["font"]["underline"])
        return None
    @underline.setter
    def underline(self, v: bool): self._apply("underline", bool(v))

    @property
    def name(self):
        sh = self._r.sheet
        rs, cs = a1_range_to_slices(self._r.a1, sh.nrows, sh.ncols)
        if (rs.stop - rs.start == 1) and (cs.stop - cs.start == 1):
            return sh._formats[(rs.start, cs.start)]["font"]["name"]
        return None
    @name.setter
    def name(self, v: str): self._apply("name", str(v) if v else None)

    @property
    def size(self):
        sh = self._r.sheet
        rs, cs = a1_range_to_slices(self._r.a1, sh.nrows, sh.ncols)
        if (rs.stop - rs.start == 1) and (cs.stop - cs.start == 1):
            return sh._formats[(rs.start, cs.start)]["font"]["size"]
        return None
    @size.setter
    def size(self, v: int): self._apply("size", int(v) if v else None)

    @property
    def color(self):
        sh = self._r.sheet
        rs, cs = a1_range_to_slices(self._r.a1, sh.nrows, sh.ncols)
        if (rs.stop - rs.start == 1) and (cs.stop - cs.start == 1):
            return sh._formats[(rs.start, cs.start)]["font"]["color"]
        return None
    @color.setter
    def color(self, v: str):
        # Accept Tk/hex color strings like '#RRGGBB' or 'red'
        self._apply("color", v)


# --------------------- Range ---------------------
class Range:
    def __init__(self, sheet: "Sheet", a1: str):
        self.sheet = sheet
        self.a1 = a1
        self.api = _ApiProxy(self)
        self._font_proxy = _FontProxy(self)

    @property
    def value(self) -> Any:
        rs, cs = a1_range_to_slices(self.a1, self.sheet.nrows, self.sheet.ncols)
        block = self.sheet.df.iloc[rs, cs]
        return block.iat[0,0] if block.shape==(1,1) else block.values.tolist()

    @value.setter
    def value(self, val: Any):
        rs, cs = a1_range_to_slices(self.a1, self.sheet.nrows, self.sheet.ncols)
        sub = self.sheet.df.iloc[rs, cs]

        # --- NEW: auto-expand lists/arrays from a single-cell anchor ---
        import numpy as _np
        if sub.shape == (1, 1):
            r0, c0 = rs.start, cs.start

            # Normalize numpy -> python lists
            if isinstance(val, _np.ndarray):
                val = val.tolist()

            # 2D list: write as block starting at anchor
            if isinstance(val, list) and val and isinstance(val[0], list):
                h = len(val); w = len(val[0])
                for i in range(h):
                    for j in range(w):
                        self.sheet.df.iat[r0 + i, c0 + j] = val[i][j]
                self.sheet._refresh_grid()
                return

            # 1D list/tuple: write horizontally by default (Excel-ish)
            if isinstance(val, (list, tuple)):
                for j, x in enumerate(val):
                    self.sheet.df.iat[r0, c0 + j] = x
                self.sheet._refresh_grid()
                return

            # scalar fallback
            self.sheet.df.iat[r0, c0] = val
            self.sheet._refresh_grid()
            return
        # --- END NEW ---

        # Existing multi-cell code (validate shape and write)
        if not isinstance(val, list):
            raise ValueError(f"Assign a 2D list for {self.a1}")
        if val and not isinstance(val[0], list):
            val = [val]
        if len(val) != sub.shape[0] or any(len(r) != sub.shape[1] for r in val):
            raise ValueError(f"Shape mismatch assigning to {self.a1}: got "
                             f"{len(val)}x{len(val[0]) if val else 0}, expected {sub.shape}")
        for i, ri in enumerate(range(sub.index.start, sub.index.stop)):
            for j, cj in enumerate(range(sub.columns.start, sub.columns.stop)):
                self.sheet.df.iat[ri, cj] = val[i][j]
        self.sheet._refresh_grid()

        
    @property
    def font(self) -> _FontProxy:
        return self._font_proxy
        
    def clear_contents(self):
        rs, cs = a1_range_to_slices(self.a1, self.sheet.nrows, self.sheet.ncols)
        for r in range(rs.start, rs.stop):
            for c in range(cs.start, cs.stop):
                self.sheet.df.iat[r, c] = ""
        self.sheet._refresh_grid()

    @property
    def number_format(self) -> Optional[str]:
        return self.sheet._get_cell_property(self.a1, "number_format")

    @number_format.setter
    def number_format(self, fmt: str):
        rs, cs = a1_range_to_slices(self.a1, self.sheet.nrows, self.sheet.ncols)
        for r in range(rs.start, rs.stop):
            for c in range(cs.start, cs.stop):
                self.sheet._formats[(r, c)]["number_format"] = fmt
        self.sheet._refresh_grid()

    def autofit(self):
        rs, cs = a1_range_to_slices(self.a1, self.sheet.nrows, self.sheet.ncols)
        self.sheet._autofit_rows_cols(rs, cs)

    def _apply_alignment(self, align: str):
        rs, cs = a1_range_to_slices(self.a1, self.sheet.nrows, self.sheet.ncols)
        for r in range(rs.start, rs.stop):
            for c in range(cs.start, cs.stop):
                self.sheet._formats[(r, c)]["align"] = align
        self.sheet._apply_alignments(rs, cs)
        self.sheet._refresh_grid()
        
        
    def _is_empty(self, v) -> bool:
        import pandas as _pd
        return v == "" or (isinstance(v, float) and _pd.isna(v))

    @property
    def row(self) -> int:
        # 1-based top-left row of the range
        rs, _ = a1_range_to_slices(self.a1, self.sheet.nrows, self.sheet.ncols)
        return rs.start + 1

    @property
    def column(self) -> int:
        _, cs = a1_range_to_slices(self.a1, self.sheet.nrows, self.sheet.ncols)
        return cs.start + 1

    def end(self, direction: str) -> "Range":
        """
        Minimal Ctrl+Arrow behavior:
        - Starting at this range's top-left single cell.
        - 'up'   -> go to the nearest non-empty going up (or row 1)
        - 'down' -> nearest non-empty going down (or last row)
        - 'left'/'right' similar for columns.
        Empty start behaves like Excel: jumps to last non-empty before an empty run.
        """
        direction = direction.lower()
        rs, cs = a1_range_to_slices(self.a1, self.sheet.nrows, self.sheet.ncols)
        r = rs.start; c = cs.start
        df = self.sheet.df

        if direction == 'up':
            i = r
            # if start is empty, jump upward to first non-empty; else to first empty above then +1
            if self._is_empty(df.iat[i, c]):
                while i > 0 and self._is_empty(df.iat[i, c]): i -= 1
            else:
                while i > 0 and not self._is_empty(df.iat[i-1, c]): i -= 1
            i = max(i, 0)
            a1 = f"{col_index_to_letters(c)}{i+1}"
            return Range(self.sheet, a1)

        if direction == 'down':
            i = r
            nmax = self.sheet.nrows - 1
            if self._is_empty(df.iat[i, c]):
                while i < nmax and self._is_empty(df.iat[i, c]): i += 1
            else:
                while i < nmax and not self._is_empty(df.iat[i+1, c]): i += 1
            a1 = f"{col_index_to_letters(c)}{i+1}"
            return Range(self.sheet, a1)

        if direction == 'left':
            j = c
            if self._is_empty(df.iat[r, j]):
                while j > 0 and self._is_empty(df.iat[r, j]): j -= 1
            else:
                while j > 0 and not self._is_empty(df.iat[r, j-1]): j -= 1
            a1 = f"{col_index_to_letters(j)}{r+1}"
            return Range(self.sheet, a1)

        if direction == 'right':
            j = c
            nmax = self.sheet.ncols - 1
            if self._is_empty(df.iat[r, j]):
                while j < nmax and self._is_empty(df.iat[r, j]): j += 1
            else:
                while j < nmax and not self._is_empty(df.iat[r, j+1]): j += 1
            a1 = f"{col_index_to_letters(j)}{r+1}"
            return Range(self.sheet, a1)

        raise ValueError("direction must be one of: 'up','down','left','right'")


# --------------------- Sheet (now with freeze panes) ---------------------
class Sheet:
    def __init__(self, book: "Book", name: str, nrows: int = 200, ncols: int = 50):
        self.book = book
        self._name = name
        self.nrows, self.ncols = nrows, ncols
        self.df = pd.DataFrame([["" for _ in range(ncols)] for _ in range(nrows)])
        self._formats = {(r, c): {
                                "number_format": None,
                                "align": None,
                                "font": {"bold": False, "italic": False, "underline": False,
                                         "name": None, "size": None, "color": None}}
                            for r in range(nrows) for c in range(ncols)
                        }

        # layout frames for panes
        self.frame = tk.Frame(book._tabs)
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)

        self._pane_mode = "single"
        self._freeze_rows = 0
        self._freeze_cols = 0

        # single grid (default)
        self.grid = tksheet.Sheet(self.frame, data=self._render_data())
        self.grid.enable_bindings(("single_select", "row_select", "column_select",
                                   "drag_select", "edit_cell", "arrowkeys",
                                   "rc_delete_row", "rc_delete_column",
                                   "copy", "cut", "paste"))
        self.grid.grid(row=0, column=0, rowspan=2, columnspan=2, sticky="nsew")

        self.grid.extra_bindings([
            ("end_edit_cell", self._on_cell_edited_single),
            ("paste_end", self._on_paste_end_single)
        ])
        try:
            self.grid.extra_bindings([("cell_select", self._on_select_cell),
            ("end_edit_cell", self._on_cell_edited_single),
            ("paste_end", self._on_paste_end_single)])
        except Exception:
            try:
                self.grid.extra_bindings([("select_cell", self._on_select_cell),
            ("end_edit_cell", self._on_cell_edited_single),
            ("paste_end", self._on_paste_end_single)])
            except Exception:
                pass


        self._font = tkfont.nametofont("TkDefaultFont")        
        self.cells = _CellsProxy(self)

        # frozen panes widgets (created on demand)
        self._f_corner = None
        self._f_top = None
        self._f_left = None
        self._f_main = None
        self._sync_job = None
        
        self._default_font = tkfont.nametofont("TkDefaultFont")  # used by _tkfont_from_spec
        self._font_cache = {}  # (family, size, weight, slant, underline) -> tkfont.Font
        
        # add top panes
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        # --- toolbar (address + formula bar + hint) ---
        self.toolbar = tk.Frame(self.frame, bg="#fffbe6", padx=6, pady=4)
        self.toolbar.grid(row=0, column=0, sticky="ew")

        self.addr_var = tk.StringVar(value="A1")
        self.formula_var = tk.StringVar(value="")
        tk.Label(self.toolbar, text="Cell", bg="#fffbe6").pack(side="left")
        tk.Label(self.toolbar, textvariable=self.addr_var, width=6, relief="groove").pack(side="left", padx=(6,10))
        entry = tk.Entry(self.toolbar, textvariable=self.formula_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", self._on_formula_commit)

        tk.Label(self.toolbar, text="Double-click to edit • Ctrl+C/V/X to copy/paste/cut",
                 fg="#8a6d3b", bg="#fffbe6").pack(side="right")

        # --- body holds the grid(s) (single or frozen panes) ---
        self.body = tk.Frame(self.frame)
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        # default single grid goes in body[0,0]
        self.grid = tksheet.Sheet(self.body, data=self._render_data())
        self.grid.grid(row=0, column=0, sticky="nsew")
        
        self._bind_selection_events(self.grid)
        
        # add right click context menu
        self._install_context_menu(self.grid)        
        self._enable_editing_on(self.grid)
        
        # --- toolbar (address + entry) ---
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        self.toolbar = tk.Frame(self.frame, bg="#fffbe6", padx=6, pady=4)
        self.toolbar.grid(row=0, column=0, sticky="ew")

        self.addr_var = tk.StringVar(value="A1")
        self.formula_var = tk.StringVar(value="")
        tk.Label(self.toolbar, text="Cell", bg="#fffbe6").pack(side="left")
        tk.Label(self.toolbar, textvariable=self.addr_var, width=8, relief="groove").pack(side="left", padx=(6,10))
        entry = tk.Entry(self.toolbar, textvariable=self.formula_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", self._on_formula_commit)

        hint = tk.Label(self.toolbar, text="Double-click to edit • Ctrl+C/V/X to copy/paste/cut",
                        fg="#8a6d3b", bg="#fffbe6")
        hint.pack(side="right")

        # Body area for grids
        self.body = tk.Frame(self.frame)
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        # Default grid goes in body
        self.grid = tksheet.Sheet(self.body, data=self._render_data())
        self.grid.grid(row=0, column=0, sticky="nsew")
        self._enable_editing_on(self.grid)

    # xlwings-y API
    def range(self, addr, addr2=None) -> "Range":
        # String A1 addressing (existing path)
        if isinstance(addr, str):
            if addr2 is None:
                return Range(self, addr)
            # two A1 strings -> "A1:B2"
            return Range(self, f"{addr}:{addr2}")

        # Tuple addressing: (row, col) 1-based
        if isinstance(addr, tuple) and len(addr) == 2:
            r1, c1 = int(addr[0]), int(addr[1])
            a1_1 = f"{col_index_to_letters(c1 - 1)}{r1}"
            if addr2 is None:
                return Range(self, a1_1)
            if isinstance(addr2, tuple) and len(addr2) == 2:
                r2, c2 = int(addr2[0]), int(addr2[1])
                a1_2 = f"{col_index_to_letters(c2 - 1)}{r2}"
                return Range(self, f"{a1_1}:{a1_2}")
            raise TypeError("range((r,c), (r2,c2)) expects two (row,col) tuples")
        raise TypeError("range expects A1 string or (row,col) tuple (optionally with a second tuple)")

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new: str):
        if new in self.book._sheets_map:
            raise ValueError(f"Sheet '{new}' already exists")
        old = self._name
        self.book._sheets_map[new] = self.book._sheets_map.pop(old)
        idx = self.book.sheets._order.index(old)
        self.book.sheets._order[idx] = new
        self._name = new
        self.book._tabs.tab(self.frame, text=new)

    def activate(self):
        self.book.activate(self.name)

    # Sheet-wide convenience
    def clear_contents(self):
        self.df.iloc[:, :] = ""
        self._refresh_grid()
    
    # copy paste handling
    def copy_selection(self):
        try: self.grid.event_generate("<Control-c>")
        except Exception: pass

    def cut_selection(self):
        try: self.grid.event_generate("<Control-x>")
        except Exception: pass

    def paste_clipboard(self):
        try: self.grid.event_generate("<Control-v>")
        except Exception: pass

    def clear_selection(self):
        try:
            cells = self.grid.get_selected_cells()
        except Exception:
            cells = []
        if not cells and hasattr(self, "_selected"):
            cells = [self._selected]
        for (r, c) in cells:
            if r is not None and c is not None:
                self.df.iat[r, c] = ""
        self._refresh_grid()

    
    # font handling
    def _tkfont_from_spec(self, spec: dict) -> tkfont.Font:
            # Ensure defaults exist
        if not hasattr(self, "_default_font"):
            try:
                self._default_font = tkfont.nametofont("TkDefaultFont")
            except Exception:
                self._default_font = tkfont.Font()  # fallback
        if not hasattr(self, "_font_cache"):
            self._font_cache = {}
        base = self._default_font.actual()
        family = spec.get("name") or base["family"]
        size   = spec.get("size") or base["size"]
        weight = "bold"  if spec.get("bold") else "normal"
        slant  = "italic" if spec.get("italic") else "roman"
        underline = 1 if spec.get("underline") else 0
        key = (family, int(size), weight, slant, int(underline))
        f = self._font_cache.get(key)
        if f is None:
            f = tkfont.Font(family=family, size=int(size), weight=weight, slant=slant, underline=underline)
            self._font_cache[key] = f
        return f

    def _get_cell_font(self, r: int, c: int) -> tkfont.Font:
        spec = self._formats[(r, c)]["font"]
        return self._tkfont_from_spec(spec)
        
    def _apply_fonts(self, rs: slice = None, cs: slice = None):
        """Best-effort: apply per-cell fonts/colors to the visible widget(s)."""
        rs = rs or slice(0, self.nrows)
        cs = cs or slice(0, self.ncols)

        def apply_to_widget(widget, row_map: List[int], col_map: List[int]):
            for i, rr in enumerate(row_map):
                for j, cc in enumerate(col_map):
                    spec = self._formats[(rr, cc)]["font"]
                    has_style = any([spec.get("bold"), spec.get("italic"), spec.get("underline"),
                                     spec.get("name"), spec.get("size"), spec.get("color")])
                    if not has_style:
                        continue
                    f = self._tkfont_from_spec(spec)
                    try:
                        # Newer tksheet builds may have a per-cell font API:
                        widget.cell_font(i, j, f)  # may raise on older versions
                    except Exception:
                        pass
                    if spec.get("color"):
                        try:
                            widget.highlight_cells(row=i, column=j, fg=spec["color"], redraw=False)
                        except Exception:
                            pass

        if getattr(self, "_pane_mode", "single") == "single":
            # single widget: index mapping is identity
            apply_to_widget(self.grid, list(range(rs.start, rs.stop)), list(range(cs.start, cs.stop)))
        else:
            # frozen: split areas and map to each sub-grid
            r0, c0 = self._freeze_rows, self._freeze_cols
            corner_rows = list(range(0, min(r0, rs.stop)))
            corner_cols = list(range(0, min(c0, cs.stop)))
            top_rows    = list(range(0, min(r0, rs.stop)))
            top_cols    = list(range(max(c0, cs.start), cs.stop))
            left_rows   = list(range(max(r0, rs.start), rs.stop))
            left_cols   = list(range(0, min(c0, cs.stop)))
            main_rows   = list(range(max(r0, rs.start), rs.stop))
            main_cols   = list(range(max(c0, cs.start), cs.stop))

            if self._f_corner: apply_to_widget(self._f_corner, corner_rows, corner_cols)
            if self._f_top:    apply_to_widget(self._f_top,    top_rows,    top_cols)
            if self._f_left:   apply_to_widget(self._f_left,   left_rows,   left_cols)
            if self._f_main:   apply_to_widget(self._f_main,   main_rows,   main_cols)



    def autofit(self, columns: bool = True, rows: bool = False):
        rs = slice(0, self.nrows)
        cs = slice(0, self.ncols)
        self._autofit_rows_cols(rs, cs, do_cols=columns, do_rows=rows)

    # ---------------- Freeze panes public API ----------------
    def freeze_panes(self, rows: int = 0, cols: int = 0):
        """Freeze the top 'rows' and left 'cols' like Excel Freeze Panes."""
        rows = max(0, int(rows)); cols = max(0, int(cols))
        if rows == 0 and cols == 0:
            self.unfreeze_panes()
            return
        self._freeze_rows, self._freeze_cols = rows, cols
        self._build_frozen_layout()

    def freeze_at(self, a1_cell: str):
        """Excel-like: freeze panes at cell (freeze rows above, columns left)."""
        r0, c0 = a1_to_rc(a1_cell)
        # a1_to_rc is 0-based; freezing 'above/left' of the cell is exactly r0, c0
        self.freeze_panes(rows=r0, cols=c0)

    def unfreeze_panes(self):
        self._freeze_rows = self._freeze_cols = 0
        if self._pane_mode == "frozen":
            self._destroy_frozen_layout()
        # back to single
        self._pane_mode = "single"
        self.grid.grid(row=0, column=0, sticky="nsew")
        self._refresh_grid()

    # ---------------- internal: build/destroy frozen layout ----------------
    def _build_frozen_layout(self):
        # destroy prior if any
        if self._pane_mode == "frozen":
            self._destroy_frozen_layout()

        self._pane_mode = "frozen"
        r, c = self._freeze_rows, self._freeze_cols

        # lay out 2x2 frames
        self.grid.grid_forget()
        corner_fr = tk.Frame(self.body);  top_fr = tk.Frame(self.body)
        left_fr   = tk.Frame(self.body);  main_fr = tk.Frame(self.body)
        corner_fr.grid(row=0, column=0, sticky="nsew")
        top_fr.grid(   row=0, column=1, sticky="nsew")
        left_fr.grid(  row=1, column=0, sticky="nsew")
        main_fr.grid(  row=1, column=1, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(1, weight=1)
        self.body.grid_columnconfigure(0, weight=0)
        self.body.grid_columnconfigure(1, weight=1)

        # create 4 sheets
        self._f_corner = tksheet.Sheet(corner_fr, data=[[""]])
        self._f_top    = tksheet.Sheet(top_fr,    data=[[""]])
        self._f_left   = tksheet.Sheet(left_fr,   data=[[""]])
        self._f_main   = tksheet.Sheet(main_fr,   data=[[""]])

        for w in (self._f_corner, self._f_top, self._f_left, self._f_main):
            w.enable_bindings(("single_select","edit_cell","arrowkeys","copy","cut","paste"))
            w.grid(sticky="nsew")
            self._enable_editing_on(w)
            self._bind_selection_events(w)
            self._install_context_menu(w)

        # bind edits to DF, mapping displayed->data indexes
        self._f_corner.extra_bindings([("end_edit_cell", lambda e: self._on_cell_edited_frozen(self._f_corner, e)),
                                       ("paste_end",     lambda e: self._on_paste_end_frozen(self._f_corner))])
        self._f_top.extra_bindings([   ("end_edit_cell", lambda e: self._on_cell_edited_frozen(self._f_top, e)),
                                       ("paste_end",     lambda e: self._on_paste_end_frozen(self._f_top))])
        self._f_left.extra_bindings([  ("end_edit_cell", lambda e: self._on_cell_edited_frozen(self._f_left, e)),
                                       ("paste_end",     lambda e: self._on_paste_end_frozen(self._f_left))])
        self._f_main.extra_bindings([  ("end_edit_cell", lambda e: self._on_cell_edited_frozen(self._f_main, e)),
                                       ("paste_end",     lambda e: self._on_paste_end_frozen(self._f_main))])

        # initial render
        self._refresh_grid()

        # start a tiny sync loop: keep top in sync with x-scroll; left with y-scroll
        self._start_sync_loop()

    def _destroy_frozen_layout(self):
        # stop any sync loop
        if getattr(self, "_sync_job", None):
            try: self._f_main.after_cancel(self._sync_job)
            except Exception: pass
            self._sync_job = None

        # destroy sub-sheets if present
        for ref in ("_f_corner","_f_top","_f_left","_f_main"):
            w = getattr(self, ref, None)
            if w is not None:
                try: w.destroy()
                except Exception: pass
                setattr(self, ref, None)

        # destroy frames we created for panes
        if hasattr(self, "_pane_frames"):
            for fr in self._pane_frames.values():
                try: fr.destroy()
                except Exception: pass
            self._pane_frames.clear()

        # reset the body grid to single-cell layout
        try:
            self.body.grid_rowconfigure(0, weight=1)
            self.body.grid_rowconfigure(1, weight=0)
            self.body.grid_columnconfigure(0, weight=1)
            self.body.grid_columnconfigure(1, weight=0)
        except Exception:
            pass


    # ---------------- internal: render ----------------
    def _render_cell(self, r: int, c: int) -> str:
        val = self.df.iat[r, c]
        fmt = self._formats[(r, c)]["number_format"]

        if fmt:
            if fmt.lower() in ("hh:mm", "h:mm"):
                if isinstance(val, (pd.Timestamp, dt.datetime)):
                    return val.strftime("%H:%M")
                if isinstance(val, dt.time):
                    return val.strftime("%H:%M")
                if isinstance(val, (int, float)) and not pd.isna(val):
                    hours = float(val)
                    h = int(math.floor(hours))
                    m = int(round((hours - h) * 60))
                    if m == 60: h, m = h+1, 0
                    return f"{h:02d}:{m:02d}"
            m = re.fullmatch(r"0(?:\.(0+))?", fmt)
            if m and isinstance(val, (int, float)) and not pd.isna(val):
                decs = 0 if m.group(1) is None else len(m.group(1))
                return f"{val:.{decs}f}"
            if "%" in fmt:
                try:
                    if isinstance(val, (pd.Timestamp, dt.datetime)):
                        return val.strftime(fmt)
                    if isinstance(val, dt.time):
                        return dt.datetime.combine(dt.date.today(), val).strftime(fmt)
                except Exception:
                    pass

        return "" if (isinstance(val, float) and pd.isna(val)) else str(val)

    def _render_data(self) -> List[List[str]]:
        return [[self._render_cell(r, c) for c in range(self.ncols)]
                for r in range(self.nrows)]

    def _refresh_grid(self):
        if self._pane_mode == "single":
            self.grid.set_sheet_data(self._render_data(), reset_highlights=False, redraw=True)
            self._apply_fonts()
            return

        # frozen mode: build 4 regions
        r, c = self._freeze_rows, self._freeze_cols
        # clamp
        r = max(0, min(r, self.nrows))
        c = max(0, min(c, self.ncols))
        # slices
        rows_top    = range(0, r)
        cols_left   = range(0, c)
        rows_main   = range(r, self.nrows)
        cols_main   = range(c, self.ncols)

        # helper to make 2D list from selections
        def data_of(rr: range, cc: range):
            return [[self._render_cell(i, j) for j in cc] for i in rr]

        self._f_corner.set_sheet_data(data_of(rows_top, cols_left),  reset_highlights=False, redraw=True)
        self._f_top.set_sheet_data(   data_of(rows_top, cols_main),  reset_highlights=False, redraw=True)
        self._f_left.set_sheet_data(  data_of(rows_main, cols_left), reset_highlights=False, redraw=True)
        self._f_main.set_sheet_data(  data_of(rows_main, cols_main), reset_highlights=False, redraw=True)

        # try to keep alignments roughly consistent (best-effort)
        # If your tksheet exposes column_align / cell_align these calls will work.
        try:
            # copy column widths & alignment between top and main for shared (main) columns
            for j, col in enumerate(cols_main):
                align = self._formats[(0 if r==0 else r-1, col)]["align"]
                if align:
                    self._f_top.column_align(j, align)
                    self._f_main.column_align(j, align)
            # copy row alignment between left and main for shared (main) rows
            for i, row in enumerate(rows_main):
                align = self._formats[(row, 0 if c==0 else c-1)]["align"]
                if align:
                    self._f_left.cell_align(i, 0, align)
                    self._f_main.cell_align(i, 0, align)
        except Exception:
            pass
            
        self._apply_fonts()

    # ---------------- internal: alignment / autofit ----------------
    def _apply_alignments(self, rs: slice, cs: slice):
        # single grid only (best-effort fallback for tksheet APIs)
        try:
            if self._pane_mode == "single":
                for c in range(cs.start, cs.stop):
                    aligns = {self._formats[(r, c)]["align"] for r in range(rs.start, rs.stop)}
                    aligns.discard(None)
                    if len(aligns) == 1:
                        self.grid.column_align(c, list(aligns)[0])
                    else:
                        for r in range(rs.start, rs.stop):
                            a = self._formats[(r, c)]["align"]
                            if a:
                                self.grid.cell_align(r, c, a)
        except Exception:
            pass

    def _autofit_rows_cols(self, rs: slice, cs: slice, do_cols=True, do_rows=False):
        pad_px = 16
        def fit_cols(grid_widget, col_indices: List[int]):
            for j, cidx in enumerate(col_indices):
                maxw = 40
                # scan ALL rows for that column in DF to decide width
                for r in range(self.nrows):
                    text = self._render_cell(r, cidx)
                    w = self._font.measure(text) + pad_px
                    if w > maxw: maxw = w
                try:
                    grid_widget.column_width(j, maxw)
                except Exception:
                    pass

        if self._pane_mode == "single":
            if do_cols:
                for c in range(cs.start, cs.stop):
                    maxw = 40
                    for r in range(rs.start, rs.stop):
                        text = self._render_cell(r, c)
                        w = self._font.measure(text) + pad_px
                        if w > maxw: maxw = w
                    try:
                        self.grid.column_width(c, maxw)
                    except Exception:
                        pass
            if do_rows:
                for r in range(rs.start, rs.stop):
                    maxh = self._font.metrics("linespace") + 8
                    try:
                        self.grid.row_height(r, maxh)
                    except Exception:
                        pass
        else:
            # top+main share columns >= freeze; left+corner share columns < freeze
            r, c = self._freeze_rows, self._freeze_cols
            if do_cols:
                if c < self.ncols:
                    fit_cols(self._f_top,  list(range(c, self.ncols)))
                    fit_cols(self._f_main, list(range(c, self.ncols)))
                if c > 0:
                    fit_cols(self._f_corner, list(range(0, c)))
                    fit_cols(self._f_left,   list(range(0, c)))
            # row heights: keep simple and uniform
            if do_rows:
                row_h = self._font.metrics("linespace") + 8
                try:
                    if r < self.nrows:
                        for i in range(self._f_main.get_total_rows()): self._f_main.row_height(i, row_h)
                        for i in range(self._f_left.get_total_rows()): self._f_left.row_height(i, row_h)
                    if r > 0:
                        for i in range(self._f_top.get_total_rows()): self._f_top.row_height(i, row_h)
                        for i in range(self._f_corner.get_total_rows()): self._f_corner.row_height(i, row_h)
                except Exception:
                    pass

    # ---------------- internal: event handlers ----------------
    def _on_cell_edited_single(self, event: dict):
        r, c = event["row"], event["column"]
        val = self.grid.get_cell_data(r, c)
        self.df.iat[r, c] = val
        self._refresh_grid()

    def _on_paste_end_single(self, event: dict):
        self.df.iloc[:, :] = self.grid.get_sheet_data(return_copy=True)
        self._refresh_grid()

    def _on_cell_edited_frozen(self, widget: "tksheet.Sheet", event: dict):
        r_local, c_local = event["row"], event["column"]
        # map local indices to data indices using displayed rows/cols
        try:
            rows_map = list(widget.displayed_rows)      # property in docs
            cols_map = list(widget.displayed_columns)   # property in docs
        except Exception:
            # fallback: infer by region & freeze counts
            rows_map, cols_map = self._infer_maps_for_widget(widget)
        rr = rows_map[r_local]; cc = cols_map[c_local]
        val = widget.get_cell_data(r_local, c_local)
        self.df.iat[rr, cc] = val
        self._refresh_grid()

    def _on_paste_end_frozen(self, widget: "tksheet.Sheet"):
        try:
            rows_map = list(widget.displayed_rows)
            cols_map = list(widget.displayed_columns)
        except Exception:
            rows_map, cols_map = self._infer_maps_for_widget(widget)
        data = widget.get_sheet_data(return_copy=True)
        for i, rr in enumerate(rows_map[:len(data)]):
            row = data[i]
            for j, cc in enumerate(cols_map[:len(row)]):
                self.df.iat[rr, cc] = row[j]
        self._refresh_grid()

    def _infer_maps_for_widget(self, widget):
        r, c = self._freeze_rows, self._freeze_cols
        if widget is self._f_corner:
            rows_map = list(range(0, r)); cols_map = list(range(0, c))
        elif widget is self._f_top:
            rows_map = list(range(0, r)); cols_map = list(range(c, self.ncols))
        elif widget is self._f_left:
            rows_map = list(range(r, self.nrows)); cols_map = list(range(0, c))
        else:  # main
            rows_map = list(range(r, self.nrows)); cols_map = list(range(c, self.ncols))
        return rows_map, cols_map
        
    def _bind_selection_events(self, w):
        def _on_select(event):
            r = event.get("row"); c = event.get("column")
            if r is None or c is None:
                # Best-effort fallbacks across versions
                try:
                    r, c = w.get_selected_cells()[0]
                except Exception:
                    try:
                        r = w.get_selected_rows()[0]; c = w.get_selected_columns()[0]
                    except Exception:
                        return
            self._update_formula_bar(r, c)
            self._highlight_focus_cell(r, c)

        try:
            w.extra_bindings([("cell_select", _on_select)])
        except Exception:
            try:
                w.extra_bindings([("select_cell", _on_select)])
            except Exception:
                # Final fallback: mouse up triggers a selection update
                w.bind("<ButtonRelease-1>", lambda e: (
                    _on_select({"row": getattr(w, "get_currently_selected", lambda: (0,0))[0] if callable(getattr(w, "get_currently_selected", None)) else 0,
                                "column": getattr(w, "get_currently_selected", lambda: (0,0))[1] if callable(getattr(w, "get_currently_selected", None)) else 0})
                ))


    # ---------------- internal: tiny scroll sync loop ----------------
    def _start_sync_loop(self):
        # Only needed in frozen mode. Keep top.xview == main.xview and left.yview == main.yview
        if self._pane_mode != "frozen" or self._f_main is None: return
        try:
            x0, _ = self._f_main.get_xview()
            y0, _ = self._f_main.get_yview()
            try:
                self._f_top.set_xview(x0)
            except Exception:
                pass
            try:
                self._f_left.set_yview(y0)
            except Exception:
                pass
        except Exception:
            pass
        # schedule again
        self._sync_job = self._f_main.after(50, self._start_sync_loop)

    # ---------------- internal: props ----------------
    def _get_cell_property(self, a1: str, key: str):
        rs, cs = a1_range_to_slices(a1, self.nrows, self.ncols)
        if rs.stop - rs.start == 1 and cs.stop - cs.start == 1:
            return self._formats[(rs.start, cs.start)][key]
        return None
        
    # ---------------- internal: link formula bar to cell -------------
    def _on_select_cell(self, event: dict):
        r = event.get("row"); c = event.get("column")
        if r is None or c is None:
            try:
                r, c = self.grid.get_selected_cells()[0]
            except Exception:
                return
        self._selected = (r, c)
        self.addr_var.set(f"{col_index_to_letters(c)}{r+1}")
        self.formula_var.set("" if pd.isna(self.df.iat[r, c]) else str(self.df.iat[r, c]))

    def _on_formula_commit(self, *_):
        if not hasattr(self, "_selected"): return
        r, c = self._selected
        self.df.iat[r, c] = self.formula_var.get()
        self._refresh_grid()
        
        
    def _enable_editing_on(self, w):
        # Try the universal switch first
        try:
            w.enable_bindings("all")
            return
        except Exception:
            pass
        # Fallback: enumerate the common editing bindings
        try:
            w.enable_bindings((
                "single_select","row_select","column_select","drag_select",
                "edit_cell","arrowkeys","rc_select",
                "rc_delete_row","rc_delete_column",
                "copy","cut","paste"
            ))
        except Exception:
            pass

    def _on_formula_commit(self, *_):
        if not hasattr(self, "_selected"):
            return
        r, c = self._selected
        self.df.iat[r, c] = self.formula_var.get()
        self._refresh_grid()

    def _update_formula_bar(self, r, c):
        self._selected = (r, c)
        self.addr_var.set(f"{col_index_to_letters(c)}{r+1}")
        val = self.df.iat[r, c]
        self.formula_var.set("" if (isinstance(val, float) and pd.isna(val)) else str(val))
        
        
    # ---------------- internal: ensure copy/paste -----------
    def _selection_rect(self):
        # Try to compute a rectangular selection (cells → rows/cols fallback)
        try:
            cells = sorted(self.grid.get_selected_cells())
            if cells:
                rows = sorted(set(r for r, _ in cells))
                cols = sorted(set(c for _, c in cells))
                return rows[0], rows[-1], cols[0], cols[-1]
        except Exception:
            pass
        try:
            rows = sorted(self.grid.get_selected_rows()); cols = sorted(self.grid.get_selected_columns())
            if rows and cols:
                return rows[0], rows[-1], cols[0], cols[-1]
        except Exception:
            pass
        # Fallback to single selected cell
        r, c = getattr(self, "_selected", (0, 0))
        return r, r, c, c

    def copy_selection(self):
        r0, r1, c0, c1 = self._selection_rect()
        lines = []
        for r in range(r0, r1 + 1):
            row = []
            for c in range(c0, c1 + 1):
                v = self.df.iat[r, c]
                row.append("" if (isinstance(v, float) and pd.isna(v)) else str(v))
            lines.append("\t".join(row))
        text = "\n".join(lines)
        try:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(text)
        except Exception:
            pass

    def cut_selection(self):
        self.copy_selection()
        self.clear_selection()

    def paste_clipboard(self):
        try:
            text = self.frame.clipboard_get()
        except Exception:
            return
        rows = [row.split("\t") for row in text.splitlines()]
        start_r, start_c = getattr(self, "_selected", (0, 0))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                r = start_r + i; c = start_c + j
                if r < self.nrows and c < self.ncols:
                    self.df.iat[r, c] = val
        self._refresh_grid()

    def clear_selection(self):
        r0, r1, c0, c1 = self._selection_rect()
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                self.df.iat[r, c] = ""
        self._refresh_grid()

    
    # ----------------- internal: focus cell -----------------
    def _highlight_focus_cell(self, r, c):
        # Clear previous highlight
        for w in (getattr(self, "_f_corner", None), getattr(self, "_f_top", None),
                  getattr(self, "_f_left", None), getattr(self, "_f_main", None), self.grid):
            if not w: continue
            try:
                w.dehighlight_all()
            except Exception:
                pass
        # Re-apply current highlight
        target_widgets = []
        if getattr(self, "_pane_mode", "single") == "single":
            target_widgets = [(self.grid, r, c)]
        else:
            # map DF coords to the right pane coords
            rr, cc = r, c
            if rr < self._freeze_rows and cc < self._freeze_cols and self._f_corner:
                target_widgets = [(self._f_corner, rr, cc)]
            elif rr < self._freeze_rows and cc >= self._freeze_cols and self._f_top:
                target_widgets = [(self._f_top, rr, cc - self._freeze_cols)]
            elif rr >= self._freeze_rows and cc < self._freeze_cols and self._f_left:
                target_widgets = [(self._f_left, rr - self._freeze_rows, cc)]
            elif self._f_main:
                target_widgets = [(self._f_main, rr - self._freeze_rows, cc - self._freeze_cols)]

        for w, rr, cc in target_widgets:
            try:
                w.highlight_cells(row=rr, column=cc, bg="#DBEAFE", fg=None, redraw=True)  # light blue
            except Exception:
                pass
                
    # ------------------ internal: right click menu --------------
    def _install_context_menu(self, w):
        # Build our simple, image-free menu once
        if not hasattr(self, "_ctx"):
            self._ctx = tk.Menu(self.frame, tearoff=0)
            self._ctx.add_command(label="Copy",  command=self.copy_selection)
            self._ctx.add_command(label="Cut",   command=self.cut_selection)
            self._ctx.add_command(label="Paste", command=self.paste_clipboard)
            self._ctx.add_separator()
            self._ctx.add_command(label="Clear", command=self.clear_selection)

        # Disable tksheet's built-in RC popup (avoids pyimage… errors)
        try:
            w.disable_bindings(("rc_select","rc_popup_menu",
                                "rc_delete_row","rc_delete_column",
                                "rc_insert_row","rc_insert_column"))
        except Exception:
            pass
        try: w.unbind("<Button-3>")
        except Exception: pass
        try: w.unbind("<Button-2>")
        except Exception: pass

        # Show our menu, and stop event propagation (“break”) so tksheet won't rc()
        def _show_ctx(ev):
            try: w.focus_set()
            except Exception: pass
            self._ctx.tk_popup(ev.x_root, ev.y_root)
            return "break"

        w.bind("<Button-3>", _show_ctx)   # Windows/Linux
        w.bind("<Button-2>", _show_ctx)   # macOS middle/right fallback



        


# --------------------- Book ---------------------
class Book:
    def __init__(self, *args, title: str = "Excel-like", path: Optional[str] = None):
        self._root = tk.Tk()
        self._root.title(title if path is None else f"{title} - {path}")
        self._tabs = ttk.Notebook(self._root)
        self._tabs.pack(fill="both", expand=True)

        self._sheets_map: dict[str, Sheet] = {}
        self.sheets = Sheets(self)
        self.active_sheet: Optional[Sheet] = None

        self._tabs.bind("<<NotebookTabChanged>>", self._on_tab_change)
        
        self._path: Optional[str] = path
        self._closed: bool = False


        if path:
            self._load_xlsx(path)
        else:
            # Excel/xlwings parity: ensure there is always an active sheet
            if not self.sheets._order:
                self.add("Sheet1")  # becomes active_sheet automatically
        #add menubar
        self._menubar = tk.Menu(self._root)
        edit_menu = tk.Menu(self._menubar, tearoff=0)
        edit_menu.add_command(label="Copy\tCtrl+C",  command=lambda: self.active_sheet and self.active_sheet.copy_selection())
        edit_menu.add_command(label="Cut\tCtrl+X",   command=lambda: self.active_sheet and self.active_sheet.cut_selection())
        edit_menu.add_command(label="Paste\tCtrl+V", command=lambda: self.active_sheet and self.active_sheet.paste_clipboard())
        edit_menu.add_separator()
        edit_menu.add_command(label="Clear\tDel",    command=lambda: self.active_sheet and self.active_sheet.clear_selection())
        self._menubar.add_cascade(label="Edit", menu=edit_menu)
        self._root.config(menu=self._menubar)


        def _call_active(self, fn):
            sh = self.active_sheet
            if sh and hasattr(sh, fn):
                getattr(sh, fn)()


    @property
    def sh(self) -> Optional[Sheet]:
        return self.active_sheet

    @sh.setter
    def sh(self, sheet_or_name: Union[Sheet, str]):
        if isinstance(sheet_or_name, Sheet):
            self.activate(sheet_or_name.name)
        elif isinstance(sheet_or_name, str):
            self.activate(sheet_or_name)
        else:
            raise TypeError("wb.sh must be a Sheet or a sheet name (str).")

    def add(self, name: str = "Sheet1", nrows=200, ncols=50) -> Sheet:
        if name in self._sheets_map:
            raise ValueError(f"Sheet '{name}' already exists")
        sht = Sheet(self, name, nrows, ncols)
        self._sheets_map[name] = sht
        self._tabs.add(sht.frame, text=name)
        if self.active_sheet is None:
            self.active_sheet = sht
        self.sheets._order.append(name)
        return sht

    def activate(self, name: str):
        if name not in self._sheets_map: raise KeyError(name)
        idx = self.sheets._order.index(name)
        self._tabs.select(idx)

    def _on_tab_change(self, _):
        idx = self._tabs.index(self._tabs.select())
        name = self.sheets._order[idx]
        self.active_sheet = self._sheets_map[name]

    def _load_xlsx(self, path: str):
        x = pd.ExcelFile(path)
        for sheet_name in x.sheet_names:
            df = x.parse(sheet_name, header=None)
            nrows = max(50, (df.shape[0] or 1) + 20)
            ncols = max(20, (df.shape[1] or 1) + 10)
            sht = self.add(sheet_name, nrows=nrows, ncols=ncols)
            for r in range(df.shape[0]):
                for c in range(df.shape[1]):
                    sht.df.iat[r, c] = df.iat[r, c]
            sht._refresh_grid()

    # ----- SAVE (path optional) -----
    def save(self, path: Optional[str] = None):
        if path is not None:
            self._path = path
        if not self._path:
            # choose a default if we’ve never had a path
            self._path = "workbook.xlsx"
        with pd.ExcelWriter(self._path, engine="openpyxl") as writer:
            for name in self.sheets._order:
                df = self._sheets_map[name].df.copy()

                def _last_nonempty_row(dfx):
                    for i in range(dfx.shape[0]-1, -1, -1):
                        if any(str(x) != "" for x in dfx.iloc[i]): return i
                    return -1
                def _last_nonempty_col(dfx):
                    for j in range(dfx.shape[1]-1, -1, -1):
                        if any(str(x) != "" for x in dfx.iloc[:, j]): return j
                    return -1

                lr = _last_nonempty_row(df)
                lc = _last_nonempty_col(df)
                trimmed = pd.DataFrame([[]]) if (lr == -1 or lc == -1) else df.iloc[:lr+1, :lc+1]
                trimmed.to_excel(writer, sheet_name=name, header=False, index=False)

    # ----- CLOSE / QUIT -----
    def close(self, save: bool = False, path: Optional[str] = None):
        """
        Close the workbook window. If save=True, save first (to 'path' if given).
        Safe to call multiple times.
        """
        if self._closed:
            return
        if save:
            self.save(path)

        def _do_close():
            try:
                self._tabs.destroy()
            except Exception:
                pass
            try:
                self._root.destroy()
            except Exception:
                pass
            self._closed = True
            self.active_sheet = None
            self._sheets_map.clear()
            self.sheets._order.clear()

        try:
            # if mainloop is running, schedule the close on the Tk event queue
            self._root.after(0, _do_close)
        except Exception:
            _do_close()

    # xlwings-style alias
    def quit(self, *args, **kwargs):
        return self.close(*args, **kwargs)

    def run(self):
        if not self._closed:
            self._root.geometry("1100x700")
            self._root.mainloop()

    # (optional) try to clean up if GC'ed
    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

# --------------------- Demo ---------------------
if __name__ == "__main__":
    wb = Book("Excel-like (Freeze Panes Demo)")
    sh = wb.add("Data", nrows=40, ncols=12)

    # Populate some data
    for i in range(1, 21):
        sh.df.iat[i, 0] = f"Item {i}"
        sh.df.iat[i, 1] = i
        sh.df.iat[i, 6] = 8.0 + i/12.0
    sh.range("B2:B21").number_format = "0"
    sh.range("G2:G21").number_format = "hh:mm"
    sh.autofit(columns=True)

    # Freeze first 2 rows and first 2 columns (like selecting C3 and Freeze Panes)
    sh.freeze_at("C3")
    # You can also:
    # sh.freeze_panes(rows=2, cols=2)
    # sh.unfreeze_panes()

    wb.run()
constants = xw.constants