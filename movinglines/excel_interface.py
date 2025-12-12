# Excel Interface codes to be used in coordination with moving_lines flight planning software
# Copyright 2015 Samuel LeBlanc

import numpy as np
from xlwings import Range
from datetime import datetime
from scipy import interpolate

import sys
#reload(sys)
#sys.setdefaultencoding('utf8')
try:
    import map_interactive as mi
    from map_interactive import pll
    import map_utils as mu
    import write_utils as wu
except ModuleNotFoundError:
    from . import map_interactive as mi
    from .map_interactive import pll
    from . import map_utils as mu
    from . import write_utils as wu

class dict_position:
    """
    Purpose:
        Class that creates an easy storage for position coordinates.
        Encompasses array values of positions, altitude, time, dist.
        Along with program to update excel spreadsheet with info, read spreadsheet data,
        and update calculations for distances
    Inputs: (at init)
        lon0: [degree] initial longitude (optional, defaults to Namibia Walvis bay airport), can be string
        lat0: [degree] initial latitude (optional, defaults to Namibia Walvis bay airport), can be string
        speed: [m/s] speed of aircraft defaults to p3 value of 150 m/s (optional)
        UTC_start: [decimal hours] time of takeoff, defaults to 7.0 UTC (optional)
        UTC_conversion: [decimal hours] conversion (dt) used to change utc to local time (optional), local = utc + dt
        alt0: [m] initial altitude of the plane, airport altitude (optional)
        verbose: if True then outputs many command line comments while interaction is executed, defaults to False
        filename: (optional) if set, opens the excel file and starts the interaction with the first sheet
        datestr: (optional) The flight day in format YYYY-MM-DD, if not set, default to today in utc.
        color: (optional) the color of the flight path defaults to red.
        sheet_num: (optional, defaults to 1) the sheet number to switch to
        profile: (optional) if set, uses a dict of basemap profile to set for the initial lat lons, alt, utc_start, utc_conversion, name
    Outputs:
        dict_position class 
    Dependencies:
        numpy
        xlwings
        Excel (win or mac)
        map_interactive
        map_utils
        simplekml
        gpxpy
        tempfile
        os
        datetime
        Pyephem
    Required files:
        none
    Example:
        ...
    Modification History:
        Written: Samuel LeBlanc, 2015-08-07, Santa Cruz, CA
        Modified: Samuel LeBlanc, 2015-08-11, Santa Cruz, CA
                 - update and bug fixes
        Modified: Samuel LeBlanc, 2015-08-14, NASA Ames, CA
                - added save to kml functionality
        Modified: Samuel LeBlanc, 2015-08-18, NASA Ames, CA
                - added open excel functionality via the filename option and extra method
        Modified: Samuel LeBlanc, 2015-08-21, Santa Cruz, CA
                - added save to GPX functionality
                - added datestr for keeping track of flight days
                - added functionality for comments and space for sza/azi
        Modified: Samuel LeBlanc, 2015-08-24, Santa Cruz, CA
                - added multi flight path handling funcitonality, by generating new sheets
                - added newsheetonly keyword and name keyword
        Modified: Samuel LeBlanc, 2015-09-02, Santa Cruz, CA
                - added color keyword
        Modified: Samuel LeBlanc, 2015-09-10, NASA Ames, Santa Cruz, CA
	        - added init codes for loading a single sheet of a workbook
        Modified: Samuel LeBlanc, 2015-09-15, NASA Ames, CA
                    - added handling of the profile dict of lat lon and starting positions
        Modified: Samuel LeBlanc, 2016-07-10, NASA Ames, from Santa Cruz, CA
                 - added handling of platform info from external files.
                 - added bearing info to excel file and flight planning version info with date
        Modified: Samuel LeBlanc, 2016-07-22, NASA Ames, from Santa Cruz, CA
                 - modified kml saving to also save a kmz with included icons
                 - modified kml/kmz to have the altitude and link to ground set.
                 - removed dependency of Pysolar, fixed bug in azimuth calculations
        Modified: Samuel LeBlanc, 2016-07-28, NASA Ames, CA
                 - fixed utc convertion issue when reading in an excel file
        Modified: Samuel LeBlanc, 2016-08-25, NASA P3, transit from Barbados to Ascension
                 - added inserts method to insert a point in between other points.
        Modified: Samuel LeBlanc, 2016-08-30, Swakopmund, Namibia
                 - added a force speed calculation
        Modified: Samuel LeBlanc, 2016-08-31, Swakopmund, Namibia
                 - fixed saving for pilots, added delay time in comments
        Modified: Samuel LeBlanc, 2019-06-03, Santa Cruz, CA
                 - Calc_climb_time typo in reading platform.txt file.
        Modified: Samuel LeBlanc, 2021-10-22, Santa Cruz, CA
                 - Made into python3 compatible
                 - using the new xlwings (v.0.24) api instead of pre-0.9
                 - added compatibility with macos
        Modified: Samuel LeBlanc, 2021-11-08, Santa Cruz, CA
                 - Bug fix for end points not being deleted properly
        Modified: Samuel LeBlanc, 2024-02-19, Santa Cruz, CA
                 - Fix to ensure max speed is not reached at any Alt.
                 - Fix for first point of the file matches expected base speed for aircraft.
    """
    def __init__(self,lon0='14 38.717E',lat0='22 58.783S',speed=130.0,UTC_start=7.0,
                 UTC_conversion=+1.0,alt0=0.0,
                 verbose=False,filename=None,datestr=None,datestr_verified=False,
                 newsheetonly=False,name='P3 Flight path',sheet_num=1,color='red',
                 profile=None,campaign='None',version='v1.09',platform_file='platform.txt'):
        import numpy as np
        import xlwings as xw
        from datetime import datetime
        import os

        try:
            import map_interactive as mi
            from map_interactive import pll
            import map_utils as mu
        except ModuleNotFoundError:
            from . import map_interactive as mi
            from .map_interactive import pll
            from . import map_utils as mu
        if profile:
            lon0,lat0,UTC_start = profile['Start_lon'],profile['Start_lat'],profile['UTC_start']
            UTC_conversion,alt0,name,campaign = profile['UTC_conversion'],profile['start_alt'],profile['Plane_name'],profile['Campaign']
            self.profile = profile
        self.__version__ = version
        self.datestr_cell = 'AB1'
        self.comments = [' ']
        self.wpname = [' ']
        self.lon = np.array([pll(lon0)])
        self.lat = np.array([pll(lat0)])
        self.n = len(self.lon)
        self.speed = np.array([speed])
        self.alt = np.array([alt0])
        self.UTC_conversion = UTC_conversion
        self.utc = np.array([UTC_start])
        self.UTC = self.utc
        self.local = self.utc+self.UTC_conversion
        self.legt = self.UTC*0.0
        self.dist = self.UTC*0.0
        self.dist_nm = self.dist*0.53996
        self.cumdist_nm = self.UTC*0.0
        self.cumdist = self.UTC*0.0
        self.cumlegt = self.legt
        self.delayt = self.legt
        self.bearing = self.lon*0.0
        self.endbearing = self.lon*0.0
        self.turn_deg = self.lon*0.0
        self.turn_time = self.lon*0.0
        self.turn_type = [' ']
        self.climb_time = self.lon*0.0
        self.sza = self.lon*0.0
        self.azi = self.lon*0.0
        self.datetime = self.lon*0.0
        self.speed_kts = self.speed*1.94384449246
        self.alt_kft = self.alt*3.28084/1000.0
        self.head = self.legt
        self.headwind = self.lon*0.0
        self.headwind_kts = self.headwind*1.94384449246
        self.timepoint = self.UTC*0.0
        self.color = color
        self.googleearthopened = False
        self.netkml = None
        self.verbose = verbose
        self.name = name
        self.campaign = campaign
        self.datestr_verified = datestr_verified
        self.platform, self.p_info,use_file = self.get_platform_info(name,platform_file)
        if profile:
            for k in profile:
                if k not in self.p_info:
                    self.p_info[k] = profile[k]
        self.pilot_format = self.p_info.get('pilot_format','DD MM SS')
        if use_file:
            print('Using platform data for: {} from platform file: {}'.format(self.platform,os.path.abspath(platform_file)))
        else:
            print('Using platform data for: {} from internal defaults'.format(self.platform))

        if datestr:
            self.datestr = datestr
        else:
            self.datestr = datetime.utcnow().strftime('%Y-%m-%d')
        if not filename:
            self.sheet_num = sheet_num
            self.speed = np.array([self.calcspeed(alt0,alt0)])
            self.speed_kts = self.speed*1.94384449246
            self.calculate()
            self.wb = self.Create_excel(newsheetonly=newsheetonly,name=name)
            try:
                self.write_to_excel()
            except:
                print('writing to excel failed')
        else:
            self.wb = self.Open_excel(filename=filename,sheet_num=sheet_num,campaign=campaign,platform_file=platform_file)
            self.check_xl()
            self.calculate()
            self.write_to_excel()
        self.sheet_num = sheet_num
        
    def get_platform_info(self,name,filename):
        """
        Function that reads the platform info from seperate file. 
        If sucessfuly uses these info to prepare speeds, altitudes, climb time, turn time, and others
        
        """
        try:
            from ml import read_prof_file
        except ModuleNotFoundError:
            from .ml import read_prof_file
        import tkinter.messagebox as tkMessageBox
        import os 
        platform = None
        p_info = None
        use_file = False
        try:
            p = read_prof_file(filename)
            for d in p:
                if any(o in name for o in d['names']):
                    platform = d['Platform']
                    p_info = d
                    use_file = True
                    break
            if not p_info:
                tkMessageBox.showwarning('Platform not found','Platform values not found in file: {}.\nUsing internal defaults.'.format(filename))
                platform = self.check_platform(name)
                p_info = self.default_p_info(platform)
        except IOError:
            print('** Error reading platform information file: {} **'.format(os.path.abspath(filename)))
            try:
                try:
                    from gui import gui_file_select_fx
                except ModuleNotFoundError:
                    from .gui import gui_file_select_fx
                filename_new = gui_file_select_fx(ext='platform.txt',ftype=[('All files','*.*'),('Platform file','*.txt')])
                p = read_prof_file(filename_new)
                for d in p:
                    if any(o in name for o in d['names']):
                        platform = d['Platform']
                        p_info = d
                        use_file = True
                        break
            except IOError:
                print('** Error reading platform information file: {} **'.format(os.path.abspath(filename)))
                print('** Using default platform profiles **')
                platform = self.check_platform(name)
                p_info = self.default_p_info(platform)
        if p_info['warning']:
            tkMessageBox.showwarning('Check needed','Platform default speeds and altitude may be off for {}. Please double check.'.format(platform))
        return platform, p_info, use_file
            
    def default_p_info(self,platform):
        'function that returns the default dict of platform info'
        if platform=='p3':
            p_info = {'Platform':'p3','names':['p3','P3','P-3','p-3','p 3','P 3'],
                      'max_alt':7000.0,'base_speed':110.0,'speed_per_alt':0.0070,
                      'max_speed':155.0,'max_speed_alt':5000.0,'descent_speed_decrease':15.0,
                      'climb_vert_speed':5.0,'descent_vert_speed':-5.0,'alt_for_variable_vert_speed':6000.0,
                      'vert_speed_base':4.5,'vert_speed_per_alt':7e-05,
                      'rate_of_turn':None,'turn_bank_angle':15.0,
                      'warning':False}
        elif platform=='er2':
            p_info = {'Platform':'er2','names':['er2','ER2','ER-2','er-2','ER 2','er 2'],
                        'max_alt':19000.0,'base_speed':70.0,'speed_per_alt':0.0071,
                        'max_speed':300.0,'max_speed_alt':30000.0,'descent_speed_decrease':0.0,
                        'climb_vert_speed':10.0,'descent_vert_speed':-10.0,'alt_for_variable_vert_speed':0.0,
                        'vert_speed_base':24.0,'vert_speed_per_alt':0.0011,
                        'rate_of_turn':None,'turn_bank_angle':15.0,
                        'warning':False}
        elif platform=='dc8':
            p_info = {'Platform':'dc8','names':['dc8','DC8','DC-8','dc-8','DC 8','dc 8'],
                        'max_alt':13000.0,'base_speed':130.0,'speed_per_alt':0.0075,
                        'max_speed':175.0,'max_speed_alt':6000.0,'descent_speed_decrease':15.0,
                        'climb_vert_speed':15.0,'descent_vert_speed':-10.0,'alt_for_variable_vert_speed':0.0,
                        'vert_speed_base':15.0,'vert_speed_per_alt':0.001,
                        'rate_of_turn':None,'turn_bank_angle':15.0,
                        'warning':False}
        elif platform=='c130':
            p_info = {'Platform':'c130','names':['c130','C130','C-130','c-130','C 130','c 130'],
                        'max_alt':7500.0,'base_speed':130.0,'speed_per_alt':0.0075,
                        'max_speed':175.0,'max_speed_alt':6000.0,'descent_speed_decrease':15.0,
                        'climb_vert_speed':10.0,'descent_vert_speed':-10.0,'alt_for_variable_vert_speed':0.0,
                        'vert_speed_base':10.0,'vert_speed_per_alt':0.001,
                        'rate_of_turn':None,'turn_bank_angle':20.0,
                        'warning':False}
        elif platform=='bae146':
            p_info = {'Platform':'bae146','names':['bae','BAE','146'],
                        'max_alt':8500.0,'base_speed':130.0,'speed_per_alt':0.002,
                        'max_speed':150.0,'max_speed_alt':8000.0,'descent_speed_decrease':15.0,
                        'climb_vert_speed':5.0,'descent_vert_speed':-5.0,'alt_for_variable_vert_speed':8000.0,
                        'vert_speed_base':4.5,'vert_speed_per_alt':7e-05,
                        'rate_of_turn':None,'turn_bank_angle':20.0,
                        'warning':True}
        elif platform=='ajax':
            p_info = {'Platform':'ajax','names':['ajax','Ajax','AJAX','alphajet','alpha','alpha-jet'],
                        'max_alt':9500.0,'base_speed':160.0,'speed_per_alt':0.09,
                        'max_speed':250.0,'max_speed_alt':9000.0,'descent_speed_decrease':5.0,
                        'climb_vert_speed':5.0,'descent_vert_speed':-5.0,'alt_for_variable_vert_speed':8000.0,
                        'vert_speed_base':4.5,'vert_speed_per_alt':7e-05,
                        'rate_of_turn':None,'turn_bank_angle':25.0,
                        'warning':True}
        else:
            p_info = {'Platform':'p3','names':['p3','P3','P-3','p-3','p 3','P 3'],
                      'max_alt':7000.0,'base_speed':110.0,'speed_per_alt':0.007,
                      'max_speed':155.0,'max_speed_alt':5000.0,'descent_speed_decrease':15.0,
                      'climb_vert_speed':5.0,'descent_vert_speed':-5.0,'alt_for_variable_vert_speed':6000.0,
                      'vert_speed_base':4.5,'vert_speed_per_alt':7e-05,
                      'rate_of_turn':None,'turn_bank_angle':15.0,
                      'warning':True}
        return p_info
        
    def check_platform(self,name):
        'Simple program that check the name of the flight path to platforms names'
        if any(p in name for p in ['p3','P3','P-3','p-3','p 3','P 3']): platform = 'p3'
        if any(p in name for p in ['er2','ER2','ER-2','er-2','ER 2','er 2']): platform = 'er2'
        if any(p in name for p in ['dc8','DC8','DC-8','dc-8','DC 8','dc 8']): platform = 'dc8'
        if any(p in name for p in ['c130','C130','C-130','c-130','C 130','c 130']): platform = 'c130'
        if any(p in name for p in ['bae','BAE','146']): platform = 'bae146'
        try:
            if not platform: platform = 'NA'
        except UnboundLocalError:
            platform = 'NA'
        return platform
        
    def get_rate_of_turn(self,i=0):
        'Function to calculate the rate of turn of the plane'
        if self.p_info.get('rate_of_turn'):
            rate_of_turn = self.p_info.get('rate_of_turn')
        elif self.p_info.get('turn_bank_angle'):
            rate_of_turn = 1091.0*np.tan(self.p_info['turn_bank_angle']*np.pi/180)/self.speed_kts[i]
        else:            
            default_bank_angle = 15.0
            rate_of_turn = 1091.0*np.tan(default_bank_angle*np.pi/180)/self.speed_kts[i] # degree per second
        return rate_of_turn
        
    def get_time_to_fly_turn_radius_by_turn_type(self,i=0,turn_type='flyby'):
        'Function to calculate the time in minutes to fly the radius of the turn, to account for extra time needed in flying that distance from turn, Dependent on type of turn (can be negative)'
        kts_to_ftpermin = 101.269
        if self.turn_deg[i]<15:
            return 0
        if np.isfinite(self.speed_kts[i]):
            speed_kts = self.speed_kts[i]
        elif self.p_info.get('max_speed'):
            speed_kts = self.p_info.get('max_speed')*1.94384449246
        else:
            speed_kts = 150.0
        
        if self.p_info.get('turn_bank_angle'):
            turn_radius = speed_kts*speed_kts/(11.26*np.tan(self.p_info['turn_bank_angle']*np.pi/180.0)) #in feet
        else:
            turn_radius = speed_kts*speed_kts/(11.26*np.tan(20.0*np.pi/180.0)) #in feet
        if turn_type=='flyby':
            #calculate the distance of the cut corner
            cut_length = 2.0*turn_radius/np.sin(self.turn_deg[i]*np.pi/180.0)
            delta_time = cut_length*(-2.0) / (speed_kts*kts_to_ftpermin)
        elif turn_type=='over':
            #here the the additionaly distance is when turn is immediatly started, then turned back to path, so about another turn radius distance
            delta_time = 0.66*turn_radius/(speed_kts * kts_to_ftpermin)
        elif turn_type=='90-270':
            #here the time is for one basically an extra 2 radius (total of 2 out, 2 in)
            delta_time = 1.0*(turn_radius/(speed_kts * kts_to_ftpermin))
        else:
            delta_time = 0.0
        
        if abs(delta_time)>30:
            print(f'*** Issue with time calculation for turn {i} - setting max turn time to 30 minutes - currently at: {delta_time} ***')
            sign = np.sign(delta_time) 
            delta_time = 30*sign
            
        return turn_radius/(speed_kts * kts_to_ftpermin)+delta_time #convert knots to feet per minute, then return minutes

    def calculate(self):
        """
        Program to fill in all the missing pieces in the dict_position class
        Involves converting from metric to aviation units
        Involves calculating distances
        Involves calculating time of flight local and utc
        Fills in the waypoint numbers

        Assumes that blank spaces/nan are to be filled with new calculations
        """
        self.n = len(self.lon)
        self.WP = range(1,self.n+1)
        previous_spiral = False
        for i in range(self.n-1):
            self.dist[i+1] = mu.spherical_dist([self.lat[i],self.lon[i]],[self.lat[i+1],self.lon[i+1]])
            if np.isfinite(self.alt.astype(float)[i+1]):
                self.alt_kft[i+1] = self.alt[i+1]*3.28084/1000.0
            elif np.isfinite(self.alt_kft.astype(float)[i+1]):
                self.alt[i+1] = self.alt_kft[i+1]*1000.0/3.28084
            else:
                self.alt[i+1] = self.get_alt(self.alt[0],self.alt[i])
                self.alt_kft[i+1] = self.alt[i+1]*3.28084/1000.0
            if np.isfinite(self.speed.astype(float)[i+1]) and np.isfinite(self.speed_kts.astype(float)[i+1]): #both are there, check if there are user changes
                speed_kts_temp = self.speed[i+1]*1.94384449246
                speed_temp = self.speed_kts[i+1]/1.94384449246
                if (speed_kts_temp != self.speed_kts[i+1]) and (speed_temp==self.speed[i+1]): #same do nothing
                    nul = 0
                if (speed_kts_temp != self.speed_kts[i+1]) and (speed_temp==self.speed[i+1]): #kts changed, keep that
                    self.speed[i+1] = speed_temp
                elif (speed_kts_temp == self.speed_kts[i+1]) and (speed_temp!=self.speed[i+1]): #m/s changed, keep that
                    self.speed_kts[i+1] = self.speed[i+1]*1.94384449246
                else: #both aren't the same, keep kts
                    self.speed[i+1] = speed_temp
            elif np.isfinite(self.speed.astype(float)[i+1]):
                self.speed_kts[i+1] = self.speed[i+1]*1.94384449246
            elif np.isfinite(self.speed_kts.astype(float)[i+1]):
                self.speed[i+1] = self.speed_kts[i+1]/1.94384449246
            else:
                self.speed[i+1] = self.calcspeed(self.alt[i],self.alt[i+1])
                self.speed_kts[i+1] = self.speed[i+1]*1.94384449246  
            
            if np.isfinite(self.headwind.astype(float)[i+1]) and np.isfinite(self.headwind_kts.astype(float)[i+1]): #both are there, check if there are user changes
                headwind_kts_temp = self.headwind[i+1]*1.94384449246
                headwind_temp = self.headwind_kts[i+1]/1.94384449246
                if (headwind_kts_temp != self.headwind_kts[i+1]) and (headwind_temp==self.headwind[i+1]): #same do nothing
                    nul = 0
                if (headwind_kts_temp != self.headwind_kts[i+1]) and (headwind_temp==self.headwind[i+1]): #kts changed, keep that
                    self.headwind[i+1] = headwind_temp
                elif (headwind_kts_temp == self.headwind_kts[i+1]) and (headwind_temp!=self.headwind[i+1]): #m/s changed, keep that
                    self.headwind_kts[i+1] = self.headwind[i+1]*1.94384449246
                else: #both aren't the same, keep kts
                    self.headwind[i+1] = headwind_temp
            elif np.isfinite(self.headwind.astype(float)[i+1]):
                self.headwind_kts[i+1] = self.headwind[i+1]*1.94384449246
            elif np.isfinite(self.headwind_kts.astype(float)[i+1]):
                self.headwind[i+1] = self.headwind_kts[i+1]/1.94384449246
            else:
                self.headwind[i+1] = 0.0
                self.headwind_kts[i+1] = 0.0
            
            self.rate_of_turn = self.get_rate_of_turn(i)
            if not np.isfinite(self.rate_of_turn):
                self.rate_of_turn = 2.4
            self.bearing[i] = mu.bearing([self.lat[i],self.lon[i]],[self.lat[i+1],self.lon[i+1]])
            self.endbearing[i] = (mu.bearing([self.lat[i+1],self.lon[i+1]],[self.lat[i],self.lon[i]])+180)%360.0
            try:
                self.bearing[i+1] = mu.bearing([self.lat[i+1],self.lon[i+1]],[self.lat[i+2],self.lon[i+2]])
            except:
                self.bearing[i+1] = self.endbearing[i]
            try:
                self.turn_deg[i+1] = abs(self.endbearing[i]-self.bearing[i+1])
            except:
                self.turn_deg[i+1] = 0.0
                
            if not (self.turn_type[i+1].lower() == 'over' or self.turn_type[i+1].lower() == 'flyby' or self.turn_type[i+1].lower() == '90-270') and (i<=(self.n-1)):
                self.turn_type[i+1] = 'Flyby'
                if self.turn_deg[i+1] > 105.0:
                    self.turn_type[i+1] = '90-270'
                elif self.turn_deg[i+1] < 2.0:
                    self.turn_type[i+1] = ' '
                    
            # adjust turn deg for turn type for over 30 degrees
            if self.turn_deg[i+1] > 30.0:
                if self.turn_deg[i+1] > 180.0:
                    self.turn_deg[i+1] = 360 - self.turn_deg[i+1] #for the shortest turn side
                if self.turn_type[i+1].lower() == '90-270':
                    self.turn_deg[i+1] += 180.0 # to account for a 90-270 turn for near 180 turns
                elif self.turn_type[i+1].lower() == 'over':
                    self.turn_deg[i+1] = 2*self.turn_deg[i+1] #roughly double the turn deg
                    
            self.turn_time[i+1] = (self.turn_deg[i+1]*self.rate_of_turn)/60.0 + self.get_time_to_fly_turn_radius_by_turn_type(i+1,self.turn_type[i+1].lower())
            turn_time_as_delay = False
            if not np.isfinite(self.delayt.astype(float)[i+1]):
                self.delayt[i+1] = self.turn_time[i+1]
                turn_time_as_delay = True
            #else:
            #    self.delayt[i+1] = self.delayt[i+1]+self.turn_time[i+1]
            self.climb_time[i+1] = self.calc_climb_time(self.alt[i],self.alt[i+1]) #defaults to P3 speed
            speed = self.speed[i+1]-self.headwind[i+1]
            if not np.isfinite(speed): 
                if not np.isfinite(self.speed[i+1]): print(f'*** self.speed[i+1] for {i+1} is not finite ***')
                if not np.isfinite(self.headwind[i+1]): print(f'*** self.headwind[i+1] for {i+1} is not finite ***')
            self.legt[i+1] = (self.dist[i+1]/(speed/1000.0))/3600.0
            
            if not np.isfinite(self.dist[i+1]): print(f'*** dist for {i+1} is not finite ***') 
            spiral = False
            if self.legt[i+1] < self.climb_time[i+1]/60.0:
                self.legt[i+1] = self.climb_time[i+1]/60.0
                spiral = True
                if not np.isfinite(self.climb_time[i+1]): print(f'*** climb_time for {i+1} is not finite ***')
            self.legt[i+1] += self.delayt[i+1]/60.0
            if not np.isfinite(self.delayt[i+1]):
                print(f'*** delayt for {i+1} is not finite ***')
            if not spiral and not turn_time_as_delay and not previous_spiral:
                self.legt[i+1] += self.turn_time[i+1]/60.0
                if not np.isfinite(self.turn_time[i+1]):
                    print(f'*** turn_time for {i+1} is not finite ***')
            if spiral:
                previous_spiral = True
            if not np.isfinite(self.legt[i+1]):
                print(f'*** legt for {i+1} is not finite ***')
            self.utc[i+1] = self.utc[i]+self.legt[i+1]
            if not np.isfinite(self.utc[i+1]):
                print(self.utc)
                import tkinter.messagebox as tkMessageBox
                tkMessageBox.showwarning('Non-finite UTC values','Problem with non real UTC values. See command line for debug interface')
                import pdb; pdb.set_trace()
            
        self.local = self.utc+self.UTC_conversion
        self.dist_nm = self.dist*0.53996
        self.cumdist = self.dist.cumsum()
        self.cumdist_nm = self.dist_nm.cumsum()
        self.cumlegt = np.nan_to_num(self.legt).cumsum()
        
        self.datetime = self.calcdatetime()
        self.sza,self.azi = mu.get_sza_azi(self.lat,self.lon,self.datetime)
        self.wpname = self.get_waypoint_names(fmt=self.p_info.get('waypoint_format','{x.name[0]}{x.datestr.split("-")[2]}{w:02d}'))
        self.time2xl()
        
    def force_calcspeed(self):
        """
        Program to override the current speed written in and calculate a new one
        """
        self.n = len(self.lon)
        for i in range(self.n-1):
            self.speed[i+1] = self.calcspeed(self.alt[i],self.alt[i+1])
            self.speed_kts[i+1] = self.speed[i+1]*1.94384449246

    def calcspeed(self,alt0,alt1):
        """
        Simple program to estimate the speed of the aircraft:
        P3 from Steven Howell based on TRACE-P
        ER2 from Samuel LeBlanc based on SEAC4RS
        """
        if self.p_info.get('base_speed'):
            TAS = self.p_info['base_speed'] + alt1*self.p_info['speed_per_alt']
            if alt1>self.p_info['max_speed_alt']:
                TAS = self.p_info['max_speed']
            if TAS > self.p_info['max_speed']:
                TAS = self.p_info['max_speed']
            if alt1>alt0+200.0:
                TAS = TAS-self.p_info['descent_speed_decrease']        
        else:
            if self.platform=='p3':
                TAS = 130.0+alt1/1000.0*7.5
                if alt1>6000.0:
                    TAS = 130.0+6*7.5
                if alt1>alt0+200.0:
                    TAS = TAS -15.0
            elif self.platform=='er2':
                TAS = 70+alt0*0.0071
            else:
                TAS = 130.0
        if not np.isfinite(TAS):
            TAS = 130.0
        return TAS

    def get_alt(self,alt0,alti):
        'Program to guesstimate the cruising altitude'
        if alti!=alt0:
            return alti
        if self.p_info.get('max_alt'):
            return self.p_info['max_alt']
        else:
            if self.platform=='p3':
                return 7500.0
            elif self.platform=='er2':
                return 19000.0
            elif self.platform=='c130':
                return 7500.0
            elif self.platform=='dc8':
                return 13000.0
            else:
                return alti
        
    def calc_climb_time(self,alt0,alt1):
        """
        Simple program to calculate the climb/descent time from previous missions
        Uses parameterization for P3 and ER2 for now.
        Default parameters are used when nothing is set.
        Uses altitude from previous point (alt0) and next point (alt1) in meters
        returns minutes of climb/descent time
        """
        if alt1>alt0:
            climb = True
            if not alt1: climb = False
        else:
            climb = False
        if self.p_info.get('climb_vert_speed'):
            if climb:
                if alt1>self.p_info['alt_for_variable_vert_speed']:
                    speed = self.p_info['vert_speed_base']-\
                            self.p_info['vert_speed_per_alt']*(alt1+alt0)/2.0
                else:
                    speed = self.p_info['climb_vert_speed']
            else:
                speed = self.p_info['descent_vert_speed']
        else:
            if self.platform=='p3':
                if climb:
                    if alt1 > 6000:
                        speed = 4.5-7e-05*(alt1+alt0)/2.0
                    else:
                        speed = 5.0
                else:
                    speed = -5.0
            elif self.platform=='er2':
                if climb:
                    speed = 24.0-0.0011*(alt1+alt0)/2.0
                else:
                    speed = -10.0
            elif self.platform=='dc8':
                if climb:
                    speed = 15.0-0.001*(alt1+alt0)/2.0
                else:
                    speed = -10.0
            elif self.platform=='c130':
                if climb:
                    speed = 10.0-0.001*(alt1+alt0)/2.0
                else:
                    speed = -10.0
            else:
                if climb:
                    speed = 5.0
                else:
                    speed = -5.0
        climb_time = (alt1-alt0)/speed/60.0
        if not np.isfinite(climb_time):
            climb_time = 5.0
            print('climb time not finite for platform: %s, alt0:%f, alt1:%f' % (self.platform,alt0,alt1))
        return climb_time

    def calcdatetime(self):
        """
        Program to convert a utc time and datestr to datetime object
        """
        from datetime import datetime
        dt = []
        for i,u in enumerate(self.utc):
            Y,M,D = [int(s) for s in self.datestr.split('-')]
            try:    
                hh = int(u)
            except ValueError:
                print('Problem on line :%i with value %f'%(i,u))
                continue
            mm = int((u-hh)*60.0)
            ss = int(((u-hh)*60.0-mm)*60.0)
            ms = int((((u-hh)*60.0-mm)*60.0-ss)*1000.0)
            while hh > 23:
                hh = hh-24
                D = D+1
            try:
                dt.append(datetime(Y,M,D,hh,mm,ss,ms))
            except ValueError:
                print('Problem on line: %i with datetime for datestr: %s' %(i,self.datestr))
                print(Y,M,D)
                self.get_datestr_from_xl()
                Y,M,D = [int(s) for s in self.datestr.split('-')]
                try:
                    dt.append(datetime(Y,M,D,hh,mm,ss,ms))
                except ValueError:
                    print('Big problem on 2nd try of calcdatetime with datestr, line: %i'%i)
                    continue
        return dt

    def time2xl(self):
        """
        Convert the UTC fractional hours to hh:mm format for use in excel
        """
        self.cumlegt_xl = self.cumlegt/24.0
        self.utc_xl = self.utc/24.0
        self.local_xl = self.local/24.0
        self.legt_xl = self.legt/24.0

    def write_to_excel(self):
        """
        writes out the dict_position class values to excel spreadsheet
        """
        import numpy as np
        import xlwings as xw
        #self.wb.set_current()
        #self.wb.sh.activate(steal_focus=False)
        sh = self.wb.sh
        sh.range('A2').value = np.array([self.WP,
                                      self.lat, self.lon,
                                      self.speed, self.delayt,
                                      self.alt, self.cumlegt_xl,
                                      self.utc_xl, self.local_xl,
                                      self.legt_xl, self.dist,
                                      self.cumdist, self.dist_nm,
                                      self.cumdist_nm, self.speed_kts,
                                      self.alt_kft, self.sza, self.azi,
                                      self.bearing, self.climb_time
                                      ]).T
        for i,c in enumerate(self.comments):
            sh.range('U%i'%(i+2)).value = c
        if hasattr(self,'wpname'):
            for i,w in enumerate(self.wpname):
                sh.range('V%i'%(i+2)).value = w
        
        sh.range('W2').value = np.array([self.headwind_kts,self.headwind]).T
        if hasattr(self,'turn_type'):
            for i,tt in enumerate(self.turn_type):
                sh.range('Y%i'%(i+2)).value = tt
        sh.range('Z2').value = np.array([self.turn_time]).T            
        sh.range('G2:J%i'% (self.n+1)).number_format = 'hh:mm'
        sh.range('E2:E%i'% (self.n+1)).number_format = '0'
       # sh.range('B:B').autofit()
       # sh.range('C:C').autofit()
       # sh.range('B:B').api.HorizontalAlignment = xw.constants.HAlign.xlHAlignCenter
       # sh.range('C:C').api.HorizontalAlignment = xw.constants.HAlign.xlHAlignCenter


    def check_xl(self):
        """
        wrapper for checking excel updates.
        Reruns check_updates_excel whenever a line is found to be deleted
        """
        self.points_changed = 0
        while self.check_updates_excel():
            self.points_changed = self.points_changed+self.num_changed
            if self.verbose:
                print('line removed, cutting it out') 

    def check_updates_excel(self):
        """
        Check for any change in the excel file
        If there is change, empty out the corresponding calculated areas
        Priority is always given to metric
        """
        import numpy as np
        sh = self.wb.sh
        #self.wb.sh.activate(steal_focus=False) #self.wb.set_current()
        row_start = 2
        last_row = sh.range((self.wb.sheets.active.cells.last_cell.row,2)).end('up').row
        tmp = sh.range((row_start,1),(last_row,30)).value 
        
        if len(np.shape(tmp))==1: tmp = [tmp]
        # run through each line to check for updates
        if self.n > len(tmp):
            deleted = True
        else:
            deleted = False
        for i,t in reversed(list(enumerate(tmp))):
            if t[1] is None or t[2] is None:#lat or lon is deleted
                self.dels(i)
                self.n = self.n-1
                sh.range((i+row_start,1),(i+row_start,29)).delete() 
                deleted = True
        # double check if end point is deleted.
        if self.n > len(tmp):
            for j in range(self.n,len(tmp)-1,-1):
                self.dels(j-1)
                self.n = self.n-1            
        # check updated sheets (after deletions)
        last_row = sh.range((self.wb.sheets.active.cells.last_cell.row,2)).end('up').row
        tmp = sh.range((row_start,1),(last_row,30)).value
        if len(np.shape(tmp))==1: tmp = [tmp]
        num = 0
        for i,t in enumerate(tmp):
            if i>self.n-1: #new points
                if not t[20]: t[20] = ' '
                if not t[21]: t[21] = ' '
                if not t[24]: t[24] = ' '
                   
                self.appends(*t[1:16],comm=t[20],wpname=t[21],turn_type=t[24],headwind=t[23],headwind_kts=t[22],timepoint=t[25])
                num = num + 1
            else: # check if modifications
                changed = self.mods(i,t[1],t[2],t[3],t[14],t[4],t[5],t[15],t[20],t[21],t[23],t[22],t[24]) 
                if i == 0:
                    if self.utc[i] != t[7]*24.0:
                        self.utc[i] = t[7]*24.0
                        changed = True
                if changed: num = num+1
        
        # closeout and updates if needed
        if num>0 or deleted:
            if self.verbose:
                print('Updated %i lines from Excel, recalculating and printing' % num)
            self.calculate()
            self.write_to_excel()
        self.num_changed = num+deleted
        return deleted

    def move_xl(self,i):
        """
        Program that moves up all excel rows by one line overriding the ith line
        """
        sh = self.wb.sh
        linesbelow = sh.range('A%i:Z%i'%(i+3,self.n+1)).value
        n_rm = (self.n+1)-(i+3)
        linelist = False
        for j,l in enumerate(linesbelow):
            if type(l) is list:
                try:
                    l[0] = l[0]-1
                except:
                    yup = True
                linesbelow[j] = l
                linelist = True
        if not linelist:
            try:
                linesbelow[0] = linesbelow[0]-1
            except:
                yup = True
        sh.range('A%i:Z%i'%(i+2,i+2)).value = linesbelow
        sh.range('A%i:Z%i'%(self.n+1,self.n+1)).clear_contents()

    def dels(self,i):
        """
        program to remove the ith item in every object
        """
        import numpy as np
        if i+1>len(self.lat):
            print('** Problem: index out of range **')
            return
        self.lat = np.delete(self.lat,i)
        self.lon = np.delete(self.lon,i)
        self.speed = np.delete(self.speed,i)
        self.delayt = np.delete(self.delayt,i)
        self.alt = np.delete(self.alt,i)
        self.alt_kft = np.delete(self.alt_kft,i)
        self.speed_kts = np.delete(self.speed_kts,i)
        self.cumlegt = np.delete(self.cumlegt,i)
        self.utc = np.delete(self.utc,i)
        self.local = np.delete(self.local,i)
        self.legt = np.delete(self.legt,i)
        self.dist = np.delete(self.dist,i)
        self.cumdist = np.delete(self.cumdist,i)
        self.dist_nm = np.delete(self.dist_nm,i)
        self.cumdist_nm = np.delete(self.cumdist_nm,i)
        self.bearing = np.delete(self.bearing,i)
        self.endbearing = np.delete(self.endbearing,i)
        self.turn_deg = np.delete(self.turn_deg,i)
        self.turn_time = np.delete(self.turn_time,i)
        self.climb_time = np.delete(self.climb_time,i)
        self.sza = np.delete(self.sza,i)
        self.azi = np.delete(self.azi,i)
        self.comments.pop(i)         
        self.turn_type.pop(i)
        self.headwind = np.delete(self.headwind,i)
        self.headwind_kts = np.delete(self.headwind_kts,i)
        self.timepoint = np.delete(self.timepoint,i)
             
        try:
            self.WP = np.delete(self.WP,i)
        except:
            self.WP = range(1,len(self.lon))
            
        try: 
            self.wpname = np.delete(self.wpname,i)
        except:
            try:
                self.wpname.pop(i)  
            except:
                pass
        #print 'deletes, number of lon left:%i' %len(self.lon)

    def appends(self,lat,lon,sp=None,dt=None,alt=None,
                clt=None,utc=None,loc=None,lt=None,d=None,cd=None,
                dnm=None,cdnm=None,spkt=None,altk=None,
                bear=0.0,endbear=0.0,turnd=0.0,turnt=0.0,climbt=0.0,
                sza=None,azi=None,comm=None,wpname=None,
                turn_type=' ',headwind=0.0,headwind_kts=0.0,timepoint=None):
        """
        Program that appends to the current class with values supplied, or with defaults from the command line
        """
        import numpy as np
        self.lat = np.append(self.lat,pll(lat))
        self.lon = np.append(self.lon,pll(lon))
        self.speed = np.append(self.speed,sp)
        self.delayt = np.append(self.delayt,dt)
        self.alt = np.append(self.alt,alt)
        if not clt: clt = np.nan
        if not utc: utc = np.nan
        if not loc: loc = np.nan
        if not lt: lt = np.nan
        if not timepoint: timepoint = np.nan
        self.cumlegt = np.append(self.cumlegt,clt*24.0)
        self.utc = np.append(self.utc,utc*24.0)
        self.local = np.append(self.local,loc*24.0)
        self.legt = np.append(self.legt,lt*24.0)
        self.dist = np.append(self.dist,d)
        self.cumdist = np.append(self.cumdist,cd)
        self.dist_nm = np.append(self.dist_nm,dnm)
        self.cumdist_nm = np.append(self.cumdist_nm,cdnm)
        self.speed_kts = np.append(self.speed_kts,spkt)
        self.alt_kft = np.append(self.alt_kft,altk)
        self.bearing = np.append(self.bearing,bear)
        self.endbearing = np.append(self.endbearing,endbear)
        self.turn_deg = np.append(self.turn_deg,turnd)
        self.turn_time = np.append(self.turn_time,turnt)
        self.climb_time = np.append(self.climb_time,climbt)
        self.sza = np.append(self.sza,sza)
        self.azi = np.append(self.azi,azi)
        self.comments.append(comm)
        
        self.turn_type.append(turn_type)
        self.headwind = np.append(self.headwind,headwind)
        self.headwind_kts = np.append(self.headwind_kts,headwind_kts)
        self.timepoint = np.append(self.timepoint,timepoint*24.0)
        
        try:
            self.wpname.append(wpname)
        except:
            self.wpname = list(self.wpname)
            self.wpname.append(wpname)
        
    def inserts(self,i,lat,lon,sp=None,dt=None,alt=None,
                clt=None,utc=None,loc=None,lt=None,d=None,cd=None,
                dnm=None,cdnm=None,spkt=None,altk=None,
                bear=0.0,endbear=0.0,turnd=0.0,turnt=0.0,climbt=0.0,
                sza=None,azi=None,comm=None,wpname=None,
                turn_type=' ',headwind=0.0,headwind_kts=0.0,timepoint=None):
        """
        Program that appends to the current class with values supplied, or with defaults from the command line
        """
        import numpy as np
        self.lat = np.insert(self.lat,i,pll(lat))
        self.lon = np.insert(self.lon,i,pll(lon))
        self.speed = np.insert(self.speed,i,sp)
        self.delayt = np.insert(self.delayt,i,dt)
        self.alt = np.insert(self.alt,i,alt)
        if not clt: clt = np.nan
        if not utc: utc = np.nan
        if not loc: loc = np.nan
        if not lt: lt = np.nan
        if not timepoint: timepoint = np.nan
        self.cumlegt = np.insert(self.cumlegt,i,clt*24.0)
        self.utc = np.insert(self.utc,i,utc*24.0)
        self.local = np.insert(self.local,i,loc*24.0)
        self.legt = np.insert(self.legt,i,lt*24.0)
        self.dist = np.insert(self.dist,i,d)
        self.cumdist = np.insert(self.cumdist,i,cd)
        self.dist_nm = np.insert(self.dist_nm,i,dnm)
        self.cumdist_nm = np.insert(self.cumdist_nm,i,cdnm)
        self.speed_kts = np.insert(self.speed_kts,i,spkt)
        self.alt_kft = np.insert(self.alt_kft,i,altk)
        self.bearing = np.insert(self.bearing,i,bear)
        self.endbearing = np.insert(self.endbearing,i,endbear)
        self.turn_deg = np.insert(self.turn_deg,i,turnd)
        self.turn_time = np.insert(self.turn_time,i,turnt)
        self.climb_time = np.insert(self.climb_time,i,climbt)
        self.sza = np.insert(self.sza,i,sza)
        self.azi = np.insert(self.azi,i,azi)
        self.comments.insert(i,comm)
        
        self.turn_type.insert(i,turn_type)
        self.headwind = np.insert(self.headwind,i,headwind)
        self.headwind_kts = np.insert(self.headwind_kts,i,headwind_kts)
        self.timepoint = np.insert(self.timepoint,i,timepoint*24.0)
        
        try:
            self.wpname.insert(i,wpname)
        except:
            self.wpname = list(self.wpname)
            self.wpname.insert(i,wpname)

    def mods(self,i,lat=None,lon=None,sp=None,spkt=None,
             dt=None,alt=None,altk=None,comm=None,wpname=None,
             hdwind=None,hdwindkt=None,turntype=None):
        """
        Program to modify the contents of the current class if
        there is an update on the line, defned by i
        If anything is not input, then the default of NaN is used
        comments are treated as none
        """
        import numpy as np
        if i+1>len(self.lat):
            print('** Problem with index too large in mods **')
            return
        changed = False
        compare_altk = True
        compare_speedk = True
        compare_hdwindk = True
        self.toempty = {'speed':0,'delayt':0,'alt':0,'speed_kts':0,'alt_kft':0,'headwind':0,'headwind_kts':0}
        if lat is None: lat = np.nan
        if lon is None: lon = np.nan
        if sp is None: sp = np.nan
        if spkt is None: spkt = np.nan
        if dt is None: dt = np.nan
        if alt is None: alt = np.nan
        if altk is None: altk = np.nan
        if hdwind is None: hdwind = np.nan
        if hdwindkt is None: hdwindkt = np.nan
        if self.lat[i] != lat:
            self.lat[i] = pll(lat)
            changed = True
        if self.lon[i] != lon:
            self.lon[i] = pll(lon)
            changed = True
        if self.speed[i] != sp:
            if np.isfinite(sp):
                self.speed[i] = sp
                self.toempty['speed_kts'] = 1
                compare_speedk = False
                changed = True
            else:
                self.toempty['speed'] = 1
                changed = True
        if self.speed_kts[i] != spkt:
            if np.isfinite(spkt)&compare_speedk:
                self.speed_kts[i] = spkt
                self.toempty['speed'] = 1
                changed = True
            else:
                self.toempty['speed_kts'] = 1
                changed = True
        if self.headwind[i] != hdwind:
            if np.isfinite(hdwind):
                self.headwind[i] = hdwind
                self.toempty['headwind_kts'] = 1
                compare_hdwindk = False
                changed = True
            else:
                self.toempty['headwind'] = 1
                changed = True
        if self.headwind_kts[i] != hdwindkt:
            if np.isfinite(hdwindkt)&compare_hdwindk:
                self.headwind_kts[i] = hdwindkt
                self.toempty['headwind'] = 1
                changed = True
            else:
                self.toempty['headwind_kts'] = 1
                changed = True
        if self.delayt[i] != dt:
            if i != 0:
                self.delayt[i] = dt
                changed = True
        if self.alt[i] != alt:
            if np.isfinite(alt):
                self.alt[i] = alt
                self.toempty['alt_kft'] = 1
                compare_altk = False
                changed = True
        if self.alt_kft[i] != altk:
            if np.isfinite(altk)&compare_altk:
                self.alt_kft[i] = altk
                self.toempty['alt'] = 1
                changed = True
        for s in self.toempty:
            if self.toempty.get(s):
                v = getattr(self,s)
                v[i] = np.nan
                setattr(self,s,v)
        if not self.comments[i] == comm:
            if comm: 
                self.comments[i] = comm
                changed = True
            if comm==' ':
                self.comments[i] = None
                changed = True
        if not self.wpname[i] == wpname:
            if wpname: 
                if wpname==' ' and self.comments[i] and self.wpname[i]: self.comments[i].replace(self.wpname[i],' ')
                self.wpname[i] = wpname
                changed = True
            if wpname==' ':
                self.wpname[i] = None
                changed = True
        if not self.turn_type[i] == turntype:
            if turntype: 
                self.turn_type[i] = turntype
                changed = True
            if turntype==' ':
                self.turn_type[i] = ' '
                changed = True
        return changed

    def Open_excel(self,filename=None,sheet_num=1,campaign='None',platform_file='platform.txt'):
        """
        Purpose:
            Program that opens and excel file and creates the proper links with pytho
        Inputs:
            filename of excel file to open
            sheet_num: what sheet to activate and load
            campaign: (optional) if set, does ask to verify the campaign for each sheet
        Outputs:
            wb: workbook instance
        Dependencies:
            xlwings
            Excel (win or mac)
            re
            tkSimpleDialog (for datestr)
            datetime
        Example:
            ...
        History:
            Written: Samuel LeBlanc, 2015-08-18, NASA Ames, CA
            Modified: Samuel LeBlanc, 2016-06-07, NASA Ames, CA
                      - updated to handle the new excel format with climb time and bearing
                      - added datestr checking and dialog interface
            Modified: Samuel LeBlanc, 2016-07-28, NASA Ames, CA
                      - updated to handle the platform file definitions and check on utc_conversion factor
        """
        #from xlwings import Workbook, Sheet, Range
        import xlwings as xw
        import numpy as np
        from datetime import datetime
        if not filename:
            print('No filename found')
            return
        try:
            wb = xw.Book(filename)
        except Exception as ie:
            print('Exception found:',ie)
            return
        self.name = wb.sheets(sheet_num).name
        wb.sheets(sheet_num).activate()
        wb.sh = wb.sheets(sheet_num)
        print('Activating sheet:%i, name:%s'%(sheet_num,wb.sheets(sheet_num).name))
        self.platform, self.p_info,use_file = self.get_platform_info(self.name,platform_file)
        print('Using platform data for: %s' %self.platform)
        header_row = wb.sh.range((1,1),(1,50)).value
        datestr_cellcol = [i for i,element in enumerate(header_row) if type(element) is datetime][0]
        if not datestr_cellcol:
            datestr_cellcol = [i for i,element in enumerate(header_row) if element=='Comment'][0]+2
        cell_datestr = wb.sh.range((1,datestr_cellcol+1)) # select one to the right because xlwings is base 1 instead of base 0 for python
        self.datestr = str(cell_datestr.value).split(' ')[0]
        self.verify_datestr()
        cell_datestr.value = self.datestr
        if campaign != 'None':
            self.campaign
        else:
            self.campaign = str(cell_datestr.offset(0,1).value).split(' ')[0]
            self.verify_campaign()
        try:
            self.__version__ = str(cell_datestr.offset(2,3).value).split(' ')[0]
        except:
            pass
        self.wb = wb
        self.UTC_conversion = self.verify_UTC_conversion()
        if self.verify_not_extended_version(cell_datestr):
            wb.sh.range((1,cell_datestr.column),(1,cell_datestr.column+5)).insert(shift='right')
            wb.sh.range((1,datestr_cellcol+1)).value = ['HdWind\n[kt]','HdWind\n[m/s]','Turn type','TurnT\n[min]','TimePt\n[hh:mm]']
            wb.sh.range((2,datestr_cellcol+5),(wb.sh.cells.last_cell.row,datestr_cellcol+5)).color = (50,50,50)
            #wb.sh.range((1,datestr_cellcol+1),(wb.sh.cells.last_cell.row,datestr_cellcol+1)).autofit()
            #wb.sh.range((1,datestr_cellcol+2),(wb.sh.cells.last_cell.row,datestr_cellcol+2)).autofit()
            #wb.sh.range((1,datestr_cellcol+3),(wb.sh.cells.last_cell.row,datestr_cellcol+3)).autofit()
            #wb.sh.range((1,datestr_cellcol+4),(wb.sh.cells.last_cell.row,datestr_cellcol+4)).autofit()
            #wb.sh.range((1,datestr_cellcol+4),(wb.sh.cells.last_cell.row,datestr_cellcol+5)).autofit()
            nul = [wb.sh.range((1,i),(wb.sh.cells.last_cell.row,i)).autofit() for i in range(1,30)]
            wb.sh.range((2,datestr_cellcol+3),(wb.sh.cells.last_cell.row,datestr_cellcol+3)).api.Validation.Add(Type=3,AlertStyle=1,Operator=1, Formula1='" ",Over,Flyby,90-270')
        return wb
        
    def verify_datestr(self):
        'Verify the input datestr is correct'
        import re
        import tkinter.simpledialog as tkSimpleDialog
        from datetime import datetime
        if not self.datestr:
            self.datestr = tkSimpleDialog.askstring('Flight Date','No datestring found!\nPlease input Flight Date (yyyy-mm-dd):')
        if not re.match('[0-9]{4}-[0-9]{2}-[0-9]{2}',self.datestr):
            self.datestr = tkSimpleDialog.askstring('Flight Date','No datestring found!\nPlease input Flight Date (yyyy-mm-dd):')
        if not self.datestr:
            print('No datestring found! Using todays date')
            
            self.datestr = datetime.utcnow().strftime('%Y-%m-%d')
        if not self.datestr_verified:
            self.datestr = tkSimpleDialog.askstring('Flight Date','Please verify Flight Date (yyyy-mm-dd):',initialvalue=self.datestr)
            self.datestr_verified = True
            
    def verify_campaign(self):
        'verify the input campaign value'
        import tkinter.simpledialog as tkSimpleDialog
        self.campaign = tkSimpleDialog.askstring('Campaign name','Please verify campaign name:',initialvalue=self.campaign)
        
    def verify_UTC_conversion(self):
        'verify the input UTC conversion when reading a excel file'
        tmp0 = self.wb.sh.range('A2:U2').value
        tmp0 = self.wb.sh.range('A2:U2').value
        _,_,_,_,_,_,_,utc,loc,_,_,_,_,_,_,_ = tmp0[0:16]
        return loc*24-utc*24
        
    def verify_not_extended_version(self,cell_datestr):
        'verify if this excel is not the extended version, by checking the location of the datestr'
        return cell_datestr.column<self.wb.sh.range(self.datestr_cell).column

    def Create_excel(self,name='P3 Flight path',newsheetonly=False):
        """
        Purpose:
            Program that creates the link to an excel file
            Starts and populates the first line and titles of the excel workbook
        Inputs:
            none
        Outputs:
            wb: workbook instance 
        Dependencies:
            xlwings
            Excel (win or mac)
        Required files:
            none
        Example:
            ...
        Modification History:
            Written: Samuel LeBlanc, 2015-07-15, Santa Cruz, CA
            Modified: Samuel LeBlanc, 2015-08-07, Santa Cruz, CA
                    - put into the dic_position class, modified slightly
            Modified: Samuel LeBlanc, 2015-08-25, NASA Ames, CA
                    - modify to permit creation of a new sheet within the current workbook
            
        """
        import xlwings as xw #from xlwings import Workbook, Sheet, Range, Chart
        try:
            from excel_interface import freeze_top_pane
        except ModuleNotFoundError:
            from .excel_interface import freeze_top_pane
        import numpy as np
        if newsheetonly:
            wb = xw.books.active
            sh = wb.sheets.add(name=name,after=wb.sheets[wb.sheets.count-1])   
            self.sheet_num = self.sheet_num+1
        else:
            try:
                wb = xw.Book()
            except:
                wb = xw.Book()
            self.name = name
            wb.sheets.active.name = self.name
            sh = wb.sheets.active
        sh.range('A1').value = ['WP','Lat\n[+-90]','Lon\n[+-180]',
                             'Speed\n[m/s]','delayT\n[min]','Altitude\n[m]',
                             'CumLegT\n[hh:mm]','UTC\n[hh:mm]','LocalT\n[hh:mm]',
                             'LegT\n[hh:mm]','Dist\n[km]','CumDist\n[km]',
                             'Dist\n[Nmi]','CumDist\n[Nmi]','Speed\n[kt]',
                             'Altitude\n[kft]','SZA\n[deg]','AZI\n[deg]',
                             'Bearing\n[deg]','ClimbT\n[min]','Comments','WP names',
                             'HdWind\n[kt]','HdWind\n[m/s]','Turn type','TurnT\n[min]','TimePt\n[hh:mm]'] # new ones for version 1.62
        freeze_top_pane(wb)
        
        sh.range('B:B').autofit()
        sh.range('C:C').autofit()
        sh.range('B:B').api.HorizontalAlignment = xw.constants.HAlign.xlHAlignCenter
        sh.range('C:C').api.HorizontalAlignment = xw.constants.HAlign.xlHAlignCenter
        
        sh.range('G2:J2').number_format = 'hh:mm'
        sh.range('AA2:AA2').number_format = 'hh:mm'
        sh.range('Z:Z').number_format = '0.0'
        sh.range('L:L').number_format = '0.0'
        sh.range('N:N').number_format = '0.0'
        sh.range('P:P').number_format = '0.0'
        sh.range('S:S').number_format = '0.0'
        sh.range('T:T').number_format = '0.0'
        sh.range('W:W').number_format = '0.0'
        sh.range('X:X').number_format = '0.0'
        
        cell_datestr = sh.range(self.datestr_cell)
        cell_datestr.value = self.datestr
        sh.range(self.datestr_cell).offset(0,1).value = self.campaign
        sh.range(self.datestr_cell).offset(0,2).value = 'Created with'
        sh.range(self.datestr_cell).offset(1,2).value = 'moving_lines'
        sh.range(self.datestr_cell).offset(2,2).value = self.__version__
        nul = [sh.range((1,i),(sh.cells.last_cell.row,i)).autofit() for i in range(1,30)]
        sh.range((1,cell_datestr.column-4),(sh.cells.last_cell.row,cell_datestr.column-4)).autofit()
        sh.range((1,cell_datestr.column-3),(sh.cells.last_cell.row,cell_datestr.column-3)).autofit()
        sh.range((1,cell_datestr.column-2),(sh.cells.last_cell.row,cell_datestr.column-2)).autofit()
        sh.range((1,cell_datestr.column-1),(sh.cells.last_cell.row,cell_datestr.column-1)).autofit()
        sh.range((1,cell_datestr.column),(sh.cells.last_cell.row,cell_datestr.column)).autofit()
        sh.range((1,cell_datestr.column),(sh.cells.last_cell.row,cell_datestr.column)).api.HorizontalAlignment = xw.constants.HAlign.xlHAlignCenter
        sh.range((1,cell_datestr.column+1),(sh.cells.last_cell.row,cell_datestr.column+1)).autofit()
        sh.range((1,cell_datestr.column+2),(sh.cells.last_cell.row,cell_datestr.column+2)).api.HorizontalAlignment = xw.constants.HAlign.xlHAlignCenter
        sh.range((1,cell_datestr.column+3),(sh.cells.last_cell.row,cell_datestr.column+3)).autofit()
        sh.range((1,cell_datestr.column+3),(sh.cells.last_cell.row,cell_datestr.column+3)).api.HorizontalAlignment = xw.constants.HAlign.xlHAlignCenter
        sh.range((2,cell_datestr.column-1),(sh.cells.last_cell.row,cell_datestr.column-1)).color = (75,75,75)
        try:
            sh.range((2,25),(sh.cells.last_cell.row,25)).api.Validation.Add(Type=3,AlertStyle=1,Operator=1, Formula1='" ",Over,Flyby,90-270')
        except AttributeError:
            sh.range((2,25)).value = " "
            sh.range((3,25)).value = "Over"
            sh.range((4,25)).value = "Flyby"
            sh.range((5,25)).value = "90-270"
            
        #Range('A2').value = np.arange(50).reshape((50,1))+1
        wb.sh = sh
        return wb

    def switchsheet(self,i):
        'Switch the active sheet with name supplied'
        #from xlwings import Sheet
        self.wb.sheets(i+1).activate()
        self.wb.sh = self.wb.sheets(i+1)

    def save2xl(self,filename=None):
        """
        Simple to program to initiate the save function in Excel
        Same as save button in Excel
        """
        self.wb.save(filename)

    def get_datestr_from_xl(self):
        'Simple program to get the datestr from the excel spreadsheet'
        self.datestr = str(self.wb.sh.range(self.datestr_cell).value).split(' ')[0]
        
    def save2txt(self,filename=None):
        """ 
        Simple method to save the points to a text file.
        For input with idl and matlab
        """
        f = open(filename,'w+')
        f.write('#WP  Lon[+-180]  Lat[+-90]  Speed[m/s]  delayT[min]  Altitude[m]'+
                '  CumLegT[H]  UTC[H]  LocalT[H]'+
                '  LegT[H]  Dist[km]  CumDist[km]'+
                '  Dist[Nmi]  CumDist[Nmi]  Speed[kt]'+
                '  Altitude[kft]  SZA[deg]  AZI[deg]  Bearing[deg]  Climbt[min]  Comments WPnames\n')
        for i in range(self.n):
            
            try:
                f.write("""%-2i  %+2.8f  %+2.8f  %-4.2f  %-3i  %-5.1f  %-2.2f  %-2.2f  %-2.2f  %-2.2f  %-5.1f  %-5.1f  %-5.1f  %-5.1f  %-3.1f %-3.2f  %-3.1f  %-3.1f  %-3.1f  %-3i  %s  %s \n""" %(
                    i+1,self.lon[i],self.lat[i],self.speed[i],
                    self.delayt[i],self.alt[i],self.cumlegt[i],
                    self.utc[i],self.local[i],self.legt[i],
                    self.dist[i],self.cumdist[i],self.dist_nm[i],self.cumdist_nm[i], 
                    self.speed_kts[i],self.alt_kft[i],self.sza[i],self.azi[i],self.bearing[i],self.climb_time[i],self.comments[i],self.wpname[i]))
            except TypeError:
                for attr in ['lon','lat','speed','delayt','alt','cumlegt','utc','local','legt','dist','cumdist','dist_nm','cumdist_nm','speed_kts','alt_kft','sza','azi','bearing','climb_time']:
                    if not getattr(self,attr):
                        setattr(self,attr,0.0)
                
                

    def save2kml(self,filename=None):
        """
        Program to save the points contained in the spreadsheet to a kml file
        """
        import simplekml
        #from xlwings import Sheet
        if not filename:
            raise NameError('filename not defined')
            return
        if not self.netkml:
            self.netkml = simplekml.Kml(open=1)
            self.netkml.name = 'Flight plan on '+self.datestr
            net = self.netkml.newnetworklink(name=self.datestr)
            net.link.href = filename
            net.link.refreshmode = simplekml.RefreshMode.onchange
            net.link.camera = simplekml.Camera(latitude=self.lat[0], longitude=self.lon[0], altitude=3000.0, roll=0, tilt=0,
                          altitudemode=simplekml.AltitudeMode.relativetoground)
            filenamenet = filename+'_net.kml'
            #self.netkml.save(filenamenet)
        self.kml = simplekml.Kml()
        for j in range(self.wb.sheets.count):
            self.switchsheet(j)
            self.name = self.wb.sheets(j+1).name
            self.check_xl()
            self.calculate()
            self.kmlfolder = self.kml.newfolder(name=self.name)
            #self.kml.document = simplekml.Folder(name = self.name)
            self.print_points_kml(self.kmlfolder)
            self.print_path_kml(self.kmlfolder,color=self.color,j=j)
        self.kml.camera = simplekml.Camera(latitude=self.lat[0], longitude=self.lon[0], altitude=3000.0, roll=0, tilt=0,
                          altitudemode=simplekml.AltitudeMode.relativetoground)
        self.kml.save(filename)
        try: 
            self.kml.savekmz(filename.replace('kml','kmz'))
        except:
            print('saving kmz didnt work')
            
        if not self.googleearthopened:
            #self.openGoogleEarth(filenamenet)
            try:
                self.openGoogleEarth(filename.replace('kml','kmz'))
                self.googleearthopened = True
            except:
                print('Not able to open google earth')
                self.googleearthopened = True

    def print_points_kml(self,folder,includepng=False):
        """
        print the points saved in lat, lon
        """
        import simplekml
        try:
            from excel_interface import get_curdir
        except ModuleNotFoundError:
            from .excel_interface import get_curdir
        if not self.kml:
            raise NameError('kml not initilaized')
            return
        for i in range(self.n):
            pnt = folder.newpoint()
            #pnt.name = 'WP # {}'.format(self.WP[i])
            pnt.name = '{}'.format(self.wpname[i])
            pnt.coords = [(self.lon[i],self.lat[i],self.alt[i]*10.0)]
            pnt.altitudemode = simplekml.AltitudeMode.relativetoground
            pnt.extrude = 1
            if includepng:
                try:
                    path = self.kml.addfile(get_curdir()+'//map_icons//number_{}.png'.format(self.WP[i]))
                    pnt.style.iconstyle.icon.href = path
                except:
                    pnt.style.iconstyle.icon.href = get_curdir()+'//map_icons//number_{}.png'.format(self.WP[i])
            else:
                 pnt.style.iconstyle.icon.href = 'https://www.samueleleblanc.com/img/icons/{}.png'.format(self.WP[i])
            pnt.description = """WP=#%02f\nUTC[H]=%2.2f\nWPname=%s\nLocal[H]=%2.2f\nCumDist[km]=%f\nspeed[m/s]=%4.2f\ndelayT[min]=%f\nSZA[deg]=%3.2f\nAZI[deg]=%3.2f\nBearing[deg]=%3.2f\nClimbT[min]=%f\nTurn_type:%s\nComments:%s""" % (self.WP[i],
                                                                   self.utc[i],self.wpname[i],self.local[i],self.cumdist[i],
                                                                   self.speed[i],self.delayt[i],self.sza[i],
                                                                   self.azi[i],self.bearing[i],self.climb_time[i],str(self.turn_type[i]),self.comments[i])

    def print_path_kml(self,folder,color='red',j=0):
        """
        print the path onto a kml file
        """
        import simplekml
        import numpy as np
        cls = [simplekml.Color.red,simplekml.Color.blue,simplekml.Color.green,simplekml.Color.cyan,
               simplekml.Color.magenta,simplekml.Color.yellow,simplekml.Color.black,simplekml.Color.lightcoral,
               simplekml.Color.teal,simplekml.Color.darkviolet,simplekml.Color.orange]
        path = folder.newlinestring(name=self.name)
        coords = [(lon,lat,alt*10) for (lon,lat,alt) in np.array((self.lon,self.lat,self.alt)).T]
        path.coords = coords
        path.altitudemode = simplekml.AltitudeMode.relativetoground
        path.extrude = 1
        path.style.linestyle.color = cls[j]
        path.style.linestyle.width = 4.0

    def openGoogleEarth(self,filename=None):
        """
        Function that uses either COM object or appscript (not yet implemented)
        to load the new Google Earth kml file
        """
        if not filename:
            print('no filename defined, returning')
            return
        from sys import platform
        from os import startfile
        if platform.startswith('win'):
            try:
                from win32com.client import Dispatch
                ge = Dispatch("GoogleEarth.ApplicationGE")
                ge.OpenKmlFile(filename,True)
            except:
                startfile(filename)
        else:
            startfile(filename)

    def save2gpx(self,filename=None):
        'Program to save the waypoints and track in gpx format'
        if not filename:
            print('** no filename selected, returning without saving **')
            return
        import gpxpy as g
        import gpxpy.gpx as gg
        f = gg.GPX()
        route = gg.GPXRoute(name=self.datestr)
        for i,w in enumerate(self.WP):
            rp = gg.GPXRoutePoint(name='WP#%i'%w,latitude=self.lat[i],
                                  longitude=self.lon[i],
                                  elevation = self.alt[i],
                                  time = self.utc2datetime(self.utc[i]),
                                  comment = self.comments[i]
                                  )
            route.points.append(rp)
        f.routes.append(route)
        fp = open(filename,'w')
        fp.write(f.to_xml())
        fp.close()
        print('GPX file saved to:'+filename)      
		
    def save2ict(self,filepath=None):
        'Program to save the flight track as simulated ict file. Similar to what is returned from flights'
        from datetime import datetime
        import getpass
        import re
        if not filepath:
            print('** no filepath selected, returning without saving **')
            return
        dt = 60 #seconds
        # setup data dict
        dict_in = {'Start_UTC':{'original_data':self.utc*3600.0,'unit':'seconds from midnight UTC','long_description':'time keeping'},
                   'Latitude':{'original_data':self.lat,'unit':'Degrees (North positive)','long_description':'Planned latitude position of the aircraft','format':'4.9f'},
                   'Longitude':{'original_data':self.lon,'unit':'Degrees (East positive)','long_description':'Planned longitude position of the aircraft','format':'4.9f'},
                   'Altitude':{'original_data':self.alt,'unit':'meters (above sea level)','long_description':'Planned altitude of the aircraft','format':'5.0f'},
                   'speed':{'original_data':self.speed,'unit':'meters per second (m/s)','long_description':'Estimated speed of aircraft'},
                   'SZA':{'original_data':self.sza,'unit':'degrees from zenith','long_description':'Elevation position of the sun in the sky per respect to zenith'},
                   'AZI':{'original_data':self.azi,'unit':'degrees from north','long_description':'Azimuthal position of the sun in the sky per respect to north'},
                   'Bearing':{'original_data':self.bearing,'unit':'degrees from north','long_description':'Direction of travel of the plane per respect to north'}}
        d_dict = self.interp_points_for_ict(dict_in,dt=dt) 
        # setup header dict
        hdict = {'PI':getpass.getuser(),
                 'Institution':'NASA Ames Research Center',
                 'Instrument':'Simulated flight plan',
                 'campaign':self.campaign,
                 'time_interval':dt,
                 'now':datetime.strptime(self.datestr,'%Y-%m-%d'),
                 'special_comments':'Simulated aircraft data interpolated from flight plan waypoints',
                 'PI_contact':getpass.getuser(),
                 'platform':self.platform,
                 'location':'N/A',
                 'instrument_info':'None',
                 'data_info':'Compiled with flight planner: moving lines {version}'.format(version=self.__version__),
                 'uncertainty':'Undefined',
                 'DM_contact':'Samuel LeBlanc, samuel.leblanc@nasa.gov',
                 'project_info':self.campaign,
                 'stipulations':'None',
                 'rev_comments':"""  RA: First iteration of the flight plan"""}
        order = ['Latitude','Longitude','Altitude','speed','Bearing','SZA','AZI']
        fcomment = self.name.upper().replace(self.platform.upper(),'').strip('_').strip('-').strip()
        rev = get_next_revision(filepath+'//'+'{data_id}_{loc_id}_{date}_{rev}{file_comment}.ict'.format(data_id='{}-Flt-plan'.format(self.campaign),loc_id=self.platform,
                                date=self.datestr.replace('-',''),rev='R?',file_comment=fcomment))
        if hdict['rev_comments'].find(rev)<0:
            num = ord(rev[1].lower())-ord('a')+1
            hdict['rev_comments'] = """ {}: Version {} of the flight plan ict \n""".format(rev,num)+hdict['rev_comments']
        wu.write_ict(hdict,d_dict,filepath=filepath+'//',
                     data_id='{}-Flt-plan'.format(self.campaign),loc_id=self.platform,
                     date=self.datestr.replace('-',''),rev=rev,order=order,file_comment=fcomment)
        
    def interp_points_for_ict(self,dict_in,dt=60.0):
        'Program to interpolate between the waypoints to have a consistent time, defined by dt (defaults to 60 seconds), the variables to be interpolated is defined by dict_in'
        utcs = np.arange(self.utc[0]*3600,self.utc[-1]*3600,dt)
        # create a dict of points using the input dict as a basis, requires it to have the original_data key for each dict entry
        # should be replaced by a interpolator that uses great circles
        for k in dict_in.keys():
            if k=='Start_UTC': 
                dict_in[k]['data'] = utcs
            else:
                fx = interpolate.interp1d(self.utc*3600,dict_in[k]['original_data'],bounds_error=False)
                dict_in[k]['data'] = fx(utcs)
        return dict_in      

    def interp_points_for_profile(self,return_alt=False,dt=None):
        'Program to make an array of evenly padded waypoints in time, for input into the vertical MSS'
        temp_dict = {'Start_UTC':{'original_data':self.utc*3600.0},
                   'Latitude':{'original_data':self.lat},
                   'Longitude':{'original_data':self.lon},
                   'Altitude':{'original_data':self.alt}}
        if not dt:
            dt = min([min(np.diff(self.utc)),0.1])*3600
        dict_out = self.interp_points_for_ict(temp_dict,dt=dt)
        if return_alt:
            return dict_out['Longitude']['data'],dict_out['Latitude']['data'],dict_out['Altitude']['data']
        else:
            return dict_out['Longitude']['data'],dict_out['Latitude']['data']

    def utc2datetime(self,utc):
        'Program to convert the datestr and utc to valid datetime class'
        from datetime import datetime
        y,m,d = self.datestr.split('-')
        year = int(y)
        month = int(m)
        day = int(d)
        hour = int(utc)
        minut = (utc-hour)*60
        minutes = int(minut)
        secon = (minut-minutes)*60
        seconds = int(secon)
        microsec = int((secon-seconds)*100)
        return datetime(year,month,day,hour,minutes,seconds,microsec)

    def exremove(self):
        'Program to remove the current Sheet'
        print('Not yet')
        pass
    
    def get_waypoint_names(self,i=None,fmt='{x.name[0]}{x.datestr.split("-")[2]}{w:02d}'):
        'function to name the waypoints'
        x = self
        if i:
            w = self.WP[i]
            return eval("f'{}'".format(fmt))
        wpname = list(self.WP)
        if hasattr(self,'wpname'):
            wpname_old = self.wpname
        else:
            wpname_old = self.WP
        onlyletters = lambda some_string : ''.join(c for c in some_string if not c.isdigit())
        alphanum = lambda some_string: ''.join(ch for ch in some_string if ch.isalnum())
        for j,w in enumerate(self.WP):
            wp_str = eval("f'{}'".format(fmt))
            #compare only the non numerics
            wpname[j] = wp_str
            if hasattr(self,'labels_points'): #check if the labeled points are near the points already identified
                for lp in self.labels_points:
                    if (lp[1]-self.lat[j])**2+(lp[2]-self.lon[j])**2 < 0.001:
                        wpname[j] = '{:X<5.5s}'.format(alphanum(lp[0].upper()))
                        break
            if (wp_str) and (wpname_old[j]):
                if len(onlyletters(wpname_old[j]).strip())>0:
                    if not onlyletters(wp_str) == onlyletters(wpname_old[j]):
                        wpname[j] = wpname_old[j]
            if len(wpname[j])!=5 and j!=0 and j!=len(self.WP)-1:
                wpname[j] = '{:X<5.5s}'.format(alphanum(wpname[j].upper()))
        return list(wpname)
    
    def get_main_points(self, combined_distances=None, combined_utc=None,combined_names=[],fmt='{wpname}:{Comment}, {utc_str} , {deltat_min} minutes since '):
        'function to pull out the points that have comments, and those that are coordinated, including time between those points.'
        main_points = []
        float_to_hh_mm = lambda float_hours: '{:02d}:{:02d}'.format(int(float_hours), int((float_hours - int(float_hours)) * 60))
        for j,w in enumerate(self.WP): 
            if self.comments[j]: # There is a comment - likely an important point
                main_points.append(dict(Comment=self.comments[j],wpname=self.wpname[j],utc=self.utc[j],
                                        utc_str=float_to_hh_mm(self.utc[j]),i=j+1,deltat_min=0,label=''))
            if combined_distances: 
                for ii,d in enumerate(combined_distances[j]):
                    if (ii != self.sheet_num-1) and (d<30.0): #there is a colocation
                        if len(main_points)>0 and self.comments[j]:
                            main_points[-1]['Comment'] = main_points[-1]['Comment'] + ' - Potential colocation with: {}'.format(combined_names[ii])
                        else:
                            main_points.append(dict(Comment='Potential colocation with: {}'.format(combined_names[ii]),
                                           wpname=self.wpname[j],utc=self.utc[j],i=j+1,deltat_min=0,label='',
                                           utc_str=float_to_hh_mm(self.utc[j])))
                
            main_points[0]['label'] = fmt.format(**main_points[-1])
            if len(main_points)>1:
                old_utc = main_points[0]['utc']
                for mpt in main_points[1:]:
                    mpt['deltat_min'] = int((mpt['utc']-old_utc)*60.0)
                    old_utc = mpt['utc']
                    mpt['label'] = fmt.format(**mpt)
                                
        labels = [mpt['label'] for mpt in main_points]
        return labels,main_points
                       
def get_next_revision(fname):
    'Program that returns the next revision value for a given filename of ict file'
    import os, glob
    a = []
    for f in glob.glob(fname):
        a.append(f)
    if len(a)==0:
        return 'RA'
    a.sort()
    b = a[-1]
    rev = os.path.basename(b.strip('.ict')).split('_')[3]
    newrev = rev[0]+chr(ord(rev[1])+1)
    return newrev
        

def populate_ex_arr(filename=None,colorcycle=['red','blue','green']):
    """
    Purpose:
        Program that opens an excel file, and runs through the sheets 
        creates an array of dict_position
    Input:
        filename of excel file
	colorcycle
    Output:
        excel_interface dict_position array
    Dependeices:
        xlwings
    History:
        written: Samuel LeBlanc, NASA Ames, Santa Cruz, CA 2015-09-10
    """
    import xlwings as xw #from xlwings import Workbook,Sheet
    try:
        import excel_interface as ex
    except ModuleNotFoundError:
        from . import excel_interface as ex
    arr = []
    wb = xw.Book(filename)
    num = wb.sheets.count
    for i in range(num):
        if i==0:
            campaign = 'None'
            datestr_verified = False
        else:
            campaign = arr[i-1].campaign
            try:
                datestr_verified = arr[i-1].datestr_verified
            except:
                datestr_verified = False
        arr.append(ex.dict_position(filename=filename,sheet_num=i+1,color=colorcycle[i],campaign=campaign,
                                    datestr_verified=datestr_verified))
    return arr
    
def save2xl_for_pilots(filename,ex_arr):
    """
    Purpose:
        Program that opens and saves a new excel file, and runs through the current opened sheets 
        creates an excel file in the format defined for pilots. format option is defined in the dict_position
    Input:
        filename: filename of new excel file
        ex_arr: array of excel interface dict_position to be saved
    Output:
        new file
    Dependices:
        xlwings
    History:
        written: Samuel LeBlanc, NASA Ames, CA 2016-07-28
        Modified: Samuel LeBlanc, Santa Cruz, CA, 2022-02-03
                  -changed for supporting python 3 
                  - removed all formatting from xlxs
    """
    import xlwings as xw #from xlwings import Workbook,Sheet,Range
    from matplotlib.colors import to_rgb
    try:
        from excel_interface import format_lat_lon, freeze_top_pane
    except ModuleNotFoundError:
        from .excel_interface import format_lat_lon, freeze_top_pane
    wb_pilot = xw.Book()
    sheet_one = True
    make_light = lambda rgb: (rgb[0]*0.9+0.1,rgb[1]*0.9+0.1,rgb[2]*0.9+0.1)
    make_lighter = lambda rgb: (rgb[0]*0.1+0.9,rgb[1]*0.1+0.9,rgb[2]*0.1+0.9)
    rgb_to_int = lambda rgb: (int(rgb[0]*255),int(rgb[1]*255),int(rgb[2]*255))
    for a in ex_arr:
        if sheet_one:
            wb_pilot.sheets(1).name = a.name
            sh = wb_pilot.sheets(1)
            sheet_one = False
        else:
            sh = wb_pilot.sheets.add(name=a.name,after=wb_pilot.sheets[wb_pilot.sheets.count-1])
            #wb_pilot.sheets(1).add(name=a.name)
        
        xw.Range('A1').value = '{name} - {daystr} - '.format(name=a.name,daystr=a.datestr)
        xw.Range('A1').font.bold = True
        xw.Range('A1').font.size = 24

        if not a.p_info.get('include_mag_heading',False):
            xw.Range('A2').value = ['WP','WP name','Lat\n[+-90]','Lon\n[+-180]',
                             'Altitude\n[kft]','UTC\n[hh:mm]','Comments']
            letter_range = ['A','B','C','D','E','F','G']
            last_rgs = 'G'
        else:
            xw.Range('A2').value = ['WP','WP name','Lat\n[+-90]','Lon\n[+-180]',
                             'Altitude\n[kft]','UTC\n[hh:mm]','Mag Heading\n[deg]','Comments']
            letter_range = ['A','B','C','D','E','F','G','H']
            xw.Range('G3:G%i'% (a.n+2)).number_format = '0.0'
            last_rgs = 'H'
        xw.Range('A1:'+last_rgs+'1').color = rgb_to_int(to_rgb(a.color))
        xw.Range('A2:'+last_rgs+'2').font.bold = True
        #freeze_top_pane(wb_pilot)
        xw.Range('F3:F%i'% (a.n+2)).number_format = 'hh:mm'
        xw.Range('E3:E%i'% (a.n+2)).number_format = '0.00'
        xw.Range('W2').value = a.datestr
        xw.Range('X2').value = a.campaign
        xw.Range('Z2').value = 'Created with'
        xw.Range('Z3').value = 'moving_lines'
        xw.Range('Z4').value = a.__version__
        #xw.Range('W:W').autofit()
        #xw.Range('W:W').api.HorizontalAlignment = xw.constants.HAlign.xlHAlignCenter
        #xw.Range('X:X').autofit()
        #xw.Range('X:X').api.HorizontalAlignment = xw.constants.HAlign.xlHAlignCenter
        #xw.Range('Z:Z').autofit()
        #xw.Range('Z:Z').api.HorizontalAlignment = xw.constants.HAlign.xlHAlignCenter
        for i in range(len(a.lon)):
            lat_f,lon_f = format_lat_lon(a.lat[i],a.lon[i],format=a.pilot_format)
            if a.delayt[i]>3.0:
                comment = 'delay: {:2.1f} min, {}'.format(a.delayt[i],a.comments[i])
            else:
                comment = a.comments[i]
            if hasattr(a,'turn_type') and type( a.turn_type) is str:
                comment += ' [{}]'.format(a.turn_type[i].lower())
            if not a.p_info.get('include_mag_heading',False):
                xw.Range('A{:d}'.format(i+3)).value = [a.WP[i],a.wpname[i],lat_f,lon_f,a.alt_kft[i],a.utc[i]/24.0,comment]
            else:
                mag_decl = a.p_info.get('mag_declination',13.0)
                xw.Range('A{:d}'.format(i+3)).value = [a.WP[i],a.wpname[i],lat_f,lon_f,a.alt_kft[i],a.utc[i]/24.0,(360.0+a.bearing[i]-mag_decl)%360,comment]
            if i%2:
                for st in letter_range:
                    xw.Range('{}{:d}'.format(st,i+2)).color = rgb_to_int(make_lighter(to_rgb(a.color)))
        xw.Range('A{:d}'.format(i+5)).value = 'One line waypoints for foreflight:'
        xw.Range('A{:d}'.format(i+6)).value = one_line_points(a)
        sh.page_setup.print_area = '$A$1:$'+last_rgs+'$%i'% (a.n+2)
    wb_pilot.save(filename)
    try:
        wb_pilot.close()
    except:
        print('** unable to close for_pilots spreadsheet, may need to close manually **')
        
def save2xl_for_pilots_xlswriter(filename, ex_arr):
    """
    Purpose:
        Create a new Excel file (xlsx) containing pilot-style waypoints for each
        entry in ex_arr, one sheet per entry, using xlsxwriter (no Excel UI).

    Input:
        filename: output .xlsx file path
        ex_arr: iterable of objects with attributes like:
                name, datestr, p_info (dict), n, color,
                lat, lon, alt_kft, utc, comments, WP, wpname,
                campaign, __version__, pilot_format, delayt,
                (optional) bearing, turn_type

    Output:
        Creates/saves the Excel file on disk.

    Dependencies:
        xlsxwriter, matplotlib.colors.to_rgb,
        excel_interface.format_lat_lon, excel_interface.one_line_points
    """
    import xlsxwriter
    from matplotlib.colors import to_rgb

    try:
        from excel_interface import format_lat_lon, one_line_points
    except ModuleNotFoundError:
        from .excel_interface import format_lat_lon, one_line_points

    # --- helpers for colors ---
    make_light = lambda rgb: (rgb[0]*0.9+0.1,rgb[1]*0.9+0.1,rgb[2]*0.9+0.1)
    make_lighter = lambda rgb: (rgb[0]*0.1+0.9,rgb[1]*0.1+0.9,rgb[2]*0.1+0.9)
    rgb_to_int = lambda rgb: (int(rgb[0]*255),int(rgb[1]*255),int(rgb[2]*255))
    rgb_to_hex   = lambda rgb: "#{:02X}{:02X}{:02X}".format(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))

    # Create workbook
    wb = xlsxwriter.Workbook(filename)
    wb.default_format_properties = {'font_name': 'Aptos Narrow','font_size': 12}

    for a in ex_arr:
        # Excel worksheet names are limited to 31 chars
        sheet_name = (a.name or "Sheet")[:31]
        ws = wb.add_worksheet(sheet_name)

        # Base colors from a.color
        base_rgb = to_rgb(a.color)
        header_hex = rgb_to_hex(base_rgb)
        alt_row_hex = rgb_to_hex(make_lighter(base_rgb))

        # --- Formats ---
        title_fmt = wb.add_format({"bold": True,"font_size": 24,"bg_color": header_hex,"font_color": "white","align": "left","valign": "vcenter"})
        header_fmt = wb.add_format({"bold": True,"text_wrap": True})

        # Normal numeric formats
        text_fmt = wb.add_format({"bold": False,"text_wrap": False})
        alt_kft_fmt = wb.add_format({"num_format": "0.00"})
        time_fmt = wb.add_format({"num_format": "hh:mm","align": "center"})
        mag_heading_fmt = wb.add_format({"num_format": "0.0"})

        # Alt-row formats with background color
        text_alt_fmt = wb.add_format({"bg_color": alt_row_hex})
        alt_kft_fmt_alt = wb.add_format({"num_format": "0.00","bg_color": alt_row_hex})
        time_fmt_alt = wb.add_format({"num_format": "hh:mm","bg_color": alt_row_hex,"align": "center"})
        mag_heading_fmt_alt = wb.add_format({"num_format": "0.0","bg_color": alt_row_hex})

        # --- Header row (row 1) ---
        include_mag_heading = a.p_info.get("include_mag_heading", False)
        include_turn_type = hasattr(a, "turn_type")
        headers = ["WP", "WP name", "Lat\n[+-90]", "Lon\n[+-180]","Altitude\n[kft]", "UTC\n[hh:mm]"]
        if include_mag_heading:
            headers.append("Mag Heading\n[deg]")
        if include_turn_type:
            headers.append("Turn type")
        headers.append("Comments")
        ws.set_row(1,32.5)
        for col, h in enumerate(headers):
            ws.write(1, col, h, header_fmt)
        last_col_idx = len(headers) - 1
        ws.merge_range(0, 0, 0, last_col_idx, f"{a.name} - {a.datestr} - ", title_fmt)

        # Freeze header (row index 2 -> freeze below row 1)
        ws.freeze_panes(2, 0)

        # --- Column number formats that apply to all rows ---
        # Altitude (kft) column = 4
        ws.set_column(4, 4, 10, alt_kft_fmt)
        # UTC time column = 5
        ws.set_column(5, 5, 12, time_fmt)
        # Comments column width
        ws.set_column(last_col_idx, last_col_idx, 40)

        if include_mag_heading:
            ws.set_column(6, 6, 12, mag_heading_fmt) # Mag heading column = 6

        # --- Metadata (row 1, columns W, X, Z) ---
        # Columns: A=0,..., W=22, X=23, Z=25
        ws.write(1, 22, a.datestr)
        ws.write(1, 23, a.campaign)
        ws.write(1, 25, "Created with")
        ws.write(2, 25, "moving_lines")
        ws.write(3, 25, getattr(a, "__version__", ""))

        # --- Data rows (starting at row 2) ---
        mag_decl = a.p_info.get("mag_declination", 13.0)
        for i in range(len(a.lon)):
            row = i + 2
            lat_f, lon_f = format_lat_lon(a.lat[i], a.lon[i],format=a.pilot_format)

            # Comment including delay
            if a.delayt[i] > 3.0:
                comment = "delay: {:2.1f} min, {}".format(a.delayt[i], a.comments[i])
            else:
                comment = a.comments[i]

            # Build row values
            row_vals = [a.WP[i],a.wpname[i],lat_f,lon_f,a.alt_kft[i],a.utc[i] / 24.0]
            if include_mag_heading:
                mag_heading = (360.0 + a.bearing[i] - mag_decl) % 360.0
                row_vals.append(mag_heading)
            if include_turn_type:
                row_vals.append(str(a.turn_type[i]))
            row_vals.append(comment)

            # Choose formats per column, with alt-row variant for odd i
            is_alt_row = bool(i % 2)
            for col, val in enumerate(row_vals):
                fmt = text_fmt
                if col == 4:  # Altitude
                    fmt = alt_kft_fmt_alt if is_alt_row else alt_kft_fmt
                elif col == 5:  # UTC
                    fmt = time_fmt_alt if is_alt_row else time_fmt
                elif include_mag_heading and col == 6:
                    fmt = mag_heading_fmt_alt if is_alt_row else mag_heading_fmt
                elif is_alt_row:
                    # Text columns in alt rows
                    fmt = text_alt_fmt
                ws.write(row, col, val, fmt)

        if len(a.lon) > 0:
            row_text1 = len(a.lon) + 3
            row_text2 = len(a.lon) + 4
        else:
            row_text1 = 4
            row_text2 = 5

        ws.write(row_text1, 0, "One line waypoints for foreflight:")
        ws.write(row_text2, 0, one_line_points(a))

        last_print_row = a.n + 1  # 0-based
        ws.print_area(0, 0, last_print_row, last_col_idx)

    wb.close()

        
def save2csv_for_FOREFLIGHT_UFP(filename,ex,foreflight_only=True,verbose=True):
    """ 
    Purpose:
        Program that saves a new csv file from the current excel sheet, with name of platform 
        Creates an excel file in the format defined for pilots for the FOREFLIGHT software.
    Input:
        filename: filename of new excel file
        ex: excel interface dict_position to be saved
        foreflight_only: 
    Output:
        new csv file
    Dependices:
        ---
    History:
        written: Samuel LeBlanc, Santa Cruz, CA 2024-04-09
        Modified: by Samuel LeBlanc, Snata Cruz, CA, 2024-08-26
                  - adding an ER2 special file format
    
    """
    if filename.endswith('.csv'): 
        filename = filename[:-4]
    if 'foreflight' in ex.p_info.get('preferred_file_format',['foreflight']):
        if verbose: print('.. saving FOREFLIGHT csv to {}'.format(filename+'_'+ex.name+'_FOREFLIGHT.csv'))
        f = open(filename+'_'+ex.name+'_FOREFLIGHT.csv','w+')
        f.write('Waypoint,Description,LAT,LONG\n')
        ex.wpname = ex.get_waypoint_names(fmt=ex.p_info.get('waypoint_format','{x.name[0]}{x.datestr.split("-")[2]}{w:02d}'))
        for i in range(ex.n):
            if ex.wpname[i] in ex.wpname[0:i]: continue

            comm = str(ex.comments[i])
            if ex.comments[i]:
                comm = ex.comments[i].replace(',', '')
            if ex.turn_type[i]:
                if not ((ex.turn_type[i] in [str(None),None,str(' ')]) and (comm in [str(None),None,str(' ')])):
                    comm += ':{}'.format(str(ex.turn_type[i]).lower())
            if comm in [str(None),None,str(' ')]:
                comm = ''
               
            f.write("""%s,ALT=%3.2f kft %s ,%+2.12f,%+2.12f\n""" %(
                    ex.wpname[i],ex.alt_kft[i],comm,ex.lat[i],ex.lon[i]))
        f.close()
    
        if verbose: print('.. saving FOREFLIGHT one liner to {}'.format(filename+'_'+ex.name+'_FOREFLIGHT_oneline.txt'))
        fo = open(filename+'_'+ex.name+'_FOREFLIGHT_oneline.txt','w+')
        fo.write(one_line_points(ex,wpnames=ex.wpname))
        fo.close()
    
    if 'er2' in ex.p_info.get('preferred_file_format',['foreflight']):
        if verbose: print('.. saving ER2 csv to {}'.format(filename+'_'+ex.name+'.csv'))
        fe = open(filename+'_'+ex.name+'.csv','w+')
        fe.write('ID,Description,LAT,LONG,Altitude [kft],UTC [hh:mm],Comments\n')
        for i in range(ex.n):
            comm = ex.comments[i]
            if ex.comments[i]:
                comm = ex.comments[i].replace(',', '')
            w = ex.WP[i]
            x = ex
            wp_str = eval("f'{}'".format(ex.p_info.get('waypoint_format','{x.name[0]}{x.datestr.split("-")[2]}{w:02d}')))
            desc = '.'+ex.wpname[i]
            if wp_str in ex.wpname[i]:
                desc = '.'+wp_str[0]+wp_str[3:5]
            fe.write("""%2.0f,%s,%+2.12f,%+2.12f,%3.2f,%2.0f:%02.0f,%s\n""" %(
                    ex.WP[i],desc,ex.lat[i],ex.lon[i],ex.alt_kft[i],np.floor(ex.utc[i]),(ex.utc[i]-np.floor(ex.utc[i]))*60.0,comm))
        fe.close()
        return #no need to print out the rest
    
    if 'ufp' in ex.p_info.get('preferred_file_format',['foreflight']):
        if verbose: print('.. saving UFP csv to {}'.format(filename+'_'+ex.name+'_UFP.csv'))
        fu = open(filename+'_'+ex.name+'_UFP.csv','w+')
        fu.write('Waypoint,LAT,LONG,Description\n')
        for i in range(ex.n):
            if ex.wpname[i] in ex.wpname[0:i]: continue
            comm = ex.comments[i]
            if ex.comments[i]:
                comm = ex.comments[i].replace(',', '')
            if ex.turn_type[i]:
                comm += ' {}'.format(str(ex.turn_type[i]).lower())
            fu.write("""%s,%+2.12f,%+2.12f,ALT=%3.2f kft %s\n""" %(
                    ex.wpname[i],ex.lat[i],ex.lon[i],ex.alt_kft[i],comm))
        fu.close()
    
    if 'honeywell' in ex.p_info.get('preferred_file_format',['foreflight']):
        if verbose: print('.. saving Honeywell csv to {}'.format(filename+'_'+ex.name+'_Honeywell.csv'))
        fh = open(filename+'_'+ex.name+'_Honeywell.csv','w+')
        fh.write('E,WPT,FIX,LAT,LON\n')
        for i in range(ex.n):
            if ex.wpname[i] in ex.wpname[0:i]: continue
            lat_str,lon_str = format_lat_lon(ex.lat[i],ex.lon[i],format='NDDD MM.SS')
            comm = ex.comments[i]
            if ex.comments[i]:
                comm = ex.comments[i].replace(',', '')
                if ex.turn_type[i]:
                    if not ((ex.turn_type[i] in [str(None),None,str(' ')]) and (comm in [str(None),None,str(' ')])):
                        comm += ' {}'.format(str(ex.turn_type[i]).lower())
            if comm in [str(None),None,str(' ')]:
                comm = ''
            fh.write("""x,%s,ALT=%3.2f kft %s,%s,%s\n""" %(
                    ex.wpname[i],ex.alt_kft[i],comm,lat_str,lon_str))
        fh.close()
    
                
def format_lat_lon(lat,lon,format='DD MM SS'):
    'Lat and lon formatter'
    if format == 'DD MM SS':
        def deg_to_dms(deg):
            d = int(deg)
            md = abs(deg - d) * 60
            m = int(md)
            sd = (md - m) * 60
            return [d, m, sd]
        latv = deg_to_dms(lat)
        lonv = deg_to_dms(lon)
        lat_f = '{:02d} {:02d} {:04.1f}'.format(latv[0],latv[1],latv[2])
        lon_f = '{:02d} {:02d} {:04.1f}'.format(lonv[0],lonv[1],lonv[2])
    elif format == 'NDDD MM.SS':
        def deg_to_dms(deg):
            d = int(deg)
            md = abs(deg - d) * 60
            return [d, md]
        latv = deg_to_dms(lat)
        lonv = deg_to_dms(lon)
        lat_f = '{n}{:02d} {:05.2f}'.format(abs(latv[0]),latv[1],n='N' if latv[0]>0 else 'S')
        lon_f = '{n}{:03d} {:05.2f}'.format(abs(lonv[0]),lonv[1],n='E' if lonv[0]>0 else 'W')
    elif format == 'DD MM':
        def deg_to_dm(deg):
            d = int(deg)
            md = abs(deg - d) * 60
            return [d, md]
        latv = deg_to_dm(lat)
        lonv = deg_to_dm(lon)
        lat_f = '{:02} {:05.2f}'.format(int(latv[0]),latv[1])
        lon_f = '{:02} {:05.2f}'.format(int(lonv[0]),lonv[1])
    return lat_f,lon_f
    
def one_line_points(a,wpnames=None):
    'Fromatting all waypoints onto one line for foreflight'
    def deg_to_dm(deg):
        d = int(deg)
        md = abs(deg - d) * 60
        return [d, md]
    str = ''
    if not wpnames:
        for i in range(len(a.lon)):
            latv = deg_to_dm(a.lat[i])
            lonv = deg_to_dm(a.lon[i])
            lat_f = '{n}{:02d}{:06.3f}'.format(abs(latv[0]),latv[1],n='N' if latv[0]>0 else 'S')
            lon_f = '{n}{:02d}{:06.3f}'.format(abs(lonv[0]),lonv[1],n='E' if lonv[0]>0 else 'W')
            str = str+lat_f+'/'+lon_f+' '
    else:
        for w in wpnames:
            str = str+w+' ' 
    return str.rstrip()
        
def get_curdir():
    'Program that gets the path of the script: for use in finding extra files'
    from os.path import dirname, realpath
    from sys import argv
    if __file__:
        path = dirname(realpath(__file__))
    else:
        path = dirname(realpath(argv[0]))
    return path
    
def freeze_top_pane(wb):
    'Freezes and formats the top pane window in the current excel workbook (wb)'
    import xlwings as xw
    try:
        active_window = wb.app.api.ActiveWindow
        active_window.FreezePanes = False
        active_window.SplitColumn = 0
        active_window.SplitRow = 1
        active_window.FreezePanes = True
    except:
        pass
    wb.sheets.active.range('1:1').font.bold = True
    wb.sheets.active.range('1:1').autofit()
    
    ## old way
    #from sys import platform
    #if platform.startswith('win'):
    #    from win32com.client import Dispatch
    #    xl = Dispatch("Excel.Application")
    #    xl.ActiveWorkbook.Windows(1).SplitRow = 1.0
    #    xl.Range(address).Font.Bold = True
    
    return