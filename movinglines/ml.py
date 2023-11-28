"""
    Purpose:
        Main program set to create a flight planning software
        Is used as a basis of the interface between an excel spreadsheet
            and a clickable map
        It is to create flight lines saved to kml, txt, xls, and others.
    Inputs: 
        test: if set to true, then command line is still useable
    Outputs:
        lines: linebuilder class object
        ui: specil ui to hold the gui interface objects
    Dependencies:
        numpy
        Tkinter
        datetime
        map_utils
        excel_interface
        map_interactive
        gui
        Basemap
        PIL (through scipy.misc.imread)
        OWSLib
    Required files:
        labels.txt: file with labels of locations
        aeronet_locations.txt: file with location of aeronet sites
        arc.ico: icon for main window
    Example:
        ...
    Modification History:   
        Written: Samuel LeBlanc, 2015-08-07, Santa Cruz, CA
                Copyright 2015 Samuel LeBlanc
        Modified: Samuel LeBlanc, 2015-09-02, NASA Ames, Santa Cruz, CA
                - added new buttons
                - changed imports to be more specific and not import everything
        Modified: Samuel LeBlanc, 2015-09-10, NASA Ames, Santa Cruz, CA
                - added multi plane capabilities via radiobuttons in the gui interface
        Modified: Samuel LeBlanc, 2015-09-16, NASA Ames
                - added icon in main figure
                - added move points buttons
                - added basemap creation questions
                - added GEOS imagerys with WMS service
        Modified: Samuel LeBlanc, 2016-07-11, on plane at SJC->WFF, CA
                - added flt_module files, rotate points, sun's principal plane direction
                - added profiles, platform information, satellite tracks
                - fixed some bugs in loading excel
        Modified: Samuel LeBlanc, 2016-07-13, WFF, VA
                - added the aeronet AOD plotting
                - added remove plots on the same buttons as add
        Modified: Samuel LeBlanc, 2016-07-17, Santa Cruz, CA
                - fixed bug that spanning past the map looses any plotting.
        Modified: Samuel LeBlanc, 2016-07-22, Santa Cruz, CA
                - added new icons for the toolbar
                - added new function calls to have the toolbar direct the refreshing
                - added showing of figures on the flt_module
                - added plotting of legend with geos wms, and cursor animation
                - fixed legend disappear issue when showing satellite tracks and aeronet values
                - updated to save kmz also, with embedded icons and altitude displayed.
                - fixed bug in bearing calculations
        Modified: Samuel LeBlanc, 2016-07-28, NASA Ames, CA
                - modified code to load special use airspace from sua.faa.gov WMS server
                - modified some potential bugs when moving lines
                - fixed bug in WMS image handling, added hires command
                - added saving excel file for pilots
        Modified: Samuel LeBlanc, 2016-08-10, NASA Ames, CA
                - modified the point selection to be a listbox instead of check marks
                - added add point dialog to put points in between others
        Modified: Samuel LeBlanc, v1.09, 2016-09-09, Swakopmund, Namibia
                - Modified code to have the user select a profile.txt file and platform.txt, and sat.tle file if not found (for fixing mac)
                - added principal plane selection button.
        Modified: Samuel LeBlanc, v1.1, 2016-09-19, Santa Cruz, CA
                - modified to have the ict file creation not override itself
                - made that kml files don't repeat
                - draggable legend
                - better update when changing window size
        Modified: Samuel LeBlanc, v1.22, 2019-06-03, Santa Cruz, CA
                - Bug fixes for line picking and climb time calculations.
        MOdified: Samuel LeBlanc, v1.23, 2019-08-05, Bathurst, NB, Canada
                - added one line saving for pilots.
        Modified: Samuel LeBlanc, v1.25, 2021-04-08, Santa Cruz, CA
                - added buttons for quick adding the IMPACTS "tropicaltidbits.com" imagery
        Modified: Samuel LeBlanc, v1.28, 2021-11-08, Santa Cruz, CA  
                - bug fix for deletion points
        Modified: Samuel LeBlanc, v1.29, 2022-01-11, Santa Cruz, CA
                - bug fix for saving multiple excel sheets
                - adding scroll to zoom 
                - adding custom color to labels.txt points
        Modified: Samuel LeBlanc, v1.30, 2022-02-03, Santa Cruz, CA
                - bug fix to for_pilots excel spreadsheet
        Modified: Samuel LeBlanc, v1.40, 2023-05-30, Santa Cruz, CA
                - added new projections
                - added new variables to the profiles.txt format
        Modified: Samuel LeBlanc, v1.41, 2023-06-08, Santa Cruz, CA
                - added surface elevation to elevation plots
                - added plotting of select kml files
                - added FIR boundaries plotting.
                - added the AERONET v3 debugging and defaults
                - modified plotting of satellite tracks for esthetics
        Modified: Samuel LeBlanc, v1.42, 2023-07-20, Santa Cruz, CA 
                - added support for the MSWMS from MSS
                - added extra selections options for the WMS loading.
        Modified: Samuel LeBlanc, v1.43, 2023-07-27, Hampton, VA 
                - bugfix for Mac OS laoding of files, and pkl map files.
        Modified: Samuel LeBlanc, v1.44, 2023-08-04, Snta Cruz, CA 
                - Adding the loading and compatibility with setuptools for pip integration and reglar python modules
        Modified: Samuel LeBlanc, v1.45, 2023-08-10, Santa Cruz, CA
                - Debugging and change of folder systems for pip install
        Modified: Samuel LeBlanc, v1.46, 2023-08-15, Santa Cruz, CA
                - Debugging for MACos and newer matplotlibs
        Modified: Samuel LeBlanc, v1.47, 2023-11-03, Santa Cruz, CA 
                - adding simple version output from command line (used for testing on conda deployments)
        
                
                 
"""
try:
    import Tkinter as tk
except:
    import tkinter as tk
    import tkinter as Tkinter
from tkinter import ttk
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
except:
    #from matplotlib.backends.backend_tkagg import FigureCanvasTk as FigureCanvasTkAgg
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk as NavigationToolbar2TkAgg
from matplotlib.figure import Figure
#import numpy as np
#from mpl_toolkits.basemap import Basemap
import datetime
import dateutil
#import scipy, scipy.misc, scipy.special, scipy.integrate
try:
    import Tkinter, FixTk, PIL
except: 
    import PIL
import re #, copy
#import ephem

try:
    import urllib2, socket, _socket, _ssl, _elementtree
except:
    import urllib, socket, _socket, _ssl, _elementtree
import pykml, simplekml
import gpxpy, gpxpy.gpx

try:
    import map_utils as mu
    import excel_interface as ex
    import map_interactive as mi
    import gui
    import aeronet
except ModuleNotFoundError:
    from . import map_utils as mu
    from . import excel_interface as ex
    from . import map_interactive as mi
    from . import gui
    from . import aeronet

try:
    import tkSimpleDialog, tkFileDialog, tkMessageBox
except:
    import tkinter.simpledialog as tkSimpleDialog
    import tkinter.filedialog as tkFileDialog
    import tkinter.messagebox as tkMessageBox
#import owslib, owslib.wms, owslib.util
#from xlwings import Range, Sheet, Workbook
#import win32com, win32com.client
#import FileDialog
#import six, six.moves
import warnings

try:
    from version import __version__
except ModuleNotFoundError:
    from .version import __version__

import argparse

profile_filename = 'profiles.txt'
platform_filename = 'platform.txt'
icon_filename = 'arc.ico'

def Get_basemap_profile():
    'Program to load profile dict basemap values'
    defaults = Get_default_profile(profile_filename)
    select = gui.Select_profile(defaults)
    return select.profile

def read_prof_file(filename):
    """
    Program that reads a file with dict format and interprets it for use within the variable space here
    """
    profile = []
    f = open(filename,'r')
    dd = None
    for line in f:
        if line.strip().startswith('#'):
            continue
        if not dd:
            first = True
            dd = line
        else:
            first = False
        if ('{' in dd) & ('}' in dd):
            profile.append(eval(dd.strip()))
            dd = line.strip()
        else:
            if first: 
                dd = line.strip()
            else:
                dd = ''.join((dd.strip(),line.strip()))
    if len(dd)>0:
        profile.append(eval(dd.strip()))
    return profile
    
def Get_default_profile(filename):
    """
    Program to try and read a text file with the default profiles
    If unavailable use some hardcoded defaults
    """
    try:
        profile = read_prof_file(filename)
    except:
        profile = [{'Profile':'ORACLES','Campaign':'ORACLES','Plane_name':'P3',
                     'Start_lon':'14 38.717E','Start_lat':'22 58.783S',
                     'Lon_range':[-20,20],'Lat_range':[-30,10],
                     'UTC_start':7.0,'UTC_conversion':+2.0,
                     'start_alt':95.0,'proj':'PlateCarree'},
                    {'Profile':'NAAMES','Campaign':'NAAMES','Plane_name':'C130',
                     'Start_lon':'52 44.547W','Start_lat':'47 37.273N',
                     'Lon_range':[-55,-20],'Lat_range':[40,60],
                     'UTC_start':8.5,'UTC_conversion':-2.5,
                     'start_alt':110.0},
                    {'Profile':'KORUS-AQ','Campaign':'KORUS-AQ','Plane_name':'DC8',
                     'Start_lon':'126 47.663E','Start_lat':'37 33.489N',
                     'Lon_range':[120,135],'Lat_range':[20,40],
                     'UTC_start':8.5,'UTC_conversion':+9,
                     'start_alt':20.0},
                    {'Profile':'AJAX','Campaign':'AJAX','Plane_name':'Alpha-jet',
                     'Start_lon':'122 3.489W','Start_lat':'37 24.387N',
                     'Lon_range':[-125,-115],'Lat_range':[30,40],
                     'UTC_start':20.0,'UTC_conversion':+7,
                     'start_alt':95.0}]
    return profile


class window:
    def __init__(self, root):
        self.root = root
        self.root.wm_title('Moving Lines: Flight planning '+__version__)
        self.root.geometry('900x950')
        self.w = 900
        self.fig = Figure()
        #self.ax1 = self.fig.add_subplot(111)
        try:
            self.root.tk.call('wm','iconbitmap',ui.root._w,'-default',icon_filename)
        except:
            pass
        self.create_left_buttons()
        self.create_right_graph()    

    def create_right_graph(self):
        right_frame = ttk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)
        self.canvas = FigureCanvasTkAgg(self.fig,right_frame) 
        self.canvas.get_tk_widget().pack(in_=right_frame,side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.canvas.draw()
        self.tb = NavigationToolbar2TkAgg(self.canvas,right_frame)
        self.tb.pack(in_=right_frame,side=tk.BOTTOM)
        self.tb.update()
        self.canvas._tkcanvas.pack(in_=right_frame,side=tk.TOP,fill=tk.BOTH, expand=1)

    def create_left_buttons(self):
        left_frame = ttk.Frame(self.root)
        left_frame.pack(side=tk.LEFT,expand=False)
        side = tk.TOP
        h = 2
        w = 20
        label = ttk.Label(self.root,text='by Samuel LeBlanc\n NASA Ames')
        label.pack(in_=left_frame,side=tk.BOTTOM)
        self.left_frame = left_frame
        self.top = left_frame


def Create_gui(vertical=True):
    'Program to set up gui interaction with figure embedded'
    class ui:
        pass
    ui = ui
    ui.root = tk.Tk()
    ui.root.wm_title('Moving Lines: Flight planning '+__version__)
    ui.root.geometry('900x950')
    ui.w = 900
    try:
        ui.root.tk.call('wm','iconbitmap',ui.root._w,'-default',icon_filename)
    except:
        pass
    ui.top = tk.Frame(ui.root)
    ui.bot = tk.Frame(ui.root)
    if vertical:
        ui.top.pack(side=tk.LEFT,expand=False)
        ui.bot.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)
    else:
        ui.top.pack(side=tk.TOP,expand=False)
        ui.bot.pack(side=tk.BOTTOM,fill=tk.BOTH,expand=True)
    ui.fig = Figure()
    ui.ax1 = ui.fig.add_subplot(111)
    ui.canvas = FigureCanvasTkAgg(ui.fig,master=ui.bot)
    try:
        ui.canvas.show()
    except:
        ui.canvas.draw()
    ui.canvas.get_tk_widget().pack(in_=ui.bot,side=tk.BOTTOM,fill=tk.BOTH,expand=1)
    ui.tb = gui.custom_toolbar(ui.canvas,ui.root)
    ui.tb.pack(in_=ui.bot,side=tk.BOTTOM)
    ui.tb.update()
    ui.canvas._tkcanvas.pack(in_=ui.bot,side=tk.TOP,fill=tk.BOTH,expand=1)
    return ui
    
class VerticalScrolledFrame(ttk.Frame):
    def __init__(self, parent, *args, **kw):
        ttk.Frame.__init__(self, parent, *args, **kw)

        # Create a canvas object and a vertical scrollbar for scrolling it.
        vscrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL)
        vscrollbar.pack(fill=tk.Y, side=tk.RIGHT, expand=tk.FALSE)
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0, 
                                width = 200, height = 300,
                                yscrollcommand=vscrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)
        vscrollbar.config(command = self.canvas.yview)

        # Reset the view
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

        # Create a frame inside the canvas which will be scrolled with it.
        self.interior = ttk.Frame(self.canvas)
        self.interior.bind('<Configure>', self._configure_interior)
        self.canvas.bind('<Configure>', self._configure_canvas)
        self.interior_id = self.canvas.create_window(0, 0, window=self.interior, anchor=tk.NW)


    def _configure_interior(self, event):
        # Update the scrollbars to match the size of the inner frame.
        size = (self.interior.winfo_reqwidth(), self.interior.winfo_reqheight())
        self.canvas.config(scrollregion=(0, 0, size[0], size[1]))
        if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
            # Update the canvas's width to fit the inner frame.
            self.canvas.config(width = self.interior.winfo_reqwidth())
        
    def _configure_canvas(self, event):
        if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
            # Update the inner frame's width to fill the canvas.
            self.canvas.itemconfigure(self.interior_id, width=self.canvas.winfo_width())
        

def build_buttons(ui,lines,vertical=True):
    'Program to set up the buttons'
    try:
        import gui
    except ModuleNotFoundError:
        from . import gui
    import tkinter as tk
    from matplotlib.colors import cnames

    if vertical:
        side = tk.TOP
        h = 2
        w = 20
    else:
        side = tk.LEFT
        h = 20
        w = 2
    g = gui.gui(lines,root=ui.root,noplt=True)
    g.refresh_style = ttk.Style()
    g.refresh_style.configure('B1.TButton',background='chartreuse',foreground='green')
    g.refresh = ttk.Button(g.root,text='Refresh',
                          command=g.refresh,style='B1.TButton')
    g.refreshspeed = ttk.Button(g.root,text='Refresh without Speeds',
                          command=g.refresh_nospeed)
    g.bopenfile = ttk.Button(g.root,text='Open',
                            command=g.gui_open_xl)
    g.bsavexl = ttk.Button(g.root,text='Save',
                          command=g.gui_save_xl)
    g.bsavexl_pilot = ttk.Button(g.root,text='for pilot',
                          command=g.gui_save_xl_pilot)
    g.bsavetxt = ttk.Button(g.root,text='TXT',
                          command=g.gui_save_txt)
    g.bsaveas2kml = ttk.Button(g.root,text='SaveAs',
                              command=g.gui_saveas2kml)
    g.bsave2kml = ttk.Button(g.root,text='Update',
                            command=g.gui_save2kml)
    g.bsave2gpx = ttk.Button(g.root,text='GPX',
                            command=g.gui_save2gpx)
    g.bsave2ict = ttk.Button(g.root,text='ICT',
			    command=g.gui_save2ict)
    g.bsavepng = ttk.Button(g.root,text='map to PNG',
			    command=g.gui_savefig)    
    g.bsaveall_style = ttk.Style()
    g.bsaveall_style.configure('B2.TButton',background='lightskyblue',foreground='blue')
    g.bsaveall = ttk.Button(g.root,text='Save All',
			    command=g.gui_saveall,style='B2.TButton')
    g.refresh.pack(in_=ui.top,side=side,fill=tk.X,pady=0)
    g.refreshspeed.pack(in_=ui.top,side=side,fill=tk.X,pady=0)
    ttk.Label(g.root,text='File options').pack(in_=ui.top,side=side) 
    g.frame_xl = ttk.Frame(ui.top)
    g.frame_xl.pack(in_=ui.top,side=side,fill=tk.X,pady=2)
    ttk.Label(ui.top,text='Excel file:').pack(in_=g.frame_xl,side=tk.LEFT)
    g.bopenfile.pack(in_=g.frame_xl,side=tk.LEFT)
    g.bsavexl.pack(in_=g.frame_xl,side=tk.LEFT)
    g.bsavexl_pilot.pack(in_=g.frame_xl,side=tk.LEFT)
    g.frame_kml = tk.Frame(ui.top)
    g.frame_kml.pack(in_=ui.top,side=side,fill=tk.X,pady=2)
    tk.Label(ui.top,text='Kml file:').pack(in_=g.frame_kml,side=tk.LEFT)
    g.bsaveas2kml.pack(in_=g.frame_kml,side=tk.LEFT)
    g.bsave2kml.pack(in_=g.frame_kml,side=tk.LEFT)
    g.frame_save = ttk.Frame(ui.top)
    g.frame_save.pack(in_=ui.top,side=side,fill=tk.X,pady=2)
    ttk.Label(ui.top,text='Saving to:').pack(in_=g.frame_save,side=tk.LEFT)
    g.bsavetxt.pack(in_=g.frame_save,side=tk.RIGHT)
    g.bsave2gpx.pack(in_=g.frame_save,side=tk.RIGHT)
    g.bsave2ict.pack(in_=g.frame_save,side=tk.RIGHT)
    g.frame_save2 = ttk.Frame(ui.top)
    g.frame_save2.pack(in_=ui.top,side=side,fill=tk.X,pady=2)
    g.bsavepng.pack(in_=g.frame_save2,side=tk.RIGHT)
    g.bsaveall.pack(in_=g.frame_save2,side=tk.LEFT)         
    tk.Frame(g.root,height=h,width=w,bg='black',relief='sunken'
             ).pack(in_=ui.top,side=side,padx=8,pady=5)
    g.frame_plot = ttk.Frame(ui.top)
    g.frame_plot.pack(in_=ui.top,side=side,fill=tk.X,pady=2)
    ttk.Label(ui.top,text='Plots:').pack(in_=g.frame_plot,side=tk.LEFT)
    g.bplotlat = ttk.Button(g.root,text='Alt vs Lat',
                           command=g.gui_plotaltlat)
    g.bplotlat.pack(in_=g.frame_plot,side=tk.RIGHT)
    g.bplotalt = ttk.Button(g.root,text='Alt vs time',
                           command=g.gui_plotalttime)
    g.bplotalt.pack(in_=g.frame_plot,side=tk.RIGHT)
    g.bplotsza = ttk.Button(g.root,text='SZA',
                           command=g.gui_plotsza)
    g.bplotsza.pack(in_=g.frame_plot,side=tk.RIGHT)
    g.bplotaltmss = ttk.Button(g.root,text='MSS Profile',
                           command=g.gui_plotmss_profile)
    g.bplotaltmss.pack(in_=ui.top,side=side)
    tk.Frame(g.root,height=h,width=w,bg='black',relief='sunken'
             ).pack(in_=ui.top,side=side,padx=8,pady=5)
    g.frame_select = tk.Frame(g.root,relief=tk.SUNKEN,bg='white')
    g.frame_select.pack(in_=ui.top,side=side,fill=tk.BOTH)
    tk.Label(g.root,text='Flight paths:',bg='white').pack(in_=g.frame_select,side=side)
    g.newflight_off = False
    g.flightselect_arr = []
    g.flightselect_arr.append(tk.Radiobutton(g.root,text=lines.ex.name,
                                             fg=lines.ex.color,
                                             variable=g.iactive,value=0,
                                             indicatoron=0,
                                             command=g.gui_changeflight,
                                             state=tk.ACTIVE,bg='white'))
    g.flightselect_arr[0].pack(in_=g.frame_select,side=side,padx=4,pady=2,fill=tk.BOTH)
    g.flightselect_arr[0].select()
    g.iactive.set(0)
    g.newflightpath = ttk.Button(g.root,text='New flight path',
                                command = g.gui_newflight)
    g.newflightpath.pack(in_=ui.top,padx=5,pady=2)
    #g.removeflightpath = tk.Button(g.root,text='Remove flight path',
    #                               command = g.gui_removeflight)
    #g.removeflightpath.pack(in_=ui.top,padx=5,pady=5)
    tk.Frame(g.root,height=h,width=w,bg='black',relief='sunken'
             ).pack(in_=ui.top,side=side,padx=8,pady=5)
    g.frame_points = ttk.Frame(ui.top)
    g.frame_points.pack(in_=ui.top,side=side,fill=tk.X,pady=2)
    ttk.Label(ui.top,text='Points:').pack(in_=g.frame_points,side=tk.LEFT)
    g.addpoint = ttk.Button(g.root,text='Add',
                           command = g.gui_addpoint)
    g.addpoint.pack(in_=g.frame_points,padx=0,pady=0,side=tk.LEFT)
    g.movepoints = ttk.Button(g.root,text='Move',
                             command = g.gui_movepoints)
    g.movepoints.pack(in_=g.frame_points,padx=0,pady=0,side=tk.LEFT)
    g.rotpoints = ttk.Button(g.root,text='Rotate',
                             command = g.gui_rotatepoints)
    g.rotpoints.pack(in_=g.frame_points,padx=0,pady=0,side=tk.LEFT)
    g.add_flt_module = ttk.Button(g.root,text='Add flt module', command=g.gui_flt_module)
    g.add_flt_module.pack(in_=ui.top)
    tk.Frame(g.root,height=h,width=w,bg='black',relief='sunken'
             ).pack(in_=ui.top,side=side,padx=8,pady=5)
    side_bar = g.root
    side_bar2 = VerticalScrolledFrame(side_bar)
    side_bar2.pack(in_=ui.top,expand = True, fill = tk.BOTH)
    top_gui = side_bar2.interior
    #top_gui = ui.top
    #tk.Label(g.root,text='Extra info:').pack(in_=ui.top,side=side)
    
    g.baddsat = ttk.Button(side_bar,text='Satellite tracks',
                         command = g.dummy_func)
    #g.baddsat.pack(in_=top_gui)
    g.baddsat.grid(in_=top_gui,row=0,column=0,  sticky='w'+'e'+'n'+'s')
    g.baddsat.config(command=g.gui_addsat_tle)
    g.baddaeronet = ttk.Button(side_bar,text='current\nAERONET AOD',
                         command = g.dummy_func)
    #g.baddaeronet.pack(in_=top_gui)
    g.baddaeronet.grid(in_=top_gui,row=0,  column=1,  sticky='w'+'e'+'n'+'s')
    g.baddaeronet.config(command=g.gui_addaeronet)
    #g.baddgeos = tk.Button(g.root,text='Add GEOS Forecast',
    #                     command = g.gui_addgeos)
    #g.baddgeos.pack(in_=top_gui)

   # g.frame_airspace = ttk.Frame(top_gui)
   # g.frame_airspace.pack(in_=top_gui,side=side,fill=tk.X,pady=2)
    
    g.baddsua = ttk.Button(side_bar,text='Special Use Airspace',
                         command = g.gui_add_SUA_WMS)
    #g.baddsua.pack(in_=g.frame_airspace,padx=0,pady=0,side=tk.LEFT,anchor=tk.CENTER)
    g.baddsua.grid(in_=top_gui,row=1,column=0,  sticky='w'+'e'+'n'+'s')
    g.baddfir = ttk.Button(side_bar,text='FIR boundaries',
                         command = g.gui_add_FIR)
    #g.baddfir.pack(in_=g.frame_airspace,padx=0,pady=0,side=tk.LEFT,anchor=tk.CENTER)
    g.baddfir.grid(in_=top_gui,padx=0,pady=0,row=1,column=1,  sticky='w'+'e'+'n'+'s')
    #g.frame_wms = ttk.Frame(top_gui)
    #g.frame_wms.pack(in_=top_gui,side=side,fill=tk.X,pady=2)
    g.baddwms = ttk.Button(side_bar,text='WMS layer',
                         command = g.gui_add_any_WMS)
    #g.baddwms.pack(in_=g.frame_wms,side=tk.LEFT,anchor=tk.CENTER)
    g.baddwms.grid(in_=top_gui,padx=0,pady=0,row=2,column=0,  sticky='w'+'e'+'n'+'s')
    g.baddkml = ttk.Button(side_bar,text='KML/KMZ',
                         command = g.gui_add_kml)
    #g.baddkml.pack(in_=g.frame_wms,padx=0,pady=0,side=tk.LEFT,anchor=tk.CENTER)
    g.baddkml.grid(in_=top_gui,padx=0,pady=0,row=2,column=1,  sticky='w'+'e'+'n'+'s')
    
    g.baddmss = ttk.Button(side_bar,text='MSS models',
                         command = g.gui_add_MSS)
    g.baddmss.grid(in_=top_gui,padx=0,pady=0,row=3,column=0,columnspan=2,sticky='w'+'e'+'n'+'s')
    #tk.Frame(side_bar,height=h,width=w,bg='black',relief='sunken'
    #         ).pack(in_=top_gui,side=side,padx=8,pady=5)
    tk.Frame(side_bar,height=h,width=w,bg='black',relief='sunken'
             ).grid(in_=top_gui,padx=8,pady=5,row=4,column=0,columnspan=2,sticky=tk.W+tk.E)
    #ttk.Label(side_bar,text='from local images:').pack(in_=top_gui,side=tk.BOTTOM)
    #g.frame_boc = ttk.Frame(top_gui)
    #g.frame_boc.pack(in_=top_gui,side=side,fill=tk.X,pady=2)
    g.baddbocachica = ttk.Button(side_bar,text='Forecast\nfrom Bocachica',
                         command = g.gui_addbocachica)
    #g.baddbocachica.pack(in_=g.frame_boc,padx=0,pady=0,side=tk.LEFT,anchor=tk.CENTER)
    g.baddbocachica.grid(in_=top_gui,padx=0,pady=0,row=5,column=0,  sticky='w'+'e'+'n'+'s')
    g.baddtrajectory = ttk.Button(side_bar,text='trajectory\nImage',
                         command = g.gui_addtrajectory)
    #g.baddtrajectory.pack(in_=g.frame_boc,padx=0,pady=0,side=tk.LEFT,anchor=tk.CENTER)
    g.baddtrajectory.grid(in_=top_gui,padx=0,pady=0,row=5,column=1,  sticky='w'+'e'+'n'+'s')
    g.baddfigure = ttk.Button(side_bar,text='image',
                         command = g.gui_addfigure)
    #g.baddfigure.pack(in_=top_gui)
    g.baddfigure.grid(in_=top_gui,padx=0,pady=0,row=6,column=0,columnspan=2,  sticky='w'+'e'+'n'+'s')
    g.baddtidbit = ttk.Button(side_bar,text='Tropical tidbit',
                         command = g.gui_addtidbit)
    #g.baddtidbit.pack(in_=top_gui)
    g.baddtidbit.grid(in_=top_gui,padx=0,pady=0,row=7,column=0,columnspan=2,  sticky='w'+'e'+'n'+'s')
    
    
    #g.bipython = tk.Button(side_bar,text='open iPython',
    #                     command = IPython.start_ipython([],user_ns=locals()))
    #g.bipython.pack(in_=top_gui)

    #g.bpythoncmd = tk.Button(side_bar,text='Python command line',
    #                     command = g.gui_python)
    #g.bpythoncmd.pack(in_=top_gui)
    
    #g.label = tk.Label(side_bar,text='by Samuel LeBlanc\n NASA Ames')
    #g.label.pack(in_=top_gui)
    
    #tk.Frame(side_bar,height=h,width=w,bg='black',relief='sunken'
    #         ).pack(in_=top_gui,side=side,padx=8,pady=5)
    tk.Frame(side_bar,height=h,width=w,bg='black',relief='sunken'
             ).grid(in_=top_gui,padx=8,pady=5,row=8,column=0,columnspan=2,sticky=tk.W+tk.E)
    quit_style = ttk.Style()
    quit_style.configure('B3.TButton',background='lightcoral',foreground='darkred')
    ttk.Button(side_bar,text='Quit',command=g.stopandquit,style='B3.TButton'
              ).grid(in_=top_gui,padx=8,pady=5,row=8,column=0,columnspan=2,sticky=tk.W+tk.E)
    g.active_style = ttk.Style()
    g.active_style.configure('Ba.TButton',background='grey',foreground='black')
    g.pressed_style = ttk.Style()
    g.pressed_style.configure('Bp.TButton',background='darkgrey',foreground='darkgrey')
    g.bg = 'Ba.TButton'#g.baddsat.cget('bg')
    ui.g = g

def get_datestr(ui):
    import tkinter.simpledialog as tkSimpleDialog
    from datetime import datetime
    import re
    ui.datestr = tkSimpleDialog.askstring('Flight Date','Flight Date (yyyy-mm-dd):',initialvalue=datetime.utcnow().strftime('%Y-%m-%d'))
    if not ui.datestr:
        ui.datestr = datetime.utcnow().strftime('%Y-%m-%d')
    else:
        while not re.match('[0-9]{4}-[0-9]{2}-[0-9]{2}',ui.datestr):
            ui.datestr = tkSimpleDialog.askstring('Flight Date',
                                                  'Bad format, please retry!\nFlight Date (yyyy-mm-dd):')
            if not ui.datestr:
                ui.datestr = datetime.utcnow().strftime('%Y-%m-%d')
    ui.ax1.set_title(ui.datestr)

def savetmp(ui,wb):
    import tempfile, os
    tmpfilename = os.path.join(tempfile.gettempdir(),ui.datestr+'.xlsx')
    try:
        wb.save2xl(tmpfilename)
    except:
        print('unable to save excel to temp file:'+tmpfilename)
        print('continuing ...')

def init_plot(m,start_lon='14 38.717E',start_lat='22 58.783S',color='red'):
    lat0,lon0 = mi.pll(start_lat), mi.pll(start_lon)
    x0,y0 = m.invert_lonlat(lon0,lat0) #m(lon0,lat0)
    line, = m.plot([x0],[y0],'o-',color=color,linewidth=3)
    line.labels_points = []
    text = ('Press s to stop interaction\\n'
            'Press i to restart interaction\\n')
    return line

def stopandquit():
    'simple function to handle the stop and quit'
    lines.ex.wb.save()
    lines.ex.wb.close()
    ui.root.quit()
    ui.root.destroy()
    
def goto_cwd():
    'Program that changes the current directory to the path of the script: for use in finding extra files'
    from os.path import dirname, realpath
    from os import chdir
    from sys import argv
    if __file__:
        path = dirname(realpath(__file__))
    else:
        path = dirname(realpath(argv[0]))
    chdir(path)
    
def bind_move_window(ui,lines):
    'program to bind any move to the window to a redraw event'
    ui.w = ui.root.winfo_width()
    def redraw_when_moved(event):
        if not ui.w==ui.root.winfo_width():
            ui.w = ui.root.winfo_width()
            lines.get_bg(redraw=True)
            #lines.redraw_pars_mers()
    ui.root.bind('<Configure>',redraw_when_moved)

def Create_interaction(test=False,profile=None,**kwargs):
    'Main program to start the moving lines and set up all the map and interactions'
    
    warnings.simplefilter(action = "ignore", category = FutureWarning)
     
    goto_cwd()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--details", help="show help details", action="store_true", default=False)
    parser.add_argument("-v", "--verbose", help="show verbose print outs, for debugging", action="store_true", default=False)

    args = parser.parse_args()
    
    flabels = 'labels.txt'
    faero = 'aeronet_locations.txt' 
    
    if args.details:
        from os.path import isfile
        print("***********************************************************************")
        print("\n            Moving Lines, Research flight planning software\n")
        print("***********************************************************************")
        print("DOI: https://zenodo.org/doi/10.5281/zenodo.1478125")
        print("Version:", __version__)
        print("***********************************************************************")
        print("\n            Checking files\n")
        print("Profile file:",profile_filename)
        print(" ... exists: ",isfile(profile_filename))
        print("Platform file:",platform_filename)
        print(" ... exists: ",isfile(platform_filename))
        print("Icon file:",icon_filename)
        print(" ... exists: ",isfile(icon_filename))
        print("Labels file:",flabels)
        print(" ... exists: ",isfile(flabels))
        print("aeronet location file:",faero)
        print(" ... exists: ",isfile(faero))
        print("satellite TLE file:",'sat.tle')
        print(" ... exists: ",isfile('sat.tle'))
        print("WMS list file:",'WMS.txt')
        print(" ... exists: ",isfile('WMS.txt'))
        
        from sys import exit
        exit()
    
    
    ui = window(tk.Tk()) #Create_gui()
    ui.tb.set_message('Creating basemap')
    profile = Get_basemap_profile()
    m = mi.build_basemap(fig=ui.fig,profile=profile)
    ui.ax1 = m
    if profile:
        sla,slo = profile['Start_lat'],profile['Start_lon']
    else:
        sla,slo = None,None
    line = init_plot(m,start_lat=sla,start_lon=slo,color='red')

    try:
        ui.tb.set_message('putting labels and aeronet')
        line.labels_points = mi.plot_map_labels(m,flabels,alpha=0.4)
        mi.plot_map_labels(m,faero,marker='*',skip_lines=2,color='y',textcolor='k',alpha=0.3)
    except Exception as e:
        print('Problem with label files!',e)
    get_datestr(ui)
    ui.tb.set_message('making the Excel connection')
    wb = ex.dict_position(datestr=ui.datestr,color=line.get_color(),profile=profile,
         version=__version__,platform_file=platform_filename,**kwargs)
    ui.tb.set_message('Building the interactivity on the map')
    lines = mi.LineBuilder(line,m=m,ex=wb,tb=ui.tb,blit=True,verbose=args.verbose)
    ui.tb.set_message('Saving temporary excel file')
    savetmp(ui,wb)
    
    build_buttons(ui,lines)
    lines.get_bg(redraw=True)
    bind_move_window(ui,lines)
    ui.tb.set_message('Ready for interaction')
    lines.get_bg(redraw=True)
    def stopandquit():
        'simple function to handle the stop and quit'
        lines.ex.wb.close()
        ui.root.quit()
        ui.root.destroy()

    ui.root.protocol('WM_DELETE_WINDOW',stopandquit)
    if not test:
        ui.root.mainloop()
    return lines,ui

if __name__ == "__main__":
    lines,ui = Create_interaction(test=False)

