# gui codes to use in coordination with moving_lines software
# Copyright 2015 Samuel LeBlanc
import tkSimpleDialog

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
        Modifies the Tkinter Basemap window via calls to plotting
    Dependencies:
        Tkinter
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
                  - added Tkinter dialog classes fopr special gui interactions
                      -initial profile setting of Basemap
                      -select flights/points
                      -move points
                  - added GEOS figure adding with WMS service
    """
    def __init__(self,line=None,root=None,noplt=False):
        import Tkinter as tk
        if not line:
            print 'No line_builder object defined'
            return
        self.line = line
        self.flight_num = 0
        self.iactive = tk.IntVar()
        self.iactive.set(0)
        self.colors = ['red']
        self.colorcycle = ['red','blue','green','cyan','magenta','yellow','black','lightcoral','teal','darkviolet','orange']
        if not root:
            self.root = tk.Tk()
        else:
            self.root = root
        self.noplt = noplt
        self.newflight_off = True
    
    def gui_file_select(self,ext='*',
                        ftype=[('Excel 1997-2003','*.xls'),('Excel','*.xlsx'),
                               ('Kml','*.kml'),('All files','*.*')]):
        """
        Simple gui file select program. Uses TKinter for interface, returns full path
        """
        from Tkinter import Tk
        from tkFileDialog import askopenfilename
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
        from Tkinter import Tk
        from tkFileDialog import asksaveasfilename
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
        from Tkinter import Tk
        from tkFileDialog import askdirectory
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
            print 'No line object'
            return
        filename = self.gui_file_save(ext='.kml',ftype=[('All files','*,*'),('KML','*.kml')])
        if not filename: return
        self.kmlfilename = filename
        self.line.ex.save2kml(filename=self.kmlfilename)
        
    def gui_save2kml(self):
        'Calls the save2kml excel_interface method'
        if not self.line:
            print 'No line object'
            return
        if not self.kmlfilename:
            self.stopandquit()
            print 'Problem with kmlfilename'
            return
        self.line.ex.save2kml(filename=self.kmlfilename)

    def gui_save_txt(self):
        'Calls the save2txt excel_interface method'
        if not self.line:
            print 'No line object'
            return
	import tkMessageBox
        tkMessageBox.showwarning('Saving one flight','Saving flight path of:%s' %self.line.ex.name)
	filename = self.gui_file_save(ext='.txt',ftype=[('All files','*.*'),
                                                         ('Plain text','*.txt')])
        if not filename: return
        print 'Saving Text file to :'+filename
        self.line.ex.save2txt(filename)

    def gui_save_xl(self):
        'Calls the save2xl excel_interface method'
        if not self.line:
            print 'No line object'
            return
        filename = self.gui_file_save(ext='.xlsx',ftype=[('All files','*.*'),
                                                         ('Excel 1997-2003','*.xls'),
                                                         ('Excel','*.xlsx')])
        if not filename: return
        print 'Saving Excel file to :'+filename
        self.line.ex.save2xl(filename)

    def gui_open_xl(self):
        if not self.line:
            print 'No line object'
            return
        filename = self.gui_file_select(ext='.xls',ftype=[('All files','*.*'),
                                                         ('Excel 1997-2003','*.xls'),
                                                         ('Excel','*.xlsx')])
        if not filename: return
        self.line.disconnect()
        self.line.ex.wb.close()
        self.line.tb.set_message('Opening Excel File:'+filename)
        import excel_interface as ex
        self.flight_num = 0
        self.iactive.set(0)
        self.line.ex_arr = ex.populate_ex_arr(filename=filename,colorcycle=self.colorcycle)
        self.line.m.ax.set_title(self.line.ex_arr[0].datestr)
        for b in self.flightselect_arr:
            b.destroy()
        self.flightselect_arr = []
        try:
            self.line.m.figure_under.remove()
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
            print 'No line object'
            return
        filename = self.gui_file_save(ext='.gpx',ftype=[('All files','*.*'),
                                                         ('GPX','*.gpx')])
        if not filename: return
        print 'Saving GPX file to :'+filename
        self.line.ex.save2gpx(filename)
		
    def gui_save2ict(self):
        'Calls the save2ict excel_interface method'
        if not self.line:
            print 'No line object'
            return
        import tkMessageBox
        tkMessageBox.showwarning('Saving one flight','Saving flight path in form of ict for:%s' %self.line.ex.name)
        filepath = self.gui_file_path(title='Select directory to save ict file')
        if not filepath: return
        print 'Saving ICT file to :'+filepath
        self.line.ex.save2ict(filepath)
        
    def gui_plotalttime(self):
        'gui function to run the plot of alt vs. time'
        if self.noplt:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
            from matplotlib.figure import Figure
            import Tkinter as tk
            root = tk.Toplevel()
            root.wm_title('Alt vs. Time')
            fig = Figure()
            canvas = FigureCanvasTkAgg(fig, master=root)
            canvas.show()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            tb = NavigationToolbar2TkAgg(canvas,root)
            tb.pack(side=tk.BOTTOM)
            tb.update()
            canvas._tkcanvas.pack(side=tk.TOP,fill=tk.BOTH,expand=1)
            ax1 = fig.add_subplot(111)
        else:
            print 'Problem with loading a new figure handler'
            return
        ax1.plot(self.line.ex.cumlegt,self.line.ex.alt,'x-')
        ax1.set_title('Altitude vs time for %s on %s' %(self.line.ex.name,self.line.ex.datestr),y=1.08)
	fig.subplots_adjust(top=0.85,right=0.8)
	ax1.set_xlabel('Flight duration [Hours]')
        ax1.set_ylabel('Alt [m]')
        ax1.xaxis.tick_bottom()
        ax2 = ax1.twiny()
        ax2.xaxis.tick_top()
        ax2.set_xlabel('UTC [Hours]')
        ax2.set_xticks(ax1.get_xticks())
	cum2utc = self.line.ex.utc[0]
	utc_label = ['%2.2f'%(u+cum2utc) for u in ax1.get_xticks()]
	ax2.set_xticklabels(utc_label)
	ax3 = ax1.twinx()
	ax3.yaxis.tick_right()
	ax3.set_ylabel('Altitude [Kft]')
	ax3.set_yticks(ax1.get_yticks())
	alt_labels = ['%2.2f'%(a*3.28084/1000.0) for a in ax1.get_yticks()]
	ax3.set_yticklabels(alt_labels)
	ax1.grid()
        if self.noplt:
            canvas.draw()
        else:
            plt.figure(f1.number)
        return fig

    def gui_plotsza(self):
        'gui function to plot the solar zenith angle of the flight path'
        #import tkMessageBox
        #tkMessageBox.showwarning('Sorry','Feature not yet implemented') 
        #return 
        if not self.noplt:
             print 'No figure handler, sorry will not work'
             return
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
        from matplotlib.figure import Figure
        import Tkinter as tk
        root = tk.Toplevel()
        root.wm_title('Solar position vs. Time')
        root.geometry('800x550')
        fig = Figure()
        canvas = FigureCanvasTkAgg(fig, master=root)
        canvas.show()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        tb = NavigationToolbar2TkAgg(canvas,root)
        tb.pack(side=tk.BOTTOM)
        tb.update()
        canvas._tkcanvas.pack(side=tk.TOP,fill=tk.BOTH,expand=1)
        ax1 = fig.add_subplot(2,1,1)
        ax1.plot(self.line.ex.cumlegt,self.line.ex.sza,'x-')
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
        ax2.set_ylabel('Azimuth angle [degree]')
        ax2.set_xlabel('Flight duration [Hours]')
        ax2.grid()
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
	import Tkinter as tk
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
        import tkSimpleDialog,tkMessageBox
        import excel_interface as ex
        import Tkinter as tk
        if self.newflight_off:
	     tkMessageBox.showwarning('Sorry','Feature not yet implemented')
             return
        
        newname = tkSimpleDialog.askstring('New flight path',
                                           'New flight path name:')
        if not newname:
            print 'Cancelled'
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
        print 'adding flight path to date: %s' %self.line.ex.datestr
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
        import tkSimpleDialog,tkMessageBox
        tkMessageBox.showwarning('Sorry','Feature not yet implemented')
        return
        import excel_interface as ex
        import Tkinter as tk
        from gui import Select_flights
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
            import tkMessageBox
            tkMessageBox.showwarning('Sorry','Feature not yet implemented')
            return
        self.flightselect_arr[self.iactive.get()].select()
        self.line.iactive = self.iactive.get()
        self.line.ex = self.line.ex_arr[self.iactive.get()]
        self.line.makegrey()
        self.line.line = self.line.line_arr[self.iactive.get()]
        self.line.ex.switchsheet(self.iactive.get())
        self.line.colorme(self.colors[self.iactive.get()])
        self.line.get_bg()
        
    def gui_savefig(self):
        'gui program to save the current figure as png'
        if not self.line:
            print 'No line object'
            return
        filename = self.gui_file_save(ext='.png')
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
        filename = self.gui_file_save(ext='*',ftype=[('Excel','*.xlsx')])
        if not filename:
            tkMessageBox.showwarning('Cancelled','Saving all files cancelled')
            return
        f_name,_ = path.splitext(filename)
        print 'Saving Excel file to :'+f_name+'.xlsx'
        self.line.ex.save2xl(f_name+'.xlsx')
        print 'Saving figure file to :'+f_name+'_map.png'
        if type(self.line.line) is list:
            lin = self.line.line[0]
        else:
            lin = self.line.line
        legend,grey_index = self.prep_mapsave()
        lin.figure.savefig(f_name+'_map.png',dpi=600,transparent=False)
        # go through each flight path
        for i,x in enumerate(self.line.ex_arr):
            self.iactive.set(i)
            self.gui_changeflight()
            print 'Saving Text file to :'+f_name+'_{}.txt'.format(x.name)
            self.line.ex.save2txt(f_name+'_{}.txt'.format(x.name))
            print 'Saving ICT file to :'+path.dirname(f_name)
            self.line.ex.save2ict(path.dirname(f_name))
            print 'Generating the figures for {}'.format(x.name)
            fig = self.gui_plotalttime()
            print 'Saving the Alt vs time plot at:'+f_name+'_alt_{}.png'.format(x.name)
            fig.savefig(f_name+'_alt_{}.png'.format(x.name),dpi=600,transparent=False)
            fig = self.gui_plotsza()
            print 'Saving the SZA vs time plot at:'+f_name+'_sza_{}.png'.format(x.name)
            fig.savefig(f_name+'_sza_{}.png'.format(x.name),dpi=600,transparent=False)
        print 'Saving kml file to :'+f_name+'.kml'
        self.kmlfilename = f_name+'.kml'
        self.line.ex.save2kml(filename=self.kmlfilename)
        self.return_map(legend,grey_index)
        
    def stopandquit(self):
        'function to force a stop and quit the mainloop, future with exit of python'
        self.root.quit()
        self.root.destroy()
        self.line.ex.wb.close()
        #import sys
        #sys.exit()

    def refresh(self):
        'function to force a refresh of the plotting window'
        self.line.onfigureenter([1])
        self.line.get_bg()
    
    def make_gui(self):
        """
        make the gui with buttons
        """
        import Tkinter as tk
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
        from gui import Move_point
        m = Move_point(speed=self.line.ex.speed[-1])
        self.line.newpoint(m.bear,m.dist)

    def gui_movepoints(self):
        'GUI button to move many points at once'
        from gui import Select_flights,Move_point
        wp_arr = []
        for w in self.line.ex.WP:
            wp_arr.append('WP #%i'%w)
        p = Select_flights(wp_arr,title='Move points',Text='Select points to move:')
        m = Move_point()
        self.line.moving = True
        for i,val in enumerate(p.result):
            if val:
                self.line.movepoint(i,m.bear,m.dist,last=False)
        self.line.movepoint(0,0,0,last=True)
        self.line.moving = False
        
    def gui_addsat(self):
        'Gui button to add the satellite tracks'
        from tkMessageBox import askquestion
        answer = askquestion('Verify import satellite tracks','Do you want to get the satellite tracks from the internet?')
        if answer == 'yes':
            from map_interactive import load_sat_from_net, get_sat_tracks, plot_sat_tracks
            self.line.tb.set_message('Loading satellite kml File from internet')
            kml = load_sat_from_net()
            if kml:
                self.line.tb.set_message('parsing file...')
                sat = get_sat_tracks(self.line.ex.datestr,kml)
                self.line.tb.set_message('Plotting satellite tracks')
                self.sat_obj = plot_sat_tracks(self.line.m,sat)
        elif answer ==  'no':
            from map_interactive import load_sat_from_file, get_sat_tracks, plot_sat_tracks
            filename = self.gui_file_select(ext='.kml',ftype=[('All files','*.*'),
                                                         ('Google Earth','*.kml')])
            if not filename:
                print 'Cancelled, no file selected'
                return
            self.line.tb.set_message('Opening kml File:'+filename)
            kml = load_sat_from_file(filename)
            self.line.tb.set_message('parsing file...')
            sat = get_sat_tracks(self.line.ex.datestr,kml)
            self.line.tb.set_message('Plotting satellite tracks') 
            self.sat_obj = plot_sat_tracks(self.line.m,sat)
        self.line.get_bg()

    def gui_addsat_tle(self):
        'Gui button to add the satellite tracks'
        from map_interactive import get_sat_tracks_from_tle, plot_sat_tracks
        self.line.tb.set_message('Loading satellite info from sat.tle file')
        sat = get_sat_tracks_from_tle(self.line.ex.datestr)
        self.line.tb.set_message('Plotting Satellite tracks')
        self.sat_obj = plot_sat_tracks(self.line.m,sat)
        self.line.get_bg(redraw=True)


    def gui_addbocachica(self):
        'GUI handler for adding bocachica foreacast maps to basemap plot'
	import tkMessageBox
	try:
            from scipy.misc import imread
            filename = self.gui_file_select(ext='.png',ftype=[('All files','*.*'),
                        				  ('PNG','*.png')])
	    if not filename:
		print 'Cancelled, no file selected'
		return
            print 'Opening png File:'+filename
            img = imread(filename)
	except:
            tkMessageBox.showwarning('Sorry','Loading image file from Bocachica not working...')
            return
	ll_lat,ll_lon,ur_lat,ur_lon = -40.0,-30.0,10.0,40.0
	self.line.addfigure_under(img[42:674,50:1015,:],ll_lat,ll_lon,ur_lat,ur_lon)
	#self.line.addfigure_under(img[710:795,35:535,:],ll_lat-7.0,ll_lon,ll_lat-5.0,ur_lon-10.0,outside=True)

    def gui_addfigure(self,ll_lat=None,ll_lon=None,ur_lat=None,ur_lon=None):
        'GUI handler for adding figures forecast maps to basemap plot'
        import tkSimpleDialog
        try:
            from scipy.misc import imread
            import PIL
            filename = self.gui_file_select(ext='.png',ftype=[('All files','*.*'),
                                                          ('PNG','*.png'),
							  ('JPEG','*.jpg'),
							  ('GIF','*.gif')])
            if not filename:
                print 'Cancelled, no file selected'
                return
            print 'Opening png File: %s' %filename
            img = imread(filename)
        except:
            import tkMessageBox
            tkMessageBox.showwarning('Sorry','Error occurred unable to load file')
            return
	# get the corners
	if not ll_lat:
	    ll_lat = tkSimpleDialog.askfloat('Lower left lat','Lower left lat? [deg]')
	    ll_lon = tkSimpleDialog.askfloat('Lower left lon','Lower left lon? [deg]')
	    ur_lat = tkSimpleDialog.askfloat('Upper right lat','Upper right lat? [deg]')
	    ur_lon = tkSimpleDialog.askfloat('Upper right lon','Upper right lon? [deg]')
	self.line.addfigure_under(img,ll_lat,ll_lon,ur_lat,ur_lon)

    def gui_addgeos(self,website='http://wms.gsfc.nasa.gov/cgi-bin/wms.cgi?project=GEOS.fp.fcst.inst1_2d_hwl_Nx'):
        'GUI handler for adding the figures from WMS support of GEOS'
        from gui import Popup_list
        try:
            from owslib.wms import WebMapService
            from owslib.util import openURL
            from StringIO import StringIO
            from PIL import Image
            self.line.tb.set_message('Loading WMS from :'+website.split('/')[2])
            wms = WebMapService(website)
            cont = list(wms.contents)
        except Exception as ie:
            print ie
            import tkMessageBox
            tkMessageBox.showwarning('Sorry','Loading WMS map file from '+website.split('/')[2]+' servers not working...')
            return
        titles = [wms[c].title for c in cont]
        arr = [x.split('-')[-1]+':  '+y for x,y in zip(cont,titles)]
        i = Popup_list(arr)
        self.line.tb.set_message('Selected WMS map: '+titles[i].split(',')[-1])
        if wms[cont[i]].timepositions:
            times = wms[cont[i]].timepositions
            j = Popup_list(times)
            time_sel = times[j]
        else:
            time_sel = None
        try:
            if not time_sel:
                time_sel = self.line.ex.datestr+'T12:00'
            ylim = self.line.line.axes.get_ylim()
            xlim = self.line.line.axes.get_xlim()
            #img = wms.getdata(layers=[cont[i]],
            #                  bbox=(ylim[0],xlim[0],ylim[1],xlim[1]),
            #                  size=(480,240),
            #                  transparent=True,
            #                  time=time_sel,
            #                  srs='EPSG:4326',
            #                  format='image/png')
            #leg_call = openURL(img.geturl().replace('GetMap','GetLegend'))
            img = wms.getdata(layers=[cont[i],'countries'],
                              bbox=(ylim[0],xlim[0],ylim[1],xlim[1]),
                              size=(480,240),
                              transparent=True,
                              time=time_sel,
                              srs='EPSG:4326',
                              format='image/png')
            geos = Image.open(StringIO(img.read()))
            self.line.addfigure_under(geos,xlim[0],ylim[0],xlim[1],ylim[1])
            #self.line.line.figure.add
            #leg = Image.open(StringIO(leg_call.read()))
            #self.line.addfigure_under(leg,xlim[0],ylim[0],xlim[1],ylim[1],outside=True)
        except:
            import tkMessageBox
            tkMessageBox.showwarning('Sorry','Problem getting the image to load')
            return
            
    def gui_flt_module(self):
        'Program to load the flt_module files and select'
        from map_interactive import get_flt_modules
        from gui import Select_flt_mod
        flt_mods = get_flt_modules()
        select = Select_flt_mod(flt_mods)
        print 'Applying the flt_module {}'.format(select.selected_flt)
        self.line.parse_flt_module_file(select.mod_path)
            
class Select_flt_mod(tkSimpleDialog.Dialog):
    """
       Dialog box pop up that lists the available flt_modules. 
       If possible it will show a small png of the flt_module (not done yet)
    """
    import Tkinter as tk
    def __init__(self,flt_mods,title='Choose flt module',text='Select flt module:'):
        import Tkinter as tk
        parent = tk._default_root
        self.flt_mods = flt_mods
        self.text = text
        tkSimpleDialog.Dialog.__init__(self,parent,title)
        pass
    def body(self,master):
        import Tkinter as tk
        self.rbuttons = []
        self.flt = tk.StringVar()
        tk.Label(master, text=self.text).grid(row=0)
        for i,l in enumerate(self.flt_mods.keys()):
            self.rbuttons.append(tk.Radiobutton(master,text=l, variable=self.flt,value=l))
            self.rbuttons[i].grid(row=i+1,sticky=tk.W)
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
        import Tkinter as tk
        if not parent:
            parent = tk._default_root
        self.pt_list = pt_list
        self.Text = Text
        tkSimpleDialog.Dialog.__init__(self,parent,title)
        pass
    
    def body(self,master):
        import tkSimpleDialog
        import Tkinter as tk
        self.results = []
        tk.Label(master, text=self.Text).grid(row=0)
        self.cbuttons = []
        for i,l in enumerate(self.pt_list):
            var = tk.IntVar()
            self.results.append(var)
            self.cbuttons.append(tk.Checkbutton(master,text=l, variable=var))
            self.cbuttons[i].grid(row=i+1,sticky=tk.W)
        return

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
    """
    def __init__(self,title='New point info',speed=None):
        import Tkinter as tk
        self.speed = speed
        parent = tk._default_root
        tkSimpleDialog.Dialog.__init__(self,parent,title)
        pass
    
    def body(self,master):
        import tkSimpleDialog
        import Tkinter as tk
        tk.Label(master, text='Enter Distance [km]').grid(row=0)
        tk.Label(master, text='Enter Bearing, 0-360, [degrees CW from North]').grid(row=1)
        self.edist = tk.Entry(master)
        self.ebear = tk.Entry(master)
        self.edist.grid(row=0,column=1)
        self.ebear.grid(row=1,column=1)
        if self.speed:
            self.speed = self.speed*3.6
            tk.Label(master,text='or').grid(row=0,column=2)
            tk.Label(master,text='Time [h]').grid(row=0,column=3)
            self.etime = tk.Entry(master)
            self.etime.grid(row=0,column=4)
        return self.edist

    def apply(self):
        try:
            self.dist = float(self.edist.get())
        except:
            self.dist = float(self.speed)*float(self.etime.get())
        self.bear = float(self.ebear.get())
        return self.dist,self.bear

    def validate(self):
        try:
            self.dist = float(self.edist.get())
            self.bear = float(self.ebear.get())
        except ValueError:
            if self.speed:
                try:
                    self.time = float(self.etime.get())
                    self.bear = float(self.ebear.get())
                except ValueError:
                    import tkMessageBox
                    tkMessageBox.showwarning('Bad input','Can not format values, try again')
            else:
                import tkMessageBox
                tkMessageBox.showwarning('Bad input','Can not format values, try again')
        return True

class ask(tkSimpleDialog.Dialog):
    """
    Simple class to ask to enter values for each item in names
    """
    def __init__(self,names,title='Enter numbers'):
        import Tkinter as tk
        self.names = names
        parent = tk._default_root
        tkSimpleDialog.Dialog.__init__(self,parent,title)
        pass
    def body(self,master):
        import Tkinter as tk
        self.fields = range(len(self.names))
        for i,n in enumerate(self.names):
            tk.Label(master,text=n).grid(row=i)
            self.fields[i] = tk.Entry(master)
            self.fields[i].grid(row=i,column=1)
    def apply(self):
        self.names_val = range(len(self.names))
        for i,n in enumerate(self.names):
            self.names_val[i] = float(self.fields[i].get())
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
    def __init__(self,default_profiles,title='Enter map defaults'):
        import Tkinter as tk
        self.default_profiles = default_profiles
        self.profile = self.default_profiles[0]
        parent = tk._default_root
        tkSimpleDialog.Dialog.__init__(self,parent,title)
        
    
    def body(self,master):
        import tkSimpleDialog
        import Tkinter as tk
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

        tk.Label(master, text='UTC Start:').grid(row=7,sticky=tk.E)
        self.start_utc = tk.Entry(master)
        self.start_utc.grid(row=7,column=1,columnspan=2)

        tk.Label(master, text='UTC conversion:').grid(row=8,sticky=tk.E)
        self.utc_convert = tk.Entry(master)
        self.utc_convert.grid(row=8,column=1,columnspan=2)

        tk.Label(master, text='Start Alt:').grid(row=9,sticky=tk.E)
        self.start_alt = tk.Entry(master)
        self.start_alt.grid(row=9,column=1,columnspan=2)

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
                self.set_val(self.start_utc,p['UTC_start'])
                self.set_val(self.utc_convert,p['UTC_conversion'])
                self.set_val(self.start_alt,p['start_alt'])

    def set_val(self,e,val):
        'Simple program to delete the value and replace with current value'
        import Tkinter as tk
        e.delete(0,tk.END)
        e.insert(tk.END,val)
    
    def apply(self):
        self.profile = {'Plane_name':self.name.get(),
                        'Start_lon':self.start_lon.get(),
                        'Start_lat':self.start_lat.get(),
                        'Lon_range':[self.lon0.get(),self.lon1.get()],
                        'Lat_range':[self.lat0.get(),self.lat1.get()],
                        'UTC_start':float(self.start_utc.get()),
                        'UTC_conversion':float(self.utc_convert.get()),
                        'start_alt':float(self.start_alt.get()),
                        'Campaign':self.pname.get()
                        }
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
        import tkMessageBox
        if not self.check_input(self.name.get(),1):
            tkMessageBox.showwarning('Bad input','Plane name error, try again')
            return False
        if not self.check_input(self.start_lon.get(),0):
            tkMessageBox.showwarning('Bad input','Start Lon error, try again')
            return False
        if not self.check_input(self.start_lat.get(),0):
            tkMessageBox.showwarning('Bad input','Start Lat error, try again')
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
            import tkMessageBox
            tkMessageBox.showwarning('Bad input','Can not format values, try again')
            return False
        return True

def Popup_list(arr):
    """
    Purpose:
        Popup box that offers selection of list
        Whatever is clicked, the window closes and returns the resulting index
    Inputs:
        arr: list of text values
    Outputs:
        index value of selection
    Dependencies:
        Tkinter
    MOdifications:
        written: Samuel LeBlanc, 2015-09-16, NASA Ames, CA
    """
    import Tkinter as tk
    top = tk.Toplevel()
    lb = tk.Listbox(top)
    lb.config(width=0)
    lb.config(height=20)
    for i,e in enumerate(arr):
        lb.insert(tk.END,e)
    top.winfo_toplevel().wm_geometry("")
    scroll = tk.Scrollbar(top)
    scroll.pack(side=tk.RIGHT,fill=tk.Y)
    lb.config(yscrollcommand=scroll.set)
    scroll.config(command=lb.yview)
    var = tk.IntVar()
    def func(e):
        value, = lb.curselection()
        var.set(value)
        top.after(50,top.destroy())
    lb.bind('<<ListboxSelect>>',func)
    lb.pack()
    return var.get()
    

