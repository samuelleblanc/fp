# gui codes to use in coordination with moving_lines software
# Copyright 2015 Samuel LeBlanc
import tkinter.simpledialog as tkSimpleDialog
import tkinter as Tk
from tkinter import ttk
try:
    from matplotlib.backends.backend_tkagg import ToolTip
except:
    from matplotlib.backends._backend_tk import ToolTip
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk as NavigationToolbar2TkAgg
from matplotlib.backend_bases import Event
from matplotlib.image import imread
import numpy as np

class gui:
    """
    Purpose:
        Class that contains gui interactions
        makes a few buttons and compiles the functions used when buttons are clicked
        Some actual calculations are made here such as loading of files
    Inputs:
        line object from linebuilder, with connected excel_interface
    outputs:
        none, only gui and its object
        Modifies the tkinter Basemap window via calls to plotting
    Dependencies:
        tkinter
        excel_interface
        os.path
        matplotlib
        tkFileDialog
        tkSimpleDialog
        tkMessageBox
        OWSLib
    Example:
        ...
    History:
        Written: Samuel LeBlanc, 2015-08-18, NASA Ames, CA
        Modified: Samuel LeBlanc, 2015-09-02, Santa Cruz, CA
	          - added handlers for a few new buttons
		  - modified imports to be more specific
        Modified: Samuel LeBlanc, 2015-09-10, Santa Cruz, CA
	          - adding new flight path for another plane capabilities
        Modified: Samuel LeBlanc, 2015-09-15, NASA Ames
                  - added tkinter dialog classes fopr special gui interactions
                      -initial profile setting of Basemap
                      -select flights/points
                      -move points
                  - added GEOS figure adding with WMS service - not yet working
        Modified: Samuel LeBlanc, 2016-06-12, NASA Ames
                  - modified the button layout and functions. added rotate buttons and flt_module
                  - modified plotting of sza and alt vs time for nicer plots
                  - fixed load_flight
                  - added saving utilities
        Modified: Samuel LeBlanc, 2016-07-11, on plane from SFO -> WFF
                  - added remove satellite tracks button.
                  - fixed a few bugs
        Modified: Samuel LeBlanc, 2016-07-12, WFF, VA
                  - added a plot aeronet values
        Modified: Samuel LeBlanc, 2016-07-22, NASA Ames at Santa Cruz, CA
                  - made custom toolbar, with new buttons, and event call backs for refreshing when zooming or panning, back or forward.
                  - loading larger part of map to simplify panning and zooming
                  - fixed some bug reporting
                  - added figures to the flt_module selections
                  - added exchange cursor to geos selection
        Modified: Samuel LeBlanc, 2016-08-25, NASA P3, on transit between Barbados to Ascension
                  - Added point insert featurs in the addpoint dialog
        Modified: Samuel LeBlanc, 2016-08-30, Swakopmund, Namibia
                  - added force speed calculation button function handler
        MOdified: Samuel LeBlanc, 2016-08-31, Swakopmund, Namibia
                  - added plot alt vs lat
                  - added waypoints on sza and alt plots
                  - made refresh also refresh the speeds
        Modified: Samuel LeBlanc, 2020-01-13, Santa Cruz, CA
                  - added screen geometry calculator
                  - reformat of flt_module list to have mutiple columns
                  
    """
    def __init__(self,line=None,root=None,noplt=False,debug=False):
        import tkinter as tk
        import os
        if not line:
            print('No line_builder object defined')
            return
        self.line = line
        self.flight_num = 0
        self.iactive = tk.IntVar()
        self.iactive.set(0)
        self.colors = ['red']
        self.colorcycle = ['red','blue','green','cyan','magenta','yellow','black','lightcoral','teal','darkviolet','orange']
        self.get_geometry()
        self.geotiff_path = os.path.relpath('elevation_10KMmd_GMTEDmd.tif')
        self.pptx_point_format = '..{deltat_min} minutes from previous\n#{i:02.0f} - {utc_str} UTC, {wpname}:{Comment}'
        if not root:
            self.root = tk.Tk()
        else:
            self.root = root

        self.noplt = noplt
        self.newflight_off = True
        self.debug = debug
        try:
            self.line.line.figure.canvas.mpl_connect('home_event', self.refresh)
        except ValueError:
            print('problem with Home button')
        self.line.line.figure.canvas.mpl_connect('pan_event', self.refresh)
        self.line.line.figure.canvas.mpl_connect('zoom_event', self.refresh)
        self.line.line.figure.canvas.mpl_connect('back_event', self.refresh)
        self.line.line.figure.canvas.mpl_connect('forward_event', self.refresh)
    
    def get_geometry(self):
        """
        Workaround to get the size of the current screen in a multi-screen setup.

        Returns:
            geometry (str): The standard Tk geometry string.
                [width]x[height]+[left]+[top]
        """
        import tkinter as tk
        
        root_nul = tk.Tk()
        root_nul.update_idletasks()
        root_nul.attributes('-fullscreen', True)
        root_nul.state('iconic')
        geometry = root_nul.winfo_geometry()
        root_nul.destroy()
        w,h,l,t = map(int,geometry.replace('+','x').split('x'))
        self.width = w
        self.height = h
        self.left = l
        self.top = t
        return w,h,l,t
    
    def gui_file_select(self,ext='*',
                        ftype=[('Excel 1997-2003','*.xls'),('Excel','*.xlsx'),
                               ('Kml','*.kml'),('All files','*.*')]):
        """
        Simple gui file select program. Uses TKinter for interface, returns full path
        """
        from tkinter import Tk
        from tkinter.filedialog import askopenfilename
        from os.path import abspath
        Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
        filename = askopenfilename(defaultextension=ext,filetypes=ftype) # show an "Open" dialog box and return the path to the selected file
        if filename:
            filename = abspath(filename)
        return filename

    def gui_file_save(self,ext='*',
                      ftype=[('Excel 1997-2003','*.xls'),('Excel','*.xlsx'),
                             ('Kml','*.kml'),('All files','*.*'),('PNG','*.png')]):
        """
        Simple gui file save select program.
        Uses TKinter for interface, returns full path
        """
        from tkinter import Tk
        from tkinter.filedialog import asksaveasfilename
        from os.path import abspath
        Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
        filename = asksaveasfilename(defaultextension=ext,filetypes=ftype) # show an "Open" dialog box and return the path to the selected file
        filename = abspath(filename)
        return filename
        
    def gui_file_path(self,title='Select directory',initial_dir=None):
        """
        Simple gui file path select program.
        Uses TKinter for interface, returns full path to directory
        """
        from tkinter import Tk
        from tkinter.filedialog import askdirectory
        from os.path import abspath, curdir
        Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
        if not initial_dir:
            initial_dir = abspath(curdir)
        filepath = askdirectory(initialdir=initial_dir,title=title) # show an "Open" dialog box and return the path to the selected file
        filepath = abspath(filepath)
        return filepath

    def make_text(self):
        k = tk.Label(self.root,text='button pressed').pack()
        
    def make_pressed(self):
        self.bpressed.config(relief='sunken')
    
    
        
    def gui_saveas2kml(self):
        'Calls the save2kml excel_interface method with new filename'
        if not self.line:
            print('No line object')
            return
        filename = self.gui_file_save(ext='.kml',ftype=[('All files','*,*'),('KML','*.kml')])
        if not filename: return
        self.kmlfilename = filename
        self.line.ex.save2kml(filename=self.kmlfilename)
        
    def gui_save2kml(self):
        'Calls the save2kml excel_interface method'
        if not self.line:
            print('No line object')
            return
        if not self.kmlfilename:
            self.stopandquit()
            print('Problem with kmlfilename')
            return
        self.line.ex.save2kml(filename=self.kmlfilename)

    def gui_save_txt(self):
        'Calls the save2txt excel_interface method'
        if not self.line:
            print('No line object')
            return
        import tkinter.messagebox as tkMessageBox
        tkMessageBox.showwarning('Saving one flight','Saving flight path of:%s' %self.line.ex.name)
        filename = self.gui_file_save(ext='.txt',ftype=[('All files','*.*'),
                                                         ('Plain text','*.txt')])
        if not filename: return
        print('Saving Text file to :'+filename)
        self.line.ex.save2txt(filename)

    def gui_save_xl(self):
        'Calls the save2xl excel_interface method'
        if not self.line:
            print('No line object')
            return
        filename = self.gui_file_save(ext='.xlsx',ftype=[('All files','*.*'),
                                                         ('Excel 1997-2003','*.xls'),
                                                         ('Excel','*.xlsx')])
        if not filename: return
        print('Saving Excel file to :'+filename)
        self.line.ex.save2xl(filename)
        
    def gui_save_xl_pilot(self):
        'gui wrapper for calling the save2xl_for_pilots excel_interface method'
        try:
            from excel_interface import save2xl_for_pilots,save2csv_for_FOREFLIGHT_UFP
        except ModuleNotFoundError:
            from .excel_interface import save2xl_for_pilots,save2csv_for_FOREFLIGHT_UFP
        filename = self.gui_file_save(ext='.xlsx',ftype=[('All files','*.*'),
                                                         ('Excel 1997-2003','*.xls'),
                                                         ('Excel','*.xlsx')])
        if not filename: return
        self.line.ex.wpname = self.line.ex.get_waypoint_names(fmt=self.line.ex.p_info.get('waypoint_format','{x.name[0]}{x.datestr.split("-")[2]}{w:02d}'))
        print('Saving Pilot Excel file to :'+filename)
        save2xl_for_pilots(filename,self.line.ex_arr)
        self.line.ex.wb.sh.activate()
        
        for ex in self.line.ex_arr:
            save2csv_for_FOREFLIGHT_UFP(filename.split('.')[0],ex,verbose=True)

    def gui_open_xl(self):
        'Function to load a excel spreadsheet that has been previously saved'
        try:
            import excel_interface as ex
        except ModuleNotFoundError:
            from . import excel_interface as ex
        
        if not self.line:
            print('No line object')
            return
        filename = self.gui_file_select(ext='.xls',ftype=[('Excel','*.xlsx'),('All files','*.*'),
                                                         ('Excel 1997-2003','*.xls')])
        if not filename: return
        try:
            self.line.disconnect()
            self.line.ex.wb.close()
        except:
            nul = 0
        self.line.tb.set_message('Opening Excel File:'+filename)
        
        
        self.flight_num = 0
        self.iactive.set(0)
        self.line.ex_arr = ex.populate_ex_arr(filename=filename,colorcycle=self.colorcycle)
        self.line.m.ax.set_title(self.line.ex_arr[0].datestr)
        for b in self.flightselect_arr:
            b.destroy()
        self.flightselect_arr = []
        try:
            for k in list(self.line.m.figure_under.keys()):
                k.remove()
        except:
            pass
        try:
            for s in self.sat_obj:
                s.remove()
        except:
            pass
        self.colors = []
        for i in range(len(self.line.ex_arr)):
            self.line.ex = self.line.ex_arr[i]
            self.line.onfigureenter([1]) # to force redraw and update from the newly opened excel
            self.load_flight(self.line.ex)
        self.line.line.figure.canvas.draw()
        self.line.connect()
        self.flight_num = len(self.line.ex_arr)-1

    def gui_save2gpx(self):
        'Calls the save2gpx excel_interface method'
        if not self.line:
            print('No line object')
            return
        filename = self.gui_file_save(ext='.gpx',ftype=[('All files','*.*'),
                                                         ('GPX','*.gpx')])
        if not filename: return
        print('Saving GPX file to :'+filename)
        self.line.ex.save2gpx(filename)
		
    def gui_save2ict(self):
        'Calls the save2ict excel_interface method'
        if not self.line:
            print('No line object')
            return
        import tkinter.messagebox as tkMessageBox
        tkMessageBox.showwarning('Saving one flight','Saving flight path in form of ict for:%s' %self.line.ex.name)
        filepath = self.gui_file_path(title='Select directory to save ict file')
        if not filepath: return
        print('Saving ICT file to :'+filepath)
        self.line.ex.save2ict(filepath)
        
    def gui_plotalttime_cmb(self,surf_alt=True,no_extra_axes=False):
        'dummy function to call plotaltitime multi'
        return self.gui_plotalttime(surf_alt=surf_alt,no_extra_axes=no_extra_axes,multi=True)
        
    def gui_plotalttime(self,surf_alt=True,no_extra_axes=False,multi=False):
        'gui function to run the plot of alt vs. time'
        import os
        if self.noplt:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            try:
                from gui import custom_toolbar
            except ModuleNotFoundError:
                from .gui import custom_toolbar
            from matplotlib.figure import Figure
            import tkinter as tk
            root = tk.Toplevel()
            root.geometry('1000x550')
            root.wm_title('Alt vs. Time: {}'.format(self.line.ex.name))
            fig = Figure()
            canvas = FigureCanvasTkAgg(fig, master=root)
            canvas.draw()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            tb = NavigationToolbar2TkAgg(canvas,root)
            tb.pack(side=tk.BOTTOM)
            tb.update()
            canvas._tkcanvas.pack(side=tk.TOP,fill=tk.BOTH,expand=1)
            ax1 = fig.add_subplot(111)
        else:
            print('Problem with loading a new figure handler')
            return
        if multi and (len(self.line.ex_arr)>1):
            # get the utc limits
            nm = 'Combined'
            surf_el_label_multi = '\nunder {}'.format(self.line.ex.name)
            root.wm_title('Alt vs. Time: {}'.format('Combined'))
            cmb,distances = self.line.calc_dist_from_each_points()
            cum2utc = cmb['utc'][0]
            coordinated_label = 'coordinated'
            for j,ex in enumerate(self.line.ex_arr):
                ax1.plot(ex.utc,ex.alt,'x-',label=ex.name,color=ex.color)
                for i,w in enumerate(ex.WP):
                    ax1.annotate('#{}'.format(w),(ex.utc[i],ex.alt[i]),color=ex.color)
                    for k in range(len(self.line.ex_arr)):
                        if not k == j and np.isfinite(distances[j][i][k]):
                            ax1.annotate('{:2.1f} km'.format(distances[j][i][k]),(ex.utc[i],ex.alt[i]-200*(k+1)*(0.5-i%2)*2),color=self.line.ex_arr[k].color,ha='center',clip_on=False,fontsize=7)
                            if distances[j][i][k]<30.0:
                                ax1.annotate('{:2.1f} km'.format(distances[j][i][k]),(ex.utc[i],ex.alt[i]-200*(k+1)*(0.5-i%2)*2),color=self.line.ex_arr[k].color,ha='center',clip_on=False,fontsize=7, weight='bold')
                                ax1.axvline(ex.utc[i]+0.02*(k+1),color=self.line.ex_arr[k].color, lw=2,linestyle=':',label=coordinated_label)
                                coordinated_label = None
            ax1.set_xlabel('UTC [Hours]')
            time = self.line.ex.utc
        else:
            ax1.plot(self.line.ex.cumlegt,self.line.ex.alt,'x-',label=self.line.ex.name)
            for i,w in enumerate(self.line.ex.WP):
                ax1.annotate('{}'.format(w),(self.line.ex.cumlegt[i],self.line.ex.alt[i]),color='r')
            cum2utc = self.line.ex.utc[0]
            nm = self.line.ex.name
            surf_el_label_multi = ''
            ax1.set_xlabel('Flight duration [Hours]')
            time = self.line.ex.cumlegt
        if surf_alt:
            try:
                try:
                    from map_interactive import get_elev
                except ModuleNotFoundError:
                    from .map_interactive import get_elev
                if not os.path.isfile(self.geotiff_path):
                    self.geotiff_path = self.gui_file_select(ext='.tif',ftype=[('All files','*.*'),
                                                             ('GeoTiff','*.tif')])
                elev,lat_new,lon_new,utcs,geotiff_path = get_elev(time,self.line.ex.lat,self.line.ex.lon,dt=60,geotiff_path=self.geotiff_path)
                ax1.fill_between(utcs,elev,0,color='tab:brown',alpha=0.3,zorder=1,label='Surface\nElevation'+surf_el_label_multi,edgecolor=None)
                self.geotiff_path = geotiff_path
            except Exception as e:
                print('Surface elevation not working'+e)
        ax1.set_title('Altitude vs time for %s on %s' %(nm,self.line.ex.datestr),y=1.08)
        fig.subplots_adjust(top=0.85,right=0.8)
        
        ax1.set_ylabel('Alt [m]')
        ax1.xaxis.tick_bottom()
        if not no_extra_axes:
            ax2 = ax1.twiny()
            ax2.xaxis.tick_top()
            if multi and (len(self.line.ex_arr)>1):
                ax2.set_xlabel('')
                ax2.set_xticks(ax1.get_xticks())
                utc_label = ['' for u in ax1.get_xticks()]
                ax2.set_xticklabels(utc_label)
            else:
                ax2.set_xlabel('UTC [Hours]')
                ax2.set_xticks(ax1.get_xticks())
                utc_label = ['%2.2f'%(u+cum2utc) for u in ax1.get_xticks()]
                ax2.set_xticklabels(utc_label)
            ax3 = ax1.twinx()
            ax3.yaxis.tick_right()
            ax3.set_ylabel('Altitude [Kft]')
            ax3.set_yticks(ax1.get_yticks())
            alt_labels = ['%2.2f'%(a*3.28084/1000.0) for a in ax1.get_yticks()]
            ax3.set_yticklabels(alt_labels)
            ax3.set_ylim(ax1.get_ylim())
        ax1.grid()
        ax1.legend(frameon=True,loc='center left', bbox_to_anchor=(1.05, 0.75))
        if self.noplt:
            canvas.draw()
            fig.canvas = canvas
        else:
            plt.figure(f1.number)

        return fig
        
    def gui_plotmss_profile(self,filename='vert_WMS.txt',hires=False):
        'function to plot the alt vs time, with the addition oif the MSS (WMS) service with under figure profiles'
        try:
            from map_interactive import alt2pres, load_WMS_file
        except ModuleNotFoundError:
            from .map_interactive import alt2pres, load_WMS_file
        fig = self.gui_plotalttime(surf_alt=False,no_extra_axes=True)
        
        #build the waypoints string
        wp_str =  ['{:2.2f},{:2.2f},'.format(la,self.line.lons[ila]) for ila,la in list(enumerate(self.line.lats))]
        wps = ''.join(wp_str).strip(',')
        
        #get the bbox extent in pressure levels
        press = alt2pres(self.line.ex.alt)
        bbox = (201,1013.25,10,min(press)/100.0)
        
        # load the wms
        out = load_WMS_file(filename)
        arr = ['{} : {}'.format(dict['name'],dict['website']) for dict in out]
        if len(arr)>1:
            popup = Popup_list(arr,title='Select WMS server to load graphics capabilities')
            i = popup.var.get()
        else:
            i = 0
        img,label,img_leg = self.add_WMS(website=out[i]['website'],printurl=True,bbox=bbox,path=wps,hires=hires,vert_crs=True)

        try:
            xlims = fig.axes[0].get_xlim()
            ylims = fig.axes[0].get_ylim()
            if img: fig.axes[0].imshow(img,origin='upper',extent=[0,max(self.line.ex.cumlegt),0,max(self.line.ex.alt)],aspect='auto') #
            fig.canvas.draw()
            #import pdb; pdb.set_trace()
        except: 
            print('Problem addin profile figure, continuning...')
            #import pdb; pdb.set_trace()

        if label:
            try:
                fig.ax.text(0.0,-0.15,label,transform=fig.ax.transAxes,clip_on=False,color='grey')
            except:
                print('Problem adding text on profile figure, continuning...')
        return fig
        
    def gui_plotaltlat(self):
        'gui function to run the plot of alt vs. latitude'
        if self.noplt:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            try:
                from gui import custom_toolbar
            except ModuleNotFoundError: 
                from .gui import custom_toolbar
            from matplotlib.figure import Figure
            import tkinter as tk
            root = tk.Toplevel()
            root.wm_title('Alt vs. Latitude: {}'.format(self.line.ex.name))
            fig = Figure()
            canvas = FigureCanvasTkAgg(fig, master=root)
            canvas.draw()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            tb = NavigationToolbar2TkAgg(canvas,root)
            tb.pack(side=tk.BOTTOM)
            tb.update()
            canvas._tkcanvas.pack(side=tk.TOP,fill=tk.BOTH,expand=1)
            ax1 = fig.add_subplot(111)
        else:
            print('Problem with loading a new figure handler')
            return
        ax1.plot(self.line.ex.lat,self.line.ex.alt,'x-',label=self.line.ex.name)
        for i,w in enumerate(self.line.ex.WP):
            ax1.annotate('{}'.format(w),(self.line.ex.lat[i],self.line.ex.alt[i]),color='r')
        try:
            try:
                from map_interactive import get_elev
            except ModuleNotFoundError:
                from .map_interactive import get_elev
            elev,lat_new,lon_new,utcs,geotiff_path = get_elev(self.line.ex.cumlegt,self.line.ex.lat,self.line.ex.lon,dt=60,geotiff_path=self.geotiff_path)
            ax1.fill_between(lat_new,elev,0,color='tab:brown',alpha=0.3,zorder=1,label='Surface\nElevation',edgecolor=None)
            [ax1.fill_between([l,lat_new[i+1]],[elev[i],elev[i+1]],0,color='tab:brown',alpha=0.1,zorder=1,edgecolor=None) for i,l in list(enumerate(lat_new[:-1]))]
            self.geotiff_path = geotiff_path
        except:
            print('Surface elevation not working')
        ax1.set_title('Altitude vs. Latitude for %s on %s' %(self.line.ex.name,self.line.ex.datestr),y=1.08)
        fig.subplots_adjust(top=0.85,right=0.8)
        ax1.set_xlabel('Latitude [Degrees]')
        ax1.set_ylabel('Alt [m]')
        ax1.xaxis.tick_bottom()
        ax3 = ax1.twinx()
        ax3.yaxis.tick_right()
        ax3.set_ylabel('Altitude [Kft]')
        ax3.set_yticks(ax1.get_yticks())
        alt_labels = ['%2.2f'%(a*3.28084/1000.0) for a in ax1.get_yticks()]
        ax3.set_yticklabels(alt_labels)
        ax3.set_ylim(ax1.get_ylim())
        ax1.grid()
        ax1.legend(frameon=True,loc='center left', bbox_to_anchor=(1.05, 0.75))
        if self.noplt:
            canvas.draw()
        else:
            plt.figure(f1.number)
        return fig

    def gui_plotsza(self):
        'gui function to plot the solar zenith angle of the flight path'
        #import tkinter.messagebox as tkMessageBox
        #tkMessageBox.showwarning('Sorry','Feature not yet implemented') 
        #return 
        if not self.noplt:
             print('No figure handler, sorry will not work')
             return
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        try:
            from gui import custom_toolbar
        except ModuleNotFoundError:
            from .gui import custom_toolbar
        from matplotlib.figure import Figure
        import tkinter as tk
        root = tk.Toplevel()
        root.wm_title('Solar position vs. Time: {}'.format(self.line.ex.name))
        root.geometry('800x550')
        fig = Figure()
        canvas = FigureCanvasTkAgg(fig, master=root)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        tb = NavigationToolbar2TkAgg(canvas,root)
        tb.pack(side=tk.BOTTOM)
        tb.update()
        canvas._tkcanvas.pack(side=tk.TOP,fill=tk.BOTH,expand=1)
        ax1 = fig.add_subplot(2,1,1)
        ax1.plot(self.line.ex.cumlegt,self.line.ex.sza,'x-')
        for i,w in enumerate(self.line.ex.WP):
            ax1.annotate('{}'.format(w),(self.line.ex.cumlegt[i],self.line.ex.sza[i]),color='r')
        ax1.set_title('Solar position along flight track for %s on %s' %(self.line.ex.name,self.line.ex.datestr), y=1.18)
        fig.subplots_adjust(top=0.85)
        #ax1.set_xlabel('Flight duration [Hours]')
        ax1.set_ylabel('SZA [degree]')
        #ax1.set_xticklabels(['','','','','',''])
        ax1.grid()
        axticks = ax1.get_xticks()
        ax1_up = ax1.twiny()
        ax1_up.xaxis.tick_top()
        cum2utc = self.line.ex.utc[0]
        ax1_up.set_xticks(axticks)
        utc_label = ['%2.2f'%(u+cum2utc) for u in axticks]
        ax1_up.set_xticklabels(utc_label)
        ax1_up.set_xlabel('UTC [Hours]')
        ax2 = fig.add_subplot(2,1,2,sharex=ax1)
        ax2.plot(self.line.ex.cumlegt,self.line.ex.azi,'ok',label='Sun PP')
        ax2.plot(self.line.ex.cumlegt,[a-180 for a in self.line.ex.azi],'o',color='lightgrey',label='Sun anti-PP')
        ax2.plot(self.line.ex.cumlegt,[a+180 for a in self.line.ex.azi],'o',color='lightgrey')
        ax2.set_ylabel('Azimuth angle [degree]')
        ax2.set_xlabel('Flight duration [Hours]')
        ax2.grid()
        ax2.set_ylim(0,360)
        ax2.plot(self.line.ex.cumlegt,self.line.ex.bearing,'xr',label='{} bearing'.format(self.line.ex.name))
        box = ax1.get_position()
        ax1.set_position([box.x0, box.y0, box.width * 0.75, box.height])
        ax1_up.set_position([box.x0, box.y0, box.width * 0.75, box.height])
        box = ax2.get_position()
        ax2.set_position([box.x0, box.y0, box.width * 0.75, box.height])
        ax2.legend(frameon=True,numpoints=1,bbox_to_anchor=[1.4,0.8])
        canvas.draw()
        return fig

    def load_flight(self,ex):
        'Program to populate the arrays of multiple flights with the info of one array'
        import tkinter as tk
        self.colors.append(ex.color)
        self.line.tb.set_message('load_flight values for:%s' %ex.name)

        self.flightselect_arr.append(tk.Radiobutton(self.root,text=ex.name,
                                                    fg=ex.color,
                                                    variable=self.iactive,
                                                    value=self.flight_num,
                                                    indicatoron=0,
                                                    command=self.gui_changeflight,bg='white'))
        self.flightselect_arr[self.flight_num].pack(in_=self.frame_select,side=tk.TOP,
                                                    padx=4,pady=2,fill=tk.BOTH)
        self.line.newline()
        self.iactive.set(self.flight_num)
        self.gui_changeflight()
        self.flight_num = self.flight_num+1

    def gui_newflight(self):
        'Program to call and create a new excel spreadsheet'
        import tkinter.simpledialog as tkSimpleDialog
        import tkinter.messagebox as tkMessageBox
        try:
            import excel_interface as ex
        except ModuleNotFoundError:
            from . import excel_interface as ex
        
        import tkinter as tk
        if self.newflight_off:
            tkMessageBox.showwarning('Sorry','Feature not yet implemented')
            return
        
        newname = tkSimpleDialog.askstring('New flight path',
                                           'New flight path name:')
        if not newname:
            print('Cancelled')
            return
        self.flight_num = self.flight_num+1
        self.colors.append(self.colorcycle[self.flight_num])
        self.flightselect_arr.append(tk.Radiobutton(self.root,text=newname,
	                                            fg=self.colorcycle[self.flight_num],
                                                    variable=self.iactive,
                                                    value=self.flight_num,
                                                    indicatoron=0,
                                                    command=self.gui_changeflight,bg='white'))
        self.flightselect_arr[self.flight_num].pack(in_=self.frame_select,side=tk.TOP,
                                                    padx=4,pady=2,fill=tk.BOTH)
        print('adding flight path to date: %s' %self.line.ex.datestr)
        self.line.ex_arr.append(ex.dict_position(datestr=self.line.ex.datestr,
                                                 name=newname,
                                                 newsheetonly=True,
                                                 sheet_num=self.flight_num,
                                                 color=self.colorcycle[self.flight_num],
                                                 lon0=self.line.ex.lon[0],lat0=self.line.ex.lat[0],
                                                 UTC_start=self.line.ex.utc[0],
                                                 UTC_conversion=self.line.ex.UTC_conversion,
                                                 alt0=self.line.ex.alt[0],version=self.line.ex.__version__,campaign=self.line.ex.campaign))
        self.line.newline()
        self.iactive.set(self.flight_num)
        self.gui_changeflight()

    def gui_removeflight(self):
        'Program to call and remove a flight path from the plotting'
        import tkinter.simpledialog as tkSimpleDialog
        import tkinter.messagebox as tkMessageBox
        tkMessageBox.showwarning('Sorry','Feature not yet implemented')
        return
        try:
            import excel_interface as ex
        except ModuleNotFoundError:
            from . import excel_interface as ex
        import tkinter as tk
        try:
            from gui import Select_flights
        except ModuleNotFoundError:
            from .gui import Select_flights
        self.name_arr = []
        for x in self.line.ex_arr:
            self.name_arr.append(x)
        flights = Select_flights(self.name_arr,title='Delete Flights',Text='Choose flights to delete')
        for i,val in enumerate(flights.result):
            if val:
                name2del = self.line.ex_arr[i].name
                self.flightselect_arr[i].destroy()
                for i in range(i,len(self.flightselect_arr)):
                    self.flightselect_arr[i].configure({'value':i-1})
                self.flightselect_arr[i].remove()
                self.line.removeline(i)
                self.line.ex_arr[i].exremove()
                self.line.ex_arr[i].remove()
    
    def gui_changeflight(self):
        'method to switch out the active flight path that is used'
        if self.newflight_off:
            import tkinter.messagebox as tkMessageBox
            tkMessageBox.showwarning('Sorry','Feature not yet implemented')
            return
        self.flightselect_arr[self.iactive.get()].select()
        self.line.iactive = self.iactive.get()
        self.line.ex = self.line.ex_arr[self.iactive.get()]
        self.line.makegrey()
        self.line.line = self.line.line_arr[self.iactive.get()]
        self.line.ex.switchsheet(self.iactive.get())
        self.line.colorme(self.colors[self.iactive.get()])
        self.line.update_labels(nodraw=False,updatexys=True)
        self.line.get_bg()
        
    def gui_savefig(self):
        'gui program to save the current figure as png'
        if not self.line:
            print('No line object')
            return
        filename = self.gui_file_save(ext='.png',ftype=[('PNG','*.png')])
        if not filename: return
        legend,grey_index = self.prep_mapsave()
        if type(self.line.line) is list:
            lin = self.line.line[0]
        else:
            lin = self.line.line
        lin.figure.savefig(filename,dpi=600,transparent=False)
        self.return_map(legend,grey_index)
        
    def prep_mapsave(self):
        'Method to prepare the map to be saved, adds a legend and colors each line'
        leg_items = []
        i_grey = []
        line_list = []
        line_start = self.line.line
        for i,b in enumerate(self.flightselect_arr):
            leg_items.append(b.config('text')[-1])
            self.line.line = self.line.line_arr[i]
            self.line.colorme(self.colors[i])
            line_list.append(self.line.line)
            if i!=self.line.iactive:
                i_grey.append(i)
        if i>3: 
            ncol=2
        else: ncol=1
        leg = self.line.m.ax.legend(line_list,leg_items,loc='lower right',bbox_to_anchor=(1.0,-0.3),ncol=ncol)
        self.line.line = line_start
        return leg,i_grey
        
    def return_map(self,leg,i_grey):
        'function to return the map to normal, greying the lines, and removing the legend'
        line_start = self.line.line
        for i in i_grey:
            self.line.line = self.line.line_arr[i]
            self.line.makegrey()
        self.line.line = line_start
        leg.remove()
    
    def gui_saveall(self):
        'gui program to run through and save all the file formats, without verbosity, for use in distribution'
        from os import path
        try:
            from excel_interface import save2xl_for_pilots, save2csv_for_FOREFLIGHT_UFP
        except ModuleNotFoundError:
            from .excel_interface import save2xl_for_pilots, save2csv_for_FOREFLIGHT_UFP
        try:
            from write_utils import create_generic_pptx
        except ModuleNotFoundError:
            from .write_utils import create_generic_pptx
        import tkinter.messagebox as tkMessageBox
        slides = []
        #slides (list of dict): Each dictionary represents a slide.
        #    - For text content: {"text": "Your slide content"}
        #    - For image content: {"image_path": "path/to/image.jpg"}
        #    - For bulelts content: {"bulelts":["bulelt1","bullet 2"]}
        #    - For multiple images: {"multiple_images":["path/to/image1.jpg"]}
        #    - For title of slide : {"title":"Your slide title"}
        filename = self.gui_file_save(ext='*',ftype=[('Excel','*.xlsx')])
        if not filename:
            tkMessageBox.showwarning('Cancelled','Saving all files cancelled')
            return
        f_name,_ = path.splitext(filename)
        print('Saving Excel file to :'+f_name+'.xlsx')
        try:
            self.line.ex.save2xl(f_name+'.xlsx')
        except:
            tkMessageBox.showwarning('Excel not saved','Error in saving excel file: {}'.format(f_name+'.xlsx'))
        print('Saving Excel file for pilots to :'+f_name+'_for_pilots.xlsx')
        try:
            save2xl_for_pilots(f_name+'_for_pilots.xlsx',self.line.ex_arr)
        except Exception as ie:
            tkMessageBox.showwarning('Excel not saved','Error in saving excel pilot file: {} \n error:{}'.format(f_name+'_for_pilots.xlsx',ie))
        try:
            self.line.ex.wpname = self.line.ex.get_waypoint_names(fmt=self.line.ex.p_info.get('waypoint_format','{x.name[0]}{x.datestr.split("-")[2]}{w:02d}'))
            self.line.ex.wb.sh.activate()
            for ex in self.line.ex_arr:
                save2csv_for_FOREFLIGHT_UFP(f_name+'_for_pilots',ex,verbose=True)
        except Exception as ef:
            tkMessageBox.showwarning('Issue saving pilot versions','Error with pilot versions saving: {}'.format(ef))
        try:
            self.line.ex.wb.set_current()
        except:
            tkMessageBox.showwarning('Unable to close for_pilots spreadsheet, please close manually')
        print('Saving figure file to :'+f_name+'_map.png')
        if type(self.line.line) is list:
            lin = self.line.line[0]
        else:
            lin = self.line.line
        legend,grey_index = self.prep_mapsave()
        lin.figure.savefig(f_name+'_map.png',dpi=600,transparent=False)
        slides.append(dict(title='Map of flight paths',image_path=f_name+'_map.png'))
        #save combined plot
        try:
            fig = self.gui_plotalttime_cmb()
            print('Saving the Alt vs time plot at:'+f_name+'_alt_{}.png'.format('combined'))
            fig.savefig(f_name+'_alt_{}.png'.format('combined'),dpi=600,transparent=False)
            slides.append(dict(title='Combined Altitude flight paths',image_path=f_name+'_alt_{}.png'.format('combined')))
        except:
            print('Issue saving the Alt vs time plot at:'+f_name+'_alt_{}.png'.format('combined'))
            
        # go through each flight path
        names = [x.name for x in self.line.ex_arr]
        subtitle = ''
        cmb,distances = self.line.calc_dist_from_each_points()
        for i,x in enumerate(self.line.ex_arr):
            self.iactive.set(i)
            self.gui_changeflight()
            print('Saving Text file to :'+f_name+'_{}.txt'.format(x.name))
            self.line.ex.save2txt(f_name+'_{}.txt'.format(x.name))
            print('Saving ICT file to :'+path.dirname(f_name))
            self.line.ex.save2ict(path.dirname(f_name))
            print('Generating the figures for {}'.format(x.name))
            fig = self.gui_plotalttime()
            print('Saving the Alt vs time plot at:'+f_name+'_alt_{}.png'.format(x.name))
            fig.savefig(f_name+'_alt_{}.png'.format(x.name),dpi=600,transparent=False)
            fig = self.gui_plotsza()
            print('Saving the SZA vs time plot at:'+f_name+'_sza_{}.png'.format(x.name))
            fig.savefig(f_name+'_sza_{}.png'.format(x.name),dpi=600,transparent=False)
            fig = self.gui_plotaltlat()
            print('Saving the Alt vs Latitude plot at:'+f_name+'_alt_lat_{}.png'.format(x.name))
            fig.savefig(f_name+'_alt_lat_{}.png'.format(x.name),dpi=600,transparent=False)

            labels,main_points = x.get_main_points(combined_distances=distances[i], combined_utc=cmb,combined_names=names,fmt=self.pptx_point_format)
            table = [[mpt['i'],mpt['utc_str'],mpt['wpname'],mpt['deltat_min'],mpt['Comment']] for mpt in main_points]
            table.insert(0,['WP #','UTC [H]','WP Name','Time delta [minutes]','Comments'])
            float_to_hh_mm = lambda float_hours: '{:02d}:{:02d}'.format(int(float_hours), int((float_hours - int(float_hours)) * 60))
            slides.append(dict(title='{}: Take-off {} UTC-> landing {} UTC\nflight time {:2.2}h {:4.0f} nm'.format(x.name,\
                               float_to_hh_mm(x.utc[0]),float_to_hh_mm(x.utc[-1]),x.cumlegt[-1],x.cumdist_nm[-1]),image_path=f_name+'_alt_{}.png'.format(x.name),
                               table=table,text='Some important points'))
            slides.append(dict(title='{}'.format(x.name),multiple_images=[f_name+'_sza_{}.png'.format(x.name),f_name+'_alt_lat_{}.png'.format(x.name)]))
            subtitle += '{}({:2.1f}h T/O@{}UTC {:4.0f} nm) '.format(x.name,x.cumlegt[-1],float_to_hh_mm(x.utc[0]),x.cumdist_nm[-1])
        print('Saving kml file to :'+f_name+'.kml')
        self.kmlfilename = f_name+'.kml'
        self.line.ex.save2kml(filename=self.kmlfilename)
        self.return_map(legend,grey_index)
        
        #now save all the figures onto at common powerpoint
        try:
            nul,file_name = path.split(f_name)
            create_generic_pptx(slides,f_name+'.pptx', title="Flight plan for {}\n{} \n {}".format(self.line.ex.datestr,file_name,subtitle),
                                subtitle='Objectives:\n   -\n   -\n   -')
        except Exception as ie:
            tkMessageBox.showwarning('Powerpoint slide saving failed.','Error saving powerpoint.\n{}'.format(ie))
            print('powerpoint slide saving failed. Error:  {}'.format(ie))
       
    def gui_savepptx(self):
        'gui program to run through and save all the figures, and makes a powerpoint presentation'
        from os import path
        try:
            from write_utils import create_generic_pptx
        except ModuleNotFoundError:
            from .write_utils import create_generic_pptx
        import tkinter.messagebox as tkMessageBox
        slides = []
        #slides (list of dict): Each dictionary represents a slide.
        #    - For text content: {"text": "Your slide content"}
        #    - For image content: {"image_path": "path/to/image.jpg"}
        #    - For bulelts content: {"bulelts":["bulelt1","bullet 2"]}
        #    - For multiple images: {"multiple_images":["path/to/image1.jpg"]}
        #    - For title of slide : {"title":"Your slide title"}
        filename = self.gui_file_save(ext='*',ftype=[('PowerPoint','*.pptx')])
        if not filename:
            tkMessageBox.showwarning('Cancelled','Saving all files cancelled')
            return
        f_name,_ = path.splitext(filename)
        slides = []
        print('Saving figure file to :'+f_name+'_map.png')
        if type(self.line.line) is list:
            lin = self.line.line[0]
        else:
            lin = self.line.line
        legend,grey_index = self.prep_mapsave()
        lin.figure.savefig(f_name+'_map.png',dpi=600,transparent=False)
        slides.append(dict(title='Map of flight paths',image_path=f_name+'_map.png'))
        #save combined plot
        try:
            fig = self.gui_plotalttime_cmb()
            print('Saving the Alt vs time plot at:'+f_name+'_alt_{}.png'.format('combined'))
            fig.savefig(f_name+'_alt_{}.png'.format('combined'),dpi=600,transparent=False)
            slides.append(dict(title='Combined Altitude flight paths',image_path=f_name+'_alt_{}.png'.format('combined')))
        except:
            print('Issue saving the Alt vs time plot at:'+f_name+'_alt_{}.png'.format('combined'))
            
        # go through each flight path
        names = [x.name for x in self.line.ex_arr]
        subtitle = ''
        cmb,distances = self.line.calc_dist_from_each_points()
        for i,x in enumerate(self.line.ex_arr):
            self.iactive.set(i)
            self.gui_changeflight()
            print('Generating the figures for {}'.format(x.name))
            fig = self.gui_plotalttime()
            print('Saving the Alt vs time plot at:'+f_name+'_alt_{}.png'.format(x.name))
            fig.savefig(f_name+'_alt_{}.png'.format(x.name),dpi=600,transparent=False)
            fig = self.gui_plotsza()
            print('Saving the SZA vs time plot at:'+f_name+'_sza_{}.png'.format(x.name))
            fig.savefig(f_name+'_sza_{}.png'.format(x.name),dpi=600,transparent=False)
            fig = self.gui_plotaltlat()
            print('Saving the Alt vs Latitude plot at:'+f_name+'_alt_lat_{}.png'.format(x.name))
            fig.savefig(f_name+'_alt_lat_{}.png'.format(x.name),dpi=600,transparent=False)
            labels,main_points = x.get_main_points(combined_distances=distances[i], combined_utc=cmb,combined_names=names,fmt=self.pptx_point_format)
            table = [[mpt['i'],mpt['utc_str'],mpt['wpname'],mpt['deltat_min'],mpt['Comment']] for mpt in main_points]
            table.insert(0,['WP #','UTC [H]','WP Name','Time delta [minutes]','Comments'])
            float_to_hh_mm = lambda float_hours: '{:02d}:{:02d}'.format(int(float_hours), int((float_hours - int(float_hours)) * 60))
            slides.append(dict(title='{}: Take-off {} UTC-> landing {} UTC\nflight time {:2.2}h '.format(x.name,float_to_hh_mm(x.utc[0]),float_to_hh_mm(x.utc[-1]),x.cumlegt[-1]),image_path=f_name+'_alt_{}.png'.format(x.name),
                               table=table,text='Some important points'))
            slides.append(dict(title='Info for: {}'.format(x.name),multiple_images=[f_name+'_sza_{}.png'.format(x.name),f_name+'_alt_lat_{}.png'.format(x.name)])) 
            subtitle += '{}({:2.2f}h T/O@{}UTC) '.format(x.name,x.cumlegt[-1],float_to_hh_mm(x.utc[0]))
        self.return_map(legend,grey_index)
        
        #now save all the figures onto at common powerpoint
        try:
            nul,file_name = path.split(f_name)
            create_generic_pptx(slides,f_name+'.pptx', title="Flight plan for {}\n{} \n {}".format(self.line.ex.datestr,file_name,subtitle),
                                subtitle='Objectives:\n   -\n   -\n   -')
        except Exception as ie:
            tkMessageBox.showwarning('Powerpoint slide saving failed.','Error saving powerpoint.\n{}'.format(ie))
            print('powerpoint slide saving failed. Error:  {}'.format(ie))
       
    def stopandquit(self):
        'function to force a stop and quit the mainloop, future with exit of python'
        self.root.quit()
        self.root.destroy()
        self.line.ex.wb.close()
        #import sys
        #sys.exit()

    def refresh(self,*arg,**karg):
        'function to force a refresh of the plotting window'
        self.line.onfigureenter([1])
        self.refresh_speed()
        #self.line.redraw_pars_mers()
        self.line.get_bg(redraw=True)
        
    def refresh_nospeed(self,*arg,**karg):
        'function to force a refresh of the plotting window'
        self.line.onfigureenter([1])
        #self.line.redraw_pars_mers()
        self.line.get_bg(redraw=True)
        
    def refresh_speed(self):
        ' function to force a refresh on the speed calculations'
        print('Recalculating the speed at each waypoint for {}'.format(self.line.ex.name))
        self.line.ex.force_calcspeed()
        self.line.ex.write_to_excel()
        self.line.ex.calculate()
        self.line.ex.write_to_excel()
    
    def make_gui(self):
        """
        make the gui with buttons
        """
        import tkinter as tk
        self.bopenfile = tk.Button(self.root,text='Open Excel file',
                                   command=self.gui_open_xl)
        self.bsavexl = tk.Button(self.root,text='Save Excel file',
                                 command=self.gui_save_xl)
        self.bsaveas2kml = tk.Button(self.root,text='SaveAs to Kml',
                                   command=self.gui_saveas2kml)
        self.bsave2kml = tk.Button(self.root,text='Update Kml',
                                   command=self.gui_save2kml)
        #self.bsavefig = tk.Button(self.root,text='Save as png',
        #                              command=self.gui_savefig)
        #bmaketext = tk.Button(text='text',command=make_text)
        #bpressed = tk.Button(text='button on',command=make_pressed)
        self.bopenfile.pack()
        self.bsavexl.pack()
        self.bsaveas2kml.pack()
        self.bsave2kml.pack()
        #self.bsavefig.pack()
        tk.Frame(self.root,height=2,width=100,bg='black',relief='sunken').pack(padx=5,pady=5)
        tk.Label(self.root,text='--- Options ---').pack()
        if self.line:
            self.yup = True
            #self.bshowWP = tk.Button(self.root,text='Show Waypoints',
            #                         command=self.bshowpressed)
            self.bplotalt = tk.Button(self.root,text='Plot alt vs time',
                                      command=self.gui_plotalttime)
            self.bplotalt.pack()

        tk.Frame(self.root,height=2,width=100,bg='black',relief='sunken').pack(padx=5,pady=5)    
        tk.Button(self.root,text='Quit',command=self.stopandquit).pack()
        #bpressed.pack()
        #bmaketext.pack()
        self.root.mainloop()

    def gui_addpoint(self):
        'Gui button to add a point via a dialog'
        try:
            from gui import Move_point, ask_option
        except ModuleNotFoundError:
            from .gui import Move_point, ask_option
        try:
            from map_utils import midpoint
        except:
            from .map_utils import midpoint
        r = ask_option(title='Select Option',Text='Select where to put the points',button1='At end',button2='After a\npoint',button3='Between 2\npoints')
        if r.out.get()==0:
            m = Move_point(speed=self.line.ex.speed[-1],pp=self.line.ex.azi[-1])
            self.line.newpoint(m.bear,m.dist)
        elif r.out.get()==1:
            wp_arr = []
            for w in self.line.ex.WP:
                wp_arr.append('WP #%i'%w)
            p0 = Popup_list(wp_arr,title='After which point?',Text='After which point do you want to add ?:',multi=False)
            #print('p0 result ',p0.result[0],p0.result[:],int(p0.result))
            i0 = p0.result
            m = Move_point(speed=self.line.ex.speed[-1],pp=self.line.ex.azi[-1])
            self.line.newpoint(m.bear,m.dist,insert=True,insert_i=i0)        
        else:
            wp_arr = []
            for w in self.line.ex.WP:
                wp_arr.append('WP #%i'%w)
            p = Popup_list(wp_arr,title='Between which points?',Text='Select two points, \nfor adding a central point:',multi=True)
            i_vals = []
            try:
                for pi in p.result:
                    i_vals.append(int(pi)) 
                nul,nul = i_vals[0],i_vals[1]
            except Exception as e:
                import tkinter.messagebox as tkMessageBox
                tkMessageBox.showwarning('Sorry',"Make sure you've selected 2 points: {}".format(e))
            mid_p = midpoint((self.line.ex.lon[i_vals[0]],self.line.ex.lat[i_vals[0]]),(self.line.ex.lon[i_vals[1]],self.line.ex.lat[i_vals[1]]))
            self.line.newpoint(None,None,lat=mid_p[1],lon=mid_p[0],insert=True,insert_i=i_vals[0])     
        self.line.update_labels()
        self.line.draw_canvas()
        

    def gui_movepoints(self):
        'GUI button to move many points at once'
        try:
            from gui import Select_flights,Move_point
        except ModuleNotFoundError:
            from .gui import Select_flights,Move_point
        wp_arr = []
        for w in self.line.ex.WP:
            wp_arr.append('WP #%i'%w)
        try:
            p = Popup_list(wp_arr,title='Move points',Text='Select points to move:',multi=True)
            m = Move_point()
            self.line.moving = True
            for i in p.result:
                self.line.movepoint(i,m.bear,m.dist,last=False)
            self.line.movepoint(0,0,0,last=True)
            self.line.moving = False
        except:
            import tkinter.messagebox as tkMessageBox
            tkMessageBox.showwarning('Sorry','Error occurred unable to move points')
        return
        
    def gui_rotatepoints(self):
        'GUI button to rotate many points at once'
        import tkinter.simpledialog as tkSimpleDialog
        try:
            from gui import Select_flights
        except ModuleNotFoundError:
            from .gui import Select_flights
        wp_arr = []
        for w in self.line.ex.WP:
            wp_arr.append('WP #%i'%w)
        p0 = Popup_list(wp_arr,title='Center rotation point',Text='Select one point to act as center of rotation:',multi=False)
        p = Popup_list(wp_arr,title='Rotate points',Text='Select points to rotate:',multi=True)
        try:
            angle = float(tkSimpleDialog.askstring('Rotation angle','Enter angle of Rotation:'))
        except:
            angle = float(tkSimpleDialog.askstring('Rotation angle','**Invalid number, Please try again**\nEnter angle of Rotation:'))
        if not angle:
            print('Cancelled rotation')
            return
        self.line.moving = True
        # get the rotation point
        lat0,lon0 = self.line.lats[int(p0.result)],self.line.lons[int(p0.result)]
        # rotate agains that center point
        for i in p.result:
        #for i,val in enumerate(p.result):
        #    if val:
            bear,dist = self.line.calc_move_from_rot(i,angle,lat0,lon0)
            self.line.movepoint(i,bear,dist,last=False)
        self.line.movepoint(0,0,0,last=True)
        self.line.moving = False
        
    def gui_addsat(self,label_sep=20):
        'Gui button to add the satellite tracks'
        from tkinter.messagebox import askquestion
        answer = askquestion('Verify import satellite tracks','Do you want to get the satellite tracks from the internet?')
        if answer == 'yes':
            try:
                from map_interactive import load_sat_from_net, get_sat_tracks, plot_sat_tracks
            except ModuleNotFoundError:
                from .map_interactive import load_sat_from_net, get_sat_tracks, plot_sat_tracks
            self.line.tb.set_message('Loading satellite kml File from internet')
            kml = load_sat_from_net()
            if kml:
                self.line.tb.set_message('parsing file...')
                sat = get_sat_tracks(self.line.ex.datestr,kml)
                self.line.tb.set_message('Plotting satellite tracks')
                self.sat_obj = plot_sat_tracks(self.line.m,sat)
        elif answer ==  'no':
            try:
                from map_interactive import load_sat_from_file, get_sat_tracks, plot_sat_tracks
            except ModuleNotFoundError:
                from .map_interactive import load_sat_from_file, get_sat_tracks, plot_sat_tracks
            filename = self.gui_file_select(ext='.kml',ftype=[('All files','*.*'),
                                                         ('Google Earth','*.kml')])
            if not filename:
                print('Cancelled, no file selected')
                return
            self.line.tb.set_message('Opening kml File:'+filename)
            kml = load_sat_from_file(filename)
            self.line.tb.set_message('parsing file...')
            sat = get_sat_tracks(self.line.ex.datestr,kml)
            self.line.tb.set_message('Plotting satellite tracks') 
            if not self.line.large: label_sep = 7
            self.sat_obj = plot_sat_tracks(self.line.m,sat,label_every=label_sep)
        self.line.get_bg()
        
    def dummy_func(self):
        'dummy function that does nothing'
        return

    def gui_addsat_tle(self):
        'Gui button to add the satellite tracks'
        try:
            from map_interactive import get_sat_tracks_from_tle, plot_sat_tracks
        except ModuleNotFoundError:
            from .map_interactive import get_sat_tracks_from_tle, plot_sat_tracks
        self.line.tb.set_message('Loading satellite info from sat.tle file')
        sat = get_sat_tracks_from_tle(self.line.ex.datestr)
        self.line.tb.set_message('Plotting Satellite tracks')
        self.sat_obj = plot_sat_tracks(self.line.m,sat)
        self.line.get_bg(redraw=True)
        self.baddsat.config(text='Remove Sat tracks')
        self.baddsat.config(command=self.gui_rmsat,style='Bp.TButton')
        
    def gui_update_tle(self):
        'GUI button function to update sat.tle'
        try:
            from map_interactive import update_sat_tle_file
        except ModuleNotFoundError:
            from .map_interactive import update_sat_tle_file
        
        try:
            self.gui_rmsat()
        except AttributeError:
            pass
        self.line.tb.set_message('Updating satellite info in sat.tle file...')
        update_sat_tle_file()
        
    def gui_openconfig(self):
        'GUI function to open the config folder with system os'
        import os
        import platform
        folder_path = '.'
        system = platform.system()
        if system == "Windows":
            os.startfile(folder_path)
        elif system == "Darwin":
            os.system("open " + folder_path)
        else:  # Assuming Linux or other POSIX systems
            os.system("xdg-open " + folder_path)
        
        
    def gui_rmsat(self):
        'Gui button to remove the satellite tracks'
        self.line.tb.set_message('Removing satellite tracks')
        try:
            self.sat_obj[-1].set_visible(False)
        except:
            pass
        for s in self.sat_obj:
            if type(s) is list:
                for so in s:
                    so.remove()
            else:
                s.remove()
        self.baddsat.config(text='Add Satellite tracks')
        self.baddsat.config(command=self.gui_addsat_tle,style=self.bg)
        self.line.get_bg(redraw=True)
        self.line.tb.set_message('Finished removing satellite tracks')
        
    def gui_addaeronet(self):
        'Gui function to add the aeronet points on the map, with a colorbar'
        try:
            import aeronet
        except ModuleNotFoundError:
            from . import aeronet
        import tkinter.messagebox as tkMessageBox
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        self.line.tb.set_message('Getting the aeronet files from http://aeronet.gsfc.nasa.gov/')
        latr = [self.line.m.llcrnrlat,self.line.m.urcrnrlat]
        lonr = [self.line.m.llcrnrlon,self.line.m.urcrnrlon]
        aero = aeronet.get_aeronet(daystr=self.line.ex.datestr,lat_range=latr,lon_range=lonr,version='3')
        if not aero:
            self.line.tb.set_message('Failed first attempt at aeronet, trying again')
            aero = aeronet.get_aeronet(daystr=str(datetime.now()-relativedelta(days=1)),lat_range=latr,lon_range=lonr,version='3')
            if not aero:
                tkMessageBox.showwarning('Sorry','Failed to access the aeronet servers or failed to load the files')
                return
        self.line.tb.set_message('Plotting the AOD from aeronet...')
        self.aero_obj = aeronet.plot_aero(self.line.m,aero)
        self.line.get_bg(redraw=True)
        self.baddaeronet.config(text='Remove Aeronet AOD')
        self.baddaeronet.config(command=self.gui_rmaeronet,style='Bp.TButton')
        
    def gui_rmaeronet(self):
        'Gui function to remove the aeronet points on the map'
        self.line.tb.set_message('Removing aeronet AOD values')
        #remove the legend first
        try:
            self.aero_obj[-1].set_visible(False)
        except:
            pass
        try: 
            self.aero_obj.remove()
        except:
            for l in self.aero_obj:
                if type(l) is list:
                    for ll in l:
                        if type(ll) is list:
                            for lll in ll:
                                lll.remove()
                        else:
                            ll.remove()
                else:
                    l.remove()
        self.baddaeronet.config(text='Add current\nAERONET AOD')
        self.baddaeronet.config(command=self.gui_addaeronet,style=self.bg)
        self.line.get_bg(redraw=True)
        self.line.tb.set_message('Finished removing AERONET AOD')
            
        
    def gui_addbocachica(self):
        'GUI handler for adding bocachica foreacast maps to basemap plot'
        import tkinter.messagebox as tkMessageBox
        try:
            filename = self.gui_file_select(ext='.png',ftype=[('All files','*.*'),
                        				  ('PNG','*.png')])
            if not filename:
                print('Cancelled, no file selected')
                return
            print('Opening png File:'+filename)
            img = imread(filename)
        except:
            tkMessageBox.showwarning('Sorry','Loading image file from Bocachica not working...')
            return
        ll_lat,ll_lon,ur_lat,ur_lon = -40.0,-30.0,10.0,40.0
        self.line.addfigure_under(img[42:674,50:1015,:],ll_lat,ll_lon,ur_lat,ur_lon,name=filename)
        #self.line.addfigure_under(img[710:795,35:535,:],ll_lat-7.0,ll_lon,ll_lat-5.0,ur_lon-10.0,outside=True)
        self.baddbocachica.config(text='Remove Forecast\nfrom Bocachica')
        self.baddbocachica.config(command=lambda: self.gui_rmbocachica(filename),style='Bp.TButton')
        
    def gui_rmbocachica(self,name):
        'GUI handler for removing the bocachica forecast image'
        self.line.tb.set_message('Removing bocachica figure under')
        try:
            self.line.m.figure_under[name].remove()
        except:
            for f in self.line.m.figure_under[name]:
                f.remove()
        self.baddbocachica.config(text='Add Forecast\nfrom Bocachica')
        self.baddbocachica.config(command=self.gui_addbocachica,style=self.bg)
        self.line.get_bg(redraw=True)
        
    def gui_addtidbit(self):
        'GUI handler for adding tropical tidbit foreacast maps to basemap plot'
        import tkinter.messagebox as tkMessageBox
        import cartopy.crs as ccrs
        try:
            from load_utils import load_from_json
        except ModuleNotFoundError:
            from .load_utils import load_from_json
        import os
        try:
            filename = self.gui_file_select(ext='.png',ftype=[('All files','*.*'),
                        				  ('PNG','*.png')])
            if not filename:
                print('Cancelled, no file selected')
                return
            print('Opening png File:'+filename)
            img = imread(filename)
        except Exception as e:
            tkMessageBox.showwarning('Sorry','Loading image file from Tropical tidbits not working...'+e)
            return
        try:
            regions = load_from_json(os.path.join('.','image_corners_tidbits.json'))
        except IOError:
            try:
                from gui import gui_file_select_fx
            except ModuleNotFoundError:
                from .gui import gui_file_select_fx
            fname = gui_file_select_fx(ext='*.json',ftype=[('All files','*.*'),('JSON corner for regions','*.json')])
            regions = load_from_json(fname)
        except Exception as ei:
            print(' ...using internal corner definitions for Tropical Tidbits')
            print(ei)
            regions = {'CONUS':[18.94,-130.38,57.54,-59.35],
                         'Eastern US':[21.25,-106.64,51.73,-57.46],
                         'North-Central US':[35.61,-105.95,51.94,-76.48],
                         'South-Central US':[24.53,-111.95,43.06,-83.53],
                         'Northeast US':[34.65,-87.84,48.83,-62.72],
                         'Southeast US':[21.51,-99.08,41.20,-67.36],
                         'Northwest US':[37.55,-136.31,56.20,-98.08],
                         'Southwest US':[27.52,-132.12,46.20,-99.32],
                         'Western US':[24.29,-136.69,51.78,-87.48],
                         'North Atlantic':[-1.83,-113.85,69.60,5.10],
                         'Western Atlantic':[3.97,-107.04,42.52,-46.95],
                         'Tropical Atlantic':[3.87,-77.25,42.80,11.68],
                         'Western Pacific':[-1.85,85.88,69.64,-153.85],
                         'Central Pacific':[-1.15,167.75,37.83,-126.64],
                         'Eastern Pacific':[-1.15,-142.25,37.90,-76.64]
                         }
        reg_list = list(regions.keys())
        p0 = Popup_list(reg_list,title='Which Region?',Text='Select the region of the figure:',multi=False)
        source_proj = False
        if reg_list[p0.result] in list(regions.keys()):
            out_reg = regions[reg_list[p0.result]]
            if len(out_reg)<5:
                ll_lat,ll_lon,ur_lat,ur_lon = out_reg 
            else:
                region_data = out_reg
                if isinstance(region_data, dict):
                    # Dictionary format
                    ll_lat,ll_lon,ur_lat,ur_lon = region_data['ll_lat'],region_data['ll_lon'],region_data['ur_lat'],region_data['ur_lon']
                    source_proj = region_data.get('projection', None)
                    coords_are_geographic = region_data.get('coordinates_are_geographic', True)
                    debug = region_data.get('debug',self.debug)
                else:
                    # List format: [ll_lat, ll_lon, ur_lat, ur_lon, proj_info]
                    ll_lat, ll_lon, ur_lat, ur_lon = region_data[:4]
                    source_proj = region_data[4] if len(region_data) > 4 else None
                    coords_are_geographic = region_data[5] if len(region_data) > 5 else True
        transform_crs = ccrs.PlateCarree()
        if source_proj and not coords_are_geographic:
            transform_crs = self._parse_projection(source_proj)
        #ll_lat,ll_lon,ur_lat,ur_lon = regions[reg_list[p0.result]]
        #ll_lat,ll_lon,ur_lat,ur_lon = 21.22,-106.64,51.70,-57.46
        self.line.addfigure_under(img,ll_lat,ll_lon,ur_lat,ur_lon,name=filename,text=filename,transform=transform_crs,debug=debug)
        #self.line.addfigure_under(img[710:795,35:535,:],ll_lat-7.0,ll_lon,ll_lat-5.0,ur_lon-10.0,outside=True)
        self.baddtidbit.config(text='Remove Tropical tidbit')
        self.baddtidbit.config(command=lambda: self.gui_rmtidbit(filename),style='Bp.TButton')
        
    def gui_rmtidbit(self,name):
        'GUI handler for removing the tropical tidbit forecast image'
        self.line.tb.set_message('Removing Tropical tidbit figure under')
        try:
            self.line.m.figure_under[name].remove()
        except:
            for f in self.line.m.figure_under[name]:
                f.remove()
        try:
            self.line.m.figure_under_text[name].remove()
        except:
            try:
                for f in self.line.m.figure_under_text[name]:
                    try:
                        f.remove  
                    except TypeError:
                        pass
            except AttributeError:
                pass
        self.baddtidbit.config(text='Add Tropical tidbit')
        self.baddtidbit.config(command=self.gui_addtidbit,style=self.bg)
        self.line.get_bg(redraw=True)
        
    def gui_addtrajectory(self):
        'GUI handler for adding bocachica foreacast maps to basemap plot'
        import tkinter.messagebox as tkMessageBox
        try:
            filename = self.gui_file_select(ext='.png',ftype=[('All files','*.*'),
                        				  ('PNG','*.png')])
            if not filename:
                print('Cancelled, no file selected')
                return
            print('Opening png File:'+filename)
            img = imread(filename)
        except:
            tkMessageBox.showwarning('Sorry','Loading image file from Bocachica not working...')
            return
        ll_lat,ll_lon,ur_lat,ur_lon = -59.392,-47.46,26.785,47.5
        self.line.addfigure_under(img,ll_lat,ll_lon,ur_lat,ur_lon,name=filename)
        #self.line.addfigure_under(img[710:795,35:535,:],ll_lat-7.0,ll_lon,ll_lat-5.0,ur_lon-10.0,outside=True)
        self.baddtrajectory.config(text='Remove trajectory\nImage')
        self.baddtrajectory.config(command=lambda: self.gui_rmtrajectory(filename),style='Bp.TButton')
        
    def gui_rmtrajectory(self,name):
        'GUI handler for removing the bocachica forecast image'
        self.line.tb.set_message('Removing trajectory figure under')
        try:
            self.line.m.figure_under[name].remove()
        except:
            for f in self.line.m.figure_under[name]:
                f.remove()
        self.baddtrajectory.config(text='Add Trajectory\nImage')
        self.baddtrajectory.config(command=self.gui_addtrajectory,style=self.bg)
        self.line.get_bg(redraw=True)

    def gui_addfigure(self,ll_lat=None,ll_lon=None,ur_lat=None,ur_lon=None,source_proj=None,coords_are_geographic=True,debug=False):
        'GUI handler for adding figures forecast maps to basemap plot'
        import tkinter.simpledialog as tkSimpleDialog
        import tkinter.messagebox as tkMessageBox
        import os
        import numpy as np
        import cartopy.crs as ccrs
        
        try:
            from load_utils import load_from_json
        except ModuleNotFoundError:
            from .load_utils import load_from_json
        try:
            from PIL import Image
            filename = self.gui_file_select(ext='.png',ftype=[('All files','*.*'),
                                                ('PNG','*.png'),('JPEG','*.jpg'),('GIF','*.gif')])
            if not filename:
                print('Cancelled, no file selected')
                return
            print('Opening png File: %s' %filename)
            #img = Image.open(filename)
            img = imread(filename)
            if debug: print('... opened')
        except Exception as ei:
            tkMessageBox.showwarning('Sorry',f'Error occurred unable to load file: \n{ei}')
            return
        # load the defined regions    
        try:
            regions = load_from_json(os.path.join('.','image_corners.json'))
        except IOError:
            try:
                from gui import gui_file_select_fx
            except ModuleNotFoundError:
                from .gui import gui_file_select_fx
            fname = gui_file_select_fx(ext='*.json',ftype=[('All files','*.*'),('JSON corner for regions','*.json')])
            regions = load_from_json(fname)
        except Exception as ej:
            tkMessageBox.showwarning('Sorry',f'Error occurred unable to load image_corners json file: \n{ej}')
            return
            
        try:
            reg_list = list(regions.keys())
            reg_list.append('manual')
            p0 = Popup_list(reg_list,title='Which Region?',Text='Select the region of the figure:',multi=False)
            print('... Selected image corners for: {}'.format(reg_list[p0.result]))
            if reg_list[p0.result] in list(regions.keys()):
                out_reg = regions[reg_list[p0.result]]
                if len(out_reg)<5:
                    ll_lat,ll_lon,ur_lat,ur_lon = out_reg 
                else:
                    region_data = out_reg
                    if isinstance(region_data, dict):
                        # Dictionary format
                        ll_lat,ll_lon,ur_lat,ur_lon = region_data['ll_lat'],region_data['ll_lon'],region_data['ur_lat'],region_data['ur_lon']
                        source_proj = region_data.get('projection', None)
                        coords_are_geographic = region_data.get('coordinates_are_geographic', True)
                        debug = region_data.get('debug',debug)
                    else:
                        # List format: [ll_lat, ll_lon, ur_lat, ur_lon, proj_info]
                        ll_lat, ll_lon, ur_lat, ur_lon = region_data[:4]
                        source_proj = region_data[4] if len(region_data) > 4 else None
                        coords_are_geographic = region_data[5] if len(region_data) > 5 else True
        except Exception as ei:
            print(f' ...error with image_corners.json, using the manual image selection: {ei}')
            ll_lat,source_proj = None,None

        if not ll_lat: # manual corner selection
            dialog_result = get_coordinates_and_projection() # The dialog replaces all those individual tkSimpleDialog calls
            if dialog_result:
                coords = dialog_result['coordinates']
                ll_lat,ll_lon,ur_lat,ur_lon = coords['ll_lat'],coords['ll_lon'],coords['ur_lat'],coords['ur_lon'] 
                coords_are_geographic = dialog_result['coordinates_are_geographic']
                projection = dialog_result['projection']
                print(f'...Adding manual image corners: LL({ll_lat},{ll_lon}) UR({ur_lat},{ur_lon}), in geographic: {coords_are_geographic}, with projection: {projection}')
                debug=True
                   
        fpath = os.path.split(filename)
        transform_crs = ccrs.PlateCarree()
        if source_proj and not coords_are_geographic:
            transform_crs = self._parse_projection(source_proj)
            
        self.line.addfigure_under(img,ll_lat,ll_lon,ur_lat,ur_lon,name=fpath[1],transform=transform_crs,text=fpath[1],debug=debug)
        self.baddfigure.config(text='Remove image')
        self.baddfigure.config(command=lambda: self.gui_rmfigure(fpath[1]),style='Bp.TButton')
        
    def _parse_projection(self, proj_info):
        """Parse projection information and return cartopy CRS object"""
        import cartopy.crs as ccrs
        import inspect
        import tkinter.messagebox as tkMessageBox
        if isinstance(proj_info, str):
            # Handle string-based projection definitions
            try:
                return ccrs.__dict__[proj_info]()
                
            except:                     
                if proj_info.lower() == 'platecarree' or proj_info.lower() == 'geographic':
                    return ccrs.PlateCarree()
                elif proj_info.lower() == 'mercator':
                    return ccrs.Mercator()
                elif proj_info.lower().startswith('utm'):
                    # Extract zone number from string like 'utm_33n'
                    zone = int(proj_info.split('_')[1][:-1])
                    southern = proj_info.split('_')[1][-1].lower() == 's'
                    return ccrs.UTM(zone=zone, southern_hemisphere=southern)
                elif proj_info.lower() == 'lambert_conformal' or proj_info.lower() == 'lambertconformal':
                    return ccrs.LambertConformal()
                elif proj_info.lower() == 'lambert_azimuthal_equal_area' or proj_info.lower() == 'lambertazimuthalequalarea':
                    return ccrs.LambertAzimuthalEqualArea()
                # Add more projections as needed
                else:
                    tkMessageBox.showwarning('Bad projection name',f'The projection defined as {proj_info} does not match any available ccrs definition.')
            
        elif isinstance(proj_info, dict):
            # Handle dictionary-based projection definitions
            try:
                return_ccrs = ccrs.__dict__[proj_info.get('type', '')]
                sig = inspect.signature (return_ccrs.__init__)
                kwargs = {}
                for param_name,param in sig.parameters.items():
                    if param_name=='self': continue
                    if param.default != sig.empty:
                        kwargs[param_name] = proj_info.get(param_name,param.default)
                    else:
                        kwargs[param_name] = proj_info.get(param_name,-999)
                        if kwargs[param_name] == -999:
                            tkMessageBox.showwarning('Bad projection definition',f'The projection defined as {return_ccrs} is missing the parameter named: {param_name}')
                return return_ccrs(**kwargs)
            except Exception as ei:
                print(f' *** Error getting the projection of the image, error: {ei} ***')
                proj_type = proj_info.get('type', '').lower()
                
                if proj_type == 'platecarree':
                    return ccrs.PlateCarree(
                        central_longitude=proj_info.get('central_longitude', 0))
                elif proj_type == 'stereographic':
                    return ccrs.Stereographic(
                        central_latitude=proj_info.get('central_latitude', 90),
                        central_longitude=proj_info.get('central_longitude', 0))
                elif proj_type == 'lambert_conformal' or proj_type == 'lambertconformal':
                    return ccrs.LambertConformal(
                        central_latitude=proj_info.get('central_latitude', 39),
                        central_longitude=proj_info.get('central_longitude', -96),
                        standard_parallels=proj_info.get('standard_parallels', (33, 45)))
                elif proj_type == 'lambert_azimuthal_equal_area' or proj_type == 'lambertazimuthalequalarea':
                    return ccrs.LambertAzimuthalEqualArea(
                        central_latitude=proj_info.get('central_latitude', 0),
                        central_longitude=proj_info.get('central_longitude', 0),
                        false_easting=proj_info.get('false_easting', 0),
                        false_northing=proj_info.get('false_northing', 0),
                        globe=proj_info.get('globe_radius', None))
                elif proj_type == 'utm':
                    return ccrs.UTM(
                        zone=proj_info.get('zone', 33),
                        southern_hemisphere=proj_info.get('southern_hemisphere', False))
                else:
                    tkMessageBox.showwarning('Bad projection name',f'The projection defined as {proj_type} does not match any available ccrs definition.')
            # Add more dictionary-based projections as needed
    
        return None    
    
    def _transform_corners_from_geographic(self, ll_lat, ll_lon, ur_lat, ur_lon, target_crs):
        """Transform corner coordinates from geographic (lat/lon) to target projection"""
        import cartopy.crs as ccrs
        
        # Transform from geographic coordinates to target projection
        ll_x, ll_y = target_crs.transform_point(ll_lon, ll_lat, ccrs.PlateCarree())
        ur_x, ur_y = target_crs.transform_point(ur_lon, ur_lat, ccrs.PlateCarree())
        
        # Convert back to lat/lon if needed (depending on your addfigure_under implementation)
        if hasattr(target_crs, 'transform_point'):
            # If your system expects lat/lon, transform back to geographic
            ll_lat_new, ll_lon_new = ccrs.PlateCarree().transform_point(ll_x, ll_y, target_crs)
            ur_lat_new, ur_lon_new = ccrs.PlateCarree().transform_point(ur_x, ur_y, target_crs)
            return ll_lat_new, ll_lon_new, ur_lat_new, ur_lon_new
        else:
            # Return projected coordinates directly
            return ll_y, ll_x, ur_y, ur_x  # Note: might need to swap x,y depending on convention


    def _transform_corners_projection_to_projection(self, ll_x, ll_y, ur_x, ur_y, source_crs, target_crs):
        """Transform corner coordinates from source projection units to target projection"""
        import cartopy.crs as ccrs
        
        # Transform from source projection to target projection
        ll_x_new, ll_y_new = target_crs.transform_point(ll_x, ll_y, source_crs)
        ur_x_new, ur_y_new = target_crs.transform_point(ur_x, ur_y, source_crs)
        
        # Convert back to lat/lon if needed (depending on your addfigure_under implementation)
        if hasattr(target_crs, 'transform_point'):
            # If your system expects lat/lon, transform to geographic
            ll_lat_new, ll_lon_new = ccrs.PlateCarree().transform_point(ll_x_new, ll_y_new, target_crs)
            ur_lat_new, ur_lon_new = ccrs.PlateCarree().transform_point(ur_x_new, ur_y_new, target_crs)
            return ll_lat_new, ll_lon_new, ur_lat_new, ur_lon_new
        else:
            # Return projected coordinates directly
            return ll_y_new, ll_x_new, ur_y_new, ur_x_new
    def _detect_coordinate_type(self, ll_val, ll_val2, ur_val, ur_val2, source_crs=None):
        """
        Automatically detect if coordinates are geographic (lat/lon) or projection units
        Returns True if coordinates appear to be geographic, False if projection units
        """
        import cartopy.crs as ccrs
        
        # Check for obvious geographic coordinate ranges
        if (-90 <= ll_val <= 90 and -90 <= ur_val <= 90 and 
            -180 <= ll_val2 <= 180 and -180 <= ur_val2 <= 180):
            # Values are within geographic bounds
            if source_crs and not isinstance(source_crs, ccrs.PlateCarree):
                # If we have a non-geographic projection but values are in geo range,
                # they could be either - use additional heuristics
                
                # Check if the values make sense for the projection
                if isinstance(source_crs, (ccrs.UTM, ccrs.Mercator)):
                    # UTM/Mercator typically have much larger coordinate values
                    if (abs(ll_val) < 100 and abs(ll_val2) < 100 and 
                        abs(ur_val) < 100 and abs(ur_val2) < 100):
                        return True  # Likely geographic
                    else:
                        return False  # Likely projection units
                
                # For other projections, assume geographic if in valid range
                return True
            else:
                # No projection specified or PlateCarree, assume geographic
                return True
        else:
            # Values outside geographic bounds, must be projection units
            return False


    def _transform_corners(self, ll_lat, ll_lon, ur_lat, ur_lon, source_crs, target_crs):
        """Legacy method - kept for backward compatibility"""
        return self._transform_corners_projection_to_projection(ll_lat, ll_lon, ur_lat, ur_lon, source_crs, target_crs)

    
    
    def gui_rmfigure(self,name):
        'GUI handler for removing the forecast image'
        self.line.tb.set_message('Removing figure under')
        try:
            self.line.m.figure_under[name].remove()
        except:
            for f in self.line.m.figure_under[name]:
                f.remove()
        try:
            self.line.m.figure_under_text[name].remove()
        except:
            try:
                for f in self.line.m.figure_under_text[name]:
                    try:
                        f.remove  
                    except TypeError:
                        pass
            except AttributeError:
                pass
        self.baddfigure.config(text='Add image',command=self.gui_addfigure,style=self.bg)
        self.line.get_bg(redraw=True)
        
    def gui_addgeos(self):
        'wrapper for the add wms function, specifically for GEOS'
        img,label,img_leg = self.add_WMS(website='http://wms.gsfc.nasa.gov/cgi-bin/wms.cgi?project=GEOS.fp.fcst.inst1_2d_hwl_Nx')
        if img:
            r = self.add_wms_images(img,img_leg,name='GEOS',text=label)
            if r:
                self.baddgeos.config(text='Remove GEOS Forecast')
                self.baddgeos.config(command=self.gui_rmgeos,style='Bp.TButton')
            
    def gui_add_any_WMS(self,filename='WMS.txt'):
        'Button to add any WMS layer defined in a WMS txt file, each line has name of server, then the website'
        try:
            from map_interactive import load_WMS_file
        except ModuleNotFoundError:
            from .map_interactive import load_WMS_file
        out = load_WMS_file(filename)
        arr = ['{} : {}'.format(dict['name'],dict['website']) for dict in out]
        popup = Popup_list(arr,title='Select WMS server to load graphics capabilities')
        i = popup.var.get()
        self.line.tb.set_message('Selected WMS server: {}'.format(out[i]['name']))
        img,label,img_leg = self.add_WMS(website=out[i]['website'],printurl=True,notime=out[i]['notime'])
        if img:
            if 'epsg3413' in out[i]['website']:
                import cartopy.crs as ccrs
                tr = ccrs.epsg(3413)
            else:
                tr = None
            r = self.add_wms_images(img,img_leg,name='WMS',text=label,transform=tr)
            if r:
                self.wmsname = out[i]['name']
                self.baddwms.config(text='Remove WMS: {}'.format(out[i]['name']))
                self.baddwms.config(command=lambda: self.gui_rm_wms('WMS'),style='Bp.TButton')
                
    def gui_add_MSS(self,filename='MSS.txt'):
        'Button to add MSS model layers defined in a MSS txt file, each line has name of server, then the website, nearly same as WMS, but with mss projections'
        try:
            from map_interactive import load_WMS_file
        except ModuleNotFoundError:
            from .map_interactive import load_WMS_file
        out = load_WMS_file(filename)
        arr = ['{} : {}'.format(dict['name'],dict['website']) for dict in out]
        popup = Popup_list(arr,title='Select WMS server to load graphics capabilities')
        i = popup.var.get()
        self.line.tb.set_message('Selected WMS server: {}'.format(out[i]['name']))
        bbo0 = self.line.m.convert_latlon(self.line.m.llcrnrlon,self.line.m.llcrnrlat)
        bbo1 = self.line.m.convert_latlon(self.line.m.urcrnrlon,self.line.m.urcrnrlat)      
        bbox = (bbo0[0],bbo0[1],bbo1[0],bbo1[1])
        img,label,img_leg = self.add_WMS(website=out[i]['website'],printurl=True,notime=out[i]['notime'],mss_crs=True,bbox=bbox)
        if img:
            transform = self.line.m.proj
            #if self.line.m.usestereformss: transform = self.line.m.usestereformss
            r = self.add_wms_images(img,img_leg,name='MSS',text=label,transform=transform)
            if r:
                self.wmsname = out[i]['name']
                self.baddmss.config(text='Remove MSS: {}'.format(out[i]['name']))
                self.baddmss.config(command=self.gui_rm_mss,style='Bp.TButton')
            
    def gui_add_SUA_WMS(self):
        'Button to add Special Use Airspace WMS layer'
        import tkinter.messagebox as tkMessageBox
        tkMessageBox.showwarning('SUA for US only','Special Use Airspace for US only')
        img,label,img_leg = self.add_WMS(website='https://sua.faa.gov/geoserver/wms?LAYERS=SUA',
                         printurl=True,notime=True,popup=False,
                         cql_filter='low_altitude<240',hires=True)
        if img:
            r = self.add_wms_images(img,img_leg,name='SUA',alpha=0.5,text=label)
            if r:
                self.baddsua.config(text='Remove SUA')
                self.baddsua.config(command=self.gui_rm_SUA_WMS,style='Bp.TButton')
            
    def gui_add_kml(self):
        'Button function to add any kml/kmz file'
        r = self.add_kml()
        
        if r:
            self.baddkml.config(text='Remove KML/KMZ')
            self.baddkml.config(command=self.gui_rm_kml,style='Bp.TButton')
            
    def gui_add_FIR(self):
        'Button function to add FIR boundaries from kmz file'
        import os
        r = self.add_kml(fname=os.path.join('.','firs.kmz'),name='FIR')
        
        if r:
            self.baddfir.config(text='Remove FIR boundaries')
            self.baddfir.config(command=self.gui_rm_fir,style='Bp.TButton')
            
    def gui_add_NATS(self,color='tan'):
        'Button function to add NATS tracks'
        try:
            from flightnav_utils import get_NATs
        except ModuleNotFoundError:
            from .flightnav_utils import get_NATs 
        try:
            from map_interactive import plot_tracks
        except ModuleNotFoundError:
            from .map_interactive import plot_tracks
        self.line.tb.set_message('Adding North-Atlantic tracks')    
        tracks = get_NATs()
        self.nats = plot_tracks(tracks,self.line.m,color=color)
        
        if tracks:
            self.baddnats.config(text='Remove NAT routes')
            self.baddnats.config(command=self.gui_rm_nat,style='Bp.TButton')
            self.line.get_bg(redraw=True)
            
    def gui_add_POCATS(self,color='tan'):
        'Button function to add POCATS tracks'
        try:
            from flightnav_utils import get_POCATS
        except ModuleNotFoundError:
            from .flightnav_utils import get_POCATS
        try:
            from map_interactive import plot_tracks
        except ModuleNotFoundError:
            from .map_interactive import plot_tracks
        self.line.tb.set_message('Adding Pacific-Oceanic tracks')
        tracks = get_POCATS()
        self.pocats = plot_tracks(tracks,self.line.m,color=color)    
       
        if tracks:
            self.baddpocats.config(text='Remove POCATS routes')
            self.baddpocats.config(command=self.gui_rm_pocat,style='Bp.TButton')
            self.line.get_bg(redraw=True)
            
    def gui_rm_nat(self):        
        'removing the NATS tracks'
        
        try:
            nul = [n.set_visible(False) for n in self.nats]
        except:
            pass
        for s in self.nats:
            if type(s) is list:
                for so in s:
                    so.remove()
            else:
                s.remove()
        
        self.baddnats.config(text='North Atlantic routes')
        self.baddnats.config(command=self.gui_add_NATS,style=self.bg)
        self.line.get_bg(redraw=True)
        
    def gui_rm_pocat(self):        
        'removing the POCATS tracks'
        
        try:
            nul = [n.set_visible(False) for n in self.pocats]
        except:
            pass
        for s in self.pocats:
            if type(s) is list:
                for so in s:
                    so.remove()
            else:
                s.remove()
        
        self.baddpocats.config(text='Pacific-Oceanic routes')
        self.baddpocats.config(command=self.gui_add_POCATS,style=self.bg)
        self.line.get_bg(redraw=True)
            
    def gui_rm_fir(self):
        'Gui button to remove the satellite tracks'
        self.line.tb.set_message('Removing FIR')
        try:
            self.FIR[-1].set_visible(False)
        except:
            pass
        for s in self.FIR:
            if type(s) is list:
                for so in s:
                    so.remove()
            else:
                s.remove()
        self.baddfir.config(text='FIR boundaries')
        self.baddfir.config(command=self.gui_add_FIR,style=self.bg)
        self.line.get_bg(redraw=True)
            
    def add_kml(self,fname=None,color='tab:pink',name='kmls'):
        'function to add kml'
        import tkinter.messagebox as tkMessageBox
        try:
            from map_interactive import plot_kml
        except ModuleNotFoundError:
            from .map_interactive import plot_kml
        if not fname:
            fname = self.gui_file_select(ext='.kml',ftype=[('All files','*.*'),
                                                          ('KML','*.kml'),('KMZ','*.kmz')])
        try:
            self.line.tb.set_message('Adding kml file:{}'.format(fname))
            self.__dict__[name] = plot_kml(fname,self.line.m,color=color)
            return True
        except Exception as ei:
            print(' *** Issue adding the kml file: {} - {}'.format(fname,ei))
            self.line.tb.set_message('Problem with kml file:{}'.format(fname))
            tkMessageBox.showwarning('Problem adding kml',f'Issue adding the kml file: {fname} - {ei}')
            return False
           
    def gui_rm_kml(self,name='kmls'):
        'Gui button to remove the satellite tracks'
        self.line.tb.set_message('Removing KML/KMZ')
        try:
            self.kmls[-1].set_visible(False)
        except:
            pass
        for s in self.kmls:
            if type(s) is list:
                for so in s:
                    so.remove()
            else:
                s.remove()
        self.baddkml.config(text='Add KML/KMZ')
        self.baddkml.config(command=self.gui_add_kml,style=self.bg)
        self.line.get_bg(redraw=True)
            
    def add_WMS(self,website='http://wms.gsfc.nasa.gov/cgi-bin/wms.cgi?project=GEOS.fp.fcst.inst1_2d_hwl_Nx',
                printurl=False,notime=False,popup=False,cql_filter=None,hires=False,
                vert_crs=False,mss_crs=False,xlim=None,ylim=None,bbox=None,**kwargs): #GEOS.fp.fcst.inst1_2d_hwl_Nx'):
        'GUI handler for adding the figures from WMS support of GEOS'
        try:
            from gui import Popup_list,inittime_sel_fx
            from map_interactive import convert_ccrs_to_epsg, get_center_lonlat
        except ModuleNotFoundError:
            from .gui import Popup_list,inittime_sel_fx
            from .map_interactive import convert_ccrs_to_epsg, get_center_lonlat
        
        import tkinter.messagebox as tkMessageBox
        import cartopy.crs as ccrs
        from datetime import datetime, timedelta
        if hires:
            res = (2160,1680)
        else:
            res = (1080,720)
        #self.line.m.usestereformss = False
        if popup:
            tkMessageBox.showwarning('Downloading from internet','Trying to load data from {}\n with most current model/measurements'.format(website.split('/')[2]))
        self.root.config(cursor='exchange')
        self.root.update()
        
        use_init_time_fx = any([mss_crs,vert_crs]) #use init time function if using the MSS
        
        # Get capabilities
        try: 
            from owslib.wms import WebMapService
            from owslib.util import openURL
            from io import StringIO,BytesIO
            from PIL import Image
            print('Loading WMS from :'+website.split('/')[2])
            self.line.tb.set_message('Loading WMS from :'+website.split('/')[2])
            wms = WebMapService(website)
            cont = list(wms.contents)
        except Exception as ie:
            print(ie)
            self.root.config(cursor='')
            tkMessageBox.showwarning('Sorry','Loading WMS map file from '+website.split('/')[2]+' servers not working...')
            return False, None, False
        titles = [wms[c].title for c in cont]
        arr = [x.split('-')[-1]+':  '+y for x,y in zip(cont,titles)]
        arrs = arr
        if mss_crs:
            #take out the vertical and line plots from MSS
            i_maps = [i for i,m in enumerate(cont) if ('.VS' not in m) and ('.LS' not in m)]
            arrs = [arr[i] for i in i_maps]
        elif vert_crs:
            i_maps = [i for i,m in enumerate(cont) if '.VS' in m]
            arrs = [arr[i] for i in i_maps]
        self.root.config(cursor='')
        popup = Popup_list(arrs)
        ii = popup.var.get()
        if any([mss_crs,vert_crs]): 
            i = i_maps[ii]
        else:
            i = ii
        wms_layer_title = titles[i].split(',')[-1]
        self.line.tb.set_message('Selected WMS map: '+wms_layer_title)
        print('Selected WMS map: '+wms_layer_title)
        
        self.root.config(cursor='exchange')
        self.root.update()
        
        if wms[cont[i]].timepositions:
            times = wms[cont[i]].timepositions
            jpop = Popup_list(times,title='Select Valid Times')
            time_sel = times[jpop.var.get()].strip()
            if '/' in time_sel:
                tss = time_sel.split('/')
                time_sel = tss[1] 
                try:
                    import dateutil.parser
                    begin_time = dateutil.parser.parse(tss[0])
                    end_time = dateutil.parser.parse(tss[1])
                    plan_time = dateutil.parser.parse(self.line.ex.datestr)
                    if (plan_time>begin_time) & (plan_time<end_time):
                        time_sel = self.line.ex.datestr+'T12:00:00Z'
                    elif plan_time>end_time:
                        time_sel = tss[1]
                    elif plan_time<begin_time:
                        time_sel = tss[0]
                    print('Selected time span:{}'.format(time_sel))
                except:
                    pass
        else:
            time_sel = None
        if not time_sel:
            time_sel = datetime.now().strftime('%Y-%m-%d')+'T12:00'
            if 'gibs.earthdata' in website:
                time_sel = datetime.now().strftime('%Y-%m-%d')
        if notime:
            time_sel = None
                       
        if wms[cont[i]].elevations:
            elevations = wms[cont[i]].elevations
            jpop = Popup_list(elevations,title='Select Valid Elevations')
            elev_sel = elevations[jpop.var.get()]
            kwargs['elevation'] = elev_sel
        else:
            elev_sel = None
            
        if wms[cont[i]].crsOptions:
            #print('building the ccrs')
            ccrs_val = convert_ccrs_to_epsg(self.line.m.proj_name)
            ccrs_str = '{}'.format(ccrs_val)
            crss = wms[cont[i]].crsOptions
            if vert_crs: ccrs_str = 'VERT'
            srss = [c for c in crss if c.find(ccrs_str)>-1]
            if mss_crs: 
                if 'stere' in self.line.m.proj_name.lower():
                    srss = ['mss:stere,{0},{1},{1}'.format(*get_center_lonlat(self.line.m.proj))]
                if 'lambertazi' in self.line.m.proj_name.lower():
                    lon0,lat0 = get_center_lonlat(self.line.m.proj)
                    #self.line.m.usestereformss = ccrs.NorthPolarStereo(central_longitude=lon0,true_scale_latitude=lat0)
                    srss = ['mss:laea,{0},{1}'.format(*get_center_lonlat(self.line.m.proj))]
            if len(srss)>0:
                srs = srss[0]
            else:
                kpop = Popup_list(crss,title='No matching EPSG values, please select')
                srs = crss[kpop.var.get()]
                bbox_in = bbox
                try:
                    ccrs_val = int(srs.split(':')[1])
                    tr_init = ccrs.epsg(ccrs_val)
                    xlim_tr,ylim_tr = tr_init.transform_points([self.line.m.llcrnrlon,self.line.m.urcrnrlon],[self.line.m.llcrnrlat,self.line.m.urcrnrlat],self.line.m.proj,)
                    bbox = (xlim_tr[0],ylim_tr[0],xlim_tr[1],ylim_tr[1])
                except:
                    bbox = bbox_in
                    pass
        else:
            srs = 'epsg:4326'
            
        if wms[cont[i]].styles:
            style = [k+':'+wms[cont[i]].styles[k]['title'] for k in wms[cont[i]].styles]
            style_list = [k for k in wms[cont[i]].styles]
            if len(style_list)<2:
                style_sel = style_list[0]
            else:
                jpop = Popup_list(style,title='Select Style')
                style_sel = style_list[jpop.var.get()].strip()
            kwargs['styles'] = [style_sel]
        try:
            if use_init_time_fx:
                inittime_sel = inittime_sel_fx(wms.getServiceXML(),cont[i],time_sel)
                if len(inittime_sel) > 1:
                    inittime_sels = inittime_sel
                    if not vert_crs:
                        # check which init time works:
                        print('...verifying init times')
                        inittime_sels = []
                        for i_init, dim_init in enumerate(inittime_sel):
                            try:
                                nul = wms.getmap(layers=[cont[i]],style='default',bbox=[0,0,1,1],size=(1,1),transparent=True,time=time_sel,srs=srs,format='image/png',dim_init_time=dim_init,CQL_filter=cql_filter,**kwargs)
                            except:
                                nul = None
                                pass
                            if nul:
                                inittime_sels.append(dim_init)
                    if len(inittime_sels) > 1:
                        jpop = Popup_list(inittime_sels,title='Select INIT_TIME')
                        inittime_sel_1 = inittime_sels[jpop.var.get()]
                        inittime_sel = [inittime_sel_1]
            else:
                inittime_sel = [datetime.now().strftime('%Y-%m-%d')+'T18:00Z',
                            datetime.now().strftime('%Y-%m-%d')+'T12:00Z', 
                            datetime.now().strftime('%Y-%m-%d')+'T06:00Z',
                            datetime.now().strftime('%Y-%m-%d')+'T00:00Z',
                            (datetime.now()- timedelta(days = 1)).strftime('%Y-%m-%d')+'T18:00Z',
                            (datetime.now()- timedelta(days = 1)).strftime('%Y-%m-%d')+'T12:00Z',
                            (datetime.now()- timedelta(days = 1)).strftime('%Y-%m-%d')+'T06:00Z',
                            (datetime.now()- timedelta(days = 1)).strftime('%Y-%m-%d')+'T00:00Z',
                            time_sel]

            label = '{}: {}[{}]\n {}'.format(cont[i],wms_layer_title,kwargs.get('styles',['default'])[0],time_sel)
            if elev_sel:
                label = label+', z:{}'.format(elev_sel)
            #ylim = self.line.line.axes.get_ylim()
            #xlim = self.line.line.axes.get_xlim()
            if not ylim: ylim = self.line.m.llcrnrlat,self.line.m.urcrnrlat
            if not xlim: xlim = self.line.m.llcrnrlon,self.line.m.urcrnrlon
        except:
            self.root.config(cursor='')
            self.root.update()
            tkMessageBox.showwarning('Sorry','Problem getting the limits and time of the image')
            return False, None, False
        if not bbox: bbox = (xlim[0],ylim[0],xlim[1],ylim[1])
        #import ipdb; ipdb.set_trace()
        for i_init, dim_init in enumerate(inittime_sel):
            try:
                #print('trying the wms get map')
                if not use_init_time_fx:
                    dim_init = None
                img = wms.getmap(layers=[cont[i]],style='default',
                                  bbox=bbox, #(ylim[0],xlim[0],ylim[1],xlim[1]),
                                  size=res,
                                  transparent=True,
                                  time=time_sel,
                                  srs=srs,
                                  format='image/png',
                                  dim_init_time=dim_init,
                                  CQL_filter=cql_filter,
                                  timeout=90,**kwargs)
                if img:
                    print('Image downloaded, Init_time: '+str(dim_init))
                    label = label+', init:'+str(dim_init)
                    if printurl:
                        print(img.geturl())
                    break
            except Exception as ie:
                if i_init>len(inittime_sel)-2:
                    print(ie)
                    if 'img' in locals(): print(img.geturl())
                    self.root.config(cursor='')
                    self.root.update()
                    tkMessageBox.showwarning('Sorry','Problem getting the image from WMS server: '+website.split('/')[2]+'\nError: {}'.format(ie))
                    try:
                        print(website)
                    except:
                        pass
                    
                    return False, None, False
        try:
            legend_call = openURL(img.geturl().replace('GetMap','GetLegend'))
            geos_legend = Image.open(BytesIO(legend_call.read()))
        except:
            self.line.tb.set_message('legend image from WMS server problem')
            geos_legend = False
        
        try:
            geos = Image.open(BytesIO(img.read()))
        except Exception as ie:
            print(ie)
            try:
                r = img.read()
                if r.lower().find('invalid date')>-1:
                    self.root.config(cursor='')
                    self.root.update()
                    tkMessageBox.showwarning('Sorry','Time definition problem on server, trying again with no time set')
                    self.root.config(cursor='exchange')
                    self.root.update()
                    img = wms.getmap(layers=[cont[i]],style=['default'],
                              bbox=bbox,
                              size=res,
                              transparent=True,
                              srs=srs,
                              format='image/png',
                              CQL_filter=cql_filter,**kwargs)
                    geos = Image.open(BytesIO(img.read()))
                elif r.lower().find('property')>-1:
                    print('problem with the CQL_filter on the WMS server, retrying...')
                    img = wms.getmap(layers=[cont[i]],style=['default'],
                              bbox=bbox,
                              size=res,
                              transparent=True,
                              srs=srs,
                              format='image/png',**kwargs)
                    geos = Image.open(BytesIO(img.read()))
            except:
                self.root.config(cursor='')
                self.root.update()
                tkMessageBox.showwarning('Sorry','Problem reading the image a second time... abandonning')
                return False, None, False
        return geos, label, geos_legend
        
        
    def add_wms_images(self,geos,geos_legend,name='GEOS',alpha=1.0,text='',flip=False,**kwargs):
        'adding the wms images to the plots'
        from PIL import Image
        import tkinter.messagebox as tkMessageBox
        ylim = self.line.m.llcrnrlat,self.line.m.urcrnrlat
        xlim = self.line.m.llcrnrlon,self.line.m.urcrnrlon
        try: 
            if flip:
                imm = geos.transpose(Image.FLIP_TOP_BOTTOM)
            else:
                imm = geos
            self.line.addfigure_under(geos,ylim[0],xlim[0],ylim[1],xlim[1],text=text,alpha=alpha,name=name,**kwargs)
        except Exception as ie:
            print(ie)
            print(ie)
            self.root.config(cursor='')
            self.root.update()
            tkMessageBox.showwarning('Sorry','Problem putting the image under plot')
            return False
            
        try:
            if geos_legend:
                self.line.addlegend_image_below(geos_legend)
        except:
            self.line.tb.set_message('WMS Legend problem')
        self.root.config(cursor='')
        self.root.update()
        return True
        
    def rm_WMS(self,name='GEOS',button=None,newcommand=None):
        'core of removing the WMS plots on the figure and relinking command'
        self.line.tb.set_message('Removing {} figure under'.format(name))
        try:
            self.line.m.figure_under[name].remove()
        except:
            try:
                for f in self.line.m.figure_under[name]:
                    try:
                        f.remove
                    except TypeError:
                        pass
            except TypeError:
                print('Issue removing figure under:'+name)
            except KeyError:
                print('Issue removing figure under:'+name+' - No figure there initially')
        try:
            self.line.m.figure_under_text[name].remove()
        except:
            try:
                for f in self.line.m.figure_under_text[name]:
                    try:
                        f.remove  
                    except TypeError:
                        pass
            except AttributeError:
                pass
        try:
            if type(self.line.line) is list:
                lin = self.line.line[0]
            else:
                lin = self.line.line
            lin.figure.delaxes(self.line.m.legend_axis)
            lin.figure.canvas.draw()
        except:
            self.line.tb.set_message('Removing legend problem')
        button_label = button.config()['text'][-1]
        button.config(command=newcommand,style=self.bg)
        button.config(text='Add {} layer'.format(name))
        self.line.get_bg(redraw=True)
        
    def gui_rmgeos(self):
        'GUI handler for removing the GEOS forecast image, wrapper to rm_WMS'
        self.rm_WMS(name='GEOS',button=self.baddgeos,newcommand=self.gui_addgeos)
        
    def gui_rm_wms(self,name='WMS'):
        'GUI handler for removing any WMS image, wrapper to rm_WMS'
        self.rm_WMS(name=name,button=self.baddwms,newcommand=self.gui_add_any_WMS)
        
    def gui_rm_mss(self,name='MSS'):
        'GUI handler for removing MSS image, wrapper to rm_WMS'
        self.rm_WMS(name=name,button=self.baddmss,newcommand=self.gui_add_MSS)
        
    def gui_rm_SUA_WMS(self):
        'Button to add Special Use Airspace WMS layer'
        self.rm_WMS(name='SUA',button=self.baddsua,newcommand=self.gui_add_SUA_WMS)
            
    def gui_flt_module(self):
        'Program to load the flt_module files and select'
        try:
            from map_interactive import get_flt_modules
            from gui import Select_flt_mod
        except ModuleNotFoundError:
            from .map_interactive import get_flt_modules
            from .gui import Select_flt_mod

        
        flt_mods = get_flt_modules()
        select = Select_flt_mod(flt_mods,height=self.height)
        try:
            print('Applying the flt_module {}'.format(select.selected_flt))
            self.line.parse_flt_module_file(select.mod_path)
        except Exception as ie:
            #if not 'selected_flt' in ie: print(ie)
            print('flt_module selection cancelled',ie)
            #import pdb; pdb.set_trace()
            return
    
   # def gui_python(self):
   #     'Program to open a new window with a python command line'
   #     import tkinter as tk
   #     from gui import prompt
   #     root = tk.Toplevel()
   #     root.wm_title('Python command line')
   #     root.geometry('800x650')
   #     termf = tk.Frame(root,height=800,width=650)
   #     termf.pack(fill=tk.BOTH,expand=tk.YES)
   #     wid = termf.winfo_id()
        
    
# def prompt(vars, message):
    # 'function that calls for a python prompt'
    # #prompt_message = "Welcome!  Useful: G is the graph, DB, C"
    # prompt_message = message
    # try:
        # from IPython.Shell import IPShellEmbed
        # ipshell = IPShellEmbed(argv=[''],banner=prompt_message,exit_msg="Goodbye")
        # return  ipshell
    # except ImportError:
        # ## this doesn't quite work right, in that it doesn't go to the right env
        # ## so we just fail.
        # import code
        # import rlcompleter
        # import readline
        # readline.parse_and_bind("tab: complete")
        # # calling this with globals ensures we can see the environment
        # print(prompt_message)
        # shell = code.InteractiveConsole(vars)
        # return shell.interact

def inittime_sel_fx(xml,content,select_time):
    'Function to parse out the WMS xml for getting the init time'
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(xml,'xml')
    for l in soup.find_all('Layer'):
        if content in l.Name.text:
            selected_layer = l
    for extents in selected_layer.find_all('Extent'):
        if 'INIT_TIME' in extents.attrs['name']:
            inittime_sel = extents.text.strip().split(',')
    
    if len(inittime_sel)<1: inittime_sel = [select_time]
    return inittime_sel
            
class Select_flt_mod(tkSimpleDialog.Dialog):
    """
       Dialog box pop up that lists the available flt_modules. 
       If possible it will show a small png of the flt_module (not done yet)
    """
    import tkinter as tk
    def __init__(self,flt_mods,title='Choose flt module',text='Select flt module:',height=1080):
        import tkinter as tk
        parent = tk._default_root
        self.flt_mods = flt_mods
        self.text = text
        self.height=height
        tkSimpleDialog.Dialog.__init__(self,parent,title)
        pass
    def body(self,master):
        import tkinter as tk
        from PIL import Image, ImageTk
        self.rbuttons = []
        self.flt = tk.StringVar()
        self.flt.set(list(self.flt_mods.keys())[0])
        tk.Label(master, text=self.text).grid(row=0)
        keys = list(self.flt_mods.keys())
        keys.sort()
        for i,l in enumerate(keys):
            try:
                im = Image.open(self.flt_mods[l]['png'])
                resized = im.resize((60, 60),Image.ANTIALIAS)
                photo = ImageTk.PhotoImage(resized)
                try:
                    bu = tk.Radiobutton(master,text=l, variable=self.flt,value=l,image=photo,compound='left')
                    bu.photo = photo
                    self.rbuttons.append(bu)
                except Exception as io:
                    print(io)
            except:
                self.rbuttons.append(tk.Radiobutton(master,text=l, variable=self.flt,value=l))
            j = int(i*80/self.height)
            imax = int(self.height/80)
            self.rbuttons[i].grid(row=(i+1)%imax,column=j,sticky=tk.W)
        return
    def apply(self):
        self.mod_path = self.flt_mods[self.flt.get()]['path']
        self.selected_flt = self.flt.get()
        return self.mod_path 
    
class Select_flights(tkSimpleDialog.Dialog):
    """
    Purpose:
        Dialog box that loads a list of points or flights to be selected.
    Inputs:
        tkSimple.Dialog
        pt_list: list of string array in the correct positions
        title: title of dialog window
        text: text to be displayed before the checkbox selection
    Outputs:
        list of integers that are selected
    Dependencies:
        tkSimpleDialog
    MOdifications:
        written: Samuel LeBlanc, 2015-09-14, NASA Ames, Santa Cruz, CA
    """
    def __init__(self,pt_list,title='Choose flight',Text='Select points:',parent=None):
        import tkinter as tk
        if not parent:
            parent = tk._default_root
        self.pt_list = pt_list
        self.Text = Text
        tkSimpleDialog.Dialog.__init__(self,parent,title)
        pass
    
    def body(self,master):
        import tkinter.simpledialog as tkSimpleDialog
        import tkinter as tk
        self.results = []
        tk.Label(master, text=self.Text).grid(row=0)

        self.cbuttons = []
        for i,l in enumerate(self.pt_list):
            var = tk.IntVar()
            self.results.append(var)
            self.cbuttons.append(tk.Checkbutton(master,text=l, variable=var))
            self.cbuttons[i].grid(row=i+1,sticky=tk.W)

    def apply(self):
        self.result = map((lambda var: var.get()),self.results)
        return self.result

class Move_point(tkSimpleDialog.Dialog):
    """
    Purpose:
        Dialog box that gets user input for point to add
    Inputs:
        tkSimple.Dialog
        title: title of dialog box (defaults to 'New point info')
        speed: (optional) speed of plane in meters/second
    Outputs:
        distance and direction of new point
    Dependencies:
        tkSimpleDialog
    MOdifications:
        written: Samuel LeBlanc, 2015-09-14, NASA Ames, Santa Cruz, CA
        Modified: Samuel LeBlanc, 2016-06-06, NASA Ames, in Santa Cruz, CA
                  - added the speed input for calculating the distance based on time until point.
        Modified: Samuel LeBlanc, 2016-09-09, Swakopmund, Namibia
                  - added pp (principal plane) keyword for setting the bearing along the principal plane
    """
    def __init__(self,title='New point info',speed=None,pp=None):
        import tkinter as tk
        self.speed = speed
        self.pp = pp
        parent = tk._default_root
        tkSimpleDialog.Dialog.__init__(self,parent,title)
        pass
    
    def body(self,master):
        import tkinter.simpledialog as tkSimpleDialog
        import tkinter as tk
        tk.Label(master, text='Enter Distance [km]').grid(row=0)
        tk.Label(master, text='Enter Bearing, 0-360, [degrees CW from North]').grid(row=1)
        self.edist = tk.Entry(master)
        self.ebear = tk.Entry(master)
        self.edist.grid(row=0,column=1)
        self.ebear.grid(row=1,column=1)
        self.ebear.grid(row=1,column=1)
        if self.speed:
            self.speed = self.speed*3.6
            tk.Label(master,text='or').grid(row=0,column=2)
            tk.Label(master,text='Time [min]').grid(row=0,column=3)
            self.etime = tk.Entry(master)
            self.etime.grid(row=0,column=4)
        if self.pp:
            tk.Label(master,text='or PP offset').grid(row=1,column=2)
            tk.Label(master,text='Degrees').grid(row=1,column=3)
            self.epp = tk.Entry(master)
            self.epp.grid(row=1,column=4)
        return self.edist

    def apply(self):
        try:
            self.dist = float(self.edist.get())
        except:
            self.dist = float(self.speed)*float(self.etime.get())/60.0
        try:
            self.bear = float(self.ebear.get())
        except:
            self.bear = float(self.epp.get())+float(self.pp)
        return self.dist,self.bear

    def validate(self):
        try:
            self.dist = float(self.edist.get())
        except ValueError:
            if self.speed:
                try:
                    self.time = float(self.etime.get())
                except ValueError:
                    import tkinter.messagebox as tkMessageBox
                    tkMessageBox.showwarning('Bad input','Can not format distance and time values, try again')
            else:
                import tkinter.messagebox as tkMessageBox
                tkMessageBox.showwarning('Bad input','Can not format distance and time values, try again')
        try:
            self.bear = float(self.ebear.get())
        except ValueError:
            if self.pp:
                try:
                    self.bear = float(self.epp.get())+float(self.pp)
                except ValueError:
                    import tkinter.messagebox as tkMessageBox
                    tkMessageBox.showwarning('Bad input','Can not format bearing and pp values, try again')
            else:
                import tkinter.messagebox as tkMessageBox
                tkMessageBox.showwarning('Bad input','Can not format bearing and pp values, try again')
        return True

class ask(tkSimpleDialog.Dialog):
    """
    Simple class to ask to enter values for each item in names
    """
    def __init__(self,names,choice=[],choice_title=None,choice2=[],choice2_title=None,title='Enter numbers',defaults=[]):
        import tkinter as tk
        self.names = names
        self.defaults = defaults
        self.choice = choice
        self.choice_title = choice_title
        self.choice2 = choice2
        self.choice2_title = choice2_title
        parent = tk._default_root
        tkSimpleDialog.Dialog.__init__(self,parent,title)
        pass
    def body(self,master):
        import tkinter as tk
        self.radb_val = tk.StringVar()
        self.radb_val.set(self.choice[0])
        self.radbutton = []
        self.radb2_val = tk.StringVar()
        self.radb2_val.set(self.choice2[0])
        self.radbutton2 = []
        ii = 0
        if self.choice_title:
            tk.Label(master,text=self.choice_title).grid(row=0,column=0,columnspan=2)
            ii = 1
        for i,l in enumerate(self.choice):
            self.radbutton.append(tk.Radiobutton(master,text=l,variable=self.radb_val,value=l))
            self.radbutton[i].grid(row=0+ii,column=i)
        if self.choice2_title:
            tk.Label(master,text=self.choice2_title).grid(row=1+ii,column=0,columnspan=2)
            ii = 3
        for i,l in enumerate(self.choice2):
            self.radbutton2.append(tk.Radiobutton(master,text=l,variable=self.radb2_val,value=l))
            self.radbutton2[i].grid(row=ii,column=i)
        self.fields = list(range(len(self.names)))
        for i,n in enumerate(self.names):
            tk.Label(master,text=n).grid(row=i+1+ii)
            self.fields[i] = tk.Entry(master)
            if self.defaults:
                try:
                    self.fields[i].insert(0,'{}'.format(self.defaults[i]))
                except: 
                    pass
            self.fields[i].grid(row=i+1+ii,column=1)
    def apply(self):
        self.names_val = list(range(len(self.names)))
        for i,n in enumerate(self.names):
            self.names_val[i] = float(self.fields[i].get())
        self.choice_val = self.radb_val.get()
        self.choice2_val = self.radb2_val.get()
        return self.names_val          
        
class Select_profile(tkSimpleDialog.Dialog):
    """
    Purpose:
        Dialog box that gets user input for what basemap profiles to load
        Allows changing of the plotting area and starting location
    Inputs:
        tkSimple.Dialog
        default_profiles: list of profile dict objects
        title: title of dialog box (defaults to 'Enter map defaults'
    Outputs:
        Single profile
    Dependencies:
        tkSimpleDialog
    MOdifications:
        written: Samuel LeBlanc, 2015-09-15, NASA Ames, CA
    """
    def __init__(self,default_profiles,title='Enter map defaults',
        proj_list=['PlateCarree','NorthPolarStereo','AlbersEqualArea','AzimuthalEquidistant',
        'LambertCylindrical','Mercator','Miller','Mollweide','Orthographic','Robinson','Stereographic','SouthPolarStereo','Geostationary','LambertAzimuthalEqualArea']):
        import tkinter as tk
        self.default_profiles = default_profiles
        self.profile = self.default_profiles[0]
        self.proj_list = proj_list
        self.oked = False
        parent = tk._default_root
        tkSimpleDialog.Dialog.__init__(self,parent,title)

    def body(self,master):
        import tkinter.simpledialog as tkSimpleDialog
        import tkinter as tk
        self.pname = tk.StringVar(master)
        self.pname.set(self.default_profiles[0]['Profile'])
        names = [pp['Profile'] for pp in self.default_profiles]
        tk.Label(master, text='Default Profiles:').grid(row=0)
        self.drop = tk.OptionMenu(master,self.pname,*names,command=self.set_profvalues)
        self.drop.grid(row=0,column=1,columnspan=2)
        tk.Label(master, text='Options', font="-weight bold").grid(row=1,columnspan=3)

        tk.Label(master, text='Plane Name:').grid(row=2,sticky=tk.E)
        self.name = tk.Entry(master)
        self.name.grid(row=2,column=1,columnspan=2)

        tk.Label(master, text='Start Lon:').grid(row=3,sticky=tk.E)
        self.start_lon = tk.Entry(master)
        self.start_lon.grid(row=3,column=1,columnspan=2)

        tk.Label(master, text='Start Lat:').grid(row=4,sticky=tk.E)
        self.start_lat = tk.Entry(master)
        self.start_lat.grid(row=4,column=1,columnspan=2)

        tk.Label(master, text='Longitude range:').grid(row=5,sticky=tk.E)
        self.lon0 = tk.Entry(master,width=10)
        self.lon1 = tk.Entry(master,width=10)
        self.lon0.grid(row=5,column=1)
        self.lon1.grid(row=5,column=2)

        tk.Label(master, text='Latitude range:').grid(row=6,sticky=tk.E)
        self.lat0 = tk.Entry(master,width=10)
        self.lat1 = tk.Entry(master,width=10)
        self.lat0.grid(row=6,column=1)
        self.lat1.grid(row=6,column=2)

        tk.Label(master, text='Central Lat/Lon:').grid(row=7,sticky=tk.E)
        self.lat_0 = tk.Entry(master,width=10)
        self.lon_0 = tk.Entry(master,width=10)
        self.lat_0.grid(row=7,column=1)
        self.lon_0.grid(row=7,column=2)
        
        self.start_lat = tk.Entry(master)
        self.start_lat.grid(row=4,column=1,columnspan=2)

        tk.Label(master, text='UTC Start:').grid(row=8,sticky=tk.E)
        self.start_utc = tk.Entry(master)
        self.start_utc.grid(row=8,column=1,columnspan=2)

        tk.Label(master, text='UTC conversion:').grid(row=9,sticky=tk.E)
        self.utc_convert = tk.Entry(master)
        self.utc_convert.grid(row=9,column=1,columnspan=2)

        tk.Label(master, text='Start Alt:').grid(row=10,sticky=tk.E)
        self.start_alt = tk.Entry(master)
        self.start_alt.grid(row=10,column=1,columnspan=2)
        
        tk.Label(master, text='Projection:').grid(row=11,sticky=tk.E)
        self.proj_string = tk.StringVar()
        self.proj_string.set(self.proj_list[0])
        self.proj = tk.OptionMenu(master,self.proj_string,*self.proj_list)
        self.proj.grid(row=11,column=1,columnspan=2)

        self.set_profvalues(names[0])
        return self.drop

    def set_profvalues(self,val):
        'Simple program to load the default profile values in the different entry points'
        for p in self.default_profiles:
            if p['Profile']==self.pname.get():
                self.set_val(self.name,p['Plane_name'])
                self.set_val(self.start_lon,p['Start_lon'])
                self.set_val(self.start_lat,p['Start_lat'])
                self.set_val(self.lon0,p['Lon_range'][0])
                self.set_val(self.lon1,p['Lon_range'][1])
                self.set_val(self.lat0,p['Lat_range'][0])
                self.set_val(self.lat1,p['Lat_range'][1])
                self.set_val(self.lat_0,p.get('lat_0',45.0))
                self.set_val(self.lon_0,p.get('lon_0',0.0))
                self.set_val(self.start_utc,p['UTC_start'])
                self.set_val(self.utc_convert,p['UTC_conversion'])
                self.set_val(self.start_alt,p['start_alt'])
                self.proj_string.set(p.get('proj','PlateCarree'))
                

    def set_val(self,e,val):
        'Simple program to delete the value and replace with current value'
        import tkinter as tk
        e.delete(0,tk.END)
        e.insert(tk.END,val)
    
    def apply(self):
        for p in self.default_profiles:
            if p['Profile']==self.pname.get():
                self.profile = p
        self.profile['Plane_name'] = self.name.get()
        self.profile['Start_lon'] = self.start_lon.get()
        self.profile['Start_lat'] = self.start_lat.get()
        self.profile['Lon_range'] = [self.lon0.get(),self.lon1.get()]
        self.profile['Lat_range'] = [self.lat0.get(),self.lat1.get()]
        self.profile['lon_0'] = self.lon_0.get()
        self.profile['lat_0'] = self.lat_0.get()
        self.profile['UTC_start'] = float(self.start_utc.get())
        self.profile['UTC_conversion'] = float(self.utc_convert.get())
        self.profile['start_alt'] = float(self.start_alt.get())
        self.profile['Campaign'] = self.pname.get()
        self.profile['proj'] = self.proj_string.get()
        print('..Applying selected profile')
        self.oked = True
        return self.profile
        
    def cancel(self,event=None):
        if not self.oked: self.profile = False
        super().cancel(event=event)
        return self.profile

    def check_input(self,s,isletter=False):
        'method to check if there is a number or letter in the string'
        if s:
            import re
            if isletter:
                u = '\w'
            else:
                u = '\d'
            if re.search(u,s):
                return True
            else:
                return False
        else:
            return false

    def validate(self):
        import tkinter.messagebox as tkMessageBox
        if not self.check_input(self.name.get(),1):
            tkMessageBox.showwarning('Bad input','Plane name error, try again')
            return False
        if not self.check_input(self.start_lon.get(),0):
            tkMessageBox.showwarning('Bad input','Start Lon error, try again')
            return False
        if not self.check_input(self.start_lat.get(),0):
            tkMessageBox.showwarning('Bad input','Start Lat error, try again')
            return False
        if not self.check_input(self.lon_0.get(),0):
            tkMessageBox.showwarning('Bad input','Central Lon error, try again')
            return False
        if not self.check_input(self.lat_0.get(),0):
            tkMessageBox.showwarning('Bad input','Central Lat error, try again')
            return False
        if not self.check_input(self.lon0.get(),0):
            tkMessageBox.showwarning('Bad input','Lon Range error, try again')
            return False
        if not self.check_input(self.lon1.get(),0):
            tkMessageBox.showwarning('Bad input','Lon Range error, try again')
            return False
        if not self.check_input(self.start_utc.get(),0):
            tkMessageBox.showwarning('Bad input','Start UTC error, try again')
            return False
        if not self.check_input(self.utc_convert.get(),0):
            tkMessageBox.showwarning('Bad input','UTC Conversion error, try again')
            return False
        if not self.check_input(self.start_alt.get(),0):
            tkMessageBox.showwarning('Bad input','Alt start error, try again')
            return False
        if not self.check_input(self.lat0.get(),0):
            tkMessageBox.showwarning('Bad input','Lat Range error, try again')
            return False
        if not self.check_input(self.lat1.get(),0):
            tkMessageBox.showwarning('Bad input','Lat Range error, try again')
            return False
        try:
            us = float(self.start_utc.get())
            uc = float(self.utc_convert.get())
            sa = float(self.start_alt.get())
        except ValueError:
            import tkinter.messagebox as tkMessageBox
            tkMessageBox.showwarning('Bad input','Can not format values, try again')
            return False
        return True

class Popup_list(tkSimpleDialog.Dialog):
    """
    Purpose:
        Popup box that offers selection of list
        Whatever is clicked, the window closes and returns the resulting index
    Inputs:
        arr: list of text values
        multi: (optional) if True, then enables selecting multiple lines
    Outputs:
        index value of selection
    Dependencies:
        tkinter
    MOdifications:
        written: Samuel LeBlanc, 2015-09-16, NASA Ames, CA
        Modified: Samuel LeBlanc, 2016-07-13, NASA WFF, VA
                  - made to be a subclass of the tkSimpleDialog product
        Modified: Samuel LeBlanc, 2016-08-09, Santa Cruz, CA
                  - added the multi keyword for selecting multiple possible values
    """
    def __init__(self,arr,title='Select graphics from server',Text=None,multi=False):
        import tkinter as tk
        self.arr = arr
        parent = tk._default_root
        self.multi = multi
        self.Text = Text
        tkSimpleDialog.Dialog.__init__(self,parent,title)
        
    def body(self,master):
        import tkinter as tk
        if self.Text:
            tk.Label(master, text=self.Text).pack()
        if self.multi:
            lb = tk.Listbox(master,selectmode=tk.EXTENDED)
        else:
            lb = tk.Listbox(master)
        lb.config(width=0)
        lb.config(height=20)
        for i,e in enumerate(self.arr):
            lb.insert(tk.END,e)
        master.winfo_toplevel().wm_geometry("")
        scroll = tk.Scrollbar(master)
        scroll.pack(side=tk.RIGHT,fill=tk.Y)
        lb.config(yscrollcommand=scroll.set)
        scroll.config(command=lb.yview)
        self.var = tk.IntVar(master)
        self.lb = lb
        self.lb.select_set(0)
        if not self.multi:
            lb.bind('<Double-1>',self.ok)
        self.lb.pack()
        
    def apply(self):
        if not self.multi:
            value, = self.lb.curselection()
            self.var.set(value)
            self.result = value
            #print(value)
        else:
            value = self.lb.curselection()
            self.result = map(int,value)
        return self.var.get()
        
class ask_option(tkSimpleDialog.Dialog):
    """
    program to ask to select between two options with buttons
    """
    def __init__(self,title='Select option',Text=None,button1='At End',button2='In Between\npoints',button3=None):
        import tkinter as tk
        self.b1 = button1
        self.b2 = button2
        if button3:
            self.b3 = button3
        parent = tk._default_root
        self.Text = Text
        tkSimpleDialog.Dialog.__init__(self,parent,title)
    def body(self,master):
        import tkinter as tk
        if self.Text:
            tk.Label(master, text=self.Text).pack()
    def buttonbox(self):
        import tkinter as tk
        box = tk.Frame(self)
        self.out = tk.IntVar()
        def but1():
            self.but(0)
        def but2():
            self.but(1)
        w = tk.Button(box, text=self.b1, width=10, command=but1, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.Button(box, text=self.b2, width=10, command=but2)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        if hasattr(self,'b3'):
            def but3():
                self.but(2)
            w = tk.Button(box, text=self.b3, width=10, command=but3)
            w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()
    def but(self,i):
        import tkinter as tk
        self.out.set(i)
        self.ok()        
        
class custom_toolbar(NavigationToolbar2TkAgg):
    """
    Custom set of toolbar points, based on the NavigationToolbar2TkAgg
    
     - removes the configure subplots_adjust
     - makes the buttons become grey when selected, and ungray when deselected
    """

    # Icons for the toolbar used from Minicons Free Vector Icons Pack fround at: www.webalys.com/minicons
    toolitems = (
        ('Home', 'Reset original view', 'ml_home', 'home'),
        ('Back', 'Back to  previous view', 'ml_back', 'back'),
        ('Forward', 'Forward to next view', 'ml_forward', 'forward'),
        (None, None, None, None),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'ml_pan', 'pan'),
        ('Zoom', 'Zoom to rectangle', 'ml_zoom', 'zoom'),
        (None, None, None, None),
        (None, None, None, None),
        ('Save', 'Save the figure', 'ml_save', 'save_figure'),
      )
                 
    def zoom(self, *args):
        'decorator for the zoom function'
        super(custom_toolbar,self).zoom(*args)
        if self.mode=='ZOOM':
            self.buttons['zoom'].config(bg='dark grey')
            self.buttons['pan'].config(bg=self.bg)
        else:
            self.buttons['zoom'].config(bg=self.bg)
        s = 'zoom_event'
        event = Event(s, self)
        self.canvas.callbacks.process(s, event)
        
    def release_zoom(self, event):
        super(custom_toolbar,self).release_zoom(event)
        s = 'zoom_event'
        event1 = Event(s, self)
        self.canvas.callbacks.process(s, event1)
        
    def back(self, *args):
        super(custom_toolbar,self).back(*args)
        s = 'back_event'
        event = Event(s, self)
        self.canvas.callbacks.process(s, event)
        
    def forward(self, *args):
        super(custom_toolbar,self).forward(*args)
        s = 'forward_event'
        event = Event(s, self)
        self.canvas.callbacks.process(s, event)

    def pan(self, *args):
        'decorator for the pan function'
        super(custom_toolbar,self).pan(*args)
        if self.mode=='PAN':
            self.buttons['pan'].config(bg='dark grey')
            self.buttons['zoom'].config(bg=self.bg)
        else:
            self.buttons['pan'].config(bg=self.bg)
        s = 'pan_event'
        event = Event(s, self)
        self.canvas.callbacks.process(s, event)
            
    def _init_toolbar(self):
        import os
        ressource_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'mpl-data') 
        xmin, xmax = self.canvas.figure.bbox.intervalx
        height, width = 50, xmax-xmin
        Tk.Frame.__init__(self, master=self.window,
                          width=int(width), height=int(height),
                          borderwidth=2)
        self.update()  # Make axes menu
        self.buttons = {}
        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                # spacer, unhandled in Tk
                pass
            else:
                try:
                    button = self._Button(text=text, file=image_file,
                                       command=getattr(self, callback),extension='.gif') # modified extension to use gif
                except:
                    button = self._Button(text=text, image_file=os.path.join(ressource_path,image_file+'.png'),
                                       command=getattr(self, callback),toggle=True) # modified extension to use gif
                self.buttons[callback] = button # modified to save button instances
                if tooltip_text is not None:
                    ToolTip.createToolTip(button, tooltip_text)
        self.bg = button.cget('bg')
        self.message = Tk.StringVar(master=self)
        self._message_label = Tk.Label(master=self, textvariable=self.message)
        self._message_label.pack(side=Tk.RIGHT)
        self.pack(side=Tk.BOTTOM, fill=Tk.X)    
        
    def home(self,*args):
        'home function that will be used to overwrite the current home button'
        super(custom_toolbar,self).home(*args)
        s = 'home_event'
        event = Event(s, self)
        try:
            self.canvas.callbacks.process(s, event)
        except:
            print('Problem with home button')

def gui_file_select_fx(ext='*',
                       ftype=[('Excel 1997-2003','*.xls'),('Excel','*.xlsx'),
                           ('Kml','*.kml'),('All files','*.*')]):
    """
    Simple gui file select program. Uses TKinter for interface, returns full path
    """
    from tkinter import Tk
    from tkinter.filedialog import askopenfilename
    from os.path import abspath
    Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
    filename = askopenfilename(defaultextension=ext,filetypes=ftype) # show an "Open" dialog box and return the path to the selected file
    if filename:
        filename = abspath(filename)
    return filename

import tkinter as tk
class CoordinateProjectionDialog(tkSimpleDialog.Dialog):
    """Custom dialog for entering coordinates and projection information"""
    
    
    def __init__(self, parent, title="Image Coordinates and Projection"):
        self.result = None
        super().__init__(parent, title)
    
    def body(self, master):
        """Create dialog body. Return widget that should have initial focus."""
        
        # Main frame
        main_frame = ttk.Frame(master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Coordinates section
        coords_frame = ttk.LabelFrame(main_frame, text="Image Coordinates", padding="5")
        coords_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Lower Left coordinates
        ttk.Label(coords_frame, text="Lower Left:").grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(coords_frame, text="Latitude/Y:").grid(row=1, column=0, sticky=tk.W, padx=(10, 5))
        self.ll_lat_var = tk.DoubleVar()
        self.ll_lat_entry = ttk.Entry(coords_frame, textvariable=self.ll_lat_var, width=15)
        self.ll_lat_entry.grid(row=1, column=1, sticky=tk.W, padx=(0, 10))
        
        ttk.Label(coords_frame, text="Longitude/X:").grid(row=2, column=0, sticky=tk.W, padx=(10, 5))
        self.ll_lon_var = tk.DoubleVar()
        self.ll_lon_entry = ttk.Entry(coords_frame, textvariable=self.ll_lon_var, width=15)
        self.ll_lon_entry.grid(row=2, column=1, sticky=tk.W, padx=(0, 10))
        
        # Upper Right coordinates
        ttk.Label(coords_frame, text="Upper Right:").grid(row=0, column=2, columnspan=2, sticky=tk.W, pady=(0, 5), padx=(20, 0))
        
        ttk.Label(coords_frame, text="Latitude/Y:").grid(row=1, column=2, sticky=tk.W, padx=(30, 5))
        self.ur_lat_var = tk.DoubleVar()
        self.ur_lat_entry = ttk.Entry(coords_frame, textvariable=self.ur_lat_var, width=15)
        self.ur_lat_entry.grid(row=1, column=3, sticky=tk.W)
        
        ttk.Label(coords_frame, text="Longitude/X:").grid(row=2, column=2, sticky=tk.W, padx=(30, 5))
        self.ur_lon_var = tk.DoubleVar()
        self.ur_lon_entry = ttk.Entry(coords_frame, textvariable=self.ur_lon_var, width=15)
        self.ur_lon_entry.grid(row=2, column=3, sticky=tk.W)
        
        # Coordinate type
        coord_type_frame = ttk.Frame(coords_frame)
        coord_type_frame.grid(row=3, column=0, columnspan=4, pady=(10, 0), sticky=tk.W)
        
        ttk.Label(coord_type_frame, text="Coordinates are:").grid(row=0, column=0, sticky=tk.W)
        self.coord_type_var = tk.StringVar(value="geographic")
        coord_geographic = ttk.Radiobutton(coord_type_frame, text="Geographic (Lat/Lon)", 
                                         variable=self.coord_type_var, value="geographic")
        coord_geographic.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        coord_projected = ttk.Radiobutton(coord_type_frame, text="Projected (meters/units)", 
                                        variable=self.coord_type_var, value="projected")
        coord_projected.grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        
        # Projection section
        proj_frame = ttk.LabelFrame(main_frame, text="Projection Information", padding="5")
        proj_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Projection type dropdown
        ttk.Label(proj_frame, text="Projection Type:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.proj_type_var = tk.StringVar()
        self.proj_type_combo = ttk.Combobox(proj_frame, textvariable=self.proj_type_var, 
                                          values=["platecarree", "mercator", "stereographic", 
                                                "lambert_conformal",  "lambert_azimuthal_equal_area", "utm", "custom"], 
                                          state="readonly", width=20)
        self.proj_type_combo.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        self.proj_type_combo.bind('<<ComboboxSelected>>', self.on_projection_change)
        self.proj_type_combo.set("platecarree")  # Default
        
        # Dynamic projection parameters frame
        self.proj_params_frame = ttk.Frame(proj_frame)
        self.proj_params_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Initialize projection parameter widgets
        self.proj_param_vars = {}
        self.proj_param_widgets = {}
        
        # Initial projection parameters display
        self.update_projection_parameters()
        
        return self.ll_lat_entry  # Initial focus
    
    def on_projection_change(self, event=None):
        """Handle projection type change"""
        self.update_projection_parameters()
    
    def update_projection_parameters(self):
        """Update the projection parameters based on selected projection"""
        # Clear existing parameter widgets
        for widget in self.proj_param_widgets.values():
            if isinstance(widget, (list, tuple)):
                for w in widget:
                    w.destroy()
            else:
                widget.destroy()
        self.proj_param_widgets.clear()
        self.proj_param_vars.clear()
        
        proj_type = self.proj_type_var.get()
        row = 0
        
        if proj_type == "platecarree":
            # Central longitude
            ttk.Label(self.proj_params_frame, text="Central Longitude:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['central_longitude'] = tk.DoubleVar(value=0.0)
            entry = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['central_longitude'], width=10)
            entry.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            self.proj_param_widgets['central_longitude'] = entry
            
        elif proj_type == "mercator":
            # Central longitude
            ttk.Label(self.proj_params_frame, text="Central Longitude:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['central_longitude'] = tk.DoubleVar(value=0.0)
            entry = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['central_longitude'], width=10)
            entry.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            self.proj_param_widgets['central_longitude'] = entry
            
        elif proj_type == "stereographic":
            # Central latitude
            ttk.Label(self.proj_params_frame, text="Central Latitude:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['central_latitude'] = tk.DoubleVar(value=90.0)
            entry1 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['central_latitude'], width=10)
            entry1.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            # Central longitude
            row += 1
            ttk.Label(self.proj_params_frame, text="Central Longitude:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['central_longitude'] = tk.DoubleVar(value=0.0)
            entry2 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['central_longitude'], width=10)
            entry2.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            self.proj_param_widgets['stereographic'] = [entry1, entry2]
            
        elif proj_type == "lambert_conformal":
            # Central latitude
            ttk.Label(self.proj_params_frame, text="Central Latitude:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['central_latitude'] = tk.DoubleVar(value=39.0)
            entry1 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['central_latitude'], width=10)
            entry1.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            # Central longitude
            row += 1
            ttk.Label(self.proj_params_frame, text="Central Longitude:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['central_longitude'] = tk.DoubleVar(value=-96.0)
            entry2 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['central_longitude'], width=10)
            entry2.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            # Standard parallels
            row += 1
            ttk.Label(self.proj_params_frame, text="Standard Parallel 1:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['std_parallel_1'] = tk.DoubleVar(value=33.0)
            entry3 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['std_parallel_1'], width=10)
            entry3.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            row += 1
            ttk.Label(self.proj_params_frame, text="Standard Parallel 2:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['std_parallel_2'] = tk.DoubleVar(value=45.0)
            entry4 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['std_parallel_2'], width=10)
            entry4.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            self.proj_param_widgets['lambert_conformal'] = [entry1, entry2, entry3, entry4]
        elif proj_type == "lambert_azimuthal_equal_area":
            # Central latitude
            ttk.Label(self.proj_params_frame, text="Central Latitude:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['central_latitude'] = tk.DoubleVar(value=0.0)
            entry1 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['central_latitude'], width=10)
            entry1.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            # Central longitude
            row += 1
            ttk.Label(self.proj_params_frame, text="Central Longitude:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['central_longitude'] = tk.DoubleVar(value=0.0)
            entry2 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['central_longitude'], width=10)
            entry2.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            # False easting
            row += 1
            ttk.Label(self.proj_params_frame, text="False Easting:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['false_easting'] = tk.DoubleVar(value=0.0)
            entry3 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['false_easting'], width=10)
            entry3.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            # False northing
            row += 1
            ttk.Label(self.proj_params_frame, text="False Northing:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['false_northing'] = tk.DoubleVar(value=0.0)
            entry4 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['false_northing'], width=10)
            entry4.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            # Globe radius (optional)
            row += 1
            ttk.Label(self.proj_params_frame, text="Globe Radius (optional):").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['globe_radius'] = tk.DoubleVar(value=1.0)
            entry5 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['globe_radius'], width=10)
            entry5.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            self.proj_param_widgets['lambert_azimuthal'] = [entry1, entry2, entry3, entry4, entry5]

        elif proj_type == "utm":
            # Zone number
            ttk.Label(self.proj_params_frame, text="UTM Zone:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['zone'] = tk.IntVar(value=33)
            entry1 = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['zone'], width=10)
            entry1.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            
            # Hemisphere
            row += 1
            ttk.Label(self.proj_params_frame, text="Hemisphere:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['hemisphere'] = tk.StringVar(value="northern")
            combo = ttk.Combobox(self.proj_params_frame, textvariable=self.proj_param_vars['hemisphere'],
                               values=["northern", "southern"], state="readonly", width=8)
            combo.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            combo.set("northern")
            
            self.proj_param_widgets['utm'] = [entry1, combo]
            
        elif proj_type == "custom":
            # Custom projection string
            ttk.Label(self.proj_params_frame, text="Custom Projection:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.proj_param_vars['custom_string'] = tk.StringVar()
            entry = ttk.Entry(self.proj_params_frame, textvariable=self.proj_param_vars['custom_string'], width=30)
            entry.grid(row=row, column=1, sticky=tk.W, padx=(5, 0), pady=2)
            self.proj_param_widgets['custom'] = entry
    
    def validate(self):
        """Validate the input values"""
        try:
            # Validate coordinates
            ll_lat = self.ll_lat_var.get()
            ll_lon = self.ll_lon_var.get()
            ur_lat = self.ur_lat_var.get()
            ur_lon = self.ur_lon_var.get()
            
            # Basic validation - can be expanded
            if self.coord_type_var.get() == "geographic":
                if not (-90 <= ll_lat <= 90) or not (-90 <= ur_lat <= 90):
                    tk.messagebox.showerror("Invalid Input", "Latitude values must be between -90 and 90 degrees")
                    return 0
                if not (-180 <= ll_lon <= 180) or not (-180 <= ur_lon <= 180):
                    tk.messagebox.showerror("Invalid Input", "Longitude values must be between -180 and 180 degrees")
                    return 0
            
            # Validate projection-specific parameters
            proj_type = self.proj_type_var.get()
            if proj_type == "utm":
                zone = self.proj_param_vars['zone'].get()
                if not (1 <= zone <= 60):
                    tk.messagebox.showerror("Invalid Input", "UTM zone must be between 1 and 60")
                    return 0
            
            return 1
            
        except tk.TclError:
            tk.messagebox.showerror("Invalid Input", "Please enter valid numeric values")
            return 0
    
    def apply(self):
        """Process the data when OK is pressed"""
        # Get coordinates
        coordinates = {
            'll_lat': self.ll_lat_var.get(),
            'll_lon': self.ll_lon_var.get(),
            'ur_lat': self.ur_lat_var.get(),
            'ur_lon': self.ur_lon_var.get(),
        }
        
        # Get coordinate type
        coords_are_geographic = self.coord_type_var.get() == "geographic"
        
        # Get projection information
        proj_type = self.proj_type_var.get()
        projection = {"type": proj_type}
        
        # Add projection-specific parameters
        if proj_type == "platecarree":
            projection["central_longitude"] = self.proj_param_vars['central_longitude'].get()
        elif proj_type == "mercator":
            projection["central_longitude"] = self.proj_param_vars['central_longitude'].get()
        elif proj_type == "stereographic":
            projection["central_latitude"] = self.proj_param_vars['central_latitude'].get()
            projection["central_longitude"] = self.proj_param_vars['central_longitude'].get()
        elif proj_type == "lambert_conformal":
            projection["central_latitude"] = self.proj_param_vars['central_latitude'].get()
            projection["central_longitude"] = self.proj_param_vars['central_longitude'].get()
            projection["standard_parallels"] = [
                self.proj_param_vars['std_parallel_1'].get(),
                self.proj_param_vars['std_parallel_2'].get()
            ]
        elif proj_type == "lambert_azimuthal_equal_area":
            projection["central_latitude"] = self.proj_param_vars['central_latitude'].get()
            projection["central_longitude"] = self.proj_param_vars['central_longitude'].get()
            projection["false_easting"] = self.proj_param_vars['false_easting'].get()
            projection["false_northing"] = self.proj_param_vars['false_northing'].get()
            globe_radius = self.proj_param_vars['globe_radius'].get()
            if globe_radius != 1.0:  # Only include if not default
                projection["globe_radius"] = globe_radius
        elif proj_type == "utm":
            projection["zone"] = self.proj_param_vars['zone'].get()
            projection["southern_hemisphere"] = self.proj_param_vars['hemisphere'].get() == "southern"
        elif proj_type == "custom":
            projection = self.proj_param_vars['custom_string'].get()
        
        # Store result
        self.result = {
            'coordinates': coordinates,
            'coordinates_are_geographic': coords_are_geographic,
            'projection': projection
        }


# Convenience function to use the dialog
def get_coordinates_and_projection(parent=None, title="Image Coordinates and Projection"):
    """
    Show the coordinate and projection dialog and return the results
    
    Returns:
        dict: Contains 'coordinates', 'coordinates_are_geographic', and 'projection' keys
        None: If dialog was cancelled
    """
    dialog = CoordinateProjectionDialog(parent, title)
    return dialog.result        